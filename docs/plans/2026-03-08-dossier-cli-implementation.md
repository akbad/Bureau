# Dossier CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI (`operations.dossiers`) that replaces raw sqlite3/frontmatter commands in fold/unfold skills with deterministic, validated operations.

**Architecture:** Single SQLite DB per dossier (WAL mode) with tables for metadata, sessions, tasks, decisions, and file_interactions. CLI accepts structured JSON input, handles all schema creation, validation, and pruning. Skills call CLI commands; agents never touch SQL or frontmatter directly.

**Tech Stack:** Python 3.12+, sqlite3 stdlib, argparse, JSON for structured input. Tests with pytest. Runs via `uv run python -m operations.dossiers`.

**Design doc:** `docs/plans/2026-03-08-dossier-cli-design.md`

---

### Task 1: Core DB module — schema and connection

**Files:**
- Create: `operations/dossiers/__init__.py`
- Create: `operations/dossiers/db.py`
- Test: `operations/dossiers/tests/__init__.py`
- Test: `operations/dossiers/tests/test_db.py`

**Step 1: Write the failing test**

```python
# operations/dossiers/tests/test_db.py
"""Tests for dossier database creation and schema."""
import sqlite3
from pathlib import Path

from operations.dossiers.db import create_dossier_db, connect_dossier_db, SCHEMA_VERSION


class TestCreateDossierDb:
    """Tests for create_dossier_db()."""

    def test_creates_db_file(self, tmp_path: Path):
        """Creates a .db file at the given path."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        assert db_path.exists()

    def test_wal_mode_enabled(self, tmp_path: Path):
        """Database uses WAL journal mode."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_all_tables_created(self, tmp_path: Path):
        """All 5 tables exist after creation."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        expected = {"metadata", "sessions", "tasks", "decisions", "file_interactions"}
        assert expected.issubset(tables)

    def test_schema_version_stored(self, tmp_path: Path):
        """Schema version is stored for future migrations."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
        assert version == SCHEMA_VERSION


class TestConnectDossierDb:
    """Tests for connect_dossier_db()."""

    def test_returns_connection(self, tmp_path: Path):
        """Returns a sqlite3 Connection with row_factory set."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = connect_dossier_db(db_path)
        assert isinstance(conn, sqlite3.Connection)
        # row_factory should be sqlite3.Row for dict-like access
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_raises_on_missing_db(self, tmp_path: Path):
        """Raises FileNotFoundError for non-existent DB."""
        db_path = tmp_path / "nonexistent.db"
        try:
            connect_dossier_db(db_path)
            assert False, "Should have raised"
        except FileNotFoundError:
            pass
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/dossiers/tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'operations.dossiers'`

**Step 3: Write minimal implementation**

```python
# operations/dossiers/__init__.py
"""Bureau dossier CLI — deterministic conversation state management."""

# operations/dossiers/tests/__init__.py
# (empty)

# operations/dossiers/db.py
"""Dossier SQLite database creation and connection."""
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS metadata (
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/dossiers/tests/test_db.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/
git commit -m "feat(dossiers): add core DB module with schema and connection"
```

---

### Task 2: Fold command — create new dossier

**Files:**
- Create: `operations/dossiers/fold.py`
- Test: `operations/dossiers/tests/test_fold.py`

**Step 1: Write the failing test**

```python
# operations/dossiers/tests/test_fold.py
"""Tests for dossier fold (create/update) operations."""
import json
import sqlite3
from pathlib import Path

from operations.dossiers.fold import fold_dossier


class TestFoldNewDossier:
    """Tests for creating a new dossier via fold."""

    def test_creates_db_file(self, tmp_path: Path):
        """Fold creates a .db file in the dossiers directory."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test Dossier",
            agent="claude-code",
            digest="This is a test digest.",
        )
        db_path = tmp_path / f"{result['slug']}.db"
        assert db_path.exists()

    def test_returns_slug_and_hash(self, tmp_path: Path):
        """Fold returns a dict with slug and hash."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test Dossier",
            agent="claude-code",
            digest="Test digest.",
        )
        assert "slug" in result
        assert "hash" in result
        assert len(result["hash"]) == 6
        assert result["slug"].endswith(result["hash"])

    def test_metadata_stored(self, tmp_path: Path):
        """Metadata row is populated with correct values."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="My Project",
            agent="claude-code",
            project="/path/to/repo",
            branch="main",
            commit_hash="abc123",
            digest="Test.",
        )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        conn.row_factory = sqlite3.Row
        meta = conn.execute("SELECT * FROM metadata").fetchone()
        conn.close()
        assert meta["name"] == "My Project"
        assert meta["agent"] == "claude-code"
        assert meta["project"] == "/path/to/repo"
        assert meta["branch"] == "main"
        assert meta["locked_by"] is None

    def test_session_digest_stored(self, tmp_path: Path):
        """Session row contains the digest text."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Full digest content here.",
        )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        conn.row_factory = sqlite3.Row
        session = conn.execute("SELECT * FROM sessions").fetchone()
        conn.close()
        assert session["digest"] == "Full digest content here."
        assert session["agent"] == "claude-code"

    def test_tasks_stored(self, tmp_path: Path):
        """Tasks from JSON are inserted into tasks table."""
        tasks = [
            {"subject": "Task A", "status": "pending"},
            {"subject": "Task B", "status": "completed", "owner": "agent-1"},
        ]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Test.",
            tasks=tasks,
        )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        rows = conn.execute("SELECT subject, status, owner FROM tasks ORDER BY id").fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0][0] == "Task A"
        assert rows[1][2] == "agent-1"

    def test_decisions_stored(self, tmp_path: Path):
        """Decisions from JSON are inserted and linked to session."""
        decisions = [
            {"what": "Use SQLite", "why": "ACID guarantees", "decided_by": "user"},
        ]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Test.",
            decisions=decisions,
        )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM decisions").fetchone()
        conn.close()
        assert row["what"] == "Use SQLite"
        assert row["session_id"] == 1

    def test_file_interactions_stored(self, tmp_path: Path):
        """File interactions are inserted and linked to session."""
        files = [
            {"path": "/src/main.py", "action": "modified", "annotation": "edited line 40"},
        ]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Test.",
            files=files,
        )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM file_interactions").fetchone()
        conn.close()
        assert row["file_path"] == "/src/main.py"
        assert row["action"] == "modified"


class TestFoldExistingDossier:
    """Tests for re-folding (updating) an existing dossier."""

    def test_appends_session(self, tmp_path: Path):
        """Re-fold appends a new session row, doesn't overwrite."""
        result1 = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Session 1 digest.",
        )
        fold_dossier(
            dossiers_dir=tmp_path,
            slug=result1["slug"],
            agent="codex",
            digest="Session 2 digest.",
        )
        conn = sqlite3.connect(tmp_path / f"{result1['slug']}.db")
        sessions = conn.execute("SELECT * FROM sessions ORDER BY id").fetchall()
        conn.close()
        assert len(sessions) == 2

    def test_updates_metadata_timestamp(self, tmp_path: Path):
        """Re-fold updates metadata.updated_at."""
        result1 = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Session 1.",
        )
        conn = sqlite3.connect(tmp_path / f"{result1['slug']}.db")
        conn.row_factory = sqlite3.Row
        ts1 = conn.execute("SELECT updated_at FROM metadata").fetchone()["updated_at"]
        conn.close()

        fold_dossier(
            dossiers_dir=tmp_path,
            slug=result1["slug"],
            agent="codex",
            digest="Session 2.",
        )
        conn = sqlite3.connect(tmp_path / f"{result1['slug']}.db")
        conn.row_factory = sqlite3.Row
        ts2 = conn.execute("SELECT updated_at FROM metadata").fetchone()["updated_at"]
        conn.close()
        assert ts2 >= ts1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/dossiers/tests/test_fold.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'operations.dossiers.fold'`

**Step 3: Write minimal implementation**

```python
# operations/dossiers/fold.py
"""Fold operation: create or update a dossier."""
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import create_dossier_db, connect_dossier_db


def _generate_hash() -> str:
    """Generate a 6-character hex hash."""
    return os.urandom(3).hex()


def _slugify(name: str) -> str:
    """Convert name to lowercase kebab-case slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fold_dossier(
    dossiers_dir: Path,
    agent: str,
    digest: str,
    name: str | None = None,
    slug: str | None = None,
    project: str | None = None,
    branch: str | None = None,
    commit_hash: str | None = None,
    tasks: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    files: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Create a new dossier or append a session to an existing one.

    For new dossiers: provide `name`. A hash and slug are generated.
    For existing dossiers: provide `slug`. A new session is appended.

    Returns dict with 'slug' and 'hash' keys.
    """
    now = _now_iso()

    if slug:
        # Re-fold: append to existing dossier
        db_path = dossiers_dir / f"{slug}.db"
        conn = connect_dossier_db(db_path)
        meta = conn.execute("SELECT hash FROM metadata").fetchone()
        dossier_hash = meta["hash"]

        conn.execute(
            "UPDATE metadata SET updated_at = ?, agent = ?, branch = ?, commit_hash = ?",
            (now, agent, branch, commit_hash),
        )
    else:
        # New fold: create dossier
        if not name:
            raise ValueError("Either 'name' (new dossier) or 'slug' (existing) is required")
        dossier_hash = _generate_hash()
        slug = f"{_slugify(name)}-{dossier_hash}"
        db_path = dossiers_dir / f"{slug}.db"

        create_dossier_db(db_path)
        conn = connect_dossier_db(db_path)

        conn.execute(
            """INSERT INTO metadata
               (hash, name, slug, created_at, updated_at, agent, project, branch, commit_hash, parent, locked_by, locked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)""",
            (dossier_hash, name, slug, now, now, agent, project, branch, commit_hash),
        )

    # Insert session
    cursor = conn.execute(
        "INSERT INTO sessions (folded_at, agent, branch, commit_hash, digest) VALUES (?, ?, ?, ?, ?)",
        (now, agent, branch, commit_hash, digest),
    )
    session_id = cursor.lastrowid

    # Insert tasks
    for task in (tasks or []):
        conn.execute(
            "INSERT INTO tasks (subject, description, status, owner, blocked_by) VALUES (?, ?, ?, ?, ?)",
            (
                task["subject"],
                task.get("description"),
                task.get("status", "pending"),
                task.get("owner"),
                task.get("blocked_by"),
            ),
        )

    # Insert decisions
    for decision in (decisions or []):
        conn.execute(
            "INSERT INTO decisions (session_id, what, why, alternatives, decided_by) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                decision["what"],
                decision["why"],
                decision.get("alternatives"),
                decision.get("decided_by"),
            ),
        )

    # Insert file interactions
    for f in (files or []):
        conn.execute(
            "INSERT INTO file_interactions (session_id, file_path, action, annotation) VALUES (?, ?, ?, ?)",
            (session_id, f["path"], f["action"], f.get("annotation")),
        )

    conn.commit()
    conn.close()

    return {"slug": slug, "hash": dossier_hash}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/dossiers/tests/test_fold.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/fold.py operations/dossiers/tests/test_fold.py
git commit -m "feat(dossiers): add fold operation for creating/updating dossiers"
```

---

### Task 3: Unfold command — render dossier for context injection

**Files:**
- Create: `operations/dossiers/unfold.py`
- Test: `operations/dossiers/tests/test_unfold.py`

**Step 1: Write the failing test**

```python
# operations/dossiers/tests/test_unfold.py
"""Tests for dossier unfold (render for context injection)."""
from pathlib import Path

from operations.dossiers.fold import fold_dossier
from operations.dossiers.unfold import unfold_dossier, list_dossiers, find_dossier


class TestFindDossier:
    """Tests for finding dossiers by hash or name."""

    def test_find_by_hash(self, tmp_path: Path):
        """Finds dossier by its 6-char hash."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="D."
        )
        found = find_dossier(tmp_path, result["hash"])
        assert found is not None
        assert found.name == f"{result['slug']}.db"

    def test_find_by_name_substring(self, tmp_path: Path):
        """Finds dossier by fuzzy name match."""
        fold_dossier(
            dossiers_dir=tmp_path, name="Auth Refactor", agent="claude-code", digest="D."
        )
        found = find_dossier(tmp_path, "auth-refactor")
        assert found is not None

    def test_returns_none_for_unknown(self, tmp_path: Path):
        """Returns None when no match found."""
        found = find_dossier(tmp_path, "nonexistent")
        assert found is None


class TestUnfoldDossier:
    """Tests for rendering dossier content for injection."""

    def test_output_contains_metadata(self, tmp_path: Path):
        """Rendered output includes metadata section."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="My Project",
            agent="claude-code",
            project="/path/to/repo",
            branch="main",
            digest="Full digest here.",
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "My Project" in output
        assert "/path/to/repo" in output
        assert "main" in output

    def test_output_contains_digest(self, tmp_path: Path):
        """Rendered output includes session digest."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="This is the important digest content.",
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "This is the important digest content." in output

    def test_output_contains_tasks(self, tmp_path: Path):
        """Rendered output includes task table."""
        tasks = [{"subject": "Fix the bug", "status": "pending"}]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="D.",
            tasks=tasks,
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Fix the bug" in output
        assert "pending" in output

    def test_output_contains_decisions(self, tmp_path: Path):
        """Rendered output includes decisions."""
        decisions = [{"what": "Use Rust", "why": "Performance", "decided_by": "user"}]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="D.",
            decisions=decisions,
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Use Rust" in output

    def test_multiple_sessions_rendered(self, tmp_path: Path):
        """All session digests are included when multiple folds exist."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="Session 1."
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="codex", digest="Session 2."
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Session 1." in output
        assert "Session 2." in output


class TestListDossiers:
    """Tests for listing all dossiers."""

    def test_lists_all(self, tmp_path: Path):
        """Returns all dossiers sorted by updated_at descending."""
        fold_dossier(dossiers_dir=tmp_path, name="Alpha", agent="a", digest="D.")
        fold_dossier(dossiers_dir=tmp_path, name="Beta", agent="b", digest="D.")
        results = list_dossiers(tmp_path)
        assert len(results) == 2

    def test_empty_directory(self, tmp_path: Path):
        """Returns empty list for empty dossiers directory."""
        results = list_dossiers(tmp_path)
        assert results == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/dossiers/tests/test_unfold.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# operations/dossiers/unfold.py
"""Unfold operation: render dossier for context injection."""
import sqlite3
from pathlib import Path
from typing import Any

from .db import connect_dossier_db


def find_dossier(dossiers_dir: Path, query: str) -> Path | None:
    """Find a dossier DB by hash or name substring.

    Searches .db files in dossiers_dir. Tries exact hash match first,
    then slug substring match.
    """
    if not dossiers_dir.exists():
        return None

    for db_file in dossiers_dir.glob("*.db"):
        slug = db_file.stem
        # Exact hash match (last 6 chars of slug)
        if slug.endswith(query):
            return db_file
        # Substring match on slug
        if query.lower() in slug.lower():
            return db_file

    return None


def list_dossiers(dossiers_dir: Path) -> list[dict[str, Any]]:
    """List all dossiers with metadata, sorted by updated_at descending."""
    if not dossiers_dir.exists():
        return []

    results = []
    for db_file in dossiers_dir.glob("*.db"):
        try:
            conn = connect_dossier_db(db_file)
            meta = conn.execute("SELECT * FROM metadata").fetchone()
            task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            conn.close()
            if meta:
                results.append({
                    "slug": meta["slug"],
                    "hash": meta["hash"],
                    "name": meta["name"],
                    "updated_at": meta["updated_at"],
                    "project": meta["project"],
                    "branch": meta["branch"],
                    "locked_by": meta["locked_by"],
                    "tasks": task_count,
                    "sessions": session_count,
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["updated_at"], reverse=True)
    return results


def unfold_dossier(dossiers_dir: Path, query: str) -> str:
    """Render a dossier as markdown for context injection.

    Finds the dossier by hash or name, reads all state, and returns
    a markdown string ready for injection into an agent's context.
    """
    db_path = find_dossier(dossiers_dir, query)
    if not db_path:
        raise FileNotFoundError(f"No dossier found matching: {query}")

    conn = connect_dossier_db(db_path)

    meta = conn.execute("SELECT * FROM metadata").fetchone()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY id").fetchall()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE status != 'deleted' ORDER BY id"
    ).fetchall()
    decisions = conn.execute("SELECT * FROM decisions ORDER BY id").fetchall()

    conn.close()

    # Render markdown
    lines = []

    # Header
    lines.append(f"# Dossier: {meta['name']}")
    lines.append("")
    lines.append(f"**Hash:** `{meta['hash']}` | **Branch:** `{meta['branch']}` | "
                 f"**Commit:** `{meta['commit_hash']}` | **Project:** `{meta['project']}`")
    lines.append(f"**Updated:** {meta['updated_at']} | **Locked by:** {meta['locked_by'] or 'none'}")
    lines.append("")

    # Tasks
    if tasks:
        lines.append("## Tasks")
        lines.append("")
        lines.append("| ID | Subject | Status | Owner | Blocked by |")
        lines.append("|----|---------|--------|-------|------------|")
        for t in tasks:
            lines.append(
                f"| {t['id']} | {t['subject']} | {t['status']} | "
                f"{t['owner'] or '—'} | {t['blocked_by'] or '—'} |"
            )
        lines.append("")

    # Decisions
    if decisions:
        lines.append("## Decisions")
        lines.append("")
        for d in decisions:
            lines.append(f"- **{d['what']}**: {d['why']} *(decided by: {d['decided_by']})*")
        lines.append("")

    # Session digests
    lines.append("## Session digests")
    lines.append("")
    for s in sessions:
        lines.append(f"### Session {s['id']} ({s['folded_at']}, {s['agent']})")
        lines.append("")
        lines.append(s["digest"])
        lines.append("")

    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/dossiers/tests/test_unfold.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/unfold.py operations/dossiers/tests/test_unfold.py
git commit -m "feat(dossiers): add unfold operation for context injection rendering"
```

---

### Task 4: Tasks command — CRUD operations

**Files:**
- Create: `operations/dossiers/tasks.py`
- Test: `operations/dossiers/tests/test_tasks.py`

**Step 1: Write the failing test**

```python
# operations/dossiers/tests/test_tasks.py
"""Tests for dossier task CRUD operations."""
from pathlib import Path

from operations.dossiers.fold import fold_dossier
from operations.dossiers.tasks import list_tasks, add_task, update_task, remove_task


class TestListTasks:
    def test_lists_all_non_deleted(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}, {"subject": "B", "status": "completed"}],
        )
        tasks = list_tasks(tmp_path, result["slug"])
        assert len(tasks) == 2

    def test_empty_when_no_tasks(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks == []


class TestAddTask:
    def test_adds_task(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        task_id = add_task(tmp_path, result["slug"], subject="New task")
        assert task_id == 1
        tasks = list_tasks(tmp_path, result["slug"])
        assert len(tasks) == 1
        assert tasks[0]["subject"] == "New task"

    def test_adds_with_all_fields(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        task_id = add_task(
            tmp_path, result["slug"],
            subject="Complex task",
            description="Details here",
            status="in_progress",
            owner="agent-1",
            blocked_by="1",
        )
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["owner"] == "agent-1"
        assert tasks[0]["blocked_by"] == "1"


class TestUpdateTask:
    def test_updates_status(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        update_task(tmp_path, result["slug"], task_id=1, status="completed")
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["status"] == "completed"

    def test_updates_owner(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        update_task(tmp_path, result["slug"], task_id=1, owner="codex")
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["owner"] == "codex"

    def test_raises_on_missing_task(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        try:
            update_task(tmp_path, result["slug"], task_id=999, status="completed")
            assert False, "Should have raised"
        except ValueError:
            pass


class TestRemoveTask:
    def test_marks_as_deleted(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        remove_task(tmp_path, result["slug"], task_id=1)
        tasks = list_tasks(tmp_path, result["slug"])
        assert len(tasks) == 0  # deleted tasks excluded from list
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/dossiers/tests/test_tasks.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# operations/dossiers/tasks.py
"""Task CRUD operations for dossier task lists."""
from pathlib import Path
from typing import Any

from .db import connect_dossier_db


def _db_path(dossiers_dir: Path, slug: str) -> Path:
    return dossiers_dir / f"{slug}.db"


def list_tasks(dossiers_dir: Path, slug: str) -> list[dict[str, Any]]:
    """List all non-deleted tasks for a dossier."""
    conn = connect_dossier_db(_db_path(dossiers_dir, slug))
    rows = conn.execute(
        "SELECT id, subject, description, status, owner, blocked_by, created_at, updated_at "
        "FROM tasks WHERE status != 'deleted' ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_task(
    dossiers_dir: Path,
    slug: str,
    subject: str,
    description: str | None = None,
    status: str = "pending",
    owner: str | None = None,
    blocked_by: str | None = None,
) -> int:
    """Add a new task. Returns the task ID."""
    conn = connect_dossier_db(_db_path(dossiers_dir, slug))
    cursor = conn.execute(
        "INSERT INTO tasks (subject, description, status, owner, blocked_by) VALUES (?, ?, ?, ?, ?)",
        (subject, description, status, owner, blocked_by),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task(
    dossiers_dir: Path,
    slug: str,
    task_id: int,
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    blocked_by: str | None = None,
) -> None:
    """Update fields on an existing task. Raises ValueError if not found."""
    conn = connect_dossier_db(_db_path(dossiers_dir, slug))

    existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not existing:
        conn.close()
        raise ValueError(f"Task {task_id} not found in dossier {slug}")

    updates = []
    values = []
    for field, value in [
        ("subject", subject), ("description", description),
        ("status", status), ("owner", owner), ("blocked_by", blocked_by),
    ]:
        if value is not None:
            updates.append(f"{field} = ?")
            values.append(value)

    if updates:
        updates.append("updated_at = datetime('now')")
        values.append(task_id)
        conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()

    conn.close()


def remove_task(dossiers_dir: Path, slug: str, task_id: int) -> None:
    """Soft-delete a task by setting status to 'deleted'."""
    update_task(dossiers_dir, slug, task_id, status="deleted")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/dossiers/tests/test_tasks.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/tasks.py operations/dossiers/tests/test_tasks.py
git commit -m "feat(dossiers): add task CRUD operations"
```

---

### Task 5: Lock and fork operations

**Files:**
- Create: `operations/dossiers/lock.py`
- Create: `operations/dossiers/fork.py`
- Test: `operations/dossiers/tests/test_lock.py`
- Test: `operations/dossiers/tests/test_fork.py`

**Step 1: Write the failing test**

```python
# operations/dossiers/tests/test_lock.py
"""Tests for advisory lock operations."""
import sqlite3
from pathlib import Path

from operations.dossiers.fold import fold_dossier
from operations.dossiers.lock import claim_lock, release_lock, get_lock_status


class TestClaimLock:
    def test_claims_unlocked_dossier(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] == "claude-code"
        assert status["locked_at"] is not None

    def test_returns_holder_when_already_locked(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        try:
            claim_lock(tmp_path, result["slug"], agent="codex")
            assert False, "Should have raised"
        except ValueError as e:
            assert "claude-code" in str(e)


class TestReleaseLock:
    def test_releases_lock(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        release_lock(tmp_path, result["slug"])
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] is None
```

```python
# operations/dossiers/tests/test_fork.py
"""Tests for dossier fork operation."""
import sqlite3
from pathlib import Path

from operations.dossiers.fold import fold_dossier
from operations.dossiers.fork import fork_dossier


class TestForkDossier:
    def test_creates_new_db(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Original", agent="a", digest="D.",
            tasks=[{"subject": "Task 1", "status": "pending"}],
        )
        fork_result = fork_dossier(tmp_path, result["slug"], name="My Fork")
        assert fork_result["slug"] != result["slug"]
        assert (tmp_path / f"{fork_result['slug']}.db").exists()

    def test_fork_copies_tasks(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Original", agent="a", digest="D.",
            tasks=[{"subject": "Task 1", "status": "pending"}],
        )
        fork_result = fork_dossier(tmp_path, result["slug"])
        conn = sqlite3.connect(tmp_path / f"{fork_result['slug']}.db")
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()
        assert len(tasks) == 1

    def test_fork_copies_sessions(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Original", agent="a", digest="Session 1."
        )
        fork_result = fork_dossier(tmp_path, result["slug"])
        conn = sqlite3.connect(tmp_path / f"{fork_result['slug']}.db")
        sessions = conn.execute("SELECT * FROM sessions").fetchall()
        conn.close()
        assert len(sessions) == 1

    def test_fork_sets_parent(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Original", agent="a", digest="D."
        )
        fork_result = fork_dossier(tmp_path, result["slug"])
        conn = sqlite3.connect(tmp_path / f"{fork_result['slug']}.db")
        conn.row_factory = sqlite3.Row
        meta = conn.execute("SELECT parent FROM metadata").fetchone()
        conn.close()
        assert meta["parent"] == result["hash"]

    def test_fork_is_unlocked(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Original", agent="a", digest="D."
        )
        fork_result = fork_dossier(tmp_path, result["slug"])
        conn = sqlite3.connect(tmp_path / f"{fork_result['slug']}.db")
        conn.row_factory = sqlite3.Row
        meta = conn.execute("SELECT locked_by FROM metadata").fetchone()
        conn.close()
        assert meta["locked_by"] is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/dossiers/tests/test_lock.py operations/dossiers/tests/test_fork.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# operations/dossiers/lock.py
"""Advisory lock operations for dossiers."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import connect_dossier_db


def get_lock_status(dossiers_dir: Path, slug: str) -> dict[str, Any]:
    """Get current lock status."""
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    meta = conn.execute("SELECT locked_by, locked_at FROM metadata").fetchone()
    conn.close()
    return {"locked_by": meta["locked_by"], "locked_at": meta["locked_at"]}


def claim_lock(dossiers_dir: Path, slug: str, agent: str) -> None:
    """Claim advisory lock. Raises ValueError if already locked by another agent."""
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    meta = conn.execute("SELECT locked_by FROM metadata").fetchone()

    if meta["locked_by"] and meta["locked_by"] != agent:
        holder = meta["locked_by"]
        conn.close()
        raise ValueError(f"Dossier already locked by {holder}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE metadata SET locked_by = ?, locked_at = ?", (agent, now))
    conn.commit()
    conn.close()


def release_lock(dossiers_dir: Path, slug: str) -> None:
    """Release advisory lock."""
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    conn.execute("UPDATE metadata SET locked_by = NULL, locked_at = NULL")
    conn.commit()
    conn.close()
```

```python
# operations/dossiers/fork.py
"""Fork operation: create independent copy of a dossier."""
import shutil
from pathlib import Path
from typing import Any

from .db import connect_dossier_db
from .fold import _generate_hash, _slugify, _now_iso


def fork_dossier(
    dossiers_dir: Path,
    slug: str,
    name: str | None = None,
) -> dict[str, str]:
    """Create an independent copy of a dossier. Always unlocked."""
    source_path = dossiers_dir / f"{slug}.db"
    if not source_path.exists():
        raise FileNotFoundError(f"Dossier not found: {slug}")

    # Read original metadata for defaults
    conn = connect_dossier_db(source_path)
    meta = conn.execute("SELECT * FROM metadata").fetchone()
    conn.close()

    new_hash = _generate_hash()
    fork_name = name or f"{meta['name']} (fork)"
    new_slug = f"{_slugify(fork_name)}-{new_hash}"
    dest_path = dossiers_dir / f"{new_slug}.db"

    # Copy the entire DB
    shutil.copy2(source_path, dest_path)

    # Update metadata in the fork
    now = _now_iso()
    conn = connect_dossier_db(dest_path)
    conn.execute(
        """UPDATE metadata SET
           hash = ?, name = ?, slug = ?, updated_at = ?,
           parent = ?, locked_by = NULL, locked_at = NULL""",
        (new_hash, fork_name, new_slug, now, meta["hash"]),
    )
    conn.commit()
    conn.close()

    return {"slug": new_slug, "hash": new_hash}
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/dossiers/tests/test_lock.py operations/dossiers/tests/test_fork.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/lock.py operations/dossiers/fork.py \
      operations/dossiers/tests/test_lock.py operations/dossiers/tests/test_fork.py
git commit -m "feat(dossiers): add lock and fork operations"
```

---

### Task 6: CLI entry point and __main__

**Files:**
- Create: `operations/dossiers/cli.py`
- Create: `operations/dossiers/__main__.py`
- Test: `operations/dossiers/tests/test_cli.py`

**Step 1: Write the failing test**

```python
# operations/dossiers/tests/test_cli.py
"""Tests for CLI entry point (integration tests)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def dossiers_dir(tmp_path: Path) -> Path:
    d = tmp_path / "dossiers"
    d.mkdir()
    return d


class TestCliFold:
    def test_fold_creates_dossier(self, dossiers_dir: Path, tmp_path: Path):
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("Test digest content.")
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--name", "CLI Test",
                "--agent", "claude-code",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Dossier saved:" in result.stdout
        # Should have created a .db file
        db_files = list(dossiers_dir.glob("*.db"))
        assert len(db_files) == 1


class TestCliUnfold:
    def test_unfold_renders_context(self, dossiers_dir: Path, tmp_path: Path):
        # First, fold something
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("Important context here.")
        fold_result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--name", "CLI Test",
                "--agent", "claude-code",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        # Extract hash from output
        # Output format: "Dossier saved: <slug> (..."
        slug = fold_result.stdout.split("`")[1]  # between backticks

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Important context here." in result.stdout


class TestCliList:
    def test_list_empty(self, dossiers_dir: Path):
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "list",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_list_json_format(self, dossiers_dir: Path, tmp_path: Path):
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("D.")
        subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold", "--name", "Test", "--agent", "a",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "list", "--format", "json",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/dossiers/tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# operations/dossiers/__main__.py
"""Expose CLI entrypoint for dossiers subpackage."""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())

# operations/dossiers/cli.py
"""CLI entry point for dossier operations."""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .fold import fold_dossier
from .unfold import unfold_dossier, list_dossiers, find_dossier
from .tasks import list_tasks, add_task, update_task, remove_task
from .lock import claim_lock, release_lock, get_lock_status
from .fork import fork_dossier


DEFAULT_DOSSIERS_DIR = Path(os.path.expanduser("~/.config/bureau/dossiers"))


def _get_dossiers_dir(args: argparse.Namespace) -> Path:
    return Path(args.dossiers_dir) if args.dossiers_dir else DEFAULT_DOSSIERS_DIR


def cmd_fold(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    dossiers_dir.mkdir(parents=True, exist_ok=True)

    # Read digest from file or stdin
    if args.digest_file:
        digest = Path(args.digest_file).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        digest = sys.stdin.read()
    else:
        print("Error: --digest-file required (or pipe digest via stdin)", file=sys.stderr)
        return 1

    tasks = json.loads(args.tasks_json) if args.tasks_json else None
    decisions = json.loads(args.decisions_json) if args.decisions_json else None
    files = json.loads(args.files_json) if args.files_json else None

    result = fold_dossier(
        dossiers_dir=dossiers_dir,
        name=args.name,
        slug=args.slug,
        agent=args.agent,
        project=args.project,
        branch=args.branch,
        commit_hash=args.commit,
        digest=digest,
        tasks=tasks,
        decisions=decisions,
        files=files,
    )
    task_count = len(tasks) if tasks else 0
    decision_count = len(decisions) if decisions else 0
    print(f"Dossier saved: `{result['slug']}` ({task_count} tasks, {decision_count} decisions)")
    return 0


def cmd_unfold(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        output = unfold_dossier(dossiers_dir, args.query)
        print(output)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    results = list_dossiers(dossiers_dir)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No dossiers found.")
            return 0
        print(f"{'Hash':<8} {'Name':<30} {'Branch':<20} {'Tasks':>5} {'Updated'}")
        print("-" * 80)
        for r in results:
            print(f"{r['hash']:<8} {r['name']:<30} {(r['branch'] or '—'):<20} {r['tasks']:>5} {r['updated_at']}")

    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    subcmd = args.tasks_command

    if subcmd == "list":
        tasks = list_tasks(dossiers_dir, args.slug)
        if not tasks:
            print("No tasks.")
            return 0
        print(f"{'ID':>4} {'Subject':<40} {'Status':<12} {'Owner':<15}")
        print("-" * 75)
        for t in tasks:
            print(f"{t['id']:>4} {t['subject']:<40} {t['status']:<12} {(t['owner'] or '—'):<15}")

    elif subcmd == "add":
        task_id = add_task(
            dossiers_dir, args.slug,
            subject=args.subject,
            description=args.description,
            status=args.status or "pending",
            owner=args.owner,
            blocked_by=args.blocked_by,
        )
        print(f"Task #{task_id} created.")

    elif subcmd == "update":
        update_task(
            dossiers_dir, args.slug, task_id=args.id,
            subject=args.subject, status=args.status,
            owner=args.owner, blocked_by=args.blocked_by,
        )
        print(f"Task #{args.id} updated.")

    elif subcmd == "remove":
        remove_task(dossiers_dir, args.slug, task_id=args.id)
        print(f"Task #{args.id} removed.")

    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    subcmd = args.lock_command

    if subcmd == "claim":
        try:
            claim_lock(dossiers_dir, args.slug, agent=args.agent)
            print(f"Lock claimed by {args.agent}.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif subcmd == "release":
        release_lock(dossiers_dir, args.slug)
        print("Lock released.")

    elif subcmd == "status":
        status = get_lock_status(dossiers_dir, args.slug)
        if status["locked_by"]:
            print(f"Locked by {status['locked_by']} since {status['locked_at']}")
        else:
            print("Unlocked.")

    return 0


def cmd_fork(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        result = fork_dossier(dossiers_dir, args.slug, name=args.name)
        print(f"Forked: `{result['slug']}`")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_show(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        output = unfold_dossier(dossiers_dir, args.query)
        print(output)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="dossiers", description="Bureau dossier CLI")
    parser.add_argument("--dossiers-dir", help="Override dossiers directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fold
    p_fold = subparsers.add_parser("fold", help="Create or update a dossier")
    p_fold.add_argument("--name", help="Dossier name (for new dossiers)")
    p_fold.add_argument("--slug", help="Existing dossier slug (for re-fold)")
    p_fold.add_argument("--agent", required=True, help="Agent identifier")
    p_fold.add_argument("--project", help="Git repo root path")
    p_fold.add_argument("--branch", help="Current git branch")
    p_fold.add_argument("--commit", help="Short HEAD hash")
    p_fold.add_argument("--digest-file", help="Path to digest markdown file")
    p_fold.add_argument("--tasks-json", help="JSON array of tasks")
    p_fold.add_argument("--decisions-json", help="JSON array of decisions")
    p_fold.add_argument("--files-json", help="JSON array of file interactions")

    # unfold
    p_unfold = subparsers.add_parser("unfold", help="Render dossier for context injection")
    p_unfold.add_argument("query", help="Dossier hash or name to find")

    # list
    p_list = subparsers.add_parser("list", help="List all dossiers")
    p_list.add_argument("--format", choices=["table", "json"], default="table")

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="Task operations")
    p_tasks.add_argument("slug", help="Dossier slug")
    tasks_sub = p_tasks.add_subparsers(dest="tasks_command", required=True)

    tasks_sub.add_parser("list", help="List tasks")

    p_task_add = tasks_sub.add_parser("add", help="Add a task")
    p_task_add.add_argument("--subject", required=True)
    p_task_add.add_argument("--description")
    p_task_add.add_argument("--status", default="pending")
    p_task_add.add_argument("--owner")
    p_task_add.add_argument("--blocked-by", dest="blocked_by")

    p_task_update = tasks_sub.add_parser("update", help="Update a task")
    p_task_update.add_argument("--id", type=int, required=True)
    p_task_update.add_argument("--subject")
    p_task_update.add_argument("--status")
    p_task_update.add_argument("--owner")
    p_task_update.add_argument("--blocked-by", dest="blocked_by")

    p_task_remove = tasks_sub.add_parser("remove", help="Remove a task")
    p_task_remove.add_argument("--id", type=int, required=True)

    # lock
    p_lock = subparsers.add_parser("lock", help="Advisory lock operations")
    p_lock.add_argument("slug", help="Dossier slug")
    lock_sub = p_lock.add_subparsers(dest="lock_command", required=True)

    p_lock_claim = lock_sub.add_parser("claim", help="Claim lock")
    p_lock_claim.add_argument("--agent", required=True)

    lock_sub.add_parser("release", help="Release lock")
    lock_sub.add_parser("status", help="Check lock status")

    # fork
    p_fork = subparsers.add_parser("fork", help="Fork a dossier")
    p_fork.add_argument("slug", help="Source dossier slug")
    p_fork.add_argument("--name", help="Name for the fork")

    # show
    p_show = subparsers.add_parser("show", help="Render human-readable view")
    p_show.add_argument("query", help="Dossier hash or name")

    args = parser.parse_args()

    commands = {
        "fold": cmd_fold,
        "unfold": cmd_unfold,
        "list": cmd_list,
        "tasks": cmd_tasks,
        "lock": cmd_lock,
        "fork": cmd_fork,
        "show": cmd_show,
    }

    return commands[args.command](args)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/dossiers/tests/test_cli.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/cli.py operations/dossiers/__main__.py \
      operations/dossiers/tests/test_cli.py
git commit -m "feat(dossiers): add CLI entry point with all subcommands"
```

---

### Task 7: Auto-prune file interactions during fold

**Files:**
- Modify: `operations/dossiers/fold.py`
- Test: `operations/dossiers/tests/test_fold.py` (add pruning tests)

**Step 1: Write the failing test**

Add to `operations/dossiers/tests/test_fold.py`:

```python
class TestFoldPruning:
    """Tests for auto-pruning file_interactions during fold."""

    def test_prunes_old_file_interactions(self, tmp_path: Path):
        """File interactions beyond max_retained_sessions are deleted."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
            files=[{"path": "/a.py", "action": "read"}],
        )
        for i in range(6):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"S{i+2}.",
                files=[{"path": f"/{i}.py", "action": "read"}],
                max_retained_sessions=5,
            )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        fi_count = conn.execute("SELECT COUNT(*) FROM file_interactions").fetchone()[0]
        session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
        # 7 sessions total, but only last 5 sessions' file_interactions kept
        assert session_count == 7
        assert fi_count == 5  # pruned first 2

    def test_no_prune_when_under_threshold(self, tmp_path: Path):
        """No pruning when sessions <= max_retained_sessions."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
            files=[{"path": "/a.py", "action": "read"}],
            max_retained_sessions=5,
        )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        fi_count = conn.execute("SELECT COUNT(*) FROM file_interactions").fetchone()[0]
        conn.close()
        assert fi_count == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/dossiers/tests/test_fold.py::TestFoldPruning -v`
Expected: FAIL (fold_dossier doesn't accept `max_retained_sessions`)

**Step 3: Add pruning to fold_dossier**

Add `max_retained_sessions: int = 5` parameter to `fold_dossier()`. After
inserting the new session and file interactions, run:

```python
# Prune old file_interactions
if max_retained_sessions > 0:
    cutoff_session = conn.execute(
        "SELECT id FROM sessions ORDER BY id DESC LIMIT 1 OFFSET ?",
        (max_retained_sessions,),
    ).fetchone()
    if cutoff_session:
        conn.execute(
            "DELETE FROM file_interactions WHERE session_id <= ?",
            (cutoff_session["id"],),
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/dossiers/tests/test_fold.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/dossiers/fold.py operations/dossiers/tests/test_fold.py
git commit -m "feat(dossiers): add auto-pruning of old file interactions during fold"
```

---

### Task 8: Update cleanup handler for new .db format

**Files:**
- Modify: `operations/cleanup/handlers/dossiers.py`
- Create: `operations/cleanup/tests/test_handlers/test_dossiers.py`

**Step 1: Write the failing test**

```python
# operations/cleanup/tests/test_handlers/test_dossiers.py
"""Tests for DossiersHandler (new .db format)."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from operations.cleanup.handlers.dossiers import DossiersHandler
from operations.dossiers.db import create_dossier_db, connect_dossier_db


@pytest.fixture
def dossiers_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "dossiers"
    d.mkdir()
    monkeypatch.setattr(
        "operations.cleanup.handlers.dossiers.DOSSIERS_DIR", d
    )
    return d


def _create_dossier(dossiers_dir: Path, slug: str, updated_at: str) -> Path:
    """Helper to create a test dossier DB with given updated_at."""
    db_path = dossiers_dir / f"{slug}.db"
    create_dossier_db(db_path)
    conn = connect_dossier_db(db_path)
    conn.execute(
        "INSERT INTO metadata (hash, name, slug, created_at, updated_at, agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("abc123", slug, slug, updated_at, updated_at, "test"),
    )
    conn.commit()
    conn.close()
    return db_path


class TestDossiersHandlerGetStaleItems:
    def test_finds_stale_dossiers(
        self, dossiers_dir: Path, cutoff_datetime: datetime
    ):
        _create_dossier(dossiers_dir, "old-dossier", "2024-01-01T00:00:00Z")
        _create_dossier(dossiers_dir, "new-dossier", "2024-02-01T00:00:00Z")
        handler = DossiersHandler()
        stale = handler.get_stale_items(cutoff_datetime)
        assert len(stale) == 1
        assert "old-dossier" in str(stale[0]["path"])

    def test_no_stale_when_all_fresh(
        self, dossiers_dir: Path, cutoff_datetime: datetime
    ):
        _create_dossier(dossiers_dir, "fresh", "2024-02-01T00:00:00Z")
        handler = DossiersHandler()
        stale = handler.get_stale_items(cutoff_datetime)
        assert len(stale) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest operations/cleanup/tests/test_handlers/test_dossiers.py -v`
Expected: FAIL (handler still looks for .md files with YAML frontmatter)

**Step 3: Update DossiersHandler to use .db format**

Rewrite `dossiers.py` to:
- Scan for `*.db` files instead of `*.md`
- Read `updated_at` from the SQLite `metadata` table instead of YAML frontmatter
- Companion files are `*.db-wal` and `*.db-shm` (no `.md` to clean up unless it exists)
- Optionally also clean up any `.md` projection file with the same stem

**Step 4: Run test to verify it passes**

Run: `uv run pytest operations/cleanup/tests/test_handlers/test_dossiers.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add operations/cleanup/handlers/dossiers.py \
      operations/cleanup/tests/test_handlers/test_dossiers.py
git commit -m "refactor(dossiers): update cleanup handler for .db format"
```

---

### Task 9: Update fold/unfold skills to use CLI

**Files:**
- Modify: `protocols/context/static/skills/fold/SKILL.md`
- Modify: `protocols/context/static/skills/unfold/SKILL.md`

**Step 1: Review current skills**

Read both SKILL.md files. Identify all places where agents are told to run
raw `sqlite3` commands or write YAML frontmatter.

**Step 2: Replace with CLI commands**

In fold SKILL.md:
- Replace hash generation (`openssl rand -hex 3`) with the CLI handling it
- Replace the "Write the dossier markdown file" section with a CLI fold command
- Replace the "Create the SQLite task database" section with the CLI handling it
- Replace the "Populate tasks" section with `--tasks-json`
- Keep the collection protocol (Steps 1-5) — agents still gather the data
- The agent writes the digest to a temp file, passes everything else as JSON flags

In unfold SKILL.md:
- Replace manual `sqlite3` queries with CLI commands
- Replace `cat` of the .md file with `dossier unfold <hash>`
- Replace task UPDATE/INSERT with `dossier tasks <slug> update/add`
- Keep the resume protocol flow — agents still interpret and inject the context

**Step 3: Verify skills are syntactically correct**

Read through both updated files to confirm they reference valid CLI commands.

**Step 4: Commit**

```bash
git add protocols/context/static/skills/fold/SKILL.md \
      protocols/context/static/skills/unfold/SKILL.md
git commit -m "refactor(dossiers): update fold/unfold skills to use CLI instead of raw sqlite3"
```

---

### Task 10: Update protocol docs (tools-guide, CLAUDE.template)

**Files:**
- Modify: `protocols/context/static/tools-guide.md`
- Modify: `protocols/context/templates/CLAUDE.template.md`

**Step 1: Add dossier section to tools-guide.md**

Add between "Memory" and "Code analysis" sections:

```markdown
## Dossier (work-stream state)

- For **saving conversation state**: `uv run python -m operations.dossiers fold`
- For **resuming a work-stream**: `uv run python -m operations.dossiers unfold <hash>`
- For **task coordination**: `uv run python -m operations.dossiers tasks <slug> <subcommand>`

> [!NOTE]
> Dossiers track **active work-stream state** (tasks, decisions, context).
> Memory tools (Qdrant/Memory MCP) track **distilled knowledge**.
> Store insights in BOTH when appropriate.
```

**Step 2: Remove claude-mem from tools-guide.md**

Remove all references to claude-mem from the Memory section and storage
protocol. Update the storage decision tree to only mention Qdrant and
Memory MCP.

**Step 3: Add handoff guidance to CLAUDE.template.md**

Add to Context Management Protocol:

```markdown
**For conversation handoff**: Use `/bureau-fold` to save work-stream state
to a dossier, then resume in a fresh agent with `/bureau-unfold`.
Preserves full fidelity — superior to context compaction.
```

**Step 4: Commit**

```bash
git add protocols/context/static/tools-guide.md \
      protocols/context/templates/CLAUDE.template.md
git commit -m "docs(dossiers): update protocol docs and remove claude-mem references"
```

---

### Task 11: Run full test suite and verify

**Step 1: Run all dossier tests**

```bash
uv run pytest operations/dossiers/tests/ -v
```

Expected: All tests PASS

**Step 2: Run cleanup handler tests**

```bash
uv run pytest operations/cleanup/tests/test_handlers/test_dossiers.py -v
```

Expected: All tests PASS

**Step 3: Smoke test the CLI end-to-end**

```bash
# Create a dossier
echo "Test digest." > /tmp/test-digest.md
uv run python -m operations.dossiers fold \
  --name "Smoke Test" --agent "claude-code" \
  --digest-file /tmp/test-digest.md

# List dossiers
uv run python -m operations.dossiers list

# Unfold it
uv run python -m operations.dossiers unfold smoke-test

# Add a task
SLUG=$(uv run python -m operations.dossiers list --format json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['slug'])")
uv run python -m operations.dossiers tasks "$SLUG" add --subject "Test task"

# List tasks
uv run python -m operations.dossiers tasks "$SLUG" list

# Clean up
rm /tmp/test-digest.md
```

Expected: All commands succeed with expected output.

**Step 4: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(dossiers): address issues found during smoke testing"
```
