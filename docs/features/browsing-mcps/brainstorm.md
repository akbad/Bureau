# *Ideation:* adding new browsing MCPs

## Updated search-tier verdict <ins>(as of April 1, 2026)</ins>

- After a wider sweep, `web-search-mcp` still looks like a **good description of the problem we want to solve**, but it no longer looks like the healthiest repository to standardize on.
- The strongest replacements I found are:

    - `open-webSearch` as the best **no-key, low-friction, direct replacement**.
    - `mcp-searxng` as the best **self-hosted and strategically cleaner replacement** if we are willing to operate SearXNG.
    - `one-search-mcp` as the most interesting **browser-backed hybrid**, but heavier and less search-tier-pure than the two options above.

- The main reason the market still feels thin is that the healthiest projects are increasingly either:

    - **vendor-backed API MCPs**, which do not solve our quota-resilience problem, or
    - **community no-key projects**, which vary a lot in maintenance quality and operational shape.

- My current recommendation is:

    - Keep `web-search-mcp` in the document as a useful reference point.
    - Move `open-webSearch` into the **current front-runner** position for the search tier.
    - Treat `mcp-searxng` as the strongest **self-hosted strategic alternative**.
    - Treat `one-search-mcp` as a **runner-up**, not the first thing we should add.

## `web-search-mcp`

- **Docs:**

    - **Repository / primary README:** <https://github.com/mrkrsl/web-search-mcp>
    - **Technical API doc:** <https://github.com/mrkrsl/web-search-mcp/blob/main/docs/API.md>

- **Why this MCP was chosen:**

    - It directly addresses the exact gap in Bureau's current browsing stack: once Tavily and Brave are unavailable or exhausted, we currently fall straight to raw Playwright with no search-specific abstraction.
    - It preserves the most important capability we lose at that point, which is **structured general web search**, rather than only browser control.
    - It is attractive as a fallback because the server is designed to work **without API keys**, which makes it materially different from Tavily and Brave rather than a weaker paid clone.
    - It gives us an **"unlimited local fallback"** story instead of a second API that can also hit quotas.

- **Current maintenance signals <ins>(important caveat)</ins>:**

    - The current GitHub API metadata shows the repo was **last pushed on August 8, 2025**.
    - Its latest release, `v0.3.2`, was published on **August 7, 2025**.
    - The repo currently shows **23 open issues**.
    - Recent issue traffic exists, but I did not verify corresponding recent maintainer code changes after August 2025.

> [!CAUTION]
>
> This does **not** prove the project is abandoned, but it does make it a **maintenance-risky dependency** for Bureau.
>
> We should treat it as:
>
> - a **good functional idea**
> - a **weaker production dependency candidate**
> - something we may still prototype against while actively looking for a healthier replacement

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

    - That said, the maintainership signal above means it is now best thought of as a **prototyping candidate**, not an obviously safe long-term default.

- **Practical Bureau-facing implications:**

    - This candidate is a good fit for the **search tier** of the fallback chain.
    - It is especially compelling when we want a fallback that remains useful **after both Tavily and Brave are unavailable**.
    - It is probably best added with clear guidance that agents should prefer:

        - Tavily first for richer structured research.
        - Brave second for specialized search verticals.
        - `web-search-mcp` when the job is still fundamentally **general search**, but quotas or provider availability make API search unavailable.

    - As of **April 1, 2026**, the bigger strategic question is no longer only **"does this solve the right problem?"**

        - It does.

    - The bigger question is **"do we want to depend on this exact implementation?"**

        - That answer is currently **much less confident**.

    - After the broader replacement sweep on **April 1, 2026**, I would no longer treat this as the current front-runner for Bureau's search tier.


## `open-webSearch`

- **Docs:**

    - **Repository / primary README:** <https://github.com/Aas-ee/open-webSearch>
    - **npm package:** <https://www.npmjs.com/package/open-websearch>

- **Why this MCP was chosen:**

    - It is the closest thing I found to a **healthier, no-key replacement** for `web-search-mcp`.
    - It preserves the exact Bureau-relevant benefit we care about most: **general web search that still works after paid-provider quotas are gone**.
    - Unlike many newer MCPs in this space, it does **not** require an API key to be useful.
    - Unlike smaller hobby servers, it now has meaningfully better maintenance signals and a broader, more explicit transport story.

- **Current maintenance signals:**

    - The current GitHub API metadata shows the repo was **last pushed on March 31, 2026**.
    - The latest release, `v2.0.2`, was published on **March 31, 2026**.
    - The repo currently shows **883 stars** and **6 open issues**.

> [!NOTE]
>
> This is not a guarantee of long-term safety, but it is a materially healthier signal than `web-search-mcp` right now.

- **What functionality it offers:**

    - It exposes a practical **search + fetch** surface rather than only one tool.

        - `search` for multi-engine search.
        - `fetchWebContent` for generic public HTTP(S) pages and Markdown files.
        - `fetchGithubReadme` for GitHub repository README retrieval.
        - `fetchCsdnArticle`, `fetchJuejinArticle`, and `fetchLinuxDoArticle` for site-specific article extraction.

    - Its search strategy is explicitly **multi-engine and no-key**.

        - The README lists support for **Bing**, **Baidu**, **DuckDuckGo**, **Brave**, **Exa**, **CSDN**, **Juejin**, and **Startpage**.
        - Agents can also restrict which engines are allowed via `ALLOWED_SEARCH_ENGINES`.

    - It has a more flexible runtime shape than `web-search-mcp`.

        - `MODE=stdio` for local MCP usage.
        - `MODE=http` or `MODE=both` for remote-style deployments.
        - An HTTP deployment can also expose an **SSE endpoint**, even though Bureau currently only installs `http` and `stdio` MCPs out of the box.

    - It supports **optional Playwright assistance**, but only when we explicitly want it.

        - `SEARCH_MODE=request` keeps it on the light path.
        - `SEARCH_MODE=auto` can fall back to Playwright for Bing.
        - `SEARCH_MODE=playwright` forces browser-backed behavior.

    - It also has several operational knobs that map well to Bureau:

        - `DEFAULT_SEARCH_ENGINE`
        - `ALLOWED_SEARCH_ENGINES`
        - `USE_PROXY` / `PROXY_URL`
        - `FETCH_WEB_INSECURE_TLS`
        - `PLAYWRIGHT_*` variables for local browser reuse, remote browser reuse, or CDP connection

- **Why this is valuable for Bureau specifically:**

    - It is the strongest candidate I found for preserving the user experience of **"we still have a real search tool"** once Tavily and Brave are unavailable.
    - It remains much closer to our current fallback need than vendor-backed MCPs such as Exa or official Brave, because those still depend on paid API availability.
    - It is also easier to slot into Bureau's current installer architecture than many browser-heavy alternatives, because it already supports **plain stdio** and **plain HTTP**.

- **Tradeoffs and limitations:**

    - It is still fundamentally a **scraping-based system**, so it inherits the usual brittleness.

        - Engines can rate-limit.
        - HTML changes can break parsing.
        - Search quality will vary by engine and geography.

    - Its no-key story is strong, but not magical.

        - The README explicitly warns about rate limiting and engine breakage.
        - This is still a best-effort public-web fallback, not a contractual API.

    - The Playwright integration is **optional but not free**.

        - The published package does not bundle Playwright anymore.
        - If we want browser-assisted search or fetch retries, we have to install or connect a Playwright client ourselves.

    - Some of its current site-specific extraction helpers are a little idiosyncratic for Bureau.

        - `fetchCsdnArticle` and `fetchJuejinArticle` are useful proof that the project handles extraction, but they are not core to Bureau's Western general-search fallback story.

- **Why it currently looks like the best direct replacement:**

    - It solves the right problem.
    - It is healthier than `web-search-mcp`.
    - It does not force us to stand up extra infrastructure just to get started.
    - It matches Bureau's current transport constraints.

- **Practical Bureau-facing implications:**

    - If we want the safest next experiment for the **search tier**, this is the best first validation target.
    - The most plausible initial Bureau posture would be:

        - Tavily first.
        - Brave second.
        - `open-webSearch` as the first **no-key search fallback** before we degrade all the way to raw Playwright.


## `mcp-searxng`

- **Docs:**

    - **Repository / primary README:** <https://github.com/ihor-sokoliuk/mcp-searxng>
    - **npm package:** <https://www.npmjs.com/package/mcp-searxng>
    - **SearXNG docs:** <https://docs.searxng.org/>

- **Why this MCP was chosen:**

    - It is the strongest **self-hosted strategic alternative** I found.
    - Instead of scraping multiple public engines directly inside the MCP server, it cleanly delegates search to a **SearXNG instance** that we control.
    - That gives it a more principled architecture than the all-in-one scraping servers, even if it raises the setup bar.

- **Current maintenance signals:**

    - The current GitHub API metadata shows the repo was **last pushed on April 1, 2026**.
    - The latest release, `v0.10.1`, was published on **March 30, 2026**.
    - The repo currently shows **590 stars** and **4 open issues**.

> [!NOTE]
>
> This is currently one of the healthiest no-key-ish search-tier projects I found, but the health signal depends partly on the fact that it pushes complexity into the separately maintained SearXNG ecosystem.

- **What functionality it offers:**

    - It intentionally keeps the MCP surface small and clear.

        - `searxng_web_search` for web search with pagination, language selection, safe search, and time filtering.
        - `web_url_read` for direct URL reading with section filtering, heading extraction, paragraph range selection, and pagination over large content.

    - It supports both of the transports Bureau can already install cleanly.

        - **STDIO** by default.
        - **HTTP** when `MCP_HTTP_PORT` is set.

    - It has more operational polish than many small MCP servers.

        - Basic auth support for protected SearXNG instances.
        - Separate search and reader proxy configuration.
        - Separate user-agent configuration for search vs URL reading.
        - Documented troubleshooting for SearXNG's JSON-format requirement.

- **Why this is valuable for Bureau specifically:**

    - It is the most credible way I found to get a **search fallback that is not tied to a third-party quota model**, while also avoiding the most fragile direct-scraping architecture.
    - It gives Bureau a cleaner long-term story if we decide we are willing to own one piece of search infrastructure.
    - It also fits Bureau's current MCP installer much better than SSE-only or remote-only servers, because it already exposes the transports we support.

- **Tradeoffs and limitations:**

    - It is **not** zero-friction.

        - We would need to run or point at a SearXNG instance.
        - That instance must have `json` enabled in its allowed formats.

    - It is only "no key" in the sense that **we host the search layer ourselves**.

        - Operationally, that is a very different commitment from `open-webSearch`.

    - Its extraction story is intentionally narrower than `one-search-mcp` or `crawl4ai-mcp-server`.

        - `web_url_read` is strong for reading a known URL.
        - It is not trying to be a full search + scrape + map + extract platform.

    - Result quality depends partly on how good the attached SearXNG instance is.

        - Engine mix, anti-bot behavior, and regional accessibility all still matter.

- **Why it still looks like a top-tier Bureau option:**

    - It is very close to the architecture we would choose if we decided to solve search fallback seriously rather than opportunistically.
    - It is fresher and more versioned than many community search MCPs.
    - It keeps the MCP surface simple enough that Bureau could explain it cleanly to agents.

- **Practical Bureau-facing implications:**

    - If we want the best **longer-term self-hosted** answer, this is the candidate I would validate after `open-webSearch`.
    - A reasonable Bureau posture would be:

        - `open-webSearch` if we want the fastest no-key improvement with no extra service to run.
        - `mcp-searxng` if we decide the search tier is important enough to justify owning SearXNG.


## `one-search-mcp` <ins>(runner-up)</ins>

- **Docs:**

    - **Repository / primary README:** <https://github.com/yokingma/one-search-mcp>
    - **npm package:** <https://www.npmjs.com/package/one-search-mcp>

- **Why it made the shortlist:**

    - It is one of the few projects that combines **search, scrape, crawl-ish mapping, and extraction** while still supporting a **local browser search** mode with no API key.
    - The current GitHub API metadata shows the repo was **last pushed on February 3, 2026**, its latest release `v1.1.2` was published on **February 2, 2026**, and it currently shows **101 stars** and **1 open issue**.

- **Why it is not my first recommendation:**

    - It is more **architecture-heavy** than the first two choices.
    - Its default no-key mode depends on **Chromium + agent-browser**, which is operationally closer to "managed browser automation" than to a clean search fallback.
    - It overlaps more with the **crawl/extract tier** than I ideally want for the search-tier fallback.

- **What it is best understood as:**

    - A promising hybrid if we want one MCP that can do:

        - `one_search`
        - `one_scrape`
        - `one_map`
        - `one_extract`

    - Not the cleanest first answer if we want to keep Bureau's fallback stack mentally simple.


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

- **Current maintenance signals <ins>(important caveat)</ins>:**

    - The current GitHub API metadata shows the repo was **last pushed on February 6, 2026**.
    - The repo currently shows **2 open issues/items**, one of which is an open PR from **March 7, 2026**.
    - I did **not** find any published GitHub releases as of **April 1, 2026**.

> [!NOTE]
>
> This is a meaningfully better maintenance signal than `web-search-mcp`, but it is still not a slam-dunk.
>
> The project still looks like:
>
> - a **single-maintainer** dependency
> - a **relatively young** repo
> - something we should validate by hands-on setup and smoke tests before treating it as a default Bureau dependency

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

    - `open-webSearch` or `mcp-searxng` gives us a stronger **search fallback**.
    - `crawl4ai-mcp-server` gives us a stronger **extraction/crawl fallback**.
    - They are complementary rather than overlapping, which is exactly what we want in a fallback stack that should remain mentally simple.

> [!IMPORTANT]
>
> After reassessing current maintenance signals on **April 1, 2026**, the original `web-search-mcp` + `crawl4ai-mcp-server` pairing no longer looks equally strong.
>
> A more honest framing is:
>
> - `crawl4ai-mcp-server` still looks like a **reasonable candidate to validate next**
> - `web-search-mcp` still looks like a **good problem-shape match**, but a **much shakier repository choice**
> - `open-webSearch` and `mcp-searxng` now look like the healthier search-tier candidates to pair with it
