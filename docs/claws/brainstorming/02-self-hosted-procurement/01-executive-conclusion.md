# Section 1: Executive Conclusion

## The answer

**No single claw-platform cleanly satisfies all constraints today.** The best realistic setup is a hybrid stack centered on one platform as the always-on gateway/shell, with local coding CLIs as the execution layer and Bureau as the engineering governance substrate.

**The two viable platforms are Hermes Agent and OpenClaw.** Everything else is either disqualified by the hard constraints or relegated to ingredient/layer status.

## Primary recommendation

**Hermes Agent** (by Nous Research) is the best primary platform for this specific constraint set.

Rationale:
- It is the only platform that can reuse Claude Code's subscription credential store as its own LLM provider — giving frontier-model reasoning quality with zero separate API keys.
- It has first-class Claude Code and Codex CLI delegation for coding tasks.
- Its memory system (MEMORY.md, USER.md, SQLite + FTS5 session archive) is fully local, elegant, and self-improving.
- Its skill-creation-from-experience loop is architecturally unique and directly addresses the "coherent personal operator" preference.
- Multi-channel messaging (Telegram, Discord, Slack, WhatsApp, Signal) is built into the single gateway daemon.
- Security posture is explicitly designed for single-operator environments with zero telemetry.
- Active development: v0.4.0 shipped March 2026, rapid iteration cadence.

## Strong alternative

**OpenClaw** is the strongest alternative and wins on specific axes:
- Broader channel coverage (25+ channels, including **iMessage** — unique among all platforms).
- Larger ecosystem and community (347K GitHub stars, massive plugin/skill library).
- More mature CLI backend model — Claude Code, Codex, and Gemini CLI are first-class subprocess backends using local auth directly.

OpenClaw loses on:
- No self-improving learning loop (it remembers, but doesn't learn procedures).
- Younger project (created November 2025, only 5 months old).
- Founder departed to OpenAI; now foundation-governed.
- January 2026 ClawHub skill-registry malware incident (Atomic Stealer supply-chain attack).
- Weaker security model (no skill sandboxing beyond a flag gate).

## Hybrid option

If maximum coverage is needed:

**Hermes Agent as the personal operator brain + OpenClaw as a secondary gateway for iMessage/additional channels + Bureau as the engineering protocol and governance layer + Ollama as the fallback local LLM for non-frontier tasks.**

This is architecturally viable but operationally heavy. Deploy only after Hermes alone proves insufficient.

## What did not survive

- **Letta**: strong memory semantics but no messaging channels, no CLI delegation, and performance suffers on local models — it is a framework ingredient, not a deployable always-on assistant.
- **OpenHands**: excellent SWE executor but session-based, no messaging, requires LLM API keys — it is a worker, not a shell.
- **Memoh**: real and promising but requires API keys for LLM inference, less mature than Hermes/OpenClaw.
- **CoPaw**: real and zero-API-key capable with MLX on Apple Silicon, but v1.0.0 just shipped (March 30, 2026), no Claude Code delegation, too immature to recommend today.
- **OpenFang**: ambitious Rust-based agent OS but pre-1.0, has an active bug preventing zero-API-key Ollama usage.
- **Khoj**: strong for personal knowledge management but no Telegram, no CLI delegation — not an agent orchestrator.
- **Goose** (Block): excellent MCP-native CLI agent but session-based, no messaging channels — useful as a worker.

## Critical nuance: "Zero API keys" and subscription auth

The user's constraint is "no API keys" — meaning no `OPENAI_API_KEY`, no `ANTHROPIC_API_KEY`, no paid provider wiring. This does **not** exclude:

1. **Subscription auth reuse**: Claude Code's credential store holds OAuth tokens from the user's existing Anthropic subscription. Hermes can reuse these. This is subscription-session auth, not API-key-provider wiring.
2. **CLI-local auth**: OpenClaw's CLI backends use whatever auth the local CLI already has. No separate keys.
3. **Bot platform tokens**: Telegram Bot tokens (free, via BotFather), Discord bot tokens, etc. are required by the messaging platforms themselves. These are self-managed credentials, not paid provider API keys.

Both Hermes and OpenClaw satisfy the spirit of "zero API keys" through these mechanisms.
