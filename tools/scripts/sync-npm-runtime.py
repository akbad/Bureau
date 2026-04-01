#!/usr/bin/env -S uv run
from __future__ import annotations

# Sync Bureau-managed Node MCP packages into a shared local runtime so CLIs can
# execute stable local binaries instead of relying on `npx` at startup.
#
# Why this approach:
# - setup is the right place to handle npm/network/cache side effects once
# - runtime launch should be deterministic and sandbox-friendly
# - the manifest file records Bureau's desired packages/binaries without trying
#   to reverse-map arbitrary npm specs into a generated package.json

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


MANIFEST_FILENAME = ".bureau-npm-runtime.json"


def _load_plan(path: str) -> dict[str, Any]:
    plan_path = Path(path).expanduser()
    return json.loads(plan_path.read_text(encoding="utf-8"))


def _manifest_path(runtime_dir: Path) -> Path:
    return runtime_dir / MANIFEST_FILENAME


def _desired_manifest(runtime_cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "packages": sorted(str(pkg) for pkg in runtime_cfg.get("packages", [])),
        "binaries": sorted(str(binary) for binary in runtime_cfg.get("binaries", [])),
    }


def _load_manifest(runtime_dir: Path) -> dict[str, Any] | None:
    manifest_path = _manifest_path(runtime_dir)
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _missing_binaries(runtime_dir: Path, binaries: list[str]) -> list[str]:
    bin_dir = runtime_dir / "node_modules" / ".bin"
    return [binary for binary in binaries if not (bin_dir / binary).exists()]


def sync_runtime(plan: dict[str, Any]) -> dict[str, Any]:
    runtime_cfg = plan.get("npm_runtime")
    if not isinstance(runtime_cfg, dict) or not runtime_cfg.get("packages"):
        return {"installed": False, "reason": "disabled"}

    runtime_dir = Path(str(runtime_cfg["runtime_dir"])).expanduser()
    cache_dir = Path(str(runtime_cfg["cache_dir"])).expanduser()
    desired = _desired_manifest(runtime_cfg)
    current = _load_manifest(runtime_dir)
    missing = _missing_binaries(runtime_dir, desired["binaries"])
    needs_install = current != desired or bool(missing)

    if not needs_install:
        return {"installed": False, "reason": "up_to_date"}

    runtime_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Keep npm writes inside the shared runtime tree so MCP startup no longer
    # depends on a writable user-scoped npm cache.
    env = dict(os.environ)
    env["NPM_CONFIG_CACHE"] = str(cache_dir)
    cmd = ["npm", "install", "--prefix", str(runtime_dir), *desired["packages"]]
    # stdout is reserved for JSON output consumed by the calling shell script;
    # redirect npm's stdout to stderr so it stays visible for debugging.
    subprocess.run(cmd, check=True, env=env, stdout=sys.stderr)

    _manifest_path(runtime_dir).write_text(
        json.dumps(desired, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "installed": True,
        "reason": "manifest_changed" if current != desired else "missing_binaries",
        "missing_binaries": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Bureau's shared local npm MCP runtime.")
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()

    result = sync_runtime(_load_plan(args.plan))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
