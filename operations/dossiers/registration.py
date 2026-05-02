"""Registration table CRUD for dossier agents.

# Design rationale

The ``registrations`` table is the DB-side mirror of on-disk session marker
files. Every agent that holds a lock or owns tasks has a row here; orchestrators
are keyed by ``<type>:<6-hex>`` and workers by ``<type>:worker-<n>:<ts>``.

This module is pure CRUD. The non-trivial logic (identity resolution,
liveness checks, session files) lives in ``identity.py``. Deregistration is
triggered explicitly by fold / complete / update command handlers, or
implicitly by inline cleanup after the TTL.

## Heartbeat semantics

``refresh_heartbeat`` is called on every identity resolution. An active
agent's ``registered_at`` is therefore always fresh, and inline cleanup
cannot reap a working session. This structurally eliminates the
reap-vs-completion race that haunted v1's explicit-heartbeat scheme.

## Worker deregistration

Workers are short-lived and single-task. They deregister when their last
``in_progress`` task transitions out (completed, blocked, or orchestrator
reassignment). ``_maybe_deregister_worker`` encodes that check in one place:
role must be ``worker`` and the owner must have zero remaining in-progress
tasks. Orchestrators never match this predicate (their role is
``orchestrator``) and are only deregistered on explicit fold.
"""
import sqlite3

from operations.dossiers.db import _now_iso


def register_agent(
    conn: sqlite3.Connection,
    agent_id: str,
    agent_type: str,
    ppid: int | None,
    role: str = "orchestrator",
) -> None:
    """Insert a registrations row.

    Raises `sqlite3.IntegrityError` on UNIQUE violation; the caller is
    responsible for retry (identity.resolve_identity mints a fresh suffix
    and retries once — collisions here are astronomically rare).
    """
    conn.execute(
        "INSERT INTO registrations (agent_id, agent_type, ppid, role, registered_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (agent_id, agent_type, ppid, role, _now_iso()),
    )
    conn.commit()


def deregister_agent(conn: sqlite3.Connection, agent_id: str) -> None:
    """Delete the registrations row for `agent_id`. Idempotent on missing."""
    conn.execute("DELETE FROM registrations WHERE agent_id = ?", (agent_id,))
    conn.commit()


def refresh_heartbeat(conn: sqlite3.Connection, agent_id: str) -> None:
    """Update `registered_at` for `agent_id` to now.

    No-op if the row is missing (UPDATE matches zero rows). Called on every
    identity resolution as the implicit heartbeat.
    """
    conn.execute(
        "UPDATE registrations SET registered_at = ? WHERE agent_id = ?",
        (_now_iso(), agent_id),
    )
    conn.commit()


def list_agents(conn: sqlite3.Connection) -> list[dict]:
    """Return all registrations as dicts, ordered for display.

    Ordering: ``agent_type`` ascending, then orchestrators before workers,
    then oldest-first within each group. Shape matches the ``who`` command's
    rendering needs.
    """
    # orchestrator sorts before worker lexicographically (o < w) — no CASE needed
    rows = conn.execute(
        "SELECT agent_id, agent_type, ppid, role, registered_at "
        "FROM registrations "
        "ORDER BY agent_type ASC, role ASC, registered_at ASC"
    ).fetchall()
    return [dict(r) for r in rows]


def _maybe_deregister_worker(conn: sqlite3.Connection, agent_id: str) -> bool:
    """Deregister `agent_id` iff it is a worker with zero in-progress tasks.

    Returns True if the row was deleted, False otherwise (not a worker,
    still has in-progress tasks, or row missing). Orchestrators are never
    deregistered by this path.
    """
    row = conn.execute(
        "SELECT role FROM registrations WHERE agent_id = ?", (agent_id,)
    ).fetchone()
    if row is None or row["role"] != "worker":
        return False

    in_progress = conn.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE owner = ? AND status = 'in_progress'",
        (agent_id,),
    ).fetchone()
    if in_progress["n"] > 0:
        return False

    conn.execute("DELETE FROM registrations WHERE agent_id = ?", (agent_id,))
    conn.commit()
    return True
