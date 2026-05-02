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
