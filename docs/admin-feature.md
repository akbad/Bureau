# Admin feature

> **Note:** This document describes the auto-memory system that underpins Bureau Concierge.
> For the full Concierge design (architecture, attachés, scheduler, UX, setup flow), see the
> [design doc](../../think/workbench/workspace/internal/bureau/CONCIERGE.md).

## Main idea

Bureau-native global auto-memory: automatic, GPT-style memory that captures useful things the user tells the agent and feeds them back into future sessions — without requiring manual curation or extra infrastructure.

### Design

The system uses a hybrid storage architecture with three tiers:

```
~/.config/bureau/memory/
├── core.md              ← Always injected into context (like MEMORY.md)
│                          Curated, <200 lines. User prefs, workflow style,
│                          communication preferences, recurring patterns.
│                          Updated by post-run hooks + agent directives.
│
├── topics/              ← Topic-specific deeper notes
│   ├── debugging.md       (referenced from core.md when relevant)
│   ├── code-style.md
│   └── ...
│
└── auto/                ← Auto-captured memories (hook-managed)
    ├── index.jsonl        Timestamped, categorized entries
    └── (managed by Bureau's existing retention system)
```

**Tier 1 — `core.md` (always-present context):**
Small, curated file (< 200 lines) containing the user's most important preferences, workflow patterns, communication style, and recurring needs. Injected into every agent session via a pre-run hook — guaranteed to be present regardless of model compliance. This is the "GPT memory" equivalent: concise enough to always fit in context, valuable enough to materially improve every interaction.

**Tier 2 — `topics/` (depth on demand):**
Topic-specific markdown files for deeper notes that don't belong in the core context but should be accessible when relevant. `core.md` references these by name so agents know what's available and can read them when a task matches. Examples: `debugging.md` (user's preferred debugging workflow), `code-style.md` (project-specific conventions beyond `code-standards.md`), `tools.md` (user's tool preferences and quirks discovered over time).

**Tier 3 — `auto/` (high-volume capture):**
A `index.jsonl` file where post-run hooks automatically append timestamped, categorized entries whenever an agent stores something tagged `user-preference` or `workflow-insight`. This is the raw capture layer — it accumulates everything without filtering. Bureau's existing retention and cleanup system manages lifecycle (TTL, trash, permanent deletion).

### How it works

1. **Pre-run hook** reads `core.md` and injects its contents into the agent's context window. This is guaranteed execution at the system level — no model compliance required. The agent starts every session already knowing the user's preferences.

2. **Post-run hook** checks whether the agent stored anything tagged `user-preference` or `workflow-insight` during the session. If so, it appends the entry to `auto/index.jsonl` with a timestamp and category.

3. **Context directive** in `CLAUDE.template.md` (and `AGENTS.template.md` for other CLIs): instructs agents that before completing a task, if the user expressed a preference or the agent learned something about how to help them better, it should store it with the `user-preference` tag. This is the "soft" ingestion path — it depends on model compliance but is reinforced by the hook layer.

4. **Periodic curation** promotes high-value entries from `auto/` into `core.md` or `topics/`. This can be triggered by:
   - A scheduled task (e.g., weekly review)
   - A manual `/compact-bureau` slash command
   - An agent prompted to "review and consolidate recent auto-memories"

5. **Retrieval at query time**: for the core context, retrieval is implicit (it's already injected). For topics and auto-captured memories, agents can read specific topic files or search `index.jsonl` when a task seems to match a known preference area.

### Why it's optimal

**`core.md` injection is zero-latency, zero-infrastructure, and works offline.** The most critical memories are always present in context without requiring a running MCP server, a database connection, or a network call. This is the single most important design choice: the memories that matter most should have the fewest failure modes.

**Hooks make ingestion automatic and CLI-agnostic.** The current memory protocol relies on directives that agents must choose to follow — and compliance varies (Gemini especially struggles with directive adherence). Hooks execute at the system level regardless of which model or CLI is running. The shift from "protocol directive agents must follow" to "hook that executes automatically" removes the compliance variable entirely.

**It separates the "always-present core" from the "searchable archive."** GPT's memory feature works because it's small and curated. If you dump everything into context, you get noise that degrades model performance. If you only query on demand, you miss things the model doesn't know to search for. The hybrid approach gives you both: a tight core that's always present (catches what the model wouldn't think to search for) plus a deep archive that's queryable when needed (handles the long tail).

**No new infrastructure is required.** The design uses flat files, JSONL, and Bureau's existing retention/cleanup system. No new MCP server, no new database, no new Docker container. The `auto/` tier plugs directly into Bureau's existing `cleanup/handlers/` pattern — it's a natural extension of the architecture, not a bolt-on.

**It leverages Bureau's existing retention and cleanup system for the auto tier.** Entries in `auto/index.jsonl` get the same TTL-based lifecycle management as Qdrant, claude-mem, Memory MCP, and Serena memories. Stale entries move to trash, then get permanently deleted after the grace period. This prevents unbounded growth without manual intervention.

**The topic files provide depth without context bloat.** Instead of cramming everything into `core.md` (which would exceed the 200-line budget and degrade signal-to-noise), deeper notes live in separate files that are loaded only when relevant. The agent knows they exist (referenced in `core.md`) and can pull them in selectively. This is the same pattern as Claude Code's own `MEMORY.md` + topic files design — proven to work well in practice.

**The curation step ensures quality over time.** Raw auto-captured memories are noisy by nature — not everything an agent tags as `user-preference` will be worth keeping. The periodic promotion step (auto → core/topics) acts as a quality filter, ensuring the always-present context stays high-signal. This mirrors how human memory works: short-term capture is broad, long-term retention is selective.
