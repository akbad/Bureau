# Phase 2 reference

## Mandatory execution loop

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
    - Otherwise (i.e., by default), select the next **`status=ready`** DAG node (i.e. whose `deps` are now empty) according to the scheduling protocol and set that node's `status` to `in_progress`.

3. Run **stale state detection:**

    1. **Re-read the target function's current contents** (always!).

        - If the user modified it since last read (or compared to what you were expecting), acknowledge and adapt: investigate as thoroughly as needed, think about and formulate the new changes needed (remaining mindful of the [DAG change protocol](#dag-change-protocol))

    2. Summarize the target function/code to the user in the following format:

        > Note each of the bullets below can have up to 3 sub-bullets as necessary to ensure information is easy to read and parse for the user.

        ```md
        - <state the inputs/outputs if within a function, surrounding context if not>
        - <the function/code's current behavior (and invariants, if any)>
        ```

    3. ***Only if* the `goal` and `diff` were updated:**

        - Output to the user:

            ```md
            ATTENTION: goal and diff for this change were updated due to changes to the ground truth; see below.
            ```

        - *Don't* print the goal and diff here; you'll do that in the next step, in the *step header*.
        - Ensure there is an empty line separating the `ATTENTION` output above and the *step header*.

4. Emit the *step header* in the *exact* format below (as Markdown/GitHub-flavoured Markdown):

    ```md
    - **Step `<id>`:** `<file>::<function>`
    - **Signature:** `<exact function signature, as currently in file>`
    - **Type:** **<API|IMPL|FIX|TEST|DOC>**
    - **Risk:** **<low|medium|high>**
    ```

5. Apply the *micro edit* based on the node's diff
6. Update the DAG node accordingly

    > Make sure not to forget the status update and DAG storage protocols as appropriate.

7. Emit the *appropriate step/explanation footer* from the variants below in the *exact* format given (as Markdown/GitHub-flavoured Markdown):

    > Note the `check` bullet is only required if there actually *is* a command we could use to verify this particular step's changes were correct.

    - For the **first step footer in the session**, use this expanded format:

        ```md
        - **Changed:** `<file>::<function>` (±<N> lines, starting at line <i> in the updated file)
        - **Goal:** <one sentence>
        - **Why now:** <deps satisfied>
        - **Summary:** <summary of the changes, 6 bullet points maximum>
        - **Check:** `<command>` → `<result>`
        - **Next candidates:** `<ready step ids>`

        ──────────────────────────────────────────────────────────────────────────────
        To choose the next action, send a prompt or use any of these shortcuts:

        - Continue to the next edit: press .

        - Explore this edit and/or ask for explanations by pressing:

            r │ repo/architecture context
            s │ syntax/idioms breakdown
            t │ design thinking/reasoning
            a │ optimality assessment
            e │ all of the above

            - Combine keys (e.g., "rt") to blend multiple aspects in one explanation.
            - "e" produces an explanation covering all these aspects.
            - Re-use these keys as follow-up prompts after explanations to go deeper.

        - See the plan overview: press ?
        ──────────────────────────────────────────────────────────────────────────────
        ```

        > Note that if `h` (or `help`) is pressed at any time, the `To choose the next action` section above (i.e. including and delimited by the `─` lines) should be re-shown to the user.

    - For **all subsequent step footers**, use this compact format:

        ```md
        - **Changed:** `<file>::<function>` (±<N> lines, starting at line <i> in the updated file)
        - **Goal:** <one sentence>
        - **Why now:** <deps satisfied>
        - **Summary:** <summary of the changes, 6 bullet points maximum>
        - **Check:** `<command>` → `<result>`
        - **Next candidates:** `<ready step ids>`

        ──────────────────────────
        Next action: shortcut keys
        ──────────┬───────────────
        *next edit* │ .
        *explore*   │ r s t a e
        *view plan* │ ?
        *help/info* │ h
        ──────────┴───────────────
        ```

    - **After any explanation/deep dive** (whether triggered via the explain keys or a custom prompt), output this *explanation footer*:

        ```md
        ──────────────────────────
        **Still at step `<id>`.**

        Next action: shortcut keys
        ──────────┬───────────────
        *next edit* │ .
        *explore*   │ r s t a e
        *view plan* │ ?
        *help/info* │ h
        ──────────┴───────────────
        ```


8. Output `⏸️` and  **STOP**: do not write the next step's header, do not read the next file, do not begin any further work. Your message **must** end within 1-2 lines after the ⏸️ symbol.

    > **Waiting for a resumption token is NOT optional.**
    >
    > If you find yourself writing a second edit in the same response, you are violating micro mode: stop, delete everything after the first `⏸️`, and end your response.

9. Upon receipt of a resumption token, restart this loop at step 1.

## End-of-phase verification

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
> The user may, of course, run checks manually between any two steps. If they report a failure, the [course-correction protocol](#course-correction-protocol) applies.

## Phase 2 protocols

> [!IMPORTANT]
>
> The following protocols are applicable **at all times while in phase 2.**

### DAG change protocol

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
>     - change the node's `status` as one of `ready|planned|blocked`
>
>         - if set to `blocked` (i.e. due to a newly-surfaced tradeoff/choice), add notes for this to `tradeoffs`
>
>     - update `diff` and `goal` to contain the remaining changes needed
>
> 2. ***Only if* `status` was set to `blocked`**:
>
>     - Present the design choice/tradeoff to the user and ask for unambiguous clarification
>     - Return to step 1 (i.e. of the steps in this callout) and make sure to clear the `tradeoffs` field after recording the chosen solution/change
>
> 3. Briefly note that the current task must be left unfinished, citing:
>
>     - the task's ID
>     - the remaining changes needed

### Course-correction protocol

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
3. Wait for a resumption token before proceeding

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
> 4. resume the execution loop
>
> **Never** defend the rejected implementation.

