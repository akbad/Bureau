# Section 7: Decision Matrix

## Scoring model

Scale: 0–3.

- `0` = absent or disqualifying
- `1` = present but weak, partial, or fragile
- `2` = solid, functional, reliable
- `3` = leading — best-in-class for this criterion

Confidence is rated separately: **H** (high — verified against primary sources), **M** (medium — inferred from strong evidence), **L** (low — inferred from indirect evidence).

## Finalists

Only the two survivors from hard-constraint filtering and their key ingredient-layer candidates.

## Matrix

| Criterion | Hermes Agent | OpenClaw | Bureau (existing, for reference) |
|---|---|---|---|
| **Zero-API-key purity** | **3** (H) — Ollama + Claude Code credential store reuse. No API key needed for frontier models. | **2** (H) — Ollama with dummy key workaround. CLI backends use local auth. But own brain limited to Ollama/Pi quality. | **3** (H) — CLI subprocess model, no API keys. But limited to subprocess delegation, not own reasoning. |
| **Local Claude/Codex reuse** | **3** (H) — Uses credential store as LLM provider + delegates tasks. Dual-use of existing subscriptions. | **3** (H) — First-class CLI backends. Best subprocess integration. "No keys beyond the CLI itself." | **2** (H) — Working subprocess model (`cc_connect.py`). Functional but less featured. |
| **Phone ergonomics** | **2** (H) — 7 channels via single gateway. Telegram, Discord, WhatsApp, Signal. Missing iMessage. | **3** (H) — 25+ channels. iMessage via BlueBubbles. Broadest coverage by far. | **1** (H) — Telegram only. Functional but limited. |
| **SWE depth** | **2** (M) — Terminal, code exec, CLI delegation. No sandbox. Depends on Claude Code/Codex for heavy lifting. Bureau layering strengthens this. | **2** (M) — CLI backends + multi-agent council + git worktree. No sandbox. Depends on CLIs. Bureau layering strengthens this. | **3** (H) — 66 roles, Assess/Micro Mode, MCP mesh, dossiers. Strongest engineering protocol. |
| **Life/task management fit** | **3** (M) — Cron scheduling, persistent user model, web search, browser. Self-improving skill creation strengthens planning over time. | **2** (M) — Heartbeat/cron events, smart home. No self-improving behavior. Memory is storage, not learning. | **1** (M) — Background runner exists but concierge is early-stage. |
| **Memory/continuity (fully local)** | **3** (H) — Five-layer system: MEMORY.md, USER.md, skills, SQLite+FTS5, optional Honcho. All in `~/.hermes/`. Self-improving. | **2** (H) — MEMORY.md, daily notes, SQLite with hybrid search. Local and transparent. But non-learning. | **2** (H) — Qdrant + Memory MCP + dossiers. Strong for engineering knowledge. Weaker for personal/assistant memory. |
| **Security posture** | **3** (H) — Single-operator design. Zero telemetry. Fail-closed approvals. Tirith command scanning. Sandboxed code exec. No known supply-chain incidents. | **1** (H) — Pairing model exists but weak skill sandboxing. ClawHub Atomic Stealer incident (Jan 2026, CVE-2026-25253). Young project. | **2** (M) — Single-user Telegram auth. Role-based access. No known incidents. But limited channel auth. |
| **Architectural elegance** | **3** (M) — Unified daemon with coherent identity, learning loop, and clean five-layer memory. Feels designed. | **2** (M) — Clean gateway architecture. SOUL.md is tidy. But it's a router, not a personality. Memory flush before compaction is clever. | **2** (M) — Pipeline orchestrator is clean. But concierge is early-stage relative to the rest of Bureau. |

## Weighted scores

Weights: Zero-API-key (5), Claude/Codex reuse (5), Phone ergonomics (4), SWE depth (3), Life/task fit (4), Memory/continuity (5), Security (4), Elegance (3).

| Criterion | Weight | Hermes | OpenClaw | Bureau |
|---|---|---|---|---|
| Zero-API-key purity | 5 | 15 | 10 | 15 |
| Local Claude/Codex reuse | 5 | 15 | 15 | 10 |
| Phone ergonomics | 4 | 8 | 12 | 4 |
| SWE depth | 3 | 6 | 6 | 9 |
| Life/task management | 4 | 12 | 8 | 4 |
| Memory/continuity | 5 | 15 | 10 | 10 |
| Security posture | 4 | 12 | 4 | 8 |
| Architectural elegance | 3 | 9 | 6 | 6 |
| **Total** | **33** | **92** | **71** | **66** |

## Interpretation

**Hermes leads decisively** (92 vs 71) primarily due to:
- Zero-API-key purity with frontier models (credential store reuse)
- Self-improving memory and learning loop
- Security posture (zero incidents, zero telemetry)
- Architectural coherence (feels like one system)

**OpenClaw's strength** is concentrated in phone ergonomics (iMessage uniquely) and Claude/Codex CLI delegation maturity. If the weights shifted heavily toward channel breadth, OpenClaw closes the gap.

**Bureau's strength** is SWE protocol depth — it scores highest there. This confirms it should remain as the engineering governance layer in any pattern, not be replaced.

## The composite answer

The best architecture is not one platform. It is:

| Layer | Component | Why |
|---|---|---|
| Personal operator + always-on shell | **Hermes Agent** | Self-improving, coherent identity, frontier models via subscription auth |
| Coding workers | **Claude Code + Codex CLI** (local, subscription auth) | Best coding agents, already authenticated, delegated by Hermes |
| Engineering governance | **Bureau** | 66 roles, Assess/Micro Mode, MCP mesh, Qdrant, Memory MCP |
| Fallback/local LLM | **Ollama** | For offline/non-frontier tasks when subscription auth unavailable |
| iMessage gateway (if needed) | **OpenClaw** (secondary, optional) | Only platform with iMessage support |

## Sources

Primary sources consulted during this analysis:

- [Hermes Agent — Nous Research](https://hermes-agent.nousresearch.com/)
- [Hermes Agent GitHub](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/)
- [Hermes Agent Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers/)
- [Hermes Agent Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/)
- [Hermes Agent Security](https://hermes-agent.nousresearch.com/docs/user-guide/security/)
- [Hermes Agent Issue #477 — OpenHands delegation](https://github.com/NousResearch/hermes-agent/issues/477)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw Docs](https://docs.openclaw.ai/)
- [OpenClaw CLI Backends](https://docs.openclaw.ai/gateway/cli-backends)
- [OpenClaw Memory](https://docs.openclaw.ai/concepts/memory)
- [OpenClaw Security](https://docs.openclaw.ai/gateway/security)
- [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [OpenClaw Ollama Provider](https://docs.openclaw.ai/providers/ollama)
- [openclaw-claude-code plugin](https://github.com/Enderfga/openclaw-claude-code)
- [OpenClaw acpx](https://github.com/openclaw/acpx)
- [Letta Docs](https://docs.letta.com/)
- [Letta Self-Hosting](https://docs.letta.com/guides/selfhosting/)
- [Letta Ollama](https://docs.letta.com/guides/server/providers/ollama/)
- [OpenHands Docs](https://docs.all-hands.dev/usage/local-setup)
- [Khoj Docs](https://docs.khoj.dev/get-started/setup/)
- [Khoj GitHub](https://github.com/khoj-ai/khoj)
- [Goose GitHub](https://github.com/block/goose)
- [Memoh GitHub](https://github.com/memohai/Memoh)
- [Memoh Docs](https://docs.memoh.ai/)
- [CoPaw GitHub](https://github.com/agentscope-ai/CoPaw)
- [CoPaw Docs](https://copaw.bot/)
- [OpenFang GitHub](https://github.com/RightNow-AI/openfang)
- [OpenFang Issue #260 — Ollama GROQ_API_KEY bug](https://github.com/RightNow-AI/openfang/issues/260)
- [Honcho GitHub](https://github.com/plastic-labs/honcho)
- [Honcho Self-Hosting](https://docs.honcho.dev/v3/contributing/self-hosting)
- [Honcho + Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho/)
- [Open Interpreter GitHub](https://github.com/openinterpreter/open-interpreter)
- [n8n Telegram + Ollama workflow](https://n8n.io/workflows/6012-create-a-privacy-focused-ai-assistant-with-telegram-ollama-and-whisper/)
- [Hermes vs OpenClaw comparison — The New Stack](https://thenewstack.io/persistent-ai-agents-compared/)
- [OpenClaw security — Akamai](https://www.akamai.com/blog/security/clawdbot-openclaw-practical-lessons-building-secure-agents)
- [OpenClaw security — Oasis](https://www.oasis.security/blog/openclaw-vulnerability)
