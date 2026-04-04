# Vector DB and Memory Backend Comparison

## Context

This document evaluates vector databases and graph stores as the **persistence layer** underneath the memory engines evaluated in the main report (Mem0, Hindsight, Graphiti, Cognee). It also considers whether Bureau's existing Qdrant + Memory MCP stack should change.

## Evaluated backends

| DB | Type | Install on macOS | Idle RAM | Hybrid search | License |
|---|---|---|---|---|---|
| **Qdrant** (in use) | Vector (server) | Docker or native binary | ~150MB | Yes (sparse+dense fusion) | Apache 2.0 |
| **ChromaDB** | Vector (embedded/server) | `pip install chromadb` | ~150MB | Weak (metadata only) | Apache 2.0 |
| **Milvus Lite** | Vector (embedded) | `pip install pymilvus[lite]` | ~200MB | Yes (sparse+dense) | Apache 2.0 |
| **LanceDB** | Vector (embedded) | `pip install lancedb` | Very low | Yes (FTS via Tantivy + vector) | Apache 2.0 |
| **SQLite-vec + FTS5** | Vector+FTS (extension) | SQLite extension | Negligible | Yes (FTS5 BM25 + vector) | MIT |
| **Neo4j CE** | Graph (server) | `brew install neo4j` | ~1GB (JVM) | Yes (v5.11+ vector indexes) | GPL |
| **FalkorDB** | Graph+Vector (in-memory) | Docker | ~200MB | Graph+vector in single query | SSPL |

## Key findings

### Qdrant (already in Bureau — keep it)

Bureau already runs Qdrant for semantic retrieval. Qdrant's hybrid search (sparse+dense vector fusion, since v1.7) and rich payload filtering make it the strongest general-purpose vector DB for agent memory. Mem0 natively supports Qdrant as a backend, so the same instance can be shared.

**Verdict:** Keep. No reason to replace.

### LanceDB — most interesting alternative

LanceDB is an embedded (no-server) vector DB built on the Lance columnar format. Its unique feature: **built-in data versioning**. Every write creates a new version, enabling time-travel queries ("what did the agent's memory look like last Tuesday?"). This is genuinely valuable for memory rollback and audit trails.

| Feature | LanceDB | Qdrant |
|---|---|---|
| Architecture | Embedded (no server) | Client-server |
| Versioning/time-travel | **Built-in** | None |
| Hybrid search | FTS (Tantivy) + vector | Sparse + dense vectors |
| Resource usage | Very low (memory-mapped) | Moderate (server process) |
| Concurrent access | Limited (embedded) | Full |
| Filtering | SQL-like expressions | Rich payload filters |

**Verdict:** Worth evaluating as a Qdrant replacement if versioning matters. The tradeoff is single-process access (no concurrent readers from different services) and younger ecosystem. Could be ideal for a Hindsight-style single-container deployment.

### SQLite-vec + FTS5 — the "boring technology" option

Already used by Hermes Agent (SQLite + FTS5 for session search). Adding sqlite-vec gives you vector similarity in the same SQLite database. Combined with regular SQL tables for entity-relations, this could theoretically replace **both** Qdrant **and** Memory MCP with a single file.

| What you get | How |
|---|---|
| Vector similarity search | sqlite-vec extension |
| Full-text keyword search (BM25) | FTS5 (built into SQLite) |
| Entity-relation storage | Regular SQL tables with JOINs |
| Zero infrastructure | One `.db` file |
| Trivial backup | Copy one file |

**Limitation:** sqlite-vec is brute-force (no ANN index). Fine for <100K vectors (millisecond queries). Impractical at 1M+. For agent memory (realistically tens of thousands of entries), this is acceptable.

**Verdict:** Most operationally simple option. Eliminates two services (Qdrant + Memory MCP) in exchange for one SQLite file. The "right" choice if minimizing moving parts is paramount. The risk is sqlite-vec's maturity and the scaling ceiling.

### Neo4j CE — powerful but heavy

Used by Mem0 for entity-relation graph storage. Cypher query language is excellent for multi-hop graph traversal. But the JVM baseline (~1GB RAM) is hard to justify on a MacBook alongside other services, especially when most agent memory queries are simple lookups or 1-hop traversals.

**Verdict:** Use it if you deploy Mem0 (which needs it for graph memory). Don't add it independently — the resource cost doesn't justify the capability for typical agent memory patterns. If Neo4j's overhead is too much, Mem0 can operate without graph memory (`MEM0_ENABLE_GRAPH=false`).

### FalkorDB — unified graph+vector without Neo4j's weight

Fork of RedisGraph. In-memory graph DB with Cypher support + vector similarity. Used by Graphiti for temporal knowledge graphs. The key advantage: combined graph+vector queries in a single system ("find nodes similar to this embedding within 2 hops of entity X") without Neo4j's JVM overhead.

**Verdict:** Use it if you deploy Graphiti (which needs it). Also interesting as a lighter Neo4j replacement for Mem0's graph memory (would require custom integration — Mem0 doesn't natively support FalkorDB). In-memory model means data loss risk on crash (mitigated by RDB snapshots/AOF persistence).

### ChromaDB and Milvus Lite — not recommended

ChromaDB is simpler than Qdrant but weaker (no real hybrid search, metadata filtering only). Switching from Qdrant to ChromaDB would be a downgrade. Milvus Lite is a development tool (explicitly designed for dev/test, not production). Neither adds value over Bureau's existing Qdrant.

## Recommendations for the memory stack

### If deploying Mem0 (recommended path):

```
Qdrant (shared with Bureau) ← Mem0 vector storage
Neo4j                       ← Mem0 graph storage (optional, toggle with MEM0_ENABLE_GRAPH)
```

This adds Neo4j as the only new infrastructure. Qdrant is shared.

### If deploying Hindsight (fallback path):

```
Embedded PostgreSQL (inside Hindsight container) ← all storage
Qdrant (keep for Bureau)                         ← Bureau's semantic retrieval
```

Hindsight manages its own storage. Bureau keeps Qdrant separately.

### If optimizing for minimal infrastructure later:

```
SQLite + FTS5 + sqlite-vec ← replaces Qdrant + Memory MCP for Bureau
Mem0 or Hindsight          ← memory engine (uses its own storage)
```

This is the "boring technology" path — eliminate Qdrant entirely for Bureau's own memory, use the memory engine's storage for everything else. Only pursue this if operational simplicity matters more than Qdrant's query sophistication.

## Sources

- Qdrant: [qdrant.tech](https://qdrant.tech/), [Qdrant hybrid search](https://qdrant.tech/documentation/concepts/hybrid-queries/)
- LanceDB: [lancedb.com](https://lancedb.github.io/lancedb/), [Lance format](https://github.com/lancedb/lance)
- sqlite-vec: [github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec)
- Neo4j: [neo4j.com/community](https://neo4j.com/licensing/)
- FalkorDB: [falkordb.com](https://www.falkordb.com/), [GitHub](https://github.com/FalkorDB/FalkorDB)
- ChromaDB: [docs.trychroma.com](https://docs.trychroma.com/)
- Milvus Lite: [milvus.io/docs/milvus_lite](https://milvus.io/docs/milvus_lite.md)
