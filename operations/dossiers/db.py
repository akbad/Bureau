"""Dossier SQLite database creation, connection, schema, and migration."""
import json
import logging
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from operations.config_loader import (
    get_cleanup_check_interval_seconds,
    get_registration_ttl_seconds,
)

# Schema 4 (v3 design): single-store identity. The `registrations` row IS the
# identity (no session marker files); `cli_pid` + `last_heartbeat` drive the
# PID-liveness-aware cleanup; `reap_log` records every reap for forensics and
# identity-reset detection.
SCHEMA_VERSION = 4

# busy_timeout for every connection. Single-user contention windows are
# sub-second; 30s is ample headroom for the migration's BEGIN IMMEDIATE and
# concurrent fold transactions. TODO(#26): wire to a config knob.
_BUSY_TIMEOUT_MS = 30_000

_log = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Input validation limits ────────────────────────────────────────────
# Prevent unbounded storage and rendering costs from oversized inputs.
# Values are generous upper bounds for legitimate use; anything beyond
# these indicates a bug or abuse, not a real workflow.
MAX_SUBJECT_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 10_000
MAX_DIGEST_LENGTH = 500_000       # ~500KB — large but bounded
MAX_CONTEXT_NOTES_LENGTH = 10_000
MAX_TASKS_PER_DOSSIER = 200

# valid task lifecycle states — used by CAS operations (claim, complete)
# and enforced at write time to prevent silent state corruption
VALID_STATUSES = {"pending", "in_progress", "completed", "blocked", "deleted"}


def _check_path_containment(path: Path, parent: Path) -> None:
    """Raise ValueError if *path* escapes *parent* after resolution."""
    if not path.resolve().is_relative_to(parent.resolve()):
        raise ValueError(f"Path escapes allowed directory: {path}")


def safe_db_path(dossiers_dir: Path, slug: str) -> Path:
    """Resolve a slug to a DB path, ensuring it stays within the dossiers directory.

    Prevents path traversal attacks via crafted slugs like '../../etc/foo'.
    """
    path = (dossiers_dir / f"{slug}.db").resolve()
    _check_path_containment(path, dossiers_dir)
    return path


def _process_alive(pid: int | None) -> bool:
    """Return True if a process with `pid` exists on this host.

    The low-level liveness oracle, shared by `identity.resolve_identity`
    (concurrent/adopt dispatch) and `_maybe_reap_stale_registrations`
    (cleanup's two-phase filter). It lives in `db` — the lowest module in the
    dossiers dependency chain — so both higher layers can import it without a
    cycle.

    Uses signal 0, a no-op existence check that never delivers a signal.
    `PermissionError` is treated as alive: the process exists but is owned by a
    different user. This is the safe bias — surface a false conflict / decline
    to reap rather than silently adopt or reap an unrelated live process.

    `None` (a worker with no recorded `cli_pid`) and `pid <= 0` (which
    `os.kill` would interpret as a process-group target) both return False so
    callers fall back to timestamp-only handling.
    """
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# characters that can introduce markdown structure (headings, bold,
# blockquotes, table delimiters, code spans, links) when agent-authored
# content is interpolated into rendered context output
_MD_CONTROL_CHARS = ("|", "*", "#", ">", "`", "[", "]")


def escape_md(text: str | None) -> str:
    """Escape markdown control characters in agent-authored content.

    Prevents stored dossier data from being interpreted as markdown
    structure (headings, bold, blockquotes, table delimiters) when
    rendered into context injection output.

    Returns empty string for None input.
    """
    if text is None:
        return ""
    for ch in _MD_CONTROL_CHARS:
        text = text.replace(ch, f"\\{ch}")
    return text


# ── Schema DDL ──────────────────────────────────────────────────────────
# The `registrations` and `reap_log` statements are defined as standalone
# constants so the *fresh-create* path (`_SCHEMA_SQL` via executescript) and
# the *migration* path (`migrate_v3_to_v4`, statement-by-statement inside one
# transaction) build byte-identical schema from a single source. Convergence
# of the two paths is asserted by a test (diff of sqlite_schema); divergence
# is the classic silent-migration bug.
#
# These deliberately omit "IF NOT EXISTS": the fresh path runs against a new
# file and the migration runs after DROP, so neither needs it, and its
# presence/absence would otherwise have to match exactly across both paths.
_CREATE_REGISTRATIONS = """CREATE TABLE registrations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id       TEXT NOT NULL UNIQUE,
    agent_type     TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'orchestrator'
                       CHECK (role IN ('orchestrator', 'worker')),
    cli_pid        INTEGER,
    registered_at  TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL
)"""

# The load-bearing invariant: at most one orchestrator per agent_type per
# dossier (the table is dossier-local — each dossier is its own .db file).
# Workers (role='worker') are excluded, so many of a type coexist.
_CREATE_REGISTRATIONS_INDEX = (
    "CREATE UNIQUE INDEX idx_registrations_orchestrator_slot "
    "ON registrations (agent_type) WHERE role = 'orchestrator'"
)

_CREATE_REAP_LOG = """CREATE TABLE reap_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reaped_at      TEXT NOT NULL,
    agent_id       TEXT NOT NULL,
    agent_type     TEXT NOT NULL,
    role           TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL,
    stale_by_sec   INTEGER NOT NULL,
    tasks_reverted TEXT,
    lock_released  INTEGER NOT NULL,
    reap_reason    TEXT NOT NULL
)"""

# No foreign key to registrations on purpose: a reap_log row must outlive the
# registration it describes (that row is gone the instant it is reaped).
_CREATE_REAP_LOG_INDEX = (
    "CREATE INDEX idx_reap_log_type_at ON reap_log (agent_type, reaped_at DESC)"
)

# Statements the v4 rebuild applies, in order, after dropping the v2/v3
# registrations table. Shared with _SCHEMA_SQL below.
_V4_REBUILD_STATEMENTS = (
    _CREATE_REGISTRATIONS,
    _CREATE_REGISTRATIONS_INDEX,
    _CREATE_REAP_LOG,
    _CREATE_REAP_LOG_INDEX,
)

# Tables/indexes unchanged since v2/v3. Kept as one executescript blob for the
# fresh-create path. registrations + reap_log are appended from the shared
# constants above so fresh-create and migrate cannot drift.
_BASE_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS metadata (
    id          INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,
    hash        TEXT NOT NULL,
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    agent       TEXT,
    project     TEXT,
    branch      TEXT,
    commit_hash TEXT,
    parent      TEXT,
    locked_by   TEXT,
    locked_at   TEXT,
    last_registration_cleanup TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    folded_at   TEXT NOT NULL,
    agent       TEXT NOT NULL,
    branch      TEXT,
    commit_hash TEXT,
    digest      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject     TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    owner       TEXT,
    blocked_by  TEXT,
    context_notes TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decisions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id),
    what        TEXT NOT NULL,
    why         TEXT NOT NULL,
    alternatives TEXT,
    decided_by  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS file_interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id),
    file_path   TEXT NOT NULL,
    action      TEXT NOT NULL,
    annotation  TEXT
);

CREATE INDEX IF NOT EXISTS idx_file_interactions_session
    ON file_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_session
    ON decisions(session_id);
"""

_SCHEMA_SQL = _BASE_SCHEMA_SQL + "\n" + ";\n".join(_V4_REBUILD_STATEMENTS) + ";\n"


def create_dossier_db(path: Path) -> None:
    """Create a new dossier database with the full v4 schema."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()
    path.chmod(0o600)  # owner read/write only


def _user_version(conn: sqlite3.Connection) -> int:
    """Return the database's PRAGMA user_version."""
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate_v3_to_v4(conn: sqlite3.Connection, path: Path) -> None:
    """Migrate a v3 dossier to v4: rebuild `registrations`, add `reap_log`.

    Called on every connect from `connect_dossier_db`, in place of v2/v3's
    always-run idempotent `_ensure_schema_current`. A destructive rebuild
    cannot use the always-run model (it would drop the table every connect),
    so this is **version-gated**: a no-op once `user_version >= 4`.

    ## Why drop-and-recreate, not backfill

    Registrations are a *cache* of liveness, not a system of record. v2/v3 ids
    (`<type>:<6hex>`) are never recomputed by v4's deterministic hash, so any
    backfilled row is orphaned on arrival and reaped on first cleanup; and a
    v2/v3 table can hold duplicate same-type rows that would violate the new
    partial `UNIQUE(agent_type) WHERE role='orchestrator'`. You invalidate a
    cache; you do not migrate it. The connecting agent re-registers this same
    connect; others re-register on their next.

    ## Crash safety (verified, not assumed)

    `DROP` + `CREATE`s + the `user_version` bump run inside one
    `BEGIN IMMEDIATE` transaction. SQLite DDL is transactional and
    `PRAGMA user_version` participates in the transaction (both proven by
    test), so a crash mid-migration rolls back to v3 and the migration
    re-runs cleanly on next open. `user_version` is bumped *last*, so even if
    that property ever regressed, a crash before COMMIT still leaves v3.

    ## Concurrency

    `BEGIN IMMEDIATE` takes the write lock (bounded by busy_timeout); a racing
    second connection re-reads `user_version >= 4` under the lock and no-ops.

    ## Belt and suspenders

    A `*.pre-v4.bak` copy is taken via `VACUUM INTO` *before* the rebuild
    (outside any transaction — VACUUM cannot run inside one). For a solo
    system this backup is more trustworthy than any rollback logic.

    Assumes a v3 base (all v3 columns present on the durable tables); this is
    the only shipped pre-v4 schema. Sub-v3 dossiers are not supported.
    """
    if _user_version(conn) >= SCHEMA_VERSION:
        return  # fast path: already migrated (or fresh-created at v4)

    # Backup before touching anything. VACUUM INTO requires no open
    # transaction and a non-existent target.
    conn.commit()
    backup = Path(str(path) + ".pre-v4.bak")
    backup.unlink(missing_ok=True)
    conn.execute("VACUUM INTO ?", (str(backup),))

    # Explicit transaction control: switch to autocommit so our manual
    # BEGIN IMMEDIATE governs atomicity (Python's implicit-transaction
    # handling would otherwise interfere with DDL ordering across versions).
    prev_isolation = conn.isolation_level
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        if _user_version(conn) >= SCHEMA_VERSION:
            # Race loser: another connection migrated while we took the lock.
            conn.execute("ROLLBACK")
            return
        # DROP TABLE removes the table's indexes (incl. the dead v2/v3
        # idx_registrations_type — Q7 resolved for free).
        conn.execute("DROP TABLE IF EXISTS registrations")
        for stmt in _V4_REBUILD_STATEMENTS:
            conn.execute(stmt)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")  # LAST write
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.isolation_level = prev_isolation

    _report_orphans(conn, path, backup)


def _report_orphans(conn: sqlite3.Connection, path: Path, backup: Path) -> None:
    """Print a one-time report of references stranded by the agent_id reset.

    The v4 `agent_id` format change strands pre-v4 identity references no v4
    agent will recompute: in-progress `tasks.owner` and `metadata.locked_by`.
    The migration does **not** silently mutate these durable rows — it surfaces
    the otherwise-confusing-error-later as a clear-message-now, with the exact
    recovery command. Recovery is manual (and uniform with the pre-v3 lock
    policy): an auto-rewrite could collide with live state and be silently
    stolen.
    """
    orphaned = conn.execute(
        "SELECT id, owner FROM tasks "
        "WHERE status = 'in_progress' AND owner IS NOT NULL ORDER BY id"
    ).fetchall()
    lock = conn.execute(
        "SELECT locked_by FROM metadata WHERE locked_by IS NOT NULL"
    ).fetchone()

    if not orphaned and not lock:
        return  # clean migration; nothing stranded, stay quiet

    slug = path.stem
    out = sys.stderr
    print(f"v3->v4 migration complete for '{slug}'. Backup: {backup.name}", file=out)
    print("  Registrations reset (liveness cache; agents re-register on next connect).", file=out)
    if orphaned:
        ids = ", ".join(f"#{r['id']} ({r['owner']})" for r in orphaned)
        print(f"  {len(orphaned)} in-progress task(s) now have orphaned owners: {ids}", file=out)
        print(f"    Reassign with: bureau-dossiers tasks {slug} update --id <n> --status pending", file=out)
    if lock:
        print(f"  1 lock held by a pre-v4 identity: {lock['locked_by']}.", file=out)
        print(f"    Clear with: bureau-dossiers lock {slug} release --force", file=out)


def _maybe_reap_stale_registrations(
    conn: sqlite3.Connection, *, protect_agent_id: str | None = None
) -> None:
    """Reap stale-AND-dead agent registrations if the throttle window elapsed.

    Runs as a preamble to `connect_dossier_db`, eliminating any external
    sweeper process. The v3 PRIMARY defense against Scenario B (a live-but-idle
    orchestrator's row reaped by another CLI's cleanup).

    ## Two-phase filter: stale AND proven dead

    A row is reaped only if it is *both* past TTL by `last_heartbeat` *and*
    its `cli_pid` is proven dead:

      1. Phase A — SQL narrows to rows past TTL (`last_heartbeat < cutoff`),
         excluding `protect_agent_id` (the connecting agent's own row, a
         belt-and-suspenders guard on top of the resolve-before-reap ordering
         in `connect_dossier_db`).
      2. Phase B — Python confirms death via `_process_alive(cli_pid)`. A live
         process with a stale heartbeat (idle-but-alive) is skipped. A worker
         with no recorded `cli_pid` falls back to timestamp-only.
      3. Phase C — for each genuinely-dead row: write a `reap_log` audit row,
         then cascade (revert its in-progress tasks to pending, release its
         lock, delete the registration).

    Every failure direction of the `os.kill` oracle is safe: it either
    preserves the row (one extra TTL window of lingering) or reverts to
    baseline timestamp-only behavior (no regression). The identity-reset
    warning (Mechanism 1, in `resolve_identity`) covers the rare wrongly-reaped
    live agent on its next connect by reading `reap_log`.

    ## Why `sqlite3.Error` specifically

    A broad `except Exception: pass` would silently swallow Python-level bugs
    (TypeError, AttributeError) forever. Catching `sqlite3.Error` handles the
    real DB failure modes (schema mismatch, SQLITE_BUSY, corruption) while
    letting programming bugs surface.
    """
    # step 1: throttle check. strftime('%s', ...) returns seconds-since-epoch;
    # the subtraction gives elapsed seconds without parsing ISO in Python.
    row = conn.execute(
        "SELECT last_registration_cleanup, "
        "CAST((strftime('%s', 'now') - "
        "strftime('%s', last_registration_cleanup)) AS INTEGER) AS elapsed_seconds "
        "FROM metadata"
    ).fetchone()

    if row is None:
        return  # uninitialized dossier (metadata row not yet created)

    interval = get_cleanup_check_interval_seconds()
    if (
        row["last_registration_cleanup"] is not None
        and row["elapsed_seconds"] is not None
        and row["elapsed_seconds"] < interval
    ):
        return  # checked recently, skip

    ttl = get_registration_ttl_seconds()
    now = _now_iso()
    cutoff = f"-{ttl} seconds"

    try:
        with conn:
            # Phase A: SQL candidates — rows past TTL by last_heartbeat, never
            # the connecting agent's own row.
            candidates = conn.execute(
                "SELECT agent_id, agent_type, role, cli_pid, last_heartbeat, "
                "CAST((strftime('%s', 'now') - "
                "strftime('%s', last_heartbeat)) AS INTEGER) AS stale_by_sec "
                "FROM registrations "
                "WHERE last_heartbeat < datetime('now', ?) "
                "AND (? IS NULL OR agent_id != ?)",
                (cutoff, protect_agent_id, protect_agent_id),
            ).fetchall()

            for cand in candidates:
                # Phase B: liveness filter.
                cli_pid = cand["cli_pid"]
                if cli_pid is None:
                    reason = "timestamp_only"  # worker without a recorded pid
                elif not _process_alive(cli_pid):
                    reason = "pid_dead"
                else:
                    # idle-but-alive: stale heartbeat, live process. Skip.
                    _log.debug(
                        "Skipping reap of %s: cli_pid %s alive despite stale "
                        "heartbeat (last=%s, stale_by=%ss)",
                        cand["agent_id"], cli_pid, cand["last_heartbeat"],
                        cand["stale_by_sec"],
                    )
                    continue

                # Phase C: audit, then cascade reap for this row.
                reverted = conn.execute(
                    "SELECT id FROM tasks "
                    "WHERE owner = ? AND status = 'in_progress' ORDER BY id",
                    (cand["agent_id"],),
                ).fetchall()
                reverted_ids = [t["id"] for t in reverted]
                if reverted_ids:
                    conn.execute(
                        "UPDATE tasks "
                        "SET status = 'pending', owner = NULL, updated_at = ? "
                        "WHERE owner = ? AND status = 'in_progress'",
                        (now, cand["agent_id"]),
                    )
                lock_cur = conn.execute(
                    "UPDATE metadata SET locked_by = NULL, locked_at = NULL "
                    "WHERE locked_by = ?",
                    (cand["agent_id"],),
                )
                lock_released = 1 if lock_cur.rowcount > 0 else 0
                conn.execute(
                    "DELETE FROM registrations WHERE agent_id = ?",
                    (cand["agent_id"],),
                )
                conn.execute(
                    "INSERT INTO reap_log "
                    "(reaped_at, agent_id, agent_type, role, last_heartbeat, "
                    "stale_by_sec, tasks_reverted, lock_released, reap_reason) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        now, cand["agent_id"], cand["agent_type"], cand["role"],
                        cand["last_heartbeat"], cand["stale_by_sec"],
                        json.dumps(reverted_ids), lock_released, reason,
                    ),
                )

            # always bump the throttle timestamp, even on an empty reap, so
            # the next call correctly skips within the throttle window
            conn.execute(
                "UPDATE metadata SET last_registration_cleanup = ?",
                (now,),
            )
    except sqlite3.Error:
        # swallow DB failures only; Python-level bugs must propagate.
        # The `with conn:` already rolled back — caller gets a clean connection.
        pass


def connect_dossier_db(
    path: Path, *, agent_type: str | None = None, slug: str | None = None
) -> sqlite3.Connection:
    """Open an existing dossier database. Raises FileNotFoundError if missing.

    When both `agent_type` and `slug` are supplied (the identity-bearing entry
    points — `cli._resolve_agent`, `fold`), the caller's identity is resolved
    *before* cleanup runs on the same connection. This is the C1 fix: it lets a
    returning orchestrator adopt and refresh its row's heartbeat before
    `_maybe_reap_stale_registrations` can consider it, and supplies
    `protect_agent_id` so the agent's own row is never a reap candidate.

    Agent-less callers (lock/task reads, unfold, context, fork) pass neither;
    cleanup still runs (PID-liveness-aware), it just has no row to protect.
    """
    if not path.exists():
        raise FileNotFoundError(f"Dossier database not found: {path}")
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        migrate_v3_to_v4(conn, path)

        protect_agent_id = None
        if agent_type is not None and slug is not None:
            # local import: identity -> registration -> db, so a module-level
            # import here would be a cycle.
            from operations.dossiers.identity import resolve_identity

            protect_agent_id = resolve_identity(conn, slug, agent_type)

        _maybe_reap_stale_registrations(conn, protect_agent_id=protect_agent_id)
    except BaseException:
        # resolve_identity (ConcurrentInstanceError), migration, or cleanup may
        # raise; don't leak the connection we just opened.
        conn.close()
        raise
    return conn


@contextmanager
def open_dossier_db(
    path: Path, *, agent_type: str | None = None, slug: str | None = None
):
    """Context manager for dossier database connections.

    Guarantees connection cleanup even if an exception is raised. Forwards
    `agent_type`/`slug` to `connect_dossier_db` for resolve-before-reap.
    """
    conn = connect_dossier_db(path, agent_type=agent_type, slug=slug)
    try:
        yield conn
    finally:
        conn.close()
