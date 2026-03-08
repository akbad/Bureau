---
description: Save the current conversation as a Bureau dossier for seamless cross-agent resumption. Activate when user says "fold", "save this conversation", "brain dump", or invokes /bureau-fold. Creates an exhaustive context snapshot at ~/.config/bureau/dossiers/ with a SQLite-backed task list for multi-agent collaboration. Outputs a hash for later resumption via /bureau-unfold.
---

# Bureau Fold: save conversation as dossier

> <ins>***Goal:** capture the full state of the current conversation — decisions, reasoning, context, preferences, and tasks — into a portable dossier that any Bureau agent can resume without losing a single insight.*</ins>

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed **exactly as they are specified**.

## Activation

### Slash command

`/bureau-fold` or `/bureau-fold "my name for this"`

When the user provides a quoted name (e.g., `/bureau-fold "concierge review"`), use that as the dossier name. Otherwise, auto-generate a short, descriptive name from the conversation topic.

### Keyword triggers

When the user says anything like:

- "fold this"
- "fold"
- "save this conversation"
- "brain dump"
- "save this"

*follow this fold protocol* until the dossier is written and confirmed. If you are unsure whether the user wants a fold, confirm unambiguously before proceeding.

### Deactivation

This skill is a one-shot operation. It activates, executes the protocol, writes the dossier, and completes. There is no persistent mode to exit.

---

## Collection protocol

Execute each step in order. Do not skip steps; every step feeds into the final dossier.

### Step 1: Collect git state

Run all four commands and record their output:

```bash
git branch --show-current
git rev-parse --short HEAD
git rev-parse --show-toplevel
git status --porcelain | wc -l
```

- `branch`: the current branch name
- `commit`: the short HEAD hash
- `project`: the absolute path to the repository root
- `dirty_files`: the count of uncommitted changes

If the working directory is not a git repository, record `branch: null`, `commit: null`, and `project: <current working directory>`.

### Step 2: Collect task list

Gather the current task state using **exactly one** of the following strategies, in priority order:

1. **Native task tools available** (TodoRead, TaskList, TaskGet, or equivalent):
   Dump all tasks with their current status, owner, and description.

2. **Resuming from an existing dossier** (a prior dossier slug is known):
   Read tasks from the existing SQLite database:
   ```bash
   sqlite3 -header -column ~/.config/bureau/dossiers/<slug>.tasks.db \
     "SELECT id, subject, status, owner FROM tasks WHERE status != 'deleted';"
   ```

3. **No task tools and no existing dossier:**
   Scan the conversation for any tasks, action items, or TODOs that were discussed. Record each one with a `pending` status and the best-guess owner.

Record the full list for later insertion into the dossier's task database.

### Step 3: Identify key files

List **every** file you read, wrote, or discussed during this session. For each file, include:

- The absolute file path
- A brief annotation of what was done (e.g., "created", "edited lines 40-60", "read for architecture context", "discussed but not modified")

Group files by action type (created, modified, read, discussed) for clarity.

### Step 4: Identify active skills

List any Bureau skills that were invoked during this session. For each skill, note:

- Skill name (e.g., `assess-mode`, `micro-mode`, `fold`)
- Whether it is still active or has completed
- Any relevant state it carries (e.g., micro-mode DAG progress)

If no skills were invoked, record `none`.

### Step 5: Generate the conversation digest

This is the most critical step in the entire protocol. The digest is the **core value** of a dossier. Write it as if the reader has **zero context** about this conversation and must resume work **without asking a single clarifying question**.

> [!IMPORTANT]
>
> **The cost of redundancy is zero. The cost of a missing insight is re-doing the entire conversation.**
>
> Be exhaustive. Be explicit. Be specific. Never summarize when you can enumerate.

You **MUST** include **ALL FIVE** of the following mandatory aspects. Omitting any single one constitutes a failed fold.

---

#### Mandatory Aspect 1: Full reasoning chains

For **every** decision made during this conversation, capture:

- **What** was decided
- **Why** this option was chosen over alternatives
- **What alternatives** were considered and why they were rejected
- **Who** made the decision (user directive vs. agent recommendation vs. mutual agreement)

If a decision was made quickly or implicitly, **reconstruct the reasoning**. Do not leave gaps — the resuming agent cannot read between the lines.

**Example format:**
```
Decision: Use SQLite for task storage instead of JSON files
  Chosen because: ACID guarantees, concurrent access from multiple agents, query flexibility
  Rejected alternatives:
    - JSON files: no locking, race conditions with parallel agents
    - YAML: same issues as JSON, plus slower parsing
  Decided by: user directive in message 3
```

#### Mandatory Aspect 2: Exact in-flight state

Capture the precise state of work at the moment of folding:

- What was the **last action** taken?
- What is **expected to happen next**?
- What question or decision is **pending**, if any?
- What subagents are **running or recently completed**?
- Include any **partial results**, intermediate findings, or half-formed hypotheses
- If there is a sequence of planned steps, indicate which step you are on

**Example format:**
```
Last action: Committed fold SKILL.md to feat/skills-system branch
Expected next: Create unfold SKILL.md, then dossiers cleanup handler
Pending question: None
Running subagents: Task #51 (unfold SKILL.md) in progress on separate agent
Partial results: Dossier YAML schema drafted but not yet validated against existing configs
```

#### Mandatory Aspect 3: Observed user preferences and patterns

Capture anything that would take multiple interactions to re-learn:

- **Communication style**: e.g., "user prefers terse responses", "user likes detailed explanations with examples", "user reads every line carefully"
- **Workflow preferences**: e.g., "user prefers worktree isolation over sequential agents", "user wants parallel agent teams whenever possible"
- **Tool choices**: e.g., "user always uses uv, never pip", "user prefers sqlite3 CLI over Python sqlite3 module"
- **Recurring instructions**: e.g., "user says '>' to advance in micro mode", "user wants git commits after every logical unit"
- **Style conventions**: e.g., "user wants type hints on all public functions", "user follows Google docstring style"
- **Frustration signals**: e.g., "user got frustrated when agent asked unnecessary clarifying questions — prefer making reasonable assumptions and proceeding"

#### Mandatory Aspect 4: Hard-won technical context

Capture everything that took significant investigation or trial-and-error to derive:

- **Architecture relationships** discovered during the session
- **Gotchas encountered** and workarounds applied
- **Performance characteristics** observed
- **Dependency quirks** and version constraints
- **Specific file paths**, line numbers, and function names that are relevant
- **Configuration details** that are not obvious from the code alone
- **API behaviors** that differ from documentation
- **Edge cases** encountered or anticipated

**Example format:**
```
- The skills installer reads SKILL.md frontmatter to extract the description;
  if a `name` field is present, it causes a VSCode warning because the install
  directory is prefixed with `bureau-` but the source directory is not.
  See: protocols/context/static/skills/README.md
- SQLite WAL mode is required for concurrent reads from multiple agents
- The config loader in bureau/config/config_loader.py does NOT auto-create
  missing directories — the caller must ensure ~/.config/bureau/ exists
```

#### Mandatory Aspect 5: Unreconstructable mental state

Capture the context that exists **only** in the conversation and cannot be recovered from files alone:

- The **mental model** of how components connect to each other
- **Trade-offs** currently being weighed but not yet decided
- **Hypotheses** being tested or about to be tested
- The **"why behind the why"** — not just what was decided, but the thought process and motivations that led there
- **Unspoken assumptions** that the user and agent have built up over the course of the conversation
- **Future plans** discussed but not yet acted on
- **Concerns or risks** identified but not yet addressed

---

## Dossier file assembly

After completing all collection steps, assemble the dossier markdown file with this **exact structure**:

```yaml
---
hash: <6-char-hex>
name: "<user-provided name or auto-generated>"
slug: <name-slugified>-<hash>
created: <ISO-8601 UTC timestamp>
updated: <ISO-8601 UTC timestamp>
agent: <agent-identifier>
project: <git repo root path>
branch: <current branch>
commit: <short HEAD>
parent: null
locked_by: null
locked_at: null
---

## Task state

<render current task list as a markdown table with columns: ID, Subject, Status, Owner>

## Decision log

<chronological list of every decision made, with reasoning per Mandatory Aspect 1>

## Pending state

<exact in-flight state per Mandatory Aspect 2>

## Key files

<files read, written, or discussed during the session, grouped by action type>

## Active skills

<skills invoked during this session, with state>

## Conversation digest

<the exhaustive brain dump covering ALL FIVE mandatory aspects>
```

### Field reference

| Field | Value |
|---|---|
| `hash` | 6-character hex string derived from dossier content (see file writing protocol below) |
| `name` | User-provided name from `/bureau-fold "name"`, or auto-generated from conversation topic |
| `slug` | `<name-slugified>-<hash>` — the name converted to lowercase kebab-case, appended with a dash and the hash. Example: `concierge-review-a7f3c2` |
| `created` | ISO-8601 UTC timestamp at time of fold. Example: `2026-03-08T14:30:00Z` |
| `updated` | Same as `created` for new dossiers; updated on subsequent folds |
| `agent` | Identifier of the agent performing the fold: `claude-code`, `codex`, `gemini-cli`, `opencode`, or similar |
| `project` | Absolute path to the git repository root (from `git rev-parse --show-toplevel`) |
| `branch` | Current git branch name |
| `commit` | Short HEAD hash |
| `parent` | Hash of the parent dossier if this is a re-fold; `null` for first fold |
| `locked_by` | Always `null` for new dossiers (locking is done by the agent that resumes) |
| `locked_at` | Always `null` for new dossiers |

---

## File writing protocol

After assembling the dossier content, write the files to disk following these exact steps.

### 1. Create the dossiers directory

```bash
mkdir -p ~/.config/bureau/dossiers
```

### 2. Generate the 6-character hex hash

Compute the hash from the dossier content and current timestamp to ensure uniqueness:

```bash
echo -n "<first-100-chars-of-dossier-body>$(date -u +%s)" | shasum -a 256 | cut -c1-6
```

Use this hash in the `hash` and `slug` fields of the frontmatter.

### 3. Write the dossier markdown file

Write the assembled dossier to:

```
~/.config/bureau/dossiers/<slug>.md
```

Where `<slug>` is `<name-slugified>-<hash>` (e.g., `concierge-review-a7f3c2.md`).

### 4. Create the SQLite task database

Create a WAL-mode SQLite database alongside the dossier:

```bash
sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    owner TEXT,
    blocked_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"
```

### 5. Populate tasks from collected task state

Insert each task collected in Step 2:

```bash
sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
INSERT INTO tasks (subject, description, status, owner, blocked_by)
VALUES ('<subject>', '<description>', '<status>', '<owner>', '<blocked_by>');
"
```

Repeat for each task. **Escape single quotes** in all values by doubling them (e.g., `it''s`). Use `NULL` (not the string `'null'`) for empty fields.

---

## Output

After writing both files successfully, confirm to the user with this exact format:

```
Dossier saved: `<slug>` (<N> tasks recorded)
Resume with `/bureau-unfold <hash>` or `/bureau-unfold <name>`
```

If any step fails, report the failure clearly and do **not** leave partial files on disk.

---

## Explicit prohibitions

- **Do NOT** save the raw conversation transcript — the digest replaces it
- **Do NOT** modify any repository files or git state — dossiers live outside the repo in `~/.config/bureau/dossiers/`
- **Do NOT** auto-lock the dossier — fresh dossiers are always `locked_by: null`
- **Do NOT** abbreviate, truncate, or summarize the digest — exhaustive detail is mandatory; if in doubt, include more rather than less
- **Do NOT** include a `name` field in this skill's YAML frontmatter (per Bureau convention — the skill name is derived from the install directory)
- **Do NOT** prompt the user for additional information unless absolutely necessary — use the conversation history and tool outputs to fill in all fields
