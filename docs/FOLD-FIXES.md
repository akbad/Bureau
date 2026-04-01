# Fold/Unfold system fixes

> Comprehensive issue tracker for the Bureau dossier fold/unfold system.
> Each issue includes root cause analysis, affected code paths, and
> detailed solution(s) ready for implementation.

#### Contents:
- [New primitive for task-scoped context](#new-primitive-for-task-scoped-context)
  - [The gap: coordination without context distribution](#the-gap-coordination-without-context-distribution)
  - [Two primitives, two scenarios](#two-primitives-two-scenarios)
  - [CLI interface](#cli-interface)
  - [Context extraction logic](#context-extraction-logic)
  - [Worker-mode output format](#worker-mode-output-format)
  - [Schema changes](#schema-changes)
  - [Workflow: Scenario 1 — main agent delegates to subagent](#workflow-scenario-1--main-agent-delegates-to-subagent)
  - [Workflow: Scenario 2 — user launches a separate interactive worker](#workflow-scenario-2--user-launches-a-separate-interactive-worker)
  - [Workflow: parallel multi-worker fan-out](#workflow-parallel-multi-worker-fan-out)
  - [Fold skill changes for task-context enrichment](#fold-skill-changes-for-task-context-enrichment)
  - [Unfold skill changes for worker mode](#unfold-skill-changes-for-worker-mode)
  - [Template changes](#template-changes)
  - [Interaction with the lock system](#interaction-with-the-lock-system)
  - [Edge cases](#edge-cases)
  - [Rejected alternatives](#rejected-alternatives)
  - [Implementation plan](#implementation-plan)
- [Critical issues](#critical-issues)
  - [C1. File interactions are stored but never rendered on unfold](#c1-file-interactions-are-stored-but-never-rendered-on-unfold)
  - [C2. `release_lock` has no agent verification](#c2-release_lock-has-no-agent-verification)
  - [C3. `--claim` without `--agent` silently stores NULL as lock holder](#c3---claim-without---agent-silently-stores-null-as-lock-holder)
- [High-value improvements](#high-value-improvements)
  - [H1. Compact unfold omits session digests entirely, losing critical resumption context](#h1-compact-unfold-omits-session-digests-entirely-losing-critical-resumption-context)
  - [H2. Rejected alternatives silently dropped from unfold output](#h2-rejected-alternatives-silently-dropped-from-unfold-output)
  - [H3. Undifferentiated error types in unfold CLI output](#h3-undifferentiated-error-types-in-unfold-cli-output)
- [Subtle issues](#subtle-issues)
  - [S1. The compact/full divide creates a context cliff](#s1-the-compactfull-divide-creates-a-context-cliff)
  - [S2. Fold instructs agents to "reconstruct reasoning" for implicit decisions](#s2-fold-instructs-agents-to-reconstruct-reasoning-for-implicit-decisions)
  - [S3. `update_task` cannot clear nullable fields](#s3-update_task-cannot-clear-nullable-fields)
  - [S4. Hash collision possible with no existence check](#s4-hash-collision-possible-with-no-existence-check)
  - [S5. `find_dossier` hash matching is case-sensitive but hashes are always lowercase](#s5-find_dossier-hash-matching-is-case-sensitive-but-hashes-are-always-lowercase)
  - [S6. Fold-then-unfold information asymmetry for decisions](#s6-fold-then-unfold-information-asymmetry-for-decisions)
  - [S7. Decision duplication on re-fold has no code-level guard](#s7-decision-duplication-on-re-fold-has-no-code-level-guard)
- [Minor polish](#minor-polish)
  - [M1. `cmd_fold` reports task/decision counts from input, not from the database](#m1-cmd_fold-reports-taskdecision-counts-from-input-not-from-the-database)
  - [M2. `cmd_list` does not render lock status](#m2-cmd_list-does-not-render-lock-status)
  - [M3. `show` command is functionally identical to `unfold`](#m3-show-command-is-functionally-identical-to-unfold)
  - [M4. `--description` in `tasks add` is write-only data](#m4---description-in-tasks-add-is-write-only-data)
  - [M5. Timestamp format inconsistency between fold and tasks](#m5-timestamp-format-inconsistency-between-fold-and-tasks)
  - [M6. Unfold SKILL expects relative timestamps but CLI outputs raw ISO](#m6-unfold-skill-expects-relative-timestamps-but-cli-outputs-raw-iso)
  - [M7. No CLI-level test coverage for fork and claim paths](#m7-no-cli-level-test-coverage-for-fork-and-claim-paths)
  - [M8. Active skills have no structured storage](#m8-active-skills-have-no-structured-storage)
- [Priority matrix](#priority-matrix)
- [Recommended implementation order](#recommended-implementation-order)


## New primitive for task-scoped context

The dossier system has strong **task coordination** primitives: `tasks claim`, `tasks complete`, and `tasks add` are all atomic, multi-agent safe, and CAS-protected. But it has no **task-scoped context distribution** primitive. When a worker agent needs to pick up a task from a dossier, it faces two bad options and nothing in between:

1. **Full unfold** (`bureau-dossiers unfold <id>`) — dumps the entire dossier narrative (all tasks, all decisions, all session digests), positions the agent as an orchestrator via the context injection directive (*"Pick up from the EXACT point described in the pending state"*), and wastes context tokens on irrelevant tasks and decisions.
2. **Just the task CLI** (`bureau-dossiers tasks <slug> list` / `claim`) — the agent can claim a task but has zero context about decisions, file interactions, constraints, or the digest. It is working blind.

This section defines the missing primitive and the workflows that use it.

### The gap: coordination without context distribution

Two concrete scenarios expose the gap:

**Scenario 1 — Main agent spawns an isolated subagent.** The main agent has full dossier context loaded via `/unfold-dossier`. It wants to delegate task #3 to a subagent (via the `Agent` tool or headless CLI invocation). Today, the main agent must manually construct the subagent prompt with cherry-picked context — an ad-hoc, lossy process with no structured mechanism. If the main agent forgets to include a relevant decision or file interaction, the subagent has no way to self-serve the missing context (short of running a full unfold and flooding its context window).

**Scenario 2 — User launches a separate interactive agent as a worker.** The user opens a second terminal / CLI session and wants that agent to pick up a specific task from an existing dossier. The agent's only options are a full unfold (becoming another orchestrator, with framing that says "you own the whole workflow") or working blind with just the task CLI. There is no "worker-mode" unfold that gives the agent just enough context for one task, with framing that says "you are here to complete this task, not to orchestrate."

### Two primitives, two scenarios

The solution introduces two complementary CLI primitives:

| Primitive | Purpose | Side effects | Primary scenario |
|-----------|---------|-------------|------------------|
| `bureau-dossiers context` | Read-only task-scoped context extraction | None (pure query) | Scenario 1: main agent extracts context to include in a subagent prompt |
| `bureau-dossiers unfold --worker --task <id>` | Self-serve worker entry: extract context + claim task + worker framing | Claims the target task | Scenario 2: separate interactive agent picks up a task |

The `context` command is the building block. It extracts and renders the subset of the dossier relevant to a specific task. It can be called multiple times (for tasks #3, #5, #7 to fan out three parallel workers) without side effects.

The `unfold --worker` flag is the self-serve entry point. It composes `context` extraction with atomic task claiming and worker-specific framing, producing a complete self-contained context injection for a single-task agent.

### CLI interface

#### `bureau-dossiers context` — read-only extraction

```
bureau-dossiers context <slug> --task <id> [--include-digest] [--format markdown|json]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `slug` (positional) | Yes | — | Dossier slug |
| `--task` | Yes | — | Task ID to extract context for |
| `--include-digest` | No | Off | Include the latest session digest (adds ~3-10KB) |
| `--format` | No | `markdown` | Output format: `markdown` or `json` |

Examples:

```bash
# extract context for task #3, compact (no digest)
bureau-dossiers context my-feature-abc123 --task 3

# include the latest session digest for a complex task
bureau-dossiers context my-feature-abc123 --task 3 --include-digest

# JSON output for programmatic consumption (e.g., building a subagent prompt)
bureau-dossiers context my-feature-abc123 --task 3 --format json
```

**Why a separate command (not a flag on `unfold`):** `context` and `unfold` have different semantics. `unfold` is an agent initialization operation — load dossier, set up framing, optionally claim/fork. `context` is a query — "give me what's relevant to this task." Mixing them would overload `unfold` with incompatible concerns. Keeping them separate also means `context` can be called repeatedly (extract for tasks #3, #5, #7) without side effects.

#### `bureau-dossiers unfold --worker --task <id>` — self-serve worker entry

```
bureau-dossiers unfold <query> --worker --task <id> --agent <agent-id>
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `query` (positional) | Yes | — | Dossier hash or name (existing) |
| `--worker` | Yes | — | Activate worker mode |
| `--task` | Yes | — | Task ID to work on |
| `--agent` | Yes | — | Agent identifier (required for the atomic task claim) |

Behavior:

1. Resolve the dossier (same resolution logic as existing `unfold`).
2. Atomically claim the task via the existing CAS `claim_task()`. If the task is not pending, fail with a structured error (see [Edge cases](#edge-cases)).
3. Extract task-scoped context (same logic as the `context` command, with `--include-digest` off by default — the digest is 3-10KB and mostly contains orchestrator-level narrative irrelevant to a focused task; workers opt in with `--include-digest` when the task is genuinely complex).
4. Wrap the output in worker-mode framing (see [Worker-mode output format](#worker-mode-output-format)).
5. Print the complete context injection to stdout.

Examples:

```bash
# user opens a second terminal, agent picks up task #3
bureau-dossiers unfold my-feature --worker --task 3 --agent claude-code

# through the unfold SKILL.md, the user can also invoke:
/unfold-dossier my-feature --worker --task 3
```

#### Validation rules

| Flag combination | Valid? | Error message |
|-----------------|--------|---------------|
| `unfold --worker --task 3 --agent x` | Yes | — |
| `unfold --worker --task 3` (no `--agent`) | **No** | `Error: --agent is required when using --worker` |
| `unfold --worker` (no `--task`) | **No** | `Error: --task is required when using --worker` |
| `unfold --worker --full` | **No** | `Error: --worker and --full are incompatible (worker uses focused context, not full unfold)` |
| `unfold --worker --claim` | **No** | `Error: --worker and --claim are incompatible (worker claims a task, not the dossier)` |
| `unfold --worker --fork` | **No** | `Error: --worker and --fork are incompatible (worker operates on an existing dossier)` |
| `context <slug> --task 3` | Yes | — |
| `context <slug>` (no `--task`) | **No** | `Error: --task is required` |

### Context extraction logic

The core question: how does the system determine what context is relevant to a specific task? Three approaches were evaluated.

#### Approach A: Explicit junction table (rejected)

Add a `task_context_links` table mapping tasks to specific decisions, files, and digest sections. The fold skill instructs agents to populate these links when creating tasks.

**Rejected because:** Adds schema complexity, fold-time cognitive burden (the folding agent is already doing substantial work), and a cold-start problem — existing dossiers have no links. Folding agents may also miss a linkage, meaning a worker silently loses a critical decision.

#### Approach B: Heuristic keyword matching (rejected)

Match the task subject and description against decision text, file paths, and digest content using keyword overlap or fuzzy matching.

**Rejected because:** Unreliable. "Fix the login page" might match a decision about "page size limits" or a file named `pagination.py`. False positives waste tokens; false negatives lose critical constraints.

#### Approach C: Fixed context slice with optional annotations (chosen)

Always include a fixed set of context for any task, composed of elements that are either universally relevant (decisions constrain all work) or compact enough that including them unconditionally is cheaper than the risk of omitting something relevant.

**Why this works:** Decisions are compact (one line each, typically 10-30 total, ~500-1500 tokens). File interactions are compact (~30 tokens each). The only large element — the session digest (~3-10KB) — is opt-in. Including all decisions unconditionally eliminates the risk of a worker violating an unseen constraint, at negligible token cost.

#### `blocked_by` field format

The `blocked_by` column is `TEXT` in the schema and holds a **single integer task ID as a string** (e.g., `"3"`). This matches all existing usage: the CLI accepts `--blocked-by 3`, `add_task()` stores it verbatim, the test suite asserts `blocked_by == "1"`, and the fold SKILL instructs agents to pass a single ID.

The dependency resolver in `context.py` must:

1. **Parse** `blocked_by` as `int(value)` after stripping whitespace.
2. **Handle malformed values gracefully** — if `int()` fails (e.g., the value is `"foo"` or `"1,2"`), skip dependency resolution for that task and render a warning: `*Warning: blocked_by value "{value}" on task #{id} is not a valid task ID — skipping dependency resolution.*`
3. **Handle dangling references** — if the parsed ID does not match any task in the dossier, skip it with a warning: `*Warning: task #{id} references blocked_by #{ref_id} which does not exist.*`

Multi-dependency (a task blocked by multiple others) is not currently supported. If needed in the future, the field can be extended to a comma-separated list with a corresponding parser change in `_resolve_dependency_chain`. This is not implemented now because no existing workflow produces multi-dependency values.

#### What gets included

For a given task ID, the extraction assembles:

| Element | Included | Est. tokens | Rationale |
|---------|----------|-------------|-----------|
| Dossier header (name, hash, branch, project, commit) | Always | ~100 | Orientation — the worker needs to know what repo/branch it's in |
| **Target task** (full details incl. description + context notes) | Always | ~50-150 | The assignment itself |
| **Dependency chain** (tasks referenced by `blocked_by`, transitively) | Always | ~50/dep | What was done before this task — the worker needs this to understand the starting state |
| **All decisions** | Always | ~500-1500 | Durable architectural constraints that apply to all work; filtering risks missing one |
| **File interactions** (latest session) | Always | ~300-900 | Which files exist, what was done to them, current state of the codebase |
| **Sibling tasks** (ID + subject + status only, no descriptions) | Always | ~20/task | The worker's place in the bigger plan — enough to avoid stepping on other workers |
| **Latest session digest** | Opt-in (`--include-digest`) | ~1000-3000 | The "why behind the why," user preferences, in-flight state, technical gotchas |

**Token budget:**

| Dossier size | Without digest | With digest |
|--------------|---------------|-------------|
| Small (5 tasks, 5 decisions, 10 files) | ~1.5KB (~500 tokens) | ~5KB (~1500 tokens) |
| Medium (15 tasks, 20 decisions, 30 files) | ~4KB (~1200 tokens) | ~12KB (~3500 tokens) |
| Large (30 tasks, 50 decisions, 50 files) | ~8KB (~2400 tokens) | ~20KB (~6000 tokens) |

For comparison, a full `unfold --full` of a medium dossier is ~15-30KB (~5000-10000 tokens). Worker context without digest is consistently 3-5x smaller.

### Worker-mode output format

#### `context` command output (raw extraction, no framing)

```markdown
# Task Context: <task subject>

**Dossier:** `<name>` (`<hash>`) | **Branch:** `<branch>` | **Project:** `<project>`

## Your task

| Field | Value |
|-------|-------|
| ID | <id> |
| Subject | <subject> |
| Status | <status> |
| Owner | <owner or "unassigned"> |
| Blocked by | <blocked_by or "none"> |

<description, rendered as paragraph if present>

**Context notes:** <context_notes, if present>

## Dependencies

<if blocked_by references exist, resolved transitively:>

These tasks were completed before yours and inform your work:

| ID | Subject | Status | Owner |
|----|---------|--------|-------|
| <dep_id> | <dep_subject> | <dep_status> | <dep_owner> |

<if no dependencies:>

This task has no dependencies.

## Decisions

All architectural decisions for this dossier. Follow these constraints:

- **<what>**: <why> *(rejected: <alternatives>)* *(decided by: <decided_by>)*
- ...

## Key files

| File | Action | Annotation |
|------|--------|------------|
| `<path>` | <action> | <annotation> |
| ... |

## Other tasks in this dossier

| ID | Subject | Status |
|----|---------|--------|
| <id> | <subject> | <status> |
| ... |

<if --include-digest:>

## Session context

*Folded at <timestamp> by <agent>*

<latest session digest content>
```

#### `unfold --worker` output (extraction + framing)

The worker-mode unfold wraps the raw extraction with a directive block:

```markdown
# Worker Agent Context

> You are a **worker agent** assigned to a single task from a multi-agent
> dossier. Your scope is strictly limited to the task below. You are NOT
> an orchestrator.
>
> **Rules:**
> - Complete ONLY the assigned task. Do not work on other tasks.
> - Follow ALL decisions listed below. Do not re-propose rejected alternatives.
> - When done, mark the task complete:
>   `bureau-dossiers tasks <slug> complete --id <id>`
> - Do not modify the dossier's task list (no adding, removing, or
>   reordering) unless you discover blocking sub-work, in which case use:
>   `bureau-dossiers tasks <slug> add --subject "..." --blocked-by <your-task-id>`
> - If you encounter a blocker that prevents completion, update the task
>   and report to the user:
>   `bureau-dossiers tasks <slug> update --id <id> --status blocked`
> - Do NOT acquire dossier-level locks. Your coordination primitive is the
>   task claim, which has already been applied.

<full output from context extraction above>


*Task #<id> claimed by <agent> at <timestamp>. Dossier: `<slug>`*
```

#### Key differences from orchestrator framing

| Aspect | Orchestrator (`unfold`) | Worker (`unfold --worker`) |
|--------|------------------------|---------------------------|
| Framing | "You are resuming a conversation from a dossier" | "You are a worker agent assigned to a single task" |
| Scope | All tasks, full narrative, open-ended | Single task, bounded scope |
| Task detail | All tasks rendered with equal weight | One task in detail; others as a compact summary |
| Session digests | Latest (compact, after H1) or last N (full) | Opt-in via `--include-digest` |
| Directives | "Pick up from the EXACT point..." | "Complete ONLY the assigned task" |
| Lock behavior | Optionally claims the dossier | Claims a single task (no dossier lock) |

### Schema changes

One new nullable column on the existing `tasks` table:

```sql
ALTER TABLE tasks ADD COLUMN context_notes TEXT;
```

**Purpose:** Free-text field populated at fold time (or via `tasks add --context-notes "..."`) containing task-specific context hints for worker agents. This is the explicit linkage between a task and the knowledge a worker needs — file paths, relevant decisions, user preferences, gotchas — without requiring a junction table or heuristic matching.

**Migration strategy:** Lazy migration applied in `connect_dossier_db()`. When a dossier is opened and the column does not exist, add it:

```python
import sqlite3

def _ensure_schema_current(conn: sqlite3.Connection) -> None:
    """Apply incremental schema migrations for older dossiers.

    Safe under concurrent access: if two agents open the same dossier
    simultaneously after an upgrade, the second ALTER TABLE will fail
    with OperationalError (duplicate column). We catch and ignore that
    specific error since it means the migration already succeeded.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "context_notes" not in columns:
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN context_notes TEXT")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                pass  # another agent already applied this migration
            else:
                raise
```

**Backward compatibility:** Existing dossiers get `context_notes = NULL` for all tasks. The context extraction still works because decisions and file interactions are included unconditionally. The `context_notes` field is strictly additive — it improves worker context when present, but its absence does not break anything.

Bump `SCHEMA_VERSION` from 1 to 2 in `db.py`.

**No new tables.** The design deliberately avoids junction tables, aspect tables, or new indexes. The `context` command works by querying existing tables (`metadata`, `tasks`, `decisions`, `file_interactions`, `sessions`) and assembling the results. The only schema change is the single `context_notes` column.

### Workflow: Scenario 1 — main agent delegates to subagent

The main agent has full dossier context loaded via `/unfold-dossier`. It identifies task #3 for delegation.

**Step 1 — Pre-claim the task on behalf of the subagent:**

```bash
bureau-dossiers tasks my-feature-abc123 claim --id 3 --agent worker-a
```

The main agent claims first (rather than letting the subagent self-claim) to eliminate the race window between subagent spawn and claim. The `worker-a` label is a convention chosen by the main agent.

**Step 2 — Extract task-scoped context:**

```bash
bureau-dossiers context my-feature-abc123 --task 3
```

**Step 3 — Spawn the subagent with the extracted context:**

For the `Agent` tool (Claude Code):

```
prompt: |
  You are a worker agent. Here is your task context:

  <output from step 2>

  Complete this task. When done, run:
  bureau-dossiers tasks my-feature-abc123 complete --id 3
```

For headless CLI invocation (cross-model delegation), the same pattern applies -- the context output is included in the prompt.

**Step 4 — The subagent works and completes:**

The subagent does the work, then runs:

```bash
bureau-dossiers tasks my-feature-abc123 complete --id 3
```

The main agent can poll `bureau-dossiers tasks my-feature-abc123 list` to check progress.

### Workflow: Scenario 2 — user launches a separate interactive worker

The user opens a second terminal and wants that agent to pick up task #3.

**Option A — Explicit invocation via the unfold SKILL:**

The user types:

```
/unfold-dossier my-feature --worker --task 3
```

The unfold skill recognizes `--worker --task` and runs:

```bash
bureau-dossiers unfold my-feature --worker --task 3 --agent claude-code
```

The CLI atomically claims task #3 and outputs the worker-mode context injection. The skill injects this and activates worker-mode framing. The agent greets the user:

```
Working on task #3: Add retry logic to webhook sender
Dossier: my-feature-abc123 | Branch: feat/webhooks

Ready to start.
```

**Option B — Natural language:**

The user tells the agent:

```
Pick up task 3 from the my-feature dossier
```

The agent, following the updated unfold SKILL.md, recognizes this as a worker-mode request and executes the same command.

**On completion:**

```bash
bureau-dossiers tasks my-feature-abc123 complete --id 3
```

The agent reports:

```
Task #3 completed. Dossier: my-feature-abc123
Remaining tasks: 2 pending, 1 in progress
```

The worker does NOT auto-fold. Its contribution is captured via the task status change. If the user wants a full fold, they invoke `/fold-dossier` in the orchestrator session.

### Workflow: parallel multi-worker fan-out

An orchestrator wants to fan out tasks #3, #5, and #7 to three parallel workers.

**Step 1 — Pre-claim all three (sequential, each is a single SQL UPDATE):**

```bash
bureau-dossiers tasks my-feature-abc123 claim --id 3 --agent worker-a
bureau-dossiers tasks my-feature-abc123 claim --id 5 --agent worker-b
bureau-dossiers tasks my-feature-abc123 claim --id 7 --agent worker-c
```

**Step 2 — Extract context for each (parallel, pure reads):**

```bash
bureau-dossiers context my-feature-abc123 --task 3 &
bureau-dossiers context my-feature-abc123 --task 5 &
bureau-dossiers context my-feature-abc123 --task 7 &
```

**Step 3 — Spawn three subagents in parallel, each with its respective context.**

Each subagent completes independently and marks its task done via `tasks complete`.

### Fold skill changes for task-context enrichment

Two changes to `protocols/context/static/skills/fold/SKILL.md`:

**Change 1 — Task enrichment guidance.** Add to Step 2 (Collect task list), after the existing collection strategies:

> **Task enrichment for worker delegation**
>
> For each task, consider whether a future worker agent — with NO prior context about this conversation — could complete the task from just its subject and description. If not, add a `context_notes` field with:
>
> - References to specific decisions that constrain this task
> - Key file paths the worker will need
> - User preferences that affect implementation
> - Technical gotchas discovered during this session
> - Any "you need to know this" context that lives only in your head
>
> ```json
> {
>   "subject": "Add retry logic to webhook sender",
>   "description": "Exponential backoff with jitter, configurable max retries",
>   "context_notes": "User wants max_retries in pipeline.yml, not hardcoded. See decision about SQLite WAL mode — the webhook queue uses the same DB. Key file: /path/to/webhook/sender.py (lines 80-120 are the send loop)."
> }
> ```
>
> The `context_notes` field is optional. Omit it for self-explanatory tasks.

**Change 2 — JSON schema update.** Update the Step 7 field reference to include `context_notes` in the task objects:

```json
"tasks": [
  {
    "subject": "Task subject",
    "status": "pending",
    "owner": null,
    "description": "Task description",
    "blocked_by": null,
    "context_notes": "Optional: context hints for worker agents"
  }
]
```

No changes to the fold collection steps (1-5) or the assembly logic (6-9). The `context_notes` field is populated within the existing Step 2 task collection, not as a new step.

### Unfold skill changes for worker mode

Three changes to `protocols/context/static/skills/unfold/SKILL.md`:

**Change 1 — Add worker-mode invocation form.** Add to the "Invocation forms" table:

```markdown
| `/unfold-dossier <hash> --worker --task <id>` | **Worker** | Claim one task and resume in worker mode |
```

**Change 2 — Add a "Worker mode" section** after the existing "Resume mode" section:

> ## Worker mode
>
> Triggered when `/unfold-dossier` is invoked with `--worker --task <id>`, or when the user asks to "pick up task N" or "work on task N from [dossier]."
>
> ### Step 1: Worker unfold via CLI
>
> ```bash
> bureau-dossiers unfold <hash-or-name> --worker --task <id> --agent <your-agent-id>
> ```
>
> The CLI atomically claims the task and returns task-scoped context with worker framing. If the task is not pending, the CLI reports an error — present the user with the current task list and suggest picking a different task.
>
> ### Step 2: Context injection
>
> Read and internalize the worker context output. Follow the worker directive strictly: complete only the assigned task, follow all decisions, do not orchestrate.
>
> ### Step 3: Greet the user
>
> ```
> Working on task #<id>: <subject>
> Dossier: <slug> | Branch: <branch>
>
> Ready to start.
> ```
>
> ### Step 4: Completion
>
> ```bash
> bureau-dossiers tasks <slug> complete --id <id>
> ```
>
> Report completion. Do NOT fold automatically — the worker's contribution is captured via the task status change.

**Change 3 — Add "Delegating tasks to workers" guidance** in the existing "Resume mode" section, after Step 3 (Context injection directive):

> ### Delegating tasks to workers
>
> When you want to delegate a task to a subagent, use the context extraction primitive:
>
> ```bash
> # pre-claim the task for the subagent
> bureau-dossiers tasks <slug> claim --id <task-id> --agent <subagent-label>
>
> # extract task-scoped context
> bureau-dossiers context <slug> --task <task-id>
> ```
>
> Include the context output in the subagent's prompt. The subagent should complete the task and mark it done via `tasks complete`.

### Template changes

**`CLAUDE.template.md`** — add to the "TASK LIST SCOPE: NATIVE vs BUREAU" section:

> **Worker mode:** When working from a `--worker` unfold, you are scoped to a single task. Use Bureau task CLI for status updates (`tasks complete`, `tasks update`). Do not use native task tools — your coordination is through the dossier.

**`AGENTS.template.md`** — add the equivalent for Codex/Gemini:

> **Worker mode:** When working from a `--worker` unfold, you are scoped to a single task. Use `bureau-dossiers tasks` for status updates. Do not orchestrate — complete your assigned task and report.

### Interaction with the lock system

Worker mode does NOT acquire a dossier-level lock. The two coordination mechanisms are orthogonal:

| Mechanism | Scope | Purpose | Granularity |
|-----------|-------|---------|-------------|
| **Dossier lock** (`lock claim`) | Entire dossier | Exclusive access for an orchestrator that wants to prevent other orchestrators from modifying the dossier structure | Dossier-wide |
| **Task claim** (`tasks claim`) | Single task | Ownership of a specific work item to prevent duplicate work | Per-task |

A dossier can simultaneously have:
- A dossier-level lock held by an orchestrator
- Multiple tasks claimed by different workers

This is the intended multi-agent pattern: one orchestrator manages the work plan, multiple workers execute tasks.

**Lock interaction with `context` reads:** The `context` command is a pure read. It does not check or require locks. A locked dossier's context is readable — locking prevents structural writes, not reads.

**Lock interaction with `unfold --worker`:** The `--worker` flag claims a task (write to the `tasks` table) but does not interact with the dossier lock. Task claiming uses CAS (`WHERE status = 'pending'`), which is independent of the lock mechanism. A worker can claim a task even when the dossier is locked by an orchestrator — the lock protects the dossier structure (metadata, task list composition), while task claims are status transitions on existing tasks.

### Edge cases

#### Task is not pending

If `unfold --worker --task 3` is invoked and task #3 is not pending (already claimed, completed, or deleted), the CLI produces a structured error and lists available tasks:

```
Error [task-claimed]: Task #3 cannot be claimed: status is "in_progress" (owner: codex).
Available pending tasks:
  #5  Add retry logic               pending
  #7  Write integration tests        pending
```

#### Task does not exist

```
Error [task-not-found]: Task #99 does not exist in dossier "my-feature-abc123".
```

#### Dossier has no tasks

```
Error [no-tasks]: Dossier "my-feature" has no tasks. Add tasks first:
  bureau-dossiers tasks my-feature-abc123 add --subject "Task description"
```

#### Task has no linked context (no description, no context_notes, no blocked_by)

The context extraction still works. Decisions and file interactions are included unconditionally, providing ambient context. The task subject is the primary information. The worker may need to explore more, but it is not working blind.

#### Tasks added mid-session via `tasks add`

Tasks added mid-session have no connection to any decision or file interaction recorded at fold time. The fixed-slice approach handles this: all decisions and files are included regardless. The task description (from `--description`) and context notes (from `--context-notes`) carry task-specific context. The agent adding the task should include enough information in these fields for a worker to proceed.

#### Circular dependency chain

If task A has `blocked_by = "B"` and task B has `blocked_by = "A"`, the dependency resolver detects the cycle by tracking visited IDs. It breaks the cycle and renders a warning:

```markdown
## Dependencies

**Warning:** Circular dependency detected in chain involving tasks #3, #5.

| ID | Subject | Status | Owner |
|----|---------|--------|-------|
| 5 | Task B | pending | — |
| 3 | Task A | pending | — |
```

#### Deep dependency chains

If task 7 depends on 6, which depends on 5, which depends on 4, etc., transitive resolution pulls every ancestor into the context. For dossiers with 30+ tasks in a long chain, this could exhaust the token budget. The dependency resolver should accept a `max_depth` parameter (defaulting to 3) and render a truncation notice when exceeded:

```markdown
## Dependencies

*Showing 3 of 8 dependencies (truncated at depth 3)*

| ID | Subject | Status | Owner |
|----|---------|--------|-------|
| ... |
```

#### Workers who discover new decisions

Workers following the worker-mode framing cannot currently record new architectural decisions via the dossier. If S7 Solution A is implemented (skip decisions on re-fold), there is no code path for adding decisions outside of fold. Workers should document findings in the task description or `context_notes` field via `tasks update`. A future `decisions add` CLI command (see S7) would close this gap.

#### Token budget limits

If a dossier has 100+ decisions (unusual but possible for long-running work streams), the `context` output without digest could reach ~15KB. For this case, a future `--max-decisions` flag can cap the count. This is not implemented initially because it is an edge case — most dossiers have 10-30 decisions.

### Rejected alternatives

#### "Smart unfold" with automatic task detection

**Idea:** `unfold --smart` automatically detects which tasks are relevant to the current agent based on file system state, git diff, or agent history.

**Rejected:** Requires assumptions about the agent's environment that may not hold. The system cannot know which task an agent intends to work on. Explicit task ID is simpler, deterministic, and composable.

#### Digest decomposition as a prerequisite

**Idea (from S1):** Break the monolithic digest into five structured aspects stored in a `session_aspects` table, then extract only relevant aspects per task.

**Rejected as a prerequisite:** Digest decomposition is a valuable improvement to the fold/unfold system (and is tracked as S1 in this document), but it is not necessary for task-scoped extraction. The fixed-slice approach — include the latest digest or omit it entirely — is sufficient for workers. Decomposition can be pursued independently and will further improve worker context quality when implemented.

#### Task-decision junction table

**Idea:** A `task_decisions` table mapping tasks to their relevant decisions, populated at fold time.

**Rejected:** Adds schema complexity and fold-time cognitive burden for marginal benefit. Decisions are compact enough to include unconditionally. A junction table would also be lossy — a folding agent might miss a linkage, and the worker would silently lose a critical decision. Including all decisions eliminates this risk.

#### Worker-mode as a standalone command

**Idea:** `bureau-dossiers worker <query> --task <id>` as a new top-level command.

**Rejected:** Worker-mode is conceptually an unfold operation — it loads dossier context for agent consumption. Making it a flag on `unfold` maintains the mental model that `unfold` is the entry point for agent initialization. The `context` command is the read-only primitive; `unfold --worker` is "extract + claim + frame."

#### Automatic re-fold from worker agents

**Idea:** Worker agents automatically fold when they complete their task, capturing their session state back into the dossier.

**Rejected:** A worker's contribution is captured via `tasks complete`. Auto-folding would create a new session digest for a potentially brief 5-minute task — noise in the session history. The orchestrator decides when to fold. Workers that discover important context can document it via `tasks update --id N --description "..."`.

#### Embedding context in the task claim response

**Idea:** Make `tasks claim` return context alongside the claim confirmation.

**Rejected:** Mixes concerns. `tasks claim` is a write operation (state transition); `context` is a read (data extraction). Combining them means every claim requires context assembly, even when the caller just wants to reserve the task. The separate design keeps them composable: claim first, extract context separately, or use `unfold --worker` to do both at once.

### Implementation plan

#### New files

| File | Purpose |
|------|---------|
| `operations/dossiers/context.py` | Task-scoped context extraction logic (`extract_task_context`, `_resolve_dependency_chain`, `render_worker_context`) |
| `operations/dossiers/tests/test_context.py` | Tests for context extraction and worker rendering |

#### Modified files

| File | Change |
|------|--------|
| `operations/dossiers/db.py` | Add `_ensure_schema_current()` lazy migration, bump `SCHEMA_VERSION` to 2 |
| `operations/dossiers/cli.py` | Add `context` subcommand, add `--worker` / `--task` flags to `unfold`, add `--context-notes` to `tasks add` and `tasks update` |
| `operations/dossiers/unfold.py` | Add `unfold_worker()` function |
| `operations/dossiers/tasks.py` | Accept `context_notes` in `add_task()` and `update_task()` — must use S3 sentinel convention for clearability |
| `protocols/context/static/skills/fold/SKILL.md` | Task enrichment guidance, `context_notes` in JSON schema |
| `protocols/context/static/skills/unfold/SKILL.md` | Worker mode section, context extraction guidance for orchestrators |
| `protocols/context/templates/CLAUDE.template.md` | Worker mode note in task list scope section |
| `protocols/context/templates/AGENTS.template.md` | Worker mode note in task list scope section |

#### Slices (each independently deployable and testable)

| Slice | Contents | Enables |
|-------|----------|---------|
| **1. Walking skeleton** | `context.py` + CLI registration + tests | Scenario 1 (main agent extracts context for subagent) |
| **2. Worker mode** | `--worker --task` flags on `unfold` + `unfold_worker()` + framing | Scenario 2 (separate interactive worker) |
| **3. Task enrichment** | Schema migration for `context_notes` + `tasks.py` changes + fold SKILL.md | Improved context quality for future dossiers |
| **4. Skill and template updates** | Unfold SKILL.md worker section + template changes | Agents discover and use the new workflows |

Slice 1 delivers value on its own — Scenario 1 works end-to-end. Slice 2 adds Scenario 2. Slices 3 and 4 are improvements, not prerequisites.

> **Implemented** — Phase 3 Slices 1-3 + Phase 4 Slice 4 (2026-03-29)


## Critical issues

### C1. File interactions are stored but never rendered on unfold

**Root cause:** `unfold.py:unfold_dossier()` queries `metadata`, `tasks`, `decisions`, and (in full mode) `sessions` — but never queries `file_interactions`. The table is populated during fold (`fold.py:121-126`), pruned on a retention window (`fold.py:128-138`), and indexed (`db.py:64-65`), but no consumer ever reads it back.

**Data flow break:**

| Stage | Code path | Works? |
|-------|-----------|--------|
| **Write** | `fold.py:122-126` — `INSERT INTO file_interactions` | Yes |
| **Prune** | `fold.py:128-138` — deletes rows beyond `max_retained_sessions` | Yes |
| **Read** | `unfold.py:71-146` — renders markdown for context injection | **Missing** |

**Impact:** The unfold SKILL.md context injection directive (line 150) tells the resuming agent: *"Do NOT re-explore or re-read files listed in file interactions unless you specifically need to verify something has changed."* But the agent cannot see any file interactions in the unfold output. It re-reads everything from scratch — wasting tokens and losing the annotated context about what action was taken on each file.

**Solution:**

Add a file interactions query and render block in `unfold.py:unfold_dossier()`, between the Decisions section and the Session Digests section. The canonical render order after this fix and H1 is: **Header → Tasks → Decisions → File Interactions (C1) → Latest Session (H1) → Older Sessions (full only)**.

1. **Query the data** — insert after `unfold.py:91` (the `decisions` query), before `conn.close()`:

   ```python
   file_interactions = conn.execute(
       "SELECT fi.file_path, fi.action, fi.annotation, s.id as session_id "
       "FROM file_interactions fi "
       "JOIN sessions s ON fi.session_id = s.id "
       "ORDER BY s.id DESC, fi.id",
   ).fetchall()
   ```

   This fetches all retained file interactions (pruning already limits these to the last N sessions), joined with sessions for ordering context.

2. **Render as a markdown table** — insert after the Decisions render block (after `unfold.py:131`):

   ```python
   if file_interactions:
       lines.append("## File interactions")
       lines.append("")
       lines.append("| File | Action | Annotation |")
       lines.append("|------|--------|------------|")
       for fi in file_interactions:
           annotation = fi["annotation"] or "—"
           lines.append(f"| `{fi['file_path']}` | {fi['action']} | {annotation} |")
       lines.append("")
   ```

3. **Render in both compact and full mode.** The file list is compact (one row per file, typically 10-30 rows) and is critical navigation context. Unlike session digests (which are large narrative blobs), file interactions are structured data with minimal token cost. There is no reason to gate them behind `--full`.

> **Implemented** — Phase 1, Stream A (2026-03-29)


### C2. `release_lock` has no agent verification

**Root cause:** `lock.py:release_lock()` (lines 36-40) unconditionally sets `locked_by = NULL` without checking who holds the lock. Any agent — or any CLI invocation — can release another agent's lock.

```python
# lock.py:36-40 — current code
def release_lock(dossiers_dir: Path, slug: str) -> None:
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    conn.execute("UPDATE metadata SET locked_by = NULL, locked_at = NULL")
    conn.commit()
    conn.close()
```

**Impact:** The unfold SKILL.md (Explicit Behavior 4) says: *"never modify a locked dossier's content or task list unless you are the agent that holds the lock."* But the implementation lets anyone break this contract by releasing a lock they don't own.

**Solution:**

Add agent identity verification to `release_lock()` with an explicit `--force` escape hatch.

1. **Update `lock.py:release_lock()`:**

   ```python
   def release_lock(dossiers_dir: Path, slug: str, agent: str | None = None, force: bool = False) -> None:
       """Release advisory lock.

       If ``agent`` is provided, verifies the caller matches ``locked_by``.
       If ``force`` is True, releases regardless of holder.
       Raises ValueError if the caller does not hold the lock and force is False.
       """
       conn = connect_dossier_db(dossiers_dir / f"{slug}.db")

       if not force and agent:
           meta = conn.execute("SELECT locked_by FROM metadata").fetchone()
           if meta["locked_by"] and meta["locked_by"] != agent:
               holder = meta["locked_by"]
               conn.close()
               raise ValueError(
                   f"Lock held by {holder}, not {agent}. Use --force to override."
               )

       conn.execute("UPDATE metadata SET locked_by = NULL, locked_at = NULL")
       conn.commit()
       conn.close()
   ```

2. **Update the CLI subparser** (`cli.py:325`):

   Replace the bare `lock_sub.add_parser("release", ...)` with:

   ```python
   p_lock_release = lock_sub.add_parser("release", help="Release lock")
   p_lock_release.add_argument("--agent", help="Verify caller identity before releasing")
   p_lock_release.add_argument("--force", action="store_true", help="Force release regardless of holder")
   ```

3. **Update `cmd_lock()`** (`cli.py:203-205`):

   ```python
   elif subcmd == "release":
       try:
           release_lock(dossiers_dir, args.slug, agent=args.agent, force=args.force)
           print("Lock released.")
       except ValueError as e:
           print(f"Error: {e}", file=sys.stderr)
           return 1
   ```

4. **Update the unfold SKILL.md** (line 240) to include `--agent`:

   ```bash
   bureau-dossiers lock <slug> release --agent <your-agent-id>
   ```

> **Implemented** — Phase 1, Stream C (2026-03-29)


### C3. `--claim` without `--agent` silently stores NULL as lock holder

**Root cause:** In `cli.py:272-273`, `--claim` and `--agent` are independent arguments with no co-dependency validation. When an agent passes `--claim` without `--agent`, `args.agent` is `None`. This flows into `claim_lock(dossiers_dir, db_path.stem, agent=None)`. Python does not enforce the `agent: str` type hint at runtime, so `locked_by = NULL` is written to the database — identical to "unlocked."

```python
# cli.py:98-103 — current code
if getattr(args, "claim", False):
    from .lock import claim_lock
    db_path = find_dossier(dossiers_dir, args.query)
    if db_path:
        claim_lock(dossiers_dir, db_path.stem, agent=args.agent)
```

**Impact:** The agent believes it acquired the lock. The dossier is actually unlocked. Any other agent can claim it, silently breaking the exclusivity guarantee.

**Solution A (preferred — CLI validation):**

Add a validation check in `cmd_unfold()` **at the top of the `try` block, before the `--fork` handler** (before `cli.py:88`). This ensures the validation fires before any side effects (forking creates a new database file; if validation ran after the fork, a `--fork --claim` invocation without `--agent` would leave an orphaned fork):

```python
# Validate --claim requires --agent (before any side effects)
if getattr(args, "claim", False) and not args.agent:
    print("Error: --agent is required when using --claim", file=sys.stderr)
    return 1
```

The existing `--claim` handler block (lines 98-103) remains unchanged — by the time it executes, `args.agent` is guaranteed non-None.

**Solution B (defense in depth — runtime guard in `claim_lock`):**

Also add a guard in `lock.py:claim_lock()` as a belt-and-suspenders measure:

```python
def claim_lock(dossiers_dir: Path, slug: str, agent: str) -> None:
    if not agent:
        raise ValueError("Agent identifier is required to claim a lock")
    # ... rest unchanged
```

Both solutions should be applied. Solution A gives a clear CLI error message. Solution B protects against programmatic callers that bypass the CLI.

> **Implemented** — Phase 1, Stream C (2026-03-29)


## High-value improvements

### H1. Compact unfold omits session digests entirely, losing critical resumption context

**Root cause:** Compact mode (the default, `full=False`) renders only metadata, tasks, and decisions. The five mandatory aspects of the fold digest — in-flight state, user preferences, technical gotchas, mental model, and reasoning chains — live exclusively in session digests. These are only rendered when `full=True`.

**The contradiction:** The unfold SKILL.md context injection directive (line 151) tells the resuming agent: *"Pick up from the EXACT point described in the pending state section of the latest session digest."* But in compact mode, no session digests are present. The agent has no way to follow this instruction.

**Impact:** Agents resuming in compact mode (the default) lack the context to meaningfully continue work. They will either ask the user redundant questions (violating the "no re-confirmation" rule) or make incorrect assumptions about what to do next.

**Solution A (minimal change — always include latest digest):**

In `unfold.py:unfold_dossier()`, always fetch and render the **most recent** session digest, regardless of `full` mode. Only older digests are gated behind `--full`.

After the file interactions render block from C1 (or after the decisions render block if C1 has not been applied yet), add:

```python
# Latest session digest (always rendered — contains critical in-flight state)
latest_session = conn.execute(
    "SELECT * FROM sessions ORDER BY id DESC LIMIT 1"
).fetchone()
if latest_session:
    lines.append("## Latest session context")
    lines.append("")
    lines.append(f"*Folded at {latest_session['folded_at']} by {latest_session['agent']}*")
    lines.append("")
    lines.append(latest_session["digest"])
    lines.append("")
```

Move this query before `conn.close()` (line 99) and render it unconditionally.

The `full` mode then renders all *remaining* older sessions as it does today.

**Solution B (structural — decompose the digest into selective fields):**

Add structured columns to the `sessions` table for the most important aspects:

```sql
ALTER TABLE sessions ADD COLUMN pending_state TEXT;
ALTER TABLE sessions ADD COLUMN user_preferences TEXT;
```

Update the fold SKILL.md to instruct agents to populate these fields separately in addition to the monolithic digest. Update `unfold_dossier()` to render these structured fields in compact mode, and the full narrative digest in full mode.

This unlocks a gradient of unfold depth:
- **Compact**: metadata + tasks + decisions + pending state + preferences (~5KB)
- **Full**: everything above + full narrative digests from last N sessions (~15KB+)

Solution B is the higher-leverage structural change but requires schema migration and SKILL.md updates. Solution A is a quick win that delivers 80% of the value.

> **Implemented** — Phase 1, Stream A (2026-03-29)


### H2. Rejected alternatives silently dropped from unfold output

**Root cause:** Decisions are stored with four fields: `what`, `why`, `alternatives`, `decided_by`. But `unfold.py:130` only renders three:

```python
lines.append(f"- **{d['what']}**: {d['why']} *(decided by: {d['decided_by']})*")
```

The `alternatives` column — which may contain a JSON-encoded array of rejected options — is never included in the output.

**Impact:** The entire purpose of recording rejected alternatives is to prevent resuming agents from re-proposing them. Without visibility, agents may re-explore paths that were already considered and rejected, wasting time and frustrating users.

**Solution:**

Replace the single-line decision rendering in `unfold.py:129-130` with:

```python
for d in decisions:
    alt_text = ""
    if d["alternatives"]:
        try:
            alts = json.loads(d["alternatives"])
            if isinstance(alts, list):
                alt_text = f" *(rejected: {', '.join(str(a) for a in alts)})*"
            else:
                alt_text = f" *(rejected: {d['alternatives']})*"
        except (json.JSONDecodeError, TypeError):
            alt_text = f" *(rejected: {d['alternatives']})*"
    lines.append(
        f"- **{d['what']}**: {d['why']}{alt_text} "
        f"*(decided by: {d['decided_by']})*"
    )
```

Add `import json` to the top of `unfold.py` (it is not currently imported there).

> **Implemented** — Phase 1, Stream A (2026-03-29)


### H3. Undifferentiated error types in unfold CLI output

**Root cause:** In `cli.py:cmd_unfold()` (lines 109-114), both `FileNotFoundError` (dossier not found) and `ValueError` (lock conflict or ambiguous match) are caught and printed as `Error: {e}`. The unfold SKILL.md tells agents to present different options depending on the failure mode — `--fork` for lock conflicts vs. re-listing for not-found — but the error messages are not structured enough for agents to distinguish them.

**Impact:** Agents cannot reliably determine the correct recovery action from the CLI output alone. They must parse the English text of the error message, which is fragile.

**Solution:**

Define distinct exception types to avoid fragile string matching. Add to `operations/dossiers/errors.py` (new file):

```python
class DossierNotFoundError(FileNotFoundError):
    """Raised when no dossier matches the query."""

class LockConflictError(ValueError):
    """Raised when a dossier is locked by another agent."""

class AmbiguousQueryError(ValueError):
    """Raised when a query matches multiple dossiers."""
```

Update the raise sites: `unfold.py:find_dossier()` raises `AmbiguousQueryError` (currently `ValueError`), `lock.py:claim_lock()` raises `LockConflictError` (currently `ValueError`), and `unfold.py:unfold_dossier()` raises `DossierNotFoundError` (currently `FileNotFoundError`).

Then replace `cli.py:109-114` with typed catches:

```python
except DossierNotFoundError:
    print(f"Error [not-found]: No dossier found matching \"{args.query}\". "
          f"Run `bureau-dossiers list` to see all dossiers.", file=sys.stderr)
    return 1
except LockConflictError as e:
    print(f"Error [lock-conflict]: {e}. Use --fork to create an independent copy.",
          file=sys.stderr)
    return 1
except AmbiguousQueryError as e:
    print(f"Error [ambiguous]: {e}", file=sys.stderr)
    return 1
except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

The `[not-found]`, `[lock-conflict]`, and `[ambiguous]` tags give agents a reliable signal. Using typed exceptions instead of string matching ensures the classification is stable even if error message wording changes.

> **Implemented** — Phase 2 (2026-03-29)


## Subtle issues

### S1. The compact/full divide creates a context cliff

**Problem:** The system offers only two unfold modes: compact (~3KB: tasks + decisions) or full (~15KB+: everything including all session digests). There is no middle ground. An agent that starts compact and finds it insufficient must re-run `--full`, paying the token cost of compact + full — worse than if it had used `--full` from the start.

The fold SKILL.md instructs agents to write five mandatory aspects into a single monolithic digest blob. The unfold side has no way to selectively retrieve individual aspects.

**Relationship to H1:** This is the structural version of the same problem. H1 provides the quick fix (always render latest digest). This issue describes the deeper architectural improvement. However, H1 combined with the task-scoped context primitive covers ~95% of the need. Defer this unless monitoring shows agents are routinely hitting context cliffs with both H1 and task-scoped context in place.

**Implementation note:** If H1 has already been applied, implementing S1 replaces H1's unconditional latest-digest rendering with selective aspect rendering. The H1 query should be removed at that point.

**Solution:**

Decompose the monolithic digest into retrievable components. Each of the five mandatory aspects becomes a separate column on the `sessions` table or a separate row in a `session_aspects` table:

```sql
CREATE TABLE IF NOT EXISTS session_aspects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id),
    aspect      TEXT NOT NULL,  -- 'pending_state', 'user_preferences', 'technical_context', 'mental_model', 'reasoning_chains'
    content     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_aspects_session
    ON session_aspects(session_id);
```

This enables selective queries:
- `SELECT content FROM session_aspects WHERE session_id = (SELECT MAX(id) FROM sessions) AND aspect = 'pending_state'` — 200 bytes
- All aspects from latest session — ~3KB
- Full narrative digests from last 3 sessions — ~45KB

The fold SKILL.md would instruct agents to populate structured aspect fields alongside the monolithic digest (for backward compatibility). The unfold CLI gains a `--aspects` flag for selective retrieval.


### S2. Fold instructs agents to "reconstruct reasoning" for implicit decisions

**Problem:** Fold SKILL.md, Mandatory Aspect 1: *"If a decision was made quickly or implicitly, reconstruct the reasoning."* This asks the folding agent to fabricate reasoning that may not accurately reflect what actually happened. The resuming agent treats this reconstructed reasoning as ground truth, potentially inheriting a false premise.

**Impact:** Cascading errors — a wrong inference about *why* something was decided leads the resuming agent to extend that (incorrect) reasoning to new decisions, compounding the error.

**Solution A (lightweight — mark inferred reasoning):**

Update the fold SKILL.md Mandatory Aspect 1 to add a qualifier for inferred reasoning:

> For decisions with **explicit** reasoning stated in the conversation, record it directly. For decisions where reasoning was **implicit or unstated**, prefix the reconstruction with `[inferred]` so the resuming agent knows to verify before relying on it.

Update the example format:

```
Decision: Use SQLite for task storage instead of JSON files
  Chosen because: [inferred] ACID guarantees, concurrent access from multiple agents
  Confidence: inferred — user did not state reasoning explicitly
```

**Solution B (structured — add confidence field to decisions table):**

Add a `confidence` column to the `decisions` table:

```sql
ALTER TABLE decisions ADD COLUMN confidence TEXT DEFAULT 'explicit';
-- Values: 'explicit' (stated in conversation), 'inferred' (reconstructed by folding agent)
```

Update `unfold.py` to render the confidence indicator when it is not `'explicit'`.

> **Implemented** — Phase 4 (2026-03-29)

### S3. `update_task` cannot clear nullable fields

**Root cause:** In `tasks.py:update_task()` (lines 62-70), the update logic skips any field where `value is None`:

```python
for field, value in [...]:
    if value is not None:
        updates.append(f"{field} = ?")
        values.append(value)
```

`None` means both "don't update this field" and "clear this field." They are indistinguishable. The CLI also defaults missing args to `None`, so there is no way to express "set to null" through any code path.

**Impact:** Once a field is set, it can never be cleared. An agent that wants to unassign itself from a task (`owner = NULL`) or clear a dependency (`blocked_by = NULL`) cannot do so.

**Solution:**

Use the empty string `""` as a sentinel meaning "clear this field." Apply only to **nullable** fields (`description`, `owner`, `blocked_by`, `context_notes`). Do not apply to NOT NULL fields (`subject`, `status`) — passing `""` for those would store NULL and violate the SQLite constraint.

Update `tasks.py:update_task()`:

```python
# fields where "" means "clear to NULL"
CLEARABLE_FIELDS = {"description", "owner", "blocked_by", "context_notes"}

for field, value in [
    ("subject", subject), ("description", description),
    ("status", status), ("owner", owner), ("blocked_by", blocked_by),
    ("context_notes", context_notes),
]:
    if value is not None:
        # empty string on clearable fields = explicit clear (set to NULL)
        if value == "" and field in CLEARABLE_FIELDS:
            updates.append(f"{field} = ?")
            values.append(None)
        elif value == "":
            continue  # ignore empty string on non-nullable fields
        else:
            updates.append(f"{field} = ?")
            values.append(value)
```

Update the CLI help text for the relevant flags to document this convention:

```
--owner OWNER          Set task owner (pass empty string "" to unassign)
--blocked-by ID        Set blocker task ID (pass empty string "" to clear)
--context-notes NOTES  Set context notes (pass empty string "" to clear)
```

**Note:** The `context_notes` field (added by the task-scoped context feature) must also use this sentinel convention. Implement S3 before or concurrently with the task-scoped context Slice 3.

> **Implemented** — Phase 1, Stream D (2026-03-29)
> `context_notes` added to `CLEARABLE_FIELDS` — Phase 3, Slice 3 (2026-03-29)


### S4. Hash collision possible with no existence check

**Root cause:** `fold.py:_generate_hash()` produces 6 hex characters (3 bytes = 16,777,216 possibilities). `fold_dossier()` does not check whether the generated slug already exists as a `.db` file. The birthday paradox applies: with ~4,000 dossiers, collision probability exceeds 50%.

If a collision occurs, `create_dossier_db()` uses `CREATE TABLE IF NOT EXISTS`, so it silently opens the existing database and the subsequent `INSERT INTO metadata` fails with a `UNIQUE constraint` violation (since `id = 1` already exists) — or worse, if the constraint is not strict enough, corrupts the existing dossier.

**Impact:** Low probability per fold, but catastrophic when it hits — an existing dossier is corrupted or the fold fails with an opaque SQLite error.

**Solution:**

Add a collision-check loop in `fold.py:fold_dossier()`. Replace lines 70-72:

```python
# current:
dossier_hash = _generate_hash()
slug = f"{_slugify(name)}-{dossier_hash}"
db_path = dossiers_dir / f"{slug}.db"
```

with:

```python
# collision-safe:
while True:
    dossier_hash = _generate_hash()
    slug = f"{_slugify(name)}-{dossier_hash}"
    db_path = dossiers_dir / f"{slug}.db"
    if not db_path.exists():
        break
```

Apply the same fix in `fork.py:fork_dossier()` (lines 28-31):

```python
while True:
    new_hash = _generate_hash()
    new_slug = f"{_slugify(fork_name)}-{new_hash}"
    dest_path = dossiers_dir / f"{new_slug}.db"
    if not dest_path.exists():
        break
```

> **Implemented** — Phase 1, Stream B (2026-03-29)

### S5. `find_dossier` hash matching is case-sensitive but hashes are always lowercase

**Root cause:** In `unfold.py:find_dossier()`, line 24 does `slug.endswith(query)` (case-sensitive), while line 26 does `query_lower in slug.lower()` (case-insensitive). Hash generation via `os.urandom(3).hex()` always produces lowercase hex. If a user types an uppercase hash (e.g., `A7F3C2`), the exact-suffix match fails and falls through to substring matching, which may match multiple slugs and raise an ambiguous error.

**Impact:** Low severity but confusing. Agents copying a hash from context where it was uppercased get unexpected results.

**Solution:**

Lowercase the query for hash suffix matching. In `unfold.py:24`, replace:

```python
if slug.endswith(query):
```

with:

```python
if slug.endswith(query_lower):
```

This is a one-line fix. The `query_lower` variable already exists on line 20.

> **Implemented** — Phase 1, Stream A (2026-03-29)


### S6. Fold-then-unfold information asymmetry for decisions

**Note:** This is the same underlying issue as H2. Listed separately for completeness and to capture the broader framing.

The fold side stores four fields per decision (`what`, `why`, `alternatives`, `decided_by`). The unfold side renders only three — `alternatives` is silently dropped. See H2 for the detailed fix.


### S7. Decision duplication on re-fold has no code-level guard

**Root cause:** In `fold.py:105-119`, the decision insertion loop runs unconditionally for both new folds and re-folds. Unlike the task insertion loop (which is guarded by `if not is_refold:` at line 92), decisions are always inserted — whatever the caller passes gets added as new rows.

```python
# fold.py:105-119 — current code (no is_refold guard)
for decision in (decisions or []):
    alternatives = decision.get("alternatives")
    if alternatives is not None and not isinstance(alternatives, str):
        alternatives = json.dumps(alternatives)
    conn.execute(
        "INSERT INTO decisions (session_id, what, why, alternatives, decided_by) VALUES (?, ?, ?, ?, ?)",
        (session_id, decision["what"], decision["why"], alternatives, decision.get("decided_by")),
    )
```

The fold SKILL.md (line 247) instructs agents to include only current-session decisions when re-folding, and the explicit prohibitions section (line 309) reinforces this: *"Do NOT include inherited decisions from prior sessions in the decisions array when re-folding."* But this is guidance only — there is no code enforcement.

**Impact:** If a confused or misbehaving agent includes inherited decisions from prior sessions in a re-fold, every inherited decision is inserted as a duplicate row. After N re-folds, the same decision appears N+1 times in the database and N+1 times in the unfold output.

**Solution:**

Deduplicate decisions against existing rows before inserting. This allows new decisions from continuation sessions while preventing duplicates from misbehaving agents that accidentally include inherited decisions:

```python
for decision in (decisions or []):
    # skip if an identical decision already exists
    existing = conn.execute(
        "SELECT id FROM decisions WHERE what = ? AND why = ?",
        (decision["what"], decision["why"]),
    ).fetchone()
    if existing:
        continue
    # ... existing insertion logic
```

The `what + why` deduplication key is sufficient in practice — two genuinely different decisions with identical `what` and `why` text would be indistinguishable to a human reader too.

**Why not skip decisions on re-fold entirely** (matching the `if not is_refold:` guard on tasks)? That breaks a legitimate use case: a continuation session may produce *new* architectural decisions. The SKILL.md tells agents not to include *inherited* decisions, but a well-behaved agent that passes only new decisions would have its input silently dropped. Deduplication enforces the no-duplicates invariant without blocking new decisions.

*Origin: merged from DOSSIER-FIXES.md Part 3, Item 3b.*

> **Implemented** — Phase 1, Stream B (2026-03-29)


## Minor polish

### M1. `cmd_fold` reports task/decision counts from input, not from the database

**Location:** `cli.py:79-81`

```python
task_count = len(tasks) if tasks else 0
decision_count = len(decisions) if decisions else 0
```

On a re-fold, the SKILL.md instructs agents to omit the `tasks` array (or pass `[]`), so the output says `"0 tasks"` even though the dossier may have 15 tasks in its database. This is misleading.

**Solution:**

Have `fold_dossier()` return the actual counts in its result dict (it already has the DB connection open — no need to reopen). Add to the return block in `fold.py`, before `conn.close()`:

```python
task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status != 'deleted'").fetchone()[0]
decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

conn.commit()
conn.close()

return {"slug": slug, "hash": dossier_hash, "task_count": task_count, "decision_count": decision_count}
```

Then in `cmd_fold()`, use the returned counts:

```python
print(f"Dossier saved: `{result['slug']}` ({result['task_count']} tasks, {result['decision_count']} decisions)")
```

> **Implemented** — Phase 1, Stream B (2026-03-29)

### M2. `cmd_list` does not render lock status

**Location:** `cli.py:127-130`

The table header renders `Hash`, `Name`, `Branch`, `Tasks`, `Updated` but omits lock status. The unfold SKILL.md (Explicit Behavior 2) says: *"always show lock status in listings."* The `list_dossiers()` function already returns `locked_by`, but `cmd_list()` does not display it.

**Solution:**

Add a `Lock` column to the table format:

```python
print(f"{'Hash':<8} {'Name':<30} {'Branch':<20} {'Tasks':>5} {'Lock':<15} {'Updated'}")
print("-" * 95)
for r in results:
    lock = r['locked_by'] or 'unlocked'
    print(f"{r['hash']:<8} {r['name']:<30} {(r['branch'] or '—'):<20} "
          f"{r['tasks']:>5} {lock:<15} {r['updated_at']}")
```

> **Implemented** — Phase 2 (2026-03-29)


### M3. `show` command is functionally identical to `unfold`

**Location:** `cli.py:228-241` vs. `cli.py:85-114`

`cmd_show()` is identical to `cmd_unfold()` minus the `--claim` and `--fork` flags. The design doc says `show` is *"intended for human inspection, not context injection"* but the implementation produces identical output.

**Decision: remove `show`.** The human reading a dossier is almost always doing so through an agent — they ask the agent to unfold, and the agent presents it. Humans rarely run `bureau-dossiers show` directly. For the rare case, `bureau-dossiers unfold <query> --full` already does exactly that. One less command, one less thing for agents to be confused about.

Remove `cmd_show()` (`cli.py:228-241`), the `show` subparser (`cli.py:334-340`), and the `"show": cmd_show` entry in the commands dict (`cli.py:351`).

*Alternatives considered and rejected: (a) making `show` an alias for `unfold --full` (DOSSIER-FIXES.md Part 1c) — still two names for the same thing; (b) differentiating `show` with ANSI colors and human formatting — a separate rendering path for a command used <1% of the time.*

> **Implemented** — Phase 2 (2026-03-29)


### M4. `--description` in `tasks add` is write-only data

**Location:** `cli.py:294` (accepts `--description`), `tasks.py:35` (stores it), but `cli.py:144-147` (`tasks list` rendering) and `unfold.py:116-122` (unfold task table) both omit it.

**Decision: render it (Option A).** The task-scoped context design renders descriptions in its worker-mode output (`<description, rendered as paragraph if present>`), so the field must be kept. Removing it (Option B) would conflict with the task-scoped context feature.

Add a `--verbose` flag to `tasks list` that shows descriptions as a second line under each task. The unfold task table and `context` command output already plan to render descriptions when present.

> **Implemented** — Phase 2 (2026-03-29)


### M5. Timestamp format inconsistency between fold and tasks

**Location:** `fold.py:28` uses `_now_iso()` → `%Y-%m-%dT%H:%M:%SZ` (explicit UTC `Z` suffix). `tasks.py:73` and `db.py:42-43` use `datetime('now')` → `YYYY-MM-DD HH:MM:SS` (no timezone indicator). The same database has two different timestamp formats depending on which code path wrote the value.

**Solution:**

Keep the `DEFAULT (datetime('now'))` clauses in `db.py` for backward compatibility (they protect against hypothetical direct SQL inserts and keep existing dossiers working identically). Override them from Python by always passing explicit timestamps.

1. In `tasks.py:add_task()`, pass `_now_iso()` explicitly:

   ```python
   from .fold import _now_iso
   now = _now_iso()
   cursor = conn.execute(
       "INSERT INTO tasks (subject, description, status, owner, blocked_by, created_at, updated_at) "
       "VALUES (?, ?, ?, ?, ?, ?, ?)",
       (subject, description, status, owner, blocked_by, now, now),
   )
   ```

2. In `tasks.py:update_task()`, replace `"updated_at = datetime('now')"` with a parameterized value:

   ```python
   updates.append("updated_at = ?")
   values.insert(-1, _now_iso())  # insert before the WHERE task_id param
   ```

   Similarly for `claim_task()` and `complete_task()`.

**Note:** No schema change needed. The `DEFAULT` clauses become dead code for Python callers but remain as a safety net. Existing dossiers retain their mixed-format timestamps; new writes will use consistent ISO 8601 with `Z` suffix.

> **Implemented** — Phase 1, Stream D (2026-03-29)


### M6. Unfold SKILL expects relative timestamps but CLI outputs raw ISO

**Location:** The unfold SKILL.md (Explicit Behavior 1) says: *"when listing dossiers, always compute relative time from the updated field (e.g., '2h ago', '3d ago')."* But `cmd_list()` prints raw ISO timestamps, leaving the relative-time computation to agents (who may not know the current time precisely).

**Solution:**

Add a `_relative_time()` utility and use it in `cmd_list()`:

```python
from datetime import datetime, timezone

def _relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to human-relative string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        if seconds < 604800:
            return f"{seconds // 86400}d ago"
        return f"{seconds // 604800}w ago"
    except (ValueError, TypeError):
        return iso_str
```

Use it in the table rendering and include it in the JSON output as a computed field.

> **Implemented** — Phase 2 (2026-03-29)


### M7. No CLI-level test coverage for fork and claim paths

**Location:** `operations/dossiers/tests/test_cli.py` has integration tests for fold, unfold, and list, but no tests for `--fork` or `--claim` through `cmd_unfold()`.

Note: `operations/dossiers/tests/test_fork.py` already exists with 5 unit tests covering the `fork_dossier()` function (new hash, new slug, parent reference, unlocked state, task copying). The gap is at the CLI integration level.

**Solution:**

Add the following cases to `test_cli.py`:

- `test_unfold_with_fork` — `cmd_unfold` with `--fork` creates a copy and outputs the fork's content
- `test_unfold_with_claim` — `cmd_unfold` with `--claim --agent X` acquires lock and unfolds
- `test_unfold_claim_without_agent_fails` — `cmd_unfold` with `--claim` but no `--agent` returns error (once C3 is fixed)
- `test_unfold_claim_conflict` — `cmd_unfold` with `--claim` on an already-locked dossier returns structured error (once H3 is fixed)


### M8. Active skills have no structured storage

**Location:** Fold SKILL.md Step 4 says to record active skills and their state. But there is no `skills` field in the JSON schema, no column in the database, and no table for skill state. The data goes into the monolithic digest narrative, where it is unstructured and unsearchable.

**Solution:**

A dedicated `session_skills` table is over-engineered for data that is small (0-3 skills per session), primarily informational, and adequately captured in the session digest or `context_notes`.

**Simpler approach:** Add a `skills_json` TEXT column to the `sessions` table, storing the skills array as a single JSON blob:

```sql
ALTER TABLE sessions ADD COLUMN skills_json TEXT;
```

The fold SKILL.md Step 7 JSON schema gains a `skills` field:

```json
"skills": [
    {"name": "assess-mode", "active": false, "state": null},
    {"name": "micro-mode", "active": true, "state": "{\"current_step\": 3, \"total_steps\": 7}"}
]
```

The unfold renderer deserializes and displays the list. No new table, no new index, no join queries. The data is inherently session-scoped, so co-locating it with the session row is the natural fit. Apply via the same lazy migration pattern as `context_notes`.

**Alternative: defer entirely.** Skills metadata in the digest narrative works today. The task-scoped context primitive does not need structured skill data. Until there is a concrete workflow that requires querying skill state across sessions, this adds complexity without demonstrated value.


## Priority matrix

| Priority | ID | Issue | Effort | Impact |
|----------|----|-------|--------|--------|
| **Critical** | C1 | File interactions never rendered on unfold | Low | High |
| **Critical** | C2 | `release_lock` no agent verification | Low | High |
| **Critical** | C3 | `--claim` without `--agent` = silent no-op | Low | High |
| **High** | H1 | Compact unfold lacks pending state | Medium | High |
| **High** | H2 | Rejected alternatives dropped from unfold | Low | Medium |
| **High** | H3 | Undifferentiated error types in unfold CLI | Low | Medium |
| **Subtle** | S1 | Compact/full context cliff (defer; H1 + task-scoped context cover 95%) | High | High |
| **Subtle** | S2 | Fabricated reasoning for implicit decisions | Low | Medium |
| **Subtle** | S3 | Cannot clear nullable fields in `update_task` | Low | Medium |
| **Subtle** | S4 | Hash collision with no existence check | Low | Low prob / High impact |
| **Subtle** | S5 | Case-sensitive hash matching | Low | Low |
| **Subtle** | S7 | Decision duplication on re-fold (no code guard) | Low | Medium |
| **Minor** | M1 | Fold reports input counts, not DB counts | Low | Low |
| **Minor** | M2 | `cmd_list` missing lock status column | Low | Low |
| **Minor** | M3 | Remove `show` command (decided) | Low | Low |
| **Minor** | M4 | `--description` is write-only (decided: render it) | Low | Low |
| **Minor** | M5 | Timestamp format inconsistency | Low | Low |
| **Minor** | M6 | CLI outputs raw ISO, not relative time | Low | Low |
| **Minor** | M7 | No fork/claim test coverage | Medium | Medium |
| **Minor** | M8 | Active skills lack structured storage | Medium | Low |


## Implementation order

> **Validation strategy:** All testing and validation (M7, test suite runs, manual smoke tests) is deferred to the final phase. This eliminates ordering constraints imposed by test dependencies (e.g., M7 needing C3 and H3) and lets implementation proceed without interruption.

### Phase 1: Core fixes (four parallel streams by file)

These four streams touch disjoint primary files and can be worked on simultaneously by separate agents. Within each stream, items are ordered sequentially.

| Stream | Items | Primary file(s) | Notes |
|--------|-------|-----------------|-------|
| **A** | C1 → H2 → S5 → H1 | `unfold.py` | C1 before H1 (render ordering dependency). H2 and S5 are independent, slotted between for efficiency |
| **B** | S4 + S7(B) + M1 | `fold.py`, `fork.py` | All independent within the file. S7 uses Solution B (deduplicate, not skip) |
| **C** | C3 → C2 | `lock.py`, `cli.py:cmd_unfold` top + `cli.py:cmd_lock` | C3's validation ensures agents always pass `--agent`; C2's verification builds on that |
| **D** | S3 + M5 | `tasks.py` | S3 (sentinel clearing) is a prerequisite for Slice 3. M5 (timestamp consistency) prepares `_now_iso` for shared use |

**Stream C note:** C3 adds 3 lines at the top of `cmd_unfold()`'s `try` block and a guard in `claim_lock()`. C2 modifies `release_lock()` and the `cmd_lock` release handler. These are well-separated from later `cli.py` edits in Phase 2.

### Phase 2: CLI polish and error types (sequential in `cli.py`)

After Phase 1 stabilizes the foundation, these changes edit `cli.py` sequentially to avoid edit conflicts. Ordered so deletions happen before additions.

1. **H3** — create `errors.py` with typed exceptions; update `cmd_unfold` except blocks
2. **M3** — remove `cmd_show`, its subparser, and its `commands` dict entry (H3 applied only to `cmd_unfold`, not the now-deleted `cmd_show`)
3. **M2 + M6** — `cmd_list`: add Lock column + replace raw ISO with relative timestamps (single edit session, same function)
4. **M4** — `tasks list`: add `--verbose` flag for description rendering

### Phase 3: New primitive — task-scoped context

Sequential; each slice depends on the previous. Slice 3 also depends on S3 from Phase 1 Stream D.

1. **Slice 1 — Walking skeleton:** `context.py` + `context` CLI subcommand + `test_context.py`. Delivers Scenario 1 (main agent extracts context for subagent) end-to-end
2. **Slice 2 — Worker mode:** `--worker --task` flags on `unfold` + `unfold_worker()` + worker framing. Delivers Scenario 2 (separate interactive worker)
3. **Slice 3 — Task enrichment:** `_ensure_schema_current()` lazy migration for `context_notes` + `tasks.py` changes + fold SKILL.md guidance. Requires S3 sentinel convention from Phase 1

### Phase 4: Documentation and conventions

No code dependencies; can be done in parallel.

- **S2** — `[inferred]` prefix convention for reconstructed reasoning (fold SKILL.md)
- **Slice 4** — unfold SKILL.md worker mode section + `CLAUDE.template.md` / `AGENTS.template.md` task list scope updates

### Phase 5: Validation

All testing runs here, after all implementation is complete.

1. **M7** — CLI-level test coverage: `test_unfold_with_fork`, `test_unfold_with_claim`, `test_unfold_claim_without_agent_fails`, `test_unfold_claim_conflict`, plus new tests for `context` and `--worker` paths
2. **Full test suite** — `pytest operations/dossiers/tests/ -q`
3. **Manual smoke test** — fold → unfold (compact + full) → tasks claim → context extraction → worker mode unfold → re-fold with new decisions (verifies S7(B) dedup)

### Deferred indefinitely

| ID | Issue | Reason |
|----|-------|--------|
| S1 | Compact/full context cliff | H1 + task-scoped context cover ~95% of the need |
| M8 | Active skills structured storage | No demonstrated workflow requires querying skill state across sessions |

> **All phases implemented and validated** (2026-03-29). Test suite: all passing.
