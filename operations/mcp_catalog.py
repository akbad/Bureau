from __future__ import annotations

import os
from typing import Any, Mapping

from .config_templating import expand_placeholders
from .mcp_validation_rules import CLIENTS_RESERVED_KEYS
from .validate_config import _infer_requires


def _has_required_env(req: list[str], env: Mapping[str, str]) -> bool:
    return all(key in env and env[key] for key in req)


def _expand_strings(value: Any, config: Mapping[str, Any], env: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return expand_placeholders(value, config, env)
    if isinstance(value, list):
        return [_expand_strings(item, config, env) for item in value]
    if isinstance(value, dict):
        return {key: _expand_strings(item, config, env) for key, item in value.items()}
    return value


def _apply_allowed_methods(
    server_id: str, server_entry: dict[str, Any]
) -> None:
    if server_id != "filesystem":
        return

    settings = server_entry.get("settings", {})
    if not isinstance(settings, dict):
        return

    allowed_methods = settings.get("allowed_methods", [])
    if not isinstance(allowed_methods, list) or not allowed_methods:
        return

    clients = server_entry.get("clients", {})
    if not isinstance(clients, dict):
        return

    normalized_methods = [str(method) for method in allowed_methods]

    for client_cfg in clients.values():
        if not isinstance(client_cfg, dict):
            continue
        if client_cfg.get("transport") != "stdio":
            continue

        command = client_cfg.get("command")
        if not isinstance(command, list) or "mcp-filter" not in command:
            continue

        # Strip any existing -a <method> pairs and append desired ones.
        rebuilt: list[str] = []
        i = 0
        while i < len(command):
            if command[i] == "-a":
                i += 2
                continue
            rebuilt.append(str(command[i]))
            i += 1
        for method in normalized_methods:
            rebuilt.extend(["-a", method])
        client_cfg["command"] = rebuilt


def resolve_mcp_catalog(
    config: Mapping[str, Any], env: Mapping[str, str] | None = None
) -> dict[str, Any]:
    if env is None:
        env = os.environ
    mcp_cfg = config.get("mcp", {})
    client_configs_cfg: dict[str, Any] = mcp_cfg.get("client_configs", {})
    services_cfg: dict[str, Any] = mcp_cfg.get("services", {})
    dependencies_cfg: dict[str, Any] = mcp_cfg.get("dependencies", {})

    # --- dependencies (topological sort by requires, W11) ---
    candidates_deps: dict[str, Any] = {}
    dep_requires_graph: dict[str, list[str]] = {}
    for name, dep in dependencies_cfg.items():
        if not dep.get("enabled", True):
            continue
        candidates_deps[name] = dep
        requires = dep.get("requires", [])
        if not isinstance(requires, list):
            requires = []
        dep_requires_graph[name] = requires

    resolved_dependencies: dict[str, Any] = {}
    resolved_dep_set: set[str] = set()
    remaining_deps = set(candidates_deps)
    progress = True
    while remaining_deps and progress:
        progress = False
        for name in list(remaining_deps):
            if all(r in resolved_dep_set for r in dep_requires_graph.get(name, [])):
                resolved_dependencies[name] = _expand_strings(
                    dict(candidates_deps[name]), config, env
                )
                resolved_dep_set.add(name)
                remaining_deps.discard(name)
                progress = True
    # Dependencies still in remaining_deps have unresolvable requires — silently skipped

    enabled_dependencies = set(resolved_dependencies.keys())

    # Update config with resolved dependencies for placeholder expansion
    config_with_deps = dict(config)
    if resolved_dependencies:
        mcp_with_deps = dict(config_with_deps.get("mcp", {}))
        mcp_with_deps["dependencies"] = resolved_dependencies
        config_with_deps["mcp"] = mcp_with_deps

    # Filter to enabled services that have their dependency (git/file) deps met,
    # and collect inter-service dependency edges for ordering.
    candidates: dict[str, Any] = {}
    service_dep_graph: dict[str, list[str]] = {}
    for name, svc in services_cfg.items():
        if not svc.get("enabled", True):
            continue

        # W6: merge auto-inferred dependency deps from placeholders
        inferred = _infer_requires(name, "services", svc)

        depends_on = svc.get("depends_on", {})
        if isinstance(depends_on, dict):
            dep_deps = depends_on.get("dependencies", [])
            if not isinstance(dep_deps, list):
                dep_deps = [dep_deps]
        else:
            dep_deps = []
        dep_deps = list(set(dep_deps) | set(inferred["dependencies"]))

        if any(dep not in enabled_dependencies for dep in dep_deps):
            continue

        candidates[name] = svc

        # Collect inter-service deps for ordering
        svc_deps: list[str] = []
        if isinstance(depends_on, dict):
            svc_deps = depends_on.get("services", [])
            if not isinstance(svc_deps, list):
                svc_deps = [svc_deps]
        service_dep_graph[name] = svc_deps

    # Resolve in dependency order, skipping services whose service deps aren't met.
    # Iterates until no more services can be resolved (handles arbitrary dict ordering).
    resolved_services: dict[str, Any] = {}
    resolved_set: set[str] = set()
    remaining = set(candidates)
    progress = True
    while remaining and progress:
        progress = False
        for name in list(remaining):
            if all(d in resolved_set for d in service_dep_graph.get(name, [])):
                resolved_services[name] = _expand_strings(
                    dict(candidates[name]), config_with_deps, env
                )
                resolved_set.add(name)
                remaining.discard(name)
                progress = True
    # Services still in `remaining` have unresolvable deps — silently skipped

    enabled_services = set(resolved_services.keys())

    resolved_client_configs: dict[str, Any] = {}
    for name, entry in client_configs_cfg.items():
        if not entry.get("enabled", True):
            continue
        requires_env = entry.get("requires_env", [])
        if requires_env and not _has_required_env(requires_env, env):
            continue

        # W6: merge auto-inferred dependencies from placeholders
        inferred = _infer_requires(name, "client_configs", entry)

        depends_on = entry.get("depends_on", {})
        if not isinstance(depends_on, dict):
            depends_on = {}
        else:
            depends_on = _expand_strings(depends_on, config_with_deps, env)

        # Union explicit + inferred service deps
        service_deps = depends_on.get("services", [])
        if not isinstance(service_deps, list):
            service_deps = [service_deps]
        service_deps = list(set(service_deps) | set(inferred["services"]))

        if any(dep not in enabled_services for dep in service_deps):
            continue

        # Union explicit + inferred dependency deps
        dep_deps = depends_on.get("dependencies", [])
        if not isinstance(dep_deps, list):
            dep_deps = [dep_deps]
        dep_deps = list(set(dep_deps) | set(inferred["dependencies"]))

        if any(dep not in enabled_dependencies for dep in dep_deps):
            continue

        clients = entry.get("clients", {})
        resolved_clients: dict[str, Any] = {}
        for client_name, client_cfg in clients.items():
            if client_name in CLIENTS_RESERVED_KEYS:
                resolved_clients[client_name] = client_cfg
                continue
            resolved_clients[client_name] = _expand_strings(
                dict(client_cfg), config_with_deps, env
            )

        server_entry = dict(entry)
        server_entry.pop("clients", None)
        server_entry = _expand_strings(server_entry, config_with_deps, env)
        server_entry["clients"] = resolved_clients
        _apply_allowed_methods(name, server_entry)
        resolved_client_configs[name] = server_entry

    return {
        "dependencies": resolved_dependencies,
        "client_configs": resolved_client_configs,
        "services": resolved_services,
    }
