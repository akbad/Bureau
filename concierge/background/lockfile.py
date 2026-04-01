"""Lock file manager — prevents overlapping background runs."""

# Design rationale:
# File-based mutual exclusion using atomic O_CREAT|O_EXCL to prevent
# concurrent background runs without requiring external dependencies.
# Stale-lock detection (based on timestamp age) handles crash recovery.
# A retry loop addresses the TOCTOU race between unlinking a stale lock
# and re-creating it: if another process wins, we re-check on the next
# iteration.
# Key invariants: lock file always contains a UTC ISO-8601 timestamp;
# acquire() never raises — it returns bool.

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


class LockError(Exception):
    """Raised when a lock cannot be acquired."""


class LockFile:
    """File-based lock to prevent concurrent background runs.

    Uses atomic file creation (os.open with O_CREAT | O_EXCL).
    Includes a stale-lock timeout to recover from crashes.
    """

    def __init__(self, path: Path, stale_timeout_minutes: int = 30) -> None:
        self.path = path
        self.stale_timeout = timedelta(minutes=stale_timeout_minutes)

    def acquire(self) -> bool:
        """Attempt to acquire the lock.

        Returns True if acquired, False if already locked.
        Automatically breaks stale locks (older than stale_timeout).

        After breaking a stale lock, the atomic ``os.open(O_CREAT|O_EXCL)``
        may fail with ``FileExistsError`` if another process won the race
        between unlink and open (TOCTOU). In that case we retry the full
        check-and-create cycle once, which is sufficient because the new
        lock is either fresh (return False) or itself stale (break and win).
        """
        for _attempt in range(2):
            # Check for stale lock
            if self.path.exists():
                try:
                    lock_time = datetime.fromisoformat(
                        self.path.read_text().strip()
                    )
                    if datetime.now(timezone.utc) - lock_time > self.stale_timeout:
                        self.path.unlink()  # Break stale lock
                    else:
                        return False  # Lock is still valid
                except (ValueError, OSError):
                    # Corrupt lock file or disappeared between exists() and
                    # read_text(); remove it if still present.
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass

            # Try to create lock atomically
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(
                    str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                try:
                    os.write(fd, datetime.now(timezone.utc).isoformat().encode())
                finally:
                    os.close(fd)
                return True
            except FileExistsError:
                # Another process created the lock between our unlink and
                # open.  Retry the full cycle so we can inspect whether
                # that new lock is valid or itself stale.
                continue

        # Both attempts lost the race — another process holds the lock.
        return False

    def release(self) -> None:
        """Release the lock."""
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def is_locked(self) -> bool:
        """Check if the lock is currently held."""
        return self.path.exists()

    def __enter__(self) -> "LockFile":
        if not self.acquire():
            raise LockError(f"Could not acquire lock: {self.path}")
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
