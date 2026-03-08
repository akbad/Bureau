#!/usr/bin/env -S uv run
"""
Helper script to update Codex config.toml with auto-approval settings
(only if the user specifies the appropriate flag in the calling script).

Usage:
    uv run add-codex-auto-approvals.py <config_file_path> [server_name_1] [server_name_2] ...
"""

import sys
from pathlib import Path

import tomlkit


def update_codex_config(config_path: str, auto_approve: list[str] | None = None) -> None:
    """
    Update Codex config.toml with auto-approval settings.

    Args:
        config_path: Path to the config.toml file
        auto_approve: MCP server names to mark as enabled
    """
    config_file = Path(config_path).expanduser()
    auto_approve_set = set(auto_approve or [])

    # Create parent directory if it doesn't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing config or create new document
    if config_file.exists():
        doc = tomlkit.parse(config_file.read_text(encoding="utf-8"))
    else:
        doc = tomlkit.document()

    # 1. Set approval_policy = "never"
    if "approval_policy" in doc:
        print("Updated 'approval_policy' to 'never'")
    else:
        print("Added 'approval_policy = \"never\"'")
    doc["approval_policy"] = "never"

    # 2. Set sandbox_mode = "workspace-write"
    if "sandbox_mode" in doc:
        print("Updated 'sandbox_mode' to 'workspace-write'")
    else:
        print("Added 'sandbox_mode = \"workspace-write\"'")
    doc["sandbox_mode"] = "workspace-write"

    # 3. Ensure [sandbox_workspace_write] section exists with network_access = true
    if "sandbox_workspace_write" not in doc:
        doc["sandbox_workspace_write"] = tomlkit.table()
        print("Added '[sandbox_workspace_write]' section with 'network_access = true'")
    elif "network_access" not in doc["sandbox_workspace_write"]:
        print("Added 'network_access = true' to [sandbox_workspace_write]")
    else:
        print("'network_access' already set to true")
    doc["sandbox_workspace_write"]["network_access"] = True

    # 4. Set enabled = true for specified MCP servers
    if auto_approve_set and "mcp_servers" in doc:
        for server_name in auto_approve_set:
            if server_name in doc["mcp_servers"]:
                doc["mcp_servers"][server_name]["enabled"] = True

    # Write updated config
    config_file.write_text(tomlkit.dumps(doc), encoding="utf-8")
    print(f"Successfully updated {config_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run add-codex-auto-approvals.py <config_file_path> [server_name_1] [server_name_2] ...")
        sys.exit(1)

    config_path = sys.argv[1]
    auto_approve = sys.argv[2:]
    update_codex_config(config_path, auto_approve)
