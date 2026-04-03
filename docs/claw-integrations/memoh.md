# Memoh Integration Analysis

**Date:** 2026-04-03
**Status:** Research complete
**Subject:** Memoh — self-hosted, always-on, containerized AI agent platform
**Repository:** [github.com/memohai/Memoh](https://github.com/memohai/Memoh)
**Docs:** [docs.memoh.ai](https://docs.memoh.ai/)
**Website:** [memoh.ai](https://memoh.ai/)

---

## 1. Platform Overview

Memoh is a self-hosted, always-on AI agent platform built in Go. Each bot runs
in its own isolated containerd container with a dedicated filesystem, network
stack, and tool set. The platform supports multiple concurrent bots that can
chat privately, in groups, or with each other, distinguishing individual users
in group conversations and maintaining per-user context with cross-platform
identity binding.

**Core value proposition:** give each bot its own computer and brain — isolated
execution, persistent structured memory, and multi-channel presence — all
managed through a web UI with no coding required.

Key architectural properties:

| Property | Detail |
|---|---|
| Language | Go (65.7%), TypeScript (Vue 3 frontend) |
| Container runtime | Embedded containerd (Linux namespaces + cgroups) |
| LLM providers | OpenAI, Anthropic, Google via Twilight AI SDK; per-bot model assignment |
| MCP support | Full (HTTP / SSE / Stdio / OAuth); per-bot independent connections; MCP federation as tool provider |
| Browser automation | Playwright browser gateway on port 8083 |
| Web UI | Vue 3 + Tailwind CSS dashboard on port 8082; dark/light theme, i18n |
| REST API | Port 8080 with integrated channel adapters |
| License | **AGPLv3** (copyleft; see Risks section 11) |
| Maturity | v0.6.3 (April 2, 2026), 1.2k stars, 120 forks, 721 commits, 29 releases |
| Edge-friendly | Go binary runs efficiently on low-resource devices |

The GitHub description explicitly positions it as "like OpenClaw" — the
dominant open-source personal AI assistant — but with deeper memory, better
container isolation, and lower inference cost due to context optimization.

---

## 2. Memory Architecture

Memoh's memory system is the platform's strongest differentiator. It operates
as a pipeline: **extract -> store -> retrieve -> compact -> rebuild**.

### 2.1 Fact Extraction

During every conversation turn, the bot runs an LLM-driven extraction pass
that identifies salient facts from the exchange and distills them into compact
structured memory entries. This is not raw-chunk storage — facts are
normalized into discrete knowledge units before persistence.

### 2.2 Pluggable Memory Providers

Memory Providers are the pluggable backends that control how a bot stores,
retrieves, and manages long-term memory. Confirmed providers:

| Provider | Type | Notes |
|---|---|---|
| Built-in: Off | File-based | No vector search; cheapest option |
| Built-in: Sparse | Neural sparse vectors | Local model, no API cost |
| Built-in: Dense | Embedding-based semantic search | Requires Qdrant |
| Mem0 | External | Leverages Mem0's extraction/consolidation pipeline |
| OpenViking | External | Alternative backend |

### 2.3 Hybrid Retrieval

On each incoming message, Memoh retrieves relevant memories via hybrid search
combining:

- **Dense vectors** — embedding similarity via Qdrant
- **Sparse vectors** — neural sparse representation via local model
- **BM25** — keyword/term-frequency matching

Retrieved memories are injected into the bot's context window alongside the
24-hour recent context loading window.

### 2.4 Context Compaction

Memory compaction merges redundant entries — when facts overlap or contradict,
the system consolidates them into a single authoritative record. This is a key
cost-optimization mechanism: by compacting before injection, Memoh sends
smaller contexts to the LLM, reducing token spend significantly compared to
platforms that stuff raw conversation history.

### 2.5 Rebuild Flows

Memory rebuild allows full reprocessing of stored memories — useful after
model upgrades, extraction prompt changes, or provider migrations. This
ensures memory quality does not degrade over time.

### 2.6 Manual Memory Management

The web UI supports manual creation, editing, and deletion of memory entries.
A vector manifold visualization (Top-K distribution & CDF curves) provides
insight into memory distribution and retrieval quality.

---

## 3. Autonomous Learning Loop

Memoh supports autonomous bot activity through two complementary scheduling
mechanisms:

- **Heartbeat** — periodic wake-up prompts at configurable intervals. During
  heartbeats, bots can review recent activity, consolidate memories, perform
  health checks, or initiate proactive outreach.
- **Cron-based scheduled tasks** — precise time-based scheduling for recurring
  operations (daily summaries, monitoring checks, data refreshes).

Together, these enable a bot to learn continuously: extract facts during
conversations, consolidate during heartbeats, and act proactively on
schedules — without requiring user interaction to trigger updates.

---

## 4. Operational Memory Stack

The operational memory stack for a single Memoh bot:

```
+--------------------------------------------------+
|  Context Window (LLM)                            |
|  +--------------------------------------------+  |
|  | System prompt + skill files                |  |
|  | 24-hour recent conversation context        |  |
|  | Hybrid-retrieved memories (Top-K)          |  |
|  | Current message + tool results             |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
          ^                    |
          |                    v
+------------------+   +------------------+
| Retrieval Engine |   | Fact Extraction  |
| (Dense+Sparse+   |   | (LLM-driven)    |
|  BM25 hybrid)    |   +--------+---------+
+--------+---------+            |
         |                      v
+--------v--------------------------+
| Memory Store (pluggable backend)  |
| - Qdrant (dense)                  |
| - Local sparse model              |
| - File storage (fallback)         |
| - Mem0 / OpenViking (external)    |
+-----------------------------------+
         |
         v
+-----------------------------------+
| Compaction & Rebuild Engine       |
| - Merge redundant facts           |
| - Resolve contradictions           |
| - Reindex on provider change      |
+-----------------------------------+
```

**Comparison with Bureau's memory stack:**

| Layer | Bureau | Memoh |
|---|---|---|
| Semantic search | Qdrant via MCP | Qdrant (dense mode) |
| Structural memory | Memory MCP server | Fact extraction + compaction |
| Session memory | claude-mem | 24-hour context window |
| Memory unification | Fragmented (3 backends, no cross-query) | Unified hybrid retrieval pipeline |
| Compaction | Manual/none | Automatic merge + rebuild |

Memoh's memory stack is more cohesive — a single pipeline handles extraction,
storage, retrieval, and maintenance. Bureau's stack is more powerful in raw
capability but fragmented across three independent systems.

---

## 5. Practical Assistant Features

Memoh bots function as general-purpose personal assistants:

- **File management** — edit files within the bot's container filesystem
- **Command execution** — run arbitrary commands in the container sandbox
- **Web browsing** — headless browser automation via Playwright (navigate,
  click, fill forms, screenshot, read accessibility trees, manage tabs)
- **MCP tool calling** — connect to external tool servers; each bot manages
  its own MCP connections independently
- **Multi-user group chat** — bots distinguish individual users, maintain
  per-person context in group conversations
- **Cross-platform identity binding** — same user recognized across channels
- **Rich media** — streaming, rich text, and attachments across all channels

---

## 6. SWE Assistant Features

Memoh is not purpose-built for software engineering (unlike Bureau), but its
container isolation and tool access provide a capable SWE substrate:

| Capability | Memoh | Bureau |
|---|---|---|
| Code editing | File edit within container | 66 specialized agent roles across 4 CLIs |
| Command execution | Container-sandboxed shell | Direct CLI invocation (Claude Code, Gemini, etc.) |
| Git operations | Via shell commands | Specialized workflow skills |
| Code review | Generic LLM + tools | Assess Mode with multi-style evaluation |
| Step-gated editing | None | Micro Mode (production) |
| MCP dev tools | Per-bot MCP connections | 15+ servers, 80+ tools |
| Browser testing | Playwright built-in | Via Playwright MCP |

Memoh lacks Bureau's deep SWE specialization (role-based orchestration,
Micro/Assess modes, dossier management) but provides a solid sandboxed
execution environment that Bureau does not have.

---

## 7. Channel & Platform Support

Memoh supports 9 channels with unified streaming, rich text, and attachments:

| Channel | Status | Notes |
|---|---|---|
| Telegram | Supported | Primary channel, feature-complete |
| Discord | Supported | Full integration |
| Lark (Feishu) | Supported | Asia-centric enterprise messenger |
| QQ | Supported | Major Chinese platform |
| Matrix | Supported | Open-protocol federation |
| WeCom (WeChat Work) | Supported | Chinese enterprise messenger |
| WeChat | Supported | Consumer Chinese messenger |
| Email | Supported | Mailgun / SMTP / Gmail OAuth |
| Web UI | Built-in | Vue 3 dashboard with streaming chat |

**Bureau comparison:** Bureau currently supports only Telegram. The concierge
pipeline is 90% channel-agnostic (isolated to `bridge/telegram.py` and
`bridge/adapter.py`), but no other transports are implemented.

Memoh's Asia-centric channel support (Lark, QQ, WeCom, WeChat) is notable —
these are difficult to integrate and represent significant engineering effort.

---

## 8. Security Model

### 8.1 Per-Bot Container Isolation

Each bot runs in its own containerd container with:

- **Dedicated filesystem** — no shared state between bots
- **Dedicated network namespace** — network isolation between bots
- **Dedicated tool set** — each bot's MCP connections are independent
- **gRPC over Unix domain sockets** — communication between the main server
  and bot containers avoids TCP, reducing attack surface
- **Snapshots and versioning** — container state can be captured, versioned,
  and rolled back
- **Data export/import** — bot data is portable between Memoh instances

Memoh embeds containerd inside the server container, requiring Linux kernel
features (namespaces, cgroups) and elevated privileges (typically
`--privileged` or specific capability grants in Docker).

This is the strongest isolation model in the open-source AI agent space.
Competitors like OpenClaw run bots in the same process; CoPaw uses
tool-guarding but not container isolation.

### 8.2 ACL-Based Access Control

Priority-based ACL rules with allow/deny effects, scoped by:

- **Channel identity** — who is sending the message
- **Channel type** — which platform (Telegram, Discord, etc.)
- **Conversation** — specific chat/room/thread

This enables fine-grained permission management: e.g., allow a user on
Telegram but deny them on Discord, or restrict certain conversations to
specific users.

### 8.3 Default Credentials

The admin UI ships with default credentials `admin/admin123`. Any production
deployment must change these immediately. If Memoh is deployed alongside
Bureau, both systems must share a coherent authentication boundary or risk
one becoming a backdoor to the other.

### 8.4 Security Implications for Bureau Integration

Memoh's container isolation addresses Bureau's identified gap: Bureau has no
container isolation (noted as "Low priority" in the agent framework
evaluation). By delegating dangerous operations to Memoh containers, Bureau
gains sandboxed execution without modifying its core architecture.

---

## 9. Integration Architecture

### 9.1 Proposal: Memoh as Isolation Layer for Risky Tasks

Bureau's core process handles orchestration, classification, and routing.
Memoh containers serve as disposable sandboxes for operations that should not
run in the main Bureau environment.

```
Bureau Orchestrator (main process, persistent)
  |
  +-- Normal workflow --> Claude Code / Gemini CLI / Codex / OpenCode
  |                       (trusted operations in Bureau's environment)
  |
  +-- Risky workflow  --> Memoh Container (disposable sandbox)
                          - Untrusted code execution
                          - Web scraping with unknown targets
                          - Experimental tool chains
                          - Third-party MCP server testing
                          - Build/test of untrusted repositories
```

### 9.2 Delegation Protocol

1. **Bureau classifies** incoming request via ML pipeline (existing
   `classify -> suite detect -> hard rules -> feature eval` flow)
2. **Risk assessment** — new classification dimension: `risk_level` (trusted
   / sandboxed / rejected)
3. **Sandboxed tasks** are dispatched to a Memoh bot via:
   - Memoh's Web UI API (REST)
   - Direct Telegram/Discord bridge (bot-to-bot messaging)
   - MCP tool call to a Bureau-side MCP server wrapping Memoh's API
4. **Memoh bot executes** in isolated container — file edits, shell commands,
   web browsing, tool calls all contained
5. **Results returned** to Bureau orchestrator for post-processing and
   delivery to user

### 9.3 Memory Bridge

Memoh's memory system and Bureau's memory stack can be bridged:

| Direction | Mechanism | Use Case |
|---|---|---|
| Bureau -> Memoh | Inject context via system prompt / skill files | Give sandbox bot project context |
| Memoh -> Bureau | Extract results via API, store in Bureau's Qdrant | Persist sandbox findings |
| Shared backend | Both point to same Qdrant instance (different collections) | Unified semantic search |

### 9.4 Concrete Integration Points

| Bureau Component | Memoh Component | Integration |
|---|---|---|
| Concierge bot (Telegram) | Memoh Telegram channel | Bot-to-bot delegation |
| ML classification pipeline | N/A | Add `sandboxed` class for risky tasks |
| MCP server mesh (15+ servers) | Per-bot MCP connections | Share MCP configs for sandbox bots |
| Dossier system | Memoh memory + file system | Snapshot/restore sandbox state |
| Workflow skills | Memoh skill files | Mirror Bureau skills as Memoh skill definitions |

### 9.5 Deployment Topology

```
Docker Compose stack:
  bureau:          # Bureau main process
  memoh-server:    # Memoh control plane (Go binary + embedded containerd)
    privileged: true
  qdrant:          # Shared vector DB
  memoh-bot-1:     # Auto-created by Memoh for sandbox task 1
  memoh-bot-2:     # Auto-created by Memoh for sandbox task 2
  ...
```

Memoh's Go binary is lightweight and runs on edge hardware. The container
overhead per bot is minimal (containerd, not full Docker-in-Docker).

---

## 10. Fit Assessment

| Dimension | Fit | Rationale |
|---|---|---|
| Container isolation for Bureau | **Strong** | Directly addresses Bureau's identified gap; no competitor offers comparable per-bot sandboxing |
| Memory system complement | **Strong** | Memoh's unified extraction/compaction pipeline could replace or unify Bureau's fragmented 3-backend stack |
| Channel expansion | **Moderate** | Memoh covers 9 channels vs Bureau's 1, but Bureau's pipeline is already channel-agnostic — adding transports directly may be simpler than proxying through Memoh |
| SWE task delegation | **Moderate** | Memoh containers can run code/commands, but lack Bureau's specialized agent roles, Micro Mode, and Assess Mode |
| Proactive assistant loop | **Moderate** | Heartbeat + cron gives Bureau proactive capabilities it currently lacks, but integrating these into Bureau's existing pipeline requires careful design |
| ACL / multi-user security | **Moderate** | Memoh's ACL is more mature than Bureau's single-user filter, but Bureau's threat model is different (dev tool vs. general assistant) |
| Admin UI | **Moderate** | Memoh's Vue 3 dashboard could manage sandbox bots, but Bureau's core config is file-based by design |
| Asia-centric platforms | **Weak** | Lark/QQ/WeCom/WeChat are valuable for Memoh's target audience but low-priority for Bureau's developer-focused use case |
| SWE depth (roles, modes, dossiers) | **Weak** | Memoh adds nothing here; Bureau is far ahead |
| Orchestration across CLIs | **Weak** | Memoh has no concept of multi-CLI orchestration; this is Bureau's unique territory |

**Overall: Strong fit as an isolation/sandbox layer; Moderate fit as a memory
unification path; Weak fit as a replacement for Bureau's core orchestration.**

---

## 11. Risks & Tradeoffs

### 11.1 Operational Risks

- **Privileged containers** — Memoh requires `--privileged` or elevated
  capabilities for containerd. This is a significant security surface in
  production deployments. The isolation benefit comes at the cost of a
  privileged parent process.
- **Resource overhead** — each bot container consumes memory and CPU. Bureau
  would need to manage container lifecycle (create on demand, destroy after
  task completion) to avoid resource leaks.
- **Go + Python boundary** — Bureau is Python; Memoh is Go. Integration
  requires API-level communication (REST/MCP), not library-level. This adds
  latency and complexity compared to in-process solutions.

### 11.2 License Risk (AGPLv3)

Memoh is licensed under AGPLv3, the most restrictive common open-source
license. If Bureau interacts with Memoh only via its REST API (network
boundary), the AGPL's copyleft provisions should not propagate to Bureau's
codebase. However, if any Memoh code is embedded in Bureau or if Bureau's
code is modified to run inside Memoh's process, AGPL copyleft would apply
to Bureau. **The integration must maintain a strict network boundary.**

### 11.3 Model Cost Amplification

Memoh's fact extraction runs an LLM call on every conversation turn. If
Bureau delegates significant traffic to Memoh bots, the extraction overhead
multiplies model costs. The "Off" memory mode should be used for bots that
serve purely as execution sandboxes without needing memory.

### 11.4 macOS Compatibility

Bureau is macOS-focused; containerd is Linux-native. Running Memoh on macOS
requires a Linux VM (e.g., via Lima or Colima), adding a layer of
indirection. This affects the development experience for Bureau contributors
and may introduce latency for sandboxed operations.

### 11.5 Architectural Risks

- **Dependency coupling** — adding Memoh as a required component increases
  Bureau's deployment complexity. The Docker Compose stack grows from
  Bureau's current services to include Memoh server + containerd.
- **Memory coherence** — bridging two memory systems (Bureau's fragmented
  stack + Memoh's unified pipeline) risks inconsistency. A sandbox bot's
  memories may diverge from Bureau's understanding of the same context.
- **Qdrant duplication** — both Bureau and Memoh use Qdrant. Running two
  instances is wasteful; sharing one requires careful collection namespacing
  to prevent data leakage. Embedding model, vector dimensions, and distance
  metric must be aligned between the two systems.
- **Heartbeat/cron overlap** — Bureau is developing its own proactive features.
  Running both Bureau's and Memoh's scheduling systems creates coordination
  challenges.

### 11.6 Strategic Risks

- **Project maturity** — Memoh is newer than OpenClaw and has a smaller
  community. Long-term maintenance is uncertain.
- **Feature overlap growth** — as both projects evolve, overlap increases.
  Bureau may end up maintaining integration code for features it could build
  natively.
- **Complexity budget** — Bureau already manages 66 agent roles, 15+ MCP
  servers, 3 memory backends, and a classification pipeline. Adding Memoh
  as an integration layer further stretches the complexity budget.

### 11.7 Recommended Approach

**Phase 1 (Low effort):** Use Memoh as an optional, standalone sandbox for
untrusted code execution. Bureau dispatches tasks via REST API, collects
results. No memory bridging, no shared Qdrant. Pure isolation layer.

**Phase 2 (Medium effort):** Add shared Qdrant backend with separate
collections. Sandbox bots can read Bureau's project context; Bureau can
harvest sandbox findings.

**Phase 3 (High effort, contingent on Phase 1-2 success):** Evaluate Memoh's
memory pipeline as a replacement for Bureau's fragmented memory stack.
This would require significant refactoring of Bureau's Qdrant semantic +
Memory MCP structural + claude-mem session architecture.

---

## 12. High-Impact Feature Merges & Extensions

### 12.1 Role-Per-Container Orchestration ("Bureau Hive")

Assign each of Bureau's 66 agent roles its own dedicated Memoh container with a
tailored filesystem, toolset, and memory collection. The architect container
carries design docs and diagramming tools; the debugger container carries core
dumps, profilers, and sanitizer runtimes; the security-compliance container
carries CVE databases and Semgrep rulesets. Bureau's orchestrator dispatches
tasks to the correct container by role, and each container's fact-extraction
pipeline builds a role-specialized memory corpus over time.

**Why it matters:** No existing platform gives every agent persona its own
isolated OS environment with persistent, role-scoped long-term memory. This
turns Bureau's role system from a prompt-level abstraction into a
hardware-level one.

---

### 12.2 Code-Review Fact Crystallization

Wire Bureau's Assess Mode output (comprehension model + per-file audit
findings) into Memoh's fact-extraction pipeline. Each review cycle produces
structured memory entries: "Module X violates single-responsibility since
commit abc123", "The retry logic in api_client.py silently swallows
ConnectionError". These crystallized facts are compacted, deduplicated, and
made retrievable via hybrid search on subsequent reviews and coding sessions.

**Why it matters:** Today, code review findings evaporate after the
conversation ends. Crystallizing them into searchable long-term memory means
the agent never re-discovers the same issue twice — and can proactively warn
when a new change risks re-introducing a previously identified defect.

---

### 12.3 Semantic Code Memory with Hybrid Retrieval ("CodeBrain")

Index an entire codebase into Memoh's hybrid retrieval stack: dense embeddings
for semantic similarity (e.g., "functions that handle authentication"),
neural sparse vectors for structural code patterns, and BM25 for exact
symbol/identifier lookup. Bureau agents query this unified index instead of
juggling separate Sourcegraph, Serena, and Qdrant tools. Compaction merges
stale entries when files are refactored, and rebuild reindexes after major
refactors or branch switches.

**Why it matters:** Current code search is fragmented across three disjoint
backends with no cross-query capability. A single hybrid retrieval pipeline
that understands both natural-language intent and exact symbol names would
collapse Bureau's tool-selection overhead and dramatically improve recall on
complex architectural queries.

---

### 12.4 Disposable Exploit Sandboxes ("Red Container")

When Scrimmage Mode generates attack vectors, execute each attack in a
purpose-built Memoh container that mirrors the target application's runtime
(same OS packages, same language version, same dependencies) but is fully
disposable. The container runs the exploit attempt, captures stdout/stderr,
filesystem diffs, and network traffic, then self-destructs. Results are
extracted and fed back to Bureau's security-compliance agent for verdict.

**Why it matters:** Running adversarial attack vectors in the same environment
as the development workspace is reckless — a successful exploit could corrupt
project state. Disposable containers let Bureau run genuine, unrestricted
penetration tests against its own code without any risk to the host.

---

### 12.5 Architecture Decision Records as Living Memory ("ADR-Mem")

Intercept architecture decisions made during Bureau sessions (detected via the
architect role, spec-kit plans, or explicit user declarations) and persist
them as first-class Memoh memory entries with structured metadata: decision
rationale, alternatives considered, constraints, date, and affected
components. On future queries, hybrid retrieval surfaces relevant past
decisions — e.g., when a developer asks "why don't we use Redis here?", the
agent retrieves the 3-month-old decision record explaining the choice of
PostgreSQL advisory locks instead.

**Why it matters:** Architecture decisions are the highest-leverage knowledge
in a codebase, yet they are the most likely to be lost. Encoding them into a
compactable, searchable memory system means the project's institutional
knowledge survives developer turnover, context switches, and the passage of
time.

---

### 12.6 Multi-Agent Parallel Debugging Swarm

When a complex bug is reported, Bureau's orchestrator spawns N Memoh
containers simultaneously — each running a different debugging strategy. One
container does binary git-bisect with test execution; another performs
backward taint analysis from the crash site; a third fuzzes the suspect
function with generated inputs; a fourth examines recent commit diffs for
suspicious changes. Each container's fact-extraction pipeline captures
findings. Bureau's orchestrator collects all containers' memory entries,
cross-references them, and synthesizes a unified diagnosis.

**Why it matters:** Sequential debugging is the bottleneck in complex
investigations. Parallel, isolated debugging containers turn a 45-minute
linear investigation into a 5-minute concurrent one — and the cross-referencing
step catches causal chains that any single strategy would miss.

---

### 12.7 Container-Isolated MCP Server Vetting

Before connecting a new, untrusted MCP server to Bureau's main process, first
spin up a Memoh container, install the MCP server there, and run a behavioral
audit: monitor its network calls, filesystem access patterns, resource
consumption, and response schemas across a battery of synthetic tool
invocations. The security-compliance agent analyzes the captured telemetry
and produces a trust score. Only servers that pass the audit get promoted to
Bureau's production MCP mesh.

**Why it matters:** MCP servers are arbitrary code that Bureau grants tool-call
access to. The current trust model is binary (installed or not). Container-
isolated vetting creates a graduated trust pipeline — try before you trust —
that is absent from every competing agent platform.

---

### 12.8 Cross-Session Debug Context Persistence ("Immortal Stacktrace")

When a debugging session ends without resolution, serialize the full
diagnostic context — stack traces, variable snapshots, hypotheses explored,
dead ends, partial fixes attempted — into Memoh's memory store as a
structured fact cluster. When the developer (or a different developer) returns
to the same issue days later, hybrid retrieval reconstructs the prior
investigation state, including which hypotheses were already eliminated.

**Why it matters:** Resuming an interrupted debugging session currently means
starting from scratch. Persisting diagnostic state as retrievable memory
eliminates redundant investigation and makes debugging progress cumulative
rather than ephemeral.

---

### 12.9 Blast Radius Simulation in Cloned Containers

Before Bureau's Blast Radius Mode marks a change as "safe" or "breaking",
actually prove it: clone the project into a Memoh container, apply the
proposed diff, run the full test suite, and compare results against a
baseline container running the unmodified code. The delta (new failures, new
warnings, performance regressions) is fed back to the blast-radius assessment
as empirical evidence rather than static analysis speculation.

**Why it matters:** Static impact analysis is inherently approximate — it
reasons about what *might* break. Running the change in a cloned container
measures what *actually* breaks. The combination of static analysis (fast,
broad) and dynamic proof (slow, precise) produces assessments that neither
approach achieves alone.

---

### 12.10 Per-User Knowledge Silos in Shared Projects

In multi-developer environments, leverage Memoh's cross-platform identity
binding and per-user context to maintain separate memory collections for each
team member. Developer A's preferences (coding style, review strictness,
preferred libraries) are stored in their silo; Developer B's in theirs.
Bureau's orchestrator selects the appropriate silo based on the authenticated
user, producing agent behavior that adapts per-developer without leaking
personal context across the team.

**Why it matters:** Current multi-user agent platforms are either fully shared
(everyone sees everything) or fully isolated (no shared project context). Per-
user silos within a shared project achieve both personalization and privacy —
a combination no existing coding agent offers.

---

### 12.11 Heartbeat-Driven Codebase Health Monitor

Configure Memoh's heartbeat scheduler to periodically wake a Bureau health-
monitor bot that runs lightweight codebase checks inside its container:
dependency audit (`npm audit` / `pip-audit`), dead code detection, test
coverage delta since last heartbeat, TODO/FIXME accumulation rate, and
security scan via Semgrep. Findings are extracted as memory entries and
compacted over time, building a longitudinal health profile. When thresholds
are breached, the bot proactively notifies the developer via Telegram,
Discord, or email.

**Why it matters:** Codebase health degrades silently between active
development sessions. A heartbeat-driven monitor that runs in an isolated
container, remembers historical trends, and alerts proactively closes the gap
between CI/CD (which runs only on push) and continuous awareness (which runs
always).

---

### 12.12 Provenance-Tracked Tool Execution Chains

Every tool invocation inside a Memoh container (shell command, file edit, MCP
call, browser action) is logged with full provenance: which Bureau agent role
initiated it, what memory entries informed the decision, what the input and
output were, and what downstream actions it triggered. This execution trace is
itself stored as a compactable memory graph. On future similar tasks, hybrid
retrieval over the provenance graph lets the agent replay or adapt prior
successful tool chains rather than re-discovering them from scratch.

**Why it matters:** Agent tool use today is memoryless — every session
rediscovers the same command sequences. Provenance-tracked execution chains
create a reusable "muscle memory" for tool use, accelerating repeated
workflows and enabling post-hoc audit of any agent action back to its
root cause.

---

## Sources

- [Memoh GitHub Repository](https://github.com/memohai/Memoh)
- [Memoh Documentation](https://docs.memoh.ai/)
- [Memoh Website](https://memoh.ai/)
- [Memoh Docker Deployment Guide (bitdoze)](https://www.bitdoze.com/memoh-ai-agent-deploy/)
- [Agent Wars 2026: OpenClaw vs Memu vs Nanobot](https://evoailabs.medium.com/agent-wars-2026-openclaw-vs-memu-vs-nanobot-which-local-ai-should-you-run-8ef0869b2e0c)
- [OpenClaw Alternatives Compared (shareuhack)](https://www.shareuhack.com/en/posts/openclaw-alternatives-guide)
- [Bureau Agent Framework Evaluation](/home/user/Bureau/docs/plans/2026-04-02-agent-framework-evaluation.md)
