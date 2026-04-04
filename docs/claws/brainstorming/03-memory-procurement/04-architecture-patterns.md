# Architecture Patterns: Memory Stack Integration

## Context

This document assumes the agent platform recommendation from Task 02: Hermes Agent (primary) or OpenClaw (fallback), with Bureau as the governance/orchestration substrate. The memory platform must integrate into that stack.

## Pattern A: Mem0 as the universal memory layer (recommended)

```
┌───────────��─────────────────────────────────────────┐
│  AGENT PLATFORM (Hermes Agent or OpenClaw)          │
│    ├── Native memory (MEMORY.md, USER.md, FTS5)     │
│    ├── Skill memory (agent-native)                  │
│    └── Session state (SQLite)                       │
│                                                     │
│  MEMORY ENGINE (Mem0 self-hosted)                   │
│    ├── Fact extraction (Ollama LLM)                 │
│    ├── Vector store (Qdrant — shared with Bureau)   │
│    ├── Graph store (Neo4j — entity relations)       │
│    └── MCP server (11 tools)                        │
│                                                     │
│  BUREAU (existing)                                  │
│    ├── Qdrant (semantic retrieval — shared)         │
│    ├── Memory MCP (structural entity-relation)      │
│    └── Dossiers (resumable workstreams)             │
│                                                     │
│  CODING WORKERS                                     │
│    ├── Claude Code (subscription auth)              │
│    └── Codex CLI (device auth)                      │
└─────────────────────────────────────────────────────┘
```

### How it works

1. Agent platform (Hermes/OpenClaw) handles conversations via messaging channels
2. Mem0 MCP server runs alongside — all agents can call `add_memory`, `search_memories`, `search_graph`
3. Mem0 uses the **same Qdrant instance** Bureau already runs (different collection/namespace)
4. Neo4j adds entity-relation graph on top of Qdrant's vector search
5. Agent-native memory (MEMORY.md, skills, FTS5) continues as lightweight always-present context
6. Bureau dossiers continue for workstream-level resumability

### Why this pattern

- **Minimal new infrastructure:** Only adds Neo4j container (Qdrant already exists)
- **No collision:** Mem0, Bureau, and agent-native memory operate on different concerns
- **Shared Qdrant:** Reduces operational overhead
- **MCP integration:** Claude Code and other MCP clients get persistent memory "for free"

### Operational cost

| Component | RAM | Disk | Notes |
|---|---|---|---|
| Qdrant (existing) | ~200MB | Depends on data | Already running |
| Neo4j | ~500MB | ~1GB | New addition |
| Mem0 API server | ~100MB | Minimal | Lightweight FastAPI |
| Ollama (if used for extraction) | 8–16GB | Model-dependent | May already be running for agent platform |

### Risks

- Ollama must be available for fact extraction — if Ollama is down, memory writes fail
- Neo4j adds maintenance burden (backup, disk growth)
- Two entity-relation systems (Neo4j via Mem0 + Memory MCP via Bureau) — need clear ownership boundaries

---

## Pattern B: Mem0 + Graphiti (maximum memory depth)

```
Pattern A + Graphiti temporal layer:

  TEMPORAL LAYER (Graphiti)
    ├── FalkorDB (in-memory graph + vector)
    ├── Temporal fact management (valid_from, valid_to)
    ├── Entity evolution tracking
    └── MCP server
```

### When to use Pattern B

Add Graphiti if you need:
- **"What was true when?"** queries — project timelines, evolving requirements, changing preferences
- **Fact invalidation without deletion** — audit trail of how knowledge changed
- **Point-in-time snapshots** — reconstruct the knowledge state at any past date

### When Pattern A is sufficient

Skip Graphiti if:
- Your memory needs are primarily "what is true now?" (most personal assistant use)
- You don't need temporal audit trails
- You want to minimize infrastructure (FalkorDB is another container)

### Operational cost of adding Graphiti

| Component | RAM | Disk | Notes |
|---|---|---|---|
| FalkorDB | ~200MB | Minimal (in-memory) | New addition |
| Graphiti library | Minimal | N/A | Python library, not a separate server |

---

## Pattern C: Hindsight instead of Mem0 (simplicity-first alternative)

```
┌─────────────────────────────────────────────────────┐
│  AGENT PLATFORM (Hermes Agent or OpenClaw)          │
│    ├── Native memory (MEMORY.md, USER.md, FTS5)     │
│    └── Session state (SQLite)                       │
│                                                     │
│  MEMORY ENGINE (Hindsight)                          │
│    ├── Fact extraction + entity resolution (Ollama) │
│    ├── Embedded PostgreSQL (single container)       │
│    ├── TEMPR 4-strategy retrieval                   │
│    └── MCP server                                   │
│                                                     │
│  BUREAU (existing)                                  │
│    ├── Qdrant (semantic retrieval)                  │
│    ├── Memory MCP (structural entity-relation)      │
│    └── Dossiers (resumable workstreams)             │
└─────────────────────────────────────────────────────┘
```

### Why choose Pattern C over Pattern A

- **Simplest deployment:** One Docker container vs three
- **Highest benchmark accuracy:** 91.4% LongMemEval
- **MIT license:** Most permissive
- **No Neo4j overhead:** Graph traversal is embedded in Hindsight's retrieval engine
- **Local embeddings by default:** No LLM call needed for basic recall

### Why Pattern A (Mem0) is still recommended over Pattern C

- Mem0 has 16x more stars and a much larger ecosystem
- Mem0 has explicit OpenClaw plugin and multiple Claude Code MCP implementations
- Mem0's Neo4j graph is more powerful for explicit entity-relation queries
- Mem0 is more battle-tested in production
- Hindsight is newer and less proven at scale

### When Pattern C wins

Choose Hindsight if:
- You strongly prefer minimal infrastructure (one container)
- MIT license matters
- You don't need explicit entity-relation graph queries
- You want the highest retrieval accuracy out of the box

---

## Pattern D: Bureau-native memory enhancement (no external engine)

```
┌─────────────────────────────────────────────────────┐
│  AGENT PLATFORM (Hermes Agent or OpenClaw)          │
│    ├── MEMORY.md / USER.md (curated by agent)       │
│    ├── SQLite + FTS5 (session search)               │
│    └── Skill documents (learned procedures)         │
│                                                     │
│  BUREAU (enhanced)                                  │
│    ├── Qdrant (semantic retrieval)                  │
│    ├── Memory MCP (structural entity-relation)      │
│    ├── Dossiers (resumable workstreams)             │
│    └── NEW: memory compiler pipeline                │
│         (Bureau-owned fact extraction + promotion)  │
└─────────────────────────────────────────────────────┘
```

### When Pattern D makes sense

If you want to build the memory compiler inside Bureau rather than adopt an external engine. This is the path described in the Task 01 brainstorming (Bureau-native control stack).

### Why it's not recommended as the first move

- Requires significant Bureau development investment
- Mem0/Hindsight are already built, tested, and have MCP servers
- The user's immediate need is a working memory layer, not a Bureau development project
- Can always migrate to Bureau-native later after learning from Mem0/Hindsight in production

---

## Recommendation

**Start with Pattern A** (Mem0 as universal memory layer). It provides the most value with the least risk. After running it for a few months, evaluate whether to:
- Add Graphiti (Pattern B) for temporal reasoning
- Migrate to Hindsight (Pattern C) if Mem0 feels too heavy
- Build Bureau-native memory compiler (Pattern D) if you want full sovereignty

**Key principle:** The memory layer should be a service, not a monolith. All patterns above keep memory as a separate, replaceable component behind an MCP/REST interface. This means you can swap engines without changing the agent platform.
