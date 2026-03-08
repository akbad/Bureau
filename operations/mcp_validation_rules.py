"""MCP schema constants for deep validation.

- All validation rules are declared here as data
- The validation engine in validate_config.py consumes these constants, using them
  as rules when checking the MCP-related settings in Bureau's YML configs.
"""

from __future__ import annotations

# ── Kind enums ──────────────────────────────────────────────────────

# Permitted values for mcp.dependencies.*.kind
DEPENDENCY_KINDS: set[str] = {"git_repo", "file"}
# Permitted values for mcp.services.*.kind
SERVICE_KINDS: set[str] = {"docker_container", "http_process"}

# ── Required fields per kind ────────────────────────────────────────

# Required fields for each mcp.dependencies kind
# i.e. if mcp.dependencies.*.kind = x, these fields must also be included
DEPENDENCY_REQUIRED: dict[str, set[str]] = {
    "git_repo": {"repo_url", "path"},
    "file": {"path"},
}

# Required fields for each mcp.services kind
# i.e. if mcp.services.*.kind = x, these fields must also be included
SERVICE_REQUIRED: dict[str, set[str]] = {
    "docker_container": {"image", "host_port", "container_port"},
    "http_process": {"port", "command"},
}

# Fields that must be present for each client_config transport type (http, stdio)
CLIENT_TRANSPORT_REQUIRED: dict[str, set[str]] = {
    "http": {"url"},
    "stdio": {"command"},
}

# ── Allowed keys per bucket (for typo detection) ───────────────────
# - These are the KNOWN keys
# - *Unknown* keys produce WARNINGS, NOT ERRORS, so that user extension keys 
#   (e.g. qdrant_mcp.settings.collection) don't break.

# Recognized keys for mcp.dependencies.* entries
DEPENDENCY_ALLOWED_KEYS: set[str] = {
    "enabled", "kind", "repo_url", "branch", "path", "post_clone",
}

# Recognized keys for mcp.services.* entries
SERVICE_ALLOWED_KEYS: set[str] = {
    "enabled", "kind", "depends_on", "healthcheck", "command",
    "env", "settings", "port", "container_name", "image",
    "host_port", "container_port", "mounts",
}

# Recognized top-level keys for mcp.client_configs.* entries
CLIENT_CONFIG_ALLOWED_KEYS: set[str] = {
    "enabled", "requires_env", "depends_on", "clients",
    "settings", "storage_path",
}

# Recognized keys for individual client entries inside clients.*
CLIENT_ENTRY_ALLOWED_KEYS: set[str] = {
    "transport", "url", "headers", "command", "env",
    "post_config", "timeout_ms", "startup_timeout_sec",
    "tool_timeout_sec", "args",
}

# Recognized sub-keys inside any depends_on block
DEPENDS_ON_ALLOWED_KEYS: set[str] = {"services", "dependencies"}

# Reserved keys inside clients.* that are metadata, not client config entries
CLIENTS_RESERVED_KEYS: set[str] = {"disabled_for"}

# ── Transport enum ─────────────────────────────────────────────────

# Valid values for client entry transport field
CLIENT_TRANSPORT_KINDS: set[str] = {"http", "stdio"}

# ── Field type rules ───────────────────────────────────────────────
# Declarative (field_name, type_tag) tuples consumed by _validate_field_types().
# Type tags: "int", "dict", "dict[str,str]", "list[str]", "list[dict]", "list[list[str]]"

# Type rules for mcp.dependencies.* entries
DEPENDENCY_TYPE_RULES: list[tuple[str, str]] = [
    ("enabled", "bool"),
    ("post_clone", "list[list[str]]"),
]

# Type rules for mcp.services.* entries
SERVICE_TYPE_RULES: list[tuple[str, str]] = [
    ("command", "list[str]"),
    ("enabled", "bool"),
    ("port", "int"),
    ("host_port", "int"),
    ("container_port", "int"),
    ("env", "dict[str,str]"),
    ("mounts", "list[dict]"),
    ("healthcheck", "dict"),
    ("settings", "dict"),
]

# Type rules for mcp.client_configs.* top-level entries
CLIENT_CONFIG_TYPE_RULES: list[tuple[str, str]] = [
    ("enabled", "bool"),
    ("requires_env", "list[str]"),
    ("settings", "dict"),
]

# Type rules for individual client entries inside clients.*
CLIENT_ENTRY_TYPE_RULES: list[tuple[str, str]] = [
    ("command", "list[str]"),
    ("env", "dict[str,str]"),
]

# ── Sub-structure key sets ─────────────────────────────────────────

# Recognized sub-keys inside healthcheck blocks
HEALTHCHECK_ALLOWED_KEYS: set[str] = {"tcp"}

# Required keys inside mounts list entries
MOUNT_REQUIRED_KEYS: set[str] = {"host_path", "container_path"}
