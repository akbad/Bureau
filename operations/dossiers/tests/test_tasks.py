"""Tests for dossier task CRUD operations."""
from pathlib import Path

import pytest

from operations.dossiers.db import (
    MAX_CONTEXT_NOTES_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_SUBJECT_LENGTH,
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
        with pytest.raises(ValueError, match="not pending"):
            claim_task(tmp_path, result["slug"], task_id=1, owner="agent-y")

    def test_claim_nonexistent_task_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
        )
        with pytest.raises(ValueError, match="not pending"):
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
        with pytest.raises(ValueError, match="not in progress"):
            complete_task(tmp_path, result["slug"], task_id=1)
