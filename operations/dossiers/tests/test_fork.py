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


class TestForkRegistrations:
    """A fork must not inherit the source's registration rows.

    `sqlite3.backup()` copies every table verbatim, so anything describing who
    is working on the source arrives in the fork unless it is explicitly
    cleared. These assert both directions: cleared in the fork, intact in the
    source.

    The rows are not merely stale, they are *unreachable*: `agent_id` is a hash
    of the **source** slug, so an agent resolving against the fork computes a
    different id and can never match them. Meanwhile the inherited orchestrator
    row occupies the fork's one `(agent_type, orchestrator)` slot.
    """

    def _source_with_registrations(self, tmp_path, mock_cli_pid):
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.identity import resolve_identity
        from operations.dossiers.tasks import claim_task

        mock_cli_pid(4242)
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Source", agent="a", digest="D.",
            tasks=[{"subject": "t1", "status": "pending"}],
        )
        slug = result["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            resolve_identity(conn, slug, "claude-code")      # orchestrator row
        claim_task(tmp_path, slug, task_id=1, owner="claude-code:w:1")  # worker row
        return slug

    def _registrations(self, tmp_path, slug):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            return [dict(r) for r in conn.execute(
                "SELECT agent_id, role FROM registrations"
            ).fetchall()]

    def test_fork_starts_with_no_registrations(self, tmp_path, mock_cli_pid):
        slug = self._source_with_registrations(tmp_path, mock_cli_pid)
        assert len(self._registrations(tmp_path, slug)) == 2  # source is populated

        fork = fork_dossier(tmp_path, slug)

        assert self._registrations(tmp_path, fork["slug"]) == []

    def test_source_registrations_are_untouched_by_the_fork(
        self, tmp_path, mock_cli_pid
    ):
        # clearing the fork must not reach back through the shared page cache
        slug = self._source_with_registrations(tmp_path, mock_cli_pid)
        fork_dossier(tmp_path, slug)
        assert len(self._registrations(tmp_path, slug)) == 2

    def test_orchestrator_slot_in_the_fork_is_claimable(self, tmp_path, mock_cli_pid):
        """The functional consequence, not just the row count.

        The inherited row squats the fork's single orchestrator slot under an
        id nobody can recompute, so the first real agent to resolve against the
        fork hits the partial unique index instead of getting its own slot.
        """
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.identity import (
            _orchestrator_agent_id, resolve_identity,
        )

        slug = self._source_with_registrations(tmp_path, mock_cli_pid)
        fork = fork_dossier(tmp_path, slug)

        with open_dossier_db(safe_db_path(tmp_path, fork["slug"])) as conn:
            resolved = resolve_identity(conn, fork["slug"], "claude-code")

        # the agent gets the id its own slug hashes to, not an inherited one
        assert resolved == _orchestrator_agent_id(fork["slug"], "claude-code")
        assert [r["agent_id"] for r in self._registrations(tmp_path, fork["slug"])] == [resolved]

    def test_fork_of_a_locked_dossier_is_unlocked_and_unregistered(
        self, tmp_path, mock_cli_pid
    ):
        # forks already start unlocked; registrations must follow the same rule,
        # since both describe "who is currently working here"
        from operations.dossiers.lock import claim_lock, get_lock_status

        slug = self._source_with_registrations(tmp_path, mock_cli_pid)
        claim_lock(tmp_path, slug, agent="somebody")
        fork = fork_dossier(tmp_path, slug)

        assert get_lock_status(tmp_path, fork["slug"])["locked_by"] is None
        assert self._registrations(tmp_path, fork["slug"]) == []


class TestForkClearsInFlightState:
    """A fork starts with nobody working on it.

    `fork` already advertises "always unlocked". The lock, the registrations,
    the task ownership and the reap log are all the same category of state:
    *who is currently working here*. Inheriting any of them puts the fork in a
    state its own machinery cannot reason about, because every id in them is
    derived from the **source** slug.
    """

    def _source_mid_flight(self, tmp_path, mock_cli_pid):
        from operations.dossiers.tasks import claim_task

        mock_cli_pid(4242)
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Source", agent="a", digest="D.",
            tasks=[
                {"subject": "t1", "status": "pending"},
                {"subject": "t2", "status": "pending"},
            ],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="claude-code:w:1")
        return result["slug"]

    def _rows(self, tmp_path, slug, sql):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    def test_in_flight_tasks_revert_to_claimable(self, tmp_path, mock_cli_pid):
        """Otherwise the fork holds an unrepairable in_progress task.

        Its owner is a source-slug-derived id with no registration row in the
        fork, and the reap cascade only iterates rows that exist — so nothing
        can ever revert it — the same orphan class the fold exit path prevents,
        reached through another door.
        """
        slug = self._source_mid_flight(tmp_path, mock_cli_pid)
        fork = fork_dossier(tmp_path, slug)

        tasks = self._rows(tmp_path, fork["slug"], "SELECT status, owner FROM tasks")
        assert all(t["status"] != "in_progress" for t in tasks)
        assert all(t["owner"] is None for t in tasks)

    def test_source_keeps_its_in_flight_work(self, tmp_path, mock_cli_pid):
        slug = self._source_mid_flight(tmp_path, mock_cli_pid)
        fork_dossier(tmp_path, slug)

        tasks = self._rows(tmp_path, slug, "SELECT status, owner FROM tasks WHERE id = 1")
        assert tasks[0]["status"] == "in_progress"
        assert tasks[0]["owner"] == "claude-code:w:1"

    def test_completed_tasks_are_preserved(self, tmp_path, mock_cli_pid):
        # only *in-flight* ownership is dropped; finished work is history and
        # a fork inherits history
        from operations.dossiers.tasks import complete_task

        slug = self._source_mid_flight(tmp_path, mock_cli_pid)
        complete_task(tmp_path, slug, task_id=1, agent="claude-code:w:1")
        fork = fork_dossier(tmp_path, slug)

        tasks = self._rows(
            tmp_path, fork["slug"], "SELECT status FROM tasks WHERE id = 1"
        )
        assert tasks[0]["status"] == "completed"

    def test_reap_log_does_not_follow_the_fork(self, tmp_path, mock_cli_pid):
        """An inherited reap makes the fork's first agent think it was reaped.

        `_maybe_warn_identity_reset` fires on any reap of its agent_type within
        the last hour, so a fork taken soon after one warns "IDENTITY RESET"
        about an event that happened in a different dossier.
        """
        from operations.dossiers.db import open_dossier_db, safe_db_path

        slug = self._source_mid_flight(tmp_path, mock_cli_pid)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "INSERT INTO reap_log (reaped_at, agent_id, agent_type, role, "
                "last_heartbeat, stale_by_sec, tasks_reverted, lock_released, "
                "reap_reason) VALUES (datetime('now'), 'orch-claude-code-x', "
                "'claude-code', 'orchestrator', '2000-01-01T00:00:00Z', 99, "
                "'[]', 0, 'pid_dead')"
            )
            conn.commit()

        fork = fork_dossier(tmp_path, slug)
        assert self._rows(tmp_path, fork["slug"], "SELECT * FROM reap_log") == []
        assert len(self._rows(tmp_path, slug, "SELECT * FROM reap_log")) == 1
