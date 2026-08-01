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
# These support tests for v3 single-store agent-registration logic: they let
# tests stub out the self-pid resolution and the liveness oracle, and override
# the config-driven TTL/interval values.


@pytest.fixture
def mock_cli_pid(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Factory: pin `identity._get_cli_process_pid` to a test value.

    `_get_cli_process_pid` is defined in `identity` and imported by name into
    `tasks` (which stamps a worker's pid at `claim_task`), so both bindings are
    patched — same reason `mock_process_alive` patches two namespaces. A
    module-level `from ... import` binds the function object, not the module
    attribute, so patching only the definition site would leave `tasks` calling
    the real one.

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
        monkeypatch.setattr(
            "operations.dossiers.tasks._get_cli_process_pid",
            lambda: pid,
        )
    return _set


@pytest.fixture
def mock_process_alive(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[int, bool]], None]:
    """Factory: pin the liveness oracle to return from a PID → alive map.

    `_process_alive` lives in `db` and is imported by `identity`; both
    resolve_identity (identity's namespace) and cleanup (db's namespace) call
    it, so both bindings are patched. Unlisted PIDs default to False (dead),
    and None (a worker without a cli_pid) is always dead.
    """
    def _set(pid_alive_map: dict[int, bool]) -> None:
        def _alive(pid: int | None) -> bool:
            return False if pid is None else pid_alive_map.get(pid, False)
        monkeypatch.setattr("operations.dossiers.db._process_alive", _alive)
        monkeypatch.setattr("operations.dossiers.identity._process_alive", _alive)
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
