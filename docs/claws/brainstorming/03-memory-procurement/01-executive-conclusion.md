# Executive Conclusion: Memory Platform Procurement

## The answer

**Mem0** is the best memory platform for your setup. Deploy it self-hosted with Qdrant + Neo4j + Ollama, zero API keys, and connect it to your Hermes Agent / OpenClaw / Bureau stack via its MCP server.

No other platform matches Mem0's combination of:
- fully self-hostable with zero API keys (Ollama for LLM + embeddings)
- production-grade graph memory (Neo4j or **Kuzu embedded** — zero-infrastructure graph DB, like SQLite for graphs)
- semantic vector memory (Qdrant server or **Qdrant local file mode** — no server needed)
- 11-tool MCP server that integrates directly with Claude Code
- existing OpenClaw plugin (`openclaw-mem0`)
- auto-use of Claude Code's session token (reads `~/.claude/.credentials.json`) when you want frontier model quality without managing a separate API key
- 48K+ GitHub stars, Apache 2.0 license, YC-backed, mature ecosystem

## The layered answer

If you want more than just Mem0, the optimal memory stack is:

| Layer | Platform | What it provides |
|---|---|---|
| **Core memory engine** | **Mem0** (self-hosted) | Fact extraction, entity-relation graphs, semantic retrieval, memory compression |
| **Temporal knowledge graph** | **Graphiti** (optional) | Time-aware facts with validity windows, entity evolution over time |
| **Existing Bureau memory** | **Qdrant + Memory MCP** (keep) | Semantic retrieval + structural entity-relation memory (already deployed) |
| **Agent-native memory** | **Hermes MEMORY.md / SQLite+FTS5** (keep) | Session search, skill memory, user profile — lightweight, always-on |

Mem0 replaces nothing in your existing Bureau stack — it layers on top as a dedicated memory extraction and retrieval service. Qdrant can even be shared between Bureau and Mem0 (Mem0 supports Qdrant natively as a vector backend).

## What about Honcho?

Honcho has the most sophisticated user modeling (dialectic reasoning, "dreams," peer cards), but it **cannot run fully locally** — its embedding system only supports OpenAI, Gemini, or OpenRouter. No local embedding option exists. You can disable embeddings (`EMBED_MESSAGES=false`) but this guts semantic search. Its LLM features can use Ollama via the "custom" provider, but the embedding hard-block makes it a partial solution.

**Verdict:** Monitor Honcho for when they add local embedding support. Until then, Mem0 + Graphiti provides 80% of Honcho's value with 100% self-hostability.

## What about Zep?

Zep Community Edition was **deprecated in April 2025**. It is now cloud-only (Zep Cloud). Hard disqualified.

However, the Zep team open-sourced **Graphiti** as a standalone temporal knowledge graph engine. Graphiti is the recommended temporal layer if you want time-aware fact tracking beyond what Mem0 provides.
