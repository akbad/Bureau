# Dossiers implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Bureau's cross-agent conversation continuity system — "Dossiers" — with `/bureau-fold` and `/bureau-unfold` slash commands, SQLite-backed task lists, and multi-agent collaboration via fork/claim semantics.

**Architecture:** Two standalone skills (SKILL.md files) installed to all Bureau-supported agents via the existing `set-up-skills.sh` mechanism. Dossier files (markdown + YAML frontmatter) and task list databases (SQLite WAL) stored at `~/.config/bureau/dossiers/`. Config integration via `defaults.yml` and `config_loader.py`. Cleanup integration via a new `DossiersHandler` following the existing `CleanupHandler` ABC pattern.

**Tech stack:** Markdown, YAML frontmatter, SQLite (WAL mode), Python (config loader, cleanup handler), Bash (skill installation)

**Design doc:** `docs/plans/2026-03-08-dossiers-design.md`

**Repository:** `/Users/danielakbarzadeh/code/bureau` (branch: `feat/skills-system`)

> [!IMPORTANT]
>
> The `bureau-concierge` worktree is on `feat/concierge`. Dossier skill files and config changes live in the **main bureau repo** at `/Users/danielakbarzadeh/code/bureau` on `feat/skills-system`. Concierge integration (Phase 5) is the only part that touches `feat/concierge`.

## Phase 1: Skill files

> Tasks 1-2 can run **in parallel** (independent SKILL.md files with no shared dependencies).

### Task 1: Create the fold skill

**Files:**

- Create: `protocols/context/static/skills/fold/SKILL.md`

**Step 1: Create the skill directory**

```bash
mkdir -p /Users/danielakbarzadeh/code/bureau/protocols/context/static/skills/fold
```

**Step 2: Write the SKILL.md**

Create `protocols/context/static/skills/fold/SKILL.md` with the following content.

The YAML frontmatter must contain only a `description` field (no `name` — see `protocols/context/static/skills/README.md` for rationale).

```yaml
---
description: Save the current conversation as a Bureau dossier for seamless cross-agent resumption. Activate when user says "fold", "save this conversation", "brain dump", or invokes /bureau-fold. Creates an exhaustive context snapshot at ~/.config/bureau/dossiers/ with a SQLite-backed task list for multi-agent collaboration. Outputs a hash for later resumption via /bureau-unfold.
---
```

The body must include:

- **Activation section**: trigger phrases and slash command syntax (`/bureau-fold` or `/bureau-fold "name"`)
- **Hard requirements for the conversation digest**: the five non-negotiable aspects from the design doc (full reasoning chains, exact in-flight state, observed preferences, hard-won technical context, unreconstructable mental state) — each with a detailed explanation and the mandate: *"Write as if the reader has zero context and must resume without asking a single clarifying question."*
- **Collection protocol**: step-by-step instructions for the agent to:

    1. Collect git state (`git branch --show-current`, `git rev-parse --short HEAD`, `git rev-parse --show-toplevel`, `git status --porcelain | wc -l`)
    2. Collect task list (dump from native task tools if available; read from existing dossier DB if resuming)
    3. Identify key files (files read, written, or discussed during the session)
    4. Identify active skills invoked during the session
    5. Generate the brain dump following the five mandated aspects
    6. Assemble the dossier file with YAML frontmatter and markdown body

- **File writing protocol**: exact commands for:

    1. Create dossier directory: `mkdir -p ~/.config/bureau/dossiers`
    2. Compute hash: instruct agent to generate a 6-char hex hash from content
    3. Write the dossier markdown file to `~/.config/bureau/dossiers/<slug>.md`
    4. Create the SQLite task DB:

        ```bash
        sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
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
        PRAGMA journal_mode=WAL;
        "
        ```

    5. Populate tasks from collected task state:

        ```bash
        sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
        INSERT INTO tasks (subject, description, status, owner, blocked_by)
        VALUES ('<subject>', '<description>', '<status>', '<owner>', '<blocked_by>');
        "
        ```

- **Output format**: instruct agent to confirm with hash and resumption command
- **Explicit prohibitions**: does NOT save raw transcript, does NOT modify repo files, does NOT auto-lock

**Step 3: Verify skill file is well-formed**

```bash
head -5 /Users/danielakbarzadeh/code/bureau/protocols/context/static/skills/fold/SKILL.md
```

Expected: YAML frontmatter with `---` delimiters and `description` field.

**Step 4: Commit**

```bash
cd /Users/danielakbarzadeh/code/bureau
git add protocols/context/static/skills/fold/SKILL.md
git commit -m "feat(dossiers): add bureau-fold skill for conversation snapshots"
```

### Task 2: Create the unfold skill

**Files:**

- Create: `protocols/context/static/skills/unfold/SKILL.md`

**Step 1: Create the skill directory**

```bash
mkdir -p /Users/danielakbarzadeh/code/bureau/protocols/context/static/skills/unfold
```

**Step 2: Write the SKILL.md**

Create `protocols/context/static/skills/unfold/SKILL.md` with the following content.

```yaml
---
description: Resume a previously saved Bureau dossier or list all saved dossiers. Activate when user says "unfold", "pick up where I left off", "resume", "my dossiers", or invokes /bureau-unfold. Supports hash lookup, fuzzy name matching, fork/claim collaboration, and shared SQLite task lists for multi-agent coordination.
---
```

The body must include:

- **Activation section**: three modes:

    - `/bureau-unfold` (no args) → list mode
    - `/bureau-unfold <hash>` → resume by hash or hash prefix
    - `/bureau-unfold <name>` → fuzzy match on name/slug
    - Flags: `--claim` (lock for exclusive access), `--fork` (create a copy)

- **List mode protocol**: instructions for scanning and displaying dossiers:

    ```bash
    # List all dossier files, sorted by modification time (newest first)
    ls -t ~/.config/bureau/dossiers/*.md 2>/dev/null
    ```

    - Parse YAML frontmatter from each file (hash, name, project, locked_by, updated)
    - Display as lettered table with status indicators
    - Accept letter selection or hash input

- **Resume mode protocol**: step-by-step:

    1. Resolve identifier (exact hash → prefix match → fuzzy slug match on filenames)
    2. Read YAML frontmatter, check `locked_by` field
    3. If locked and no `--fork`: inform user, offer to fork
    4. If `--fork`: create new dossier file with `parent: <original-hash>`, copy task DB
    5. If `--claim`: update `locked_by` and `locked_at` in frontmatter
    6. Read full dossier body
    7. Read task list from SQLite:

        ```bash
        sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
        SELECT id, subject, status, owner, blocked_by FROM tasks ORDER BY id;
        "
        ```

    8. Present dossier content and task list as opening context

- **Context injection directive**: instruct the resuming agent:

    > *You are resuming a conversation from a dossier. Read the entire dossier below. Do NOT re-ask any question that has a decision in the decision log. Do NOT re-explore files listed in key files unless you need to verify something has changed. Pick up from the exact point described in "Pending state".*

- **Task list interaction instructions** (for agents without native task support):

    - How to claim a task:

        ```bash
        sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
        UPDATE tasks SET status='in_progress', owner='<session-id>',
        updated_at=datetime('now') WHERE id=<N>;
        "
        ```

    - How to complete a task:

        ```bash
        sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
        UPDATE tasks SET status='completed', updated_at=datetime('now') WHERE id=<N>;
        "
        ```

    - How to add a task:

        ```bash
        sqlite3 ~/.config/bureau/dossiers/<slug>.tasks.db "
        INSERT INTO tasks (subject, description, status)
        VALUES ('<subject>', '<description>', 'pending');
        "
        ```

    - How to list current tasks:

        ```bash
        sqlite3 -header -column ~/.config/bureau/dossiers/<slug>.tasks.db "
        SELECT id, status, owner, subject FROM tasks WHERE status != 'deleted';
        "
        ```

**Step 3: Verify skill file is well-formed**

```bash
head -5 /Users/danielakbarzadeh/code/bureau/protocols/context/static/skills/unfold/SKILL.md
```

**Step 4: Commit**

```bash
cd /Users/danielakbarzadeh/code/bureau
git add protocols/context/static/skills/unfold/SKILL.md
git commit -m "feat(dossiers): add bureau-unfold skill for dossier resumption and listing"
```

## Phase 2: Configuration

> Tasks 3-4 must run **sequentially** (Task 4 depends on the TypedDict from Task 3).

### Task 3: Add ConversationsConfig to config loader

**Files:**

- Modify: `/Users/danielakbarzadeh/code/bureau/operations/config_loader.py`

**Step 1: Read the current config_loader.py**

Read the file to find the `Config` TypedDict definition (around line 163) and the existing TypedDicts above it.

**Step 2: Add ConversationsConfig TypedDict**

Insert the new TypedDict before the `Config` class definition:

```python
class ConversationsConciergeConfig(TypedDict, total=False):
    auto_offer_resume: bool
    auto_offer_save: bool
    notify_task_updates: bool
    notify_interval: str


class ConversationsConfig(TypedDict, total=False):
    save: str                                   # command verb, default "fold"
    resume: str                                 # command verb, default "unfold"
    storage_dir: str                            # default "~/.config/bureau/dossiers"
    stale_dossier_days: int                     # cleanup threshold, default 30
    concierge: ConversationsConciergeConfig
    keywords: dict[str, list[str]]
```

**Step 3: Add `conversations` to the root Config TypedDict**

```python
class Config(TypedDict, total=False):
    # ... existing fields ...
    conversations: ConversationsConfig
```

**Step 4: Add accessor function**

Add after the existing accessor functions:

```python
def get_conversations_config() -> ConversationsConfig:
    """Get conversations (dossiers) configuration."""
    config = get_config()
    return config.get("conversations", {})
```

**Step 5: Commit**

```bash
cd /Users/danielakbarzadeh/code/bureau
git add operations/config_loader.py
git commit -m "feat(dossiers): add ConversationsConfig to config loader schema"
```

### Task 4: Add conversations defaults to defaults.yml

**Files:**

- Modify: `/Users/danielakbarzadeh/code/bureau/defaults.yml`

**Step 1: Read defaults.yml**

Find the insertion point — after the `assess_mode` section (around line 463) and before `retention_period_for`.

**Step 2: Add conversations config block**

```yaml
# Dossiers: cross-agent conversation continuity
# Fold saves a conversation snapshot; unfold resumes it.
# See docs/plans/2026-03-08-dossiers-design.md for full design.
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

**Step 3: Add dossiers to retention config**

In the `retention_period_for` section, add:

```yaml
retention_period_for:
    claude_mem: 30d
    serena: 90d
    qdrant: 180d
    memory_mcp: 365d
    dossiers: 30d          # matches stale_dossier_days default
```

**Step 4: Add fold and unfold to skills.enabled list**

In the `skills` section, add the new skills:

```yaml
skills:
    enabled: [micro-mode, assess-mode, fold, unfold]
    disabled: []
    sources:
        - path: protocols/context/static/skills
          prefix: bureau-
```

**Step 5: Commit**

```bash
cd /Users/danielakbarzadeh/code/bureau
git add defaults.yml
git commit -m "feat(dossiers): add conversations config and enable fold/unfold skills"
```

## Phase 3: Cleanup integration

### Task 5: Create dossiers cleanup handler

**Files:**

- Create: `/Users/danielakbarzadeh/code/bureau/operations/cleanup/handlers/dossiers.py`
- Modify: `/Users/danielakbarzadeh/code/bureau/operations/cleanup/core.py` (register handler)

**Step 1: Read the base handler and serena handler for reference**

```bash
cat /Users/danielakbarzadeh/code/bureau/operations/cleanup/handlers/base.py
cat /Users/danielakbarzadeh/code/bureau/operations/cleanup/handlers/serena.py
```

**Step 2: Create dossiers cleanup handler**

Create `/Users/danielakbarzadeh/code/bureau/operations/cleanup/handlers/dossiers.py`:

```python
"""Cleanup handler for Bureau dossiers.

Manages retention of conversation dossier files (.md) and their associated
task list databases (.tasks.db) in ~/.config/bureau/dossiers/.

Design rationale:
# Dossiers are paired files: a markdown snapshot and a SQLite task DB.
# Both must be cleaned up together -- orphaned task DBs or headless
# markdown files are both invalid states.
# Retention is based on the dossier's 'updated' frontmatter timestamp,
# not filesystem mtime, to respect logical activity over file access.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import CleanupHandler


class DossiersHandler(CleanupHandler):
    """Cleanup handler for Bureau dossier files and task databases."""

    name = "dossiers"

    def __init__(self) -> None:
        self.dossiers_dir = Path(
            os.path.expanduser("~/.config/bureau/dossiers")
        )

    def get_stale_items(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Return dossiers older than cutoff based on frontmatter 'updated' field."""
        if not self.dossiers_dir.is_dir():
            return []

        stale = []
        for md_file in self.dossiers_dir.glob("*.md"):
            updated = self._parse_updated(md_file)
            if updated and updated < cutoff:
                # Pair with task DB if it exists
                task_db = md_file.with_suffix(".tasks.db")
                stale.append({
                    "path": str(md_file),
                    "task_db": str(task_db) if task_db.is_file() else None,
                    "updated": updated.isoformat(),
                    "size": md_file.stat().st_size,
                })
        return stale

    def export_items_to_trash(
        self, items: list[dict[str, Any]], retention: str
    ) -> str:
        """Move stale dossier files (and their task DBs) to trash."""
        from ..trash import move_to_trash

        paths = []
        for item in items:
            paths.append(item["path"])
            if item.get("task_db"):
                paths.append(item["task_db"])
                # Also grab WAL and SHM files if present
                for suffix in (".tasks.db-wal", ".tasks.db-shm"):
                    wal = Path(item["path"]).with_suffix(suffix)
                    if wal.is_file():
                        paths.append(str(wal))

        return move_to_trash(paths, self.name, retention)

    def delete_items_from_storage(
        self, items: list[dict[str, Any]]
    ) -> int:
        """Count items moved (files already relocated by export_items_to_trash)."""
        return len(items)

    def _wipe(self, backup: bool) -> dict[str, Any]:
        """Wipe all dossiers."""
        if not self.dossiers_dir.is_dir():
            return {"storage": self.name, "wiped": 0}

        files = list(self.dossiers_dir.iterdir())
        count = 0
        if backup:
            from ..trash import move_to_trash
            move_to_trash(
                [str(f) for f in files], self.name, "backup"
            )
        else:
            for f in files:
                f.unlink(missing_ok=True)
        count = len(files)
        return {"storage": self.name, "wiped": count}

    @staticmethod
    def _parse_updated(md_file: Path) -> datetime | None:
        """Extract 'updated' timestamp from YAML frontmatter."""
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            return None

        # Simple frontmatter extraction (between --- delimiters)
        match = re.search(
            r"^---\s*\n(.*?)\n---", text, re.DOTALL
        )
        if not match:
            return None

        # Find 'updated:' line in frontmatter
        for line in match.group(1).splitlines():
            if line.strip().startswith("updated:"):
                value = line.split(":", 1)[1].strip().strip("'\"")
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    return None
        return None
```

**Step 3: Read core.py to find handler registration point**

Read `/Users/danielakbarzadeh/code/bureau/operations/cleanup/core.py` and find where handlers are imported and registered.

**Step 4: Register the dossiers handler**

Add the import and registration following the pattern of existing handlers (e.g., `SerenaHandler`, `QdrantHandler`).

**Step 5: Commit**

```bash
cd /Users/danielakbarzadeh/code/bureau
git add operations/cleanup/handlers/dossiers.py operations/cleanup/core.py
git commit -m "feat(dossiers): add cleanup handler for stale dossier retention"
```

## Phase 4: Installation and verification

### Task 6: Verify skill installation works

**Files:**

- Read: `/Users/danielakbarzadeh/code/bureau/protocols/scripts/set-up-skills.sh`

**Step 1: Run the skill installation script in dry-run mode (if supported)**

```bash
cd /Users/danielakbarzadeh/code/bureau
bash protocols/scripts/set-up-skills.sh --dry-run
```

If no dry-run mode, inspect the script to confirm it will discover `fold/` and `unfold/` directories and create `bureau-fold` and `bureau-unfold` symlinks.

**Step 2: Run the installation**

```bash
cd /Users/danielakbarzadeh/code/bureau
bash protocols/scripts/set-up-skills.sh
```

**Step 3: Verify symlinks were created**

```bash
ls -la ~/.claude/skills/bureau-fold/
ls -la ~/.claude/skills/bureau-unfold/
```

Expected: symlinks pointing to `protocols/context/static/skills/fold` and `unfold`.

**Step 4: Verify skill appears in Claude Code**

```bash
# The skill should be listed when Claude Code starts
# Check by looking at the skills directory
cat ~/.claude/skills/bureau-fold/SKILL.md | head -5
cat ~/.claude/skills/bureau-unfold/SKILL.md | head -5
```

**Step 5: Manual smoke test**

Start a fresh Claude Code session and invoke `/bureau-fold "test dossier"`. Verify:

- Dossier file created at `~/.config/bureau/dossiers/test-dossier-<hash>.md`
- Task DB created at `~/.config/bureau/dossiers/test-dossier-<hash>.tasks.db`
- YAML frontmatter is well-formed
- Digest section is exhaustive
- Output shows hash and resumption command

Then invoke `/bureau-unfold <hash>`. Verify:

- Dossier content is loaded and presented
- Agent picks up context without re-asking decided questions
- Task list is readable

**Step 6: Commit any fixes**

```bash
cd /Users/danielakbarzadeh/code/bureau
git add -A
git commit -m "fix(dossiers): address issues found during smoke test"
```

## Phase 5: Concierge integration (future)

> [!NOTE]
>
> This phase is **blocked by** the Concierge pipeline orchestrator (task #37) and Telegram bot integration (task #42). It is documented here for completeness but should not be implemented until those prerequisites are in place.

### Task 7: Add fold/unfold keywords to classifier config

**Files:**

- Modify: `/Users/danielakbarzadeh/code/bureau-concierge/concierge/config/defaults/classifier.yml`

Add fold/unfold verbs to the fuzzy command verb list so the classifier routes them to `COMMAND` class.

### Task 8: Add dossier-aware proactive behaviors

**Files:**

- Create: `/Users/danielakbarzadeh/code/bureau-concierge/concierge/features/dossiers.py`
- Create: `/Users/danielakbarzadeh/code/bureau-concierge/concierge/tests/test_dossiers.py`

Implement:

- `check_for_resumable_dossiers(project_path)` — scans `~/.config/bureau/dossiers/` for recent dossiers matching the project
- `build_resume_keyboard(dossiers)` — creates quick-reply buttons for dossier selection
- `should_offer_save(session_state)` — heuristic for when to proactively suggest folding (conversation length, elapsed time, milestone detection)

### Task 9: Add task update notifications

**Files:**

- Create: `/Users/danielakbarzadeh/code/bureau-concierge/concierge/background/dossier_watcher.py`

Implement a background check that polls the active dossier's task DB for changes and notifies the user over Telegram when another agent updates a task.

## Parallelization summary

```
Phase 1: Task 1 (fold skill) ─────────┐
         Task 2 (unfold skill) ────────┤── parallel
                                       │
Phase 2: Task 3 (config TypedDict) ────┤── sequential (3 before 4)
         Task 4 (defaults.yml) ────────┤
                                       │
Phase 3: Task 5 (cleanup handler) ─────┤── parallel with Phase 1-2
                                       │
Phase 4: Task 6 (install + verify) ────┘── after all above

Phase 5: Tasks 7-9 (Concierge) ──── blocked by tasks #37 and #42
```

**Maximum parallelism for Phases 1-3:** 3 agents (fold skill, unfold skill, cleanup handler). Config changes (Phase 2) are small enough for a single sequential agent.
