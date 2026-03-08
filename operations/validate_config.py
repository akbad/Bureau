"""Config validator for Bureau cleanup module.

Validates that all required configuration fields are present before
cleanup operations run. This prevents silent failures due to missing keys
or unsupported values.
"""
import sys
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, overload

from .config_templating import _PLACEHOLDER_REGEX


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


@dataclass
class ValidationResult:
    """Validation output with errors (hard failures), warnings (soft), and info (advisory)."""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)


# Required schema for cleanup operations
REQUIRED_SCHEMA: dict[str, Any] = {
    "agents": list,            # At least one agent enabled
    "retention_period_for": {
        "claude_mem": str,     # Duration string (e.g., "30d")
        "serena": str,
        "qdrant": str,
        "memory_mcp": str,
    },
    "cleanup": {
        "min_interval": str,   # Duration string
    },
    "trash": {
        "grace_period": str,   # Duration string
    },
    "path_to": {
        "workspace": str,      # Base workspace path string
    },
    "startup_timeout_for": {
        "mcp_servers": int,    # Seconds to wait for MCP servers
        "docker_daemon": int,  # Seconds to wait for Docker daemon
    },
    "mcp": {
        "services": {},
        "client_configs": {},
    },
}


def _validate_node(config: Mapping[str, Any], schema: dict, path: str = "") -> list[str]:
    """Recursively validate config against schema.

    Args:
        config: Configuration dict to validate.
        schema: Schema dict defining required structure.
        path: Current path for error messages.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    for key, expected_type in schema.items():
        current_path = f"{path}.{key}" if path else key

        if key not in config:
            errors.append(f"Missing required key: {current_path}")
            continue

        value = config[key]

        if isinstance(expected_type, dict):
            # Nested structure - recurse
            if not isinstance(value, dict):
                errors.append(
                    f"Expected dict for '{current_path}', got {type(value).__name__}"
                )
            else:
                errors.extend(_validate_node(value, expected_type, current_path))
        elif expected_type is list:
            # Check it's a list
            if not isinstance(value, list):
                errors.append(
                    f"Expected list for '{current_path}', got {type(value).__name__}"
                )
            elif len(value) == 0:
                errors.append(f"'{current_path}' cannot be empty")
        elif expected_type is str:
            # Check it's a string (or can be stringified)
            if value is None:
                errors.append(f"'{current_path}' cannot be None")
            elif not isinstance(value, (str, int, float)):
                errors.append(
                    f"Expected string-like for '{current_path}', got {type(value).__name__}"
                )
        elif expected_type is int:
            if not isinstance(value, int):
                errors.append(
                    f"Expected int for '{current_path}', got {type(value).__name__}"
                )

    return errors


def validate_config_schema(config: Mapping[str, Any]) -> list[str]:
    """Validate config dict against required schema.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        List of error messages (empty list = valid).
    """
    if not isinstance(config, dict):
        return ["Configuration must be a dictionary"]

    return _validate_node(config, REQUIRED_SCHEMA)


def validate_legacy_mcp_keys(config: Mapping[str, Any]) -> list[str]:
    """Reject legacy MCP keys removed by schema migrations."""
    mcp = config.get("mcp", {})
    if not isinstance(mcp, dict):
        return []

    if "runtime_services" in mcp:
        return [
            "Unsupported key: 'mcp.runtime_services'."
        ]
    return []


def validate_and_raise(config: Mapping[str, Any]) -> None:
    """Validate config and raise ConfigurationError if invalid.

    Args:
        config: Configuration dictionary to validate.

    Raises:
        ConfigurationError: If configuration is invalid.
    """
    errors = validate_config_schema(config)
    errors.extend(validate_legacy_mcp_keys(config))
    if errors:
        error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        raise ConfigurationError(error_msg)


def validate_duration_format(duration: str) -> str | None:
    """Validate a duration string format.

    Delegates to parse_duration() to ensure validation and parsing
    always agree on what constitutes a valid duration.

    Args:
        duration: Duration string to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    from .config_loader import parse_duration

    try:
        parse_duration(duration)
        return None
    except ValueError as e:
        return str(e)


def _check_durations(section: Mapping[str, Any], section_name: str, *keys: str) -> list[str]:
    """Check duration format for specified keys in a config section.

    Args:
        section: Config section dictionary.
        section_name: Name of section for error messages.
        *keys: Keys to check within the section.

    Returns:
        List of error messages for invalid durations.
    """
    errors = []
    for key in keys:
        if key in section:
            if err := validate_duration_format(str(section[key])):
                errors.append(f"{section_name}.{key}: {err}")
    return errors


def validate_durations(config: Mapping[str, Any]) -> list[str]:
    """Validate all duration strings in config have correct format.

    Args:
        config: Configuration dictionary.

    Returns:
        List of error messages for invalid durations.
    """
    errors = []

    errors.extend(_check_durations(
        config.get("retention_period_for", {}), "retention_period_for",
        "claude_mem", "serena", "qdrant", "memory_mcp"
    ))
    errors.extend(_check_durations(
        config.get("cleanup", {}), "cleanup",
        "min_interval"
    ))
    errors.extend(_check_durations(
        config.get("trash", {}), "trash",
        "grace_period"
    ))

    return errors


def _collect_placeholder_refs(
    node: Any, path: str, graph: dict[str, set[str]]
) -> None:
    """
    Recursively collect placeholder references (i.e. `${...}` segments in config strings 
    that are meant to be replaced by env var values) into a dependency graph.
    """
    if isinstance(node, str):
        if refs := set(_PLACEHOLDER_REGEX.findall(node)):
            graph[path] = refs
    elif isinstance(node, dict):
        for k, v in node.items():
            _collect_placeholder_refs(v, f"{path}.{k}" if path else k, graph)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _collect_placeholder_refs(v, f"{path}[{i}]", graph)


def _find_graph_cycles(graph: dict[str, set[str]]) -> list[str]:
    """
    Detects cycles via DFS in the placeholder dependency graph, returns formatted cycle paths.
    
    Used as part of placeholder validation to ensure no cycles exist that would cause
    infinite placeholder expansion (e.g. val="...${val}...")
    """
    visited, in_stack, stack, cycles = set(), set(), [], []

    def dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        stack.append(node)

        for neighbor in graph.get(node, ()):
            if neighbor in in_stack:
                cycles.append(" → ".join(stack[stack.index(neighbor) :] + [neighbor]))
            elif neighbor not in visited:
                dfs(neighbor)

        stack.pop()
        in_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def validate_placeholder_cycles(config: Mapping[str, Any]) -> list[str]:
    """
    Validate that placeholder references in the YML configs' setting strings don't form cycles, which
    would cause infinite expansion

    Cycles cause infinite expansion (e.g., val="...${val}..." would cause `val` to keep getting expanded
    forever).
    """
    graph: dict[str, set[str]] = {}
    _collect_placeholder_refs(config, "", graph)
    return [f"Circular placeholder reference: {c}" for c in _find_graph_cycles(graph)]


def _collect_service_dep_graph(config: Mapping[str, Any]) -> dict[str, set[str]]:
    """Build adjacency list from mcp.services.*.depends_on.services."""
    graph: dict[str, set[str]] = {}
    services = config.get("mcp", {}).get("services", {})
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        depends_on = svc.get("depends_on", {})
        if not isinstance(depends_on, dict):
            continue
        deps = _as_list(depends_on.get("services"))
        if deps:
            graph[name] = set(deps)
    return graph


def validate_service_dependency_cycles(config: Mapping[str, Any]) -> list[str]:
    """Validate that service dependencies don't form cycles."""
    graph = _collect_service_dep_graph(config)
    return [
        f"Circular service dependency: {c}"
        for c in _find_graph_cycles(graph)
    ]


def _as_list(value: Any) -> list:
    """Normalize a value to a list (for depends_on entries that might be bare strings)."""
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


_OUTER_TYPES: dict[str, type] = {
    "bool": bool,
    "int": int,
    "dict": dict,
    "dict[str,str]": dict,
    "list[str]": list,
    "list[dict]": list,
    "list[list[str]]": list,
}


def _check_type(value: Any, type_tag: str) -> str | None:
    """Check a value against a type tag string. Returns error message or None.

    Type tags: "int", "dict", "dict[str,str]", "list[str]", "list[dict]", "list[list[str]]"
    """
    expected = _OUTER_TYPES.get(type_tag)
    if expected is None:
        return None

    # bool is a subclass of int in Python, so True/False would pass without this guard
    if expected is int and isinstance(value, bool):
        return "expected int, got bool"
    if not isinstance(value, expected):
        return f"expected {type_tag}, got {type(value).__name__}"

    # Inner element validation for compound types
    if type_tag == "dict[str,str]":
        for k, v in value.items():
            if not isinstance(v, str):
                return f"expected dict[str, str], but value for key '{k}' is {type(v).__name__}"
    elif type_tag == "list[str]":
        for i, item in enumerate(value):
            if not isinstance(item, str):
                return f"expected list[str], but element [{i}] is {type(item).__name__}"
    elif type_tag == "list[dict]":
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                return f"expected list[dict], but element [{i}] is {type(item).__name__}"
    elif type_tag == "list[list[str]]":
        for i, item in enumerate(value):
            if not isinstance(item, list):
                return f"expected list[list[str]], but element [{i}] is {type(item).__name__}"
            for j, sub in enumerate(item):
                if not isinstance(sub, str):
                    return (
                        f"expected list[list[str]], but element [{i}][{j}] "
                        f"is {type(sub).__name__}"
                    )
    return None


def _validate_field_types(
    entry: dict[str, Any],
    path: str,
    type_rules: list[tuple[str, str]],
) -> ValidationResult:
    """Validate field value types against declarative rules from mcp_validation_rules.py.

    Skips values that contain ${...} placeholders since their final type
    depends on expansion (e.g. healthcheck.tcp: ${...} is a string at parse
    time but resolves to an int).
    """
    result = ValidationResult()
    for field_name, type_tag in type_rules:
        if field_name not in entry:
            continue
        value = entry[field_name]
        # skip placeholder-bearing strings; type resolves after expansion
        if isinstance(value, str) and _PLACEHOLDER_REGEX.search(value):
            continue
        if error := _check_type(value, type_tag):
            result.errors.append(f"{path}.{field_name}: {error}")
    return result


def _validate_mounts(
    entry: dict[str, Any], path: str, result: ValidationResult,
) -> None:
    """Validate mounts sub-structure if present and already type-checked as list[dict]."""
    from .mcp_validation_rules import MOUNT_REQUIRED_KEYS

    mounts = entry.get("mounts")
    if not isinstance(mounts, list):
        return
    for i, mount in enumerate(mounts):
        if not isinstance(mount, dict):
            return  # already caught by type rules
        mount_path = f"{path}.mounts[{i}]"
        for req in sorted(MOUNT_REQUIRED_KEYS):
            if req not in mount:
                result.errors.append(f"{mount_path}: missing required key '{req}'")
        for key in sorted(set(mount.keys()) - MOUNT_REQUIRED_KEYS):
            result.warnings.append(f"{mount_path}: unknown key '{key}'")
        # W10: validate path values are strings (skip placeholders)
        for key in ("host_path", "container_path"):
            if key not in mount:
                continue
            val = mount[key]
            if isinstance(val, str) and _PLACEHOLDER_REGEX.search(val):
                continue
            if not isinstance(val, str):
                result.errors.append(
                    f"{mount_path}.{key}: expected string, got {type(val).__name__}"
                )


def _validate_healthcheck(
    entry: dict[str, Any], path: str, result: ValidationResult,
) -> None:
    """Validate healthcheck sub-structure if present and already type-checked as dict."""
    from .mcp_validation_rules import HEALTHCHECK_ALLOWED_KEYS

    hc = entry.get("healthcheck")
    if not isinstance(hc, dict):
        return  # already caught by type rules
    hc_path = f"{path}.healthcheck"
    for key in sorted(set(hc.keys()) - HEALTHCHECK_ALLOWED_KEYS):
        result.warnings.append(f"{hc_path}: unknown key '{key}'")
    # validate tcp field type (int), skip if placeholder
    tcp = hc.get("tcp")
    if tcp is not None:
        if isinstance(tcp, str) and _PLACEHOLDER_REGEX.search(tcp):
            pass  # placeholder; type resolves after expansion
        elif isinstance(tcp, bool) or not isinstance(tcp, int):
            result.errors.append(
                f"{hc_path}.tcp: expected int, got {type(tcp).__name__}"
            )


def _validate_entry_schema(
    name: str,
    entry: Any,
    path_prefix: str,
    allowed_keys: set[str],
    kind_enum: set[str] | None = None,
    required_by_kind: dict[str, set[str]] | None = None,
) -> ValidationResult:
    """Validate a single MCP entry against declarative rules from mcp_validation_rules.py.

    This is a generic engine: bucket-specific validators (e.g. _validate_mcp_dependencies, 
    _validate_mcp_services, _validate_mcp_client_configs) call this with their 
    constants one-by-one to validate the config entries in their scope.
    """
    from .mcp_validation_rules import DEPENDS_ON_ALLOWED_KEYS

    result = ValidationResult()
    prefix = f"{path_prefix}.{name}"

    if not isinstance(entry, dict):
        result.errors.append(f"{prefix}: expected dict, got {type(entry).__name__}")
        return result

    # unknown keys → warnings (not errors, to allow extension keys)
    for key in sorted(set(entry.keys()) - allowed_keys):
        result.warnings.append(f"{prefix}: unknown key '{key}'")

    # kind required → error (when kind_enum is provided, the bucket requires kind)
    if kind_enum is not None and "kind" not in entry:
        result.errors.append(f"{prefix}: missing required field 'kind'")
        return result  # no point checking kind-dependent rules without kind

    # kind enum validation → errors
    if kind_enum is not None and "kind" in entry:
        kind = entry["kind"]
        if kind not in kind_enum:
            result.errors.append(
                f"{prefix}.kind: '{kind}' not in {sorted(kind_enum)}"
            )

    # required fields per kind → errors
    if required_by_kind is not None and "kind" in entry:
        kind = entry["kind"]
        for req in sorted(required_by_kind.get(kind, set())):
            if req not in entry:
                result.errors.append(
                    f"{prefix}: missing required field '{req}' for kind '{kind}'"
                )

    # depends_on sub-key validation → warnings
    depends_on = entry.get("depends_on")
    if isinstance(depends_on, dict):
        for key in sorted(set(depends_on.keys()) - DEPENDS_ON_ALLOWED_KEYS):
            result.warnings.append(f"{prefix}.depends_on: unknown key '{key}'")

    return result


def _validate_mcp_dependencies(config: Mapping[str, Any]) -> ValidationResult:
    """Validate mcp.dependencies entries: kind enums, required fields, unknown keys, field types."""
    from .mcp_validation_rules import (
        DEPENDENCY_ALLOWED_KEYS, DEPENDENCY_KINDS, DEPENDENCY_REQUIRED,
        DEPENDENCY_TYPE_RULES,
    )

    result = ValidationResult()
    deps = config.get("mcp", {}).get("dependencies", {})
    for name, entry in deps.items():
        r = _validate_entry_schema(
            name, entry, "mcp.dependencies",
            DEPENDENCY_ALLOWED_KEYS, DEPENDENCY_KINDS, DEPENDENCY_REQUIRED,
        )
        result.errors.extend(r.errors)
        result.warnings.extend(r.warnings)
        # field type validation (only if entry is a dict — non-dict already caught above)
        if isinstance(entry, dict):
            t = _validate_field_types(entry, f"mcp.dependencies.{name}", DEPENDENCY_TYPE_RULES)
            result.errors.extend(t.errors)
    return result


def _validate_mcp_services(config: Mapping[str, Any]) -> ValidationResult:
    """Validate mcp.services entries: kind enums, required fields, unknown keys, field types."""
    from .mcp_validation_rules import (
        SERVICE_ALLOWED_KEYS, SERVICE_KINDS,
        SERVICE_REQUIRED, SERVICE_TYPE_RULES,
    )

    result = ValidationResult()
    services = config.get("mcp", {}).get("services", {})
    for name, entry in services.items():
        r = _validate_entry_schema(
            name, entry, "mcp.services",
            SERVICE_ALLOWED_KEYS, SERVICE_KINDS, SERVICE_REQUIRED,
        )
        result.errors.extend(r.errors)
        result.warnings.extend(r.warnings)
        # field type validation + sub-structure checks
        if isinstance(entry, dict):
            prefix = f"mcp.services.{name}"
            t = _validate_field_types(entry, prefix, SERVICE_TYPE_RULES)
            result.errors.extend(t.errors)
            _validate_mounts(entry, prefix, result)
            _validate_healthcheck(entry, prefix, result)
    return result


def _validate_mcp_client_configs(config: Mapping[str, Any]) -> ValidationResult:
    """Validate mcp.client_configs entries: top-level keys, client entries, transport requirements.

    Client configs have two nesting levels — the top-level entry (enabled, clients, settings, ...)
    and individual client entries inside clients.* (transport, url, command, ...).  Both are checked.
    """
    from .mcp_validation_rules import (
        CLIENT_CONFIG_ALLOWED_KEYS, CLIENT_CONFIG_TYPE_RULES,
        CLIENT_ENTRY_ALLOWED_KEYS, CLIENT_ENTRY_TYPE_RULES,
        CLIENT_TRANSPORT_KINDS, CLIENT_TRANSPORT_REQUIRED,
        CLIENTS_RESERVED_KEYS,
    )

    result = ValidationResult()
    configs = config.get("mcp", {}).get("client_configs", {})
    for name, entry in configs.items():
        # validate top-level entry keys (no kind_enum — client_configs don't have kind)
        r = _validate_entry_schema(name, entry, "mcp.client_configs", CLIENT_CONFIG_ALLOWED_KEYS)
        result.errors.extend(r.errors)
        result.warnings.extend(r.warnings)

        if not isinstance(entry, dict):
            continue

        # top-level field type validation
        t = _validate_field_types(
            entry, f"mcp.client_configs.{name}", CLIENT_CONFIG_TYPE_RULES,
        )
        result.errors.extend(t.errors)

        clients = entry.get("clients", {})
        if not isinstance(clients, dict):
            result.errors.append(
                f"mcp.client_configs.{name}.clients: expected dict, "
                f"got {type(clients).__name__}"
            )
            continue

        # validate disabled_for if present
        disabled_for = clients.get("disabled_for")
        if disabled_for is not None:
            df_path = f"mcp.client_configs.{name}.clients.disabled_for"
            if not isinstance(disabled_for, list):
                result.errors.append(
                    f"{df_path}: expected list, got {type(disabled_for).__name__}"
                )
            else:
                top_agents = set(config.get("agents", []))
                for i, val in enumerate(disabled_for):
                    if not isinstance(val, str):
                        result.errors.append(
                            f"{df_path}[{i}]: expected string, "
                            f"got {type(val).__name__}"
                        )
                    elif val not in top_agents:
                        result.warnings.append(
                            f"{df_path}: '{val}' is not in the "
                            f"top-level agents list"
                        )

        actual_clients = {
            k: v for k, v in clients.items() if k not in CLIENTS_RESERVED_KEYS
        }
        if not actual_clients:
            result.errors.append(
                f"mcp.client_configs.{name}.clients: must have at least one client"
            )

        # W8: info when clients.default is absent
        if actual_clients and "default" not in clients:
            result.info.append(
                f"mcp.client_configs.{name} has no clients.default — "
                f"agents without a specific override will skip this server"
            )

        for client_name, client_cfg in clients.items():
            if client_name in CLIENTS_RESERVED_KEYS:
                continue
            client_path = f"mcp.client_configs.{name}.clients.{client_name}"
            if not isinstance(client_cfg, dict):
                result.errors.append(
                    f"{client_path}: expected dict, got {type(client_cfg).__name__}"
                )
                continue

            # unknown client entry keys → warnings
            for key in sorted(set(client_cfg.keys()) - CLIENT_ENTRY_ALLOWED_KEYS):
                result.warnings.append(f"{client_path}: unknown key '{key}'")

            # client entry field type validation
            ct = _validate_field_types(client_cfg, client_path, CLIENT_ENTRY_TYPE_RULES)
            result.errors.extend(ct.errors)

            # transport required → error (W2)
            transport = client_cfg.get("transport")
            if transport is None:
                result.errors.append(
                    f"{client_path}: missing required field 'transport'"
                )
                continue  # skip transport-dependent checks

            # transport enum validation → errors
            if transport not in CLIENT_TRANSPORT_KINDS:
                result.errors.append(
                    f"{client_path}.transport: '{transport}' not in "
                    f"{sorted(CLIENT_TRANSPORT_KINDS)}"
                )

            # transport-required fields → errors
            if transport:
                for req in sorted(CLIENT_TRANSPORT_REQUIRED.get(transport, set())):
                    if req not in client_cfg:
                        result.errors.append(
                            f"{client_path}: missing required field '{req}' "
                            f"for transport '{transport}'"
                        )

    return result


def _validate_cross_references(config: Mapping[str, Any]) -> ValidationResult:
    """Validate that depends_on references point to declared entries.

    Checks both services and client_configs depends_on blocks.
    Mismatches produce warnings (not errors) because the reference might
    come from a conditionally-loaded config layer.
    """
    result = ValidationResult()
    mcp = config.get("mcp", {})
    declared_services = set(mcp.get("services", {}).keys())
    declared_deps = set(mcp.get("dependencies", {}).keys())

    # check references in services
    for name, svc in mcp.get("services", {}).items():
        if not isinstance(svc, dict):
            continue
        depends_on = svc.get("depends_on", {})
        if not isinstance(depends_on, dict):
            continue
        for ref in _as_list(depends_on.get("services")):
            if ref not in declared_services:
                result.warnings.append(
                    f"mcp.services.{name}.depends_on.services: "
                    f"'{ref}' does not match any declared service"
                )
        for ref in _as_list(depends_on.get("dependencies")):
            if ref not in declared_deps:
                result.warnings.append(
                    f"mcp.services.{name}.depends_on.dependencies: "
                    f"'{ref}' does not match any declared dependency"
                )

    # check references in client_configs
    for name, entry in mcp.get("client_configs", {}).items():
        if not isinstance(entry, dict):
            continue
        depends_on = entry.get("depends_on", {})
        if not isinstance(depends_on, dict):
            continue
        for ref in _as_list(depends_on.get("services")):
            if ref not in declared_services:
                result.warnings.append(
                    f"mcp.client_configs.{name}.depends_on.services: "
                    f"'{ref}' does not match any declared service"
                )
        for ref in _as_list(depends_on.get("dependencies")):
            if ref not in declared_deps:
                result.warnings.append(
                    f"mcp.client_configs.{name}.depends_on.dependencies: "
                    f"'{ref}' does not match any declared dependency"
                )

    return result


def validate_mcp_rules(config: Mapping[str, Any]) -> ValidationResult:
    """Validate MCP entry schemas: kinds, required fields, unknown keys, types, cross-references.

    Orchestrates the bucket-specific validators plus cross-reference checks
    and merges their results.
    """
    result = ValidationResult()
    for validator in (
        _validate_mcp_dependencies,
        _validate_mcp_services,
        _validate_mcp_client_configs,
        _validate_cross_references,
    ):
        r = validator(config)
        result.errors.extend(r.errors)
        result.warnings.extend(r.warnings)
        result.info.extend(r.info)
    return result


@overload
def validate_config(config: Mapping[str, Any], add_warnings: Literal[True]) -> ValidationResult: ...
@overload
def validate_config(config: Mapping[str, Any], add_warnings: Literal[False] = ...) -> list[str]: ...
def validate_config(config: Mapping[str, Any], add_warnings: bool = False) -> ValidationResult | list[str]:
    """Perform full validation including structure and format checks.

    Backward-compatible: returns errors only (warnings discarded).
    Use full_validate_with_warnings() to also get warnings.

    Args:
        config: Configuration dictionary.

    Returns:
        List of all error messages.
    """
    errors = validate_config_schema(config)
    errors.extend(validate_legacy_mcp_keys(config))

    # only run deeper checks if structure is valid
    if errors:
        return errors
    
    errors.extend(validate_durations(config))
    errors.extend(validate_placeholder_cycles(config))
    errors.extend(validate_service_dependency_cycles(config))

    # may contain both warnings *and* errors
    validation_result = validate_mcp_rules(config)
    errors.extend(validation_result.errors)

    return ValidationResult(errors=errors, warnings=validation_result.warnings, info=validation_result.info) if add_warnings else errors


def main() -> int:
    """CLI entry point for config validation.

    Returns:
        0 if valid, 1 if invalid.
    """
    from .config_loader import get_config

    try:
        config = get_config()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    result = validate_config(config, add_warnings=True)

    if result.info:
        for i in result.info:
            print(f"  \u2139 {i}", file=sys.stderr)

    if result.warnings:
        for w in result.warnings:
            print(f"  \u26a0 {w}", file=sys.stderr)

    if result.errors:
        print("Configuration validation failed:", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Configuration is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
