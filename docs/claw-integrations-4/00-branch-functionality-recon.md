# Bureau branch functionality reconnaissance (existing + planned)

## Scope and method
This reconnaissance synthesizes this branch by reading top-level product docs, usage docs, and active design plans.

## What Bureau currently is
Bureau is a cross-CLI orchestration layer for agentic coding workflows across Claude Code, Codex, Gemini CLI, and OpenCode. It standardizes:
- role prompts/agents,
- workflow skills,
- MCP server wiring,
- memory behaviors,
- and multi-CLI setup/operations ergonomics.

## Existing capabilities (implemented and user-facing)

### 1) Agent role system
- ~66 specialized roles available across supported CLIs.
- Two invocation modes:
  - as native/isolated subagents,
  - as interactive “main agent” personas.
- Wrapper scripts and slash commands smooth activation depending on CLI.

### 2) Skills as operational protocols
- Core installed skills include `assess-mode` and `micro-mode`.
- Optional cataloged skills include attack testing (`scrimmage-mode`), blast-radius analysis, completion gating (`clearance-mode`), invariant checking (`safeguard-mode`), and prompt engineering.
- Skills are intended to be low-friction and auto-triggerable via task pattern recognition.

### 3) Memory and context stack
- Multi-memory approach:
  - semantic/vector memory via Qdrant,
  - structural graph memory via Memory MCP,
  - optional Claude-only auto-memory via claude-mem.
- Explicit guidance exists for:
  - retrieval before work,
  - incremental storage during work,
  - metadata conventions for future reuse.

### 4) Tooling and MCP integration
- MCP stack includes code/search, web research, docs retrieval, memory services, security scanning, and browser automation.
- Operational docs emphasize deterministic tool routing and “smallest sufficient tool” selection.

### 5) Concierge mode (Telegram + pipeline)
- Concierge can run as a persistent Telegram bot.
- Message handling pipeline includes intent/classification and feature scoring/selection before LLM generation.
- Background runner supports automated periodic checks and actions.

## Branch direction (planned/in-flight)

### A) Context architecture overhaul (hub-and-spoke)
- Status indicates approved design pending implementation planning.
- Goal: reduce startup token load and route context instructions on-demand.
- Strategy: small mandatory hub + task-specific spoke docs + hook reinjection.

### B) Delegation modernization
- Planned shift away from PAL/clink toward native headless CLI invocation.
- Strong emphasis on JSON outputs/session IDs, auto-approval flags, and avoiding self-invocation anti-patterns.

### C) MCP portfolio evolution
- Planned GitHub MCP addition.
- PAL MCP removal (if clink deprecation completes).
- Codex-as-MCP examined but currently recommended against versus headless invocation.

### D) Skill naming/install unification
- Move to canonical unprefixed skill names.
- Consolidate Codex + Gemini skill installs under shared `~/.agents/skills/`.
- Improve cleanup/migration semantics to avoid deleting user-owned content.

## Practical interpretation for integrations
Bureau’s architecture strongly favors:
1. protocolized workflows over ad hoc prompt-only behavior,
2. modular memory infrastructure,
3. explicit delegation semantics,
4. adapter-oriented cross-platform compatibility,
5. preserving operator control while enabling autonomy.

For external platform integrations, the best fit will usually come from:
- mapping external memory models into Bureau’s Qdrant/graph patterns,
- wrapping external autonomous loops behind Bureau’s explicit approval gates,
- translating external role/agent taxonomies into Bureau role prompts + skills,
- and preserving CLI-agnostic behavior wherever possible.
