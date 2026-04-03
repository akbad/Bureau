# Section 5: Final Recommendation

## Deploy first: Hermes Agent (Pattern A)

**Hermes Agent is what I would actually tell you to deploy first.**

Reasons, in order of weight:

1. **It solves the "zero API keys + frontier models" problem uniquely.** By reusing Claude Code's credential store, Hermes gets Anthropic's best models without any API key. No other platform does this as cleanly. OpenClaw can delegate coding to Claude Code, but its own reasoning brain runs on Ollama or the bundled Pi binary — a meaningful quality gap for non-coding tasks (research, planning, life management).

2. **It is the only platform with a real self-improving loop.** Hermes creates reusable skill documents from experience, deepens its user model over time, and searches its own conversation history. This directly addresses the stated preference for "a coherent personal operator, not just a bag of plugins." OpenClaw stores memories but does not learn procedures.

3. **Memory architecture is the most elegant under fully-local constraints.** Five layers (MEMORY.md, USER.md, skills, SQLite+FTS5, optional Honcho), all in `~/.hermes/`, all Markdown + SQLite, all human-editable. No external database required. Compounding intelligence, not just durable storage.

4. **Security posture is explicitly single-operator.** Zero telemetry, fail-closed approval system, command scanning, sandboxed code execution. No ClawHub-equivalent supply-chain attack history.

5. **Messaging channels cover the practical bases.** Telegram, Discord, Slack, WhatsApp, Signal — all from a single gateway process. Missing iMessage is the main gap.

6. **Backed by Nous Research** — an established AI research organization with ongoing commitment. Contrast with OpenClaw, whose founder departed to OpenAI within months of creation.

7. **Bureau can layer underneath** for engineering protocol depth (Assess Mode, Micro Mode, MCP mesh, Qdrant, Memory MCP), providing what Hermes lacks in structured SWE governance.

### First-day deployment steps

1. Install Hermes via one-line installer on Mac.
2. Run `hermes model` to configure Claude Code auth (subscription reuse, zero API key).
3. Optionally configure Ollama as fallback for local/offline tasks.
4. Set up Telegram bot (via BotFather) and configure Hermes gateway.
5. Configure approval mode (recommend: `smart` for daily use).
6. Test: send a Telegram message from phone, verify Hermes responds.
7. Layer in Bureau's MCP servers for enhanced engineering capabilities.

## Second-best fallback: OpenClaw (Pattern B)

**Deploy OpenClaw if Hermes proves insufficient in practice, or if iMessage is a hard requirement.**

OpenClaw wins specifically when:
- You need **iMessage** (no other platform offers this).
- You need **25+ messaging channels** (OpenClaw's breadth is unmatched).
- You want the **most mature CLI backend delegation** (Claude Code, Codex, Gemini as first-class subprocess workers).
- You prefer a **huge community ecosystem** for skills, tutorials, and support.

OpenClaw loses when:
- You want the system to **get better over time** (it doesn't learn).
- You want **frontier-model quality** for non-coding reasoning without API keys (Ollama/Pi is the brain for non-delegated tasks).
- You care about **supply-chain security** (ClawHub incident history).
- You want **project governance stability** (founder departed, now foundation-governed).

### When to switch from Hermes to OpenClaw

- If you find yourself constantly wishing for iMessage access.
- If you need channels beyond Hermes's 7 (e.g., LINE, Matrix, Teams).
- If Hermes's CLI delegation proves less robust than OpenClaw's first-class backends.
- If the learning loop does not produce tangible value in practice.

## "Only if you specifically prioritize X" alternative

### If you prioritize total sovereignty and zero external platform risk: Bureau-native evolution (Pattern C)

Bureau already has a working Telegram → Claude Code/Codex/Gemini bridge, background runner, session state, and the strongest engineering protocol stack in this comparison. If you are willing to invest weeks of development to add more channels, a learning loop, and a stronger memory layer, you can build a fully sovereign solution with zero dependency on Hermes, OpenClaw, or any external project.

**Choose this only if:**
- You are certain you can sustain the development effort.
- You only need Telegram for now and can add channels over time.
- You value zero external dependency above deployment speed.
- You want to control the architecture completely.

**Do not choose this if:**
- You want phone access beyond Telegram today.
- You want self-improving behavior without building it yourself.
- You want a community ecosystem of skills and integrations.

### If OpenFang fixes its Ollama bug: reconsider it

OpenFang (github.com/RightNow-AI/openfang) is architecturally the most ambitious platform reviewed — a single 32MB Rust binary with 40 channel adapters, 38 built-in tools, 16 security systems, and explicit Claude Code CLI wrapping. It has a `CLAUDE.md` file in its repo and can wrap Claude Code as an agent runtime with scheduled tasks, heartbeat monitors, and event-driven workflows. It also supports migration from OpenClaw (`openfang migrate --from openclaw`).

**However**, issue #260 (March 2026) shows that Ollama local mode incorrectly demands `GROQ_API_KEY`, which breaks the zero-API-key requirement. The project is also pre-1.0 with "rough edges." Monitor this issue — if fixed, OpenFang could become the strongest single-binary contender.

### If you prioritize Apple Silicon optimization and local-only with zero network: CoPaw

CoPaw (v1.0.0, March 30, 2026) is the only platform with explicit MLX optimization for Apple Silicon M1–M4. Built by Alibaba's AgentScope team (14.4K stars, Apache 2.0). If you want to run everything on-device with zero network dependency, CoPaw is the best-optimized option. It supports iMessage, Telegram, Discord, and several Asia-centric channels (DingTalk, Feishu, WeChat). However, it is brand-new (v1.0.0 just shipped), has no built-in Claude Code delegation (would need a custom skill), and its self-improving capabilities are unproven. Watch this space — it may become a serious contender within 6 months.
