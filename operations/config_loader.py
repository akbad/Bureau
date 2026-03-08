"""Bureau configuration loader providing type-safe access to all Bureau settings.

1. Merges configuration from YAML files with the following precedence hierarchy
   (later sources override earlier ones):

   a. defaults.yml:  Package defaults (all git-tracked settings)
   b. .bureau.yml:   Project config (optional, discovered by CWD walk-up)
   c. local.yml:     Personal overrides (gitignored)
   d. env vars:      Highest-priority runtime overrides

2. Loads configuration

"""

import os
import re
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeAlias, TypedDict, cast

import yaml


# runtime invariants are documented in docs/CONFIGURATION.md and are not fully
# enforceable via TypedDict alone; several schemas below are discriminator-based
# (for example, kind/transport) and rely on runtime validation conventions


# TypedDict schemas corresponding to nested YAML config sections
class RetentionPeriodForConfig(TypedDict):
    claude_mem: str
    serena: str
    qdrant: str
    memory_mcp: str


class TrashConfig(TypedDict):
    grace_period: str


class CleanupConfig(TypedDict):
    min_interval: str


class StartupTimeoutForConfig(TypedDict):
    mcp_servers: int
    docker_daemon: int


class PathToConfig(TypedDict, total=False):
    workspace: str
    serena_memories_root: str
    mcp_clones: str


class AgentSourceConfig(TypedDict):
    path: str
    cli: list[str]


class NativeAgentsConfig(TypedDict, total=False):
    enabled: list[str] | str  # List of agent names or "all"
    disabled: list[str]
    sources: list[AgentSourceConfig]


class MCPDependencyConfig(TypedDict, total=False):
    """Config for an entry in mcp.dependencies."""

    enabled: bool
    kind: str
    repo_url: str
    branch: str
    path: str
    post_clone: list[list[str]]


class MCPDependsOnConfig(TypedDict, total=False):
    """Shared depends_on schema for services and client configs."""

    services: list[str]
    dependencies: list[str]


class MCPHealthcheckConfig(TypedDict, total=False):
    """Runtime service healthcheck settings."""

    tcp: int | str


class MCPMountConfig(TypedDict):
    """Docker mount entry."""

    host_path: str
    container_path: str


class MCPRuntimeServiceConfig(TypedDict, total=False):
    """Config for an entry in mcp.runtime_services."""

    enabled: bool
    kind: str
    depends_on: MCPDependsOnConfig
    healthcheck: MCPHealthcheckConfig
    env: dict[str, str]
    command: list[str]
    settings: dict[str, Any]
    # docker_container fields
    container_name: str
    image: str
    host_port: int | str
    container_port: int | str
    mounts: list[MCPMountConfig]
    # http_process fields
    port: int | str


class MCPPostConfig(TypedDict, total=False):
    """CLI-specific side effects for a client config."""

    claude_settings_env: dict[str, str]


class MCPClientTransportConfig(TypedDict, total=False):
    """A single clients.<client_id> transport configuration."""

    transport: str
    url: str
    headers: dict[str, str]
    command: list[str]
    env: dict[str, str]
    timeout_ms: int
    startup_timeout_sec: int
    tool_timeout_sec: int
    post_config: MCPPostConfig


# allows mixed `clients` values: either a "default" client object 
#   OR the "disabled_for" list
MCPClientEntry: TypeAlias = MCPClientTransportConfig | list[str]


class MCPClientConfig(TypedDict, total=False):
    """Config for an entry in mcp.client_configs."""

    enabled: bool
    requires_env: list[str]
    depends_on: MCPDependsOnConfig
    clients: dict[str, MCPClientEntry]
    settings: dict[str, Any]
    storage_path: str


class MCPConfig(TypedDict, total=False):
    """Top-level mcp configuration."""

    dependencies: dict[str, MCPDependencyConfig]
    runtime_services: dict[str, MCPRuntimeServiceConfig]
    client_configs: dict[str, MCPClientConfig]


class ConversationsConciergeConfig(TypedDict, total=False):
    """Concierge-specific dossier behaviors."""

    auto_offer_resume: bool
    auto_offer_save: bool
    notify_task_updates: bool
    notify_interval: str


class ConversationsConfig(TypedDict, total=False):
    """Dossiers: cross-agent conversation continuity configuration."""

    save: str                                   # command verb, default "fold"
    resume: str                                 # command verb, default "unfold"
    storage_dir: str                            # default "~/.config/bureau/dossiers"
    stale_dossier_days: int                     # cleanup threshold, default 30
    concierge: ConversationsConciergeConfig
    keywords: dict[str, list[str]]


# root-level config-modeling object
class Config(TypedDict, total=False):
    agents: list[str]
    retention_period_for: RetentionPeriodForConfig
    trash: TrashConfig
    cleanup: CleanupConfig
    startup_timeout_for: StartupTimeoutForConfig
    path_to: PathToConfig
    roles: NativeAgentsConfig
    mcp: MCPConfig
    conversations: ConversationsConfig


def find_repo_root(start_path: Path | None = None) -> Path:
    """Find the repository root by looking for defaults.yml or .git directory.

    Args:
        start_path: Starting directory for search. Defaults to cwd.

    Returns:
        Path to repository root.

    Raises:
        FileNotFoundError: If no repo root found.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while True:
        if (current / "defaults.yml").exists() or (current / ".git").exists():
            return current
        elif current == current.parent:
            # reached root dir without finding repo root
            raise FileNotFoundError(
                f"Could not find repository root (defaults.yml or .git) starting from {start_path}"
            )
        current = current.parent


def find_project_config() -> Path | None:
    """
    Find .bureau.yml by walking up from cwd.

    Searches from the current working directory upward, stopping at
    filesystem root. Returns None if no .bureau.yml is found.
    
    Does NOT search inside the Bureau repo itself 
    (to avoid confusion if Bureau DOES ever happen to have a .bureau.yml).
    """
    try:
        repo_root = find_repo_root().resolve()
    except FileNotFoundError:
        repo_root = None

    current = Path.cwd().resolve()

    while True:
        candidate = current / ".bureau.yml"

        # skip the Bureau repo root itself to avoid self-referencing
        if (repo_root and current == repo_root) or (not candidate.exists()):
            if current == current.parent:
                # reached root dir without finding a .bureau.yml
                return None
            current = current.parent
            continue

        return candidate


def get_main_repo_root() -> Path:
    """Get the main repository root (not worktree root).

    Uses `git rev-parse --git-common-dir` which returns:
      - Main repo: `.git` (relative)
      - Worktree: `/path/to/main/.git` (absolute path to main repo's .git)

    The parent of the git directory is the main repo root.

    Returns:
        Path to main repository root.

    Raises:
        FileNotFoundError: If not in a git repository.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_common_dir = Path(result.stdout.strip())

        # If relative path (like `.git`), resolve from cwd
        if not git_common_dir.is_absolute():
            git_common_dir = (Path.cwd() / git_common_dir).resolve()
        else:
            git_common_dir = git_common_dir.resolve()

        # Parent of .git is the repo root
        return git_common_dir.parent
    except subprocess.CalledProcessError as e:
        raise FileNotFoundError(
            f"Not in a git repository: {e.stderr.strip()}"
        ) from e


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively deep-merge two dicts with `override` taking precedence.

    Nested values are merged ONLY when both are dictionaries;
    otherwise the value from `override` replaces `base`.

    Args:
        base:      Base dictionary
        override:  Dictionary with override values

    Returns:
        Merged dictionary.
    """
    result = base.copy()

    for key, override_value in override.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = deep_merge(base_value, override_value)
        else:
            result[key] = override_value

    return result


def expand_path(path_str: str) -> Path:
    """Expand `~` and environment variables in path string."""
    expanded = os.path.expandvars(os.path.expanduser(path_str))
    return Path(expanded)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load YAML file if it exists, otherwise return empty dict."""
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


@lru_cache(maxsize=1)  # cache most recent returned config (clear using clear_config_cache())
def get_config() -> Config:
    """Load and merge configs, following this resolution order:

    1. defaults.yml (package defaults, required)
    2. .bureau.yml (project config, optional — discovered by CWD walk-up)
    3. local.yml (personal overrides, optional — gitignored)
    4. Environment variables (highest priority)

    Settings specified at layers LATER in the list OVERRIDE IDENTICAL SETTINGS
    at layers EARLIER in the list.
    > e.g. `auto_approved.mcp_tools: true` in local.yml overrides the default in defaults.yml

    Returns:
        Merged configuration dictionary.

    Raises:
        FileNotFoundError: If repo root cannot be found.

    NOTE: when testing this function:
    1. monkeypatch find_repo_root() to return the temp testing directory path
    2. call clear_config_cache() to clear cache
    3. call get_config() to do a fresh config read, retrieving the test-oriented config
    
    Example of this testing approach:

        monkeypatch.setattr("operations.config_loader.find_repo_root", lambda: tmp_path)
        clear_config_cache()
        config = get_config()
    """
    repo_root = find_repo_root()

    config: dict[str, Any] = {}

    # 1. Package defaults (required)
    config = deep_merge(config, _load_yaml_file(repo_root / "defaults.yml"))

    # 2. Project config (optional, discovered by CWD walk-up)
    project_config_path = find_project_config()
    if project_config_path:
        config = deep_merge(config, _load_yaml_file(project_config_path))

    # 3. Personal overrides (optional, gitignored)
    config = deep_merge(config, _load_yaml_file(repo_root / "local.yml"))

    # Apply environment variable overrides for path_to
    path_to = config.get("path_to", {})
    path_env_overrides = {
        "serena_memories_root": "BUREAU_WORKSPACE",
    }

    for path_key, env_var in path_env_overrides.items():
        if env_val := os.environ.get(env_var):
            path_to[path_key] = env_val

    # Derive paths from workspace if not explicitly set
    if workspace := path_to.get("workspace"):
        # Only set these if not already configured
        if "serena_memories_root" not in path_to:
            path_to["serena_memories_root"] = workspace

    # Resolve mcp_clones: relative paths are resolved from main repo root (shared across worktrees)
    if mcp_clones := path_to.get("mcp_clones"):
        if not mcp_clones.startswith("/") and not mcp_clones.startswith("~"):
            path_to["mcp_clones"] = str(get_main_repo_root() / mcp_clones)

    config["path_to"] = path_to

    return config  # type: ignore[return-value]


def clear_config_cache() -> None:
    """Clear the cached config (for testing)."""
    get_config.cache_clear()


# Convenience accessors
def get_enabled_agents() -> list[str]:
    """Get list of enabled agent names."""
    config = get_config()
    return config.get("agents", [])


def is_agent_enabled(agent_name: str) -> bool:
    """Check if a specific agent is enabled.

    Args:
        agent_name: Agent name (claude, gemini, codex, opencode).

    Returns:
        True if agent is in enabled list.
    """
    return agent_name.lower() in [a.lower() for a in get_enabled_agents()]


def get_retention(storage_name: str) -> str:
    """Get retention period for a storage backend.

    Args:
        storage_name: Storage name (e.g., "claude-mem", "qdrant").

    Returns:
        Retention period string (e.g., "30d").
    """
    config = get_config()
    # Normalize: claude-mem -> claude_mem
    key = storage_name.replace("-", "_")
    return cast(str, config.get("retention_period_for", {}).get(key, "30d"))


def get_trash_grace_period() -> str:
    """Get trash grace period."""
    config = get_config()
    return config.get("trash", {}).get("grace_period", "30d")


def get_cleanup_interval() -> str:
    """Get minimum cleanup interval."""
    config = get_config()
    return config.get("cleanup", {}).get("min_interval", "24h")


def get_path(path_name: str) -> Path:
    """Get a configured file path, expanded.

    Args:
        path_name: Path key (serena_memories_root, mcp_clones).

    Returns:
        Expanded Path object.
    """
    config = get_config()
    path_str = cast(str, config.get("path_to", {}).get(path_name, ""))
    return expand_path(path_str) if path_str else Path()


def get_mcp_dependency(name: str) -> MCPDependencyConfig | None:
    """Get MCP dependency config by name."""
    mcp_config = get_config().get("mcp")
    if not mcp_config:
        return None
    dependencies = mcp_config.get("dependencies")
    if not dependencies:
        return None
    return dependencies.get(name)


def get_mcp_service(name: str) -> MCPRuntimeServiceConfig | None:
    """Get MCP runtime service config by name."""
    mcp_config = get_config().get("mcp")
    if not mcp_config:
        return None
    runtime_services = mcp_config.get("runtime_services")
    if not runtime_services:
        return None
    return runtime_services.get(name)


def get_mcp_server(name: str) -> MCPClientConfig | None:
    """Get MCP client config by name."""
    mcp_config = get_config().get("mcp")
    if not mcp_config:
        return None
    client_configs = mcp_config.get("client_configs")
    if not client_configs:
        return None
    return client_configs.get(name)


def get_storage(storage_name: str) -> Path | None:
    """Get a configured storage path, expanded.

    Args:
        storage_name: Storage key (memory_mcp, claude_mem).

    Returns:
        Expanded Path object or None if not configured.
    """
    path_str = ""
    if storage_name == "memory_mcp":
        server = get_mcp_server("memory") or {}
        path_str = cast(str, server.get("storage_path", ""))
    elif storage_name == "claude_mem":
        # Try dependency first, then fall back to service for backwards compatibility
        dependency = get_mcp_dependency("claude_mem_storage")
        if dependency:
            path_str = cast(str, dependency.get("path", ""))
        else:
            service = get_mcp_service("claude_mem_storage") or {}
            path_str = cast(str, service.get("path", ""))

    return expand_path(path_str) if path_str else None


# Path constants (computed from config)
def get_repo_root() -> Path:
    """Get repository root path."""
    try:
        return find_repo_root()
    except FileNotFoundError:
        return Path.cwd()


def get_archives_dir() -> Path:
    """Get .archives directory path (in repo root)."""
    return get_repo_root() / ".archives"


def get_state_path() -> Path:
    """Get state.json path."""
    return get_archives_dir() / "state.json"


def get_trash_dir() -> Path:
    """Get trash directory path."""
    return get_archives_dir() / "trash"


def get_qdrant_url() -> str:
    """Get Qdrant server URL."""
    from .config_templating import expand_placeholders

    service = get_mcp_service("qdrant_mcp") or {}
    env = service.get("env", {}) if isinstance(service, dict) else {}
    url = env.get("QDRANT_URL") if isinstance(env, dict) else ""
    if not url:
        return ""
    return expand_placeholders(str(url), get_config(), os.environ)


def get_qdrant_collection() -> str:
    """Get Qdrant collection name."""
    from .config_templating import expand_placeholders

    service = get_mcp_service("qdrant_mcp") or {}
    settings = service.get("settings", {}) if isinstance(service, dict) else {}
    collection = settings.get("collection") if isinstance(settings, dict) else ""
    if not collection:
        return ""
    return expand_placeholders(str(collection), get_config(), os.environ)


def get_conversations_config() -> ConversationsConfig:
    """Get conversations (dossiers) configuration."""
    config = get_config()
    return config.get("conversations", {})


# Duration parsing (moved from cleanup/config.py)
def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string like '30d', '2w', '3m', '1y', '24h' to timedelta.

    Args:
        duration_str: Duration string (e.g., "30d", "24h", "always").

    Returns:
        timedelta object.

    Raises:
        ValueError: If format is invalid.
    """
    if duration_str.lower() == "always":
        return timedelta.max

    match = re.match(r"^(\d+)([hdwmy])$", duration_str.lower())
    if not match:
        raise ValueError(
            f"Invalid duration format: {duration_str}. "
            "Use format like '24h', '30d', '2w', '3m', '1y'"
        )

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    elif unit == "m":
        return timedelta(days=value * 30)  # Approximate month
    elif unit == "y":
        return timedelta(days=value * 365)  # Approximate year

    raise ValueError(f"Unknown duration unit: {unit}")
