# Schema Fix Plan

## High Priority (Breaking/Silent Failures)

### 1. Runtime service dependency enforcement ✅
Add enforcement for `mcp.services.<service>.depends_on.services` during catalog resolution so services depending on disabled or missing services are skipped before `service-order.py` runs. Current behavior only checks dependency IDs, which can cause ordering to fail at runtime.

**Additionally:** Add cycle detection for service dependencies to prevent infinite loops/deadlocks. A service depending on itself (directly or transitively) would cause startup to hang. Implement using DFS-based cycle detection similar to `validate_placeholder_cycles()`.

**Example problem case:**
```yaml
mcp:
  services:
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
`operations/validate_config.py` only checks that `mcp.services` and `mcp.client_configs` exist, not that entries contain required keys or valid values. Add deeper validation for MCP entries (kinds, required fields, and types) to fail fast on misconfiguration.

**Specific validation gaps to address:**

#### 5.1 ✅ Kind enum validation
Validate that `kind` fields contain only allowed values:
- `mcp.dependencies.<id>.kind`: Must be `git_repo` or `file`
- `mcp.services.<id>.kind`: Must be `docker_container` or `http_process`

**Problem:** Typos like `kind: http_server` (instead of `http_process`) silently fail later during resolution.

#### 5.2 ✅ Required field validation per kind
Each `kind` has mandatory fields that should be validated:

**For `services`:**
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
  services:
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

---

### 11. ✅ Rename `runtime_services` → `services`
Rename across the entire repo (config keys, validators, docs, setup scripts, `depends_on.services` references). The old name was unnecessarily verbose; `services` is sufficient and consistent with `depends_on.services`.

**Resolution:** Implemented as a hard break with no compatibility bridge. The MCP config contract now uses `mcp.services` and setup plan JSON now uses `services`. Placeholder paths were updated from `${mcp.runtime_services.*}` to `${mcp.services.*}`. Validation now errors if legacy `mcp.runtime_services` is present, including mixed-key configs where both old and new keys are defined.

### 12. Rename `depends_on` → `requires`
Rename across the entire repo. Eliminates the stutter between the `depends_on.dependencies` sub-key and the top-level `dependencies` bucket — `requires.dependencies` reads more naturally.

### 13. Investigate schema autocomplete support
Explore providing editor-level autocomplete/validation for Bureau's YAML config (e.g., JSON Schema for YAML, LSP integration, or a custom VS Code extension). This is the right layer for catching typos like `clients.claud` instead of `clients.claude` — runtime validation warnings are the wrong tool for that job. Investigate:
- Generating a JSON Schema from `mcp_validation_rules.py` constants
- VS Code YAML extension (`redhat.vscode-yaml`) schema association
- Whether dynamic placeholders (`${...}`) complicate schema generation
- Effort vs payoff given the small user base

---

## Design: MCP Schema Validation Fixes (W1-W11)

> **Date:** 2026-03-07
> **Branch:** `feat/skills-system`
> **Scope:** Fix all 11 weaknesses identified in [`docs/mcp-schema-eval.md`](mcp-schema-eval.md). Ship as a single changeset.
> **Files:** `operations/validate_config.py`, `operations/mcp_validation_rules.py`, `operations/mcp_catalog.py`

### Severity model

Add a third tier to `ValidationResult`:

| Tier | Semantics | Examples |
|------|-----------|----------|
| **error** | Will crash at runtime. Must fix. | Missing `kind`, missing `transport`, `enabled: 42` |
| **warning** | Probably wrong, might be intentional. | Unknown key (typo?), cross-ref to missing entry |
| **info** | FYI — system is doing something you should know about. | Auto-detected dependency, missing `clients.default` |

Add `info: list[str]` field to `ValidationResult`. Consumers print info messages with distinct, non-alarming formatting.

### W1: `kind` required (error) ✅

In `_validate_entry_schema`, if `kind_enum` is provided but `"kind" not in entry`, emit an error. All downstream per-kind checks (required fields, type rules) already gate on `kind` being present — no cascading changes needed. Engine-only change in `validate_config.py`.

### W2: `transport` required (error) ✅

Same pattern as W1. If a client entry lacks `transport`, emit an error. Transport-required field checks already gate on transport being present. Engine-only change.

### W3: `enabled` type check ✅

Add `("enabled", "bool")` to all three bucket type rule lists:
- `DEPENDENCY_TYPE_RULES`
- `RUNTIME_SERVICE_TYPE_RULES`
- `CLIENT_CONFIG_TYPE_RULES`

Missing `enabled` is fine (defaults to `true`). Wrong type (`enabled: "yes"`, `enabled: 42`) is a hard error.

### W4: `sse` transport ✅

Add `sse` as a valid transport with the same required field as `http`:
- `CLIENT_TRANSPORT_KINDS`: `{"http", "sse", "stdio"}`
- `CLIENT_TRANSPORT_REQUIRED`: add `"sse": {"url"}`

### W5: Already fixed

No work. The eval doc was wrong — `validate_config.py` already validates `healthcheck.tcp` as int, skips `${...}` placeholders, and rejects bools.

### W6: Auto-detect dependencies from placeholders (hybrid) ✅

**Inference function:** New `_infer_requires(entry_name, entry_bucket, entry_data) -> dict` in `validate_config.py`. Walks all string values recursively, extracts `${mcp.<bucket>.<name>.<field>}` references, filters out self-references, returns `{"services": [...], "dependencies": [...]}`.

**Validation integration:** During `_validate_cross_references`, union auto-inferred deps with any explicit `requires` block. Auto-inferred references to missing/disabled entries produce **info** messages:

> `info: client_configs.qdrant auto-depends on services.qdrant_mcp (via placeholder in clients.default.url)`

**Resolution integration:** In `mcp_catalog.py`, auto-inferred deps feed into the existing enablement-gating and topological-sort logic. Merge is a union — explicit `requires` adds to auto-detected, never subtracts.

**User impact:** `requires` becomes optional for entries whose dependencies are visible via placeholders (~95% of cases). Stays available for non-placeholder deps or documentation intent.

### W7: Skip (by design)

Don't validate `clients.<cli>` keys against the `agents` list. The failure mode is harmless (unused config, not broken config), and coupling creates friction during normal setup workflows. Schema autocomplete (#13) is the right layer for typo detection.

### W8: Missing `clients.default` log (info) ✅

After the existing "must have at least one client" check, if `clients` dict exists but has no `"default"` key, emit an **info** message:

> `info: client_configs.qdrant has no clients.default — agents without a specific override will skip this server`

### W9: `settings` type check ✅

Add `("settings", "dict")` to:
- `RUNTIME_SERVICE_TYPE_RULES`
- `CLIENT_CONFIG_TYPE_RULES`

Contents remain opaque. The consuming MCP server is the real validator for its own settings.

### W10: Mount path value types ✅

In `_validate_mounts`, after checking that `host_path` and `container_path` keys exist, validate their values are strings. Skip `${...}` placeholders (same pattern as `_validate_field_types`).

### W11: Dependency ordering ✅

**Schema:** Add `"requires"` to `DEPENDENCY_ALLOWED_KEYS`. Add `("requires", "list[str]")` to `DEPENDENCY_TYPE_RULES`. Dependencies can only require other dependencies — flat list, no sub-keys.

**Validation:** Check that each name in `requires` references a declared dependency. Warning if not found. Add cycle detection (DFS, same pattern as service/placeholder cycle checks).

**Resolution:** Change dependency resolution in `mcp_catalog.py` from dict-order iteration to topological sort based on `requires`. Dependencies whose required deps failed to resolve are silently skipped (same cascading pattern as services).

```yaml
mcp:
  dependencies:
    base_repo:
      kind: git_repo
      repo_url: "..."
      path: "..."

    overlay_repo:
      kind: git_repo
      repo_url: "..."
      path: "..."
      requires: [base_repo]
```
