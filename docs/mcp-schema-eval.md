# MCP schema evaluation

> **Date:** 2026-03-04
> **Scope:** `mcp` key in Bureau's YAML config — schema design, validation coverage, and doc consistency.
>
> **Files reviewed:**
> - [`docs/CONFIGURATION.md`](CONFIGURATION.md) — user-facing schema reference
> - [`defaults.yml`](/defaults.yml) — canonical defaults
> - [`operations/validate_config.py`](/operations/validate_config.py) — validation engine
> - [`operations/mcp_validation_rules.py`](/operations/mcp_validation_rules.py) — declarative rule constants

---

***Contents***:

- [Architecture overview](#architecture-overview)
- [Strengths](#strengths)
- [Weaknesses](#weaknesses)
  - [Missing required-field checks](#missing-required-field-checks)
  - [Doc/schema drift](#docschema-drift)
  - [Implicit coupling not validated](#implicit-coupling-not-validated)
  - [Shallow sub-structure validation](#shallow-sub-structure-validation)
  - [Design limitation](#design-limitation)
- [Summary](#summary)

---

## Architecture overview

The schema has **three buckets** under the `mcp` key, forming a dependency graph:

```
dependencies → services → client_configs
  (repos, files)    (docker, processes)    (what CLIs actually see)
```

Each bucket uses a **discriminated union** pattern — a `kind` field determines which fields are required. Validation is split across two files:

| File | Role |
|:-----|:-----|
| `operations/mcp_validation_rules.py` | Declarative constants (allowed keys, required fields, type rules) |
| `operations/validate_config.py` | Engine that consumes those constants |

---

## Strengths

### 1. Declarative validation rules

All field sets, kind enums, and type rules live in `mcp_validation_rules.py` as plain data. Adding a new `kind` or field means editing a dict/set, not writing new validation logic. This is the right separation of concerns.

### 2. Warnings vs errors distinction

Unknown keys produce **warnings**, not errors. This means user extension keys (like `settings.collection`) don't break validation, but typos still get flagged. The `ValidationResult` dataclass makes this a first-class concept.

### 3. Cross-reference validation

`_validate_cross_references` checks that `depends_on.services` and `depends_on.dependencies` actually point to declared entries. These are warnings (not errors) because references might come from conditionally-loaded config layers — good pragmatic choice for a multi-tier config system.

### 4. Transport-dependent required fields

`CLIENT_TRANSPORT_REQUIRED` maps `http → {url}` and `stdio → {command}`, so the validator correctly enforces that HTTP clients have URLs and stdio clients have commands.

### 5. Placeholder-aware type checking

`_validate_field_types` skips values containing `${...}` since their final type depends on expansion. Without this, every port reference like `${mcp.services.qdrant_db.host_port}` would fail the `int` check.

---

## Weaknesses

### Missing required-field checks

#### W1. `kind` is not validated as *required* — only its *value* is

In `_validate_entry_schema`, the `kind_enum` check is:

```python
if kind_enum is not None and "kind" in entry:
```

If `kind` is **missing entirely**, nothing fires — no error about the missing field, no required-field-per-kind check. A `services` entry without `kind` silently passes schema validation.

#### W2. `transport` is not validated as required for client entries

Same pattern: `if transport is not None` means a client entry with no `transport` field passes validation. The transport-required fields check (`if transport:`) also silently skips. A client entry like `{url: "http://..."}` with no `transport` would pass.

#### W3. `enabled` field type is never validated

Every bucket supports `enabled: true/false`, but no type rule checks that `enabled` is actually a boolean. Setting `enabled: "yes"` or `enabled: 42` would pass validation. None of `DEPENDENCY_TYPE_RULES`, `SERVICE_TYPE_RULES`, or `CLIENT_CONFIG_TYPE_RULES` include an `enabled` check.

---

### Doc/schema drift

#### W4. `sse` transport is mentioned in docs but not in the schema

`CONFIGURATION.md` says:

> `http/sse` expect `url`; `stdio` expects `command`

But `CLIENT_TRANSPORT_KINDS` is `{"http", "stdio"}`. There is no `sse` transport in the validator. Either the docs are wrong or the schema is incomplete.

#### W5. `healthcheck.tcp` type is not validated

The docs say `healthcheck.tcp` is an `int` (port number). The type rule says `("healthcheck", "dict")`. But the inner validation (`_validate_healthcheck`) only checks **allowed keys**, not the type of `tcp`. A config like `healthcheck: {tcp: "not-a-number"}` would pass.

---

### Implicit coupling not validated

#### W6. `${...}` URL references create undeclared dependencies

Many client configs implicitly reference runtime services via `${mcp.services.X.port}` in their URLs, but the cross-reference validator only checks `depends_on` blocks. If you disable `qdrant_mcp` but keep the `qdrant` client config enabled (without `depends_on`), validation passes but the URL won't resolve at runtime.

#### W7. `clients.<cli>` keys are not checked against the `agents` list

`disabled_for` values are cross-checked against the top-level `agents` list (producing warnings for unknown agents), but `clients.<cli>` keys are **not** checked. You could have `clients.codex` without `codex` in the agents list and get no feedback.

#### W8. `clients.default` is "strongly recommended" but not enforced

The docs say `clients.default` is "optional but strongly recommended." The validator checks `must have at least one client` but doesn't warn if `default` is missing. A config with only `clients.claude` would pass silently, then break for Gemini/Codex users who don't have a client override.

---

### Shallow sub-structure validation

#### W9. No validation for `settings` sub-structure

`settings` is allowed but completely opaque — any value type passes. While this is intentional (extension point), there's no opt-in mechanism for known settings schemas. For example, `qdrant_mcp.settings.collection` should be a string and `settings.embedding_provider` should be a string, but nothing checks this.

#### W10. Mount validation doesn't check value types

`_validate_mounts` checks that `host_path` and `container_path` **keys exist** in each mount entry, but doesn't validate their **values are strings**. A mount like `{host_path: 42, container_path: []}` would pass.

---

### Design limitation

#### W11. Dependencies can't express inter-dependency ordering

The docs say:

> Dependencies cannot depend on other dependencies — they are prepared in sorted order first.

But the schema has no mechanism to enforce or express ordering between dependencies. If `dependency_B` needs `dependency_A`'s `path` to exist first, there's no way to declare that. The current sorted-order convention is implicit and fragile.

---

## Summary

| Category | Count | Items |
|:---------|------:|:------|
| **Strengths** | 5 | Declarative rules, warning/error split, cross-refs, transport-required, placeholder-aware |
| **Missing required checks** | 3 | W1 (`kind`), W2 (`transport`), W3 (`enabled` type) |
| **Doc/schema drift** | 2 | W4 (`sse` transport), W5 (`healthcheck.tcp` type) |
| **Implicit coupling not validated** | 3 | W6 (`${...}` URL refs), W7 (`clients.<cli>` vs agents), W8 (`clients.default`) |
| **Shallow sub-structure validation** | 2 | W9 (`settings` opaque), W10 (mount value types) |
| **Design limitation** | 1 | W11 (no inter-dependency ordering) |

> **Biggest systemic gap:** `kind` and `transport` are the schema's primary discriminators, yet neither is enforced as *present*. The discriminated union pattern works when configs are correct, but fails silently when they're incomplete.
>
> **Potential improvement:** A "strict mode" flag that promotes warnings to errors for CI validation, and enforcing `kind`/`transport` as required fields, would close the largest gaps with minimal changes to the existing declarative structure.
