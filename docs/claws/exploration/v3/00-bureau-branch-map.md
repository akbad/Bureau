# Bureau branch reconnaissance (existing + planned)

## Existing functionality (as-of this branch)

- Cross-CLI agent orchestration across Claude Code, Codex, Gemini CLI, and OpenCode.
- 66 specialized role prompts, usable as native subagents (where supported) or via wrappers/launchers.
- Unified MCP stack for search, docs retrieval, memory, security scans, and browser automation.
- Dossier workflow (`fold` / `unfold`) for preserving and resuming full workstream state across sessions.
- Opinionated but configurable skill system (`assess-mode`, `micro-mode`, plus additional catalog skills).
- Concierge pipeline modules for command detection, scheduling, queueing, scoring, and Telegram bridge support.

## Planned / in-flight direction signaled in docs

- Context architecture migration to a hub-and-spoke system with per-task progressive disclosure and lower startup token load.
- Increased use of native headless CLI invocation for cross-CLI delegation; de-emphasis of PAL `clink` in some paths.
- Skill naming unification: canonical unprefixed skill names + shared install path for Codex/Gemini (`~/.agents/skills`).
- Cleanup model shift from prefix-based deletion to ownership-safe cleanup.
- Stronger memory and protocol hygiene around retrieval-first startup + incremental storage during execution.

## Implications for integrations

Bureau is already strongest where it can: (1) route tasks to specialist agents, (2) preserve long-lived state via dossiers + memory backends, and (3) normalize workflows across fragmented CLIs. Integrations that offer durable memory, autonomous background loops, or better UX surfaces (chat channels, PM dashboards, agent telemetry) are the highest-leverage fit.
