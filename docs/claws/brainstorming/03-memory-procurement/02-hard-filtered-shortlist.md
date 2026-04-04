# Hard-Filtered Shortlist: Memory Platforms

## Platforms evaluated

| Platform | GitHub | Stars | License | Category |
|---|---|---|---|---|
| Honcho | [plastic-labs/honcho](https://github.com/plastic-labs/honcho) | ~2K | AGPL-3.0 | User modeling + memory service |
| Mem0 | [mem0ai/mem0](https://github.com/mem0ai/mem0) | ~48K | Apache 2.0 | Universal memory layer |
| Zep CE | [getzep/zep](https://github.com/getzep/zep) (legacy/) | ~2K | MIT | Context engineering (deprecated) |
| Graphiti | [getzep/graphiti](https://github.com/getzep/graphiti) | ~8K | Apache 2.0 | Temporal knowledge graph |
| Cognee | [topoteretes/cognee](https://github.com/topoteretes/cognee) | ~6K | Apache 2.0 | Knowledge graph + vector engine |
| Hindsight | [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) | ~3K | MIT | Agent memory that learns |
| Letta | [letta-ai/letta](https://github.com/letta-ai/letta) | ~15K | Apache 2.0 | Agent runtime with memory |
| MemOS | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | ~1K | Apache 2.0 | Memory OS for LLM/agents |
| MemoClaw | memoclaw.com | N/A | Proprietary | Cloud memory service |
| LangMem | Part of LangChain | N/A | MIT | Library (not standalone) |

## Hard constraints applied

### Constraint 1: Zero API keys

| Platform | Zero-API-key possible? | How? |
|---|---|---|
| Mem0 | **YES** | Ollama for both LLM (fact extraction) and embeddings (nomic-embed-text / bge-m3). Qdrant or pgvector for vectors. Neo4j for graph. |
| Graphiti | **YES** | Ollama via OpenAI-compatible endpoint. Requires dummy `OPENAI_API_KEY=abc` env var (not actually used). FalkorDB for graph. |
| Cognee | **YES** | Ollama for LLM + embeddings. `EMBEDDING_PROVIDER="ollama"`, `EMBEDDING_MODEL="nomic-embed-text:latest"`. |
| Hindsight | **YES** | Ollama as LLM provider (`HINDSIGHT_API_LLM_PROVIDER=ollama`). Local embeddings by default — no LLM call needed for basic semantic search. |
| Honcho | **PARTIAL** | LLM features can use `custom`/`vllm` provider (Ollama-compatible). BUT: embeddings ONLY support openai/gemini/openrouter — NO local option. `EMBED_MESSAGES=false` disables embeddings but guts semantic search. |
| Letta | **YES** (but not a memory layer) | Ollama for LLM + embeddings. Self-contained agent runtime. |
| MemOS | **UNCLEAR** | Insufficient documentation to verify |
| Zep CE | **N/A** | Deprecated April 2025. Cloud-only. |
| MemoClaw | **NO** | Cloud service with wallet-based billing |
| LangMem | **N/A** | Library, not standalone |

### Constraint 2: Fully self-hosted on Mac

| Platform | macOS self-hosting? | Method |
|---|---|---|
| Mem0 | **YES** | Docker Compose: 3 containers (API, Qdrant/pgvector, Neo4j) |
| Graphiti | **YES** | pip install + FalkorDB via Docker |
| Cognee | **YES** | Docker or pip install |
| Hindsight | **YES** | Single Docker container with embedded PostgreSQL |
| Honcho | **YES** | Docker Compose: 6 containers (API, deriver, PostgreSQL, Redis, Prometheus, Grafana) |

### Constraint 3: No hosted memory services / no cloud dependency

All Tier 1 survivors (Mem0, Graphiti, Cognee, Hindsight) pass this constraint when configured with Ollama.

### Constraint 4: Integrates with Hermes / OpenClaw / Bureau

| Platform | Integration paths |
|---|---|
| Mem0 | MCP server ([mem0-mcp-selfhosted](https://github.com/elvismdev/mem0-mcp-selfhosted)), OpenClaw plugin ([openclaw-mem0](https://github.com/serenichron/openclaw-memory-mem0)), Python SDK, REST API |
| Graphiti | MCP server ([graphiti MCP](https://github.com/getzep/graphiti/tree/main/mcp_server)), REST API, [graphiti-memory MCP with Ollama](https://github.com/mandelbro/graphiti-memory) |
| Cognee | MCP server, REST API, Python SDK |
| Hindsight | MCP server, REST API, Python SDK. [Blog post on Hermes Agent integration](https://hindsight.vectorize.io/blog/2026/03/17/hermes-agent-memory) |
| Honcho | REST API, Python SDK, [OpenClaw plugin](https://github.com/plastic-labs/openclaw-honcho), [Hermes integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho/) |

## Elimination results

| Platform | Status | Reason |
|---|---|---|
| **Mem0** | **SURVIVES** | Zero API keys, fully self-hosted, excellent integration, largest ecosystem |
| **Graphiti** | **SURVIVES** | Zero API keys (dummy env var), unique temporal capability, MCP server |
| **Cognee** | **SURVIVES** | Zero API keys, unique knowledge graph construction, MCP server |
| **Hindsight** | **SURVIVES** | Zero API keys, highest benchmark score (91.4% LongMemEval), simplest deployment |
| **Honcho** | **BORDERLINE** | Embedding limitation blocks full local operation. LLM features work with Ollama. Monitor for local embedding support. |
| Zep CE | **ELIMINATED** | Deprecated April 2025. Cloud-only. |
| MemoClaw | **ELIMINATED** | Cloud service with proprietary billing |
| LangMem | **ELIMINATED** | Not a standalone platform |
| Letta | **RECLASSIFIED** | Agent runtime, not a memory layer. Evaluated in platform procurement (Task 02). |
| MemOS | **INSUFFICIENT DATA** | Too early to evaluate — documentation sparse |
