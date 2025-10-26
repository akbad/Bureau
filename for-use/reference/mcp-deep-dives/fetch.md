# Fetch MCP: Deep Dive

## Overview

Simple, unlimited HTTP/HTTPS URL fetching. Converts HTML to Markdown. No rate limits, no complexity.

## Available Tools

### 1. `fetch` - Fetch URL Content

**What it does:** Fetches content from a URL and optionally converts HTML to Markdown

**Parameters:**
- `url` (required) - Target URL (HTTP/HTTPS)
- `raw` (bool, default false) - Return raw HTML vs. Markdown
- `max_length` (default 5000, max 1000000) - Max characters to return
- `start_index` (default 0) - Start position for chunk reading

**Returns:** Content in Markdown (default) or raw HTML

**Best for:** Simple one-off URL fetches with unlimited usage

**Rate limits:** None

## Tradeoffs

### Advantages
✅ **Unlimited usage** (no rate limits)
✅ **Simple and fast** (no complexity)
✅ **HTML → Markdown** conversion (LLM-friendly)
✅ **Chunk reading** via start_index (handle long content)
✅ **No credits/costs** to track

### Disadvantages
❌ **No GitHub.com support** (use raw.githubusercontent.com)
❌ **No search** capabilities (just fetching)
❌ **No crawling** (one URL at a time)
❌ **No JavaScript** rendering (static content only)
❌ **No extraction** features (just raw content)

## Common Pitfalls: When NOT to Use

### ❌ GitHub.com URLs
**Problem:** Fetch doesn't support github.com
**Alternative:** raw.githubusercontent.com, gh CLI, or Sourcegraph

**Example:**
```
Bad:  fetch("https://github.com/user/repo/blob/main/file.js")
Good: fetch("https://raw.githubusercontent.com/user/repo/main/file.js")
Good: sourcegraph.search("repo:user/repo file.js")
Good: gh api repos/user/repo/contents/file.js
```

### ❌ Web Search Needed
**Problem:** Fetch requires knowing the URL
**Alternative:** Tavily or Brave

**Example:**
```
Bad:  fetch("?") # Don't know URL
Good: tavily_search("topic") → get URLs → fetch if needed
```

### ❌ Multi-Page Content
**Problem:** Fetch handles one URL at a time
**Alternative:** Tavily extract (batch) or Tavily crawl

**Example:**
```
Bad:  fetch(url1) + fetch(url2) + fetch(url3) # Multiple calls
Good: tavily_extract([url1, url2, url3]) # Batch extraction
```

### ❌ JavaScript-Heavy Sites
**Problem:** Fetch doesn't render JavaScript
**Alternative:** Firecrawl (if content requires JS rendering)

**Example:**
```
Bad:  fetch("https://spa-app.com") # Returns empty shell
Good: firecrawl_scrape("https://spa-app.com") # Renders JS
```

### ❌ Structured Data Extraction
**Problem:** Fetch returns raw content, no extraction
**Alternative:** Firecrawl extract with schema

**Example:**
```
Bad:  fetch + manual parsing
Good: firecrawl_extract with JSON schema
```

### ❌ Need Citations
**Problem:** Fetch just fetches, doesn't verify or cite
**Alternative:** Tavily (includes citations)

**Example:**
```
Bad:  fetch random URLs from search
Good: tavily_search (returns cited sources)
```

## When Fetch IS the Right Choice

✅ **Known URL**, simple content fetch
✅ **Unlimited usage** needed (no credit concerns)
✅ **Static HTML** content
✅ **No search/crawl** required
✅ **After exhausting** Tavily/Brave credits

**Decision rule:** "Do I know the exact URL and is it simple HTML?"

## Usage Patterns

**Basic fetch:**
```
fetch("https://example.com/article")
→ Returns Markdown content
```

**Raw HTML:**
```
fetch("https://example.com/page", raw=true)
→ Returns original HTML
```

**Chunk reading (long content):**
```
fetch("https://example.com/long-doc", max_length=5000, start_index=0)
→ First 5000 chars

fetch("https://example.com/long-doc", max_length=5000, start_index=5000)
→ Next 5000 chars
```

**GitHub files:**
```
fetch("https://raw.githubusercontent.com/user/repo/main/README.md")
→ Works (raw.githubusercontent.com)

fetch("https://github.com/user/repo/blob/main/README.md")
→ Fails (github.com not supported)
```

## Alternatives Summary

| Task | Instead of Fetch | Use This |
|------|-----------------|----------|
| GitHub.com URLs | fetch | raw.githubusercontent.com / gh CLI / Sourcegraph |
| Web search | fetch | Tavily / Brave |
| Multi-page | fetch multiple | Tavily extract |
| JS-heavy sites | fetch | Firecrawl scrape |
| Structured extraction | fetch | Firecrawl extract |
| Need citations | fetch | Tavily |

## Best Practices

**Use Fetch when:**
- You have the exact URL
- Content is static HTML
- No credit/limit concerns
- Simple one-off fetch

**Optimize with Fetch:**
- Use `max_length` for long content
- Use `start_index` for pagination
- Check `raw=true` if Markdown conversion fails
- Combine with other tools for full workflow

**Common workflow:**
1. Tavily search → Find URLs
2. Fetch → Get content from found URLs (save credits)
3. Or: Skip Fetch, use Tavily extract if credits available

**GitHub workflow:**
```
Known file: fetch from raw.githubusercontent.com
Search code: Use Sourcegraph
API access: Use gh CLI
Repo analysis: Clone + Git MCP + Serena
```

## Quick Reference

**Rate limits:** None (unlimited)
**Cost:** Free
**Best for:** Simple, known URL fetches
**Avoid for:** github.com, search, crawl, JS sites

**URL format for GitHub:**
```
❌ https://github.com/user/repo/blob/branch/file
✅ https://raw.githubusercontent.com/user/repo/branch/file
```

**Links:**
- [Category guide: Web research](../category/web-research.md)
- [Full decision guide](../../../mcps/tools-decision-guide.md)
