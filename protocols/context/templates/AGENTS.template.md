# Global context for Gemini CLI & Codex (always read first)

## MUST-READ FILES

Read these files using the appropriate read tool before starting any task and at the beginning of any conversation:

### [Output style]({{PROTOCOLS_DIR}}/output-style.md)

> **Read**: `@{{PROTOCOLS_DIR}}/output-style.md`

### [Operations hub]({{PROTOCOLS_DIR}}/ops-hub.md)

> **Read**: `@{{PROTOCOLS_DIR}}/ops-hub.md`

The output style shapes always-on response behavior for this session.

The hub routes you to task-specific context. Read the relevant spoke(s) for your current task.

## TASK LIST SCOPE: NATIVE vs BUREAU

Two task list systems exist. Using the wrong one loses state.

| System | Backing | Visibility | Use for |
|--------|---------|-----------|---------|
| **Native** (Codex internal planner, Gemini internal task tracking) | In-memory, tied to one session | Only the current session | Single-session subtask planning |
| **Bureau** (`bureau-dossiers tasks`) | SQLite on disk | Any process, any CLI, any agent | Cross-session and cross-CLI coordination |

When working from an unfolded dossier, ALL task operations go through Bureau CLI.

**Worker mode:** When working from a `--worker` unfold, you are scoped to a single task. Use `bureau-dossiers tasks` for status updates. Do not orchestrate — complete your assigned task and report.

## Note for Gemini & Codex

You are running via Gemini CLI or Codex, not Claude Code. Use headless CLI invocation for cross-model delegation (see task-assessment spoke). You have access to the same MCPs as Claude Code.
