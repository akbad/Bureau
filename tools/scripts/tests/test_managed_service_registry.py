import json
from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "managed-service-registry.py"
spec = util.spec_from_file_location("managed_service_registry", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

assess_service = module.assess_service
fingerprint_service_entry = module.fingerprint_service_entry
load_registry = module.load_registry
normalize_service_entry = module.normalize_service_entry
record_adopted = module.record_adopted
record_managed = module.record_managed
write_registry = module.write_registry


def _plan(service_entry: dict) -> dict:
    return {"services": {"qdrant_mcp": service_entry}}


SERVICE_ENTRY = {
    "kind": "http_process",
    "port": 8782,
    "command": ["uvx", "mcp-server-qdrant"],
    "env": {"QDRANT_URL": "http://127.0.0.1:8780"},
    "healthcheck": {
        "tcp": 8782,
        "mcp_tool": {
            "url": "http://localhost:8782/mcp/",
            "tool": "qdrant-find",
            "arguments": {"query": "bureau healthcheck"},
        },
    },
}


def test_normalize_service_entry_uses_only_resolved_config_fields():
    normalized = normalize_service_entry("qdrant_mcp", SERVICE_ENTRY)

    assert normalized == {
        "service_id": "qdrant_mcp",
        "kind": "http_process",
        "command": ["uvx", "mcp-server-qdrant"],
        "env": {"QDRANT_URL": "http://127.0.0.1:8780"},
        "port": 8782,
        "healthcheck": SERVICE_ENTRY["healthcheck"],
    }


def test_fingerprint_service_entry_is_stable():
    normalized = normalize_service_entry("qdrant_mcp", SERVICE_ENTRY)

    assert fingerprint_service_entry(normalized) == fingerprint_service_entry(normalized)


def test_assess_service_starts_when_no_listener():
    decision = assess_service("qdrant_mcp", _plan(SERVICE_ENTRY), {}, port_listening=False)

    assert decision["action"] == "start"
    assert decision["status"] == "absent"


def test_assess_service_reuses_matching_managed_listener():
    fingerprint = fingerprint_service_entry(
        normalize_service_entry("qdrant_mcp", SERVICE_ENTRY)
    )
    registry = {"services": {"qdrant_mcp": {"status": "managed", "fingerprint": fingerprint}}}

    decision = assess_service("qdrant_mcp", _plan(SERVICE_ENTRY), registry, port_listening=True)

    assert decision["action"] == "reuse"
    assert decision["status"] == "managed_current"


def test_assess_service_restarts_stale_managed_listener():
    registry = {"services": {"qdrant_mcp": {"status": "managed", "fingerprint": "old"}}}

    decision = assess_service("qdrant_mcp", _plan(SERVICE_ENTRY), registry, port_listening=True)

    assert decision["action"] == "restart"
    assert decision["status"] == "managed_stale"


def test_assess_service_restarts_adopted_unverified_listener():
    registry = {"services": {"qdrant_mcp": {"status": "adopted_unverified"}}}

    decision = assess_service("qdrant_mcp", _plan(SERVICE_ENTRY), registry, port_listening=True)

    assert decision["action"] == "restart"
    assert decision["status"] == "adopted_unverified"


def test_assess_service_adopts_unregistered_listener_temporarily():
    decision = assess_service("qdrant_mcp", _plan(SERVICE_ENTRY), {}, port_listening=True)

    assert decision["action"] == "adopt"
    assert decision["status"] == "unregistered"


def test_record_managed_preserves_other_services_and_runtime_metadata():
    registry = {"version": 1, "services": {"sourcegraph_mcp": {"status": "managed"}}}

    updated = record_managed(
        registry,
        "qdrant_mcp",
        _plan(SERVICE_ENTRY),
        pid=123,
        log_file="/tmp/mcp-qdrant_mcp-server.log",
        now="2026-01-01T00:00:00+00:00",
    )

    service = updated["services"]["qdrant_mcp"]
    assert updated["services"]["sourcegraph_mcp"]["status"] == "managed"
    assert service["status"] == "managed"
    assert service["pid"] == 123
    assert service["log_file"] == "/tmp/mcp-qdrant_mcp-server.log"
    assert service["last_verified_at"] == "2026-01-01T00:00:00+00:00"
    assert service["fingerprint"] == fingerprint_service_entry(
        normalize_service_entry("qdrant_mcp", SERVICE_ENTRY)
    )


def test_record_adopted_does_not_mark_fingerprint_as_managed():
    updated = record_adopted(
        {},
        "qdrant_mcp",
        _plan(SERVICE_ENTRY),
        pid=123,
        log_file="/tmp/mcp-qdrant_mcp-server.log",
        now="2026-01-01T00:00:00+00:00",
    )

    service = updated["services"]["qdrant_mcp"]
    assert service["status"] == "adopted_unverified"
    assert "fingerprint" not in service
    assert service["desired_fingerprint_at_adoption"] == fingerprint_service_entry(
        normalize_service_entry("qdrant_mcp", SERVICE_ENTRY)
    )


def test_load_registry_moves_invalid_json_aside(tmp_path):
    registry_path = tmp_path / "managed-services.json"
    registry_path.write_text("{bad json", encoding="utf-8")

    registry = load_registry(str(registry_path))

    assert registry == {"version": 1, "services": {}}
    assert not registry_path.exists()
    assert registry_path.with_suffix(".json.backup").exists()


def test_write_registry_uses_json_file(tmp_path):
    registry_path = tmp_path / "managed-services.json"

    write_registry(str(registry_path), {"version": 1, "services": {}})

    assert json.loads(registry_path.read_text(encoding="utf-8")) == {
        "version": 1,
        "services": {},
    }
