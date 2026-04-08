"""Tests for roles_catalog.py"""
from pathlib import Path

import pytest
import yaml

from operations.roles_catalog import resolve_roles_catalog


def test_resolve_all_agents(tmp_path, monkeypatch):
    """Test with enabled: all"""
    agents_dir = tmp_path / "agents" / "role-prompts"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").touch()
    (agents_dir / "debugger.md").touch()
    (agents_dir / "frontend.md").touch()

    config = {
        "roles": {
            "enabled": "all",
            "disabled": [],
            "sources": [
                {"path": "agents/role-prompts", "cli": ["codex"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)
    result = resolve_roles_catalog(config, "codex")

    assert set(result["roles"]) == {"architect", "debugger", "frontend"}
    assert "role-prompts" in result["source_path"]


def test_resolve_filtered_agents(tmp_path, monkeypatch):
    """Test with explicit enabled list"""
    agents_dir = tmp_path / "agents" / "role-prompts"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").touch()
    (agents_dir / "debugger.md").touch()
    (agents_dir / "frontend.md").touch()

    config = {
        "roles": {
            "enabled": ["architect", "debugger"],
            "disabled": [],
            "sources": [
                {"path": "agents/role-prompts", "cli": ["codex"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)
    result = resolve_roles_catalog(config, "codex")

    assert result["roles"] == ["architect", "debugger"]


def test_disabled_takes_precedence(tmp_path, monkeypatch):
    """Test that disabled list overrides enabled"""
    agents_dir = tmp_path / "agents" / "role-prompts"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").touch()
    (agents_dir / "debugger.md").touch()

    config = {
        "roles": {
            "enabled": "all",
            "disabled": ["debugger"],
            "sources": [
                {"path": "agents/role-prompts", "cli": ["codex"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)
    result = resolve_roles_catalog(config, "codex")

    assert result["roles"] == ["architect"]


def test_per_cli_sources(tmp_path, monkeypatch):
    """Test different source paths per CLI"""
    # Claude-specific directory
    claude_dir = tmp_path / "agents" / "claude-subagents"
    claude_dir.mkdir(parents=True)
    (claude_dir / "architect.md").touch()

    # Shared directory
    shared_dir = tmp_path / "agents" / "role-prompts"
    shared_dir.mkdir(parents=True)
    (shared_dir / "debugger.md").touch()

    config = {
        "roles": {
            "enabled": "all",
            "disabled": [],
            "sources": [
                {"path": "agents/claude-subagents", "cli": ["claude"]},
                {"path": "agents/role-prompts", "cli": ["codex", "gemini"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)

    # Claude should see claude-subagents
    claude_result = resolve_roles_catalog(config, "claude")
    assert claude_result["roles"] == ["architect"]
    assert "claude-subagents" in claude_result["source_path"]

    # Codex should see role-prompts
    codex_result = resolve_roles_catalog(config, "codex")
    assert codex_result["roles"] == ["debugger"]
    assert "role-prompts" in codex_result["source_path"]


def test_empty_enabled_list(tmp_path, monkeypatch):
    """Test with empty enabled list"""
    agents_dir = tmp_path / "agents" / "role-prompts"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").touch()

    config = {
        "roles": {
            "enabled": [],
            "disabled": [],
            "sources": [
                {"path": "agents/role-prompts", "cli": ["codex"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)
    result = resolve_roles_catalog(config, "codex")

    assert result["roles"] == []


def test_missing_source_directory(tmp_path, monkeypatch):
    """Test with nonexistent source directory"""
    config = {
        "roles": {
            "enabled": "all",
            "disabled": [],
            "sources": [
                {"path": "agents/nonexistent", "cli": ["codex"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)
    result = resolve_roles_catalog(config, "codex")

    assert result["roles"] == []


def test_disabled_with_explicit_enabled(tmp_path, monkeypatch):
    """Test disabled filter with explicit enabled list"""
    agents_dir = tmp_path / "agents" / "role-prompts"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").touch()
    (agents_dir / "debugger.md").touch()
    (agents_dir / "frontend.md").touch()

    config = {
        "roles": {
            "enabled": ["architect", "debugger", "frontend"],
            "disabled": ["debugger"],
            "sources": [
                {"path": "agents/role-prompts", "cli": ["codex"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)
    result = resolve_roles_catalog(config, "codex")

    # debugger should be excluded even though it's in enabled list
    assert result["roles"] == ["architect", "frontend"]


def test_no_matching_cli_source(tmp_path, monkeypatch):
    """Test when no source matches the CLI name"""
    agents_dir = tmp_path / "agents" / "role-prompts"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").touch()

    config = {
        "roles": {
            "enabled": "all",
            "disabled": [],
            "sources": [
                {"path": "agents/role-prompts", "cli": ["codex", "gemini"]}
            ]
        }
    }

    monkeypatch.setattr("operations.roles_catalog.find_repo_root", lambda: tmp_path)

    # Request for "claude" which is not in the CLI list
    result = resolve_roles_catalog(config, "claude")

    assert result["roles"] == []
    assert result["source_path"] == ""


def test_default_enabled_roles_exist_in_role_prompts():
    """The shipped defaults should not reference missing role prompt files."""
    repo_root = Path(__file__).resolve().parents[2]
    defaults = yaml.safe_load((repo_root / "defaults.yml").read_text(encoding="utf-8"))
    enabled = defaults["roles"]["enabled"]
    role_prompts_dir = repo_root / "agents" / "role-prompts"

    missing = [
        role_name
        for role_name in enabled
        if not (role_prompts_dir / f"{role_name}.md").exists()
    ]

    assert missing == []
