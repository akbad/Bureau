# Task execution

## Tool selection

| Operation | Tool | Notes |
| :--- | :--- | :--- |
| OSS code search | Sourcegraph MCP | Use `count:all` for exhaustive; bump timeout for large sets |
| Local semantic/symbol navigation | Serena MCP (`find_symbol`, `get_symbols_overview`) | |
| Local text search | ripgrep/grep | Respects `.gitignore` |
| Web search / current web research | Tavily / Brave when available → Bureau Search (`bureau_search_web`) → open-webSearch → native/built-in web search | Bureau Search is the default local SearXNG path; use open-webSearch as the no-key direct DuckDuckGo/Bing fallback |
| Domain-specific web search | Bureau Search (`bureau_search_code`, `bureau_search_packages`, `bureau_search_research`) | Prefer these semantic profiles over generic web search when the query is clearly code, package, or paper oriented |
| Single known URL fetch | Fetch MCP | Fast static fetch to Markdown; do **not** use on github.com page URLs because they return wrapper HTML |
| Extraction / bounded crawl | Tavily extract/crawl → Crawl4AI MCP | Use Crawl4AI for JS-rendered pages, bounded multi-page crawls, sitemap crawls, or persisted crawl output |
| Browser interaction / auth / visual checks | Playwright MCP | Use when interaction, login state, screenshots, or DOM/browser behavior matter |
| GitHub content | `raw.githubusercontent.com` via Fetch, or `gh` CLI via Bash | |
| API/library docs | Context7 MCP | Versioned, public repos only |
| Read 1-9 files | Native Read tool | Do **not** use Serena `read_file` |
| Read 10+ files | Filesystem MCP `read_multiple_files` | 30-60% token savings |
| Symbol-level refactors | Serena: `replace_symbol_body`, `insert_after/before_symbol`, `rename_symbol` | |
| All other edits | Native Write/Edit tools | |
| Security scans | Semgrep | Local, autofix |

## Memory storage

- Store incrementally throughout work, not just at end.
- **Qdrant MCP** (`qdrant-store`): solutions, patterns, gotchas, root causes, design decisions
- **Memory MCP** (`create_entities`, `create_relations`): components, architecture, data flows, dependencies
- Before completing any task: "would future agents benefit?" → yes = store it.

## Limits

| Tool | Limit | Reset |
| :--- | :--- | :--- |
| Tavily | 1,000 credits/month | 1st of month |
| Brave | 2,000 queries/month | 1st of month |
| Bureau Search / SearXNG | No Bureau API key or quota; local Docker/runtime cost | Localhost-only by default; Google and Google Scholar engines are disabled unless explicitly enabled locally |
| open-webSearch | No Bureau API key or quota | Scraped engine availability, rate limits, and terms still apply |
| Crawl4AI | No API key; local Docker/runtime cost | Keep crawls bounded; default target is small crawls, not whole-site mirroring |
| Sourcegraph | Interactive limits | Use `count:all`; switch to `src-cli` for large sets |
