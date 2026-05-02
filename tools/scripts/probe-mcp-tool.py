#!/usr/bin/env -S uv run
"""Probe a streamable HTTP MCP server by calling a configured tool.

The setup script needs an end-to-end readiness check that exercises the same
MCP surface as coding agents. This helper intentionally uses only the Python
standard library so Bureau does not need to add an MCP client dependency just
to verify local services during bootstrap.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

JsonObject = dict[str, Any]
UrlOpener = Callable[..., Any]

DEFAULT_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_TIMEOUT_SECONDS = 10.0


class McpProbeError(RuntimeError):
    """Raised when an MCP readiness probe cannot prove the server is usable."""


def parse_sse_jsonrpc(raw_body: bytes) -> JsonObject:
    """Parse the first JSON-RPC payload from a streamable HTTP response.

    Args:
        raw_body: Raw response body from the MCP streamable HTTP endpoint.

    Returns:
        Decoded JSON-RPC response object.

    Raises:
        McpProbeError: If no parseable `data:` payload is present.
    """
    text = raw_body.decode("utf-8", errors="replace")
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise McpProbeError(f"MCP response contained invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise McpProbeError("MCP response JSON-RPC payload must be an object")
        return payload

    data_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
        elif not line.strip() and data_lines:
            break

    if not data_lines:
        raise McpProbeError("MCP response did not contain an SSE data payload")

    payload_text = "\n".join(data_lines)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise McpProbeError(f"MCP response contained invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise McpProbeError("MCP response JSON-RPC payload must be an object")
    return payload


def _post_jsonrpc(
    url: str,
    payload: JsonObject,
    timeout_seconds: float,
    opener: UrlOpener,
) -> JsonObject:
    """Send one streamable HTTP JSON-RPC request and return its response."""
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )

    try:
        with opener(request, timeout=timeout_seconds) as response:
            response_body = response.read()
    except HTTPError as exc:
        raise McpProbeError(f"MCP endpoint returned HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise McpProbeError(f"MCP endpoint unavailable: {exc.reason}") from exc
    except TimeoutError as exc:
        raise McpProbeError("MCP endpoint timed out") from exc

    response_payload = parse_sse_jsonrpc(response_body)
    if error := response_payload.get("error"):
        raise McpProbeError(f"MCP JSON-RPC error: {error}")
    return response_payload


def _result_payload(response_payload: JsonObject, method: str) -> JsonObject:
    """Extract a JSON-RPC result object from `response_payload`."""
    result = response_payload.get("result")
    if not isinstance(result, dict):
        raise McpProbeError(f"MCP method {method} returned no object result")
    return result


def probe_mcp_tool(
    url: str,
    tool: str,
    arguments: JsonObject,
    *,
    expected_server_name: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> JsonObject:
    """Verify that an MCP server exposes and can call `tool`.

    Args:
        url: Streamable HTTP MCP endpoint.
        tool: Tool name to verify and call.
        arguments: JSON object passed to the tool call.
        expected_server_name: Optional `initialize` serverInfo.name contract.
        timeout_seconds: Per-request timeout.
        opener: Injectable URL opener for tests.

    Returns:
        A compact success payload for CLI output.

    Raises:
        McpProbeError: If initialization, tool discovery, or the tool call fails.
    """
    initialize_response = _post_jsonrpc(
        url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": DEFAULT_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "bureau-healthcheck", "version": "0"},
            },
        },
        timeout_seconds,
        opener,
    )
    initialize_result = _result_payload(initialize_response, "initialize")
    server_info = initialize_result.get("serverInfo", {})
    server_name = server_info.get("name") if isinstance(server_info, dict) else None
    if expected_server_name and server_name != expected_server_name:
        raise McpProbeError(
            f"expected server '{expected_server_name}', got '{server_name}'"
        )

    list_response = _post_jsonrpc(
        url,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        timeout_seconds,
        opener,
    )
    list_result = _result_payload(list_response, "tools/list")
    tools = list_result.get("tools")
    if not isinstance(tools, list):
        raise McpProbeError("MCP tools/list returned no tools array")

    tool_names = {
        item.get("name")
        for item in tools
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if tool not in tool_names:
        raise McpProbeError(f"MCP server does not expose tool '{tool}'")

    call_response = _post_jsonrpc(
        url,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
        timeout_seconds,
        opener,
    )
    call_result = _result_payload(call_response, "tools/call")
    if call_result.get("isError") is True:
        raise McpProbeError(f"MCP tool '{tool}' reported an error")

    return {"status": "ok", "server": server_name, "tool": tool}


def main() -> int:
    """Run the MCP probe from the command line."""
    parser = argparse.ArgumentParser(description="Probe a streamable HTTP MCP tool.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments-json", required=True)
    parser.add_argument("--expected-server-name", default=None)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    args = parser.parse_args()

    try:
        arguments = json.loads(args.arguments_json)
    except json.JSONDecodeError as exc:
        print(f"Invalid --arguments-json: {exc}", file=sys.stderr)
        return 2
    if not isinstance(arguments, dict):
        print("--arguments-json must decode to an object", file=sys.stderr)
        return 2

    try:
        result = probe_mcp_tool(
            args.url,
            args.tool,
            arguments,
            expected_server_name=args.expected_server_name,
            timeout_seconds=args.timeout_seconds,
        )
    except McpProbeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
