# OpenFang: Agent Operating System -- Integration Assessment

> Research report for Bureau integration evaluation. OpenFang is an open-source Agent Operating System built in Rust by RightNow-AI, open-sourced March 1 2026 under the MIT license. It compiles 137 000 lines of Rust into a single ~32 MB binary that runs autonomous agents across 40 channel adapters, 26 LLM providers, and 38 built-in tools.

**Report date:** 2026-04-03
**Source maturity:** Early-stage open source (one month post-launch). Documentation is growing but still incomplete in places; community adoption is in its first wave.

---

## Contents

- [1. Platform Overview](#1-platform-overview)
- [2. Feature Set](#2-feature-set)
- [3. Memory Architecture](#3-memory-architecture)
- [4. Autonomous Learning Loop](#4-autonomous-learning-loop)
- [5. Operational Memory Stack](#5-operational-memory-stack)
- [6. Daily Assistant Features](#6-daily-assistant-features)
- [7. SWE Assistant Features](#7-swe-assistant-features)
- [8. Workflow Design and UX](#8-workflow-design-and-ux)
- [9. Integration Capabilities](#9-integration-capabilities)
- [10. Bureau Integration Fit Assessment](#10-bureau-integration-fit-assessment)

---

## 1. Platform Overview

OpenFang brands itself as an "Agent Operating System" rather than a framework or library. The distinction is deliberate: it ships as a self-contained binary (compiled from 14 Rust crates) that includes its own runtime, memory subsystem, security sandbox, HTTP/WebSocket API layer, and scheduling infrastructure. Where frameworks like LangGraph or CrewAI ask you to assemble agents from Python components, OpenFang delivers a running system you configure rather than code.

**Core repository:** [RightNow-AI/openfang](https://github.com/RightNow-AI/openfang)
**Website:** [openfang.sh](https://www.openfang.sh/)
**License:** MIT

### Architecture at a glance

| Crate | Responsibility |
|---|---|
| `openfang-kernel` | Orchestration, workflow engine, agent lifecycle |
| `openfang-runtime` | Agent execution loop, WASM sandbox |
| `openfang-memory` | Unified SQLite + vector embedding store |
| `openfang-channels` | 40 messaging adapters (Telegram, Discord, Slack, WhatsApp, Teams, IRC, Matrix, and 33 more) |
| `openfang-tools` | 38 built-in tool implementations |
| `openfang-api` | 140+ REST/WebSocket/SSE endpoints |

### Value proposition

OpenFang targets a gap between conversational chatbots and production autonomous agents. Its thesis is that current agent frameworks require too much glue code, lack production security, and cannot run unattended. By providing scheduling, persistent memory, audit trails, and a WASM sandbox out of the box, it aims to make "set it and forget it" agent deployments viable without bespoke infrastructure.

Early benchmarks (reported by SitPoint and the project itself) claim approximately 13x throughput over CrewAI and LangGraph on routing tasks, attributed to the Rust runtime and zero-copy message passing.

---

## 2. Feature Set

### Hands -- pre-built autonomous agents

The central abstraction is the "Hand": a pre-built, schedule-driven autonomous capability package. Unlike conversational agents that wait for prompts, a Hand has a job description, a schedule, and a mandate to deliver results to a dashboard. OpenFang ships seven Hands:

| Hand | Function |
|---|---|
| **Clip** | Converts long-form video into short, viral clips with captions and thumbnails |
| **Lead** | Autonomous lead generation -- discovers, enriches, and scores qualified leads; builds ICP (Ideal Customer Profile) graphs |
| **Collector** | OSINT-style intelligence gatherer; monitors targets for changes and sentiment shifts |
| **Predictor** | Superforecasting engine using Brier scores to track its own accuracy over time |
| **Researcher** | Fact-checking engine using the CRAAP method (Currency, Relevance, Authority, Accuracy, Purpose); generates cited reports |
| **Twitter** | Social media management -- posting, engagement, analytics |
| **Browser** | General web automation and scraping |

### LLM provider support

26 LLM providers are supported, allowing agents to swap models without code changes. The kernel routes requests through a unified provider abstraction.

### Tool ecosystem

38 built-in tools ship with the binary. Custom tools can be added as WASM modules that run inside the sandboxed runtime.

### Channel adapters

40 adapters for messaging platforms enable agents to operate across multiple channels simultaneously with "cross-channel canonical sessions" -- meaning a single agent can maintain a unified conversation context across, say, Discord and a web UI.

---

## 3. Memory Architecture

OpenFang's memory subsystem is one of its most architecturally distinctive features. It unifies three memory types into a single embedded layer:

- **Episodic memory** -- conversation history and interaction traces
- **Semantic memory** -- vector embeddings for retrieval-augmented recall
- **Procedural memory** -- tool call history and execution patterns

### Implementation: embedded SQLite + vector store

The choice of SQLite over PostgreSQL is deliberate and aligned with the single-binary philosophy. Memory queries are local function calls rather than TCP roundtrips. Vector embedding storage is built into the memory layer, eliminating the need for an external vector database like Pinecone or Weaviate.

This design trades horizontal scalability for deployment simplicity and latency. For single-node deployments (which is the target use case), it removes an entire infrastructure dependency and its associated failure modes.

### LLM-based compaction

Older memories are automatically summarized by the LLM to keep context windows efficient without losing critical information. This is conceptually similar to how Bureau's memory systems use Qdrant and Memory MCP for long-term context, but OpenFang handles it internally rather than delegating to external services.

### Canonical sessions

A canonical session merges interactions from multiple platforms into a single continuous memory stream for an agent. If a user talks to an agent on Discord and then continues on a web UI, the agent sees one conversation, not two.

---

## 4. Autonomous Learning Loop

OpenFang's learning loop is most visible in the Predictor Hand, which uses Brier scoring to measure its own forecasting accuracy over time. This creates a quantified self-improvement feedback cycle: predictions are logged, outcomes are recorded, accuracy is scored, and the agent can adjust its confidence calibration.

More broadly, the procedural memory system records tool call patterns and outcomes, creating a form of experiential learning. When an agent encounters a similar task, it can reference past execution traces to inform its approach. This is not full reinforcement learning -- it is pattern retrieval from stored experience -- but it provides a meaningful improvement over stateless agent execution.

The Researcher Hand's CRAAP-based fact-checking creates another feedback loop: sources are evaluated, reliability is scored, and the system builds a trust graph over information sources that improves with use.

**Limitations to note:** OpenFang does not currently implement prompt evolution, skill distillation, or other advanced self-improvement patterns documented in the research literature (DSPy-style optimization, Reflexion-style verbal self-critique). Its learning is primarily retrieval-based rather than parametric. The project is one month old; these capabilities may arrive later.

---

## 5. Operational Memory Stack

Mapping OpenFang's memory to a standard working/long-term/episodic taxonomy:

### Working memory

The active context window during agent execution. OpenFang manages this through its kernel, feeding relevant episodic and semantic memories into the LLM prompt. The LLM-based compaction system keeps working memory sized appropriately for the model's context window.

### Long-term memory

Persistent SQLite storage containing all three memory types (episodic, semantic, procedural). Survives process restarts by design since SQLite is file-based. The vector embedding layer enables similarity-based retrieval from long-term storage, functioning as the agent's "recall" capability.

### Episodic memory

Conversation histories and interaction traces, stored with timestamps and channel metadata. The canonical session feature means episodic memory is unified across channels -- a significant architectural advantage for multi-channel agents.

### Comparison with Bureau's memory stack

Bureau uses Qdrant for vector storage, Memory MCP for structured persistence, and SQLite for lightweight state. OpenFang consolidates all of this into a single embedded layer. The tradeoff is clear: Bureau's approach offers more flexibility and horizontal scalability; OpenFang's approach offers simpler deployment and lower latency for single-node use cases.

---

## 6. Daily Assistant Features

OpenFang is primarily designed for autonomous background operation rather than interactive daily assistance. However, several capabilities serve daily assistant use cases:

- **Multi-channel presence** -- agents are available on whichever platform the user prefers (Slack, Discord, Telegram, web, etc.), with context preserved across channels
- **Dashboard reporting** -- Hands deliver results to a web dashboard, providing a daily briefing without requiring the user to initiate queries
- **Lead Hand** -- delivers daily qualified lead reports for sales teams
- **Collector Hand** -- provides daily intelligence briefings on monitored targets (competitors, markets, topics)
- **Researcher Hand** -- generates cited research reports on demand
- **Clip Hand** -- automates content repurposing from long-form video, a common daily task for content teams

The interaction model is closer to "agent that works for you and reports back" than "assistant you chat with." Users configure Hands, set schedules, and receive outputs rather than engaging in real-time conversation. This is a fundamentally different paradigm from conversational assistants like Claude Code or Gemini CLI.

---

## 7. SWE Assistant Features

OpenFang is **not currently positioned as a software engineering assistant**. Its seven Hands are oriented toward marketing, sales intelligence, research, and content creation rather than code generation, debugging, or repository management.

There is no equivalent to:
- Claude Code's codebase understanding and editing
- Codex's autonomous issue resolution
- SWE-bench-style code repair capabilities
- Git-aware workflow integration
- Test generation or execution

The Browser Hand could theoretically be used for web-based development tasks (e.g., monitoring CI dashboards), and the Researcher Hand could support technical research. The WASM extension system means custom SWE-focused Hands could be built. But out of the box, OpenFang does not compete in the SWE assistant space.

**This is a significant finding for the Bureau integration assessment** -- Bureau is specifically a coding environment orchestrator, and OpenFang's current capabilities are orthogonal to that mission.

---

## 8. Workflow Design and UX

### Configuration over code

OpenFang agents are configured through YAML/TOML manifests rather than code. Each Hand has a configuration schema defining its schedule, targets, LLM provider, and output format. This makes agent deployment accessible to non-developers but limits customization compared to code-first frameworks.

### Dashboard-centric

The primary UX is a web dashboard powered by 140+ API endpoints (REST, WebSocket, SSE). Agents report results to the dashboard, and users monitor and configure agents through it. This is a monitoring-and-control paradigm rather than a conversational paradigm.

### Schedule-driven execution

Agents run on configurable schedules (cron-style). This is a fundamentally different execution model from Bureau's on-demand, session-based agent invocation. OpenFang agents are persistent daemons; Bureau agents are ephemeral sessions.

### Cross-channel sessions

The canonical session feature provides a seamless UX when users interact with agents across multiple platforms. This is a genuine UX innovation -- most frameworks treat each channel as a separate conversation.

---

## 9. Integration Capabilities

### API surface

140+ REST, WebSocket, and SSE endpoints provide comprehensive programmatic access. This is the primary integration vector for external systems.

### Channel adapters

40 messaging platform adapters. Adding a new channel requires implementing the adapter trait in Rust.

### LLM providers

26 providers with a unified abstraction. Model switching is configuration-level, not code-level.

### WASM extension system

Custom tools and capabilities can be packaged as WASM modules. The dual-metered sandbox (fuel metering for CPU, epoch metering for timeouts) ensures untrusted extensions cannot compromise the host.

### Security model

16 security systems make OpenFang unusually security-conscious for an agent framework:
- WASM dual-metered sandbox
- Ed25519 manifest signing
- Merkle hash-chain audit trail
- Taint tracking for data provenance
- SSRF protection
- Secret zeroization (secrets are wiped from memory after use)
- HMAC-SHA256 mutual authentication
- GCRA rate limiter
- Subprocess isolation
- Prompt injection scanner

### Protocol support

OpenFang does not currently advertise MCP (Model Context Protocol) support, A2A (Agent-to-Agent) protocol support, or other emerging agent interoperability standards. Its integration model is REST API-first. This is a notable gap for Bureau integration, which relies heavily on MCP.

---

## 10. Bureau Integration Fit Assessment

### What Bureau is

Bureau is a unified orchestration framework for multi-agent AI coding environments (Claude Code, Gemini CLI, Codex, OpenCode) with 66 agent roles, MCP servers, memory systems (Qdrant, Memory MCP, SQLite), workflow skills, and a hub-and-spoke context architecture. It is focused on software engineering workflows.

### Synergies

1. **Memory architecture alignment** -- Both Bureau and OpenFang use SQLite as a persistence layer. Bureau's memory stack (Qdrant + Memory MCP + SQLite) and OpenFang's unified memory subsystem share philosophical alignment around persistent agent memory. A bridge that syncs memory between the two systems is architecturally feasible.

2. **Channel adapters for Bureau notification** -- OpenFang's 40 channel adapters could serve as a notification layer for Bureau workflows. Bureau agents completing tasks could push status updates through OpenFang's Slack, Discord, or Telegram adapters.

3. **Research and intelligence augmentation** -- OpenFang's Researcher and Collector Hands could feed contextual intelligence into Bureau's hub-and-spoke context system. A coding agent working on a competitor analysis feature could pull from OpenFang's Collector data.

4. **Security model** -- OpenFang's security posture (WASM sandbox, audit trails, taint tracking) exceeds what most agent frameworks provide. Bureau could delegate sandboxed execution of untrusted tools to OpenFang's runtime.

5. **Complementary scheduling** -- Bureau runs on-demand sessions; OpenFang runs scheduled background agents. Together they could cover both interactive and background agent workloads.

### Friction points

1. **No SWE capabilities** -- OpenFang has zero software engineering features. It cannot read code, edit files, run tests, understand repositories, or perform any of Bureau's core agent tasks. This is the fundamental mismatch.

2. **No MCP support** -- Bureau's architecture relies heavily on MCP servers. OpenFang uses a REST API model with no MCP compatibility. Integration would require a custom bridge (an MCP server that wraps OpenFang's REST API).

3. **Single-binary vs. distributed** -- OpenFang's embedded-everything architecture conflicts with Bureau's distributed, composable design. Running OpenFang alongside Bureau means running a separate daemon with its own memory, its own API surface, and its own scheduling -- duplicating infrastructure rather than complementing it.

4. **Rust vs. Bureau's ecosystem** -- Bureau operates in a JavaScript/Python/shell ecosystem. Extending OpenFang requires Rust or WASM, raising the contribution barrier for Bureau's user base.

5. **Different execution paradigms** -- Bureau agents are session-scoped and task-driven. OpenFang agents are persistent daemons on schedules. Bridging these paradigms requires careful design to avoid architectural confusion.

6. **Early maturity** -- OpenFang open-sourced one month ago (March 2026). APIs, configuration formats, and extension interfaces may change significantly. Building Bureau integrations against an unstable API is risky.

### Recommendation

**Integration priority: Low for core workflows, Medium for auxiliary capabilities.**

OpenFang is not a natural fit for Bureau's core mission of orchestrating AI coding agents. The platform has no SWE capabilities, no MCP support, and a fundamentally different execution model. Attempting to use OpenFang as a coding agent within Bureau would require building all SWE capabilities from scratch.

However, OpenFang has genuine value as a **peripheral intelligence and notification layer**:

- Use the Researcher Hand to feed background research into Bureau context
- Use the Collector Hand for competitive/technology intelligence gathering
- Use channel adapters as a notification bus for Bureau workflow events
- Use the Predictor Hand for project timeline forecasting

The recommended integration approach, if pursued, would be:

1. Build a lightweight MCP server that wraps OpenFang's REST API
2. Expose Researcher, Collector, and Predictor capabilities as MCP tools
3. Feed OpenFang intelligence outputs into Bureau's hub-and-spoke context
4. Keep the integration thin and optional -- OpenFang is not a dependency

**Wait for:** MCP support in OpenFang (if it arrives), stabilization of the REST API, and community validation of production reliability before investing in deeper integration.

---

## Sources

- [RightNow-AI/openfang on GitHub](https://github.com/RightNow-AI/openfang)
- [OpenFang official site](https://www.openfang.sh/)
- [OpenFang documentation -- Architecture](https://www.openfang.sh/docs/architecture)
- [OpenFang on Product Hunt](https://www.producthunt.com/products/openfang)
- [OpenFANG: The Rust Agent OS Benchmarked Against CrewAI and LangGraph (SitePoint)](https://www.sitepoint.com/openfang-rust-agent-os-performance-benchmarks/)
- [OpenFang: The First Serious Agent Operating System (Medium / AI for Life)](https://medium.com/ai-for-life/openfang-the-first-serious-agent-operating-system-and-why-it-matters-f361a7d9ba2b)
- [The AI Agent That Runs Without You (Medium)](https://medium.com/@creativeaininja/the-ai-agent-that-runs-without-you-what-openfang-changes-about-autonomous-automation-cfa2830080e4)
- [OpenFang introduction (Mintlify docs)](https://rightnow-ai-openfang-65.mintlify.app/introduction)
- [OpenFang on i-scoop](https://www.i-scoop.eu/openfang/)
