"""Advisory lock operations for dossiers."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import open_dossier_db, safe_db_path
from .errors import LockConflictError


def get_lock_status(dossiers_dir: Path, slug: str) -> dict[str, Any]:
    """Get current lock status."""
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        meta = conn.execute("SELECT locked_by, locked_at FROM metadata").fetchone()
    return {"locked_by": meta["locked_by"], "locked_at": meta["locked_at"]}


def claim_lock(dossiers_dir: Path, slug: str, agent: str) -> None:
    """Claim advisory lock. Raises ValueError if already locked by another agent."""
    if not agent:
        raise ValueError("Agent identifier is required to claim a lock")
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cursor = conn.execute(
                "UPDATE metadata SET locked_by = ?, locked_at = ? "
                "WHERE locked_by IS NULL OR locked_by = ?",
                (agent, now, agent),
            )
            affected = cursor.rowcount
        if affected == 0:
            meta = conn.execute("SELECT locked_by FROM metadata").fetchone()
            holder = meta["locked_by"] if meta else "unknown"
            raise LockConflictError(f"Dossier already locked by {holder}")


def release_lock_on_conn(conn, agent: str) -> int:
    """Clear the lock iff `agent` holds it, on a caller-supplied connection.

    The connection-level primitive behind `release_lock`, extracted so a caller
    already inside a transaction can release *atomically with* its other writes
    rather than through a second connection afterwards.

    Kept as one definition rather than duplicating the UPDATE at the second call
    site: the conditional predicate is the whole safety property, and two copies
    of a safety predicate is how they diverge.

    Does not commit — the caller owns the transaction, matching
    `registration.py`'s convention.

    Returns the number of rows updated: 1 if the lock was held by `agent` and is
    now clear, 0 if it was held by somebody else or by no one.
    """
    return conn.execute(
        "UPDATE metadata SET locked_by = NULL, locked_at = NULL WHERE locked_by = ?",
        (agent,),
    ).rowcount


def release_lock(dossiers_dir: Path, slug: str, agent: str | None = None, force: bool = False) -> None:
    """Release advisory lock.

    Requires either ``agent`` (verified release) or ``force`` (unconditional).
    Raises ValueError if neither is provided, or if the caller does not hold the lock.
    Uses a conditional UPDATE to avoid TOCTOU races.
    """
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        if force:
            with conn:  # transaction boundary
                conn.execute("UPDATE metadata SET locked_by = NULL, locked_at = NULL")
        elif agent:
            with conn:  # transaction boundary
                # atomic check-and-release: only clears if caller holds the lock
                released = release_lock_on_conn(conn, agent)
            if released == 0:
                meta = conn.execute("SELECT locked_by FROM metadata").fetchone()
                holder = meta["locked_by"] if meta and meta["locked_by"] else "no one"
                raise ValueError(
                    f"Lock held by {holder}, not {agent}. Use --force to override."
                )
        else:
            raise ValueError("--agent or --force is required to release a lock")
