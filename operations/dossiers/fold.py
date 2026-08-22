"""Fold operation: create or update a dossier."""
import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from .db import (
    LIVE_FINDING_PREDICATE,
    MAX_DIGEST_LENGTH,
    MAX_TASKS_PER_DOSSIER,
    _now_iso,
    create_dossier_db,
    open_dossier_db,
    safe_db_path,
)
from .errors import ConcurrentInstanceError
from .findings import (
    HASH_PREFIX_LENGTH,
    canonical_element,
    finding_hash,
    finding_kind,
    short_hash,
)
from .identity import resolve_identity
from .lock import release_lock_on_conn
from .registration import deregister_agent
from .tasks import _validate_task_fields

_log = logging.getLogger(__name__)

# How a decisions row entered this dossier. Only one writer exists today; the
# column is a string rather than a flag so a future `merge` primitive can name
# itself without another migration.
_DECISION_SOURCE_FOLD = "fold"

# How much finding text a resolution-failure message quotes. Long enough to
# tell two candidates apart, short enough that a warning stays one line.
_CANDIDATE_TEXT_CHARS = 40

# ── Payload value typing ────────────────────────────────────────────────
# THE THREAT: these fields reach SQLite's parameter binder, which raises on
# any type it cannot store. Raising happens *inside* the fold transaction, so
# one malformed element rolls back the whole session — the digest included.
# Before v5 these keys were dropped wholesale and a bad value was harmless, so
# an unguarded write here would make the migration a regression.
#
# Two further reasons this is a rejection and never a coercion:
#
#   - `str(8780)` would store "8780" while the hash was computed over the
#     *number* 8780, so one value would carry two identities.
#   - a coerced value is a guess about what the agent meant, and a finding is
#     a constraint an agent will later act on.
_FINDING_STRING_FIELDS = ("finding", "why_abandoned", "retry")
_MEMORY_QUERY_STRING_FIELDS = ("query", "tool", "result_summary", "used_for")

_STRING_TYPE_REMEDY = "Re-fold with string values."
_FINDING_TYPE_REMEDY = "Re-fold with string values (and a true/false `dead_end`)."

# Enough of the offending value to recognize it, capped so a warning stays
# readable when an agent sends a whole nested object.
_VALUE_REPR_CHARS = 60


def _short_repr(value: Any) -> str:
    """Return a length-capped repr of a rejected payload value."""
    text = repr(value)
    return text if len(text) <= _VALUE_REPR_CHARS else text[:_VALUE_REPR_CHARS] + "..."


def _type_complaints(source: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    """Return one complaint per field holding neither a string nor null."""
    return [
        f"`{field}` must be a string, got {type(source[field]).__name__} "
        f"({_short_repr(source[field])})"
        for field in fields
        if source.get(field) is not None and not isinstance(source.get(field), str)
    ]


def _checked_scalar(value: Any, field: str) -> str | None:
    """Return a per-session scalar, or None (with a warning) if it is not text."""
    if value is None or isinstance(value, str):
        return value
    _log.warning(
        "Dropping `%s`: must be a string, got %s (%s). %s",
        field, type(value).__name__, _short_repr(value), _STRING_TYPE_REMEDY,
    )
    return None


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


def _discard_new_dossier(db_path: Path) -> None:
    """Delete a just-created dossier database and its WAL sidecars.

    Only ever called for a *new* fold that failed before committing, so there
    is nothing here worth keeping: the file holds schema and no `metadata`
    row. The `-wal`/`-shm` companions are normally removed by SQLite on a
    clean close, but are unlinked explicitly so an unclean exit cannot leave
    a sidecar orphaned next to a database that no longer exists.

    Idempotent (`missing_ok=True`) because this runs on an error path where
    the exact stage of failure is unknown.
    """
    for path in (
        db_path,
        db_path.with_name(f"{db_path.name}-wal"),
        db_path.with_name(f"{db_path.name}-shm"),
    ):
        path.unlink(missing_ok=True)


# ── Element writers ─────────────────────────────────────────────────────
# One helper per array-valued payload key. Each takes the open transaction's
# connection and the session it is writing for, and each obeys the same
# policy: **warn, never reject.** A fold runs at the end of a session, so a
# refusal costs the agent the entire context the command exists to preserve;
# an incomplete write is recoverable on the next fold, a refused one is not.


def _encode_alternatives(alternatives: Any) -> str | None:
    """Return `alternatives` as the TEXT the column stores, or None."""
    if alternatives is None or isinstance(alternatives, str):
        return alternatives
    return json.dumps(alternatives)


def _store_decisions(
    conn: sqlite3.Connection, session_id: int, decisions: list[dict[str, Any]]
) -> None:
    """Insert this session's decisions, deduplicating on the full tuple.

    ## Why the dedupe key is every semantic field (r2-F7)

    The original matched on `what` + `why` alone, so a re-send that carried
    `decided_by` or `alternatives` the first send lacked was silently
    discarded — the richer copy lost to the poorer one, with no signal. A
    duplicate is now only a duplicate when *nothing about it is different*,
    which is the same rule the `pinned_findings` content hash enforces
    structurally.

    **Rejected: enriching the existing row in place.** It renders more neatly
    (one row instead of two near-identical ones), but it mutates a durable
    record from a later session's payload, and it needs a guess for the case
    where both copies carry *different* non-null values. Appending keeps the
    fold-never-destroys invariant, and `unfold`'s recency window bounds the
    cost of the extra row.

    `origin_session` is inherited from the earliest row recording the same
    `what` + `why`, so a decision re-sent with richer fields in session 5
    still reports that it dates from session 1.
    """
    for decision in decisions:
        what, why = decision["what"], decision["why"]
        alternatives = _encode_alternatives(decision.get("alternatives"))
        decided_by = decision.get("decided_by")

        # `IS` is SQLite's null-safe equality: `alternatives = NULL` would
        # never match, silently re-inserting every field-less decision.
        duplicate = conn.execute(
            "SELECT id FROM decisions "
            "WHERE what = ? AND why = ? AND alternatives IS ? AND decided_by IS ?",
            (what, why, alternatives, decided_by),
        ).fetchone()
        if duplicate:
            continue

        ancestor = conn.execute(
            "SELECT COALESCE(origin_session, session_id) AS origin FROM decisions "
            "WHERE what = ? AND why = ? ORDER BY id LIMIT 1",
            (what, why),
        ).fetchone()
        conn.execute(
            "INSERT INTO decisions "
            "(session_id, what, why, alternatives, decided_by, source, origin_session) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id, what, why, alternatives, decided_by,
                _DECISION_SOURCE_FOLD,
                ancestor["origin"] if ancestor else session_id,
            ),
        )


def _store_memory_queries(
    conn: sqlite3.Connection, session_id: int, queries: list[dict[str, Any]]
) -> None:
    """Append this session's memory-system queries.

    No dedupe: re-running the same query in a later session is a real event
    with a real (possibly different) result, and the render windows the table
    by session anyway.
    """
    for index, entry in enumerate(queries):
        if not isinstance(entry, dict):
            _log.warning("Skipping memory_queries[%d]: not an object.", index)
            continue
        complaints = _type_complaints(entry, _MEMORY_QUERY_STRING_FIELDS)
        if complaints:
            _log.warning(
                "Skipping memory_queries[%d]: %s. %s",
                index, "; ".join(complaints), _STRING_TYPE_REMEDY,
            )
            continue
        query = entry.get("query")
        if not query:
            _log.warning(
                "Skipping memory_queries[%d]: no `query` text to record.", index
            )
            continue
        conn.execute(
            "INSERT INTO memory_queries "
            "(session_id, tool, query, result_summary, used_for) VALUES (?, ?, ?, ?, ?)",
            (
                session_id, entry.get("tool"), query,
                entry.get("result_summary"), entry.get("used_for"),
            ),
        )


def _is_retired(conn: sqlite3.Connection, digest: str) -> bool:
    """Return True if a stored finding is superseded or is itself a tombstone."""
    return conn.execute(
        f"SELECT 1 FROM pinned_findings WHERE hash = ? AND NOT ({LIVE_FINDING_PREDICATE})",
        (digest,),
    ).fetchone() is not None


def _write_supersession_edges(
    conn: sqlite3.Connection, new_hash: str, supersedes: Any, index: int
) -> None:
    """Resolve `supersedes` prefixes against storage and write the edges.

    Three outcomes, three responses, because their costs are asymmetric
    (resolution failures may leave the render showing too *much*, never
    silently too little):

      - **exactly one match** — write the edge, the unambiguous case.
      - **none** — the finding is stored, the edge is skipped, and the CLI
        warns. Rejecting would discard new content over a typo in metadata.
      - **two or more** — the finding is stored, the edge is skipped, and the
        CLI reports at error grade naming every candidate. Guessing would
        coin-flip a live constraint into retirement, and the loser is a dead
        end an agent later walks back into. It is error-*grade* but does not
        fail the fold: skipping an edge produces an incomplete write, not a
        wrong one.

    Called only for a finding this transaction just inserted, which is what
    makes cycles unconstructible: every edge is born pointing from the newest
    row to one that already existed, so no arrow can aim forward in time. The
    new row is excluded from its own candidate set for the same reason: a
    short prefix that happens to match only the finding being written would
    otherwise retire it at birth, hiding a constraint nobody asked to hide.
    """
    if supersedes is None:
        return
    if not isinstance(supersedes, list):
        _log.warning(
            "Ignoring `supersedes` in pinned_findings[%d]: expected an array of "
            "%d-hex prefixes, got %s.",
            index, HASH_PREFIX_LENGTH, type(supersedes).__name__,
        )
        return

    for raw in supersedes:
        if not isinstance(raw, str):
            _log.warning(
                "Ignoring a `supersedes` entry in pinned_findings[%d]: expected a "
                "%d-hex prefix string, got %s (%s).",
                index, HASH_PREFIX_LENGTH, type(raw).__name__, _short_repr(raw),
            )
            continue
        prefix = raw.strip().lower()
        if not prefix:
            continue
        matches = conn.execute(
            "SELECT hash, text FROM pinned_findings "
            "WHERE substr(hash, 1, ?) = ? AND hash != ? ORDER BY hash",
            (len(prefix), prefix, new_hash),
        ).fetchall()

        if len(matches) == 1:
            # OR IGNORE: one payload may name the same target twice
            conn.execute(
                "INSERT OR IGNORE INTO finding_supersessions (new_hash, old_hash) "
                "VALUES (?, ?)",
                (new_hash, matches[0]["hash"]),
            )
        elif not matches:
            _log.warning(
                "Unknown supersedes prefix %s: no other stored finding matches it. "
                "The finding was stored; nothing was retired.",
                prefix,
            )
        else:
            # Full digests, not the rendered 8-hex handles: on a true prefix
            # collision those handles are identical, so this message is the
            # only surface that can supply the longer prefix its own remedy
            # asks for. Nothing else in the CLI prints a hash past 8 chars.
            candidates = ", ".join(
                f'{m["hash"]} ("{m["text"][:_CANDIDATE_TEXT_CHARS]}")' for m in matches
            )
            _log.error(
                "Ambiguous supersedes prefix %s: matches %s. The finding was "
                "stored; re-fold with a longer prefix from that list to retire "
                "the intended target.",
                prefix, candidates,
            )


def _store_pinned_findings(
    conn: sqlite3.Connection,
    session_id: int,
    elements: list[dict[str, Any]],
    now: str,
) -> None:
    """Append this session's pinned findings and their supersession edges.

    Writes are `INSERT OR IGNORE` against the content-hash primary key, so the
    duplicate check is not code that runs — it is the key itself. That matters
    because the misbehaving sender is the threat model rather than an edge
    case: agents run cached skill copies, and a check-then-insert would both
    race under concurrent folds and match only a field subset.

    Re-sending **live** content is therefore a silent no-op, and silence is
    load-bearing (a warning on the everyday path trains readers to ignore the
    channel). Re-sending **retired** content is the one deliberate exception:
    it escalates to a warning, because the alternative is the agent's freshly
    re-pinned constraint rendering nowhere at all.
    """
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            _log.warning("Skipping pinned_findings[%d]: not an object.", index)
            continue

        # Type-check before canonicalizing: `canonical_element` hashes what it
        # is given, so a number here would hash as a number and store as TEXT.
        complaints = _type_complaints(element, _FINDING_STRING_FIELDS)
        dead_end = element.get("dead_end")
        if dead_end is not None and not isinstance(dead_end, bool):
            complaints.append(
                f"`dead_end` must be true or false, got {type(dead_end).__name__} "
                f"({_short_repr(dead_end)})"
            )
        if complaints:
            _log.warning(
                "Skipping pinned_findings[%d]: %s. %s",
                index, "; ".join(complaints), _FINDING_TYPE_REMEDY,
            )
            continue

        canonical = canonical_element(element)
        text = canonical.get("finding")
        if not text:
            _log.warning(
                "Skipping pinned_findings[%d]: no `finding` text to pin.", index
            )
            continue

        kind = finding_kind(element)
        if kind is None:
            _log.warning(
                "pinned_findings[%d] has an unrecognized kind %r; storing it as a "
                "plain finding.",
                index, element.get("kind"),
            )
            kind = "finding"

        # The stored text is the canonical form, so the rendered line is
        # single-line by construction and a quoted-back copy re-hashes equal.
        digest = finding_hash(element)
        inserted = conn.execute(
            "INSERT OR IGNORE INTO pinned_findings "
            "(hash, kind, text, why_abandoned, retry, origin_session, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                digest, kind, text, canonical.get("why_abandoned"),
                canonical.get("retry"), session_id, now,
            ),
        ).rowcount == 1

        if inserted:
            _write_supersession_edges(conn, digest, element.get("supersedes"), index)
            continue

        # The row already exists. Its edges are frozen with it: accepting new
        # ones now is the only way an arrow could point forward in time.
        if element.get("supersedes"):
            _log.warning(
                "Supersession edges for pinned finding %s were skipped: that "
                "finding is already stored, and edges are only written with the "
                "row that creates them. Re-word the finding to retire a target.",
                short_hash(digest),
            )
        if _is_retired(conn, digest):
            _log.warning(
                "Pinned finding %s matches a retired row and was not revived. "
                "Supersede the tombstone with re-worded text: a verbatim "
                "re-assertion carries no information about why the retirement "
                "was wrong.",
                short_hash(digest),
            )


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
    last_exchange: str | None = None,
    next_words: str | None = None,
    mood: str | None = None,
    pinned_findings: list[dict[str, Any]] | None = None,
    memory_queries: list[dict[str, Any]] | None = None,
    max_retained_sessions: int = 0,
) -> dict[str, str]:
    """Create a new dossier or append a session to an existing one.

    For new dossiers: provide `name`. A hash and slug are generated.
    For existing dossiers: provide `slug`. A new session is appended.

    A failed fold leaves nothing behind. A re-fold's writes roll back with the
    transaction, so the existing dossier is untouched; a new fold's database is
    deleted outright, because it is created *before* the transaction that
    populates it (see `_discard_new_dossier`).

    Args:
        last_exchange: verbatim final turns of the conversation.
        next_words: what the agent was about to say or do next.
        mood: the session's emotional register, pace, and tone.

            All three are **per-session scalars**: they describe the moment
            this fold captured, so a re-fold records its own rather than
            overwriting an earlier session's.

        pinned_findings: findings and dead ends that accumulate across the
            dossier's lifetime, identified by the content hash of their
            semantic fields. Agents send only what is *new*; re-sends of live
            content are a guaranteed no-op, so a stale skill that carries
            everything forward cannot duplicate the table.
        memory_queries: this session's memory-system lookups. Append-only and
            session-scoped; `unfold` windows them at render time.
        max_retained_sessions: When > 0, delete `file_interactions` rows
            belonging to sessions older than the newest N. **Opt-in, and
            destructive.** Defaults to 0 (never prune) because a fold's
            contract is "append a session"; keeping the output compact is a
            rendering concern that `unfold` handles with a non-destructive
            window. See the retention comment at the prune site. Scoped to
            file interactions alone: `memory_queries` is windowed at render
            for the same reason and is never deleted.

    Returns:
        Dict with `slug`, `hash`, `task_count`, `decision_count`, and
        `pruned_file_rows` (0 unless retention was explicitly requested).
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

    try:
        with open_dossier_db(db_path) as conn:
            with conn:  # transaction: auto-commit on success, rollback on exception
                if is_refold:
                    meta = conn.execute("SELECT hash FROM metadata").fetchone()
                    dossier_hash = meta["hash"]

                    # `branch`/`commit_hash` are per-session snapshots: overwrite
                    # with whatever this session observed, including NULL.
                    # `project` is not — it is the stable repo the dossier is
                    # *about*. COALESCE refreshes it when the payload sends it
                    # (repos move; worktrees differ) while refusing to erase it
                    # for an older cached skill that omits the key.
                    conn.execute(
                        "UPDATE metadata SET updated_at = ?, agent = ?, branch = ?, "
                        "commit_hash = ?, project = COALESCE(?, project)",
                        (now, agent, branch, commit_hash, project),
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
                    "INSERT INTO sessions "
                    "(folded_at, agent, branch, commit_hash, digest, "
                    "last_exchange, next_words, mood) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        now, agent, branch, commit_hash, digest,
                        _checked_scalar(last_exchange, "last_exchange"),
                        _checked_scalar(next_words, "next_words"),
                        _checked_scalar(mood, "mood"),
                    ),
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
                _store_decisions(conn, session_id, decisions or [])

                # Insert file interactions
                for f in (files or []):
                    conn.execute(
                        "INSERT INTO file_interactions (session_id, file_path, action, annotation) VALUES (?, ?, ?, ?)",
                        (session_id, f["path"], f["action"], f.get("annotation")),
                    )

                # Insert memory queries and pinned findings. Findings come
                # last because their supersession edges may target a finding
                # written earlier in this same payload.
                _store_memory_queries(conn, session_id, memory_queries or [])
                _store_pinned_findings(conn, session_id, pinned_findings or [], now)

                # ── File-interaction retention (opt-in, destructive) ───────────
                # THE INVARIANT: a fold only ever APPENDS. This prune is the one
                # exception and it stays opt-in, because the rows it deletes are
                # earlier sessions' per-file annotations and nothing can recover
                # them.
                #
                # Keeping injected context small is a *rendering* concern, and
                # `unfold` owns it with a window that hides old rows rather than
                # deleting them — so the compact view stays small while `--full`
                # still reaches the whole history.
                #
                # Rejected: pruning by default and merely logging it. That makes
                # an append destructive by default to solve a problem the reader
                # already solves non-destructively.
                pruned_file_rows = 0
                if max_retained_sessions > 0:
                    cutoff_session = conn.execute(
                        "SELECT id FROM sessions ORDER BY id DESC LIMIT 1 OFFSET ?",
                        (max_retained_sessions,),
                    ).fetchone()
                    if cutoff_session:
                        cursor = conn.execute(
                            "DELETE FROM file_interactions WHERE session_id <= ?",
                            (cutoff_session["id"],),
                        )
                        pruned_file_rows = cursor.rowcount

                # query actual DB counts from the same transaction so the result reflects
                # exactly what this fold committed, not a post-commit concurrent write
                task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status != 'deleted'").fetchone()[0]
                decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

            # ── Exit path 1: refold deregistration + lock release ─────────────
            # Fold semantically means "I'm done with this dossier." Delete the
            # agent's registrations row so the slot can be reused, and release the
            # lock so other agents aren't blocked. Single store: the row is the
            # only identity artifact (no session file).
            # Only applies to refolds by an orchestrator (bare type). Fresh folds
            # have no prior registration to clean up. Worker labels never reach fold.
            if is_refold and agent and ":" not in agent:
                try:
                    # resolve_identity adopts/refreshes my slot (or raises if a
                    # live other instance owns it — then leave their state alone).
                    agent_id = resolve_identity(conn, slug, agent)

                    # ONE transaction for both writes, release first.
                    #
                    # Splitting these across two commits admits a state with no
                    # repair path: `registrations` empty while `metadata.locked_by`
                    # still names the deleted agent. Cleanup's cascade only
                    # iterates registration rows that still exist, so it can never
                    # find a lock whose holder has no row, leaving `lock release
                    # --force` as the only exit.
                    #
                    # Ordering alone would merely narrow that window; sharing a
                    # transaction removes it — either both land or neither does.
                    # Order still decides the *rollback* direction: if only one
                    # could survive it must be the registration, because cleanup
                    # reaps that on TTL while an orphaned lock is terminal.
                    with conn:
                        # Only release if SOMETHING holds it. `--claim` is opt-in,
                        # so the common fold runs unlocked, and reporting a no-op
                        # release would warn on essentially every fold. Warning
                        # noise on the happy path trains readers to ignore the
                        # channel that real payload warnings share.
                        #
                        # Not a TOCTOU risk: `release_lock_on_conn`'s conditional
                        # UPDATE remains the authority. This read only suppresses
                        # the no-op case; a lock claimed by someone else simply
                        # fails to match and is reported below.
                        holder_row = conn.execute(
                            "SELECT locked_by FROM metadata"
                        ).fetchone()
                        if holder_row and holder_row["locked_by"] is not None:
                            if release_lock_on_conn(conn, agent_id) == 0:
                                _log.warning(
                                    "Lock on %s not released on fold: held by %s, "
                                    "not %s.",
                                    slug, holder_row["locked_by"], agent_id,
                                )
                        deregister_agent(conn, agent_id)
                except ConcurrentInstanceError as e:
                    # another live process owns the slot — don't clean up their
                    # state. The fold itself already committed.
                    _log.warning("Skipping fold deregistration: %s", e)

    except BaseException:
        # A new fold creates its database BEFORE the transaction that
        # populates it, so any failure below leaves a schema-only file with
        # no `metadata` row. That orphan is invisible to `list` (which skips
        # metadata-less databases) yet still matched by `find_dossier`'s
        # `*.db` glob, so `unfold <name>` finds it and dies subscripting a
        # NULL row. Deleting it is what makes "a failed fold leaves nothing
        # behind" true rather than aspirational.
        #
        # `BaseException`, matching `db.connect_dossier_db`: a Ctrl-C mid-fold
        # must not strand a database either. Re-folds never take this branch
        # -- their database predates the call and holds real data.
        if not is_refold:
            _discard_new_dossier(db_path)
        raise

    return {
        "slug": slug,
        "hash": dossier_hash,
        "task_count": task_count,
        "decision_count": decision_count,
        "pruned_file_rows": pruned_file_rows,
    }
