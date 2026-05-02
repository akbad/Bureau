from importlib import util
from pathlib import Path

import yaml

module_path = Path(__file__).resolve().parents[1] / "render-mcp-setup.py"
spec = util.spec_from_file_location("render_mcp_setup", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
render_setup_plan = module.render_setup_plan
DEFAULTS_PATH = Path(__file__).resolve().parents[3] / "defaults.yml"


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


def test_default_qdrant_healthchecks_use_resolved_ports():
    config = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8"))
    config["mcp"]["services"]["qdrant_db"]["host_port"] = 9870
    config["mcp"]["services"]["qdrant_mcp"]["port"] = 9872

    plan = render_setup_plan(config)

    assert (
        plan["services"]["qdrant_db"]["healthcheck"]["http"]
        == "http://127.0.0.1:9870/readyz"
    )
    assert (
        plan["services"]["qdrant_mcp"]["healthcheck"]["mcp_tool"]["url"]
        == "http://localhost:9872/mcp/"
    )
    assert (
        plan["services"]["qdrant_mcp"]["healthcheck"]["mcp_tool"]["arguments"]
        == {"query": "bureau healthcheck"}
    )


def test_default_browsing_fallbacks_render_for_all_clis():
    config = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8"))

    plan = render_setup_plan(config)

    for cli in ["claude", "gemini", "codex", "opencode"]:
        assert "open-websearch" in plan["client_configs"][cli]
        assert "crawl4ai-mcp-server" in plan["client_configs"][cli]

    runtime_servers = plan["npm_runtime"].get("servers", {})
    assert "open-websearch" not in runtime_servers
    assert "crawl4ai-mcp-server" not in runtime_servers

    crawl4ai_client = plan["client_configs"]["codex"]["crawl4ai-mcp-server"]
    assert crawl4ai_client["startup_timeout_sec"] == 300
    assert crawl4ai_client["tool_timeout_sec"] == 1200

    assert "crawl4ai_mcp_repo" in plan["dependencies"]
    crawl4ai_post_clone = plan["dependencies"]["crawl4ai_mcp_repo"]["post_clone"]
    patch_commands = [
        command for command in crawl4ai_post_clone
        if "crawl4ai-mcp-server-c3c3b43-bureau1.patch" in command[-1]
    ]
    assert len(patch_commands) == 1
    assert "git apply --reverse --check" in patch_commands[0][2]

    assert plan["auto_approved"]["mcp_servers"]["codex_tools"]["open-websearch"] == [
        "fetchCsdnArticle",
        "fetchGithubReadme",
        "fetchJuejinArticle",
        "fetchLinuxDoArticle",
        "fetchWebContent",
        "search",
    ]
    assert plan["auto_approved"]["mcp_servers"]["codex_tools"]["crawl4ai-mcp-server"] == [
        "crawl",
        "crawl_site",
        "crawl_sitemap",
        "scrape",
    ]


def test_default_managed_searxng_and_bureau_search_render_for_all_clis():
    config = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8"))
    config["path_to"]["bureau_repo"] = "/repo/bureau"

    plan = render_setup_plan(config)

    searxng = plan["services"]["searxng"]
    assert searxng["kind"] == "docker_container"
    assert searxng["host_bind"] == "127.0.0.1"
    assert searxng["host_port"] == 8786
    assert searxng["container_port"] == 8080
    assert searxng["recreate_on_setup"] is True
    assert searxng["healthcheck"]["http"] == "http://127.0.0.1:8786/"
    assert searxng["healthcheck"]["http_headers"] == {
        "User-Agent": "BureauHealthcheck/0 (local)",
        "X-Forwarded-For": "127.0.0.1",
        "X-Real-IP": "127.0.0.1",
    }
    assert searxng["mounts"] == [
        {
            "host_path": "~/.config/bureau/searxng/settings.yml",
            "container_path": "/etc/searxng/settings.yml",
            "type": "file",
        }
    ]

    for cli in ["claude", "gemini", "codex", "opencode"]:
        assert "bureau-search" in plan["client_configs"][cli]
        client = plan["client_configs"][cli]["bureau-search"]
        assert client["transport"] == "stdio"
        assert client["command"] == [
            "uv", "--directory", "/repo/bureau", "run", "bureau-search-mcp",
        ]
        assert client["env"]["BUREAU_SEARCH_ROUTER_CONFIG"] == (
            "~/.config/bureau/internal/search-router.json"
        )

    assert plan["auto_approved"]["mcp_servers"]["codex_tools"]["bureau-search"] == [
        "bureau_search_code",
        "bureau_search_packages",
        "bureau_search_research",
        "bureau_search_web",
    ]


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
