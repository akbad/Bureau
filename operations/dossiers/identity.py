"""Identity resolution for dossier agents (v3 single-store model).

# Design rationale

`resolve_identity` runs on every identity-bearing connect and answers exactly
one question: *which registration row is this caller, right now?* Its return
value — the resolved agent id — is the principal every downstream CAS predicate
is written against (`complete_task`, `claim_task`, `update_task --agent`, lock
acquire/release all gate on `WHERE owner = <resolved_agent_id>`). If it returns
the wrong id, or a non-deterministic one across resume, every guard is silently
wrong. So it is made correct by construction; the rest of the v3 design
composes against it.

## Single store: the DB row IS the identity

v2 kept identity in two places — an on-disk session marker file and a
`registrations` row — and branched on their cross-product. Every write
ordering left a window where the two diverged. v3 deletes the file. The
`registrations` row is the only identity store, so the divergence class is
gone by construction.

What the file used to provide — self-identification across process death — is
recovered by a **deterministic** orchestrator id: a pure function of
(slug, agent_type). A resuming process recomputes its own id from inputs it
already holds, with nothing to read back first.

## The collapse: one conditional insert, then dispatch

The partial `UNIQUE(agent_type) WHERE role='orchestrator'` index makes the
orchestrator slot a single row. v2's four branches (fresh / same-session /
concurrent / adopt) collapse: fresh, same-session, and adopt all converge to
"my cli_pid owns this row"; only a live *other* instance (concurrent) diverges
and is rejected. The write is a single target-less `INSERT ... ON CONFLICT DO
NOTHING`, whose `was_insert` result drives a post-SQL dispatch on liveness.

## Why liveness stays outside SQL

`_process_alive` (in `db`) is `os.kill(pid, 0)`, never a SQL predicate: SQL has
no portable, side-effect-free liveness primitive, so a transaction depending on
one would be non-deterministic and untestable. As an injectable Python
function, every branch (alive / dead / raises) is unit-testable by stubbing it.
"""
import hashlib
import logging
import os
import subprocess

import sqlite3

from operations.dossiers.db import _now_iso, _process_alive
from operations.dossiers.errors import ConcurrentInstanceError

_log = logging.getLogger(__name__)

# Bound on the adopt-race re-resolve loop. Four consecutive races is
# astronomically unlikely on a solo system; surfacing it loudly beats looping
# forever. This is resolution contention, distinct from the task-CAS errors.
MAX_RESOLVE_ATTEMPTS = 4

# timeout for the `ps` ancestor lookup; 2s is generous for a local `ps` and
# bounds worst-case CLI latency if something is very wrong.
_PS_TIMEOUT_SECONDS = 2


def _orchestrator_agent_id(slug: str, agent_type: str) -> str:
    """Return the deterministic orchestrator id for a (slug, agent_type) slot.

    Deterministic, not a random UUID: the same slot always resolves to the same
    id, so a resuming process recomputes its identity without reading it back,
    and Mechanism 1 (identity-reset detection) works because a returning agent
    re-inserts a *recognizable* id. The id is intentionally not unique across
    *time* for a slot — ownership is per-slot, and `reap_log` carries the
    temporal distinction on the rare occasions it is needed.
    """
    digest = hashlib.sha256(
        f"{slug}\x00{agent_type}\x00orchestrator".encode()
    ).hexdigest()[:16]
    return f"orch-{agent_type}-{digest}"


def _ppid_via_proc(pid: int) -> int | None:
    """Return the parent pid of `pid` via /proc/<pid>/stat, or None.

    Works in Linux containers without procps (distroless/Alpine), where `ps`
    is absent. The stat line is ``<pid> (<comm>) <state> <ppid> ...``; ``comm``
    can contain spaces and parens, so the fields after it are parsed from the
    rightmost ``)`` — field[0] is state, field[1] is ppid.
    """
    try:
        with open(f"/proc/{pid}/stat") as f:
            content = f.read()
    except OSError:
        return None
    try:
        after = content[content.rindex(")") + 1:].split()
        ppid = int(after[1])
    except (ValueError, IndexError):
        return None
    return ppid if ppid > 0 else None


def _ppid_via_ps(pid: int) -> int | None:
    """Return the parent pid of `pid` via `ps -o ppid=`, or None.

    Portable POSIX fallback for platforms without `/proc` (macOS/BSD).
    """
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=True,
            timeout=_PS_TIMEOUT_SECONDS,
        )
        ppid = int(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        return None
    return ppid if ppid > 0 else None


def _get_cli_process_pid() -> int:
    """Resolve the pid of the long-lived CLI process to register as.

    `os.getppid()` returns the shell pid, which churns on every tool call (a
    fresh shell often spawns per invocation), defeating liveness checks. The
    enclosing CLI process (Node.js for Claude Code, Python for Codex, ...) is
    the long-lived ancestor. The chain degrades through four sources:

      1. `BUREAU_CLI_PID` env var, if a wrapper/harness/test exported it.
      2. `/proc/<shell_pid>/stat` ancestor walk (Linux containers).
      3. `ps -o ppid= -p <shell_pid>` (macOS/BSD).
      4. `os.getppid()` as the last-resort degrade.

    Reaching the degrade requires *no env, no /proc, and no ps* simultaneously
    — a vanishingly narrow intersection on any real stack. TODO(#26): a
    `cli_pid_strict` config knob would refuse (fail closed) instead of
    degrading; today it always degrades (the documented default).
    """
    env = os.environ.get("BUREAU_CLI_PID")
    if env:
        try:
            pid = int(env)
        except ValueError:
            _log.warning("Ignoring non-integer BUREAU_CLI_PID=%r", env)
        else:
            if pid > 0:
                return pid

    shell_pid = os.getppid()
    for source in (_ppid_via_proc, _ppid_via_ps):
        pid = source(shell_pid)
        if pid is not None:
            return pid

    _log.warning(
        "Falling back to shell PID %d for cli_pid (no BUREAU_CLI_PID, /proc, "
        "or ps); liveness checks will be weaker.",
        shell_pid,
    )
    return shell_pid


def _maybe_warn_identity_reset(
    conn: sqlite3.Connection, agent_type: str, new_agent_id: str
) -> None:
    """Warn (Mechanism 1) if this fresh insert follows a recent reap.

    A fresh insert (`was_insert=True`) normally means "first-ever session for
    this type on this dossier". It can also mean "my prior identity was reaped
    while I was idle" — including the case where primary defense's PID oracle
    wrongly reported me dead. Cross-referencing `reap_log` disambiguates and
    surfaces the reversion on the *first connect after return*, not later when a
    CAS silently fails. Observability is independent of prevention's success.
    """
    recent = conn.execute(
        "SELECT agent_id, reaped_at, tasks_reverted, stale_by_sec, reap_reason "
        "FROM reap_log "
        "WHERE agent_type = ? AND reaped_at > datetime('now', '-1 hour') "
        "ORDER BY reaped_at DESC LIMIT 1",
        (agent_type,),
    ).fetchone()
    if recent is None:
        return
    _log.warning(
        "IDENTITY RESET: your prior %s identity '%s' was reaped at %s "
        "(reason=%s, idle_for=%ss). Tasks %s were reverted and any lock was "
        "released. You now have fresh identity '%s'. Re-claim any in-progress "
        "work from the prior session manually.",
        agent_type, recent["agent_id"], recent["reaped_at"],
        recent["reap_reason"], recent["stale_by_sec"],
        recent["tasks_reverted"], new_agent_id,
    )


def resolve_identity(
    conn: sqlite3.Connection,
    slug: str,
    agent_type: str,
) -> str:
    """Resolve a bare orchestrator type to its deterministic agent id.

    One target-less insert-or-nothing, then a liveness-gated dispatch, in a
    bounded re-resolve loop. Returns the resolved agent id. Refreshes
    `last_heartbeat` on adopt/same-session so an active agent's row is never
    stale (which is what makes PID-liveness cleanup safe to run on the same
    connect).

    Args:
        conn: open dossier DB connection (v4 schema).
        slug: dossier slug (no ``.db`` suffix); an input to the id hash only.
        agent_type: bare CLI type (``claude-code``, ``codex``, ...).

    Returns:
        The resolved orchestrator ``agent_id`` (``orch-<type>-<16hex>``).

    Raises:
        ConcurrentInstanceError: a live other instance of this type owns the
            slot.
        RuntimeError: the adopt-race loop did not converge (should-never-happen
            invariant violation, not a branchable condition).
    """
    my_cli_pid = _get_cli_process_pid()
    my_id = _orchestrator_agent_id(slug, agent_type)

    for _attempt in range(MAX_RESOLVE_ATTEMPTS):
        now = _now_iso()

        # Phase 1: insert-or-nothing. Target-less DO NOTHING catches BOTH
        # unique constraints (agent_id and the orchestrator slot) and never
        # overwrites an existing row — a targeted upsert would raise on the
        # non-targeted constraint. See db._CREATE_REGISTRATIONS.
        cur = conn.execute(
            "INSERT INTO registrations "
            "(agent_id, agent_type, role, cli_pid, registered_at, last_heartbeat) "
            "VALUES (?, ?, 'orchestrator', ?, ?, ?) "
            "ON CONFLICT DO NOTHING",
            (my_id, agent_type, my_cli_pid, now, now),
        )
        if cur.rowcount == 1:  # was_insert
            _maybe_warn_identity_reset(conn, agent_type, my_id)
            conn.commit()
            return my_id  # Fresh (or identity-reset, warned above)

        # Phase 2: a row holds the orchestrator slot. Read it and dispatch on
        # liveness. The partial unique index guarantees at most one.
        prior = conn.execute(
            "SELECT agent_id, cli_pid FROM registrations "
            "WHERE agent_type = ? AND role = 'orchestrator'",
            (agent_type,),
        ).fetchone()
        if prior is None:
            # The slot row vanished between the no-op insert and this read (a
            # concurrent reap/deregister). Re-resolve from the top.
            continue

        if prior["cli_pid"] == my_cli_pid:
            # Same-session: refresh heartbeat only.
            conn.execute(
                "UPDATE registrations SET last_heartbeat = ? WHERE agent_id = ?",
                (now, prior["agent_id"]),
            )
            conn.commit()
            return prior["agent_id"]

        if _process_alive(prior["cli_pid"]):
            # Concurrent: a live other instance owns the slot. Refuse.
            raise ConcurrentInstanceError(
                f"A live {agent_type} orchestrator (cli_pid={prior['cli_pid']}) "
                f"already owns dossier '{slug}'. Refusing to take over."
            )

        # Phase 3: prior cli_pid is dead => Adopt via a conditional takeover.
        # CAS on the slot row + the cli_pid we observed dead: if it still
        # matches, we win and inherit the slot's agent_id; if not, another
        # process adopted first (adopt race) and we re-resolve.
        taken = conn.execute(
            "UPDATE registrations SET cli_pid = ?, last_heartbeat = ? "
            "WHERE agent_id = ? AND cli_pid = ?",
            (my_cli_pid, now, prior["agent_id"], prior["cli_pid"]),
        )
        if taken.rowcount == 1:
            conn.commit()
            return prior["agent_id"]  # Adopt succeeded
        # rowcount == 0: adopt race. On re-resolve we will see the winner's
        # live cli_pid (=> Concurrent, reject) or our own (=> Same-session);
        # either way the loop terminates well within MAX_RESOLVE_ATTEMPTS.
        continue

    raise RuntimeError(
        f"resolve_identity for '{slug}'/{agent_type} did not converge after "
        f"{MAX_RESOLVE_ATTEMPTS} attempts (adopt-race contention)."
    )
