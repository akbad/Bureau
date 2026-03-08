"""Tests for MCP deep schema validation (Issue #5).

Covers kind enum validation, required fields per kind, unknown key
warnings, transport-required fields, and edge cases across all three
MCP config buckets (dependencies, services, client_configs).
"""
import pytest

from operations.validate_config import (
    ValidationResult,
    validate_mcp_rules,
    validate_config,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _errors(config: dict) -> list[str]:
    """Shortcut: extract only errors from validate_mcp_rules."""
    return validate_mcp_rules(config).errors


def _warnings(config: dict) -> list[str]:
    """Shortcut: extract only warnings from validate_mcp_rules."""
    return validate_mcp_rules(config).warnings


# ── Dependency kind validation ──────────────────────────────────────

class TestDependencyKindValidation:
    """Tests for mcp.dependencies kind enum and required field checks."""

    def test_valid_git_repo_produces_no_errors(self):
        config = {"mcp": {"dependencies": {
            "my_repo": {
                "enabled": True, "kind": "git_repo",
                "repo_url": "https://example.com/repo.git", "path": "/tmp/repo",
            },
        }}}
        assert _errors(config) == []

    def test_valid_file_produces_no_errors(self):
        config = {"mcp": {"dependencies": {
            "my_store": {"enabled": True, "kind": "file", "path": "/data/store"},
        }}}
        assert _errors(config) == []

    def test_invalid_kind_produces_error(self):
        config = {"mcp": {"dependencies": {
            "bad": {"enabled": True, "kind": "invalid_kind", "path": "/x"},
        }}}
        errors = _errors(config)
        assert len(errors) == 1
        assert "'invalid_kind' not in" in errors[0]

    def test_missing_kind_produces_error(self):
        """kind is required for dependencies (W1)."""
        config = {"mcp": {"dependencies": {
            "repo": {"enabled": True, "path": "/tmp/repo"},
        }}}
        errors = _errors(config)
        assert any("missing required field 'kind'" in e for e in errors)

    def test_git_repo_missing_required_fields(self):
        config = {"mcp": {"dependencies": {
            "bad_repo": {"enabled": True, "kind": "git_repo"},
        }}}
        errors = _errors(config)
        assert any("path" in e for e in errors)
        assert any("repo_url" in e for e in errors)

    def test_file_missing_path(self):
        config = {"mcp": {"dependencies": {
            "bad_store": {"enabled": True, "kind": "file"},
        }}}
        errors = _errors(config)
        assert len(errors) == 1
        assert "path" in errors[0]


# ── Runtime service kind validation ─────────────────────────────────

class TestServiceKindValidation:
    """Tests for mcp.services kind enum and required field checks."""

    def test_valid_docker_container_produces_no_errors(self):
        config = {"mcp": {"services": {
            "db": {
                "enabled": True, "kind": "docker_container",
                "image": "postgres", "host_port": 5432, "container_port": 5432,
            },
        }}}
        assert _errors(config) == []

    def test_valid_http_process_produces_no_errors(self):
        config = {"mcp": {"services": {
            "api": {
                "enabled": True, "kind": "http_process",
                "port": 8080, "command": ["uvx", "run", "server"],
            },
        }}}
        assert _errors(config) == []

    def test_invalid_kind_produces_error(self):
        config = {"mcp": {"services": {
            "bad": {"enabled": True, "kind": "k8s_pod"},
        }}}
        errors = _errors(config)
        assert len(errors) == 1
        assert "'k8s_pod' not in" in errors[0]

    def test_docker_container_missing_required_fields(self):
        config = {"mcp": {"services": {
            "db": {"enabled": True, "kind": "docker_container"},
        }}}
        errors = _errors(config)
        assert any("image" in e for e in errors)
        assert any("host_port" in e for e in errors)
        assert any("container_port" in e for e in errors)

    def test_http_process_missing_required_fields(self):
        config = {"mcp": {"services": {
            "api": {"enabled": True, "kind": "http_process"},
        }}}
        errors = _errors(config)
        assert any("port" in e for e in errors)
        assert any("command" in e for e in errors)


# ── Client config validation ────────────────────────────────────────

class TestClientConfigValidation:
    """Tests for mcp.client_configs: top-level, nested clients, transport requirements."""

    def test_valid_http_client_produces_no_errors(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "http", "url": "http://localhost:8080/mcp/"},
            }},
        }}}
        assert _errors(config) == []

    def test_valid_stdio_client_produces_no_errors(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "stdio", "command": ["npx", "server"]},
            }},
        }}}
        assert _errors(config) == []

    def test_http_client_missing_url(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "http"},
            }},
        }}}
        errors = _errors(config)
        assert any("url" in e for e in errors)

    def test_stdio_client_missing_command(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "stdio"},
            }},
        }}}
        errors = _errors(config)
        assert any("command" in e for e in errors)

    def test_empty_clients_dict_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {}},
        }}}
        errors = _errors(config)
        assert any("must have at least one client" in e for e in errors)

    def test_non_dict_clients_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": "not_a_dict"},
        }}}
        errors = _errors(config)
        assert any("expected dict" in e for e in errors)

    def test_non_dict_client_entry_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": "not_a_dict",
            }},
        }}}
        errors = _errors(config)
        assert any("expected dict" in e for e in errors)


# ── Unknown key warnings ────────────────────────────────────────────

class TestUnknownKeyWarnings:
    """Tests that unknown keys produce warnings (not errors) across all buckets."""

    def test_unknown_dependency_key_produces_warning(self):
        config = {"mcp": {"dependencies": {
            "repo": {"enabled": True, "kind": "git_repo",
                     "repo_url": "https://x.git", "path": "/x",
                     "typo_key": "val"},
        }}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("typo_key" in w for w in result.warnings)

    def test_unknown_service_key_produces_warning(self):
        config = {"mcp": {"services": {
            "svc": {"enabled": True, "kind": "http_process",
                    "port": 1, "command": ["x"],
                    "misspelled_key": "val"},
        }}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("misspelled_key" in w for w in result.warnings)

    def test_unknown_client_config_key_produces_warning(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "http", "url": "http://x"},
            }, "enabeld": True},
        }}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("enabeld" in w for w in result.warnings)

    def test_unknown_client_entry_key_produces_warning(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "http", "url": "http://x",
                            "timout_ms": 5000},
            }},
        }}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("timout_ms" in w for w in result.warnings)

    def test_unknown_depends_on_key_produces_warning(self):
        config = {"mcp": {"services": {
            "svc": {"enabled": True, "kind": "http_process",
                    "port": 1, "command": ["x"],
                    "depends_on": {"servies": ["other"]}},
        }}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("servies" in w for w in result.warnings)


# ── Edge cases ──────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases: non-dict entries, empty config, integration, etc."""

    @staticmethod
    def _base_valid_config() -> dict:
        return {
            "agents": ["claude"],
            "retention_period_for": {
                "claude_mem": "30d",
                "serena": "30d",
                "qdrant": "30d",
                "memory_mcp": "30d",
            },
            "cleanup": {"min_interval": "1h"},
            "trash": {"grace_period": "7d"},
            "path_to": {"workspace": "/tmp"},
            "startup_timeout_for": {"mcp_servers": 30, "docker_daemon": 30},
            "mcp": {
                "services": {},
                "client_configs": {},
            },
        }

    def test_non_dict_entry_produces_error(self):
        config = {"mcp": {"dependencies": {
            "bad": "not_a_dict",
        }}}
        errors = _errors(config)
        assert any("expected dict" in e for e in errors)

    def test_empty_mcp_section_produces_no_errors(self):
        config = {"mcp": {}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert result.warnings == []

    def test_missing_mcp_section_produces_no_errors(self):
        config = {}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_dataclass_defaults(self):
        r = ValidationResult()
        assert r.errors == []
        assert r.warnings == []

    def test_validation_result_instances_are_independent(self):
        """Verify default_factory prevents shared mutable state."""
        a = ValidationResult()
        b = ValidationResult()
        a.errors.append("x")
        assert b.errors == []

    def test_validate_config_includes_mcp_validation_errors(self):
        """Verify that validate_config() surfaces MCP schema errors."""
        # build a config that passes structural validation but has a bad kind
        config = self._base_valid_config()
        config["mcp"]["services"] = {"bad_svc": {"kind": "invalid_kind"}}
        errors = validate_config(config)
        assert any("invalid_kind" in e for e in errors)

    def test_validate_config_with_warnings_returns_warnings(self):
        """Verify that validate_config with add_warnings set surfaces warnings."""
        config = self._base_valid_config()
        config["mcp"]["services"] = {
            "svc": {
                "kind": "http_process",
                "port": 1,
                "command": ["x"],
                "typo_field": "val",
            }
        }
        result = validate_config(config, add_warnings=True)
        assert any("typo_field" in w for w in result.warnings)

    def test_validate_config_rejects_legacy_runtime_services_key_only(self):
        config = self._base_valid_config()
        config["mcp"].pop("services")
        config["mcp"]["runtime_services"] = {
            "svc": {"kind": "http_process", "port": 1, "command": ["x"]}
        }

        errors = validate_config(config)
        assert any("Unsupported key: 'mcp.runtime_services'." in e for e in errors)

    def test_validate_config_rejects_legacy_runtime_services_even_with_services(self):
        config = self._base_valid_config()
        config["mcp"]["runtime_services"] = {
            "legacy": {"kind": "http_process", "port": 9, "command": ["x"]}
        }
        config["mcp"]["services"] = {
            "svc": {"kind": "http_process", "port": 1, "command": ["x"]}
        }

        errors = validate_config(config)
        assert any("Unsupported key: 'mcp.runtime_services'." in e for e in errors)

    def test_validate_config_accepts_services_without_legacy_key(self):
        config = self._base_valid_config()
        config["mcp"]["services"] = {
            "svc": {"kind": "http_process", "port": 1, "command": ["x"]}
        }

        errors = validate_config(config)
        assert not any("mcp.runtime_services" in e for e in errors)

    def test_real_config_produces_no_errors(self):
        """Smoke test: the real defaults.yml should pass with zero errors."""
        from operations.config_loader import get_config
        config = get_config()
        result = validate_mcp_rules(config)
        assert result.errors == [], f"Real config has schema errors: {result.errors}"


# ── disabled_for validation ────────────────────────────────────────

class TestDisabledForValidation:
    """Tests for clients.disabled_for validation."""

    def test_valid_disabled_for_produces_no_errors(self):
        config = {
            "agents": ["claude", "codex", "gemini"],
            "mcp": {"client_configs": {
                "srv": {"enabled": True, "clients": {
                    "disabled_for": ["codex"],
                    "default": {"transport": "http", "url": "http://x"},
                }},
            }},
        }
        assert _errors(config) == []

    def test_disabled_for_non_list_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "disabled_for": "codex",
                "default": {"transport": "http", "url": "http://x"},
            }},
        }}}
        errors = _errors(config)
        assert any("expected list" in e for e in errors)

    def test_disabled_for_non_string_element_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "disabled_for": [123],
                "default": {"transport": "http", "url": "http://x"},
            }},
        }}}
        errors = _errors(config)
        assert any("expected string" in e for e in errors)

    def test_disabled_for_unknown_agent_produces_warning(self):
        config = {
            "agents": ["claude"],
            "mcp": {"client_configs": {
                "srv": {"enabled": True, "clients": {
                    "disabled_for": ["codex"],
                    "default": {"transport": "http", "url": "http://x"},
                }},
            }},
        }
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("codex" in w and "not in the" in w for w in result.warnings)

    def test_disabled_for_not_treated_as_client_entry(self):
        """disabled_for (a list) must not produce 'expected dict' errors."""
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "disabled_for": ["codex"],
                "default": {"transport": "http", "url": "http://x"},
            }},
        }}}
        errors = _errors(config)
        assert not any("expected dict" in e for e in errors)

    def test_only_disabled_for_with_no_clients_produces_error(self):
        """clients with only disabled_for and no actual client entries is invalid."""
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "disabled_for": ["codex"],
            }},
        }}}
        errors = _errors(config)
        assert any("must have at least one client" in e for e in errors)

    def test_empty_disabled_for_produces_no_errors(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "disabled_for": [],
                "default": {"transport": "http", "url": "http://x"},
            }},
        }}}
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert result.warnings == []


# ── Field type validation ──────────────────────────────────────────

class TestFieldTypeValidation:
    """Tests for field value type checking across all MCP buckets."""

    # ── services field types ──

    def test_command_bare_string_produces_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": "uvx run server"},
        }}}
        errors = _errors(config)
        assert any("command" in e and "list[str]" in e for e in errors)

    def test_command_list_str_produces_no_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": ["uvx", "run", "server"]},
        }}}
        assert _errors(config) == []

    def test_port_string_produces_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": "8080",
                    "command": ["x"]},
        }}}
        errors = _errors(config)
        assert any("port" in e and "expected int" in e for e in errors)

    def test_port_int_produces_no_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": ["x"]},
        }}}
        assert _errors(config) == []

    def test_port_bool_produces_error(self):
        """bool is a subclass of int; must be rejected for port fields."""
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": True,
                    "command": ["x"]},
        }}}
        errors = _errors(config)
        assert any("port" in e and "expected int" in e for e in errors)

    def test_host_port_string_produces_error(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": "5432", "container_port": 5432},
        }}}
        errors = _errors(config)
        assert any("host_port" in e and "expected int" in e for e in errors)

    def test_container_port_string_produces_error(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": "5432"},
        }}}
        errors = _errors(config)
        assert any("container_port" in e and "expected int" in e for e in errors)

    def test_env_list_produces_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": ["x"], "env": ["KEY=VAL"]},
        }}}
        errors = _errors(config)
        assert any("env" in e and "expected dict" in e for e in errors)

    def test_env_dict_str_str_produces_no_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": ["x"], "env": {"KEY": "val"}},
        }}}
        assert _errors(config) == []

    def test_env_dict_non_string_value_produces_error(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": ["x"], "env": {"KEY": 123}},
        }}}
        errors = _errors(config)
        assert any("env" in e and "dict[str, str]" in e for e in errors)

    def test_mounts_not_list_produces_error(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": 5432,
                   "mounts": {}},
        }}}
        errors = _errors(config)
        assert any("mounts" in e and "expected list[dict]" in e for e in errors)

    def test_placeholder_string_skips_type_check(self):
        """Fields containing ${...} placeholders should not produce type errors."""
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process",
                    "port": "${some.ref}", "command": ["x"]},
        }}}
        errors = _errors(config)
        assert not any("port" in e and "expected int" in e for e in errors)

    # ── dependency field types ──

    def test_post_clone_bare_string_produces_error(self):
        config = {"mcp": {"dependencies": {
            "repo": {"kind": "git_repo", "repo_url": "https://x.git",
                     "path": "/x", "post_clone": "uv sync"},
        }}}
        errors = _errors(config)
        assert any("post_clone" in e and "list[list[str]]" in e for e in errors)

    def test_post_clone_list_list_str_produces_no_error(self):
        config = {"mcp": {"dependencies": {
            "repo": {"kind": "git_repo", "repo_url": "https://x.git",
                     "path": "/x", "post_clone": [["uv", "sync"]]},
        }}}
        assert _errors(config) == []

    # ── client_config field types ──

    def test_requires_env_bare_string_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "requires_env": "TAVILY_API_KEY",
                    "clients": {
                        "default": {"transport": "http", "url": "http://x"},
                    }},
        }}}
        errors = _errors(config)
        assert any("requires_env" in e and "list[str]" in e for e in errors)

    def test_requires_env_list_str_produces_no_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "requires_env": ["TAVILY_API_KEY"],
                    "clients": {
                        "default": {"transport": "http", "url": "http://x"},
                    }},
        }}}
        assert _errors(config) == []

    # ── client entry field types ──

    def test_client_entry_command_bare_string_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "stdio", "command": "npx server"},
            }},
        }}}
        errors = _errors(config)
        assert any("command" in e and "list[str]" in e for e in errors)

    def test_client_entry_env_list_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"enabled": True, "clients": {
                "default": {"transport": "stdio", "command": ["npx"],
                            "env": ["KEY=VAL"]},
            }},
        }}}
        errors = _errors(config)
        assert any("env" in e and "expected dict" in e for e in errors)


# ── Mount sub-structure validation ─────────────────────────────────

class TestMountSubStructure:
    """Tests for mounts list entry validation inside services."""

    def _docker_config(self, mounts):
        return {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": 5432,
                   "mounts": mounts},
        }}}

    def test_valid_mount_produces_no_error(self):
        config = self._docker_config([
            {"host_path": "/data", "container_path": "/var/data"},
        ])
        assert _errors(config) == []

    def test_mount_missing_host_path_produces_error(self):
        config = self._docker_config([{"container_path": "/var/data"}])
        errors = _errors(config)
        assert any("host_path" in e for e in errors)

    def test_mount_missing_container_path_produces_error(self):
        config = self._docker_config([{"host_path": "/data"}])
        errors = _errors(config)
        assert any("container_path" in e for e in errors)

    def test_mount_unknown_key_produces_warning(self):
        config = self._docker_config([
            {"host_path": "/data", "container_path": "/var/data",
             "read_only": True},
        ])
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("read_only" in w for w in result.warnings)


# ── Healthcheck sub-structure validation ───────────────────────────

class TestHealthcheckSubStructure:
    """Tests for healthcheck dict validation inside services."""

    def _svc_config(self, healthcheck):
        return {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 8080,
                    "command": ["x"], "healthcheck": healthcheck},
        }}}

    def test_valid_tcp_healthcheck_produces_no_error(self):
        config = self._svc_config({"tcp": 8080})
        assert _errors(config) == []

    def test_healthcheck_tcp_string_produces_error(self):
        config = self._svc_config({"tcp": "8080"})
        errors = _errors(config)
        assert any("healthcheck.tcp" in e and "expected int" in e for e in errors)

    def test_healthcheck_tcp_placeholder_skips_type_check(self):
        config = self._svc_config({"tcp": "${mcp.services.svc.port}"})
        errors = _errors(config)
        assert not any("healthcheck.tcp" in e for e in errors)

    def test_healthcheck_unknown_key_produces_warning(self):
        config = self._svc_config({"grpc": 9090})
        result = validate_mcp_rules(config)
        assert result.errors == []
        assert any("grpc" in w for w in result.warnings)


# ── Transport enum validation ──────────────────────────────────────

class TestTransportEnumValidation:
    """Tests for transport field enum checking in client entries."""

    def test_valid_http_transport_produces_no_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"clients": {
                "default": {"transport": "http", "url": "http://x"},
            }},
        }}}
        assert _errors(config) == []

    def test_valid_stdio_transport_produces_no_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"clients": {
                "default": {"transport": "stdio", "command": ["npx"]},
            }},
        }}}
        assert _errors(config) == []

    def test_unknown_transport_produces_error(self):
        config = {"mcp": {"client_configs": {
            "srv": {"clients": {
                "default": {"transport": "sse", "url": "http://x"},
            }},
        }}}
        errors = _errors(config)
        assert any("transport" in e and "'sse'" in e for e in errors)

    def test_missing_transport_produces_no_error(self):
        """Client entry without transport field should not trigger enum error."""
        config = {"mcp": {"client_configs": {
            "srv": {"clients": {
                "default": {"url": "http://x"},
            }},
        }}}
        errors = _errors(config)
        assert not any("transport" in e for e in errors)


# ── Cross-reference validation ─────────────────────────────────────

class TestCrossReferenceValidation:
    """Tests for depends_on references pointing to declared entries."""

    def test_valid_service_ref_produces_no_warning(self):
        config = {"mcp": {
            "services": {
                "db": {"kind": "docker_container", "image": "pg",
                       "host_port": 5432, "container_port": 5432},
                "api": {"kind": "http_process", "port": 8080,
                        "command": ["x"],
                        "depends_on": {"services": ["db"]}},
            },
        }}
        result = validate_mcp_rules(config)
        assert not any("does not match" in w for w in result.warnings)

    def test_invalid_service_ref_produces_warning(self):
        config = {"mcp": {
            "services": {
                "api": {"kind": "http_process", "port": 8080,
                        "command": ["x"],
                        "depends_on": {"services": ["qdrant_dbb"]}},
            },
        }}
        result = validate_mcp_rules(config)
        assert any("qdrant_dbb" in w and "does not match" in w
                    for w in result.warnings)

    def test_valid_dependency_ref_produces_no_warning(self):
        config = {"mcp": {
            "dependencies": {
                "repo": {"kind": "git_repo", "repo_url": "https://x.git",
                         "path": "/x"},
            },
            "services": {
                "svc": {"kind": "http_process", "port": 8080,
                        "command": ["x"],
                        "depends_on": {"dependencies": ["repo"]}},
            },
        }}
        result = validate_mcp_rules(config)
        assert not any("does not match" in w for w in result.warnings)

    def test_invalid_dependency_ref_produces_warning(self):
        config = {"mcp": {
            "services": {
                "svc": {"kind": "http_process", "port": 8080,
                        "command": ["x"],
                        "depends_on": {"dependencies": ["repoo"]}},
            },
        }}
        result = validate_mcp_rules(config)
        assert any("repoo" in w and "does not match" in w
                    for w in result.warnings)

    def test_client_config_invalid_service_ref_produces_warning(self):
        config = {"mcp": {
            "client_configs": {
                "srv": {"enabled": True, "depends_on": {"services": ["typo_svc"]},
                        "clients": {
                            "default": {"transport": "http", "url": "http://x"},
                        }},
            },
        }}
        result = validate_mcp_rules(config)
        assert any("typo_svc" in w and "does not match" in w
                    for w in result.warnings)

    def test_client_config_invalid_dependency_ref_produces_warning(self):
        config = {"mcp": {
            "client_configs": {
                "srv": {"enabled": True,
                        "depends_on": {"dependencies": ["typo_dep"]},
                        "clients": {
                            "default": {"transport": "http", "url": "http://x"},
                        }},
            },
        }}
        result = validate_mcp_rules(config)
        assert any("typo_dep" in w and "does not match" in w
                    for w in result.warnings)

    def test_no_depends_on_produces_no_warning(self):
        config = {"mcp": {
            "services": {
                "svc": {"kind": "http_process", "port": 8080,
                        "command": ["x"]},
            },
        }}
        result = validate_mcp_rules(config)
        assert not any("does not match" in w for w in result.warnings)

    def test_non_dict_depends_on_skipped(self):
        """Non-dict depends_on should not crash cross-reference validation."""
        config = {"mcp": {
            "services": {
                "svc": {"kind": "http_process", "port": 8080,
                        "command": ["x"], "depends_on": "invalid"},
            },
        }}
        # should not raise, and should not produce cross-ref warnings
        result = validate_mcp_rules(config)
        assert not any("does not match" in w for w in result.warnings)


# ── Info tier ──────────────────────────────────────────────────────

class TestKindRequired:
    """W1: kind is required for dependencies and services."""

    def test_dependency_missing_kind_produces_error(self):
        config = {"mcp": {"dependencies": {
            "repo": {"enabled": True, "path": "/tmp/repo", "repo_url": "https://x.git"},
        }}}
        errors = _errors(config)
        assert any("missing required field 'kind'" in e for e in errors)

    def test_service_missing_kind_produces_error(self):
        config = {"mcp": {"services": {
            "svc": {"port": 8080, "command": ["x"]},
        }}}
        errors = _errors(config)
        assert any("missing required field 'kind'" in e for e in errors)

    def test_client_config_missing_kind_is_fine(self):
        """client_configs don't have a kind field — no error expected."""
        config = {"mcp": {"client_configs": {
            "qdrant": {"clients": {"default": {"transport": "http", "url": "http://localhost"}}},
        }}}
        errors = _errors(config)
        assert not any("kind" in e for e in errors)


class TestInfoTier:
    """Tests for the info severity tier on ValidationResult."""

    def test_validation_result_has_info_field(self):
        from operations.validate_config import ValidationResult
        r = ValidationResult()
        assert r.info == []

    def test_info_field_is_independent(self):
        from operations.validate_config import ValidationResult
        r = ValidationResult()
        r.info.append("note")
        r2 = ValidationResult()
        assert r2.info == []

    def test_validate_config_returns_info_when_add_warnings(self):
        """validate_config(add_warnings=True) result should carry info list."""
        from operations.validate_config import validate_config
        config = self._base_valid_config()
        result = validate_config(config, add_warnings=True)
        assert hasattr(result, "info")
        assert isinstance(result.info, list)

    @staticmethod
    def _base_valid_config() -> dict:
        return {
            "agents": ["claude"],
            "retention_period_for": {"claude_mem": "30d", "serena": "30d", "qdrant": "30d", "memory_mcp": "30d"},
            "cleanup": {"min_interval": "1h"},
            "trash": {"grace_period": "7d"},
            "path_to": {"workspace": "/tmp"},
            "startup_timeout_for": {"mcp_servers": 30, "docker_daemon": 30},
            "mcp": {"services": {}, "client_configs": {}},
        }
