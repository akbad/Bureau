"""Smoke tests for Bureau skill installation."""

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SET_UP_SKILLS = REPO_ROOT / "protocols" / "scripts" / "set-up-skills.sh"


def test_installs_unprefixed_skills_into_shared_agents_dir(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    result = subprocess.run(
        ["bash", str(SET_UP_SKILLS)],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(home),
            "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (home / ".agents" / "skills" / "assess-mode").is_symlink()
    assert not (home / ".agents" / "skills" / "bureau-assess-mode").exists()
    assert not (home / ".gemini" / "skills" / "assess-mode").exists()


def test_replace_mode_overwrites_foreign_symlinks(tmp_path: Path) -> None:
    """In replace mode, foreign symlinks at Bureau skill names are overwritten."""
    home = tmp_path / "home"
    skills_dir = home / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    # Create a foreign symlink (points somewhere Bureau doesn't own)
    foreign_target = tmp_path / "foreign-skill"
    foreign_target.mkdir()
    (skills_dir / "assess-mode").symlink_to(foreign_target)

    result = subprocess.run(
        ["bash", str(SET_UP_SKILLS), "--mode", "replace"],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(home),
            "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    link = skills_dir / "assess-mode"
    assert link.is_symlink()
    # Should now point to Bureau source, not the foreign target
    assert str(foreign_target) not in str(link.resolve())
    assert "Replacing foreign symlink" in result.stderr or "Replacing foreign symlink" in result.stdout


def test_default_mode_skips_foreign_symlinks(tmp_path: Path) -> None:
    """Without replace/sync mode, foreign symlinks are skipped (backward compat)."""
    home = tmp_path / "home"
    skills_dir = home / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    foreign_target = tmp_path / "foreign-skill"
    foreign_target.mkdir()
    (skills_dir / "assess-mode").symlink_to(foreign_target)

    result = subprocess.run(
        ["bash", str(SET_UP_SKILLS)],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(home),
            "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    link = skills_dir / "assess-mode"
    assert link.is_symlink()
    # Should still point to the foreign target (not overwritten)
    assert link.readlink() == foreign_target


def test_leaves_legacy_gemini_skills_dir_untouched(tmp_path: Path) -> None:
    home = tmp_path / "home"
    legacy_skill = home / ".gemini" / "skills" / "bureau-assess-mode"
    legacy_skill.parent.mkdir(parents=True)
    legacy_skill.write_text("legacy")

    result = subprocess.run(
        ["bash", str(SET_UP_SKILLS)],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(home),
            "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert legacy_skill.exists()
