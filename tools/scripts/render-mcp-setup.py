#!/usr/bin/env -S uv run
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from operations.config_loader import get_config
from operations.mcp_catalog import resolve_mcp_catalog


def _render_npm_runtime_plan(
    config: Mapping[str, Any],
    catalog: Mapping[str, Any],
    client_configs_by_cli: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    included_servers = {
        server_id
        for client_map in client_configs_by_cli.values()
        for server_id in client_map.keys()
    }
    if not included_servers:
        return {}

    packages: set[str] = set()
    binaries: set[str] = set()
    servers: dict[str, dict[str, list[str]]] = {}
    for server_id in sorted(included_servers):
        entry = catalog["client_configs"].get(server_id, {})
        npm_runtime = entry.get("npm_runtime")
        if not isinstance(npm_runtime, dict):
            continue
        runtime_packages = [str(pkg) for pkg in npm_runtime.get("packages", [])]
        runtime_binaries = [str(binary) for binary in npm_runtime.get("binaries", [])]
        if not runtime_packages and not runtime_binaries:
            continue
        packages.update(runtime_packages)
        binaries.update(runtime_binaries)
        servers[server_id] = {
            "packages": runtime_packages,
            "binaries": runtime_binaries,
        }

    if not servers:
        return {}

    runtime_root = Path(str(config.get("path_to", {}).get("mcp_clones", ""))) / "npm-tools"
    cache_dir = runtime_root / ".npm-cache"
    return {
        "runtime_dir": str(runtime_root),
        "cache_dir": str(cache_dir),
        "packages": sorted(packages),
        "binaries": sorted(binaries),
        "servers": servers,
    }


def render_setup_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    agents = config.get("agents", [])
    catalog = resolve_mcp_catalog(config, env=os.environ)
    auto_approved_cfg = config.get("auto_approved") or {}

    client_configs_by_cli: dict[str, dict[str, Any]] = {agent: {} for agent in agents}
    for name, entry in catalog["client_configs"].items():
        clients = entry.get("clients", {})
        default_client = clients.get("default")
        disabled_for = set(clients.get("disabled_for", []))
        for agent in agents:
            if agent in disabled_for:
                continue
            client_cfg = clients.get(agent, default_client)
            if not client_cfg:
                continue
            client_configs_by_cli[agent][name] = client_cfg

    # build per-tool approval mapping for Codex (servers with explicit tool lists)
    codex_tools: dict[str, list[str]] = {}
    for server_name in client_configs_by_cli.get("codex", {}):
        entry = catalog["client_configs"].get(server_name, {})
        tools = entry.get("tools")
        if isinstance(tools, list) and tools:
            codex_tools[server_name] = sorted(str(t) for t in tools)

    auto_approved = dict(auto_approved_cfg)
    auto_approved["mcp_servers"] = {
        "claude": sorted(client_configs_by_cli.get("claude", {}).keys()),
        "gemini": sorted(client_configs_by_cli.get("gemini", {}).keys()),
        "codex": sorted(client_configs_by_cli.get("codex", {}).keys()),
        "codex_tools": codex_tools,
    }

    npm_runtime = _render_npm_runtime_plan(config, catalog, client_configs_by_cli)

    return {
        "dependencies": catalog.get("dependencies", {}),
        "services": catalog["services"],
        "client_configs": client_configs_by_cli,
        "npm_runtime": npm_runtime,
        "auto_approved": auto_approved,
        "prune_disabled_mcps": bool(config.get("prune_disabled_mcps", False)),
    }


def main() -> None:
    plan = render_setup_plan(get_config())
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
