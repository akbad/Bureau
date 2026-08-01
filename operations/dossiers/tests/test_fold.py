"""Tests for dossier fold (create/update) operations."""
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

import operations.dossiers.fold as fold_module
from operations.dossiers.db import (
    MAX_CONTEXT_NOTES_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_DIGEST_LENGTH,
    MAX_SUBJECT_LENGTH,
    MAX_TASKS_PER_DOSSIER,
    connect_dossier_db,
)
from operations.dossiers.fold import fold_dossier


def _over_limit(limit: int, ch: str = "x") -> str:
    """Return a string one character longer than the provided limit."""
    return ch * (limit + 1)


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

    def test_default_fold_never_prunes_file_interactions(self, tmp_path: Path):
        """A fold that does not opt into pruning must preserve every file row.

        Regression guard for F2: appending a session used to destroy the
        evicted sessions' file annotations as a side effect, with no flag to
        stop it and no mention in the success line.
        """
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
            files=[{"path": "/a.py", "action": "read"}],
        )
        for i in range(6):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"S{i + 2}.",
                files=[{"path": f"/{i}.py", "action": "read"}],
            )
        conn = sqlite3.connect(tmp_path / f"{result['slug']}.db")
        fi_count = conn.execute("SELECT COUNT(*) FROM file_interactions").fetchone()[0]
        session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
        assert session_count == 7
        assert fi_count == 7, "default fold must not delete file interactions"

    def test_prune_reports_deleted_row_count(self, tmp_path: Path):
        """Opting into pruning reports how many rows it destroyed."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
            files=[{"path": "/a.py", "action": "read"}],
        )
        for i in range(5):
            last = fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"S{i + 2}.",
                files=[{"path": f"/{i}.py", "action": "read"}],
                max_retained_sessions=5,
            )
        # 6 sessions, window of 5 -> session 1's single row is destroyed
        assert last["pruned_file_rows"] == 1

    def test_default_fold_reports_zero_pruned_rows(self, tmp_path: Path):
        """A non-pruning fold reports zero, not a missing key."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
            files=[{"path": "/a.py", "action": "read"}],
        )
        assert result["pruned_file_rows"] == 0


class TestRefoldTaskDuplication:
    """Tests for re-fold task duplication fix."""

    def test_refold_does_not_duplicate_tasks(self, tmp_path: Path):
        """Re-folding with tasks in input should NOT create duplicate tasks."""
        tasks = [{"subject": "A"}, {"subject": "B"}, {"subject": "C"}]
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            tasks=tasks,
        )
        # Re-fold with same tasks in input
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            tasks=tasks,
        )
        # Verify: should still have 3 tasks, not 6
        conn = connect_dossier_db(tmp_path / f"{result['slug']}.db")
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        conn.close()
        assert count == 3

    def test_refold_still_inserts_decisions(self, tmp_path: Path):
        """Re-folding should still insert new decisions."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            decisions=[{"what": "Decision A", "why": "Reason A", "decided_by": "user"}],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            decisions=[{"what": "Decision B", "why": "Reason B", "decided_by": "user"}],
        )
        conn = connect_dossier_db(tmp_path / f"{result['slug']}.db")
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        assert count == 2  # Both decisions should exist


class TestFoldInputValidation:
    """Tests for fold-path validation limits and status enforcement."""

    def test_rejects_digest_over_max_length(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Digest exceeds maximum length"):
            fold_dossier(
                dossiers_dir=tmp_path,
                name="Test",
                agent="claude-code",
                digest=_over_limit(MAX_DIGEST_LENGTH),
            )

    def test_rejects_task_list_over_max_count(self, tmp_path: Path):
        tasks = [{"subject": f"Task {i}", "status": "pending"} for i in range(MAX_TASKS_PER_DOSSIER + 1)]

        with pytest.raises(ValueError, match="Task list exceeds maximum count"):
            fold_dossier(
                dossiers_dir=tmp_path,
                name="Test",
                agent="claude-code",
                digest="Test.",
                tasks=tasks,
            )

    @pytest.mark.parametrize(
        ("task", "error_match"),
        [
            (
                {"subject": _over_limit(MAX_SUBJECT_LENGTH), "status": "pending"},
                "Subject exceeds maximum length",
            ),
            (
                {
                    "subject": "Task",
                    "description": _over_limit(MAX_DESCRIPTION_LENGTH),
                    "status": "pending",
                },
                "Description exceeds maximum length",
            ),
            (
                {
                    "subject": "Task",
                    "context_notes": _over_limit(MAX_CONTEXT_NOTES_LENGTH),
                    "status": "pending",
                },
                "Context notes exceeds maximum length",
            ),
            (
                {"subject": "Task", "status": "invalid"},
                "Invalid status",
            ),
        ],
        ids=[
            "subject-too-long",
            "description-too-long",
            "context-notes-too-long",
            "invalid-status",
        ],
    )
    def test_rejects_invalid_initial_task_fields(
        self,
        tmp_path: Path,
        task: dict[str, str],
        error_match: str,
    ):
        with pytest.raises(ValueError, match=error_match):
            fold_dossier(
                dossiers_dir=tmp_path,
                name="Test",
                agent="claude-code",
                digest="Test.",
                tasks=[task],
            )

    def test_accepts_digest_at_max_length(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="d" * MAX_DIGEST_LENGTH,
        )

        assert result["task_count"] == 0

    def test_accepts_task_list_at_max_count(self, tmp_path: Path):
        tasks = [{"subject": f"Task {i}", "status": "pending"} for i in range(MAX_TASKS_PER_DOSSIER)]

        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Test.",
            tasks=tasks,
        )

        assert result["task_count"] == MAX_TASKS_PER_DOSSIER

    def test_accepts_initial_task_fields_at_max_length(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Test.",
            tasks=[{
                "subject": "s" * MAX_SUBJECT_LENGTH,
                "description": "d" * MAX_DESCRIPTION_LENGTH,
                "context_notes": "c" * MAX_CONTEXT_NOTES_LENGTH,
                "status": "blocked",
            }],
        )

        conn = connect_dossier_db(tmp_path / f"{result['slug']}.db")
        task = conn.execute(
            "SELECT subject, description, context_notes, status FROM tasks"
        ).fetchone()
        conn.close()
        assert len(task["subject"]) == MAX_SUBJECT_LENGTH
        assert len(task["description"]) == MAX_DESCRIPTION_LENGTH
        assert len(task["context_notes"]) == MAX_CONTEXT_NOTES_LENGTH
        assert task["status"] == "blocked"


class TestFoldResultCounts:
    """Tests for fold result summary counts."""

    def test_counts_reflect_the_fold_transaction(self, tmp_path: Path, monkeypatch):
        """Returned counts should ignore post-commit concurrent writes."""

        class RacingConnection:
            def __init__(self, conn: sqlite3.Connection, path: Path):
                self._conn = conn
                self._path = path

            def __enter__(self):
                self._conn.__enter__()
                return self

            def __exit__(self, exc_type, exc, tb):
                result = self._conn.__exit__(exc_type, exc, tb)
                if exc_type is None:
                    with sqlite3.connect(self._path) as other_conn:
                        other_conn.execute(
                            "INSERT INTO tasks (subject, status) VALUES (?, ?)",
                            ("concurrent task", "pending"),
                        )
                return result

            def __getattr__(self, name):
                return getattr(self._conn, name)

        @contextmanager
        def patched_open_dossier_db(path: Path):
            conn = connect_dossier_db(path)
            try:
                yield RacingConnection(conn, path)
            finally:
                conn.close()

        monkeypatch.setattr(fold_module, "open_dossier_db", patched_open_dossier_db)

        result = fold_module.fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="Test.",
            tasks=[{"subject": "initial task", "status": "pending"}],
        )

        assert result["task_count"] == 1

        conn = connect_dossier_db(tmp_path / f"{result['slug']}.db")
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        conn.close()
        assert count == 2


class TestRefoldDeregistration:
    """Fold exit-path-1: a refold by an orchestrator deregisters its v3
    single-store slot and releases its lock (or leaves a live other instance
    alone)."""

    def test_refold_deregisters_orchestrator_and_releases_lock(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.identity import resolve_identity
        from operations.dossiers.lock import claim_lock, get_lock_status

        mock_cli_pid(54321)
        slug = make_dossier(tasks=[{"subject": "t"}])["slug"]
        # simulate an active orchestrator session: registered + holding the lock
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            agent_id = resolve_identity(conn, slug, "claude-code")
        claim_lock(tmp_path, slug, agent=agent_id)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 1

        fold_dossier(dossiers_dir=tmp_path, slug=slug, agent="claude-code", digest="s2")

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0
        assert get_lock_status(tmp_path, slug)["locked_by"] is None

    def test_refold_skips_deregister_when_live_concurrent_instance(
        self, tmp_path, make_dossier, mock_cli_pid, mock_process_alive
    ):
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.identity import resolve_identity

        mock_cli_pid(11111)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            resolve_identity(conn, slug, "claude-code")  # cli_pid 11111 owns the slot

        # a different live instance now holds the slot; the folding process must
        # not clobber its registration
        mock_cli_pid(22222)
        mock_process_alive({11111: True})
        fold_dossier(dossiers_dir=tmp_path, slug=slug, agent="claude-code", digest="s2")

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 1


class TestFoldLockWarnings:
    """Fold must not warn about a lock that nobody holds (F8).

    `--claim` is opt-in, so the overwhelmingly common fold runs against an
    unlocked dossier. Warning on every one of those trains readers to ignore
    fold warnings wholesale, which defeats the warnings that matter.
    """

    def test_refold_on_unlocked_dossier_logs_no_lock_warning(
        self, tmp_path: Path, caplog
    ):
        """The normal case — an unlocked dossier — must be silent."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Quiet", agent="claude-code", digest="S1.",
        )
        with caplog.at_level(logging.WARNING, logger="operations.dossiers.fold"):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="claude-code",
                digest="S2.",
            )
        lock_warnings = [
            r.getMessage() for r in caplog.records if "Lock on" in r.getMessage()
        ]
        assert lock_warnings == [], f"unexpected lock warning: {lock_warnings}"

    def test_refold_still_warns_when_another_agent_holds_the_lock(
        self, tmp_path: Path, caplog
    ):
        """A genuinely contended lock is still worth reporting."""
        from operations.dossiers.lock import claim_lock

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Contended", agent="claude-code", digest="S1.",
        )
        claim_lock(tmp_path, result["slug"], agent="some-other-agent")
        with caplog.at_level(logging.WARNING, logger="operations.dossiers.fold"):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="claude-code",
                digest="S2.",
            )
        assert any(
            "not released on fold" in r.getMessage() for r in caplog.records
        ), "a lock held by another agent must still warn"
