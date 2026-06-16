"""Registration table CRUD for dossier agents.

# Design rationale

Under v3's single-store model the ``registrations`` row *is* the agent's
identity — there is no on-disk session marker file. Every agent that holds a
lock or owns tasks has a row here: orchestrators carry a deterministic id
(``orch-<type>-<hash>``) keyed to their slot, workers carry a discriminator
(``work-<type>-<pid>`` or an explicit ``<type>:worker-<n>:<ts>`` label).

This module is pure CRUD. The non-trivial logic — the target-less UPSERT,
liveness dispatch, and identity-reset detection — lives in ``identity.py``,
which inlines its own orchestrator INSERT rather than going through
``register_agent`` (it needs ``ON CONFLICT DO NOTHING`` semantics). The CRUD
here serves the worker path and display.

## Two timestamps, one meaning each

v2 overloaded a single ``registered_at`` as both "first seen" and the
liveness heartbeat. v3 splits them:

  - ``registered_at`` is set once at first insert and never refreshed; it is
    the identity's birth time, for audit and ``who`` ("since").
  - ``last_heartbeat`` is refreshed on every connect/resolution; it is the
    staleness oracle the TTL cleanup compares against ("last seen").

## Worker deregistration

Workers are short-lived and single-task. They deregister when their last
``in_progress`` task transitions out (completed, blocked, or reassignment).
``_maybe_deregister_worker`` encodes that check in one place: role must be
``worker`` and the owner must have zero remaining in-progress tasks.
Orchestrators never match this predicate and are only deregistered on fold.

## Transaction ownership (C2 invariant)

None of these functions commit. The caller owns the transaction boundary —
typically a ``with conn:`` block at the call site. This is load-bearing: the
worker path (``tasks.claim_task``) registers a worker and then CAS-claims its
task in *one* transaction, so the speculative registration must roll back if
the claim fails. An internal ``conn.commit()`` here would persist that
registration permanently (Python's ``with conn:`` only rolls back the *current*
implicit transaction; an inner commit escapes it), reverting register-then-claim
to a non-atomic two-step. Each direct caller (incl. ``fold`` and tests) must
wrap these in its own transaction.
"""
import sqlite3

from operations.dossiers.db import _now_iso


def register_agent(
    conn: sqlite3.Connection,
    agent_id: str,
    agent_type: str,
    cli_pid: int | None,
    role: str = "orchestrator",
) -> None:
    """Insert a registrations row with `registered_at` and `last_heartbeat` both now.

    Raises `sqlite3.IntegrityError` on a UNIQUE/partial-index violation. The
    orchestrator path does not use this (it inlines a target-less UPSERT in
    `identity.resolve_identity`); this serves the worker path, whose ids carry
    a discriminator and so do not collide.

    Does not commit — the caller owns the transaction (see module docstring,
    "Transaction ownership").
    """
    now = _now_iso()
    conn.execute(
        "INSERT INTO registrations "
        "(agent_id, agent_type, role, cli_pid, registered_at, last_heartbeat) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (agent_id, agent_type, role, cli_pid, now, now),
    )


def deregister_agent(conn: sqlite3.Connection, agent_id: str) -> None:
    """Delete the registrations row for `agent_id`. Idempotent on missing.

    Does not commit — the caller owns the transaction (see module docstring).
    """
    conn.execute("DELETE FROM registrations WHERE agent_id = ?", (agent_id,))


def refresh_heartbeat(conn: sqlite3.Connection, agent_id: str) -> None:
    """Update `last_heartbeat` for `agent_id` to now.

    No-op if the row is missing (UPDATE matches zero rows). `registered_at` is
    deliberately left untouched — it is the set-once birth time.

    Does not commit — the caller owns the transaction (see module docstring).
    """
    conn.execute(
        "UPDATE registrations SET last_heartbeat = ? WHERE agent_id = ?",
        (_now_iso(), agent_id),
    )


def list_agents(conn: sqlite3.Connection) -> list[dict]:
    """Return all registrations as dicts, ordered for display.

    Ordering: ``agent_type`` ascending, then orchestrators before workers,
    then oldest-first within each group. Shape matches the ``who`` command's
    rendering needs.
    """
    # orchestrator sorts before worker lexicographically (o < w) — no CASE needed
    rows = conn.execute(
        "SELECT agent_id, agent_type, role, cli_pid, registered_at, last_heartbeat "
        "FROM registrations "
        "ORDER BY agent_type ASC, role ASC, registered_at ASC"
    ).fetchall()
    return [dict(r) for r in rows]


def _maybe_deregister_worker(conn: sqlite3.Connection, agent_id: str) -> bool:
    """Deregister `agent_id` iff it is a worker with zero in-progress tasks.

    Returns True if the row was deleted, False otherwise (not a worker,
    still has in-progress tasks, or row missing). Orchestrators are never
    deregistered by this path.

    Does not commit — the caller owns the transaction (see module docstring).
    Callers invoke this inside their task-mutation transaction so the
    in-progress count reflects the just-applied state change.
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
    return True
