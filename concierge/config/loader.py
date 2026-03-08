"""Config loader for concierge YAML configuration.

Loads default configs from concierge/config/defaults/*.yml,
optionally merges user overrides, and provides cached accessors.
"""

# Design rationale:
# Separates default configs (shipped with the package) from user overrides so
# the package always has sane defaults even without user configuration.  Deep
# merge (_deep_merge) is used instead of dict.update so users can override a
# single nested key without clobbering sibling keys.  The lru_cache on
# get_classifier_config / get_priorities_config / get_pipeline_config provides
# fast, zero-arg access to default-only config for hot paths (classifier,
# pipeline) that never need user overrides at runtime; load_config(user_dir)
# remains uncached for the setup/wizard flow where overrides matter.

from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DEFAULTS_DIR = Path(__file__).parent / "defaults"
_CONFIG_NAMES = ("classifier", "priorities", "pipeline")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into a copy of *base*.

    For nested dicts the merge is recursive; for all other types the
    override value wins outright.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _load_defaults() -> dict[str, Any]:
    """Load all default YAML files from ``concierge/config/defaults/``."""
    config: dict[str, Any] = {}
    for name in _CONFIG_NAMES:
        path = _DEFAULTS_DIR / f"{name}.yml"
        if path.exists():
            with open(path) as fh:
                data = yaml.safe_load(fh)
            if data:
                config[name] = data
    return config


def _load_user_overrides(user_config_dir: Path | str) -> dict[str, Any]:
    """Load matching YAML files from a user-supplied directory.

    Only files whose stem matches one of the known config names
    (classifier, priorities, pipeline) are loaded.
    """
    user_dir = Path(user_config_dir)
    overrides: dict[str, Any] = {}
    for name in _CONFIG_NAMES:
        path = user_dir / f"{name}.yml"
        if path.exists():
            with open(path) as fh:
                data = yaml.safe_load(fh)
            if data:
                overrides[name] = data
    return overrides


def load_config(user_config_dir: Path | str | None = None) -> dict[str, Any]:
    """Return the full merged config (defaults + optional user overrides)."""
    config = _load_defaults()
    if user_config_dir is not None:
        overrides = _load_user_overrides(user_config_dir)
        for name, override_data in overrides.items():
            if name in config:
                config[name] = _deep_merge(config[name], override_data)
            else:
                config[name] = copy.deepcopy(override_data)
    return config


@lru_cache(maxsize=1)
def get_classifier_config() -> dict[str, Any]:
    """Return the classifier section of the default config (cached)."""
    return load_config()["classifier"]


@lru_cache(maxsize=1)
def get_priorities_config() -> dict[str, Any]:
    """Return the priorities section of the default config (cached)."""
    return load_config()["priorities"]


@lru_cache(maxsize=1)
def get_pipeline_config() -> dict[str, Any]:
    """Return the pipeline section of the default config (cached)."""
    return load_config()["pipeline"]
