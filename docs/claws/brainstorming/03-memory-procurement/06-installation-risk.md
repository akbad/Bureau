# Installation Risk and Unknowns: Memory Platforms

## Mem0 (primary recommendation)

### 1. Local model quality for fact extraction

Mem0's memory quality depends entirely on the LLM used for fact extraction. The default is `gpt-5-nano` (cloud). With Ollama:

- **Question:** Which local models produce reliable fact extraction? Do they miss facts, hallucinate facts, or fail at entity deduplication?
- **Known:** `qwen3:14b` has 0.971 tool-calling F1 (nearly matching GPT-4's 0.974) and fits in ~8GB VRAM. This is the most promising local option.
- **Risk:** Smaller models (7B and below) may produce significantly degraded memory quality.
- **Verification step:** Run Mem0 with Ollama + qwen3:14b, add 20 diverse conversations, then query memories and check extraction accuracy manually.

### 2. Claude Code session token auto-detection

The `mem0-mcp-selfhosted` server reads Claude Code's session token from `~/.claude/.credentials.json` automatically.

- **Question:** Is this token stable? Does it expire? Does it refresh automatically?
- **Question:** Does this token provide API access equivalent to an API key, or are there rate limits / capability restrictions?
- **Risk:** If the token is short-lived, memory writes during long sessions could silently fail.
- **Verification step:** Start the MCP server, run Claude Code for an extended session, verify memory writes succeed throughout.

### 3. Qdrant namespace isolation

If sharing Qdrant between Bureau and Mem0:

- **Question:** Do they use separate collections? Is there collision risk?
- **Question:** Can Bureau's Qdrant handle the additional load from Mem0's writes?
- **Mitigation:** If collision risk exists, run a second Qdrant instance (lightweight — ~200MB RAM).
- **Verification step:** Check Mem0's Qdrant collection naming. Verify it doesn't conflict with Bureau's.

### 4. Neo4j vs Kuzu for graph store

Mem0 supports both Neo4j (server) and **Kuzu** (embedded, like SQLite for graphs).

- **Neo4j:** ~500MB-1GB RAM (JVM baseline). Full Cypher queries, ACID transactions. Production-grade but resource-heavy.
- **Kuzu:** Negligible overhead. Embedded, single file. No server, no Docker container. Supports Cypher-like queries.
- **Recommendation:** Start with Kuzu for simplicity. Migrate to Neo4j only if you need full Cypher, ACID transactions, or complex multi-hop graph reasoning.
- **Verification step:** Run Mem0 with Kuzu, add 1000 memories, check graph query speed and entity deduplication quality.

### 4b. Qdrant server vs Qdrant file mode

Mem0 supports both Qdrant server (localhost:6333) and Qdrant local file mode (`path="/path/to/qdrant"`).

- **Server mode:** Needed if Bureau and Mem0 share the same Qdrant instance. More capable (concurrent access, filtering).
- **File mode:** Zero infrastructure. Good if Mem0 is the only consumer.
- **Recommendation:** If Bureau already runs Qdrant, share it (server mode). Otherwise, start with file mode.

### 4c. PostHog telemetry

Mem0 includes PostHog analytics that phones home to `https://us.i.posthog.com`.

- **Action:** Set `MEM0_TELEMETRY=false` in environment before first run.
- **Note:** The `posthog` and `openai` Python packages are hard dependencies in `pyproject.toml` even when not used. They are imported unconditionally but do not phone home without keys / with telemetry disabled.

### 5. Memory deduplication quality with local models

- **Question:** Does Mem0's deduplication work well with Ollama models? Or does it create duplicate memories due to lower LLM quality?
- **Risk:** Duplicate memories pollute context and waste tokens.
- **Verification step:** Add the same fact in different phrasings across 5 conversations, check if Mem0 deduplicates correctly.

## Hindsight (fallback)

### 1. Embedded PostgreSQL persistence

Hindsight uses embedded PostgreSQL — no separate database container.

- **Question:** Where is the data directory? Is it in the Docker volume?
- **Question:** How do you back up the database?
- **Risk:** If the container is removed without preserving the volume, all memories are lost.
- **Verification step:** Start Hindsight, add memories, stop/restart container, verify memories persist.

### 2. RAM requirements for quality local models

- **Question:** Is 16GB MacBook RAM sufficient for `gpt-oss:20b` + Hindsight + Ollama + the agent platform?
- **Risk:** Memory pressure on MacBook if running multiple services simultaneously.
- **Verification step:** Start full stack (Hermes/OpenClaw + Hindsight + Ollama + Qdrant), monitor Activity Monitor for memory pressure.

### 3. MCP server maturity

- **Question:** How stable is Hindsight's MCP server? Is it production-grade or experimental?
- **Verification step:** Run the MCP server with Claude Code for a day, check for connection drops, timeouts, or errors.

## Graphiti (optional temporal layer)

### 1. FalkorDB stability on macOS

- **Question:** FalkorDB is an in-memory database. Does it persist to disk on Mac? What happens on crash?
- **Risk:** In-memory = data loss on container restart unless persistence is configured.
- **Verification step:** Check FalkorDB Docker volume mount, add temporal facts, restart container, verify facts survive.

### 2. Ollama integration fragility

- **Question:** The `OpenAIGenericClient` workaround for Ollama — is this stable or likely to break on Graphiti updates?
- **Question:** Does the dummy `OPENAI_API_KEY=abc` cause issues anywhere?
- **Risk:** Workaround may break on Graphiti version upgrades.
- **Verification step:** Run Graphiti with Ollama, add temporal facts, query point-in-time, verify correctness.

## Cognee (optional knowledge layer)

### 1. Structured output quality with local models

Cognee "relies heavily on structured output" — the LLM must return properly formatted JSON with entities, relationships, and metadata.

- **Question:** Which Ollama models reliably produce structured JSON output?
- **Risk:** Many local models struggle with consistent JSON formatting, especially for complex entity extraction.
- **Verification step:** Ingest 5 diverse documents with Ollama, check extracted entity quality.

## Honcho (monitor — not recommended yet)

### 1. Embedding limitation timeline

- **Question:** Is there a GitHub issue or roadmap item for adding Ollama embedding support?
- **Question:** Would an OpenAI-compatible embedding endpoint (Ollama serves one at `/v1/embeddings`) work if someone added it?
- **Action:** Search Honcho GitHub issues for "ollama embedding" or "local embedding". If a PR exists, consider contributing or testing it.

## General risks across all platforms

### Docker resource contention on MacBook Pro

Running the full stack simultaneously:
- Hermes Agent or OpenClaw (gateway process)
- Ollama (8–16GB for the model)
- Mem0 API server
- Qdrant
- Neo4j
- Bureau services
- Claude Code / Codex CLI (when delegated to)

**Total estimated RAM:** 12–20GB minimum (without Ollama model in VRAM).

- **Risk:** MacBook Pro with 16GB RAM may be insufficient. 32GB+ recommended.
- **Verification step:** Start all services, run a realistic workload, check Activity Monitor for swap usage.

### Ollama as a single point of failure

Multiple services (Mem0, Graphiti, Cognee, Hindsight, agent platform) may all depend on Ollama.

- **Risk:** If Ollama crashes or is restarting, memory writes from ALL platforms fail simultaneously.
- **Mitigation:** Ollama is generally stable as a daemon. Use `launchd` (macOS) to auto-restart it.

### Memory quality ceiling with local models

All platforms' memory quality is bounded by the local LLM's capability.

- **Fact:** Claude Code's session token path (Mem0 reads `~/.claude/.credentials.json`) provides frontier model quality without a separate API key. This is the highest-quality zero-API-key path.
- **Fact:** Local models (qwen3:14b, llama3.3:8b) are significantly less capable than frontier models for structured extraction.
- **Recommendation:** Use Claude Code's session token for memory extraction quality when possible; fall back to Ollama when offline.
