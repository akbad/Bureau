"""Typed exceptions for structured CLI error reporting.

Each exception type maps to a specific failure mode, enabling agents
to distinguish errors by tag (e.g., [not-found], [lock-conflict])
rather than parsing English error messages.
"""


class DossierNotFoundError(FileNotFoundError):
    """Raised when no dossier matches the query."""


class LockConflictError(ValueError):
    """Raised when a dossier is locked by another agent."""


class AmbiguousQueryError(ValueError):
    """Raised when a query matches multiple dossiers."""


class ConcurrentInstanceError(LockConflictError):
    """Raised when another live CLI process of the same agent type holds
    the session for this dossier (detected via PID liveness check)."""


# ── Task CAS taxonomy (Mechanism 2: rich CAS failure errors) ─────────────────
# A task compare-and-swap (e.g. complete: in_progress -> completed) that matches
# zero rows is opaque on its own ("not in progress") — it hides *why* the swap
# failed. These types disambiguate the one rowcount==0 outcome into a precondition
# failure plus four distinct coordination root causes, each with its own
# remediation. All subclass `ValueError` so existing `except ValueError` callers
# (and the CLI's generic handler) keep working; new code can catch the specific
# cause. See `tasks._raise_task_cas_failure`.


class TaskNotFoundError(ValueError):
    """Raised when a task id does not exist — a precondition failure.

    Categorically distinct from the four CAS-dispatch errors below: there is no
    task to compare-and-swap against, so this is "you targeted a row that was
    never there", not "the row exists but is in the wrong state".
    """


class IdentityReapedError(ValueError):
    """Raised when a task CAS fails because the caller's registration is gone.

    The primary-defense cleanup reaped the caller's identity (PID-dead or stale)
    while it held the task, reverting the in-progress work. The remediation is to
    re-claim and redo; the message carries the `reap_log` entry (when present) so
    the cause and timing are self-explaining.
    """


class TaskAlreadyCompletedError(ValueError):
    """Raised when a task CAS fails because the task is already ``completed``.

    Legitimate (e.g. a manual ``update_task status='completed'`` via the no-agent
    escape hatch, or a concurrent completion). No action needed.
    """


class TaskDeletedError(ValueError):
    """Raised when a task CAS fails because the task was soft-deleted.

    Legitimate; the remediation is to acknowledge the deletion rather than retry.
    """


class TaskStateError(ValueError):
    """Raised when a task CAS fails with the caller's registration intact and the
    task in an unexpected state (not ``completed``/``deleted``).

    This is the "should never happen under correct usage" case — a coordination
    invariant was violated (a bug or DB corruption), warranting investigation
    rather than a retry.
    """
