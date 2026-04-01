#!/usr/bin/env -S uv run
"""Install or remove Bureau's native Claude Code output style."""

from __future__ import annotations

import argparse
from pathlib import Path

from operations.json_config_utils import load_json_config, save_json_config


STYLE_NAME = "Bureau"
STYLE_FILENAME = "bureau.md"


def build_style_document(style_body: str) -> str:
    """Wrap the compiled Bureau style in Claude-native output-style frontmatter."""
    body = style_body.rstrip()
    return (
        "---\n"
        f"name: {STYLE_NAME}\n"
        "description: Bureau-managed output style\n"
        "keep-coding-instructions: true\n"
        "---\n\n"
        f"{body}\n"
    )


def install_style(source: Path) -> int:
    home = Path.home()
    style_dir = home / ".claude" / "output-styles"
    style_dir.mkdir(parents=True, exist_ok=True)

    style_body = source.read_text(encoding="utf-8")
    (style_dir / STYLE_FILENAME).write_text(build_style_document(style_body), encoding="utf-8")

    settings_path = home / ".claude" / "settings.json"
    settings = load_json_config(str(settings_path), default={}, create_backup=True)
    settings["outputStyle"] = STYLE_NAME
    save_json_config(str(settings_path), settings, indent=2)
    return 0


def remove_style() -> int:
    home = Path.home()
    style_path = home / ".claude" / "output-styles" / STYLE_FILENAME
    if style_path.exists():
        style_path.unlink()

    settings_path = home / ".claude" / "settings.json"
    settings = load_json_config(str(settings_path), default={}, create_backup=True)
    if settings.get("outputStyle") == STYLE_NAME:
        settings.pop("outputStyle", None)
        save_json_config(str(settings_path), settings, indent=2)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="Compiled Bureau output-style source file")
    parser.add_argument("--remove", action="store_true", help="Remove Bureau-managed Claude output style")
    args = parser.parse_args()

    if args.remove:
        return remove_style()
    if not args.source:
        raise SystemExit("--source is required unless --remove is used")
    return install_style(Path(args.source).expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
