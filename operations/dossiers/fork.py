"""Fork operation: create independent copy of a dossier."""
import sqlite3
from pathlib import Path
from typing import Any

from .db import open_dossier_db, safe_db_path
from .db import _now_iso
from .fold import _generate_hash, _slugify


def fork_dossier(
    dossiers_dir: Path,
    slug: str,
    name: str | None = None,
) -> dict[str, str]:
    """Create an independent copy of a dossier. Always unlocked.

    Uses sqlite3.backup() for a WAL-safe copy (ensures uncommitted
    WAL transactions are included in the fork).
    """
    source_path = safe_db_path(dossiers_dir, slug)
    if not source_path.exists():
        raise FileNotFoundError(f"Dossier not found: {slug}")

    # Read original metadata for defaults
    with open_dossier_db(source_path) as source_conn:
        meta = source_conn.execute("SELECT * FROM metadata").fetchone()

        fork_name = name or f"{meta['name']} (fork)"
        # collision-safe: retry until we find an unused slug
        while True:
            new_hash = _generate_hash()
            new_slug = f"{_slugify(fork_name)}-{new_hash}"
            dest_path = dossiers_dir / f"{new_slug}.db"
            if not dest_path.exists():
                break

        # WAL-safe copy via sqlite3 backup API
        dest_conn = sqlite3.connect(dest_path)
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
        dest_path.chmod(0o600)  # owner read/write only

    # Update metadata in the fork, and clear every trace of who was working on
    # the source. `sqlite3.backup()` copies the database verbatim, including
    # tables whose contents are only meaningful relative to the source slug.
    now = _now_iso()
    with open_dossier_db(dest_path) as conn:
        with conn:  # transaction boundary
            conn.execute(
                """UPDATE metadata SET
                   hash = ?, name = ?, slug = ?, updated_at = ?,
                   parent = ?, locked_by = NULL, locked_at = NULL""",
                (new_hash, fork_name, new_slug, now, meta["hash"]),
            )
            _clear_in_flight_state(conn, now)

    return {"slug": new_slug, "hash": new_hash}


def _clear_in_flight_state(conn, now: str) -> None:
    """Drop everything describing *who is currently working here*.

    A fork starts with nobody working on it. `sqlite3.backup()` copies verbatim,
    so registrations, task ownership and the reap log would otherwise be
    inherited from the source — and every id in them is derived from the
    **source** slug, so none of it is even addressable from the fork.

    Each removal prevents a distinct failure, not just untidiness:

      - **`registrations`** — the inherited orchestrator row occupies the
        fork's single `(agent_type, orchestrator)` slot under an id that a
        fresh `resolve_identity` against the fork's slug can never recompute.
        The first real agent either adopts a stale identity or is wrongly
        rejected as a concurrent instance.

      - **In-flight task ownership** — an `in_progress` task whose owner has no
        registration row is *unrepairable*: the reap cascade only iterates rows
        that still exist, so nothing ever reverts it. Clearing registrations
        without also releasing their tasks would manufacture exactly that
        state. Reverting to `pending` is what makes the task claimable again.

      - **`reap_log`** — `_maybe_warn_identity_reset` fires on any reap of the
        caller's `agent_type` within the last hour, so an inherited entry tells
        the fork's first agent that its prior identity was reaped, citing an
        event from a different dossier. The source keeps its own history, which
        stays reachable through the fork's `parent`.

    Completed and deleted tasks are deliberately untouched: those are history,
    and a fork inherits history. Only *in-flight* claims are dropped.
    """
    conn.execute("DELETE FROM registrations")
    conn.execute("DELETE FROM reap_log")
    conn.execute(
        "UPDATE tasks SET status = 'pending', owner = NULL, updated_at = ? "
        "WHERE status = 'in_progress'",
        (now,),
    )
