# *Handoff guidelines:* how and when to delegate to subagents

> **Purpose**: a concise guide for when to delegate work vs. when to ask the user for guidance.

## Table of contents

- [Table of contents](#table-of-contents)
- [Terminology](#terminology)
- [Core delegation strategies](#core-delegation-strategies)
  - [Delegation mechanisms available](#delegation-mechanisms-available)
  - [General principles](#general-principles)
  - [Integration with *Superpowers* skills *(Claude and Codex only)*](#integration-with-superpowers-skills-claude-and-codex-only)
- [Choosing *roles* and *mechanisms*](#choosing-roles-and-mechanisms)
  - [Overall guidelines](#overall-guidelines)
  - [When to use `clink`](#when-to-use-clink)
  - [Special guidance for delegating to *Explore* and *Plan* agents](#special-guidance-for-delegating-to-explore-and-plan-agents)
- [When to use Task tool *(Claude Code only)*](#when-to-use-task-tool-claude-code-only)
- [Choosing *models* to use](#choosing-models-to-use)
  - [General guidelines](#general-guidelines)
  - [Detailed picks to use by task category](#detailed-picks-to-use-by-task-category)
  - [Intra-prompt thinking level optimization (by CLI)](#intra-prompt-thinking-level-optimization-by-cli)
- [Handoff patterns](#handoff-patterns)
- [When to ask the user (AskUserQuestion)](#when-to-ask-the-user-askuserquestion)
  - [General guidelines](#general-guidelines-1)
  - [Best practices](#best-practices)
  - [What requires explicit approval, always](#what-requires-explicit-approval-always)

## Terminology

| Concept | Definition |
| :------ | :--------- |
| **Skill** | *Superpowers* workflow (e.g., `superpowers:test-driven-development`) + any extra Claude/Codex skills files you define |
| **Agent** |  Personas used by agents (e.g., `debugger`, `architect`), invoked either directly in your main chat or as subagents |
| **Subagent** | A child **agent**, isolated from the main chat, spawned to complete a particular task by *either* (1) Claude Code first-party "subagents" feature or (2) `clink` |
| **MCP** | MCP servers made available for you to use; see `compact-mcp-list.md` (on your list of must-read files) for a full guide |

## Core delegation strategies

### Delegation mechanisms available

1. `clink` (from Zen MCP, available everywhere): Cross-model orchestration to Claude, Codex (GPT‑5‑Codex), Gemini
2. `Task` tool (Claude‑only): Spawn specialized Claude Code subagents
3. `AskUserQuestion`: Stop and obtain explicit user guidance

### General principles

- Delegate when another model or role materially improves accuracy, speed, cost, or context handling.
- Ask the user when requirements are ambiguous, multiple valid options exist, or explicit approval is required.
- Handle directly when the task is within your capability and scope is clear.

### Integration with *Superpowers* skills *(Claude and Codex only)*

#### Precedence rule when both systems apply

1. **Process enforcement (*Superpowers*)**: If a *Superpowers* skill mandates a specific workflow (e.g., TDD, systematic debugging), you MUST follow it — this is non-negotiable per the skill's requirements.
2. **Capability selection**: Within that mandated workflow, use handoff guidelines (this file) and model selection guide to choose:

    - Which model/CLI to use (`clink` with appropriate role)
    - Which MCP tools to leverage (per `compact-mcp-list.md`)
    - When to delegate vs. handle directly

#### Both systems are complementary

- *Superpowers* defines ***how** to work*
- `handoff-guidelines.md` defines ***who** does it*
- `mcp-compact-list.md` defines ***which tools** are used*

For example, suppose you are performing a debugging task. Examples of what could be enforced by each system:

| System | What it enforces/leads you to do |
| :-- | :-- |
| Superpowers | Use `systematic-debugging` skill (4-phase investigation process) |
| "Handoff guidelines" and "Compact MCP list" guides | Use Codex via `clink` with `debugger` role + Serena MCP for code search |

## Choosing *roles* and *mechanisms*

### Overall guidelines
- If you are Claude Code (Sonnet/Haiku/Opus):
  
  - Use `Task` tool only for Claude subagents.
  - Use `clink` for delegation to Codex or Gemini.

- If you are Codex or Gemini CLI: Use `clink` for all delegation (never `Task`).

### When to use `clink`

Use `clink` to delegate to another model when:
- Context window constraints require Gemini’s 1M context; otherwise prefer Codex for code accuracy.
- Cost/speed optimizations are needed (e.g., batch generation, fast prototyping).
- Specialized reasoning is required (e.g., heavy math/algorithm analysis, large‑scale mechanical refactors, formal threat modeling, maximum depth reasoning).
- Ultra‑fast interactive loops are needed (e.g., Haiku for speed).

How to use `clink` (canonical specifics):
- Provide `cli_name` (`claude`, `codex`, `gemini`), a clear `prompt`, and a `role` (roles live in the clink role prompts directory).
- Always reuse `continuation_id` to preserve conversation context.
- Include absolute file paths when relevant.

### Special guidance for delegating to *Explore* and *Plan* agents

For these agents, you can specify *thoroughness* in your prompt:
| Thoroughness level | Result |
| :--- | :--- |
| "quick" | Basic pattern matching, fast lookups |
| "medium" | Moderate exploration across multiple files |
| "very thorough" | Comprehensive analysis across entire codebase |

## When to use Task tool *(Claude Code only)*

`Task` is Claude Code‑only. Use it to spawn Claude subagents for:
- Codebase exploration (e.g., Explore agent with configurable thoroughness).
- Multi‑step research tasks and token‑conserving searches.
- Parallelizing independent search/analysis tasks.

When not to use `Task`:
- Single known file reads or known symbol queries (use direct tools instead).
- Cross‑model delegation (use `clink`).

## Choosing *models* to use

### General guidelines

- Prefer **GPT‑5‑Codex** for multi‑file refactoring, mechanical changes, contract/testing, and cross‑file code accuracy when the total context fits ≤400K.

    - Especially prefer **GPT-5-Codex + High thinking** for DB/ML/optimization/other math-heavy work (unless context is above >400K: see the next point).

- Use **Gemini** ONLY when you genuinely need >400K context.
- Use **Claude** for complex agentic coordination, planning, and reasoning where context fits.
    
    - **Sonnet** (with extended thinking) should be sufficient for most tasks.
    - **Opus** has strict weekly limits; use sparingly for highest-impact work and when tasks require maximum rigour.

### Detailed picks to use by task category

Note you must also defer to [Rules of thumb](#rules-of-thumb) for size‑driven decisions.

| Task Category | First Pick | CLI | Role | Why |
| --- | --- | --- | --- | --- |
| Architecture & system design | Sonnet 4.5 | `claude` | `architect` | Trade‑off aware planning; extended thinking |
| Large migrations & refactors | GPT‑5‑Codex | `codex` | `migration-refactoring` | Best for repo‑wide mechanical changes |
| API integration | GPT‑5‑Codex | `codex` | `api-integration` | Contract‑first design; idempotency/retry patterns |
| Data engineering / ML | GPT‑5‑Codex | `codex` | `ai-ml-eng` | Superior code/math accuracy when ≤400K tokens |
| Database optimization | GPT‑5‑Codex | `codex` | `db-internals` | Cross‑file SQL + app code analysis |
| Performance optimization | GPT‑5‑Codex | `codex` | `optimization` | Finds N+1s, blocking I/O, complexity issues |
| Frontend / design systems | GPT‑5‑Codex | `codex` | `frontend` | Component refactors; accessibility |
| Platform / DevEx / Infra | Haiku 4.5 | `claude` | `platform-eng` | CI fix‑ups; batch hygiene; speed |
| Observability / incident | Sonnet 4.5 | `claude` | `observability` | Runbooks; SLO/error budgets; RCAs |
| Reliability / scalability | Sonnet 4.5 | `claude` | `scalability-reliability` | Capacity plans; coordination |
| Security / privacy | Sonnet 4.5 | `claude` | `security-compliance` | Threat modeling; audits |
| Testing / verification | GPT‑5‑Codex | `codex` | `testing` | Unit/property/mutation tests |
| Real‑time systems | GPT‑5‑Codex | `codex` | `realtime` | Latency budgets; scheduling |
| Systems: C++ | GPT‑5‑Codex | `codex` | `cpp-pro` | Concurrency, FFI, safety |
| Systems: Rust | GPT‑5‑Codex | `codex` | `rust-pro` | Ownership, unsafe blocks |
| Systems: Go | GPT‑5‑Codex | `codex` | `golang-pro` | Goroutines, channels |
| DevOps / IaC | GPT‑5‑Codex | `codex` | `devops-infra-as-code` | Terraform, Kubernetes |
| Implementation helper | Any | Any | `implementation-helper` | General coding assistance |
| Code explanation / understanding | Any with good context | Any | `explainer` | Choose model based on codebase size/complexity |
| Architecture audits | Sonnet 4.5 | `claude` | `architecture-audit` | Deep analysis of existing architecture; identify issues |
| Tech debt analysis | Sonnet 4.5 | `claude` | `tech-debt` | Identify and prioritize technical debt systematically |
| Cost optimization | Sonnet 4.5 | `claude` | `cost-optimization-finops` | Cloud costs; resource optimization; FinOps strategies |
| Distributed systems design | Sonnet 4.5 | `claude` | `distributed-systems` | Consensus; consistency; partition tolerance |
| Networking / edge infrastructure | GPT‑5‑Codex | `codex` | `networking-edge-infra` | CDN; load balancing; edge compute patterns |
| Mobile engineering | GPT‑5‑Codex | `codex` | `mobile-eng-architect` | iOS/Android architecture; mobile‑specific patterns |
| Whole‑repo analysis >400K tokens | Gemini 2.5 Pro | `gemini` | `explainer` | 1M‑token context |
| API client SDK design | GPT‑5‑Codex | `codex` | `api-client-designer` | Idiomatic SDKs; retries/pagination/auth; contract‑driven |
| Authentication engineering | Sonnet 4.5 | `claude` | `auth-specialist` | Secure flows (sessions/OAuth/JWT); OWASP; least privilege |
| Caching strategy & implementation | Gemini 2.5 Pro | `gemini` | `caching-specialist` | Layering, TTL/invalidations, cache keys, metrics |
| Chaos engineering & resilience drills | Sonnet 4.5 | `claude` | `chaos-engineer` | Plan experiments, limit blast radius, SLOs; coordinate runs |
| Code review | GPT‑5‑Codex | `codex` | `code-reviewer` | Quality, security, maintainability; actionable diffs |
| Data engineering pipelines | Gemini 2.5 Pro | `gemini` | `data-eng` | ETL/ELT, SQL tuning, batch/stream jobs |
| Debugging and triage | GPT‑5‑Codex | `codex` | `debugger` | Cross‑file fault isolation; logs/traces; reproduction |
| Event‑driven design/implementation | GPT‑5‑Codex | `codex` | `event-driven` | Topics/queues, idempotency, backpressure, ordering |
| Engineering historian | Sonnet 4.5 | `claude` | `historian` | Change timelines, root causes, commit/story synthesis |
| Incident command | Sonnet 4.5 | `claude` | `incident-commander` | Runbooks, comms, decision logs, mitigations |
| Interviewer (requirements) | Sonnet 4.5 | `claude` | `interviewer` | Clarify constraints/trade‑offs; elicit missing info |
| Schema evolution & migrations | GPT‑5‑Codex | `codex` | `schema-evolution` | Backward‑compatible changes, migrations, rollout/rollback |
| Repository/code search | Haiku 4.5 | `claude` | `searcher` | Fast exploration; summarize findings; pointers |
| Task decomposition | Sonnet 4.5 | `claude` | `task-decomposer` | Break goals into verifiable steps, deps, risks |

### Intra-prompt thinking level optimization (by CLI)

#### Codex 

Within your prompt:
- "minimal effort": formatting, regex
- "low effort": single-file
- default: cross-file
- "high effort": migrations, concurrency

#### Claude

Mention "extended thinking" for:
- Long-horizon refactors, RCAs, multi-service planning, complex research

## Handoff patterns

Follow the sequential flow of phases in the table below (in the order presented):

| Order | Phase name | Objectives | Actions to perform |
| :--- | :--- | :--- | :--- |
| **1** | **Research** | Understand requirements, code, and constraints | Use `Task` Explore (Claude) for codebase exploration; use direct read/glob for known files/symbols; use `clink`→Gemini for long‑context needs (>~400K). If ambiguity remains, see [AskUserQuestion](#when-to-ask-the-user-askuserquestion) |
| **2** | **Planning** | Design the approach, break down tasks, identify risks | Outline steps; note trade‑offs; delegate complex architecture to Claude (`architect`) or refactoring planning to Codex (`migration-refactoring`) via `clink`. For large goals, use `task-decomposer` to produce verifiable substeps and dependencies. Resolve ambiguities via [AskUserQuestion](#when-to-ask-the-user-askuserquestion). Obtain approval before implementation when needed (see [What requires explicit approval, always](#what-requires-explicit-approval-always)). |
| **3** | **Implementation** | Execute the plan and write changes | Track tasks; use Codex for wide refactors/testing; use Claude for coordination; use Gemini for long‑context codebase analysis. Leverage specialist roles as needed (e.g., `schema-evolution`, `auth-specialist`, `caching-specialist`, `event-driven`, `debugger`). For approval gates (commits/deploys/destructive ops), see [What requires explicit approval, always](#what-requires-explicit-approval-always). |
| **4** | **Review/Verification (optional)** | Verify changes, run tests, prepare for commit | Request code review (use `code-reviewer` for structured guidance); run tests; follow the [Approval pattern](#approval-pattern) before committing/pushing. |

## When to ask the user (AskUserQuestion)

### General guidelines

Ask the user when:
- Requirements are ambiguous, trade‑offs are uncited, or multiple valid approaches exist.
- High‑impact architectural decisions are involved (system design, stack selection, breaking changes).
- Critical information is missing (configs, environment details).
- Security/compliance sensitivity exists (credentials, access control, retention).
- Before destructive operations or any action listed under “Explicit Approval”.

### Best practices
- Provide 2–4 clear options with concise trade‑offs; allow multi‑select when appropriate.
- Include context about why you’re asking; keep headers short.

### What requires <ins>explicit</ins> approval, <ins>always</ins>

- **Version control operations**: creating commits (unless explicitly told), pushing, merging, rebasing, force pushes, amending commits.

  - Exception: User explicitly says "commit this" or "push these changes".

- **Destructive operations**: deleting files/dirs, truncating databases, dropping tables, purging caches, removing dependencies.

  - *Exception*: User explicitly says "delete X" or removal is part of an explicitly approved refactoring task.

- **Production/deployment**: prod deploys, prod config changes, service restarts, env var changes, prod migrations.

  - Never assume: always ask even if user says "deploy".

- **Security/access changes**: authN/Z changes, permission grants, exposing endpoints, disabling security features, handling secrets.
- **Breaking changes**: public API removals, signature changes without backward compatibility, schema changes without migrations, config format changes.

  - *Exception*: Proceed only with explicit user approval for the breaking change.

- **Cost‑impacting changes**: adding cloud resources, increasing instance size, storage tier changes, rate‑limit changes, adding paid third‑party services.

#### Approval pattern

1. Clearly state what will happen
2. List affected resources/files
3. Explain potential risks/impacts
4. Use AskUserQuestion with clear options
5. Wait for explicit approval
6. Proceed only after approval
