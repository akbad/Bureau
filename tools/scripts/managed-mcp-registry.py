#!/usr/bin/env -S uv run
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from operations.json_config_utils import load_json_config, save_json_config


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = load_json_config(str(path), create_backup=False)
    except SystemExit:
        return {}
    return data if isinstance(data, dict) else {}


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        return {}

    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_cli_entries(cli: str, config_path: str) -> dict[str, Any]:
    path = Path(config_path).expanduser()
    if cli == "claude":
        data = _load_json(path)
        return data.get("mcpServers", {}) if isinstance(data, dict) else {}
    if cli == "gemini":
        data = _load_json(path)
        return data.get("mcpServers", {}) if isinstance(data, dict) else {}
    if cli == "opencode":
        data = _load_json(path)
        return data.get("mcp", {}) if isinstance(data, dict) else {}
    if cli in {"codex", "grok"}:
        data = _load_toml(path)
        return data.get("mcp_servers", {}) if isinstance(data, dict) else {}
    return {}


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def normalize_entry(cli: str, raw_entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_entry, dict):
        return {}

    if cli == "claude":
        transport = raw_entry.get("type")
        if transport == "http":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if transport == "stdio":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                }
            )

    if cli == "gemini":
        if "httpUrl" in raw_entry:
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("httpUrl"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if "command" in raw_entry:
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                    "timeout_ms": raw_entry.get("timeout"),
                }
            )

    if cli == "codex":
        transport = raw_entry.get("transport")
        if transport is None:
            if "url" in raw_entry:
                transport = "http"
            elif "command" in raw_entry:
                transport = "stdio"
        if transport == "http":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "bearer_token_env_var": raw_entry.get("bearer_token_env_var"),
                }
            )
        if transport == "stdio":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                    "startup_timeout_sec": raw_entry.get("startup_timeout_sec"),
                    "tool_timeout_sec": raw_entry.get("tool_timeout_sec"),
                }
            )

    if cli == "grok":
        # Grok config.toml uses Codex-like mcp_servers sections; HTTP supports headers.
        transport = raw_entry.get("transport")
        if transport is None:
            if "url" in raw_entry:
                transport = "http"
            elif "command" in raw_entry:
                transport = "stdio"
        if transport == "http":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if transport == "stdio":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "args": raw_entry.get("args", []),
                    "env": raw_entry.get("env"),
                    "startup_timeout_sec": raw_entry.get("startup_timeout_sec"),
                    "tool_timeout_sec": raw_entry.get("tool_timeout_sec"),
                }
            )

    if cli == "opencode":
        entry_type = raw_entry.get("type")
        if entry_type == "remote":
            return _drop_none(
                {
                    "transport": "http",
                    "url": raw_entry.get("url"),
                    "headers": raw_entry.get("headers"),
                }
            )
        if entry_type == "local":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": raw_entry.get("command"),
                    "env": raw_entry.get("environment") or raw_entry.get("env"),
                    "timeout_ms": raw_entry.get("timeout"),
                }
            )

    return {}


def fingerprint_entry(normalized: dict[str, Any]) -> str:
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_registry(path: str) -> dict[str, Any]:
    data = _load_json(Path(path).expanduser())
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("servers", {})
    return data


def write_registry(path: str, data: dict[str, Any]) -> None:
    save_json_config(path, data, indent=2)


def _desired_servers(plan: dict[str, Any], cli: str) -> list[str]:
    client_configs = plan.get("client_configs", {}).get(cli, {})
    if isinstance(client_configs, dict):
        return sorted(client_configs.keys())
    return []


def normalize_desired_entry(cli: str, desired_entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(desired_entry, dict):
        return {}

    transport = desired_entry.get("transport")
    if transport == "http":
        payload = {
            "transport": "http",
            "url": desired_entry.get("url"),
        }
        if cli in {"claude", "gemini", "opencode", "grok"}:
            payload["headers"] = desired_entry.get("headers")
        if cli == "codex":
            payload["bearer_token_env_var"] = desired_entry.get("bearer_token_env_var")
        return _drop_none(payload)

    if transport == "stdio":
        command = desired_entry.get("command", [])
        if not isinstance(command, list) or not command:
            return {}
        if cli == "opencode":
            return _drop_none(
                {
                    "transport": "stdio",
                    "command": command,
                    "env": desired_entry.get("env") or desired_entry.get("environment"),
                    "timeout_ms": desired_entry.get("timeout_ms"),
                }
            )
        payload = {
            "transport": "stdio",
            "command": command[0],
            "args": command[1:],
            "env": desired_entry.get("env"),
        }
        if cli == "gemini":
            payload["timeout_ms"] = desired_entry.get("timeout_ms")
        if cli in {"codex", "grok"}:
            payload["startup_timeout_sec"] = desired_entry.get("startup_timeout_sec")
            payload["tool_timeout_sec"] = desired_entry.get("tool_timeout_sec")
        return _drop_none(payload)

    return {}


def compute_prune(
    cli: str,
    plan: dict[str, Any],
    registry: dict[str, Any],
    current_entries: dict[str, Any],
) -> list[str]:
    desired = set(_desired_servers(plan, cli))
    to_remove: list[str] = []
    servers = registry.get("servers")
    if not isinstance(servers, dict):
        servers = {}
    for server_id, info in servers.items():
        if server_id in desired:
            continue
        current = current_entries.get(server_id)
        if not isinstance(current, dict):
            continue
        normalized = normalize_entry(cli, current)
        if not normalized:
            continue
        if fingerprint_entry(normalized) == info.get("fingerprint"):
            to_remove.append(server_id)
    return sorted(to_remove)


def compute_update(
    cli: str,
    plan: dict[str, Any],
    registry: dict[str, Any],
    current_entries: dict[str, Any],
) -> list[str]:
    if cli == "opencode":
        return []

    desired_cfgs = plan.get("client_configs", {}).get(cli, {})
    if not isinstance(desired_cfgs, dict):
        return []

    to_update: list[str] = []
    servers = registry.get("servers")
    if not isinstance(servers, dict):
        servers = {}

    for server_id, desired_entry in desired_cfgs.items():
        current = current_entries.get(server_id)
        registry_info = servers.get(server_id)
        if not isinstance(current, dict) or not isinstance(registry_info, dict):
            continue

        normalized_current = normalize_entry(cli, current)
        normalized_desired = normalize_desired_entry(cli, desired_entry)
        if not normalized_current or not normalized_desired:
            continue

        current_fingerprint = fingerprint_entry(normalized_current)
        desired_fingerprint = fingerprint_entry(normalized_desired)
        recorded_fingerprint = registry_info.get("fingerprint")

        if current_fingerprint == recorded_fingerprint and current_fingerprint != desired_fingerprint:
            to_update.append(server_id)

    return sorted(to_update)


def record_registry(
    cli: str,
    plan: dict[str, Any],
    current_entries: dict[str, Any],
    previous_registry: dict[str, Any],
    written_ids: set[str],
    now: str | None = None,
) -> dict[str, Any]:
    """Rebuild the managed-MCP registry for `cli`, remembering entries until they leave the live config.

    The registry stores a fingerprint of every entry Bureau wrote to a CLI's
    config so `compute_prune` can later remove a no-longer-desired entry while
    leaving user-modified ones alone. An entry is retained until it is physically
    absent from the config — not merely until it stops being desired — so a failed
    removal is retried on a subsequent run instead of becoming an orphan.

    Args:
        `cli`: target CLI (`claude` / `gemini` / `codex` / `opencode` / `grok`).
        `plan`: resolved MCP plan; `plan["client_configs"][cli]` lists desired servers.
        `current_entries`: servers actually present in the live CLI config right now.
        `previous_registry`: the prior run's registry, whose `servers` memory is carried forward.
        `written_ids`: ids the per-agent add step actually WROTE to `cli`'s config
            this run (as opposed to finding already present and skipping). Only
            these ids are eligible to be freshly fingerprinted below — see the
            C6 safety note on the fingerprinting loop for why.
        `now`: ISO-8601 `updated_at` value; defaults to current UTC time.

    Returns:
        New registry dict with `version`, `updated_at`, and `servers`. A present-but-
        undesired entry carries `retired: True` (diagnostic only; `compute_prune`
        ignores it).
    """
    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    desired = set(_desired_servers(plan, cli))

    # carry forward prior memory so an entry is never forgotten while it still
    # exists in the live config. forgetting on "no longer desired" (the previous
    # behaviour) stranded any entry whose removal failed: record erased it while
    # it was still present, and compute_prune only ever acts on remembered ids,
    # so nothing could retry — a permanent, unprunable orphan (issue C5).
    # rejected alternative: tag the entry inside the CLI's own config file.
    # Bureau delegates Claude writes to `claude mcp add` (no metadata field) and
    # CLIs may strip unknown keys on rewrite, so a config-side tag cannot cover
    # all four CLIs; a Bureau-owned ledger is CLI-agnostic.
    servers: dict[str, Any] = {}
    prior_servers = previous_registry.get("servers")
    if isinstance(prior_servers, dict):
        for server_id, info in prior_servers.items():
            if isinstance(info, dict):
                servers[server_id] = dict(info)

    # (re)fingerprint only ids Bureau is CERTAIN it wrote this run — never
    # "everything currently desired" (issue C6). The per-agent add step
    # returns "already exists" (not "written") whenever an id collides with
    # something already sitting in the live config, and that something is not
    # necessarily a Bureau entry: it can be a user's own hand-added server
    # that happens to share an id with a Bureau catalog entry. Fingerprinting
    # every desired-and-present id, regardless of who put it there, silently
    # adopted such a user entry as Bureau-owned; once the id later left the
    # plan, compute_prune's fingerprint match still succeeded and Bureau
    # deleted the user's entry. Restricting this loop to `written_ids` means
    # an unwritten collision is never fingerprinted here, so it can never
    # enter `servers` and can therefore never be pruned. A carried-forward
    # entry (the block above) is untouched by this restriction, so an id
    # Bureau legitimately wrote in a *prior* run and merely finds
    # already-present this run (the common case) still stays tracked.
    #
    # rejected alternative: infer ownership by comparing the current entry's
    # fingerprint against the desired plan entry's fingerprint. Rejected
    # because a user could hand-write an entry that happens to exactly match
    # Bureau's desired shape (e.g. copying Bureau's own recommended snippet),
    # which would still misattribute ownership; only the add step's own
    # success/failure outcome — did *this run* put the bytes there? —
    # actually distinguishes the two cases.
    #
    # intersect with `desired`: written_ids is caller-supplied; guard against
    # fingerprinting an id outside the current plan should it ever contain one.
    #
    # known limitation: this prevents NEW mis-records but does not auto-heal
    # one that already exists in the registry from before this fix — such an
    # entry is carried forward like any other tracked id above. Clearing it
    # requires a one-time registry audit/reset, not something record_registry
    # can safely infer on its own.
    for server_id in written_ids & desired:
        current = current_entries.get(server_id)
        if not isinstance(current, dict):
            # written this run but not present now is a contradiction we don't
            # expect, but fail safe: nothing to fingerprint, so leave unrecorded
            continue
        normalized = normalize_entry(cli, current)
        if not normalized:
            continue
        servers[server_id] = {"fingerprint": fingerprint_entry(normalized)}

    # reconcile memory to physical reality: forget an id only once it is truly
    # gone from the live config (this bounds registry growth); keep a still-present
    # but no-longer-desired id, flagged, so the next reconcile retries its removal
    for server_id in list(servers):
        if server_id not in current_entries:
            del servers[server_id]
        elif server_id not in desired:
            servers[server_id]["retired"] = True

    # emit servers in a stable key order so the persisted registry is
    # deterministic across runs, avoiding spurious rewrites and noisy diffs
    return {
        "version": 1,
        "updated_at": now,
        "servers": {server_id: servers[server_id] for server_id in sorted(servers)},
    }


def should_preserve_registry(
    current_entries: dict[str, Any],
    previous_registry: dict[str, Any],
) -> bool:
    """Return True when the live config looks unreadable, so prior memory must be kept.

    An empty `current_entries` at record time is anomalous: the per-agent add step
    runs before record (see `set-up-tools.sh`), so the desired entries should already
    be present. Empty therefore almost always means the config failed to load — e.g.
    a concurrent rewrite of `~/.claude.json` left it briefly unparseable — in which
    case rewriting the registry would wipe the carried-forward memory that lets a
    failed removal be retried (issue C5). Preserve the prior registry when, and only
    when, there is such memory to lose.

    Args:
        `current_entries`: servers read from the live CLI config this run.
        `previous_registry`: the registry produced by the prior run.

    Returns:
        True if the prior registry should be kept unchanged; False to record normally.
    """
    if current_entries:
        return False
    prior_servers = previous_registry.get("servers")
    return isinstance(prior_servers, dict) and bool(prior_servers)


def _load_plan(path: str) -> dict[str, Any]:
    return _load_json(Path(path).expanduser())


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Bureau MCP registry state.")
    parser.add_argument("--mode", choices=["prune", "record", "reconcile"], required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--written",
        default="",
        help=(
            "Comma-separated ids the per-agent add step actually WROTE to the "
            "CLI config this run (record mode only); absent/empty means none"
        ),
    )
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    registry = load_registry(args.registry)
    current_entries = load_cli_entries(args.cli, args.config)

    if args.mode == "prune":
        result = {
            "to_remove": compute_prune(args.cli, plan, registry, current_entries),
            "registry": registry,
        }
        print(json.dumps(result))
        return 0

    if args.mode == "reconcile":
        result = {
            "to_remove": compute_prune(args.cli, plan, registry, current_entries),
            "to_update": compute_update(args.cli, plan, registry, current_entries),
            "registry": registry,
        }
        print(json.dumps(result))
        return 0

    # guard against wiping memory on an unreadable live config: an empty read at
    # record time almost always means a load failure, not a genuinely empty config
    if should_preserve_registry(current_entries, registry):
        print(json.dumps(registry))
        return 0

    # split on comma and drop empties so "" and "a,b" both parse cleanly,
    # including a trailing comma from the shell caller's accumulation pattern
    written_ids = {server_id for server_id in args.written.split(",") if server_id}

    # `registry` is the prior run's on-disk state (reconcile mode never writes it),
    # so record carries that memory forward rather than starting from scratch
    updated = record_registry(args.cli, plan, current_entries, registry, written_ids)
    write_registry(args.registry, updated)
    print(json.dumps(updated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
