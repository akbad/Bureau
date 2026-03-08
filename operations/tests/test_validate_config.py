import pytest

from operations.validate_config import (
    validate_placeholder_cycles,
    validate_service_dependency_cycles,
    validate_dependency_requires_cycles,
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
