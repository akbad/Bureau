<bureau:required-context-by-task>

  <read-file-when task="starting a session" path="{{PROTOCOLS_DIR}}/ops/session-start.md" />
  <read-file-when task="deciding to delegate, choosing model/tool, parallelizing" path="{{PROTOCOLS_DIR}}/ops/task-assessment.md" />
  <read-file-when task="executing: searching, editing, storing memories" path="{{PROTOCOLS_DIR}}/ops/task-execution.md" />
  <read-file-when task="finishing: approvals, memory persistence, handoff" path="{{PROTOCOLS_DIR}}/ops/task-completion.md" />
  <read-file-when task="writing or editing code" path="{{PROTOCOLS_DIR}}/code-standards.md" />

  <bureau-rules>
    <output-style-reminder>
      The Bureau output style loaded at session start from {{PROTOCOLS_DIR}}/output-style.md remains active for this session.
      Do not re-read it every turn.
      Changes take effect on a new session unless explicitly refreshed.
    </output-style-reminder>

    <task-lists>
      Two task list systems exist. Using the wrong one loses state.

      | System | Backing | Visibility | Use for |
      |--------|---------|-----------|---------|
      | **Native** (`TodoWrite`/`TodoRead`, Codex internal planner, Gemini internal task tracking) | In-memory, tied to one process/session | Only the spawning agent and its subagents | Intra-session subagent coordination |
      | **Bureau** (`bureau-dossiers tasks`) | SQLite on disk | Any process, any CLI, any agent | Cross-session and cross-CLI coordination |

      When working from an unfolded dossier, ALL task operations go through Bureau CLI.

      **Worker mode:** When working from a `--worker` unfold, you are scoped to a single task. Use Bureau task CLI for status updates (`tasks complete`, `tasks update`). Do not use native task tools or orchestrate; complete your assigned task and report.
    </task-lists>

    <cross-model-note>
      If running via Gemini CLI or Codex (not Claude Code): use headless CLI invocation for cross-model delegation (see task-assessment spoke). You have access to the same MCPs as Claude Code.
    </cross-model-note>
  </bureau-rules>

</bureau:required-context-by-task>
