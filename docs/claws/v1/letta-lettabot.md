# Letta + LettaBot Integration Analysis

**Date:** 2026-04-03
**Status:** Research Complete / Pre-Integration
**Targets:** Letta v0.16.7 (V1 architecture) + LettaBot (Node.js bridge)
**License:** Both Apache 2.0

---

## 1. Platform Overview

Letta and LettaBot form two complementary layers targeting the same problem Bureau faces: how to give AI agents persistent, structured memory and multi-channel presence.

**Letta** (formerly MemGPT) is a platform for building stateful AI agents. Its core thesis is the "LLM-as-Operating-System" paradigm -- the language model manages its own memory hierarchy the way an OS manages virtual memory, paging information in and out of a finite context window. The V1 agent architecture (`letta_v1_agent`) represents a significant departure from the original MemGPT design: heartbeats and the `send_message` tool are deprecated, native reasoning tokens are supported (OpenAI Responses API), and base system prompts are simplified. Performance is specifically tuned for GPT-5 and Claude 4.5 Sonnet. With 176 releases, full REST/Python/TypeScript SDKs, and deployment options spanning CLI (Letta Code), hosted (app.letta.com), and self-hosted Docker with PostgreSQL, Letta is a mature infrastructure layer.

**LettaBot** is a Node.js 20+ chat bridge that connects a single Letta agent to Telegram, Slack, Discord, WhatsApp, Signal, and Bluesky (read-only). It is not a framework -- it is a thin routing layer that maps inbound messages from multiple channels to one Letta agent's API, giving that agent unified memory across all surfaces. Built on the Letta Code SDK, it authenticates via API keys and identifies the target agent by `agent_id`.

Together, they provide what Bureau currently assembles from disparate parts: a memory-equipped agent backend (Letta) and a channel multiplexer (LettaBot). The question is whether adopting them consolidates Bureau's stack or merely adds another layer.

---

## 2. Memory Architecture

This is Letta's crown jewel and the primary reason to evaluate it against Bureau's fragmented memory stack.

### Letta Memory Tiers

| Tier | Scope | Persistence | Mechanism |
|------|-------|-------------|-----------|
| **Core Memory Blocks** | Always in context window | Database-backed, survives restarts | Structured sections (human, persona, custom) that the agent reads every turn |
| **Human Memory Block** | Per-user contextual info | Persistent | Subset of core memory; stores facts, preferences, history about the user |
| **Persona Memory Block** | Agent identity/behavior | Persistent | Subset of core memory; behavioral guidelines, personality, operational rules |
| **Archival Memory** | Long-term knowledge | Vector-searchable database | Equivalent to a per-agent RAG store; agent can write and query |
| **Recall Memory** | Conversation history | Database-backed | Searchable message log; agent can retrieve past conversations |

### Bureau Memory Stack (Current)

| Layer | Tool | Role |
|-------|------|------|
| **Semantic** | Qdrant | Vector search over knowledge fragments |
| **Structural** | Memory MCP | Hierarchical entity/relation storage |
| **Session** | claude-mem | Per-session working memory |
| **Dossier** | Custom files | Agent-specific persistent knowledge |

### Comparative Analysis

The fundamental difference: Letta persists state in databases, not Python variables. Bureau's stack is fragmented across three to four tools with no unified API. Letta provides a single, coherent memory interface where every tier is accessible through the same SDK.

Where Letta is stronger:
- Core memory blocks guarantee certain information is always in the context window without retrieval calls, eliminating the "forgot to check memory" failure mode.
- The human/persona split is a clean abstraction Bureau lacks -- Bureau's dossier system conflates agent identity with user knowledge.
- Archival memory subsumes Qdrant's role with tighter agent integration.

Where Bureau's stack is stronger:
- Qdrant supports cross-agent semantic search; Letta's archival memory is per-agent.
- Memory MCP's entity-relation model captures structured relationships (agent A depends on tool B) that Letta's flat memory blocks do not natively represent.
- Bureau's fragmentation, while operationally messy, allows each layer to be independently optimized or replaced.

---

## 3. Autonomous Learning Loop

The most architecturally significant feature of Letta is self-editing memory: agents actively modify their own memory blocks using built-in memory tools. This is not passive logging -- it is an autonomous learning loop.

**How it works:**
1. The agent receives a message.
2. Core memory blocks (human, persona, custom) are injected into the context window.
3. The agent processes the message and decides whether its memory needs updating.
4. Using memory tools, the agent edits core blocks, writes to archival memory, or both.
5. On the next turn, the updated memory is already in context.

**Why this matters for Bureau:** Bureau's 66 agent roles currently have no mechanism to learn from interactions. An agent that fails a task today will fail the same way tomorrow unless a human updates its dossier or prompt. Letta's self-editing memory would allow Bureau agents to:
- Accumulate operational knowledge (e.g., "this repository uses pnpm, not npm").
- Refine their own behavioral guidelines based on user feedback.
- Build progressively richer user models without explicit dossier maintenance.

**The risk:** Unconstrained self-editing can lead to memory drift, where agents gradually rewrite their own guidelines in ways that diverge from intended behavior. Any integration must include memory auditing and rollback capabilities.

---

## 4. Operational Memory Stack

If Bureau adopts Letta as its memory backend, the operational mapping would be:

| Bureau Need | Letta Component | Notes |
|-------------|-----------------|-------|
| Agent identity/prompt | Persona memory block | Replaces static system prompts with editable persona blocks |
| User context | Human memory block | Replaces dossier user sections |
| Session state | Core memory (custom blocks) | Replaces claude-mem; always in context |
| Knowledge retrieval | Archival memory | Replaces Qdrant for per-agent knowledge |
| Conversation history | Recall memory | Native; no additional tooling needed |
| Cross-agent knowledge | Shared memory blocks or archival | Requires custom implementation; Letta does not natively support cross-agent memory |
| Entity-relation graphs | Not natively supported | Memory MCP would need to remain or be replicated as custom blocks |

The critical gap is cross-agent memory. Bureau's orchestration model requires agents to share context (e.g., Assess Mode producing findings that Micro Mode consumes). Letta's per-agent memory model would require either shared memory blocks (configurable via `memory_blocks` per agent) or an external coordination layer.

---

## 5. Practical Assistant Features

LettaBot adds several operational capabilities relevant to Bureau's Telegram concierge bot:

**Heartbeat mechanism:** Periodic check-ins where the agent proactively reaches out. Bureau's concierge currently only responds to inbound messages. Heartbeats enable proactive status updates, reminders, and ambient awareness.

**Task scheduling:** Native scheduling support. Bureau currently has no built-in task scheduler for its Telegram interface.

**Voice support:** Transcription via OpenAI Whisper or Mistral Voxtral, TTS via ElevenLabs or OpenAI. Native voice bubbles on Telegram, WhatsApp, Signal, Slack, and Discord. Bureau has no voice pipeline.

**Streaming responses:** LettaBot streams responses from the Letta agent, reducing perceived latency on chat channels.

**Conversation routing modes:**
- *Shared:* One conversation state across all channels (single memory context).
- *Per-channel:* Separate conversation threads per adapter (Telegram sees different history than Slack).
- *Group modes:* Open (respond to all), listen (absorb to memory, reply only on mention), mention-only, disabled.

The group modes are particularly relevant. Bureau's Telegram bot currently lacks nuanced group behavior -- it either responds to everything or nothing. LettaBot's "listen" mode (memory only, reply on mention) would allow the bot to passively learn from group conversations without being disruptive.

---

## 6. SWE Assistant Features

Letta Code is positioned as a software engineering assistant with:

- **Skills and subagents:** Pre-built skills and subagents for advanced memory and continual learning. This maps to Bureau's workflow skills (Assess Mode, Micro Mode) but with the advantage of persistent memory across skill invocations.
- **Node.js 18+ CLI:** Letta Code runs as a CLI tool, similar to Bureau's target coding CLIs (Claude Code, Gemini CLI, Codex, OpenCode).

However, Letta Code is not a coding CLI itself -- it is an agent framework that could back one. Bureau's value proposition is orchestrating existing coding CLIs, not replacing them. Letta Code's skills system is complementary: Bureau orchestrates the CLI, Letta provides the memory layer that persists across orchestration sessions.

---

## 7. Channel & Platform Support

### LettaBot Channel Matrix

| Channel | Send | Receive | Voice | Group | Notes |
|---------|------|---------|-------|-------|-------|
| Telegram | Yes | Yes | Native bubbles | All modes | Primary target |
| Slack | Yes | Yes | Native bubbles | All modes | |
| Discord | Yes | Yes | Native bubbles | All modes | |
| WhatsApp | Yes | Yes | Native bubbles | All modes | |
| Signal | Yes | Yes | Native bubbles | All modes | |
| Bluesky | No | Yes (feed) | No | N/A | Read-only ingestion |

### Bureau Channel Status

Bureau currently supports Telegram via its concierge bot with ML classification pipeline. LettaBot would extend this to five additional channels with zero custom adapter code, plus add voice capabilities across all of them.

**Key consideration:** LettaBot routes all channels to a single Letta agent. Bureau's concierge bot routes to 66 agent roles. The integration must either:
1. Use LettaBot purely as a channel adapter, forwarding to Bureau's routing layer.
2. Make Bureau's agent roles available as Letta tools/subagents that the single Letta agent can invoke.
3. Run multiple LettaBot instances, one per agent role (impractical at 66 roles).

Option 2 is the most architecturally clean: the Letta agent becomes Bureau's "front door" with unified memory, and Bureau's agent roles become its specialized tools.

---

## 8. Security Model

**Letta:**
- API key authentication (hosted or self-hosted).
- Self-hosted deployment keeps all data on-premises (PostgreSQL backend).
- Memory is database-backed -- standard database security applies (encryption at rest, access controls, backups).
- Self-editing memory introduces a novel attack surface: prompt injection could cause an agent to corrupt its own memory blocks. No built-in memory integrity verification is documented.
- Alembic migrations for schema evolution imply database schema changes between versions.

**LettaBot:**
- All outbound connections -- no public URL or webhook endpoint required. This is a significant security advantage; the bot initiates all connections, reducing attack surface.
- Configuration via `lettabot.yaml` including tool restrictions (can limit which Letta tools the agent may invoke through the bridge).
- API keys stored in configuration files -- standard secrets management applies.

**Bureau-specific concerns:**
- Bureau's MCP servers (15+) would need access controls if exposed as Letta tools.
- The ML classification pipeline in the Telegram concierge would need to operate upstream of LettaBot's routing, or be reimplemented within Letta's tool framework.
- Memory auditing is essential if self-editing memory is enabled for Bureau agents.

---

## 9. Integration Architecture

### Proposed Architecture: Letta as Unified Memory + LettaBot as Channel Multiplexer

```
Channels                    Bridge              Memory/Agent Layer           Orchestration
---------                   ------              ------------------           -------------
Telegram  --\                                   
Slack     ---\              LettaBot            Letta Agent                  Bureau
Discord  ----+-- messages ---> (Node.js) -----> (unified memory) ---------> Orchestrator
WhatsApp --/                    |               - Core blocks (identity)     - 66 agent roles
Signal  -/                      |               - Human block (user ctx)     - Workflow skills
                                |               - Archival (knowledge)       - MCP servers
                            Voice pipeline      - Recall (history)           - Coding CLIs
                            (Whisper/ElevenLabs)
```

### Layer Responsibilities

**LettaBot (channel layer):**
- Receives messages from all supported channels.
- Handles voice transcription/synthesis.
- Manages conversation routing modes (shared, per-channel, group behaviors).
- Streams responses back to channels.
- Replaces Bureau's custom Telegram adapter.

**Letta Agent (memory + routing layer):**
- Maintains unified memory across all channels and sessions.
- Replaces Qdrant (archival memory), Memory MCP (core blocks), claude-mem (session state), and dossier files (persona/human blocks).
- Routes requests to Bureau agent roles exposed as Letta tools/subagents.
- Learns autonomously via self-editing memory.

**Bureau Orchestrator (execution layer):**
- Retains all 66 agent roles, workflow skills, and MCP servers.
- Exposed to Letta as callable tools via Letta's REST API.
- Coding CLI orchestration (Claude Code, Gemini CLI, Codex, OpenCode) remains Bureau's domain.
- ML classification pipeline migrates from Telegram-specific to channel-agnostic (operates on text extracted by LettaBot).

### Migration Path

1. **Phase 1 -- Parallel operation:** Deploy Letta alongside existing memory stack. LettaBot handles new channels (Slack, Discord, WhatsApp, Signal); Telegram remains on Bureau's existing adapter. Letta archival memory mirrors Qdrant.
2. **Phase 2 -- Memory consolidation:** Migrate dossier content to persona/human memory blocks. Route Telegram through LettaBot. Retire claude-mem in favor of core memory blocks.
3. **Phase 3 -- Full integration:** Bureau agent roles registered as Letta tools. ML classification operates within Letta's tool selection. Qdrant retained only for cross-agent semantic search if Letta's shared blocks prove insufficient.

---

## 10. Fit Assessment

| Dimension | Fit | Rationale |
|-----------|-----|-----------|
| **Memory unification** | **Strong** | Letta's tiered memory directly replaces Bureau's fragmented stack (Qdrant + Memory MCP + claude-mem + dossiers) with a single coherent system. Database persistence is superior to file-based dossiers. |
| **Multi-channel support** | **Strong** | LettaBot adds five channels (Slack, Discord, WhatsApp, Signal, Bluesky) with zero custom code. Voice support is a net-new capability. All-outbound connection model is operationally clean. |
| **Autonomous learning** | **Strong** | Self-editing memory is the single most impactful capability Bureau lacks. Agents that learn from interactions without human dossier maintenance is a qualitative leap. |
| **Agent orchestration** | **Moderate** | Letta's multi-agent support (skills, subagents) overlaps with but does not replace Bureau's 66-role orchestration. Bureau's orchestration is more sophisticated; Letta provides the memory backbone, not the routing logic. |
| **Coding CLI integration** | **Moderate** | Letta Code is complementary but not a replacement for Bureau's CLI orchestration. Memory persistence across coding sessions is valuable; Letta does not orchestrate Claude Code or Gemini CLI directly. |
| **Cross-agent memory** | **Weak** | Letta's per-agent memory model does not natively support Bureau's cross-agent context sharing. Shared memory blocks are configurable but not designed for 66 agents sharing findings in real time. |
| **Entity-relation modeling** | **Weak** | Memory MCP's structured entity-relation graphs have no direct equivalent in Letta. Core memory blocks are flat text, not graph structures. This capability would need to be retained or reimplemented. |
| **macOS focus** | **Moderate** | Letta is Python-based (compatible), LettaBot is Node.js (compatible), Docker self-hosting works on macOS. No platform-specific issues, but no macOS-specific advantages either. |
| **License compatibility** | **Strong** | Both Apache 2.0 -- fully compatible with any Bureau licensing model. |
| **Maturity** | **Strong** | 176 releases, v0.16.7, active development, three SDK options (Python, TypeScript, REST). Production-grade infrastructure. |

---

## 11. Risks & Tradeoffs

### Risks

**Memory drift from self-editing.** Agents rewriting their own persona blocks can gradually diverge from intended behavior. Without memory versioning, rollback, or integrity checks, a single bad self-edit can cascade. Mitigation: implement memory snapshots and diff-based auditing before enabling self-editing for production agents.

**Single-agent bottleneck.** LettaBot routes all channels to one Letta agent. Bureau has 66 roles. If the Letta agent becomes the routing layer, it is a single point of failure and a potential latency bottleneck. Mitigation: the Letta agent should be a thin dispatcher; heavy work stays in Bureau's agent roles.

**Cross-agent memory gap.** Bureau's workflow skills (Assess Mode producing findings for Micro Mode) require shared context. Letta's per-agent model means either maintaining a parallel cross-agent memory system or building custom shared-block infrastructure. This is the largest architectural gap.

**Migration complexity.** Replacing four memory systems (Qdrant, Memory MCP, claude-mem, dossiers) with one is conceptually clean but operationally risky. Data migration, format translation, and ensuring no context loss during transition require careful planning.

**Dependency addition.** Adopting Letta adds PostgreSQL (for self-hosted) or a third-party hosted service (app.letta.com) as a hard dependency. Bureau currently runs without external database dependencies for its memory stack.

**V1 architecture churn.** The V1 agent architecture is a "significant departure" from MemGPT. Deprecation of heartbeats and send_message in V1 suggests the API surface is still stabilizing. Building deep integrations against a moving target carries version-lock risk.

### Tradeoffs

| Gain | Cost |
|------|------|
| Unified memory API | Loss of per-layer optimization flexibility |
| Five new channels via LettaBot | Node.js dependency added to Python-based Bureau |
| Self-editing memory / learning | Memory integrity risk, need for auditing infrastructure |
| Voice pipeline (Whisper, ElevenLabs) | Additional API costs and latency |
| Database-backed persistence | PostgreSQL operational overhead (self-hosted) or vendor dependency (hosted) |
| Simplified memory tooling | Memory MCP entity-relation capabilities must be retained separately |
| Proactive features (heartbeat, scheduling) | Heartbeat deprecated in V1 -- LettaBot's heartbeat mechanism may need adaptation |

### Recommendation

Letta + LettaBot is the strongest memory-layer candidate evaluated for Bureau integration. The self-editing memory system, tiered memory architecture, and multi-channel bridge via LettaBot address Bureau's three biggest gaps: fragmented memory, single-channel presence, and lack of autonomous learning.

The integration should proceed as a memory-layer replacement with LettaBot as channel adapter, not as a wholesale framework migration. Bureau's orchestration logic, agent roles, workflow skills, and coding CLI integration remain Bureau's domain. Letta provides the stateful memory backbone; LettaBot provides the channel surface.

Priority: address the cross-agent memory gap before Phase 3. If shared memory blocks prove insufficient for 66-agent context sharing, a hybrid approach retaining Qdrant for cross-agent semantic search alongside Letta for per-agent memory is the pragmatic path.

---

## 12. High-Impact Feature Merges & Extensions

The following ideas represent high-leverage integration points where Bureau's multi-agent orchestration and Letta's stateful memory architecture produce capabilities that neither system can achieve alone.

### 12.1 Evolutionary Role Genomes

Each of Bureau's 66 agent roles becomes a Letta agent whose persona memory block functions as a living "genome" -- a self-editing behavioral specification that mutates based on task outcomes. After every task delegation, the agent writes a structured outcome record (success/failure, time taken, user satisfaction signal) to its archival memory, then periodically rewrites its own persona block to reinforce strategies correlated with success and deprecate those correlated with failure. Over hundreds of invocations, each role evolves into a specialist finely tuned to the specific codebase, team, and problem distribution it encounters -- without any human prompt engineering.

**Why it matters:** Today, Bureau's role prompts are static text written once by a human. This turns them into living documents that optimize themselves, creating agents that are measurably better at their jobs after 100 tasks than after 10.

### 12.2 Cross-Agent Recall Mesh

Implement a shared archival memory partition accessible to all 66 Bureau agents, functioning as an organizational "institutional memory." When any agent encounters a novel pattern -- a tricky debugging solution, an architectural decision rationale, a security vulnerability class -- it writes a structured knowledge fragment to the shared partition with metadata tags (domain, confidence, source agent, timestamp). Other agents query this mesh before starting work, effectively inheriting the accumulated experience of every other agent in the system. A relevance-decay function deprioritizes stale knowledge, and conflicting entries trigger a reconciliation protocol where the originating agents are re-queried.

**Why it matters:** Bureau's agents currently operate in hermetic isolation -- the debugger's hard-won insight about a race condition never reaches the architect planning the next module. This creates a collective intelligence where the system as a whole becomes smarter than any individual agent.

### 12.3 Dossier-to-Living-Memory Migration Engine

Build a one-shot migration tool that parses Bureau's existing dossier files and decomposes them into Letta memory tiers: identity/behavioral content maps to persona blocks, user-specific knowledge maps to human blocks, reference material maps to archival memory with vector embeddings, and session-specific transient notes map to custom core blocks. Post-migration, the dossier format is retired entirely -- agents read and write structured memory blocks instead of flat markdown files. A reverse-export function can snapshot the current memory state back into dossier-format markdown for human review or version control.

**Why it matters:** Bureau's dossier system is the single largest source of maintenance burden. Migrating it to self-maintaining Letta memory blocks eliminates manual dossier upkeep while preserving (and enhancing) every piece of accumulated knowledge.

### 12.4 Code Review Pattern Crystallization

The Assess Mode skill writes its findings -- comprehension model, per-file audit results, quality standard violations -- into the invoking agent's archival memory as structured review records. Over successive reviews of the same codebase, Letta's recall memory builds a longitudinal dataset of what kinds of issues recur, which files are chronic problem areas, and which quality standards the team consistently violates versus consistently meets. The agent then edits its own core memory to create a "review prior" -- a compressed summary of known hotspots, common anti-patterns, and team-specific style preferences -- that is automatically injected into the context window at the start of every future review, making each review faster and more targeted than the last.

**Why it matters:** Code review today is memoryless -- every review starts from zero. This creates a reviewer that has read every past review and remembers what it found, turning Assess Mode from a stateless tool into a continuously improving quality oracle.

### 12.5 Five-Channel Unified Development Console

LettaBot's five channels (Telegram, Slack, Discord, WhatsApp, Signal) each serve a distinct development workflow surface, all backed by a single Letta agent with unified memory. Telegram becomes the mobile triage interface (quick approvals, status checks, alerts). Slack becomes the team collaboration surface (Bureau agent outputs posted to channels, threaded discussions with the agent). Discord hosts a persistent "war room" for long-running debugging sessions with voice narration via ElevenLabs TTS. WhatsApp serves as the emergency escalation path with voice-note-driven incident response (Whisper transcription into the agent's recall memory). Signal handles security-sensitive communications (credential rotation confirmations, vulnerability disclosures). The Letta agent's core memory maintains a unified "operational state" block that synchronizes context across all five surfaces -- a conversation started on Telegram can be continued on Slack with full context.

**Why it matters:** Developers currently context-switch between tools and lose state. This creates a single agent that follows the developer across every communication surface, maintaining perfect continuity -- something no existing coding assistant offers.

### 12.6 Speculative Pre-Computation via Heartbeat Cycles

Repurpose LettaBot's heartbeat mechanism (periodic unprompted agent activation) as a speculative pre-computation engine. During idle heartbeat cycles, the Letta agent examines its recall memory for recent conversations and archival memory for pending tasks, then proactively delegates work to Bureau agents: running Assess Mode on recently modified files, pre-computing blast radius analysis for open PRs, refreshing stale memory entries by re-querying codebases via Serena/Sourcegraph, and pre-fetching API documentation via Context7 for libraries mentioned in recent conversations. Results are written to archival memory with a "speculative" tag. When the user next interacts, the agent checks for relevant speculative results and presents them immediately, creating the illusion of instant, anticipatory assistance.

**Why it matters:** Every existing coding assistant is purely reactive -- it waits for you to ask. This creates an agent that works while you sleep, so your next morning standup starts with a pre-computed status report and your next code review is already half-done.

### 12.7 Memory-Versioned Rollback Trees

Implement a git-like versioning layer over Letta's memory blocks. Every self-edit to a persona block, human block, or custom block is recorded as a diff with a parent pointer, forming a tree of memory states. Agents can branch their memory (e.g., "try an aggressive refactoring style for this sprint"), and if the branch produces worse outcomes (measured by task success rates in archival memory), roll back to the parent state. A CLI command (`bureau memory log <agent-role>`) displays the memory evolution history. A diff viewer shows exactly what the agent changed about its own beliefs and when. Critical for the Evolutionary Role Genomes feature (12.1): without rollback, a single bad self-edit can permanently degrade an agent.

**Why it matters:** Self-editing memory without version control is like code without git -- one bad commit and you lose everything. This makes autonomous learning safe by making it reversible, which is the prerequisite for trusting agents to modify their own behavior.

### 12.8 Multi-Agent Debate with Shared Working Memory

When Bureau dispatches a complex task (e.g., "design the authentication system"), multiple agent roles (architect, security-compliance, api-design, performance) are each instantiated as Letta agents that share a single custom core memory block labeled "debate-workspace." Each agent reads the workspace, appends its perspective with structured reasoning, and the next agent reads the accumulated perspectives before adding its own. The workspace block functions as a real-time blackboard visible to all participants. After all agents have contributed, a synthesizer agent reads the full debate workspace plus each agent's archival memory (for historical context on similar decisions) and produces a final recommendation. The entire debate transcript is preserved in archival memory for future reference.

**Why it matters:** Bureau can already dispatch to multiple agents, but they cannot see or respond to each other's reasoning. Shared working memory turns parallel independent analysis into genuine collaborative deliberation -- the difference between asking five experts separately and putting them in a room together.

### 12.9 Adaptive Skill Activation via Memory-Driven Classification

Replace Bureau's current prompt-matching skill activation with a Letta memory-driven classifier. The agent maintains a core memory block containing a compressed decision tree: given task characteristics (keywords, file types, repository structure, recent history from recall memory, user preferences from human block), which skill (Assess Mode, Micro Mode, Scrimmage Mode, etc.) produces the best outcomes? This decision tree self-edits based on observed results -- if Scrimmage Mode consistently catches issues that Assess Mode misses in security-critical repos, the agent learns to prefer Scrimmage Mode for those contexts. The agent also learns compound skill sequences: "for this user, always run Blast Radius Mode before Micro Mode" -- a personalized workflow that emerges from memory, not configuration.

**Why it matters:** Skill activation today is rigid pattern matching. This creates a system that learns which workflows work best for which situations and which users, turning Bureau's skill catalog into an adaptive toolkit that configures itself.

### 12.10 Context-Aware Model Routing with Historical Performance Memory

Bureau supports four CLI backends (Claude Code, Gemini CLI, Codex, OpenCode). Build a Letta-backed routing layer where the dispatching agent maintains archival memory records of task-model performance pairs: "Claude Code completed architecture tasks in 45s avg with 92% user acceptance; Gemini CLI completed broad code search tasks in 12s avg with 88% acceptance." The agent's core memory holds a compressed routing table derived from these records, which self-edits as new data arrives. When a task comes in, the agent consults its routing table, current model availability (via heartbeat-driven health checks stored in memory), and the user's human memory block (which may contain explicit preferences like "prefer Claude for reviews") to select the optimal CLI backend. This transforms Bureau's `handoff-guide.md` from a static document into a continuously learning routing optimizer.

**Why it matters:** Bureau's handoff guide is a human-written heuristic. This replaces it with an empirical, self-improving routing function that gets better at choosing the right model for the right task with every interaction -- personalized to the specific user, codebase, and task distribution.

### 12.11 Incident Replay and Post-Mortem Memory

When a debugging session occurs (via the debugger agent role), the entire investigation is recorded as a structured "incident record" in archival memory: initial symptoms, hypotheses explored, dead ends encountered, root cause identified, and fix applied. These records are tagged with error signatures (exception types, stack trace patterns, error message templates). On future incidents, before the debugger begins work, it queries archival memory for matching error signatures and retrieves relevant past incident records. If a match is found, the debugger's core memory is pre-loaded with the previous investigation path, allowing it to skip dead ends and jump directly to likely root causes. Over time, the system builds a codebase-specific incident knowledge base that makes debugging progressively faster.

**Why it matters:** Debugging the same class of issue twice is pure waste. This creates a debugger with perfect recall of every past investigation, turning repeated incidents from full investigations into instant pattern matches -- the equivalent of a senior engineer who has "seen this before."
