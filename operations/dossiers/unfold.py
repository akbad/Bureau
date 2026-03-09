"""Unfold operation: render dossier for context injection."""
import sqlite3
from pathlib import Path
from typing import Any

from .db import connect_dossier_db


def find_dossier(dossiers_dir: Path, query: str) -> Path | None:
    """Find a dossier DB by hash or name substring.

    Priority: exact hash suffix > substring match.
    Raises ValueError if multiple matches at the same priority level.
    """
    if not dossiers_dir.exists():
        return None

    exact_matches = []
    substring_matches = []
    query_lower = query.lower()

    for db_file in sorted(dossiers_dir.glob("*.db")):
        slug = db_file.stem
        if slug.endswith(query):
            exact_matches.append(db_file)
        elif query_lower in slug.lower():
            substring_matches.append(db_file)

    # Priority: exact hash match > substring
    matches = exact_matches or substring_matches
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        slugs = [m.stem for m in matches]
        raise ValueError(f"Ambiguous query '{query}', matches: {', '.join(slugs)}")
    return None


def list_dossiers(dossiers_dir: Path) -> list[dict[str, Any]]:
    """List all dossiers with metadata, sorted by updated_at descending."""
    if not dossiers_dir.exists():
        return []

    results = []
    for db_file in dossiers_dir.glob("*.db"):
        try:
            conn = connect_dossier_db(db_file)
            meta = conn.execute("SELECT * FROM metadata").fetchone()
            task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            conn.close()
            if meta:
                results.append({
                    "slug": meta["slug"],
                    "hash": meta["hash"],
                    "name": meta["name"],
                    "updated_at": meta["updated_at"],
                    "project": meta["project"],
                    "branch": meta["branch"],
                    "locked_by": meta["locked_by"],
                    "tasks": task_count,
                    "sessions": session_count,
                })
        except (sqlite3.Error, FileNotFoundError):
            continue

    results.sort(key=lambda x: x["updated_at"], reverse=True)
    return results


def unfold_dossier(dossiers_dir: Path, query: str, max_sessions: int = 5) -> str:
    """Render a dossier as markdown for context injection.

    Finds the dossier by hash or name, reads all state, and returns
    a markdown string ready for injection into an agent's context.
    Only the last `max_sessions` session digests are rendered (all
    sessions are kept in storage).
    """
    db_path = find_dossier(dossiers_dir, query)
    if not db_path:
        raise FileNotFoundError(f"No dossier found matching: {query}")

    conn = connect_dossier_db(db_path)

    meta = conn.execute("SELECT * FROM metadata").fetchone()
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    sessions = conn.execute(
        "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (max_sessions,)
    ).fetchall()[::-1]  # reverse to chronological order
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE status != 'deleted' ORDER BY id"
    ).fetchall()
    decisions = conn.execute("SELECT * FROM decisions ORDER BY id").fetchall()

    conn.close()

    # Render markdown
    lines = []

    # Header
    lines.append(f"# Dossier: {meta['name']}")
    lines.append("")
    lines.append(f"**Hash:** `{meta['hash']}` | **Branch:** `{meta['branch']}` | "
                 f"**Commit:** `{meta['commit_hash']}` | **Project:** `{meta['project']}`")
    lines.append(f"**Updated:** {meta['updated_at']} | **Locked by:** {meta['locked_by'] or 'none'}")
    lines.append("")

    # Tasks
    if tasks:
        lines.append("## Tasks")
        lines.append("")
        lines.append("| ID | Subject | Status | Owner | Blocked by |")
        lines.append("|----|---------|--------|-------|------------|")
        for t in tasks:
            lines.append(
                f"| {t['id']} | {t['subject']} | {t['status']} | "
                f"{t['owner'] or '—'} | {t['blocked_by'] or '—'} |"
            )
        lines.append("")

    # Decisions (all — decisions are durable architectural choices)
    if decisions:
        lines.append("## Decisions")
        lines.append("")
        for d in decisions:
            lines.append(f"- **{d['what']}**: {d['why']} *(decided by: {d['decided_by']})*")
        lines.append("")

    # Session digests (capped)
    if total_sessions > len(sessions):
        lines.append(f"## Session digests (showing {len(sessions)} of {total_sessions})")
    else:
        lines.append("## Session digests")
    lines.append("")
    for s in sessions:
        lines.append(f"### Session {s['id']} ({s['folded_at']}, {s['agent']})")
        lines.append("")
        lines.append(s["digest"])
        lines.append("")

    return "\n".join(lines)
