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
