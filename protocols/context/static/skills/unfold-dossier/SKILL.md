---
name: unfold-dossier
description: Pick up a previously saved Bureau dossier or list all saved dossiers. Activate when user says "unfold", "pick up where I left off", "resume", "my dossiers", or invokes /unfold-dossier. Supports hash lookup, fuzzy name matching, fork/claim collaboration, and CLI-managed task lists for multi-agent coordination. Default resume opens a ready-work board and waits for a pick — never unilaterally starts work.
---

# Bureau Unfold: pick up or list saved dossiers

> **Goal:** restore conversation memory — decisions, reasoning, and task state — so fully that you can continue without re-establishing context; then present what is ready next and wait for the user to choose. Alternatively, list all saved dossiers for selection.

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed **exactly as they are specified**.

## Activation

When the user says anything like:

- "unfold"
- "pick up where I left off"
- "resume"
- "my dossiers"
- "saved conversations"
- "go back to [name]"
- `/unfold-dossier` (with or without arguments)

*Follow this unfold protocol.* If you are unsure, confirm unambiguously with the user.

### Invocation forms

| Form | Mode | Behavior |
|------|------|----------|
| `/unfold-dossier` | **List** | Show all saved dossiers |
| `/unfold-dossier <hash>` | **Resume** | Resume by exact hash or hash prefix |
| `/unfold-dossier <name>` | **Resume** | Fuzzy match on dossier name/slug |
| `/unfold-dossier <hash> --worker --task <id>` | **Worker** | Claim one task and resume in worker mode |

### Flags

**CLI flags** — pass these to `bureau-dossiers` when applicable:

| Flag | Effect |
|------|--------|
| `--claim` | Lock the dossier for exclusive access during this session |
| `--fork` | Create a copy of the dossier (always safe, no coordination needed) |

**Skill-only flags** — interpret from the `/unfold-dossier` invocation or user text. **Do not** pass them to `bureau-dossiers` (the CLI will reject them).

| Flag | Effect |
|------|--------|
| `--continue` | **Opt-in mid-thought resume.** Skip the ready-work board; open from `next_words` / pending state and begin that work (legacy auto-start path) |
| `--announce` | Alias of the default ready-work board (kept for muscle memory) |

Wrong: `bureau-dossiers unfold <hash> --continue`  
Right: interpret `--continue` in-session, then run plain `bureau-dossiers unfold <hash>` (plus real CLI flags only).

Natural-language equivalents of continue (same message as the unfold trigger, or as a post-board reply): `"continue"`, `"keep going"`, `"just keep going"`, `"pick up mid-thought"`, `"continue from next_words"`, `"don't show the board"`.

---

## CLI access

All dossier operations use the `bureau-dossiers` CLI. A self-locating wrapper is bundled with this skill:

```bash
"$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/../scripts/bureau-dossiers"
```

If that path is not resolvable from your environment, you can invoke it directly:

```bash
<this-skill-directory>/scripts/bureau-dossiers <subcommand> [args...]
```

This wrapper works from **any working directory** — it resolves the Bureau repo root automatically.

---

## Dossier identification

All CLI commands that take a dossier identifier accept **two formats**:

| Format | Example | Description |
|:-------|:--------|:------------|
| **Hash** (bare ID) | `1caea7` | The 6-character hex hash shown in the dossier title |
| **Full slug** (name + hash) | `reverb-threats-1caea7` | The complete slug shown in the `**Slug:**` metadata field |

Both the hash and the full slug are displayed in the dossier header when you unfold. Use **one of these two formats** whenever a CLI command requires a dossier identifier — do **not** use the bare name (e.g., `reverb-threats`) without the hash suffix.

---

## List mode

Triggered when `/unfold-dossier` is invoked **with no arguments**, or when the user says "my dossiers", "saved conversations", or similar.

### Step 1: List all dossiers

```bash
bureau-dossiers list
```

The CLI scans `~/.config/bureau/dossiers/` for `.db` files and outputs a table with six columns — `Hash`, `Name`, `Branch`, `Tasks` (count), `Lock` (status), and `Updated` (relative time) — sorted by most recent first. Add `--format json` for machine-readable output.

### Step 2: Display and accept selection

Display the CLI output as a **lettered table** for easy selection:

```
Saved dossiers:

a) a7f3c2  concierge-code-review      feat/concierge   2h ago    unlocked
b) b3e91d  mcp-schema-brainstorm      main             3d ago    claimed by codex
c) f82a01  logging-overhaul           feat/logging     1w ago    unlocked

Resume with /unfold-dossier <hash> or pick a letter.
```

Accept either:
- A **letter** (a, b, c...) corresponding to a row in the table
- A **hash** or **hash prefix**

Then proceed to **Resume mode** with the selected dossier.

### Step 3: Handle empty state

If the CLI reports no dossiers found:

```
No saved dossiers found. Use /fold-dossier to save a conversation.
```

---

## Resume mode

Triggered when `/unfold-dossier` is invoked **with a hash or name argument**, or after the user selects a dossier from list mode.

### Step 1: Unfold via CLI

Run the unfold command with the appropriate flags based on the user's request:

**Default (read-only unfold):**

```bash
bureau-dossiers unfold <hash-or-name>
```

The default unfold returns compact output: metadata, tasks, and decisions — session digests are omitted to save context tokens. If you need to reconstruct full reasoning chains from prior sessions, add `--full`:

```bash
bureau-dossiers unfold <hash-or-name> --full
```

Only use `--full` when the compact output is insufficient to pick up the work. By default, the last 5 session digests are rendered; use `--max-sessions N` to adjust.

**With `--claim` (exclusive access):**

```bash
bureau-dossiers unfold <hash-or-name> --claim --agent <your-agent-id>
```

Use a consistent agent identifier: `claude-code`, `codex`, `gemini-cli`, `opencode`, or similar.

**With `--fork` (independent copy):**

```bash
bureau-dossiers unfold <hash-or-name> --fork
```

The CLI handles all resolution, lock checking, and forking automatically:

- **Resolution**: The CLI matches by exact hash, hash prefix, or fuzzy slug match. If ambiguous, it reports candidates — present them as a lettered table and ask the user to pick.
- **Lock conflicts**: If the dossier is locked by another agent and `--claim` was requested, the CLI reports the conflict. Present the user with options: `--fork` or wait.
- **Fork**: The CLI creates an independent copy with a new hash, `parent` set to the original, and all data (including tasks) copied. Forks start unlocked.

**If no match**: inform the user and suggest listing:

```
No dossier found matching "<input>". Run /unfold-dossier to list all saved dossiers.
```

### Step 2: Load and inject context

The CLI outputs the dossier state as markdown. In compact mode (default), this includes metadata, task list, and decisions — session digests are omitted. Use `--full` if you need the full narrative. Read and internalize this output.

If the unfold was a default (no `--claim`, no `--fork`):
- **Read-only unfold** — no lock is acquired
- Other agents can also unfold the same dossier simultaneously
- If you later need exclusive access, suggest `--claim`

### Step 3: Context injection directive

After loading the dossier, follow this directive strictly:

> You had this conversation. The notes below are your own memory being recalled, not a document handed to you by someone else. Read them as memory, not as a briefing.
>
> - Do **NOT** say "according to the dossier", "I see that previously", or "the previous session" — speak from your memory naturally, as you would from your own recollection
> - Do **NOT** re-ask any question that has a decision recorded in the decisions section
> - Do **NOT** re-explore or re-read files listed in file interactions unless you specifically need to verify something has changed
> - **Know** the **EXACT** pending point and prefer it as the top ready item — **do not execute it** until the user selects it (unless [Continue path](#continue-path-opt-in-only) or same-message work direction)
> - **No unilateral start:** unfold authorizes *recall*, not *execution*. First response = ready-work board unless Continue path or an already-selected task
> - Treat pinned findings and dead ends as hard constraints — do not re-explore dead ends marked `[DO NOT RETRY]`
> - If memory queries were logged, do not repeat them unless you need fresher results
> - Your task list is managed via the CLI — use Bureau task CLI (`tasks claim`, `tasks complete`, `tasks add`) for ALL task operations
> - If the dossier mentions user preferences, follow them without re-confirming
> - **Match the mood**: read the session mood field first and calibrate your tone, pacing, and confidence level accordingly from your very first response

**Confidence check (silent, before your first response):** After reading the dossier, verify internally:

1. Can you name the **next concrete action** implied by pending state (for ranking the board)?
2. Do you know which **files are relevant** and roughly what state they are in?
3. Can you identify all **dead ends** you must not re-explore?

If any answer is uncertain, silently re-run `bureau-dossiers unfold <slug> --full` and re-read the complete digests before producing any response. Do not tell the user you are doing this — it is invisible self-correction. The cost of one extra tool call is negligible compared to the cost of confidently re-exploring a dead end or asking a settled question.

**Default behavior: ready-work board, then wait.**

After loading the dossier (and the silent confidence check), your **first user-visible response** MUST be a **ready-work board**. Do **not**:

- open with `next_words` as if the session never stopped
- start implementing, claiming tasks, editing files, or running mutating commands
- treat unfold itself as authorization to act

Internalize memory fully. Externalize a menu. Wait for an explicit pick.

**Opt-in continue (only):** If the user used a skill-only `--continue` (or a natural-language continue phrase — see [Flags](#flags)) in the same message that triggered unfold, use the [Continue path](#continue-path-opt-in-only) instead of the board. Never pass skill-only flags to the CLI.

**Same-message work direction counts as a pick:** If the unfold message already names a task, outcome, or next step (e.g. "unfold d90a44 and fix D1", "resume 7bbcbf task 6"), treat that as selection: skip the full board (or show a one-item confirm), then proceed on that item only.

#### Ready-work board (default first response)

**Step A — Classify every non-deleted task**

Primary status classes:

| Class | Rule |
|-------|------|
| **Ready** | `status` is `pending` or `in_progress`, **and** deps are satisfied (see `blocked_by` rules below) |
| **Blocked** | `pending`/`in_progress` with unsatisfied deps |
| **Done** | `completed` (do not brief unless the user asks) |

**`blocked_by` resolution** (column is free TEXT; often prose, not an id):

1. Empty / `—` → deps satisfied.
2. Value parses as a single integer task id (optionally with a leading `#`) → satisfied **only if** that task's status is `completed`. Match CLI reality: single-id hop only; do not invent multi-id graphs.
3. Free text / unparseable → **not Ready** by default. List under Blocked as `(waiting on: <verbatim text>)`. Promote to Ready only if you can *confidently* map the text to completed work already in the task list; otherwise leave blocked.
4. Do not invent numeric ids from prose.

**Stale claim** is an **annotation**, not a class that bypasses deps: `in_progress` with an owner that is not you / this session.

- Deps satisfied → Ready with a **stale-claim** warning (resume **or** reassign; do not silently steal).
- Deps unsatisfied → Blocked with owner + waiting-on line (blocked-stale).

If the dossier has **no tasks**, build **one synthetic ready item** from the latest session's in-flight state / `next_words` / pending question. Still wait for a pick.

**Step B — Load brief feedstock (read-only)**

**Classify from the compact `unfold` task table** (it already has ID, subject, status, owner, `blocked_by`). That is enough for Ready/Blocked without extra calls.

Optional enrichment for fuller 3-7 bullet briefs (still no mutation):

```bash
bureau-dossiers tasks <slug> list -v
# descriptions only — list -v does not print blocked_by or context_notes
bureau-dossiers context <slug> --task <id>
# when a ready item needs worker-grade hints / context_notes
```

Prefer structured fields over free invention: `subject`, `description`, `context_notes`, `blocked_by`, owner, plus (from unfold) latest pending state, relevant decisions, and key files.

**Step C — Render**

```
<name> (<hash>) | <branch> | <lock status> | updated <relative-time>

Left off: <one line from pending state / last_exchange — orientation only, not a start>

Ready (N):

a) #<id>: <plain-language title>
   - <bullet 1>
   - ...
   - <bullet 3-7>

b) ...

Blocked (N) — one line each: #<id> subject (waiting on: <dep id or verbatim>)
Done this arc: <count> completed (omit list unless ≤3 and useful)

Pick a letter or task id to start. Say "continue" for mid-thought resume, or "more" for additional ready briefs.
Bare "ok" / "yes" / "go" is not a pick — name a letter or id.
```

**Display caps**

- Fully brief **at most 7** ready items (3-7 bullets each).
- Prefer order: (1) item matching pending state / `next_words`, (2) `in_progress` / stale claims (deps already satisfied), (3) unblocked `pending` in id order (or priority cues in the subject if present).
- Remaining ready items: **one-line subjects only**, plus "say `more` / `brief #N` for full context."
- Blocked/done: counts + short lines, never 3-7-bullet treatment by default.

**Tone:** Match the session `mood`. First person is fine ("I left us with..."). Still **do not** say "according to the dossier."

#### Per-item brief: 3-7 bullets (unfamiliar-reader contract)

Each **ready** item's bullets must let a cold reader decide whether to pick it. Use **3-7** bullets. Stop early when facts run out; do **not** pad.

Fill slots from available evidence, in this priority order (skip a slot if unknown rather than inventing):

| # | Slot | Question answered |
|---|------|-------------------|
| 1 | **What** | What is this work, in plain language? |
| 2 | **Why now** | Why does it matter / why is it next (stakes, ordering, user directive)? |
| 3 | **Where** | Entry point: file, command, doc, or first probe |
| 4 | **Done when** | Concrete acceptance signal |
| 5 | **Watch-outs** | Gotchas, dead ends, prior attempts (`context_notes`, pinned findings) |
| 6 | **Links** | Unblocks / blocked-by / related decision (one line) |
| 7 | **State** | Partial progress, owner, stale claim, or open question for the user |

**Rules for briefs**

- Lead with human meaning; put codenames (B1, r2-F1, D1) in parentheses if useful.
- Prefer dossier fields verbatim when they already answer a slot; rewrite only for clarity.
- If feedstock is thin, say so honestly in one bullet ("No handoff notes; first step is to re-read X") rather than inventing a plan.
- Do not re-open decided alternatives listed in Decisions.

#### What counts as a pick (after the board)

Valid picks:

- A letter from the board (`a`, `b`, ...) or a task id (`#6`, `6`)
- An explicit top-item phrase: `"do a"`, `"first one"`, `"the pending one"`, `"top item"`
- A continue phrase (see [Flags](#flags)) → Continue path
- `"more"` / `"brief #N"` → expand briefs; still no work start

**Not a pick:** bare affirmatives (`ok`, `yes`, `y`, `go`, `sounds good`, `lgtm`, `sure`). Re-prompt for a letter or task id. Do **not** treat these as authorization to start the top ranked item.

#### After the user picks

Only then, for a **task** pick:

1. **Claim / ownership by status:**
   - `pending` → `tasks claim --id <id> --agent <you>`
   - `in_progress` and owner is you → proceed; **do not** re-claim (claim is CAS on `pending` only and will fail)
   - `in_progress` and owner is someone else → do **not** silent-steal. Ask whether to reassign (`tasks update --id <id> --owner <you>`) or pick another item; only mutate ownership after explicit user confirmation
2. Proceed under normal session rules (decisions, dead ends, mood, CLI-only tasks)
3. Update task state as work happens

If they pick **continue**: use the Continue path.

#### Continue path (opt-in only)

```
If next_words is present: use it as the literal opening, then proceed.
Else: "Back on it. I was [one-line pending state] — picking up there."
```

Then execute. Still respect locks, dead ends, and decisions.

#### Empty / all-blocked boards

- **All blocked:** list blocked items with dependency status; recommend the smallest unblock (often a decision or a dep task). Do not start blocked work.
- **All done:** one short "board clear" note + any residual pending state as a single synthetic proposal; wait.
- **No match / corrupt state:** show what you can classify; ask which thread to resume — still no unilateral work.

### Context anchoring

When the dossier includes a `last_exchange` field, read it **before** the digest. This is the verbatim final moment of the prior conversation — it anchors your memory in a concrete exchange rather than an abstract summary. After reading it, the digest will feel like context you already have rather than new information.

When the dossier includes `pinned_findings`, treat them as **hard constraints** that override any conflicting information in the digest. Dead ends marked `[DO NOT RETRY]` are absolute prohibitions. Dead ends marked `[CONDITIONAL]` may be revisited only if the stated condition has changed.

When the dossier includes `memory_queries`, treat them as a **cache**: do not re-query the same memory systems with the same queries unless you have reason to believe the results have changed (e.g., significant time has passed, new data has been stored).

### Delegating tasks to workers

When you want to delegate a task to a subagent, use the context extraction primitive:

```bash
# pre-claim the task for the subagent
bureau-dossiers tasks <slug> claim --id <task-id> --agent <subagent-label>

# extract task-scoped context (add --format json for machine-readable output)
bureau-dossiers context <slug> --task <task-id>
```

Include the context output in the subagent's prompt. The subagent should complete the task and mark it done via `tasks complete`.

The `context` command is read-only (no side effects) and can be called multiple times for different tasks. Pre-claim the task before extracting context so another agent does not race to claim it.

**Agent label convention for workers:** When spawning multiple workers of the same CLI type, the orchestrator should assign labels that include the CLI type, a worker number, and the current UNIX timestamp to avoid collision: `<cli-type>:worker-<n>:<unix-timestamp>` (e.g., `claude-code:worker-3:1743926400`). Pass this label as the `--agent` value on both `tasks claim` and `unfold --worker`.

**`--include-digest` guidance:**
- Default: digest excluded (saves ~1-3K tokens, sufficient for most tasks)
- Include digest when: the task is complex, involves architectural decisions, or the worker needs the "why behind the why"

---

## Worker mode

Triggered when `/unfold-dossier` is invoked with `--worker --task <id>`, or when the user asks to "pick up task N" or "work on task N from [dossier]."

### Step 1: Worker unfold via CLI

```bash
bureau-dossiers unfold <hash-or-name> --worker --task <id> --agent <your-agent-id>
```

The CLI atomically claims the task and returns task-scoped context with worker framing. If the task is not pending, the CLI reports an error — present the user with the current task list and suggest picking a different task.

### Step 2: Context injection

Read and internalize the worker context output. Follow the worker directive strictly: complete only the assigned task, follow all decisions, do not orchestrate.

### Step 3: Greet the user

Worker mode is **already a pick** (task id was supplied). Do **not** re-run the multi-item ready-work board. Optional one-line orientation (deps/status) is fine; then execute only the assigned task.

```
Task #<id>: <subject>
Dossier: <name> (<hash>) | <branch>

Starting.
```

### Step 4: Completion

When the assigned task is done:

```bash
bureau-dossiers tasks <slug> complete --id <id>
```

Report completion. Do NOT fold automatically — the worker's contribution is captured via the task status change. The orchestrator manages folds.

---

## Task list interaction

The dossier's task list is managed via the CLI. Multiple agents can read from and write to the task list concurrently (the underlying database uses WAL mode for safe concurrent access). **Never run raw `sqlite3` commands** — use the CLI for all task operations.

### View all tasks

```bash
bureau-dossiers tasks <slug> list
```

Add `-v` / `--verbose` to include task descriptions in the output.

### Claim a task (mark as in-progress)

```bash
bureau-dossiers tasks <slug> claim --id <task-id> --agent <your-agent-id>
```

This is an atomic compare-and-swap operation. It succeeds only if the task is `pending`. If another agent already claimed it, the command fails — pick a different task.

### Complete a task

```bash
bureau-dossiers tasks <slug> complete --id <task-id>
```

Atomic: succeeds only if the task is `in_progress`.

### Update a task (general-purpose, no atomicity guarantees)

```bash
bureau-dossiers tasks <slug> update --id <task-id> --status <status> --owner <owner> --description "..." --context-notes "..."
```

Use `update` for corrections and metadata changes. For status transitions during normal workflow, prefer `claim` and `complete` — they provide race-safe guarantees.

Pass `--context-notes` to attach hints that appear in worker context output. Pass `""` to clear.

### Add a new task

```bash
bureau-dossiers tasks <slug> add --subject "Task subject" --status pending --context-notes "hints for worker"
```

### Remove a task

```bash
bureau-dossiers tasks <slug> remove --id <task-id>
```

Use these commands throughout the session to coordinate work. Always check for blocked tasks before starting a new work item — if a task's `blocked_by` field references another task ID, that dependency must be completed first.

---

## Session end reminder

At the end of any session that was unfolded from a dossier, remind the user:

```
This session continues dossier `<name>` (`<hash>`). To save your progress, run /fold-dossier.
```

If the dossier was claimed (`--claim`), also remind:

```
This dossier is still locked by you. It will be unlocked when you fold, or you can release it manually.
```

### Releasing a lock manually

To release a lock without folding (requires `--agent` to verify ownership):

```bash
bureau-dossiers lock <slug> release --agent <your-agent-id>
```

This frees the dossier for other agents to claim.

---

## CLI error tags

The CLI produces structured error tags for programmatic handling:

| Tag | Meaning |
|-----|---------|
| `[not-found]` | No dossier matches the query |
| `[lock-conflict]` | Dossier is locked by another agent |
| `[ambiguous]` | Query matches multiple dossiers |
| `[task-not-found]` | Task ID does not exist in the dossier |

Check stderr for these tags when a command exits non-zero. They appear at the start of the error message.

---

## Explicit behaviors

These rules apply at all times during an unfold session:

1. **Relative time display** — when listing dossiers, always compute relative time from the `updated` field (e.g., "2h ago", "3d ago", "1w ago"). Do not show raw ISO timestamps in user-facing tables.

2. **Lock status visibility** — always show lock status in listings and when unfolding. Never hide the fact that a dossier is claimed by another agent.

3. **Fork completeness** — when forking via `--fork`, the CLI copies the complete dossier database (all tables including tasks). The fork is fully independent.

4. **Lock integrity** — never modify a locked dossier's content or task list unless you are the agent that holds the lock (i.e., `locked_by` matches your identifier). Read access is always permitted.

5. **No re-confirmation** — after unfolding, do not ask the user to re-confirm decisions, preferences, or context that is already recorded in the dossier. The entire point of dossiers is to avoid re-establishing context. Selecting *which ready item to work next* is not re-confirmation of a decision.

6. **Identifier stability** — when using `--claim`, use a consistent agent identifier across the session. If your agent framework provides a session ID, use it. Otherwise, use your agent type (e.g., `claude-code`, `codex`, `gemini-cli`, `opencode`).

7. **CLI only** — never run raw `sqlite3` commands, write YAML frontmatter, or directly manipulate `.db` files. All dossier operations go through `bureau-dossiers`.

8. **Ready-work board is the default first response** on resume (not list mode, not already-selected worker/task). No mutating tool use before a pick. Read-only feedstock loads (`tasks list -v`, `context --task`) are allowed. Bare affirmatives after the board are not picks.

9. **Ready is dependency-aware** — empty `blocked_by` or a single completed task id → eligible; free-text / unparseable `blocked_by` → Blocked with verbatim waiting-on (unless confidently mapped to completed work). Stale claim is an annotation on Ready/Blocked, never a deps bypass; no silent ownership steal.

10. **Brief quality** — each fully shown ready item gets 3-7 bullets that pass the unfamiliar-reader test (what / why now / where / done when / watch-outs as available). No padding; no invented facts. Classify from the unfold task table; use `list -v` / `context` only to enrich briefs.

11. **Board cap** — fully brief at most 7 ready items; remainder one-lined with expansion (`more` / `brief #N`).

12. **Continue is opt-in** — skill-only `--continue` (never a CLI argv) or an explicit continue phrase including bare `"continue"` / `"keep going"`. `next_words` feeds board ranking and orientation; it is not an auto-start trigger unless Continue path is active.

13. **Post-pick claim matches status** — `pending` → `tasks claim`; own `in_progress` → proceed without re-claim; other-owner `in_progress` → explicit reassign confirmation only.
