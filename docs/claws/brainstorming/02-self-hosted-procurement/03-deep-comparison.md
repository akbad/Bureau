# Section 3: Deep Comparison of Survivors

---

## Hermes Agent

**Source:** [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) · [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/)

### What it is

An open-source, self-hosted personal AI agent by Nous Research. Tagline: "The agent that grows with you." Built around a closed learning loop — it creates skills from experience, improves them during use, searches its own past conversations, and builds a deepening model of who you are across sessions. Single gateway daemon with multi-channel messaging.

### What it offers

- 40+ built-in tools: web search, terminal, filesystem, browser automation, vision, image gen, TTS, code execution, subagent delegation, memory, task planning, cron scheduling, multi-model reasoning.
- Skill creation from experience: when Hermes solves a hard problem, it writes a reusable skill document. Skills are searchable, shareable, and compatible with the agentskills.io open standard.
- Background scheduling via cron tick loop.
- MCP server mode: exposes conversations/sessions to any MCP-compatible client.

### Fully self-hostable with zero API keys?

**Yes.**

- **LLM inference:** Ollama supported natively. Docs explicitly state "Skip API key (Ollama doesn't need one)."
- **Claude Code auth reuse:** "Hermes prefers Claude Code's own credential store over copying the token into ~/.hermes/.env." This means Hermes can use Anthropic's frontier Claude models via the user's existing Claude Code subscription — no separate API key needed.
- **Codex auth reuse:** Device code auth (browser-based OAuth). Hermes stores resulting credentials in its own auth store.
- **Copilot ACP:** Can spawn local Copilot CLI as a subprocess.
- **No hosted dependency:** Honcho is explicitly optional. Full operation with just skills + FTS5 (fully local, no external services).

### How well it uses local Claude Code and Codex CLI

**First-class, with a nuance.**

- Hermes can use Claude Code's credential store as an LLM provider (for reasoning).
- Hermes can delegate coding tasks to Claude Code and Codex CLI.
- [Issue #477](https://github.com/NousResearch/hermes-agent/issues/477) confirms both Claude Code and Codex exist as delegation targets; the issue proposes adding OpenHands as a model-agnostic alternative.
- The delegation model is: Hermes reasons → identifies a coding task → delegates to the appropriate CLI → collects results.
- **Nuance:** The delegation is functional but the boundary between "Hermes using Claude Code's credentials as its own provider" and "Hermes delegating a task to Claude Code CLI as a subprocess" is architecturally distinct. The former gives Hermes the model; the latter gives Hermes a worker. Both are supported.

### Remote phone ergonomics

**Strong.**

| Channel | Status | iPhone ergonomics |
|---|---|---|
| Telegram | Built-in (gateway) | Excellent — native iOS app, notifications, media |
| Discord | Built-in | Good — native iOS app |
| Slack | Built-in | Good — native iOS app |
| WhatsApp | Built-in | Excellent — most natural phone channel |
| Signal | Built-in | Excellent — strong privacy |
| Email | Built-in | Good — async, universal |
| CLI | Built-in | N/A (local only) |

All channels run through a single gateway daemon. No per-channel server needed.

### SWE depth

**Good, not exceptional.**

Hermes has terminal access, file system tools, code execution, and can delegate to Claude Code/Codex for deep coding work. It has 60+ expert knowledge skills including GitHub, Docker, Kubernetes, security audit, etc.

However, Hermes is not an SWE-specialized platform. It does not have:
- Docker-sandboxed execution environments (like OpenHands)
- Branch-aware workflow management (like Bureau)
- Structured review protocols (like Bureau's Assess Mode / Micro Mode)

The SWE story is: Hermes as the planner/router, Claude Code/Codex as the coding executors, Bureau as the quality/protocol layer. This combination is stronger than Hermes alone.

### Research/planning/life management depth

**Strong — this is Hermes's sweet spot.**

- Persistent user model (USER.md) that deepens over time.
- Skill creation from experience — accumulated know-how persists.
- Cron-based scheduling for recurring tasks, briefings, checks.
- Web search, browser automation for research.
- Background task execution.
- Cross-session memory recall via FTS5 search.

Life management is viable: reminders, routine planning, preference persistence, adaptive behavior. Research is viable: web search + browser + persistent notes. Planning is viable: task decomposition + memory + scheduling.

### Mac-native assistant ergonomics

**Limited.**

Hermes does not have:
- Apple Notes / Reminders integration
- iMessage support (no adapter documented)
- macOS notification center integration
- macOS Services integration
- Spotlight / Siri Shortcuts integration

It runs as a daemon process and interacts through messaging channels or CLI. Mac-native integration would require custom wiring.

### Memory model

**One of the strongest in the field under fully-local constraints.**

Five layers, all stored in `~/.hermes/`:

| Layer | Storage | Purpose |
|---|---|---|
| MEMORY.md | Markdown file | Environment facts, conventions, lessons learned. Injected into every session. |
| USER.md | Markdown file | User preferences, communication style, personal facts. Injected into every session. |
| Skills | Markdown files | Reusable procedures created from experience. Searchable, shareable. |
| Session archive | SQLite + FTS5 | Every past session, full-text indexed. Agent can search and retrieve relevant context. |
| Honcho (optional) | External service | User modeling layer. **Fully optional.** Can self-host locally via Docker (PostgreSQL backend, no external API key for basic operation). |

All memory is:
- Plain-text and human-readable
- Editable by the user
- Portable (single folder)
- No external database server required (SQLite)
- No vector DB required for base operation

The self-improving loop: Hermes writes skill documents when it solves hard problems. These accumulate over time. The USER.md deepens as Hermes learns the operator's preferences. This is genuine compounding intelligence, not just storage.

### Assistant-core coherence

**High — the strongest of all platforms reviewed.**

Hermes is explicitly designed as a single coherent personal operator, not a gateway/router/plugin bus. The learning loop, persistent identity (MEMORY.md + USER.md), skill creation, and unified gateway create a system that behaves like one assistant getting better over time.

This contrasts with OpenClaw, which is architecturally a gateway/router that connects channels to an LLM — capable and broad, but not inherently self-improving.

### Security / trust model

**Explicitly designed for single-operator environments.**

- **Approval modes:** manual, smart, or off. Fail-closed (denied if no response within timeout).
- **Command scanning:** Tirith integration for content-level threat detection (homograph URLs, pipe-to-interpreter patterns).
- **Code sandbox:** Python/Node scripts run in isolated subprocesses via Unix domain sockets. Sandboxed code cannot access delegation or further code-execution tools. 300-second timeout, 50-tool-call limit.
- **Container support:** Docker, Singularity, Modal, Daytona backends. When containerized, dangerous command checks are skipped (container is the boundary).
- **Zero telemetry:** Explicitly claimed, simpler to audit for single-operator use.
- **Patch cadence:** Active — v0.4.0 (March 23, 2026), v0.3.0 before that. Rapid iteration.

**Known risks:**
- The skill ecosystem (agentskills.io) is shared/community — same supply-chain risk as any package registry. Must vet skills manually.
- File-system access is effectively full user-level access.
- Messaging channel tokens (Telegram bot token, etc.) are stored in config files.

### Main strengths

1. Self-improving learning loop (skill creation from experience) — architecturally unique.
2. Claude Code credential reuse — frontier models with zero API keys.
3. Fully local memory with elegant five-layer design.
4. Single-operator security posture with zero telemetry.
5. Coherent personal-operator identity — not just a tool router.
6. Active development by a credible organization (Nous Research).

### Main weaknesses

1. No iMessage support (OpenClaw has this).
2. SWE depth is delegated, not native — depends on Claude Code/Codex quality.
3. Mac-native integration is absent (no Apple Notes, Reminders, Shortcuts).
4. Younger than some alternatives (though backed by established Nous Research).
5. Skill ecosystem supply-chain risk (shared with all plugin registries).
6. Documentation quality varies — some features better documented than others.

### Verdict

**Best overall match for the stated constraints.** Hermes is the only platform that combines zero-API-key operation, Claude Code subscription auth reuse, self-improving memory, multi-channel phone access, and coherent personal-operator identity in a single self-hosted daemon. Its weaknesses (no iMessage, no Mac-native integration) are real but addressable.

---

## OpenClaw

**Source:** [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw) · [docs.openclaw.ai](https://docs.openclaw.ai/)

### What it is

An open-source, self-hosted personal AI assistant gateway. Originally "Clawdbot" (November 2025), renamed to OpenClaw (January 2026) after trademark issues. Created by Peter Steinberger (PSPDFKit founder), who subsequently joined OpenAI in February 2026. Now governed by an open-source foundation. 347K GitHub stars as of April 2026 — one of the fastest-growing open-source projects in history.

### What it offers

- Long-running Node.js gateway daemon connecting messaging channels to an LLM agent pipeline.
- 50+ integrations: chat platforms, AI models, productivity tools, music/audio, smart home, automation.
- Skills system: pluggable capability directories with SKILL.md metadata + code.
- SOUL.md: personality/identity configuration.
- AGENTS.md: workspace-level rules and SOPs.
- Multi-agent council: parallel agents on same codebase with git worktree isolation and consensus voting.
- Auto-start daemon on macOS via `openclaw onboard --install-daemon`.

### Fully self-hostable with zero API keys?

**Yes, with a minor workaround.**

- **LLM inference:** Ollama supported natively. Requires a dummy placeholder key (`OLLAMA_API_KEY=ollama-local`) because the auth system incorrectly demands a non-empty value even for local models. This is a known quirk (GitHub issues #3740, #22055, #28927), not a real API key.
- **Default mode:** "If you do nothing, OpenClaw uses the bundled Pi binary in RPC mode" — a local model that requires no key at all.
- **CLI backends:** Use local CLI auth directly. "No keys, no extra auth config needed beyond the CLI itself."

### How well it uses local Claude Code and Codex CLI

**First-class — the best CLI backend integration of any platform reviewed.**

- Three officially supported CLI backends with bundled plugin defaults:
  - `claude-cli`: invokes `claude` with JSON output
  - `codex-cli`: invokes `codex exec` with JSONL streaming
  - `google-gemini-cli`: invokes `gemini` with JSON formatting
- "No keys, no extra auth config needed beyond the CLI itself" — uses the CLI's own local authentication.
- The [coding-agent skill](https://github.com/openclaw/openclaw/blob/main/skills/coding-agent/SKILL.md) delegates to Claude Code/Codex in three modes: ask (plan+approval), delegate (auto-approve safe plans), autonomous (hands-off).
- [openclaw-claude-code plugin](https://github.com/Enderfga/openclaw-claude-code): turns Claude Code into a "programmable, headless coding engine" from within OpenClaw.
- [acpx](https://github.com/openclaw/acpx): headless CLI client for Agent Client Protocol (ACP), supporting Claude Code, Codex, and others.
- Multi-agent council: parallel Claude Code instances on the same codebase with git worktree isolation.

### Remote phone ergonomics

**Excellent — the broadest of any platform reviewed.**

| Channel | Method | iPhone ergonomics |
|---|---|---|
| Telegram | Bot API (grammY) | Excellent |
| Discord | Bot API + Gateway | Good |
| WhatsApp | Baileys (QR pairing) | Excellent |
| **iMessage** | **BlueBubbles** | **Excellent — native iOS, unique among platforms** |
| Signal | signal-cli | Excellent |
| Slack | Bot API | Good |
| IRC | Native | N/A |
| WebChat | WebSocket UI | Good (browser) |

Plus 15+ plugin-based channels: Feishu/Lark, LINE, Matrix, Mattermost, Teams, QQ, Twitch, WeChat, Zalo, etc.

**iMessage support is a significant differentiator.** No other reviewed platform offers it. This is achieved via BlueBubbles, which requires a Mac running as the iMessage gateway — exactly the user's setup.

### SWE depth

**Strong via delegation, not native.**

OpenClaw itself is a gateway, not an SWE agent. But its CLI delegation model makes SWE work viable:
- Delegates coding to Claude Code/Codex/Gemini CLI as background subprocesses.
- Multi-agent council for parallel coding with consensus voting.
- Git worktree isolation for concurrent coding tasks.
- Skills can spawn shell commands and manage file operations.

What it lacks natively:
- No Docker-sandboxed execution environments.
- No structured review/assessment protocols (Bureau provides these).
- No branch-aware workflow management beyond git worktree delegation.

### Research/planning/life management depth

**Moderate.**

- MEMORY.md for persistent facts and preferences.
- Daily notes (`memory/YYYY-MM-DD.md`) for running context.
- Web search, browser capabilities via skills.
- Cron/heartbeat events for background scheduling.
- Smart home integration (Home Assistant, etc.).

Weaker than Hermes on:
- No self-improving skill creation from experience.
- No deepening user model.
- Memory is storage, not learning.
- Less "personal operator" feel, more "capable gateway."

### Mac-native assistant ergonomics

**Better than Hermes in one critical area: iMessage.**

- **iMessage:** Supported via BlueBubbles — requires the Mac to be running (which it is in this use case). This enables natural phone interaction through the native Messages app.
- Auto-start daemon via `openclaw onboard --install-daemon`.
- No Apple Notes, Reminders, Shortcuts, or Notification Center integration.
- Filesystem access for local file operations.
- Terminal/shell execution.

### Memory model

**Solid but simpler than Hermes.**

| Component | Storage | Purpose |
|---|---|---|
| MEMORY.md | Markdown file | Long-term durable facts, preferences, decisions. Loaded every session. |
| Daily notes | `memory/YYYY-MM-DD.md` | Running context and observations. Today's + yesterday's auto-loaded. |
| Knowledge base | Markdown folder | User's reference documents. |
| Search index | SQLite (`~/.openclaw/memory/{agentId}.sqlite`) | Hybrid: vector search (70% cosine similarity) + BM25 keyword search (30%). |

All local, all plain-text Markdown, all human-editable. No external database required.

**Key design feature:** Before context-window compaction, OpenClaw runs a silent "memory flush" turn that reminds the agent to save important context. This prevents information loss during long sessions.

**What it lacks vs Hermes:**
- No skill creation from experience.
- No self-improving user model (USER.md equivalent).
- No FTS5 session archive for searching past conversations.
- Memory is durable storage, not a learning system.

### Assistant-core coherence

**Moderate — it's a gateway, not a personality.**

OpenClaw is architecturally a message router + tool executor + memory store. SOUL.md provides personality configuration, but the system does not learn or deepen over time. It feels like a very capable dispatcher, not a growing personal operator.

This is fine for users who want a Swiss Army knife. It is less satisfying for users who want "a coherent personal operator, not just a bag of plugins."

### Security / trust model

**Weaker than Hermes. Notable incident history.**

- **Trust boundary:** Filesystem access. If someone can edit workspace files, they are trusted.
- **Pairing model:** Devices must pair with the gateway. Pairing requires explicit approval. Commands on paired devices are not automatically exposed.
- **Inbound access control:** Critical — any user on Telegram/WhatsApp/Slack who finds the bot can message it. Must configure allow-lists immediately.
- **Skill sandboxing:** Skills that spawn subprocesses require `--dangerously-force-unsafe-install` flag. This is the only guardrail.
- **Security audit tool:** Built-in audit detects common footguns (gateway auth exposure, elevated permissions, open-channel tool exposure).

**Critical incident — January 2026 ClawHub malware:**
Hundreds of skills in the ClawHub registry were found to contain an **Atomic Stealer payload** that:
- Harvested API keys
- Injected malicious content into MEMORY.md and SOUL.md
- Created persistent "sticky" attacks across sessions (because memory is loaded at every session start)

CVE-2026-25253 was issued. Fix included in version 2026.2.25+.

**Assessment:** The security model is "trust the operator, audit the skills." For a single-user home deployment this is manageable, but the supply-chain attack history is a real concern. Never install skills from ClawHub without manual review.

### Main strengths

1. **iMessage support** — unique among all platforms.
2. **Broadest channel coverage** — 25+ messaging platforms.
3. **Best CLI backend integration** — Claude Code, Codex, Gemini are first-class subprocess backends.
4. **Largest community** — 347K stars, massive ecosystem, extensive tutorials/documentation.
5. **Auto-start daemon** on macOS — operationally convenient.
6. **Multi-agent council** — parallel coding with consensus voting.

### Main weaknesses

1. **No self-improving learning loop** — remembers but does not learn procedures.
2. **Young project** — created November 2025, only 5 months old.
3. **Founder departed** — Peter Steinberger joined OpenAI in February 2026.
4. **Supply-chain attack history** — ClawHub malware incident (January 2026).
5. **Weaker security model** — no skill sandboxing beyond a flag gate.
6. **Gateway, not personality** — less coherent as a personal operator.
7. **Dummy API key workaround** for Ollama — minor friction but inelegant.

### Verdict

**Best choice if channel breadth (especially iMessage) and CLI backend integration are the top priorities.** OpenClaw is the most capable gateway platform in the space. But it is a dispatcher, not a learning companion. For users who want "a coherent personal operator that grows with me," Hermes is stronger. For users who want "maximum reach, maximum flexibility, maximum ecosystem," OpenClaw wins.
