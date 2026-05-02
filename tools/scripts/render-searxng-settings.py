#!/usr/bin/env -S uv run
"""Render Bureau's managed SearXNG settings file.

# Design rationale
#
# Bureau owns only the local SearXNG boundary, not a search index.  This helper
# keeps that boundary reproducible by generating the tiny settings.yml fragment
# that the Docker service needs: JSON output enabled, public-instance behavior
# disabled, and fragile Google engines explicitly off by default.  The secret is
# stored separately so re-rendering settings does not rotate cookies or break a
# running local instance unnecessarily.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path
from typing import Any

JsonObject = dict[str, Any]

DEFAULT_DISABLED_ENGINES = [
    "google",
    "google images",
    "google news",
    "google videos",
    "google scholar",
]


def _expand_path(path_text: str) -> Path:
    """Expand `~` and environment variables in a path string.

    Args:
        path_text: Path from the resolved setup plan.

    Returns:
        Expanded filesystem path.
    """
    return Path(os.path.expandvars(os.path.expanduser(path_text)))


def _load_plan(plan_path: Path) -> JsonObject:
    """Load a rendered MCP setup plan from disk.

    Args:
        plan_path: Path to the JSON setup plan.

    Returns:
        Decoded setup plan object.
    """
    with plan_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("setup plan must be a JSON object")
    return payload


def _service_settings(plan: JsonObject, service_id: str) -> JsonObject:
    """Return the settings block for a Docker service.

    Args:
        plan: Rendered setup plan.
        service_id: Service whose settings should be read.

    Returns:
        Service settings dictionary.

    Raises:
        KeyError: If the service is missing from the plan.
        TypeError: If the service settings are not a dictionary.
    """
    service = plan.get("services", {}).get(service_id)
    if not isinstance(service, dict):
        raise KeyError(f"service not found in setup plan: {service_id}")
    settings = service.get("settings", {})
    if not isinstance(settings, dict):
        raise TypeError(f"services.{service_id}.settings must be an object")
    return settings


def _read_or_create_secret(secret_file: Path) -> str:
    """Read the persistent SearXNG secret, creating it when absent.

    Args:
        secret_file: Path where the secret is stored.

    Returns:
        Secret text with surrounding whitespace removed.
    """
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    if secret_file.exists():
        secret = secret_file.read_text(encoding="utf-8").strip()
        if secret:
            return secret

    # 32 bytes gives a stable high-entropy local secret without user input.
    secret = secrets.token_urlsafe(32)
    secret_file.write_text(f"{secret}\n", encoding="utf-8")
    return secret


def _render_settings(secret: str, disabled_engines: list[str]) -> str:
    """Build SearXNG settings.yml content.

    Args:
        secret: Persistent local server secret.
        disabled_engines: SearXNG engine names that should be disabled.

    Returns:
        YAML text for `/etc/searxng/settings.yml`.
    """
    engine_blocks = "\n".join(
        f"  - name: {engine}\n    disabled: true" for engine in disabled_engines
    )
    return (
        "use_default_settings: true\n"
        "\n"
        "general:\n"
        "  debug: false\n"
        "  instance_name: Bureau Search\n"
        "\n"
        "search:\n"
        "  safe_search: 0\n"
        "  autocomplete: \"\"\n"
        "  default_lang: auto\n"
        "  formats:\n"
        "    - html\n"
        "    - json\n"
        "\n"
        "server:\n"
        f"  secret_key: {secret}\n"
        "  limiter: false\n"
        "  public_instance: false\n"
        "  image_proxy: false\n"
        "\n"
        "engines:\n"
        f"{engine_blocks}\n"
    )


def render_settings_from_plan(plan_path: str | Path, service_id: str) -> JsonObject:
    """Render managed SearXNG settings from a setup plan.

    Args:
        plan_path: Path to the rendered setup plan JSON.
        service_id: Docker service id, usually `searxng`.

    Returns:
        Small status object with the written settings path.
    """
    plan = _load_plan(Path(plan_path))
    settings = _service_settings(plan, service_id)
    settings_file = _expand_path(str(settings["settings_file"]))
    secret_file = _expand_path(str(settings["secret_file"]))
    disabled_engines = [
        str(engine) for engine in settings.get("disabled_engines", DEFAULT_DISABLED_ENGINES)
    ]

    secret = _read_or_create_secret(secret_file)
    rendered = _render_settings(secret, disabled_engines)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    if not settings_file.exists() or settings_file.read_text(encoding="utf-8") != rendered:
        settings_file.write_text(rendered, encoding="utf-8")

    return {"settings_file": str(settings_file), "secret_file": str(secret_file)}


def main() -> int:
    """CLI entry point for setup script integration."""
    parser = argparse.ArgumentParser(description="Render managed SearXNG settings.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--service", default="searxng")
    args = parser.parse_args()

    result = render_settings_from_plan(args.plan, args.service)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
