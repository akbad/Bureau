# Final Recommendation: Memory Platform

## Deploy first: Mem0 (self-hosted)

**Install:** Docker Compose with 3 containers (Mem0 API, Qdrant, Neo4j).

**Configure:**
- LLM: Ollama with `qwen3:14b` (or reuse Claude Code session token for frontier quality)
- Embeddings: Ollama with `bge-m3` or `nomic-embed-text`
- Vector store: Qdrant (share with Bureau's existing instance if possible)
- Graph store: Neo4j with APOC plugin

**Connect:**
- Claude Code: via [mem0-mcp-selfhosted](https://github.com/elvismdev/mem0-mcp-selfhosted) MCP server
- OpenClaw: via [openclaw-mem0](https://github.com/serenichron/openclaw-memory-mem0) plugin
- Hermes Agent: via MCP server or REST API
- Bureau: shares Qdrant backend; coexists with Memory MCP and dossiers

**Why first:** Largest ecosystem, most integrations, graph memory, battle-tested, zero API keys verified.

## Second-best fallback: Hindsight

**When to switch:** If Mem0 feels operationally too heavy (Neo4j overhead, three containers, complex configuration).

**Install:** Single Docker container with embedded PostgreSQL.

**Configure:**
- `HINDSIGHT_API_LLM_PROVIDER=ollama`
- Local embeddings by default (no LLM call for basic recall)

**Connect:** MCP server. [Hermes Agent integration guide exists](https://hindsight.vectorize.io/blog/2026/03/17/hermes-agent-memory).

**Why fallback:** Simpler deployment, highest benchmark accuracy (91.4%), MIT license. Smaller ecosystem and no OpenClaw plugin are the tradeoffs.

## Add later if temporal reasoning matters: Graphiti

**When:** If you find yourself needing "what was true about X at time Y?" queries — project timelines, evolving requirements, changing preferences.

**Install:** `pip install graphiti-core` + FalkorDB via Docker.

**Configure:** Ollama with dummy `OPENAI_API_KEY=abc`, FalkorDB on localhost.

**Connect:** MCP server or Python SDK.

**Why optional:** Most personal assistant / SWE use cases don't need temporal fact tracking. Add it when you do.

## Add later if document knowledge matters: Cognee

**When:** If you regularly ingest research papers, documentation, or reference corpora and want them turned into searchable knowledge graphs.

**Install:** Docker or pip. Ollama for LLM + embeddings.

**Why optional:** Cognee excels at document → knowledge graph pipelines. If your primary need is conversational memory (which Mem0 handles), Cognee is not needed.

## Monitor: Honcho

**When to adopt:** If/when Honcho adds local embedding support (Ollama or any OpenAI-compatible endpoint).

**Why monitor:** Honcho's user modeling (dialectic reasoning, dreams, peer cards) is architecturally unique. No other platform offers natural-language Q&A about user behavior, personality, and preferences. If the embedding limitation is removed, Honcho becomes immediately viable as a user modeling layer alongside Mem0's fact memory.

## What NOT to deploy

| Platform | Why not |
|---|---|
| **Zep CE** | Deprecated April 2025. Cloud-only. |
| **MemoClaw** | Cloud service with proprietary billing. Not self-hosted. |
| **LangMem** | Library, not standalone. Tied to LangChain ecosystem. |
| **Letta** | Full agent runtime, not a memory layer. Use if replacing Hermes/OpenClaw entirely, not as a memory plugin. |
| **MemOS** | Insufficient documentation to evaluate. Too early. |

## What to keep from Bureau

| Bureau component | Keep? | Why |
|---|---|---|
| **Qdrant** | **Yes** | Share with Mem0. Both use it for vector storage. |
| **Memory MCP** | **Yes** | Structural entity-relation memory. Complementary to Mem0's graph. |
| **Dossiers** | **Yes** | Workstream-level resumability. Orthogonal to memory platforms. |
| **claude-mem** | **Evaluate** | May overlap with Mem0's MCP server for Claude Code. Test both, keep whichever is more useful. |
