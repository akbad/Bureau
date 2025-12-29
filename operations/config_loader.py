"""Bureau configuration loader providing type-safe access to all Bureau settings.

1. Merges configuration from YAML files with the following precedence hierarchy
   (later sources override earlier ones):

   a. charter.yml:  Fixed system config (cloud endpoints, disabled tools)
   b. directives.yml: Team defaults (agents, retention, paths)
   c. stacks/{name}.yml: Stack-specific overrides (when BUREAU_STACK is set)
   d. local.yml: Local overrides (gitignored)
   e. env vars:  Highest-priority overrides

2. Loads configuration

"""
import os
import re
from datetime import timedelta
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml


# All HOME subdirectories that Bureau tools use (source of truth for stack isolation)
BUREAU_HOME_PATHS = [
    ".claude",
    ".claude.json",      # Claude CLI state file
    ".codex",
    ".gemini",
    ".pal",
    ".config/opencode",
    ".qdrant",
    ".memory-mcp",
    ".claude-mem",
    ".neo4j",
    ".local/bin",        # Role launchers
]


class StackValidationError(Exception):
    """Raised when stack configuration is invalid."""
    pass


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


class PortForConfig(TypedDict):
    qdrant_db: int
    qdrant_mcp: int
    sourcegraph_mcp: int
    semgrep_mcp: int
    serena_mcp: int
    neo4j_db: int
    neo4j_http: int


class StorageForConfig(TypedDict, total=False):
    qdrant: str
    memory_mcp: str
    claude_mem: str
    neo4j: str


class PathToConfig(TypedDict, total=False):
    workspace: str
    serena_projects: str
    fs_mcp_whitelist: str
    mcp_clones: str
    storage_for: StorageForConfig


class QdrantConfig(TypedDict, total=False):
    collection: str
    embedding_provider: str


class Neo4jAuthConfig(TypedDict):
    username: str
    password: str


class Neo4jConfig(TypedDict, total=False):
    auth: Neo4jAuthConfig
    plugins: str


class EndpointForConfig(TypedDict):
    sourcegraph: str
    context7: str
    tavily: str


class StackConfig(TypedDict, total=False):
    """Stack configuration for parallel Bureau environments."""
    name: str
    port_offset: int
    container_prefix: str
    home_override: str
    overrides: dict[str, Any]


class Config(TypedDict, total=False):
    agents: list[str]
    retention_period_for: RetentionPeriodForConfig
    trash: TrashConfig
    cleanup: CleanupConfig
    startup_timeout_for: StartupTimeoutForConfig
    port_for: PortForConfig
    path_to: PathToConfig
    qdrant: QdrantConfig
    neo4j: Neo4jConfig
    endpoint_for: EndpointForConfig
    _stack: StackConfig  # Stack metadata when BUREAU_STACK is set


# Environment-aware config cache (replaces @lru_cache to respect BUREAU_STACK changes)
_config_cache: dict[tuple[str, ...], Config] = {}


def _get_cache_key() -> tuple[str, ...]:
    """Get cache key that includes stack environment.

    This ensures cache invalidates when BUREAU_STACK changes.
    """
    return (os.environ.get("BUREAU_STACK", ""),)


def find_repo_root(start_path: Path | None = None) -> Path:
    """Find the repository root by looking for directives.yml or .git directory.

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

    while current != current.parent:
        if (current / "directives.yml").exists() or (current / ".git").exists():
            return current
        current = current.parent

    # Check root directory
    if (current / "directives.yml").exists() or (current / ".git").exists():
        return current

    raise FileNotFoundError(
        f"Could not find repository root (directives.yml or .git) starting from {start_path}"
    )


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
    """Deep merge two dicts, with the `override` dict taking precedence.

    Args:
        base: Base dictionary.
        override: Dictionary with override values.

    Returns:
        Merged dictionary.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def expand_path(path_str: str) -> Path:
    """Expand ~ and environment variables in path string."""
    expanded = os.path.expandvars(os.path.expanduser(path_str))
    return Path(expanded)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load YAML file if it exists, otherwise return empty dict."""
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_base_ports() -> dict[str, int]:
    """Get base port configuration (without stack offsets).

    Returns:
        Dict mapping port names to their base values.
    """
    return {
        "qdrant_db": 6780,
        "qdrant_mcp": 8780,
        "sourcegraph_mcp": 3090,
        "semgrep_mcp": 4151,
        "serena_mcp": 5100,
        "neo4j_db": 7687,
        "neo4j_http": 7474,
    }


def validate_stack(stack_name: str, stack_config: dict[str, Any]) -> None:
    """Validate stack configuration.

    Args:
        stack_name: Name of the stack.
        stack_config: Stack configuration dict.

    Raises:
        StackValidationError: If configuration is invalid.
    """
    # Port range check
    base_ports = get_base_ports()
    offset = stack_config.get("port_offset", 0)

    for port_name, base_port in base_ports.items():
        effective = base_port + offset
        if effective > 65535:
            raise StackValidationError(
                f"Port overflow for stack '{stack_name}': "
                f"{port_name} = {base_port} + {offset} = {effective} (max 65535)"
            )
        if effective < 1:
            raise StackValidationError(
                f"Invalid port for stack '{stack_name}': "
                f"{port_name} = {base_port} + {offset} = {effective} (min 1)"
            )

    # Container prefix length (Docker limit: 128 chars, leave room for service name)
    prefix = stack_config.get("container_prefix", f"{stack_name}-")
    if len(prefix) > 100:
        raise StackValidationError(
            f"Container prefix too long for stack '{stack_name}': "
            f"{len(prefix)} chars (max 100)"
        )


def _load_config() -> Config:
    """Internal config loader (called by get_config with caching)."""
    repo_root = find_repo_root()

    config: dict[str, Any] = {}

    # Load base configs in precedence order (later overrides earlier)
    for filename in ["charter.yml", "directives.yml"]:
        config = deep_merge(config, _load_yaml_file(repo_root / filename))

    # Load stack config if BUREAU_STACK is set
    stack_name = os.environ.get("BUREAU_STACK")
    if stack_name:
        stack_file = repo_root / "stacks" / f"{stack_name}.yml"
        if stack_file.exists():
            stack_data = _load_yaml_file(stack_file)
            stack_config = stack_data.get("stack", {})

            # Validate stack config
            validate_stack(stack_name, stack_config)

            # Merge stack overrides into config
            if overrides := stack_config.get("overrides"):
                config = deep_merge(config, overrides)

            # Store stack metadata (accessible via config["_stack"])
            config["_stack"] = stack_config

    # Load local.yml (after stack, so local can override stack settings)
    config = deep_merge(config, _load_yaml_file(repo_root / "local.yml"))

    # Apply environment variable overrides for path_to
    path_to = config.get("path_to", {})
    path_env_overrides = {
        "serena_projects": "BUREAU_WORKSPACE",
    }

    for path_key, env_var in path_env_overrides.items():
        if env_val := os.environ.get(env_var):
            path_to[path_key] = env_val

    # Apply environment variable overrides for path_to.storage_for
    storage_for = path_to.get("storage_for", {})
    storage_env_overrides = {
        "memory_mcp": "MEMORY_MCP_STORAGE_PATH",
        "claude_mem": "CLAUDE_MEM_STORAGE_PATH",
        "qdrant": "QDRANT_STORAGE_PATH",
        "neo4j": "NEO4J_STORAGE_PATH",
    }

    for storage_key, env_var in storage_env_overrides.items():
        if env_val := os.environ.get(env_var):
            storage_for[storage_key] = env_val

    # Derive paths from workspace if not explicitly set
    if workspace := path_to.get("workspace"):
        # Only set these if not already configured
        if "serena_projects" not in path_to:
            path_to["serena_projects"] = workspace
        if "fs_mcp_whitelist" not in path_to:
            path_to["fs_mcp_whitelist"] = workspace

    # Resolve mcp_clones: relative paths are resolved from main repo root (shared across worktrees)
    if mcp_clones := path_to.get("mcp_clones"):
        if not mcp_clones.startswith("/") and not mcp_clones.startswith("~"):
            path_to["mcp_clones"] = str(get_main_repo_root() / mcp_clones)

    # Derive qdrant_url if not provided: use port_for.qdrant_db
    if "qdrant_url" not in path_to:
        ports_cfg = config.get("port_for", {})
        port = ports_cfg.get("qdrant_db", 8780)
        path_to["qdrant_url"] = f"http://127.0.0.1:{port}"

    path_to["storage_for"] = storage_for
    config["path_to"] = path_to

    # Merge Qdrant section defaults if missing
    qdrant_cfg = config.get("qdrant", {})
    if "collection" not in qdrant_cfg:
        qdrant_cfg["collection"] = "coding-memory"
    if "embedding_provider" not in qdrant_cfg:
        qdrant_cfg["embedding_provider"] = "fastembed"
    config["qdrant"] = qdrant_cfg

    return config  # type: ignore[return-value]


def get_config() -> Config:
    """Load and merge configs, following this resolution order:

    1. charter.yml (base defaults, required)
    2. directives.yml (team config, if exists)
    3. stacks/{BUREAU_STACK}.yml (if BUREAU_STACK env var is set)
    4. local.yml (local overrides, if exists)
    5. Environment variables (highest priority)

    For testing:
    1. monkeypatch find_repo_root() to return the temp testing directory path
    2. call clear_config_cache() to clear cache
    3. call get_config() to do a fresh config read, retrieving the test-oriented config

        monkeypatch.setattr("operations.config_loader.find_repo_root", lambda: tmp_path)
        clear_config_cache()
        config = get_config()

    Settings specified at paths LATER in the list OVERRIDE IDENTICAL SETTINGS at paths EARLIER in the list.
    > e.g. `mcp.auto_approve: yes` in local.yml overrides `mcp.auto_approve: no` in directives.yml

    Cache is environment-aware: changes to BUREAU_STACK env var automatically invalidate the cache.

    Returns:
        Merged configuration dictionary.

    Raises:
        FileNotFoundError: If repo root cannot be found.
        StackValidationError: If stack config is invalid.
    """
    cache_key = _get_cache_key()
    if cache_key not in _config_cache:
        _config_cache[cache_key] = _load_config()
    return _config_cache[cache_key]


def clear_config_cache() -> None:
    """Clear the cached config (for testing or after stack changes)."""
    _config_cache.clear()


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
        path_name: Path key (serena_projects, fs_mcp_whitelist, mcp_clones).

    Returns:
        Expanded Path object.
    """
    config = get_config()
    path_str = cast(str, config.get("path_to", {}).get(path_name, ""))
    return expand_path(path_str) if path_str else Path()


def get_storage(storage_name: str) -> Path:
    """Get a configured storage path, expanded.

    Args:
        storage_name: Storage key (qdrant, memory_mcp, claude_mem).

    Returns:
        Expanded Path object.
    """
    config = get_config()
    path_str = cast(str, config.get("path_to", {}).get("storage_for", {}).get(storage_name, ""))
    return expand_path(path_str) if path_str else Path()


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
    config = get_config()
    return cast(str, config.get("path_to", {}).get("qdrant_url", "http://127.0.0.1:8780"))


def get_qdrant_collection() -> str:
    """Get Qdrant collection name."""
    config = get_config()
    return config.get("qdrant", {}).get("collection", "coding-memory")


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


# =============================================================================
# Stack-aware accessors (for parallel Bureau environments)
# =============================================================================


def get_stack_info() -> StackConfig | None:
    """Get current stack configuration if BUREAU_STACK is set.

    Returns:
        Stack configuration dict, or None if no stack is active.
    """
    config = get_config()
    return config.get("_stack")


def get_effective_port(port_key: str) -> int:
    """Get effective port value with stack offset applied.

    Args:
        port_key: Port name (e.g., "qdrant_db", "neo4j_db").

    Returns:
        Base port + stack offset (if stack is active).
    """
    base_ports = get_base_ports()
    base = base_ports.get(port_key)

    if base is None:
        # Fall back to config value
        config = get_config()
        base = config.get("port_for", {}).get(port_key, 0)

    stack = get_stack_info()
    offset = stack.get("port_offset", 0) if stack else 0

    return base + offset


def get_container_name(base_name: str) -> str:
    """Get container name with stack prefix applied.

    Args:
        base_name: Base container name (e.g., "qdrant", "neo4j").

    Returns:
        Prefixed container name (e.g., "test-qdrant" if stack prefix is "test-").
    """
    stack = get_stack_info()
    if stack:
        prefix = stack.get("container_prefix", "")
        # Default prefix is "{stack_name}-" if not specified
        if not prefix:
            prefix = f"{stack.get('name', '')}-"
        return f"{prefix}{base_name}"
    return base_name


def get_effective_home() -> Path:
    """Get effective HOME directory for Bureau tools.

    Returns:
        Stack home override if set, otherwise user's HOME.
    """
    # First check BUREAU_STACK_HOME env var (set by activation script)
    if stack_home := os.environ.get("BUREAU_STACK_HOME"):
        return Path(stack_home)

    # Then check stack config
    stack = get_stack_info()
    if stack and (home_override := stack.get("home_override")):
        return expand_path(home_override)

    # Default to user's HOME
    return Path.home()


def get_home_paths() -> list[str]:
    """Get list of HOME subdirectories used by Bureau.

    Returns:
        List of relative paths (e.g., [".claude", ".gemini", ...]).
    """
    return BUREAU_HOME_PATHS.copy()
