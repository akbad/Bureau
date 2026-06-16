#!/usr/bin/env -S uv run
"""Track Bureau-owned runtime services by resolved configuration fingerprint.

Client MCP registries already protect user-edited CLI config by hashing the
normalized desired entry. Runtime services need the same ownership proof plus a
small lifecycle state so `open-bureau` can distinguish current Bureau services,
stale Bureau services, and healthy but unverified legacy listeners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JsonObject = dict[str, Any]
MANAGED_STATUS = "managed"
ADOPTED_UNVERIFIED_STATUS = "adopted_unverified"


def _load_json(path: Path) -> JsonObject:
    """Load a JSON object from `path`, returning an empty dict if absent."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def load_registry(path: str) -> JsonObject:
    """Load managed-service registry state.

    Invalid JSON is moved aside because a corrupt registry cannot safely prove
    ownership of any running process.
    """
    registry_path = Path(path).expanduser()
    if not registry_path.exists():
        return {"version": 1, "services": {}}

    try:
        data = _load_json(registry_path)
    except json.JSONDecodeError:
        backup_path = registry_path.with_suffix(".json.backup")
        registry_path.replace(backup_path)
        return {"version": 1, "services": {}}

    data.setdefault("version", 1)
    services = data.get("services")
    if not isinstance(services, dict):
        data["services"] = {}
    return data


def write_registry(path: str, registry: JsonObject) -> None:
    """Atomically write `registry` to `path`."""
    registry_path = Path(path).expanduser()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = registry_path.with_name(f".{registry_path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp_path, registry_path)


def _service_entry(plan: JsonObject, service_id: str) -> JsonObject:
    services = plan.get("services", {})
    if not isinstance(services, dict):
        return {}
    entry = services.get(service_id, {})
    return entry if isinstance(entry, dict) else {}


def normalize_service_entry(service_id: str, entry: JsonObject) -> JsonObject:
    """Normalize resolved service config into fingerprint input.

    Runtime facts such as PID, log file, timestamps, and healthcheck results are
    deliberately excluded. The fingerprint answers whether Bureau's desired
    launch contract changed, not whether the process is currently alive.
    """
    normalized: JsonObject = {
        "service_id": service_id,
        "kind": entry.get("kind"),
    }
    for key in ("command", "env", "port", "healthcheck"):
        if key in entry:
            normalized[key] = entry[key]
    return normalized


def fingerprint_service_entry(normalized: JsonObject) -> str:
    """Return a stable SHA-256 fingerprint for `normalized` service config."""
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _desired_fingerprint(service_id: str, plan: JsonObject) -> str:
    entry = _service_entry(plan, service_id)
    return fingerprint_service_entry(normalize_service_entry(service_id, entry))


def assess_service(
    service_id: str,
    plan: JsonObject,
    registry: JsonObject,
    *,
    port_listening: bool,
) -> JsonObject:
    """Decide whether setup should start, reuse, restart, or adopt a service."""
    desired_fingerprint = _desired_fingerprint(service_id, plan)
    if not port_listening:
        return {
            "service_id": service_id,
            "action": "start",
            "status": "absent",
            "desired_fingerprint": desired_fingerprint,
        }

    services = registry.get("services", {})
    info = services.get(service_id) if isinstance(services, dict) else None
    if not isinstance(info, dict):
        return {
            "service_id": service_id,
            "action": "adopt",
            "status": "unregistered",
            "desired_fingerprint": desired_fingerprint,
        }

    status = info.get("status")
    if status == ADOPTED_UNVERIFIED_STATUS:
        return {
            "service_id": service_id,
            "action": "restart",
            "status": ADOPTED_UNVERIFIED_STATUS,
            "desired_fingerprint": desired_fingerprint,
        }

    if status == MANAGED_STATUS and info.get("fingerprint") == desired_fingerprint:
        return {
            "service_id": service_id,
            "action": "reuse",
            "status": "managed_current",
            "desired_fingerprint": desired_fingerprint,
        }

    return {
        "service_id": service_id,
        "action": "restart",
        "status": "managed_stale",
        "desired_fingerprint": desired_fingerprint,
    }


def _copy_registry(registry: JsonObject) -> JsonObject:
    """Return a JSON-safe deep copy of `registry`."""
    return json.loads(json.dumps(registry))


def _record_common(
    registry: JsonObject,
    service_id: str,
    plan: JsonObject,
    *,
    pid: int | None,
    log_file: str | None,
    now: str,
    status: str,
    last_action: str,
) -> JsonObject:
    updated = _copy_registry(registry)
    updated.setdefault("version", 1)
    updated["updated_at"] = now
    services = updated.setdefault("services", {})

    entry = _service_entry(plan, service_id)
    service_record: JsonObject = {
        "status": status,
        "port": entry.get("port"),
        "health_port": entry.get("healthcheck", {}).get("tcp", entry.get("port"))
        if isinstance(entry.get("healthcheck"), dict)
        else entry.get("port"),
        "last_verified_at": now,
        "last_action": last_action,
    }
    if pid is not None:
        service_record["pid"] = pid
    if log_file is not None:
        service_record["log_file"] = log_file

    services[service_id] = service_record
    return updated


def record_managed(
    registry: JsonObject,
    service_id: str,
    plan: JsonObject,
    *,
    pid: int | None,
    log_file: str | None,
    now: str | None = None,
    last_action: str = "recorded",
) -> JsonObject:
    """Record `service_id` as Bureau-managed for the current resolved config."""
    if now is None:
        now = datetime.now(timezone.utc).isoformat()
    updated = _record_common(
        registry,
        service_id,
        plan,
        pid=pid,
        log_file=log_file,
        now=now,
        status=MANAGED_STATUS,
        last_action=last_action,
    )
    updated["services"][service_id]["fingerprint"] = _desired_fingerprint(
        service_id, plan
    )
    return updated


def record_adopted(
    registry: JsonObject,
    service_id: str,
    plan: JsonObject,
    *,
    pid: int | None,
    log_file: str | None,
    now: str | None = None,
) -> JsonObject:
    """Record a healthy pre-existing listener without claiming config freshness."""
    if now is None:
        now = datetime.now(timezone.utc).isoformat()
    updated = _record_common(
        registry,
        service_id,
        plan,
        pid=pid,
        log_file=log_file,
        now=now,
        status=ADOPTED_UNVERIFIED_STATUS,
        last_action="adopted",
    )
    updated["services"][service_id]["desired_fingerprint_at_adoption"] = (
        _desired_fingerprint(service_id, plan)
    )
    return updated


def _load_plan(path: str) -> JsonObject:
    return _load_json(Path(path).expanduser())


def main() -> int:
    """Manage runtime service registry state from shell setup scripts."""
    parser = argparse.ArgumentParser(description="Manage Bureau service registry.")
    parser.add_argument("--mode", choices=["assess", "record-managed", "record-adopted"], required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--port-listening", choices=["true", "false"], default="false")
    parser.add_argument("--pid", type=int, default=None)
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--last-action", default="recorded")
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    registry = load_registry(args.registry)

    if args.mode == "assess":
        result = assess_service(
            args.service,
            plan,
            registry,
            port_listening=args.port_listening == "true",
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.mode == "record-managed":
        updated = record_managed(
            registry,
            args.service,
            plan,
            pid=args.pid,
            log_file=args.log_file,
            last_action=args.last_action,
        )
    else:
        updated = record_adopted(
            registry,
            args.service,
            plan,
            pid=args.pid,
            log_file=args.log_file,
        )

    write_registry(args.registry, updated)
    print(json.dumps(updated, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
