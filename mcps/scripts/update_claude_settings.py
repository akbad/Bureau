#!/usr/bin/env python3
"""
Helper script to update Claude Code settings.json with MCP auto-approval configuration.

Usage:
    python3 update_claude_settings.py <settings_file_path>

This script:
1. Creates the settings file if it doesn't exist
2. Merges in the MCP auto-approval permissions
3. Preserves existing settings
"""

import json
import sys
from pathlib import Path


def update_claude_settings(settings_path: str) -> None:
    """
    Update Claude settings.json with MCP auto-approval configuration.

    Args:
        settings_path: Path to the settings.json file
    """
    settings_file = Path(settings_path).expanduser()

    # Create parent directory if it doesn't exist
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing settings or start with empty dict
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {settings_file} contains invalid JSON. Creating backup and starting fresh.")
            backup_path = settings_file.with_suffix('.json.backup')
            settings_file.rename(backup_path)
            settings = {}
    else:
        settings = {}

    # Ensure permissions structure exists
    if 'permissions' not in settings:
        settings['permissions'] = {}

    if 'allow' not in settings['permissions']:
        settings['permissions']['allow'] = []

    # Add MCP wildcard if not already present
    mcp_pattern = "mcp__*"
    if mcp_pattern not in settings['permissions']['allow']:
        settings['permissions']['allow'].append(mcp_pattern)
        print(f"Added '{mcp_pattern}' to permissions.allow")
    else:
        print(f"'{mcp_pattern}' already in permissions.allow")

    # Add enableAllProjectMcpServers if not already set
    if 'enableAllProjectMcpServers' not in settings:
        settings['enableAllProjectMcpServers'] = True
        print("Added 'enableAllProjectMcpServers': true")
    else:
        print(f"'enableAllProjectMcpServers' already set to: {settings['enableAllProjectMcpServers']}")

    # Write updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')  # Add trailing newline

    print(f"Successfully updated {settings_file}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 update_claude_settings.py <settings_file_path>")
        sys.exit(1)

    settings_path = sys.argv[1]
    update_claude_settings(settings_path)
