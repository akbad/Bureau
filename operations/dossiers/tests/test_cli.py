"""Tests for CLI entry point (integration tests)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def dossiers_dir(tmp_path: Path) -> Path:
    d = tmp_path / "dossiers"
    d.mkdir()
    return d


class TestCliFold:
    def test_fold_creates_dossier(self, dossiers_dir: Path, tmp_path: Path):
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("Test digest content.")
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--name", "CLI Test",
                "--agent", "claude-code",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Dossier saved:" in result.stdout
        # Should have created a .db file
        db_files = list(dossiers_dir.glob("*.db"))
        assert len(db_files) == 1


class TestCliUnfold:
    def test_unfold_renders_context(self, dossiers_dir: Path, tmp_path: Path):
        # First, fold something
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("Important context here.")
        fold_result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--name", "CLI Test",
                "--agent", "claude-code",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert fold_result.returncode == 0, fold_result.stderr
        # Extract slug from output: "Dossier saved: `<slug>` (..."
        import re as _re
        slug_match = _re.search(r"`([^`]+)`", fold_result.stdout)
        assert slug_match, f"Could not parse slug from: {fold_result.stdout}"
        slug = slug_match.group(1)

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Important context here." in result.stdout


class TestCliList:
    def test_list_empty(self, dossiers_dir: Path):
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "list",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_list_json_format(self, dossiers_dir: Path, tmp_path: Path):
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("D.")
        subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold", "--name", "Test", "--agent", "a",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "list", "--format", "json",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
