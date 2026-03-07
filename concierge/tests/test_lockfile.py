"""Tests for lock file manager."""
from datetime import datetime, timezone, timedelta

import pytest

from concierge.background.lockfile import LockFile, LockError


@pytest.fixture
def lock_path(tmp_path):
    return tmp_path / "test.lock"


@pytest.fixture
def lock(lock_path):
    return LockFile(lock_path)


class TestAcquireRelease:
    def test_acquire_creates_file(self, lock, lock_path):
        """Acquiring a lock should create the lock file."""
        assert lock.acquire() is True
        assert lock_path.exists()

    def test_acquire_fails_when_locked(self, lock):
        """A second acquire should fail when lock is held."""
        assert lock.acquire() is True
        assert lock.acquire() is False

    def test_release_removes_file(self, lock, lock_path):
        """Releasing should remove the lock file."""
        lock.acquire()
        lock.release()
        assert not lock_path.exists()

    def test_release_missing_is_noop(self, lock):
        """Releasing a non-existent lock should not raise."""
        lock.release()  # Should not raise


class TestStaleLock:
    def test_stale_lock_broken(self, lock_path):
        """A stale lock (older than timeout) should be broken automatically."""
        lock = LockFile(lock_path, stale_timeout_minutes=30)
        # Write a stale timestamp
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=60)
        lock_path.write_text(stale_time.isoformat())
        # Should acquire despite existing file
        assert lock.acquire() is True


class TestContextManager:
    def test_context_manager_happy_path(self, lock_path):
        """Context manager should acquire on enter and release on exit."""
        lock = LockFile(lock_path)
        with lock:
            assert lock_path.exists()
        assert not lock_path.exists()

    def test_context_manager_raises_on_failure(self, lock_path):
        """Context manager should raise LockError if acquire fails."""
        lock1 = LockFile(lock_path)
        lock2 = LockFile(lock_path)
        lock1.acquire()
        with pytest.raises(LockError):
            with lock2:
                pass  # Should not reach here


class TestIsLocked:
    def test_is_locked(self, lock, lock_path):
        """is_locked should reflect whether the lock file exists."""
        assert lock.is_locked() is False
        lock.acquire()
        assert lock.is_locked() is True
        lock.release()
        assert lock.is_locked() is False
