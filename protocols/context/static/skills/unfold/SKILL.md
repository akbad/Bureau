---
description: Resume a previously saved Bureau dossier or list all saved dossiers. Activate when user says "unfold", "pick up where I left off", "resume", "my dossiers", or invokes /bureau-unfold. Supports hash lookup, fuzzy name matching, fork/claim collaboration, and CLI-managed task lists for multi-agent coordination.
---

# Bureau Unfold: resume or list saved dossiers

> **Goal:** resume a previously saved conversation from a dossier, picking up from the exact point where it was folded — with full context, decisions, and task state intact. Alternatively, list all saved dossiers for selection.

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
- `/bureau-unfold` (with or without arguments)

*Follow this unfold protocol.* If you are unsure, confirm unambiguously with the user.

### Invocation forms

| Form | Mode | Behavior |
|------|------|----------|
| `/bureau-unfold` | **List** | Show all saved dossiers |
| `/bureau-unfold <hash>` | **Resume** | Resume by exact hash or hash prefix |
| `/bureau-unfold <name>` | **Resume** | Fuzzy match on dossier name/slug |

### Flags

| Flag | Effect |
|------|--------|
| `--claim` | Lock the dossier for exclusive access during this session |
| `--fork` | Create a copy of the dossier (always safe, no coordination needed) |

---

## List mode

Triggered when `/bureau-unfold` is invoked **with no arguments**, or when the user says "my dossiers", "saved conversations", or similar.

### Step 1: List all dossiers

```bash
uv run python -m operations.dossiers list
```

The CLI scans `~/.config/bureau/dossiers/` for `.db` files and outputs a table with hash, name, branch, relative time, and lock status — sorted by most recent first.

### Step 2: Display and accept selection

Display the CLI output as a **lettered table** for easy selection:

```
Saved dossiers:

a) a7f3c2  concierge-code-review      feat/concierge   2h ago    unlocked
b) b3e91d  mcp-schema-brainstorm      main             3d ago    claimed by codex
c) f82a01  logging-overhaul           feat/logging     1w ago    unlocked

Resume with /bureau-unfold <hash> or pick a letter.
```

Accept either:
- A **letter** (a, b, c...) corresponding to a row in the table
- A **hash** or **hash prefix**

Then proceed to **Resume mode** with the selected dossier.

### Step 3: Handle empty state

If the CLI reports no dossiers found:

```
No saved dossiers found. Use /bureau-fold to save a conversation.
```

---

## Resume mode

Triggered when `/bureau-unfold` is invoked **with a hash or name argument**, or after the user selects a dossier from list mode.

### Step 1: Unfold via CLI

Run the unfold command with the appropriate flags based on the user's request:

**Default (read-only resume):**

```bash
uv run python -m operations.dossiers unfold <hash-or-name>
```

**With `--claim` (exclusive access):**

```bash
uv run python -m operations.dossiers unfold <hash-or-name> --claim --agent <your-agent-id>
```

Use a consistent agent identifier: `claude-code`, `codex`, `gemini-cli`, `opencode`, or similar.

**With `--fork` (independent copy):**

```bash
uv run python -m operations.dossiers unfold <hash-or-name> --fork
```

The CLI handles all resolution, lock checking, and forking automatically:

- **Resolution**: The CLI matches by exact hash, hash prefix, or fuzzy slug match. If ambiguous, it reports candidates — present them as a lettered table and ask the user to pick.
- **Lock conflicts**: If the dossier is locked by another agent and `--claim` was requested, the CLI reports the conflict. Present the user with options: `--fork` or wait.
- **Fork**: The CLI creates an independent copy with a new hash, `parent` set to the original, and all data (including tasks) copied. Forks start unlocked.

**If no match**: inform the user and suggest listing:

```
No dossier found matching "<input>". Run /bureau-unfold to list all saved dossiers.
```

### Step 2: Load and inject context

The CLI outputs the full dossier state rendered as markdown: metadata, recent session digests, task list, and all decisions. Read and internalize this output.

If the unfold was a default (no `--claim`, no `--fork`):
- **Read-only resume** — no lock is acquired
- Other agents can also resume from the same dossier simultaneously
- If you later need exclusive access, suggest `--claim`

### Step 3: Context injection directive

After loading the dossier, follow this directive strictly:

> You are resuming a conversation from a dossier. Read the entire dossier content above. Follow these rules:
>
> - Do **NOT** re-ask any question that has a decision recorded in the decisions section
> - Do **NOT** re-explore or re-read files listed in file interactions unless you specifically need to verify something has changed since the dossier was created
> - Pick up from the **EXACT** point described in the pending state section of the latest session digest
> - Your task list is managed via the CLI — use it to track work items
> - Treat the session digests as if you personally had the conversation — internalize the reasoning, preferences, and mental state described there
> - If the dossier mentions user preferences, follow them without re-confirming

Greet the user with a brief summary of where you are picking up:

```
Resumed dossier <hash> (<name>).
Branch: <branch> | Project: <project> | Last updated: <relative-time>

Pending state: <one-line summary from the latest session digest>

Task list: <N> total — <X> pending, <Y> in progress, <Z> completed

Ready to continue.
```

---

## Task list interaction

The dossier's task list is managed via the CLI. Multiple agents can read from and write to the task list concurrently (the underlying database uses WAL mode for safe concurrent access). **Never run raw `sqlite3` commands** — use the CLI for all task operations.

### View all tasks

```bash
uv run python -m operations.dossiers tasks <slug> list
```

### Claim a task (mark as in-progress)

```bash
uv run python -m operations.dossiers tasks <slug> update --id <task-id> --status in_progress --owner <your-agent-id>
```

### Complete a task

```bash
uv run python -m operations.dossiers tasks <slug> update --id <task-id> --status completed
```

### Add a new task

```bash
uv run python -m operations.dossiers tasks <slug> add --subject "Task subject" --status pending
```

### Remove a task

```bash
uv run python -m operations.dossiers tasks <slug> remove --id <task-id>
```

Use these commands throughout the session to coordinate work. Always check for blocked tasks before starting a new work item — if a task's `blocked_by` field references another task ID, that dependency must be completed first.

---

## Session end reminder

At the end of any session that was resumed from a dossier, remind the user:

```
You resumed from dossier `<slug>`. To save your progress, run /bureau-fold to create an updated dossier.
```

If the dossier was claimed (`--claim`), also remind:

```
This dossier is still locked by you. It will be unlocked when you fold, or you can release it manually.
```

### Releasing a lock manually

To release a lock without folding:

```bash
uv run python -m operations.dossiers lock <slug> release
```

This frees the dossier for other agents to claim.

---

## Explicit behaviors

These rules apply at all times during an unfold session:

1. **Relative time display** — when listing dossiers, always compute relative time from the `updated` field (e.g., "2h ago", "3d ago", "1w ago"). Do not show raw ISO timestamps in user-facing tables.

2. **Lock status visibility** — always show lock status in listings and when resuming. Never hide the fact that a dossier is claimed by another agent.

3. **Fork completeness** — when forking via `--fork`, the CLI copies the complete dossier database (all tables including tasks). The fork is fully independent.

4. **Lock integrity** — never modify a locked dossier's content or task list unless you are the agent that holds the lock (i.e., `locked_by` matches your identifier). Read access is always permitted.

5. **No re-confirmation** — when resuming, do not ask the user to re-confirm decisions, preferences, or context that is already recorded in the dossier. The entire point of dossiers is to avoid re-establishing context.

6. **Identifier stability** — when using `--claim`, use a consistent agent identifier across the session. If your agent framework provides a session ID, use it. Otherwise, use your agent type (e.g., `claude-code`, `codex`, `gemini-cli`, `opencode`).

7. **CLI only** — never run raw `sqlite3` commands, write YAML frontmatter, or directly manipulate `.db` files. All dossier operations go through `uv run python -m operations.dossiers`.
