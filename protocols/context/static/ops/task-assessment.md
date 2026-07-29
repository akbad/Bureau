# Task assessment

## Delegation mechanisms

| Mechanism | Use for |
| :--- | :--- |
| Native subagents (Task/Agent tool, internal planner) | Same-CLI delegation; always prefer this over headless self-invocation |
| Headless CLI via Bash | Cross-CLI delegation only (see invocation table below) |
| AskUserQuestion | Ambiguity, multiple valid approaches, approval needed |

### Headless invocation

- For delegating to a **different** CLI than the one you are running in.
- **Never** invoke *your own* CLI headlessly; use your native subagent tools instead.

| CLI | Invoke | Resume | Output | Auto-approve |
| :--- | :--- | :--- | :--- | :--- |
| Claude Code | `claude -p "prompt"` | `--resume SESSION_ID` | `--output-format json` | `--allowedTools "tools"` |
| Codex | `codex exec "prompt"` | `codex exec resume SESSION_ID` | `--json` | `--full-auto` |
| Gemini | `gemini -p "prompt"` | (session ID from init event) | `--output-format json` | TBD: verify Gemini CLI auto-approve flag before implementation |
| Grok Build | `grok -p "prompt"` | `-r ID` / `-c` | `--output-format json` | `--yolo` / `--permission-mode bypassPermissions` |

**Essential rules:**

- Always set auto-approve flags; headless agents hang on permission prompts.
- Inject role via `--append-system-prompt` (Claude) or in the prompt itself (Codex/Gemini/Grok).
- Use `--bare` (Claude) for simple scoped tasks that don't need MCPs.
- Omit `--bare` when the headless agent needs MCP server access.
- Always use JSON output to capture session IDs.
- Always use the exact session ID to resume.

## Parallel delegation

- **Default:** before starting work, ask "can I split this into 2+ independent subtasks?"
- If yes → spawn multiple subagents in a single response (not sequentially).
- **Superpowers precedence:** if a skill mandates a workflow, follow it; use these guidelines to choose who/what within that workflow.
