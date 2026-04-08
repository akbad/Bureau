---
name: unfold-dossier
description: Pick up a previously saved Bureau dossier or list all saved dossiers. Activate when user says "unfold", "pick up where I left off", "resume", "my dossiers", or invokes /unfold-dossier. Supports hash lookup, fuzzy name matching, fork/claim collaboration, and CLI-managed task lists for multi-agent coordination.
---

# Bureau Unfold: pick up or list saved dossiers

> **Goal:** pick up a conversation exactly where it was left off — with your own memory, decisions, reasoning, and task state intact — so seamlessly that neither you nor the user notice the seam. Alternatively, list all saved dossiers for selection.

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

| Flag | Effect |
|------|--------|
| `--claim` | Lock the dossier for exclusive access during this session |
| `--fork` | Create a copy of the dossier (always safe, no coordination needed) |

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

The CLI scans `~/.config/bureau/dossiers/` for `.db` files and outputs a table with hash, name, branch, relative time, and lock status — sorted by most recent first.

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

Only use `--full` when the compact output is insufficient to pick up the work.

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
> - Pick up from the **EXACT** point described in the pending state
> - Treat pinned findings and dead ends as hard constraints — do not re-explore dead ends marked `[DO NOT RETRY]`
> - If memory queries were logged, do not repeat them unless you need fresher results
> - Your task list is managed via the CLI — use Bureau task CLI (`tasks claim`, `tasks complete`, `tasks add`) for ALL task operations
> - If the dossier mentions user preferences, follow them without re-confirming
> - **Match the mood**: read the session mood field first and calibrate your tone, pacing, and confidence level accordingly from your very first response

**Confidence check (silent, before your first response):** After reading the dossier, verify internally:

1. Can you name the **next concrete action** you need to take?
2. Do you know which **files are relevant** and roughly what state they are in?
3. Can you identify all **dead ends** you must not re-explore?

If any answer is uncertain, silently re-run `bureau-dossiers unfold <slug> --full` and re-read the complete digests before producing any response. Do not tell the user you are doing this — it is invisible self-correction. The cost of one extra tool call is negligible compared to the cost of confidently re-exploring a dead end or asking a settled question.

**Default behavior: continue mid-thought.** Do not announce your return. If `next_words` is present in the dossier, use it as the literal opening of your first response — complete the thought, then proceed. If there is a pending action, start doing it. The user knows they unfolded; they do not need a status report.

If `next_words` is absent or the pending state is unclear, fall back to a **minimal orientation** (not a full status dump):

```
Back on it. I was [one-line pending state] — picking up there.
```

**Structured greeting (opt-in only):** The full status block is available when the user passes `--announce` or explicitly asks "where are we?":

```
<name> (<hash>) | <branch> | updated <relative-time>

Pending: <one-line summary from latest session digest>
Tasks: <N> total — <X> pending, <Y> in progress, <Z> completed
```

### Context anchoring

When the dossier includes a `last_exchange` field, read it **before** the digest. This is the verbatim final moment of the prior conversation — it anchors your memory in a concrete exchange rather than an abstract summary. After reading it, the digest will feel like context you already have rather than new information.

When the dossier includes `pinned_findings`, treat them as **hard constraints** that override any conflicting information in the digest. Dead ends marked `[DO NOT RETRY]` are absolute prohibitions. Dead ends marked `[CONDITIONAL]` may be revisited only if the stated condition has changed.

When the dossier includes `memory_queries`, treat them as a **cache**: do not re-query the same memory systems with the same queries unless you have reason to believe the results have changed (e.g., significant time has passed, new data has been stored).

### Delegating tasks to workers

When you want to delegate a task to a subagent, use the context extraction primitive:

```bash
# pre-claim the task for the subagent
bureau-dossiers tasks <slug> claim --id <task-id> --agent <subagent-label>

# extract task-scoped context
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
bureau-dossiers tasks <slug> update --id <task-id> --status <status> --owner <owner>
```

Use `update` for corrections and metadata changes. For status transitions during normal workflow, prefer `claim` and `complete` — they provide race-safe guarantees.

### Add a new task

```bash
bureau-dossiers tasks <slug> add --subject "Task subject" --status pending
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

## Explicit behaviors

These rules apply at all times during an unfold session:

1. **Relative time display** — when listing dossiers, always compute relative time from the `updated` field (e.g., "2h ago", "3d ago", "1w ago"). Do not show raw ISO timestamps in user-facing tables.

2. **Lock status visibility** — always show lock status in listings and when unfolding. Never hide the fact that a dossier is claimed by another agent.

3. **Fork completeness** — when forking via `--fork`, the CLI copies the complete dossier database (all tables including tasks). The fork is fully independent.

4. **Lock integrity** — never modify a locked dossier's content or task list unless you are the agent that holds the lock (i.e., `locked_by` matches your identifier). Read access is always permitted.

5. **No re-confirmation** — after unfolding, do not ask the user to re-confirm decisions, preferences, or context that is already recorded in the dossier. The entire point of dossiers is to avoid re-establishing context.

6. **Identifier stability** — when using `--claim`, use a consistent agent identifier across the session. If your agent framework provides a session ID, use it. Otherwise, use your agent type (e.g., `claude-code`, `codex`, `gemini-cli`, `opencode`).

7. **CLI only** — never run raw `sqlite3` commands, write YAML frontmatter, or directly manipulate `.db` files. All dossier operations go through `bureau-dossiers`.
