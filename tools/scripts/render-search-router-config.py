#!/usr/bin/env -S uv run
"""Render the Bureau search-router runtime config.

# Design rationale
#
# Agent clients only receive stdio command wiring, while the router also needs
# richer profile metadata from mcp.client_configs.*.settings.  render-mcp-setup
# preserves that catalog metadata under catalog_client_configs; this helper
# writes the small JSON file consumed by bureau-search-mcp at process startup.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

JsonObject = dict[str, Any]


def _expand_path(path_text: str) -> Path:
    """Expand `~` and environment variables in a path string."""
    return Path(os.path.expandvars(os.path.expanduser(path_text)))


def _load_plan(plan_path: Path) -> JsonObject:
    """Load and validate a rendered setup plan JSON object."""
    with plan_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("setup plan must be a JSON object")
    return payload


def _client_settings(plan: JsonObject, client_id: str) -> JsonObject:
    """Return catalog settings for a client config.

    Args:
        plan: Rendered MCP setup plan.
        client_id: Client config id, usually `bureau-search`.

    Returns:
        Settings dictionary from catalog_client_configs.
    """
    catalog = plan.get("catalog_client_configs", {})
    if not isinstance(catalog, dict):
        raise TypeError("setup plan catalog_client_configs must be an object")

    entry = catalog.get(client_id)
    if not isinstance(entry, dict):
        raise KeyError(f"client config not found in setup plan catalog: {client_id}")

    settings = entry.get("settings", {})
    if not isinstance(settings, dict):
        raise TypeError(f"catalog_client_configs.{client_id}.settings must be an object")
    return settings


def render_router_config_from_plan(plan_path: str | Path, client_id: str) -> JsonObject:
    """Render the bureau-search runtime config from a setup plan.

    Args:
        plan_path: Path to the rendered setup plan JSON.
        client_id: Client config id, usually `bureau-search`.

    Returns:
        Small status object with the written config path.
    """
    plan = _load_plan(Path(plan_path))
    settings = dict(_client_settings(plan, client_id))
    config_path = _expand_path(str(settings.pop("config_path")))

    config_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(settings, indent=2, sort_keys=True) + "\n"
    if not config_path.exists() or config_path.read_text(encoding="utf-8") != rendered:
        config_path.write_text(rendered, encoding="utf-8")

    return {"config_path": str(config_path)}


def main() -> int:
    """CLI entry point for setup script integration."""
    parser = argparse.ArgumentParser(description="Render bureau-search router config.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--client", default="bureau-search")
    args = parser.parse_args()

    result = render_router_config_from_plan(args.plan, args.client)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
