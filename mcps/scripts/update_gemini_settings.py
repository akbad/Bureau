#!/usr/bin/env python3
"""
Helper script to update Gemini settings.json with auto-approved MCP tools.

Usage:
    python3 update_gemini_settings.py <settings_file_path> <tool1> [tool2] [tool3] ...
"""

import json
import sys
from pathlib import Path


def update_gemini_settings(settings_path: str, tools: list[str]) -> None:
    """
    Update Gemini settings.json with auto-approved tools.

    Args:
        settings_path: Path to the settings.json file
        tools: List of tool names to auto-approve
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

    # Ensure autoApprovedTools array exists
    if 'autoApprovedTools' not in settings:
        settings['autoApprovedTools'] = []
        print("Created 'autoApprovedTools' array")

    # Get existing tools
    existing_tools = set(settings['autoApprovedTools'])
    new_tools = set(tools)

    # Add new tools that aren't already in the list
    tools_to_add = new_tools - existing_tools
    if tools_to_add:
        settings['autoApprovedTools'].extend(sorted(tools_to_add))
        settings['autoApprovedTools'].sort()  # Keep sorted for readability
        print(f"Added tools: {', '.join(sorted(tools_to_add))}")
    else:
        print("All specified tools already in autoApprovedTools")

    # Show current list
    print(f"Auto-approved tools: {', '.join(settings['autoApprovedTools'])}")

    # Write updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')  # Add trailing newline

    print(f"Successfully updated {settings_file}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 update_gemini_settings.py <settings_file_path> [tool1] [tool2] ...")
        sys.exit(1)

    settings_path = sys.argv[1]
    tools = sys.argv[2:] if len(sys.argv) > 2 else []

    if not tools:
        print("Warning: No tools specified. Settings file will be created but autoApprovedTools will be empty.")

    update_gemini_settings(settings_path, tools)
