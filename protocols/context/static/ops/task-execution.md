<task-execution>

  <tool-selection>
    | Operation | Tool | Notes |
    |---|---|---|
    | OSS code search | Sourcegraph MCP | Use count:all for exhaustive; bump timeout for large sets |
    | Local semantic/symbol navigation | Serena MCP (find_symbol, get_symbols_overview) | |
    | Local text search | ripgrep/grep | Respects .gitignore |
    | Web research | Tavily → Brave (fallback) → your native/built-in web search tools | |
    | Simple URL fetch | Fetch MCP | Do NOT use on github.com — returns wrapper HTML |
    | GitHub content | raw.githubusercontent.com via Fetch, or gh CLI via Bash | |
    | API/library docs | Context7 MCP | Versioned, public repos only |
    | Read 1-9 files | Native Read tool | Do NOT use Serena read_file |
    | Read 10+ files | Filesystem MCP read_multiple_files | 30-60% token savings |
    | Symbol-level refactors | Serena: replace_symbol_body, insert_after/before_symbol, rename_symbol | |
    | All other edits | Native Write/Edit tools | |
    | Security scans | Semgrep | Local, autofix |
  </tool-selection>

  <memory-storage>
    Store incrementally throughout work, not just at end.
    - Qdrant MCP (qdrant-store): solutions, patterns, gotchas, root causes, design decisions
    - Memory MCP (create_entities, create_relations): components, architecture, data flows, dependencies
    - Before completing any task: "Would future agents benefit?" → yes = store it
  </memory-storage>

  <limits>
    | Tool | Limit | Reset |
    |---|---|---|
    | Tavily | 1,000 credits/month | 1st of month |
    | Brave | 2,000 queries/month | 1st of month |
    | Sourcegraph | Interactive limits | Use count:all; switch to src-cli for large sets |
  </limits>

</task-execution>
