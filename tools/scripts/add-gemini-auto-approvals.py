#!/usr/bin/env -S uv run
"""
Helper script to update Gemini settings.json with auto-approved MCP tools
(only if the user specifies the appropriate flag in the calling script).

Usage:
    uv run add-gemini-auto-approvals.py <settings_file_path> <tool1> [tool2] [tool3] ... \\
        [--bash-allow "<prefix>"] [--bash-deny "<prefix>"]
"""

from operations.approval_rules import build_gemini_bash_rules
from operations.json_config_utils import load_json_config, save_json_config


def update_gemini_settings(
    settings_path: str,
    tools: list[str],
    bash_allow: list[str] | None = None,
    bash_deny: list[str] | None = None,
) -> None:
    """
    Update Gemini settings.json with auto-approved tools.

    Args:
        settings_path: Path to the settings.json file
        tools: List of tool names to auto-approve
    """
    # Load existing settings or start with empty dict
    settings = load_json_config(settings_path, default={})

    if tools:
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

    if 'tools' not in settings:
        settings['tools'] = {}
    if 'core' not in settings['tools']:
        settings['tools']['core'] = []
    if 'exclude' not in settings['tools']:
        settings['tools']['exclude'] = []

    for rule in build_gemini_bash_rules(bash_allow or []):
        if rule not in settings['tools']['core']:
            settings['tools']['core'].append(rule)

    for rule in build_gemini_bash_rules(bash_deny or []):
        if rule not in settings['tools']['exclude']:
            settings['tools']['exclude'].append(rule)

    if tools:
        # Show current list
        print(f"Auto-approved tools: {', '.join(settings['autoApprovedTools'])}")

    # Write updated settings
    save_json_config(settings_path, settings)
    print(f"Successfully updated {settings_path}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Update Gemini settings.json with MCP auto-approvals and Bash restrictions."
    )
    parser.add_argument("settings_path", help="Path to Gemini settings.json")
    parser.add_argument("tools", nargs="*", help="MCP tools to auto-approve")
    parser.add_argument("--bash-allow", action="append", default=[], help="Bash prefix to allow")
    parser.add_argument("--bash-deny", action="append", default=[], help="Bash prefix to deny")
    args = parser.parse_args()

    update_gemini_settings(
        args.settings_path,
        args.tools,
        bash_allow=args.bash_allow,
        bash_deny=args.bash_deny,
    )
