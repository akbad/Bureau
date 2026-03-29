---
name: micro-mode
description: Step-gated editing with DAG-based planning and continuous user steering. Activate when user says "MICRO MODE ON", "implement in micro mode", or wants maximum control over each atomic edit with pause points after every change. Each edit is limited to one function and 30 lines. User resumes with ">" or ".". Ideal for careful refactoring, high-risk changes, or when user wants to review every modification before proceeding.
---

# Micro Mode editing protocol

> <ins>***Goal:** step-gated edits in auto-accept mode*</ins>
>
> *Maximum throughput with continuous, real-time user steering. You will make exactly **one atomic "micro edit"** at a time, then pause. The user can course-correct immediately; you must rebase on the user's edits before continuing.*

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed **exactly as they are specified**.

## Entry/exit protocols

### Activation/deactivation

When the user says anything like:

- "MICRO MODE ON"
- complete this task in micro mode
- implement in micro mode

*follow this Micro Mode protocol* until you are told anything like:

- exit micro mode
- finish the task/implementation without micro mode
- "MICRO MODE OFF"

If you are unsure, confirm unambiguously with the user.

Upon exit, you must output in this exact format:

```
═══════════════════════════════════════
Micro Mode OFF
Completed: N/M steps
Remaining: [step-ids, or "none"]
DAG stored: [location, or "chat only"]
═══════════════════════════════════════
```

If there are no steps/nodes remaining and the DAG is persisted to a memory tool (Neo4j-based graph memory or Qdrant), delete the DAG from memory.

### Partial completion (pausing for later)

If the user says anything like:

- "pause for now"
- "stop here"
- "let's continue later"
- "save progress"

You must:

1. **Persist the DAG** to memory (see [DAG persistence protocol](#dag-persistence-protocol)) and ensure it is updated to reflect current progress
2. **Emit pause summary**:

    ```
    ⏸️ Micro Mode PAUSED
    Completed: N/M steps
    Next ready: [step-ids]
    Blocked: [step-ids, or "none"]
    DAG stored: [location]
    Resume: "MICRO MODE ON, continue"
    ```

3. Exit micro mode protocol (but do **not** emit deactivation summary: this is a pause, not an exit)

## Domain-specific terms

### *Micro edits*

One micro edit may modify **at most**:

- **one function** (primary target)
- **≤30 total lines changed** *(added + removed)*

> [!NOTE]
> - **Line counting**: Count gross changes. Replacing 5 lines with 3 new lines = 8 changes (5 removed + 3 added).
> - **Multi-file exception**: A function rename (definition + call-site updates) counts as *one* micro edit if call-site changes are mechanical and total <10 additional lines.

If a change exceeds these limits, you *must* split it into multiple micro edits, in this preferred order:

1. interface / signature / scaffolding
2. core logic
3. edge cases
4. tests
5. cleanup or refactor

### *Resumption tokens*

> These enable a fast control loop.

The user resumes execution (in phase 2 below) by sending **one character**:

- `>` (preferred)
- `.` (equivalent)

Alternatives like "continue", "proceed", "go on" or "next edit" are also permitted for flexibility.

> [!NOTE]
> Explain keys (`r`, `s`, `t`, `a`, `e`) are **not** resumption tokens. They produce explanations at the current pause point without advancing the DAG. See [Explain keys](#explain-keys) below.

### *Explain keys*

> These enable on-demand, distinguished-engineer-level explanations of any micro edit, without advancing the DAG.

Five single-character keys, available at every pause point alongside the existing resumption tokens:

| Key | Axis | Mnemonic | Focus |
|-----|------|----------|-------|
| `r` | Repo | **r**epo | Architectural context, design decisions, how this change fits the surrounding codebase |
| `s` | Syntax | **s**yntax | Language-level mechanics, idioms, conventions — whether the edit reflects them and why/why not |
| `t` | Thinking | **t**hinking | DE-level design reasoning, systems thinking, concurrency, hardware considerations |
| `a` | Assessment | **a**ssessment | Optimality verdict — is this change optimal, maintainable, conventional, efficient? |
| `e` | Explain (all) | **e**xplain | Equivalent to `r` + `s` + `t` + `a` combined |

Keyboard ergonomics: all five keys sit in a tight left-hand cluster on QWERTY layouts, enabling fast one-handed input.

#### Depth counter

Each axis maintains a depth counter scoped to the current pause point:

- Starts at 0 (no explanation requested yet)
- Any key press increments its axis's counter by 1
- Combinations (e.g., `rt`, `sa`) increment all included axes by 1
- `e` increments all four axes by 1
- All counters reset when the user advances with `>` / `.`

#### Combination mechanics

- Keys can be combined in any order in a single prompt (e.g., `rt`, `tr`, `sa`, `rsta`)
- Order within a combination does not matter (`rt` = `tr`)
- `rsta` = `e` (incrementing all four is equivalent to the explain-all key)

#### Relationship to the pause point

- Explain keys do **not** consume the pause — after receiving the explanation, the user is still at the same pause point and must still use a [resumption token](#resumption-tokens) (`>` / `.`) to advance
- The user can issue as many explain keys as they want before advancing
- Explain keys are explicitly **not** resumption tokens

## Phase 1: planning

Before editing anything: 

1. Carefully ensure any outstanding ambiguities/tradeoffs/design choices in the implementation are **unambiguously resolved** through dialogue with the user.
2. Construct a **DAG of *micro edits***:

    - Each [node](#node-specification) is a *micro edit*
    - Each edge is a *blocking dependency* (encoded in each node's `deps` field, which contains a list of in-neighbours; see the spec below)

    You must execute nodes in **topological order**, never violating dependencies.

### Node specification

Each node must include:

- `id` *(string, unique)*: **stable**, human-addressable (e.g. `parse_headers`, `validate_cfg`)

    > Stable IDs allow the user to give *unambiguous* instructions like:
    >
    > - "redo `validate_cfg`"
    > - "skip `parse_headers`"
    > - "run high-risk steps first"

- `file` *(string)*
- `function` *(string)*
- `signature` *(string)*: signature of the function above
- `goal` *(string)*: intent/goal/nature of the change, in one sentence
- `diff` *(string)*: a concrete diff containing the exact changes needed; updated during phase 2 execution if stale state detection reveals the ground truth has changed (see stale state detection in [phase 2's execution loop](#mandatory-execution-loop))

- `deps` *(list of 0 or more `id`s)*: list of IDs of nodes corresponding to steps that block/must be completed before this one
- `risk` *(string enum)*: *exactly one* of `low | medium | high`

    - `risk: high` *micro edits*, in particular, are defined as those touching:

        - APIs / interfaces
        - types or schemas
        - concurrency / ordering
        - serialization formats
        - invariants relied on downstream

- `type` *(string enum)*: *exactly one* of `API | IMPL | FIX | TEST | DOC`
- `status` *(string enum)*: *exactly one* of `planned|ready|in_progress|done|blocked|cancelled`

    - All nodes should have `status` set as one of the following at DAG creation:

        | Value of node's `deps` list | Resulting `status` value to set |
        | --- | --- |
        | Empty | `ready` |
        | Non-empty | `planned` |

    - Status values are defined as follows:

        | `status` value | Definition |
        | --- | --- |
        | `ready` | Node's `deps` list (i.e. blocking micro edits) is *empty* |
        | `planned` | Node's `deps` list is *non-empty* |
        | `blocked` | Waiting on clarification or external decision as to how or whether to implement the node's *micro edit* |
        | `done` | Node's *micro edit* was successfully applied and accepted |
        | `in_progress` | Currently working on node's *micro edit* |
        | `cancelled` | Node's changes are no longer needed; equivalent to `WONTFIX` in Jira tickets/GitHub issues |

- `tradeoffs` *(string)*: contains extra notes about the node/change when the node is `status=blocked`; should be empty to begin with

### Cross-phase protocols

> [!IMPORTANT]
> These protocols must be followed **at all times *as soon as* the DAG is created**: from phase 1, all the way through to the very end of phase 2 (i.e., completion of the implementation/changeset represented by the DAG).

#### Status update protocol

> [!IMPORTANT]
>
> - Any time you set a node's `status` field to `cancelled` or `done` from any other status value, you **must** ensure that node is removed from any other nodes' `deps` lists in which it appears.
>
>     - The converse also applies: whenever a node's `status` field is changed from `cancelled` or `done` from any status value, you **must** carefully ensure the node is added to any other node's `deps` list that depends on it.
>
> - Any time you change a node's `status` from `blocked` to any other value (i.e., since the blocking issue was resolved via resolution/clarification from the user) ensure the `tradeoffs` field's value is cleared (if non-empty).

#### DAG persistence protocol

Maintain the DAG explicitly in any structural memory tools available (or, as a last resort, in chat) and update it if needed/as appropriate after every prompt.

> [!IMPORTANT]
> 
> **No implicit dependencies allowed**: dependencies between nodes must be **explicitly encoded** in the DAG.

> [!TIP]
>
> The `deps` list does NOT need to be explicitly maintained as a list/array of node IDs; in particular, if the storage tool/mechanism (e.g. a memory storage MCP) natively supports graph (ideally, digraph) or similar operations, `deps` can and should be recorded as edges (ideally, directed edges/arcs). 
>
> Optimize for efficiency and native support (by the tool) of the DAG's representation in storage (while maintaining its completeness, of course).

#### Scheduling protocol

> *To surface design errors **before** building on top of them.*

When multiple steps are ready (deps satisfied), prefer executing based on the following heuristics in the hierarchy given (unless explicitly told otherwise, or there is a clear reason not to):

1. **steps with higher `risk` earlier**
2. nodes prioritized by `type` in this order ***(where `deps` allow)***:

  **`API → IMPL → FIX → TEST → DOC`**

## Phase 2: execution

### Mandatory execution loop

This loop runs until every node in the DAG is marked `done`.

> [!IMPORTANT]
>
> At any point in the execution of the loop below before the planned implementation/task at hand is complete, if the user gives a prompt explicitly outside of this loop's prescribed steps (e.g. asking a question about the code), you must **ensure the DAG is updated to reflect the current progress state before continuing**.

Until the planned implementation/task is complete, execute the steps below, in the order given and in a loop:

1. If there is currently a node with `status=in_progress`: 
    
    - if the node's changes have (ostensibly very recently) been completed (with or without changes from the user, set that node's `status=done`)
    - else, set the node's status to `ready|planned|blocked|cancelled` as appropriate; seek clarification if unsure

2. Determine the next node to process:

    - If the user requested a certain step/node to be implemented, select that one (even if it's not the next in the topological ordering)
    - Otherwise (i.e., by default), select the next **`status=ready`** DAG node (i.e. whose `deps` are now empty) according to the [scheduling protocol above](#scheduling-protocol) and set that node's `status` to `in_progress`.

3. Run **stale state detection:**
    
    1. **Re-read the target function's current contents** (always!).

        - If the user modified it since last read (or compared to what you were expecting), acknowledge and adapt: investigate as thoroughly as needed, think about and formulate the new changes needed (remaining mindful of the [DAG change protocol](#dag-change-protocol))

    2. Summarize the target function/code to the user in the following format:

        > Note each of the bullets below can have up to 3 sub-bullets as necessary to ensure information is easy to read and parse for the user.

        ```md
        - <state the inputs/outputs if within a function, surrounding context if not>
        - <the function/code's current behavior (and invariants, if any)>
        ```

    3. ***Only if* the `goal` and `diff` were updated:** \

        - Output to the user:

            ```md
            ATTENTION: goal and diff for this change were updated due to changes to the ground truth; see below.
            ```

        - *Don't* print the goal and diff here; you'll do that in the next step, in the *step header*. 
        - Ensure there is an empty line separating the `ATTENTION` output above and the *step header*.
        
4. Emit the *step header* in the *exact* format below:

    ```md
    - Step <id>: <file>::<function>
    - Signature: <exact function signature, as currently in file>
    - Type: <API|IMPL|FIX|TEST|DOC>
    - Risk: <low|medium|high>
    
    <diff of changes>

    - Goal: <one sentence>
    - Why now: <deps satisfied>
    - Summary: <summary of the changes, 6 bullet points maximum>
    ```

5. Apply the *micro edit* based on the node's diff
6. Update the DAG node accordingly 

    > Make sure not to forget the [status update](#status-update-protocol) and [DAG storage](#dag-persistence-protocol) protocols as appropriate.

7. Emit the *step footer* in the *exact* format below:

    > Note the `check` bullet is only required if there actually *is* a command we could use to verify this particular step's changes were correct.

    ```md
    - Changed: <file>::<function> (±<N> lines, starting at line <i> in the updated file)
    - Exact diff:

        <output diff of the changes you made here>

    - Check: <command> → <result>
    - Next candidates: <ready step ids>
    
    Press ">" or "." to continue, or explore with: r · s · t · a · e
    ```

8. Output `⏸️` and  **STOP**: do not write the next step's header, do not read the next file, do not begin any further work. Your message **must** end within 1-2 lines after the ⏸️ symbol.

    > **Waiting for a [resumption token](#resumption-tokens) is NOT optional.** 
    > 
    > If you find yourself writing a second edit in the same response, you are violating micro mode: stop, delete everything after the first `⏸️`, and end your response.

9. Upon receipt of a [resumption token](#resumption-tokens), restart this loop at step 1.

### End-of-phase verification

After all DAG nodes are marked `done`:

1. Collect every distinct `Check` command from the step footers emitted during the loop
2. Run each one and record the result
3. If all pass: report success and proceed to exit/wrap-up
4. If any fail: present the failures to the user and ask how to proceed:

    - **Fix in micro mode** → plan new `FIX` nodes for each failure, re-enter the execution loop
    - **Fix outside micro mode** → exit micro mode, address failures conversationally
    - **Ignore** → user accepts the current state as-is

> [!NOTE]
>
> The `Check` line in each step footer is **informational during the loop**: it documents what *would* verify that step, but the agent does not run it mid-loop. Verification is batched here to preserve the fast edit cadence.
>
> The user may, of course, run checks manually between any two steps. If they report a failure, the [course-correction protocol](#course-correction-protocol-contingent-on-user-input) applies.

### Explain keys: axis directives

> [!IMPORTANT]
>
> These directives define the **purpose, voice, and depth-progression behavior** of each [explain key](#explain-keys) axis. They are non-negotiable quality standards.

| Axis | Directive |
|------|-----------|
| `r` — **Repo** | Explain the change in the context of the surrounding codebase. Where does this code sit in the architecture? What modules, types, or contracts does it interact with? What design decisions in the repo led to this code looking the way it does — and how does the micro edit honor, extend, or intentionally break those decisions?<br/><br/>*Depth progression:* Each deeper pass should widen the aperture: from the immediate function, to the module, to cross-module interactions, to system-level architectural patterns — revealing context that the previous pass took for granted. |
| `s` — **Syntax** | Break down the language-level mechanics of the change. What constructs, idioms, and conventions does it use — and are they the right ones? If the edit is idiomatic for the language, say so and explain what makes it idiomatic. If it departs from convention, explain why the departure is justified (or flag it if it isn't). Cover type signatures, control flow, error handling patterns, and any language-specific subtleties (ownership, lifetimes, goroutine semantics, decorator behavior, etc.) that a reader unfamiliar with this language's idioms would miss.<br/><br/>*Depth progression:* Each deeper pass should become more granular and more foundational: from "what this construct does in context" down to "why this language feature exists and what it compiles/evaluates to." |
| `t` — **Thinking** | Explain the design reasoning behind the change the way a veteran distinguished engineer would explain it to a peer — not dumbed down, not padded. State the tradeoff that was made, name the alternatives that were not chosen, and explain why this path wins. If systems-level concerns are relevant — concurrency, memory layout, cache behavior, ordering guarantees, failure modes, hardware constraints — they are mandatory, not optional color. This is the axis where "it works" is insufficient; the explanation must address whether it works *for the right reasons* and *under adversarial conditions*.<br/><br/>*Depth progression:* Each deeper pass should surface reasoning and constraints that the previous pass took for granted — peeling back assumptions until you reach first principles. |
| `a` — **Assessment** | Deliver a frank verdict on the change's optimality, maintainability, conventionality, and efficiency. Would a distinguished engineer reviewing this change in critical detail and with an eye on the big picture approve it without comment, request modifications, or reject it? Be specific: if optimal, state what makes it so and what would have to change in requirements for it to stop being optimal. If not optimal, name the concrete improvement — not a vague gesture at "could be better," but the specific alternative and why it wins.<br/><br/>*Depth progression:* Each deeper pass should tighten the lens: from the overall verdict, to specific dimensions (performance, readability, maintainability, robustness), to quantitative or formal reasoning where applicable. |
| `e` — **Explain (all)** | Equivalent to `r` + `s` + `t` + `a`. Produce a unified explanation that weaves all four axes together where they naturally intersect, rather than presenting four siloed sections. The axes should reinforce each other: architectural context should inform the assessment, syntax should support the design reasoning, and the verdict should be grounded in all three. |

#### Cross-axis directive

> Applies to **all** axes, at **all** depths, for **all** combinations.

**Quality bar:** Produce an explanation that would thoroughly pass a veteran distinguished engineer's discerning bullshit radar. No filler. No hedge words used to avoid committing to a position. No "generally speaking" or "it depends" without immediately specifying what it depends *on*. Every sentence must advance the reader's understanding or it does not belong.

**Depth progression:** Each subsequent explanation at a given depth must reveal information not present in any previous explanation at this pause point. Never restate what the step header or step footer already communicated. Never restate what a previous explanation at this pause point already covered — build on it.

**Weaving:** When multiple axes are requested together (via combination keys or `e`), weave them into a cohesive explanation rather than emitting labeled sections. The axes are lenses on the same change, not independent reports.

### Phase 2 protocols

> [!IMPORTANT]
>
> The following protocols are applicable **at all times while in phase 2.**

#### DAG change protocol

If, for any reason, you must:

- roll back in the execution sequence (i.e., the topological ordering) by one or more nodes
- edit/add new nodes (i.e. due to changes in implementation and/or approach)

You must:

1. Carefully think through the resulting updates to the DAG that are necessary

    > Note that **multiple (and potentially many) DAG changes may be needed,** including **new and/or updated nodes _and_ edges**.
    >
    > This is because node additions and/or changes may cause the need for changes/adjustments to ripple through to the rest of the implementation (and hence the rest of the DAG nodes/edges).

> [!IMPORTANT]
>
> If and when planning changes and additions to the implementation/solution represented by the DAG, there may (and often will) be design decisions/tradeoffs that are substantial enough to require user input. 
>
> For all nodes whose implementation is subject to a design tradeoff/choice:
>   
> 1. Encode the implementation/choice (in the `diff` and `goal` fields) that maximizes the objective function `(2/3 * optimality + 1/3 * likeliness to be approved by the user)` 
> 2. Set the node's:
>   
>   - `status` field to `blocked`
>   - `tradeoffs` field to contain a detailed but concise description of the tradeoff/choice to be made/resolved

2. Update the DAG based on the results of step 1, ensuring `deps` and `status` fields are carefully set

3. **Log the update to the user** based on the following template

    ```md
    *** DAG CHANGED ***

    - What triggered the change: <summarize in 1-2 sentences>
    - Changes made to DAG: <summarize in 1-2 sentences OR 1-4 sub-bullet points each containing 1 sentence; make sure these cover both any concrete implementation changes AND changes made to the DAG>
    ```

4. If there were any implementation changes made **that haven't been discussed with the user yet** (i.e. because you were asked to come up with them independently/agentically), output a final bullet point (as part of the output from step 3) explaining why these changes are needed and optimal:

    ```md
    - Why the new implementation is necessary AND optimal: <describe in 1-2 sentences OR 1-4 sub-bullet points each containing 1 sentence>
    ```

5. **Only if there are any nodes whose `status` is `blocked`**:

    1. Respond with a numbered list of questions (e.g. via the `AskUserQuestion` tool or equivalent) seeking unambiguous clarification/resolution of each design choice/tradeoff, with each question preceded by a description of the design choice/tradeoff at hand based on (but not a direct reprint of) the node's `tradeoffs` field.
    2. Once clarifications/resolutions have been received, restart at step 1 of this DAG change protocol.

> [!IMPORTANT]
>
> If any task (i.e., corresponding to an in-progress node that was interrupted) must be left unfinished due to step 4 above:
> 
> 1. Ensure the DAG is updated (if not already) to:
>   
>   - change the node's `status` as one of `ready|planned|blocked`
>       
>       - if set to `blocked` (i.e. due to a newly-surfaced tradeoff/choice), add notes for this to `tradeoffs`
>
>   - update `diff` and `goal` to contain the remaining changes needed
>
> 2. ***Only if* `status` was set to `blocked`**:
> 
>     - Present the design choice/tradeoff to the user and ask for unambiguous clarification
>     - Return to step 1 (i.e. of the steps in this callout) and make sure to clear the `tradeoffs` field after recording the chosen solution/change
>
> 3. Briefly note that the current task must be left unfinished, citing:
>
>   - the task's ID
>   - the remaining changes needed

#### Course-correction protocol (contingent on user input)

If the user does *any* of the following:

- edits your code manually
- says anything like:

    - "I tweaked it"
    - "I changed it"
    - "I fixed your code"
    - "Read my version"
    - "Take a look at my edits"
    - "Rebase on my edits"

You **must**:

1. Re-open and re-read the affected file(s)
    
    > **Never** assume previous patch state.

2. Briefly confirm you are now using the current contents
3. Wait for one of the [*resumption tokens* listed above](#resumption-tokens) before proceeding

> [!IMPORTANT]
>
> #### <ins>*Revert-by-default* rule</ins> (for auto-reverts & redos)
> 
> If the user says anything like:
> 
> - "no"
> - "wrong direction"
> - "redo"
> - "undo that"
> - or manually reverts your change
> 
> You **must:**
>
> 1. revert the change if asked to (or if the user manually reverted, treat the new working tree as authoritative)
> 2. assume the step you just performed is invalid and seek unambiguous clarification as to the correct way to proceed
> 3. update the DAG as needed
>   
>     - in particular, ensure the current `status=in_progress` node has its status set to `cancelled|ready|planned` as appropriate
>     - if the node's status becomes `cancelled`, remove it from all other nodes' `deps` lists in which it appears
>
> 4. resume the [execution loop](#mandatory-execution-loop) 
>  
> **Never** defend the rejected implementation.

#### Flaw detection protocol (explain keys)

> Applies when the agent discovers a flaw or improvement opportunity while formulating an [explain key](#explain-keys) response.

##### When it triggers

During the process of formulating an explanation along any axis, the agent may identify:

- A flaw in the current micro edit (correctness, efficiency, idiom violation, missed edge case)
- A possible improvement to the current micro edit
- An issue with the broader plan (a downstream node's approach is suboptimal given what this explanation revealed, or a missing node that should exist)

##### How it presents

The explanation is emitted first, cleanly and completely. Then, **separated by a clear visual break**, the flaw/improvement is presented in a distinct block:

```md
───────────────────────────────────
⚠️ Finding: <one-line summary>

- What: <description of the flaw or improvement>
- Impact: <what breaks, degrades, or is left on the table>
- Suggested fix: <concrete alternative — not a vague gesture>
- Scope: <"this edit" | "DAG node <id>" | "new node needed">

Options:
  (1) Apply fix → [describe what changes]
  (2) Dismiss → continue with current edit as-is
───────────────────────────────────
```

Multiple findings are presented as separate blocks, each with its own options.

##### Resolution

- If the user picks **(1)**: the fix flows into the existing [DAG change protocol](#dag-change-protocol) — the agent updates the DAG, logs the change to the user per that protocol's format, and the user remains at the same pause point
- If the user picks **(2)**: nothing changes — the user can advance with `>` / `.` or continue exploring with more explain keys

Flaw detection does not create a parallel change-tracking mechanism. It is a *discovery* mechanism; the [DAG change protocol](#dag-change-protocol) is the *execution* mechanism.

## Compatibility with other Bureau-configured workflows

### Superpowers skills *(Claude Code & Codex)*

Micro Mode is **compatible** with Superpowers skills:

- **TDD skill**: Each test-first step and implementation step becomes a micro edit. The TDD cycle (Red → Green → Refactor) maps to the DAG naturally.
- **Systematic debugging**: Investigation steps remain conversational; only actual code fixes become micro edits.
- **Code review**: Review findings can inform DAG construction; fixes are micro edits.

### Handoff guidelines

Micro Mode operates **within** a single agent session. If you need to delegate:

1. **Pause** micro mode (persist DAG)
2. **Delegate** via `clink` or `Task` tool
3. **Resume** micro mode after delegation completes

Do not attempt to run micro mode across multiple agents simultaneously.
