#!/usr/bin/env python3
"""Generate a resolved skills configuration JSON for Bureau."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from operations.config_loader import expand_path, find_repo_root, get_config
from operations.skills_catalog import resolve_skills_catalog

GENERATED_BUREAU_SKILLS_ROOT = "~/.config/bureau/generated/skills"
PROTOCOL_OWNED_SKILLS = {
    "code-standards": "code_standards",
}


def _resolve_source_root(source_path: str, repo_root: Path) -> Path:
    root = expand_path(source_path)
    if not root.is_absolute():
        root = repo_root / root
    return root


def _protocol_skill_enabled(config: Mapping[str, Any], protocol_key: str) -> bool:
    protocols = config.get("protocols", {})
    if not isinstance(protocols, Mapping):
        return True

    value = protocols.get(protocol_key, "default")
    return value != "off" and value is not False


def _append_protocol_owned_skill(
    *,
    entries: list[dict[str, str]],
    source_roots: list[str],
    seen_names: set[str],
    name: str,
    root: Path,
) -> None:
    skill_dir = root / name
    if not skill_dir.exists() or name in seen_names:
        return

    source_root = str(root)
    if source_root not in source_roots:
        source_roots.append(source_root)

    entries.append({"name": name, "source_path": str(skill_dir)})
    seen_names.add(name)


def _build_skills_entries(config: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    resolved = resolve_skills_catalog(config)
    resolved_names = [
        name
        for name in resolved.get("skills", [])
        if name not in PROTOCOL_OWNED_SKILLS
    ]
    remaining = Counter(resolved_names)

    skills_cfg = config.get("skills", {})
    sources = skills_cfg.get("sources", [])

    entries: list[dict[str, str]] = []
    source_roots: list[str] = []
    seen_names: set[str] = set()
    for source in sources:
        source_path = source.get("path")
        if not source_path:
            continue
        root = _resolve_source_root(source_path, repo_root)
        if not root.exists():
            continue
        source_root = str(root)
        if source_root not in source_roots:
            source_roots.append(source_root)
        for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            name = skill_dir.name
            if remaining.get(name, 0) <= 0:
                continue
            entries.append(
                {
                    "name": name,
                    "source_path": str(skill_dir),
                }
            )
            seen_names.add(name)
            remaining[name] -= 1

    protocol_root = _resolve_source_root(GENERATED_BUREAU_SKILLS_ROOT, repo_root)
    for name, protocol_key in PROTOCOL_OWNED_SKILLS.items():
        if not _protocol_skill_enabled(config, protocol_key):
            continue
        _append_protocol_owned_skill(
            entries=entries,
            source_roots=source_roots,
            seen_names=seen_names,
            name=name,
            root=protocol_root,
        )

    return {"skills": entries, "source_roots": source_roots}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate skills config JSON.")
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print generated JSON to stdout instead of writing a file.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = find_repo_root()
    output_path = repo_root / "protocols/context/generated/skills-config.generated.json"

    config = get_config()
    payload = _build_skills_entries(config, repo_root)

    if args.stdout:
        json.dump(payload, indent=2, fp=sys.stdout)
        print()
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
