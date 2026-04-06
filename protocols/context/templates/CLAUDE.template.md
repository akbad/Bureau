# Global context (always read first)

## MUST-READ FILE

Read this file using the Read tool before starting any task and at the beginning of any conversation:

### [Operations hub]({{PROTOCOLS_DIR}}/ops-hub.md)

> **Read**: `@{{PROTOCOLS_DIR}}/ops-hub.md`

The hub routes you to task-specific context. Read the relevant spoke(s) for your current task.

## TASK LIST SCOPE: NATIVE vs BUREAU

Two task list systems exist. Using the wrong one loses state.

| System | Backing | Visibility | Use for |
|--------|---------|-----------|---------|
| **Native** (`TodoWrite`/`TodoRead`) | In-memory, tied to one Claude Code process | Only the spawning agent and its subagents | Intra-session subagent coordination |
| **Bureau** (`bureau-dossiers tasks`) | SQLite on disk | Any process, any CLI, any agent | Cross-session and cross-CLI coordination |

When working from an unfolded dossier, ALL task operations go through Bureau CLI.

**Worker mode:** When working from a `--worker` unfold, you are scoped to a single task. Use Bureau task CLI for status updates (`tasks complete`, `tasks update`). Do not use native task tools — your coordination is through the dossier.
