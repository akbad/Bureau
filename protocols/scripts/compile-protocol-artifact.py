#!/usr/bin/env -S uv run
"""Compile one Bureau-managed protocol artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from operations.protocol_artifacts import (
    OFF_EXIT_CODE,
    compile_protocol_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--setting",
        choices=("output_style", "code_standards"),
        required=True,
        help="Protocol config key to resolve and compile",
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Path to the compiled runtime artifact",
    )
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        default=[],
        help="Explicit source override. When omitted, the merged Bureau config is used.",
    )
    args = parser.parse_args()

    wrote_artifact = compile_protocol_artifact(
        args.setting,
        Path(args.destination).expanduser(),
        source_overrides=[Path(source) for source in args.sources] if args.sources else None,
    )
    return 0 if wrote_artifact else OFF_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
