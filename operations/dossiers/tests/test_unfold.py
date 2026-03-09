"""Tests for dossier unfold (render for context injection)."""
from pathlib import Path

import pytest

from operations.dossiers.fold import fold_dossier
from operations.dossiers.unfold import unfold_dossier, list_dossiers, find_dossier


class TestFindDossier:
    """Tests for finding dossiers by hash or name."""

    def test_find_by_hash(self, tmp_path: Path):
        """Finds dossier by its 6-char hash."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="D."
        )
        found = find_dossier(tmp_path, result["hash"])
        assert found is not None
        assert found.name == f"{result['slug']}.db"

    def test_find_by_name_substring(self, tmp_path: Path):
        """Finds dossier by fuzzy name match."""
        fold_dossier(
            dossiers_dir=tmp_path, name="Auth Refactor", agent="claude-code", digest="D."
        )
        found = find_dossier(tmp_path, "auth-refactor")
        assert found is not None

    def test_returns_none_for_unknown(self, tmp_path: Path):
        """Returns None when no match found."""
        found = find_dossier(tmp_path, "nonexistent")
        assert found is None


class TestUnfoldDossier:
    """Tests for rendering dossier content for injection."""

    def test_output_contains_metadata(self, tmp_path: Path):
        """Rendered output includes metadata section."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="My Project",
            agent="claude-code",
            project="/path/to/repo",
            branch="main",
            digest="Full digest here.",
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "My Project" in output
        assert "/path/to/repo" in output
        assert "main" in output

    def test_output_contains_digest(self, tmp_path: Path):
        """Rendered output includes session digest."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="This is the important digest content.",
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "This is the important digest content." in output

    def test_output_contains_tasks(self, tmp_path: Path):
        """Rendered output includes task table."""
        tasks = [{"subject": "Fix the bug", "status": "pending"}]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="D.",
            tasks=tasks,
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Fix the bug" in output
        assert "pending" in output

    def test_output_contains_decisions(self, tmp_path: Path):
        """Rendered output includes decisions."""
        decisions = [{"what": "Use Rust", "why": "Performance", "decided_by": "user"}]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="D.",
            decisions=decisions,
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Use Rust" in output

    def test_multiple_sessions_rendered(self, tmp_path: Path):
        """All session digests are included when multiple folds exist."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="Session 1."
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="codex", digest="Session 2."
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Session 1." in output
        assert "Session 2." in output

    def test_caps_rendered_sessions(self, tmp_path: Path):
        """Only last N session digests are rendered when max_sessions is set."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="Session 1."
        )
        for i in range(2, 8):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"Session {i}.",
            )
        output = unfold_dossier(tmp_path, result["hash"], max_sessions=3)
        assert "Session 5." in output
        assert "Session 7." in output
        assert "Session 1." not in output
        assert "showing 3 of 7" in output

    def test_raises_on_unknown_dossier(self, tmp_path: Path):
        """Raises FileNotFoundError for unknown dossier."""
        with pytest.raises(FileNotFoundError):
            unfold_dossier(tmp_path, "nonexistent")


class TestListDossiers:
    """Tests for listing all dossiers."""

    def test_lists_all(self, tmp_path: Path):
        """Returns all dossiers sorted by updated_at descending."""
        fold_dossier(dossiers_dir=tmp_path, name="Alpha", agent="a", digest="D.")
        fold_dossier(dossiers_dir=tmp_path, name="Beta", agent="b", digest="D.")
        results = list_dossiers(tmp_path)
        assert len(results) == 2

    def test_empty_directory(self, tmp_path: Path):
        """Returns empty list for empty dossiers directory."""
        results = list_dossiers(tmp_path)
        assert results == []
