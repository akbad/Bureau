# Bureau Integration Analysis: Synthesis & Recommendations

**Date:** 2026-04-03
**Scope:** 7 platforms evaluated for integration with Bureau

---

## Executive Summary

Bureau occupies a unique position in the agent landscape: it is the only framework that provides **cross-CLI orchestration** (Claude Code, Gemini CLI, Codex, OpenCode) with **66 specialized agent roles**, **structured workflow skills** (Assess Mode, Micro Mode), and a **cohesive MCP tool ecosystem** (15+ servers). No competitor attempts this. However, Bureau has three critical gaps: **channel breadth** (Telegram only), a **fragmented memory stack** (Qdrant + Memory MCP + claude-mem with no unified retrieval), and **no autonomous learning loop** (agents start fresh every session).

Seven platforms were evaluated for integration fit. The analysis reveals a clear hierarchy: **Hermes Agent** is the strongest overall integration candidate due to its complementary memory architecture, autonomous learning loop, and developer-first philosophy. **Letta/LettaBot** offers the most sophisticated memory system but less channel breadth. **OpenHands** is the best sandboxed execution backend. **OpenClaw** and **OpenFang** provide maximum channel coverage but with higher risk and lower architectural fit. **CoPaw** is the best choice if iMessage is critical. **Memoh** is the best isolation layer for risky operations.

The recommended integration stack is **Hermes Agent (primary) + OpenHands (execution sandbox)** — Hermes provides channels, learning, and user modeling while OpenHands provides the isolated execution environment Bureau's coding agents need for safe, verifiable work.

---

## Ranked Recommendations

### #1: Hermes Agent

**Verdict:** The closest philosophy match and the most complementary capability set.

- **Best for:** Closing Bureau's three biggest gaps simultaneously — channels (6), learning loop (skill-from-experience + user model), and cross-session recall (FTS5)
- **Biggest risk:** Pre-1.0 maturity (v0.6.0); two-system maintenance
- **Integration complexity:** Medium
- **Report:** [hermes-agent.md](hermes-agent.md)

### #2: OpenHands

**Verdict:** The best sandboxed execution backend for Bureau's coding workflows.

- **Best for:** Isolated, verifiable code execution — Assess Mode findings tested in sandbox, Micro Mode edits verified after each step, untrusted code contained
- **Biggest risk:** Docker dependency; resource overhead per sandbox
- **Integration complexity:** Medium
- **Report:** [openhands.md](openhands.md)

### #3: Letta / LettaBot

**Verdict:** The most sophisticated memory architecture, but heavier integration.

- **Best for:** Replacing Bureau's fragmented memory stack with a unified, self-editing memory system (core/archival/recall). LettaBot adds 5 channels with shared memory
- **Biggest risk:** V1 API churn (heartbeats deprecated); PostgreSQL dependency; single-agent bottleneck for multi-role workflows
- **Integration complexity:** High
- **Report:** [letta-lettabot.md](letta-lettabot.md)

### #4: CoPaw

**Verdict:** The best choice if iMessage and macOS-native operation matter.

- **Best for:** Native iMessage without disabling SIP; strongest built-in security guardrails (tool guard, file guard, skill scanning for prompt injection)
- **Biggest risk:** Smaller ecosystem (14.3k stars vs Hermes's 8.7k); Asia-platform-heavy channel mix
- **Integration complexity:** Medium
- **Report:** [copaw.md](copaw.md)

### #5: OpenFang

**Verdict:** Maximum channels and security, but a Rust/Python language divide.

- **Best for:** 40 channel adapters (broadest coverage); 16-layer security model; autonomous Hands for scheduled operations
- **Biggest risk:** Rust codebase (no code sharing with Bureau's Python); pre-1.0 (v0.3.x); single-maintainer bus factor
- **Integration complexity:** Medium-High
- **Report:** [openfang.md](openfang.md)

### #6: Memoh

**Verdict:** Best isolation layer for risky/sandboxed secondary tasks.

- **Best for:** Per-bot container isolation (containerd); hybrid memory retrieval (dense + sparse + BM25); ACL-based access control
- **Biggest risk:** AGPLv3 license (copyleft); Go codebase; containerd is Linux-native (Bureau is macOS-focused)
- **Integration complexity:** High
- **Report:** [memoh.md](memoh.md)

### #7: OpenClaw

**Verdict:** Maximum feature surface but maximum risk. Best as channel-only proxy.

- **Best for:** 23+ channels, companion apps (macOS/iOS/Android), voice wake/talk mode, live canvas, 13k ClawHub skills
- **Biggest risk:** 9 CVEs in 4 days (March 2026) including a 9.9 CVSS privilege escalation; no memory architecture; largest attack surface
- **Integration complexity:** High
- **Report:** [openclaw.md](openclaw.md)

---

## Recommended Integration Stack

### Primary: Hermes Agent + OpenHands

```
User (Telegram/Discord/Slack/WhatsApp/Signal/Email)
    ↓
Hermes Agent Gateway
    ├── Channel I/O (6 platforms)
    ├── Learning loop (skill creation, user model)
    ├── Cross-session recall (FTS5)
    ├── Scheduling (cron-based)
    └── Non-coding tasks (handled directly)
    ↓ coding task detected
Bureau Concierge Pipeline
    ├── 6-stage classification
    ├── 66 agent roles
    ├── Assess Mode / Micro Mode
    └── MCP tool ecosystem
    ↓ execution needed
OpenHands Sandbox
    ├── Docker-isolated runtime
    ├── Event stream state
    ├── SWE-bench 77.6% agent
    └── Verified execution results
```

### Why this combination

| Gap | Hermes fills | OpenHands fills |
|---|---|---|
| Channel breadth | 6 channels via single gateway | N/A |
| Learning loop | Skill-from-experience, USER.md, Honcho | N/A |
| Cross-session recall | FTS5 session search | N/A |
| User model | USER.md + Honcho | N/A |
| Sandboxed execution | N/A | Docker isolation per task |
| Verified code review | N/A | Test execution proving Assess Mode findings |
| Memory unification | Shared Qdrant + FTS5 | Event log state |
| Proactive behaviors | Cron scheduler | N/A |
| Execution backends | 6 (local, Docker, SSH, Daytona, Singularity, Modal) | Docker + overlay mounts |

### What about the others?

- **Letta:** Consider as a *future* memory layer replacement if Bureau's Qdrant + Memory MCP + claude-mem fragmentation becomes untenable. Not needed immediately if Hermes's FTS5 + shared Qdrant solves the recall problem.
- **CoPaw:** Add *only* if iMessage is a hard requirement. Its security scanning patterns (tool guard, skill scanning) are worth adopting as concepts even without full integration.
- **OpenFang:** Consider if you outgrow Hermes's 6 channels and need 40. The Rust/Python divide makes it a heavier lift.
- **Memoh:** Consider for specific isolation needs (running untrusted MCP servers, sandboxing experimental agents). Not a primary integration.
- **OpenClaw:** Avoid as an integration target. Use it as a reference for UI/UX ideas (canvas, voice, companion apps) but the security track record and architectural overlap make it the riskiest option.

---

## Head-to-Head Comparison Matrix

| Dimension | Hermes | Letta | OpenHands | CoPaw | OpenFang | Memoh | OpenClaw |
|---|---|---|---|---|---|---|---|
| **Philosophy match** | Strong | Moderate | Strong | Moderate | Moderate | Moderate | Weak |
| **Channel breadth** | Strong (6) | Moderate (5) | Weak (API) | Moderate (7) | Strong (40) | Moderate (9) | Strong (23) |
| **Memory architecture** | Strong | Strong | Moderate | Moderate | Moderate | Strong | Weak |
| **Learning loop** | Strong | Moderate | Weak | Weak | Weak | Weak | Weak |
| **Security model** | Moderate | Moderate | Strong | Strong | Strong | Strong | Weak |
| **SWE/dev depth** | Moderate | Weak | Strong | Weak | Weak | Weak | Weak |
| **Practical assistant** | Strong | Moderate | Weak | Moderate | Strong | Moderate | Strong |
| **Integration complexity** | Medium | High | Medium | Medium | Med-High | High | High |
| **Maintenance burden** | Moderate | Moderate | Moderate | Moderate | Moderate | High | High |
| **Community/maturity** | Moderate | Strong | Strong | Moderate | Moderate | Low | Strong |

---

## Top 10 Feature Merge Ideas Across All Platforms

Curated from the brainstorm sections of all 7 reports. Selected for maximum differentiation — ideas that make Bureau + integration genuinely unprecedented.

### 1. Role-Scoped Evolving Memory (Hermes)
Each of Bureau's 66 roles gets its own MEMORY.md slice. The debugger accumulates codebase-specific failure patterns; the architect learns team preferences. 66 agents that each independently get better at their specific job.
> *From [hermes-agent.md](hermes-agent.md) §12.1*

### 2. Verified Code Review via Sandbox Execution (OpenHands)
Assess Mode proves its own findings by spinning up an OpenHands sandbox, running the test suite, and demonstrating that the flagged issue is real — not theoretical.
> *From [openhands.md](openhands.md) §12.1*

### 3. Self-Improving Skills via Feedback Loop (Hermes)
When a Bureau agent completes a task using a skill, Hermes evaluates the outcome. Successful runs reinforce; failed runs trigger skill revision proposals. Skills evolve per-project.
> *From [hermes-agent.md](hermes-agent.md) §12.3*

### 4. Step-Gated Editing with Sandboxed Verification (OpenHands)
Micro Mode's DAG gains a test-run gate after each step: the edit is applied in an OpenHands container, tests run, and only if green does the step commit to the real workspace.
> *From [openhands.md](openhands.md) §12.2*

### 5. Dossier Auto-Hydration via Cross-Session Recall (Hermes)
Replace manual fold/unfold with automatic context loading: when working on a module, FTS5 finds all prior sessions involving it and builds a live, queryable dossier.
> *From [hermes-agent.md](hermes-agent.md) §12.5*

### 6. Parallel Debugging Swarm (Memoh)
Spawn N Memoh containers, each running a different Bureau debugging strategy concurrently. Cross-reference findings across all containers to identify the root cause faster.
> *From [memoh.md](memoh.md) §12.6*

### 7. Code Review Pattern Crystallization (Letta)
Assess Mode findings accumulate in Letta's self-editing memory as a "review prior" — each successive review is faster and more targeted because the agent remembers what it found before.
> *From [letta-lettabot.md](letta-lettabot.md) §12.4*

### 8. CVE Watchdog Hand (OpenFang)
OpenFang's Collector Hand monitors dependency CVEs and breaking changes. When detected, Bureau's security-compliance agent auto-triages and drafts patches.
> *From [openfang.md](openfang.md) §12.2*

### 9. Container-Isolated MCP Server Vetting (Memoh)
Before promoting an untrusted MCP server to production, install it in a disposable Memoh container and behaviorally audit it — watching for data exfiltration, excessive permissions, or injection attempts.
> *From [memoh.md](memoh.md) §12.7*

### 10. iMessage-Driven Spec-Kit Workflow (CoPaw)
Async, mobile-native spec-driven development: agent proposes spec sections via iMessage, developer approves/edits via replies, specs build up conversationally while commuting.
> *From [copaw.md](copaw.md) §12.6*

---

## Tradeoff Summary

### Channel breadth vs security risk
- More channels = larger attack surface. OpenClaw's 23 channels came with 9 CVEs in 4 days
- Sweet spot: Hermes's 6 channels cover the most common platforms with manageable risk
- If 6 isn't enough, OpenFang's 40 channels come with a 16-layer security model — but a Rust/Python divide

### Memory unification vs fragmentation flexibility
- Bureau's 3-backend memory stack is fragmented but each backend serves a purpose
- Letta offers full unification (core/archival/recall) but requires adopting a new framework
- Hermes's approach (shared Qdrant + FTS5 recall) unifies the retrieval layer without replacing backends
- Recommendation: start with Hermes's approach; consider Letta if fragmentation remains painful

### Build vs integrate
- Bureau could build its own channels, learning loop, and sandbox — the architecture supports it (MessageEnvelope is channel-agnostic, pipeline is decoupled)
- Integration is faster but adds dependencies and coordination complexity
- Recommendation: integrate for channels and learning (Hermes); build if the integration doesn't fit after 2-3 months

### Single-system simplicity vs multi-system power
- One system is easier to maintain, debug, and reason about
- But no single system covers Bureau's full need: dev orchestration + channels + learning + sandbox
- The Hermes + OpenHands stack is the minimum viable multi-system architecture — 2 additions, not 7

---

## Next Steps

### Immediate (Week 1)

1. **Install Hermes Agent** on the M4 Pro Mac alongside Bureau
2. **Configure shared Qdrant** — point Hermes's external memory provider at Bureau's Qdrant instance
3. **Set up Hermes Telegram** — run both Bureau's concierge and Hermes's gateway on Telegram (different bot tokens) to compare UX
4. **Add Discord + Slack to Hermes** — validate multi-channel message flow

### Short-term (Weeks 2-3)

5. **Build Bureau→Hermes delegation** — modify Bureau's valet feature evaluator to route non-coding tasks to Hermes via RPC
6. **Build Hermes→Bureau delegation** — configure Hermes to invoke Bureau CLI agents for coding requests detected in Discord/Slack
7. **Set up OpenHands** — install Docker-based sandbox; test Bureau's Assess Mode with sandboxed verification
8. **Import USER.md** — start feeding Hermes's user model into Bureau's concierge pipeline

### Medium-term (Weeks 4-8)

9. **Role-scoped memory** — implement per-role MEMORY.md slices in Hermes's SQLite store
10. **Dossier auto-hydration** — replace manual fold/unfold with FTS5-driven context loading
11. **Sandboxed Micro Mode** — wire OpenHands containers into Micro Mode's step verification
12. **Adopt CoPaw security patterns** — implement prompt injection scanning and tool-guard rules in Bureau's concierge (concepts, not full CoPaw integration)

### Long-term (Months 3+)

13. **Self-improving skills** — wire Hermes's learning loop into Bureau's skill feedback
14. **Evaluate Letta migration** — if memory fragmentation persists, pilot Letta as unified memory layer
15. **Evaluate OpenFang** — if 6 channels aren't enough, pilot OpenFang's 40-adapter gateway

---

## Individual Reports

| Platform | Report | Lines | Key finding |
|---|---|---|---|
| Hermes Agent | [hermes-agent.md](hermes-agent.md) | 430+ | #1 overall — learning loop + channels + memory |
| Letta / LettaBot | [letta-lettabot.md](letta-lettabot.md) | 350+ | Best memory architecture; heavier integration |
| OpenClaw | [openclaw.md](openclaw.md) | 420+ | Most features; most risk (9 CVEs) |
| CoPaw | [copaw.md](copaw.md) | 620+ | Best iMessage + security guardrails |
| Memoh | [memoh.md](memoh.md) | 680+ | Best container isolation; AGPLv3 concern |
| OpenHands | [openhands.md](openhands.md) | 400+ | Best sandboxed execution; 77.6% SWE-bench |
| OpenFang | [openfang.md](openfang.md) | 550+ | 40 channels + 16 security layers; Rust divide |
