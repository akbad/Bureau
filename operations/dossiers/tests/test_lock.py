"""Tests for advisory lock operations."""
import sqlite3
from pathlib import Path

import pytest

from operations.dossiers.fold import fold_dossier
from operations.dossiers.lock import claim_lock, release_lock, get_lock_status


class TestClaimLock:
    def test_claims_unlocked_dossier(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D."
        )
        claim_lock(tmp_path, result["slug"], agent="claude-code")
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] == "claude-code"
        assert status["locked_at"] is not None

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
        release_lock(tmp_path, result["slug"])
        status = get_lock_status(tmp_path, result["slug"])
        assert status["locked_by"] is None
