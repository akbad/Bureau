"""Dossier SQLite database creation and connection."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from operations.config_loader import (
    get_cleanup_check_interval_seconds,
    get_registration_ttl_seconds,
)

SCHEMA_VERSION = 3


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

_SCHEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS registrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id      TEXT NOT NULL UNIQUE,
    agent_type    TEXT NOT NULL,
    ppid          INTEGER,
    role          TEXT NOT NULL DEFAULT 'orchestrator',
    registered_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_file_interactions_session
    ON file_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_session
    ON decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_registrations_type
    ON registrations(agent_type);
"""


def create_dossier_db(path: Path) -> None:
    """Create a new dossier database with the full schema."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()
    path.chmod(0o600)  # owner read/write only


def _ensure_schema_current(conn: sqlite3.Connection) -> None:
    """Apply incremental schema migrations for older dossiers.

    Safe under concurrent access: if two agents open the same dossier
    simultaneously after an upgrade, the second ALTER TABLE will fail
    with OperationalError (duplicate column).  We catch and ignore that
    specific error since it means the migration already succeeded.
    """
    task_columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "context_notes" not in task_columns:
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN context_notes TEXT")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                pass  # another agent already applied this migration
            else:
                raise

    metadata_columns = {row[1] for row in conn.execute("PRAGMA table_info(metadata)").fetchall()}
    if "last_registration_cleanup" not in metadata_columns:
        try:
            conn.execute("ALTER TABLE metadata ADD COLUMN last_registration_cleanup TEXT")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                pass
            else:
                raise

    # CREATE TABLE IF NOT EXISTS is idempotent under concurrent access
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id      TEXT NOT NULL UNIQUE,
            agent_type    TEXT NOT NULL,
            ppid          INTEGER,
            role          TEXT NOT NULL DEFAULT 'orchestrator',
            registered_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_registrations_type
            ON registrations(agent_type)
    """)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _maybe_reap_stale_registrations(conn: sqlite3.Connection) -> None:
    """Reap stale agent registrations if the throttle window has elapsed.

    Runs as a preamble to `connect_dossier_db`. Eliminates dependency on an
    external sweeper process by piggybacking cleanup onto normal DB connections.

    ## Cascade on stale registration

    For each ``registrations`` row whose ``registered_at`` is older than
    ``registration_ttl`` (24h default):

      1. Release any ``metadata.locked_by`` match (NULL out lock).
      2. Reset any ``tasks.owner`` match with ``status = 'in_progress'`` back
         to ``pending`` with NULL owner.
      3. Delete the registrations row.

    All three steps run in a single ``with conn:`` transaction, atomic under
    SQLite's write-serialization. Concurrent callers both triggering cleanup
    are safe: SQLite serializes writes, and the second transaction's
    DELETE/UPDATE statements are no-ops after the first commit.

    ## Why `sqlite3.Error` specifically

    Broad ``except Exception: pass`` would silently swallow Python-level bugs
    (TypeError, AttributeError, refactoring errors) in this function — these
    would be invisible forever. Catching ``sqlite3.Error`` handles the real
    failure modes (schema mismatch, SQLITE_BUSY, corrupt DB) while letting
    programming bugs surface.

    ## Cost when throttled

    One single-row SELECT. The SELECT computes ``elapsed_seconds`` server-side
    via strftime so we avoid parsing ISO timestamps in Python.
    """
    # step 1: throttle check. strftime('%s', ...) returns seconds-since-epoch
    # as a string; the subtraction gives the elapsed seconds. Faster than
    # parsing ISO timestamps in Python.
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

    # step 2: reap. All SQL in a single transaction; `with conn:` commits on
    # success and rolls back on any sqlite3.Error.
    ttl = get_registration_ttl_seconds()
    now = _now_iso()
    cutoff = f"-{ttl} seconds"

    try:
        with conn:
            stale_rows = conn.execute(
                "SELECT agent_id FROM registrations "
                "WHERE registered_at < datetime('now', ?)",
                (cutoff,),
            ).fetchall()
            stale_ids = [r["agent_id"] for r in stale_rows]

            if stale_ids:
                placeholders = ",".join("?" * len(stale_ids))

                # release any locks held by a stale agent
                conn.execute(
                    f"UPDATE metadata "
                    f"SET locked_by = NULL, locked_at = NULL "
                    f"WHERE locked_by IN ({placeholders})",
                    stale_ids,
                )

                # reset in_progress tasks owned by stale agents to pending;
                # context_notes and other fields are preserved for re-assignment
                conn.execute(
                    f"UPDATE tasks "
                    f"SET status = 'pending', owner = NULL, updated_at = ? "
                    f"WHERE owner IN ({placeholders}) AND status = 'in_progress'",
                    [now, *stale_ids],
                )

                # delete the stale registrations themselves
                conn.execute(
                    f"DELETE FROM registrations WHERE agent_id IN ({placeholders})",
                    stale_ids,
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


def connect_dossier_db(path: Path) -> sqlite3.Connection:
    """Open an existing dossier database. Raises FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Dossier database not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema_current(conn)
    _maybe_reap_stale_registrations(conn)
    return conn


@contextmanager
def open_dossier_db(path: Path):
    """Context manager for dossier database connections.

    Guarantees connection cleanup even if an exception is raised.
    """
    conn = connect_dossier_db(path)
    try:
        yield conn
    finally:
        conn.close()
