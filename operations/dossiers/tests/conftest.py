"""Shared fixtures for dossier tests."""
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from operations.dossiers.fold import fold_dossier
from operations.dossiers.tasks import remove_task


@pytest.fixture
def dossiers_dir(tmp_path: Path) -> Path:
    """Return a dedicated dossiers directory for CLI-style tests."""
    path = tmp_path / "dossiers"
    path.mkdir()
    return path


@pytest.fixture
def make_dossier(tmp_path: Path) -> Callable[..., dict[str, str]]:
    """Create a dossier in the current test directory."""

    def _make(
        *,
        name: str = "Test",
        agent: str = "a",
        digest: str = "D.",
        tasks: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        files: list[dict[str, Any]] | None = None,
        project: str | None = None,
        branch: str | None = None,
        commit_hash: str | None = None,
    ) -> dict[str, str]:
        return fold_dossier(
            dossiers_dir=tmp_path,
            name=name,
            agent=agent,
            digest=digest,
            tasks=tasks,
            decisions=decisions,
            files=files,
            project=project,
            branch=branch,
            commit_hash=commit_hash,
        )

    return _make


@pytest.fixture
def make_dossier_with_deleted_tasks(
    tmp_path: Path,
    make_dossier: Callable[..., dict[str, str]],
) -> Callable[..., dict[str, str]]:
    """Create a dossier, then soft-delete selected task IDs via the public API."""

    def _make(*, delete_ids: tuple[int, ...] = (), **kwargs: Any) -> dict[str, str]:
        result = make_dossier(**kwargs)
        for task_id in delete_ids:
            remove_task(tmp_path, result["slug"], task_id)
        return result

    return _make


# ── Identity / registration / cleanup fixtures ──────────────────────────
# These support tests for v2 agent-registration logic. They isolate session
# marker files into tmp_path, let tests stub out process-alive and PID
# lookups, and allow overrides of the config-driven TTL/interval values.


@pytest.fixture
def sessions_root(tmp_path: Path) -> Path:
    """Temp directory root for session marker files, isolated per test."""
    path = tmp_path / "sessions"
    path.mkdir()
    return path


@pytest.fixture
def mock_cli_pid(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Factory: pin `identity._get_cli_process_pid` to a test value.

    Usage:

        def test_something(mock_cli_pid):
            mock_cli_pid(12345)
            ...
    """
    def _set(pid: int) -> None:
        monkeypatch.setattr(
            "operations.dossiers.identity._get_cli_process_pid",
            lambda: pid,
        )
    return _set


@pytest.fixture
def mock_process_alive(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[int, bool]], None]:
    """Factory: pin `identity._process_alive` to return from a PID → alive map.

    Unlisted PIDs default to False (dead).
    """
    def _set(pid_alive_map: dict[int, bool]) -> None:
        monkeypatch.setattr(
            "operations.dossiers.identity._process_alive",
            lambda pid: pid_alive_map.get(pid, False),
        )
    return _set


@pytest.fixture
def set_registration_ttl(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Factory: override the registration TTL seen by inline cleanup."""
    def _set(seconds: int) -> None:
        monkeypatch.setattr(
            "operations.dossiers.db.get_registration_ttl_seconds",
            lambda: seconds,
        )
    return _set


@pytest.fixture
def set_cleanup_check_interval(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Factory: override the cleanup-check throttle interval seen by inline cleanup."""
    def _set(seconds: int) -> None:
        monkeypatch.setattr(
            "operations.dossiers.db.get_cleanup_check_interval_seconds",
            lambda: seconds,
        )
    return _set
