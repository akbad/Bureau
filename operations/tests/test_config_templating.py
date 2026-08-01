from operations.config_templating import expand_placeholders


def test_expand_placeholders_prefers_env_then_config():
    config = {
        "mcp": {"services": {"qdrant_mcp": {"port": 8782}}},
    }
    env = {"TAVILY_API_KEY": "abc123"}

    value = "http://localhost:${mcp.services.qdrant_mcp.port}/mcp/?k=${TAVILY_API_KEY}"
    assert (
        expand_placeholders(value, config, env)
        == "http://localhost:8782/mcp/?k=abc123"
    )


def test_expand_placeholders_leaves_unknown_keys():
    config = {}
    env = {}
    value = "http://example.com/${UNKNOWN_KEY}"
    assert expand_placeholders(value, config, env) == value


def test_expand_placeholders_resolves_nested_config_values():
    # workspace is now a top-level anchor; the nested whitelist references ${workspace}.
    # The outer ${mcp.client_configs.fs.settings.whitelist} still exercises deep
    # (multi-segment) dot-path resolution plus recursive placeholder expansion.
    config = {
        "workspace": "~/code",
        "mcp": {"client_configs": {"fs": {"settings": {"whitelist": "${workspace}"}}}},
    }
    env = {}
    value = "root=${mcp.client_configs.fs.settings.whitelist}"
    assert expand_placeholders(value, config, env) == "root=~/code"
