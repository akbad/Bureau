---
name: fold-dossier
description: Save the current conversation as a Bureau dossier for seamless cross-agent resumption. Activate when user says "fold", "save this conversation", "brain dump", or invokes /fold-dossier. Creates an exhaustive context snapshot at ~/.config/bureau/dossiers/ via the dossier CLI with a SQLite-backed task list for multi-agent collaboration. Outputs a hash for later resumption via /unfold-dossier.
---

# Bureau Fold: save conversation as dossier

> ***Goal:** capture the full state of the current conversation — decisions, reasoning, context, preferences, and tasks — into a portable dossier that any Bureau agent can resume without losing a single insight.*

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

## Dossier identification

All CLI commands that take a dossier identifier accept **two formats**:

| Format | Example | Description |
|:-------|:--------|:------------|
| **Hash** (bare ID) | `1caea7` | The 6-character hex hash shown in the dossier title |
| **Full slug** (name + hash) | `reverb-threats-1caea7` | The complete slug shown in the `**Slug:**` metadata field |

Use **one of these two formats** whenever a CLI command requires a dossier identifier (e.g., the `slug` payload key on re-fold, or the positional `slug` argument for `tasks`). Do **not** use the bare name (e.g., `reverb-threats`) without the hash suffix.

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

For every task, also record **`context_notes`**: the hints a worker agent picking up that task in a fresh session would need and cannot reconstruct from the subject alone. Which file to start in, the approach already ruled out, the test that reproduces the bug. This is the field that makes a task handoff-ready rather than merely named, and it is surfaced verbatim by `bureau-dossiers context --task <id>`.

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

> **Voice:** Write the entire digest in **first person, past tense** — as if leaving a voice memo to yourself. Use "I", "we", "my"; never "the agent" or "the assistant". This is not a report about someone else's work — it is your own memory being recorded for later recall.

You **MUST** include **ALL EIGHT** of the following mandatory aspects. Omitting any single one constitutes a failed fold.

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

#### Mandatory Aspect 6: Session mood

Capture the emotional register and pace of the conversation in **3-5 sentences**. This is not metadata — it is calibration data that lets the resuming agent match the tone and energy of the session from its very first response.

Include:

- The **overall tenor**: was this exploratory, focused, tense, playful, frustrated, triumphant?
- The **user's current state**: patient, impatient, curious, stressed, satisfied?
- The **pacing**: rapid back-and-forth iteration, slow deliberate exploration, mixed?
- The **confidence level**: were we on solid ground or still searching?
- Any **notable shifts** during the session (e.g., "started frustrated but broke through around message 20")

**Example:**
```
This was an intense debugging session — the user was visibly frustrated after 3 failed approaches to the WAL locking issue and wanted fast, concrete answers rather than exploration. Pacing was rapid: short messages, immediate tool calls, no room for preamble. By the end we'd found the root cause and the mood shifted to relief, but the user's patience for verbose explanations was clearly spent. I should resume with directness and confidence, not tentativeness.
```

#### Mandatory Aspect 7: Pinned findings and dead ends

Two categories of information that **must survive every re-fold**. They do survive it: findings accumulate in the dossier for its whole lifetime, so **send only what is new in this session.** Re-sending something already pinned changes nothing, and carrying inherited entries forward is wasted payload.

##### Pinned findings

Facts, discoveries, or constraints that are critical to the project but easy to lose across sessions. Each entry should be a single, self-contained statement that is true regardless of session context.

**Format:** One bullet per finding. Prefix with the session number or date if known.

**Example:**
```
- SQLite WAL mode is required for concurrent agent access — without it, SQLITE_BUSY errors appear under parallel fold/unfold
- The config loader does NOT auto-create missing directories — callers must ensure ~/.config/bureau/ exists
- The user's local.yml overrides default retention to 7d (not the 30d in defaults.yml)
```

##### Dead ends

For every approach explored but **not adopted** during this session, record:

- **What** was tried
- **How far** it got
- **Why** it was abandoned (explicit reason from the user/conversation, or `[inferred]`)
- A **do-not-retry** flag: `[DO NOT RETRY]` or `[CONDITIONAL — retry if X changes]`

**Example:**
```
- Tried using YAML for dossier storage (got as far as a working prototype)
  Why abandoned: [inferred] concurrent writes caused data corruption without locking
  [DO NOT RETRY]
- Explored Redis for task queue (researched only, no code written)
  Why abandoned: user directive — "too much infrastructure for this use case"
  [CONDITIONAL — retry if Bureau adds a daemon process]
```

##### Amending, consolidating, and retracting

Every stored finding has an id, which `unfold` and `context` render as an 8-hex prefix at the start of its line (`- a3f91c2e [dead end: DO NOT RETRY] port 8780 is owned...`, with any free-text `why abandoned:` / `retry:` detail on indented lines beneath it). Findings are never edited or deleted in place — to change what the dossier holds, send a **new** finding whose `supersedes` array names the ids it replaces:

| Situation | What to send |
|:---|:---|
| **Amend** — better wording, or the constraint changed | One new finding, `supersedes` naming the one it replaces |
| **Consolidate** — several entries say one thing | One well-worded finding, `supersedes` naming every entry it retires (no limit) |
| **Retract** — a finding became false and has no successor | A finding with `"kind": "retraction"` whose text is the *reason*, `supersedes` naming the finding it retires |

Two things the CLI will tell you about on stderr, both of which need action from you:

- **A retracted or superseded finding cannot be revived verbatim.** To re-assert one, send it in **new words** — the re-wording is what carries the justification ("port 8780 is owned again as of the 08-20 reinstall"), and re-sending the original text carries none.
- **An id that matches nothing, or matches two findings**, leaves the new finding stored and the retirement undone. Re-send with a corrected or longer id — an ambiguity report prints each candidate's full id, so copy the one you meant from there. Nothing was lost in the meantime.
- **Every value in a finding is text**, apart from the `true`/`false` `dead_end` flag. A number, list, or object in `finding`, `why_abandoned`, or `retry` is reported and that finding is skipped; the rest of the fold still lands.

#### Mandatory Aspect 8: Memory query log

Record every query made to persistent memory systems during this session so the resuming agent can skip redundant retrieval and build on prior results.

For each query, record:

| Field | Description |
|:------|:------------|
| `tool` | The MCP tool used (e.g., `qdrant-find`, `search_nodes`, `read_graph`, `smart_search`) |
| `query` | The search query or parameters |
| `result_summary` | What was found (or "no relevant results") |
| `used_for` | How the result informed a decision or action |

If no memory queries were made, record `No memory queries this session.`

## Dossier assembly and writing

After completing all collection steps, assemble the data and write the dossier using the CLI. The CLI handles all file creation, hash generation, schema setup, and metadata — you never touch the database or write frontmatter directly.

### Step 6: Assemble the JSON input payload

Assemble a single JSON payload containing all structured data collected in Steps 1-5. The digest is inlined directly in the JSON.

You will pass this payload directly to the CLI via stdin. This avoids shared temp files when multiple agents fold concurrently.

```json
{
  "name": "<user-provided name or auto-generated>",
  "agent": "<agent-identifier>",
  "project": "<git repo root path>",
  "branch": "<current branch>",
  "commit": "<short HEAD>",
  "digest": "<the exhaustive brain dump covering ALL EIGHT mandatory aspects>",
  "tasks": [
    {"subject": "Task subject", "status": "pending", "owner": null, "description": "Task description", "blocked_by": null, "context_notes": "Where a worker should start, gotchas, what was already tried"}
  ],
  "decisions": [
    {"what": "What was decided", "why": "Why this option was chosen", "alternatives": "JSON-encoded array of rejected alternatives", "decided_by": "user directive"}
  ],
  "files": [
    {"path": "/absolute/path/to/file.py", "action": "modified", "annotation": "edited lines 40-60"}
  ],
  "last_exchange": "<verbatim last 2-3 turns of conversation: the final user message(s) and your final response(s), unedited>",
  "next_words": "<the first 1-2 sentences of what you were about to say or do next, as if completing a thought mid-sentence>",
  "mood": "<3-5 sentences capturing the session's emotional register, pace, and tone — from Mandatory Aspect 6>",
  "pinned_findings": [
    {"finding": "Self-contained statement of a finding new in this session"},
    {"finding": "Description of a dead end", "dead_end": true, "why_abandoned": "reason", "retry": "DO NOT RETRY"},
    {"finding": "Why the entry it replaces is no longer true", "kind": "retraction", "supersedes": ["a3f91c2e"]}
  ],
  "memory_queries": [
    {"tool": "qdrant-find", "query": "bureau dossier schema", "result_summary": "found 3 entries, all pre-2024", "used_for": "confirmed no existing schema docs"}
  ]
}
```

> [!IMPORTANT]
> **Re-fold vs. new fold behavior:**
>
> - **Which keys change by mode** is specified once, in [Step 7](#step-7-run-the-cli). Do not duplicate that decision here; a re-fold is selected by including the `slug` key, never by a flag.
> - **Pinned findings on re-fold**: send only findings and dead ends that are **new in this session**. They accumulate in the dossier for its whole lifetime, so inherited ones need no carrying forward; to change one that is already there, supersede it (see [Amending, consolidating, and retracting](#amending-consolidating-and-retracting)).

**Field reference:**

| Field | Value |
|---|---|
| `name` | User-provided name from `/fold-dossier "name"`, or auto-generated from conversation topic. Required for new dossiers; **omit when re-folding** — a fold cannot rename a dossier. |
| `slug` | Slug of the dossier to append to. Its presence is what selects re-fold mode; omit it entirely to create a new dossier. |
| `agent` | Identifier of the agent performing the fold: `claude-code`, `codex`, `gemini-cli`, `opencode`, or similar |
| `project` | Absolute path to the git repository root (from `git rev-parse --show-toplevel`) |
| `branch` | Current git branch name |
| `commit` | Short HEAD hash |
| `digest` | The full conversation digest covering all eight mandatory aspects (inlined as a string) |
| `digest_file` | Alternative to `digest`: a path to read the digest from, used only when the digest approaches the 500 KB ceiling. The path **must** resolve inside the dossiers directory (`~/.config/bureau/dossiers/`) or the fold exits 1. Ignored when `digest` is non-empty. |
| `tasks` | Array of task objects from Step 2 |
| `decisions` | Array of decision objects from the conversation (Mandatory Aspect 1) |
| `files` | Array of file interaction objects from Step 3 |
| `last_exchange` | Verbatim last 2-3 conversational turns (final user messages and agent responses). Captures the exact moment of folding for continuity anchoring. |
| `next_words` | The first 1-2 sentences the agent was about to say or the next action it was about to take. Used by unfold to continue mid-thought. |
| `mood` | 3-5 sentences describing the session's emotional register, pace, and tone (Mandatory Aspect 6). |
| `pinned_findings` | Array of findings and dead ends **new in this session** — they accumulate across the dossier's lifetime, so never re-send inherited ones. Dead ends add `dead_end: true`, `why_abandoned` and `retry`. To replace or retire existing entries, add `supersedes`: an array of the 8-hex ids `unfold` renders, with `kind: "retraction"` when the entry became false and has no successor. See [Mandatory Aspect 7](#mandatory-aspect-7-pinned-findings-and-dead-ends). |
| `memory_queries` | Array of memory system queries made during this session, with tool, query, result summary, and how the result was used. |

### Step 7: Run the CLI

Run **one** command, piping the Step 6 payload to stdin. There is a single payload shape; the mode is selected by which keys you include, **not** by a flag.

```bash
bureau-dossiers fold --input-file - << 'ENDJSON'
{ ...the payload assembled in Step 6... }
ENDJSON
```

**Which keys to include, by mode:**

| Key | New dossier | Re-fold |
| :--- | :--- | :--- |
| `slug` | omit | **required** — its presence is what selects re-fold mode |
| `name` | **required** | **omit** — a fold cannot rename a dossier |
| `tasks` | include the full array | **omit** — task state lives in the database and is managed with `tasks add` / `claim` / `complete` |
| `decisions` | every decision from the session | only decisions made in **this** session, never inherited ones |
| `pinned_findings` | every finding and dead end from the session | only findings new in **this** session; supersede an existing one rather than re-sending it |

Everything else (`agent`, `project`, `branch`, `commit`, `digest`, `files`, `last_exchange`, `next_words`, `mood`, `memory_queries`) is sent identically in both modes.

> [!IMPORTANT]
>
> **Read stderr.** Sending a key that this mode ignores, or one the CLI does not recognize, is never fatal — the fold proceeds and warns. A warning on stderr means part of your payload did not land, and it is the only signal you will get.

**What the CLI guarantees**, so you never do any of it yourself:

- **A fold only ever appends.** Re-folding never deletes an earlier session's digest, decisions, or file interactions, so you can fold as often as you like without losing prior context.
- **Identity and storage are the CLI's job.** Hashes, slugs, database creation, and timestamps are all handled for you. See [Explicit prohibitions](#explicit-prohibitions).
- **A failed fold leaves nothing behind.** A non-zero exit does not create a partial dossier and does not modify an existing one, so it is always safe to fix the payload and retry.

### Step 8: Confirm output

On success, relay the CLI's confirmation output **verbatim**, then add the resume line:

```
Resume with `/unfold-dossier <hash>` or `/unfold-dossier <name>`
```

Relay it verbatim rather than reformatting it: the CLI reports what it actually did, and that can include lines this skill does not describe.

If the CLI exits non-zero, report the error clearly and do not retry without changing the payload.

## Explicit prohibitions

- **Do NOT** save the raw conversation transcript — the digest replaces it. Exception: `last_exchange` captures the verbatim final 2-3 turns for continuity anchoring.
- **Do NOT** modify any repository files or git state — dossiers live outside the repo in `~/.config/bureau/dossiers/`
- **Do NOT** auto-lock the dossier — fresh dossiers are always unlocked
- **Do NOT** abbreviate, truncate, or summarize the digest — exhaustive detail is mandatory; if in doubt, include more rather than less
- **Do NOT** include a `name` field in this skill's YAML frontmatter (per Bureau convention — the skill name is derived from the install directory)
- **Do NOT** prompt the user for additional information unless absolutely necessary — use the conversation history and tool outputs to fill in all fields
- **Do NOT** run raw `sqlite3` commands or write YAML frontmatter manually — all database and file operations go through the CLI
- **Do NOT** run `openssl rand` for hash generation — the CLI generates hashes automatically
- **Do NOT** include inherited decisions or already-pinned findings from prior sessions when re-folding — `decisions` and `pinned_findings` carry only what the current session produced

## Task state management during sessions

When working from an unfolded dossier, update task state via the Bureau CLI **as events happen** — do not batch task updates into the fold.

- When you start working on a task: `bureau-dossiers tasks <slug> claim --id <task-id> --agent <your-agent-id>`
- When you complete a task: `bureau-dossiers tasks <slug> complete --id <task-id>`
- When you discover new work: `bureau-dossiers tasks <slug> add --subject "New task"`

This ensures other agents checking the task list see accurate, up-to-date state — even before this session folds.
