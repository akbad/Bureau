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
    show     — render human-readable view (on-demand)

  Backend: SQLite (WAL mode). Bureau-specific.
        │
        ▼
Storage (~/.config/bureau/dossiers/)
  <slug>.db     — all state (single SQLite file)
```

### Key decisions

1. **Single `.db` file per dossier** replaces the split `.md` + `.tasks.db` model.
   No `.md` projection is generated; use `unfold` to render on-demand.

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
    id          INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,
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
    alternatives TEXT,          -- JSON-encoded array of rejected alternatives
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

-- Indexes for pruning and join queries
CREATE INDEX IF NOT EXISTS idx_file_interactions_session
    ON file_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_session
    ON decisions(session_id);
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
# Via CLI flags (good for simple folds):
uv run python -m operations.dossiers fold \
  --name "Dossiers Implementation" \
  --project /path/to/repo \
  --branch feat/concierge \
  --commit 93408be \
  --digest-file /tmp/digest.md \
  --tasks-json '[{"subject":"Wire up pipeline","status":"pending"}]' \
  --decisions-json '[{"what":"Use SQLite","why":"ACID guarantees","decided_by":"user"}]' \
  --files-json '[{"path":"fold/SKILL.md","action":"created"}]'

# Via input file (recommended — avoids shell escaping):
uv run python -m operations.dossiers fold \
  --input-file /tmp/fold-input.json
```

The `--input-file` JSON format:

```json
{
  "name": "Dossiers Implementation",
  "agent": "claude-code",
  "project": "/path/to/repo",
  "branch": "feat/concierge",
  "commit": "93408be",
  "digest": "Full digest text here...",
  "tasks": [{"subject": "Wire up pipeline", "status": "pending"}],
  "decisions": [{"what": "Use SQLite", "why": "ACID guarantees", "decided_by": "user"}],
  "files": [{"path": "fold/SKILL.md", "action": "created"}]
}
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

### `unfold`

Render dossier context to stdout for injection into a fresh agent.

```bash
uv run python -m operations.dossiers unfold <hash-or-name>
uv run python -m operations.dossiers unfold <hash-or-name> --claim --agent claude-code
uv run python -m operations.dossiers unfold <hash-or-name> --fork
uv run python -m operations.dossiers unfold <hash-or-name> --max-sessions 3
```

Flags:
- `--claim --agent <name>`: acquire advisory lock during unfold (single step)
- `--fork`: create an independent copy and unfold the fork
- `--max-sessions N`: limit rendered session digests to the last N (default 5).
  All sessions remain stored; only the rendered output is capped.

Output: full dossier state rendered as markdown (metadata, recent session
digests, task list, all decisions) — ready for context injection.

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

Render human-readable view to stdout (on-demand replacement for the
removed auto-generated `.md` projection).

```bash
uv run python -m operations.dossiers show <slug>
uv run python -m operations.dossiers show <slug> > dossier.md
```

Same rendering as `unfold` but intended for human inspection, not
context injection. Pipe to a file to get the `.md` view when needed.

## Cleanup

Two-level cleanup strategy:

### Level 1: Intra-dossier pruning (automatic during fold)

- `file_interactions` older than `max_retained_sessions` sessions are deleted
- `sessions`, `decisions`, `tasks` are never auto-pruned
- Triggered automatically during each `fold` operation

### Level 2: Whole-dossier retention (periodic cleanup)

- Entire `.db` (plus WAL/SHM sidecars) deleted when `metadata.updated_at`
  exceeds `stale_dossier_days`
- Handled by the existing `DossiersHandler` (updated to scan `*.db` files
  and read `updated_at` from the SQLite `metadata` table)
- During transition: also cleans up legacy `.md` + `.tasks.db` files

### Configuration

```yaml
conversations:
  max_retained_sessions: 5    # prune file_interactions beyond this
  stale_dossier_days: 30      # whole-dossier retention
```

## Migration from legacy format

The old format used `.md` (YAML frontmatter) + `.tasks.db` per dossier.
The new format uses a single `.db` file per dossier.

During the transition period:
1. The cleanup handler scans for **both** `*.db` (new) and `*.md` (legacy) files
2. `unfold` and `list` only read the new `.db` format
3. Legacy dossiers are not auto-migrated — they age out via `stale_dossier_days`
4. No `migrate` command is needed; the old format was short-lived

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
