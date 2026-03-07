# Schema Fix Plan

## High Priority (Breaking/Silent Failures)

### 1. Runtime service dependency enforcement ✅
Add enforcement for `mcp.runtime_services.<service>.depends_on.services` during catalog resolution so services depending on disabled or missing services are skipped before `service-order.py` runs. Current behavior only checks dependency IDs, which can cause ordering to fail at runtime.

**Additionally:** Add cycle detection for service dependencies to prevent infinite loops/deadlocks. A service depending on itself (directly or transitively) would cause startup to hang. Implement using DFS-based cycle detection similar to `validate_placeholder_cycles()`.

**Example problem case:**
```yaml
mcp:
  runtime_services:
    service_a:
      depends_on:
        services: [service_b]
    service_b:x
      depends_on:
        services: [service_a]  # Circular dependency!
```

**Implementation:** Add `validate_service_dependency_cycles()` function in `operations/validate_config.py` and call from `full_validate()`.

---

### 5. ✅ MCP schema validation depth
`operations/validate_config.py` only checks that `mcp.runtime_services` and `mcp.client_configs` exist, not that entries contain required keys or valid values. Add deeper validation for MCP entries (kinds, required fields, and types) to fail fast on misconfiguration.

**Specific validation gaps to address:**

#### 5.1 ✅ Kind enum validation
Validate that `kind` fields contain only allowed values:
- `mcp.dependencies.<id>.kind`: Must be `git_repo` or `file`
- `mcp.runtime_services.<id>.kind`: Must be `docker_container` or `http_process`

**Problem:** Typos like `kind: http_server` (instead of `http_process`) silently fail later during resolution.

#### 5.2 ✅ Required field validation per kind
Each `kind` has mandatory fields that should be validated:

**For `runtime_services`:**
- `docker_container` requires: `image`, `host_port`, `container_port`
- `http_process` requires: `port`, `command`

**For `dependencies`:**
- `git_repo` requires: `repo_url`, `path`
- `file` requires: `path`

**For `client_configs`:**
- All entries require: `clients` dict with at least one client
- `http` transport clients require: `url`
- `stdio` transport clients require: `command`

**Problem:** Missing required fields cause cryptic errors during setup rather than clear validation failures.

#### 5.3 ✅ Field typo detection
Common typos that should be caught:
- `enabeld` instead of `enabled`
- `depends_on.servies` instead of `depends_on.services`
- `commmand` instead of `command`

**Resolution:** All three sub-issues (5.1-5.3) were implemented in `mcp_validation_rules.py` (declarative schema constants) and `validate_config.py` (generic `_validate_entry_schema()` engine). Additionally, the following deeper validation was added:

- **Field type validation**: Declarative `(field, type_tag)` rules in `mcp_validation_rules.py` consumed by `_check_type()` / `_validate_field_types()` in `validate_config.py`. Catches misconfigurations like `command: "uvx run server"` (should be a list) or `port: "8080"` (should be an int). Skips placeholder-bearing values (`${...}`) to avoid false positives on fields that resolve after expansion.
- **Transport enum validation**: `transport` values checked against `CLIENT_TRANSPORT_KINDS` (`http`, `stdio`). Unknown transports produce errors.
- **Sub-structure validation**: `mounts` entries checked for required `host_path`/`container_path` keys. `healthcheck` blocks checked against `HEALTHCHECK_ALLOWED_KEYS`. Unknown sub-keys produce warnings.
- **Cross-reference validation**: `depends_on.services` and `depends_on.dependencies` names verified against declared entries. Mismatches produce warnings (not errors) to handle conditional config layers.
- **Test coverage**: 76 tests in `test_mcp_validation_rules.py` (38 new across 5 test classes: `TestFieldTypeValidation`, `TestMountSubStructure`, `TestHealthcheckSubStructure`, `TestTransportEnumValidation`, `TestCrossReferenceValidation`).

---

## Medium Priority (UX/Clarity)

### 2. ✅ Per-CLI disable semantics
`render-mcp-setup.py` always falls back to `clients.default`, so you cannot disable a server for a specific CLI while keeping it for others. Add an explicit per-CLI disable flag (for example `clients.<cli>.enabled: false`) or a `clients.<cli>: null` convention and update render logic accordingly.

**Resolution:** Added `clients.disabled_for` list setting. Agents in this list are excluded from the server, even if a `clients.<cli>` override exists. Validated against top-level `agents` list (warnings for unknown agents). Updated `mcp_validation_rules.py`, `mcp_catalog.py`, `render-mcp-setup.py`, `validate_config.py`, and `CONFIGURATION.md`.

---

### 6. ✅ Naming inconsistencies

#### 6.1 ✅ Confusing term: `auto_approved.mcps`
The setting `auto_approved.mcps` controls whether **MCP tool calls** are auto-approved, but elsewhere `mcp.*` refers to **MCP servers/infrastructure**. This terminology clash causes confusion.

**Current:**
```yaml
auto_approved:
  mcps: false      # Approval for MCP TOOL CALLS

mcp:
  client_configs:  # Configuration for MCP SERVERS
    qdrant: ...
```

**Recommendation:** Rename to `auto_approved.mcp_tools` or `auto_approved.mcp_tool_calls` for clarity.

#### 6.2 ✅ Redundant prefix: `auto_clean_managed_mcps`
The name contains redundant qualifiers. The registry already tracks "managed" MCPs, and "auto" is implicit in a boolean flag.

**Current:** `auto_clean_managed_mcps: true`
**Clearer alternatives:** `clean_removed_mcps` or `prune_disabled_mcps`

**Impact:** Low risk but affects config readability. Consider for next major version or document clearly.

**Resolution:** Clean-break rename (no backward compat) across all config, code, tests, and docs:
- `auto_approved.mcps` → `auto_approved.mcp_tools` — clarifies that this controls tool call approval, not server infrastructure
- `auto_clean_managed_mcps` → `prune_disabled_mcps` — drops redundant "auto" (implicit) and "managed" (implementation detail)

---

### 7. ✅ Default `enabled: true` behavior undocumented
The implementation uses `dep.get("enabled", True)` throughout `mcp_catalog.py`, meaning services/dependencies are **enabled by default** if the key is omitted. This is not documented in CONFIGURATION.md schema reference.

**Problem:** Users may be surprised when adding a service definition without `enabled: false` causes it to start immediately on next `open-bureau` run.

**Fix:** Update CONFIGURATION.md schema reference to explicitly state:
```markdown
- `enabled` (bool, default: `true`): Skip service if `false`.
  **Note:** Services and dependencies are enabled by default.
```

**Resolution:** The schema reference (added in Issue #5) already documented `enabled (bool, default: true)` for all three buckets, but the default-true behavior wasn't called out prominently. Added an explicit "Enabled by default" callout note in the schema reference Notes section. Also removed redundant `enabled: true` from examples, which obscured the default rather than clarifying it.

---

### 8. ✅ Missing placeholder escaping mechanism
Users have no way to include a literal `${...}` string in configuration values if they need it for shell commands or other purposes. The placeholder expansion is always applied.

**Problem case:**
```yaml
mcp:
  runtime_services:
    my_service:
      command:
        - sh
        - -c
        - "echo ${VARIABLE}"  # Expanded by Bureau, not by shell!
```

**Recommendation:** Document that `${...}` is always expanded by Bureau before passing to commands. If literal expansion needed, use environment variables or document workarounds.

**Resolution:** No escape hatch needed. Bureau doesn't launch shell commands directly — it writes resolved values into CLI config files. Users who want env vars forwarded to MCP servers should use the `env` block in their client config (e.g. `MY_VAR: "${MY_VAR}"`), which is the existing pattern throughout `charter.yml`. Added a doc note to CONFIGURATION.md clarifying this approach.

---

## Low Priority (Documentation/Polish)

### 3. ✅ Unused `filesystem.settings.allowed_methods`
`charter.yml` defines `mcp.client_configs.filesystem.settings.allowed_methods` but `set-up-tools.sh` hardcodes `read_multiple_files`. Either wire this list into the command generation or remove the setting to avoid misleading configuration.

**Resolution:** Already resolved during the `mcp_catalog.py` refactoring. The `_apply_allowed_methods()` function reads `settings.allowed_methods` at resolution time, strips any existing `-a` flags from the command, and rebuilds them from the config list. The hardcoded `-a read_multiple_files` in `charter.yml` is just a default template. `set-up-tools.sh` no longer exists. Test: `test_filesystem_allowed_methods_override_command`.

---

### 4. Documentation file location mismatch
`docs/CONFIGURATION.md` states the `mcp` block lives in `directives.yml`, but defaults are in `charter.yml` with overrides in `directives.yml` and `local.yml`. Update the docs to reflect actual precedence and source files.

**Additionally:** The schema reference section is very dense (150+ lines). Consider splitting into:
- Quick Start (common patterns, examples)
- Schema Reference (complete field listing)
- Advanced Topics (placeholder expansion, dependency resolution, troubleshooting)

---

### 9. Missing extension guides ⭐
Add to CONFIGURATION.md:
- **"Adding a Custom MCP Server"** section with step-by-step template
- **"Troubleshooting"** section covering common issues:
  - "Server not appearing" → Check `enabled`, `requires_env`, `depends_on`
  - "Placeholder not expanding" → Check syntax, circular references
  - "Validation errors" → Common typos and fixes

---

### 10. Inline examples in charter.yml
Add commented-out example blocks showing how to extend the MCP catalog:

```yaml
# Example: Add your own HTTP MCP server
# mcp:
#   client_configs:
#     my_server:
#       enabled: true
#       clients:
#         default:
#           transport: http
#           url: "http://localhost:9000/mcp/"
#
# Example: Add your own stdio MCP server
# mcp:
#   client_configs:
#     my_stdio_server:
#       enabled: true
#       clients:
#         default:
#           transport: stdio
#           command:
#             - npx
#             - -y
#             - my-mcp-package
```
