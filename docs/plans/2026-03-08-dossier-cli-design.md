# Dossier CLI design

> Approved design for the Bureau dossier CLI — a deterministic Python backend
> that replaces raw sqlite3/frontmatter commands in the fold/unfold skills.

## Problem

The current fold/unfold skills instruct agents to write raw `sqlite3` CLI
commands with heredocs and hand-craft YAML frontmatter. This is fragile:
shell escaping issues, no input validation, schema drift, and every agent
must know the exact SQL and frontmatter format.

## Architecture

```
Skills (SKILL.md)
  fold / unfold — agent-facing protocol
  Calls CLI commands, never touches DB directly
        │
        │ shell commands
        ▼
CLI (Python, operations.dossiers)
  uv run python -m operations.dossiers <cmd>

  Commands:
    fold     — create/update dossier
    unfold   — render dossier for context injection
    tasks    — CRUD on task list
    list     — list all dossiers
    lock     — claim/release advisory lock
    fork     — create independent copy
    show     — render human-readable view

  Backend: SQLite (WAL mode). Bureau-specific.
        │
        ▼
Storage (~/.config/bureau/dossiers/)
  <slug>.db     — all state (single SQLite file)
  <slug>.md     — rendered projection (optional)
```

### Key decisions

1. **Single `.db` file per dossier** replaces the split `.md` + `.tasks.db` model.
   The `.md` becomes a generated view, not a source of truth.

2. **All agent I/O goes through the CLI.** Skills never run `sqlite3`, write
   frontmatter, or touch the DB directly.

3. **Dossiers are Bureau-specific, not a Vinyl precursor.** Vinyl (Reverb's Rust
   MCP server) is a memory system (what was learned). Dossiers are a work-stream
   management system (what's being worked on). They're independent, with optional
   future integration: fold can push digests to Vinyl via `store_observation`,
   unfold can pull related memories via `retrieve_memories`.

4. **Dossiers are core Bureau, not concierge-specific.** Any Bureau-configured
   agent can fold/unfold. The concierge may optionally suggest fold/unfold, but
   the system works independently.

## SQLite schema

One `.db` file per dossier. All tables in a single database, WAL mode.

```sql
PRAGMA journal_mode=WAL;

-- Metadata (single row, updated on each fold)
CREATE TABLE metadata (
    hash        TEXT NOT NULL,
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL,
    created_at  TEXT NOT NULL,  -- ISO 8601
    updated_at  TEXT NOT NULL,
    agent       TEXT,
    project     TEXT,
    branch      TEXT,
    commit_hash TEXT,
    parent      TEXT,           -- hash of parent dossier (if re-fold)
    locked_by   TEXT,
    locked_at   TEXT
);

-- Session digests (one row per fold — append-only)
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    folded_at   TEXT NOT NULL,
    agent       TEXT NOT NULL,
    branch      TEXT,
    commit_hash TEXT,
    digest      TEXT NOT NULL   -- full conversation digest markdown
);

-- Tasks (mutable, cross-session)
CREATE TABLE tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject     TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    owner       TEXT,
    blocked_by  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Decisions (append-only, cross-session)
CREATE TABLE decisions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id),
    what        TEXT NOT NULL,
    why         TEXT NOT NULL,
    alternatives TEXT,          -- JSON array of rejected alternatives
    decided_by  TEXT,           -- "user directive", "agent recommendation", etc.
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- File interactions (append-only, per session — auto-pruned)
CREATE TABLE file_interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id),
    file_path   TEXT NOT NULL,
    action      TEXT NOT NULL,  -- "created", "modified", "read", "discussed"
    annotation  TEXT
);
```

### Table semantics

- **`sessions`**: Append-only. Each fold adds a row. The digest accumulates
  over the dossier's lifetime.
- **`tasks`**: Mutable. Multiple agents can update task status across sessions.
- **`decisions`**: Append-only. Linked to the session that made them.
- **`metadata`**: Single row. Updated on each fold with latest git state and
  timestamps.
- **`file_interactions`**: Append-only per session, but auto-pruned during fold
  to keep only the last N sessions' worth.

## CLI commands

```
uv run python -m operations.dossiers <command> [options]
```

### `fold`

Create or update a dossier. Accepts structured JSON input for all fields.
The agent writes the digest as free-form text; everything else is validated JSON.

```bash
uv run python -m operations.dossiers fold \
  --name "Dossiers Implementation" \
  --project /path/to/repo \
  --branch feat/concierge \
  --commit 93408be \
  --digest-file /tmp/digest.md \
  --tasks-json '[{"subject":"Wire up pipeline","status":"pending"}]' \
  --decisions-json '[{"what":"Use SQLite","why":"ACID guarantees","decided_by":"user"}]' \
  --files-json '[{"path":"fold/SKILL.md","action":"created"}]'
```

For existing dossiers (re-fold):

```bash
uv run python -m operations.dossiers fold \
  --slug dossiers-implementation-a7f3c2 \
  --digest-file /tmp/digest.md \
  --files-json '[...]'
```

Output: `Dossier saved: <slug> (<N> tasks, <M> decisions)`

During fold, the CLI automatically:
1. Prunes `file_interactions` older than `max_retained_sessions`
2. Updates `metadata.updated_at`
3. Regenerates the `.md` projection

### `unfold`

Render dossier context to stdout for injection into a fresh agent.

```bash
uv run python -m operations.dossiers unfold <hash-or-name>
uv run python -m operations.dossiers unfold <hash-or-name> --claim --agent claude-code
uv run python -m operations.dossiers unfold <hash-or-name> --fork
```

Output: full dossier state rendered as markdown (metadata, latest session
digest, task list, recent decisions) — ready for context injection.

### `list`

List all dossiers.

```bash
uv run python -m operations.dossiers list
uv run python -m operations.dossiers list --format json
```

### `tasks`

Task CRUD for a specific dossier.

```bash
uv run python -m operations.dossiers tasks <slug> list
uv run python -m operations.dossiers tasks <slug> add --subject "Wire up pipeline" --status pending
uv run python -m operations.dossiers tasks <slug> update --id 3 --status completed
uv run python -m operations.dossiers tasks <slug> remove --id 5
```

### `lock`

Advisory lock management.

```bash
uv run python -m operations.dossiers lock <slug> claim --agent claude-code
uv run python -m operations.dossiers lock <slug> release
```

### `fork`

Create independent copy.

```bash
uv run python -m operations.dossiers fork <slug> --name "my fork"
```

### `show`

Render human-readable view to stdout.

```bash
uv run python -m operations.dossiers show <slug>
```

## Cleanup

Two-level cleanup strategy:

### Level 1: Intra-dossier pruning (automatic during fold)

- `file_interactions` older than `max_retained_sessions` sessions are deleted
- `sessions`, `decisions`, `tasks` are never auto-pruned
- Triggered automatically during each `fold` operation

### Level 2: Whole-dossier retention (periodic cleanup)

- Entire `.db` + `.md` deleted when `metadata.updated_at` exceeds
  `stale_dossier_days`
- Handled by the existing `DossiersHandler` (updated to scan `*.db` files
  and read `updated_at` from the SQLite `metadata` table)

### Configuration

```yaml
conversations:
  max_retained_sessions: 5    # prune file_interactions beyond this
  stale_dossier_days: 30      # whole-dossier retention
```

## Protocol updates

### tools-guide.md

Add new section between Memory and Code analysis:

```markdown
## Dossier (work-stream state)

- For saving conversation state: `uv run python -m operations.dossiers fold`
- For resuming a work-stream: `uv run python -m operations.dossiers unfold <hash>`
- For task coordination: `uv run python -m operations.dossiers tasks <slug> <subcommand>`

Dossiers track active work-stream state (tasks, decisions, context).
Memory tools (Qdrant/Memory MCP) track distilled knowledge.
Store insights in BOTH when appropriate.
```

### CLAUDE.template.md

Add to Context Management Protocol:

```markdown
For conversation handoff: Use /bureau-fold to save work-stream state,
then resume in a fresh agent with /bureau-unfold.
Preserves full fidelity — superior to context compaction.
```

### claude-mem removal

Remove all claude-mem references from `tools-guide.md` and
`CLAUDE.template.md`. The memory stack becomes three tiers:

| Tier | Tool | Purpose |
|------|------|---------|
| Distilled knowledge | Qdrant MCP | Patterns, solutions, gotchas |
| Entity relationships | Memory MCP | Architecture, dependencies |
| Work-stream state | Dossiers CLI | Tasks, decisions, digests, handoff |

## Relationship to Reverb Vinyl

Dossiers and Vinyl are complementary, not competing:

- **Vinyl**: Automatic ambient memory (what was learned). Rust MCP server with
  composite scoring, multi-sector memory, bi-temporal KG.
- **Dossiers**: Explicit work-stream state (what's being worked on). Python CLI
  with SQLite backend.

Optional future integration when Vinyl ships:
- `fold` can push session digests to Vinyl via `store_observation(sector="episodic")`
- `unfold` can pull related memories via `retrieve_memories` to enrich context
- Core dossier functionality (tasks, locks, fork) stays in its own SQLite DB
