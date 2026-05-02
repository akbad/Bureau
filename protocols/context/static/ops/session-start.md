# Session start

## Factual accuracy

> Factual accuracy >> response speed. Verify before answering.

- Technical info → search official docs (Context7; Fetch for known URLs; web search only when discovery is needed)
- Current events → Tavily/Brave when available → Bureau Search (`bureau_search_web`) → open-webSearch/native web search, using freshness filters where supported
- Code behavior → read actual code, run tests, check logs
- API details → fetch current documentation, not training data
- "I don't know" > wrong answer; "let me verify" > speculation.
- **Speculative answers stored in memory = poisoning future agents.**

## Memory retrieval

Before starting any task, query all memory systems:

- **Qdrant MCP** (`qdrant-find`): past solutions, patterns, gotchas
- **Memory MCP** (`read_graph`, `search_nodes`): architecture, components, relationships
- **claude-mem** (`get_observations`, `search`): recent session history (Claude Code only)

## Memory metadata

Always include when storing memories:

| Storage tool | Required field |
| :--- | :--- |
| Qdrant MCP | `metadata.created_at` (ISO 8601 UTC, e.g., `2025-12-05T21:10:00+00:00`) |
| Memory MCP | `created_at` (ISO 8601 UTC, e.g., `2025-12-05T21:10:00+00:00`) |
| Serena MCP | None; automatic |
| claude-mem | None; automatic |
