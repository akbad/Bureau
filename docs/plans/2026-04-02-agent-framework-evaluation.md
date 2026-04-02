# Agent Framework Evaluation: Bureau vs. Field

**Date:** 2026-04-02
**Status:** Active — informing two-track development plan

## Context

Evaluated Bureau against six competing always-on multi-channel personal
assistant frameworks: **OpenClaw**, **CoPaw**, **Hermes Agent**, **Memoh**,
**LettaBot + Letta**, and **LocalAGI**.

Bureau is not a direct competitor — it is a **multi-agent orchestration layer
for coding CLIs** (Claude Code, Gemini CLI, Codex, OpenCode) with a Telegram
bot concierge.  The competitors are **general-purpose always-on personal
assistants** with broad channel support.  The overlap is in the concierge layer
and the memory/scheduling subsystems.

## Competitive Position

### Where Bureau leads (no competitor attempts this)

| Capability | Bureau | Nearest rival |
|---|---|---|
| Cross-CLI agent orchestration | 29 roles across 4 CLIs | None |
| Step-gated editing (Micro Mode) | Production | None |
| Multi-style code assessment (Assess Mode) | Production | None |
| MCP server integration depth | 15+ servers, 80+ tools | OpenClaw (broad but less dev-focused) |
| Conversation snapshot/resume (Dossiers) | Production | None |

### Where Bureau trails

| Capability | Bureau | Leader | Gap |
|---|---|---|---|
| Channel breadth | Telegram only | OpenClaw (~8 channels) | Critical |
| Proactive assistant loop | Basic (WIP features) | Hermes (learning loop) | Significant |
| Memory unification | 3 fragmented backends | Letta (unified stateful agents) | Moderate |
| Security hardening | Single-user filter + env vars | CoPaw (tool-guard, skill scanning) | Moderate |
| Container isolation | None | Memoh (per-bot containers) | Low priority |
| iMessage | None | CoPaw (macOS native) | Nice-to-have |

### Architecture advantage: pipeline is 90% channel-agnostic

The concierge pipeline (classify -> suite detect -> hard rules -> feature eval
-> lottery -> response) operates entirely on domain types (`MessageEnvelope`,
`SessionState`, `FeatureCandidate`).  Telegram is isolated to two files:

- `bridge/telegram.py` — PTB bot loop + handlers
- `bridge/adapter.py` — Telegram -> `MessageEnvelope` conversion + 4096-char truncation

Adding a new channel = one transport file + one adapter function.  The pipeline
does not change.

## Decision: Build Both Tracks in Parallel

### Track A — Multi-Channel Assistant Expansion

Goal: close the channel-breadth and assistant-behavior gaps.

| ID | Task | Effort | Depends on |
|---|---|---|---|
| A1 | Abstract `ChannelTransport` protocol from `telegram.py` | 1-2d | — |
| A2 | Parameterize truncation per channel (move out of adapter) | 0.5d | A1 |
| A3 | Discord adapter + transport | 2-3d | A1, A2 |
| A4 | Unified `main()` booting multiple transports from config | 1d | A3 |
| A5 | Signal adapter (via signal-cli) | 2-3d | A1 |
| A6 | Slack adapter | 1-2d | A1 |
| A7 | Memory unification layer (single interface over Qdrant + Memory MCP + claude-mem) | 2-4d | — |
| A8 | Proactive assistant loop (heartbeat-driven dispatches) | 2-3d | A4 |
| A9 | iMessage adapter (macOS Messages.app/db) | 3-5d | A1 |

### Track B — Dev Tool Improvements

Goal: finish WIP features and unlock multi-agent workflows.

| ID | Task | Effort | Depends on |
|---|---|---|---|
| B1 | Fold/Unfold critical fixes (C1-C3) | 2-3d | — |
| B2 | Hub-and-spoke protocol restructure (76% token savings) | 3-4d | — |
| B3 | Task-scoped context extraction (worker mode) | 2-3d | B1 |
| B4 | Protocol deployment modes (-u/-f/-b) | 2-3d | — |
| B5 | Skill naming unification (drop `bureau-` prefix) | 2-3d | — |
| B6 | Micro Mode batch approval + pattern atlas | 3-4d | — |
| B7 | Dossier event log with causal ordering | 3-5d | B1 |
| B8 | Heartbeat leases for task claims | 2-3d | B1 |

### Execution order

**Sprint 1:** A1 + A2 (transport abstraction) || B1 (fold/unfold fixes)
**Sprint 2:** A3 (Discord) || B2 (hub-and-spoke)
**Sprint 3:** A4 + A7 (unified boot + memory) || B3 + B4 (worker mode + deploy modes)
**Sprint 4+:** A5-A9, B5-B8 based on priority

## Projected Competitive Position After Sprint 2

- 2 channels (Telegram + Discord) with clean abstraction for more
- 76% token reduction on non-coding tasks
- Safe multi-agent dossier workflows
- Still unique: 29 agent roles, cross-CLI orchestration, Assess/Micro Mode, full MCP stack

## Competitor Reference

### Rankings (for always-on home assistant use case)

1. **OpenClaw** — broadest feature surface, highest maintenance burden
2. **CoPaw** — best balance of breadth + guardrails, strong on macOS/iMessage
3. **Hermes Agent** — best dev-first non-iMessage option, autonomous learning
4. **Memoh** — best isolation (per-bot containers), Docker-heavy
5. **LettaBot + Letta** — best memory-first architecture
6. **LocalAGI** — best pure local/privacy-first posture

### Key takeaways for Bureau

- Prefer Telegram/Discord as primary remote channels (cleanest support across field)
- iMessage has high friction everywhere (BlueBubbles/SIP on OpenClaw, macOS-only on CoPaw)
- Tool approvals should stay on (OpenClaw + Hermes both gate tool execution)
- Stronger models for tool-enabled agents (OpenClaw security guidance)
- Memory unification is table stakes (Letta, Memoh, Hermes all have coherent retrieval)
