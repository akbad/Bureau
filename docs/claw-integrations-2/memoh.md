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

## Sources

- [Memoh GitHub Repository](https://github.com/memohai/Memoh)
- [Memoh Official Website](https://memoh.ai/)
- [Memoh Documentation](https://docs.memoh.ai/)
- [How To Deploy Memoh AI Agent Platform with Docker Compose](https://www.bitdoze.com/memoh-ai-agent-deploy/)
- [Memoh-v2 (Community Fork)](https://github.com/Kxiandaoyan/Memoh-v2)
