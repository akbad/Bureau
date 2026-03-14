# Competitive Inspiration: cc.dev & Continue.dev

> **Purpose**: Competitive analysis of two notable AI developer tools and strategic
> recommendations for Bureau features that would supersede or outcompete their
> functionality.

---

## Table of contents

- [Tool profiles](#tool-profiles)
  - [cc.dev (Command Center)](#ccdev-command-center)
  - [Continue.dev](#continuedev)
- [Comparative analysis](#comparative-analysis)
  - [Feature matrix](#feature-matrix)
  - [Architectural philosophy comparison](#architectural-philosophy-comparison)
  - [Where Bureau already wins](#where-bureau-already-wins)
  - [Where Bureau has gaps](#where-bureau-has-gaps)
- [Strategic additions](#strategic-additions)
  - [1. Session replay and architectural walkthrough system](#1-session-replay-and-architectural-walkthrough-system)
  - [2. Cross-CLI quality gates pipeline](#2-cross-cli-quality-gates-pipeline)
  - [3. Adaptive context orchestration engine](#3-adaptive-context-orchestration-engine)
  - [4. Agent performance observatory](#4-agent-performance-observatory)
  - [5. Snapshot-aware dossier system with rollback](#5-snapshot-aware-dossier-system-with-rollback)

---

## Tool profiles

### cc.dev (Command Center)

**Core thesis**: If AIs write code 100x faster, the bottleneck shifts from *writing*
code to *understanding and reviewing* AI-generated code. Command Center addresses
that bottleneck.

**Category**: Post-IDE code review, comprehension, and refactoring platform.

**Founded by**: James Koppel (MIT PhD in program transformation, Thiel Fellow, trained
500+ engineers at Google/Meta/Amazon/Stripe/Apple). Company: Algebras AI.

**Key features**:

| Feature | Description |
|---------|-------------|
| **AI-generated walkthroughs** | Human-readable explanations of every PR/changeset, configurable depth, explains *why* changes were made rather than just *what* |
| **Research-backed refactoring** | One-click automated refactoring powered by 60 years of software design research: duplicate extraction, method extraction, indirection removal, concern separation, legacy modernization |
| **Real-time diff viewer** | Live-updating GitHub-style diffs with word-level highlighting, virtual scrolling, unified/split views, commit range comparison |
| **Multi-agent orchestration** | Run many coding agents simultaneously in isolated environments with agent picker (Claude Code, OpenCode, Codex, Gemini CLI) |
| **Snapshot undo system** | Branch-like snapshot navigation to restore code state when an agent breaks things, without polluting git history |
| **Plan mode UI** | Agents present implementation plans for approval before writing code |
| **Agent loops** | Run agents repeatedly until success with configurable retry/error handling |
| **Per-workspace agent memory** | Context and preferences persist per workspace |
| **GitHub integration** | Create PRs with AI-generated descriptions, clone repos, push/pull/sync |
| **Extensions marketplace** | One-click installation of hooks, subagents, commands, MCP servers |

**Pricing**: Free (3 workspaces) / $7/mo Starter / $16/mo Pro

**Architecture**: Local-first. All data stored in `~/.commandcenter`. Code sent
directly to user's chosen AI provider (Anthropic, OpenAI, Google) -- Command Center
servers never see code. Free bundled Gemini proxy and OpenCode agent. Installed via
npx.

**What makes it unique**: It does not compete with code generators -- it is a
*complementary review layer* that sits on top of any coding agent. The refactoring
engine encodes research-backed patterns (not just lint rules). The snapshot system
enables fearless agent experimentation. The walkthrough system transforms diffs from
"what changed" into "what this means architecturally."

---

### Continue.dev

**Core thesis**: Developers deserve full control over their AI coding experience --
which models, where code is processed, how AI behaves -- with zero vendor lock-in.

**Category**: Open-source AI coding platform (IDE extension + CLI + cloud hub).

**Stats**: 31,800+ GitHub stars, 2.3M+ VS Code installs, 458 contributors, Apache 2.0
license.

**Key features**:

| Feature | Description |
|---------|-------------|
| **Four interaction modes** | Chat (conversational), Agent (autonomous multi-step), Plan (read-only exploration), Autocomplete (inline suggestions) |
| **Model agnosticism** | 20+ providers plus any OpenAI-compatible endpoint. Different models per task (fast local model for autocomplete, Claude for chat, custom embeddings for RAG) |
| **Context provider system** | Rich `@`-mention architecture: `@File`, `@Code`, `@Git Diff`, `@Terminal`, `@Debugger`, `@Repository Map`, `@MCP`, `@HTTP`, `@Clipboard`, `@Tree`, `@Problems`, `@OS` |
| **Rules-as-code** | Markdown files in `.continue/rules/` with glob/regex conditional activation, hierarchical loading, YAML frontmatter -- version-controlled team standards |
| **CI/CD quality checks** | CLI (`cn`) runs markdown-defined AI checks as native GitHub status checks with pass/fail + suggested diffs |
| **Next Edit Prediction** | Proactive prediction of the developer's next code change (not just completion) via their open-source Instinct model (7B params, fine-tuned Qwen2.5-Coder-7B) |
| **Codebase indexing** | Local embeddings-based RAG with user-configurable embedding model. Code never leaves the machine |
| **Full MCP support** | stdio/SSE/streamable HTTP transports, Docker containerization, drop-in compatibility with Claude Desktop/Cursor/Cline MCP configs |
| **Continue Hub** | Community marketplace for sharing agents, rules, MCP servers, and configurations |
| **Custom slash commands** | User-defined prompt templates via `/` syntax |

**Pricing**: Free/BYOK (full features, $0) / Starter ($3/M tokens) / Team ($20/seat/mo) / Company (custom)

**Architecture**: TypeScript-first (84%), extension-based (VS Code + JetBrains),
local-first with optional cloud. Configuration-as-code via YAML. Modular provider
layer abstracts LLM communication. Local codebase indexing for RAG.

**What makes it unique**: True model agnosticism (mix-and-match providers per task),
data sovereignty (full air-gapped deployment possible), configuration-as-code
(PR-reviewable AI settings), and the CI/CD bridge (IDE assistance to automated code
review pipeline). Trades polish for control.

---

## Comparative analysis

### Feature matrix

| Capability | Bureau | cc.dev | Continue.dev |
|------------|--------|--------|--------------|
| **Multi-CLI support** | 4 CLIs (Claude, Codex, Gemini, OpenCode) | 4 agents (Claude, Codex, Gemini, OpenCode) | 2 IDEs (VS Code, JetBrains) |
| **Cross-CLI delegation** | PAL MCP `clink` (spawn any agent from any CLI) | Agent picker per workspace | N/A (single IDE) |
| **Agent roles** | 66 specialized roles | Generic agent sessions | Agent mode (single) |
| **Workflow skills** | 11 multi-step protocols (assess, micro, fold/unfold, etc.) | Plan mode, agent loops | Plan mode, rules |
| **Code review** | Assess mode (2-phase) | AI walkthroughs + refactoring engine | Rules + CI checks |
| **Memory systems** | 5 backends (Qdrant, Memory MCP, claude-mem, Serena, dossiers) | Per-workspace memory | Codebase indexing |
| **Context management** | Auto-injected protocols + handoff guides | Workspace-scoped | @-mention providers + rules |
| **Model flexibility** | Any model via CLI providers | AI provider selection | 20+ providers + local |
| **Configuration** | 4-tier YAML hierarchy + env vars | Settings UI | YAML config-as-code |
| **MCP ecosystem** | 16 MCP servers (curated, managed) | MCP support via extensions | Full MCP client |
| **CI/CD integration** | None | None | Native GitHub status checks |
| **Code comprehension** | Manual (agent-driven) | AI-generated walkthroughs | @Repository Map + RAG |
| **Undo/rollback** | Git-based | Snapshot system (non-git) | Git-based |
| **Conversation continuity** | Dossiers (fold/unfold) with SQLite task lists | Session persistence | None |
| **Cleanup/retention** | Automated retention + soft-delete trash | Manual | Manual |
| **Refactoring** | Agent-driven | Research-backed automated engine | Agent-driven |
| **Local/air-gapped** | Fully local | Fully local | Fully local |
| **Open source** | No | No | Yes (Apache 2.0) |

### Architectural philosophy comparison

| Dimension | Bureau | cc.dev | Continue.dev |
|-----------|--------|--------|--------------|
| **Primary abstraction** | The *agent role* (portable across CLIs) | The *workspace* (agent-scoped environment) | The *model provider* (swappable AI backend) |
| **Relationship to IDE/CLI** | Orchestrates across CLIs, owns none | Wraps CLIs in its own UI | Extends existing IDEs |
| **Configuration model** | Declarative YAML, walk-up discovery | GUI settings | Declarative YAML, version-controlled |
| **Extensibility** | MCP servers + skills + roles | Extensions marketplace | MCP + context providers + rules |
| **Data philosophy** | Multi-backend memory with retention policies | Ephemeral per-workspace | Local indexing + optional cloud |

### Where Bureau already wins

1. **Cross-CLI portability**: Bureau is the only system where an agent role, skill, or
   MCP configuration works identically across 4 different CLI platforms. cc.dev supports
   multiple agents but as opaque backends. Continue is IDE-bound.

2. **Conversation continuity**: The dossier system (fold/unfold with SQLite task lists)
   is unique. Neither competitor has anything comparable to cross-session, cross-CLI
   conversation state preservation with concurrent task coordination.

3. **Depth of specialization**: 66 agent roles vs. generic agent sessions. Bureau
   agents carry domain-specific prompts, thinking-level optimization, and delegation
   guidance that neither competitor approaches.

4. **Memory architecture**: Five coordinated memory backends with automated retention,
   cleanup, and soft-delete recovery. cc.dev has per-workspace memory. Continue has
   local indexing. Neither has Bureau's layered, persistent, cross-session memory graph.

5. **Workflow protocols**: Skills like assess-mode, micro-mode, scrimmage-mode, and
   blast-radius-mode are structured multi-step protocols that enforce engineering rigor.
   Neither competitor has equivalent structured workflow enforcement.

6. **MCP curation**: Bureau manages 16 MCP servers with dependency resolution,
   topological startup ordering, health checks, and per-CLI client overrides. Continue
   supports MCP but leaves orchestration to the user.

### Where Bureau has gaps

1. **No code comprehension layer**: cc.dev's AI-generated walkthroughs that explain the
   *architectural meaning* of changes are a genuine capability gap. Bureau agents
   produce changes but don't automatically generate human-readable narratives explaining
   what happened and why.

2. **No CI/CD quality gates**: Continue's CLI runs AI-powered checks as native GitHub
   status checks. Bureau has no pipeline for translating its quality standards (code
   standards, assess-mode criteria) into automated CI enforcement.

3. **No non-git rollback**: cc.dev's snapshot system enables fearless agent
   experimentation without git history pollution. Bureau relies entirely on git for
   state management.

4. **No agent performance tracking**: Neither Bureau nor its competitors systematically
   measure agent effectiveness across roles, models, and CLIs. This is data Bureau is
   uniquely positioned to collect given its multi-CLI, multi-model architecture.

5. **No dynamic context adaptation**: Continue's context provider system (`@`-mentions)
   gives developers explicit control over what context the AI sees. Bureau injects
   context statically via protocols. There's no mechanism for the concierge pipeline's
   ML capabilities to dynamically optimize context injection based on task
   characteristics.

---

## Strategic additions

Five additions that would make Bureau the definitive AI development orchestration
platform -- each synthesizes competitor strengths with Bureau's unique architectural
advantages.

### 1. Session replay and architectural walkthrough system

**Inspired by**: cc.dev's AI-generated walkthroughs

**The gap**: When an agent session produces 15 file changes across 3 commits, the
developer still has to manually reconstruct *what happened and why*. cc.dev solves this
with AI-generated walkthroughs. Bureau can go further.

**The Bureau advantage**: Bureau already captures rich session metadata via dossiers
(decisions, reasoning, file references) and has 5 memory backends tracking what agents
did. This is far more signal than cc.dev has access to.

**Proposed design**:

A `walkthrough` command (invocable as `/bureau-walkthrough` or via the concierge) that:

1. **Collects session artifacts**: Gathers the dossier markdown, task list state, git
   diff since session start, Qdrant memories stored during the session, and Memory MCP
   entities/relations created
2. **Generates an architectural narrative**: Uses an LLM to synthesize these artifacts
   into a structured walkthrough document with sections:
   - **Summary**: 2-3 sentence overview of what was accomplished
   - **Decision log**: Key decisions made and alternatives rejected (extracted from
     dossier + Qdrant memories)
   - **Change map**: File-by-file explanation of *why* each change was made (not just
     what changed)
   - **Dependency impact**: Which downstream systems/modules are affected
   - **Open questions**: Unresolved issues or deferred work
3. **Attaches to the dossier**: The walkthrough becomes a section of the dossier,
   available when the session is unfolded later or shared with other developers
4. **Optionally generates a PR description**: When creating a pull request, the
   walkthrough auto-populates the PR body with the architectural narrative

**Why this supersedes cc.dev**: cc.dev generates walkthroughs from diffs alone. Bureau
walkthroughs incorporate *agent reasoning* (from dossiers), *learned patterns* (from
Qdrant), and *structural relationships* (from Memory MCP) -- producing narratives that
explain not just what changed but the full decision chain that led there. Bureau's
walkthroughs would also be *cross-session aware*: if a walkthrough references a previous
session's decisions, those connections are preserved.

**Implementation complexity**: Medium. The infrastructure (dossiers, memory backends,
LLM access via PAL) already exists. The main work is artifact collection, prompt
engineering for narrative synthesis, and integration with the fold/unfold lifecycle.

---

### 2. Cross-CLI quality gates pipeline

**Inspired by**: Continue.dev's CI/CD quality checks

**The gap**: Bureau defines comprehensive code standards and has assess-mode for
interactive review, but these only run when a developer manually invokes them. There's
no automated enforcement -- changes can be pushed without Bureau's quality bar being
applied.

**The Bureau advantage**: Bureau already has 66 specialized roles, a code standards
document, assess-mode with configurable audit criteria, and scrimmage-mode for
adversarial testing. These are far richer quality signals than Continue's
markdown-defined checks.

**Proposed design**:

A `bureau-check` CLI command and GitHub Action that:

1. **Defines checks as structured YAML** in `.bureau/checks/`:

   ```yaml
   # .bureau/checks/architecture-review.yml
   name: Architecture Review
   trigger: [pull_request]
   role: architect
   model: sonnet  # or configurable
   standards: code-standards.md
   scope:
     include: ["src/**", "lib/**"]
     exclude: ["**/*.test.*", "**/__mocks__/**"]
   severity: blocking  # or advisory
   checks:
     - dependency-direction
     - blast-radius
     - naming-conventions
   ```

2. **Runs Bureau roles as CI agents**: Each check spawns the appropriate Bureau role
   (architect, security-compliance, testing, etc.) against the PR diff, using the same
   role prompts and code standards that interactive agents use
3. **Reports as GitHub status checks**: Pass/fail with inline PR comments explaining
   issues and suggesting fixes -- similar to Continue's approach but with Bureau's
   deeper role specialization
4. **Supports check composition**: A `full-review` check can compose `architect` +
   `security-compliance` + `testing` checks in parallel, merging results
5. **Configurable severity**: Checks can be `blocking` (must pass to merge),
   `advisory` (comment only), or `silent` (log for metrics)

**Why this supersedes Continue.dev**: Continue's checks are generic markdown prompts.
Bureau checks leverage specialized role prompts, configurable code standards, and
structured audit criteria (assess-mode's 4 comprehension styles). Bureau checks also
naturally support the full role library -- a security check uses the
`security-compliance` role, not a generic prompt. And Bureau's multi-model delegation
(via PAL) means checks can use the optimal model per check type.

**Implementation complexity**: Medium-high. Requires a new CLI entry point, GitHub
Action packaging, result formatting, and PR comment integration. The role system,
standards, and LLM access are already in place.

---

### 3. Adaptive context orchestration engine

**Inspired by**: Continue.dev's context provider system

**The gap**: Bureau injects context statically -- every agent session gets the same
handoff guide, tools guide, and code standards regardless of what the agent is doing.
Continue's `@`-mention system gives developers explicit control over context. But
neither system *adapts* context dynamically based on what the task actually needs.

**The Bureau advantage**: Bureau has an ML-based concierge pipeline (DistilBERT
classifier) that understands message intent, a suite detector for operational modes, and
hard rules for explicit routing. This infrastructure is already designed for adaptive
decision-making -- it just doesn't yet control context injection.

**Proposed design**:

An adaptive context layer that sits between the agent and its context sources:

1. **Task-type classification**: The concierge pipeline classifies the incoming task
   (debugging, refactoring, feature development, review, exploration, etc.)
2. **Context budget allocation**: Based on the task type and the target model's context
   window, allocate a token budget across context sources:
   - **Debugging**: Heavy on git diff, error logs, stack traces; light on code
     standards
   - **Refactoring**: Heavy on dependency graph, blast radius analysis; medium on code
     standards
   - **Feature development**: Heavy on architectural context, related modules; light on
     git history
   - **Review**: Heavy on code standards, test coverage; medium on architectural context
3. **Dynamic context provider activation**: Context providers (analogous to Continue's
   `@`-mentions but automatic) are activated based on the budget:
   - `@RecentChanges` -- git diff/log for the relevant scope
   - `@DependencyGraph` -- Serena's symbol references for affected modules
   - `@RelatedMemories` -- Qdrant memories relevant to the task
   - `@TestCoverage` -- test files covering the modified code
   - `@ArchitecturalContext` -- Memory MCP entities/relations for the affected area
4. **Progressive disclosure**: Start with high-level context summaries; the agent can
   request deeper context on specific areas as needed (via tool calls that the
   orchestration layer intercepts and enriches)
5. **Context quality feedback loop**: Track which context sources the agent actually
   *used* (referenced in its response) vs. which were provided but ignored, and adjust
   future allocations accordingly

**Why this supersedes Continue.dev**: Continue requires developers to manually
`@`-mention context sources. Bureau's adaptive engine would automatically provide the
*right* context for the *right* task, learning from usage patterns over time. This is
the difference between a manual transmission and an adaptive automatic -- both give
control, but one also reduces cognitive load.

**Implementation complexity**: High. Requires extending the concierge pipeline with
context budget logic, building context providers as a pluggable abstraction, and
implementing the feedback loop. The ML classifier and provider infrastructure
(Serena, Qdrant, Memory MCP) already exist.

---

### 4. Agent performance observatory

**Inspired by**: A gap in both competitors (and the broader ecosystem)

**The gap**: No tool in the ecosystem systematically measures agent effectiveness.
Developers choose models and roles based on intuition, marketing, and anecdote. cc.dev
runs multiple agents but doesn't compare their quality. Continue supports many models
but doesn't track which performs best for which tasks.

**The Bureau advantage**: Bureau is uniquely positioned to collect this data. It
orchestrates 66 roles across 4 CLIs with multiple models. Every delegation decision
(via PAL's `clink`) is a natural experiment comparing model/role combinations.

**Proposed design**:

A lightweight telemetry and analytics system:

1. **Capture agent session metrics** (stored locally in SQLite, never transmitted):
   - **Task metadata**: Role used, model used, CLI used, task type (classified by
     concierge pipeline)
   - **Quality signals**: Did the agent's changes pass tests? Were they accepted
     by the developer (committed) or reverted? How many iterations were needed?
   - **Efficiency signals**: Token usage, wall-clock time, number of tool calls, number
     of files modified
   - **Delegation signals**: Was the task delegated? To which model/role? Was the
     delegation successful?

2. **Aggregate into a local dashboard** (CLI-based, no web server):

   ```
   $ bureau observatory

   Role Performance (last 30 days):
   ┌──────────────┬─────────┬──────────┬───────────┬────────────┐
   │ Role         │ Sessions│ Accepted │ Avg Iters │ Avg Tokens │
   ├──────────────┼─────────┼──────────┼───────────┼────────────┤
   │ architect    │ 12      │ 92%      │ 1.3       │ 45K        │
   │ debugger     │ 28      │ 89%      │ 2.1       │ 32K        │
   │ testing      │ 15      │ 100%     │ 1.0       │ 18K        │
   └──────────────┴─────────┴──────────┴───────────┴────────────┘

   Model Comparison (debugger role):
   ┌───────────────┬─────────┬──────────┬───────────┐
   │ Model         │ Sessions│ Accepted │ Avg Iters │
   ├───────────────┼─────────┼──────────┼───────────┤
   │ claude-opus   │ 8       │ 100%     │ 1.5       │
   │ gpt-5.1-codex │ 12      │ 83%      │ 2.4       │
   │ gemini-2.5    │ 8       │ 88%      │ 2.0       │
   └───────────────┴─────────┴──────────┴───────────┘
   ```

3. **Inform delegation decisions**: The handoff guide's model selection table (currently
   static) becomes data-driven. When an agent considers delegating, the observatory
   provides empirical recommendations:

   > "For debugging tasks in this codebase, Claude Opus has a 100% acceptance rate
   > vs. 83% for Codex. Recommend Claude Opus."

4. **Detect degradation**: Alert when a model/role combination that previously worked
   well starts underperforming (e.g., after a model version change)

5. **Export for team sharing**: Anonymized performance profiles that teams can share to
   optimize their Bureau configurations

**Why this is novel**: No competitor collects this data. It turns Bureau's multi-CLI,
multi-model architecture from a feature into a *learning system* that gets better at
delegation over time. The observatory makes the handoff guide's model selection table
empirically grounded rather than opinion-based.

**Implementation complexity**: Medium. Session metric capture is straightforward
(instrument PAL's `clink` and dossier lifecycle hooks). The dashboard is a CLI table
renderer. The adaptive delegation recommendations require light statistical analysis.

---

### 5. Snapshot-aware dossier system with rollback

**Inspired by**: cc.dev's snapshot/undo system

**The gap**: When an agent goes off the rails and produces bad code, the developer's
only recovery option is git (reset, revert, checkout). But git operations are heavy,
visible in history, and don't capture the full picture (uncommitted changes, stashed
work, virtual environment state). cc.dev's snapshot system enables lightweight rollback
without git history pollution.

**The Bureau advantage**: Bureau's dossier system already captures session state
(decisions, reasoning, task lists). Adding code snapshots to dossiers creates a
*complete* session recovery mechanism -- not just code state (like cc.dev) but code
state + reasoning state + task state.

**Proposed design**:

Extend dossiers with lightweight, non-git code snapshots:

1. **Automatic snapshot on fold**: When a developer runs `/bureau-fold`, in addition to
   the current dossier artifacts (markdown + SQLite task DB), capture:
   - A `git stash`-like snapshot of the working tree (uncommitted changes, staged
     changes, untracked files)
   - The current HEAD commit SHA (to anchor the snapshot to a git state)
   - Active branch name and any in-progress merge/rebase state
   - Stored as a compressed tarball alongside the dossier files

2. **Manual snapshot checkpoints**: A `/bureau-snapshot` command that creates a named
   checkpoint mid-session without folding:

   ```
   /bureau-snapshot "before refactoring auth module"
   ```

   These are lightweight (only changed files since last snapshot) and stored in the
   dossier's session directory.

3. **Snapshot-aware unfold**: When unfolding a dossier, the developer can optionally
   restore the code state:

   ```
   /bureau-unfold my-dossier --restore-snapshot
   ```

   This restores the working tree to the exact state when the snapshot was taken,
   including uncommitted changes.

4. **Rollback to any checkpoint**: If an agent produces bad output mid-session, roll
   back to a named checkpoint:

   ```
   /bureau-rollback "before refactoring auth module"
   ```

   This restores the working tree without creating git commits, resets, or reverts.

5. **Snapshot diffing**: Compare the current working tree against any snapshot to see
   exactly what the agent changed since that checkpoint:

   ```
   /bureau-snapshot-diff "before refactoring auth module"
   ```

**Why this supersedes cc.dev**: cc.dev's snapshots are code-only and workspace-scoped.
Bureau snapshots are *holistic* -- they capture code state, conversation state (dossier),
task state (SQLite), and memory state (what was learned). Rolling back a Bureau snapshot
doesn't just undo code changes; it can restore the full context of where the developer
was in their workflow. And because dossiers are cross-CLI, snapshots taken in a Claude
Code session can be restored in a Gemini session.

**Implementation complexity**: Medium. The `git stash`-like mechanism and tarball
compression are well-understood patterns. The main challenge is making snapshot
restoration reliable across different working tree states and integrating with the
existing dossier lifecycle (fold/unfold).

---

## Summary: strategic positioning

| Addition | Supersedes | Bureau's unique angle | Impact |
|----------|-----------|----------------------|--------|
| **Session replay & walkthroughs** | cc.dev walkthroughs | Multi-source narrative synthesis (dossiers + memories + diffs) | Transforms agent sessions from opaque to transparent |
| **Cross-CLI quality gates** | Continue CI checks | 66 specialized roles as CI agents with configurable standards | Bridges interactive quality to automated enforcement |
| **Adaptive context orchestration** | Continue @-mentions | ML-driven automatic context optimization with feedback loop | Reduces developer cognitive load while improving agent accuracy |
| **Agent performance observatory** | Nothing (novel) | Multi-CLI, multi-model performance data collection and analysis | Makes delegation decisions data-driven, not opinion-based |
| **Snapshot-aware dossiers** | cc.dev snapshots | Holistic state capture (code + reasoning + tasks + memory) | Enables fearless agent experimentation with full-context rollback |

Together, these five additions would position Bureau as the only platform that:
1. **Orchestrates** agents across CLIs (existing strength)
2. **Explains** what agents did and why (walkthrough system)
3. **Enforces** quality standards automatically (quality gates)
4. **Optimizes** context and delegation empirically (adaptive context + observatory)
5. **Protects** developers from agent mistakes (snapshot system)

No competitor addresses more than two of these five capabilities.
