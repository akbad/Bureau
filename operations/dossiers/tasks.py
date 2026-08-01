"""Task CRUD operations for dossier task lists."""
import sqlite3
from pathlib import Path
from typing import Any

from .db import (
    open_dossier_db, safe_db_path, _now_iso,
    MAX_SUBJECT_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_CONTEXT_NOTES_LENGTH,
    VALID_STATUSES,
)
from .errors import (
    TaskNotFoundError, IdentityReapedError, TaskAlreadyCompletedError,
    TaskDeletedError, TaskStateError,
)
from .identity import _get_cli_process_pid
from .registration import _maybe_deregister_worker, register_agent

# nullable fields where passing "" means "clear to NULL";
# non-nullable fields (subject, status) ignore empty strings to avoid
# violating SQLite NOT NULL constraints
CLEARABLE_FIELDS = {"description", "owner", "blocked_by", "context_notes"}


def _raise_task_cas_failure(
    conn: sqlite3.Connection, task_id: int, agent: str | None
) -> None:
    """Diagnose why an ``in_progress`` task CAS matched zero rows and raise.

    Mechanism 2 (rich CAS failure errors): a guarded ``UPDATE ... WHERE
    status='in_progress'`` that affects no rows is opaque on its own. This reads
    the task's current state — and, when `agent` is known, the caller's
    registration plus the `reap_log` — to dispatch to the specific cause:

    1. `TaskNotFoundError` — the id does not exist (precondition failure).
    2. `TaskAlreadyCompletedError` — the task is already ``completed``.
    3. `TaskDeletedError` — the task was soft-deleted.
    4. `IdentityReapedError` — the task is in a non-terminal state *and* the
       caller's registration is gone, i.e. the primary-defense cleanup reaped it
       and reverted the work (only checked when `agent` is provided; the reap
       timing is read from `reap_log`).
    5. `TaskStateError` — non-terminal state with the registration intact ⇒ a
       coordination invariant was violated (investigate).

    ## Ordering: terminal status before identity

    Terminal states (``completed``/``deleted``) are checked *before* the
    reaped-identity branch — a deliberate deviation from the v3.md sketch, which
    checked identity first. The reap signature is a task *reverted to a
    non-terminal state* plus a missing registration; a ``completed`` task is
    "already completed" regardless of registration state. Checking identity first
    misreports the legitimate case where a worker completes its task and is
    self-deregistered (`_maybe_deregister_worker`) as "reaped, work reverted".

    Args:
        conn: open connection; only reads are issued (safe inside or after the
            caller's transaction since the failed CAS wrote nothing).
        task_id: the task whose CAS failed.
        agent: the resolved caller id, or ``None`` when the call site has no
            identity (e.g. the unguarded manual-repair path); when ``None`` the
            reaped-identity branch is skipped.

    Always raises; the ``-> None`` return is never reached.
    """
    diag = conn.execute(
        "SELECT status, owner, updated_at FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if diag is None:
        # precondition guard: no row to compare-and-swap against
        raise TaskNotFoundError(f"Task {task_id} does not exist.")

    if diag["status"] == "completed":
        # terminal + proximate truth; legitimate (manual override or a prior/
        # concurrent completion), independent of the caller's registration state
        raise TaskAlreadyCompletedError(
            f"Task {task_id} is already completed by {diag['owner']} "
            f"at {diag['updated_at']}. No action needed."
        )
    if diag["status"] == "deleted":
        raise TaskDeletedError(
            f"Task {task_id} was soft-deleted by {diag['owner']} "
            f"at {diag['updated_at']}."
        )

    # non-terminal state: a reverted task. caller identity gone ⇒ primary-defense
    # cleanup reaped it mid-work (the revert to pending is why the CAS missed)
    if agent is not None:
        my_reg = conn.execute(
            "SELECT 1 FROM registrations WHERE agent_id = ?", (agent,)
        ).fetchone()
        if my_reg is None:
            reap = conn.execute(
                "SELECT reaped_at, reap_reason FROM reap_log "
                "WHERE agent_id = ? ORDER BY reaped_at DESC LIMIT 1",
                (agent,),
            ).fetchone()
            reap_info = (
                f" (reaped at {reap['reaped_at']}, reason={reap['reap_reason']})"
                if reap else ""
            )
            raise IdentityReapedError(
                f"Task {task_id} CAS failed: your registration '{agent}' is "
                f"gone{reap_info}. Current task state: status={diag['status']}, "
                f"owner={diag['owner']}, last_modified={diag['updated_at']}. Your "
                f"in-progress work was reverted; re-claim and redo: "
                f"`bureau-dossiers tasks <slug> claim --id {task_id} --agent <type>`."
            )

    # non-terminal state + registration intact ⇒ "should never happen" invariant
    # violation; fail loud so it gets investigated rather than silently retried
    raise TaskStateError(
        f"Task {task_id} is '{diag['status']}' (not 'in_progress'), last modified "
        f"{diag['updated_at']} by {diag['owner'] or 'nobody'}. Your registration "
        f"is intact; this may indicate a coordination invariant was violated — "
        f"investigate."
    )


def list_tasks(dossiers_dir: Path, slug: str) -> list[dict[str, Any]]:
    """List all non-deleted tasks for a dossier."""
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        rows = conn.execute(
            "SELECT id, subject, description, status, owner, blocked_by, "
            "context_notes, created_at, updated_at "
            "FROM tasks WHERE status != 'deleted' ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def _validate_task_fields(
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    context_notes: str | None = None,
) -> None:
    """Validate task field lengths and status values.

    Fields are only checked when non-None and not the empty-string
    clear sentinel (empty string on clearable fields means "set to NULL").
    """
    if subject is not None and subject != "" and len(subject) > MAX_SUBJECT_LENGTH:
        raise ValueError(f"Subject exceeds maximum length ({MAX_SUBJECT_LENGTH} chars)")
    if description is not None and description != "" and len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"Description exceeds maximum length ({MAX_DESCRIPTION_LENGTH} chars)")
    if context_notes is not None and context_notes != "" and len(context_notes) > MAX_CONTEXT_NOTES_LENGTH:
        raise ValueError(f"Context notes exceeds maximum length ({MAX_CONTEXT_NOTES_LENGTH} chars)")
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_STATUSES))}")


def add_task(
    dossiers_dir: Path,
    slug: str,
    subject: str,
    description: str | None = None,
    status: str = "pending",
    owner: str | None = None,
    blocked_by: str | None = None,
    context_notes: str | None = None,
) -> int:
    """Add a new task. Returns the task ID."""
    _validate_task_fields(
        subject=subject, description=description,
        status=status, context_notes=context_notes,
    )
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            now = _now_iso()
            cursor = conn.execute(
                "INSERT INTO tasks (subject, description, status, owner, blocked_by, "
                "context_notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (subject, description, status, owner, blocked_by, context_notes, now, now),
            )
            task_id = cursor.lastrowid
    return task_id


def update_task(
    dossiers_dir: Path,
    slug: str,
    task_id: int,
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    blocked_by: str | None = None,
    context_notes: str | None = None,
    agent: str | None = None,
) -> None:
    """Update fields on an existing task.

    Raises `ValueError` if the task is not found.

    ## Worker-reassignment CAS guard

    When `agent` is provided **and** `status` is being set to ``pending`` or
    ``blocked``, the UPDATE adds a ``WHERE status = 'in_progress'`` guard.
    Without this, an orchestrator reassigning a worker's task could clobber
    a concurrent ``complete_task`` and revert a ``completed`` row back to
    ``pending``. The CAS returns `rowcount = 0` on contention and the caller
    sees a clear error.

    When `agent` is not provided, the update is unguarded (current escape-hatch
    semantics for manual repair via CLI with no `--agent`).

    After a successful CAS out of `in_progress`, the former owner is passed
    through `_maybe_deregister_worker`, which is a no-op unless the owner
    was a worker with zero remaining in-progress tasks.
    """
    _validate_task_fields(
        subject=subject, description=description,
        status=status, context_notes=context_notes,
    )
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        existing = conn.execute(
            "SELECT id, owner, status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not existing:
            raise TaskNotFoundError(f"Task {task_id} not found in dossier {slug}")

        updates = []
        values = []
        for field, value in [
            ("subject", subject), ("description", description),
            ("status", status), ("owner", owner), ("blocked_by", blocked_by),
            ("context_notes", context_notes),
        ]:
            if value is not None:
                # empty string on clearable fields = explicit clear (set to NULL)
                if value == "" and field in CLEARABLE_FIELDS:
                    updates.append(f"{field} = ?")
                    values.append(None)
                elif value == "":
                    continue  # ignore empty string on non-nullable fields
                else:
                    updates.append(f"{field} = ?")
                    values.append(value)

        if not updates:
            return

        # decide whether to add the worker-reassignment CAS guard
        cas_guarded = agent is not None and status in ("pending", "blocked")

        with conn:
            updates.append("updated_at = ?")
            values.append(_now_iso())
            values.append(task_id)

            sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            if cas_guarded:
                sql += " AND status = 'in_progress'"

            cursor = conn.execute(sql, values)

            if cas_guarded and cursor.rowcount == 0:
                # raise inside `with conn:` so the no-op txn rolls back cleanly;
                # the dispatcher only reads, then raises the specific cause
                _raise_task_cas_failure(conn, task_id, agent)

            # former owner deregistration (only meaningful when owner was a worker
            # and we cleared their ownership via an in_progress → ... transition)
            former_owner = existing["owner"]
            if (
                cas_guarded
                and former_owner
                and ":" in former_owner
                and cursor.rowcount > 0
            ):
                _maybe_deregister_worker(conn, former_owner)


def remove_task(dossiers_dir: Path, slug: str, task_id: int) -> None:
    """Soft-delete a task by setting status to 'deleted'."""
    update_task(dossiers_dir, slug, task_id, status="deleted")


def claim_task(dossiers_dir: Path, slug: str, task_id: int, owner: str) -> None:
    """Atomically claim a pending task (CAS: pending -> in_progress).

    If `owner` is a worker label (contains ``:``), ensures a worker
    registration row exists for it (idempotent — skipped if already present).
    Workers don't have session files; their registration is managed by the
    orchestrator via explicit labels.

    Register-then-claim is atomic: if the claim CAS fails, the speculative worker
    registration is rolled back (the failure is raised inside the transaction).

    Raises `TaskNotFoundError` if no such task, or `ValueError` if the task
    exists but is not pending (already claimed, completed, or deleted).
    """
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            # worker labels carry ':' — orchestrators pass bare types, which
            # get resolved in the CLI layer and arrive here as 'type:hex'.
            # the registration ensures cleanup/who/deregister paths see them.
            if ":" in owner:
                already = conn.execute(
                    "SELECT 1 FROM registrations WHERE agent_id = ?", (owner,)
                ).fetchone()
                if not already:
                    # record the ancestor CLI pid, not None (reg-A): a NULL here
                    # gives the reap's liveness oracle nothing to ask, so it
                    # falls through to reaping the worker on age alone. The pid
                    # is the enclosing CLI process — the worker lives exactly as
                    # long as it does.
                    register_agent(
                        conn, owner, owner.split(":", 1)[0],
                        _get_cli_process_pid(), role="worker",
                    )

            now = _now_iso()
            cursor = conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ?, updated_at = ? "
                "WHERE id = ? AND status = 'pending'",
                (owner, now, task_id),
            )
            if cursor.rowcount == 0:
                # raise INSIDE the txn so the speculative worker register above
                # rolls back — register-then-claim must be atomic (C2). The claim
                # CAS expects 'pending', so the reaped-identity branch does not
                # apply here; just distinguish missing from wrong-state.
                diag = conn.execute(
                    "SELECT status FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
                if diag is None:
                    raise TaskNotFoundError(f"Task {task_id} does not exist.")
                raise ValueError(
                    f"Task {task_id} cannot be claimed: it is '{diag['status']}', "
                    f"not 'pending' (already in progress / completed / deleted)."
                )


def complete_task(
    dossiers_dir: Path,
    slug: str,
    task_id: int,
    agent: str | None = None,
) -> None:
    """Atomically complete an in-progress task (CAS: in_progress -> completed).

    If `agent` is provided and was a worker with zero remaining in-progress
    tasks after this completion, the worker's registration row is deleted
    (see `_maybe_deregister_worker` — no-op for orchestrators).

    Raises `TaskNotFoundError` / `IdentityReapedError` /
    `TaskAlreadyCompletedError` / `TaskDeletedError` / `TaskStateError` (the
    Mechanism 2 dispatch) when the CAS finds no in-progress row.
    """
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:  # transaction boundary
            now = _now_iso()
            cursor = conn.execute(
                "UPDATE tasks SET status = 'completed', updated_at = ? "
                "WHERE id = ? AND status = 'in_progress'",
                (now, task_id),
            )
            if cursor.rowcount == 0:
                # raise inside the txn (the no-op CAS rolls back cleanly); the
                # dispatcher only reads, then raises the specific cause
                _raise_task_cas_failure(conn, task_id, agent)

            # deregister inside the same transaction so the ownership-count query
            # observes the just-completed task's new state
            if agent:
                _maybe_deregister_worker(conn, agent)
