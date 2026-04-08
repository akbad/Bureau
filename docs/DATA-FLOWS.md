# Data flows

> End-to-end traces of every data flow in Bureau, from configuration inputs to CLI outputs.

Each section contains:

1. **Prose overview** (hand-written) -- what the flow does and why it exists
2. **Mermaid diagram** (hand-written) -- visual trace of data movement
3. **Function-level detail table** (generated) -- extracted from structured docstrings by `scripts/extract-flow-docs.py`

Generated tables are inserted at `<!-- GENERATED:... -->` markers by the extraction script. Do not edit content between `<!-- GENERATED:... -->` and `<!-- /GENERATED -->` markers by hand.

---

***Contents***

- [System overview](#system-overview)
- [Conventions and legend](#conventions-and-legend)
- [1. Config resolution](#1-config-resolution)
- [2. MCP catalog and setup](#2-mcp-catalog-and-setup)
- [3. Role setup](#3-role-setup)
- [4. Skill setup](#4-skill-setup)
- [5. Protocol and context setup](#5-protocol-and-context-setup)
- [7. OpenCode pipeline](#7-opencode-pipeline)
- [8. Auto-approval configuration](#8-auto-approval-configuration)
- [9. MCP registry management](#9-mcp-registry-management)
- [10. Cleanup system](#10-cleanup-system)
- [Generated table format](#generated-table-format)

---

## System overview

Bureau's `open-bureau` entrypoint orchestrates all flows in a fixed sequence. The diagram below shows the relationships between flows and the data that passes between them.

```mermaid
flowchart TB
    subgraph inputs["Configuration inputs"]
        DY[defaults.yml]
        BY[.bureau.yml]
        LY[local.yml]
        ENV[Environment variables]
    end

    subgraph F1["1. Config resolution"]
        MERGE[4-tier merge]
        EXPAND[Placeholder expansion]
        VALIDATE[Validation]
    end

    DY --> MERGE
    BY --> MERGE
    LY --> MERGE
    ENV --> MERGE
    MERGE --> EXPAND --> VALIDATE
    VALIDATE --> CONFIG[(Merged Config)]

    subgraph F2["2. MCP catalog + setup"]
        RESOLVE_MCP[resolve_mcp_catalog]
        RENDER_PLAN[render_setup_plan]
        BASH_ORCH[set-up-tools.sh]
    end

    CONFIG --> RESOLVE_MCP --> RENDER_PLAN --> BASH_ORCH

    subgraph F3["3. Role setup"]
        ROLE_CAT[roles_catalog]
        AGENT_SETUP[set-up-agents.sh]
    end

    CONFIG --> ROLE_CAT --> AGENT_SETUP

    subgraph F4["4. Skill setup"]
        SKILL_CAT[skills_catalog]
        SKILL_GEN[generate-skills-config.py]
        SKILL_SH[set-up-skills.sh]
    end

    CONFIG --> SKILL_CAT --> SKILL_GEN --> SKILL_SH

    subgraph F5["5. Protocol + context"]
        PROTO_DEPLOY[Protocol file deployment]
        HOOK_CFG[Hook configuration]
        REMINDER[Per-prompt reminders]
    end

    CONFIG --> PROTO_DEPLOY --> HOOK_CFG --> REMINDER

    subgraph F7["7. OpenCode pipeline"]
        OC_MCP[render-opencode-mcp.py]
        OC_PERMS[render-opencode-permissions.py]
        OC_TMPL[render-opencode-template.py]
    end

    RENDER_PLAN --> OC_MCP --> OC_TMPL
    CONFIG --> OC_PERMS --> OC_TMPL

    subgraph F8["8. Auto-approval"]
        APPROVAL_RULES[approval_rules.py]
        PER_CLI_WRITERS["add-*-auto-approvals.py"]
    end

    RENDER_PLAN --> APPROVAL_RULES --> PER_CLI_WRITERS

    subgraph F9["9. MCP registry"]
        REG_RECORD[record fingerprints]
        REG_PRUNE[prune stale entries]
    end

    RENDER_PLAN --> REG_RECORD
    RENDER_PLAN --> REG_PRUNE

    subgraph F10["10. Cleanup"]
        CLEANUP_CORE[cleanup/core.py]
        HANDLERS[4 backend handlers]
        TRASH[Trash lifecycle]
    end

    CONFIG --> CLEANUP_CORE --> HANDLERS --> TRASH

    BASH_ORCH --> CLI_CONFIGS
    AGENT_SETUP --> CLI_CONFIGS
    SKILL_SH --> CLI_CONFIGS
    HOOK_CFG --> CLI_CONFIGS
    OC_TMPL --> CLI_CONFIGS
    PER_CLI_WRITERS --> CLI_CONFIGS

    CLI_CONFIGS[/"CLI config files
    ~/.claude/ ~/.gemini/
    ~/.codex/ ~/.config/opencode/"/]
```

---

## Conventions and legend

**Diagram conventions used throughout this document:**

| Symbol | Meaning |
|:-------|:--------|
| Rounded rectangle | Processing step (function or script) |
| Cylinder / database shape | Persistent data store |
| Parallelogram | File on disk (config, generated artifact) |
| Diamond | Decision / conditional branch |
| Dashed border | Optional / conditional path |
| Arrow label | Data format or key being passed |

**CLI abbreviations:**

| Abbreviation | Full name |
|:-------------|:----------|
| CC | Claude Code |
| GC | Gemini CLI |
| CX | Codex |
| OC | OpenCode |

**File location shorthand:**

| Shorthand | Expands to |
|:----------|:-----------|
| `~/.claude/` | User-scoped Claude Code config directory |
| `~/.gemini/` | User-scoped Gemini CLI config directory |
| `~/.codex/` | User-scoped Codex config directory |
| `~/.config/opencode/` | User-scoped OpenCode config directory |
| `~/.config/bureau/` | Bureau's user-scoped state directory |

---

## 1. Config resolution

Bureau loads configuration from four sources in a strict merge order. Later sources override earlier ones. After merging, placeholders are expanded and the result is validated before any downstream flow consumes it.

```mermaid
flowchart LR
    DY["defaults.yml
    (package defaults)"]
    BY[".bureau.yml
    (project, CWD walk-up)"]
    LY["local.yml
    (personal, gitignored)"]
    EV["Environment
    variables"]

    DY -->|"layer 1"| DM[deep_merge]
    BY -->|"layer 2"| DM
    LY -->|"layer 3"| DM
    DM --> RAW["Raw merged dict"]

    EV -->|"layer 4: path_to overrides"| ENVAPP[Apply env overrides]
    RAW --> ENVAPP

    ENVAPP --> DERIVE["Derive paths
    (workspace -> serena_memories_root,
    mcp_clones resolved from main repo root)"]

    DERIVE --> CACHE["LRU-cached Config dict
    (get_config)"]

    CACHE --> EXPAND["expand_placeholders
    (env vars first, then
    dot-notation config keys)"]

    CACHE --> VALIDATE["validate_config
    (required schema check,
    runtime invariants)"]

    EXPAND --> CONSUMERS["Downstream flows
    (MCP catalog, roles,
    skills, cleanup, etc.)"]

    VALIDATE --> CONSUMERS
```

**Key details:**

- `find_project_config()` walks up from CWD to locate `.bureau.yml`, skipping the Bureau repo root itself
- `deep_merge()` recursively merges dicts; non-dict values are replaced wholesale (lists are not merged)
- `expand_placeholders()` loops until a fixed point (no new expansions), with env vars taking priority over config key paths
- Config is LRU-cached (`@lru_cache(maxsize=1)`) and cleared via `clear_config_cache()` for testing

**Cross-references:** All subsequent flows consume the output of this flow via `get_config()` or its convenience accessors.

<!-- GENERATED:config-resolution -->
<!-- /GENERATED -->

---

## 2. MCP catalog and setup

The MCP catalog resolves which dependencies, runtime services, and client configs are active, then a setup plan JSON drives the bash orchestration script that provisions Docker containers, HTTP processes, and per-CLI MCP entries.

```mermaid
flowchart TB
    CONFIG[(Merged Config)] --> RESOLVE["resolve_mcp_catalog()
    operations/mcp_catalog.py"]

    subgraph resolve["Catalog resolution"]
        direction TB
        DEPS["Filter enabled dependencies
        (git_repo, file)"] --> EXPAND_D["Expand placeholders
        in dependency configs"]
        EXPAND_D --> SVC["Filter enabled services
        (check dependency deps met)"]
        SVC --> TOPO["Topological sort
        (inter-service depends_on)"]
        TOPO --> EXPAND_S["Expand placeholders
        in service configs"]
        EXPAND_S --> CLIENT["Filter enabled client_configs
        (check requires_env, depends_on)"]
        CLIENT --> EXPAND_C["Expand placeholders
        per client transport"]
        EXPAND_C --> METHODS["Apply allowed_methods
        (filesystem server only)"]
    end

    RESOLVE --> resolve
    resolve --> CATALOG[/"Resolved catalog
    {dependencies, services,
    client_configs}"/]

    CATALOG --> RENDER["render_setup_plan()
    tools/scripts/render-mcp-setup.py"]
    CONFIG --> RENDER

    RENDER --> PLAN[/"Setup plan JSON
    (per-CLI client_configs,
    auto_approved lists)"/]

    PLAN --> TOOLS["set-up-tools.sh"]

    subgraph bash_orch["Bash orchestration"]
        direction TB
        DEP_LOOP["Prepare dependencies
        (git clone, file touch)"]
        DEP_LOOP --> DOCKER_CHECK{"Docker services
        in plan?"}
        DOCKER_CHECK -->|yes| RANCHER["ensure_rancher_running()"]
        DOCKER_CHECK -->|no| SVC_LOOP
        RANCHER --> SVC_LOOP["Start services
        (dependency order)"]
        SVC_LOOP --> AGENT_LOOP["Per-agent MCP registration
        (add_http_mcp_to_agent /
        add_stdio_mcp_to_agent)"]
        AGENT_LOOP --> POST["apply_claude_post_config()
        (settings.json env injection)"]
    end

    TOOLS --> bash_orch

    bash_orch --> CC_CFG["~/.claude/settings.json
    ~/.claude.json"]
    bash_orch --> GC_CFG["~/.gemini/settings.json"]
    bash_orch --> CX_CFG["~/.codex/config.toml"]
    bash_orch --> OC_CFG["~/.config/opencode/opencode.json"]
```

**Key details:**

- `render_setup_plan()` fans out `client_configs` into per-CLI dicts, respecting `disabled_for` and per-CLI client overrides (with `default` as fallback)
- Service startup order is determined by topological sort on `depends_on.services` edges
- Each per-CLI MCP addition is idempotent: existing entries are skipped (grep-based detection)
- Codex HTTP transport does not support custom headers; servers requiring headers must use `stdio` for Codex

**Cross-references:** [9. MCP registry management](#9-mcp-registry-management) records fingerprints after this flow completes. [7. OpenCode pipeline](#7-opencode-pipeline) uses the setup plan for OpenCode-specific rendering. [8. Auto-approval configuration](#8-auto-approval-configuration) uses the setup plan's `auto_approved` lists.

<!-- GENERATED:mcp-catalog-setup -->
<!-- /GENERATED -->

---

## 3. Role setup

The role system resolves which agent roles are enabled per CLI, then wires them into the correct filesystem locations: slash commands for Claude Code, launcher scripts for Codex/Gemini, and filtered symlinks for OpenCode.

```mermaid
flowchart TB
    CONFIG[(Merged Config)] --> ROLES_CAT["resolve_roles_catalog()
    operations/roles_catalog.py"]

    subgraph catalog["Per-CLI role resolution"]
        direction TB
        ENABLED{"enabled = 'all'
        or list?"}
        ENABLED -->|all| DISCOVER["Discover *.md files
        in CLI's source dir"]
        ENABLED -->|list| FILTER_EN["Filter to enabled set"]
        DISCOVER --> FILTER_DIS["Apply disabled filter
        (takes precedence)"]
        FILTER_EN --> FILTER_DIS
    end

    ROLES_CAT --> catalog
    catalog --> ROLE_LIST[/"Filtered role names
    + source_path per CLI"/]

    ROLE_LIST --> SETUP["set-up-agents.sh"]

    subgraph agent_setup["Agent setup steps"]
        direction TB
        STEP1["Step 1: Claude Code subagents
        Symlink agents/claude-subagents/ ->
        ~/.claude/agents/bureau-agents/"]
        STEP2["Step 2: Per-CLI launchers"]
        STEP1 --> STEP2
    end

    SETUP --> agent_setup

    subgraph launchers["Per-CLI launcher creation"]
        CC_SLASH["Claude Code:
        set-up-claude-slash-commands.sh
        -> ~/.claude/commands/*.md"]
        CX_LAUNCH["Codex:
        set-up-codex-role-launchers.sh
        -> ~/.local/bin/codex-*"]
        GC_LAUNCH["Gemini CLI:
        set-up-gemini-role-launchers.sh
        -> ~/.local/bin/gemini-*"]
        OC_LINKS["OpenCode:
        Per-role symlinks ->
        ~/.config/opencode/agent/bureau-agents/"]
    end

    STEP3 --> launchers
```

**Key details:**

- Two distinct source directories: `agents/claude-subagents/` (Claude-specific, with frontmatter) and `agents/role-prompts/` (all other CLIs)
- `disabled` list always takes precedence over `enabled` (even when `enabled: all`)
- OpenCode uses individually symlinked role files (not a directory symlink) to respect per-role filtering
**Cross-references:** None.

<!-- GENERATED:role-setup -->
<!-- /GENERATED -->

---

## 4. Skill setup

Skills are structured multi-step protocols (e.g., `assess-mode`) that agents activate automatically when they recognise a matching task. The skill flow resolves which skills are enabled, generates a JSON config, then installs symlinks into each CLI's user-scoped skills directory.

```mermaid
flowchart LR
    CONFIG[(Merged Config)] --> SKILL_CAT["resolve_skills_catalog()
    operations/skills_catalog.py"]

    subgraph resolution["Skill resolution"]
        direction TB
        EN{"enabled = 'all'
        or list?"}
        EN -->|all| SCAN["Scan source dirs
        for skill subdirs"]
        EN -->|list| FILT["Filter to enabled set"]
        SCAN --> DIS["Apply disabled filter"]
        FILT --> DIS
    end

    SKILL_CAT --> resolution
    resolution --> NAMES[/"Canonical skill names
    [assess-mode, ...]"/]

    NAMES --> GEN["generate-skills-config.py"]
    GEN --> JSON[/"skills-config.generated.json
    {skills: [{name, source_path}, ...],
    source_roots: [...]}"/]

    JSON --> SH["set-up-skills.sh"]

    subgraph install["Installation per CLI"]
        direction TB
        CLEAN["Remove Bureau-owned symlinks
        and legacy bureau-* entries"]
        CLEAN --> LINK["Symlink each skill's
        source dir into CLI skills dir"]
    end

    SH --> install

    install --> CC_SK["~/.claude/skills/<skill-name>"]
    install --> OC_SK["~/.config/opencode/skill/<skill-name>"]
    install --> CX_GC_SK["~/.agents/skills/<skill-name>
    (Codex + Gemini CLI)"]
```

**Key details:**

- Bureau removes only symlinks it owns at canonical names, plus legacy `bureau-*` entries left by older installs
- Skills are installed as symlinks pointing back to `protocols/context/static/skills/<skill-name>/` in the repo
- Each skill directory must contain a `SKILL.md` file (the protocol definition the agent reads)

**Cross-references:** [5. Protocol and context setup](#5-protocol-and-context-setup) is the parent script that calls skill setup.

<!-- GENERATED:skill-setup -->
<!-- /GENERATED -->

---

## 5. Protocol and context setup

This flow deploys protocol files (hub + spokes) to the user-scoped protocols directory, then configures SessionStart hooks in each CLI's settings so that agents receive Bureau context at the start of every session. Per-prompt reminder hooks are also installed. OpenCode uses a separate path via its native `instructions` array.

```mermaid
flowchart TB
    subgraph static_src["Protocol source files"]
        HUB_SRC["ops-hub.md"]
        subgraph spokes_src["ops/ (spoke files)"]
            S_SESSION["session-start.md"]
            S_ASSESS["task-assessment.md"]
            S_EXEC["task-execution.md"]
            S_COMPLETE["task-completion.md"]
            S_CODE_STD["code-standards.md"]
        end
    end

    CONFIG[(Merged Config)] --> PROTO_SH["set-up-protocols.sh"]
    static_src --> PROTO_SH

    PROTO_SH -->|"deploy"| PROTO_DIR["~/.config/bureau/protocols/
    (hub + spoke files,
    output-style.md, code-standards.md)"]

    PROTO_DIR --> HOOKS["configure-hooks.py"]
    CONFIG --> HOOKS

    subgraph hook_targets["SessionStart hook configuration"]
        CC_HOOK["Claude Code:
        ~/.claude/settings.json
        hooks.SessionStart → cat ops-hub.md"]
        GC_HOOK["Gemini CLI:
        ~/.gemini/settings.json
        hooks.SessionStart → cat output-style.md
        && cat ops-hub.md"]
        CX_HOOK["Codex:
        ~/.codex/hooks.json
        SessionStart → cat output-style.md
        && cat ops-hub.md"]
    end

    HOOKS --> hook_targets

    subgraph reminder_hooks["Per-prompt reminder hooks"]
        REMINDER["Each CLI receives a hook that
        echoes a short bureau-reminder
        on every prompt"]
    end

    HOOKS --> reminder_hooks

    subgraph opencode_path["OpenCode (separate path)"]
        OC_TMPL["render-opencode-template.py"]
        OC_INSTR["instructions array in
        opencode.json"]
    end

    PROTO_DIR --> OC_TMPL --> OC_INSTR
```

**Key details:**

- `set-up-protocols.sh` deploys hub + spoke files to `~/.config/bureau/protocols/`; default files are copied only on first run (when directory is empty or absent)
- `configure-hooks.py` writes SessionStart hooks into each CLI's settings, causing agents to `cat` the relevant protocol files at session start
- Per-prompt hooks echo a short `<bureau-reminder>` on every prompt to reinforce key directives
- OpenCode uses its native `instructions` array (populated by `render-opencode-template.py`) rather than hooks
- `bin/reset-protocols` restores defaults by re-copying from `protocols/context/static/`

**Cross-references:** This script also calls [4. Skill setup](#4-skill-setup) as a sub-step.

<!-- GENERATED:protocol-context-setup -->
<!-- /GENERATED -->

---

## 7. OpenCode pipeline

OpenCode requires a distinct configuration format. Three rendering scripts produce the MCP server entries, permission rules, and merged template that become OpenCode's `opencode.json`.

```mermaid
flowchart TB
    PLAN[/"Setup plan JSON
    (from render-mcp-setup.py)"/] --> OC_MCP["render-opencode-mcp.py
    -> MCP entries JSON (tmpfile)"]

    CONFIG[(Merged Config)] --> OC_PERMS["render-opencode-permissions.py
    -> Permissions JSON (tmpfile)"]

    TEMPLATE["protocols/config/templates/
    opencode.json"] --> OC_TMPL

    OC_MCP --> OC_TMPL["render-opencode-template.py
    --template --mcp --permissions
    --repo-root --output"]
    OC_PERMS --> OC_TMPL

    OC_TMPL --> GENERATED["protocols/config/generated/
    opencode.generated.json"]

    GENERATED --> MERGE["configure-opencode.py
    --target --generated
    (preserves user overrides)"]

    EXISTING["~/.config/opencode/
    opencode.json (existing)"] --> MERGE

    MERGE --> FINAL["~/.config/opencode/
    opencode.json (merged)"]
```

**Key details:**

- Rendering uses tmpfiles for intermediate JSON to avoid polluting the repo
- `configure-opencode.py` preserves user-added overrides while reconciling Bureau-managed `instructions` and `agent` entries in the existing `opencode.json`
- If any rendering step fails, the existing `opencode.json` is left unchanged (fail-safe)
- OpenCode MCP entries use `type: "remote"` (for HTTP) and `type: "local"` (for stdio), distinct from other CLIs

**Cross-references:** [2. MCP catalog and setup](#2-mcp-catalog-and-setup) produces the setup plan consumed here. [9. MCP registry management](#9-mcp-registry-management) records OpenCode's entries after this flow completes.

<!-- GENERATED:opencode-pipeline -->
<!-- /GENERATED -->

---

## 8. Auto-approval configuration

Each CLI has its own permission format for auto-approving MCP tool invocations and bash command prefixes. This flow translates a common input (the setup plan's approval lists) into per-CLI permission strings.

```mermaid
flowchart TB
    PLAN[/"Setup plan JSON"/] -->|"auto_approved.mcp_servers
    per CLI"| MCP_RULES

    PLAN -->|"auto_approved.bash
    .enabled, .ruleset"| BASH_RULES

    subgraph MCP_RULES["MCP tool auto-approval"]
        direction TB
        CC_MCP["add-claude-auto-approvals.py
        + Read rules for protocols dir"]
        GC_MCP["add-gemini-auto-approvals.py"]
        CX_MCP["add-codex-auto-approvals.py"]
    end

    subgraph BASH_RULES["Bash prefix approvals"]
        direction TB
        BUILDERS["approval_rules.py builders:
        build_claude_bash_rules()
        build_gemini_bash_rules()
        build_codex_rule_lines()
        build_opencode_bash_rules()"]
        BUILDERS --> CC_BASH["Claude: Bash(prefix:*)
        -> ~/.claude/settings.json"]
        BUILDERS --> GC_BASH["Gemini: run_shell_command(prefix)
        -> ~/.gemini/settings.json"]
        BUILDERS --> CX_BASH["Codex: prefix_rule(pattern, decision)
        -> write-codex-exec-policy.py"]
    end

    MCP_RULES --> CC_CFG["~/.claude/settings.json"]
    MCP_RULES --> GC_CFG["~/.gemini/settings.json"]
    MCP_RULES --> CX_CFG["~/.codex/config.toml"]
```

**Key details:**

- MCP auto-approval writes server names as `autoApprovedTools` (Claude/Gemini JSON) or config entries (Codex TOML)
- Claude also gets a `Read(~/.config/bureau/protocols/**)` rule for the protocols directory
- Bash rules use prefix matching only (no wildcards); if a prefix appears in both allow and deny, the CLI's native precedence applies (deny wins)
- All builders are idempotent: duplicate rules are not appended

**Cross-references:** [2. MCP catalog and setup](#2-mcp-catalog-and-setup) drives MCP approval lists. [1. Config resolution](#1-config-resolution) provides the `auto_approved` config section.

<!-- GENERATED:auto-approval-config -->
<!-- /GENERATED -->

---

## 9. MCP registry management

Bureau tracks which MCP servers it manages per CLI using fingerprint-based registry files. This enables safe pruning of entries that Bureau previously installed but are no longer desired, without touching user-modified entries.

```mermaid
sequenceDiagram
    participant SH as set-up-tools.sh
    participant REG as managed-mcp-registry.py
    participant FILE as ~/.config/bureau/internal/<br/>managed-mcps.{cli}.json
    participant CLI_CFG as CLI config file

    Note over SH: After MCP setup completes

    rect rgb(240, 248, 255)
        Note over SH,CLI_CFG: Prune phase (if prune_disabled_mcps=true)
        SH->>REG: --mode prune --cli {cli}<br/>--plan {plan} --registry {reg}<br/>--config {cli_cfg}
        REG->>FILE: load_registry()
        REG->>CLI_CFG: load_cli_entries()
        REG->>REG: For each server in registry<br/>not in current plan:<br/>normalize_entry() -> fingerprint_entry()<br/>Compare with recorded fingerprint
        REG-->>SH: {to_remove: [server_ids]}
        SH->>CLI_CFG: Remove matched servers<br/>(claude mcp remove / gemini mcp remove / etc.)
    end

    rect rgb(255, 248, 240)
        Note over SH,CLI_CFG: Record phase (always runs)
        SH->>REG: --mode record --cli {cli}<br/>--plan {plan} --registry {reg}<br/>--config {cli_cfg}
        REG->>CLI_CFG: load_cli_entries()
        REG->>REG: For each desired server:<br/>normalize_entry() -> fingerprint_entry()
        REG->>FILE: write_registry()<br/>{version, updated_at, servers: {id: {fingerprint}}}
    end
```

**Key details:**

- Fingerprints are SHA-256 hashes of normalized, JSON-serialized entry configs (sorted keys, compact separators)
- Normalization extracts a transport-agnostic representation per CLI (e.g., Claude's `type` field maps to `transport`)
- A server is only pruned if its current config fingerprint matches the recorded one (user modifications protect the entry)
- Registry files live at `~/.config/bureau/internal/managed-mcps.{cli}.json`

**Cross-references:** [2. MCP catalog and setup](#2-mcp-catalog-and-setup) calls prune before MCP registration and record after.

<!-- GENERATED:mcp-registry-management -->
<!-- /GENERATED -->

---

## 10. Cleanup system

Bureau's cleanup system uses an abstract handler pattern with four storage-specific backends. It runs automatically on `open-bureau` if enough time has passed, or manually via `uv run sweep`.

```mermaid
flowchart TB
    CONFIG[(Merged Config)] --> CORE["run_cleanup()
    operations/cleanup/core.py"]

    CORE --> VALIDATE["validate_config()"]
    VALIDATE -->|errors| ABORT["Return error dict"]
    VALIDATE -->|ok| STATE["load_state()
    .archives/state.json"]

    STATE --> INTERVAL{"Last run
    < min_interval
    ago?"}
    INTERVAL -->|"yes (unless --force)"| SKIP["Return skipped"]
    INTERVAL -->|no| HANDLER_LOOP

    subgraph HANDLER_LOOP["Per-handler loop"]
        direction TB
        HANDLER["handler.cleanup(retention)"]

        subgraph handler_steps["CleanupHandler.cleanup()"]
            direction TB
            CUTOFF["get_cutoff(retention)"] --> STALE["get_stale_items(cutoff)"]
            STALE --> EXPORT["export_items_to_trash(items)"]
            EXPORT --> DELETE["delete_items_from_storage(items)"]
        end

        HANDLER --> handler_steps
    end

    HANDLER_LOOP --> TRASH["empty_expired_trash()
    (items older than grace_period)"]
    TRASH --> SAVE["save_state()
    (update last_cleanup_run)"]

    subgraph backends["4 backend handlers"]
        CM["ClaudeMemHandler
        (SQLite DELETE + VACUUM)"]
        SR["SerenaHandler
        (move .md files to trash)"]
        QD["QdrantHandler
        (REST API scroll + delete)"]
        MM["MemoryMcpHandler
        (JSONL file rewrite)"]
    end

    HANDLER_LOOP --> backends
```

**Key details:**

- `CleanupHandler` is the abstract base class; subclasses implement `get_stale_items()`, `export_items_to_trash()`, `delete_items_from_storage()`, and `_wipe()`
- Retention is per-backend (from `retention_period_for` config); `"always"` skips cleanup for that backend
- Deleted items go to `.archives/trash/` with a configurable grace period before permanent deletion
- The `wipe` command (`uv run sweep --wipe <storage>`) is a separate code path that erases all data (optionally with backup)
- `CleanupError` is the expected exception type; raw exceptions are caught and reported as error dicts

**Cross-references:** [1. Config resolution](#1-config-resolution) provides retention periods and paths.

<!-- GENERATED:cleanup-system -->
<!-- /GENERATED -->

---

## Generated table format

The extraction script (`scripts/extract-flow-docs.py`) produces tables with the following columns for each function entry:

| Column | Description |
|:-------|:-----------|
| **Function** | Fully qualified name (e.g., `operations.mcp_catalog.resolve_mcp_catalog`) |
| **Module** | Source file relative to repo root |
| **Signature** | Parameter names and types (from type hints) |
| **Purpose** | First line of the docstring |
| **Inputs** | Parameters with their types and brief descriptions (from docstring Args section) |
| **Output** | Return type and description (from docstring Returns section) |
| **Side effects** | File writes, network calls, state mutations (from docstring or annotation) |
| **Called by** | Parent function(s) or script(s) that invoke this function |
| **Calls** | Child function(s) this function invokes |
| **Flow** | Which data flow section(s) this function participates in |

Tables are sorted by call order within each flow section.

**Example generated row:**

| Function | Module | Signature | Purpose | Inputs | Output | Side effects | Called by | Calls | Flow |
|:---------|:-------|:----------|:--------|:-------|:-------|:-------------|:---------|:------|:-----|
| `resolve_mcp_catalog` | `operations/mcp_catalog.py` | `(config: Mapping, env: Mapping \| None) -> dict` | Resolve enabled MCP entries from catalog config | `config`: merged Bureau config; `env`: environment variables | Dict with `dependencies`, `client_configs`, `services` | None | `render_setup_plan()` | `expand_placeholders()`, `_apply_allowed_methods()` | MCP catalog + setup |
