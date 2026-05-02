#!/usr/bin/env -S uv run
from __future__ import annotations

import json
from typing import Any, Mapping

from operations.config_loader import get_config
from operations.mcp_catalog import resolve_mcp_catalog


def render_opencode_mcp(config: Mapping[str, Any]) -> dict[str, Any]:
    catalog = resolve_mcp_catalog(config)
    client_configs = catalog["client_configs"]
    opencode_cfg: dict[str, Any] = {}

    for name, entry in client_configs.items():
        clients = entry.get("clients", {})
        disabled_for = clients.get("disabled_for", [])
        if isinstance(disabled_for, list) and "opencode" in disabled_for:
            continue
        client = clients.get("opencode") or clients.get("default")
        if not client:
            continue
        if client["transport"] == "http":
            entry_cfg: dict[str, Any] = {
                "type": "remote",
                "url": client["url"],
                "enabled": True,
            }
            if "headers" in client:
                entry_cfg["headers"] = client["headers"]
            if "timeout_ms" in client:
                entry_cfg["timeout"] = client["timeout_ms"]
            opencode_cfg[name] = entry_cfg
        else:
            entry_cfg = {
                "type": "local",
                "command": client["command"],
                "enabled": True,
            }
            if "env" in client:
                entry_cfg["environment"] = client["env"]
            if "timeout_ms" in client:
                entry_cfg["timeout"] = client["timeout_ms"]
            opencode_cfg[name] = entry_cfg
    return opencode_cfg


def main() -> None:
    print(json.dumps(render_opencode_mcp(get_config())))


if __name__ == "__main__":
    main()
