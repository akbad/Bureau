#!/usr/bin/env -S uv run

import sys
from typing import Any

from operations.json_config_utils import load_json_config, save_json_config, expand_vars


def build_entry(transport: str, payload: list[str]) -> dict:
    """
    Build an MCP server entry based on transport type.

    Args:
        transport: Either 'http' or 'stdio'
        payload: Transport-specific configuration arguments.
            For stdio, supports special flags:
            - --timeout <ms>: Request timeout in milliseconds
            - --env KEY=VALUE: Environment variable (can be repeated)

    Returns:
        Dictionary containing server configuration

    Raises:
        SystemExit: If transport is invalid or required arguments are missing
    """
    if transport == "http":
        if not payload:
            raise SystemExit("HTTP transport requires a URL argument")
        url, *headers = payload
        entry: dict[str, Any] = {"httpUrl": expand_vars(url)}
        header_map: dict[str, str] = {}
        for header in headers:
            if ":" not in header:
                continue
            key, value = header.split(":", 1)
            header_map[key] = expand_vars(value)
        if header_map:
            entry["headers"] = header_map
        return entry

    if transport == "stdio":
        if not payload:
            raise SystemExit("stdio transport requires a command argument")

        # Parse special flags from payload
        command = payload[0]
        args: list[str] = []
        env_vars: dict[str, str] = {}
        timeout: int | None = None

        i = 1
        while i < len(payload):
            arg = payload[i]
            if arg == "--timeout" and i + 1 < len(payload):
                timeout = int(payload[i + 1])
                i += 2
            elif arg == "--env" and i + 1 < len(payload):
                env_str = payload[i + 1]
                if "=" in env_str:
                    key, value = env_str.split("=", 1)
                    env_vars[key] = expand_vars(value)
                i += 2
            else:
                args.append(arg)
                i += 1

        entry: dict[str, Any] = {"command": command, "args": args}
        if env_vars:
            entry["env"] = env_vars
        if timeout is not None:
            entry["timeout"] = timeout
        return entry

    raise SystemExit(f"Unsupported transport: {transport}")


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) < 4:
        raise SystemExit(
            "Usage: add-to-gemini-settings.py <transport> <server> <config_path> [payload...]"
        )

    transport, server_name, config_path, *payload = sys.argv[1:]

    # Load existing config with default mcpServers structure
    config = load_json_config(config_path, default={"mcpServers": {}}, create_backup=False)
    config.setdefault("mcpServers", {})
    config["mcpServers"][server_name] = build_entry(transport, payload)

    # Save updated config
    save_json_config(config_path, config)


if __name__ == "__main__":
    main()
