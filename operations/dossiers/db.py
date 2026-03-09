"""Dossier SQLite database creation and connection."""
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

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
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA_SQL)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    conn.close()


def connect_dossier_db(path: Path) -> sqlite3.Connection:
    """Open an existing dossier database. Raises FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Dossier database not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
