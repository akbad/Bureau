---
name: micro-mode
description: Step-gated editing with DAG-based planning and continuous user steering. Activate when user says "MICRO MODE ON", "implement in micro mode", or wants maximum control over each atomic edit with pause points after every change. Each edit is limited to one function and 30 lines, with shortcut keys for continuing onwards, asking for explanations of various types, and more. Ideal for careful refactoring, high-risk changes, or when user wants to review every modification before proceeding.
---

# Micro mode editing protocol

> **Goal:** step-gated edits in auto-accept mode.
> 
> Maximum throughput with continuous, real-time user steering. You will make exactly **one atomic "micro edit"** at a time, then pause. The user can course-correct immediately; you must rebase on the user's edits before continuing.

## Entry & exit protocols

### Activation

When the user says anything like:

- "MICRO MODE ON"
- "complete this task in micro mode"
- "implement in micro mode"

Follow this protocol until told anything like:

- "exit micro mode"
- "finish the task/implementation without micro mode"
- "MICRO MODE OFF"

If unsure, confirm unambiguously with the user.

### Deactivation

Upon exit, output in this exact format:

```
═══════════════════════════════════════
Micro Mode OFF
Completed: N/M steps
Remaining: [step-ids, or "none"]
DAG stored: [location, or "chat only"]
═══════════════════════════════════════
```

If no steps/nodes remain, delete the DAG from memory and any persisted instances.

### Pause

If the user says anything like "pause for now", "stop here", "let's continue later", or "save progress":

1. Persist the DAG to memory (see [DAG persistence protocol](#dag-persistence-protocol)) and ensure it reflects current progress
2. Emit pause summary:

    ```
    ⏸️ Micro Mode PAUSED
    Completed: N/M steps
    Next ready: [step-ids]
    Blocked: [step-ids, or "none"]
    DAG stored: [location]
    Resume: "MICRO MODE ON, continue"
    ```

3. Exit micro mode (do **not** emit the deactivation summary — this is a pause, not an exit)

## Skill-specific vocabulary

### *Micro edits*

One micro edit may modify **at most**:

- **One function** (primary target)
- **≤30 total lines changed** *(added + removed)*

> [!NOTE]
> - **Line counting**: Count gross changes. Replacing 5 lines with 3 new lines = 8 changes (5 removed + 3 added).
> - **Multi-file exception**: A function rename (definition + call-site updates) counts as *one* micro edit if call-site changes are mechanical and total <10 additional lines.

If a change exceeds these limits, split it into multiple micro edits in this order:

1. Interface / signature / scaffolding
2. Core logic
3. Edge cases
4. Tests
5. Cleanup or refactor

### *Resumption tokens*

The user resumes execution (in phase 2) by either sending: 

- any natural language prompt like "continue", "proceed", "go on" or "next edit"
- the **resumption token** (ergonomic shortcut): `.`

> [!NOTE]
> Any other shortcuts defined in this protocol (e.g., *explain keys*) are **not** resumption tokens (and hence do *not* advance the DAG).

### *Explain keys*

Six single-character keys for on-demand, *distinguished engineer-level* explanations of any micro edit, without advancing the DAG. Available at every pause point alongside resumption tokens.

| Key | Axis | Mnemonic | Focus |
|-----|------|----------|-------|
| `r` | Repo | **r**epo | Architectural context, design decisions, how this change fits the surrounding codebase |
| `s` | Syntax | **s**yntax | Language-level mechanics, idioms, conventions, and whether the edit reflects them |
| `t` | Thinking | **t**hinking | DE-level design reasoning, systems thinking, concurrency, hardware considerations |
| `a` | Assessment | **a**ssessment | Optimality verdict: is this change optimal, maintainable, conventional, efficient? |
| `e` | Explain (all) | **e**xplain | Equivalent to `r` + `s` + `t` + `a` combined |
| `h` | Help | **h**elp | Reprints the first-footer legend (key descriptions and usage hints) |

Keyboard ergonomics: `r`, `s`, `t`, `a`, `e` sit in a tight left-hand cluster on QWERTY layouts.

#### Depth counter

Each axis maintains a depth counter scoped to the current pause point:

- Starts at 0 (no explanation requested yet)
- Any key press increments its axis's counter by 1
- Combinations (e.g., `rt`, `sa`) increment all included axes by 1
- `e` increments all four axes by 1
- All counters reset when the user advances with `.`

#### Combination mechanics

- Keys can be combined in any order in a single prompt (e.g., `rt`, `tr`, `sa`, `rsta`)
- `rsta` = `e` (incrementing all four is equivalent to explain-all)

## Phase 1: *planning*

Before editing anything:

1. Carefully ensure any outstanding ambiguities/tradeoffs/design choices in the implementation are **unambiguously resolved** through dialogue with the user.
2. Construct a **DAG of *micro edits***:

    - Each node is a *micro edit* (see node specification in the reference below)
    - Each edge is a *blocking dependency* (encoded in each node's `deps` field)

    You must execute nodes in **topological order**, never violating dependencies.

> [!IMPORTANT]
> Before proceeding, read `references/phase-1.md` for the node specification, status update protocol, DAG persistence protocol, and scheduling protocol.

## Phase 2: *execution*

> [!IMPORTANT]
> Before proceeding, read `references/phase-2.md` for the execution loop, step header/footer templates, end-of-phase verification, DAG change protocol, course-correction protocol, and flaw detection protocol.
>
> When an [*explain key*](#explain-keys) is pressed for the first time in a session, read `references/explain-keys.md` for the axis directives and cross-axis quality standards.

Execute the DAG by running the mandatory execution loop until every node is marked `done`.

## Compatibility with other Bureau-configured workflows

### Superpowers skills *(Claude Code & Codex)*

Micro Mode is **compatible** with Superpowers skills:

- **TDD skill**: Each test-first step and implementation step becomes a micro edit. The TDD cycle (Red → Green → Refactor) maps to the DAG naturally.
- **Systematic debugging**: Investigation steps remain conversational; only actual code fixes become micro edits.
- **Code review**: Review findings can inform DAG construction; fixes are micro edits.

### Handoff guidelines

Micro Mode operates **within** a single agent session. If you need to delegate:

1. **Pause** micro mode (persist DAG)
2. **Delegate** via `Task` tool or headless CLI invocation
3. **Resume** micro mode after delegation completes

Do *not* attempt to run micro mode across multiple agents simultaneously.
