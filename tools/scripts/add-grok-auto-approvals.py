#!/usr/bin/env -S uv run
"""Merge Bureau auto-approval rules into Grok Build's config.toml [permission] section.

Managed rules are tracked in ``~/.config/bureau/internal/managed-permissions.grok.json``
so re-runs can remove previous Bureau rules without touching user-authored ones.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.items import Array, Table

from operations.approval_rules import (
    build_grok_bash_rules,
    build_grok_mcp_rules,
    build_grok_path_rules,
)


DEFAULT_MANAGED_PATH = Path(
    os.path.expanduser("~/.config/bureau/internal/managed-permissions.grok.json")
)


def _load_managed(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {"allow": [], "deny": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"allow": [], "deny": []}
    if not isinstance(data, dict):
        return {"allow": [], "deny": []}
    allow = data.get("allow", [])
    deny = data.get("deny", [])
    return {
        "allow": [str(x) for x in allow] if isinstance(allow, list) else [],
        "deny": [str(x) for x in deny] if isinstance(deny, list) else [],
    }


def _save_managed(path: Path, allow: list[str], deny: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"allow": allow, "deny": deny}, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_doc(path: Path) -> Any:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return tomlkit.document()
    return tomlkit.parse(path.read_text(encoding="utf-8"))


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _set_str_array(table: Table, key: str, values: list[str]) -> None:
    arr: Array = tomlkit.array()
    arr.multiline(True)
    for item in values:
        arr.append(item)
    table[key] = arr


def merge_permission_rules(
    existing_allow: list[str],
    existing_deny: list[str],
    previous_managed: dict[str, list[str]],
    new_allow: list[str],
    new_deny: list[str],
) -> tuple[list[str], list[str]]:
    """Replace prior Bureau-managed rules with *new_* sets; keep foreign rules."""
    prev_allow = set(previous_managed.get("allow", []))
    prev_deny = set(previous_managed.get("deny", []))

    kept_allow = [r for r in existing_allow if r not in prev_allow]
    kept_deny = [r for r in existing_deny if r not in prev_deny]

    # de-dupe while preserving order: user rules first, then bureau
    allow_out: list[str] = []
    seen_allow: set[str] = set()
    for rule in kept_allow + new_allow:
        if rule not in seen_allow:
            allow_out.append(rule)
            seen_allow.add(rule)

    deny_out: list[str] = []
    seen_deny: set[str] = set()
    for rule in kept_deny + new_deny:
        if rule not in seen_deny:
            deny_out.append(rule)
            seen_deny.add(rule)

    return allow_out, deny_out


def apply_approvals(
    config_path: Path,
    *,
    mcp_servers: list[str],
    bash_allow: list[str],
    bash_deny: list[str],
    access_paths: list[str],
    managed_path: Path = DEFAULT_MANAGED_PATH,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    new_allow = (
        build_grok_mcp_rules(mcp_servers)
        + build_grok_bash_rules(bash_allow)
        + build_grok_path_rules(access_paths)
    )
    new_deny = build_grok_bash_rules(bash_deny)

    doc = _load_doc(config_path)
    if "permission" not in doc or not isinstance(doc["permission"], Table):
        doc["permission"] = tomlkit.table()
    perm = doc["permission"]

    existing_allow = _as_str_list(perm.get("allow"))
    existing_deny = _as_str_list(perm.get("deny"))
    previous = _load_managed(managed_path)

    merged_allow, merged_deny = merge_permission_rules(
        existing_allow,
        existing_deny,
        previous,
        new_allow,
        new_deny,
    )

    if not dry_run:
        _set_str_array(perm, "allow", merged_allow)
        _set_str_array(perm, "deny", merged_deny)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        _save_managed(managed_path, new_allow, new_deny)

    return {"allow": new_allow, "deny": new_deny}


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Grok Build auto-approvals")
    parser.add_argument("config", help="Path to ~/.grok/config.toml")
    parser.add_argument(
        "--mcp-server",
        action="append",
        default=[],
        dest="mcp_servers",
        help="MCP server id to allow as MCPTool(id__*) (repeatable)",
    )
    parser.add_argument(
        "--bash-allow",
        action="append",
        default=[],
        help="Bash command prefix to allow (repeatable)",
    )
    parser.add_argument(
        "--bash-deny",
        action="append",
        default=[],
        help="Bash command prefix to deny (repeatable)",
    )
    parser.add_argument(
        "--access-path",
        action="append",
        default=[],
        dest="access_paths",
        help="Filesystem path to allow Read+Edit (repeatable)",
    )
    parser.add_argument(
        "--managed-path",
        default=str(DEFAULT_MANAGED_PATH),
        help="Path for Bureau-managed permission ledger",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    managed = apply_approvals(
        Path(args.config),
        mcp_servers=args.mcp_servers,
        bash_allow=args.bash_allow,
        bash_deny=args.bash_deny,
        access_paths=args.access_paths,
        managed_path=Path(args.managed_path),
        dry_run=args.dry_run,
    )
    print(json.dumps(managed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
