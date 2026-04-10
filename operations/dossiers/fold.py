"""Fold operation: create or update a dossier."""
import json
import os
import re
from pathlib import Path
from typing import Any

from .db import create_dossier_db, open_dossier_db, safe_db_path, _now_iso, MAX_DIGEST_LENGTH, MAX_TASKS_PER_DOSSIER
from .tasks import _validate_task_fields


def _generate_hash() -> str:
    """Generate a 6-character hex hash."""
    return os.urandom(3).hex()


def _slugify(name: str) -> str:
    """Convert name to lowercase kebab-case slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        slug = "dossier"
    return slug


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
    max_retained_sessions: int = 5,
) -> dict[str, str]:
    """Create a new dossier or append a session to an existing one.

    For new dossiers: provide `name`. A hash and slug are generated.
    For existing dossiers: provide `slug`. A new session is appended.

    Returns dict with 'slug' and 'hash' keys.
    """
    # validate inputs before any side effects
    if len(digest) > MAX_DIGEST_LENGTH:
        raise ValueError(f"Digest exceeds maximum length ({MAX_DIGEST_LENGTH} chars)")
    if tasks and len(tasks) > MAX_TASKS_PER_DOSSIER:
        raise ValueError(f"Task list exceeds maximum count ({MAX_TASKS_PER_DOSSIER} tasks)")

    now = _now_iso()
    is_refold = bool(slug)

    if slug:
        # Re-fold: append to existing dossier
        db_path = safe_db_path(dossiers_dir, slug)
    else:
        # New fold: create dossier
        if not name:
            raise ValueError("Either 'name' (new dossier) or 'slug' (existing) is required")
        # collision-safe: retry until we find an unused slug
        while True:
            dossier_hash = _generate_hash()
            slug = f"{_slugify(name)}-{dossier_hash}"
            db_path = dossiers_dir / f"{slug}.db"
            if not db_path.exists():
                break

        create_dossier_db(db_path)

    with open_dossier_db(db_path) as conn:
        with conn:  # transaction: auto-commit on success, rollback on exception
            if is_refold:
                meta = conn.execute("SELECT hash FROM metadata").fetchone()
                dossier_hash = meta["hash"]

                conn.execute(
                    "UPDATE metadata SET updated_at = ?, agent = ?, branch = ?, commit_hash = ?",
                    (now, agent, branch, commit_hash),
                )
            else:
                conn.execute(
                    """INSERT INTO metadata
                       (id, hash, name, slug, created_at, updated_at, agent, project, branch, commit_hash, parent, locked_by, locked_at)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)""",
                    (dossier_hash, name, slug, now, now, agent, project, branch, commit_hash),
                )

            # Insert session
            cursor = conn.execute(
                "INSERT INTO sessions (folded_at, agent, branch, commit_hash, digest) VALUES (?, ?, ?, ?, ?)",
                (now, agent, branch, commit_hash, digest),
            )
            session_id = cursor.lastrowid

            # Insert tasks (only on initial fold — re-fold manages tasks via CLI)
            if not is_refold:
                for task in (tasks or []):
                    status = task.get("status", "pending")
                    _validate_task_fields(
                        subject=task["subject"],
                        description=task.get("description"),
                        status=status,
                        context_notes=task.get("context_notes"),
                    )
                    conn.execute(
                        "INSERT INTO tasks (subject, description, status, owner, blocked_by, context_notes) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            task["subject"],
                            task.get("description"),
                            status,
                            task.get("owner"),
                            task.get("blocked_by"),
                            task.get("context_notes"),
                        ),
                    )

            # Insert decisions
            for decision in (decisions or []):
                # deduplicate: skip if an identical decision already exists
                existing = conn.execute(
                    "SELECT id FROM decisions WHERE what = ? AND why = ?",
                    (decision["what"], decision["why"]),
                ).fetchone()
                if existing:
                    continue
                alternatives = decision.get("alternatives")
                if alternatives is not None and not isinstance(alternatives, str):
                    alternatives = json.dumps(alternatives)
                conn.execute(
                    "INSERT INTO decisions (session_id, what, why, alternatives, decided_by) VALUES (?, ?, ?, ?, ?)",
                    (session_id, decision["what"], decision["why"], alternatives, decision.get("decided_by")),
                )

            # Insert file interactions
            for f in (files or []):
                conn.execute(
                    "INSERT INTO file_interactions (session_id, file_path, action, annotation) VALUES (?, ?, ?, ?)",
                    (session_id, f["path"], f["action"], f.get("annotation")),
                )

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

        # query actual DB counts so the caller reports what's in the dossier, not what was passed in
        # note: outside the transaction block since these are read-only
        task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status != 'deleted'").fetchone()[0]
        decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

    return {"slug": slug, "hash": dossier_hash, "task_count": task_count, "decision_count": decision_count}
