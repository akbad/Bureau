# CoPaw Integration Analysis

**Date:** 2026-04-03
**Status:** Research complete
**Project:** [agentscope-ai/CoPaw](https://github.com/agentscope-ai/CoPaw) (Apache 2.0)
**Website:** [copaw.bot](https://copaw.bot/)
**Parent org:** AgentScope (Alibaba)

---

## 1. Platform Overview

CoPaw ("Co Personal Agent Workstation") is an open-source, self-hostable
personal AI assistant built on top of the AgentScope framework.  It targets
always-on personal assistant use-cases with broad channel support and strong
local-first privacy guarantees.

Key facts:

- **Language:** Python (PyPI package: `copaw`)
- **Framework dependency:** AgentScope (agent runtime) + ReMe (memory management)
- **Model layer:** Unified provider supporting cloud APIs (Qwen series, mainstream
  LLMs), Ollama, llama.cpp (built-in with auto-download), MLX (Apple Silicon
  native), and self-hosted inference services
- **Deployment:** Local machine, cloud VM, or hybrid (local for cheap tasks, cloud
  models for complex reasoning)
- **License:** Apache 2.0
- **Maturity:** Latest release v0.2.0; active development with >2400 issues filed

CoPaw is not a coding CLI orchestrator.  It is a **general-purpose personal
assistant** with broad channel coverage and a focus on Asia-platform messaging
apps.  The overlap with Bureau is in the concierge/bot layer, memory subsystems,
scheduling, and security model.

---

## 2. Memory Architecture

CoPaw delegates all long-term memory to **ReMe** (Remember Me, Refine Me), a
standalone library by the same AgentScope team.

### ReMe four-layer architecture

| Layer | Responsibility |
|---|---|
| **ReMe Class Layer** | Public API; entry point for CoPaw code |
| **Handler Layer** | `MemoryHandler` + `ProfileHandler` for low-level read/write |
| **Agent Layer** | Specialized memory agents that delegate to type-specific processors |
| **Storage Layer** | Vector stores, embedding models, profile files via `ServiceContext` |

### Vector store backends

ReMe supports pluggable vector stores:

- **Local** (default, file-based)
- **Chroma**
- **Qdrant**
- **Elasticsearch**

### Context management

CoPaw's `ContextChecker` uses token counting to determine when context exceeds
configurable thresholds and automatically splits messages into a "to compact"
group and a "to keep" group.  This is a sliding-window + summarization approach,
not the multi-backend fragmentation Bureau currently uses.

### Comparison with Bureau memory stack

| Dimension | Bureau | CoPaw / ReMe |
|---|---|---|
| Backends | Qdrant + Memory MCP + claude-mem (fragmented) | ReMe (unified API over pluggable stores) |
| Unification | Three separate systems, no cross-query | Single ReMe API, one query path |
| Profile/preference tracking | Manual / MCP-based | First-class `ProfileHandler` |
| Semantic search | Qdrant | Qdrant, Chroma, ES, or local |
| Context compaction | None (manual dossiers) | Automatic via `ContextChecker` |

**Takeaway:** ReMe's unified API is cleaner than Bureau's fragmented stack.
If integrating, Bureau could either adopt ReMe as a memory backend or use its
architecture as a template for unifying the existing three backends.

---

## 3. Autonomous Learning Loop

CoPaw's **Heartbeat** mechanism is its version of proactive autonomy:

- A Markdown file defines a set of questions/tasks
- A timer fires on a configurable schedule (cron-based)
- CoPaw runs through the questions and sends answers to the last-used channel
- Use-cases: check emails, compile reports, track news, organize to-dos

This is conceptually similar to Bureau's WIP proactive features but is
**production-ready** in CoPaw.  The loop is:

```
timer fires -> load heartbeat.md -> execute each question as a task
            -> send results to active channel -> sleep until next tick
```

CoPaw does not have a "learning loop" in the reinforcement-learning sense.
Its autonomy is schedule-driven, not feedback-driven.  It remembers user
preferences via ReMe's ProfileHandler but does not self-modify its behavior
based on outcome signals.

---

## 4. Operational Memory Stack

CoPaw's operational memory stack during a running session:

| Component | Role |
|---|---|
| **Conversation buffer** | In-memory message history for the active session |
| **ContextChecker** | Token-counting gate; triggers compaction when threshold exceeded |
| **ReMe long-term store** | Persisted vector store (Qdrant/Chroma/local) for cross-session recall |
| **ProfileHandler** | Structured user preferences, updated on-the-fly |
| **Knowledge base** | File-indexed searchable store (PDFs, docs, local files) with semantic + exact match |
| **File watcher** | Monitors `memory.md` and syncs changes to vector store (see issue #666 for known bugs) |

The stack is coherent: short-term buffer feeds into long-term store via
compaction, and the knowledge base is a parallel read path for document search.

---

## 5. Practical Assistant Features

CoPaw ships a broad set of built-in "skills" (its term for plugins):

| Skill | Description |
|---|---|
| **Cron / Scheduling** | Scheduled messages and recurring tasks via CLI or API |
| **News digest** | Track tech/AI news, compile daily summaries |
| **File management** | Organize, search, read local files; request files via chat |
| **Document processing** | Read & summarize PDFs, Word, Excel, PPT |
| **Knowledge base** | Index local documents for semantic search |
| **Heartbeat** | Autonomous check-ins (see section 3) |
| **Custom skills** | User-installable via CLI (`copaw skill install`) |

Skills are managed like packages: install, remove, configure, list.  The skill
system includes security scanning before installation (see section 8).

---

## 6. SWE Assistant Features

CoPaw is **not a software engineering assistant**.  It has no:

- Code generation or editing workflows
- Repository-aware context loading
- Test runner integration
- Multi-file refactoring
- Step-gated editing (Bureau's Micro Mode)
- Code assessment pipelines (Bureau's Assess Mode)
- MCP server integration for dev tools

Its file-management and shell-execution capabilities are general-purpose, not
dev-focused.  This is the key non-overlap with Bureau: CoPaw handles the
"personal assistant / concierge" domain; Bureau handles the "coding CLI
orchestration" domain.

---

## 7. Channel & Platform Support

| Channel | CoPaw | Bureau |
|---|---|---|
| **DingTalk** | Native | None |
| **Feishu (Lark)** | Native | None |
| **QQ** | Native | None |
| **Discord** | Native | None |
| **iMessage** | Native (macOS only) | None |
| **Telegram** | Supported | Native (primary) |
| **WeChat** | Community/planned | None |
| **Console / CLI** | Yes | Yes (via CLIs) |
| **Custom channels** | Pluggable via CLI | Pluggable (adapter pattern) |

CoPaw's channel management uses a CLI-driven model: `copaw channel add discord`,
etc.  Each channel is a transport adapter, similar to Bureau's
`bridge/telegram.py` + `bridge/adapter.py` pattern.

### iMessage integration (macOS-specific)

CoPaw's iMessage channel runs on macOS and connects through the user's iCloud
account.  It supports attachments, reactions, and thread continuity.  This is a
differentiating feature that no other framework in the competitive set offers
with this level of integration.  It requires macOS as the host OS.

---

## 8. Security Model

CoPaw has a three-layer security model that is more mature than Bureau's
current single-user filter + env var approach.

### 8.1 Tool Guard

A **pre-execution security layer** that scans tool call parameters before execution:

- **Dangerous shell patterns:** `rm -rf /`, fork bombs, reverse shells, pipe to
  bash, broad `kill`, `dd` writes to block devices
- **System control:** reboot, shutdown, service stop/start, privilege escalation
  (`sudo`, `su`, `chmod 777`)
- **Network exfiltration:** `curl | bash`, `wget | sh`, outbound `nc` listeners

Blocked calls require explicit user approval via `/approve` command.  Permanently
denied patterns are always blocked regardless of approval.

### 8.2 File Access Guard

Restricts agent access to sensitive filesystem paths:

- `~/.ssh/`, `~/.gnupg/`, `~/.aws/`, system key files
- `/etc/passwd`, `/etc/shadow`, system config directories
- Configurable allowlist/denylist

### 8.3 Skill Security Scanning

Before a skill is installed, CoPaw scans the skill code for:

- **Prompt injection patterns** (including Chinese-language regex patterns)
- **Command injection** (shell metacharacters in string templates)
- **Hardcoded secrets** (API keys, tokens, passwords in source)
- **Data exfiltration** (outbound HTTP calls to non-allowlisted domains)
- **Jailbreak attempts** (instruction override patterns)

### Comparison with Bureau

| Dimension | Bureau | CoPaw |
|---|---|---|
| Pre-execution tool scanning | None (relies on Claude's judgment) | Tool Guard with pattern matching |
| File access restriction | None | File Access Guard with path denylist |
| Skill/plugin vetting | None | Security scanner pre-install |
| Auth model | Single Telegram user ID filter | Per-channel auth + local-only default |
| Secret management | Env vars + `.env` files | Local storage, no third-party upload |

**Takeaway:** CoPaw's security model is significantly more mature.  Bureau
should consider adopting similar pre-execution guards, especially if expanding
to multi-channel or multi-user scenarios.

---

## 9. Integration Architecture

### Thesis: CoPaw as macOS front door, Bureau as dev backend

The two systems have **complementary, non-overlapping strengths**:

```
                    +------------------+
                    |     Channels     |
                    | iMessage, QQ,    |
                    | DingTalk, Feishu,|
                    | Discord          |
                    +--------+---------+
                             |
                    +--------v---------+
                    |     CoPaw        |
                    | (personal asst)  |
                    | - scheduling     |
                    | - file mgmt      |
                    | - news digest    |
                    | - tool guards    |
                    | - ReMe memory    |
                    +--------+---------+
                             |
                   intent = "code task"
                             |
                    +--------v---------+
                    |     Bureau       |
                    | (dev backend)    |
                    | - 66 agent roles |
                    | - Micro Mode     |
                    | - Assess Mode    |
                    | - 15+ MCP servers|
                    | - dossiers       |
                    +------------------+
```

### Integration points

**A. Channel bridge (high value, moderate effort)**

CoPaw's channel adapters feed into Bureau's `MessageEnvelope` pipeline.
Implementation:

1. CoPaw receives message on any channel (iMessage, Discord, QQ, etc.)
2. CoPaw's classifier determines if the intent is a "code task"
3. Code tasks are forwarded to Bureau's concierge pipeline via HTTP/IPC
4. Bureau processes through its classify -> suite detect -> hard rules ->
   feature eval -> response pipeline
5. Response is returned to CoPaw, which delivers it on the originating channel

This gives Bureau instant access to 6+ channels without building each adapter.

**B. Memory bridge (moderate value, moderate effort)**

Option 1: Bureau adopts ReMe as a unified memory backend, replacing the
fragmented Qdrant + Memory MCP + claude-mem stack.

Option 2: Bureau keeps its memory stack but exposes a query API that CoPaw's
ReMe can call, creating a bidirectional knowledge graph.

Option 3 (pragmatic): Shared Qdrant instance.  Both systems already support
Qdrant.  Use a shared instance with namespace separation.

**C. Security layer import (high value, low effort)**

Adopt CoPaw's Tool Guard patterns as a pre-execution hook in Bureau's MCP
tool calls.  Bureau already has a YAML-based configuration system; tool-guard
rules could live in `bureau.yaml` under a `security:` key.

**D. Heartbeat as Bureau scheduler (low value, already covered)**

Bureau already has scheduling via its Telegram bot and planned cron features.
CoPaw's Heartbeat is conceptually similar but targets non-dev tasks.  Low
integration value unless Bureau wants to support personal-assistant scheduling.

### Protocol considerations

- Both are Python-based; IPC can be Unix sockets, HTTP, or direct import
- CoPaw is Apache 2.0; Bureau can freely incorporate code
- CoPaw depends on AgentScope; importing CoPaw means importing AgentScope
  (heavyweight dependency)
- Alternative: extract just the channel adapters and security scanner as
  standalone modules without the full AgentScope dependency

---

## 10. Fit Assessment

| Dimension | Fit | Rationale |
|---|---|---|
| **Channel expansion** | **Strong** | CoPaw provides 5+ channels Bureau lacks, especially iMessage and Asia platforms |
| **Security model** | **Strong** | Tool Guard + File Access Guard + Skill Scanner are all directly applicable to Bureau |
| **Memory unification** | **Moderate** | ReMe is cleaner than Bureau's stack, but migration has cost and Bureau's needs are dev-specific |
| **Personal assistant features** | **Moderate** | Useful for Bureau's concierge layer but orthogonal to its core dev orchestration mission |
| **SWE capabilities** | **Weak** | CoPaw has zero dev-specific features; no value for Bureau's core mission |
| **Proactive autonomy** | **Moderate** | Heartbeat is useful pattern but Bureau's needs differ (code monitoring vs personal tasks) |
| **Local model support** | **Moderate** | llama.cpp + MLX integration is mature; Bureau could use for cost-sensitive background tasks |
| **Dependency weight** | **Weak** | Full CoPaw import brings AgentScope; selective extraction preferred |
| **Community/ecosystem** | **Moderate** | Active project (Alibaba-backed) but Asia-centric community; English docs improving |
| **Architecture alignment** | **Strong** | Both use adapter patterns for channels; both are Python; both support Qdrant |

### Overall: **Moderate-Strong fit as a complementary front-end layer**

CoPaw is not a replacement for any Bureau component.  It is a potential
**front door** that gives Bureau access to consumer messaging channels and
a mature security model, while Bureau provides the dev-backend capabilities
that CoPaw completely lacks.

---

## 11. Risks & Tradeoffs

### Risks

1. **Dependency weight.**  AgentScope is a large framework.  Importing CoPaw
   means adopting or managing that dependency.  Mitigation: extract channel
   adapters and security modules as standalone code.

2. **Maintenance burden.**  CoPaw is actively evolving (0.x releases).  API
   stability is not guaranteed.  Tight coupling risks breakage on upstream
   updates.

3. **Asia-platform channel complexity.**  DingTalk, Feishu, and QQ have
   complex API requirements, rate limits, and approval processes.  Enabling
   these channels is not just a code problem; it requires platform-specific
   developer accounts and compliance.

4. **macOS lock-in for iMessage.**  The iMessage channel requires macOS as
   the host OS.  This conflicts with Bureau's current Linux/server deployment
   model.  A hybrid setup (macOS CoPaw + Linux Bureau) adds operational
   complexity.

5. **Memory model mismatch.**  ReMe is designed for personal assistant memory
   (preferences, conversation history, knowledge base).  Bureau's memory needs
   are dev-centric (code context, session state, dossiers, MCP tool results).
   The overlap is smaller than it appears.

6. **Security scanner false positives.**  CoPaw's skill scanner uses regex
   patterns (including Chinese-language patterns).  Applying this to Bureau's
   MCP tools or skills may produce false positives that require tuning.

### Tradeoffs

| Choice | Gain | Cost |
|---|---|---|
| Full CoPaw integration | 6+ channels, security model, ReMe memory | AgentScope dependency, maintenance burden, macOS requirement for iMessage |
| Selective extraction (adapters + security) | Channels + security without framework lock-in | Manual maintenance of extracted code; divergence from upstream |
| Shared Qdrant only | Simple memory bridge, no code dependency | Limited integration depth; no channel or security benefits |
| CoPaw as separate service (IPC bridge) | Full separation of concerns, both systems evolve independently | Network hop latency, deployment complexity, two systems to maintain |

### Recommended path

**Selective extraction** (channel adapters + security scanner) with a
**shared Qdrant instance** for memory bridging.  This captures the two
highest-value integration points (channels and security) without the
dependency weight of full AgentScope adoption.  The IPC bridge approach
is a viable alternative if CoPaw is already deployed as a personal
assistant and Bureau is added alongside it.
