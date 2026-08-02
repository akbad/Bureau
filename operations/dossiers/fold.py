"""Fold operation: create or update a dossier."""
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from .db import create_dossier_db, open_dossier_db, safe_db_path, _now_iso, MAX_DIGEST_LENGTH, MAX_TASKS_PER_DOSSIER
from .errors import ConcurrentInstanceError
from .identity import resolve_identity
from .lock import release_lock_on_conn
from .registration import deregister_agent
from .tasks import _validate_task_fields

_log = logging.getLogger(__name__)


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
        max_retained_sessions: When > 0, delete `file_interactions` rows
            belonging to sessions older than the newest N. **Opt-in, and
            destructive.** Defaults to 0 (never prune) because a fold's
            contract is "append a session"; keeping the output compact is a
            rendering concern that `unfold` handles with a non-destructive
            window. See the retention comment at the prune site.

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
                    # *about*, and the documented re-fold payload sends it, so it
                    # was silently dropped here until now. COALESCE refreshes it
                    # when sent (repos move; worktrees differ) while refusing to
                    # erase it for an older cached skill that omits the key.
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

                # ── File-interaction retention (opt-in, destructive) ───────────
                # This prune used to run on EVERY fold with a hard-coded window of
                # 5 and no way to disable it, so appending a session silently
                # destroyed earlier sessions' per-file annotations. That is data
                # loss the caller never requested and the success line never
                # mentioned.
                #
                # The invariant now: a fold only ever APPENDS. Keeping injected
                # context small is a *rendering* concern, and `unfold` enforces it
                # with a window that hides old rows instead of deleting them, so
                # the compact view is byte-identical to the old behaviour while
                # `--full` can still reach the whole history.
                #
                # Rejected: keeping the prune and merely logging it. That still
                # makes an append destructive by default, and the rows it destroys
                # are unrecoverable — the treadmill only ever runs one way.
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

                    # ONE transaction for both writes, release first (reg-B).
                    #
                    # These used to be two commits on two connections:
                    # `deregister_agent` committed here, then `release_lock`
                    # opened a fresh connection after the dossier context closed.
                    # A failure in between left `registrations` empty while
                    # `metadata.locked_by` still named the deleted agent, and
                    # that state is UNRECOVERABLE by design: cleanup's cascade
                    # only iterates registration rows that still exist, so it can
                    # never find a lock whose holder has no row. `lock release
                    # --force` was the only way out.
                    #
                    # Reordering alone would only narrow the window. Sharing a
                    # transaction removes it: either both land or neither does.
                    # Order still matters for the *rollback* direction, though —
                    # if only one could survive, a stale registration is the
                    # right residue, because cleanup reaps it on TTL while an
                    # orphaned lock has no repair path at all.
                    with conn:
                        # Only release if SOMETHING holds it. `--claim` is opt-in,
                        # so the common fold runs unlocked, and reporting a
                        # no-op release logged a warning on essentially every
                        # fold (r2-F8). Warning noise on the happy path trains
                        # readers to ignore the channel that real payload
                        # warnings share.
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
