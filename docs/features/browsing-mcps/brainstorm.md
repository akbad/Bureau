# *Ideation:* adding new browsing MCPs

## `web-search-mcp`

- **Docs:**

    - **Repository / primary README:** <https://github.com/mrkrsl/web-search-mcp>
    - **Technical API doc:** <https://github.com/mrkrsl/web-search-mcp/blob/main/docs/API.md>

- **Why this MCP was chosen:**

    - It directly addresses the exact gap in Bureau's current browsing stack: once Tavily and Brave are unavailable or exhausted, we currently fall straight to raw Playwright with no search-specific abstraction.
    - It preserves the most important capability we lose at that point, which is **structured general web search**, rather than only browser control.
    - It is attractive as a fallback because the server is designed to work **without API keys**, which makes it materially different from Tavily and Brave rather than a weaker paid clone.
    - It gives us an **"unlimited local fallback"** story instead of a second API that can also hit quotas.

- **What functionality it offers:**

    - It exposes **three distinct tools** rather than one catch-all surface.

        - `full-web-search` is the comprehensive mode.
        - `get-web-search-summaries` is the lightweight mode.
        - `get-single-web-page-content` is the direct URL extraction mode.

    - Its search strategy is explicitly **multi-engine**.

        - The current README says it prioritizes **Bing**, then **Brave**, then **DuckDuckGo**.
        - That matters because it reduces the chance that a single engine outage or blocking pattern makes the fallback useless.

    - Its extraction path is more thoughtful than "search page + click around manually".

        - It first tries **fast HTTP extraction**.
        - It then falls back to **browser-based extraction** when needed.
        - It includes **concurrent extraction**, **timeout protection**, and **HTTP/2 -> HTTP/1.1 recovery**.

    - It also exposes several **runtime tuning knobs** that are genuinely useful in a Bureau context.

        - Content size control via `MAX_CONTENT_LENGTH`.
        - Timeout control via `DEFAULT_TIMEOUT`.
        - Browser pool control via `MAX_BROWSERS`.
        - Search-quality tuning via `ENABLE_RELEVANCE_CHECKING` and `RELEVANCE_THRESHOLD`.
        - Engine strategy tuning via `FORCE_MULTI_ENGINE_SEARCH`.

- **Why this functionality is valuable for Bureau specifically:**

    - Bureau already has **good API-backed search**.

        - Tavily gives us search, extraction, crawl, and research.
        - Brave gives us broad web search plus news, local, image, and video variants.

    - The real missing piece is not "yet another premium search API".

        - The real missing piece is a **general-search fallback that remains ergonomic after quotas are gone**.

    - `web-search-mcp` fits that role well because it is best understood as a **search abstraction layer over local browser automation**, not as a competitor to Tavily's richer API surface.

    - That makes it a better conceptual replacement for **raw Playwright fallback** than for **Tavily itself**.

- **Tradeoffs and limitations:**

    - It is **heavier** than the current remote API options.

        - It requires Node.js, npm dependencies, and Playwright browser installation.
        - That increases first-time setup cost and local disk/runtime footprint.

    - It is not presented in its README as a universal, battle-tested MCP across all coding CLIs.

        - The current README says it has been developed and tested with **LM Studio** and **LibreChat**.
        - That means we should treat compatibility with Claude Code, Codex, Gemini CLI, and OpenCode as something Bureau must validate itself.

    - It is not a feature-for-feature substitute for Brave or Tavily.

        - I did **not** find first-class equivalents in the current docs for Brave's separate **news**, **local**, **image**, or **video** tools.
        - I also did **not** see Tavily-style research or crawl workflows exposed as first-class tools.
        - Because of that, it should be positioned as a **broad general-search fallback**, not as a complete replacement for the existing browsing stack.

    - Its extraction-rich default can become **token-expensive** if used carelessly.

        - `full-web-search` is useful when the agent genuinely needs page bodies.
        - `get-web-search-summaries` should likely be the Bureau-preferred first call for fast lookup and cost control.

- **Why it is still a strong candidate despite those tradeoffs:**

    - The tradeoffs are mostly **operational**, not **architectural**.
    - Bureau already has strong machinery for installing local MCPs and guiding agents toward the right tool for the right step.
    - If we integrate it carefully, we gain a fallback that feels like **"still using a search tool"** instead of **"now manually drive a browser"**.

- **Practical Bureau-facing implications:**

    - This candidate is a good fit for the **search tier** of the fallback chain.
    - It is especially compelling when we want a fallback that remains useful **after both Tavily and Brave are unavailable**.
    - It is probably best added with clear guidance that agents should prefer:

        - Tavily first for richer structured research.
        - Brave second for specialized search verticals.
        - `web-search-mcp` when the job is still fundamentally **general search**, but quotas or provider availability make API search unavailable.


## `crawl4ai-mcp-server`

- **Docs:**

    - **Repository / MCP server README:** <https://github.com/sadiuysal/crawl4ai-mcp-server>
    - **Underlying Crawl4AI docs:** <https://docs.crawl4ai.com/>

- **Why this MCP was chosen:**

    - It solves a **different problem** from `web-search-mcp`, which is exactly why it is a strong companion candidate rather than a redundant one.
    - The main gap it addresses is **high-quality extraction and controlled site crawling**, especially for pages where simple fetching is noisy or incomplete.
    - It gives us a more principled answer than raw Fetch when we need:

        - JavaScript-rendered pages.
        - Boilerplate reduction.
        - Multi-page traversal.
        - Site- or sitemap-scoped collection.

    - That makes it a natural candidate for the **extraction/crawl tier**, not the search tier.

- **What functionality it offers:**

    - It exposes **four tools** with clean separation of concerns.

        - `scrape` for one-page extraction.
        - `crawl` for bounded breadth-first crawling.
        - `crawl_site` for larger persisted site crawls.
        - `crawl_sitemap` for sitemap-driven collection.

    - Its feature set is broader than "return me markdown from a URL".

        - It supports **depth-controlled crawling**.
        - It supports **adaptive crawling**, which can stop once enough useful content has been collected.
        - It supports **URL include/exclude filtering**.
        - It supports **persistence to disk** via `output_dir` for larger runs.

    - It also brings **safety-oriented behavior**.

        - The README explicitly calls out blocking **localhost**, **private IPs**, and **internal networks**.

    - It is built on top of **Crawl4AI + Playwright**, which is important for modern web content.

        - That gives it a better shot than plain fetch tools on client-rendered documentation sites and JS-heavy content.

- **Why this functionality is valuable for Bureau specifically:**

    - Bureau already has a simple single-URL fetch path via Fetch.
    - Bureau also has Tavily, which can search, extract, crawl, and research when quotas are available.
    - The missing resilience story is what happens when we want **cleaner extraction or deeper site traversal without relying on Tavily credits**.

    - `crawl4ai-mcp-server` fills that resilience gap well because it gives us:

        - A **better self-hosted extraction tool** than raw Fetch.
        - A **real crawl primitive** that does not depend on Tavily remaining available.
        - A way to treat crawling as a first-class capability instead of improvising with Playwright loops.

- **Tradeoffs and limitations:**

    - It is **not a search engine**.

        - It does not replace Tavily or Brave for broad discovery.
        - It becomes useful once we already have a URL, a seed site, or a sitemap.

    - It is operationally heavier than Fetch.

        - The recommended path is Docker.
        - Manual installation requires a Python environment plus Playwright browser setup.

    - Some of its strongest workflows are more powerful than we often need.

        - `crawl_site` and `crawl_sitemap` are excellent for documentation harvests.
        - They are overkill for quick one-off page lookups.

    - Persistence is a strength, but it also adds surface area.

        - `output_dir`-based workflows are useful for larger runs and handoffs.
        - They also mean the tool can create files, manifests, and stored crawl outputs that Bureau should name and manage carefully.

- **Why it is still a strong candidate despite those tradeoffs:**

    - The tradeoffs are exactly the tradeoffs of a **real crawler**, not signs that the MCP is poorly chosen.
    - Bureau does not need another shallow one-page fetcher.
    - Bureau needs a fallback that can reliably do the jobs that agents eventually end up forcing onto Tavily, Fetch, or raw Playwright.

- **Practical Bureau-facing implications:**

    - This candidate makes the most sense as an **extraction and crawl fallback**, not as a general search fallback.
    - It is especially strong for:

        - Documentation sites.
        - Blogs or articles with noisy chrome.
        - JS-rendered pages.
        - "Explore this site/section" tasks.
        - Sitemap-driven harvesting.

    - It likely pairs best with a policy like:

        - Use Tavily when available and the task is broad or research-heavy.
        - Use Fetch for the fastest simple one-page retrieval.
        - Use `crawl4ai-mcp-server` when content quality, rendering, or multi-page traversal matter enough that Fetch is no longer a good fit.

- **Why this pair makes sense together:**

    - `web-search-mcp` gives us a stronger **search fallback**.
    - `crawl4ai-mcp-server` gives us a stronger **extraction/crawl fallback**.
    - They are complementary rather than overlapping, which is exactly what we want in a fallback stack that should remain mentally simple.
