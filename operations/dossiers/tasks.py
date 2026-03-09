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
