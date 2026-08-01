"""Tests for dossier task CRUD operations."""
from pathlib import Path

import pytest

from operations.dossiers.db import (
    MAX_CONTEXT_NOTES_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_SUBJECT_LENGTH,
    open_dossier_db,
    safe_db_path,
)
from operations.dossiers.errors import (
    IdentityReapedError,
    TaskAlreadyCompletedError,
    TaskDeletedError,
    TaskNotFoundError,
    TaskStateError,
)
from operations.dossiers.fold import fold_dossier
from operations.dossiers.tasks import list_tasks, add_task, update_task, remove_task, claim_task, complete_task


def _over_limit(limit: int, ch: str = "x") -> str:
    """Return a string one character longer than the provided limit."""
    return ch * (limit + 1)


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

    @pytest.mark.parametrize(
        ("kwargs", "error_match"),
        [
            ({"subject": _over_limit(MAX_SUBJECT_LENGTH)}, "Subject exceeds maximum length"),
            (
                {"subject": "Task", "description": _over_limit(MAX_DESCRIPTION_LENGTH)},
                "Description exceeds maximum length",
            ),
            (
                {"subject": "Task", "context_notes": _over_limit(MAX_CONTEXT_NOTES_LENGTH)},
                "Context notes exceeds maximum length",
            ),
            ({"subject": "Task", "status": "invalid"}, "Invalid status"),
        ],
        ids=[
            "subject-too-long",
            "description-too-long",
            "context-notes-too-long",
            "invalid-status",
        ],
    )
    def test_rejects_invalid_fields(self, tmp_path: Path, kwargs: dict[str, str], error_match: str):
        """add_task should reject invalid lengths and statuses."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )

        with pytest.raises(ValueError, match=error_match):
            add_task(tmp_path, result["slug"], **kwargs)

    def test_accepts_fields_at_max_length(self, tmp_path: Path):
        """Boundary-length values should be accepted unchanged."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )

        add_task(
            tmp_path,
            result["slug"],
            subject="s" * MAX_SUBJECT_LENGTH,
            description="d" * MAX_DESCRIPTION_LENGTH,
            context_notes="c" * MAX_CONTEXT_NOTES_LENGTH,
            status="blocked",
        )

        task = list_tasks(tmp_path, result["slug"])[0]
        assert len(task["subject"]) == MAX_SUBJECT_LENGTH
        assert len(task["description"]) == MAX_DESCRIPTION_LENGTH
        assert len(task["context_notes"]) == MAX_CONTEXT_NOTES_LENGTH
        assert task["status"] == "blocked"


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
        with pytest.raises(ValueError):
            update_task(tmp_path, result["slug"], task_id=999, status="completed")

    @pytest.mark.parametrize(
        ("kwargs", "error_match"),
        [
            ({"subject": _over_limit(MAX_SUBJECT_LENGTH)}, "Subject exceeds maximum length"),
            (
                {"description": _over_limit(MAX_DESCRIPTION_LENGTH)},
                "Description exceeds maximum length",
            ),
            (
                {"context_notes": _over_limit(MAX_CONTEXT_NOTES_LENGTH)},
                "Context notes exceeds maximum length",
            ),
            ({"status": "invalid"}, "Invalid status"),
        ],
        ids=[
            "subject-too-long",
            "description-too-long",
            "context-notes-too-long",
            "invalid-status",
        ],
    )
    def test_rejects_invalid_fields(self, tmp_path: Path, kwargs: dict[str, str], error_match: str):
        """update_task should reject invalid lengths and statuses."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )

        with pytest.raises(ValueError, match=error_match):
            update_task(tmp_path, result["slug"], task_id=1, **kwargs)

    def test_accepts_fields_at_max_length(self, tmp_path: Path):
        """Boundary-length updates should be accepted unchanged."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )

        update_task(
            tmp_path,
            result["slug"],
            task_id=1,
            subject="s" * MAX_SUBJECT_LENGTH,
            description="d" * MAX_DESCRIPTION_LENGTH,
            context_notes="c" * MAX_CONTEXT_NOTES_LENGTH,
            status="blocked",
        )

        task = list_tasks(tmp_path, result["slug"])[0]
        assert len(task["subject"]) == MAX_SUBJECT_LENGTH
        assert len(task["description"]) == MAX_DESCRIPTION_LENGTH
        assert len(task["context_notes"]) == MAX_CONTEXT_NOTES_LENGTH
        assert task["status"] == "blocked"


class TestRemoveTask:
    def test_marks_as_deleted(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        remove_task(tmp_path, result["slug"], task_id=1)
        tasks = list_tasks(tmp_path, result["slug"])
        assert len(tasks) == 0  # deleted tasks excluded from list


class TestClaimTask:
    def test_claims_pending_task(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="agent-x")
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["status"] == "in_progress"
        assert tasks[0]["owner"] == "agent-x"

    def test_claim_already_in_progress_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="agent-x")
        with pytest.raises(ValueError, match="is 'in_progress'"):
            claim_task(tmp_path, result["slug"], task_id=1, owner="agent-y")

    def test_claim_nonexistent_task_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
        )
        with pytest.raises(TaskNotFoundError, match="does not exist"):
            claim_task(tmp_path, result["slug"], task_id=999, owner="agent-x")


class TestCompleteTask:
    def test_completes_in_progress_task(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="agent-x")
        complete_task(tmp_path, result["slug"], task_id=1)
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["status"] == "completed"

    def test_complete_pending_task_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        # never-claimed task is non-terminal with no caller identity ⇒ the
        # dispatcher falls through to TaskStateError (unexpected state)
        with pytest.raises(TaskStateError, match="not 'in_progress'"):
            complete_task(tmp_path, result["slug"], task_id=1)


# ── v2 worker-registration + CAS-guard behavior ─────────────────────────


class TestClaimRegistersWorker:
    def test_worker_label_creates_registration(self, tmp_path: Path):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1,
                   owner="claude-code:worker-1:42")

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            row = conn.execute(
                "SELECT agent_type, role FROM registrations WHERE agent_id = ?",
                ("claude-code:worker-1:42",),
            ).fetchone()
        assert row is not None
        assert row["agent_type"] == "claude-code"
        assert row["role"] == "worker"

    def test_worker_registration_is_idempotent_on_repeat_claims(
        self, tmp_path: Path
    ):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}, {"subject": "B"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)
        complete_task(tmp_path, result["slug"], task_id=1)
        # second claim for the same worker must not raise on UNIQUE
        claim_task(tmp_path, result["slug"], task_id=2, owner=worker)

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            rows = conn.execute(
                "SELECT COUNT(*) AS n FROM registrations WHERE agent_id = ?",
                (worker,),
            ).fetchone()
        assert rows["n"] == 1

    def test_bare_type_owner_does_not_register(self, tmp_path: Path):
        """Orchestrator (no ':') bypasses the worker-registration path."""
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="claude-code")

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM registrations").fetchone()["n"]
        assert n == 0


class TestCompleteDeregistersWorker:
    def test_complete_with_worker_agent_deregisters(self, tmp_path: Path):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)
        complete_task(tmp_path, result["slug"], task_id=1, agent=worker)

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM registrations WHERE agent_id = ?",
                (worker,),
            ).fetchone()["n"]
        assert n == 0

    def test_complete_without_agent_leaves_registration(self, tmp_path: Path):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)
        complete_task(tmp_path, result["slug"], task_id=1)  # no --agent

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM registrations WHERE agent_id = ?",
                (worker,),
            ).fetchone()["n"]
        assert n == 1

    def test_complete_with_remaining_tasks_keeps_worker(self, tmp_path: Path):
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}, {"subject": "B"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)
        claim_task(tmp_path, result["slug"], task_id=2, owner=worker)

        complete_task(tmp_path, result["slug"], task_id=1, agent=worker)

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM registrations WHERE agent_id = ?",
                (worker,),
            ).fetchone()["n"]
        # registration preserved — worker still owns task 2
        assert n == 1


class TestUpdateTaskCasGuard:
    def test_reassign_rejects_already_completed_task(self, tmp_path: Path):
        """CAS guard prevents a blind UPDATE from reverting a completed task."""
        from operations.dossiers.tasks import update_task

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)
        complete_task(tmp_path, result["slug"], task_id=1, agent=worker)

        # terminal status takes precedence over the (now-deregistered) worker's
        # missing registration: "already completed", not "reaped"
        with pytest.raises(TaskAlreadyCompletedError, match="already completed"):
            update_task(
                tmp_path, result["slug"], task_id=1,
                status="pending", owner="",
                agent="claude-code:orch-hex",
            )

    def test_reassign_succeeds_on_in_progress_task(self, tmp_path: Path):
        from operations.dossiers.tasks import update_task

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)

        update_task(
            tmp_path, result["slug"], task_id=1,
            status="pending", owner="",
            agent="claude-code:orch-hex",
        )

        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["status"] == "pending"
        assert tasks[0]["owner"] is None

    def test_unguarded_update_without_agent_still_works(self, tmp_path: Path):
        """Manual CLI repair (no --agent) stays unguarded — escape hatch."""
        from operations.dossiers.tasks import update_task

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="claude-code:worker-1:42")
        complete_task(tmp_path, result["slug"], task_id=1)

        update_task(tmp_path, result["slug"], task_id=1, status="pending")
        tasks = list_tasks(tmp_path, result["slug"])
        assert tasks[0]["status"] == "pending"

    def test_blocked_transition_deregisters_worker(self, tmp_path: Path):
        from operations.dossiers.db import open_dossier_db, safe_db_path
        from operations.dossiers.tasks import update_task

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)

        update_task(
            tmp_path, result["slug"], task_id=1,
            status="blocked", agent=worker,
        )

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM registrations WHERE agent_id = ?",
                (worker,),
            ).fetchone()["n"]
        assert n == 0


# ── Mechanism 2: rich CAS failure dispatch + C2 atomicity ───────────────────


class TestRichCasErrors:
    """A failed in_progress CAS is diagnosed into one of five specific causes
    (`_raise_task_cas_failure`), not a single opaque 'not in progress'."""

    def test_complete_nonexistent_raises_not_found(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
        )
        with pytest.raises(TaskNotFoundError, match="does not exist"):
            complete_task(tmp_path, result["slug"], task_id=999)

    def test_complete_already_completed_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="agent-x")
        complete_task(tmp_path, result["slug"], task_id=1)
        with pytest.raises(TaskAlreadyCompletedError, match="already completed"):
            complete_task(tmp_path, result["slug"], task_id=1)

    def test_deleted_task_takes_precedence_over_missing_registration(
        self, tmp_path: Path
    ):
        """Terminal 'deleted' is reported even when the caller is unregistered —
        deleted wins over the reaped-identity branch (the ordering deviation)."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="agent-x")
        remove_task(tmp_path, result["slug"], task_id=1)  # soft-delete
        # 'agent-x' is a bare id (never registered); deleted-check fires first
        with pytest.raises(TaskDeletedError, match="soft-deleted"):
            complete_task(tmp_path, result["slug"], task_id=1, agent="agent-x")

    def test_reaped_identity_raises_with_reap_log_context(self, tmp_path: Path):
        """Registration gone + task reverted to a non-terminal state ⇒
        IdentityReapedError, surfacing the reap_log reason."""
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        worker = "claude-code:worker-1:42"
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)

        # simulate a primary-defense reap: delete the registration, revert the
        # in-progress task to pending, and write the audit row cleanup would
        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            with conn:
                conn.execute("DELETE FROM registrations WHERE agent_id = ?", (worker,))
                conn.execute(
                    "UPDATE tasks SET status = 'pending', owner = NULL WHERE id = 1"
                )
                conn.execute(
                    "INSERT INTO reap_log (reaped_at, agent_id, agent_type, role, "
                    "last_heartbeat, stale_by_sec, tasks_reverted, lock_released, "
                    "reap_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ("2026-06-07T00:00:00Z", worker, "claude-code", "worker",
                     "2026-06-06T00:00:00Z", 7200, "[1]", 0, "pid_dead"),
                )

        with pytest.raises(IdentityReapedError, match="pid_dead") as exc:
            complete_task(tmp_path, result["slug"], task_id=1, agent=worker)
        # the remediation hint and the gone-registration are both surfaced
        assert "reverted" in str(exc.value)
        assert worker in str(exc.value)

    def test_non_terminal_state_with_live_registration_raises_state_error(
        self, tmp_path: Path
    ):
        """Registration intact + task not in a terminal/in-progress state ⇒
        the 'should never happen' TaskStateError, not a reap."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "owned"}, {"subject": "pending"}],
        )
        worker = "claude-code:worker-1:42"
        # claim task 1 so `worker` is registered (and stays live); task 2 is pending
        claim_task(tmp_path, result["slug"], task_id=1, owner=worker)
        with pytest.raises(TaskStateError, match="invariant"):
            complete_task(tmp_path, result["slug"], task_id=2, agent=worker)

    def test_failed_claim_rolls_back_speculative_worker_registration(
        self, tmp_path: Path
    ):
        """C2: register-then-claim is atomic. A claim that loses the CAS must not
        leave a worker registration behind."""
        from operations.dossiers.db import open_dossier_db, safe_db_path

        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A"}],
        )
        holder = "claude-code:worker-1:1"
        contender = "claude-code:worker-2:2"
        claim_task(tmp_path, result["slug"], task_id=1, owner=holder)

        with pytest.raises(ValueError, match="in_progress"):
            claim_task(tmp_path, result["slug"], task_id=1, owner=contender)

        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            ids = {
                r["agent_id"] for r in conn.execute(
                    "SELECT agent_id FROM registrations"
                ).fetchall()
            }
        assert holder in ids          # the winner stays registered
        assert contender not in ids   # the loser's register rolled back


class TestWorkerRegistrationPid:
    """reg-A half 1: a worker's registration must carry a real ancestor pid.

    `claim_task` inserted workers with `cli_pid = None`, so the reap's liveness
    filter had nothing to ask and fell through to reaping on age alone.
    """

    def test_claim_registers_worker_with_the_cli_pid(self, tmp_path: Path, mock_cli_pid):
        mock_cli_pid(4242)
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="claude-code:worker-1:42")
        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            row = conn.execute(
                "SELECT role, cli_pid FROM registrations WHERE agent_id = ?",
                ("claude-code:worker-1:42",),
            ).fetchone()
        assert row["role"] == "worker"
        assert row["cli_pid"] == 4242

    def test_bare_owner_registers_nothing(self, tmp_path: Path, mock_cli_pid):
        # unchanged: only labelled owners (with ':') get a speculative worker row
        mock_cli_pid(4242)
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "A", "status": "pending"}],
        )
        claim_task(tmp_path, result["slug"], task_id=1, owner="agent-x")
        with open_dossier_db(safe_db_path(tmp_path, result["slug"])) as conn:
            rows = conn.execute("SELECT * FROM registrations").fetchall()
        assert rows == []
