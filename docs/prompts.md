# prompts to keep saved

## to pick up

Read the handoff file at `memory/handoff-mcp-schema-design.md` (in the auto
memory directory). It contains the full state of an in-progress brainstorming
interview for designing MCP schema validation fixes. Your job is to resume this
interview exactly where it left off.

Before doing anything else:
1. Read the handoff file thoroughly — it has all decisions made so far, pending
   questions, file references, and checklist status
2. Read these files to rebuild context: `docs/mcp-schema-eval.md`,
   `docs/schema-fix-plan.md`, `operations/mcp_validation_rules.py`
3. Invoke the **brainstorming** skill to load the process, then resume at step 2
   (clarifying questions), picking up from the question about **W6** which the
   user hasn't answered yet

Do NOT re-ask any question that already has a decision in the handoff file. Do
NOT re-explore the codebase. Just re-present the pending W6 question and
continue the interview through W7-W11.

## add as slash command later

```md
# Persist current session state for handoff

You are about to create a **complete context snapshot** of the current
conversation so that a fresh agent with zero context can resume this exact task
without losing any progress.

## Where to persist

Write to a file in the **auto memory directory** (the `memory/` directory in
Claude Code's project config, e.g.
`~/.claude/projects/<project-path>/memory/`). This is the ONLY location that
persists across `/clear` and new sessions.

- **Do NOT use task lists** — they are session-scoped and die on `/clear`.
- **Do NOT pollute repo files** like CLAUDE.md or AGENTS.md.
- Name the file descriptively: `handoff-<topic>.md`
- Add or update a pointer in `MEMORY.md` under an `## Active Handoffs` section
  so future agents discover it automatically.
- Add a note at the top: `> **Delete this file** once the task is complete.`

## What to capture

The handoff file must contain ALL of the following:

### 1. Task overview
- What we are doing, in 2-3 sentences a stranger could understand
- Which skill/workflow/process is active (if any) and its checklist status
- The key files involved (with absolute or repo-relative paths)

### 2. Decision log
- Every decision made during this conversation, with:
  - The question that was asked
  - The option chosen (and its letter/label if applicable)
  - Brief rationale if one was given
- Decisions must be listed in chronological order
- Do NOT summarize or compress — each decision is its own entry

### 3. Pending state
- The exact question or action that was in progress when this snapshot was taken
- Whether the user has answered it yet
- Any subagent results that haven't been presented to the user yet
- Any open threads, unresolved ambiguities, or "we'll come back to this" items

### 4. Changes already made
- List all file edits, renames, config changes, and fixes made during this
  session
- Include enough detail that the next agent won't accidentally redo or revert
  them

### 5. Handoff prompt
- Write the exact prompt the user should paste to a fresh agent to resume
  seamlessly
- This prompt must tell the new agent: where to find the handoff file, what to
  read first, which skill to invoke (if any), and exactly where to pick up

## Rules

- **Err on the side of too much detail.** The cost of redundancy is zero; the
  cost of a missing decision is re-doing the entire conversation.
- **Do NOT paraphrase the user's decisions.** Quote or preserve their exact
  choice.
- **Include subagent outputs verbatim** (or summarized with key facts preserved)
  if they contain information the next agent will need.
- **After writing the handoff file, read it back** and verify: "Could an agent
  with empty context reconstruct our full mental stack from this alone?" If not,
  add what's missing.
- **Update `MEMORY.md`** — if it doesn't exist, create it. If it does, add or
  update the entry under `## Active Handoffs`. Never overwrite existing content.
```
