# MCP updates

#### Contents:

- [High-level overview](#high-level-overview)
  - [MCP *additions*](#mcp-additions)
  - [MCP *deletions*](#mcp-deletions)
- [Decision: Codex MCP](#decision-codex-mcp)
  - [How Codex-as-MCP works](#how-codex-as-mcp-works)
  - [Head-to-head comparison](#head-to-head-comparison)
  - [Recommendation: headless CLI invocation](#recommendation-headless-cli-invocation)
- [Implementation plan](#implementation-plan)
  - [Workstream 1: Add GitHub MCP](#workstream-1-add-github-mcp)
  - [Workstream 2: Remove PAL MCP and all clink references](#workstream-2-remove-pal-mcp-and-all-clink-references)
  - [Workstream 3: Verify and update headless invocation docs](#workstream-3-verify-and-update-headless-invocation-docs)
  - [Execution order](#execution-order)

## High-level overview

### MCP *additions*

#### Codex MCP

> This one is still undecided and **requires a head-to-head comparison** as mentioned below.

Codex offers **direct support** for [being run as an MCP server](https://developers.openai.com/codex/guides/agents-sdk).

It's great at following instructions and thus is an invaluable partner to delegate thoroughly-defined tasks to.

Let's explore adding it as an MCP to both Gemini CLI, Claude Code and OpenCode *if and only if* Codex is enabled in the YML configs (note this includes removing it as an MCP when it's disabled). This will require a **head-to-head comparison/pro-con list** of running Codex *headlessly via direct CLI invocation* vs. *adding Codex as an MCP to the other Bureau-supported CLIs* (that are enabled in the YML configs).

Further, let's *not* add support for this via:

- a new `open-bureau` CLI flag that users will have to process and add to their mental model
- any interactive prompts that harass the user during `open-bureau` invocation

Instead, let's add a **single lowkey YML config setting** that can be set to `true` or `false`: 

- name it, for example, `add-codex-mcp-to-clis` or something shorter but still self-explanatory *(what would a veteran distinguished engineer name it?)*
- if it's set to `true`, the behaviour above is enabled
- if it's set to `false`, the behaviour above is disabled entirely

> [!NOTE]
>
> If we pursue adding this (which we probably should), we must also update the guidance in the context files on **cross-CLI delegation via headless invocation** (previously done via PAL MCP's `clink`) so that delegation to Codex is done via this MCP rather than via headless CLI invocation.

#### GitHub MCP

This one seems straightforward enough to add based on the [GitHub MCP documentation on GitHub](https://github.com/github/github-mcp-server).

### MCP *deletions*

#### PAL MCP (only used for `clink`)

As part of the [context file overhaul](2026-03-29-context-hub-spoke-design.md), we planned to drop PAL MCP since we only use it for `clink`, which we're transitioning away from in favour of headless instantiation (and potentially the Codex MCP as mentioned above).

Thus we should scrupulously plan the removal of *all* PAL MCP-related and `clink`-related setup and documentation in Bureau.

## Decision: Codex MCP

### How Codex-as-MCP works

Running `codex mcp-server` starts a long-lived stdio MCP server exposing two tools:

| Tool | Purpose | Key parameters |
|------|---------|----------------|
| `codex` | Start a new agent session | `prompt`, `base-instructions` (system prompt), `approval-policy`, `sandbox`, `model`, `cwd`, `config` |
| `codex-reply` | Continue an existing session | `prompt`, `threadId` |

- **Transport**: stdio only (no SSE or streamable-http — open issues [#2129](https://github.com/openai/codex/issues/2129), [#11284](https://github.com/openai/codex/issues/11284))
- **System prompt injection**: `base-instructions` replaces default system prompt; `config.developer_instructions` appends after AGENTS.md
- **Permissions**: `approval-policy: "never"` + `sandbox: "workspace-write"` for automation
- **Session continuity**: `threadId` returned from `codex`, passed to `codex-reply` for multi-turn
- **Capabilities**: Full Codex agent — file reads/writes, shell, code search, all MCP tools from its own config

### Head-to-head comparison

| Dimension | Headless CLI invocation | Codex-as-MCP |
|-----------|------------------------|--------------|
| **Latency** | Process spawn per call (2-5s cold start); session resume avoids context reload | Warm server after first call; near-zero per-call startup for `codex-reply` |
| **Coverage** | Universal — Claude, Codex, Gemini all support headless mode | Codex only — Claude/Gemini delegation still needs headless CLI |
| **System prompt** | Per-CLI divergence: `--append-system-prompt` (Claude), embedded in prompt (Codex/Gemini) | Clean `base-instructions` parameter per call, but Codex only |
| **Tool access** | Inherits full MCP ecosystem (Serena, Memory, Qdrant, etc.) | Limited to Codex's own `config.toml` MCP config; no dynamic MCP injection |
| **Output format** | JSON output with session IDs; requires parsing | Structured MCP response with `threadId`; native protocol handling |
| **Parallelism** | Trivially parallel — spawn N processes; mixed-model parallelism | Concurrent `threadId` sessions; but only Codex |
| **Sandboxing** | Process-level + git worktrees (Bureau's current recommendation) | Granular: `read-only` / `workspace-write` / `danger-full-access` per call |
| **Token cost** | Both models billed; no extra protocol overhead | Both models billed; adds MCP protocol overhead |
| **Setup complexity** | Zero additional setup; CLIs already installed; patterns documented in `task-assessment.md` | New long-lived process to manage (startup, health checks, crash recovery) |
| **Maintenance** | Low — CLI flags rarely change | Medium — must track Codex MCP API changes (e.g., `conversationId` → `threadId` rename) |
| **Session resume** | Supported: `claude --resume`, `codex exec resume` | Native via `codex-reply` + `threadId`; in-process (no restart) |
| **Bureau code changes** | Minimal — already 80% implemented in `task-assessment.md` spoke | Significant — new MCP server config, lifecycle management, adapter code |

### Recommendation: headless CLI invocation

**Use headless CLI as the sole cross-CLI delegation mechanism.** Do not add Codex-as-MCP at this time.

## Implementation plan

Three workstreams, executed in this order due to dependencies:

### Workstream 1: Add GitHub MCP

**Why**: Provides structured GitHub API access (PRs, issues, code search, Copilot agent integration, security scanning) beyond what `gh` CLI offers. No Bureau-supported CLI currently has GitHub MCP configured (Claude Code's built-in plugin was removed in favor of Bureau-managed wiring for consistency).

**Approach**: Use the **remote hosted server** at `https://api.githubcopilot.com/mcp/` — zero local footprint, no Docker, and includes extra tools (Copilot PR creation, support docs search). Bureau manages the config for all 4 CLIs uniformly.

**Authentication**: Single GitHub PAT stored in env var (e.g., `GITHUB_PAT`), referenced by all CLI configs.

**Toolset scoping**: Use default toolsets only (context, repos, issues, pull_requests, users) to avoid bloating agent context with 90+ tools. Add `actions` and `code_security` as opt-in.

#### Steps

| # | Change | File(s) |
|---|--------|---------|
| 1 | Add `github` entry to `mcp.client_configs` with `requires_env: [GITHUB_PAT]` | `defaults.yml` |
| 2 | Add per-CLI client configs (remote HTTP for all; Codex uses `bearer_token_env_var` pattern in TOML) | `defaults.yml` |
| 3 | Extend `add_mcp_to_codex()` to emit `bearer_token_env_var` for HTTP servers that need auth (currently returns error 2 when headers are needed — Codex doesn't support custom headers, only bearer tokens via env var) | `tools/scripts/set-up-tools.sh` |
| 4 | Ensure Claude Code's built-in GitHub plugin stays disabled (Bureau's tools setup takes precedence) | `tools/scripts/set-up-tools.sh` or equivalent |
| 5 | Document in `tools-guide.md` (spoke) when to use GitHub MCP vs `gh` CLI | `protocols/context/static/ops/task-execution.md` or equivalent |
| 6 | Add `GITHUB_PAT` to setup docs | `docs/SETUP.md` |

### Workstream 2: Remove PAL MCP and all clink references

**Why**: PAL MCP is only used for `clink`. With headless CLI invocation as the replacement (decision above), all PAL/clink infrastructure becomes dead code.

**Scope** (from codebase audit):

#### 2a. Delete PAL infrastructure

| File / directory | Action |
|------------------|--------|
| `protocols/pal/` (entire directory) | Delete — contains `settings.yaml` and `generated/*.json` |
| `protocols/scripts/generate-pal-configs.py` | Delete |
| `protocols/scripts/set-up-protocols.sh` lines 388-435 | Delete — PAL config generation & symlink section |
| `agents/scripts/set-up-agents.sh` lines 37-53, 149 | Delete — clink subagent setup, `~/.pal/cli_clients/systemprompts` symlinks |
| `tools/scripts/set-up-tools.sh` lines 86-97 | Delete — `CLI_BIN_PATHS` setup for PAL MCP |
| `defaults.yml` `mcp.client_configs.pal` section | Delete — entire PAL MCP client config |
| `defaults.yml` top-level `pal:` section (lines 364-399) | Delete — PAL role config (`base-roles`, per-CLI model/effort/extra-roles) |
| `operations/tests/test_config_loader.py` `test_defaults_yml_anchors_resolve` | Delete — tests PAL YAML anchor resolution |

#### 2b. Update 126 role prompt files

All files in `agents/role-prompts/` (62) and `agents/claude-subagents/` (64) reference clink. Each needs a find-and-replace:

- `"Use clink for ..."` → `"Delegate via headless CLI invocation for ..."`
- `"Use cross‑model delegation (clink)"` → `"Use cross-model delegation (headless CLI invocation)"`
- Any clink-specific examples → headless CLI equivalents

This is a mechanical bulk edit — suitable for a single scripted pass or a dedicated subagent.

#### 2c. Update documentation

| File | Changes |
|------|---------|
| `docs/CONFIGURATION.md` | Remove PAL/clink sections (security note, `pal.base-roles` table rows, clink references) |
| `docs/USAGE.md` | Replace clink spawning section with headless CLI invocation; remove PAL definitions |
| `docs/SETUP.md` | Remove PAL config file references; update delegation examples |
| `docs/DATA-FLOWS.md` | Delete section 6 "PAL config generation" and all PAL subgraph nodes/edges |
| `docs/FOLD-FIXES.md` | Remove clink context output references |
| `protocols/context/static/skills/micro-mode/SKILL.md` | Replace `clink` with headless CLI invocation |
| Deployed `handoff-guide.md` and `tools-guide.md` | Update delegation mechanism references |

#### 2d. Update context templates and regenerate

| File | Changes |
|------|---------|
| `protocols/context/templates/AGENTS.template.md` | Remove any clink delegation guidance (if present) |
| `protocols/context/templates/CLAUDE.template.md` | Remove clink references in delegation section |
| `protocols/context/generated/AGENTS.md` | Regenerate after template changes |
| `protocols/context/generated/CLAUDE.md` | Regenerate after template changes |

### Workstream 3: Verify and update headless invocation docs

**Why**: With clink gone, headless CLI invocation becomes the *only* cross-CLI delegation mechanism. The documentation must be complete and authoritative.

| # | Task |
|---|------|
| 1 | Verify `task-assessment.md` spoke has complete, current invocation tables for all 3 CLIs |
| 2 | Update `handoff-guide.md` — replace all clink references with headless CLI patterns; update the delegation mechanisms table, quick comparison, and tool-specific guidance sections |
| 3 | Update `tools-guide.md` — remove PAL from limits table and MCP server listings |
| 4 | Verify `cc_connect.py` `build_headless_command()` covers all CLIs correctly |

### Execution order

```
Workstream 1 (GitHub MCP)     ──── can start immediately, independent
Workstream 2a (delete PAL)    ──── can start immediately
Workstream 2b (role prompts)  ──── can start immediately (parallel with 2a)
Workstream 2c (docs)          ──── after 2a (needs to reference final state)
Workstream 2d (templates)     ──── after 2c (templates reference docs patterns)
Workstream 3 (headless docs)  ──── after 2a-2d (final verification pass)
```

Workstreams 1, 2a, and 2b are fully independent and can be parallelized.
