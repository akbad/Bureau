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
