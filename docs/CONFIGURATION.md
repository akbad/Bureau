# Configuration reference

Bureau uses a YAML-based configuration system with a three-tier hierarchy that allows team-wide defaults while supporting personal overrides.

> [!IMPORTANT]
>
> **[`open-bureau`](../bin/open-bureau) <ins>must</ins> be re-run after editing any config values** in *any* of [the configuration sources used by Bureau](#configuration-sources-and-precedence).

***Contents***:

- [Configuration sources and precedence](#configuration-sources-and-precedence)
  - [When to use each file](#when-to-use-each-file)
- [Settings](#settings)
  - [`agents`](#agents)
  - [`mcp`](#mcp)
  - [`pal`](#pal)
  - [`retention_period_for`](#retention_period_for)
  - [`cleanup`](#cleanup)
  - [`trash`](#trash)
  - [`startup_timeout_for`](#startup_timeout_for)
  - [`port_for`](#port_for)
  - [`path_to`](#path_to)
  - [`endpoint_for`](#endpoint_for)
  - [`qdrant`](#qdrant)
- [Environment variable overrides](#environment-variable-overrides)
- [Examples](#examples)
  - [Disable specific CLI agents locally](#disable-specific-cli-agents-locally)
  - [Enable MCP tool auto-approval](#enable-mcp-tool-auto-approval)
  - [Keep memories longer](#keep-memories-longer)
  - [Use different workspace directory](#use-different-workspace-directory)
  - [Change ports to avoid conflicts](#change-ports-to-avoid-conflicts)
- [Security note for subagents spawned via PAL MCP's `clink`](#security-note-for-subagents-spawned-via-pal-mcps-clink)
  - [Solutions](#solutions)
- [Related commands](#related-commands)


## Configuration sources and precedence

Configuration is loaded and merged in this order (later sources override earlier):

| Priority | File | Purpose | Tracked by git? |
|:---------|:-----|:--------|:------------------|
| 1 (lowest) | **`charter.yml`** | Fixed system defaults | Yes |
| 2 | **`directives.yml`** | Streamlined collection of team-/user-oriented settings that are often tweaked | Yes |
| 3 | **`local.yml`** | Personal overrides | No |
| 4 (highest) | **Environment variables** | Runtime overrides *(should be used rarely; for more persistent personal overrides, use `local.yml`)* | N/A |

### When to use each file

#### `charter.yml`

- Don't edit unless you're changing upstream service endpoints or package conventions. 
- These are values that rarely (if ever) need changing.

#### `directives.yml` 

- *Read* to see examples of how to set config values (to then override in your `local.yml`).
- *Edit* to change team-wide defaults like retention periods, enabled agents, MCP catalog entries, or paths. 

    - Changes here affect everyone using *that* particular Bureau installation.

#### `local.yml` 

Create and write to this file for personal overrides that shouldn't be shared, e.g.: 

- custom workspace paths 
- custom retention periods for memories (configured per-MCP)
- disabling Bureau configuration for agent CLIs you don't use

## Settings

### `agents`

**File:** `directives.yml`

List of CLI agents that Bureau should configure during setup.

```yaml
agents:
  - claude    # Claude Code
  - gemini    # Gemini CLI
  - codex     # OpenAI Codex CLI
  - opencode  # OpenCode
```

Remove an agent from the list to skip configuring it. Note that the CLI's config directory must also exist (e.g., `~/.claude/` for Claude Code).


### `mcp`

**File:** `directives.yml`

MCP catalog configuration.

**Cross-cutting conventions:**

- **Canonical IDs:** map keys serve as *canonical IDs* for both `mcp.runtime_services` and `mcp.client_configs`.

  - Do **not** add `name` fields; these cause needless duplication and drift.

- **Placeholder expansion:** all string fields support `${...}` expansion.

  - **Expansion order:** OS environment variables first, then config key paths (e.g. `${path_to.workspace}`, `${mcp.runtime_services.qdrant_mcp.port}`).
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
  - `runtime_services` (map\<string, RuntimeService\>): Managed runtime services (containers, processes) that may depend on dependencies.
  - `client_configs` (map\<string, ClientConfig\>): MCP servers exposed to CLIs.

#### <ins>`mcp.dependencies`</ins>

**Files:** `charter.yml` (defaults), `directives.yml` (shared overrides), `local.yml` (personal overrides)

Defines non-daemon prerequisites (git repos, file storage) that are prepared before services. Dependencies cannot depend on other dependencies — they are prepared in sorted order first, then services (which may depend on them) are started.

**Config schema** for each entry in `mcp.dependencies.<dependency_id>`:

- `enabled` (bool, default: `true`): Skip dependency if `false`.
- `kind` (string, required): One of `git_repo`, `file`.
- All kind-specific fields (see below).

**Dependency kinds:**

- `git_repo`:
  - `repo_url` (string, required)
  - `branch` (string, optional)
  - `path` (string, required): Clone destination.
  - `post_clone` (`list<list<string>>`, optional): Commands run in `path` after clone/update.
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

#### <ins>`mcp.runtime_services`</ins>

**Files:** `charter.yml` (defaults), `directives.yml` (shared overrides), `local.yml` (personal overrides)

Defines managed runtime services that Bureau starts (containers, local HTTP processes). Services can depend on dependencies via `depends_on.dependencies`.

**Schema** — config values for each entry in `mcp.runtime_services.<service_id>`:

- `enabled` (bool, default: `true`): Skip service if `false`.
- `kind` (string, required): One of `docker_container`, `http_process`; see kind-specific fields below.
- `depends_on` (object, optional):
  - `services` (list\<string\>): Service IDs that must be started and pass `healthcheck` first.
  - `dependencies` (list\<string\>): Dependency IDs that must be prepared first.
- `healthcheck` (object, optional):
  - `tcp` (int): Port to probe for readiness.
- `env` (map\<string,string\>, optional): Environment vars for process services.
- `command` (list\<string\>, optional): Command array (executable + args) for process services.
- `settings` (map\<string, any\>, optional): Service-specific data used for templating.

**Kind-specific fields:**

- `docker_container`:
  - `container_name` (string, optional): Docker container name.
  - `image` (string, required): Docker image ref.
  - `host_port` (int, required): Host port bound to container.
  - `container_port` (int, required): Container port to expose.
  - `mounts` (`list<object>`, optional):
    - `host_path` (string, required)
    - `container_path` (string, required)
- `http_process`:
  - `port` (int, required): Port the process should listen on.
  - `command` (`list<string>`, required): Command array to launch server.
  - `env` (`map<string,string>`, optional)

**Example:**
```yaml
mcp:
  runtime_services:
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

**Files:** `charter.yml` (defaults), `directives.yml` (shared overrides), `local.yml` (personal overrides)

Defines MCP servers exposed to CLIs, including per‑CLI client overrides. Servers can depend on runtime services and dependencies via `depends_on`.

**Schema** — config values for each entry in `mcp.client_configs.<server_id>`:

- `enabled` (bool, default: `true`): Skip server if `false`.
- `requires_env` (`list<string>`, optional): If any env var is missing/empty, the server is skipped.
- `depends_on` (object, optional):
  - `services` (list\<string\>): Service IDs that must be enabled/resolved for the server to be included.
  - `dependencies` (list\<string\>): Dependency IDs that must be enabled/resolved for the server to be included.
- `clients` (`map<string, Client>`, required): Per‑CLI client configs.
  - `clients.default` (Client, optional but strongly recommended): Used by all CLIs unless a CLI override exists.
  - `clients.<cli>` (Client, optional): Overrides for `claude`, `gemini`, `codex`, `opencode`.
  - `clients.disabled_for` (`list<string>`, optional): Agent names to exclude from this server. Values should match entries in the top-level `agents` list. When listed, the agent does not receive this server, even if a `clients.<cli>` override exists.
- `settings` (`map<string, any>`, optional): Server-level settings (e.g. PAL disabled tools). Pass‑through; the renderer should not drop unknown keys.
- `storage_path` (string, optional): Server‑specific storage (used by cleanup, e.g. Memory MCP).

**Client** — each entry in `mcp.client_configs.<server_id>.clients.<client_id>`:

- `transport` (string, required): `http` or `stdio`.
- `url` (string, required for `http`): MCP HTTP endpoint.
- `headers` (`map<string,string>`, optional): HTTP headers (expanded).
- `command` (`list<string>`, required for `stdio`): Command array to launch MCP server.
- `env` (`map<string,string>`, optional): Environment vars for stdio servers.
- `timeout_ms` (int, optional): Per‑server tool timeout (Gemini).
- `startup_timeout_sec` (int, optional): Startup timeout (Codex).
- `tool_timeout_sec` (int, optional): Tool timeout (Codex).
- `post_config` (object, optional): CLI‑specific side effects, e.g.:
  - `claude_settings_env` (`map<string,string>`): Adds keys to `~/.claude/settings.json` under `.env`.

> [!NOTE]
> Codex HTTP does not support custom headers; use `clients.codex` with `stdio` for servers requiring headers (e.g. Context7).

### `skills`

**Files:** `directives.yml` (defaults), `local.yml` (personal overrides)

Controls which skills are installed by `protocols/scripts/set-up-skills.sh`.

```yaml
skills:
  enabled: all
  disabled: []
  sources:
    - path: protocols/context/static/skills
      prefix: bureau-
```

**Fields:**
- `enabled`: `all` or a list of skill directory names (without prefix) to include.
- `disabled`: list of skill directory names to exclude.
- `sources`: list of directories to scan for skills.
  - `path`: absolute path or repo‑relative path.
  - `prefix`: prefix applied to installed skill names (e.g. `bureau-`).

> [!CAUTION]
> - `protocols/scripts/set-up-skills.sh` removes **all** existing skills with the `bureau-` prefix from each CLI's skills directory before reinstalling. 
> - **Avoid naming your own custom skills `bureau-*`** unless you expect them to be wiped during setup.


### `assess_mode`

**Files:** `directives.yml` (defaults), `local.yml` (personal overrides)

Runtime configuration for the [`bureau-assess-mode` skill](../protocols/context/static/skills/assess-mode/SKILL.md). These values are read by the skill at activation time to determine what to review. Standards for audit are configured via the top-level [`code_standards`](#code_standards) setting.

```yaml
assess_mode:
  default_target: git-diff
  default_diff: HEAD
```

**Fields:**
- `default_target`: how the skill determines what to review when the user doesn't specify explicit files. Currently only `git-diff` is supported.
- `default_diff`: the git ref to diff against when `default_target` is `git-diff`. Common values: `HEAD` (unstaged + untracked vs last commit), `main` (full branch diff), or any commit SHA.

### `roles`

**Files:** `directives.yml` (defaults), `local.yml` (personal overrides)

Controls which agent roles are available when launching CLIs **directly** through their native features (slash commands for Claude Code, launcher scripts for Codex/Gemini, auto-discovery for OpenCode). This is **separate from** PAL's `clink` tool cross-CLI delegation, which is configured via [`pal.base-roles`](#palbase-roles).

```yaml
roles:
  enabled:
    - architect
    - debugger
    - code-reviewer
    - optimization
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

The default configuration enables 6 core agent roles, excluding all others:
- `architect` - Principal software architect for system design
- `debugger` - Deep debugging and root-cause analysis
- `code-reviewer` - Code quality and security audits
- `optimization` - Performance optimization specialist
- `testing` - Test infrastructure and quality engineering
- `migration-refactoring` - Large-scale refactoring strategist

**Distinction from PAL configuration:**

| Setting | Scope | Purpose |
|:--------|:------|:--------|
| `roles` | **Native CLI usage** | Controls slash commands, launchers, auto-discovery |
| `pal.base-roles` | **PAL's `clink` tool** | Controls cross-CLI subagent delegation |

These are independent: you can have all agents available for PAL's `clink` while restricting native CLI usage to a smaller set, or vice versa.

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
    - chaos-engineer
    - incident-commander  # Exclude specific roles from "all"
```

**Example: Custom agent set**

```yaml
# local.yml
roles:
  enabled:
    - architect
    - frontend
    - security-compliance
    - distributed-systems
  disabled: []
```

> [!NOTE]
> After modifying `roles` configuration, run `./bin/open-bureau` to regenerate slash commands, launchers, and symlinks. For Claude Code, the changes take effect immediately (run `/help` to see updated list). For Codex/Gemini launchers, you may need to restart your shell or run `hash -r` to refresh the command cache.

### `pal`

**File:** `directives.yml`

Configures the PAL MCP server's `clink` tool, which spawns subagents across different coding CLIs (Claude, Codex, Gemini). These settings control which models are used and which role prompts are available.

#### `pal.base-roles`

Baseline set of role prompts made available to ALL coding CLIs.

```yaml
pal:
  base-roles: all    # options: "all", "none", or list of role names
```

**Values** *(these also apply to `extra-roles` below)*:
- `all` - All discovered roles from `agents/role-prompts/`
- `none` - No roles (except the default role)
- `[list]` - Explicit list of role names corresponding to filestems in `agents/role-prompts/` (e.g., `[architect, debugger]`)

#### Per-CLI settings (`pal.<claude|codex|gemini>`)

Each CLI has its own configuration block with model and role settings.

The options (with their default values) are shown below:

**Claude:**
```yaml
pal:
  claude:
    model: sonnet      # Any valid Claude model
    extra-roles: none  # Extra roles beyond base-roles to include for Claude
```

**Codex:**
```yaml
pal:
  codex:
    model: gpt-5.2-codex   # Any valid Codex model
    effort: medium         # Options: minimal, low, medium, high, xhigh
    extra-roles: none      # Extra roles beyond base-roles to include for Codex
```

**Gemini:**
```yaml
pal:
  gemini:
    extra-roles: none  # Extra roles beyond base-roles to include for Gemini
```

### `retention_period_for`

**File:** `directives.yml`

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

**File:** `directives.yml`

Controls automatic cleanup behavior.

```yaml
cleanup:
  min_interval: 24h  # Minimum time between cleanup runs
```

Cleanup runs automatically on `./bin/open-bureau` if enough time has passed since the last run.

### `trash`

**File:** `directives.yml`

Controls the soft-delete trash system.

```yaml
trash:
  grace_period: 30d  # Time before trash is permanently deleted
```

Deleted items go to `.archives/trash/` and remain recoverable until the grace period expires.

### `startup_timeout_for`

**File:** `directives.yml`

Timeouts for startup operations (in seconds).

```yaml
startup_timeout_for:
  mcp_servers: 200     # MCP server startup timeout
  docker_daemon: 120   # Docker daemon startup timeout
```

Increase these values on slower machines.

### `port_for`

**File:** `directives.yml`

Ports for locally-run servers and containers.

```yaml
port_for:
  qdrant_db: 8780        # Qdrant database
  qdrant_mcp: 8782       # Qdrant MCP server
  sourcegraph_mcp: 8783  # Sourcegraph MCP server
  semgrep_mcp: 8784      # Semgrep MCP server
  serena_mcp: 8785       # Serena MCP server
```

Change these if you have port conflicts.

### `path_to`

**File:** `directives.yml` (user-tunable) and `charter.yml` (package defaults)

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

Some configuration values can be overridden via environment variables:

| Environment Variable | Overrides | Description |
|:---------------------|:----------|:------------|
| `BUREAU_WORKSPACE` | `path_to.serena_memories_root` | Root for scanning Serena memory files |

> [!NOTE]
> 
> Some remote MCPs require API keys (even for their free versions). Set these env vars accordingly to enable them:
> 
> - `TAVILY_API_KEY`
> - `BRAVE_API_KEY`
> - `CONTEXT7_API_KEY`

## Examples

### Disable specific CLI agents locally

Create `local.yml`:
```yaml
agents:
  - claude
  - gemini
  # codex and opencode omitted = not configured
```

### Enable MCP tool auto-approval

```yaml
# local.yml
mcp:
  auto_approve: yes
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

### Change ports to avoid conflicts

For example, if port `8780` (the default Qdrant DB listening port) is already in use on your device, you could do:

```yaml
# local.yml
port_for:
  qdrant_db: 9780
```

## Security note for subagents spawned via PAL MCP's `clink`

When you delegate tasks via `clink`, the spawned CLI (Claude, Codex, or Gemini) runs with flags that bypass interactive approvals:

| CLI    | Flag                                         | Effect                        |
|:-------|:---------------------------------------------|:------------------------------|
| Claude | `--permission-mode acceptEdits`              | Auto-accepts file edits       |
| Codex  | `--dangerously-bypass-approvals-and-sandbox` | Bypasses all safety checks    |
| Gemini | `--yolo`                                     | Permissive mode (auto-approve)|

**This is intentional:** 

- Subagents are spawned programmatically (whether autonomously or via explicit prompting) by a parent agent that already has your trust. 
- Requiring interactive approval for each subagent action would break the automation flow: the whole point of delegation is autonomous execution.

### Solutions

Stash/commit changes before delegating complex tasks. If you need stronger isolation, direct agents to run `clink`-spawned agents in worktrees with fresh branches, merging the subsequent changes only if they're approved by you.

Also, don't delegate commands you wouldn't run yourself; the parent agent's judgment is only as strong as yours.

## Related commands

| Command | Description |
|:--------|:------------|
| `./bin/open-bureau` | Start Bureau (runs cleanup if needed) |
| `./bin/bureau-prune` | Manually run cleanup |
| `./bin/bureau-empty-trash` | Permanently delete trash contents |
| `./bin/bureau-wipe <storage>` | Wipe a storage backend |
| `./bin/check-prereqs` | Verify prerequisites are installed |
