"""Tests for tools/scripts/add-mcp-to-grok.py."""
from __future__ import annotations

from importlib import util
from pathlib import Path

import tomlkit

module_path = Path(__file__).resolve().parents[1] / "add-mcp-to-grok.py"
spec = util.spec_from_file_location("add_mcp_to_grok", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

build_http_entry = module.build_http_entry
build_stdio_entry = module.build_stdio_entry
entries_equivalent = module.entries_equivalent
upsert_mcp_server = module.upsert_mcp_server
remove_mcp_server = module.remove_mcp_server
main = module.main


def test_build_http_entry_with_headers():
    entry = build_http_entry("http://localhost:8782/mcp/", {"Authorization": "Bearer x"})
    assert entry == {
        "url": "http://localhost:8782/mcp/",
        "enabled": True,
        "headers": {"Authorization": "Bearer x"},
    }


def test_build_stdio_entry():
    entry = build_stdio_entry(
        ["uvx", "mcp-server-fetch"],
        {"FOO": "bar"},
        startup_timeout_sec=30,
    )
    assert entry["command"] == "uvx"
    assert entry["args"] == ["mcp-server-fetch"]
    assert entry["env"] == {"FOO": "bar"}
    assert entry["startup_timeout_sec"] == 30
    assert entry["enabled"] is True


def test_entries_equivalent_ignores_default_enabled():
    assert entries_equivalent(
        {"url": "http://x", "enabled": True},
        {"url": "http://x"},
    )
    assert not entries_equivalent(
        {"url": "http://x"},
        {"url": "http://y"},
    )


def test_upsert_writes_http_and_is_idempotent(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text('[cli]\ninstaller = "internal"\n', encoding="utf-8")

    entry = build_http_entry("http://localhost:8782/mcp/")
    assert upsert_mcp_server(config, "qdrant", entry) == 0
    assert upsert_mcp_server(config, "qdrant", entry) == 1  # unchanged

    doc = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert doc["cli"]["installer"] == "internal"
    assert doc["mcp_servers"]["qdrant"]["url"] == "http://localhost:8782/mcp/"
    assert doc["mcp_servers"]["qdrant"]["enabled"] is True


def test_upsert_stdio_preserves_unrelated_servers(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text(
        """
[mcp_servers.user-tool]
command = "echo"
args = ["hi"]
enabled = true
""",
        encoding="utf-8",
    )

    entry = build_stdio_entry(["uvx", "mcp-server-fetch"], {"A": "b"})
    assert upsert_mcp_server(config, "fetch", entry) == 0

    doc = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert doc["mcp_servers"]["user-tool"]["command"] == "echo"
    assert doc["mcp_servers"]["fetch"]["command"] == "uvx"
    assert list(doc["mcp_servers"]["fetch"]["args"]) == ["mcp-server-fetch"]
    assert doc["mcp_servers"]["fetch"]["env"]["A"] == "b"


def test_upsert_updates_changed_entry(tmp_path: Path):
    config = tmp_path / "config.toml"
    entry_v1 = build_http_entry("http://localhost:1/")
    assert upsert_mcp_server(config, "qdrant", entry_v1) == 0
    entry_v2 = build_http_entry("http://localhost:2/")
    assert upsert_mcp_server(config, "qdrant", entry_v2) == 0
    doc = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert doc["mcp_servers"]["qdrant"]["url"] == "http://localhost:2/"


def test_remove_mcp_server(tmp_path: Path):
    config = tmp_path / "config.toml"
    entry = build_http_entry("http://localhost:8782/mcp/")
    assert upsert_mcp_server(config, "qdrant", entry) == 0
    assert remove_mcp_server(config, "qdrant") == 0
    assert remove_mcp_server(config, "qdrant") == 1
    doc = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert "qdrant" not in doc.get("mcp_servers", {})


def test_cli_upsert_stdio_via_main(tmp_path: Path):
    config = tmp_path / "config.toml"
    rc = main(
        [
            "upsert",
            "--config",
            str(config),
            "--name",
            "fetch",
            "--transport",
            "stdio",
            "--env",
            "FOO=bar",
            "--arg",
            "uvx",
            "--arg",
            "mcp-server-fetch",
        ]
    )
    assert rc == 0
    doc = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert doc["mcp_servers"]["fetch"]["command"] == "uvx"
    assert doc["mcp_servers"]["fetch"]["env"]["FOO"] == "bar"
