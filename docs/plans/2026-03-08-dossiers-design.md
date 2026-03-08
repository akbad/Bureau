# Dossiers: cross-agent conversation continuity

> **Created:** 2026-03-08
> **Status:** approved design, pending implementation plan
> **Scope:** Bureau-wide feature (all supported agents + Concierge/Telegram)

## Overview

- Dossiers are Bureau's mechanism for **saving, resuming, and sharing conversation state** across agents, sessions, and interfaces
- A dossier captures an exhaustive brain dump of a conversation — decisions, reasoning chains, technical context, in-flight state, user preferences — paired with a **live, agent-agnostic task list** backed by SQLite
- Two slash commands expose the feature: `/bureau-fold` (save) and `/bureau-unfold` (resume/list)
- Concierge (Telegram) provides equivalent access via keyword triggers and proactive inline buttons

## Motivation

- Claude Code's context compaction loses nuance; `/clear` and new terminals lose everything
- Task lists are session-scoped — they die with the session
- Multiple agents working on the same project have no shared coordination layer
- The Concierge needs a way to offer conversation continuity over Telegram without slash commands

Dossiers solve all four by creating a **persistent, agent-agnostic, lockable conversation record** with a living task list that multiple agents can collaborate on simultaneously.

## Architecture

### Two-file model

Each dossier consists of two files in `~/.config/bureau/dossiers/`:

- **`<slug>.md`** — the dossier itself

    - Markdown with YAML frontmatter
    - Contains the brain dump: structured state + exhaustive conversation digest
    - **Session-locked**: one agent claims it for the duration of a session, or other agents fork it
    - Written once on fold, read on unfold

- **`<slug>.tasks.db`** — the collaborative task list

    - SQLite database (WAL mode)
    - ACID transactions for concurrent multi-agent access
    - **Fleetingly locked**: lock held only for the duration of each read-modify-write operation (milliseconds)
    - Updated continuously by any agent working from this dossier

### Why this split

- The dossier file is the **immutable context** — rich, detailed, human-readable, written once
- The task list is the **mutable coordination layer** — frequently updated, concurrently accessed, requires transactional guarantees
- Flat-file locking cannot guarantee safety for concurrent task list writes (TOCTOU races, crash-truncation, stale locks). SQLite provides ACID guarantees with zero lock management code.
- The dossier itself has no concurrency concern (written once, read many), so markdown is the right format for maximum readability and portability

## Dossier file format

```yaml
---
hash: a7f3c2
name: "concierge code review"
slug: concierge-code-review-a7f3c2
created: 2026-03-08T14:32:00+00:00
updated: 2026-03-08T14:32:00+00:00
agent: claude-code
project: /Users/danny/code/bureau-concierge
branch: feat/concierge
commit: 74057a7
parent: null          # hash of parent dossier if forked
locked_by: null       # agent session ID when claimed
locked_at: null
---

## Task state

<current task list rendered as markdown at time of fold>

## Decision log

<chronological list of every decision made, with reasoning>

## Pending state

<exact in-flight state: what was last done, what's expected next>

## Key files

<files read, written, or discussed during the session>

## Conversation digest

<exhaustive brain dump — see digest requirements below>
```

- **Hash**: 6-char hex from `hashlib.sha256(content + timestamp)`
- **Slug**: `<user-name-or-auto-slug>-<hash>`
- **Parent**: enables fork tracking (links to the dossier this was forked from)
- **Lock state**: `locked_by` and `locked_at` live in frontmatter; agents check before writing

## Conversation digest requirements

> [!IMPORTANT]
>
> The conversation digest is the core value of a dossier. It must be written as if the reader has **zero context** and must resume the conversation **without asking a single clarifying question**. The cost of redundancy is zero; the cost of a missing insight is re-doing the entire conversation.

**Non-negotiable — the digest must include ALL of the following:**

1. **Full reasoning chains** — for every decision made, capture *why* this option was chosen over alternatives

    - Include the alternatives that were rejected and the rationale for rejection
    - If the decision was made quickly or implicitly, reconstruct the reasoning

2. **Exact in-flight state** — what was the last action taken, what is expected next, what question is pending, what subagents are running or recently completed

    - The resuming agent must know *precisely* where to pick up
    - Include any partial results, intermediate findings, or half-formed hypotheses

3. **Observed user preferences and patterns** — communication style, workflow preferences, tool choices, recurring instructions

    - Examples: "user prefers worktree isolation over sequential agents", "user says '>' to advance in micro mode", "user wants parallel agent teams whenever possible"
    - Anything that would take multiple interactions to re-learn

4. **Hard-won technical context** — architecture relationships, gotchas encountered, workarounds applied, performance characteristics, dependency quirks

    - Anything that took significant investigation or trial-and-error to derive
    - Include specific file paths, line numbers, function names where relevant

5. **Unreconstructable mental state** — the mental model of how components connect, trade-offs currently being weighed, hypotheses being tested

    - Context that exists *only* in the conversation and cannot be recovered from files alone
    - The "why behind the why" — not just what was decided, but the thought process that led there

## Task list schema

SQLite database at `~/.config/bureau/dossiers/<slug>.tasks.db`:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    owner TEXT,
    blocked_by TEXT,        -- JSON array of task IDs, e.g. '[1, 3]'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- status: 'pending' | 'in_progress' | 'completed' | 'deleted'
-- owner: agent session identifier (e.g. 'claude-code-session-a7f3')
-- blocked_by: tasks that must complete before this one can start
```

**Concurrency model:**

- SQLite WAL mode enables concurrent readers with serialized writers
- No application-level locking needed — SQLite handles it
- Each agent opens its own connection with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`
- Writes are atomic transactions: `BEGIN; UPDATE ...; COMMIT;`

**For agents without native Python/SQLite:**

- The skill prompt teaches agents to interact via the `sqlite3` CLI, which is available on every macOS/Linux system
- Example: `sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "UPDATE tasks SET status='in_progress', owner='my-session' WHERE id=3;"`

## `/bureau-fold` skill

### Activation

- Slash command: `/bureau-fold` or `/bureau-fold "my name for this"`
- Concierge keywords: "save this", "fold this", "brain dump"

### Behavior

1. **Collect structured state**

    - Git: current branch, HEAD commit, repo root, dirty file count
    - Task list: dump all tasks with status (from native task tools if available, or from an existing dossier's SQLite DB)
    - Active skills: which skills were invoked during this session
    - Key files: files read, written, or discussed

2. **Generate the brain dump**

    - Follow the five non-negotiable digest requirements above
    - The skill prompt *mandates* this depth — agents cannot abbreviate or summarize

3. **Compute hash and write files**

    - Hash: `hashlib.sha256((content + iso_timestamp).encode()).hexdigest()[:6]`
    - Slug: `<user-name-or-auto-generated>-<hash>`
    - Write dossier to `~/.config/bureau/dossiers/<slug>.md`
    - Create task list DB at `~/.config/bureau/dossiers/<slug>.tasks.db`
    - Populate tasks table from the collected task state
    - Create the dossiers directory if it doesn't exist

4. **Confirm to user**

    - Output: *"Dossier saved: `concierge-review-a7f3c2`. Resume with `/bureau-unfold a7f3c2`"*
    - Concierge: render as quick-reply confirmation

### What fold does NOT do

- Does not save raw conversation transcript
- Does not modify repo files or git state
- Does not auto-lock the dossier (fresh dossiers are unlocked)

## `/bureau-unfold` skill

### Activation

- `/bureau-unfold a7f3c2` — resume by hash or hash prefix
- `/bureau-unfold concierge-review` — fuzzy match on name/slug
- `/bureau-unfold` (no args) — list saved dossiers
- Concierge keywords: "pick up where I left off", "unfold", "my dossiers", "saved conversations"

### List mode (no args)

- Scan `~/.config/bureau/dossiers/*.md`, parse YAML frontmatter
- Display sorted by most recent:

    ```
    Saved dossiers:

    a) a7f3c2  concierge-code-review      feat/concierge   2h ago    unlocked
    b) b3e91d  mcp-schema-brainstorm      main             3d ago    claimed by codex
    c) f82a01  logging-overhaul           feat/logging     1w ago    unlocked

    Resume with /bureau-unfold <hash> or pick a letter.
    ```

- Concierge: render as inline keyboard buttons

### Resume mode (with hash or name)

1. **Resolve identifier** — exact hash → hash prefix → fuzzy slug match. If ambiguous, show candidates and ask.

2. **Check lock state**

    - Unlocked → proceed; optionally `--claim` to lock for exclusive updates
    - Locked by another agent → offer to fork: *"This dossier is claimed by a codex session. Fork it?"*
    - `--fork` flag → always fork regardless of lock state

3. **Load and inject context**

    - Read the full dossier file
    - Read current task list from the SQLite DB
    - Present both to the agent as opening context
    - Instruct the agent:

        > *You are resuming a conversation from a dossier. Read the entire dossier below. Do NOT re-ask any question that has a decision in the decision log. Do NOT re-explore files listed in key files unless you need to verify something has changed. Pick up from the exact point described in "Pending state". Your task list is at `~/.config/bureau/dossiers/<slug>.tasks.db` — read it for current work items.*

4. **Claim or fork**

    - `--claim`: set `locked_by` and `locked_at` in dossier frontmatter
    - `--fork`: create new dossier with `parent: <original-hash>`, new hash, own task DB (copied from parent)
    - Default (no flag): read-only resume, no lock acquired. Agent can read the shared task list but the dossier itself is not locked.

### Auto-offer at session start (Concierge only)

- On Telegram session start, check for dossiers matching current project (< 7 days old)
- If found, offer quick-reply: *"You have a saved conversation about [name]. Want to pick it up?"*

## Concierge integration

### Keyword detection

- Add fold/unfold verbs to `classifier.yml`'s fuzzy command list
- The classifier pipeline routes these to `COMMAND` class
- Concierge maps the command to the appropriate dossier operation

### Keyword → action mapping

| User says | Action |
|-----------|--------|
| "save this", "fold this", "brain dump" | Fold (create dossier) |
| "pick up where I left off", "resume", "unfold" | Unfold (resume dossier) |
| "my dossiers", "saved conversations" | List dossiers |
| "go back to [name]" | Unfold with fuzzy match on name |

### Proactive behaviors

- **Session start**: offer to resume if recent dossiers exist for the project
- **Context pressure**: suggest folding when conversation is getting long and rich
- **Farewell**: offer to fold when user says goodbye/done
- **Task updates**: when an agent (in any terminal) updates the shared task list, Concierge can notify over Telegram: *"Codex just completed: Wire up pipeline orchestrator"*

## Configuration

Addition to Bureau's `directives.yml` / `defaults.yml`:

```yaml
conversations:
    save: fold
    resume: unfold
    storage_dir: ~/.config/bureau/dossiers
    stale_dossier_days: 30
    concierge:
        auto_offer_resume: true
        auto_offer_save: true
        notify_task_updates: true
        notify_interval: 30s
    keywords:
        save:
            - "save this"
            - "fold this"
            - "brain dump"
        resume:
            - "pick up where I left off"
            - "resume"
            - "unfold"
            - "my dossiers"
            - "saved conversations"
```

- **`save` / `resume`**: control the slash command names (`/bureau-<verb>`)
- **`storage_dir`**: allows relocating dossiers (e.g., to a synced folder for multi-machine use)
- **`stale_dossier_days`**: integrates with Bureau's existing cleanup handlers
- **`keywords`**: user-customizable Concierge trigger phrases

## Skill installation

- Two skill directories: `fold/SKILL.md` and `unfold/SKILL.md`
- Installed via Bureau's existing `set-up-skills.sh` to all supported agents:

    - Claude Code: `~/.claude/skills/bureau-fold/`, `~/.claude/skills/bureau-unfold/`
    - Codex: `~/.agents/skills/bureau-fold/`, `~/.agents/skills/bureau-unfold/`
    - Gemini CLI: `~/.gemini/skills/bureau-fold/`, `~/.gemini/skills/bureau-unfold/`
    - OpenCode: `~/.config/opencode/skill/bureau-fold/`, `~/.config/opencode/skill/bureau-unfold/`

- Command name customization (`conversations.save` / `conversations.resume` in config) is applied at install time by `set-up-skills.sh`, which renames the install directories accordingly

## Design decisions

- **Markdown over JSON for dossier files** — human-readable, editable, inspectable with any tool. The brain dump section benefits enormously from prose formatting.
- **SQLite over flat-file for task lists** — concurrent multi-agent writes require ACID guarantees. Flat-file advisory locking has known TOCTOU races (we fixed one in `concierge/background/lockfile.py` during this session).
- **Fork-by-default over lock-by-default** — forking is the safe operation (no coordination overhead). Claiming is opt-in for agents that genuinely need to update the original dossier in place.
- **Global storage over per-project** — dossiers are about *conversations*, not codebases. A single conversation may span multiple repos. Global storage with project metadata in frontmatter enables cross-project discovery.
- **Two skills over one** — fold and unfold have distinct UX, distinct activation triggers, and distinct complexity. A single skill would need branching logic that's harder to maintain and test.
- **"Dossier"** — evokes a comprehensive file/record, aligning with the exhaustive brain-dump philosophy. "Fold/unfold" metaphor: fold the conversation into a compact record, unfold it to resume.
