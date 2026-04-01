#!/usr/bin/env -S uv run
"""
Update Codex config.toml with auto-approval settings and per-tool approval
entries derived from the Bureau setup plan.

Usage:
    uv run add-codex-auto-approvals.py <config_file_path> [--plan <plan.json>] [server_name ...]
"""

import argparse
import json
import sys
from pathlib import Path

import tomlkit


def update_codex_config(
    config_path: str,
    auto_approve: list[str] | None = None,
    plan_path: str | None = None,
) -> None:
    """
    Update Codex config.toml with auto-approval settings.

    Args:
        config_path: Path to the config.toml file
        auto_approve: MCP server names to mark as enabled
        plan_path: Optional path to setup plan JSON (supplies per-tool approval lists)
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

    # 5. Set per-tool approval_mode for Codex-managed MCP tools
    codex_tools: dict[str, list[str]] = {}
    if plan_path:
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        codex_tools = (
            plan.get("auto_approved", {})
                .get("mcp_servers", {})
                .get("codex_tools", {})
        )

    if codex_tools and "mcp_servers" in doc:
        for server_name, tools in codex_tools.items():
            if server_name not in doc["mcp_servers"]:
                continue
            server_table = doc["mcp_servers"][server_name]
            if "tools" not in server_table:
                server_table["tools"] = tomlkit.table()
            for tool_name in tools:
                if tool_name not in server_table["tools"]:
                    server_table["tools"][tool_name] = tomlkit.table()
                server_table["tools"][tool_name]["approval_mode"] = "approve"
        tool_count = sum(len(t) for t in codex_tools.values())
        server_count = sum(
            1 for s in codex_tools if s in doc["mcp_servers"]
        )
        print(f"Set per-tool approval for {tool_count} tools across {server_count} servers")

    # Write updated config
    config_file.write_text(tomlkit.dumps(doc), encoding="utf-8")
    print(f"Successfully updated {config_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update Codex config.toml with auto-approval settings",
    )
    parser.add_argument("config_path", help="Path to the config.toml file")
    parser.add_argument(
        "--plan",
        dest="plan_path",
        default=None,
        help="Path to setup plan JSON (supplies per-tool approval lists)",
    )
    parser.add_argument(
        "servers",
        nargs="*",
        help="MCP server names to mark as enabled",
    )

    args = parser.parse_args()
    update_codex_config(args.config_path, args.servers, args.plan_path)
