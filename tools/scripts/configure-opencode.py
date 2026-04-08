#!/usr/bin/env -S uv run
"""
Merge OpenCode config: fill missing keys from generated template into user config,
preserving existing user overrides.
"""

import argparse
import sys
from pathlib import Path

from operations import json_config_utils as cu


LEGACY_BUREAU_INSTRUCTIONS = {
    "/repo/protocols/context/static/tools-guide.md",
    "/repo/protocols/context/static/handoff-guide.md",
}

LEGACY_BUREAU_AGENT_PROMPT_MARKERS = (
    "/.config/opencode/agent/bureau-agents/",
    "/agents/role-prompts/",
)


def _is_bureau_instruction(path: str) -> bool:
    """Identify Bureau-managed instruction entries across current and legacy layouts."""
    return (
        path in LEGACY_BUREAU_INSTRUCTIONS
        or path.endswith("/.config/bureau/protocols/output-style.md")
        or path.endswith("/.config/bureau/protocols/ops-hub.md")
        or path.endswith("/protocols/context/static/tools-guide.md")
        or path.endswith("/protocols/context/static/handoff-guide.md")
    )


def reconcile_instructions(existing: list[str], managed: list[str], remove: bool = False) -> list[str]:
    """Keep user entries while replacing or removing Bureau-managed instructions."""
    extras = [path for path in existing if not _is_bureau_instruction(path)]
    if remove:
        return extras
    return list(managed) + extras


def _is_bureau_agent_entry(config: object) -> bool:
    """Identify Bureau-managed OpenCode agent entries across current and legacy layouts."""
    if not isinstance(config, dict):
        return False

    description = config.get("description")
    if isinstance(description, str) and description.startswith("Bureau agent:"):
        return True

    prompt = config.get("prompt")
    return isinstance(prompt, str) and any(
        marker in prompt for marker in LEGACY_BUREAU_AGENT_PROMPT_MARKERS
    )


def reconcile_agents(
    existing: dict[str, object],
    managed: dict[str, object],
    remove: bool = False,
) -> dict[str, object]:
    """Keep user-defined agents while replacing or removing Bureau-managed agents."""
    extras = {
        name: config
        for name, config in existing.items()
        if not _is_bureau_agent_entry(config)
    }
    if remove:
        return extras
    return {**managed, **extras}


def merge_missing(base: dict, add: dict, parent_key: str = "") -> dict:
    """
    Merge 'add' into 'base', filling missing keys and skipping existing ones.

    EXCEPTION: MCP startup command arrays are always overwritten.
    """
    for k, v in add.items():
        is_mcp_command = parent_key == "mcp" and k == "command"

        if k not in base or base[k] is None or is_mcp_command:
            base[k] = v
        elif isinstance(base[k], dict) and isinstance(v, dict):
            # For MCP server entries, pass the key so nested merge knows context
            ctx = "mcp" if parent_key == "mcp" or k == "mcp" else parent_key
            merge_missing(base[k], v, parent_key=ctx)
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Path to user OpenCode config (will be created/updated)")
    parser.add_argument("--generated", required=True, help="Path to generated OpenCode template")
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Remove Bureau-managed instruction entries instead of syncing them",
    )
    args = parser.parse_args()

    target_path = Path(args.target).expanduser()
    generated_path = Path(args.generated).expanduser()

    if not generated_path.exists():
        print(f"Generated config not found: {generated_path}", file=sys.stderr)
        return 1

    generated_cfg = cu.load_json_config(str(generated_path), default={}, create_backup=False)
    target_cfg = cu.load_json_config(str(target_path), default={}, create_backup=True)

    merged = merge_missing(target_cfg, generated_cfg)
    existing_instructions = target_cfg.get("instructions", [])
    managed_instructions = generated_cfg.get("instructions", [])
    if isinstance(existing_instructions, list) and isinstance(managed_instructions, list):
        merged["instructions"] = reconcile_instructions(
            [str(path) for path in existing_instructions],
            [str(path) for path in managed_instructions],
            remove=args.bare,
        )

    existing_agents = target_cfg.get("agent", {})
    managed_agents = generated_cfg.get("agent", {})
    if isinstance(existing_agents, dict) and isinstance(managed_agents, dict):
        merged["agent"] = reconcile_agents(
            existing_agents,
            managed_agents,
            remove=args.bare,
        )
    cu.save_json_config(str(target_path), merged, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
