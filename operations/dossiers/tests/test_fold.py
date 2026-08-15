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
    open_dossier_db,
    safe_db_path,
)
from operations.dossiers.findings import finding_hash
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


class TestFailedFoldLeavesNothingBehind:
    """A new fold creates its database *before* the transaction that fills it.

    Any failure below that point used to leave a schema-only file with no
    `metadata` row: invisible to `list` (which skips metadata-less databases)
    but still matched by `find_dossier`'s `*.db` glob, so `unfold <name>`
    found it and died on a NULL metadata row.
    """

    def test_failed_new_fold_removes_the_database_it_created(self, tmp_path: Path):
        with pytest.raises(ValueError):
            fold_dossier(
                dossiers_dir=tmp_path, name="Doomed", agent="claude-code",
                digest="D.", tasks=[{"subject": _over_limit(MAX_SUBJECT_LENGTH)}],
            )

        assert list(tmp_path.glob("*.db")) == [], "a failed new fold left an orphan"

    def test_failed_new_fold_leaves_no_wal_sidecars(self, tmp_path: Path):
        with pytest.raises(ValueError):
            fold_dossier(
                dossiers_dir=tmp_path, name="Doomed", agent="claude-code",
                digest="D.", tasks=[{"subject": _over_limit(MAX_SUBJECT_LENGTH)}],
            )

        assert list(tmp_path.iterdir()) == [], "a failed new fold left files behind"

    def test_failed_refold_preserves_the_existing_dossier(self, tmp_path: Path):
        """The cleanup must never delete a database that predates the call."""
        created = fold_dossier(
            dossiers_dir=tmp_path, name="Keep", agent="claude-code", digest="S1.",
        )

        with pytest.raises(KeyError):
            fold_dossier(
                dossiers_dir=tmp_path, slug=created["slug"], agent="claude-code",
                digest="S2.", decisions=[{"why": "no 'what' key"}],
            )

        with connect_dossier_db(tmp_path / f"{created['slug']}.db") as conn:
            name = conn.execute("SELECT name FROM metadata").fetchone()["name"]
        assert name == "Keep"


class TestRefoldExitAtomicity:
    """The lock release and the deregistration must not be separable.

    Split across two commits, a failure in between leaves `registrations` empty
    while `metadata.locked_by` still names the deleted agent — and cleanup can
    never repair that, because its cascade only iterates registration rows that
    still exist, leaving `lock release --force` as the sole escape.
    """

    def _registered_lock_holder(self, tmp_path, slug):
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.identity import resolve_identity
        from operations.dossiers.lock import claim_lock

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            agent_id = resolve_identity(conn, slug, "claude-code")
        claim_lock(tmp_path, slug, agent=agent_id)
        return agent_id

    def test_an_orphaned_lock_is_unrepairable_by_cleanup(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        """Why this outranks its blast radius: the bad state has no way out.

        Passes before and after the fix; it characterises the hazard rather
        than the fix, and is what makes an orphaned lock worth preventing
        atomically instead of merely narrowing the window.
        """
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.lock import get_lock_status

        slug = make_dossier()["slug"]
        # exactly the state the old exit path could leave: a lock naming an
        # agent whose registration row is gone
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "UPDATE metadata SET locked_by = ?, locked_at = ?",
                ("orch-claude-code-vanished", "2000-01-01T00:00:00Z"),
            )
            conn.commit()

        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        for _ in range(3):  # cleanup runs as a connect preamble; give it chances
            with open_dossier_db(safe_db_path(tmp_path, slug)):
                pass

        # the cascade only iterates rows that still exist, so it never sees this
        assert get_lock_status(tmp_path, slug)["locked_by"] == "orch-claude-code-vanished"

    def test_a_failing_out_of_band_release_cannot_orphan_the_lock(
        self, tmp_path, make_dossier, mock_cli_pid, monkeypatch
    ):
        """The hazardous window: deregistration commits, then the release fails.

        `raising=False` because no out-of-band `release_lock` call exists to
        patch: sharing one transaction is what makes the window unreachable, so
        the invariant holds by construction rather than by the patch missing.
        """
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.lock import get_lock_status

        mock_cli_pid(54321)
        slug = make_dossier()["slug"]
        self._registered_lock_holder(tmp_path, slug)

        def _boom(*args, **kwargs):
            raise RuntimeError("crash after deregistration, before release")

        monkeypatch.setattr(
            "operations.dossiers.fold.release_lock", _boom, raising=False
        )
        try:
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="claude-code", digest="s2"
            )
        except RuntimeError:
            pass  # the crash itself is fine; the state it leaves behind is not

        holder = get_lock_status(tmp_path, slug)["locked_by"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            registered = [
                r["agent_id"]
                for r in conn.execute("SELECT agent_id FROM registrations").fetchall()
            ]
        assert holder is None or holder in registered, (
            f"orphaned lock: {holder!r} holds the lock with no registration row"
        )

    def test_failure_during_deregistration_rolls_back_the_release(
        self, tmp_path, make_dossier, mock_cli_pid, monkeypatch
    ):
        """Reordering alone is not enough; the two writes must share a txn.

        With the release moved first but left in its own transaction, a failing
        deregistration would leave the lock released and the registration
        intact. One transaction is what makes that unreachable.
        """
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.lock import get_lock_status

        mock_cli_pid(54321)
        slug = make_dossier()["slug"]
        agent_id = self._registered_lock_holder(tmp_path, slug)

        def _boom(conn, agent):
            raise RuntimeError("crash during deregistration")

        monkeypatch.setattr("operations.dossiers.fold.deregister_agent", _boom)
        with pytest.raises(RuntimeError):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="claude-code", digest="s2"
            )

        assert get_lock_status(tmp_path, slug)["locked_by"] == agent_id
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM registrations"
            ).fetchone()[0] == 1

    def test_lock_never_outlives_its_registration(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        # the invariant, stated directly: no state in which
        # `locked_by` names an agent with no registration row
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.lock import get_lock_status

        mock_cli_pid(54321)
        slug = make_dossier()["slug"]
        self._registered_lock_holder(tmp_path, slug)

        fold_dossier(dossiers_dir=tmp_path, slug=slug, agent="claude-code", digest="s2")

        holder = get_lock_status(tmp_path, slug)["locked_by"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            registered = [
                r["agent_id"]
                for r in conn.execute("SELECT agent_id FROM registrations").fetchall()
            ]
        assert holder is None or holder in registered

    def test_lock_held_by_another_agent_survives_the_fold(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        # releasing on the same connection must keep `release_lock`'s conditional
        # semantics: a lock we do not hold is not ours to clear
        from operations.dossiers.lock import claim_lock, get_lock_status

        mock_cli_pid(54321)
        slug = make_dossier()["slug"]
        claim_lock(tmp_path, slug, agent="somebody-else")

        fold_dossier(dossiers_dir=tmp_path, slug=slug, agent="claude-code", digest="s2")

        assert get_lock_status(tmp_path, slug)["locked_by"] == "somebody-else"


# ── v5: the five payload keys that used to be dropped ───────────────────


def _rows(tmp_path: Path, slug: str, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Return rows from a dossier, read outside the fold's own connection."""
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        return conn.execute(sql, params).fetchall()


def _findings(tmp_path: Path, slug: str) -> list[sqlite3.Row]:
    return _rows(tmp_path, slug, "SELECT * FROM pinned_findings ORDER BY created_at, hash")


def _edges(tmp_path: Path, slug: str) -> list[tuple[str, str]]:
    return [
        (r["new_hash"], r["old_hash"])
        for r in _rows(
            tmp_path, slug,
            "SELECT new_hash, old_hash FROM finding_supersessions ORDER BY new_hash, old_hash",
        )
    ]


@contextmanager
def _fold_log(caplog):
    """Capture the fold module's warnings and errors around a fold."""
    with caplog.at_level(logging.WARNING, logger="operations.dossiers.fold"):
        yield caplog


def _messages(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records]


class TestFoldSessionScalars:
    """`last_exchange`, `next_words` and `mood` are per-session, one row each."""

    def test_stores_the_three_scalars_on_the_session_row(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            last_exchange="user: ship it\nme: on it",
            next_words="Right, the migration first.",
            mood="Focused, fast, and slightly punchy.",
        )

        row = _rows(tmp_path, result["slug"], "SELECT * FROM sessions")[0]

        assert row["last_exchange"] == "user: ship it\nme: on it"
        assert row["next_words"] == "Right, the migration first."
        assert row["mood"] == "Focused, fast, and slightly punchy."

    def test_leaves_them_null_when_the_payload_omits_them(self, tmp_path: Path):
        """An older cached skill sends none of these; NULL is how render skips."""
        result = fold_dossier(dossiers_dir=tmp_path, name="Test", agent="a", digest="D.")

        row = _rows(tmp_path, result["slug"], "SELECT * FROM sessions")[0]

        assert (row["last_exchange"], row["next_words"], row["mood"]) == (None, None, None)

    def test_each_session_keeps_its_own_scalars(self, tmp_path: Path):
        """Per-session, not per-dossier: a re-fold never overwrites session 1's."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.", mood="tense",
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            mood="relieved",
        )

        moods = [
            r["mood"]
            for r in _rows(tmp_path, result["slug"], "SELECT mood FROM sessions ORDER BY id")
        ]

        assert moods == ["tense", "relieved"]


class TestFoldMemoryQueries:
    """Session-scoped, append-only, never pruned at write time."""

    def test_stores_a_memory_query_against_its_session(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            memory_queries=[{
                "tool": "qdrant-find", "query": "bureau dossier schema",
                "result_summary": "3 entries, all stale", "used_for": "skipped a re-read",
            }],
        )

        row = _rows(tmp_path, result["slug"], "SELECT * FROM memory_queries")[0]

        assert row["tool"] == "qdrant-find"
        assert row["query"] == "bureau dossier schema"
        assert row["result_summary"] == "3 entries, all stale"
        assert row["used_for"] == "skipped a re-read"
        assert row["session_id"] == 1

    def test_accumulates_across_folds(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            memory_queries=[{"query": "q1"}],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            memory_queries=[{"query": "q2"}],
        )

        queries = [
            r["query"]
            for r in _rows(tmp_path, result["slug"], "SELECT query FROM memory_queries ORDER BY id")
        ]

        assert queries == ["q1", "q2"]

    def test_retention_never_deletes_memory_queries(self, tmp_path: Path):
        """`--max-retained-sessions` is scoped to file interactions, and stays so."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            memory_queries=[{"query": "q1"}],
        )
        for i in range(2, 5):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest=f"D{i}.",
                memory_queries=[{"query": f"q{i}"}], max_retained_sessions=1,
            )

        rows = _rows(tmp_path, result["slug"], "SELECT id FROM memory_queries")

        assert len(rows) == 4

    def test_skips_an_element_with_no_query_text(self, tmp_path: Path, caplog):
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                memory_queries=[{"tool": "qdrant-find"}],
            )

        assert _rows(tmp_path, result["slug"], "SELECT id FROM memory_queries") == []
        assert any("memory_queries[0]" in m for m in _messages(caplog))


class TestPinnedFindingIdentity:
    """D1/D5: the content hash is the primary key, so dedupe is the PK itself."""

    def test_stores_a_finding_under_its_content_hash(self, tmp_path: Path):
        element = {"finding": "qdrant must be up before searxng starts"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        row = _findings(tmp_path, result["slug"])[0]

        assert row["hash"] == finding_hash(element)
        assert row["kind"] == "finding"
        assert row["text"] == "qdrant must be up before searxng starts"
        assert row["origin_session"] == 1
        assert row["created_at"]

    def test_stores_a_dead_end_with_its_metadata(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[{
                "finding": "port 8780 is owned by another app",
                "dead_end": True,
                "why_abandoned": "the owning app cannot be uninstalled",
                "retry": "DO NOT RETRY",
            }],
        )

        row = _findings(tmp_path, result["slug"])[0]

        assert row["kind"] == "dead_end"
        assert row["why_abandoned"] == "the owning app cannot be uninstalled"
        assert row["retry"] == "DO NOT RETRY"

    def test_stores_the_canonicalized_text(self, tmp_path: Path):
        """Storing the normalized form is what keeps the rendered line single-line."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[{"finding": "  qdrant   must be up\nbefore searxng "}],
        )

        assert _findings(tmp_path, result["slug"])[0]["text"] == (
            "qdrant must be up before searxng"
        )

    def test_provenance_is_recorded_by_the_cli_not_the_payload(self, tmp_path: Path):
        """Two sessions discovering one fact must mint one identity."""
        element = {"finding": "the same fact, learned twice"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[element],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="b", digest="D2.",
            pinned_findings=[element],
        )

        rows = _findings(tmp_path, result["slug"])

        assert len(rows) == 1
        assert rows[0]["origin_session"] == 1

    def test_refolding_the_same_finding_is_idempotent(self, tmp_path: Path):
        """D5: the misbehaving sender is the threat model, not an edge case."""
        elements = [{"finding": "A"}, {"finding": "B"}, {"finding": "C"}]
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=elements,
        )
        for i in range(2, 5):
            # a stale-skill agent carrying everything forward every time
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest=f"D{i}.",
                pinned_findings=elements,
            )

        assert len(_findings(tmp_path, result["slug"])) == 3

    def test_resending_live_content_warns_about_nothing(self, tmp_path: Path, caplog):
        """A guaranteed no-op must also be a silent one, or the channel dies."""
        element = {"finding": "qdrant must be up"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[element],
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
                pinned_findings=[element],
            )

        assert _messages(caplog) == []

    def test_a_richer_resend_is_stored_as_new_content(self, tmp_path: Path):
        """The r2-F7 class on the new table: nothing richer is silently dropped."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[{
                "finding": "port 8780 is owned", "dead_end": True,
                "retry": "CONDITIONAL: the owner is uninstalled",
            }],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{
                "finding": "port 8780 is owned", "dead_end": True,
                "retry": "DO NOT RETRY",
            }],
        )

        retries = {r["retry"] for r in _findings(tmp_path, result["slug"])}

        assert retries == {"CONDITIONAL: the owner is uninstalled", "DO NOT RETRY"}

    def test_concurrent_folds_of_one_finding_store_one_row(self, tmp_path: Path):
        """The PK is atomic, so there is no check-then-act window to lose."""
        import threading

        element = {"finding": "two agents discovered this at once"}
        result = fold_dossier(dossiers_dir=tmp_path, name="Test", agent="a", digest="D0.")
        slug = result["slug"]
        barrier = threading.Barrier(2)
        errors: list[BaseException] = []

        def _fold(tag: str) -> None:
            try:
                barrier.wait(timeout=10)
                fold_dossier(
                    dossiers_dir=tmp_path, slug=slug, agent=tag, digest=f"D-{tag}.",
                    pinned_findings=[element],
                )
            except BaseException as exc:  # noqa: BLE001 - re-raised by the assertion
                errors.append(exc)

        threads = [threading.Thread(target=_fold, args=(t,)) for t in ("one", "two")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert errors == []
        assert len(_findings(tmp_path, slug)) == 1

    def test_skips_an_element_with_no_finding_text(self, tmp_path: Path, caplog):
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[{"dead_end": True, "why_abandoned": "orphaned"}],
            )

        assert _findings(tmp_path, result["slug"]) == []
        assert any("pinned_findings[0]" in m for m in _messages(caplog))

    def test_stores_an_unrecognized_kind_as_a_plain_finding(self, tmp_path: Path, caplog):
        """Warn, never reject: an odd `kind` must not cost the agent its finding."""
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[{"finding": "still worth keeping", "kind": "musing"}],
            )

        assert _findings(tmp_path, result["slug"])[0]["kind"] == "finding"
        assert any("musing" in m for m in _messages(caplog))


class TestPinnedFindingSupersession:
    """D3/D8: one edge per arrow, resolved from 8-hex prefixes at fold time."""

    @staticmethod
    def _seed(tmp_path: Path, *findings: dict) -> tuple[str, list[str]]:
        """Fold `findings` into a new dossier; return its slug and their hashes."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=list(findings),
        )
        return result["slug"], [finding_hash(f) for f in findings]

    def test_an_unambiguous_prefix_writes_the_edge(self, tmp_path: Path):
        slug, [old] = self._seed(tmp_path, {"finding": "qdrant must be started first"})
        new = {"finding": "qdrant must be up before searxng; shared readiness dep",
               "supersedes": [old[:8]]}

        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[new],
        )

        assert _edges(tmp_path, slug) == [(finding_hash(new), old)]

    def test_one_finding_can_retire_many_predecessors(self, tmp_path: Path):
        """Consolidation is the remedy D6's health warning tells agents to use."""
        slug, olds = self._seed(
            tmp_path,
            {"finding": "qdrant must be started before searxng"},
            {"finding": "searxng fails unless qdrant is already up"},
            {"finding": "start order: qdrant first, then searxng"},
        )
        new = {"finding": "qdrant must be up before searxng starts",
               "supersedes": [h[:8] for h in olds]}

        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[new],
        )

        assert sorted(o for _, o in _edges(tmp_path, slug)) == sorted(olds)

    def test_a_dangling_prefix_keeps_the_finding_and_warns(self, tmp_path: Path, caplog):
        """Rejecting would discard new content over a typo in its metadata."""
        slug, _ = self._seed(tmp_path, {"finding": "an existing finding"})
        new = {"finding": "brand new content", "supersedes": ["deadbeef"]}

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
                pinned_findings=[new],
            )

        assert finding_hash(new) in {r["hash"] for r in _findings(tmp_path, slug)}
        assert _edges(tmp_path, slug) == []
        assert any("deadbeef" in m for m in _messages(caplog))

    def test_an_ambiguous_prefix_keeps_the_finding_and_names_every_candidate(
        self, tmp_path: Path, caplog
    ):
        """Guessing would coin-flip a live constraint into retirement."""
        slug, [existing] = self._seed(tmp_path, {"finding": "an existing finding"})
        ambiguous = existing[:2]  # two hex chars: the seed plus whatever we add
        sibling = {"finding": "a sibling that shares the prefix"}
        # find a second finding whose hash starts with the same two characters
        counter = 0
        while not finding_hash(sibling).startswith(ambiguous):
            counter += 1
            sibling = {"finding": f"a sibling that shares the prefix {counter}"}
        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[sibling],
        )
        new = {"finding": "consolidating text", "supersedes": [ambiguous]}

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest="D3.",
                pinned_findings=[new],
            )

        messages = _messages(caplog)
        assert finding_hash(new) in {r["hash"] for r in _findings(tmp_path, slug)}
        assert _edges(tmp_path, slug) == []
        assert any("ambiguous" in m.lower() for m in messages), messages
        # full digests, not the rendered 8-hex: on a real prefix collision the
        # 8-hex handles are identical, so a "use a longer prefix" remedy needs
        # this message to be the surface that supplies the longer prefix
        assert any(
            existing in m and finding_hash(sibling) in m for m in messages
        ), messages

    def test_an_ambiguous_resolution_is_reported_at_error_grade(
        self, tmp_path: Path, caplog
    ):
        """Error-grade wording, but the fold still succeeds (warn, never reject)."""
        slug, [existing] = self._seed(tmp_path, {"finding": "an existing finding"})
        sibling = {"finding": "a sibling"}
        counter = 0
        while not finding_hash(sibling).startswith(existing[:2]):
            counter += 1
            sibling = {"finding": f"a sibling {counter}"}
        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[sibling],
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest="D3.",
                pinned_findings=[{"finding": "consolidating", "supersedes": [existing[:2]]}],
            )

        assert [r.levelname for r in caplog.records] == ["ERROR"]

    def test_an_edge_is_refused_when_its_new_hash_already_exists(
        self, tmp_path: Path, caplog
    ):
        """D3: edges live only in the transaction that creates their row.

        Accepting one against a pre-existing row is the only way an arrow could
        ever point forward in time, so it is the one place cycles could enter.
        """
        slug, [old] = self._seed(tmp_path, {"finding": "the older finding"})
        new = {"finding": "the newer finding"}
        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[new],
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest="D3.",
                pinned_findings=[{**new, "supersedes": [old[:8]]}],
            )

        assert _edges(tmp_path, slug) == []
        assert any(finding_hash(new)[:8] in m for m in _messages(caplog))

    def test_a_finding_can_supersede_one_folded_in_the_same_payload(self, tmp_path: Path):
        """The target must pre-exist the edge, not the transaction."""
        first = {"finding": "the first phrasing"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[
                first,
                {"finding": "the better phrasing", "supersedes": [finding_hash(first)[:8]]},
            ],
        )

        assert _edges(tmp_path, result["slug"]) == [
            (finding_hash({"finding": "the better phrasing"}), finding_hash(first))
        ]

    def test_a_prefix_matching_only_the_new_finding_writes_no_self_edge(
        self, tmp_path: Path, caplog
    ):
        """A self-edge would retire the finding at birth — silently too little.

        Reachable without a collision: a short prefix aimed at a target that
        does not exist can still match the row being written.
        """
        element = {"finding": "a fact that retires nothing"}
        own = finding_hash(element)

        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[{**element, "supersedes": [own[:2]]}],
            )

        assert _edges(tmp_path, result["slug"]) == []
        assert [r["hash"] for r in _findings(tmp_path, result["slug"])] == [own]
        assert any("no other stored finding" in m for m in _messages(caplog))

    def test_a_non_list_supersedes_is_ignored_with_a_warning(self, tmp_path: Path, caplog):
        slug, [old] = self._seed(tmp_path, {"finding": "the older finding"})

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
                pinned_findings=[{"finding": "newer", "supersedes": old[:8]}],
            )

        assert _edges(tmp_path, slug) == []
        assert any("supersedes" in m for m in _messages(caplog))


class TestPinnedFindingRetraction:
    """D4: a tombstone is an ordinary row; revival requires re-wording."""

    def test_a_retraction_is_a_row_plus_an_ordinary_edge(self, tmp_path: Path):
        dead_end = {"finding": "port 8780 is permanently owned", "dead_end": True,
                    "retry": "DO NOT RETRY"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[dead_end],
        )
        tombstone = {
            "finding": "the app owning port 8780 was uninstalled 08-12; the port is free",
            "kind": "retraction",
            "supersedes": [finding_hash(dead_end)[:8]],
        }

        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[tombstone],
        )

        kinds = {r["hash"]: r["kind"] for r in _findings(tmp_path, result["slug"])}
        assert kinds[finding_hash(tombstone)] == "retraction"
        assert _edges(tmp_path, result["slug"]) == [
            (finding_hash(tombstone), finding_hash(dead_end))
        ]

    def test_resending_a_superseded_finding_warns_instead_of_no_opping(
        self, tmp_path: Path, caplog
    ):
        """Silent loss of exactly what this table exists to never lose."""
        old = {"finding": "the first phrasing"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[old],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{"finding": "the better phrasing",
                              "supersedes": [finding_hash(old)[:8]]}],
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D3.",
                pinned_findings=[old],
            )

        messages = _messages(caplog)
        assert any(finding_hash(old)[:8] in m for m in messages), messages
        assert any("re-worded" in m for m in messages), messages

    def test_resending_a_retracted_finding_warns(self, tmp_path: Path, caplog):
        dead_end = {"finding": "port 8780 is owned", "dead_end": True}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[dead_end],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{"finding": "port 8780 was freed on 08-12",
                              "kind": "retraction",
                              "supersedes": [finding_hash(dead_end)[:8]]}],
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D3.",
                pinned_findings=[dead_end],
            )

        assert any("re-worded" in m for m in _messages(caplog))

    def test_resending_a_tombstone_warns(self, tmp_path: Path, caplog):
        """A tombstone is retired too: it never renders as a live constraint."""
        dead_end = {"finding": "port 8780 is owned", "dead_end": True}
        tombstone = {"finding": "port 8780 was freed on 08-12", "kind": "retraction",
                     "supersedes": [finding_hash(dead_end)[:8]]}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[dead_end],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[tombstone],
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D3.",
                pinned_findings=[{"finding": tombstone["finding"], "kind": "retraction"}],
            )

        assert any("re-worded" in m for m in _messages(caplog))

    def test_reworded_revival_lands_as_a_new_live_finding(self, tmp_path: Path):
        """The remedy the warning names must actually work."""
        dead_end = {"finding": "port 8780 is owned", "dead_end": True}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[dead_end],
        )
        tombstone = {"finding": "port 8780 was freed on 08-12", "kind": "retraction",
                     "supersedes": [finding_hash(dead_end)[:8]]}
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[tombstone],
        )
        revival = {"finding": "port 8780 is owned again as of the 08-20 reinstall",
                   "dead_end": True, "supersedes": [finding_hash(tombstone)[:8]]}

        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D3.",
            pinned_findings=[revival],
        )

        assert (finding_hash(revival), finding_hash(tombstone)) in _edges(
            tmp_path, result["slug"]
        )


class TestDecisionProvenance:
    """r2-F7: a duplicate is a duplicate only when nothing about it is richer."""

    def test_an_identical_decision_is_still_deduped(self, tmp_path: Path):
        decision = {"what": "Use SQLite", "why": "ACID", "decided_by": "user"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            decisions=[decision],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            decisions=[decision],
        )

        assert len(_rows(tmp_path, result["slug"], "SELECT id FROM decisions")) == 1

    def test_a_richer_duplicate_is_not_discarded(self, tmp_path: Path):
        """The defect: `decided_by` and `alternatives` vanished on the re-send."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            decisions=[{"what": "Use SQLite", "why": "ACID"}],
        )

        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            decisions=[{"what": "Use SQLite", "why": "ACID", "decided_by": "user",
                        "alternatives": ["JSON files", "YAML"]}],
        )

        rows = _rows(tmp_path, result["slug"], "SELECT * FROM decisions ORDER BY id")
        assert len(rows) == 2
        assert rows[1]["decided_by"] == "user"
        assert json.loads(rows[1]["alternatives"]) == ["JSON files", "YAML"]

    def test_a_richer_duplicate_inherits_the_original_provenance(self, tmp_path: Path):
        """An inherited decision keeps its age, whichever fold rewrote it."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            decisions=[{"what": "Use SQLite", "why": "ACID"}],
        )
        fold_dossier(dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.")

        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D3.",
            decisions=[{"what": "Use SQLite", "why": "ACID", "decided_by": "user"}],
        )

        rows = _rows(tmp_path, result["slug"], "SELECT * FROM decisions ORDER BY id")
        assert rows[1]["session_id"] == 3, "the row was written by the third fold"
        assert rows[1]["origin_session"] == 1, "but the decision dates from the first"

    def test_records_how_the_row_entered_the_dossier(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            decisions=[{"what": "Use SQLite", "why": "ACID"}],
        )

        row = _rows(tmp_path, result["slug"], "SELECT * FROM decisions")[0]

        assert row["source"] == "fold"
        assert row["origin_session"] == 1


class TestMalformedPayloadValuesNeverKillTheFold:
    """A bad value in one element must never cost the session its fold.

    Before v5 these keys were dropped wholesale, so a malformed one was
    harmless. Persisting them made a non-string value reach SQLite's binder,
    which raises inside the fold transaction and takes the *session row* down
    with it — strictly worse than the world this migration replaced.
    """

    def test_a_non_string_finding_skips_the_element_and_keeps_the_session(
        self, tmp_path: Path, caplog
    ):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="S2.",
                pinned_findings=[{"finding": ["multi", "part"]}],
            )

        sessions = _rows(tmp_path, result["slug"], "SELECT digest FROM sessions ORDER BY id")
        assert [s["digest"] for s in sessions] == ["S1.", "S2."]
        assert _findings(tmp_path, result["slug"]) == []
        [message] = _messages(caplog)
        assert "pinned_findings[0]" in message
        assert "finding" in message and "multi" in message
        assert "string" in message

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("finding", ["a", "b"]),
            ("finding", {"text": "a"}),
            ("finding", 8780),
            ("finding", True),
            ("why_abandoned", 42),
            ("retry", ["DO NOT RETRY"]),
        ],
        ids=["list", "dict", "int", "bool", "why-int", "retry-list"],
    )
    def test_a_non_string_semantic_field_skips_the_element(
        self, tmp_path: Path, caplog, field: str, value: object
    ):
        element = {"finding": "a valid finding", field: value}

        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[element],
            )

        assert _findings(tmp_path, result["slug"]) == []
        assert any(field in m for m in _messages(caplog))

    def test_a_numeric_finding_never_reaches_storage(self, tmp_path: Path, caplog):
        """Stored as TEXT but hashed as a number: one value, two identities."""
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[{"finding": 8780}, {"finding": "8780"}],
            )

        assert [r["text"] for r in _findings(tmp_path, result["slug"])] == ["8780"]

    def test_a_non_boolean_dead_end_skips_the_element(self, tmp_path: Path, caplog):
        """`dead_end` participates in identity, so a near-miss type is not a guess."""
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[{"finding": "f", "dead_end": "true"}],
            )

        assert _findings(tmp_path, result["slug"]) == []
        assert any("dead_end" in m for m in _messages(caplog))

    def test_a_valid_element_still_lands_beside_a_malformed_one(self, tmp_path: Path, caplog):
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                pinned_findings=[{"finding": 1}, {"finding": "the good one"}],
            )

        assert [r["text"] for r in _findings(tmp_path, result["slug"])] == ["the good one"]

    @pytest.mark.parametrize(
        ("field", "value"),
        [("query", ["q"]), ("tool", 3), ("result_summary", {}), ("used_for", False)],
        ids=["query-list", "tool-int", "summary-dict", "used-for-bool"],
    )
    def test_a_non_string_memory_query_field_skips_the_element(
        self, tmp_path: Path, caplog, field: str, value: object
    ):
        entry = {"query": "a valid query", field: value}

        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                memory_queries=[entry],
            )

        assert _rows(tmp_path, result["slug"], "SELECT id FROM memory_queries") == []
        assert any(field in m and "memory_queries[0]" in m for m in _messages(caplog))

    @pytest.mark.parametrize(
        "scalar", ["last_exchange", "next_words", "mood"],
    )
    def test_a_non_string_session_scalar_is_dropped_not_fatal(
        self, tmp_path: Path, caplog, scalar: str
    ):
        with _fold_log(caplog):
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
                **{scalar: {"not": "a string"}},
            )

        row = _rows(tmp_path, result["slug"], "SELECT * FROM sessions")[0]
        assert row[scalar] is None
        assert row["digest"] == "D."
        assert any(scalar in m for m in _messages(caplog))

    def test_a_non_string_supersedes_prefix_is_skipped(self, tmp_path: Path, caplog):
        slug, [old] = TestPinnedFindingSupersession._seed(
            tmp_path, {"finding": "the older finding"}
        )

        with _fold_log(caplog):
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
                pinned_findings=[{"finding": "newer", "supersedes": [{"hash": old}]}],
            )

        assert _edges(tmp_path, slug) == []
        assert any("supersedes" in m for m in _messages(caplog))
