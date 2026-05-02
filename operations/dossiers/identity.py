"""Session marker file management and identity resolution.

# Design rationale

The CLI maps a bare agent type (e.g., `claude-code`) to a unique per-session
identity (e.g., `claude-code:a7f3c2`) so that two concurrent instances of the
same CLI type cannot silently collide on lock or task ownership.

Identity lives in two stores with distinct lifetimes:

  - On-disk session file at ``<sessions_root>/<slug>/<agent_type>`` keyed by
    (slug, agent_type). Survives process restarts. Content:
    ``{agent_id, pid, created_at}``.
  - ``registrations`` table row keyed by ``agent_id``. Survives everything
    short of a fold or TTL-expired inline cleanup.

The session file is the primary oracle; the registrations row mirrors it so
that DB-side queries (liveness, cleanup, ``who``) can reason about identities.

## Why session file + PID, not PID alone?

Pure-PID identity breaks on session resume: when the user kills and resumes
the CLI (``claude --resume``), the underlying Node.js/Python process acquires
a new PID while the logical session is unchanged. Storing identity on disk
and using the PID only for liveness-testing is what lets the "adopt" branch
work after restarts.

## Why grandparent PID, not ``os.getppid()``?

``os.getppid()`` returns the shell PID, which is ephemeral: a new shell is
often spawned per tool call, defeating the liveness check (the previous
shell has always died by the next invocation). The grandparent PID is the
long-lived enclosing CLI process (Node.js for Claude Code, Python for
Codex, etc.), which persists for the duration of the user's session.

## Concurrency model

Session-file writes are atomic via ``os.rename`` from a same-directory
tempfile (POSIX guarantee). The registrations table provides SQLite-level
atomicity for DB operations. The two stores can briefly diverge (e.g.,
session file written, DB insert pending). The ``UNIQUE(agent_id)`` constraint
on ``registrations`` prevents duplicate identities even under crashes.
"""
import json
import logging
import os
import secrets
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from operations.dossiers.db import _check_path_containment, _now_iso
from operations.dossiers.errors import ConcurrentInstanceError
from operations.dossiers.registration import refresh_heartbeat, register_agent

_log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────
# 3 bytes = 6 hex chars = ~16.7M distinct values per (agent_type, dossier).
# Collision probability on a UNIQUE retry is <1e-13 at realistic scales.
_AGENT_ID_RANDOM_BYTES = 3

# timeout for the grandparent PID lookup; 2s is generous for a local `ps`
# and bounds the worst-case CLI latency if something is very wrong.
_PS_TIMEOUT_SECONDS = 2

# default sessions root mirrors cli.py's DEFAULT_DOSSIERS_DIR pattern.
# note: conversations.storage_dir is declared in defaults.yml but not yet
# consumed; wiring it through is out of scope for v2.
DEFAULT_SESSIONS_ROOT = Path(os.path.expanduser("~/.config/bureau/sessions"))


def _get_cli_process_pid() -> int:
    """Return the long-lived CLI process PID (grandparent of this Python process).

    Uses ``ps -o ppid= -p <shell_pid>`` because `os.getppid` returns the shell
    PID, which churns on every tool call. The grandparent PID is the enclosing
    Node.js / Python CLI process that owns the session.

    Fallback: on `ps` failure (containers without procps, unusual shells),
    return the shell PID and emit a warning. Correctness is preserved — the
    session file is simply rewritten more often — but the liveness-check
    distinction between concurrent and adopted weakens, because a fresh shell
    per tool call looks like a dead process to the next invocation.
    """
    shell_pid = os.getppid()
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(shell_pid)],
            capture_output=True,
            text=True,
            check=True,
            timeout=_PS_TIMEOUT_SECONDS,
        )
        return int(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError) as e:
        _log.warning(
            "Falling back to shell PID for identity (ps failed: %s); "
            "liveness check will be weaker.",
            e,
        )
        return shell_pid


def _process_alive(pid: int) -> bool:
    """Return True if a process with `pid` exists on this host.

    Uses signal 0, a no-op existence check that never actually delivers a
    signal. `PermissionError` is treated as alive: the process exists but is
    owned by a different user. This is the safe bias for concurrent-instance
    detection — we would rather surface a false conflict than silently adopt
    an unrelated live process's identity.

    Guards against `pid <= 0` because `os.kill(0, ...)` targets the entire
    process group, which is never a valid identity-resolution PID.
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def safe_session_file_path(sessions_root: Path, slug: str, agent_type: str) -> Path:
    """Resolve (slug, agent_type) to a session file path, containment-checked.

    Mirrors `safe_db_path` in db.py: prevents path traversal via crafted
    slugs or agent types ('..', '/', absolute paths, etc.).
    """
    path = (sessions_root / slug / agent_type).resolve()
    _check_path_containment(path, sessions_root)
    return path


def _read_session_file(path: Path) -> dict | None:
    """Read and parse a session marker file.

    Returns `None` on any of: missing file, invalid JSON, non-dict payload,
    missing required keys. Callers treat `None` as "no prior session" —
    corruption therefore triggers a fresh registration. Any orphaned
    registrations row from a prior session is reaped by inline cleanup
    after the TTL.
    """
    try:
        with path.open("r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    if not all(k in data for k in ("agent_id", "pid", "created_at")):
        return None
    return data


def _write_session_file(path: Path, data: dict) -> None:
    """Atomically write a session marker file with restrictive permissions.

    Writes to a tempfile in the same directory and then `os.rename`s, which
    is atomic on POSIX filesystems (both source and destination share an
    inode table). Directory is created 0o700; file is 0o600.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # tempfile in the same directory keeps rename on the same filesystem,
    # which is required for atomicity
    fd, tmp = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.chmod(tmp, 0o600)
        os.rename(tmp, path)
    except Exception:
        # best-effort tempfile cleanup on failure; ignore if already gone
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _delete_session_file(path: Path) -> None:
    """Remove a session marker file if present; silent on missing."""
    path.unlink(missing_ok=True)


def _generate_agent_id(agent_type: str) -> str:
    """Return a fresh agent_id of the form ``<agent_type>:<6-hex>``."""
    return f"{agent_type}:{secrets.token_hex(_AGENT_ID_RANDOM_BYTES)}"


def resolve_identity(
    conn: sqlite3.Connection,
    sessions_root: Path,
    slug: str,
    agent_type: str,
) -> str:
    """Resolve a bare agent type to a unique session identity.

    Runs the 4-branch algorithm and refreshes ``registered_at`` on every
    successful resolution as an implicit heartbeat.

    Branches:

    1. **Fresh** — no prior session file. Generate `agent_id`, write the
       session file, insert the `registrations` row.
    2. **Same session** — session file's PID equals the current CLI PID.
       Return the cached `agent_id`, refresh heartbeat.
    3. **Concurrent** — session file's PID differs and is alive. Raise
       `ConcurrentInstanceError`.
    4. **Adopt** — session file's PID differs and is dead (resume or crash).
       Update PID in both stores, refresh heartbeat, return the cached
       `agent_id`.

    Args:
        conn: open dossier DB connection.
        sessions_root: directory root holding per-dossier session files.
        slug: dossier slug (no ``.db`` suffix).
        agent_type: bare CLI type (``claude-code``, ``codex``, ...).

    Returns:
        The resolved `agent_id` (e.g., ``claude-code:a7f3c2``).

    Raises:
        ConcurrentInstanceError: another live process of the same CLI type
            holds the session for this dossier.
    """
    session_path = safe_session_file_path(sessions_root, slug, agent_type)
    cli_pid = _get_cli_process_pid()
    existing = _read_session_file(session_path)

    # branch 1: fresh registration
    # DB-first ordering: if the session file write fails after INSERT, the
    # stranded row is reaped by inline cleanup. If INSERT fails, no session
    # file was written and the caller can retry cleanly.
    # UNIQUE-violation retry lives here (not inside register_agent) so this
    # branch has full context to mint a fresh suffix.
    if existing is None:
        for attempt in range(2):
            agent_id = _generate_agent_id(agent_type)
            try:
                register_agent(conn, agent_id, agent_type, cli_pid, role="orchestrator")
                break
            except sqlite3.IntegrityError:
                if attempt == 1:
                    raise
        _write_session_file(
            session_path,
            {"agent_id": agent_id, "pid": cli_pid, "created_at": _now_iso()},
        )
        return agent_id

    agent_id = existing["agent_id"]
    stored_pid = existing["pid"]

    # branch 2: same session — fast path, one UPDATE
    if stored_pid == cli_pid:
        refresh_heartbeat(conn, agent_id)
        return agent_id

    # branch 3: concurrent live instance — refuse
    if _process_alive(stored_pid):
        raise ConcurrentInstanceError(
            f"Dossier has an active {agent_type} session "
            f"(PID {stored_pid}); refusing to resolve identity for "
            f"this process (PID {cli_pid})"
        )

    # branch 4: adopt — prior PID is dead, inherit the identity
    _write_session_file(
        session_path,
        {
            "agent_id": agent_id,
            "pid": cli_pid,
            "created_at": existing["created_at"],
        },
    )
    conn.execute(
        "UPDATE registrations SET ppid = ?, registered_at = ? WHERE agent_id = ?",
        (cli_pid, _now_iso(), agent_id),
    )
    conn.commit()
    return agent_id
