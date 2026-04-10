"""Tests for advisory lock operations."""
from pathlib import Path

import pytest

from operations.dossiers.fold import fold_dossier
from operations.dossiers.lock import claim_lock, release_lock, get_lock_status


def _make_locked_dossier(tmp_path: Path, holder: str = "claude-code") -> str:
    """Create a dossier and claim its advisory lock for the requested holder."""
    result = fold_dossier(
        dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
    )
    claim_lock(tmp_path, result["slug"], agent=holder)
    return result["slug"]


class TestClaimLock:
    def test_claims_unlocked_dossier(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] == "claude-code"
        assert status["locked_at"] is not None

    def test_same_agent_reclaim_succeeds(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] == "claude-code"

    def test_returns_holder_when_already_locked(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        with pytest.raises(ValueError, match="claude-code"):
            claim_lock(tmp_path, result["slug"], agent="codex")


class TestReleaseLock:
    def test_releases_lock(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        release_lock(tmp_path, result["slug"], agent="claude-code")
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] is None

    def test_release_without_agent_or_force_raises(self, tmp_path: Path):
        slug = _make_locked_dossier(tmp_path)

        with pytest.raises(ValueError, match="--agent or --force is required"):
            release_lock(tmp_path, slug)

    def test_release_with_wrong_agent_raises_and_preserves_lock(self, tmp_path: Path):
        slug = _make_locked_dossier(tmp_path, holder="claude-code")

        with pytest.raises(ValueError, match="Lock held by claude-code, not codex"):
            release_lock(tmp_path, slug, agent="codex")

        status = get_lock_status(tmp_path, slug)
        assert status["locked_by"] == "claude-code"

    def test_force_release_succeeds_for_different_agents_lock(self, tmp_path: Path):
        slug = _make_locked_dossier(tmp_path, holder="claude-code")

        release_lock(tmp_path, slug, force=True)

        status = get_lock_status(tmp_path, slug)
        assert status["locked_by"] is None

    def test_release_unlocked_dossier_with_agent_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )

        with pytest.raises(ValueError, match="Lock held by no one, not claude-code"):
            release_lock(tmp_path, result["slug"], agent="claude-code")

    def test_force_release_unlocked_dossier_is_noop(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )

        release_lock(tmp_path, result["slug"], force=True)

        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] is None
