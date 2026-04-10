#!/usr/bin/env -S uv run
"""Generate the Bureau-managed code-standards skill."""

from __future__ import annotations

import argparse
from pathlib import Path

from operations.protocol_artifacts import OFF_EXIT_CODE, compile_code_standards_skill


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        required=True,
        help="Path to the generated SKILL.md file",
    )
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        default=[],
        help="Explicit standards source override. When omitted, the merged Bureau config is used.",
    )
    args = parser.parse_args()

    wrote_skill = compile_code_standards_skill(
        Path(args.destination).expanduser(),
        source_overrides=[Path(source) for source in args.sources] if args.sources else None,
    )
    return 0 if wrote_skill else OFF_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
