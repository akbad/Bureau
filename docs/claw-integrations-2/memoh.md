# Memoh - Self-Hosted Containerized AI Agent Platform

> **Research Date:** 2026-04-03
> **Platform:** [memoh.ai](https://memoh.ai/) | **Source:** [github.com/memohai/Memoh](https://github.com/memohai/Memoh) | **Docs:** [docs.memoh.ai](https://docs.memoh.ai/)
> **License:** AGPLv3 | **Stars:** ~1.2k | **Latest:** v0.6.3 (April 2026)

---

## 1. Platform Overview

Memoh is a self-hosted, always-on AI agent platform that runs multiple bots in isolated containers, each with its own persistent memory system, filesystem, network access, and tool integrations. It positions itself as a "Powerful AI Agent System" for creating autonomous, memory-rich conversational agents that connect to nine communication channels (Telegram, Discord, Lark/Feishu, QQ, Matrix, WeCom, WeChat, Email, and a built-in Web UI).

### Architecture

Memoh uses a layered, containerized architecture:

- **Server Layer:** Go backend (port 8080) handling REST API and channel adapters.
- **Agent Engine:** In-process AI agent built on the Twilight AI SDK (a Go library inspired by the Vercel AI SDK), providing provider-agnostic integration with OpenAI-compatible, Anthropic, and Google models.
- **Tool Providers:** Memory, web search, scheduling, container management, browser automation, and MCP (Model Context Protocol) federation.
- **Storage Layer:** PostgreSQL for relational data and Qdrant for vector database operations.
- **Browser Gateway:** Playwright-based browser automation service (port 8083) for headless Chromium/Firefox interaction.
- **Workspace Containers:** Each bot runs in its own isolated containerd container with a dedicated filesystem and network stack, connected via gRPC bridge over Unix Domain Sockets.
- **Web UI:** Vue 3 + Tailwind CSS frontend (port 8082) with streaming chat visualization, tool call inspection, file management, and dark/light themes with i18n support.

### Value Proposition

Memoh's core differentiation lies in combining three things that are typically separate concerns: (1) multi-bot orchestration with full container isolation, (2) structured long-term memory with hybrid retrieval, and (3) broad channel connectivity. It targets users who want to self-host persistent AI agents that remember context across conversations and operate autonomously across platforms. The Go-based backend is designed to run efficiently on edge devices, making it suitable for home labs and small-team deployments.

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Go (65.7% of codebase) |
| Frontend | Vue 3, TypeScript (20.4%) |
| Deployment | Docker Compose + containerd |
| Databases | PostgreSQL, Qdrant |
| Browser Automation | Playwright |
| AI SDK | Twilight (custom Go SDK) |

---

## 2. Feature Set

Memoh provides a broad feature set organized around bot management, communication, memory, and automation:

- **Multi-Bot Management:** Create and run multiple bots simultaneously, each with isolated contexts, independent model assignments, and separate memory stores.
- **Multi-User Awareness:** Bots distinguish individual users in group chats, maintaining per-person context and recall.
- **Cross-Platform Identity Binding:** Users can be recognized across different communication channels.
- **Nine Communication Channels:** Telegram, Discord, Lark (Feishu), QQ, Matrix, WeCom, WeChat, Email (Mailgun/SMTP/Gmail OAuth), and a built-in Web UI.
- **Container Isolation:** Each bot gets an isolated containerd container with snapshots, data export/import, and version control.
- **MCP Federation:** Full Model Context Protocol integration (HTTP/SSE/Stdio/OAuth) with independent per-bot MCP connections.
- **Browser Automation:** Headless browser operation via Playwright -- navigate, click, fill forms, take screenshots.
- **Skills & Sub-Agents:** Modular skill files defining bot personality and capabilities; task delegation to sub-agents with independent context.
- **Scheduled Tasks:** Cron-based automation and periodic heartbeat functionality.
- **Web Search:** Built-in web search provider integration.
- **Access Control:** Priority-based ACL rules with allow/deny effects, scoped by channel identity, type, or conversation.
- **Full GUI Management:** All configuration (bots, channels, MCP, skills, settings) through the web UI with no coding required.

---

## 3. Memory Architecture

Memoh's memory system is its most technically interesting subsystem. It is built around pluggable **Memory Providers** that control how a bot stores, retrieves, and manages long-term memory.

### Memory Providers

Three provider options are available:

1. **Built-in Provider** -- Self-hosted with three operational modes:
   - **Off:** File-based storage only, no vector search.
   - **Sparse:** Neural sparse vectors via a local model (no API cost, runs on-device).
   - **Dense:** Full embedding-based semantic search via Qdrant vector database.
2. **Mem0 Provider** -- SaaS integration via the Mem0 API for cloud-hosted memory.
3. **OpenViking Provider** -- Self-hosted or SaaS alternative memory backend.

### Memory Pipeline

The memory pipeline operates in two phases:

**Extraction (Write Path):** During conversation, the bot uses LLM-driven fact extraction to identify key information from every conversation turn. These facts are stored as structured memory entries in the vector database with metadata (user identity, timestamp, channel, conversation context).

**Retrieval (Read Path):** On each new incoming message, the system performs hybrid retrieval combining dense vector search, sparse vector search, and BM25 keyword matching. The most relevant memories are selected and injected into the bot's context window alongside the current conversation, giving the bot personalized, long-term recall across sessions.

### Context Management

- **24-Hour Context Window:** Recent conversation history within a sliding 24-hour window is automatically loaded.
- **Memory Compaction:** Over time, memories can be compacted and rebuilt to reduce redundancy and maintain relevance.
- **Per-User Segmentation:** Memories are segmented by user identity, so each person's context is distinct even in group conversations.

---

## 4. Autonomous Learning Loop

Memoh implements an implicit autonomous learning loop through its continuous memory extraction and retrieval cycle. The loop operates as follows:

1. **Observe:** The bot receives a message and loads relevant memories plus recent conversation context.
2. **Extract:** After responding, the LLM-driven fact extraction pipeline identifies new information, preferences, and context from the exchange.
3. **Store:** Extracted facts are written to the memory provider as structured entries.
4. **Retrieve:** On the next interaction, hybrid search surfaces the most relevant stored memories.
5. **Apply:** Retrieved memories are injected into the prompt context, influencing the bot's response.

This creates a cumulative learning effect where the bot improves its personalization and contextual awareness over time without explicit retraining. The memory compaction mechanism serves as a consolidation step, analogous to how biological memory consolidates short-term into long-term storage.

Additionally, the **heartbeat** and **scheduled task** systems allow bots to perform autonomous background activities -- checking on tasks, sending proactive messages, or updating their knowledge -- without waiting for user interaction, creating a true always-on learning agent.

It is worth noting that Memoh does not appear to have an explicit "learning from mistakes" or self-improvement feedback loop documented. The learning is primarily through memory accumulation rather than active reflection or strategy adjustment.

---

## 5. Operational Memory Stack

Memoh's memory can be mapped to a three-tier conceptual model:

### Working Memory (Short-Term)

The **24-hour context window** serves as working memory. Recent conversation turns are loaded directly into the LLM's context, providing immediate continuity. This includes the current conversation thread and any active tool call results. The containerd container's runtime state (files, processes) also functions as a form of working memory.

### Long-Term Memory (Semantic/Factual)

The **structured memory entries** stored in the vector database (Qdrant) represent long-term memory. These are LLM-extracted facts with metadata, retrieved via hybrid search. They persist indefinitely and are available across all future conversations. The three search modes (dense, sparse, BM25) ensure both semantic similarity and keyword precision in retrieval.

### Episodic Memory (Conversational)

While Memoh does not explicitly label an "episodic memory" tier, the combination of per-user memory segmentation and timestamped fact extraction creates an episodic-like record. The system can recall what a specific user said in previous conversations and the context around it. The memory compaction feature suggests that older episodic details may be summarized over time, trading granularity for efficiency.

### Memory Operations

- **Rebuild:** Reconstruct memory index from stored data.
- **Compaction:** Merge and summarize redundant or aged memories.
- **Export/Import:** Move memory data between bot instances via container snapshots.

---

## 6. Daily Assistant Features

Memoh is well-suited for daily assistant use cases through its multi-channel connectivity:

- **Cross-Platform Messaging:** Users can interact with their bot through whichever channel is convenient -- Telegram on mobile, Discord on desktop, web UI from a browser, email for async communication.
- **Persistent Context:** The bot remembers user preferences, past conversations, and established context across all channels and sessions.
- **Scheduled Tasks:** Cron-based scheduling enables reminders, daily briefings, periodic check-ins, and other time-based automation.
- **Web Search:** Built-in web search allows the bot to look up current information on behalf of the user.
- **Browser Automation:** Bots can navigate websites, fill forms, and take screenshots -- useful for monitoring, data collection, or automated web tasks.
- **Group Chat Support:** In group settings, the bot maintains distinct context for each participant while contributing to the shared conversation.
- **Rich Media:** Unified support for streaming responses, rich text formatting, and file attachments across channels.

---

## 7. SWE (Software Engineering) Assistant Features

Memoh provides several capabilities relevant to software engineering workflows:

- **Container-Based Workspace:** Each bot has its own isolated filesystem and network within a containerd container. This allows bots to edit files, run commands, and manage projects in a sandboxed environment.
- **Slash Commands:** Built-in command system for triggering specific bot behaviors.
- **Skills System:** Modular skill definitions allow configuring bots for specialized tasks like code review, debugging, or documentation.
- **Sub-Agent Delegation:** Complex tasks can be delegated to sub-agents with independent context, enabling multi-step workflows where one agent generates code and another reviews it.
- **MCP Integration:** Full Model Context Protocol support means bots can connect to external development tools, code analysis services, and other MCP-compatible servers.
- **File Management:** Web UI includes a file manager for browsing and managing files within bot containers.
- **Multi-Model Support:** Per-bot model assignment means different bots can use different models optimized for different tasks (e.g., a fast model for quick questions, a reasoning model for complex debugging).

It should be noted that Memoh is not primarily marketed as a software engineering tool like Claude Code or Codex. Its SWE capabilities emerge from its general-purpose container-based agent architecture rather than from purpose-built code intelligence features (AST parsing, language servers, test runners, etc.).

---

## 8. Workflow Design & UX

Memoh emphasizes a low-code/no-code management experience:

- **Web Dashboard:** All configuration is done through a Vue 3 + Tailwind CSS interface. No YAML editing or CLI configuration is required for basic operation.
- **Streaming Chat UI:** Real-time streaming visualization of bot responses with tool call inspection, allowing users to see what tools the bot is invoking and what results it receives.
- **Bot Configuration:** Per-bot settings for model selection, memory provider, channel bindings, MCP connections, skills, and access control rules.
- **Channel Management:** Visual configuration of communication channel connections with credential management.
- **Dark/Light Theme:** UI theming with internationalization support.
- **One-Click Deployment:** `curl -fsSL https://memoh.sh | sudo sh` for quick installation, or Docker Compose for manual setup.
- **Container Management:** Visual container operations including snapshots, export/import, and version control.

The UX is oriented toward a "configure and deploy" workflow rather than a "code and customize" workflow. Power users can extend functionality through skill files and MCP server connections.

---

## 9. Integration Capabilities

### Communication Channels

| Channel | Notes |
|---------|-------|
| Telegram | Bot API |
| Discord | Bot integration |
| Lark (Feishu) | Enterprise messaging |
| QQ | Chinese messaging platform |
| Matrix | Federated protocol |
| WeCom | WeChat enterprise |
| WeChat | Consumer messaging |
| Email | Mailgun, SMTP, Gmail OAuth |
| Web UI | Built-in Vue 3 interface |

### Model Providers

- **OpenAI-compatible** endpoints (any provider exposing the OpenAI API format)
- **Anthropic** (Claude models)
- **Google** (Gemini models)
- Per-bot model assignment with automatic model import

### MCP (Model Context Protocol)

Full MCP support with four transport modes:
- **HTTP** -- Standard HTTP transport
- **SSE** -- Server-Sent Events for streaming
- **Stdio** -- Standard I/O for local processes
- **OAuth** -- Authenticated MCP connections

Each bot can have independent MCP server connections, enabling per-bot tool access. This is Memoh's primary extensibility mechanism.

### Memory Providers

- **Built-in** (PostgreSQL + Qdrant)
- **Mem0** (SaaS API)
- **OpenViking** (self-hosted or SaaS)

### APIs

Memoh exposes a REST API on port 8080 for programmatic control. The Twilight AI SDK (used internally) is also available as a standalone Go library for building custom integrations.

---

## 10. Bureau Integration Fit Assessment

### Synergies

1. **MCP Protocol Alignment:** Memoh's full MCP support (HTTP/SSE/Stdio/OAuth) directly aligns with Bureau's MCP server architecture. Memoh bots could connect to Bureau's MCP servers for memory access (Qdrant, Memory MCP, SQLite), and Bureau agents could potentially interact with Memoh bots through MCP federation.

2. **Qdrant Overlap:** Both Memoh and Bureau use Qdrant as a vector database. This creates an opportunity for shared memory infrastructure -- Memoh bots could read from Bureau's Qdrant collections and vice versa, enabling cross-system memory sharing.

3. **Multi-Agent Architecture:** Memoh's multi-bot system with sub-agent delegation mirrors Bureau's multi-agent orchestration model. Memoh bots could serve as persistent, always-on agents in Bureau's hub-and-spoke architecture, handling communication channels while Bureau's 66 agent roles handle specialized tasks.

4. **Container Isolation:** Memoh's containerd-based isolation provides security guarantees that complement Bureau's orchestration. Each Memoh bot runs in a sandbox, reducing risk when connecting to external systems.

5. **Channel Gateway Potential:** Memoh's nine-channel connectivity could serve as a communication gateway for Bureau, enabling Bureau agents to interact with users through Telegram, Discord, Matrix, etc., without Bureau needing to implement those integrations directly.

6. **Self-Hosted Philosophy:** Both platforms emphasize self-hosted, privacy-respecting deployment, making them philosophically compatible.

### Friction Points

1. **Architectural Overlap:** Memoh is itself an agent orchestration platform, not a library or service. Integrating two orchestration systems creates complexity around which system "owns" the agent lifecycle, memory, and context.

2. **Go vs. Bureau's Stack:** Memoh is written in Go with its own Twilight SDK. Bureau's agent roles (Claude Code, Gemini CLI, Codex, OpenCode) operate in different runtime environments. Deep integration would require bridging these stacks, likely through MCP or REST APIs rather than native code integration.

3. **Memory Model Differences:** Memoh's memory is designed around conversational fact extraction for chatbot-style interactions. Bureau's memory systems (Qdrant, Memory MCP, SQLite) are more general-purpose. The memory models may not map cleanly -- Memoh's per-user conversational memories are structured differently from Bureau's task-oriented agent memories.

4. **Not SWE-Focused:** Memoh lacks purpose-built software engineering features (AST parsing, language server integration, test framework awareness, linting). Bureau's coding agents (Claude Code, Codex, etc.) are significantly more capable for SWE tasks. Memoh would add channel connectivity and persistent memory, not coding capability.

5. **AGPLv3 License:** The AGPLv3 license has network-use copyleft provisions that may create licensing considerations depending on how Bureau integrates with Memoh.

### Recommended Integration Strategy

The most natural integration point is **Memoh as a communication and persistent-memory gateway**:

- Use Memoh bots as front-ends connected to Telegram/Discord/Matrix channels.
- Connect Memoh bots to Bureau's MCP servers for tool access and memory sharing.
- Route complex SWE tasks from Memoh conversations to Bureau's specialized agent roles.
- Share the Qdrant vector database between systems for unified memory.

This leverages Memoh's strengths (channel connectivity, always-on presence, conversational memory) while relying on Bureau's strengths (multi-agent SWE orchestration, specialized coding roles, workflow skills).

---

## Summary

Memoh is a well-architected, actively developed self-hosted AI agent platform with strong container isolation, pluggable memory systems, and broad communication channel support. Its primary value for Bureau lies in its channel connectivity (nine platforms), persistent conversational memory, and full MCP compatibility, making it a potential communication gateway layer. The main friction points are architectural overlap as a competing orchestration system, its Go-based stack, and the AGPLv3 license. Integration through MCP and shared Qdrant infrastructure represents the most practical path forward.

---

## 11. High-Impact Bureau x Memoh Integration Ideas

### 11.1 The Qdrant Membrane -- Shared Memory Fabric with Namespace Federation

Both Bureau and Memoh already run Qdrant as their vector backbone. Instead of treating these as two separate databases that happen to use the same engine, the integration should create a **federated namespace architecture** where a single Qdrant cluster hosts partitioned collections with controlled cross-namespace read/write policies. Bureau's 66 agent roles would write to `bureau/*` collections (task artifacts, code embeddings, blast-radius graphs, session state), while Memoh bots write to `memoh/*` collections (conversational facts, user preferences, episodic memories). A thin "Membrane" proxy layer -- implementable as a shared MCP server -- enforces ACLs and performs on-the-fly re-ranking when an agent from one side queries the other's namespace.

The multiplicative value is profound: a Memoh bot fielding a Telegram question from a developer can transparently query Bureau's code-intelligence memories to answer "What broke in the auth module last week?" without Bureau agents needing to be online. Conversely, Bureau's Assess Mode can pull a developer's stated preferences and past feedback patterns from Memoh's per-user memory to calibrate code review tone and focus areas. Neither platform alone has both the conversational-fact extraction pipeline AND the deep SWE artifact memory -- the Membrane makes them one continuously learning organism.

A practical implementation would use Qdrant's multi-tenancy features (payload-based filtering and collection aliases) combined with a lightweight Go sidecar (natural for Memoh's stack) that exposes a unified MCP tool interface. Bureau agents call `membrane_query` with a scope parameter; the sidecar handles cross-namespace fan-out, deduplication, and relevance fusion across dense, sparse, and BM25 results from both systems.

### 11.2 Containerd Sandboxes for Bureau Agent Roles -- "One Container Per Brain"

Bureau orchestrates 66 agent roles, but they all share the host environment. Memoh has already solved per-bot containerd isolation with snapshot/restore, filesystem isolation, and gRPC bridging. The integration should let Bureau **spawn each agent role inside a Memoh-managed container**, inheriting Memoh's full isolation stack: dedicated filesystem, network namespace, resource limits, and snapshotting.

This transforms Bureau's agent roles from logical abstractions into physically isolated execution units. The Scrimmage Mode attacker agent runs in a container that literally cannot see the defender's filesystem. The Blast Radius analyzer gets a read-only snapshot of the codebase that it cannot mutate. Each Micro Mode DAG node executes in its own container, and if it corrupts state, the snapshot rolls back in milliseconds. Memoh's container lifecycle management (create, pause, resume, snapshot, export) becomes Bureau's infrastructure layer, and Bureau's orchestration logic becomes Memoh's missing multi-agent workflow brain.

The implementation leverages Memoh's existing gRPC bridge over Unix Domain Sockets. Bureau's hub process sends agent-spawn requests to Memoh's container manager, which creates a lightweight containerd container pre-loaded with the agent's role definition, MCP connections, and memory namespace. The agent communicates back through the gRPC bridge. Container snapshots before and after each task create a complete audit trail of every agent's actions -- something neither platform provides alone.

### 11.3 Channel Gateway Router -- Bureau Speaks Nine Languages

Bureau currently operates through CLI invocation and terminal interfaces. Memoh connects to nine communication channels. The Channel Gateway Router turns every Bureau workflow into a multi-channel conversational experience by routing Bureau events, queries, and results through Memoh's channel adapters.

A developer pushes a commit. Bureau's Assess Mode triggers a code review. Instead of the review sitting in a terminal log, the Gateway Router dispatches a structured summary to the developer's Telegram, with inline buttons (via Telegram's bot API) for "Approve," "Request Changes," or "Escalate to Senior." The developer taps "Request Changes" and types a voice note explaining what they want. Memoh's bot receives this, runs fact extraction on the transcribed audio, and routes the structured feedback back to Bureau's hub, which dispatches it to the appropriate agent role. The entire review cycle happens without the developer opening a terminal.

The router is implemented as a Memoh skill file that maps Bureau event types to channel-specific message templates. Bureau publishes events to a shared message queue (or directly via MCP tool calls to the Memoh bot). Memoh's per-user memory segmentation means the router knows each developer's preferred channel, notification preferences, and timezone -- it sends code reviews to Alice on Discord at 9am and to Bob on Matrix at 2pm. Bureau gets a complete communications layer it would take months to build natively; Memoh gets high-value, structured content flowing through its channels instead of just chat.

### 11.4 Conversational Fact Extraction for Coding Sessions -- "Session Sediment"

Bureau's coding agents (Claude Code, Gemini CLI, Codex, OpenCode) generate massive amounts of conversational context during coding sessions -- architectural decisions, rejected approaches, bug hypotheses, performance observations, user preferences about code style. Today, this context evaporates when the session ends (or at best gets partially captured in Bureau's Fold/Unfold state). Memoh's LLM-driven fact extraction pipeline should run as a **sidecar on every Bureau coding session**, continuously extracting structured facts and depositing them into the shared Qdrant memory.

The "Session Sediment" accumulates over weeks and months into an institutional knowledge base that no wiki or documentation system can match, because it captures the *reasoning* behind decisions, not just the decisions themselves. Six months later, when a developer asks "Why did we use Redis instead of Memcached for the session store?", the system retrieves the exact extracted fact: "Team decided Redis over Memcached because the session data requires sorted set operations for leaderboard features -- discussed during PR #847 review on 2026-01-15."

Memoh's hybrid retrieval (dense + sparse + BM25) is critical here because coding-session facts contain both natural language reasoning and code-specific tokens (function names, error codes, dependency versions) that need keyword-precise retrieval alongside semantic search. Bureau's agents contribute the raw material; Memoh's extraction pipeline contributes the refining process; the Qdrant Membrane stores the refined product. The combination creates an ever-growing organizational memory that makes every future coding session smarter.

### 11.5 Sub-Agent Delegation Chains -- "Bureau as Memoh's Specialist Network"

Memoh supports sub-agent delegation, where a bot can spawn a sub-agent with independent context to handle a specific task. Bureau has 66 specialized agent roles. The integration should make Bureau's entire agent roster available as Memoh's specialist delegation targets, creating delegation chains that flow from conversational channels through Memoh into Bureau's deep SWE capabilities.

A product manager sends a message to the team's Memoh bot on Lark: "Can we add OAuth support to the user service? What's the effort estimate?" The Memoh bot delegates to Bureau's Blast Radius agent, which analyzes the codebase and returns an impact graph. The Memoh bot then delegates to Bureau's Assess Mode agent for a complexity estimate. Results flow back through the delegation chain, and the Memoh bot synthesizes a conversational response: "Adding OAuth touches 12 files across 3 services. Estimated 3-5 days. The main risk is the session middleware refactor. Want me to create a detailed task breakdown?" The PM says yes, and the chain delegates to Bureau's planning agent.

This is implemented by registering each Bureau agent role as an MCP tool endpoint that Memoh bots can invoke through MCP federation. Bureau exposes a `bureau_delegate` MCP tool that accepts a role name, task description, and context payload. Memoh's skill files define delegation strategies that map conversational intents to Bureau role invocations. The key differentiator: Memoh maintains the conversational continuity and user relationship while Bureau provides the deep technical analysis. Neither could deliver this end-to-end experience alone.

### 11.6 Concierge Pipeline Meets Heartbeat -- "The Autonomous Context Curator"

Bureau's Concierge ML pipeline classifies messages into suites (WORK, REST, SOCIAL, CREATIVE, PROCESSING). Memoh's heartbeat system triggers autonomous background activities on a schedule. Combining these creates an **Autonomous Context Curator** that proactively maintains and enriches the shared memory layer without human prompting.

Every heartbeat cycle (configurable, e.g., every 30 minutes), the Curator wakes up and performs a suite-aware sweep. For WORK-classified memories, it cross-references against the current Git state to detect stale information ("memory says auth uses JWT, but code now uses session tokens -- flagging for update"). For PROCESSING-classified items, it checks whether pending tasks have been completed and updates their status. For CREATIVE-classified memories, it periodically runs associative retrieval to surface unexpected connections ("the UI animation pattern discussed last Tuesday is similar to the loading-state approach in the mobile app -- consider unifying").

The Curator also performs memory hygiene: compacting redundant facts, promoting frequently-retrieved memories to higher-priority tiers, and garbage-collecting memories about deleted code or resolved issues. Bureau's Concierge provides the semantic classification intelligence; Memoh's heartbeat provides the autonomous execution schedule; the shared Qdrant layer provides the substrate. The result is a memory system that actively maintains itself -- a capability that emerges only from the combination and that dramatically improves retrieval quality over time.

### 11.7 Scrimmage Mode Over the Wire -- "Red Team as a Service"

Bureau's Scrimmage Mode pits an attacker agent against a defender agent for adversarial code review. Currently this runs locally. With Memoh's container isolation and channel connectivity, Scrimmage Mode becomes a distributed, observable, multi-participant security exercise.

The attacker agent runs in one Memoh container; the defender in another. They have completely isolated filesystems and network namespaces -- the attacker genuinely cannot see the defender's analysis, and vice versa. A dedicated Memoh bot on Discord streams the Scrimmage in real-time to a security channel, formatting attack vectors as red-highlighted messages and defense responses as green-highlighted messages. Team members can interject with hints or constraints via the channel, and these are routed to the appropriate agent through Memoh's multi-user awareness. The entire Scrimmage is recorded as structured memory entries with full fact extraction, building a security knowledge base over time.

Post-Scrimmage, the Session Sediment system (idea 11.4) extracts the key findings into the shared memory layer, tagged with the specific code regions, vulnerability categories, and remediation patterns discussed. Future Scrimmages on similar code automatically retrieve these historical findings as context. Bureau contributes the adversarial workflow design; Memoh contributes the isolation infrastructure, real-time channel streaming, and persistent memory capture. The integration transforms an internal testing tool into a team-facing security practice with institutional memory.

### 11.8 MCP Federation Bridge -- "The Universal Tool Mesh"

Bureau runs 8+ MCP servers (Qdrant, Memory MCP, Serena, Sourcegraph, Brave/Tavily, Playwright, Semgrep, GitHub). Memoh supports MCP federation with four transport modes (HTTP, SSE, Stdio, OAuth) and per-bot independent connections. The MCP Federation Bridge creates a **unified tool mesh** where every tool from both platforms is discoverable and invocable by any agent on either side.

The Bridge is a dedicated MCP proxy server that aggregates tool registrations from all Bureau MCP servers and all Memoh bot MCP connections into a single federated catalog. An agent on either platform calls `federation_discover` to list available tools, then invokes any tool through the Bridge regardless of which platform hosts it. A Memoh bot handling a Discord conversation can invoke Bureau's Semgrep server to run a security scan, or Bureau's Sourcegraph server to search across repositories. A Bureau agent in Micro Mode can invoke a Memoh bot's browser automation to screenshot a staging deployment for visual regression checking.

The Bridge also handles capability negotiation and transport translation -- if a Bureau MCP server speaks Stdio and a Memoh bot expects SSE, the Bridge adapts. OAuth credentials are managed centrally. The Bridge logs all cross-platform tool invocations to the shared memory layer, creating an audit trail and enabling the Autonomous Context Curator (idea 11.6) to track tool usage patterns and suggest workflow optimizations. This transforms two separate tool ecosystems into one composable mesh with multiplicative capability expansion.

### 11.9 Fold/Unfold Across Channels -- "Portable Session State"

Bureau's Fold/Unfold skill compresses and restores session state, enabling context portability between sessions. Memoh's cross-platform identity binding recognizes users across channels. Combining these creates **channel-portable session state**: a developer starts a complex debugging session with Bureau in their terminal, Folds the state, commutes home, and Unfolds it in a Telegram conversation with a Memoh bot that has full access to Bureau's agent capabilities.

The Fold operation serializes not just the conversation context but the full agent state: which files were examined, what hypotheses were formed, what tools were invoked, and what the agent's current "mental model" of the problem is. This serialized state is stored in the shared Qdrant layer with the user's cross-platform identity as the key. When the user Unfolds from any channel -- Discord, Matrix, email, web UI -- Memoh retrieves the state, hydrates the appropriate Bureau agent role, and resumes exactly where the session left off.

This solves a fundamental friction in developer workflows: context switching between devices and interfaces destroys continuity. Neither Bureau alone (no multi-channel presence) nor Memoh alone (no deep SWE session state) can provide this. Together, they create a development assistant that follows the developer across their entire device and platform landscape without losing a single thread of context.

### 11.10 The Learning Concierge -- "Adaptive Routing Through Accumulated Wisdom"

Bureau's Concierge classifies incoming messages into suites for routing. Memoh's memory pipeline accumulates facts about user behavior, preferences, and interaction patterns. The Learning Concierge feeds Memoh's accumulated user knowledge back into Bureau's classification and routing decisions, creating a system that gets measurably better at task dispatch over time.

Initially, Bureau's Concierge routes a message like "fix the flaky test" to a standard debugging workflow. Over weeks, Memoh's memory accumulates facts: this particular developer's "flaky test" reports are 80% related to race conditions in async code; they prefer seeing the fix as a diff before it is applied; they work on the payments service exclusively; they get frustrated when the agent modifies test assertions instead of fixing the underlying bug. The Learning Concierge injects these accumulated preferences into the routing decision, selecting a Bureau agent role preconfigured with async-debugging expertise, diff-first presentation, payments-service context, and a "fix the cause, not the symptom" instruction.

The feedback loop closes when the developer's satisfaction signal (explicit approval, speed of acceptance, absence of follow-up corrections) is captured by Memoh's fact extraction and stored as a routing-quality observation. Over months, the system converges toward optimal routing for each user, each project, and each problem type. This is a genuine machine learning loop implemented entirely through LLM-driven fact extraction and retrieval augmentation -- no traditional ML training required, and only possible with both Bureau's routing infrastructure and Memoh's persistent user-modeling memory.

---

## Sources

- [Memoh GitHub Repository](https://github.com/memohai/Memoh)
- [Memoh Official Website](https://memoh.ai/)
- [Memoh Documentation](https://docs.memoh.ai/)
- [How To Deploy Memoh AI Agent Platform with Docker Compose](https://www.bitdoze.com/memoh-ai-agent-deploy/)
- [Memoh-v2 (Community Fork)](https://github.com/Kxiandaoyan/Memoh-v2)
