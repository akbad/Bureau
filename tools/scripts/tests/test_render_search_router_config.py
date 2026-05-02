import json
from importlib import util
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "render-search-router-config.py"
spec = util.spec_from_file_location("render_search_router_config", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_render_router_config_writes_bureau_search_settings(tmp_path):
    config_path = tmp_path / "search-router.json"
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps({
            "client_configs": {
                "claude": {
                    "bureau-search": {
                        "transport": "stdio",
                        "command": ["uv", "run", "bureau-search-mcp"],
                    }
                }
            },
            "catalog_client_configs": {
                "bureau-search": {
                    "settings": {
                        "config_path": str(config_path),
                        "searxng_url": "http://127.0.0.1:8786",
                        "profiles": {
                            "web": {"engines": ["duckduckgo", "bing"]},
                            "code": {"engines": ["stackoverflow", "github"]},
                        },
                    }
                }
            },
        }),
        encoding="utf-8",
    )

    result = module.render_router_config_from_plan(plan_path, "bureau-search")

    assert result["config_path"] == str(config_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["searxng_url"] == "http://127.0.0.1:8786"
    assert payload["profiles"]["code"]["engines"] == ["stackoverflow", "github"]
