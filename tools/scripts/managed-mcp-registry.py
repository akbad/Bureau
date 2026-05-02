#!/usr/bin/env -S uv run
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from operations.json_config_utils import load_json_config, save_json_config


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = load_json_config(str(path), create_backup=False)
    except SystemExit:
        return {}
    return data if isinstance(data, dict) else {}


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        return {}

    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_cli_entries(cli: str, config_path: str) -> dict[str, Any]:
    path = Path(config_path).expanduser()
    if cli == "claude":
        data = _load_json(path)
        return data.get("mcpServers", {}) if isinstance(data, dict) else {}
    if cli == "gemini":
        data = _load_json(path)
        return data.get("mcpServers", {}) if isinstance(data, dict) else {}
    if cli == "opencode":
        data = _load_json(path)
        return data.get("mcp", {}) if isinstance(data, dict) else {}
    if cli == "codex":
        data = _load_toml(path)
        return data.get("mcp_servers", {}) if isinstance(data, dict) else {}
    return {}


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def normalize_entry(cli: str, raw_entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_entry, dict):
        return {}

    if cli == "claude":
        transport = raw_entry.get("type")
        if transport == "http":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if transport == "stdio":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                }
            )

    if cli == "gemini":
        if "httpUrl" in raw_entry:
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("httpUrl"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if "command" in raw_entry:
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                    "timeout_ms": raw_entry.get("timeout"),
                }
            )

    if cli == "codex":
        transport = raw_entry.get("transport")
        if transport is None:
            if "url" in raw_entry:
                transport = "http"
            elif "command" in raw_entry:
                transport = "stdio"
        if transport == "http":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "bearer_token_env_var": raw_entry.get("bearer_token_env_var"),
                }
            )
        if transport == "stdio":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                    "startup_timeout_sec": raw_entry.get("startup_timeout_sec"),
                    "tool_timeout_sec": raw_entry.get("tool_timeout_sec"),
                }
            )

    if cli == "opencode":
        entry_type = raw_entry.get("type")
        if entry_type == "remote":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if entry_type == "local":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "env": raw_entry.get("environment") or raw_entry.get("env"),
                    "timeout_ms": raw_entry.get("timeout"),
                }
            )

    return {}


def fingerprint_entry(normalized: dict[str, Any]) -> str:
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_registry(path: str) -> dict[str, Any]:
    data = _load_json(Path(path).expanduser())
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("servers", {})
    return data


def write_registry(path: str, data: dict[str, Any]) -> None:
    save_json_config(path, data, indent=2)


def _desired_servers(plan: dict[str, Any], cli: str) -> list[str]:
    client_configs = plan.get("client_configs", {}).get(cli, {})
    if isinstance(client_configs, dict):
        return sorted(client_configs.keys())
    return []


def normalize_desired_entry(cli: str, desired_entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(desired_entry, dict):
        return {}

    transport = desired_entry.get("transport")
    if transport == "http":
        payload = {
            "transport": "http",
            "url": desired_entry.get("url"),
        }
        if cli in {"claude", "gemini", "opencode"}:
            payload["headers"] = desired_entry.get("headers")
        if cli == "codex":
            payload["bearer_token_env_var"] = desired_entry.get("bearer_token_env_var")
        return _drop_none(payload)

    if transport == "stdio":
        command = desired_entry.get("command", [])
        if not isinstance(command, list) or not command:
            return {}
        if cli == "opencode":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": command,
                    "env": desired_entry.get("env") or desired_entry.get("environment"),
                    "timeout_ms": desired_entry.get("timeout_ms"),
                }
            )
        payload = {
            "transport": "stdio",
            "command": command[0],
            "args": command[1:],
            "env": desired_entry.get("env"),
        }
        if cli == "gemini":
            payload["timeout_ms"] = desired_entry.get("timeout_ms")
        if cli == "codex":
            payload["startup_timeout_sec"] = desired_entry.get("startup_timeout_sec")
            payload["tool_timeout_sec"] = desired_entry.get("tool_timeout_sec")
        return _drop_none(payload)

    return {}


def compute_prune(
    cli: str,
    plan: dict[str, Any],
    registry: dict[str, Any],
    current_entries: dict[str, Any],
) -> list[str]:
    desired = set(_desired_servers(plan, cli))
    to_remove: list[str] = []
    servers = registry.get("servers")
    if not isinstance(servers, dict):
        servers = {}
    for server_id, info in servers.items():
        if server_id in desired:
            continue
        current = current_entries.get(server_id)
        if not isinstance(current, dict):
            continue
        normalized = normalize_entry(cli, current)
        if not normalized:
            continue
        if fingerprint_entry(normalized) == info.get("fingerprint"):
            to_remove.append(server_id)
    return sorted(to_remove)


def compute_update(
    cli: str,
    plan: dict[str, Any],
    registry: dict[str, Any],
    current_entries: dict[str, Any],
) -> list[str]:
    if cli == "opencode":
        return []

    desired_cfgs = plan.get("client_configs", {}).get(cli, {})
    if not isinstance(desired_cfgs, dict):
        return []

    to_update: list[str] = []
    servers = registry.get("servers")
    if not isinstance(servers, dict):
        servers = {}

    for server_id, desired_entry in desired_cfgs.items():
        current = current_entries.get(server_id)
        registry_info = servers.get(server_id)
        if not isinstance(current, dict) or not isinstance(registry_info, dict):
            continue

        normalized_current = normalize_entry(cli, current)
        normalized_desired = normalize_desired_entry(cli, desired_entry)
        if not normalized_current or not normalized_desired:
            continue

        current_fingerprint = fingerprint_entry(normalized_current)
        desired_fingerprint = fingerprint_entry(normalized_desired)
        recorded_fingerprint = registry_info.get("fingerprint")

        if current_fingerprint == recorded_fingerprint and current_fingerprint != desired_fingerprint:
            to_update.append(server_id)

    return sorted(to_update)


def record_registry(
    cli: str,
    plan: dict[str, Any],
    current_entries: dict[str, Any],
    now: str | None = None,
) -> dict[str, Any]:
    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    servers: dict[str, Any] = {}
    for server_id in _desired_servers(plan, cli):
        current = current_entries.get(server_id)
        if not isinstance(current, dict):
            continue
        normalized = normalize_entry(cli, current)
        if not normalized:
            continue
        servers[server_id] = {"fingerprint": fingerprint_entry(normalized)}

    return {
        "version": 1,
        "updated_at": now,
        "servers": servers,
    }


def _load_plan(path: str) -> dict[str, Any]:
    return _load_json(Path(path).expanduser())


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Bureau MCP registry state.")
    parser.add_argument("--mode", choices=["prune", "record", "reconcile"], required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    registry = load_registry(args.registry)
    current_entries = load_cli_entries(args.cli, args.config)

    if args.mode == "prune":
        result = {
            "to_remove": compute_prune(args.cli, plan, registry, current_entries),
            "registry": registry,
        }
        print(json.dumps(result))
        return 0

    if args.mode == "reconcile":
        result = {
            "to_remove": compute_prune(args.cli, plan, registry, current_entries),
            "to_update": compute_update(args.cli, plan, registry, current_entries),
            "registry": registry,
        }
        print(json.dumps(result))
        return 0

    updated = record_registry(args.cli, plan, current_entries)
    write_registry(args.registry, updated)
    print(json.dumps(updated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
