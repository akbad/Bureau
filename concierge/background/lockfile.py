"""Lock file manager — prevents overlapping background runs."""
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
        """
        # Check for stale lock
        if self.path.exists():
            try:
                lock_time = datetime.fromisoformat(self.path.read_text().strip())
                if datetime.now(timezone.utc) - lock_time > self.stale_timeout:
                    self.path.unlink()  # Break stale lock
                else:
                    return False  # Lock is still valid
            except (ValueError, OSError):
                self.path.unlink()  # Corrupt lock file, remove it

        # Try to create lock atomically
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, datetime.now(timezone.utc).isoformat().encode())
            finally:
                os.close(fd)
            return True
        except FileExistsError:
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

    def __exit__(self, *args) -> None:
        self.release()
