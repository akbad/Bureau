# Data Flow Docstring Specification

**Status:** Draft
**Scope:** All Python functions and shell scripts/functions that participate in Bureau data flows.
**Goal:** A consistent, human-readable, machine-parseable annotation format that lets both human developers and AI agents trace how data moves through the system.

---

## 1. Survey of Existing Conventions

### 1.1 Python (operations/)

The codebase already uses **Google-style docstrings** with `Args:`, `Returns:`, and `Raises:` sections. Coverage is uneven:

| Pattern | Examples | Notes |
|---|---|---|
| Full Google-style (summary + Args + Returns) | `validate_config_schema`, `find_repo_root`, `parse_duration`, `resolve_roles_catalog` | Clean, consistent |
| Summary-only | `run_cleanup`, `_get_qdrant_config`, most methods in `QdrantHandler` | No Args/Returns |
| Freeform multi-line | `expand_placeholders`, `find_project_config`, `_collect_placeholder_refs` | Description present but no structured sections |
| Module-level docstring | `config_loader.py`, `validate_config.py`, `roles_catalog.py` | Present; some omit it (`mcp_catalog.py`, `skills_catalog.py`) |
| No docstring at all | `resolve_mcp_catalog`, `_expand_strings`, `_has_required_env`, `render_setup_plan` | Several core data-flow functions lack any documentation |

**No existing function documents what config keys it reads, what files it writes, or what other functions call it.**

### 1.2 Shell scripts

| Pattern | Examples | Notes |
|---|---|---|
| Top-level header block | `set-up-tools.sh` (prerequisites + usage), `set-up-protocols.sh` (one-line purpose) | Inconsistent depth |
| Per-function comments | `discover_agents` (3-line: Usage/Sets/Exits), `agent_enabled` (2-line: Usage/Returns) | Ad-hoc, no standard structure |
| Library file header | `logging.sh` (full function catalog + env vars), `agent-selection.sh` (2-line purpose) | `logging.sh` is the gold standard here |
| No comments at all | Most helper functions in `set-up-tools.sh` (`expand_tilde`, `plan_jq`, `check_port`, etc.) | |

**No existing shell function documents its data flow (reads/writes/calls/calledby).**

---

## 2. Python Docstring Template

### 2.1 Structure

```python
def function_name(arg1: str, arg2: Mapping[str, Any]) -> dict[str, Any]:
    """One-line summary in imperative mood (72 chars max).

    Extended description if the one-liner is insufficient. Keep this
    to 1-3 sentences. Focus on *what* and *why*, not *how*.

    Args:
        arg1: Description of first argument.
        arg2: Description of second argument.

    Returns:
        Description of return value. For dicts, list the keys:
            - key_one: what it contains
            - key_two: what it contains

    Raises:
        ValueError: When this specific condition occurs.
        FileNotFoundError: When that specific condition occurs.

    Data Flow:
        Reads:
            config -> mcp.client_configs
            config -> mcp.services
            config -> mcp.dependencies
            env -> TAVILY_API_KEY
        Writes:
            stdout (JSON setup plan)
        Calls:
            operations.mcp_catalog.resolve_mcp_catalog
            operations.config_loader.get_config
        Called By:
            tools/scripts/render-mcp-setup.py::main
            tools/scripts/set-up-tools.sh (via `uv run`)
    """
```

### 2.2 Section Rules

Every function that participates in a data flow MUST have the `Data Flow:` section. The standard Google-style sections (`Args`, `Returns`, `Raises`) follow their normal rules and are not changed by this spec.

#### Data Flow Section

The `Data Flow:` section contains up to four subsections. **Include only subsections that apply.** Do not include empty subsections.

| Subsection | When to include | What to list |
|---|---|---|
| `Reads:` | Function reads external state | Config paths, env vars, files, network endpoints |
| `Writes:` | Function produces side effects | Files, stdout, stderr, network calls, state mutations |
| `Calls:` | Function calls other data-flow functions | Qualified function names |
| `Called By:` | Known callers exist | Qualified function names or script paths |

### 2.3 Config Path Notation

Use **dot-separated paths** rooted at `config` to express config key access.

```
config -> mcp.client_configs
config -> retention_period_for.qdrant
config -> agents
config -> path_to.workspace
```

**Rules:**
- Always root at `config` followed by `->`.
- Use dots for nesting: `config -> mcp.services.qdrant_mcp.env.QDRANT_URL`.
- For iteration over dynamic keys, use `*` as a wildcard: `config -> mcp.client_configs.*`.
- For access into a dynamic-keyed subtree, chain the wildcard: `config -> mcp.client_configs.*.clients.*`.

**Rationale:** Dot notation matches the YAML structure in `defaults.yml` and is what the existing `_get_config_value()` function uses internally. It avoids Python-dict-literal noise (`config['mcp']['dependencies']`) and is greppable.

### 2.4 File Path Notation

Express file paths **relative to the repo root**, prefixed with `repo://`. For paths under the user's home directory, use `~/`. For absolute system paths, write them as-is.

```
Reads:
    repo://defaults.yml
    repo://local.yml
    ~/.<cli>/settings.json
Writes:
    repo://bin/close-bureau
    /tmp/mcp-*-server.log
```

**Rules:**
- `repo://` means relative to the repository root (the directory containing `defaults.yml`).
- `~/` means relative to `$HOME`.
- Absolute paths (`/tmp/...`) are written verbatim.
- Use shell-style globs where the exact filename is dynamic: `/tmp/mcp-*-server.log`.
- For directories (not specific files), append a trailing `/`: `repo://.archives/trash/`.

### 2.5 Environment Variable Notation

Prefix with `env ->`:

```
Reads:
    env -> TAVILY_API_KEY
    env -> BRAVE_API_KEY
    env -> HOME
```

### 2.6 Standard Output / Error Notation

Use the literal tokens `stdout` and `stderr`, with a parenthetical format hint:

```
Writes:
    stdout (JSON setup plan)
    stderr (validation error messages)
    stdout (newline-separated role names)
```

### 2.7 Network Endpoint Notation

Use `http ->` or `https ->` followed by a description:

```
Reads:
    http -> Qdrant /collections/{collection}/points/scroll
Writes:
    http -> Qdrant /collections/{collection}/points/delete
```

### 2.8 Pure Functions

Functions with no side effects and no reads from external state (config, env, files, network) should use the marker `Pure` instead of listing subsections:

```
Data Flow:
    Pure
```

This explicitly communicates that the function is safe to call without context and has no hidden dependencies.

### 2.9 Calls / Called By Notation

Use the **module-qualified function name** for Python. For shell scripts, use the repo-relative path. For shell functions within a library, use `path::function_name`.

```
Calls:
    operations.config_loader.get_config
    operations.mcp_catalog.resolve_mcp_catalog
Called By:
    operations.cleanup.core.run_cleanup
    tools/scripts/set-up-tools.sh (via `uv run`)
    bin/lib/agent-selection.sh::discover_agents
```

**Rules:**
- For methods on a class, include the class: `operations.cleanup.handlers.qdrant.QdrantHandler.get_stale_items`.
- For private/internal callers within the same module, use relative names: `._validate_node` (leading dot means same-module).
- When a shell script calls a Python function via a subprocess (`uv run`, `python -m`), note the invocation mechanism in parentheses.
- The `Called By:` list is best-effort. It documents *known* callers at the time of writing. It does not need to be exhaustive for widely-used utility functions (see Section 4.4).

---

## 3. Shell Script / Function Template

### 3.1 Top-Level Script Header

```bash
#!/usr/bin/env bash
#
# One-line summary of what the script does.
#
# Extended description (1-3 lines). Focus on purpose and context,
# not implementation details.
#
# Prerequisites:
#   - Node.js/npm
#   - uv/uvx with Python 3.12+
#   - Docker daemon
#
# Usage: ./script-name.sh [--flag] [args...]
#
# Data Flow:
#   Reads:
#       config -> agents
#       config -> mcp.client_configs.*
#       config -> startup_timeout_for.mcp_servers
#       env -> TAVILY_API_KEY
#       env -> BRAVE_API_KEY
#   Writes:
#       ~/.claude/settings.json (MCP server registrations)
#       ~/.gemini/settings.json (MCP server registrations)
#       ~/.codex/config.toml (MCP server registrations)
#       repo://bin/close-bureau (teardown script)
#       /tmp/mcp-*-server.log (server logs)
#       stdout (progress messages)
#   Calls:
#       tools/scripts/render-mcp-setup.py (via `uv run`)
#       bin/lib/agent-selection.sh::discover_agents (via `source`)
#       bin/lib/logging.sh (via `source`)
#   Called By:
#       bin/open-bureau (orchestrator)
```

### 3.2 Shell Function Within a Script or Library

```bash
# One-line summary of what the function does.
#
# Extended description if needed.
#
# Args:
#   $1 - agent: Display name of the agent (e.g., "Claude Code")
#   $2 - server: MCP server identifier
#   $3+ - headers: Optional header key:value pairs
#
# Returns:
#   0 on success, 1 if already exists, 2 if headers not supported
#
# Data Flow:
#   Reads:
#       $CLAUDE_CLI_STATE
#       $GEMINI_CONFIG
#   Writes:
#       ~/.claude.json (via `claude mcp add`)
#       ~/.gemini/settings.json (via add_mcp_to_gemini)
#       ~/.codex/config.toml (via add_mcp_to_codex)
#   Calls:
#       add_mcp_to_gemini
#       add_mcp_to_codex
#   Called By:
#       (main script body in set-up-tools.sh)
add_http_mcp_to_agent() {
```

### 3.3 Shell-Specific Notation Rules

**Global variable side effects** use the `Sets:` sub-section (shell-only, not used in Python):

```
# Data Flow:
#   Sets:
#       AGENTS (array of enabled agent display names)
#   Reads:
#       config -> agents (via `_get_config --list agents`)
```

**Shell variables** referenced from the enclosing scope are listed with a `$` prefix under `Reads:`:

```
# Data Flow:
#   Reads:
#       $SETUP_PLAN_FILE
#       $REPO_ROOT
```

---

## 4. Edge Cases

### 4.1 Functions That Are Both Callers and Callees (Mid-Chain)

Include both `Calls:` and `Called By:`. This is the common case for orchestration functions.

```python
def validate_config(config, add_warnings=False):
    """Perform full validation including structure and format checks.

    ...

    Data Flow:
        Reads:
            config -> * (full config tree)
        Calls:
            .validate_config_schema
            .validate_durations
            .validate_placeholder_cycles
            .validate_service_dependency_cycles
            .validate_mcp_rules
        Called By:
            operations.cleanup.core.run_cleanup
            operations.validate_config.main (CLI entry point)
    """
```

### 4.2 Functions With Dynamic Reads

When a function iterates over config keys that are not known statically, use the wildcard `*` syntax and add a parenthetical explanation:

```python
Data Flow:
    Reads:
        config -> mcp.client_configs.* (iterates all client config entries)
        config -> mcp.client_configs.*.clients.* (iterates per-CLI client transports)
        config -> mcp.client_configs.*.depends_on.services
```

When a function reads from a path that is itself derived from config or input:

```python
Data Flow:
    Reads:
        config -> mcp.services.{name}.env (name from function arg)
```

Use `{name}` to indicate a variable part derived from an argument or loop variable. This is distinct from `*` which means "all keys at this level."

### 4.3 Shell Functions Within a Script File

Shell functions defined inside a larger script (not in a separate library file) use the same comment format as library functions. When referencing them in `Calls:` or `Called By:`, use the script path plus `::function_name`:

```
Calls:
    tools/scripts/set-up-tools.sh::start_docker_container
    tools/scripts/set-up-tools.sh::start_http_process
```

When the function is only called from the main body of its own script, use:

```
Called By:
    (main body)
```

### 4.4 Private / Helper Functions

Functions should be annotated according to their role in data flow, not their visibility:

| Category | Treatment |
|---|---|
| **Helper that touches external state** (reads config, writes files, makes HTTP calls) | Full `Data Flow:` section required |
| **Helper that is pure computation** (string formatting, data transformation with no I/O) | Use `Data Flow: Pure` |
| **Trivial one-liner helper** (e.g., `_as_list`, `expand_tilde`) | `Data Flow: Pure` or omit entirely if the function is obviously pure from its signature and 1-2 lines of body |

The `Called By:` list for widely-reused internal helpers (e.g., `_expand_strings`, `_check_type`) MAY be abbreviated to `Called By: (multiple validators)` or `Called By: (internal)` rather than listing every call site. The key information for these helpers is their `Reads:` and `Writes:` (or `Pure` status), not their caller list.

---

## 5. Complete Examples

### 5.1 Python Function: `resolve_mcp_catalog`

```python
def resolve_mcp_catalog(
    config: Mapping[str, Any], env: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Resolve the full MCP catalog from config, filtering by enablement and dependencies.

    Processes the three MCP config buckets (dependencies, services,
    client_configs) in dependency order. Entries are filtered by their
    `enabled` flag, required environment variables, and inter-entry
    dependency satisfaction. Placeholder strings are expanded against
    both the config tree and the process environment.

    Args:
        config: Full Bureau configuration dictionary (as returned by get_config).
        env: Environment variable mapping. Defaults to os.environ.

    Returns:
        Dictionary with three keys:
            - dependencies: Resolved and expanded dependency entries.
            - services: Resolved services in dependency-start order.
            - client_configs: Resolved client configs with per-CLI transport details.

    Data Flow:
        Reads:
            config -> mcp.dependencies.* (kind, enabled, repo_url, path, ...)
            config -> mcp.services.* (kind, enabled, depends_on, ...)
            config -> mcp.client_configs.* (enabled, requires_env, clients, ...)
            env -> * (any env var referenced by ${...} placeholders)
        Writes:
            None (returns value only)
        Calls:
            operations.config_templating.expand_placeholders
            ._has_required_env
            ._expand_strings
            ._apply_allowed_methods
    """
```

### 5.2 Top-Level Shell Script: `set-up-tools.sh`

```bash
#!/usr/bin/env bash
#
# Configure all coding CLI agents to use Bureau's MCP servers.
#
# Orchestrates the full MCP setup pipeline: resolves the config-driven
# setup plan, provisions dependencies (git clones, file stubs), starts
# runtime services (Docker containers, HTTP processes), registers MCP
# servers with each enabled CLI agent, and configures auto-approvals.
#
# Prerequisites:
#   - Node.js/npm
#   - uv/uvx with Python 3.12+
#   - Docker daemon (for container-based MCP services)
#   - API keys in environment: TAVILY_API_KEY, BRAVE_API_KEY, CONTEXT7_API_KEY
#
# Usage: ./set-up-tools.sh
#
# Data Flow:
#   Reads:
#       config -> agents
#       config -> startup_timeout_for.mcp_servers
#       config -> startup_timeout_for.docker_daemon
#       config -> mcp.dependencies.* (via render-mcp-setup.py)
#       config -> mcp.services.* (via render-mcp-setup.py)
#       config -> mcp.client_configs.* (via render-mcp-setup.py)
#       config -> auto_approved.mcp_tools
#       config -> auto_approved.mcp_servers.*
#       config -> auto_approved.bash.*
#       config -> prune_disabled_mcps
#       env -> TAVILY_API_KEY
#       env -> BRAVE_API_KEY
#       env -> CONTEXT7_API_KEY
#       env -> HOME
#       ~/.claude.json (existing MCP registrations)
#       ~/.gemini/settings.json (existing MCP registrations)
#       ~/.codex/config.toml (existing MCP registrations)
#   Writes:
#       ~/.claude.json (MCP server registrations via `claude mcp add`)
#       ~/.claude/settings.json (auto-approvals, post_config env)
#       ~/.gemini/settings.json (MCP servers + auto-approvals)
#       ~/.codex/config.toml (MCP servers + auto-approvals)
#       ~/.config/bureau/internal/managed-mcps.*.json (managed registry)
#       repo://bin/close-bureau (generated teardown script)
#       /tmp/mcp-*-server.log (HTTP server logs)
#       stdout (progress and status messages)
#       stderr (warnings and errors)
#   Calls:
#       tools/scripts/render-mcp-setup.py (via `uv run python`)
#       tools/scripts/managed-mcp-registry.py (via `uv run python`)
#       tools/scripts/add-claude-auto-approvals.py (via `uv run`)
#       tools/scripts/add-codex-auto-approvals.py (via `uv run`)
#       tools/scripts/add-gemini-auto-approvals.py (via `uv run`)
#       tools/scripts/write-codex-exec-policy.py (via `uv run`)
#       bin/lib/agent-selection.sh::discover_agents (via `source`)
#       bin/lib/logging.sh (via `source`)
#       bin/ensure-prereqs
#   Called By:
#       bin/open-bureau (main orchestrator)
```

### 5.3 Shell Library Function: `discover_agents`

```bash
# Detect enabled agents from merged YML config and populate AGENTS array.
#
# Reads the `agents` list from the merged config (defaults.yml + .bureau.yml
# + local.yml), maps config names to display names, and stores the result
# in the global AGENTS array. Exits with an error if no agents are enabled.
#
# Args:
#   (none)
#
# Returns:
#   0 on success, exits 1 if no agents found.
#
# Data Flow:
#   Reads:
#       config -> agents (via `_get_config --list agents`)
#   Sets:
#       AGENTS (array of display names, e.g., "Claude Code", "Gemini CLI")
#   Writes:
#       stdout (log messages listing detected agents)
#       stderr (error messages if config read fails)
#   Calls:
#       bin/lib/agent-selection.sh::_get_config
#       bin/lib/agent-selection.sh::_agent_display_name
#   Called By:
#       tools/scripts/set-up-tools.sh
#       protocols/scripts/set-up-protocols.sh
#       agents/scripts/set-up-agents.sh
discover_agents() {
```

---

## 6. Parsing Rules (for Extraction Scripts)

The format is designed to be extractable with simple text processing. The key structural invariants:

1. **Python:** The `Data Flow:` section begins on a line matching `^\s+Data Flow:\s*$` inside a docstring. It ends at the next unindented section header (matching `^\s+\w+:$` at the same indentation as `Data Flow:`) or at the closing `"""`.

2. **Shell:** The `Data Flow:` section begins on a comment line matching `^#\s+Data Flow:\s*$`. It ends at the first non-comment line or a comment line matching `^#\s+\w+:$` at the same indentation level (a sibling section like `Args:`).

3. **Subsections** (`Reads:`, `Writes:`, `Calls:`, `Called By:`, `Sets:`, `Pure`) are always indented one level deeper than `Data Flow:`.

4. **Entries** within a subsection are indented one level deeper than the subsection header.

5. **Parenthetical annotations** (e.g., `(JSON setup plan)`, `(via uv run)`) are always at the end of an entry line and are optional metadata, not part of the identifier.

6. A function with `Data Flow: Pure` on a single line (with `Pure` on the same line as `Data Flow:`) is a pure function with no subsections.

---

## 7. Adoption Strategy

This format is adopted **incrementally**, not as a mass rewrite:

1. **New functions:** Must include `Data Flow:` from the start.
2. **Modified functions:** Add `Data Flow:` when touching a function for any reason.
3. **Critical-path functions:** Annotate the core data-flow spine first (config_loader -> mcp_catalog -> render-mcp-setup -> set-up-tools.sh) as a reference implementation.
4. **Validation:** A lint script can check that any function containing I/O keywords (`get_config`, `open(`, `urlopen`, `os.environ`, `subprocess.run`) has a `Data Flow:` section. This is advisory, not blocking.
