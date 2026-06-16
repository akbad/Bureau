#!/usr/bin/env -S uv run
from __future__ import annotations

import argparse
from pathlib import Path

from operations.json_config_utils import (
    load_json_config,
    load_json_text,
    save_json_config,
)


def load_json_strict(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return load_json_config(str(path), create_backup=False)


def filter_missing_protocol_instructions(instructions: list[str]) -> list[str]:
    """Drop optional Bureau instructions whose runtime artifacts are disabled."""
    filtered: list[str] = []
    for instruction in instructions:
        path = Path(instruction).expanduser()
        if path.name == "output-style.md" and not path.exists():
            continue
        filtered.append(instruction)
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="Render OpenCode config template")
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--protocols-dir")
    parser.add_argument("--mcp", required=True)
    parser.add_argument("--permissions")
    args = parser.parse_args()

    template_path = Path(args.template)
    output_path = Path(args.output)
    repo_root = args.repo_root
    protocols_dir = args.protocols_dir or ""
    mcp_path = Path(args.mcp)
    permissions_path = Path(args.permissions) if args.permissions else None

    raw = template_path.read_text(encoding="utf-8")
    raw = raw.replace("{{REPO_ROOT}}", repo_root)
    raw = raw.replace("{{PROTOCOLS_DIR}}", protocols_dir)
    data = load_json_text(raw, source=str(template_path))

    instructions = data.get("instructions")
    if isinstance(instructions, list):
        data["instructions"] = filter_missing_protocol_instructions(
            [str(item) for item in instructions]
        )

    data["mcp"] = load_json_strict(mcp_path)

    if permissions_path and permissions_path.exists():
        permissions = load_json_strict(permissions_path)
        data.setdefault("permission", {})
        data["permission"].update(permissions.get("permission", {}))

    save_json_config(str(output_path), data, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
