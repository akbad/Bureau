# MCPs: quick decision guide

- Fast, first-choice tool per task with limits.
- Contains links to:

    - Per-category guides (only look at these if your exact, desired use case is not covered here)
    - Per-MCP deep dives (only look when you need full guidance on the intricacies of using a particular MCP's toolset)

## Code search

- For going through **public, open-source code**: use Sourcegraph ([deep dive](deep-dives/sourcegraph.md)) to find examples/patterns (interactive time/result limits)
- **Within local codebases**:

    - For **semantic navigation/symbol-level refactors**: use Serena MCP ([deep dive](deep-dives/serena.md))
    - For **simple text searches**: use ripgrep/grep to find plain text/regex matches fast (respects .gitignore)

> Link: [Full category guide - *code search*](by-category/code-search.md)

## Web research

- For **general web info**: use Tavily (cited results; 1k/mo) ([deep dive](deep-dives/tavily.md))

    - Fallback if *Tavily is exhausted*: use Brave (2k/mo) ([deep dive](deep-dives/brave.md))

    - Fallback if *Tavily and Brave are exhausted*: use Playwright to use the browser to search the web (unlimited)

- For **simple URL fetches**: use Fetch (unlimited) ([deep dive](deep-dives/fetch.md))

> Link: [full category guide - *web research*](by-category/web-research.md)

## GitHub access

> [!CAUTION]
> **DON'T** use Fetch MCP on `github.com` URLs: it returns page navigation/wrapper HTML, not file content.

**For GitHub file content:**

| Desired use case | Best method | Notes |
|----------|-------------|-------|
| **Raw file content** | Fetch MCP on `raw.githubusercontent.com/<user>/<repo>/<branch>/<path>` | Direct, fast, reliable |
| **Files via API** | `gh api repos/<owner>/<repo>/contents/<path>` via Bash | Decode with `--jq '.content' \| base64 -d` |
| **PRs, issues, comments** | `gh` CLI via Bash | Full GitHub API access |
| **Code search (public repos)** | Sourcegraph MCP | Best for pattern/example discovery |
| **Page content extraction** | WebFetch on `github.com/*` | AI extracts meaningful content from rendered page |
| **Complex interactions** | Playwright | Full browser automation fallback |
| **Deep local analysis** | Clone + Git/Serena MCP | Best for comprehensive codebase work |

## API docs

- For **official documentation**: use Context7 (versioned; public repos only) ([deep dive](deep-dives/context7.md))

> Link: [full category guide - *API docs*](by-category/documentation.md)

## Memory

### Tool Selection by Purpose

| Purpose | MCP | Key Tools |
|---------|-----|-----------|
| **Entity/relation CRUD** | neo4j-memory | `create_entities`, `create_relations`, `search_nodes`, `read_graph` |
| **Graph algorithms** | neo4j-gds | `betweenness_centrality`, `louvain`, `shortest_path` |
| **Impact analysis** | bureau-graph-extras | `blast_radius`, `detect_cycles` |
| **Semantic search** | Qdrant | `qdrant-find` (patterns, solutions, gotchas) |

### MANDATORY MEMORY RETRIEVAL PROTOCOL

> [!IMPORTANT]
> **You MUST check memories at the START of EVERY task.**

**Before starting ANY task, you MUST:**

1. **Query graph memory for context:**

   - neo4j-memory (`read_graph`, `search_nodes`) - for entities, relations, architecture
   - Qdrant MCP (`qdrant-find`) - for past solutions, patterns, gotchas, learnings
   - claude-mem (`get_recent_context`, `search_observations`) **(*ONLY* if you are Claude Code)** for recent session history

2. **Assess change impact BEFORE modifying:**

   - **ALWAYS** run `blast_radius(entity)` before changing any significant entity
   - Understand downstream effects before making changes
   - If impact is large, consider breaking into smaller changes

3. **Verify memory accuracy BEFORE trusting it:**

   - Compare memory timestamps with file modification dates
   - If memory references specific files/code → Read those files to verify
   - If memory describes system behavior → Test/verify it's still true
   - **Older memories are MORE LIKELY to be stale** - verify aggressively

4. **Update or delete incorrect memories immediately:**

   - Found stale info? → Overwrite with current truth
   - Found obsolete relationships? → Delete and recreate
   - Found incorrect patterns? → Store the correction

**This is NOT OPTIONAL. This is NOT NEGOTIABLE.**

**Starting work with stale memories = building on false assumptions = failure.**

### MANDATORY MEMORY STORAGE PROTOCOL

**You MUST store memories after ANY task involving:**
- Analysis/investigation (code patterns, repository structure, bugs, performance issues)
- Thinking/reasoning (design decisions, trade-offs, alternatives considered)
- Derivation of results (calculations, conclusions, recommendations)
- Problem-solving (solutions found, approaches that failed, workarounds)
- Discovery (undocumented behavior, quirks, gotchas, lessons learned)

**This is NOT OPTIONAL. This is NOT NEGOTIABLE.**

**Before finishing ANY task, ask yourself:**
1. Did I analyze something? → Store in Qdrant
2. Did I discover relationships? → Store in neo4j-memory
3. Would future agents benefit from knowing this? → Store it

**Failure to store memories = failure to complete the task.**

> [!TIP]
>
> **Storage decision tree:**
>
> - **Qdrant MCP**: Code patterns, solutions, gotchas, insights, "how I solved X"
> - **neo4j-memory**: Who/what/how relationships, project structure, dependencies
> - **Both**: Complex problems (store solution in Qdrant, track entities/relations in neo4j-memory)

> [!IMPORTANT]
>
> When storing memories, *always* include these metadata fields:
>
> | Memory storage tool | Metadata field to include |
> | --- | --- |
> | Qdrant MCP | `metadata.created_at` (ISO 8601, UTC, e.g., `2025-12-05T21:10:00+00:00`) |
> | neo4j-memory | `created_at` observation on each entity |
> | Serena MCP | *None required; automatically created* |
> | claude-mem (Claude Code *only*) | *None required; automatically created* |

### GRAPH INTELLIGENCE PROTOCOL

**Use graph algorithms strategically - they are powerful but have cost:**

| Scenario | Tool | Why |
|----------|------|-----|
| **Before significant changes** | `blast_radius(entity)` | Understand all downstream effects |
| **Debugging dependency issues** | `detect_cycles()` | Find circular dependencies causing problems |
| **Finding critical components** | `betweenness_centrality` | Identify bottleneck entities that many paths flow through |
| **Understanding architecture** | `louvain` | Discover natural clusters/modules in the graph |
| **Tracing connections** | `shortest_path` | Find how two entities are connected |

> [!CAUTION]
>
> **DO NOT** run expensive graph algorithms (centrality, community detection) on every task.
> Use them when:
> - Onboarding to a new codebase
> - Debugging architectural issues
> - Planning major refactors
> - The simpler tools (`search_nodes`, `blast_radius`) aren't sufficient

> Link: [full category guide - *memory MCPs*](by-category/memory.md)

## Code analysis, editing and Git

### Reads and exploration

| Desired operation | Method/tool | Extra notes |
| --- | --- | --- |
| **Read: *1-9 files*** | Use your native/built-in Read tool | Do NOT use `serena.read_file`: it adds overhead |
| **Read: *10+ files*** | Use Filesystem MCP's `read_multiple_files` | For bulk reads, this method results in 30-60% token savings compared to the native/built-in tool |
| **Directory tree exploration** | `ls -R` or `find` via Bash |
| Understanding code **symbols** (classes/methods) | Serena MCP's `find_symbol` with `include_body=true` |

### Writes & edits

- For symbol-level operations and refactors *only*, use the following Serena tools:

    | Symbol-level operation | Serena MCP tool to use |
    | --- | --- |
    | Replacing **entire symbol** | `replace_symbol_body` (NOT for 1-line edits) |
    | Adding **new symbol** | `insert_after_symbol` / `insert_before_symbol` |
    | **Renaming symbol** *codebase-wide* | `rename_symbol` |

- For *all other operations*, default to your **native/built-in Write/Edit tool(s)**.

> [!TIP]
>
> To resolve any remaining ambiguities, see the [Serena deep dive](deep-dives/serena.md) for the *full* decision tree for symbol vs text-based editing.

### Git operations

Use (via Bash):

- `git` *(primarily)*
- `gh` *(where appropriate)*

### Security and quality scans

Use **Semgrep** (local scans; autofix) *(for more info, see the [Semgrep deep dive](deep-dives/semgrep.md))*

## Browser automation

- For **web automation and testing**: use Playwright (click, type, navigate, extract content) ([deep dive](deep-dives/playwright.md))

> Link: [full category guide - *browser automation*](by-category/browser-automation.md)

## Limits

All non-listed MCPs are local and/or have no usage limits.

| Tool        | Limit                    | Reset/Notes                                    |
|-------------|--------------------------|------------------------------------------------|
| Tavily      | 1,000 credits/month      | Resets on 1st of month                        |
| Brave       | 2,000 queries/month      | Free tier; basic web search                    |
| Sourcegraph | Interactive limits       | use count:all to make the search exhaustive, bump timeout if needed; switch to src-cli for very large result sets beyond the UI display limit. |
