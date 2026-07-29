#!/usr/bin/env -S uv run
"""Upsert Bureau-managed MCP servers into Grok Build's config.toml.

Grok stores MCP servers under ``[mcp_servers.<name>]`` in ``~/.grok/config.toml``:

  HTTP:  url, optional headers, enabled
  stdio: command, args, optional env, enabled, optional timeouts

Exit codes (mirrors other Bureau add helpers used by set-up-tools.sh):
  0 — wrote / updated the entry this run
  1 — entry already present with an equivalent configuration (no write)
  2 — invalid arguments / unsupported config
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.items import Table


def _load_doc(path: Path) -> Any:
    if not path.exists():
        return tomlkit.document()
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return tomlkit.document()
    return tomlkit.parse(text)


def _ensure_mcp_servers_table(doc: Any) -> Table:
    if "mcp_servers" not in doc:
        doc["mcp_servers"] = tomlkit.table(is_super_table=True)
    table = doc["mcp_servers"]
    if not isinstance(table, Table):
        # Replace a non-table value so we can write servers safely.
        doc["mcp_servers"] = tomlkit.table(is_super_table=True)
        table = doc["mcp_servers"]
    return table


def _table_to_plain(table: Any) -> dict[str, Any]:
    """Convert a tomlkit table (or dict) to a plain JSON-friendly dict."""
    if table is None:
        return {}
    if isinstance(table, dict):
        out: dict[str, Any] = {}
        for key, value in table.items():
            if isinstance(value, dict):
                out[str(key)] = _table_to_plain(value)
            elif isinstance(value, list):
                out[str(key)] = list(value)
            else:
                out[str(key)] = value
        return out
    return {}


def build_http_entry(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    enabled: bool = True,
) -> dict[str, Any]:
    entry: dict[str, Any] = {"url": url, "enabled": enabled}
    if headers:
        entry["headers"] = dict(headers)
    return entry


def build_stdio_entry(
    command: list[str],
    env: dict[str, str] | None = None,
    *,
    enabled: bool = True,
    startup_timeout_sec: int | None = None,
    tool_timeout_sec: int | None = None,
) -> dict[str, Any]:
    if not command:
        raise ValueError("stdio transport requires a non-empty command")
    entry: dict[str, Any] = {
        "command": command[0],
        "args": list(command[1:]),
        "enabled": enabled,
    }
    if env:
        entry["env"] = dict(env)
    if startup_timeout_sec is not None:
        entry["startup_timeout_sec"] = int(startup_timeout_sec)
    if tool_timeout_sec is not None:
        entry["tool_timeout_sec"] = int(tool_timeout_sec)
    return entry


def _normalize_for_compare(entry: dict[str, Any]) -> dict[str, Any]:
    """Drop fields that do not affect Grok MCP identity for equality checks."""
    payload = dict(entry)
    # Treat missing enabled as true (Grok default).
    if payload.get("enabled", True) is True:
        payload.pop("enabled", None)
    else:
        payload["enabled"] = False
    # Empty args/env equivalent to absent.
    if not payload.get("args"):
        payload.pop("args", None)
    if not payload.get("env"):
        payload.pop("env", None)
    if not payload.get("headers"):
        payload.pop("headers", None)
    return payload


def entries_equivalent(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
    return _normalize_for_compare(existing) == _normalize_for_compare(desired)


def _apply_entry_to_table(servers: Table, server_name: str, entry: dict[str, Any]) -> None:
    server_table = tomlkit.table()
    for key, value in entry.items():
        if key == "headers" and isinstance(value, dict):
            headers_table = tomlkit.table()
            for h_key, h_val in value.items():
                headers_table[h_key] = h_val
            server_table["headers"] = headers_table
        elif key == "env" and isinstance(value, dict):
            env_table = tomlkit.table()
            for e_key, e_val in value.items():
                env_table[e_key] = e_val
            server_table["env"] = env_table
        elif key == "args" and isinstance(value, list):
            server_table["args"] = value
        else:
            server_table[key] = value
    servers[server_name] = server_table


def upsert_mcp_server(
    config_path: Path,
    server_name: str,
    entry: dict[str, Any],
    *,
    dry_run: bool = False,
) -> int:
    """Write *entry* for *server_name*. Return 0 if written, 1 if unchanged."""
    config_path = config_path.expanduser()
    doc = _load_doc(config_path)
    servers = _ensure_mcp_servers_table(doc)

    existing_raw = servers.get(server_name)
    existing = _table_to_plain(existing_raw) if existing_raw is not None else {}
    if existing and entries_equivalent(existing, entry):
        return 1

    _apply_entry_to_table(servers, server_name, entry)

    if dry_run:
        return 0

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return 0


def remove_mcp_server(config_path: Path, server_name: str, *, dry_run: bool = False) -> int:
    """Remove *server_name* if present. Return 0 if removed, 1 if absent."""
    config_path = config_path.expanduser()
    if not config_path.exists():
        return 1
    doc = _load_doc(config_path)
    if "mcp_servers" not in doc:
        return 1
    servers = doc["mcp_servers"]
    if not isinstance(servers, Table) or server_name not in servers:
        return 1
    del servers[server_name]
    if dry_run:
        return 0
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return 0


def _parse_headers(pairs: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for pair in pairs:
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def _parse_env(pairs: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        env[key] = value
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add/update/remove Grok MCP servers in config.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_upsert = sub.add_parser("upsert", help="Add or update an MCP server")
    p_upsert.add_argument("--config", required=True, help="Path to ~/.grok/config.toml")
    p_upsert.add_argument("--name", required=True, help="Server id / section name")
    p_upsert.add_argument(
        "--transport",
        choices=["http", "stdio"],
        required=True,
    )
    p_upsert.add_argument("--url", help="HTTP URL (http transport)")
    p_upsert.add_argument(
        "--header",
        action="append",
        default=[],
        help="HTTP header KEY:value (repeatable)",
    )
    p_upsert.add_argument(
        "--env",
        action="append",
        default=[],
        dest="env_pairs",
        help="stdio env KEY=value (repeatable)",
    )
    p_upsert.add_argument("--startup-timeout-sec", type=int, default=None)
    p_upsert.add_argument("--tool-timeout-sec", type=int, default=None)
    p_upsert.add_argument(
        "--arg",
        action="append",
        default=[],
        dest="command_args",
        help="stdio command token (repeatable; first is the executable)",
    )
    p_upsert.add_argument("--dry-run", action="store_true")

    p_remove = sub.add_parser("remove", help="Remove an MCP server")
    p_remove.add_argument("--config", required=True)
    p_remove.add_argument("--name", required=True)
    p_remove.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "remove":
        return remove_mcp_server(Path(args.config), args.name, dry_run=args.dry_run)

    # upsert
    if args.transport == "http":
        if not args.url:
            print("ERROR: --url required for http transport", file=sys.stderr)
            return 2
        entry = build_http_entry(args.url, _parse_headers(args.header))
    else:
        command = list(args.command_args or [])
        if not command:
            print(
                "ERROR: stdio transport requires at least one --arg <token>",
                file=sys.stderr,
            )
            return 2
        entry = build_stdio_entry(
            command,
            _parse_env(args.env_pairs),
            startup_timeout_sec=args.startup_timeout_sec,
            tool_timeout_sec=args.tool_timeout_sec,
        )

    return upsert_mcp_server(Path(args.config), args.name, entry, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
