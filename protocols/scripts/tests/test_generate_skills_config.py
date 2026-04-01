"""Tests for generated Bureau skills config payloads."""

from pathlib import Path
from runpy import run_path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = run_path(str(REPO_ROOT / "protocols/scripts/generate-skills-config.py"))
BUILD_SKILLS_ENTRIES = MODULE["_build_skills_entries"]


def test_build_skills_entries_emits_name_and_source_path_only(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    alpha = skills_dir / "alpha"
    alpha.mkdir(parents=True)

    payload = BUILD_SKILLS_ENTRIES(
        {
            "skills": {
                "enabled": ["alpha"],
                "disabled": [],
                "sources": [{"path": str(skills_dir)}],
            }
        },
        repo_root=Path("/repo"),
    )

    assert payload == {
        "skills": [{"name": "alpha", "source_path": str(alpha)}],
        "source_roots": [str(skills_dir)],
    }


def test_build_skills_entries_includes_source_roots_for_cleanup(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha").mkdir(parents=True)

    payload = BUILD_SKILLS_ENTRIES(
        {
            "skills": {
                "enabled": ["alpha"],
                "disabled": [],
                "sources": [{"path": str(skills_dir)}],
            }
        },
        repo_root=Path("/repo"),
    )

    assert payload["source_roots"] == [str(skills_dir)]
