# Bureau context routing

Read or activate the context source matching your current task:

| Task | Spoke |
| :--- | :--- |
| Starting a session | `{{PROTOCOLS_DIR}}/ops/session-start.md` |
| Deciding to delegate, choosing model/tool, parallelizing | `{{PROTOCOLS_DIR}}/ops/task-assessment.md` |
| Executing: searching, editing, storing memories | `{{PROTOCOLS_DIR}}/ops/task-execution.md` |
| Finishing: approvals, memory persistence, handoff | `{{PROTOCOLS_DIR}}/ops/task-completion.md` |
| Writing or editing code | Activate the `code-standards` skill |

## Bureau rules

### Output style

- The Bureau output style loaded at session start from `{{PROTOCOLS_DIR}}/output-style.md` remains active for this session.
- Do not re-read it every turn.
- Changes take effect on a new session unless explicitly refreshed.

### Task lists

Two task list systems exist. Using the wrong one loses state.

| System | Backing | Visibility | Use for |
| :--- | :--- | :--- | :--- |
| **Native** (`TodoWrite`/`TodoRead`, Codex internal planner, Gemini internal task tracking) | In-memory, tied to one process/session | Only the spawning agent and its subagents | Intra-session subagent coordination |
| **Bureau** (`bureau-dossiers tasks`) | SQLite on disk | Any process, any CLI, any agent | Cross-session and cross-CLI coordination |

- When working from an unfolded dossier, **all** task operations go through Bureau CLI.
- **Worker mode:** when working from a `--worker` unfold, you are scoped to a single task.

    - Use Bureau task CLI for status updates (`tasks complete`, `tasks update`).
    - Do not use native task tools or orchestrate; complete your assigned task and report.

### Cross-model delegation

- If running via Gemini CLI or Codex (not Claude Code): use headless CLI invocation for cross-model delegation (see task-assessment spoke).
- You have access to the same MCPs as Claude Code.
