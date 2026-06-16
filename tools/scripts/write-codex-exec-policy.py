#!/usr/bin/env -S uv run
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from operations.approval_rules import build_codex_rule_lines


def write_exec_policy(
    allow: Iterable[str],
    deny: Iterable[str],
    rules_path: Path | None = None,
) -> Path:
    if rules_path is None:
        rules_path = Path("~/.codex/rules/bureau.rules").expanduser()

    rules_path.parent.mkdir(parents=True, exist_ok=True)

    lines = build_codex_rule_lines(allow, deny)

    rules_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rules_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write Codex exec-policy rules for Bash allow/deny prefixes."
    )
    parser.add_argument("--allow", action="append", default=[], help="Bash prefix to allow")
    parser.add_argument("--deny", action="append", default=[], help="Bash prefix to deny")
    args = parser.parse_args()

    rules_path = write_exec_policy(args.allow, args.deny)
    print(f"Wrote exec-policy rules to {rules_path}")


if __name__ == "__main__":
    main()
