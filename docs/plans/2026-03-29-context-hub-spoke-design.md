# Context files restructure: hub-and-spoke architecture

**Date**: 2026-03-29
**Status**: Design approved, pending implementation planning
**Scope**: tools-guide.md, handoff-guide.md, CLAUDE.template.md, AGENTS.template.md → hub + spokes

## Problem

Bureau's agent context files consume ~773 lines (~10K tokens) before an agent starts working, regardless of task type. Much of this content is either:
- Knowledge SOTA models already have (e.g., "verify facts before answering," "parallelize independent tasks")
- Duplicated across files (memory protocols in both templates and tools-guide)
- Always loaded when only sometimes needed (code-standards.md read even for non-coding tasks)

Additionally, the clink (PAL MCP) delegation mechanism is now redundant — all three Bureau-supported CLIs (Claude Code, Codex, Gemini) support native headless invocation with session resumption, structured JSON output, and system prompt injection.

## Design

### Architecture: hub-and-spoke with per-prompt hook injection

```
CLAUDE.template.md (~20 lines)
  ──reads──→ ops-hub.md (~20 lines, routing table)
                ├──→ ops/session-start.md (~25 lines)
                ├──→ ops/task-assessment.md (~30 lines)
                ├──→ ops/task-execution.md (~45 lines)
                ├──→ ops/task-completion.md (~20 lines)
                └──→ ops/code-standards.md (~370 lines, unchanged)
```

- The **hub** is the only must-read file. It routes agents to task-specific spokes via `<read-file-when>` tags.
- **Spokes** are read on-demand — agents load only what's relevant to the current task.
- **Hooks** (UserPromptSubmit / userpromptsubmit / BeforeAgent) re-inject the hub content before each prompt as a routing reminder. Graceful degradation: without hooks, agent reads hub at session start only.

### Content strategy

- **Drop**: Content SOTA models already know (delegation principles, "when NOT to delegate," merge/verify checklists, AskUserQuestion best practices, approval step-by-step patterns, context management advice, git/browser tool guidance)
- **Keep item 1.1**: Factual accuracy protocol — retained per user decision
- **Distill**: Prioritization signals compressed to compact tables/lists
- **Keep**: All Bureau-specific content (MCP tool routing, memory destinations, tool limits, task-list scope, headless CLI invocation, fold/unfold)
- **Deduplicate**: Memory protocols appear once (retrieval in session-start, storage in task-execution; removed from templates)

### Key architectural decisions

1. **clink deprecated for delegation.** Replaced by native headless CLI invocation (`claude -p`, `codex exec`, `gemini -p`). Each CLI supports structured JSON output with session IDs, session resumption, system prompt injection, and auto-approval flags. PAL MCP's `clink` tool and `generate-pal-configs.py` role config generation can be simplified.

2. **code-standards.md becomes a spoke.** No longer a startup must-read. Agents read it only when writing or editing code. Saves ~4K tokens on every non-coding task.

3. **XML tags for structure.** All files use XML tags for unambiguous scope delineation. Research confirms all three SOTA models (Claude, GPT-5.x, Gemini 2.5 Pro) handle XML tags well — this is a cross-model optimization, not Claude-specific.

4. **Task-list scope rule is inline in the hub.** Critical enough to survive even if no spoke is read. Also duplicated in templates as defense-in-depth.

5. **Self-invocation guard.** Headless CLI guidance explicitly states "never invoke your own CLI headlessly — use native subagent tools instead" to prevent agents from spawning headless versions of themselves.

## File specifications

### Hub: `ops-hub.md`

```xml
<bureau:required-context-by-task>

  <read-file-when task="starting a session" path="{{PROTOCOLS_DIR}}/ops/session-start.md" />
  <read-file-when task="deciding to delegate, choosing model/tool, parallelizing" path="{{PROTOCOLS_DIR}}/ops/task-assessment.md" />
  <read-file-when task="executing: searching, editing, storing memories" path="{{PROTOCOLS_DIR}}/ops/task-execution.md" />
  <read-file-when task="finishing: approvals, memory persistence, handoff" path="{{PROTOCOLS_DIR}}/ops/task-completion.md" />
  <read-file-when task="writing or editing code" path="{{PROTOCOLS_DIR}}/ops/code-standards.md" />

  <bureau-rules>
    <task-lists>
      Two systems exist. Using the wrong one loses state.
      - Within a single session: use native task tools (TodoWrite, internal planner, etc.)
      - Working from an unfolded dossier or across sessions/CLIs: use Bureau CLI exclusively
        (tasks claim --id N --agent X, tasks complete --id N, tasks add, tasks list)
    </task-lists>
  </bureau-rules>

</bureau:required-context-by-task>
```

### Spoke: `ops/session-start.md`

```xml
<session-start>

  <factual-accuracy>
    Factual accuracy >> response speed. Verify before answering.
    - Technical info → search official docs (Context7, WebFetch, WebSearch)
    - Current events → search recent news (Tavily, Brave with freshness filters)
    - Code behavior → read actual code, run tests, check logs
    - API details → fetch current documentation, not training data
    - "I don't know" > wrong answer. "Let me verify" > speculation.
    Speculative answers stored in memory = poisoning future agents.
  </factual-accuracy>

  <memory-retrieval>
    Before starting any task, query all memory systems:
    - Qdrant MCP (qdrant-find) — past solutions, patterns, gotchas
    - Memory MCP (read_graph, search_nodes) — architecture, components, relationships
    - claude-mem (get_observations, search) — recent session history (Claude Code only)
  </memory-retrieval>

  <memory-metadata>
    Always include when storing memories:
    | Storage tool | Required field |
    |---|---|
    | Qdrant MCP | metadata.created_at (ISO 8601 UTC, e.g. 2025-12-05T21:10:00+00:00) |
    | Memory MCP | created_at (ISO 8601 UTC, e.g. 2025-12-05T21:10:00+00:00) |
    | Serena MCP | None — automatic |
    | claude-mem | None — automatic |
  </memory-metadata>

</session-start>
```

### Spoke: `ops/task-assessment.md`

```xml
<task-assessment>

  <delegation-mechanisms>
    | Mechanism | Use for |
    |---|---|
    | Native subagents (Task/Agent tool, internal planner) | Same-CLI delegation — always prefer this over headless self-invocation |
    | Headless CLI via Bash | Cross-CLI delegation only (see invocation table below) |
    | AskUserQuestion | Ambiguity, multiple valid approaches, approval needed |

    <headless-invocation>
      For delegating to a DIFFERENT CLI than the one you are running in.
      Never invoke your own CLI headlessly — use your native subagent tools instead.

      | CLI | Invoke | Resume | Output | Auto-approve |
      |---|---|---|---|---|
      | Claude Code | claude -p "prompt" | --resume SESSION_ID | --output-format json | --allowedTools "tools" |
      | Codex | codex exec "prompt" | codex exec resume SESSION_ID | --json | --full-auto |
      | Gemini | gemini -p "prompt" | (session ID from init event) | --output-format json | TBD — verify Gemini CLI auto-approve flag before implementation |

      Essential rules:
      - Always set auto-approve flags — headless agents hang on permission prompts
      - Inject role via --append-system-prompt (Claude) or in the prompt itself (Codex/Gemini)
      - Use --bare (Claude) for simple scoped tasks that don't need MCPs
      - Omit --bare when the headless agent needs MCP server access
      - Always use JSON output to capture session IDs
      - Always use the exact session ID to resume
    </headless-invocation>
  </delegation-mechanisms>

  <parallel-delegation>
    Default: before starting work, ask "can I split this into 2+ independent subtasks?"
    If yes → spawn multiple subagents in a single response (not sequentially).
    Superpowers precedence: if a skill mandates a workflow, follow it; use these guidelines to choose who/what within that workflow.
  </parallel-delegation>

</task-assessment>
```

### Spoke: `ops/task-execution.md`

```xml
<task-execution>

  <tool-selection>
    | Operation | Tool | Notes |
    |---|---|---|
    | OSS code search | Sourcegraph MCP | Use count:all for exhaustive; bump timeout for large sets |
    | Local semantic/symbol navigation | Serena MCP (find_symbol, get_symbols_overview) | |
    | Local text search | ripgrep/grep | Respects .gitignore |
    | Web research | Tavily → Brave (fallback) → Playwright (fallback) | |
    | Simple URL fetch | Fetch MCP | Do NOT use on github.com — returns wrapper HTML |
    | GitHub content | raw.githubusercontent.com via Fetch, or gh CLI via Bash | |
    | API/library docs | Context7 MCP | Versioned, public repos only |
    | Read 1-9 files | Native Read tool | Do NOT use Serena read_file |
    | Read 10+ files | Filesystem MCP read_multiple_files | 30-60% token savings |
    | Symbol-level refactors | Serena: replace_symbol_body, insert_after/before_symbol, rename_symbol | |
    | All other edits | Native Write/Edit tools | |
    | Security scans | Semgrep | Local, autofix |
  </tool-selection>

  <memory-storage>
    Store incrementally throughout work, not just at end.
    - Qdrant MCP (qdrant-store): solutions, patterns, gotchas, root causes, design decisions
    - Memory MCP (create_entities, create_relations): components, architecture, data flows, dependencies
    - Before completing any task: "Would future agents benefit?" → yes = store it
  </memory-storage>

  <limits>
    | Tool | Limit | Reset |
    |---|---|---|
    | Tavily | 1,000 credits/month | 1st of month |
    | Brave | 2,000 queries/month | 1st of month |
    | Sourcegraph | Interactive limits | Use count:all; switch to src-cli for large sets |
  </limits>

</task-execution>
```

### Spoke: `ops/task-completion.md`

```xml
<task-completion>

  <approval-gates>
    Always get explicit approval before:
    - Creating commits, pushing, merging, rebasing, force pushing
    - Deleting files/dirs, dropping tables, purging caches
    - Any production/deployment action
    - Security/access/permission changes
    - Breaking public API changes
    - Adding cloud resources or paid services
  </approval-gates>

  <conversation-handoff>
    To save work-stream state for cross-agent resumption:
    - /fold — saves conversation as a Bureau dossier
    - /unfold — resumes a previously saved dossier
    Preferred over context compaction for preserving full fidelity.
  </conversation-handoff>

</task-completion>
```

### Template: `CLAUDE.template.md`

```markdown
# Global context (always read first)

## MUST-READ FILE

Read this file using the Read tool before starting any task and at the beginning of any conversation:

### [Operations hub]({{PROTOCOLS_DIR}}/ops-hub.md)

> **Read**: `@{{PROTOCOLS_DIR}}/ops-hub.md`

The hub routes you to task-specific context. Read the relevant spoke(s) for your current task.

## TASK LIST SCOPE: NATIVE vs BUREAU

Two task list systems exist. Using the wrong one loses state.

| System | Backing | Visibility | Use for |
|--------|---------|-----------|---------|
| **Native** (`TodoWrite`/`TodoRead`) | In-memory, tied to one Claude Code process | Only the spawning agent and its subagents | Intra-session subagent coordination |
| **Bureau** (`bureau-dossiers tasks`) | SQLite on disk | Any process, any CLI, any agent | Cross-session and cross-CLI coordination |

When working from an unfolded dossier, ALL task operations go through Bureau CLI.
```

### Template: `AGENTS.template.md`

Same as CLAUDE.template.md with these differences:
- Title: "Global context for Gemini CLI & Codex"
- Native task list row references: "Codex internal planner, Gemini internal task tracking"
- Additional note: "You are running via Gemini CLI or Codex. Use headless CLI invocation for cross-model delegation (see task-assessment spoke). You have access to the same MCPs as Claude Code."

## Hooks configuration

Each CLI needs a hook to re-inject the hub content before every prompt:

| CLI | Hook event | Mechanism |
|-----|-----------|-----------|
| Claude Code | `UserPromptSubmit` | Shell command that cats `ops-hub.md` to stdout |
| Codex CLI | `userpromptsubmit` | Shell command that cats `ops-hub.md` to stdout |
| Gemini CLI | `BeforeAgent` | Shell command that cats `ops-hub.md` to stdout |

Graceful degradation: without hooks configured, the agent reads the hub at session start via the template's must-read directive. The hub is still effective — the hook just reinforces it between prompts.

## Deployment changes

### `set-up-protocols.sh` updates
- Create `{{PROTOCOLS_DIR}}/ops/` subdirectory
- Copy spoke files to `ops/` subdirectory
- Copy (or symlink) existing `code-standards.md` into `ops/`
- New `{{PROTOCOLS_DIR}}` placeholder substitution in hub file
- Configure hooks for each enabled CLI
- Simplify or remove clink-related PAL config generation

### File layout (deployed)

```
~/.config/bureau/protocols/
├── ops-hub.md                    (generated with absolute paths)
└── ops/
    ├── session-start.md
    ├── task-assessment.md
    ├── task-execution.md
    ├── task-completion.md
    └── code-standards.md         (existing file, unchanged)
```

### File layout (source, in repo)

```
protocols/context/
├── static/
│   ├── ops-hub.md                (authored with {{PROTOCOLS_DIR}} placeholders)
│   ├── ops/
│   │   ├── session-start.md
│   │   ├── task-assessment.md
│   │   ├── task-execution.md
│   │   └── task-completion.md
│   ├── code-standards.md         (unchanged)
│   └── skills/                   (unchanged)
├── templates/
│   ├── CLAUDE.template.md        (slimmed)
│   └── AGENTS.template.md        (slimmed)
└── generated/
    ├── CLAUDE.md                  (generated)
    └── AGENTS.md                  (generated)
```

## Token budget

| Component | Current lines | Proposed lines | Reduction |
|---|---|---|---|
| Hub (ops-hub.md) | N/A | ~20 | — |
| session-start.md | ~75 | ~25 | 67% |
| task-assessment.md | ~250 | ~30 | 88% |
| task-execution.md | ~180 | ~45 | 75% |
| task-completion.md | ~50 | ~20 | 60% |
| CLAUDE.template.md | 115 | ~20 | 83% |
| AGENTS.template.md | 103 | ~25 | 76% |
| code-standards.md | 370 | 370 (unchanged) | 0% |
| **Total (excl. code-standards)** | **~773** | **~185** | **~76%** |
| **Per-prompt, non-coding** | **~773** | **~65-90** | **~88-92%** |
| **Per-prompt, coding** | **~1143** | **~435-460** | **~60%** |

## Deprecations

| Item | Status | Notes |
|---|---|---|
| PAL clink for delegation | Deprecated | Replaced by native headless CLI invocation |
| `generate-pal-configs.py` role config generation | Simplify | No longer needs clink role configs; PAL still useful for listmodels/version |
| `tools-guide.md` (standalone) | Replaced | Content merged into spokes |
| `handoff-guide.md` (standalone) | Replaced | Content merged into spokes |
| Factual accuracy protocol in templates | Removed | Moved to session-start spoke |
| Memory protocol in templates | Removed | Split across session-start (retrieval) and task-execution (storage) |
| Context management protocol in templates | Removed | Obvious to SOTA models |
