# Neo4j Graph Memory Implementation Summary

## 1. Changes Made

### Configuration Infrastructure

**`directives.yml`** - Neo4j ports configured:
```yaml
port_for:
  neo4j_db: 7687      # Neo4j Bolt protocol
  neo4j_http: 7474    # Neo4j Browser/HTTP API
```

**`charter.yml`** - Neo4j defaults:
```yaml
path_to:
  storage_for:
    neo4j: ~/.neo4j/

neo4j:
  auth:
    username: neo4j
    password: bureau
  plugins: '["graph-data-science"]'
```

**`operations/config_loader.py`** - TypedDicts for Neo4j config:
- `Neo4jAuthConfig` and `Neo4jConfig`
- Port configuration for `neo4j_db` and `neo4j_http`

**`operations/validate_config.py`** - Schema validation:
- Neo4j ports in `REQUIRED_SCHEMA["port_for"]`
- Neo4j auth section in schema

### Docker Setup

**`tools/scripts/set-up-tools.sh`** - Neo4j container management:
- `start_neo4j_docker()` - Creates/starts Neo4j container with GDS plugin
- `wait_for_neo4j_ready()` - Polls bolt port until container is ready
- Neo4j starts unconditionally with other Docker containers
- `close-bureau` script includes `docker stop neo4j`

### MCP Configuration

**`tools/scripts/set-up-tools.sh`** - Memory MCPs (always Neo4j-backed):
- `setup_neo4j_memory_mcp()` - mcp-neo4j-memory for entity/relation CRUD
- `setup_gds_agent_mcp()` - gds-agent for Graph Data Science algorithms
- `setup_bureau_graph_extras_mcp()` - blast_radius and cycle detection

### bureau-graph-extras MCP

**Package: `tools/mcp-servers/bureau-graph-extras/`**

| Tool | Purpose |
|------|---------|
| `blast_radius(entity)` | Find all entities transitively affected by changing an entity, with distance |
| `detect_cycles(entity?, limit?)` | Find circular dependencies in the graph |

### Neo4j Cleanup Handler

**`operations/cleanup/handlers/neo4j_memory.py`** - Cleanup handler:
- `get_stale_items()` - Finds Memory nodes older than retention period
- `export_items_to_trash()` - Exports to JSON before deletion
- `delete_items_from_storage()` - Uses `DETACH DELETE` for proper cleanup
- `wipe()` - Removes all Memory nodes

### Context Files

**`protocols/context/templates/tools-guide.template.md`** - Graph memory directives inlined:
- Neo4j-memory, neo4j-gds, bureau-graph-extras tool tables
- MANDATORY MEMORY RETRIEVAL PROTOCOL
- MANDATORY MEMORY STORAGE PROTOCOL
- GRAPH INTELLIGENCE PROTOCOL with `blast_radius` usage guidance

---

## 2. Testing Plan

### A. Neo4j Container Tests

```bash
# Test 1: Container starts correctly
./bin/open-bureau
docker ps | grep neo4j  # Should show neo4j:5 running

# Test 2: Check container logs
docker logs neo4j
# Should show: "Bolt enabled on 0.0.0.0:7687"

# Test 3: GDS plugin loaded
docker exec neo4j cypher-shell -u neo4j -p bureau \
  "RETURN gds.version() AS gdsVersion"
# Should return GDS version

# Test 4: Data persistence
docker stop neo4j && docker start neo4j
# Data should survive restart (volume mount at ~/.neo4j/)
```

### B. MCP Server Tests

```bash
# Test 5: Verify MCP config has Neo4j servers
cat ~/.claude/mcp.json | jq '.mcpServers | keys'
# Should include: neo4j-memory, neo4j-gds, bureau-graph-extras

# Test 6: Verify JSONL Memory MCP is NOT configured
cat ~/.claude/mcp.json | jq '.mcpServers.memory'
# Should be null/missing

# Test 7: mcp-neo4j-memory basic CRUD
# In Claude Code:
# Create entity → search_nodes → verify found → delete → verify gone

# Test 8: gds-agent algorithms
# Create test graph, then run:
# - betweenness_centrality
# - louvain (community detection)
# - shortest_path between two nodes

# Test 9: bureau-graph-extras blast_radius
# Create: A → B → C → D
# Run blast_radius("A")
# Should return: B (distance 1), C (distance 2), D (distance 3)

# Test 10: bureau-graph-extras detect_cycles
# Create: A → B → C → A (cycle)
# Run detect_cycles()
# Should return the cycle path
```

### C. Cleanup Handler Tests

```bash
# Test 11: Stale item detection
cd ~/Code/swe/Bureau/.worktrees/feat-add-graph-memory
uv run python -c "
from operations.cleanup.handlers.neo4j_memory import Neo4jMemoryHandler
from datetime import timedelta

handler = Neo4jMemoryHandler(
    uri='bolt://localhost:7687',
    username='neo4j',
    password='bureau'
)
stale = handler.get_stale_items(retention=timedelta(days=30))
print(f'Found {len(stale)} stale items')
handler.close()
"

# Test 12: Verify handler registration
uv run python -c "from operations.cleanup.handlers import HANDLERS; print([h.backend_name for h in HANDLERS])"
# Should NOT include 'memory_mcp', SHOULD include 'neo4j_memory'
```

### D. Context File Tests

```bash
# Test 13: tools-guide.md has graph memory content
grep "blast_radius" protocols/context/guides/tools-guide.md
# Should find matches

grep "GRAPH INTELLIGENCE PROTOCOL" protocols/context/guides/tools-guide.md
# Should find matches

# Test 14: No JSONL memory references
grep -i "jsonl" protocols/context/guides/tools-guide.md
# Should find NO matches (or only in unrelated context)
```

---

## 3. Gotchas, Edge Cases & Important Checks

### Neo4j Container

| Issue | What to Check |
|-------|---------------|
| **Slow startup** | Neo4j can take 30-60s to initialize. `wait_for_neo4j_ready()` has 60s timeout - may need increase on slow machines |
| **Port conflicts** | If 7687/7474 already in use, container fails silently. Check `docker logs neo4j` |
| **netcat missing** | `nc -z` used for port check. On some systems: `brew install netcat` or `apt install netcat` |
| **GDS plugin not loading** | Verify `NEO4J_PLUGINS='["graph-data-science"]'` syntax - must be JSON array as string |
| **Volume permissions** | `~/.neo4j/` must be writable. Docker may create as root on some systems |

### bureau-graph-extras

| Issue | What to Check |
|-------|---------------|
| **Node label mismatch** | Uses `Memory` label from mcp-neo4j-memory. If that package changes labels, queries break |
| **Empty graph** | `blast_radius` on non-existent entity returns "not found" - verify error message is clear |
| **No outgoing relationships** | Entity with no outgoing edges returns empty affected list (correct behavior) |
| **Large graphs** | `max_depth` defaults to 10. Very deep graphs may need higher limit or timeout handling |
| **Cycle detection performance** | On large graphs, cycle detection can be slow. Limit parameter exists but verify it's respected |

### Cleanup Handler

| Issue | What to Check |
|-------|---------------|
| **Timestamp format** | Expects ISO 8601 with timezone. Memory nodes must have `created_at` observation |
| **Missing timestamps** | Nodes without `created_at` won't be found by stale query. May accumulate |
| **Relationship cleanup** | `DETACH DELETE` removes relationships. Verify this is desired behavior |
| **Large deletions** | Bulk delete on large graphs may timeout. Consider batching |

### Integration Verification

```bash
# Full integration test:

# 1. Start Bureau
./bin/open-bureau

# 2. Verify Neo4j is running
docker ps | grep neo4j

# 3. In Claude Code, create test entities
# mcp__neo4j-memory__create_entities with Memory nodes

# 4. Verify blast_radius works
# mcp__bureau-graph-extras__blast_radius

# 5. Verify cleanup can find them
# Run cleanup handler test from above

# 6. Stop Bureau
./bin/close-bureau

# 7. Verify Neo4j stopped
docker ps | grep neo4j  # Should be empty
```
