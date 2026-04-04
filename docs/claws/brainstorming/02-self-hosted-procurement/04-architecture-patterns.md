# Section 4: Best Architecture Patterns

## Context

No single product perfectly covers all requirements. The strongest realistic setup layers multiple components. Three architecture patterns emerged from the analysis; they differ primarily in which component owns the user-facing identity and which owns the engineering protocol.

---

## Pattern A: Hermes-led personal operator

```
┌─────────────────────────────────────────────────┐
│              Hermes Agent (daemon)               │
│                                                  │
│  Identity: MEMORY.md + USER.md + Skills          │
│  LLM:      Claude (via CC credential store)      │
│            + Ollama (fallback / local tasks)      │
│  Channels: Telegram · Discord · WhatsApp · Signal│
│  Memory:   SQLite + FTS5 + Markdown (local)      │
│  Sched:    Cron tick loop (background tasks)      │
│                                                  │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │  Claude Code CLI │  │   Codex CLI     │       │
│  │  (subprocess,    │  │   (subprocess,  │       │
│  │   local auth)    │  │    local auth)  │       │
│  └─────────────────┘  └─────────────────┘       │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │  Bureau (protocol layer)                 │    │
│  │  Role prompts · Skills (Assess/Micro)    │    │
│  │  MCP servers · Qdrant · Memory MCP       │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Roles

| Component | Role |
|---|---|
| **Hermes** | Always-on personal operator. Owns identity, memory, learning loop, scheduling, and all channel surfaces. |
| **Claude Code CLI** | Primary coding worker. Invoked by Hermes for SWE tasks via subprocess. Uses subscription auth. |
| **Codex CLI** | Secondary coding worker. Invoked for tasks where OpenAI models are stronger. Uses subscription auth. |
| **Bureau** | Engineering protocol layer. Provides role prompts, structured skills (Assess Mode, Micro Mode), MCP server mesh, and memory backends (Qdrant, Memory MCP) for deeper engineering governance. |
| **Ollama** | Fallback/local LLM for non-frontier tasks, or when subscription auth is unavailable. |

### Why this pattern

- **Hermes owns the coherent identity.** The learning loop, USER.md, and skill creation give it the strongest "personal operator" feel.
- **Claude Code's credential store** solves the "zero API keys + frontier models" problem elegantly — Hermes uses Claude models via the user's subscription.
- **Bureau provides what Hermes lacks:** structured engineering protocols, review gates, and a richer memory stack (Qdrant semantic search, Memory MCP entity graph).
- **Coding delegation preserves CLI value.** Claude Code and Codex do what they do best, invoked by Hermes when needed.

### Strengths

- Highest assistant-core coherence.
- Self-improving over time (skills + user model).
- Frontier-model reasoning without API keys.
- Clean separation: Hermes reasons/plans, CLIs execute, Bureau governs engineering.

### Weaknesses

- No iMessage (Hermes lacks this channel).
- Bureau integration is not built-in — requires manual wiring (Hermes calling Bureau's MCP servers, or Bureau's concierge delegating to Hermes).
- Two daemon processes (Hermes + Bureau concierge) could overlap on Telegram unless coordinated.
- Hermes's engineering protocol depth is weaker without Bureau layered in.

### When to choose

**When the user values: coherent personal operator identity, self-improvement, and elegant memory — and does not need iMessage.**

---

## Pattern B: OpenClaw gateway + Bureau governance

```
┌─────────────────────────────────────────────────┐
│              OpenClaw (daemon)                    │
│                                                  │
│  Identity: SOUL.md + MEMORY.md                   │
│  LLM:      Ollama (local) or bundled Pi          │
│  Channels: Telegram · Discord · WhatsApp ·       │
│            iMessage · Signal · 20+ more          │
│  Memory:   MEMORY.md + daily notes + SQLite      │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │claude-cli│ │codex-cli │ │gemini-cli│        │
│  │(backend) │ │(backend) │ │(backend) │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │  Bureau (governance + protocol layer)    │    │
│  │  Role prompts · Skills · MCP mesh        │    │
│  │  Qdrant · Memory MCP · Assess/Micro      │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Roles

| Component | Role |
|---|---|
| **OpenClaw** | Always-on gateway. Owns all channel surfaces, message routing, and session memory. Routes coding tasks to CLI backends. |
| **Claude Code / Codex / Gemini CLI** | Coding backends. First-class subprocess workers using their own local auth. |
| **Bureau** | Engineering governance. Provides role prompts, structured skills, MCP servers, and deeper memory for engineering work. |
| **Ollama** | Primary LLM for OpenClaw's own reasoning (non-coding tasks). |

### Why this pattern

- **OpenClaw wins on channel breadth**, especially iMessage.
- **CLI backend integration is the most mature** — three CLIs are first-class with plugin defaults.
- **Bureau fills the coherence and protocol gaps** that OpenClaw lacks as a gateway.
- **Multi-agent council** enables parallel Claude Code instances for large coding tasks.

### Strengths

- Maximum channel reach (iMessage is unique).
- Best CLI delegation architecture — most native, least fragile.
- Largest ecosystem for extensions and skills.
- Auto-start daemon on macOS.
- Multi-agent council with git worktree isolation.

### Weaknesses

- No self-improving learning loop — OpenClaw does not get better over time the way Hermes does.
- Gateway personality (SOUL.md) is configuration, not learned identity.
- Ollama or bundled Pi as the main reasoning LLM may produce noticeably weaker non-coding responses than frontier models.
- January 2026 ClawHub supply-chain attack history.
- Young project with departed founder — long-term governance uncertainty.
- Bureau integration requires custom wiring (OpenClaw calling Bureau MCP servers, or skill-level integration).

### When to choose

**When the user values: iMessage, maximum channel breadth, best CLI delegation, and a huge ecosystem — and accepts a gateway personality over a learning operator.**

---

## Pattern C: Bureau-native evolution

```
┌─────────────────────────────────────────────────┐
│         Bureau Concierge (enhanced daemon)        │
│                                                  │
│  Identity: Bureau config + enhanced memory        │
│  LLM:      Claude Code CLI (subprocess, sub auth)│
│  Channels: Telegram (existing)                    │
│            + new: Discord, WhatsApp, Signal       │
│  Memory:   Qdrant + Memory MCP + dossiers         │
│            + new: MEMORY.md, USER.md equivalents  │
│  SWE:      Bureau roles, Assess/Micro, MCP mesh  │
│                                                  │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │  Claude Code CLI │  │   Codex CLI     │       │
│  │  (existing       │  │   (existing     │       │
│  │   bridge)        │  │    bridge)      │       │
│  └─────────────────┘  └─────────────────┘       │
└─────────────────────────────────────────────────┘
```

### Roles

| Component | Role |
|---|---|
| **Bureau Concierge** | Enhanced to be the always-on personal operator. Already has Telegram bridge, Claude Code/Codex/Gemini CLI delegation, background runner, pipeline orchestrator, and session state. Would need: more channels, stronger memory layer, self-improving behavior. |
| **Claude Code / Codex CLI** | Already first-class workers via `cc_connect.py` subprocess model. |
| **Bureau's existing stack** | Qdrant, Memory MCP, dossiers, role prompts, skills — all already operational. |

### Why this pattern

- **Zero new dependencies.** Everything builds on what Bureau already has.
- **Maximum governance coherence.** No external platform to coordinate with.
- **Bureau's Telegram bridge already works** with Claude Code/Codex/Gemini as backends.
- **Memory stack is already stronger** than Hermes or OpenClaw for structured engineering knowledge (Qdrant + Memory MCP + dossiers).

### Strengths

- Total sovereignty — no external platform risk.
- Existing Telegram → CLI delegation already works.
- Strongest engineering protocol depth (Assess Mode, Micro Mode, role catalog).
- No new daemon processes to manage.
- Most consistent with Bureau's existing architecture philosophy.

### Weaknesses

- **Major development effort required.** Adding Discord, WhatsApp, Signal, iMessage adapters is substantial work.
- **No self-improving learning loop** exists in Bureau today — would need to be designed and built.
- **Concierge is early-stage** compared to Hermes/OpenClaw — fewer features, less battle-tested as an always-on assistant.
- **Only Telegram today.** The user wants phone access now, not after months of development.
- **Misses the ecosystem.** No community skills, no shared skill standards, no plugin ecosystem.

### When to choose

**When the user values: total sovereignty, zero external risk, and is willing to invest significant development time to build what Hermes/OpenClaw already offer — or when the user only needs Telegram and existing Bureau capabilities.**

---

## Pattern comparison

| Criterion | Pattern A (Hermes-led) | Pattern B (OpenClaw gateway) | Pattern C (Bureau-native) |
|---|---|---|---|
| Time to deploy | Days | Days | Weeks to months |
| Channel breadth | 7 channels | 25+ channels | 1 today (Telegram) |
| iMessage | No | **Yes** | No (without development) |
| Self-improving | **Yes** (core feature) | No | No (without development) |
| CLI delegation | Good | **Best** | Good (existing) |
| Frontier models (zero keys) | **Yes** (CC auth reuse) | Limited (Ollama/Pi for brain) | **Yes** (CC subprocess) |
| Engineering protocol depth | Moderate + Bureau | Moderate + Bureau | **Strongest** (native) |
| Operational complexity | Medium (2 daemons) | Medium (2 systems) | Low (1 system) |
| External risk | Nous Research dependency | Foundation governance risk | None |
| Assistant coherence | **Highest** | Moderate | Moderate |
| Development effort | Low | Low | **High** |
