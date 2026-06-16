"""Tests for generated Bureau skills config payloads."""

from pathlib import Path
from runpy import run_path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = run_path(str(REPO_ROOT / "protocols/scripts/generate-skills-config.py"))
BUILD_SKILLS_ENTRIES = MODULE["_build_skills_entries"]


def test_build_skills_entries_emits_name_and_source_path_only(tmp_path: Path, monkeypatch) -> None:
    skills_dir = tmp_path / "skills"
    alpha = skills_dir / "alpha"
    alpha.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

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


def test_build_skills_entries_includes_source_roots_for_cleanup(tmp_path: Path, monkeypatch) -> None:
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

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


def test_build_skills_entries_includes_protocol_owned_code_standards_even_if_not_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    static_skills_dir = tmp_path / "skills"
    generated_skills_dir = tmp_path / "home" / ".config" / "bureau" / "generated" / "skills"
    (static_skills_dir / "alpha").mkdir(parents=True)
    code_standards = generated_skills_dir / "code-standards"
    code_standards.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    payload = BUILD_SKILLS_ENTRIES(
        {
            "skills": {
                "enabled": ["alpha"],
                "disabled": [],
                "sources": [{"path": str(static_skills_dir)}],
            },
            "protocols": {
                "code_standards": "default",
            },
        },
        repo_root=Path("/repo"),
    )

    assert payload["skills"] == [
        {"name": "alpha", "source_path": str(static_skills_dir / "alpha")},
        {"name": "code-standards", "source_path": str(code_standards)},
    ]
    assert str(generated_skills_dir) in payload["source_roots"]


def test_build_skills_entries_ignores_skills_disabled_for_protocol_owned_code_standards(
    tmp_path: Path, monkeypatch
) -> None:
    generated_skills_dir = tmp_path / "home" / ".config" / "bureau" / "generated" / "skills"
    code_standards = generated_skills_dir / "code-standards"
    code_standards.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    payload = BUILD_SKILLS_ENTRIES(
        {
            "skills": {
                "enabled": [],
                "disabled": ["code-standards"],
                "sources": [],
            },
            "protocols": {
                "code_standards": "default",
            },
        },
        repo_root=Path("/repo"),
    )

    assert payload["skills"] == [
        {"name": "code-standards", "source_path": str(code_standards)},
    ]


def test_build_skills_entries_omits_protocol_owned_code_standards_when_disabled(
    tmp_path: Path,
) -> None:
    generated_skills_dir = tmp_path / "generated"
    (generated_skills_dir / "code-standards").mkdir(parents=True)

    payload = BUILD_SKILLS_ENTRIES(
        {
            "skills": {
                "enabled": ["code-standards"],
                "disabled": [],
                "sources": [{"path": str(generated_skills_dir)}],
            },
            "protocols": {
                "code_standards": "off",
            },
        },
        repo_root=Path("/repo"),
    )

    assert payload["skills"] == []
