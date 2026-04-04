# Decision Matrix: Memory Platforms

## Scoring model

Scale: `0` = absent, `1` = weak/partial, `2` = adequate, `3` = strong/leading

Primary criteria weighted `5x`. Secondary criteria weighted `3x`.

## Criteria

### Primary (5x)

| Criterion | Why it matters |
|---|---|
| Zero-API-key purity | Must run fully local with no cloud dependency for memory operations |
| Memory extraction quality | How well does it extract structured facts from conversations? |
| Integration with recommended stack | Works with Hermes / OpenClaw / Bureau / Claude Code via MCP |

### Secondary (3x)

| Criterion | Why it matters |
|---|---|
| Self-hosting simplicity | Fewer containers, less configuration, easier to maintain |
| Graph / relational memory | Entity-relation knowledge beyond flat vector search |
| Temporal reasoning | Can it track how facts change over time? |
| User modeling depth | Does it model the user's personality, preferences, behavior? |
| Ecosystem maturity | Stars, community, production track record, documentation |

## Matrix

| Platform | Zero-API-key (5x) | Extraction quality (5x) | Stack integration (5x) | Self-hosting simplicity (3x) | Graph memory (3x) | Temporal reasoning (3x) | User modeling (3x) | Ecosystem maturity (3x) | **Weighted total** | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| **Mem0** | 3 | 2 | 3 | 2 | 3 | 0 | 1 | 3 | **67** | High |
| **Hindsight** | 3 | 3 | 2 | 3 | 2 | 2 | 1 | 1 | **63** | Medium |
| **Graphiti** | 2 | 2 | 2 | 2 | 3 | 3 | 0 | 2 | **55** | Medium |
| **Cognee** | 3 | 2 | 2 | 2 | 3 | 0 | 0 | 2 | **53** | Medium |
| **Honcho** | 1 | 2 | 2 | 1 | 1 | 0 | 3 | 1 | **38** | High |

### Score justifications

**Mem0:**
- Zero-API-key: 3 — fully verified with Ollama + Qdrant + Neo4j. Also supports Claude Code session token.
- Extraction quality: 2 — good with frontier models, adequate with local (qwen3:14b). Not 3 because local model ceiling.
- Stack integration: 3 — MCP server (11 tools), OpenClaw plugin, can use Claude Code session token, shares Qdrant with Bureau.
- Self-hosting: 2 — 3 Docker containers (API + Qdrant + Neo4j). Not the simplest but manageable.
- Graph: 3 — Neo4j with APOC for entity-relation extraction.
- Temporal: 0 — no temporal fact validity. Facts are current-state only.
- User modeling: 1 — basic entity tracking but no personality/behavior inference.
- Ecosystem: 3 — 48K stars, YC-backed, extensive documentation, multiple MCP implementations.

**Hindsight:**
- Zero-API-key: 3 — verified with Ollama. Local embeddings by default.
- Extraction quality: 3 — 91.4% LongMemEval (highest score). 4-strategy retrieval with reranker.
- Stack integration: 2 — MCP server and Hermes blog post. No OpenClaw plugin.
- Self-hosting: 3 — single Docker container with embedded PostgreSQL.
- Graph: 2 — embedded graph traversal in retrieval. Not as powerful as Neo4j but functional.
- Temporal: 2 — temporal reasoning is one of 4 retrieval strategies. Not as sophisticated as Graphiti.
- User modeling: 1 — observations and mental models, but no dialectic/personality inference.
- Ecosystem: 1 — ~3K stars, newer project, less battle-tested.

**Graphiti:**
- Zero-API-key: 2 — works with Ollama but requires dummy OPENAI_API_KEY env var and OpenAIGenericClient workaround.
- Extraction quality: 2 — capable entity extraction with tool-calling models.
- Stack integration: 2 — MCP server. Community Ollama integration. No OpenClaw plugin.
- Self-hosting: 2 — pip install + FalkorDB container.
- Graph: 3 — temporal knowledge graph is its entire purpose.
- Temporal: 3 — leading. Fact validity windows, entity evolution, point-in-time queries.
- User modeling: 0 — not its purpose.
- Ecosystem: 2 — ~8K stars, backed by Zep team, active development.

**Cognee:**
- Zero-API-key: 3 — verified with Ollama for LLM + embeddings.
- Extraction quality: 2 — good ECL pipeline but "relies heavily on structured output" — local models may struggle.
- Stack integration: 2 — MCP server for Claude Code. No OpenClaw or Hermes plugin.
- Self-hosting: 2 — Docker or pip. Multiple backends to configure.
- Graph: 3 — knowledge graph construction is its core purpose.
- Temporal: 0 — no temporal fact tracking.
- User modeling: 0 — not its purpose.
- Ecosystem: 2 — ~6K stars, active development, good documentation.

**Honcho:**
- Zero-API-key: 1 — LLM features work with Ollama but embeddings require cloud API key. Partial.
- Extraction quality: 2 — dialectic and dream features produce sophisticated insights.
- Stack integration: 2 — OpenClaw plugin (official), Hermes integration documented.
- Self-hosting: 1 — 6 Docker containers. AGPL-3.0 license (copyleft concern).
- Graph: 1 — peer modeling tracks relationships but not a general-purpose knowledge graph.
- Temporal: 0 — no temporal fact validity.
- User modeling: 3 — leading. Dialectic reasoning, dreams, peer cards, personality inference.
- Ecosystem: 1 — ~2K stars, small team, AGPL-3.0 limits adoption.

## Reading the matrix

- **Mem0 wins on total score and confidence.** It leads on stack integration, graph memory, and ecosystem maturity. Its main gap (temporal reasoning) can be filled by adding Graphiti.
- **Hindsight is a close second** with the highest extraction quality score and simplest deployment. It trades ecosystem maturity for benchmarked accuracy.
- **Graphiti is complementary**, not competitive. It fills the temporal reasoning gap for either Mem0 or Hindsight.
- **Cognee is niche** — best for document-to-knowledge-graph pipelines, not conversational memory.
- **Honcho is blocked** by the embedding limitation but would score highest on user modeling if unblocked.

## Sources

### Mem0
- [mem0ai/mem0 GitHub](https://github.com/mem0ai/mem0)
- [Mem0 self-hosted Docker guide](https://mem0.ai/blog/self-host-mem0-docker)
- [mem0-mcp-selfhosted](https://github.com/elvismdev/mem0-mcp-selfhosted)
- [openclaw-mem0 plugin](https://github.com/serenichron/openclaw-memory-mem0)
- [Mem0 local companion with Ollama](https://docs.mem0.ai/cookbooks/companions/local-companion-ollama)
- [Mem0 open source overview](https://docs.mem0.ai/open-source/overview)

### Graphiti
- [getzep/graphiti GitHub](https://github.com/getzep/graphiti)
- [graphiti-mcp-ollama](https://github.com/Flo976/graphiti-mcp-ollama)
- [graphiti-memory MCP](https://github.com/mandelbro/graphiti-memory)
- [Graphiti issue #1116 — Ollama api_base](https://github.com/getzep/graphiti/issues/1116)

### Cognee
- [topoteretes/cognee GitHub](https://github.com/topoteretes/cognee)
- [Cognee Ollama tutorial](https://docs.cognee.ai/tutorials/setup-ollama)
- [Cognee embedding providers](https://docs.cognee.ai/setup-configuration/embedding-providers)
- [Self-hosting Cognee with Ollama](https://www.glukhov.org/post/2025/12/selfhosting-cognee-quickstart-llms-comparison/)

### Hindsight
- [vectorize-io/hindsight GitHub](https://github.com/vectorize-io/hindsight)
- [Hindsight + Ollama setup](https://hindsight.vectorize.io/blog/2026/03/10/run-hindsight-with-ollama)
- [Hindsight + Hermes Agent](https://hindsight.vectorize.io/blog/2026/03/17/hermes-agent-memory)
- [Hindsight overview](https://hindsight.vectorize.io/)

### Honcho
- [plastic-labs/honcho GitHub](https://github.com/plastic-labs/honcho)
- [Honcho self-hosting docs](https://docs.honcho.dev/v3/contributing/self-hosting)
- [openclaw-honcho plugin](https://github.com/plastic-labs/openclaw-honcho)
- [Hermes Agent Honcho integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho/)

### Zep (deprecated — for reference)
- [getzep/zep GitHub](https://github.com/getzep/zep) — Community Edition moved to `legacy/` folder
- [Zep FAQ](https://help.getzep.com/faq)

### Comparisons
- [Mem0 vs Zep vs LangMem vs MemoClaw (DEV Community)](https://dev.to/anajuliabit/mem0-vs-zep-vs-langmem-vs-memoclaw-ai-agent-memory-comparison-2026-1l1k)
- [Top 10 AI Memory Products 2026 (Medium)](https://medium.com/@bumurzaqov2/top-10-ai-memory-products-2026-09d7900b5ab1)
- [Agent memory: Letta vs Mem0 vs Zep vs Cognee (Letta Forum)](https://forum.letta.com/t/agent-memory-letta-vs-mem0-vs-zep-vs-cognee/88)
- [AI Memory Tools Evaluation — Cognee blog](https://www.cognee.ai/blog/deep-dives/ai-memory-tools-evaluation)
- [Best AI Agent Memory Systems 2026 (Vectorize)](https://vectorize.io/articles/best-ai-agent-memory-systems)
- [State of AI Agent Memory 2026 (Mem0 blog)](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
