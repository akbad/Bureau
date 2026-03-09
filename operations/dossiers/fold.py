"""Fold operation: create or update a dossier."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import create_dossier_db, connect_dossier_db


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
) -> dict[str, str]:
    """Create a new dossier or append a session to an existing one.

    For new dossiers: provide `name`. A hash and slug are generated.
    For existing dossiers: provide `slug`. A new session is appended.

    Returns dict with 'slug' and 'hash' keys.
    """
    now = _now_iso()

    if slug:
        # Re-fold: append to existing dossier
        db_path = dossiers_dir / f"{slug}.db"
        conn = connect_dossier_db(db_path)
        meta = conn.execute("SELECT hash FROM metadata").fetchone()
        dossier_hash = meta["hash"]

        conn.execute(
            "UPDATE metadata SET updated_at = ?, agent = ?, branch = ?, commit_hash = ?",
            (now, agent, branch, commit_hash),
        )
    else:
        # New fold: create dossier
        if not name:
            raise ValueError("Either 'name' (new dossier) or 'slug' (existing) is required")
        dossier_hash = _generate_hash()
        slug = f"{_slugify(name)}-{dossier_hash}"
        db_path = dossiers_dir / f"{slug}.db"

        create_dossier_db(db_path)
        conn = connect_dossier_db(db_path)

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

    # Insert tasks
    for task in (tasks or []):
        conn.execute(
            "INSERT INTO tasks (subject, description, status, owner, blocked_by) VALUES (?, ?, ?, ?, ?)",
            (
                task["subject"],
                task.get("description"),
                task.get("status", "pending"),
                task.get("owner"),
                task.get("blocked_by"),
            ),
        )

    # Insert decisions
    for decision in (decisions or []):
        alternatives = decision.get("alternatives")
        if alternatives is not None and not isinstance(alternatives, str):
            alternatives = json.dumps(alternatives)
        conn.execute(
            "INSERT INTO decisions (session_id, what, why, alternatives, decided_by) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                decision["what"],
                decision["why"],
                alternatives,
                decision.get("decided_by"),
            ),
        )

    # Insert file interactions
    for f in (files or []):
        conn.execute(
            "INSERT INTO file_interactions (session_id, file_path, action, annotation) VALUES (?, ?, ?, ?)",
            (session_id, f["path"], f["action"], f.get("annotation")),
        )

    conn.commit()
    conn.close()

    return {"slug": slug, "hash": dossier_hash}
