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
