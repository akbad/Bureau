import json
from importlib import util
from pathlib import Path
from urllib.error import HTTPError

import pytest

module_path = Path(__file__).resolve().parents[1] / "probe-mcp-tool.py"
spec = util.spec_from_file_location("probe_mcp_tool", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

McpProbeError = module.McpProbeError
parse_sse_jsonrpc = module.parse_sse_jsonrpc
probe_mcp_tool = module.probe_mcp_tool


def _sse(payload: dict) -> bytes:
    return f"event: message\ndata: {json.dumps(payload)}\n\n".encode()


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return _sse(self._payload)


def test_parse_sse_jsonrpc_returns_message_payload():
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

    assert parse_sse_jsonrpc(_sse(payload)) == payload


def test_parse_sse_jsonrpc_accepts_plain_json_response():
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

    assert parse_sse_jsonrpc(json.dumps(payload).encode()) == payload


def test_probe_mcp_tool_successful_flow():
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "mcp-server-qdrant"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [{"name": "qdrant-find"}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": "[]"}]},
        },
    ]

    def fake_urlopen(request, timeout):
        return FakeResponse(responses.pop(0))

    result = probe_mcp_tool(
        "http://127.0.0.1:8782/mcp/",
        "qdrant-find",
        {"query": "bureau healthcheck"},
        expected_server_name="mcp-server-qdrant",
        opener=fake_urlopen,
    )

    assert result["tool"] == "qdrant-find"
    assert responses == []


def test_probe_mcp_tool_rejects_server_name_mismatch():
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "other-server"}},
        },
    ]

    with pytest.raises(McpProbeError, match="expected server"):
        probe_mcp_tool(
            "http://127.0.0.1:8782/mcp/",
            "qdrant-find",
            {"query": "bureau healthcheck"},
            expected_server_name="mcp-server-qdrant",
            opener=lambda request, timeout: FakeResponse(responses.pop(0)),
        )


def test_probe_mcp_tool_rejects_missing_tool():
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "mcp-server-qdrant"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [{"name": "qdrant-store"}]},
        },
    ]

    with pytest.raises(McpProbeError, match="does not expose tool"):
        probe_mcp_tool(
            "http://127.0.0.1:8782/mcp/",
            "qdrant-find",
            {"query": "bureau healthcheck"},
            opener=lambda request, timeout: FakeResponse(responses.pop(0)),
        )


def test_probe_mcp_tool_rejects_jsonrpc_error():
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "mcp-server-qdrant"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {"code": -32601, "message": "nope"},
        },
    ]

    with pytest.raises(McpProbeError, match="JSON-RPC error"):
        probe_mcp_tool(
            "http://127.0.0.1:8782/mcp/",
            "qdrant-find",
            {"query": "bureau healthcheck"},
            opener=lambda request, timeout: FakeResponse(responses.pop(0)),
        )


def test_probe_mcp_tool_rejects_mcp_tool_error_result():
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "mcp-server-qdrant"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [{"name": "qdrant-find"}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"isError": True, "content": [{"type": "text", "text": "bad"}]},
        },
    ]

    with pytest.raises(McpProbeError, match="reported an error"):
        probe_mcp_tool(
            "http://127.0.0.1:8782/mcp/",
            "qdrant-find",
            {"query": "bureau healthcheck"},
            opener=lambda request, timeout: FakeResponse(responses.pop(0)),
        )


def test_probe_mcp_tool_wraps_http_errors():
    http_error = HTTPError(
        "http://127.0.0.1:8782/mcp/",
        500,
        "boom",
        hdrs=None,
        fp=None,
    )

    with pytest.raises(McpProbeError, match="HTTP 500"):
        probe_mcp_tool(
            "http://127.0.0.1:8782/mcp/",
            "qdrant-find",
            {"query": "bureau healthcheck"},
            opener=lambda request, timeout: (_ for _ in ()).throw(http_error),
        )
