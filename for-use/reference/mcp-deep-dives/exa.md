# Exa MCP: Deep Dive

## Critical Warning

**$10 ONE-TIME CREDIT** - New account/API key required after exhaustion. Use sparingly for semantic search only.

## Available Tools

### 1. `web_search_exa` - Neural Semantic Search

**What it does:** AI-native semantic search optimized for LLMs

**Parameters:**
- `query` (required) - Semantic search query
- `numResults` (default 5) - Number of results to return

**Returns:** Search results with AI-formatted content

**Best for:** Semantic/conceptual queries, knowledge discovery

**Cost:** Varies per search (from $10 one-time credit)

### 2. `get_code_context_exa` - Code-Specific Context

**What it does:** Search and retrieve context for programming tasks

**Parameters:**
- `query` (required) - Programming-related query
- `tokensNum` (default 5000, range 1000-50000) - Context length

**Returns:** Relevant code context for APIs, libraries, SDKs

**Best for:** Library documentation, API usage, code examples

**Cost:** Varies by tokens requested

**Note:** Has highest quality, freshest context for programming

## Tradeoffs

### Advantages
✅ **Neural search** (semantic understanding, not keywords)
✅ **AI-optimized results** (formatted for LLM consumption)
✅ **Superior for research** and knowledge discovery
✅ **Code-specific tool** (get_code_context_exa)
✅ Better than keyword search for conceptual queries

### Disadvantages
❌ **$10 one-time credit** (no monthly reset)
❌ **Permanent consumption** (like Firecrawl)
❌ **New account needed** after exhaustion
❌ No citations included
❌ No built-in extraction/crawling

## Common Pitfalls: When NOT to Use

### ❌ Simple Keyword Search
**Problem:** Wastes limited credits on task keyword search handles
**Alternative:** Tavily or Brave

**Example:**
```
Bad:  exa_search("Python pandas documentation")
Good: tavily_search("Python pandas documentation")
```

### ❌ Factual Lookup
**Problem:** Simple facts don't need semantic understanding
**Alternative:** Tavily (with citations)

**Example:**
```
Bad:  exa_search("What is the capital of France?")
Good: tavily_search("What is the capital of France?")
```

### ❌ Current Events/News
**Problem:** Exa not optimized for news, Tavily has news topic
**Alternative:** Tavily with topic="news"

**Example:**
```
Bad:  exa_search("latest AI developments 2024")
Good: tavily_search("latest AI developments 2024", topic="news")
```

### ❌ Need Content Extraction
**Problem:** Exa only returns search results, not extracted content
**Alternative:** Tavily extract or Fetch

**Example:**
```
Bad:  exa_search + manual URL fetching
Good: tavily_search + tavily_extract
```

### ❌ Official API Documentation
**Problem:** Context7 provides structured, version-specific docs
**Alternative:** Context7

**Example:**
```
Bad:  get_code_context_exa("Next.js routing API")
Good: context7.get_library_docs("/vercel/next.js", topic="routing")
```

### ❌ Multiple Similar Queries
**Problem:** Each query consumes permanent credit
**Alternative:** Combine into one comprehensive query

**Example:**
```
Bad:  exa_search("CQRS") + exa_search("Event sourcing") + exa_search("Saga pattern")
Good: exa_search("CQRS, event sourcing, and saga patterns explained")
```

## When Exa IS the Right Choice

✅ **Semantic/conceptual queries** that keyword search fails
✅ **Knowledge discovery** (find related concepts)
✅ **Research requiring deep understanding**
✅ **Tavily failed** to find what you need
✅ **Task justifies** using permanent credit

**Decision rule:** "Did Tavily fail, and do I need semantic understanding?"

## Usage Pattern

**Ideal workflow:**
1. Try Tavily first (1k/month, resets)
2. If results insufficient, evaluate if semantic search needed
3. If yes, use Exa (but be mindful of permanent credit)

**Example use cases:**
```
"Architectural patterns similar to event sourcing"
→ Exa finds CQRS, saga, outbox pattern

"Modern alternatives to REST APIs"
→ Exa finds GraphQL, gRPC, tRPC, WebSockets

"Authentication architectures for microservices"
→ Exa finds JWT, OAuth2, service mesh, mTLS
```

## Alternatives Summary

| Task | Instead of Exa | Use This |
|------|---------------|----------|
| Keyword search | web_search_exa | Tavily / Brave |
| Factual lookup | web_search_exa | Tavily |
| News/current events | web_search_exa | Tavily (topic="news") |
| Content extraction | web_search_exa | Tavily extract |
| API documentation | get_code_context_exa | Context7 |
| Code examples | get_code_context_exa | Sourcegraph |

## Best Practices

**Preserve limited credit:**
- **Always try Tavily first** (monthly reset)
- Use Exa only when semantic search needed
- Combine related queries into one
- Monitor remaining balance

**Optimize queries:**
- Be specific about what you want to find
- Frame queries conceptually, not as keywords
- Ask for relationships/alternatives/patterns

**When to use get_code_context_exa:**
- Need fresh context for new libraries
- Context7 lacks the library
- Semantic code search needed
- Adjust `tokensNum` based on depth needed

**Track usage:**
- No built-in counter
- Estimate costs manually
- Stop before exhausting credit
- Plan for new account if needed

## Quick Reference

**Total budget:** $10 one-time credit
**Rate limits:** None apparent (credit-based)
**Reset:** Never (new account required)
**Cost:** ~$0.X per search (varies)

**Best for:** Semantic search when Tavily insufficient
**Avoid for:** Keyword search, news, factual lookup

**Links:**
- [Category guide: Web research](../category/web-research.md)
- [Full decision guide](../../../mcps/tools-decision-guide.md)
