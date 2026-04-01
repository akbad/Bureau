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

