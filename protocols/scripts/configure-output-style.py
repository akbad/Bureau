#!/usr/bin/env -S uv run
"""Compile Bureau output styles and manage Claude Code's native style wrapper."""

from __future__ import annotations

import argparse
from pathlib import Path

from operations import json_config_utils as cu

CLAUDE_STYLE_NAME = "Bureau"
CLAUDE_STYLE_FILE = "bureau.md"


def compile_output_style(sources: list[Path], destination: Path) -> None:
    """Compile ordered source files into one runtime artifact."""
    if not sources:
        raise SystemExit("At least one output style source is required")

    destination.parent.mkdir(parents=True, exist_ok=True)

    preamble_lines = [
        "<!-- Bureau-generated output style",
        "Source files:",
    ]
    preamble_lines.extend(f"- {source}" for source in sources)
    preamble_lines.extend(
        [
            "Do not edit this runtime artifact directly.",
            "-->",
            "",
        ]
    )

    body_parts: list[str] = []
    for index, source in enumerate(sources):
        body_parts.append(source.read_text(encoding="utf-8"))
        if index < len(sources) - 1:
            body_parts.append("\n\n<!-- Bureau source boundary -->\n\n")

    destination.write_text("\n".join(preamble_lines) + "".join(body_parts), encoding="utf-8")


def _render_claude_output_style(runtime_body: str) -> str:
    frontmatter = [
        "---",
        f"name: {CLAUDE_STYLE_NAME}",
        "description: Bureau-managed output style",
        "keep-coding-instructions: true",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + runtime_body


def install_claude_output_style(runtime_path: Path, styles_dir: Path, settings_path: Path) -> None:
    """Install the Bureau runtime style as Claude's selected native output style."""
    runtime_body = runtime_path.read_text(encoding="utf-8")
    styles_dir.mkdir(parents=True, exist_ok=True)

    wrapper_path = styles_dir / CLAUDE_STYLE_FILE
    wrapper_path.write_text(_render_claude_output_style(runtime_body), encoding="utf-8")

    settings = cu.load_json_config(str(settings_path), default={}, create_backup=True)
    settings["outputStyle"] = CLAUDE_STYLE_NAME
    cu.save_json_config(str(settings_path), settings, indent=2)


def remove_claude_output_style(styles_dir: Path, settings_path: Path) -> None:
    """Remove Bureau's Claude wrapper and clear selection if Bureau was active."""
    wrapper_path = styles_dir / CLAUDE_STYLE_FILE
    if wrapper_path.exists():
        wrapper_path.unlink()

    settings = cu.load_json_config(str(settings_path), default={}, create_backup=True)
    if settings.get("outputStyle") == CLAUDE_STYLE_NAME:
        settings.pop("outputStyle", None)
    cu.save_json_config(str(settings_path), settings, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-output", help="Path to compiled Bureau runtime output-style artifact")
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        default=[],
        help="Ordered markdown source file for output style compilation",
    )
    parser.add_argument(
        "--claude-dir",
        default=str(Path.home() / ".claude"),
        help="Claude user config directory (default: ~/.claude)",
    )
    parser.add_argument(
        "--install-claude",
        action="store_true",
        help="Install Bureau's compiled output style into Claude's native output-style location",
    )
    parser.add_argument(
        "--remove-claude",
        action="store_true",
        help="Remove Bureau's native Claude output style and clear the selected style if Bureau is active",
    )
    args = parser.parse_args()

    claude_dir = Path(args.claude_dir).expanduser()
    styles_dir = claude_dir / "output-styles"
    settings_path = claude_dir / "settings.json"

    if args.remove_claude:
        remove_claude_output_style(styles_dir, settings_path)
        return 0

    if not args.runtime_output:
        raise SystemExit("--runtime-output is required unless --remove-claude is set")

    sources = [Path(source).expanduser() for source in args.sources]
    runtime_output = Path(args.runtime_output).expanduser()
    compile_output_style(sources, runtime_output)

    if args.install_claude:
        install_claude_output_style(runtime_output, styles_dir, settings_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
