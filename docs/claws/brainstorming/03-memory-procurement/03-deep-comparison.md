# Deep Comparison: Surviving Memory Platforms

## 1. Mem0

**What it is:** A universal memory layer for AI agents that extracts structured memories from conversations, stores them in vector + graph form, and retrieves them on demand. Think of it as an automatic "memory compiler" — it turns messy conversation history into clean, searchable, deduplicated facts and entity relationships.

**GitHub:** [mem0ai/mem0](https://github.com/mem0ai/mem0) — ~48K stars, Apache 2.0, YC-backed ($24M Series A)

### Architecture

```
Conversations → Mem0 API → [LLM extracts facts] → Qdrant (vectors) + Neo4j (graph)
                                                          ↕
                              MCP Server ← Claude Code / Hermes / OpenClaw
```

Three Docker containers:
1. **FastAPI server** — REST API for memory operations
2. **Qdrant** (or pgvector) — vector storage and semantic search
3. **Neo4j** (optional) — entity-relation knowledge graph

### Zero-API-key self-hosting

**Fully verified.** Configuration for zero-cloud operation:

- `MEM0_PROVIDER=ollama` — uses Ollama for fact extraction LLM
- `MEM0_LLM_MODEL=qwen3:14b` — or any capable local model
- Embedding: Ollama with `nomic-embed-text:latest` or `bge-m3` (1024 dims)
- Vector store: Qdrant on localhost:6333
- Graph store: Neo4j on localhost:7687 (optional, toggle with `MEM0_ENABLE_GRAPH`)

**Alternative zero-key path:** If you want frontier model quality for fact extraction without managing a separate API key, Mem0's MCP server auto-reads Claude Code's session token from `~/.claude/.credentials.json`. This uses your existing Claude Code subscription — no separate API key needed. Source: [mem0-mcp-selfhosted](https://github.com/elvismdev/mem0-mcp-selfhosted).

### Memory model

- **Fact extraction:** LLM parses conversations into discrete facts ("user prefers Python," "project X uses FastAPI")
- **Deduplication:** New facts are compared against existing memories; duplicates are merged
- **Entity resolution:** Entities are linked across conversations (the "Alice" from Tuesday is the same "Alice" from Monday)
- **Memory compression:** 80% prompt token reduction vs raw history (claimed by Mem0)
- **Graph relationships:** Neo4j stores entity → relationship → entity triples

### MCP server (11 tools)

| Tool | Purpose |
|---|---|
| `add_memory` | Store a new memory |
| `search_memories` | Semantic search across memories |
| `get_memories` | List all memories for a user |
| `get_memory` | Retrieve specific memory by ID |
| `update_memory` | Modify existing memory |
| `delete_memory` | Remove specific memory |
| `delete_all_memories` | Clear all memories |
| `list_entities` | Browse knowledge graph entities |
| `delete_entities` | Remove graph entities |
| `search_graph` | Query knowledge graph |
| `get_entity` | Retrieve specific entity details |

### Integration with the recommended stack

- **Claude Code:** MCP server provides persistent memory across sessions. Auto-uses Claude subscription token.
- **OpenClaw:** Dedicated plugin (`openclaw-mem0`) with auto-recall (injects relevant memories before agent responds) and auto-capture (extracts memories after agent responds).
- **Hermes Agent:** MCP server or REST API. Can layer on top of Hermes's native MEMORY.md/FTS5 system.
- **Bureau:** Shares Qdrant backend. Can coexist with Bureau's Memory MCP and dossier system.

### Strengths

- Largest ecosystem (48K+ stars, YC-backed, 5,500+ forks)
- Production-grade (Fortune 500 users reported)
- Graph memory via Neo4j (entity-relation extraction)
- 20+ vector store backends
- MCP server with 11 tools
- OpenClaw and Hermes integration paths exist
- Can share Qdrant with Bureau

### Weaknesses

- Fact extraction quality depends on the LLM — local models (Ollama) produce lower quality than Claude/GPT
- Neo4j adds resource overhead (~500MB RAM baseline)
- No temporal reasoning (facts don't have time validity windows — see Graphiti for that)
- No "user modeling" in the Honcho sense (no dialectic reasoning, no personality inference)
- Memory is flat facts + graph — no hierarchical memory tiers

### Verdict

**Primary recommendation.** Mem0 is the most mature, best-integrated, fully-self-hostable memory platform. It fills the gap that Bureau, Hermes, and OpenClaw all have: systematic extraction of durable facts from conversations into a searchable, deduplicated, graph-linked memory store.

---

## 2. Graphiti

**What it is:** A temporal knowledge graph engine that tracks how facts change over time. Where Mem0 stores "Alice works at Google," Graphiti stores "Alice works at Google (valid from: March 2024, valid to: present)" and when she leaves, the old fact is invalidated — not deleted — so you can query what was true at any point in time.

**GitHub:** [getzep/graphiti](https://github.com/getzep/graphiti) — ~8K stars, Apache 2.0. Built by the Zep team after they deprecated Zep CE.

### Architecture

```
Data → Graphiti → [LLM extracts entities/facts] → FalkorDB (graph + vector)
                                                          ↕
                              MCP Server ← Claude Code / agents
```

Key components:
- **FalkorDB** — in-memory graph database with vector search (single container)
- **Graphiti library** — Python SDK that manages the knowledge graph
- **MCP server** — exposes graph operations to Claude Code and other MCP clients

### Zero-API-key self-hosting

**Verified with workaround.** Graphiti uses an OpenAI-compatible client internally. To use Ollama:

- Set `OPENAI_API_KEY=abc` (dummy value — required by env var validation but not actually used for auth)
- Configure Ollama base URL: `http://localhost:11434/v1`
- Use `OpenAIGenericClient` (not the default, because Ollama lacks `/v1/responses` endpoint)
- Models: `qwen2.5:14b` for LLM, `nomic-embed-text` for embeddings

Source: [graphiti-mcp-ollama](https://github.com/Flo976/graphiti-mcp-ollama), [Graphiti issue #1116](https://github.com/getzep/graphiti/issues/1116)

### Memory model

- **Temporal facts:** Every fact has `valid_from`, `valid_to`, and `invalid_at` timestamps
- **Entity episodes:** Track how entities evolve over time
- **Fact invalidation:** When information changes, old facts are marked invalid (not deleted)
- **Point-in-time queries:** "What was true about Alice in March 2024?"
- **Community detection:** Automatic grouping of related entities

### Strengths

- **Unique temporal reasoning** — no other memory platform in this comparison tracks fact validity over time
- FalkorDB is lightweight (in-memory, single container)
- Clean MCP server for Claude Code integration
- Can complement Mem0 (Mem0 handles flat facts, Graphiti handles temporal evolution)

### Weaknesses

- Requires dummy `OPENAI_API_KEY` env var even with Ollama (cosmetic but annoying)
- Ollama integration requires `OpenAIGenericClient` workaround (not seamless)
- Smaller ecosystem than Mem0
- No built-in MCP integration with OpenClaw or Hermes (needs manual setup)
- Needs capable local model for structured entity extraction (small models struggle)

### Verdict

**Recommended as an optional temporal layer.** Graphiti fills a specific gap that Mem0 does not: tracking how facts change over time. If your use cases include project timelines, evolving requirements, or any domain where "what was true when" matters, add Graphiti alongside Mem0. If not, Mem0 alone is sufficient.

---

## 3. Cognee

**What it is:** A knowledge engine that ingests documents and conversations, extracts entities and relationships, builds a knowledge graph, and provides combined vector + graph retrieval. Think of it as "document → structured knowledge" pipeline, using an ECL (Extract, Cognify, Load) approach inspired by ETL.

**GitHub:** [topoteretes/cognee](https://github.com/topoteretes/cognee) — ~6K stars, Apache 2.0

### Architecture

```
Documents/Data → Cognee ECL Pipeline → [Extract entities] → [Cognify: build graph] → [Load: store]
                                              ↓                      ↓
                                    Vector store (Qdrant/etc.)    Graph store (Neo4j/FalkorDB/etc.)
```

### Zero-API-key self-hosting

**Verified.** Full local setup:

- `LLM_PROVIDER="ollama"`, `LLM_MODEL="qwen2.5:14b"`
- `EMBEDDING_PROVIDER="ollama"`, `EMBEDDING_MODEL="nomic-embed-text:latest"`, `EMBEDDING_ENDPOINT="http://localhost:11434/api/embed"`
- `HUGGINGFACE_TOKENIZER` must be set for proper token counting with Ollama
- Vector store: Qdrant, PGVector, Weaviate, or LanceDB
- Graph store: Neo4j, FalkorDB, or NetworkX (in-memory)

Source: [Cognee Ollama tutorial](https://docs.cognee.ai/tutorials/setup-ollama), [Cognee embedding providers](https://docs.cognee.ai/setup-configuration/embedding-providers)

### Memory model

- **Entity extraction:** Named entities, concepts, relationships from documents
- **Knowledge graph construction:** Entities linked by typed relationships
- **Semantic chunking:** Documents split into meaningful segments (not just token windows)
- **Combined retrieval:** Vector similarity + graph traversal for queries
- **MCP server:** Exposes knowledge operations to Claude Code

### Strengths

- **Best for document ingestion** — if you have a corpus of docs/notes to turn into searchable knowledge
- Combines vector + graph retrieval in one pipeline
- Multiple graph backends (Neo4j, FalkorDB, in-memory NetworkX)
- Multiple vector backends (Qdrant, PGVector, LanceDB)
- Active development, clean Python SDK

### Weaknesses

- "Relies heavily on structured output" — local models must produce clean JSON for entity extraction. Many smaller models struggle with this.
- More of a knowledge construction pipeline than a conversational memory system
- Smaller ecosystem than Mem0
- No built-in OpenClaw or Hermes integration (MCP server covers Claude Code)
- Heavier setup than Mem0 (more configuration knobs)

### Verdict

**Recommended as an optional knowledge layer.** Cognee excels at turning documents into searchable knowledge graphs. If you regularly ingest research papers, documentation, or reference material, Cognee adds value alongside Mem0. If your primary need is conversational memory, Mem0 alone is sufficient.

---

## 4. Hindsight

**What it is:** A high-accuracy agent memory system that extracts facts, resolves entities, and enables "reflection" (reasoning over stored memories). Achieved 91.4% on LongMemEval benchmark — the highest score ever reported as of December 2025.

**GitHub:** [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) — ~3K stars, MIT license. Built by Vectorize.io.

### Architecture

```
Agent interactions → Hindsight → [retain()] → Embedded PostgreSQL
                                 [recall()]  ← TEMPR multi-strategy retrieval
                                 [reflect()] → LLM reasoning over memories
```

**Simplest deployment of all candidates:** single Docker container with embedded PostgreSQL. No separate database setup.

### Zero-API-key self-hosting

**Verified.** Configuration:
- `HINDSIGHT_API_LLM_PROVIDER=ollama`
- Local embeddings by default — "recall uses local embeddings by default, so no LLM call is needed for basic semantic search"
- LLM needed only for `retain()` (fact extraction), `reflect()` (reasoning), and the reranker
- System requirements: ~16GB RAM for 20B model, ~80GB for 120B model

Source: [Hindsight + Ollama blog post](https://hindsight.vectorize.io/blog/2026/03/10/run-hindsight-with-ollama)

### Memory model

Four knowledge types:
1. **Mental Models** — user-curated summaries for common queries
2. **Observations** — automatically consolidated patterns
3. **World Facts** — objective information ("Alice works at Google")
4. **Experience Facts** — the agent's own actions and interactions

**TEMPR retrieval** (4 parallel strategies):
- Semantic search (vector similarity)
- BM25 keyword matching
- Graph traversal (entity connections)
- Temporal reasoning (time-based queries)
- Cross-encoder reranker merges results

### Strengths

- **Highest benchmark accuracy** (91.4% LongMemEval)
- **Simplest deployment** — one Docker container, embedded PostgreSQL
- MIT license (most permissive)
- Local embeddings by default
- 4-strategy parallel retrieval with reranker
- MCP server available
- [Hermes Agent integration blog post](https://hindsight.vectorize.io/blog/2026/03/17/hermes-agent-memory)

### Weaknesses

- Smaller ecosystem (~3K stars vs Mem0's 48K)
- No graph database for explicit entity-relation storage (graph is embedded, not Neo4j-grade)
- No OpenClaw plugin (MCP server covers Claude Code)
- Newer project — less battle-tested in production
- Requires significant RAM for quality local models (16GB+ for 20B model)

### Verdict

**Strong alternative to Mem0 if simplicity is paramount.** Hindsight's single-container deployment, MIT license, and highest benchmark accuracy make it attractive. However, Mem0's graph memory (Neo4j), larger ecosystem, and existing OpenClaw plugin give it the edge for a multi-platform setup.

---

## 5. Honcho (borderline — for context)

**What it is:** A memory and user modeling service with the most sophisticated psychological modeling of any platform evaluated. Concepts include "dialectic reasoning" (natural-language Q&A about users), "dreams" (background deep reasoning), "representations" (AI-derived personality models), and "peer cards" (auto-generated profiles).

**GitHub:** [plastic-labs/honcho](https://github.com/plastic-labs/honcho) — ~2K stars, AGPL-3.0

### Why it's borderline

**Embedding hard-block:** The `embedding_client.py` only supports three providers: `openai`, `gemini`, `openrouter`. There is no `ollama`, `vllm`, or `custom` option for embeddings. If `EMBED_MESSAGES=true` (the default), you MUST have a cloud API key for one of those three.

**Workaround:** Set `EMBED_MESSAGES=false` — this disables semantic search over messages. You can still use all other features (sessions, messages, representations, summaries, dialectic, dreams) because the LLM features can use the `custom` or `vllm` provider (Ollama-compatible).

**What you lose with EMBED_MESSAGES=false:**
- No semantic search across past messages
- Collections/Documents RAG functionality is unavailable
- Must rely on summaries, dialectic, and explicit recalls instead

### What makes Honcho unique

No other platform in this comparison offers:
- **Dialectic API:** Natural language Q&A about any peer — "What learning styles does this user prefer?" "How does this user typically approach debugging?"
- **Dreams:** Background deep reasoning that generates inductive/deductive insights about users
- **Peer modeling:** Both humans AND AI agents are modeled as "peers" with representations
- **Peer cards:** Auto-generated personality/behavior profiles

### Integration

- [OpenClaw plugin](https://github.com/plastic-labs/openclaw-honcho) — official, by plastic-labs
- [Hermes Agent integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho/) — documented, optional feature

### Verdict

**Monitor for local embedding support.** Honcho's user modeling is unmatched, but the embedding limitation is a hard block for fully local operation. If Honcho adds Ollama embedding support (or an OpenAI-compatible embedding endpoint option), it becomes immediately viable. Until then, Mem0 + the agent platform's native memory (Hermes MEMORY.md/USER.md) provides a reasonable substitute for basic user modeling.
