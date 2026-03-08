---
description: Resume a previously saved Bureau dossier or list all saved dossiers. Activate when user says "unfold", "pick up where I left off", "resume", "my dossiers", or invokes /bureau-unfold. Supports hash lookup, fuzzy name matching, fork/claim collaboration, and shared SQLite task lists for multi-agent coordination.
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

### Step 1: Ensure dossiers directory exists

```bash
mkdir -p ~/.config/bureau/dossiers
```

### Step 2: Scan for dossier files

```bash
ls -t ~/.config/bureau/dossiers/*.md 2>/dev/null
```

### Step 3: Parse and display

For each `.md` file found, parse the YAML frontmatter (between `---` delimiters) to extract:

- `hash` — the 6-character dossier identifier
- `name` — human-readable dossier name
- `project` — the project/repo this dossier belongs to
- `branch` — the git branch at time of fold
- `locked_by` — which agent currently holds the lock (if any)
- `updated` — ISO-8601 timestamp of last modification

Compute a relative time string from the `updated` field (e.g., "2h ago", "3d ago", "1w ago").

Determine lock status:
- If `locked_by` is `null` or empty: display **unlocked**
- If `locked_by` is set: display **claimed by \<locked_by\>**

Display as a **lettered table**, sorted by most recent first:

```
Saved dossiers:

a) a7f3c2  concierge-code-review      feat/concierge   2h ago    unlocked
b) b3e91d  mcp-schema-brainstorm      main             3d ago    claimed by codex
c) f82a01  logging-overhaul           feat/logging     1w ago    unlocked

Resume with /bureau-unfold <hash> or pick a letter.
```

### Step 4: Accept selection

Accept either:
- A **letter** (a, b, c...) corresponding to a row in the table
- A **hash** or **hash prefix**

Then proceed to **Resume mode** with the selected dossier.

### Step 5: Handle empty state

If no `.md` files are found in the dossiers directory:

```
No saved dossiers found. Use /bureau-fold to save a conversation.
```

---

## Resume mode

Triggered when `/bureau-unfold` is invoked **with a hash or name argument**, or after the user selects a dossier from list mode.

### Step 1: Resolve identifier

Attempt to match the provided identifier against dossier files in `~/.config/bureau/dossiers/`. Try in this order:

1. **Exact hash match** — look for files whose YAML frontmatter `hash` field equals the input exactly, or whose filename matches the pattern `*-<input>.md`
2. **Hash prefix match** — look for files where the `hash` field starts with the input string
3. **Fuzzy slug match** — look for filenames containing the input string (case-insensitive)

**If ambiguous** (multiple matches): show candidates and ask the user to pick:

```
Multiple dossiers match "<input>":

a) a7f3c2  concierge-code-review      feat/concierge   2h ago
b) a7f9d1  concierge-refactor         feat/concierge   5d ago

Which one? (letter or hash)
```

**If no match**: inform the user and suggest listing:

```
No dossier found matching "<input>". Run /bureau-unfold to list all saved dossiers.
```

### Step 2: Read and check lock state

Read the YAML frontmatter of the matched dossier file. Check the `locked_by` field:

**If unlocked** (`locked_by` is `null` or empty):
- Proceed normally to Step 3.

**If locked** (`locked_by` is set to another agent):

```
This dossier is currently claimed by <locked_by> (since <locked_at>).
Options:
1. Fork it (create your own copy): /bureau-unfold <hash> --fork
2. Wait for the other session to release it
```

Do **not** proceed with `--claim` on a dossier already locked by another agent. The user must explicitly `--fork` or wait.

**If `--fork` flag was provided**: always fork regardless of lock state (skip to fork handling in Step 3).

### Step 3: Handle claim or fork

#### If `--claim` flag is provided

Update the dossier file's YAML frontmatter in-place:

- Set `locked_by` to your agent/session identifier (e.g., `claude-code`, `codex`, `gemini-cli`, or a session-specific ID if available)
- Set `locked_at` to the current ISO-8601 UTC timestamp (e.g., `2026-03-08T14:30:00Z`)
- Update `updated` to the current ISO-8601 UTC timestamp

You now have **exclusive write access** to this dossier file. No other agent should modify it while you hold the lock.

#### If `--fork` flag is provided

1. Read the original dossier file completely (frontmatter + body)
2. Generate a new 6-character hex hash (e.g., via `openssl rand -hex 3`)
3. Create a new dossier file with:
   - The new hash
   - A new slug derived from the original (e.g., `<original-slug>-fork-<new-hash>`)
   - `parent: <original-hash>` added to frontmatter to track lineage
   - `locked_by: null` (forks start unlocked)
   - All other content copied verbatim from the original
4. Copy the task database (if it exists):

```bash
if [ -f ~/.config/bureau/dossiers/<original-slug>.tasks.db ]; then
    cp ~/.config/bureau/dossiers/<original-slug>.tasks.db ~/.config/bureau/dossiers/<new-slug>.tasks.db
fi
```

5. Inform the user:

```
Forked dossier <original-hash> → <new-hash> (<new-slug>).
Task database copied. You can now work on this fork independently.
```

If the original had no task database, note this: "No task database found in original — fork has dossier content only."

#### If no flag (default)

- **Read-only resume** — no lock is acquired
- You can read the dossier content and the shared task list
- Other agents can also resume from the same dossier simultaneously
- If you later need exclusive access, suggest `--claim`

### Step 4: Load and inject context

Read the **full dossier body** (everything after the YAML frontmatter).

Then load the **current task list** from the SQLite database:

```bash
sqlite3 -header -column ~/.config/bureau/dossiers/<slug>.tasks.db "
SELECT id, subject, status, owner, blocked_by FROM tasks WHERE status != 'deleted' ORDER BY id;
"
```

If the `.tasks.db` file does not exist, note this to the user but continue with the dossier content alone.

Present **both** the dossier content and the task list as your opening context for the resumed session.

### Step 5: Context injection directive

After loading the dossier, follow this directive strictly:

> You are resuming a conversation from a dossier. Read the entire dossier content above. Follow these rules:
>
> - Do **NOT** re-ask any question that has a decision recorded in the "Decision log" section
> - Do **NOT** re-explore or re-read files listed in "Key files" unless you specifically need to verify something has changed since the dossier was created
> - Pick up from the **EXACT** point described in the "Pending state" section
> - Your task list is in the SQLite database — use it to track work items
> - Treat the "Conversation digest" as if you personally had the conversation — internalize the reasoning, preferences, and mental state described there
> - If the dossier mentions user preferences, follow them without re-confirming

Greet the user with a brief summary of where you are picking up:

```
Resumed dossier <hash> (<name>).
Branch: <branch> | Project: <project> | Last updated: <relative-time>

Pending state: <one-line summary from the Pending state section>

Task list: <N> total — <X> pending, <Y> in progress, <Z> completed

Ready to continue.
```

---

## Task list interaction

The dossier's task list lives in a shared SQLite database at `~/.config/bureau/dossiers/<slug>.tasks.db`. Multiple agents can read from and write to this database concurrently (the database uses WAL mode for safe concurrent access).

**Important:** For all write operations (UPDATE, INSERT), always ensure WAL mode is active by prefixing with `PRAGMA journal_mode=WAL;`. **Escape single quotes** in all values by doubling them (e.g., `it''s`). Use `NULL` (not the string `'null'`) for empty fields.

### View all tasks

```bash
sqlite3 -header -column ~/.config/bureau/dossiers/<slug>.tasks.db "
SELECT id, status, owner, subject FROM tasks WHERE status != 'deleted' ORDER BY id;
"
```

### Claim a task (mark as in-progress)

```bash
sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
PRAGMA journal_mode=WAL;
UPDATE tasks SET status='in_progress', owner='<your-session-id>', updated_at=datetime('now') WHERE id=<task-id>;
"
```

### Complete a task

```bash
sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
PRAGMA journal_mode=WAL;
UPDATE tasks SET status='completed', updated_at=datetime('now') WHERE id=<task-id>;
"
```

### Add a new task

```bash
sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db <<'ENDSQL'
PRAGMA journal_mode=WAL;
INSERT INTO tasks (subject, description, status, created_at, updated_at)
VALUES ('subject here', 'description here', 'pending', datetime('now'), datetime('now'));
ENDSQL
```

### Check for blocked tasks

```bash
sqlite3 -header -column ~/.config/bureau/dossiers/<slug>.tasks.db "
SELECT id, subject, blocked_by FROM tasks WHERE blocked_by IS NOT NULL AND status = 'pending';
"
```

Use these commands throughout the session to coordinate work. Always check for blocked tasks before starting a new work item — if a task's `blocked_by` field references another task ID, that dependency must be completed first.

If your agent environment supports native SQLite libraries or file-writing tools, prefer those over shell commands to avoid quoting issues entirely.

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

To release a lock without folding, edit the dossier file's YAML frontmatter and set:

```yaml
locked_by: null
locked_at: null
```

Update the `updated` timestamp to the current time as well. This frees the dossier for other agents to claim.

---

## Explicit behaviors

These rules apply at all times during an unfold session:

1. **Relative time display** — when listing dossiers, always compute relative time from the `updated` field (e.g., "2h ago", "3d ago", "1w ago"). Do not show raw ISO timestamps in user-facing tables.

2. **Lock status visibility** — always show lock status in listings and when resuming. Never hide the fact that a dossier is claimed by another agent.

3. **Fork completeness** — when forking, copy the **complete task database** (the `.tasks.db` file), not just the markdown content. The fork must be fully independent.

4. **Lock integrity** — never modify a locked dossier's content or task database unless you are the agent that holds the lock (i.e., `locked_by` matches your identifier). Read access is always permitted.

5. **Directory bootstrapping** — if the dossiers directory (`~/.config/bureau/dossiers`) does not exist at any point during execution, create it:

   ```bash
   mkdir -p ~/.config/bureau/dossiers
   ```

6. **Graceful degradation** — if the `.tasks.db` file is missing for a dossier, resume from the markdown content alone. Inform the user that no task database was found and suggest creating one via `/bureau-fold`.

7. **No re-confirmation** — when resuming, do not ask the user to re-confirm decisions, preferences, or context that is already recorded in the dossier. The entire point of dossiers is to avoid re-establishing context.

8. **Identifier stability** — when using `--claim`, use a consistent agent identifier across the session. If your agent framework provides a session ID, use it. Otherwise, use your agent type (e.g., `claude-code`, `codex`, `gemini-cli`, `opencode`).
