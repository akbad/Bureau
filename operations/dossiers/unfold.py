"""Unfold operation: render dossier for context injection."""
import json
import sqlite3
from pathlib import Path
from typing import Any

from .db import escape_md, open_dossier_db
from .errors import AmbiguousQueryError, DossierNotFoundError


def find_dossier(dossiers_dir: Path, query: str) -> Path:
    """Find a dossier DB by hash, slug, or name substring.

    Priority: exact hash suffix > substring match.
    Raises AmbiguousQueryError if multiple matches at the same priority level.
    Raises DossierNotFoundError if no match.
    """
    if not dossiers_dir.exists():
        raise DossierNotFoundError(f"No dossier found matching: {query}")

    exact_matches = []
    substring_matches = []
    query_lower = query.lower()

    for db_file in sorted(dossiers_dir.glob("*.db")):
        slug = db_file.stem
        if slug.endswith(query_lower):
            exact_matches.append(db_file)
        elif query_lower in slug.lower():
            substring_matches.append(db_file)

    # Priority: exact hash match > substring
    matches = exact_matches or substring_matches
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        slugs = [m.stem for m in matches]
        raise AmbiguousQueryError(f"Ambiguous query '{query}', matches: {', '.join(slugs)}")
    raise DossierNotFoundError(f"No dossier found matching: {query}")


def list_dossiers(dossiers_dir: Path) -> list[dict[str, Any]]:
    """List all dossiers with metadata, sorted by updated_at descending."""
    if not dossiers_dir.exists():
        return []

    results = []
    for db_file in dossiers_dir.glob("*.db"):
        try:
            with open_dossier_db(db_file) as conn:
                meta = conn.execute("SELECT * FROM metadata").fetchone()
                task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status != 'deleted'").fetchone()[0]
                session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
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


def unfold_dossier(dossiers_dir: Path, query: str, max_sessions: int = 5, full: bool = False) -> str:
    """Render a dossier as markdown for context injection.

    Finds the dossier by hash or name, reads all state, and returns
    a markdown string ready for injection into an agent's context.

    When ``full=False`` (default), session digests are omitted for a
    compact view.  When ``full=True``, the last ``max_sessions``
    session digests are rendered (all sessions are kept in storage).
    """
    db_path = find_dossier(dossiers_dir, query)

    with open_dossier_db(db_path) as conn:
        meta = conn.execute("SELECT * FROM metadata").fetchone()
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE status != 'deleted' ORDER BY id"
        ).fetchall()
        decisions = conn.execute("SELECT * FROM decisions ORDER BY id").fetchall()
        file_interactions = conn.execute(
            "SELECT fi.file_path, fi.action, fi.annotation, s.id as session_id "
            "FROM file_interactions fi "
            "JOIN sessions s ON fi.session_id = s.id "
            "ORDER BY s.id DESC, fi.id",
        ).fetchall()

        # always fetch latest session for compact resumption context (H1)
        latest_session = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if full:
            total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            sessions = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (max_sessions,)
            ).fetchall()[::-1]  # reverse to chronological order

    # Render markdown
    lines = []

    # Header
    lines.append(f"# Dossier: {meta['name']} (ID: {meta['hash']})")
    lines.append("")
    lines.append(f"**Slug:** `{meta['slug']}` | **Branch:** `{meta['branch']}` | "
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
                f"| {t['id']} | {escape_md(t['subject'])} | {t['status']} | "
                f"{escape_md(t['owner']) if t['owner'] else '—'} | "
                f"{escape_md(t['blocked_by']) if t['blocked_by'] else '—'} |"
            )
        lines.append("")

    # Decisions (all — decisions are durable architectural choices)
    if decisions:
        lines.append("## Decisions")
        lines.append("")
        for d in decisions:
            alt_text = ""
            if d["alternatives"]:
                try:
                    alts = json.loads(d["alternatives"])
                    if isinstance(alts, list):
                        alt_text = f" *(rejected: {', '.join(escape_md(str(a)) for a in alts)})*"
                    else:
                        alt_text = f" *(rejected: {escape_md(d['alternatives'])})*"
                except (json.JSONDecodeError, TypeError):
                    alt_text = f" *(rejected: {escape_md(d['alternatives'])})*"
            lines.append(
                f"- **{escape_md(d['what'])}**: {escape_md(d['why'])}{alt_text} "
                f"*(decided by: {escape_md(d['decided_by'])})*"
            )
        lines.append("")

    # File interactions (compact structured data — rendered in both modes)
    if file_interactions:
        lines.append("## File interactions")
        lines.append("")
        lines.append("| File | Action | Annotation |")
        lines.append("|------|--------|------------|")
        for fi in file_interactions:
            annotation = escape_md(fi["annotation"]) if fi["annotation"] else "\u2014"
            lines.append(
                f"| `{escape_md(fi['file_path'])}` | {escape_md(fi['action'])} | "
                f"{annotation} |"
            )
        lines.append("")

    # Latest session digest (always rendered — contains critical in-flight state)
    if latest_session:
        lines.append("## Latest session context")
        lines.append("")
        lines.append(f"*Folded at {latest_session['folded_at']} by {latest_session['agent']}*")
        lines.append("")
        lines.append(latest_session["digest"])
        lines.append("")

    # Older session digests (only in full mode, skip latest to avoid duplication)
    if full:
        # exclude the latest session already rendered above
        older_sessions = [s for s in sessions if s["id"] != latest_session["id"]] if latest_session else sessions
        if total_sessions > len(sessions):
            lines.append(f"## Session digests (showing {len(sessions)} of {total_sessions})")
        else:
            lines.append("## Session digests")
        lines.append("")
        for s in older_sessions:
            lines.append(f"### Session {s['id']} ({s['folded_at']}, {s['agent']})")
            lines.append("")
            lines.append(s["digest"])
            lines.append("")

    return "\n".join(lines)
