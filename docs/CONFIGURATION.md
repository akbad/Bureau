# Configuration reference

Bureau uses a YAML-based configuration system with a four-tier hierarchy that allows package defaults, project-level sharing, and personal overrides.

> [!IMPORTANT]
>
> **[`open-bureau`](../bin/open-bureau) <ins>must</ins> be re-run after editing any config values** in *any* of [the configuration sources used by Bureau](#configuration-sources-and-precedence).

***Contents***:

- [Configuration sources and precedence](#configuration-sources-and-precedence)
  - [When to use each file](#when-to-use-each-file)
- [Configuration settings](#configuration-settings)
  - [`agents`](#agents)
  - [`auto_approved`](#auto_approved)
  - [`prune_disabled_mcps`](#prune_disabled_mcps)
  - [`mcp`](#mcp)
  - [`skills`](#skills)
  - [`protocols`](#protocols)
  - [`assess_mode`](#assess_mode)
  - [`roles`](#roles)
  - [`retention_period_for`](#retention_period_for)
  - [`cleanup`](#cleanup)
  - [`trash`](#trash)
  - [`startup_timeout_for`](#startup_timeout_for)
  - [`path_to`](#path_to)
- [Environment variable overrides](#environment-variable-overrides)
  - [Direct config overrides](#direct-config-overrides)
  - [API keys and placeholder expansion](#api-keys-and-placeholder-expansion)
- [Examples](#examples)
  - [Disable specific CLIs locally](#disable-specific-clis-locally)
  - [Customize available agent roles](#customize-available-agent-roles)
  - [Enable MCP tool auto-approval](#enable-mcp-tool-auto-approval)
  - [Keep memories longer](#keep-memories-longer)
  - [Use different workspace directory](#use-different-workspace-directory)
  - [Change MCP ports to avoid conflicts](#change-mcp-ports-to-avoid-conflicts)
  - [Customize installed skills](#customize-installed-skills)
  - [Provide custom coding standards](#provide-custom-coding-standards)
  - [Provide a custom output style](#provide-a-custom-output-style)
  - [Configure the assess mode skill](#configure-the-assess-mode-skill)
- [Agent context files](#agent-context-files)
- [Related commands](#related-commands)



## Configuration sources and precedence

Configuration is loaded and merged in this order (later sources override earlier):

| Priority | File | Purpose | Tracked by git? |
|:---------|:-----|:--------|:------------------|
| 1 **(lowest)** | [`defaults.yml`](/defaults.yml) | All git-tracked package defaults (ships with Bureau) | Yes |
| 2 | `.bureau.yml` | Optional project-level config (discovered by walk-up from working directory) | Yes (in *your* project) |
| 3 | `local.yml` | Personal overrides | No |
| 4 **(highest)** | Environment variables | Runtime overrides *(should be used rarely; for more persistent personal overrides, use `local.yml`)* | N/A |

### When to use each file

#### `defaults.yml`

- This is the **single source of all git-tracked defaults that ship with Bureau.**
- It contains examples of how to set config values (to use as exemplars to follow when overriding them in `.bureau.yml` or `local.yml`).

#### `.bureau.yml`

- Optional project-level config file discovered by walking up from the current working directory (like ESLint, Prettier, or Ruff configs).
- Can override any setting from `defaults.yml`.
- Shareable via git: commit it to your project repo so all team members using Bureau get the same project-specific settings.
- Typical uses: project-specific workspace paths, retention periods, enabled agents, MCP catalog entries, or custom tool settings.

#### `local.yml`

Create and write to this file for personal overrides that shouldn't be shared, e.g.:

- custom workspace paths
- custom retention periods for memories (configured per-MCP)
- disabling Bureau configuration for agent CLIs you don't use

## Configuration settings

### `agents`

**File:** `defaults.yml`

List of CLI agents that Bureau should configure during setup.

```yaml
agents:
  - claude    # Claude Code
  - gemini    # Gemini CLI
  - codex     # OpenAI Codex CLI
  - opencode  # OpenCode
```

Remove an agent from the list to skip configuring it. Note that the CLI's config directory must also exist (e.g., `~/.claude/` for Claude Code).

### `auto_approved`

Controls auto‑approvals for MCP tools and Bash command prefixes.

```yaml
auto_approved:
  mcps: false
  bash:
    enabled: true
    ruleset:
      allow:
        - "git status"
        - "npm run test"
      deny:
        - "rm"
        - "git commit"
```

**Notes:**
- Prefix matching only; no wildcards in the canonical list.
- If a prefix appears in both lists, the CLI's native precedence applies (i.e., `deny` wins).
- Multi‑word prefixes are preserved via the setup plan JSON (do not rely on `get-config` output for these).
- `auto_approved.mcp_tools` and `auto_approved.bash` are independent; you can enable either or both.

### `prune_disabled_mcps`

When `true`, Bureau removes MCP entries that were previously managed by Bureau but are no longer desired
(disabled or removed). Removals are guarded by per‑CLI registry fingerprints so user‑modified entries
aren't touched.

- Registry location: `~/.config/bureau/internal/managed-mcps.<cli>.json`
- Only entries whose current CLI config still matches the recorded fingerprint are removed.
- Bureau still refreshes the registry after setup even when this is `false`, so future runs can
  clean safely.

### `mcp`

MCP catalog configuration.

**Cross-cutting conventions:**

- **Canonical IDs:** map keys serve as *canonical IDs* for both `mcp.services` and `mcp.client_configs`.

  - Do **not** add `name` fields; these cause needless duplication and drift.

- **Placeholder expansion:** all string fields support `${...}` expansion.

  - **Expansion order:** OS environment variables first, then config key paths (e.g. `${path_to.workspace}`, `${mcp.services.qdrant_mcp.port}`).
  - Unknown placeholders remain untouched.
  - **Environment variables for MCP servers:** 
      - To pass environment variables to an MCP server process, add them as `env` entries in the server's client config. 
      - The **values** in these `env` entries can themselves contain `${...}` placeholders that get resolved from your OS environment at config-load time before being passed to the MCP server.
      - **Example:**

          ```yaml
          mcp:
            client_configs:
              context7:
                clients:
                  default:
                    transport: http
                    url: https://api.context7.dev/mcp
                    env:
                      CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"  # ← Expanded from your shell's $CONTEXT7_API_KEY
          ```

- **Dependency semantics:**

  - `depends_on.services` is a list of service IDs.
  - A service is considered ready only after its `healthcheck` succeeds (if present).
  - Startup order is topological: servers with `depends_on.services` are skipped if any dependency is disabled or missing.

- **Unknown keys:** unknown keys are preserved during resolution to allow future/custom extensions.
- **Enabled by default:** dependencies, runtime services, and client configs are all **enabled by default** when `enabled` is omitted.

  - **Adding an entry to any MCP bucket is sufficient to activate it on the next `open-bureau` run.**
  - You *must* set `enabled: false` explicitly to define an entry without activating it.
- **No-key MCPs:** local stdio MCPs can omit `requires_env`; they remain available even when cloud/search API keys are missing.

#### Runtime invariants (not fully type-enforced)

Bureau uses permissive `TypedDict` schemas in code for config loading, which means some value-dependent rules cannot be expressed purely in the Python type system. These invariants are validated by runtime logic and conventions.

| Where | Condition | Required / expected fields | Notes |
|:--|:--|:--|:--|
| `mcp.dependencies.<id>` | `kind: git_repo` | `repo_url`, `path` (optional: `branch`, `post_clone`) | Type checker cannot enforce `kind` → required-field mapping |
| `mcp.dependencies.<id>` | `kind: file` | `path` | Same discriminator limitation |
| `mcp.services.<id>` | `kind: docker_container` | `image`, `host_port`, `container_port` (optional: `container_name`, `host_bind`, `mounts`, `recreate_on_setup`) | Docker-only fields are flat in schema |
| `mcp.services.<id>` | `kind: http_process` | `port`, `command` (optional: `env`) | Process-only fields share same flat schema |
| `mcp.services.<id>.healthcheck.mcp_tool` | Present | `url`, `tool`, `arguments` (optional: `expected_server_name`) | Runs an end-to-end MCP tool probe after TCP/HTTP readiness |
| `mcp.client_configs.<id>.clients.<client>` | `transport` value | `http/sse` expect `url`; `stdio` expects `command` (optional transport-specific extras) | Transport-specific requirements are runtime-validated |
| `mcp.client_configs.<id>.tools` | Present | `list<string>` | Used for Codex per-tool auto-approval metadata |
| `roles` | `enabled` as string | Only documented sentinel values (for example `all`) are meaningful | Typed as `list[str] \| str` for flexibility |
| `path_to` | `workspace` present | `serena_memories_root` may be derived if unset | Derived behavior, not schema-required |
| `path_to` | `mcp_clones` or `bureau_repo` is relative | `mcp_clones` resolves against the shared main repo root; `bureau_repo` resolves against the active Bureau worktree root | Normalization rule, not schema-required |
| Named lookups in helpers | Service/config IDs must exist (`qdrant_mcp`, `memory`, `claude_mem_storage`) | Expected nested keys depend on helper | Name-based contracts are conventional and documented here |

When adding new discriminator-based config sections, document the `value -> required fields` mapping in this section and enforce it in runtime validators.

**Top-level structure:**

- `auto_approved` (object):
  - `mcp_tools` (bool, default: `false`): Whether MCP tools should be auto‑approved by setup scripts.
  - `bash` (object):
    - `enabled` (bool, default: `false`): Whether Bash allow/deny rules should be applied.
    - `ruleset` (object):
      - `allow` (list\<string\>): Literal command prefixes to allow.
      - `deny` (list\<string\>): Literal command prefixes to deny.
- `prune_disabled_mcps` (bool, default: `false`): When `true`, Bureau prunes previously managed MCPs that are no longer desired, using per‑CLI registry fingerprints to avoid removing user‑modified entries.
- `mcp` (object):
  - `dependencies` (map\<string, Dependency\>): Non-daemon prerequisites (git repos, file storage) prepared before services.
  - `services` (map\<string, Service\>): Managed runtime services (containers, processes) that may depend on dependencies.
  - `client_configs` (map\<string, ClientConfig\>): MCP servers exposed to CLIs.

#### <ins>`mcp.dependencies`</ins>

Defines non-daemon prerequisites (git repos, file storage) that are prepared before services. Dependencies may use `requires` to order themselves, then services (which may depend on them) are started.

**Config schema** for each entry in `mcp.dependencies.<dependency_id>`:

- `enabled` (bool, default: `true`): Skip dependency if `false`.
- `kind` (string, required): One of `git_repo`, `file`.
- `requires` (`list<string>`, optional): Dependency IDs that must be prepared first.
- All kind-specific fields (see below).

**Dependency kinds:**

- `git_repo`:
  - `repo_url` (string, required)
  - `branch` (string, optional)
  - `path` (string, required): Clone destination.
  - `post_clone` (`list<list<string>>`, optional): Commands run in `path` after clone/update. Use this for pinned checkouts, local builds, or other reproducible setup steps.
- `file`:
  - `path` (string, required): File path used by cleanup and other tools.

**Example:**
```yaml
mcp:
  dependencies:
    sourcegraph_repo:
      kind: git_repo
      repo_url: https://github.com/user/repo.git
      branch: main
      path: ${path_to.mcp_clones}/repo
      post_clone:
        - ["uv", "sync"]

    claude_mem_storage:
      kind: file
      path: ~/.claude-mem/claude-mem.db
```

#### <ins>`mcp.services`</ins>

Defines managed runtime services that Bureau starts (containers, local HTTP processes). Services can depend on dependencies via `depends_on.dependencies`.

**Config schema** for each entry in `mcp.services.<service_id>`:

- `enabled` (bool, default: `true`): Skip service if `false`.
- `kind` (string, required): One of `docker_container`, `http_process`; see kind-specific fields below.
- `depends_on` (object, optional):
  - `services` (list\<string\>): Service IDs that must be started and pass `healthcheck` first.
  - `dependencies` (list\<string\>): Dependency IDs that must be prepared first.
- `healthcheck` (object, optional):
  - `tcp` (int): Port to probe for readiness.
  - `http` (string): URL that must return a successful HTTP response.
  - `mcp_tool` (object): End-to-end MCP probe for streamable HTTP services.
    - `url` (string, required): MCP endpoint to call.
    - `expected_server_name` (string, optional): Expected `initialize.result.serverInfo.name`.
    - `tool` (string, required): Tool that must be listed and callable.
    - `arguments` (object, required): JSON object passed to the tool call.
- `env` (map\<string,string\>, optional): Environment vars for process services.
- `command` (list\<string\>, optional): Command array (executable + args) for process services.
- `settings` (map\<string, any\>, optional): Service-specific data used for templating.

Bureau records resolved `http_process` service fingerprints in `~/.config/bureau/internal/managed-services.json`. A matching managed listener is reused only after healthchecks pass; stale managed listeners are restarted; healthy unregistered listeners are adopted for the current run and marked for restart on the next run; unhealthy unregistered listeners are left untouched and setup fails closed.

**Kind-specific fields:**

- `docker_container`:
  - `container_name` (string, optional): Docker container name.
  - `image` (string, required): Docker image ref.
  - `host_bind` (string, optional): Host interface for published ports. Use `127.0.0.1` for localhost-only services.
  - `host_port` (int, required): Host port bound to container.
  - `container_port` (int, required): Container port to expose.
  - `recreate_on_setup` (bool, optional): Remove and recreate an existing container on setup. Use this when a mounted config file is generated by Bureau and only read at container startup.
  - `mounts` (`list<object>`, optional):
    - `host_path` (string, required)
    - `container_path` (string, required)
    - `type` (`directory` or `file`, optional, default: `directory`)
- `http_process`:
  - `port` (int, required): Port the process should listen on.
  - `command` (`list<string>`, required): Command array to launch server.
  - `env` (`map<string,string>`, optional)

**Example:**
```yaml
mcp:
  services:
    sourcegraph_mcp:
      kind: http_process
      port: 8783
      depends_on:
        dependencies: [sourcegraph_repo]
      command:
        - uv
        - --directory
        - ${mcp.dependencies.sourcegraph_repo.path}
        - run
        - sourcegraph-mcp
```

#### <ins>`mcp.client_configs`</ins>

Defines MCP servers exposed to CLIs, including per‑CLI client overrides. Servers can depend on runtime services and dependencies via `depends_on`.

**Config schema** for each entry in `mcp.client_configs.<server_id>`:

- `enabled` (bool, default: `true`): Skip server if `false`.
- `requires_env` (`list<string>`, optional): If any env var is missing/empty, the server is skipped.
- `tools` (`list<string>`, optional): Tool names exposed by this MCP server. Bureau uses this metadata for Codex per-tool auto-approval.
- `depends_on` (object, optional):
  - `services` (list\<string\>): Service IDs that must be enabled/resolved for the server to be included.
  - `dependencies` (list\<string\>): Dependency IDs that must be enabled/resolved for the server to be included.
- `clients` (`map<string, Client>`, required): Per‑CLI client configs.
  - `clients.default` (Client, optional but strongly recommended): Used by all CLIs unless a CLI override exists.
  - `clients.<cli>` (Client, optional): Overrides for `claude`, `gemini`, `codex`, `opencode`.
  - `clients.disabled_for` (`list<string>`, optional): Agent names to exclude from this server. Values should match entries in the top-level `agents` list. When listed, the agent does not receive this server, even if a `clients.<cli>` override exists.
- `npm_runtime` (object, optional): Opts a Node-based stdio MCP into Bureau's shared local npm runtime.
  - `packages` (`list<string>`, required when present): npm package specs installed into `${path_to.mcp_clones}/npm-tools` during setup.
  - `binaries` (`list<string>`, required when present): executable names expected under `node_modules/.bin`; missing binaries trigger a repair install during setup.
- `settings` (`map<string, any>`, optional): Server-level settings. Pass‑through; the renderer should not drop unknown keys.
- `storage_path` (string, optional): Server‑specific storage (used by cleanup, e.g. Memory MCP).

**Client** — each entry in `mcp.client_configs.<server_id>.clients.<client_id>`:

- `transport` (string, required): `http` or `stdio`.
- `url` (string, required for `http`): MCP HTTP endpoint.
- `headers` (`map<string,string>`, optional): HTTP headers (expanded).
- `command` (`list<string>`, required for `stdio`): Command array to launch MCP server.
- `env` (`map<string,string>`, optional): Environment variables to pass to the MCP server process. Values support `${...}` placeholder expansion from your OS environment.
- `timeout_ms` (int, optional): Per‑server tool timeout (Gemini).
- `startup_timeout_sec` (int, optional): Startup timeout (Codex).
- `tool_timeout_sec` (int, optional): Tool timeout (Codex).
- `post_config` (object, optional): CLI‑specific side effects, e.g.:
  - `claude_settings_env` (`map<string,string>`): Adds keys to `~/.claude/settings.json` under `.env`.

> [!NOTE]
> Codex HTTP does not support custom headers; use `clients.codex` with `stdio` for servers requiring headers (e.g. Context7).

> [!NOTE]
> `npm_runtime` is setup metadata only. CLIs still receive the resolved `clients.*.command` array, which should point at the shared local binaries under `${path_to.mcp_clones}/npm-tools/node_modules/.bin/...` rather than `npx`.

> [!TIP]
> Source-built Docker stdio MCPs should usually be modeled as a `git_repo` dependency with `post_clone` commands that pin and build the image, plus a `mcp.client_configs.<id>` entry whose stdio command runs `docker run --rm -i ...`. This keeps one-shot MCP processes out of the long-running `mcp.services` bucket.

#### Managed SearXNG and Bureau Search

By default, Bureau starts a localhost-only SearXNG container and exposes it through the `bureau-search` stdio MCP. Agents get semantic tools rather than one raw search endpoint:

- `bureau_search_web`
- `bureau_search_code`
- `bureau_search_packages`
- `bureau_search_research`

Bureau generates `~/.config/bureau/searxng/settings.yml` with JSON output enabled and Google / Google Scholar engines disabled by default.

To use your own SearXNG instance instead of Bureau's managed container:

```yaml
mcp:
  services:
    searxng:
      enabled: false
  client_configs:
    bureau-search:
      depends_on:
        services: []
      settings:
        searxng_url: http://127.0.0.1:8080
```

### `skills`


Controls which skills are installed by `protocols/scripts/set-up-skills.sh`.

```yaml
skills:
  enabled: all
  disabled: []
  sources:
    - path: protocols/context/static/skills
```

**Fields:**
- `enabled`: `all` or a list of canonical skill directory names to include.
- `disabled`: list of skill directory names to exclude.
- `sources`: list of directories to scan for skills.
  - `path`: absolute path or repo‑relative path.

This section controls normal catalog skills only. The generated `code-standards` skill is protocol-owned and is controlled by `protocols.code_standards`, not by `skills.enabled`, `skills.disabled`, or `skills.sources`.

> [!CAUTION]
> - `protocols/scripts/set-up-skills.sh` removes Bureau-owned skill symlinks before reinstalling.
> - Legacy `bureau-*` installs are also cleaned up during migration.
> - If a canonical skill path already exists as foreign content, setup warns and skips it instead of overwriting it.

### `protocols`

**Files:** `defaults.yml` (defaults), `.bureau.yml` (project overrides), `local.yml` (personal overrides)

Controls Bureau-owned protocol deployment, the source material for the generated `output-style.md` runtime artifact, and the detailed standards content for the generated `code-standards` skill.

```yaml
protocols:
  mode: replace
  output_style: default
  code_standards: default
```

**Fields:**
- `mode`: one of `replace`, `sync`, or `off`.
  - `replace`: always reconcile Bureau-owned protocol files without backup.
  - `sync`: always reconcile Bureau-owned protocol files and back up replaced or removed artifacts to `.bak`.
  - `off`: remove Bureau-owned protocol files, generated context wiring, and protocol hooks.
- `output_style`: one of `default`, `off`, or a non-empty list of file paths.
  - `default`: compile Bureau's shipped default source file into `~/.config/bureau/protocols/output-style.md`.
  - `off`: disable the output-style feature and remove the runtime artifact.
  - `[paths...]`: merge the listed Markdown files, in order, into the runtime artifact.
- `code_standards`: one of `default`, `off`, or a non-empty list of file paths.
  - `default`: compile Bureau's shipped default reference source into the protocol-owned generated `code-standards` skill.
  - `off`: disable both the startup `code-standards.md` mindset artifact and the generated `code-standards` skill.
  - `[paths...]`: merge the listed Markdown files, in order, into the generated `code-standards` skill.
  - `skills.enabled`, `skills.disabled`, and `skills.sources` do not control this built-in; if `code-standards` appears there, Bureau warns and ignores it.

Bureau ships with default sources at:

- `protocols/context/static/ops/output-style.md`
- `protocols/context/static/code-standards-reference.md`

Setup compiles the selected output-style sources into `~/.config/bureau/protocols/output-style.md`, deploys a fixed startup `code-standards.md` mindset artifact when code standards are enabled, and compiles the selected code-standards sources into the protocol-owned generated `code-standards` skill at `~/.config/bureau/generated/skills/code-standards/SKILL.md`. Bureau treats both directories as generated, Bureau-owned state.

**Path resolution:**
- Paths starting with `~` → expanded to `$HOME`
- Absolute paths (starting with `/`) → used as-is
- Relative paths → resolved from the Bureau repository root

**Runtime behavior:**
- Claude Code: Bureau installs a native Claude output style and selects it in `~/.claude/settings.json` when `protocols.output_style` is enabled
- Codex and Gemini: SessionStart hooks load `output-style.md` and `ops-hub.md` at session start when `protocols.output_style` is enabled
- Supported CLIs load the startup `code-standards.md` mindset artifact at session start only when `protocols.code_standards` is enabled
- Writing or editing code should activate the generated `code-standards` skill for the detailed standards layer
- OpenCode: generated config includes `output-style.md` only when the runtime artifact exists, and always includes `ops-hub.md`
- Changes take effect on a new session after re-running `bin/open-bureau`

### `assess_mode`

**Files:** `defaults.yml` (defaults), `.bureau.yml` (project overrides), `local.yml` (personal overrides)

Runtime configuration for the [`assess-mode` skill](../protocols/context/static/skills/assess-mode/SKILL.md). These values are read by the skill at activation time to determine what to review. Standards for audit are configured via [`protocols.code_standards`](#protocols).

```yaml
assess_mode:
  default_target: git-diff
  default_diff: HEAD
```

**Fields:**
- `default_target`: how the skill determines what to review when the user doesn't specify explicit files. Currently only `git-diff` is supported.
- `default_diff`: the git ref to diff against when `default_target` is `git-diff`. Common values: `HEAD` (unstaged + untracked vs last commit), `main` (full branch diff), or any commit SHA.

### `roles`

**Files:** `defaults.yml` (defaults), `.bureau.yml` (project overrides), `local.yml` (personal overrides)

Controls which agent roles are available when launching CLIs **directly** through their native features (slash commands for Claude Code, launcher scripts for Codex/Gemini, auto-discovery for OpenCode).

```yaml
roles:
  enabled:
    - architect
    - code-reviewer
    - testing
    - migration-refactoring
  disabled: []
  sources:
    - path: agents/role-prompts        # For Codex, Gemini, OpenCode
      cli: [codex, gemini, opencode]
    - path: agents/claude-subagents    # For Claude Code (has frontmatter)
      cli: [claude]
```

**Fields:**
- `enabled`: `all` or a list of agent role names to include. Agent names correspond to role file stems (e.g., `architect` for `architect.md`).
- `disabled`: List of agent role names to exclude (takes precedence over `enabled`).
- `sources`: List of directories to scan for agent role prompts, with per-CLI mappings.
  - `path`: Relative path from repo root to agent role directory.
  - `cli`: List of CLIs that should use this source directory.

**How setup scripts use this:**

| CLI | Native Feature | Setup Script | Result |
|:----|:---------------|:-------------|:-------|
| Claude Code | Slash commands | `agents/scripts/set-up-claude-slash-commands.sh` | Creates `~/.claude/commands/*.md` files |
| Codex | Launcher scripts | `agents/scripts/set-up-codex-role-launchers.sh` | Creates `~/.local/bin/codex-*` executables |
| Gemini CLI | Launcher scripts | `agents/scripts/set-up-gemini-role-launchers.sh` | Creates `~/.local/bin/gemini-*` executables |
| OpenCode | Auto-discovery | `agents/scripts/set-up-agents.sh` | Creates filtered symlinks in `~/.config/opencode/agent/bureau-agents/` |

**Default enabled agents:**

The default configuration enables 4 core agent roles, excluding all others:
- `architect` - Principal software architect for system design
- `code-reviewer` - Code quality and security audits
- `testing` - Test infrastructure and quality engineering
- `migration-refactoring` - Large-scale refactoring strategist

**Example: Enable all agents for native usage**

```yaml
# local.yml
roles:
  enabled: all
```

**Example: Enable specific agents with exclusions**

```yaml
# local.yml
roles:
  enabled: all
  disabled:
    - historian
    - incident-commander  # Exclude specific roles from "all"
```

**Example: Custom agent set**

```yaml
# local.yml
roles:
  enabled:
    - architect
    - observability
    - security-compliance
    - schema-evolution
  disabled: []
```

> [!NOTE]
> After modifying `roles` configuration, run `./bin/open-bureau` to regenerate slash commands, launchers, and symlinks. For Claude Code, the changes take effect immediately (run `/help` to see updated list). For Codex/Gemini launchers, you may need to restart your shell or run `hash -r` to refresh the command cache.

### `retention_period_for`

**File:** `defaults.yml`

Retention periods for each memory backend. Memories older than these thresholds are automatically moved to trash during cleanup.

```yaml
retention_period_for:
  claude_mem: 30d    # Claude-mem SQLite database
  serena: 90d        # Serena project memories
  qdrant: 180d       # Qdrant vector database
  memory_mcp: 365d   # Memory MCP knowledge graph
```

**Storage backends and cleanup methods:**

| Backend | Default retention period | Cleanup method |
|:--------|:--------|:---------------|
| `claude_mem` | 30d | SQLite DELETE + VACUUM |
| `serena` | 90d | Move `.md` files to trash |
| `qdrant` | 180d | REST API scroll + delete |
| `memory_mcp` | 365d | JSONL file rewrite |

**Duration format:** `<number><unit>` where unit is:
- `h` - hours (e.g., `24h`)
- `d` - days (e.g., `30d`)
- `w` - weeks (e.g., `2w`)
- `m` - months (e.g., `3m`)
- `y` - years (e.g., `1y`)
- `always` - disable cleanup for this storage

### `cleanup`

**File:** `defaults.yml`

Controls automatic cleanup behavior.

```yaml
cleanup:
  min_interval: 24h  # Minimum time between cleanup runs
```

Cleanup runs automatically on `./bin/open-bureau` if enough time has passed since the last run.

### `trash`

**File:** `defaults.yml`

Controls the soft-delete trash system.

```yaml
trash:
  grace_period: 30d  # Time before trash is permanently deleted
```

Deleted items go to `.archives/trash/` and remain recoverable until the grace period expires.

### `startup_timeout_for`

**File:** `defaults.yml`

Timeouts for startup operations (in seconds).

```yaml
startup_timeout_for:
  mcp_servers: 200     # MCP server startup timeout
  docker_daemon: 120   # Docker daemon startup timeout
```

Increase these values on slower machines.

### Concierge Telegram bot

**File:** `concierge/config/defaults/pipeline.yml`

The Telegram bot reads its configuration from the `telegram` section of the pipeline config:

```yaml
telegram:
  polling_timeout: 30        # seconds between long-poll requests
  typing_indicator: true     # send "typing..." while processing
  max_response_length: 4096  # Telegram message limit
```

The bot token is **always** loaded from the `BUREAU_TELEGRAM_TOKEN` environment variable and is never stored in config files. See [SETUP.md](SETUP.md#telegram-bot-setup-optional) for full setup instructions.

### `path_to`

**File:** `defaults.yml`

File and directory paths used by Bureau and its tools.

| Setting | Default | Description |
|:--------|:--------|:------------|
| `workspace` | `~/code` | Base workspace directory; other paths derive from this |
| `serena_memories_root` | (= `workspace`) | Root directory for scanning Serena memory files *(used for **Bureau-run cleanup only**)* |
| `mcp_clones` | `.mcp-servers/` | Clone location for MCP server source code |

> [!NOTE]
> 
> #### Paths automatically derived from `workspace`
> 
> When `workspace` is set, the following path is automatically derived from it (unless explicitly overridden):
>
> - `serena_memories_root` → same as `workspace`
> 
> This means you only need to configure `workspace` in `local.yml` to change all workspace-related paths at once.

#### YML example

```yaml
path_to:
  # User-tunable paths
  workspace: ~/code                 # Base workspace directory
  serena_memories_root: ~/code      # Root for scanning Serena memory files (used by Bureau-run cleanup only)
  mcp_clones: .mcp-servers/         # MCP server clone location (in repo root)
```

## Environment variable overrides

### Direct config overrides

Some configuration values can be overridden via environment variables:

| Environment Variable | Overrides | Description |
|:---------------------|:----------|:------------|
| `BUREAU_WORKSPACE` | `path_to.workspace` | Base workspace directory |
| `BUREAU_TELEGRAM_TOKEN` | — | Telegram bot token (required to start the Concierge bot; never stored in config files) |
| `BUREAU_TELEGRAM_USER_ID` | — | Telegram user ID (fallback when no wizard config exists) |

### API keys and placeholder expansion

Environment variables are also used for placeholder expansion in config strings. Any `${...}` placeholder in your config files first checks your **OS environment** (where you `export` variables in your shell) before falling back to config key paths.

**Common pattern for MCP API keys:**

```yaml
# In your config YAML
mcp:
  client_configs:
    tavily:
      clients:
        default:
          env:
            TAVILY_API_KEY: "${TAVILY_API_KEY}"  # Reads from your shell environment
```

**Required environment variables for remote/cloud MCPs:**

Some remote/cloud MCPs require API keys (even for their free versions). Set these in your shell environment for the best search/docs path. Local/no-key MCPs such as Bureau Search, Fetch, open-webSearch, and Crawl4AI do not need API keys.

| Env var name | Stores API key for... |
| --- | --- |
| `TAVILY_API_KEY` | Tavily web search |
| `BRAVE_API_KEY` | Brave web search |
| `CONTEXT7_API_KEY` | Context7 documentation lookup |

**How to set them:**

```bash
# In your ~/.zshrc, ~/.bashrc, or shell config:
export TAVILY_API_KEY="your-key-here"
export BRAVE_API_KEY="your-key-here"
export CONTEXT7_API_KEY="your-key-here"
```

## Examples

### Disable specific CLIs locally

If you only want Bureau to configure certain CLIs (and skip others), create `local.yml`:
```yaml
agents:
  - claude
  - gemini
  # codex and opencode omitted = not configured by Bureau
```

### Customize available agent roles

To enable a custom set of agents for native CLI usage:
```yaml
# local.yml
roles:
  enabled:
    - architect
    - frontend
    - security-compliance
    - testing
  disabled: []
```

Or to enable all agents except specific ones:
```yaml
# local.yml
roles:
  enabled: all
  disabled:
    - chaos-engineer
    - incident-commander
```

### Enable MCP tool auto-approval

```yaml
# local.yml
auto_approved:
  mcps: true
```

### Keep memories longer

```yaml
# local.yml
retention_period_for:
  claude_mem: 90d
  qdrant: 365d
  memory_mcp: always  # Always keep
```

### Use different workspace directory

```yaml
# local.yml
path_to:
  workspace: ~/Projects  # All other paths derive from this automatically
```

Or if you need to override individual paths:

```yaml
# local.yml
path_to:
  workspace: ~/Projects
  mcp_clones: ~/CustomMCPLocation  # Override the default (.mcp-servers/ in repo root)
```

### Change MCP ports to avoid conflicts

For example, if port `8780` (the default Qdrant DB listening port) is already in use on your device, you could do:

```yaml
# local.yml
mcp:
  services:
    qdrant_db:
      host_port: 9780
    qdrant_mcp:
      port: 9782
```

### Customize installed skills

```yaml
# local.yml
skills:
  enabled:
    - micro-mode
    - debugging
  disabled:
    - shadow-mode
  sources:
    - path: protocols/context/static/skills
```

### Provide custom coding standards

```yaml
# local.yml
protocols:
  code_standards:
    - ~/my-team/style-guide.md
    - ~/my-team/design-principles.md
```

### Provide a custom output style

```yaml
# local.yml
protocols:
  output_style:
    - ~/my-team/voice.md
    - ~/my-team/response-formatting.md
```

### Configure the assess mode skill

```yaml
# local.yml
assess_mode:
  default_diff: main    # Diff against main instead of HEAD
```

## Agent context files

**Location:** `~/.config/bureau/protocols/`

Bureau maintains a user-scoped directory of generated agent context files that are read at the start of every conversation. Setup reconciles this directory according to `protocols.mode`.

| File | Purpose |
|:-----|:--------|
| `output-style.md` | Compiled session-level output style used by all supported CLIs |
| `code-standards.md` | Fixed startup coding mindset artifact loaded when code standards are enabled |
| `ops-hub.md` | Routing table pointing to task-specific context (the hub) |
| `ops/session-start.md` | Memory retrieval, factual accuracy protocol |
| `ops/task-assessment.md` | Delegation mechanisms, headless CLI invocation |
| `ops/task-execution.md` | Tool selection, memory storage, limits |
| `ops/task-completion.md` | Approval gates, conversation handoff |

**How it works:**
- Setup (`bin/open-bureau`) reconciles Bureau-owned files in this directory according to `protocols.mode`
- Setup compiles `protocols.output_style` into `~/.config/bureau/protocols/output-style.md` unless the feature is `off`
- Setup deploys the fixed startup `code-standards.md` mindset artifact when `protocols.code_standards` is enabled
- Setup compiles `protocols.code_standards` into the protocol-owned generated `code-standards` skill under `~/.config/bureau/generated/skills/` unless the feature is `off`
- Codex and Gemini SessionStart hooks load `output-style.md` and `ops-hub.md` at session start when the output-style artifact exists; Claude uses the compiled file to install a native output style; OpenCode includes `output-style.md` only when the runtime artifact exists
- Customize these generated artifacts through config, not by editing files in `~/.config/bureau/protocols/` directly

> [!WARNING]
> If you customize Bureau's MCP catalog (add, remove, or reconfigure tools), the default spoke files, particularly `ops/task-execution.md`, may no longer accurately reflect your setup. Update your configuration inputs or replace the shipped sources and then re-run `bin/open-bureau`.

**Restoring defaults:**
```bash
bin/reset-protocols          # Interactive (prompts before overwriting)
bin/reset-protocols --force  # Non-interactive (overwrites without prompting)
```


## Related commands

| Command | Description |
|:--------|:------------|
| `./bin/open-bureau` | Start Bureau (runs cleanup if needed) |
| `./bin/bureau-prune` | Manually run cleanup |
| `./bin/bureau-empty-trash` | Permanently delete trash contents |
| `./bin/bureau-wipe <storage>` | Wipe a storage backend |
| `./bin/ensure-prereqs` | Verify prerequisites are installed |
| `./bin/reset-protocols` | Restore agent protocols files to defaults |
| `./bin/start-concierge-bot` | Start the Concierge Telegram bot |
