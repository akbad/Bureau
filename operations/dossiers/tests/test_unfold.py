"""Tests for dossier unfold (render for context injection)."""
from pathlib import Path

import pytest

from operations.dossiers.errors import DossierNotFoundError
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

    def test_raises_for_unknown(self, tmp_path: Path):
        """Raises DossierNotFoundError when no match found."""
        with pytest.raises(DossierNotFoundError):
            find_dossier(tmp_path, "nonexistent")


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
        """Rendered output includes session digest when full=True."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="This is the important digest content.",
        )
        output = unfold_dossier(tmp_path, result["hash"], full=True)
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
        """All session digests are included when multiple folds exist and full=True."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="Session 1."
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="codex", digest="Session 2."
        )
        output = unfold_dossier(tmp_path, result["hash"], full=True)
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
        output = unfold_dossier(tmp_path, result["hash"], max_sessions=3, full=True)
        assert "Session 5." in output
        assert "Session 7." in output
        assert "Session 1." not in output
        assert "showing 3 of 7" in output

    def test_raises_on_unknown_dossier(self, tmp_path: Path):
        """Raises FileNotFoundError for unknown dossier."""
        with pytest.raises(FileNotFoundError):
            unfold_dossier(tmp_path, "nonexistent")

    def test_compact_includes_latest_digest_only(self, tmp_path: Path):
        """Compact unfold includes the latest session digest but omits older ones."""
        result = fold_dossier(dossiers_dir=tmp_path, name="Test", agent="a", digest="Old session digest.")
        fold_dossier(dossiers_dir=tmp_path, slug=result["slug"], agent="b", digest="Latest session digest.")
        output = unfold_dossier(tmp_path, "test")  # default full=False

        # latest session digest always rendered under "Latest session context"
        assert "Latest session context" in output
        assert "Latest session digest." in output

        # older session digests are NOT rendered in compact mode
        assert "Session digests" not in output
        assert "Old session digest." not in output

    def test_full_includes_digests(self, tmp_path: Path):
        """Full unfold includes session digests."""
        fold_dossier(dossiers_dir=tmp_path, name="Test", agent="a", digest="My session digest here.")
        output = unfold_dossier(tmp_path, "test", full=True)
        assert "Session digests" in output
        assert "My session digest here" in output

    def test_compact_includes_tasks_and_decisions(self, tmp_path: Path):
        """Compact unfold still includes tasks and decisions."""
        fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "Fix bug"}],
            decisions=[{"what": "Use SQLite", "why": "ACID", "decided_by": "user"}],
        )
        output = unfold_dossier(tmp_path, "test")  # default full=False
        assert "Tasks" in output
        assert "Fix bug" in output
        assert "Decisions" in output
        assert "Use SQLite" in output

    @pytest.mark.parametrize("full", [False, True], ids=["compact", "full"])
    def test_omits_deleted_tasks_from_rendered_tasks_table(
        self,
        tmp_path: Path,
        make_dossier_with_deleted_tasks,
        full: bool,
    ):
        """Deleted tasks should not leak into unfold output in either mode."""
        result = make_dossier_with_deleted_tasks(
            name="Deleted",
            tasks=[
                {"subject": "Live task", "status": "pending"},
                {"subject": "Deleted task", "status": "pending"},
            ],
            delete_ids=(2,),
        )

        output = unfold_dossier(tmp_path, result["hash"], full=full)

        assert "Live task" in output
        assert "Deleted task" not in output

    def test_omits_tasks_section_when_all_tasks_are_deleted(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """The tasks section should disappear when no live tasks remain."""
        result = make_dossier_with_deleted_tasks(
            name="Deleted",
            tasks=[{"subject": "Deleted task", "status": "pending"}],
            delete_ids=(1,),
        )

        output = unfold_dossier(tmp_path, result["hash"])

        assert "## Tasks" not in output
        assert "Deleted task" not in output


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

    def test_task_count_excludes_deleted_tasks(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """List output should count only non-deleted tasks."""
        make_dossier_with_deleted_tasks(
            name="Alpha",
            tasks=[
                {"subject": "Live task 1", "status": "pending"},
                {"subject": "Deleted task", "status": "pending"},
                {"subject": "Live task 2", "status": "completed"},
            ],
            delete_ids=(2,),
        )

        results = list_dossiers(tmp_path)

        assert len(results) == 1
        assert results[0]["tasks"] == 2


class TestFileInteractionRenderWindow:
    """Storage keeps every file row; the render window keeps unfold compact.

    F2 moved retention from write time to render time. These tests pin the
    resulting split: nothing is destroyed, but compact output stays bounded.
    """

    @staticmethod
    def _dossier_with_sessions(tmp_path: Path, count: int) -> str:
        """Fold `count` sessions, each contributing one distinct file row."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Windowed", agent="a", digest="S1.",
            files=[{"path": "/f1.py", "action": "read"}],
        )
        for i in range(2, count + 1):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"S{i}.",
                files=[{"path": f"/f{i}.py", "action": "read"}],
            )
        return result["slug"]

    def test_compact_unfold_windows_to_recent_sessions(self, tmp_path: Path):
        """Compact output shows only the newest `max_sessions` sessions' rows."""
        slug = self._dossier_with_sessions(tmp_path, 7)
        out = unfold_dossier(tmp_path, slug, max_sessions=5)
        # sessions 3-7 are inside the window; 1-2 fall outside it
        for i in range(3, 8):
            assert f"/f{i}.py" in out
        assert "/f1.py" not in out
        assert "/f2.py" not in out

    def test_full_unfold_renders_every_file_row(self, tmp_path: Path):
        """`--full` renders the complete history, proving nothing was deleted."""
        slug = self._dossier_with_sessions(tmp_path, 7)
        out = unfold_dossier(tmp_path, slug, max_sessions=5, full=True)
        for i in range(1, 8):
            assert f"/f{i}.py" in out, f"/f{i}.py was destroyed or not rendered"
