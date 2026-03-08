from importlib import util
from pathlib import Path

import pytest
import tomlkit

module_path = Path(__file__).resolve().parents[1] / "add-codex-auto-approvals.py"
spec = util.spec_from_file_location("add_codex_auto_approvals", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
update_codex_config = module.update_codex_config


class TestCodexAutoApprovals:
    """Tests for Codex TOML auto-approval script"""

    def test_empty_file_adds_all_settings(self, tmp_path):
        """Starting from empty file should add all required settings"""
        config_path = tmp_path / "config.toml"
        config_path.write_text("", encoding="utf-8")

        update_codex_config(str(config_path), [])

        content = config_path.read_text(encoding="utf-8")
        doc = tomlkit.parse(content)

        assert doc["approval_policy"] == "never"
        assert doc["sandbox_mode"] == "workspace-write"
        assert "sandbox_workspace_write" in doc
        assert doc["sandbox_workspace_write"]["network_access"] is True

    @pytest.mark.parametrize("setting,initial,expected", [
        ("approval_policy", '"on-request"', "never"),
        ("sandbox_mode", '"readonly"', "workspace-write"),
    ])
    def test_updates_existing_setting(self, tmp_path, setting, initial, expected):
        """Should update existing top-level settings to required values"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(f'{setting} = {initial}\n', encoding="utf-8")

        update_codex_config(str(config_path), [])

        doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        assert doc[setting] == expected

    def test_adds_network_access_to_existing_sandbox_section(self, tmp_path):
        """Should add network_access while preserving other settings in section"""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[sandbox_workspace_write]
some_other_setting = true
""".lstrip(), encoding="utf-8")

        update_codex_config(str(config_path), [])

        doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        assert doc["sandbox_workspace_write"]["network_access"] is True
        assert doc["sandbox_workspace_write"]["some_other_setting"] is True

    def test_sets_enabled_true_for_auto_approved_servers(self, tmp_path):
        """Should add enabled=true only for servers in auto-approve list"""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[mcp_servers.alpha]
url = "http://example.com"

[mcp_servers.beta]
url = "http://example.com"
enabled = false

[mcp_servers.gamma]
url = "http://example.com"
""".lstrip(), encoding="utf-8")

        update_codex_config(str(config_path), ["alpha", "beta"])

        doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        assert doc["mcp_servers"]["alpha"]["enabled"] is True
        assert doc["mcp_servers"]["beta"]["enabled"] is True
        assert doc["mcp_servers"]["gamma"].get("enabled") is None  # Not in list

    def test_preserves_other_mcp_server_settings(self, tmp_path):
        """Should preserve existing settings when adding enabled=true"""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[mcp_servers.complex]
url = "http://example.com"
timeout = 30
custom_header = "Bearer token"
""".lstrip(), encoding="utf-8")

        update_codex_config(str(config_path), ["complex"])

        doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        server = doc["mcp_servers"]["complex"]
        assert server["enabled"] is True
        assert server["url"] == "http://example.com"
        assert server["timeout"] == 30
        assert server["custom_header"] == "Bearer token"

    def test_handles_empty_auto_approve_list(self, tmp_path):
        """Should add core settings but not modify servers when list is empty"""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[mcp_servers.test]
url = "http://example.com"
""".lstrip(), encoding="utf-8")

        update_codex_config(str(config_path), [])

        doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        assert doc["approval_policy"] == "never"
        assert doc["mcp_servers"]["test"].get("enabled") is None

    def test_creates_config_file_if_missing(self, tmp_path):
        """Should create config file and parent directories if they don't exist"""
        config_path = tmp_path / "nested" / "path" / "config.toml"

        update_codex_config(str(config_path), [])

        assert config_path.exists()
        doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        assert doc["approval_policy"] == "never"

    def test_preserves_comments(self, tmp_path):
        """Should preserve existing comments in the config file (key tomlkit feature)"""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
# This is a header comment
approval_policy = "on-request"  # inline comment

[mcp_servers.test]
# Server comment
url = "http://example.com"
""".lstrip(), encoding="utf-8")

        update_codex_config(str(config_path), ["test"])

        content = config_path.read_text(encoding="utf-8")
        assert "# This is a header comment" in content
        assert "# inline comment" in content
        assert "# Server comment" in content

        doc = tomlkit.parse(content)
        assert doc["approval_policy"] == "never"
        assert doc["mcp_servers"]["test"]["enabled"] is True
