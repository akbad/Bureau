"""Role catalog resolver.

Discovers and filters role configurations based on roles configuration.
Similar to skills_catalog.py but handles multiple source directories per CLI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .config_loader import find_repo_root


def resolve_roles_catalog(
    config: Mapping[str, Any],
    cli_name: str
) -> dict[str, Any]:
    """Resolve enabled roles for a specific CLI.

    Args:
        config: Full Bureau configuration dictionary
        cli_name: CLI name (claude, codex, gemini, opencode)

    Returns:
        Dictionary with:
            - roles: List of enabled role names (basenames without .md)
            - source_path: Path to source directory for this CLI
    """
    roles_cfg = config.get("roles", {})
    enabled = roles_cfg.get("enabled", [])
    disabled = set(roles_cfg.get("disabled", []))
    sources = roles_cfg.get("sources", [])

    # Normalize enabled setting
    if enabled == "all":
        enabled_set = None  # None means "all discovered"
    elif isinstance(enabled, list):
        enabled_set = set(enabled)
    else:
        enabled_set = set()

    # Find repo root
    try:
        repo_root = find_repo_root()
    except FileNotFoundError:
        repo_root = Path.cwd()

    # Find source directory for this CLI
    source_path = None
    for source in sources:
        if cli_name in source.get("cli", []):
            source_path = Path(source["path"]).expanduser()
            if not source_path.is_absolute():
                source_path = repo_root / source_path
            break

    if not source_path or not source_path.exists():
        return {"roles": [], "source_path": str(source_path) if source_path else ""}

    # Discover all role files
    resolved: list[str] = []
    for role_file in sorted(source_path.glob("*.md")):
        name = role_file.stem

        # Apply enabled filter
        if enabled_set is not None and name not in enabled_set:
            continue

        # Apply disabled filter (takes precedence)
        if name in disabled:
            continue

        resolved.append(name)

    return {
        "roles": resolved,
        "source_path": str(source_path)
    }


def get_enabled_roles(cli_name: str) -> list[str]:
    """Get list of enabled role names for a CLI.

    Convenience function for use in bash scripts via:
        python3 -c "from operations.roles_catalog import get_enabled_roles; ..."

    Args:
        cli_name: CLI name (claude, codex, gemini, opencode)

    Returns:
        List of enabled role names
    """
    from .config_loader import get_config

    config = get_config()
    catalog = resolve_roles_catalog(config, cli_name)
    return catalog["roles"]


def get_role_source_path(cli_name: str) -> Path:
    """Get source path for role files for a CLI.

    Args:
        cli_name: CLI name (claude, codex, gemini, opencode)

    Returns:
        Path to role source directory
    """
    from .config_loader import get_config

    config = get_config()
    catalog = resolve_roles_catalog(config, cli_name)
    return Path(catalog["source_path"])


def main() -> None:
    """CLI entry point for getting enabled roles.

    Usage:
        python -m operations.roles_catalog <cli_name>
    """
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <cli_name>", file=sys.stderr)
        print("Example: python -m operations.roles_catalog claude", file=sys.stderr)
        sys.exit(1)

    cli_name = sys.argv[1]
    roles = get_enabled_roles(cli_name)
    print(' '.join(roles))


if __name__ == "__main__":
    main()
