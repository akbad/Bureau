# Prompt calibration for subagent dispatch

Best practices for writing subagent prompts during Phase 4. This file
complements the handoff guide's subagent context management section -- it
does not duplicate it. The handoff guide covers WHAT to include; this file
covers HOW to structure it for Dispatch-specific concerns.

## Prompt structure

Every subagent prompt dispatched through this skill must contain these
sections in this order:

```
1. TASK         — what to do (one sentence)
2. CONTEXT      — what the subagent needs to know
3. INPUTS       — files to read, resources to consult
4. DELIVERABLE  — what to produce and in what format
5. ACCEPTANCE   — how success is verified
6. CONSTRAINTS  — what NOT to do
7. SKILLS       — Bureau/Superpowers skills to follow
8. STOP         — SUBAGENT-STOP directive
```

## Section guidance

### TASK

One sentence. If you cannot describe the task in one sentence, the work unit
is too large or too vague. Decompose further.

Good: "Write unit tests for the `UserService` class covering all public methods."
Bad: "Work on the user module and make sure it's well-tested and clean."

### CONTEXT

Summarize only what the subagent needs. Do not dump your entire conversation
history. Include:

- Architectural context relevant to this specific task
- Design decisions that constrain the implementation
- Known gotchas discovered during your investigation

Omit:
- Context about other work units (irrelevant to this subagent)
- History of how you arrived at this decomposition
- General project information the subagent can discover from code

### INPUTS

Absolute file paths. Always. Never relative paths.

List files in two groups:
- **Must read**: files the subagent must read before starting
- **May reference**: files available for context but not essential

### DELIVERABLE

Specify exactly what the subagent should produce and where to put it. This
must match the reconciliation plan from Phase 3.

Good: "Create test file at `/absolute/path/to/test_user_service.py`. Do not
modify any existing files."
Bad: "Write some tests."

### ACCEPTANCE

Observable, testable conditions. Each criterion should be verifiable by
running a command or inspecting output.

Good:
- "All tests in `test_user_service.py` pass when run with `pytest`"
- "Test coverage for `UserService` exceeds 80%"
- "No new linter warnings introduced"

Bad:
- "Tests are comprehensive"
- "Code is clean"
- "Good coverage"

### CONSTRAINTS

Explicitly name files and directories the subagent must NOT modify. This
defines the blast radius boundary. When in doubt, be restrictive.

Always include:
- Files in other work units' blast radii
- Configuration files not directly related to the task
- Database schemas (unless the task is specifically a migration)

### SKILLS

List any Bureau or Superpowers skills the subagent should follow. Only
include skills relevant to the task.

Example: "Follow the `test-driven-development` skill for writing tests."

Do not list Dispatch itself. The SUBAGENT-STOP directive handles that.

### STOP

Always end with:

```
<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip the
Dispatch skill. Do not spawn your own subagents unless explicitly instructed.
</SUBAGENT-STOP>
```

## Model selection

Do not reinvent model selection here. Reference the handoff guide's decision
tree and task category table. The Dispatch skill's value is in structural
discipline, not in model recommendations.

Quick reference for common dispatch scenarios:
- **Mechanical code changes** (refactors, renames, test writing): see handoff
  guide's "Mechanical refactors" category
- **Analysis and research**: see handoff guide's "Research" phase
- **Architecture decisions**: see handoff guide's "Planning" phase

## Common calibration mistakes

| Mistake | Fix |
|---------|-----|
| Prompt is longer than the task itself | Trim context to what is task-specific; the subagent can read code |
| Acceptance criteria are subjective ("good code") | Replace with commands to run and expected outcomes |
| Deliverable format is unspecified | Specify file paths, naming conventions, and structure |
| Constraints are absent | At minimum, list files in other work units' blast radii as off-limits |
| No SUBAGENT-STOP | Always include it -- even for simple tasks |
| Relative file paths | Convert every path to absolute before including in the prompt |
