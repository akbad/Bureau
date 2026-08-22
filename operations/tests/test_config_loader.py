"""Tests for the four-tier config loader (defaults → .bureau.yml → local.yml → env vars).

Validates:
- find_project_config() CWD walk-up and Bureau-repo-root exclusion
- Merge precedence across all four tiers
- YAML anchor resolution in the real defaults.yml
"""

import yaml
import pytest
from pathlib import Path

from operations.config_loader import (
    find_project_config,
    find_repo_root,
    get_config,
    clear_config_cache,
)


# ─────────────────────────────────────────────────────────────────────────────
# find_project_config() tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFindProjectConfig:
    """Tests for .bureau.yml discovery via CWD walk-up."""

    def test_find_project_config_in_cwd(self, tmp_path, monkeypatch):
        """Should find .bureau.yml when it exists in the current working directory."""
        bureau_yml = tmp_path / ".bureau.yml"
        bureau_yml.write_text("agents: [claude]\n")

        # point find_repo_root away so Bureau-repo-root exclusion doesn't trigger
        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path / "_not_a_repo",
        )
        monkeypatch.chdir(tmp_path)

        result = find_project_config()

        assert result is not None
        assert result.resolve() == bureau_yml.resolve()

    def test_find_project_config_walks_up(self, tmp_path, monkeypatch):
        """Should find .bureau.yml in a parent directory when cwd is a child."""
        bureau_yml = tmp_path / ".bureau.yml"
        bureau_yml.write_text("agents: [claude]\n")

        child = tmp_path / "deep" / "nested" / "dir"
        child.mkdir(parents=True)

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path / "_not_a_repo",
        )
        monkeypatch.chdir(child)

        result = find_project_config()

        assert result is not None
        assert result.resolve() == bureau_yml.resolve()

    def test_find_project_config_returns_none_when_absent(self, tmp_path, monkeypatch):
        """Should return None when no .bureau.yml exists anywhere in the hierarchy."""
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path / "_not_a_repo",
        )
        monkeypatch.chdir(child)

        result = find_project_config()

        assert result is None

    def test_find_project_config_skips_bureau_repo_root(self, tmp_path, monkeypatch):
        """Should skip .bureau.yml at the Bureau repo root to avoid self-referencing."""
        # Simulate Bureau repo root (where defaults.yml lives)
        (tmp_path / "defaults.yml").write_text("agents: [claude]\n")
        (tmp_path / ".bureau.yml").write_text("agents: [gemini]\n")

        # find_repo_root returns this dir, so find_project_config should skip it
        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.chdir(tmp_path)

        result = find_project_config()

        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Four-tier merge precedence tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMergePrecedence:
    """Tests that later config tiers override earlier ones."""

    def _write_yaml(self, path: Path, data: dict) -> None:
        """Helper: dump a dict to a YAML file."""
        path.write_text(yaml.dump(data, default_flow_style=False))

    def test_defaults_provides_base_values(self, tmp_path, monkeypatch):
        """Values from defaults.yml should appear when no overrides exist."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "cleanup": {"min_interval": "48h"},
        })

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        # ensure no .bureau.yml is found
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: None,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["cleanup"]["min_interval"] == "48h"

    def test_bureau_yml_overrides_defaults(self, tmp_path, monkeypatch):
        """.bureau.yml values should override defaults.yml."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "cleanup": {"min_interval": "48h"},
        })
        bureau_yml = tmp_path / "project" / ".bureau.yml"
        bureau_yml.parent.mkdir()
        self._write_yaml(bureau_yml, {
            "cleanup": {"min_interval": "12h"},
        })

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: bureau_yml,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["cleanup"]["min_interval"] == "12h"

    def test_local_yml_overrides_bureau_yml(self, tmp_path, monkeypatch):
        """local.yml values should override .bureau.yml."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "cleanup": {"min_interval": "48h"},
        })
        bureau_yml = tmp_path / "project" / ".bureau.yml"
        bureau_yml.parent.mkdir()
        self._write_yaml(bureau_yml, {
            "cleanup": {"min_interval": "12h"},
        })
        self._write_yaml(tmp_path / "local.yml", {
            "cleanup": {"min_interval": "1h"},
        })

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: bureau_yml,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["cleanup"]["min_interval"] == "1h"

    def test_full_four_tier_precedence(self, tmp_path, monkeypatch):
        """local.yml should win when all three files set the same key."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "trash": {"grace_period": "90d"},
        })
        bureau_yml = tmp_path / "project" / ".bureau.yml"
        bureau_yml.parent.mkdir()
        self._write_yaml(bureau_yml, {
            "trash": {"grace_period": "60d"},
        })
        self._write_yaml(tmp_path / "local.yml", {
            "trash": {"grace_period": "7d"},
        })

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: bureau_yml,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["trash"]["grace_period"] == "7d"

    def test_protocol_document_settings_can_be_overridden(self, tmp_path, monkeypatch):
        """protocols.* document settings should follow normal four-tier merge precedence."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "protocols": {
                "mode": "replace",
                "output_style": "default",
                "code_standards": "default",
            },
        })
        self._write_yaml(tmp_path / "local.yml", {
            "protocols": {
                "output_style": ["~/custom-style.md", "/tmp/extra-style.md"],
                "code_standards": "off",
            },
        })

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: None,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["protocols"]["mode"] == "replace"
        assert config["protocols"]["output_style"] == ["~/custom-style.md", "/tmp/extra-style.md"]
        assert config["protocols"]["code_standards"] == "off"

    def test_protocols_mode_can_be_overridden(self, tmp_path, monkeypatch):
        """protocols.mode should merge like other nested config values."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "protocols": {"mode": "replace"},
        })
        self._write_yaml(tmp_path / "local.yml", {
            "protocols": {"mode": "sync"},
        })

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: None,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["protocols"]["mode"] == "sync"

    def test_bureau_workspace_env_overrides_workspace_and_derived_serena_root(
        self,
        tmp_path,
        monkeypatch,
    ):
        """BUREAU_WORKSPACE should override the top-level workspace anchor."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "workspace": "~/code",
            "path_to": {
                "mcp_clones": "/tmp/mcp-clones",
            },
        })
        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: None,
        )
        monkeypatch.setenv("BUREAU_WORKSPACE", "/tmp/bureau-workspace")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        # the override now targets the top-level workspace, and serena_memories_root
        # is derived from it (still kept under path_to for get_path consumers)
        assert config["workspace"] == "/tmp/bureau-workspace"
        assert config["path_to"]["serena_memories_root"] == "/tmp/bureau-workspace"

    def test_relative_bureau_repo_resolves_from_active_repo_root(self, tmp_path, monkeypatch):
        """path_to.bureau_repo should point at the worktree with pyproject.toml."""
        self._write_yaml(tmp_path / "defaults.yml", {
            "path_to": {
                "workspace": "~/code",
                "mcp_clones": ".mcp-servers",
                "bureau_repo": ".",
            },
        })
        main_repo_root = tmp_path.parent / ".bare"

        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: None,
        )
        monkeypatch.setattr(
            "operations.config_loader.get_main_repo_root",
            lambda: main_repo_root,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()

        config = get_config()

        assert config["path_to"]["bureau_repo"] == str(tmp_path)
        assert config["path_to"]["mcp_clones"] == str(main_repo_root / ".mcp-servers")


# ─────────────────────────────────────────────────────────────────────────────
# workspace promotion + agent_access parsing
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkspacePromotionAndAgentAccess:
    """Top-level workspace anchor, derivation, the back-compat shim, agent_access."""

    def _write_yaml(self, path: Path, data: dict) -> None:
        path.write_text(yaml.dump(data, default_flow_style=False))

    def _load(self, tmp_path, monkeypatch, data: dict):
        """Write data as defaults.yml, isolate discovery, return the merged config."""
        self._write_yaml(tmp_path / "defaults.yml", data)
        monkeypatch.setattr(
            "operations.config_loader.find_repo_root",
            lambda *_a, **_kw: tmp_path,
        )
        monkeypatch.setattr(
            "operations.config_loader.find_project_config",
            lambda: None,
        )
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        return get_config()

    def test_top_level_workspace_round_trips(self, tmp_path, monkeypatch):
        """A top-level workspace key should survive the load as-is."""
        config = self._load(tmp_path, monkeypatch, {"workspace": "/srv/code"})

        assert config["workspace"] == "/srv/code"

    def test_serena_memories_root_derived_from_workspace_when_unset(self, tmp_path, monkeypatch):
        """serena_memories_root should be derived from the top-level workspace when absent."""
        config = self._load(tmp_path, monkeypatch, {"workspace": "/srv/code"})

        assert config["path_to"]["serena_memories_root"] == "/srv/code"

    def test_explicit_serena_memories_root_is_not_overridden(self, tmp_path, monkeypatch):
        """An explicitly-configured serena_memories_root must not be clobbered by derivation."""
        config = self._load(tmp_path, monkeypatch, {
            "workspace": "/srv/code",
            "path_to": {"serena_memories_root": "/custom/serena"},
        })

        assert config["path_to"]["serena_memories_root"] == "/custom/serena"

    def test_back_compat_shim_mirrors_workspace_into_path_to(self, tmp_path, monkeypatch):
        """The temporary shim should mirror the top-level workspace into path_to.workspace.

        Keeps ${path_to.workspace} (the Filesystem MCP whitelist) resolving until
        Step 2 removes that block. Remove this test when the shim is deleted.
        """
        config = self._load(tmp_path, monkeypatch, {"workspace": "/srv/code"})

        assert config["path_to"]["workspace"] == "/srv/code"

    def test_agent_access_paths_parsed(self, tmp_path, monkeypatch):
        """agent_access.paths entries should load with their enabled/path shape intact."""
        config = self._load(tmp_path, monkeypatch, {
            "workspace": "/srv/code",
            "agent_access": {
                "paths": {
                    "bureau_config": {"enabled": True, "path": "~/.config/bureau"},
                    "workspace": {"enabled": False, "path": "${workspace}"},
                },
            },
        })

        paths = config["agent_access"]["paths"]
        assert paths["bureau_config"] == {"enabled": True, "path": "~/.config/bureau"}
        assert paths["workspace"] == {"enabled": False, "path": "${workspace}"}
