from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "render-opencode-mcp.py"
spec = util.spec_from_file_location("render_opencode_mcp", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
render_opencode_mcp = module.render_opencode_mcp


def test_renders_mcp_block():
    config = {
        "agents": ["opencode"],
        "mcp": {
            "client_configs": {
                "fetch": {
                    "enabled": True,
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": ["uvx", "mcp-server-fetch"],
                        }
                    },
                }
            }
        },
    }

    result = render_opencode_mcp(config)

    assert "fetch" in result
    assert result["fetch"]["type"] == "local"


def test_local_mcp_renders_environment_and_timeout():
    config = {
        "agents": ["opencode"],
        "mcp": {
            "client_configs": {
                "open-websearch": {
                    "enabled": True,
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": ["npx", "-y", "open-websearch@2.1.7"],
                            "env": {
                                "MODE": "stdio",
                                "ALLOWED_SEARCH_ENGINES": "duckduckgo,bing",
                            },
                            "timeout_ms": 45000,
                        }
                    },
                }
            }
        },
    }

    result = render_opencode_mcp(config)

    assert result["open-websearch"] == {
        "type": "local",
        "command": ["npx", "-y", "open-websearch@2.1.7"],
        "enabled": True,
        "environment": {
            "MODE": "stdio",
            "ALLOWED_SEARCH_ENGINES": "duckduckgo,bing",
        },
        "timeout": 45000,
    }


def test_disabled_for_excludes_opencode():
    config = {
        "agents": ["opencode"],
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["opencode"],
                        "default": {
                            "transport": "stdio",
                            "command": ["npx", "srv"],
                        },
                        "opencode": {
                            "transport": "stdio",
                            "command": ["npx", "srv-opencode"],
                        },
                    },
                }
            }
        },
    }

    result = render_opencode_mcp(config)

    assert "srv" not in result
