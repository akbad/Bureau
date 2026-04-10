import pytest

from operations.validate_config import (
    validate_config,
    validate_placeholder_cycles,
    validate_service_dependency_cycles,
    validate_dependency_requires_cycles,
    validate_protocol_settings,
    _collect_placeholder_refs,
    _collect_service_dep_graph,
    _collect_dependency_requires_graph,
    _find_graph_cycles,
)


class TestPlaceholderCycleDetection:
    """Tests for circular placeholder reference detection."""

    def test_no_cycles_returns_empty(self):
        config = {"a": "${b}", "b": "leaf"}
        assert validate_placeholder_cycles(config) == []

    def test_no_placeholders_returns_empty(self):
        config = {"a": "plain", "b": "values"}
        assert validate_placeholder_cycles(config) == []

    def test_detects_self_reference(self):
        config = {"a": "${a}x"}
        errors = validate_placeholder_cycles(config)
        assert len(errors) == 1
        assert "a → a" in errors[0]

    def test_detects_mutual_cycle(self):
        config = {"a": "${b}x", "b": "${a}"}
        errors = validate_placeholder_cycles(config)
        assert len(errors) == 1
        assert "a → b → a" in errors[0] or "b → a → b" in errors[0]

    def test_detects_longer_cycle(self):
        config = {"x": "${y}", "y": "${z}", "z": "${x}foo"}
        errors = validate_placeholder_cycles(config)
        assert len(errors) == 1
        assert "x" in errors[0] and "y" in errors[0] and "z" in errors[0]

    def test_nested_config_paths(self):
        config = {"mcp": {"a": "${mcp.b}", "b": "${mcp.a}x"}}
        errors = validate_placeholder_cycles(config)
        assert len(errors) == 1
        assert "mcp.a" in errors[0] and "mcp.b" in errors[0]

    def test_list_values_tracked(self):
        config = {"items": ["${items[1]}", "${items[0]}"]}
        errors = validate_placeholder_cycles(config)
        assert len(errors) == 1


class TestCollectPlaceholderRefs:
    """Tests for the graph building helper."""

    def test_collects_simple_refs(self):
        graph = {}
        _collect_placeholder_refs({"a": "${b}"}, "", graph)
        assert graph == {"a": {"b"}}

    def test_collects_multiple_refs(self):
        graph = {}
        _collect_placeholder_refs({"a": "${b}/${c}"}, "", graph)
        assert graph == {"a": {"b", "c"}}

    def test_nested_paths(self):
        graph = {}
        _collect_placeholder_refs({"x": {"y": "${z}"}}, "", graph)
        assert graph == {"x.y": {"z"}}


class TestFindGraphCycles:
    """Tests for the cycle detection helper."""

    def test_no_cycles(self):
        graph = {"a": {"b"}, "b": {"c"}}
        assert _find_graph_cycles(graph) == []

    def test_self_loop(self):
        graph = {"a": {"a"}}
        cycles = _find_graph_cycles(graph)
        assert len(cycles) == 1
        assert "a → a" in cycles[0]

    def test_two_node_cycle(self):
        graph = {"a": {"b"}, "b": {"a"}}
        cycles = _find_graph_cycles(graph)
        assert len(cycles) == 1


class TestServiceDependencyCycleDetection:
    """Tests for circular service dependency detection."""

    def test_no_cycles_returns_empty(self):
        config = {"mcp": {"services": {
            "a": {"depends_on": {"services": ["b"]}},
            "b": {},
        }}}
        assert validate_service_dependency_cycles(config) == []

    def test_no_deps_returns_empty(self):
        config = {"mcp": {"services": {"a": {}, "b": {}}}}
        assert validate_service_dependency_cycles(config) == []

    def test_detects_self_reference(self):
        config = {"mcp": {"services": {
            "a": {"depends_on": {"services": ["a"]}},
        }}}
        errors = validate_service_dependency_cycles(config)
        assert len(errors) == 1
        assert "a → a" in errors[0]

    def test_detects_mutual_cycle(self):
        config = {"mcp": {"services": {
            "a": {"depends_on": {"services": ["b"]}},
            "b": {"depends_on": {"services": ["a"]}},
        }}}
        errors = validate_service_dependency_cycles(config)
        assert len(errors) == 1

    def test_detects_longer_cycle(self):
        config = {"mcp": {"services": {
            "x": {"depends_on": {"services": ["y"]}},
            "y": {"depends_on": {"services": ["z"]}},
            "z": {"depends_on": {"services": ["x"]}},
        }}}
        errors = validate_service_dependency_cycles(config)
        assert len(errors) == 1
        assert "x" in errors[0] and "y" in errors[0] and "z" in errors[0]

    def test_missing_services_returns_empty(self):
        config = {"mcp": {}}
        assert validate_service_dependency_cycles(config) == []


class TestCollectServiceDepGraph:
    """Tests for the service dependency graph builder."""

    def test_collects_service_deps(self):
        config = {"mcp": {"services": {
            "api": {"depends_on": {"services": ["db"]}},
            "db": {},
        }}}
        graph = _collect_service_dep_graph(config)
        assert graph == {"api": {"db"}}

    def test_skips_non_dict_entries(self):
        config = {"mcp": {"services": {"bad": "not_a_dict"}}}
        assert _collect_service_dep_graph(config) == {}

    def test_handles_scalar_services_dep(self):
        config = {"mcp": {"services": {
            "api": {"depends_on": {"services": "db"}},
        }}}
        graph = _collect_service_dep_graph(config)
        assert graph == {"api": {"db"}}


class TestDependencyRequiresCycleDetection:
    """W11: detect cycles in dependency requires."""

    def test_self_reference_produces_error(self):
        config = {"mcp": {"dependencies": {
            "a": {"kind": "file", "path": "/x", "requires": ["a"]},
        }}}
        errors = validate_dependency_requires_cycles(config)
        assert len(errors) == 1

    def test_mutual_cycle_produces_error(self):
        config = {"mcp": {"dependencies": {
            "a": {"kind": "file", "path": "/x", "requires": ["b"]},
            "b": {"kind": "file", "path": "/y", "requires": ["a"]},
        }}}
        errors = validate_dependency_requires_cycles(config)
        assert len(errors) >= 1

    def test_no_cycle_is_fine(self):
        config = {"mcp": {"dependencies": {
            "base": {"kind": "file", "path": "/x"},
            "overlay": {"kind": "file", "path": "/y", "requires": ["base"]},
        }}}
        errors = validate_dependency_requires_cycles(config)
        assert errors == []

    def test_missing_dependencies_returns_empty(self):
        config = {"mcp": {}}
        assert validate_dependency_requires_cycles(config) == []


class TestCollectDependencyRequiresGraph:
    """Tests for the dependency requires graph builder."""

    def test_collects_requires(self):
        config = {"mcp": {"dependencies": {
            "overlay": {"kind": "file", "path": "/x", "requires": ["base"]},
            "base": {"kind": "file", "path": "/y"},
        }}}
        graph = _collect_dependency_requires_graph(config)
        assert graph == {"overlay": {"base"}, "base": set()}

    def test_skips_non_dict_entries(self):
        config = {"mcp": {"dependencies": {"bad": "not_a_dict"}}}
        assert _collect_dependency_requires_graph(config) == {}

    def test_non_list_requires_produces_empty_set(self):
        config = {"mcp": {"dependencies": {
            "a": {"kind": "file", "path": "/x", "requires": "bad"},
        }}}
        graph = _collect_dependency_requires_graph(config)
        assert graph == {"a": set()}


class TestProtocolSettingsValidation:
    """Tests for the consolidated protocols schema."""

    def test_accepts_default_protocol_settings(self):
        config = {
            "protocols": {
                "mode": "replace",
                "output_style": "default",
                "code_standards": "default",
            }
        }

        assert validate_protocol_settings(config) == []

    def test_accepts_off_and_custom_path_lists(self):
        config = {
            "protocols": {
                "mode": "sync",
                "output_style": ["~/styles/base.md", "/tmp/style extension.md"],
                "code_standards": "off",
            }
        }

        assert validate_protocol_settings(config) == []

    def test_accepts_boolean_false_for_off_like_yaml_scalars(self):
        config = {
            "protocols": {
                "mode": "replace",
                "output_style": False,
                "code_standards": False,
            }
        }

        assert validate_protocol_settings(config) == []

    def test_rejects_unknown_protocol_mode(self):
        config = {
            "protocols": {
                "mode": "first-run-only",
                "output_style": "default",
                "code_standards": "default",
            }
        }

        errors = validate_protocol_settings(config)

        assert any("protocols.mode" in error for error in errors)

    def test_rejects_empty_custom_protocol_document_list(self):
        config = {
            "protocols": {
                "mode": "replace",
                "output_style": [],
                "code_standards": "default",
            }
        }

        errors = validate_protocol_settings(config)

        assert any("protocols.output_style" in error for error in errors)

    def test_rejects_legacy_protocol_keys(self):
        config = {
            "protocols": {
                "update": True,
                "force": False,
                "bare": False,
            }
        }

        errors = validate_protocol_settings(config)

        assert any("protocols.update" in error for error in errors)
        assert any("protocols.force" in error for error in errors)
        assert any("protocols.bare" in error for error in errors)

    def test_warns_when_code_standards_is_listed_in_skills_enabled(self):
        config = {
            "agents": ["codex"],
            "retention_period_for": {
                "claude_mem": "30d",
                "serena": "30d",
                "qdrant": "30d",
                "memory_mcp": "30d",
            },
            "cleanup": {"min_interval": "1d"},
            "trash": {"grace_period": "7d"},
            "path_to": {"workspace": "~/code"},
            "startup_timeout_for": {"mcp_servers": 30, "docker_daemon": 30},
            "mcp": {"services": {}, "client_configs": {}},
            "skills": {
                "enabled": ["micro-mode", "code-standards"],
                "disabled": [],
                "sources": [],
            },
            "protocols": {"code_standards": "default"},
        }

        result = validate_config(config, add_warnings=True)

        assert result.errors == []
        assert any("skills.enabled" in warning for warning in result.warnings)
        assert any("protocols.code_standards" in warning for warning in result.warnings)

    def test_warns_when_code_standards_is_listed_in_skills_disabled(self):
        config = {
            "agents": ["codex"],
            "retention_period_for": {
                "claude_mem": "30d",
                "serena": "30d",
                "qdrant": "30d",
                "memory_mcp": "30d",
            },
            "cleanup": {"min_interval": "1d"},
            "trash": {"grace_period": "7d"},
            "path_to": {"workspace": "~/code"},
            "startup_timeout_for": {"mcp_servers": 30, "docker_daemon": 30},
            "mcp": {"services": {}, "client_configs": {}},
            "skills": {
                "enabled": ["micro-mode"],
                "disabled": ["code-standards"],
                "sources": [],
            },
            "protocols": {"code_standards": "default"},
        }

        result = validate_config(config, add_warnings=True)

        assert result.errors == []
        assert any("skills.disabled" in warning for warning in result.warnings)
        assert any("protocols.code_standards" in warning for warning in result.warnings)
