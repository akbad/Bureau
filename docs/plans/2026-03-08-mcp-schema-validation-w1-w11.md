# MCP Schema Validation Fixes (W1–W11) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 11 weaknesses identified in `docs/mcp-schema-eval.md` by adding missing required-field checks, a third severity tier (`info`), auto-dependency inference, and tighter type/enum validation.

**Architecture:** All changes land in three files: `operations/mcp_validation_rules.py` (declarative constants), `operations/validate_config.py` (validation engine), and `operations/mcp_catalog.py` (resolution logic). The existing pattern — rules declare, engine consumes — is preserved. A new `info` field on `ValidationResult` carries advisory messages that are neither errors nor warnings.

**Tech Stack:** Python 3.12+, pytest, dataclasses. No new dependencies.

**Design doc:** `docs/schema-fix-plan.md` §"Design: MCP Schema Validation Fixes (W1–W11)"

---

## Conventions

**Files under edit:**
- Rules: `operations/mcp_validation_rules.py`
- Engine: `operations/validate_config.py`
- Catalog: `operations/mcp_catalog.py`
- Tests: `operations/tests/test_mcp_validation_rules.py`
- Tests: `operations/tests/test_validate_config.py`

**Test helpers already available:**
```python
def _errors(config: dict) -> list[str]:
    return validate_mcp_rules(config).errors

def _warnings(config: dict) -> list[str]:
    return validate_mcp_rules(config).warnings
```

**Config builder already available:**
```python
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
```

**Assertion patterns:**
- `assert _errors(cfg) == []` — no errors
- `assert any("keyword" in e for e in _errors(cfg))` — specific error present
- `assert len(_errors(cfg)) == N` — exact error count

**Run tests:**
```bash
uv run pytest operations/tests/test_mcp_validation_rules.py -v
uv run pytest operations/tests/test_validate_config.py -v
```

---

## Task 1: Add `info` tier to `ValidationResult`

This is the foundation for W6, W8, and any future advisory messages. Every subsequent task may emit info messages, so this goes first.

**Files:**
- Modify: `operations/validate_config.py` (lines 19–23 — `ValidationResult` dataclass)
- Modify: `operations/validate_config.py` (lines 750–777 — `main()` CLI)
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

Add a new test class `TestInfoTier` in `test_mcp_validation_rules.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestInfoTier -v`
Expected: FAIL — `ValidationResult` has no `info` attribute.

**Step 3: Implement**

In `operations/validate_config.py`, add `info` field to `ValidationResult`:

```python
@dataclass
class ValidationResult:
    """Validation output with errors (hard failures), warnings (soft), and info (advisory)."""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
```

In `validate_mcp_rules()`, merge info from sub-validators:

```python
def validate_mcp_rules(config: Mapping[str, Any]) -> ValidationResult:
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
```

In `validate_config()`, propagate info when returning `ValidationResult`:

```python
return ValidationResult(
    errors=errors,
    warnings=validation_result.warnings,
    info=validation_result.info,
) if add_warnings else errors
```

In `main()`, print info messages with a distinct prefix before warnings:

```python
if result.info:
    for i in result.info:
        print(f"  ℹ {i}", file=sys.stderr)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestInfoTier -v`
Expected: PASS

**Step 5: Run full test suite to check for regressions**

Run: `uv run pytest operations/tests/ -v`
Expected: All existing tests PASS. The new field has a default so nothing breaks.

**Step 6: Commit**

```bash
git add operations/validate_config.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): add info severity tier to ValidationResult (W1-W11 foundation)"
```

---

## Task 2: W1 — `kind` required for dependencies and services (error)

Currently `_validate_entry_schema()` only validates `kind` if it's present. Missing `kind` should be a hard error for buckets that require it (dependencies and services — not client_configs).

**Files:**
- Modify: `operations/validate_config.py` (lines 434–484 — `_validate_entry_schema()`)
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

Add to `test_mcp_validation_rules.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestKindRequired -v`
Expected: FAIL — first two tests fail because missing `kind` currently produces no error.

**Step 3: Implement**

In `_validate_entry_schema()`, after the unknown-keys check and before the kind-enum check, add:

```python
    # kind required → error (when kind_enum is provided, the bucket requires kind)
    if kind_enum is not None and "kind" not in entry:
        result.errors.append(f"{prefix}: missing required field 'kind'")
        return result  # no point checking kind-dependent rules without kind
```

Note the early return: without `kind`, per-kind required-field checks would be meaningless.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestKindRequired -v`
Expected: PASS

**Step 5: Check that the existing `test_missing_kind_produces_no_error` test needs updating**

The existing test `TestDependencyKindValidation::test_missing_kind_produces_no_error` asserts that missing kind produces NO error. This test must be updated or removed since it contradicts W1.

Update it to expect the error:

```python
def test_missing_kind_produces_error(self):
    config = {"mcp": {"dependencies": {
        "repo": {"enabled": True, "path": "/tmp/repo"},
    }}}
    errors = _errors(config)
    assert any("missing required field 'kind'" in e for e in errors)
```

**Step 6: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 7: Commit**

```bash
git add operations/validate_config.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): require kind field for dependencies and services (W1)"
```

---

## Task 3: W2 — `transport` required for client entries (error)

Currently missing `transport` is silently accepted. It should be a hard error.

**Files:**
- Modify: `operations/validate_config.py` (lines 536–639 — `_validate_mcp_client_configs()`)
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

```python
class TestTransportRequired:
    """W2: transport is required for client entries."""

    def test_client_missing_transport_produces_error(self):
        config = {"mcp": {"client_configs": {
            "svc": {"clients": {"default": {"url": "http://localhost"}}},
        }}}
        errors = _errors(config)
        assert any("missing required field 'transport'" in e for e in errors)

    def test_client_with_transport_is_fine(self):
        config = {"mcp": {"client_configs": {
            "svc": {"clients": {"default": {"transport": "http", "url": "http://localhost"}}},
        }}}
        errors = _errors(config)
        assert not any("transport" in e for e in errors)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestTransportRequired -v`
Expected: First test FAILS.

**Step 3: Implement**

In `_validate_mcp_client_configs()`, in the client entry loop (after the `isinstance(client_cfg, dict)` check, around line 613), add before the transport enum check:

```python
            # transport required → error
            transport = client_cfg.get("transport")
            if transport is None:
                result.errors.append(
                    f"{client_path}: missing required field 'transport'"
                )
                continue  # skip transport-dependent checks
```

Remove the existing `transport = client_cfg.get("transport")` line that follows (around line 623) since we now get it above.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestTransportRequired -v`
Expected: PASS

**Step 5: Check existing tests**

The existing `TestTransportEnumValidation::test_missing_transport_is_allowed` test asserts missing transport is OK. Update it:

```python
def test_missing_transport_produces_error(self):
    config = {"mcp": {"client_configs": {
        "svc": {"clients": {"default": {"url": "http://localhost"}}},
    }}}
    errors = _errors(config)
    assert any("missing required field 'transport'" in e for e in errors)
```

**Step 6: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 7: Commit**

```bash
git add operations/validate_config.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): require transport field for client entries (W2)"
```

---

## Task 4: W3 — `enabled` type check + W9 — `settings` type check

Both are simple additions to the type rule lists. Grouped because they're the same pattern.

**Files:**
- Modify: `operations/mcp_validation_rules.py`
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

```python
class TestEnabledTypeCheck:
    """W3: enabled must be bool if present."""

    def test_enabled_string_produces_error_dependency(self):
        config = {"mcp": {"dependencies": {
            "repo": {"kind": "file", "path": "/x", "enabled": "yes"},
        }}}
        assert any("enabled" in e and "bool" in e for e in _errors(config))

    def test_enabled_int_produces_error_service(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 1, "command": ["x"], "enabled": 42},
        }}}
        assert any("enabled" in e for e in _errors(config))

    def test_enabled_string_produces_error_client_config(self):
        config = {"mcp": {"client_configs": {
            "svc": {"enabled": "true", "clients": {"default": {"transport": "http", "url": "http://x"}}},
        }}}
        assert any("enabled" in e for e in _errors(config))

    def test_enabled_true_is_valid(self):
        config = {"mcp": {"dependencies": {
            "repo": {"kind": "file", "path": "/x", "enabled": True},
        }}}
        assert not any("enabled" in e for e in _errors(config))

    def test_enabled_missing_is_valid(self):
        config = {"mcp": {"dependencies": {
            "repo": {"kind": "file", "path": "/x"},
        }}}
        assert not any("enabled" in e for e in _errors(config))


class TestSettingsTypeCheck:
    """W9: settings must be dict if present."""

    def test_settings_string_produces_error_service(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 1, "command": ["x"], "settings": "bad"},
        }}}
        assert any("settings" in e for e in _errors(config))

    def test_settings_list_produces_error_client_config(self):
        config = {"mcp": {"client_configs": {
            "svc": {"settings": [1, 2], "clients": {"default": {"transport": "http", "url": "http://x"}}},
        }}}
        assert any("settings" in e for e in _errors(config))

    def test_settings_dict_is_valid(self):
        config = {"mcp": {"services": {
            "svc": {"kind": "http_process", "port": 1, "command": ["x"], "settings": {"collection": "test"}},
        }}}
        assert not any("settings" in e for e in _errors(config))
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestEnabledTypeCheck operations/tests/test_mcp_validation_rules.py::TestSettingsTypeCheck -v`
Expected: FAIL — `enabled` and `settings` have no type rules yet.

**Step 3: Implement**

In `operations/mcp_validation_rules.py`, add to each type rules list:

```python
DEPENDENCY_TYPE_RULES: list[tuple[str, str]] = [
    ("enabled", "bool"),          # W3: added
    ("post_clone", "list[list[str]]"),
]

SERVICE_TYPE_RULES: list[tuple[str, str]] = [
    ("enabled", "bool"),          # W3: added
    ("command", "list[str]"),
    ("port", "int"),
    ("host_port", "int"),
    ("container_port", "int"),
    ("env", "dict[str,str]"),
    ("mounts", "list[dict]"),
    ("healthcheck", "dict"),
    ("settings", "dict"),         # W9: added
]

CLIENT_CONFIG_TYPE_RULES: list[tuple[str, str]] = [
    ("enabled", "bool"),          # W3: added
    ("requires_env", "list[str]"),
    ("settings", "dict"),         # W9: added
]
```

Also need to add `"bool"` to `_OUTER_TYPES` in `validate_config.py` if not present. Check existing `_OUTER_TYPES`:

```python
_OUTER_TYPES = {"int": int, "dict": dict, "list": list, "str": str}
```

Add `"bool": bool` to support the `"bool"` type tag. But note: we also need to handle the fact that `bool` is a subclass of `int` — `_check_type` already guards `int` against bools, but we need to make sure `bool` type tag works correctly.

Add to `_check_type()` — the existing `_OUTER_TYPES` dict (around line 316):

```python
_OUTER_TYPES: dict[str, type] = {
    "bool": bool,
    "int": int,
    "dict": dict,
    "list": list,
    "str": str,
}
```

No special inner-type handling needed for `"bool"` — it's a scalar type.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestEnabledTypeCheck operations/tests/test_mcp_validation_rules.py::TestSettingsTypeCheck -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add operations/mcp_validation_rules.py operations/validate_config.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): add enabled (W3) and settings (W9) type checks"
```

---

## Task 5: W4 — Add `sse` transport

Add `sse` as a valid transport kind with the same required field as `http`.

**Files:**
- Modify: `operations/mcp_validation_rules.py`
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

```python
class TestSseTransport:
    """W4: sse is a valid transport."""

    def test_sse_transport_is_valid(self):
        config = {"mcp": {"client_configs": {
            "svc": {"clients": {"default": {"transport": "sse", "url": "http://localhost/sse"}}},
        }}}
        errors = _errors(config)
        assert not any("transport" in e for e in errors)

    def test_sse_requires_url(self):
        config = {"mcp": {"client_configs": {
            "svc": {"clients": {"default": {"transport": "sse"}}},
        }}}
        errors = _errors(config)
        assert any("url" in e and "sse" in e for e in errors)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestSseTransport -v`
Expected: First test FAILS — `sse` not in `CLIENT_TRANSPORT_KINDS`.

**Step 3: Implement**

In `operations/mcp_validation_rules.py`:

```python
CLIENT_TRANSPORT_KINDS: set[str] = {"http", "sse", "stdio"}

CLIENT_TRANSPORT_REQUIRED: dict[str, set[str]] = {
    "http": {"url"},
    "sse": {"url"},
    "stdio": {"command"},
}
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestSseTransport -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add operations/mcp_validation_rules.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): add sse transport support (W4)"
```

---

## Task 6: W10 — Mount path value type validation

After checking that `host_path` and `container_path` keys exist, validate they are strings. Skip `${...}` placeholders.

**Files:**
- Modify: `operations/validate_config.py` (lines 391–408 — `_validate_mounts()`)
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

```python
class TestMountPathValueTypes:
    """W10: mount path values must be strings."""

    def test_host_path_int_produces_error(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": 5432,
                   "mounts": [{"host_path": 123, "container_path": "/data"}]},
        }}}
        errors = _errors(config)
        assert any("host_path" in e and "string" in e for e in errors)

    def test_container_path_int_produces_error(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": 5432,
                   "mounts": [{"host_path": "/host", "container_path": 42}]},
        }}}
        errors = _errors(config)
        assert any("container_path" in e and "string" in e for e in errors)

    def test_placeholder_paths_skip_type_check(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": 5432,
                   "mounts": [{"host_path": "${path_to.data}", "container_path": "/data"}]},
        }}}
        errors = _errors(config)
        assert not any("host_path" in e for e in errors)

    def test_string_paths_are_valid(self):
        config = {"mcp": {"services": {
            "db": {"kind": "docker_container", "image": "pg",
                   "host_port": 5432, "container_port": 5432,
                   "mounts": [{"host_path": "/host/data", "container_path": "/data"}]},
        }}}
        errors = _errors(config)
        assert not any("host_path" in e or "container_path" in e for e in errors)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestMountPathValueTypes -v`
Expected: First two tests FAIL — no value type checking for mount paths yet.

**Step 3: Implement**

In `_validate_mounts()`, after the required-key check loop, add value type checks:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestMountPathValueTypes -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add operations/validate_config.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): validate mount path value types (W10)"
```

---

## Task 7: W8 — Missing `clients.default` info message

Emit an `info` message when a `client_configs` entry has clients but no `default` key.

**Files:**
- Modify: `operations/validate_config.py` (lines 536–639 — `_validate_mcp_client_configs()`)
- Test: `operations/tests/test_mcp_validation_rules.py`

**Step 1: Write the failing tests**

We need a helper for info messages. Add alongside existing `_errors`/`_warnings`:

```python
def _info(config: dict) -> list[str]:
    """Shortcut: extract only info from validate_mcp_rules."""
    return validate_mcp_rules(config).info
```

Then add tests:

```python
class TestMissingDefaultClient:
    """W8: info message when clients.default is absent."""

    def test_no_default_client_produces_info(self):
        config = {"mcp": {"client_configs": {
            "svc": {"clients": {"claude": {"transport": "http", "url": "http://localhost"}}},
        }}}
        info = _info(config)
        assert any("no clients.default" in i for i in info)
        assert any("svc" in i for i in info)

    def test_default_client_present_no_info(self):
        config = {"mcp": {"client_configs": {
            "svc": {"clients": {"default": {"transport": "http", "url": "http://localhost"}}},
        }}}
        info = _info(config)
        assert not any("clients.default" in i for i in info)

    def test_no_clients_key_no_info(self):
        """No clients dict at all — different error, not this info message."""
        config = {"mcp": {"client_configs": {
            "svc": {"enabled": True},
        }}}
        info = _info(config)
        assert not any("clients.default" in i for i in info)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestMissingDefaultClient -v`
Expected: First test FAILS — no info message emitted.

**Step 3: Implement**

In `_validate_mcp_client_configs()`, after the `actual_clients` check (around line 602), add:

```python
        # W8: info when clients.default is absent
        if actual_clients and "default" not in clients:
            result.info.append(
                f"mcp.client_configs.{name} has no clients.default — "
                f"agents without a specific override will skip this server"
            )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestMissingDefaultClient -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add operations/validate_config.py operations/tests/test_mcp_validation_rules.py
git commit -m "feat(validation): info message for missing clients.default (W8)"
```

---

## Task 8: W11 — Dependency ordering with `requires`

Dependencies can now declare ordering constraints via a `requires` list. Resolution changes from dict-order iteration to topological sort.

This is a multi-part task because it touches rules, validation, AND resolution.

**Files:**
- Modify: `operations/mcp_validation_rules.py`
- Modify: `operations/validate_config.py`
- Modify: `operations/mcp_catalog.py` (lines 78–85 — dependency resolution)
- Test: `operations/tests/test_mcp_validation_rules.py`
- Test: `operations/tests/test_validate_config.py`

### Part A: Schema rules

**Step 1: Write the failing tests**

```python
class TestDependencyRequires:
    """W11: dependencies can declare requires for ordering."""

    def test_requires_is_allowed_key(self):
        config = {"mcp": {"dependencies": {
            "overlay": {"kind": "git_repo", "repo_url": "https://x.git",
                        "path": "/x", "requires": ["base"]},
        }}}
        warnings = _warnings(config)
        assert not any("requires" in w and "unknown" in w for w in warnings)

    def test_requires_non_list_produces_error(self):
        config = {"mcp": {"dependencies": {
            "overlay": {"kind": "git_repo", "repo_url": "https://x.git",
                        "path": "/x", "requires": "base"},
        }}}
        errors = _errors(config)
        assert any("requires" in e for e in errors)

    def test_requires_non_string_element_produces_error(self):
        config = {"mcp": {"dependencies": {
            "overlay": {"kind": "git_repo", "repo_url": "https://x.git",
                        "path": "/x", "requires": [123]},
        }}}
        errors = _errors(config)
        assert any("requires" in e for e in errors)

    def test_requires_unknown_dep_produces_warning(self):
        config = {"mcp": {"dependencies": {
            "overlay": {"kind": "git_repo", "repo_url": "https://x.git",
                        "path": "/x", "requires": ["nonexistent"]},
        }}}
        warnings = _warnings(config)
        assert any("nonexistent" in w for w in warnings)

    def test_requires_valid_dep_no_warning(self):
        config = {"mcp": {"dependencies": {
            "base": {"kind": "git_repo", "repo_url": "https://x.git", "path": "/x"},
            "overlay": {"kind": "git_repo", "repo_url": "https://y.git",
                        "path": "/y", "requires": ["base"]},
        }}}
        warnings = _warnings(config)
        assert not any("does not match" in w for w in warnings)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestDependencyRequires -v`
Expected: FAIL — `requires` is unknown key, type rules don't exist.

**Step 3: Implement schema rules**

In `operations/mcp_validation_rules.py`:

```python
DEPENDENCY_ALLOWED_KEYS: set[str] = {
    "enabled", "kind", "repo_url", "branch", "path", "post_clone", "requires",
}

DEPENDENCY_TYPE_RULES: list[tuple[str, str]] = [
    ("enabled", "bool"),
    ("post_clone", "list[list[str]]"),
    ("requires", "list[str]"),
]
```

**Step 4: Implement cross-reference validation for dependency requires**

In `_validate_cross_references()`, after the existing loops, add:

```python
    # check requires in dependencies
    for name, dep in mcp.get("dependencies", {}).items():
        if not isinstance(dep, dict):
            continue
        requires = dep.get("requires", [])
        if not isinstance(requires, list):
            continue
        for ref in requires:
            if isinstance(ref, str) and ref not in declared_deps:
                result.warnings.append(
                    f"mcp.dependencies.{name}.requires: "
                    f"'{ref}' does not match any declared dependency"
                )
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestDependencyRequires -v`
Expected: PASS

### Part B: Cycle detection

**Step 6: Write the failing tests for dependency requires cycles**

Add to `test_validate_config.py`:

```python
class TestDependencyRequiresCycleDetection:
    """W11: detect cycles in dependency requires."""

    def test_self_reference_produces_error(self):
        config = {"mcp": {"dependencies": {
            "a": {"kind": "file", "path": "/x", "requires": ["a"]},
        }}}
        from operations.validate_config import validate_dependency_requires_cycles
        errors = validate_dependency_requires_cycles(config)
        assert len(errors) == 1

    def test_mutual_cycle_produces_error(self):
        config = {"mcp": {"dependencies": {
            "a": {"kind": "file", "path": "/x", "requires": ["b"]},
            "b": {"kind": "file", "path": "/y", "requires": ["a"]},
        }}}
        from operations.validate_config import validate_dependency_requires_cycles
        errors = validate_dependency_requires_cycles(config)
        assert len(errors) >= 1

    def test_no_cycle_is_fine(self):
        config = {"mcp": {"dependencies": {
            "base": {"kind": "file", "path": "/x"},
            "overlay": {"kind": "file", "path": "/y", "requires": ["base"]},
        }}}
        from operations.validate_config import validate_dependency_requires_cycles
        errors = validate_dependency_requires_cycles(config)
        assert errors == []
```

**Step 7: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_validate_config.py::TestDependencyRequiresCycleDetection -v`
Expected: FAIL — `validate_dependency_requires_cycles` doesn't exist.

**Step 8: Implement cycle detection**

In `operations/validate_config.py`, add (following the pattern of `_collect_service_dep_graph` / `validate_service_dependency_cycles`):

```python
def _collect_dependency_requires_graph(config: Mapping[str, Any]) -> dict[str, set[str]]:
    """Build adjacency list from mcp.dependencies.*.requires."""
    graph: dict[str, set[str]] = {}
    deps = config.get("mcp", {}).get("dependencies", {})
    for name, dep in deps.items():
        if not isinstance(dep, dict):
            continue
        requires = dep.get("requires", [])
        if isinstance(requires, list):
            graph[name] = {r for r in requires if isinstance(r, str)}
        else:
            graph[name] = set()
    return graph


def validate_dependency_requires_cycles(config: Mapping[str, Any]) -> list[str]:
    """Validate that dependency requires don't form cycles."""
    graph = _collect_dependency_requires_graph(config)
    return _find_graph_cycles(graph)
```

Wire into `validate_config()`, right after `validate_service_dependency_cycles`:

```python
    errors.extend(validate_dependency_requires_cycles(config))
```

**Step 9: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_validate_config.py::TestDependencyRequiresCycleDetection -v`
Expected: PASS

### Part C: Topological sort in resolution

**Step 10: Write the failing test for ordering**

Create `operations/tests/test_mcp_catalog.py` (or add to existing):

```python
from operations.mcp_catalog import resolve_mcp_catalog


class TestDependencyRequiresOrdering:
    """W11: dependencies resolve in topological order based on requires."""

    def test_requires_ordering(self):
        """overlay requires base — base must resolve first."""
        config = {
            "mcp": {
                "dependencies": {
                    "overlay": {"kind": "file", "path": "/y", "requires": ["base"], "enabled": True},
                    "base": {"kind": "file", "path": "/x", "enabled": True},
                },
                "services": {},
                "client_configs": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        dep_names = list(result["dependencies"].keys())
        assert dep_names.index("base") < dep_names.index("overlay")

    def test_requires_missing_dep_skips(self):
        """If a required dep is disabled, the requiring dep is skipped."""
        config = {
            "mcp": {
                "dependencies": {
                    "base": {"kind": "file", "path": "/x", "enabled": False},
                    "overlay": {"kind": "file", "path": "/y", "requires": ["base"], "enabled": True},
                },
                "services": {},
                "client_configs": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "overlay" not in result["dependencies"]
        assert "base" not in result["dependencies"]
```

**Step 11: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_catalog.py::TestDependencyRequiresOrdering -v`
Expected: FAIL — current resolution uses dict-order, doesn't check `requires`.

**Step 12: Implement topological sort for dependencies**

In `operations/mcp_catalog.py`, replace the simple dependency iteration (lines 78–85) with a topological sort matching the existing service pattern:

```python
    # --- dependencies (topological sort by requires) ---
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
```

**Step 13: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_catalog.py::TestDependencyRequiresOrdering -v`
Expected: PASS

**Step 14: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 15: Commit**

```bash
git add operations/mcp_validation_rules.py operations/validate_config.py operations/mcp_catalog.py operations/tests/test_mcp_validation_rules.py operations/tests/test_validate_config.py operations/tests/test_mcp_catalog.py
git commit -m "feat(validation): add dependency ordering with requires and cycle detection (W11)"
```

---

## Task 9: W6 — Auto-detect dependencies from placeholders

This is the most complex task. A new function infers dependencies by scanning `${mcp.<bucket>.<name>.<field>}` references in entry values, then merges them with any explicit `depends_on`/`requires` during both validation (info messages) and resolution (enablement gating).

**Files:**
- Modify: `operations/validate_config.py`
- Modify: `operations/mcp_catalog.py`
- Test: `operations/tests/test_mcp_validation_rules.py`
- Test: `operations/tests/test_mcp_catalog.py`

### Part A: Inference function

**Step 1: Write the failing tests**

```python
class TestInferRequires:
    """W6: auto-detect dependencies from placeholder references."""

    def test_infer_service_dep_from_placeholder(self):
        from operations.validate_config import _infer_requires
        entry = {"clients": {"default": {"url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/"}}}
        result = _infer_requires("qdrant", "client_configs", entry)
        assert "qdrant_mcp" in result["services"]

    def test_infer_dependency_dep_from_placeholder(self):
        from operations.validate_config import _infer_requires
        entry = {"command": ["--repo", "${mcp.dependencies.my_repo.path}"]}
        result = _infer_requires("svc", "services", entry)
        assert "my_repo" in result["dependencies"]

    def test_no_self_reference(self):
        from operations.validate_config import _infer_requires
        entry = {"url": "http://localhost:${mcp.services.self_svc.port}"}
        result = _infer_requires("self_svc", "services", entry)
        assert "self_svc" not in result["services"]

    def test_no_placeholder_returns_empty(self):
        from operations.validate_config import _infer_requires
        entry = {"url": "http://localhost:8080"}
        result = _infer_requires("svc", "client_configs", entry)
        assert result == {"services": [], "dependencies": []}

    def test_multiple_refs_deduplicated(self):
        from operations.validate_config import _infer_requires
        entry = {
            "url": "http://${mcp.services.a.host}:${mcp.services.a.port}",
            "extra": "${mcp.services.b.port}",
        }
        result = _infer_requires("svc", "client_configs", entry)
        assert sorted(result["services"]) == ["a", "b"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestInferRequires -v`
Expected: FAIL — `_infer_requires` doesn't exist.

**Step 3: Implement the inference function**

In `operations/validate_config.py`:

```python
# Regex to extract bucket and name from MCP placeholder references.
# Matches: ${mcp.<bucket>.<name>.<field>} where bucket is services/dependencies/client_configs
_MCP_REF_REGEX = re.compile(
    r"\$\{mcp\.(services|dependencies|client_configs)\.([^.}]+)\.[^}]+\}"
)


def _infer_requires(
    entry_name: str, entry_bucket: str, entry_data: Any,
) -> dict[str, list[str]]:
    """Infer dependencies from ${mcp.<bucket>.<name>.<field>} placeholders.

    Walks all string values recursively, extracts references, filters out
    self-references, and returns deduplicated lists.
    """
    refs: dict[str, set[str]] = {"services": set(), "dependencies": set()}
    _collect_mcp_refs(entry_data, refs)

    # filter self-references
    if entry_bucket in ("services",) and entry_name in refs["services"]:
        refs["services"].discard(entry_name)
    if entry_bucket in ("dependencies",) and entry_name in refs["dependencies"]:
        refs["dependencies"].discard(entry_name)

    return {k: sorted(v) for k, v in refs.items()}


def _collect_mcp_refs(node: Any, refs: dict[str, set[str]]) -> None:
    """Recursively collect ${mcp.<bucket>.<name>} references from values."""
    if isinstance(node, str):
        for match in _MCP_REF_REGEX.finditer(node):
            bucket, name = match.group(1), match.group(2)
            if bucket in refs:
                refs[bucket].add(name)
    elif isinstance(node, list):
        for item in node:
            _collect_mcp_refs(item, refs)
    elif isinstance(node, dict):
        for value in node.values():
            _collect_mcp_refs(value, refs)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestInferRequires -v`
Expected: PASS

### Part B: Validation integration (info messages)

**Step 5: Write the failing tests**

```python
class TestAutoDetectedDependencyInfo:
    """W6: info messages for auto-detected dependencies."""

    def test_auto_detected_service_dep_produces_info(self):
        config = {"mcp": {
            "services": {"qdrant_mcp": {"kind": "docker_container", "image": "qdrant",
                         "host_port": 6333, "container_port": 6333}},
            "client_configs": {
                "qdrant": {"clients": {"default": {
                    "transport": "http",
                    "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                }}},
            },
        }}
        info = _info(config)
        assert any("qdrant" in i and "qdrant_mcp" in i and "auto" in i.lower() for i in info)

    def test_explicit_dep_no_duplicate_info(self):
        """If depends_on already declares the dep, no info message needed."""
        config = {"mcp": {
            "services": {"qdrant_mcp": {"kind": "docker_container", "image": "qdrant",
                         "host_port": 6333, "container_port": 6333}},
            "client_configs": {
                "qdrant": {
                    "depends_on": {"services": ["qdrant_mcp"]},
                    "clients": {"default": {
                        "transport": "http",
                        "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                    }},
                },
            },
        }}
        info = _info(config)
        assert not any("auto" in i.lower() and "qdrant_mcp" in i for i in info)
```

**Step 6: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestAutoDetectedDependencyInfo -v`
Expected: FAIL — no auto-detection info messages.

**Step 7: Implement validation integration**

In `_validate_cross_references()`, after the existing cross-reference checks, add auto-detection info for services and client_configs:

```python
    # W6: auto-detect dependencies from placeholders → info messages
    for name, entry in mcp.get("services", {}).items():
        if not isinstance(entry, dict):
            continue
        inferred = _infer_requires(name, "services", entry)
        explicit_deps = set()
        depends_on = entry.get("depends_on", {})
        if isinstance(depends_on, dict):
            explicit_deps.update(_as_list(depends_on.get("dependencies", [])))
        for ref in inferred["dependencies"]:
            if ref not in explicit_deps:
                result.info.append(
                    f"mcp.services.{name} auto-depends on dependencies.{ref} (via placeholder)"
                )

    for name, entry in mcp.get("client_configs", {}).items():
        if not isinstance(entry, dict):
            continue
        inferred = _infer_requires(name, "client_configs", entry)
        explicit_svcs = set()
        explicit_deps = set()
        depends_on = entry.get("depends_on", {})
        if isinstance(depends_on, dict):
            explicit_svcs.update(_as_list(depends_on.get("services", [])))
            explicit_deps.update(_as_list(depends_on.get("dependencies", [])))
        for ref in inferred["services"]:
            if ref not in explicit_svcs:
                result.info.append(
                    f"mcp.client_configs.{name} auto-depends on services.{ref} (via placeholder)"
                )
        for ref in inferred["dependencies"]:
            if ref not in explicit_deps:
                result.info.append(
                    f"mcp.client_configs.{name} auto-depends on dependencies.{ref} (via placeholder)"
                )
```

**Step 8: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestAutoDetectedDependencyInfo -v`
Expected: PASS

### Part C: Resolution integration

**Step 9: Write the failing tests**

Add to `operations/tests/test_mcp_catalog.py`:

```python
class TestAutoDetectedDependencyResolution:
    """W6: auto-detected deps affect enablement gating in resolution."""

    def test_client_config_skipped_when_inferred_service_disabled(self):
        """If qdrant client_config references qdrant_mcp service via placeholder,
        and qdrant_mcp is disabled, qdrant should be skipped even without explicit depends_on."""
        config = {
            "mcp": {
                "services": {
                    "qdrant_mcp": {"kind": "docker_container", "image": "qdrant",
                                   "host_port": 6333, "container_port": 6333,
                                   "enabled": False},
                },
                "client_configs": {
                    "qdrant": {"clients": {"default": {
                        "transport": "http",
                        "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                    }}},
                },
                "dependencies": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "qdrant" not in result["client_configs"]

    def test_client_config_kept_when_inferred_service_enabled(self):
        config = {
            "mcp": {
                "services": {
                    "qdrant_mcp": {"kind": "docker_container", "image": "qdrant",
                                   "host_port": 6333, "container_port": 6333},
                },
                "client_configs": {
                    "qdrant": {"clients": {"default": {
                        "transport": "http",
                        "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                    }}},
                },
                "dependencies": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "qdrant" in result["client_configs"]

    def test_explicit_depends_on_unions_with_inferred(self):
        """Explicit depends_on adds to inferred, never subtracts."""
        config = {
            "mcp": {
                "services": {
                    "svc_a": {"kind": "http_process", "port": 1, "command": ["x"]},
                    "svc_b": {"kind": "http_process", "port": 2, "command": ["y"],
                              "enabled": False},
                },
                "client_configs": {
                    "client": {
                        "depends_on": {"services": ["svc_b"]},
                        "clients": {"default": {
                            "transport": "http",
                            "url": "http://localhost:${mcp.services.svc_a.port}/",
                        }},
                    },
                },
                "dependencies": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        # svc_b disabled → explicit dep fails → client skipped
        assert "client" not in result["client_configs"]
```

**Step 10: Run tests to verify they fail**

Run: `uv run pytest operations/tests/test_mcp_catalog.py::TestAutoDetectedDependencyResolution -v`
Expected: First and third tests FAIL — resolution doesn't consider inferred deps.

**Step 11: Implement resolution integration**

In `operations/mcp_catalog.py`, import the inference function:

```python
from .validate_config import _infer_requires
```

In the client_configs resolution loop, after getting the `depends_on` dict, merge auto-inferred deps:

```python
        # W6: merge auto-inferred dependencies from placeholders
        inferred = _infer_requires(name, "client_configs", entry)

        depends_on = entry.get("depends_on", {})
        if not isinstance(depends_on, dict):
            depends_on = {}

        # Union explicit + inferred service deps
        service_deps = depends_on.get("services", [])
        if not isinstance(service_deps, list):
            service_deps = [service_deps]
        service_deps = list(set(service_deps) | set(inferred["services"]))

        # Union explicit + inferred dependency deps
        dep_deps = depends_on.get("dependencies", [])
        if not isinstance(dep_deps, list):
            dep_deps = [dep_deps]
        dep_deps = list(set(dep_deps) | set(inferred["dependencies"]))

        if any(dep not in enabled_services for dep in service_deps):
            continue
        if any(dep not in enabled_dependencies for dep in dep_deps):
            continue
```

Apply the same pattern in the services resolution candidate filtering — services can reference dependencies via placeholders:

```python
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
```

**Step 12: Run tests to verify they pass**

Run: `uv run pytest operations/tests/test_mcp_catalog.py -v`
Expected: PASS

**Step 13: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 14: Commit**

```bash
git add operations/validate_config.py operations/mcp_catalog.py operations/tests/test_mcp_validation_rules.py operations/tests/test_mcp_catalog.py
git commit -m "feat(validation): auto-detect dependencies from placeholders (W6)"
```

---

## Task 10: Final integration test and docs update

Verify all W items work together with a realistic config and update the design doc.

**Files:**
- Modify: `operations/tests/test_mcp_validation_rules.py`
- Modify: `docs/schema-fix-plan.md`

**Step 1: Write integration test**

```python
class TestW1W11Integration:
    """Integration: all W1-W11 fixes work together on a realistic config."""

    def test_realistic_config_with_all_fixes(self):
        config = {
            "agents": ["claude", "codex"],
            "retention_period_for": {"claude_mem": "30d", "serena": "30d", "qdrant": "30d", "memory_mcp": "30d"},
            "cleanup": {"min_interval": "1h"},
            "trash": {"grace_period": "7d"},
            "path_to": {"workspace": "/tmp"},
            "startup_timeout_for": {"mcp_servers": 30, "docker_daemon": 30},
            "mcp": {
                "dependencies": {
                    "base_repo": {"kind": "git_repo", "repo_url": "https://example.com/base.git",
                                  "path": "/tmp/base", "enabled": True},
                    "overlay": {"kind": "git_repo", "repo_url": "https://example.com/overlay.git",
                                "path": "/tmp/overlay", "requires": ["base_repo"]},
                },
                "services": {
                    "qdrant_mcp": {
                        "kind": "docker_container",
                        "image": "qdrant/qdrant",
                        "host_port": 6333,
                        "container_port": 6333,
                        "mounts": [{"host_path": "/data/qdrant", "container_path": "/qdrant/storage"}],
                        "healthcheck": {"tcp": 6333},
                        "settings": {"collection": "test"},
                        "enabled": True,
                    },
                },
                "client_configs": {
                    "qdrant": {
                        "enabled": True,
                        "settings": {"collection": "bureau"},
                        "clients": {
                            "default": {
                                "transport": "http",
                                "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                            },
                        },
                    },
                    "sse_server": {
                        "clients": {
                            "claude": {
                                "transport": "sse",
                                "url": "http://localhost:9000/sse",
                            },
                        },
                    },
                },
            },
        }
        from operations.validate_config import validate_config
        result = validate_config(config, add_warnings=True)
        assert result.errors == [], f"Unexpected errors: {result.errors}"

        # W6: qdrant auto-detected dep on qdrant_mcp
        assert any("auto-depends" in i and "qdrant_mcp" in i for i in result.info)

        # W8: sse_server has no clients.default
        assert any("no clients.default" in i and "sse_server" in i for i in result.info)

    def test_all_error_conditions(self):
        """Config with every error type produces the right errors."""
        config = {
            "agents": ["claude"],
            "retention_period_for": {"claude_mem": "30d", "serena": "30d", "qdrant": "30d", "memory_mcp": "30d"},
            "cleanup": {"min_interval": "1h"},
            "trash": {"grace_period": "7d"},
            "path_to": {"workspace": "/tmp"},
            "startup_timeout_for": {"mcp_servers": 30, "docker_daemon": 30},
            "mcp": {
                "dependencies": {
                    "no_kind": {"path": "/x"},                         # W1: missing kind
                },
                "services": {
                    "bad_svc": {"kind": "http_process", "port": 1,
                                "command": ["x"], "enabled": "yes"},   # W3: bad enabled type
                },
                "client_configs": {
                    "no_transport": {
                        "clients": {"default": {"url": "http://x"}},   # W2: missing transport
                        "settings": [1, 2],                            # W9: bad settings type
                    },
                },
            },
        }
        from operations.validate_config import validate_config
        result = validate_config(config, add_warnings=True)
        errors = result.errors
        # W1
        assert any("missing required field 'kind'" in e for e in errors)
        # W2
        assert any("missing required field 'transport'" in e for e in errors)
        # W3
        assert any("enabled" in e for e in errors)
        # W9
        assert any("settings" in e for e in errors)
```

**Step 2: Run tests**

Run: `uv run pytest operations/tests/test_mcp_validation_rules.py::TestW1W11Integration -v`
Expected: PASS (all prior tasks implemented correctly).

**Step 3: Run full test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All PASS.

**Step 4: Update design doc**

In `docs/schema-fix-plan.md`, add implementation status markers to the W1–W11 design section. Update each subsection header:

- `### W1: \`kind\` required (error)` → `### W1: \`kind\` required (error) ✅`
- `### W2: \`transport\` required (error)` → `### W2: \`transport\` required (error) ✅`
- `### W3: \`enabled\` type check` → `### W3: \`enabled\` type check ✅`
- `### W4: \`sse\` transport` → `### W4: \`sse\` transport ✅`
- `### W5: Already fixed` — already done, no change
- `### W6: Auto-detect dependencies from placeholders (hybrid)` → `### W6: Auto-detect dependencies from placeholders (hybrid) ✅`
- `### W7: Skip (by design)` — already done, no change
- `### W8: Missing \`clients.default\` log (info)` → `### W8: Missing \`clients.default\` log (info) ✅`
- `### W9: \`settings\` type check` → `### W9: \`settings\` type check ✅`
- `### W10: Mount path value types` → `### W10: Mount path value types ✅`
- `### W11: Dependency ordering` → `### W11: Dependency ordering ✅`

**Step 5: Commit**

```bash
git add operations/tests/test_mcp_validation_rules.py docs/schema-fix-plan.md
git commit -m "feat(validation): integration tests and mark W1-W11 complete"
```

---

## Summary

| Task | Scope | Items | Estimated Tests |
|------|-------|-------|-----------------|
| 1 | `info` tier foundation | — | 3 |
| 2 | `kind` required | W1 | 3 + 1 update |
| 3 | `transport` required | W2 | 2 + 1 update |
| 4 | `enabled` + `settings` type checks | W3, W9 | 8 |
| 5 | `sse` transport | W4 | 2 |
| 6 | Mount path types | W10 | 4 |
| 7 | Missing `clients.default` info | W8 | 3 |
| 8 | Dependency `requires` + ordering | W11 | 8 + topo sort |
| 9 | Auto-detect deps from placeholders | W6 | 10 + resolution |
| 10 | Integration tests + doc update | all | 2 |
| **Total** | | **W1–W11** | **~46 new tests** |

Items not requiring implementation work: **W5** (already fixed), **W7** (skip by design).
