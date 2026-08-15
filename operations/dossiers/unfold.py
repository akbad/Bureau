"""Unfold operation: render dossier for context injection.

# Design rationale

Storage is complete; rendering is windowed; nothing is silently dropped. A
fold only ever appends, so every bound in this module is a *render* decision
that `--full` can lift, and each windowed section states what it hid.

Two rules shape the whole file:

  - **Recency for provenance, liveness for constraints.** Decisions, file
    interactions, and memory queries explain why the past happened; their
    value decays with age and hiding an old one costs a `--full`. Pinned
    findings *bind the present* — a `DO NOT RETRY` from session 1 can be the
    most important line in the output, and a hidden constraint is a dead end
    an agent re-explores. Findings are therefore filtered by liveness and
    never by recency; their growth control is the supersession lifecycle.
  - **The finding render adds no characters that need removing.** Its lines
    are the one part of this output an agent may quote *back* into a fold
    payload, and dedupe holds only if the text survives that trip
    byte-identical after normalization. The line grammar therefore lives in
    `findings.render_findings`, beside the hash it has to survive, and
    `context` renders through the same function.
"""
import json
import sqlite3
from pathlib import Path
from typing import Any

from .db import LIVE_FINDING_PREDICATE, escape_md, open_dossier_db
from .errors import AmbiguousQueryError, DossierNotFoundError
from .findings import render_findings

# ── Render windows and accounting ───────────────────────────────────────

# A negative LIMIT is SQLite's "no upper bound", so one query serves both the
# compact window and `--full`.
_UNBOUNDED = -1

# The one definition of "belongs to a recently-folded session", shared by
# every windowed table. Rows with no session (only reachable by hand-editing
# the database) always render: a resolution failure may leave the output
# showing too much, never silently too little.
_RECENT_SESSIONS = (
    "(session_id IS NULL "
    "OR session_id IN (SELECT id FROM sessions ORDER BY id DESC LIMIT ?))"
)

# Where the live-findings count stops being a memory and starts being silt.
# Assumed, not measured: findings render at roughly 200-400 bytes each, so 30
# is about 6-12 KB against the 44 KB of decision bloat that motivated the
# render windows — low enough to catch accumulation, high enough that the
# warning stays rare and therefore meaningful. Revisit with real data.
FINDINGS_HEALTH_THRESHOLD = 30

# The remedy each accounting line names. `--full` lifts most windows; it does
# not lift the session-digest cap, so that surface names the flag that does.
_FULL_REMEDY = "--full shows all"
_MAX_SESSIONS_REMEDY = "--max-sessions raises the cap"


def _findings_health_warning(live_count: int) -> list[str]:
    """Return the findings-section health line, or nothing.

    Not an omission notice — nothing in that section is ever hidden — but a
    smell detector with a remedy. Growth control for findings is the
    supersession lifecycle rather than a window, so the line names it.
    """
    if live_count <= FINDINGS_HEALTH_THRESHOLD:
        return []
    return [
        f"{live_count} live pinned findings; consolidate stale ones via supersedes.",
        "",
    ]


def _omission_footer(
    omitted: int, singular: str, plural: str, remedy: str = _FULL_REMEDY
) -> list[str]:
    """Return the accounting line for a windowed section, or nothing.

    One shared sentence shape across every section, and per-section rather
    than a single document footer: the agent decides "do I need more decision
    context?" while reading the decisions, not at the end of the document.

    Both noun forms are passed in because one of them ("memory query") does not
    pluralize by appending an `s`.

    Returns an empty list when the window hid nothing — a footer that fires on
    the everyday path is noise, and the real ones share its channel.
    """
    if omitted <= 0:
        return []
    noun = singular if omitted == 1 else plural
    return [f"{omitted} older {noun} omitted; {remedy}.", ""]


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

    The latest session's digest is rendered in **both** modes — it carries the
    in-flight state a resuming agent cannot do without. ``full`` widens the
    windowed surfaces around it:

      - **Older digests.** ``full=True`` additionally renders the sessions
        preceding the latest, up to ``max_sessions`` sessions in total.
      - **Decisions, file interactions and memory queries.** Compact mode
        windows each to the newest ``max_sessions`` sessions; ``full=True``
        renders every session's.
      - **Pinned findings.** Compact mode renders the live set — always all of
        it. ``full=True`` adds the retired rows (superseded findings and the
        tombstones that retired them) as archaeology.

    Storage is never the constraint: a fold only appends, so both modes read
    from a complete history and differ only in how much of it they render.
    """
    db_path = find_dossier(dossiers_dir, query)

    with open_dossier_db(db_path) as conn:
        meta = conn.execute("SELECT * FROM metadata").fetchone()
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE status != 'deleted' ORDER BY id"
        ).fetchall()

        # Every windowed table reads through the same predicate and the same
        # unbounded-LIMIT trick, so the four surfaces cannot drift apart.
        session_window = _UNBOUNDED if full else max_sessions
        decisions = conn.execute(
            f"SELECT * FROM decisions WHERE {_RECENT_SESSIONS} ORDER BY id",
            (session_window,),
        ).fetchall()
        file_interactions = conn.execute(
            "SELECT file_path, action, annotation, session_id FROM file_interactions "
            f"WHERE {_RECENT_SESSIONS} ORDER BY session_id DESC, id",
            (session_window,),
        ).fetchall()
        memory_queries = conn.execute(
            "SELECT tool, query, result_summary, used_for FROM memory_queries "
            f"WHERE {_RECENT_SESSIONS} ORDER BY session_id DESC, id",
            (session_window,),
        ).fetchall()
        omitted = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] - shown
            for table, shown in (
                ("decisions", len(decisions)),
                ("file_interactions", len(file_interactions)),
                ("memory_queries", len(memory_queries)),
            )
        }

        # Findings are constraints, not provenance: liveness filters them,
        # recency never does, and `--full` only adds the retired rows. Ordered
        # by insertion — payload order within a fold, fold order across them —
        # because hash order would scramble the sequence the agent wrote.
        live_only = "" if full else f"WHERE {LIVE_FINDING_PREDICATE} "
        findings = conn.execute(
            "SELECT hash, kind, text, why_abandoned, retry, "
            f"({LIVE_FINDING_PREDICATE}) AS is_live "
            f"FROM pinned_findings {live_only}ORDER BY created_at, rowid"
        ).fetchall()
        live_findings = sum(row["is_live"] for row in findings)

        # always fetch latest session for compact resumption context
        latest_session = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

        if full:
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

    # Pinned findings: hard constraints, rendered before the provenance
    # sections because a dead end an agent walks back into costs more than any
    # decision it re-reads. The line grammar lives in `findings` beside the
    # hash it has to survive a round trip against.
    lines.extend(render_findings(findings))
    lines.extend(_findings_health_warning(live_findings))

    # Decisions (windowed by session — provenance decays, constraints do not)
    #
    # `or omitted[...]` on every windowed section: when the window hides the
    # whole table, the section still renders its header and its accounting
    # line with no items. Dropping both would leave a populated table with
    # zero signal that it exists, which is how a settled decision gets
    # re-litigated. A table that is genuinely empty has nothing to account for
    # and stays silent.
    if decisions or omitted["decisions"]:
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
        if decisions:
            lines.append("")
        lines.extend(_omission_footer(omitted["decisions"], "decision", "decisions"))

    # File interactions (compact structured data — rendered in both modes)
    if file_interactions or omitted["file_interactions"]:
        lines.append("## File interactions")
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
            lines.append("")
        lines.extend(_omission_footer(
            omitted["file_interactions"], "file interaction", "file interactions",
        ))

    # Memory queries (a cache of what has already been looked up)
    if memory_queries or omitted["memory_queries"]:
        lines.append("## Memory queries")
        lines.append("")
        if memory_queries:
            lines.append("| Tool | Query | Result | Used for |")
            lines.append("|------|-------|--------|----------|")
            for mq in memory_queries:
                lines.append(
                    f"| {escape_md(mq['tool']) or '—'} | {escape_md(mq['query'])} | "
                    f"{escape_md(mq['result_summary']) or '—'} | "
                    f"{escape_md(mq['used_for']) or '—'} |"
                )
            lines.append("")
        lines.extend(_omission_footer(
            omitted["memory_queries"], "memory query", "memory queries",
        ))

    # Latest session digest (always rendered — contains critical in-flight state)
    if latest_session:
        lines.append("## Latest session context")
        lines.append("")
        lines.append(f"*Folded at {latest_session['folded_at']} by {latest_session['agent']}*")
        lines.append("")
        # The per-session scalars frame the digest rather than repeat it: mood
        # calibrates tone and `next_words` names the pending move, so both are
        # read before the narrative; `last_exchange` is bulk verbatim text and
        # follows it. Rendered unescaped, like the digest itself — they are
        # prose for a reader, not cells in a table.
        if latest_session["mood"]:
            lines.append(f"**Mood:** {latest_session['mood']}")
            lines.append("")
        if latest_session["next_words"]:
            lines.append(f"**Next words:** {latest_session['next_words']}")
            lines.append("")
        lines.append(latest_session["digest"])
        lines.append("")
        if latest_session["last_exchange"]:
            lines.append("### Last exchange")
            lines.append("")
            lines.append(latest_session["last_exchange"])
            lines.append("")

    if full:
        # Older session digests, skipping the latest already rendered above.
        older_sessions = [s for s in sessions if s["id"] != latest_session["id"]] if latest_session else sessions
        lines.append("## Session digests")
        lines.append("")
        for s in older_sessions:
            lines.append(f"### Session {s['id']} ({s['folded_at']}, {s['agent']})")
            lines.append("")
            lines.append(s["digest"])
            lines.append("")
        # `--full` does not lift this cap, so the footer names the flag that does
        lines.extend(_omission_footer(
            total_sessions - len(sessions), "session digest", "session digests",
            _MAX_SESSIONS_REMEDY,
        ))
    else:
        # Compact renders exactly one digest. `--full` is only the remedy when
        # it would show *all* the hidden ones — it does not lift the
        # `max_sessions` cap, so past that point the honest flag is the cap's.
        lines.extend(_omission_footer(
            total_sessions - 1, "session digest", "session digests",
            _FULL_REMEDY if max_sessions >= total_sessions else _MAX_SESSIONS_REMEDY,
        ))

    return "\n".join(lines)
