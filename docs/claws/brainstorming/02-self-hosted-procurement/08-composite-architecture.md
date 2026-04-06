# Section 8: Composite Architecture — Detailed Design

> The procurement analysis converges on a layered composite rather than any single platform. This document elaborates on that composite: what each layer does, how they interact at runtime, where the seams are, and what breaks.

## The layers

```
┌──────────────────────────────────────────────────────────────────┐
│                    Layer 1: Personal Operator                    │
│                       Hermes Agent (daemon)                      │
│                                                                  │
│  Identity    MEMORY.md · USER.md · skills (self-improving)       │
│  LLM         Claude (CC credential store) + Ollama (fallback)    │
│  Channels    Telegram · Discord · WhatsApp · Signal · Slack      │
│  Memory      SQLite + FTS5 + Markdown (all in ~/.hermes/)        │
│  Scheduling  Cron tick loop (background tasks, briefings)        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               Layer 2: Coding Workers                      │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                 │  │
│  │  │  Claude Code CLI │  │   Codex CLI     │                 │  │
│  │  │  (subprocess,    │  │  (subprocess,   │                 │  │
│  │  │   sub auth)      │  │   sub auth)     │                 │  │
│  │  └─────────────────┘  └─────────────────┘                 │  │
│  │                                                            │  │
│  │  Bureau's CLAUDE.md auto-injects into every CC session     │  │
│  │  (file-based — no special wiring needed)                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │         Layer 3: Engineering Governance (Bureau)            │  │
│  │                                                            │  │
│  │  Role catalog (66 roles) · Assess Mode · Micro Mode       │  │
│  │  MCP mesh: Qdrant · Memory MCP · Sourcegraph              │  │
│  │  Dossiers · Skills · Protocol layer                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │            Layer 4: Fallback LLM (Ollama)                  │  │
│  │                                                            │  │
│  │  Local inference on Mac (llama 3.3, Qwen, etc.)            │  │
│  │  For: offline tasks, non-frontier work, sub auth outage    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│        Layer 5: iMessage Gateway (OpenClaw) — OPTIONAL           │
│                                                                  │
│  Channels    iMessage (BlueBubbles) + any overflow channels      │
│  LLM         Ollama / bundled Pi (NOT Hermes's Claude brain)     │
│  CLI backs   claude-cli · codex-cli · gemini-cli (subprocess)    │
│  Memory      SOUL.md · MEMORY.md · daily notes · SQLite          │
│                                                                  │
│  IMPORTANT: parallel brain, not a channel adapter for Hermes     │
└──────────────────────────────────────────────────────────────────┘
```

## Runtime workflows

### Workflow 1: Phone message → non-coding response

The most common interaction: the user sends a message from their phone and gets a direct answer.

1. User sends a Telegram message from iPhone
2. Hermes gateway receives it via long-polling (no webhook, no port forwarding needed behind NAT)
3. Hermes loads context: `MEMORY.md` + `USER.md` + relevant skills + FTS5 session search results
4. Hermes reasons using Claude (via Claude Code credential store) or Ollama (if offline/fallback)
5. Hermes responds via Telegram

- **No other layer is involved.** Bureau, Claude Code CLI, Codex, and OpenClaw are untouched.
- **Latency**: dominated by LLM inference time. With Claude via credential store: comparable to Claude Code response times. With Ollama: limited by local hardware.

### Workflow 2: Phone message → coding task

The user requests a code change from their phone.

1. User sends "fix the failing test in bureau-concierge" via Telegram
2. Hermes receives, reasons about the request, identifies it as a coding task
3. Hermes invokes Claude Code CLI as a subprocess: `claude -p "fix the failing test in bureau-concierge" --json`
4. Claude Code starts, loads `CLAUDE.md` from the target repo → **Bureau's protocol layer is automatically engaged**

    - Role prompts, skills (Assess Mode, Micro Mode), and MCP server declarations are injected
    - Bureau's MCP mesh becomes available: Qdrant for semantic code search, Memory MCP for entity knowledge, Sourcegraph for cross-repo search

5. Claude Code executes the task (reads files, edits code, runs tests)
6. Claude Code returns structured output to Hermes
7. Hermes synthesizes the result, responds via Telegram
8. *If the task was novel/hard*: Hermes may create a new skill document from the experience (learning loop)

- **Key insight**: Bureau's `CLAUDE.md` injection is the critical integration seam, and it's *free* because it's file-based. Hermes doesn't need to "know about" Bureau; it just needs to invoke Claude Code in a directory that has a `CLAUDE.md`.

### Workflow 3: Background scheduled task

Hermes runs a recurring task without user initiation.

1. Hermes cron tick fires (e.g., 8:00 AM daily briefing)
2. Hermes executes the scheduled skill (may involve web search, file reads, API checks)
3. If the task requires coding: delegates to Claude Code CLI (same as Workflow 2)
4. Result is stored in Hermes's memory and/or sent to user via their preferred channel

- **Bureau is involved only if the cron task delegates to Claude Code in a Bureau-governed repo.**
- **Ollama may be used for lower-stakes scheduled tasks** (summaries, checks) to avoid consuming subscription quota.

### Workflow 4: iMessage interaction (OpenClaw deployed)

A *parallel path*, architecturally separate from Workflows 1–3.

1. User sends an iMessage from iPhone
2. BlueBubbles (running on the same Mac) receives it and forwards to OpenClaw
3. OpenClaw processes the message using its own reasoning brain (Ollama or bundled Pi)
4. If coding task: OpenClaw delegates to its own Claude Code/Codex CLI backend (subprocess, local auth)
5. Response flows back via iMessage

- **Hermes is not involved.** OpenClaw is a separate daemon with its own identity (`SOUL.md`), memory (`MEMORY.md`), and reasoning engine.
- **The user gets a different-quality brain on iMessage** (Ollama/Pi) than on Telegram (Claude via credential store). This is the primary coherence cost of the composite architecture.

### Workflow 5: Engineering-governed coding session (direct, no Hermes)

The user sits down at the Mac and works with Claude Code directly.

1. User opens a terminal, runs `claude` in a Bureau-governed repo
2. Claude Code loads `CLAUDE.md` → Bureau's full protocol stack is active
3. Bureau's MCP mesh is available (Qdrant, Memory MCP, etc.)
4. User works with Claude Code directly using Assess Mode, Micro Mode, role prompts, dossiers, etc.

- **Hermes and OpenClaw are irrelevant.** This is the existing Bureau workflow, unchanged.
- **This workflow is the highest-governance-depth path** — richer than anything routed through Hermes or OpenClaw, because the user has direct interactive control over Claude Code.

### Workflow 6: Cross-session memory recall

Information persists across sessions, but through *separate, unsynchronized channels*.

```
Hermes memory (identity + experiences)        Bureau memory (engineering knowledge)
┌─────────────────────────────────┐           ┌───────────────────────────────────┐
│ MEMORY.md    environment facts  │           │ Qdrant       semantic vectors     │
│ USER.md      user preferences   │           │ Memory MCP   entity graph         │
│ Skills       learned procedures │           │ Dossiers     session snapshots    │
│ SQLite+FTS5  session archive    │           │ claude-mem   observation timeline │
│ Honcho       user modeling      │           │ CLAUDE.md    protocol injection   │
└─────────────────────────────────┘           └───────────────────────────────────┘
        ↕ NOT synchronized ↕
```

- **Hermes knows what the user asked via Telegram last week** (FTS5 session search).
- **Bureau knows what code was changed and why** (Qdrant, dossiers, claude-mem).
- **Neither knows what the other knows**, unless the user explicitly bridges the gap (e.g., telling Hermes about a dossier, or telling Claude Code about a Hermes skill).

## Advantages

### 1. Frontier-model reasoning without API keys

- Hermes reuses Claude Code's credential store for Anthropic's best models.
- This is the **singular capability that no other single-platform setup achieves**: zero API keys *and* frontier-quality reasoning.
- The alternative (Ollama/Pi as the reasoning brain) produces noticeably weaker output for non-coding tasks like research synthesis, nuanced planning, and life management.

### 2. Self-improving intelligence

- Hermes creates reusable skill documents when it solves hard problems.
- `USER.md` deepens as Hermes learns the operator's communication style, preferences, and patterns.
- This is **compounding intelligence**, not just durable storage; the system after 6 months is meaningfully better than the system on day one.
- Neither OpenClaw nor Bureau offer this behavior natively.

### 3. Clean separation of concerns

- Each layer does exactly what it's best at, and *only* that:

    | Layer | Responsibility | Does NOT do |
    | :--- | :--- | :--- |
    | Hermes | Identity, memory, reasoning, channels, learning | Coding execution, engineering protocols |
    | Claude Code / Codex | Coding execution | Identity, scheduling, messaging |
    | Bureau | Engineering governance, structured review, MCP mesh | User-facing messaging, personal memory |
    | Ollama | Cheap local inference | Anything requiring frontier quality |
    | OpenClaw | iMessage gateway | Personal operator identity |

- This means each component can be **upgraded, replaced, or removed independently** without cascading effects on the others.

### 4. Bureau integration is automatic for coding tasks

- Bureau's `CLAUDE.md` is file-based: any Claude Code subprocess that runs in a Bureau-governed repo automatically picks up the full protocol stack.
- **No special Hermes→Bureau wiring is needed for this specific integration path.**
- Role prompts, skills, MCP server declarations all inject transparently.
- This is the single most elegant integration seam in the entire architecture.

### 5. Graceful degradation

- If Hermes crashes: Bureau's existing Telegram bridge can serve as a degraded fallback for coding tasks.
- If subscription auth is down: Ollama handles non-frontier tasks until auth recovers.
- If OpenClaw is down: only iMessage is affected; all other channels remain operational via Hermes.
- If Ollama is down: Hermes falls back entirely to Claude via credential store (higher quality, higher cost).
- No single failure takes the entire system offline.

### 6. Zero vendor lock-in on any single component

- Hermes can be replaced by a future better personal operator without touching Bureau or Claude Code.
- Ollama can be swapped for llama.cpp, MLX, or any other local inference runtime.
- Bureau's protocol layer evolves independently of the messaging surface.
- This is a genuine modularity advantage, not a theoretical one: the components are connected by subprocess calls and file-system conventions, not tight API coupling.

### 7. Engineering governance depth exceeds any single platform

- Bureau provides 66 roles, Assess Mode, Micro Mode, dossier system, MCP mesh (Qdrant, Memory MCP, Sourcegraph), and structured review protocols.
- Neither Hermes nor OpenClaw offers anything comparable for engineering work.
- The composite gets the best engineering governance (Bureau) *and* the best personal operator (Hermes) simultaneously, rather than compromising on either.

## Disadvantages

### 1. Memory fragmentation (the most serious architectural problem)

- Hermes and Bureau maintain **completely separate memory systems** with no synchronization.
- Information learned during a Hermes conversation (via Telegram) does not flow into Bureau's knowledge base.
- Information stored in Bureau's Qdrant or dossiers is invisible to Hermes's reasoning.
- **Concrete consequence**: the user tells Hermes via Telegram "we decided to use Restate instead of Temporal." Hermes stores this in `MEMORY.md`. The next day, the user opens Claude Code directly — Bureau has no record of this decision unless the user repeats it.
- **Mitigation options**:

    - Manual bridging (the user tells both systems)
    - A sync script that mirrors Hermes `MEMORY.md` entries into Bureau's Memory MCP
    - Making Hermes an MCP client that reads/writes Bureau's memory servers

- None of these mitigations exist today. This is the highest-priority integration gap.

### 2. Identity incoherence across iMessage

- If OpenClaw is deployed for iMessage, the user interacts with **two different agents**:

    - Telegram/Discord/WhatsApp → Hermes (Claude-quality brain, `USER.md` identity, self-improving)
    - iMessage → OpenClaw (Ollama/Pi brain, `SOUL.md` identity, non-learning)

- The "coherent personal operator" promise **fractures at the iMessage boundary**.
- The user may notice: the iMessage assistant gives worse answers, doesn't remember things the Telegram assistant knows, and doesn't improve over time.
- **Mitigation**: deploy OpenClaw as a thin relay that forwards messages to Hermes rather than reasoning independently. This is not currently supported by either platform and would require custom development.

### 3. Concurrent subscription consumption

- If Hermes uses Claude Code's credential store for its own reasoning **and** delegates coding to Claude Code CLI, that is **two concurrent consumers of the same Anthropic subscription**.
- Anthropic's per-subscription concurrency limits for credential store auth are undocumented.
- **Concrete risk**: Hermes is mid-reasoning on a Telegram message, simultaneously delegates a coding task to Claude Code CLI. Both hit the Claude API through the same credential store. One or both may be rate-limited or rejected.
- **Mitigation**: Hermes could queue coding delegations to avoid concurrent credential store use. Or Hermes could use Ollama for its own reasoning and reserve credential store exclusively for Claude Code CLI. The latter sacrifices the "frontier reasoning" advantage.

### 4. Operational complexity: multiple daemon processes

- Minimum: 2 daemons (Hermes + Ollama). Practical: 3 (add Bureau concierge). Maximum: 4 (add OpenClaw).
- Each daemon has its own:

    - Configuration surface (config files, environment variables, auth tokens)
    - Logging output
    - Update/upgrade cycle
    - Crash/restart behavior
    - macOS sleep/wake reconnection characteristics

- **Concrete cost**: a breaking change in Hermes v0.5.0 that alters the Claude Code credential store format requires testing against Bureau's `CLAUDE.md` injection and verifying that Ollama fallback still works. Every update to any component must be tested against the seams.

### 5. Telegram channel conflict

- Both Hermes and Bureau's concierge can serve Telegram.
- If both run, they'd need **separate Telegram bots** (separate BotFather tokens) or one must be disabled entirely.
- Two separate bots means the user must decide which bot to message for which task, which defeats the "single coherent operator" goal.
- **Mitigation**: disable Bureau's Telegram bridge entirely and let Hermes own the channel. Bureau is then engaged only through Claude Code subprocess delegation, not through messaging.

### 6. No unified conversation history

- A conversation started on Telegram (Hermes) has its context in Hermes's SQLite+FTS5 archive.
- A conversation continued on iMessage (OpenClaw) has its context in OpenClaw's SQLite.
- A coding session done directly in Claude Code has its context in Bureau's dossier system and claude-mem.
- **Cross-channel continuity does not exist.** Searching "what did I ask about Restate?" requires searching three separate datastores.
- This is a direct consequence of disadvantage #1 (memory fragmentation), applied to conversation history specifically.

### 7. OpenClaw's reasoning quality ceiling

- OpenClaw's own brain runs on Ollama or the bundled Pi binary.
- For non-coding tasks routed through OpenClaw (iMessage), the reasoning quality is **significantly weaker** than Hermes's Claude-backed reasoning.
- This creates a first-class/second-class channel split that the user will feel in practice.
- **Question that remains unvalidated**: can OpenClaw route its *own* general reasoning through a Claude Code CLI backend (not just coding delegation)? If yes, this disadvantage disappears. The docs are unclear on this point (see Section 6, OpenClaw unknown #1).

### 8. Debugging across layer boundaries

- When a phone-initiated coding task produces a wrong result, the failure could be in:

    1. Hermes's task interpretation (reasoning layer)
    2. Hermes's delegation prompt to Claude Code (handoff layer)
    3. Claude Code's execution (coding layer)
    4. Bureau's protocol injection conflicting with Hermes's prompt (governance layer)
    5. Ollama producing a low-quality intermediate result (fallback layer)

- **No unified logging or tracing** exists across these layers. Each component logs independently in its own format and location.
- **Mitigation**: a structured error-reporting convention (e.g., Hermes attaches a trace ID to delegation calls, Claude Code surfaces it in output). This does not exist today.

### 9. Sleep/wake fragility (Mac-specific)

- Multiple daemons on a Mac that sleeps and wakes must each independently handle:

    - Telegram long-polling reconnection
    - WhatsApp Baileys WebSocket reconnection (known to disconnect periodically)
    - Signal signal-cli Java process restart
    - BlueBubbles iMessage adapter reconnection
    - Ollama model unloading/reloading

- **Compounding probability**: if each channel has a 95% chance of surviving a sleep/wake cycle cleanly, four channels give a ~81% chance that *all* reconnect successfully. Over daily sleep/wake cycles, failures accumulate.
- **Mitigation**: configure `pmset` or `caffeinate` to prevent Mac sleep entirely (feasible for a plugged-in home server Mac). Alternatively, add a watchdog that monitors and restarts failed channel connections.

## Summary assessment

| Dimension | Verdict |
| :--- | :--- |
| **Is the composite better than any single platform?** | **Yes**, decisively. No single platform passes all hard constraints *and* provides frontier reasoning, self-improvement, engineering governance, and multi-channel phone access. |
| **Is it operationally simple?** | **No.** 2–4 daemons, 8+ configuration surfaces, unsynchronized memory systems, and cross-layer debugging complexity. This is an enthusiast-grade setup, not an appliance. |
| **What is the single biggest risk?** | Memory fragmentation. Two (or three) separate knowledge stores that don't talk to each other undermine the "one coherent operator" promise more than any other factor. |
| **What is the single most elegant property?** | Bureau's `CLAUDE.md` auto-injection into Claude Code subprocesses. The governance layer integrates with the coding layer for free, via the file system, with zero custom wiring. |
| **What should be built first if this architecture is adopted?** | A memory bridge: Hermes → Bureau memory sync, so that learnings from phone conversations are available during direct coding sessions and vice versa. Without this, the operator's knowledge is balkanized across channels. |
