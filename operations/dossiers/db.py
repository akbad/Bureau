"""Dossier SQLite database creation and connection."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 2

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


def safe_db_path(dossiers_dir: Path, slug: str) -> Path:
    """Resolve a slug to a DB path, ensuring it stays within the dossiers directory.

    Prevents path traversal attacks via crafted slugs like '../../etc/foo'.
    """
    path = (dossiers_dir / f"{slug}.db").resolve()
    if not str(path).startswith(str(dossiers_dir.resolve())):
        raise ValueError(f"Invalid slug: path escapes dossier directory")
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
    locked_at   TEXT
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


def create_dossier_db(path: Path) -> None:
    """Create a new dossier database with the full schema."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA_SQL)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    conn.close()
    path.chmod(0o600)  # owner read/write only


def _ensure_schema_current(conn: sqlite3.Connection) -> None:
    """Apply incremental schema migrations for older dossiers.

    Safe under concurrent access: if two agents open the same dossier
    simultaneously after an upgrade, the second ALTER TABLE will fail
    with OperationalError (duplicate column).  We catch and ignore that
    specific error since it means the migration already succeeded.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "context_notes" not in columns:
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN context_notes TEXT")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                pass  # another agent already applied this migration
            else:
                raise


def connect_dossier_db(path: Path) -> sqlite3.Connection:
    """Open an existing dossier database. Raises FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Dossier database not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema_current(conn)
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
