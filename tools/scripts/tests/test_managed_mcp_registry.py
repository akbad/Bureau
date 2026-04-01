import json
from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "managed-mcp-registry.py"
spec = util.spec_from_file_location("managed_mcp_registry", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

normalize_entry = module.normalize_entry
normalize_desired_entry = module.normalize_desired_entry
fingerprint_entry = module.fingerprint_entry
compute_prune = module.compute_prune
compute_update = module.compute_update
record_registry = module.record_registry
load_cli_entries = module.load_cli_entries
load_registry = module.load_registry
write_registry = module.write_registry


def test_normalize_entries_across_clis():
    assert normalize_entry(
        "claude",
        {"type": "http", "url": "http://x", "headers": {"A": "b"}},
    ) == {"transport": "http", "url": "http://x", "headers": {"A": "b"}}

    assert normalize_entry(
        "gemini",
        {
            "command": "uvx",
            "args": ["mcp"],
            "env": {"A": "b"},
            "timeout": 123,
        },
    ) == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp"],
        "env": {"A": "b"},
        "timeout_ms": 123,
    }

    assert normalize_entry(
        "codex",
        {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp"],
            "env": {"A": "b"},
            "startup_timeout_sec": 5,
            "tool_timeout_sec": 9,
        },
    ) == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp"],
        "env": {"A": "b"},
        "startup_timeout_sec": 5,
        "tool_timeout_sec": 9,
    }

    assert normalize_entry(
        "opencode",
        {
            "type": "local",
            "command": ["uvx", "mcp"],
            "timeout": 2500,
        },
    ) == {
        "transport": "stdio",
        "command": ["uvx", "mcp"],
        "timeout_ms": 2500,
    }


def test_fingerprint_stable_for_same_input():
    normalized = {"transport": "http", "url": "http://x"}
    assert fingerprint_entry(normalized) == fingerprint_entry(normalized)


def test_compute_prune_only_removes_matching_fingerprints():
    plan = {"client_configs": {"claude": {"keep": {}}}}
    current_entries = {
        "keep": {"type": "http", "url": "http://keep"},
        "remove": {"type": "http", "url": "http://remove"},
        "changed": {"type": "http", "url": "http://changed"},
    }
    registry = {
        "version": 1,
        "servers": {
            "remove": {
                "fingerprint": fingerprint_entry(
                    normalize_entry("claude", current_entries["remove"])
                )
            },
            "changed": {
                "fingerprint": "not-the-same",
            },
            "missing": {
                "fingerprint": "irrelevant",
            },
        },
    }

    to_remove = compute_prune("claude", plan, registry, current_entries)

    assert to_remove == ["remove"]


def test_normalize_desired_entry_for_codex_stdio():
    desired = normalize_desired_entry(
        "codex",
        {
            "transport": "stdio",
            "command": ["/tmp/mcp-filter", "--include", "read_multiple_files"],
            "env": {"A": "b"},
            "startup_timeout_sec": 5,
            "tool_timeout_sec": 9,
        },
    )

    assert desired == {
        "transport": "stdio",
        "command": "/tmp/mcp-filter",
        "args": ["--include", "read_multiple_files"],
        "env": {"A": "b"},
        "startup_timeout_sec": 5,
        "tool_timeout_sec": 9,
    }


def test_compute_update_marks_managed_entry_when_desired_changes():
    current_entries = {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-filter", "--include", "read_multiple_files"],
            "startup_timeout_sec": 30,
        }
    }
    plan = {
        "client_configs": {
            "codex": {
                "filesystem": {
                    "transport": "stdio",
                    "command": [
                        "/shared/.mcp-servers/npm-tools/node_modules/.bin/mcp-filter",
                        "--include",
                        "read_multiple_files",
                    ],
                    "startup_timeout_sec": 30,
                }
            }
        }
    }
    registry = {
        "version": 1,
        "servers": {
            "filesystem": {
                "fingerprint": fingerprint_entry(
                    normalize_entry("codex", current_entries["filesystem"])
                )
            }
        },
    }

    to_update = compute_update("codex", plan, registry, current_entries)

    assert to_update == ["filesystem"]


def test_compute_update_skips_user_modified_entry():
    current_entries = {
        "filesystem": {
            "transport": "stdio",
            "command": "custom-wrapper",
            "args": ["filesystem"],
        }
    }
    plan = {
        "client_configs": {
            "codex": {
                "filesystem": {
                    "transport": "stdio",
                    "command": ["/shared/.mcp-servers/npm-tools/node_modules/.bin/mcp-filter"],
                }
            }
        }
    }
    registry = {
        "version": 1,
        "servers": {
            "filesystem": {
                "fingerprint": fingerprint_entry(
                    {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "mcp-filter"],
                    }
                )
            }
        },
    }

    to_update = compute_update("codex", plan, registry, current_entries)

    assert to_update == []


def test_record_registry_tracks_only_desired_entries():
    plan = {"client_configs": {"gemini": {"keep": {}, "missing": {}}}}
    current_entries = {
        "keep": {"httpUrl": "http://keep"},
    }

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        now="2026-01-01T00:00:00+00:00",
    )

    assert recorded["version"] == 1
    assert recorded["updated_at"] == "2026-01-01T00:00:00+00:00"
    assert list(recorded["servers"].keys()) == ["keep"]


def test_load_codex_entries_from_toml(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[mcp_servers.alpha]
transport = "http"
url = "http://alpha"
""",
        encoding="utf-8",
    )

    entries = load_cli_entries("codex", str(config_path))

    assert entries["alpha"]["transport"] == "http"
    assert entries["alpha"]["url"] == "http://alpha"
