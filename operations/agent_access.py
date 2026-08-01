"""Resolution of agent_access.paths into concrete, absolute filesystem paths.

Design rationale
================
`agent_access.paths` is Bureau's explicit access-policy surface: a keyed map of
named entries, each ``{enabled, path}``, declaring which directories
Bureau-managed agent CLIs may touch. This module is the SINGLE SOURCE OF TRUTH
for projecting that policy into concrete paths.

Native-CLI adapters (Claude / Codex / Gemini / OpenCode) call
``resolve_agent_access_paths()`` rather than re-reading and re-expanding the
config themselves, so the expansion rules — ``${...}`` substitution, ``~``
expansion, enabled-filtering, and ordering — live in exactly one place and
cannot drift between adapters.

Invariants (do not violate)
---------------------------
- Entries are returned in ``defaults.yml`` insertion order (PyYAML preserves
  dict order on Python 3.7+), so adapter output is deterministic and re-runs
  produce no diff.
- A disabled entry is omitted unless ``include_disabled`` is set.
- Returned ``path`` values are absolute, with ``${...}`` placeholders and ``~``
  already expanded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config_loader import get_config
from .config_templating import expand_placeholders


@dataclass(frozen=True)
class AgentAccessPath:
    """A single RESOLVED agent-access entry.

    Distinct from ``config_loader.AgentAccessPathConfig`` (the raw on-disk
    ``{enabled, path}`` shape): this is the expanded, absolute form adapters act on.

    Attributes:
        name: The entry's key in ``agent_access.paths`` (e.g. ``"bureau_config"``).
            Retained so adapters can make per-name decisions (e.g. a future Codex
            read-only-only skip). The ``get-config --list access-paths`` accessor
            flattens this away for the subprocess-dispatched adapters, but the
            OpenCode render script consumes these objects directly and keeps it.
        path: Absolute filesystem path, with ``${...}`` placeholders and ``~``
            already expanded.
        enabled: Whether the entry is enabled. Always ``True`` for entries from a
            default (enabled-only) resolution; meaningful only when
            ``include_disabled=True`` also surfaces disabled entries.
    """

    name: str
    path: str
    enabled: bool


def resolve_agent_access_paths(
    config: Mapping[str, Any] | None = None,
    *,
    include_disabled: bool = False,
) -> list[AgentAccessPath]:
    """Resolve ``agent_access.paths`` into expanded, absolute entries.

    Args:
        config: Pre-merged config to read from. Defaults to ``get_config()``;
            pass an explicit mapping in tests, or when a caller already holds one.
        include_disabled: When ``True``, return disabled entries too (still flagged
            via the ``enabled`` field). Defaults to ``False`` (enabled-only).

    Returns:
        ``AgentAccessPath`` entries in ``defaults.yml`` insertion order. Each
        ``path`` is absolute with ``${...}`` (e.g. ``${workspace}``) and ``~``
        already expanded.

    Raises:
        ValueError: If an entry is not a mapping, or is missing its required
            ``path`` field. This is the load-time guard rail: ``validate_config()``
            does NOT run on normal ``get_config()`` loads (only
            ``validate_protocol_settings`` does), so a malformed entry would
            otherwise pass silently until an adapter dereferenced it. Fail loud here.
    """
    cfg = config if config is not None else get_config()
    raw = cfg.get("agent_access", {}).get("paths", {})

    resolved: list[AgentAccessPath] = []
    for name, entry in raw.items():
        # fail loud on a structurally-broken entry: the resolver is the only
        # load-time gate, so an opaque AttributeError downstream is worse than a
        # clear ValueError naming the offending key
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"agent_access.paths.{name} must be a mapping, got {type(entry).__name__}"
            )

        enabled = bool(entry.get("enabled", False))
        if not enabled and not include_disabled:
            continue

        if "path" not in entry:
            raise ValueError(
                f"agent_access.paths.{name} is missing the required 'path' field"
            )

        # expand ${workspace} (and any other ${...}) against the merged config,
        # then resolve ~ and any relative segments to an absolute path
        expanded = expand_placeholders(entry["path"], cfg)
        absolute = str(Path(expanded).expanduser().resolve())
        resolved.append(AgentAccessPath(name=name, path=absolute, enabled=enabled))

    return resolved
