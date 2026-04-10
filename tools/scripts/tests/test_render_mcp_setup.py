from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "render-mcp-setup.py"
spec = util.spec_from_file_location("render_mcp_setup", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
render_setup_plan = module.render_setup_plan


def test_warns_when_server_skipped_for_missing_requires_env(capsys, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "tavily": {
                    "enabled": True,
                    "requires_env": ["TAVILY_API_KEY", "OPENAI_API_KEY"],
                    "clients": {
                        "default": {
                            "transport": "http",
                            "url": "https://tavily/mcp",
                        }
                    },
                }
            }
        },
    }

    plan = render_setup_plan(config)
    captured = capsys.readouterr()

    assert "tavily" not in plan["client_configs"]["claude"]
    assert "tavily" not in plan["client_configs"]["codex"]
    assert "Skipping MCP server 'tavily'" in captured.err
    assert "OPENAI_API_KEY" in captured.err
    assert "TAVILY_API_KEY" in captured.err


def test_renders_servers_for_all_clis():
    config = {
        "agents": ["claude", "gemini", "codex", "opencode"],
        "mcp": {
            "client_configs": {
                "tavily": {
                    "enabled": True,
                    "clients": {
                        "default": {
                            "transport": "http",
                            "url": "https://tavily/mcp",
                        }
                    },
                }
            }
        },
    }

    plan = render_setup_plan(config)

    assert "tavily" in plan["client_configs"]["claude"]
    assert "tavily" in plan["client_configs"]["codex"]
    assert "tavily" in plan["client_configs"]["opencode"]


def test_auto_approved_lists_sorted_servers():
    config = {
        "agents": ["claude", "gemini", "codex"],
        "mcp": {
            "client_configs": {
                "brave": {
                    "enabled": True,
                    "clients": {
                        "default": {"transport": "stdio", "command": ["npx", "brave"]}
                    },
                },
                "tavily": {
                    "enabled": True,
                    "clients": {
                        "default": {
                            "transport": "http",
                            "url": "https://tavily/mcp",
                        }
                    },
                },
            }
        },
    }

    plan = render_setup_plan(config)

    assert plan["auto_approved"]["mcp_servers"]["claude"] == ["brave", "tavily"]


def test_setup_plan_uses_services_key():
    config = {
        "agents": ["claude"],
        "mcp": {
            "services": {
                "svc": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 8782,
                    "command": ["uvx", "run", "svc"],
                }
            },
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "default": {"transport": "http", "url": "http://localhost:8782/mcp"}
                    },
                }
            },
        },
    }

    plan = render_setup_plan(config)

    assert "services" in plan
    assert "runtime_services" not in plan
    assert "svc" in plan["services"]


def test_includes_auto_approved_block():
    config = {
        "agents": ["claude"],
        "auto_approved": {
            "bash": {
                "enabled": True,
                "ruleset": {
                    "allow": ["git status"],
                    "deny": ["rm"],
                },
            },
        },
    }

    plan = render_setup_plan(config)

    assert plan["auto_approved"]["bash"] == config["auto_approved"]["bash"]
    assert plan["auto_approved"]["mcp_servers"]["claude"] == []


def test_includes_prune_disabled_mcps():
    config = {
        "agents": ["claude"],
        "prune_disabled_mcps": True,
    }

    plan = render_setup_plan(config)

    assert plan["prune_disabled_mcps"] is True


def test_aggregates_npm_runtime_for_included_servers():
    config = {
        "agents": ["claude", "codex"],
        "path_to": {"mcp_clones": "/tmp/mcp-clones"},
        "mcp": {
            "client_configs": {
                "filesystem": {
                    "enabled": True,
                    "npm_runtime": {
                        "packages": [
                            "mcp-filter",
                            "@modelcontextprotocol/server-filesystem",
                        ],
                        "binaries": [
                            "mcp-filter",
                            "mcp-server-filesystem",
                        ],
                    },
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": ["/tmp/mcp-filter", "--"],
                        }
                    },
                },
            }
        },
    }

    plan = render_setup_plan(config)

    assert plan["npm_runtime"]["runtime_dir"] == "/tmp/mcp-clones/npm-tools"
    assert plan["npm_runtime"]["cache_dir"] == "/tmp/mcp-clones/npm-tools/.npm-cache"
    assert plan["npm_runtime"]["packages"] == [
        "@modelcontextprotocol/server-filesystem",
        "mcp-filter",
    ]
    assert plan["npm_runtime"]["binaries"] == [
        "mcp-filter",
        "mcp-server-filesystem",
    ]
    assert "filesystem" in plan["npm_runtime"]["servers"]


def test_skips_npm_runtime_for_servers_disabled_for_all_agents():
    config = {
        "agents": ["claude"],
        "path_to": {"mcp_clones": "/tmp/mcp-clones"},
        "mcp": {
            "client_configs": {
                "filesystem": {
                    "enabled": True,
                    "npm_runtime": {
                        "packages": ["mcp-filter"],
                        "binaries": ["mcp-filter"],
                    },
                    "clients": {
                        "disabled_for": ["claude"],
                        "default": {
                            "transport": "stdio",
                            "command": ["/tmp/mcp-filter", "--"],
                        },
                    },
                }
            }
        },
    }

    plan = render_setup_plan(config)

    assert plan["npm_runtime"] == {}


# ── disabled_for tests ─────────────────────────────────────────────

def test_disabled_for_excludes_agent():
    config = {
        "agents": ["claude", "codex", "gemini"],
        "mcp": {
            "client_configs": {
                "qdrant": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["codex"],
                        "default": {"transport": "http", "url": "http://localhost:9090/mcp/"},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "qdrant" in plan["client_configs"]["claude"]
    assert "qdrant" in plan["client_configs"]["gemini"]
    assert "qdrant" not in plan["client_configs"]["codex"]


def test_disabled_for_excludes_even_with_explicit_cli_config():
    """disabled_for takes precedence over an explicit clients.<cli> config."""
    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["codex"],
                        "default": {"transport": "http", "url": "http://x"},
                        "codex": {"transport": "stdio", "command": ["test"]},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "srv" in plan["client_configs"]["claude"]
    assert "srv" not in plan["client_configs"]["codex"]


def test_disabled_for_removes_from_auto_approved():
    """Servers disabled for a CLI must not appear in auto_approved.mcp_servers."""
    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["codex"],
                        "default": {"transport": "http", "url": "http://x"},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "srv" in plan["auto_approved"]["mcp_servers"]["claude"]
    assert "srv" not in plan["auto_approved"]["mcp_servers"]["codex"]


def test_disabled_for_empty_list_disables_nothing():
    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": [],
                        "default": {"transport": "http", "url": "http://x"},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "srv" in plan["client_configs"]["claude"]
    assert "srv" in plan["client_configs"]["codex"]


def test_disabled_for_all_agents_excludes_server_entirely():
    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["claude", "codex"],
                        "default": {"transport": "http", "url": "http://x"},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "srv" not in plan["client_configs"]["claude"]
    assert "srv" not in plan["client_configs"]["codex"]


# ── codex_tools tests ────────────────────────────────────────────────

def test_codex_tools_included_in_auto_approved():
    """Catalog entries with tools lists should appear in codex_tools."""
    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "qdrant": {
                    "enabled": True,
                    "tools": ["qdrant-find", "qdrant-store"],
                    "clients": {
                        "default": {"transport": "http", "url": "http://localhost:8782/mcp/"},
                    },
                },
                "tavily": {
                    "enabled": True,
                    "tools": ["tavily_search", "tavily_extract"],
                    "clients": {
                        "default": {"transport": "http", "url": "https://tavily/mcp"},
                    },
                },
            }
        },
    }
    plan = render_setup_plan(config)
    codex_tools = plan["auto_approved"]["mcp_servers"]["codex_tools"]
    assert codex_tools["qdrant"] == ["qdrant-find", "qdrant-store"]
    assert codex_tools["tavily"] == ["tavily_extract", "tavily_search"]


def test_codex_tools_omitted_when_no_tools_declared():
    """Entries without a tools key should be absent from codex_tools."""
    config = {
        "agents": ["codex"],
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "default": {"transport": "http", "url": "http://x"},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "srv" not in plan["auto_approved"]["mcp_servers"]["codex_tools"]


def test_codex_tools_respects_disabled_for():
    """Server disabled for codex should not appear in codex_tools."""
    config = {
        "agents": ["claude", "codex"],
        "mcp": {
            "client_configs": {
                "qdrant": {
                    "enabled": True,
                    "tools": ["qdrant-find", "qdrant-store"],
                    "clients": {
                        "disabled_for": ["codex"],
                        "default": {"transport": "http", "url": "http://localhost:8782/mcp/"},
                    },
                }
            }
        },
    }
    plan = render_setup_plan(config)
    assert "qdrant" not in plan["auto_approved"]["mcp_servers"]["codex_tools"]
