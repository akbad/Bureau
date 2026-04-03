# Section 2: Hard-Filtered Shortlist

## Platform existence verification

Before filtering on constraints, every named platform was verified against primary sources (GitHub repos, official docs, setup guides).

| Platform | Real? | GitHub | Stars | Last active | Language |
|---|---|---|---|---|---|
| Hermes Agent | **Yes** | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | ~24K+ | April 2026 | Python |
| OpenClaw | **Yes** | [openclaw/openclaw](https://github.com/openclaw/openclaw) | ~347K | April 2026 | TypeScript |
| Letta | **Yes** | [letta-ai/letta](https://github.com/letta-ai/letta) | ~15K+ | 2026 | Python |
| OpenHands | **Yes** | [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) | ~50K+ | 2026 | Python |
| Memoh | **Yes** | [memohai/Memoh](https://github.com/memohai/Memoh) | smaller | 2026 | Go |
| CoPaw | **Yes** | [agentscope-ai/CoPaw](https://github.com/agentscope-ai/CoPaw) | newer | March 2026 | Python |
| OpenFang | **Yes** | [RightNow-AI/openfang](https://github.com/RightNow-AI/openfang) | newer | 2026 | Rust |
| Khoj | **Yes** | [khoj-ai/khoj](https://github.com/khoj-ai/khoj) | ~25K+ | 2026 | Python |
| Goose | **Yes** | [block/goose](https://github.com/block/goose) | ~30K+ | Jan 2026 | Rust |

**Note:** The prior v4 integration reports had "low confidence" on CoPaw, Memoh, and OpenFang because those research passes could not locate canonical docs. All three have since been verified as real projects with public repos and documentation.

## Hard constraint filter

Each constraint is evaluated as PASS / FAIL / PARTIAL. A single FAIL on any hard constraint eliminates the platform from the shortlist.

### Constraint 1: Zero API keys — can the platform function with no paid provider API keys?

| Platform | Verdict | Evidence |
|---|---|---|
| Hermes Agent | **PASS** | Ollama (local, no key). Also reuses Claude Code credential store (subscription auth, not API key). Minor caveat: FTS5 session search summarization defaults to Gemini Flash — may need redirection to local model or accepted as one small cloud call. |
| OpenClaw | **PASS** | Ollama (dummy placeholder key, not a real key). CLI backends use local CLI auth. |
| Letta | **PASS** (degraded) | Ollama supported, but docs warn: "very demanding agent harness, unlikely to get good performance with most open weights models." |
| OpenHands | **PASS** (degraded) | Ollama supported. Requires LLM API key field (can point to Ollama). |
| Memoh | **PARTIAL** | Uses "any OpenAI-compatible provider" — Ollama likely works but not explicitly documented as zero-key path. |
| CoPaw | **PASS** | Explicit: "no API keys, no cloud services required" with llama.cpp, MLX, Ollama. |
| OpenFang | **FAIL** | Active bug: Ollama local mode incorrectly demands `GROQ_API_KEY` even with local config (GitHub issue #260, March 2026). |
| Khoj | **PASS** | Explicit: `USE_EMBEDDED_DB="true" khoj --anonymous-mode` with Ollama, zero keys. |
| Goose | **PASS** | Works with any LLM including Ollama. |

### Constraint 2: No hosted memory, orchestration, or cloud dependencies

| Platform | Verdict | Evidence |
|---|---|---|
| Hermes Agent | **PASS** | All memory in `~/.hermes/` (SQLite + FTS5 + Markdown). Honcho is explicitly optional. |
| OpenClaw | **PASS** | All memory as local Markdown + SQLite. ClawHub is optional (can install skills from filesystem). |
| Letta | **PASS** | Self-hosted server via Docker. All state in local PostgreSQL or SQLite. |
| OpenHands | **PASS** | Self-hosted via Docker. Session state local. |
| Memoh | **PASS** | Docker Compose. Memory providers: file-based, sparse (local model), dense (local Qdrant). |
| CoPaw | **PASS** | Fully local with AgentScope runtime. |
| Khoj | **PASS** | All data on private network. |
| Goose | **PASS** | All local. |

### Constraint 3: Can use local Claude Code and Codex CLI (subscription auth, not API keys)

| Platform | Verdict | Evidence |
|---|---|---|
| Hermes Agent | **PASS** | Claude Code credential store reuse as LLM provider. Delegates coding to Claude Code and Codex CLI. ([Issue #477](https://github.com/NousResearch/hermes-agent/issues/477) confirms both exist as delegation targets; OpenHands proposed as model-agnostic addition.) |
| OpenClaw | **PASS** | First-class CLI backends: `claude-cli`, `codex-cli`, `google-gemini-cli`. "No keys, no extra auth config needed beyond the CLI itself." Each CLI runs as subprocess using its own local auth. |
| Letta | **FAIL** | No concept of delegating to external CLI tools. Letta IS the agent runtime. |
| OpenHands | **FAIL** | Self-contained SWE agent. Does not delegate to external CLIs. It replaces them, not orchestrates them. |
| Memoh | **PARTIAL** | MCP support enables tool extensibility, but no documented Claude Code/Codex CLI delegation. |
| CoPaw | **PARTIAL** | Multi-agent system but no explicit Claude Code/Codex delegation documented. |
| Khoj | **FAIL** | Knowledge search focused. No CLI tool orchestration. |
| Goose | **FAIL** | Is itself a CLI agent. Does not orchestrate other CLIs. |

### Constraint 4: Remote phone access via practical messaging channels

| Platform | Verdict | Key channels |
|---|---|---|
| Hermes Agent | **PASS** | Telegram, Discord, Slack, WhatsApp, Signal, Email, Home Assistant |
| OpenClaw | **PASS** | Telegram, Discord, WhatsApp, iMessage, Signal, 25+ total |
| Letta | **FAIL** | No built-in messaging channels. Framework only. |
| OpenHands | **FAIL** | Web UI only. No messaging channels. |
| Memoh | **PASS** | Telegram, Discord, Feishu/Lark, Matrix, QQ, WeCom, WeChat, Email, Web UI |
| CoPaw | **PASS** | DingTalk, Feishu, WeChat, Discord, Telegram |
| Khoj | **PARTIAL** | WhatsApp, Web, Desktop, Obsidian. No Telegram, no Discord. |
| Goose | **FAIL** | CLI + Desktop app only. No messaging channels. |

### Constraint 5: Viable on macOS as single-user home deployment

| Platform | Verdict | Notes |
|---|---|---|
| Hermes Agent | **PASS** | One-line installer, runs natively on macOS. Single `~/.hermes/` folder. |
| OpenClaw | **PASS** | Homebrew install, auto-start daemon, macOS 12+, Node 22+. |
| Letta | **PASS** | Docker or pip install. |
| OpenHands | **PASS** | Docker-based. |
| Memoh | **PASS** | Docker Compose. |
| CoPaw | **PASS** | Python pip. MLX optimized for Apple Silicon. |
| Khoj | **PASS** | Docker or pip install. |
| Goose | **PASS** | Native binary + desktop app. |

## Elimination results

| Platform | Constraint failures | Status |
|---|---|---|
| **Hermes Agent** | None | **SURVIVES** |
| **OpenClaw** | None | **SURVIVES** |
| Letta | CLI delegation (FAIL), Phone channels (FAIL) | **ELIMINATED** — strong as a memory ingredient, not as a deployable platform |
| OpenHands | CLI delegation (FAIL), Phone channels (FAIL) | **ELIMINATED** — strong as a SWE executor ingredient, not as a shell |
| Memoh | CLI delegation (PARTIAL), API key clarity (PARTIAL) | **ELIMINATED** — promising but unverified on critical constraints |
| CoPaw | CLI delegation (PARTIAL) | **BORDERLINE** — watch closely, too immature (v1.0.0, March 2026) |
| OpenFang | API keys (FAIL — active bug) | **ELIMINATED** — would need bug fix before reconsideration |
| Khoj | CLI delegation (FAIL), Phone channels (PARTIAL) | **ELIMINATED** — wrong category (knowledge manager, not agent orchestrator) |
| Goose | Phone channels (FAIL) | **ELIMINATED** — useful as a worker CLI, not as an always-on shell |

## Survivors for deep comparison

1. **Hermes Agent** — full pass on all constraints
2. **OpenClaw** — full pass on all constraints

## Ingredient-layer candidates (not eliminated, but not deployable shells)

These failed as primary platforms but remain relevant as components in hybrid architectures:

- **Letta** — best-in-class memory hierarchy, usable as a memory compiler backend
- **OpenHands** — best-in-class SWE execution, usable as a sandboxed coding executor
- **Goose** — strong MCP-native CLI agent, usable as an alternative coding worker
- **Bureau** (existing) — strongest protocol/governance/orchestration substrate, already has Telegram bridge + CLI delegation
