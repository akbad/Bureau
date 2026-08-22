"""Tests for resolve_agent_access_paths() — the agent_access.paths resolver.

Drives the resolver with explicit config dicts (its `config` parameter), so these
tests never touch get_config()/defaults.yml. Path assertions are computed through
the same Path(...).expanduser().resolve() pipeline the resolver uses, so they hold
regardless of symlink canonicalization (e.g. /tmp → /private/tmp on macOS).
"""

from pathlib import Path

import pytest

from operations.agent_access import AgentAccessPath, resolve_agent_access_paths


def _resolved(path_str: str) -> str:
    """Expected absolute form of a path, matching the resolver's own pipeline."""
    return str(Path(path_str).expanduser().resolve())


def test_empty_or_absent_agent_access_returns_empty():
    assert resolve_agent_access_paths({}) == []
    assert resolve_agent_access_paths({"agent_access": {"paths": {}}}) == []


def test_disabled_entries_are_filtered_by_default():
    config = {"agent_access": {"paths": {
        "on": {"enabled": True, "path": "/tmp/on"},
        "off": {"enabled": False, "path": "/tmp/off"},
    }}}

    result = resolve_agent_access_paths(config)

    assert [e.name for e in result] == ["on"]


def test_include_disabled_returns_all_entries_with_flags():
    config = {"agent_access": {"paths": {
        "on": {"enabled": True, "path": "/tmp/on"},
        "off": {"enabled": False, "path": "/tmp/off"},
    }}}

    result = resolve_agent_access_paths(config, include_disabled=True)

    assert [(e.name, e.enabled) for e in result] == [("on", True), ("off", False)]


def test_workspace_placeholder_is_expanded(tmp_path):
    config = {
        "workspace": str(tmp_path),
        "agent_access": {"paths": {"ws": {"enabled": True, "path": "${workspace}/proj"}}},
    }

    result = resolve_agent_access_paths(config)

    assert result == [AgentAccessPath(name="ws", path=_resolved(f"{tmp_path}/proj"), enabled=True)]


def test_tilde_is_expanded_to_absolute_home_path():
    config = {"agent_access": {"paths": {"home": {"enabled": True, "path": "~/bureau-test-dir"}}}}

    result = resolve_agent_access_paths(config)

    assert result[0].path == _resolved("~/bureau-test-dir")
    assert Path(result[0].path).is_absolute()


def test_order_follows_insertion_order():
    config = {"agent_access": {"paths": {
        "first": {"enabled": True, "path": "/tmp/1"},
        "second": {"enabled": True, "path": "/tmp/2"},
        "third": {"enabled": True, "path": "/tmp/3"},
    }}}

    assert [e.name for e in resolve_agent_access_paths(config)] == ["first", "second", "third"]


def test_idempotent_across_repeated_calls():
    config = {"agent_access": {"paths": {"a": {"enabled": True, "path": "/tmp/a"}}}}

    assert resolve_agent_access_paths(config) == resolve_agent_access_paths(config)


def test_enabled_entry_missing_path_raises_valueerror():
    config = {"agent_access": {"paths": {"bad": {"enabled": True}}}}

    with pytest.raises(ValueError, match="missing the required 'path'"):
        resolve_agent_access_paths(config)


def test_non_mapping_entry_raises_valueerror():
    config = {"agent_access": {"paths": {"bad": "not-a-dict"}}}

    with pytest.raises(ValueError, match="must be a mapping"):
        resolve_agent_access_paths(config)
