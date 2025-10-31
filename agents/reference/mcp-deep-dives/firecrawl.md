# Firecrawl MCP: Deep Dive

## Critical Warning

**500 LIFETIME LIMIT** - New account/API key required after exhaustion. Every use is permanent.

## Available Tools

### 1. `firecrawl_scrape` - Single Page Content Extraction

**What it does:** Scrapes content from a single URL with advanced options

**Parameters:**
- `url` (required) - Target URL
- `formats` - Array: `["markdown", "html", "rawHtml", "screenshot", "links", "summary"]`
- `onlyMainContent` (bool) - Filter to main content only
- `includeTags` / `excludeTags` - HTML tag filtering
- `waitFor` (ms) - Wait time before scraping
- `maxAge` (ms) - Use cached data if available (500% faster)

**Returns:** Content in specified formats

**Best for:** Single-page extraction with advanced filtering

**Rate limits:** 10/min, uses 1 credit per call

### 2. `firecrawl_crawl` - Multi-Page Deep Crawling

**What it does:** Recursively crawls website starting from base URL

**Parameters:**
- `url` (required) - Starting URL
- `limit` - Max pages to crawl
- `maxDiscoveryDepth` - How far from base URL
- `includePaths` / `excludePaths` - URL patterns to filter
- `scrapeOptions` - Same options as scrape
- `allowExternalLinks` (bool) - Follow external domains
- `deduplicateSimilarURLs` (bool) - Avoid near-duplicates

**Returns:** Job ID for status checking

**Best for:** Multi-page content extraction (10+ pages)

**Rate limits:** 1/min, uses 1+ credits (depends on pages)

### 3. `firecrawl_map` - URL Discovery

**What it does:** Maps website structure without extracting content

**Parameters:**
- `url` (required) - Root URL
- `search` - Filter URLs by search term
- `limit` - Max URLs to return
- `includeSubdomains` (bool)
- `ignoreQueryParameters` (bool)

**Returns:** Array of discovered URLs

**Best for:** Understanding site structure before scraping

**Rate limits:** Included in credit system

### 4. `firecrawl_search` - Web Search with Scraping

**What it does:** Search web and optionally scrape results

**Parameters:**
- `query` (required) - Search query
- `limit` - Max results
- `sources` - Array: `["web", "images", "news"]`
- `scrapeOptions` - Apply scraping to results

**Returns:** Search results with optional scraped content

**Best for:** Finding + extracting content in one operation

**Rate limits:** Uses credits based on scrape options

### 5. `firecrawl_extract` - Structured Data Extraction

**What it does:** Extract structured data using LLM + schema

**Parameters:**
- `urls` (required) - Array of URLs
- `prompt` - Custom extraction prompt
- `schema` - JSON schema for structured output
- `allowExternalLinks` (bool)
- `enableWebSearch` (bool) - Add web search context

**Returns:** Structured data matching schema

**Best for:** Extracting specific fields (prices, names, dates)

**Rate limits:** Uses credits per URL

### 6. `firecrawl_check_crawl_status` - Monitor Crawl Jobs

**What it does:** Check status of background crawl

**Parameters:**
- `id` (required) - Job ID from crawl

**Returns:** Status and results if complete

## Tradeoffs

### Advantages
✅ Most powerful web scraping capabilities
✅ Handles JavaScript-heavy sites
✅ Batch operations across many pages
✅ Structured extraction with LLM
✅ Caching for faster repeated scrapes

### Disadvantages
❌ **500 lifetime limit (critical)**
❌ Permanent credit consumption
❌ Slower than simpler tools
❌ Overkill for simple tasks
❌ No warning when approaching limit

## Common Pitfalls: When NOT to Use

### ❌ Single URL Scraping
**Problem:** Wastes permanent credit on simple task
**Alternative:** Use Fetch MCP (unlimited) or Tavily extract

**Example:**
```
Bad:  firecrawl_scrape("https://example.com/article")
Good: fetch("https://example.com/article")
```

### ❌ Known URL List Extraction
**Problem:** Batch extraction uses multiple permanent credits
**Alternative:** Tavily extract or Fetch iteratively

**Example:**
```
Bad:  firecrawl_extract(["url1", "url2", "url3"])
Good: tavily_extract(["url1", "url2", "url3"])
```

### ❌ Simple Web Search
**Problem:** Search doesn't require Firecrawl's advanced features
**Alternative:** Tavily search (1k/mo) or Brave (2k/mo)

**Example:**
```
Bad:  firecrawl_search("React hooks tutorial")
Good: tavily_search("React hooks tutorial")
```

### ❌ Documentation Lookup
**Problem:** Structured docs don't need crawling
**Alternative:** Context7 for APIs, Tavily for tutorials

**Example:**
```
Bad:  firecrawl_crawl("https://docs.library.com/*")
Good: context7.get_library_docs("/library/docs")
```

### ❌ GitHub Content
**Problem:** GitHub has better alternatives
**Alternative:** Sourcegraph, gh CLI, or raw.githubusercontent.com

**Example:**
```
Bad:  firecrawl_scrape("https://github.com/user/repo")
Good: sourcegraph.search("repo:user/repo")
```

## When Firecrawl IS the Right Choice

✅ **Deep multi-page crawls (50+ pages)** that Tavily can't handle
✅ **Complex JavaScript sites** that Fetch can't render
✅ **Batch structured extraction** where LLM+schema is needed
✅ **Site mapping** before selective scraping (use map first)
✅ **Deduplication needed** across similar URLs

**Decision rule:** "Have I tried Tavily, Fetch, and Sourcegraph first?"

## Alternatives Summary

| Task | Instead of Firecrawl | Use This |
|------|---------------------|----------|
| Single URL | scrape | Fetch MCP |
| Web search | search | Tavily / Brave |
| Multi-URL extract | extract | Tavily extract |
| API docs | crawl docs site | Context7 |
| Code examples | crawl GitHub | Sourcegraph |
| Simple crawl (5-10 pages) | crawl | Tavily crawl |

## Best Practices

**Always check alternatives first:**
1. Fetch - Can it handle this URL?
2. Tavily - Can search/extract/crawl do this?
3. Sourcegraph - Is this code-related?
4. Context7 - Is this API documentation?

**Use Firecrawl only when:**
- Other tools explicitly failed
- Task requires unique Firecrawl capabilities
- Permanent credit cost is justified

**Track usage manually:**
- No built-in counter
- Estimate: scrape=1, crawl=1+ per page
- Stop at ~450 to preserve buffer

**Optimize when using:**
- Use `maxAge` for caching (500% faster)
- Use `map` first to understand structure
- Set tight `limit` and `maxDiscoveryDepth`
- Use `includePaths`/`excludePaths` to filter

## Quick Reference

**Total budget:** 500 lifetime credits
**Rate limits:** 10 scrapes/min, 1 crawl/min
**Reset:** Never (new account required)
**Cost:** ~$0.02 per credit (free plan)

**Links:**
- [Category guide: Web research](../category/web-research.md)
- [Full decision guide](../../../tools/tools-decision-guide.md)
