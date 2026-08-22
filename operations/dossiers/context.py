"""Task-scoped context extraction for worker agents.

Assembles the subset of a dossier relevant to a specific task: dossier
header, target task details, transitive dependency chain, live pinned
findings, all decisions, latest-session file interactions, sibling task
summaries, and (optionally) the latest session digest.

Design choice: fixed context slice with optional annotations (Approach C
from the spec).  Decisions and file interactions are included
unconditionally because they are compact and filtering risks omitting a
constraint the worker needs.  The session digest is opt-in because it is
large (~3-10 KB) and mostly contains orchestrator-level narrative.
"""
import json
import sqlite3
from pathlib import Path
from typing import Any

from .db import LIVE_FINDING_PREDICATE, escape_md, open_dossier_db, safe_db_path
from .errors import DossierNotFoundError
from .findings import render_findings


# ─────────────────────────────────────────────────────────────────────
# Dependency chain resolution
# ─────────────────────────────────────────────────────────────────────

# depth cap prevents token-budget exhaustion on long chains
MAX_DEPENDENCY_DEPTH = 3


def _resolve_dependency_chain(
    conn: sqlite3.Connection,
    task: sqlite3.Row,
    max_depth: int = MAX_DEPENDENCY_DEPTH,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Walk the blocked_by chain transitively, returning (deps, warnings).

    Each dependency is a dict with id/subject/status/owner.
    Warnings capture malformed references, dangling IDs, and cycles.

    Cycle detection: track visited task IDs; break and warn on revisit.
    Depth cap: stop after ``max_depth`` hops and note truncation.
    """
    deps: list[dict[str, Any]] = []
    warnings: list[str] = []
    visited: set[int] = {task["id"]}
    total_ancestors = 0  # track how many exist beyond the cap

    current = task
    depth = 0

    while depth < max_depth:
        blocked_by_raw = current["blocked_by"]
        if not blocked_by_raw or not str(blocked_by_raw).strip():
            break

        raw = str(blocked_by_raw).strip()
        try:
            ref_id = int(raw)
        except ValueError:
            warnings.append(
                f'blocked_by value "{raw}" on task #{current["id"]} '
                f"is not a valid task ID — skipping dependency resolution"
            )
            break

        if ref_id in visited:
            # cycle detected — include what we have and warn
            cycle_ids = [str(d["id"]) for d in deps] + [str(ref_id)]
            warnings.append(
                f"Circular dependency detected in chain involving tasks "
                f"#{', #'.join(cycle_ids)}"
            )
            break

        visited.add(ref_id)

        row = conn.execute(
            "SELECT id, subject, description, status, owner, blocked_by "
            "FROM tasks WHERE id = ?",
            (ref_id,),
        ).fetchone()

        if not row:
            warnings.append(
                f"task #{current['id']} references blocked_by #{ref_id} "
                f"which does not exist"
            )
            break

        deps.append({
            "id": row["id"],
            "subject": row["subject"],
            "status": row["status"],
            "owner": row["owner"],
        })
        depth += 1
        current = row

    # detect whether the chain continues beyond max_depth
    if depth == max_depth and current["blocked_by"]:
        # count remaining ancestors (approximate via continued walk)
        remaining = current
        extra = 0
        seen = set(visited)
        while remaining["blocked_by"]:
            raw = str(remaining["blocked_by"]).strip()
            try:
                nxt_id = int(raw)
            except ValueError:
                break
            if nxt_id in seen:
                break
            seen.add(nxt_id)
            nxt = conn.execute(
                "SELECT id, blocked_by FROM tasks WHERE id = ?", (nxt_id,)
            ).fetchone()
            if not nxt:
                break
            extra += 1
            remaining = nxt
        if extra > 0:
            total_ancestors = depth + extra
            warnings.append(
                f"Showing {depth} of {total_ancestors} dependencies "
                f"(truncated at depth {max_depth})"
            )

    return deps, warnings


# ─────────────────────────────────────────────────────────────────────
# Context extraction
# ─────────────────────────────────────────────────────────────────────

def extract_task_context(
    dossiers_dir: Path,
    slug: str,
    task_id: int,
    include_digest: bool = False,
) -> str:
    """Query the dossier DB and render task-scoped context as markdown.

    Raises DossierNotFoundError if the dossier does not exist.
    Raises ValueError if the task ID is not found.

    The output follows the spec's "context command output" format:
    header, target task, dependency chain, decisions, file interactions,
    sibling tasks, and (optionally) the latest session digest.
    """
    db_path = safe_db_path(dossiers_dir, slug)
    if not db_path.exists():
        raise DossierNotFoundError(f"No dossier found matching: {slug}")

    with open_dossier_db(db_path) as conn:
        meta = conn.execute("SELECT * FROM metadata").fetchone()
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND status != 'deleted'",
            (task_id,),
        ).fetchone()

        if not task:
            raise ValueError(
                f'Task #{task_id} does not exist in dossier "{slug}"'
            )

        # resolve transitive dependency chain
        deps, dep_warnings = _resolve_dependency_chain(conn, task)

        # Live pinned findings. Never windowed and never session-scoped: a
        # worker inherits every decision already, so withholding the dead ends
        # would hand it the record of what was chosen and none of the walls.
        findings = conn.execute(
            "SELECT hash, kind, text, why_abandoned, retry, 1 AS is_live "
            f"FROM pinned_findings WHERE {LIVE_FINDING_PREDICATE} "
            "ORDER BY created_at, rowid"
        ).fetchall()

        # all decisions (durable constraints)
        decisions = conn.execute(
            "SELECT * FROM decisions ORDER BY id"
        ).fetchall()

        # file interactions from the latest session only
        latest_session = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        file_interactions = []
        if latest_session:
            file_interactions = conn.execute(
                "SELECT file_path, action, annotation "
                "FROM file_interactions WHERE session_id = ? ORDER BY id",
                (latest_session["id"],),
            ).fetchall()

        # sibling tasks (all non-deleted tasks except the target)
        siblings = conn.execute(
            "SELECT id, subject, status FROM tasks "
            "WHERE status != 'deleted' AND id != ? ORDER BY id",
            (task_id,),
        ).fetchall()

    return _render_task_context(
        meta=meta,
        task=task,
        deps=deps,
        dep_warnings=dep_warnings,
        findings=findings,
        decisions=decisions,
        file_interactions=file_interactions,
        siblings=siblings,
        latest_session=latest_session if include_digest else None,
    )


def _render_task_context(
    *,
    meta: sqlite3.Row,
    task: sqlite3.Row,
    deps: list[dict[str, Any]],
    dep_warnings: list[str],
    findings: list[sqlite3.Row],
    decisions: list[sqlite3.Row],
    file_interactions: list[sqlite3.Row],
    siblings: list[sqlite3.Row],
    latest_session: sqlite3.Row | None,
) -> str:
    """Render extracted context as the spec's markdown format."""
    lines: list[str] = []

    # ── Title + dossier header ──
    lines.append(f"# Task Context: {task['subject']}")
    lines.append("")
    lines.append(
        f"**Dossier:** `{meta['name']}` (`{meta['hash']}`) | "
        f"**Branch:** `{meta['branch']}` | "
        f"**Project:** `{meta['project']}`"
    )
    lines.append("")

    # ── Target task detail table ──
    lines.append("## Your task")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| ID | {task['id']} |")
    lines.append(f"| Subject | {escape_md(task['subject'])} |")
    lines.append(f"| Status | {task['status']} |")
    lines.append(f"| Owner | {escape_md(task['owner']) if task['owner'] else 'unassigned'} |")
    lines.append(f"| Blocked by | {escape_md(task['blocked_by']) if task['blocked_by'] else 'none'} |")
    lines.append("")

    if task["description"]:
        lines.append(escape_md(task["description"]))
        lines.append("")

    # context_notes — present only when the column exists and is populated
    context_notes = None
    try:
        context_notes = task["context_notes"]
    except (IndexError, KeyError):
        pass  # column does not exist in older schema
    if context_notes:
        lines.append(f"**Context notes:** {escape_md(context_notes)}")
        lines.append("")

    # ── Dependencies ──
    lines.append("## Dependencies")
    lines.append("")

    for w in dep_warnings:
        lines.append(f"*Warning: {w}*")
        lines.append("")

    if deps:
        lines.append(
            "These tasks were completed before yours and inform your work:"
        )
        lines.append("")
        lines.append("| ID | Subject | Status | Owner |")
        lines.append("|----|---------|--------|-------|")
        for d in deps:
            lines.append(
                f"| {d['id']} | {escape_md(d['subject'])} | {d['status']} | "
                f"{escape_md(d['owner']) if d['owner'] else 'unassigned'} |"
            )
    else:
        if not dep_warnings:
            lines.append("This task has no dependencies.")
    lines.append("")

    # ── Pinned findings ──
    # Rendered through the same grammar `unfold` uses, so a worker and an
    # orchestrator read a constraint in exactly one shape — and so a finding
    # quoted back from either surface re-hashes to the same identity. Silent
    # when there are none: unlike decisions, an absent constraint set is not
    # a fact worth a line.
    lines.extend(render_findings(findings))

    # ── Decisions ──
    lines.append("## Decisions")
    lines.append("")
    if decisions:
        lines.append(
            "All architectural decisions for this dossier. "
            "Follow these constraints:"
        )
        lines.append("")
        for d in decisions:
            alt_text = ""
            if d["alternatives"]:
                try:
                    alts = json.loads(d["alternatives"])
                    if isinstance(alts, list):
                        alt_text = (
                            f" *(rejected: {', '.join(escape_md(str(a)) for a in alts)})*"
                        )
                    else:
                        alt_text = f" *(rejected: {escape_md(d['alternatives'])})*"
                except (json.JSONDecodeError, TypeError):
                    alt_text = f" *(rejected: {escape_md(d['alternatives'])})*"
            decided_by = escape_md(d["decided_by"]) if d["decided_by"] else "unknown"
            lines.append(
                f"- **{escape_md(d['what'])}**: {escape_md(d['why'])}{alt_text} "
                f"*(decided by: {decided_by})*"
            )
    else:
        lines.append("No decisions recorded.")
    lines.append("")

    # ── File interactions (latest session) ──
    lines.append("## Key files")
    lines.append("")
    if file_interactions:
        lines.append("| File | Action | Annotation |")
        lines.append("|------|--------|------------|")
        for fi in file_interactions:
            annotation = escape_md(fi["annotation"]) if fi["annotation"] else "\u2014"
            lines.append(
                f"| `{escape_md(fi['file_path'])}` | {escape_md(fi['action'])} | "
                f"{annotation} |"
            )
    else:
        lines.append("No file interactions recorded.")
    lines.append("")

    # ── Sibling tasks ──
    lines.append("## Other tasks in this dossier")
    lines.append("")
    if siblings:
        lines.append("| ID | Subject | Status |")
        lines.append("|----|---------|--------|")
        for s in siblings:
            lines.append(f"| {s['id']} | {escape_md(s['subject'])} | {s['status']} |")
    else:
        lines.append("No other tasks.")
    lines.append("")

    # ── Optional: session digest ──
    if latest_session:
        lines.append("## Session context")
        lines.append("")
        lines.append(
            f"*Folded at {latest_session['folded_at']} "
            f"by {latest_session['agent']}*"
        )
        lines.append("")
        lines.append(latest_session["digest"])
        lines.append("")

    return "\n".join(lines)
