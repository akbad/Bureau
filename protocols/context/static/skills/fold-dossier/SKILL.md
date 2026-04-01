---
name: fold-dossier
description: Save the current conversation as a Bureau dossier for seamless cross-agent resumption. Activate when user says "fold", "save this conversation", "brain dump", or invokes /fold-dossier. Creates an exhaustive context snapshot at ~/.config/bureau/dossiers/ via the dossier CLI with a SQLite-backed task list for multi-agent collaboration. Outputs a hash for later resumption via /unfold-dossier.
---

# Bureau Fold: save conversation as dossier

> <ins>***Goal:** capture the full state of the current conversation — decisions, reasoning, context, preferences, and tasks — into a portable dossier that any Bureau agent can resume without losing a single insight.*</ins>

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed **exactly as they are specified**.

## Activation

### Slash command

`/fold-dossier` or `/fold-dossier "my name for this"`

When the user provides a quoted name (e.g., `/fold-dossier "concierge review"`), use that as the dossier name. Otherwise, auto-generate a short, descriptive name from the conversation topic.

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

Use **one of these two formats** whenever a CLI command requires a dossier identifier (e.g., `--slug` on re-fold, or the positional `slug` argument for `tasks`). Do **not** use the bare name (e.g., `reverb-threats`) without the hash suffix.

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

1. **Resuming from an existing dossier** (a prior dossier slug is known):
   Task state is already managed in the Bureau DB via `tasks claim`/`tasks complete` throughout the session. Read the current state:
   ```bash
   bureau-dossiers tasks <slug> list
   ```
   Do **NOT** re-collect tasks from native task tools (TodoWrite/TodoRead) — the Bureau DB is the source of truth.

2. **New fold, native task tools available** (TodoRead, TaskList, TaskGet, or equivalent):
   Dump all tasks with their current status, owner, and description.

3. **New fold, no task tools and no existing dossier:**
   Scan the conversation for any tasks, action items, or TODOs that were discussed. Record each one with a `pending` status and the best-guess owner.

Record the full list for later insertion into the dossier's task database (new folds) or for reporting (re-folds).

### Step 3: Identify key files

List **every** file you read, wrote, or discussed during this session. For each file, include:

- The absolute file path
- A brief annotation of what was done (e.g., "created", "edited lines 40-60", "read for architecture context", "discussed but not modified")

Group files by action type (created, modified, read, discussed) for clarity.

### Step 4: Identify active skills

List any Bureau skills that were invoked during this session. For each skill, note:

- Skill name (e.g., `assess-mode`, `micro-mode`, `fold-dossier`)
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

For decisions with **explicit** reasoning stated in the conversation, record it directly. For decisions where reasoning was **implicit or unstated**, prefix the reconstruction with `[inferred]` so the resuming agent knows to verify before relying on it.

**Example format:**
```
Decision: Use SQLite for task storage instead of JSON files
  Chosen because: [inferred] ACID guarantees, concurrent access from multiple agents
  Confidence: inferred — user did not state reasoning explicitly
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

## Dossier assembly and writing

After completing all collection steps, assemble the data and write the dossier using the CLI. The CLI handles all file creation, hash generation, schema setup, and metadata — you never touch the database or write frontmatter directly.

### Step 6: Assemble the JSON input file

Create a JSON file containing all structured data collected in Steps 1-5. The digest is inlined directly in the JSON.

```bash
cat > /tmp/fold-input.json << 'ENDJSON'
{
  "name": "<user-provided name or auto-generated>",
  "agent": "<agent-identifier>",
  "project": "<git repo root path>",
  "branch": "<current branch>",
  "commit": "<short HEAD>",
  "digest": "<the exhaustive brain dump covering ALL FIVE mandatory aspects>",
  "tasks": [
    {"subject": "Task subject", "status": "pending", "owner": null, "description": "Task description", "blocked_by": null}
  ],
  "decisions": [
    {"what": "What was decided", "why": "Why this option was chosen", "alternatives": "JSON-encoded array of rejected alternatives", "decided_by": "user directive"}
  ],
  "files": [
    {"path": "/absolute/path/to/file.py", "action": "modified", "annotation": "edited lines 40-60"}
  ]
}
ENDJSON
```

> [!IMPORTANT]
> **Re-fold vs. new fold behavior:**
>
> - **New fold** (no `--slug`): include the full `tasks` and `decisions` arrays. The CLI uses them for initial population.
> - **Re-fold** (`--slug` provided): **omit the `tasks` array** (or pass `[]`). The CLI ignores tasks on re-fold — task state is managed via `tasks claim`/`tasks complete`/`tasks add` throughout the session. For `decisions`, include only decisions made in the **current** session, not inherited decisions from prior sessions.

**Field reference:**

| Field | Value |
|---|---|
| `name` | User-provided name from `/fold-dossier "name"`, or auto-generated from conversation topic. Required for new dossiers; omit when re-folding with `--slug`. |
| `agent` | Identifier of the agent performing the fold: `claude-code`, `codex`, `gemini-cli`, `opencode`, or similar |
| `project` | Absolute path to the git repository root (from `git rev-parse --show-toplevel`) |
| `branch` | Current git branch name |
| `commit` | Short HEAD hash |
| `digest` | The full conversation digest covering all five mandatory aspects (inlined as a string) |
| `tasks` | Array of task objects from Step 2 |
| `decisions` | Array of decision objects from the conversation (Mandatory Aspect 1) |
| `files` | Array of file interaction objects from Step 3 |

### Step 7: Run the CLI

Run **one** command to create or update the dossier:

**For a new dossier:**

```bash
bureau-dossiers fold --input-file /tmp/fold-input.json
```

**For re-folding an existing dossier** (when a prior slug is known):

```bash
bureau-dossiers fold --slug <existing-slug> --input-file /tmp/fold-input.json
```

The CLI automatically:
- Generates the 6-character hex hash and slug (new dossiers)
- Creates the SQLite database with the full schema (WAL mode)
- Inserts metadata, session digest, tasks, decisions, and file interactions
- Prunes old file interactions beyond the retention window
- Updates `metadata.updated_at` on re-folds

### Step 8: Confirm output

The CLI prints a confirmation line on success. Relay it to the user in this format:

```
Dossier saved: `<slug>` (<N> tasks, <M> decisions)
Resume with `/unfold-dossier <hash>` or `/unfold-dossier <name>`
```

If the CLI exits with a non-zero status, report the error clearly. The CLI is atomic — a failed fold leaves no partial state.

---

## Explicit prohibitions

- **Do NOT** save the raw conversation transcript — the digest replaces it
- **Do NOT** modify any repository files or git state — dossiers live outside the repo in `~/.config/bureau/dossiers/`
- **Do NOT** auto-lock the dossier — fresh dossiers are always unlocked
- **Do NOT** abbreviate, truncate, or summarize the digest — exhaustive detail is mandatory; if in doubt, include more rather than less
- **Do NOT** include a `name` field in this skill's YAML frontmatter (per Bureau convention — the skill name is derived from the install directory)
- **Do NOT** prompt the user for additional information unless absolutely necessary — use the conversation history and tool outputs to fill in all fields
- **Do NOT** run raw `sqlite3` commands or write YAML frontmatter manually — all database and file operations go through the CLI
- **Do NOT** run `openssl rand` for hash generation — the CLI generates hashes automatically
- **Do NOT** include inherited decisions from prior sessions in the `decisions` array when re-folding — only include decisions made during the current session

---

## Task state management during sessions

When working from an unfolded dossier, update task state via the Bureau CLI **as events happen** — do not batch task updates into the fold.

- When you start working on a task: `bureau-dossiers tasks <slug> claim --id <task-id> --agent <your-agent-id>`
- When you complete a task: `bureau-dossiers tasks <slug> complete --id <task-id>`
- When you discover new work: `bureau-dossiers tasks <slug> add --subject "New task"`

This ensures other agents checking the task list see accurate, up-to-date state — even before this session folds.
