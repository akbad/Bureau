"""Task CRUD operations for dossier task lists."""
from pathlib import Path
from typing import Any

from .db import (
    open_dossier_db, safe_db_path,
    MAX_SUBJECT_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_CONTEXT_NOTES_LENGTH,
    VALID_STATUSES,
)
from .fold import _now_iso

# nullable fields where passing "" means "clear to NULL";
# non-nullable fields (subject, status) ignore empty strings to avoid
# violating SQLite NOT NULL constraints
CLEARABLE_FIELDS = {"description", "owner", "blocked_by", "context_notes"}


def list_tasks(dossiers_dir: Path, slug: str) -> list[dict[str, Any]]:
    """List all non-deleted tasks for a dossier."""
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        rows = conn.execute(
            "SELECT id, subject, description, status, owner, blocked_by, "
            "context_notes, created_at, updated_at "
            "FROM tasks WHERE status != 'deleted' ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def _validate_task_fields(
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    context_notes: str | None = None,
) -> None:
    """Validate task field lengths and status values.

    Fields are only checked when non-None and not the empty-string
    clear sentinel (empty string on clearable fields means "set to NULL").
    """
    if subject is not None and subject != "" and len(subject) > MAX_SUBJECT_LENGTH:
        raise ValueError(f"Subject exceeds maximum length ({MAX_SUBJECT_LENGTH} chars)")
    if description is not None and description != "" and len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"Description exceeds maximum length ({MAX_DESCRIPTION_LENGTH} chars)")
    if context_notes is not None and context_notes != "" and len(context_notes) > MAX_CONTEXT_NOTES_LENGTH:
        raise ValueError(f"Context notes exceeds maximum length ({MAX_CONTEXT_NOTES_LENGTH} chars)")
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_STATUSES))}")


def add_task(
    dossiers_dir: Path,
    slug: str,
    subject: str,
    description: str | None = None,
    status: str = "pending",
    owner: str | None = None,
    blocked_by: str | None = None,
    context_notes: str | None = None,
) -> int:
    """Add a new task. Returns the task ID."""
    _validate_task_fields(
        subject=subject, description=description,
        status=status, context_notes=context_notes,
    )
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            now = _now_iso()
            cursor = conn.execute(
                "INSERT INTO tasks (subject, description, status, owner, blocked_by, "
                "context_notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (subject, description, status, owner, blocked_by, context_notes, now, now),
            )
            task_id = cursor.lastrowid
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
    context_notes: str | None = None,
) -> None:
    """Update fields on an existing task. Raises ValueError if not found."""
    _validate_task_fields(
        subject=subject, description=description,
        status=status, context_notes=context_notes,
    )
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            raise ValueError(f"Task {task_id} not found in dossier {slug}")

        updates = []
        values = []
        for field, value in [
            ("subject", subject), ("description", description),
            ("status", status), ("owner", owner), ("blocked_by", blocked_by),
            ("context_notes", context_notes),
        ]:
            if value is not None:
                # empty string on clearable fields = explicit clear (set to NULL)
                if value == "" and field in CLEARABLE_FIELDS:
                    updates.append(f"{field} = ?")
                    values.append(None)
                elif value == "":
                    continue  # ignore empty string on non-nullable fields
                else:
                    updates.append(f"{field} = ?")
                    values.append(value)

        if updates:
            with conn:  # transaction boundary
                updates.append("updated_at = ?")
                values.append(_now_iso())
                values.append(task_id)
                conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values)


def remove_task(dossiers_dir: Path, slug: str, task_id: int) -> None:
    """Soft-delete a task by setting status to 'deleted'."""
    update_task(dossiers_dir, slug, task_id, status="deleted")


def claim_task(dossiers_dir: Path, slug: str, task_id: int, owner: str) -> None:
    """Atomically claim a pending task (CAS: pending -> in_progress).

    Raises ValueError if the task is not pending (already claimed, completed, deleted, or nonexistent).
    """
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            now = _now_iso()
            cursor = conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ?, updated_at = ? "
                "WHERE id = ? AND status = 'pending'",
                (owner, now, task_id),
            )
            affected = cursor.rowcount
    if affected == 0:
        raise ValueError(
            f"Task {task_id} cannot be claimed: it is not pending "
            f"(may not exist, or is already in progress / completed / deleted)"
        )


def complete_task(dossiers_dir: Path, slug: str, task_id: int) -> None:
    """Atomically complete an in-progress task (CAS: in_progress -> completed).

    Raises ValueError if the task is not in progress.
    """
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            now = _now_iso()
            cursor = conn.execute(
                "UPDATE tasks SET status = 'completed', updated_at = ? "
                "WHERE id = ? AND status = 'in_progress'",
                (now, task_id),
            )
            affected = cursor.rowcount
    if affected == 0:
        raise ValueError(
            f"Task {task_id} cannot be completed: it is not in progress "
            f"(may not exist, or is still pending / already completed / deleted)"
        )
