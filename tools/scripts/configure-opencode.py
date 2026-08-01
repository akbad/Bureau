#!/usr/bin/env -S uv run
"""
Merge OpenCode config: fill missing keys from generated template into user config,
preserving existing user overrides.
"""

import argparse
import sys
from pathlib import Path

from operations import json_config_utils as cu


# prefix for the machine-readable final stdout line that reports which MCP ids this
# run wrote; set-up-tools.sh extracts everything after it. A marker (rather than a
# bare last line) keeps extraction unambiguous when the CSV is empty and earlier
# stdout lines exist (e.g. load_json_config's invalid-JSON warnings). See C6.
OC_WRITTEN_MARKER = "__BUREAU_OC_WRITTEN__:"


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


def newly_written_mcp_ids(original_mcp: object, generated_mcp: object) -> list[str]:
    """Return the MCP server ids this run newly created in the OpenCode config.

    An id is Bureau-written only if it was absent (or null) in the user's config
    before the merge. `merge_missing` preserves a pre-existing entry (overwriting
    only its `command`), so a pre-existing id — which may be the user's own — must
    NOT be reported as Bureau-written; otherwise a later prune keyed off the
    registry could delete the user's entry (issue C6). This gives OpenCode's
    separate merge path the same write-confirmed ownership signal that Claude and
    Codex get from the per-agent add loop.

    Args:
        `original_mcp`: the `mcp` table from the user's config BEFORE the merge.
        `generated_mcp`: the `mcp` table from Bureau's generated template.

    Returns:
        Sorted ids in `generated_mcp` that were absent or null in `original_mcp`.
    """
    original = original_mcp if isinstance(original_mcp, dict) else {}
    generated = generated_mcp if isinstance(generated_mcp, dict) else {}
    return sorted(
        server_id
        for server_id in generated
        if server_id not in original or original.get(server_id) is None
    )


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

    # snapshot the user's MCP ids BEFORE merge_missing mutates target_cfg in place,
    # so we can report which MCP servers this run actually created (issue C6 below)
    original_mcp = target_cfg.get("mcp")
    original_mcp = dict(original_mcp) if isinstance(original_mcp, dict) else {}

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

    # report the newly-written MCP ids so set-up-tools.sh can hand ONLY
    # Bureau-authored entries to the registry recorder — a pre-existing (possibly
    # user-owned) entry must never be recorded as Bureau's (issue C6). A marker
    # prefix makes the value unambiguous to extract even when the CSV is empty and
    # `load_json_config` printed invalid-JSON warnings to stdout ahead of it.
    written = newly_written_mcp_ids(original_mcp, generated_cfg.get("mcp"))
    print(f"{OC_WRITTEN_MARKER}{','.join(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
