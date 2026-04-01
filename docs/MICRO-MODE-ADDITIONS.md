# Micro mode additions

> Proposed additions to the micro mode editing protocol, extending the core step-gated editing loop with ergonomic, learning, and systems-level features.
>
> Each addition is **independently adoptable** and designed to compose with the existing protocol (DAG, pause points, explain keys, flaw detection) without modifying its core mechanics.

***Contents:***

- [Batch approval](#batch-approval)
- [Pattern atlas](#pattern-atlas)
- [DAG status command](#dag-status-command)
- [Decision ledger](#decision-ledger)
- [Atomic undo stack](#atomic-undo-stack)
- [Hot-path performance tags](#hot-path-performance-tags)
- [Insight carry-forward](#insight-carry-forward)
- [DAG checkpoints](#dag-checkpoints)
- [Sketch nodes and node groups](#sketch-nodes-and-node-groups)

## Batch approval

> *Run multiple low-risk steps without pausing between each one.*

- Introduces **batch resumption commands** alongside the existing single-step tokens (`>` / `.`)

    - `>> N` — run the next N ready steps without pausing
    - `>> low` — run all currently-ready nodes whose `risk` is `low`
    - `>> all` — run every remaining ready node

- Each step in a batch still executes the **full mandatory execution loop** internally (stale state detection, diff application, DAG update)

    - The scheduling protocol still governs ordering within a batch

- Step headers/footers within a batch are **compressed to one line each**:

    ```
    id | file::function | risk | type | ±N lines | check
    ```

- After the batch completes, the agent emits a **consolidated footer** listing every step that was applied, then pauses normally

### Halt conditions

A batch **halts immediately** (mid-batch, not at the end) if any of the following occur:

- A step triggers the **DAG change protocol** (e.g., stale state requires replanning)
- A node is `blocked` (waiting on user clarification)
- A step's diff **cannot be applied cleanly** (file state diverged unexpectedly)
- A **sketch node** whose deps are all satisfied is encountered — the batch halts and prompts the user to resolve, skip, or cancel (see [sketch nodes](#sketch-nodes))

When a batch halts, the agent reports:

- Which steps completed successfully
- Which step caused the halt and why
- The current DAG state (equivalent to the `?` status command)

### Interaction with other features

- **Explain keys** are unavailable mid-batch (the agent does not pause between steps)

    - After the batch finishes, the user can request explain-key review on any completed step by referencing its `id` (e.g., `e parse_headers` or `t validate_cfg`)

- **Undo** (`u`) can revert any or all steps from a completed batch

- **Conditional execution** (if adopted later) composes naturally: `>> low if check` would mean "batch all low-risk ready steps, but only if the previous check passed"

### When to use

- Clusters of **mechanical, low-risk** nodes (call-site updates after a rename, docstring additions, import reordering)
- `DOC` and `TEST` nodes that are formulaic
- Any situation where per-step pausing adds friction without adding safety

### When *not* to use

- `risk: high` or `risk: medium` nodes — these deserve individual review
- Nodes touching concurrency, APIs, or type signatures
- When the user is actively learning from each step (use single-step mode or Socratic checkpoints instead)

## Pattern atlas

> *Tag each edit with the distributed systems or software engineering pattern it instantiates.*

- Each DAG node gains an optional `pattern` field *(string)*

    - Set during phase 1 planning when the pattern is known upfront
    - Populated during phase 2 execution when the agent recognizes the pattern while formulating the diff

- When non-empty, a new line appears in the **step header** between `Risk` and the diff:

    ```
    Pattern: <name> (<one-line definition>)
    ```

- When the edit only **partially implements** a pattern, the annotation explains what remains

- When the edit **departs from** a canonical pattern, the annotation explains why

### Examples of patterns the agent should recognize

- **Distributed systems:** check-then-act, optimistic locking, two-phase commit, saga, outbox, CRDT merge, protocol step narration, quorum intersection, lease-based locking, crashing recovery, idempotency key
- **Concurrency:** monitor pattern, producer-consumer, fan-out/fan-in, double-checked locking, compare-and-swap loop, work-stealing
- **General:** builder, strategy, template method, circuit breaker, bulkhead, backpressure, retry with exponential backoff

### Interaction with explain keys

- The `t` (thinking) axis at depth 1+ should **elaborate on the tagged pattern**

    - Its formal properties
    - Where it appears in well-known production systems
    - Known failure modes and edge cases

- The `r` (repo) axis can **reference other places** in the same codebase where the same pattern appears

### Quality standard

- The agent should **only emit a pattern tag** when the match is strong and defensible

    - Prefer omission over a stretch
    - The `a` (assessment) axis provides the channel for the user to challenge a tag

## DAG status command

> *Instant situational awareness of the full DAG state via the `?` key.*

- A single-character key, usable at any pause point, that emits a **compact, topologically-sorted table** of all nodes

- Like explain keys, `?` does **not** consume the pause and does **not** advance the DAG

### Output format

The default view is a one-line-per-node table:

```
?  DAG Status (12/20 done)
───────────────────────────────────
 id              │ status      │ risk   │ type │ file::function
─────────────────┼─────────────┼────────┼──────┼──────────────────────
 parse_headers   │ done        │ high   │ API  │ src/http.rs::parse
 validate_cfg    │ done        │ medium │ IMPL │ src/config.rs::validate
 add_retry       │ in_progress │ high   │ IMPL │ src/client.rs::send
 update_tests    │ ready       │ low    │ TEST │ tests/client_test.rs::test_send
 fix_timeout     │ planned     │ medium │ FIX  │ src/client.rs::connect
 ...
───────────────────────────────────
```

### Variants

| Command | Behavior |
|---------|----------|
| `?` | Full DAG table (default) |
| `? <id>` | Full node spec for a specific node (including `diff`, `deps`, `tradeoffs`) |
| `? ready` | Filter to nodes with `status=ready` |
| `? blocked` | Filter to nodes with `status=blocked` |
| `? done` | Filter to completed nodes |

### Keyboard ergonomics

- `?` sits on the right hand, complementing the left-hand explain key cluster (`r`, `s`, `t`, `a`, `e`)
- Universally intuitive for "help/status"
- Composes with other navigation: inspect a node with `? <id>`, then decide whether to reorder, skip, or batch

## Decision ledger

> *Auto-build a structured design decision document as a byproduct of the editing session.*

- The agent maintains a **running ledger** of every non-trivial design choice made during planning (phase 1) and execution (phase 2)

- Each entry follows a lightweight ADR format:

    ```md
    ### DL-<N>: <decision title>

    - **Context:** <what prompted the decision>
    - **Options:** <2-3 alternatives, each 1 sentence>
    - **Chosen:** <which option and why>
    - **Constraints:** <what made alternatives inferior>
    - **Revisit if:** <condition under which this decision should be reconsidered>
    ```

### When entries are created

- During **phase 1 planning**: splitting strategy, node ordering rationale, risk assessments, architectural approach
- During **phase 2 execution**: DAG change protocol invocations, blocked-node resolutions, flaw detection findings
- The `tradeoffs` field on `blocked` nodes provides natural raw material for ledger entries

### When entries are *not* created

- Trivial decisions where no reasonable engineer would have chosen differently
- Mechanical choices with no alternatives (e.g., "renamed the function because the spec said to")

### Output and persistence

- At **exit or pause**, the agent emits the full ledger as a Markdown document

    - Inline in the exit/pause summary
    - Optionally persisted as a file (if the user requests it)

- The `t` (thinking) explain key axis can **reference ledger entries by ID** (e.g., "see DL-3 for why this approach was chosen over the saga pattern")

### Why this is useful

- Design thinking inside a micro mode session **evaporates** once the session ends
- A decision ledger accompanying a PR is a strong signal of engineering maturity — it shows the contributor understands *why*, not just *what*
- Practically **free to implement**: the raw material (tradeoffs, blocked resolutions, flaw detection findings) already exists in the protocol

## Atomic undo stack

> *Revert one or more completed steps with a single command.*

- Introduces the `u` key, usable at any pause point

    - `u` — undo the most recently completed step
    - `u N` — undo the last N steps in reverse-completion order

- Like explain keys and `?`, the `u` key does **not** consume the pause

### Mechanics

- Each undo **atomically reverts** the exact diff that was applied

    - The reverted node's status returns to `ready`
    - Downstream nodes whose `deps` included the undone node return to `planned`

- The agent emits a summary after the undo:

    ```
    Undone: <id> (file::function, ±N lines reverted)
    DAG updated: [downstream-ids] → planned
    ```

- The **status update protocol** already specifies the converse case (re-adding a node to `deps` when its status changes from `done`)

    - Undo leverages this existing rule rather than introducing new mechanics

### Conflict handling

- If the user manually edited the file between the original step and the undo, the reverse diff may not apply cleanly

- In this case, the agent:

    1. Reports the conflict
    2. Shows the original state and current state side by side
    3. Asks the user how to proceed (manual resolution, skip undo, or force revert)

### Relationship to revert-by-default

- The existing **revert-by-default rule** (triggered by "no", "undo that", etc.) becomes a special case of `u 1` triggered by user rejection

    - The rule's semantics are preserved; `u` generalizes it to multi-step rollback

### When to use

- A flaw becomes apparent **several steps after** the edit that introduced it
- The user wants to **try a different approach** from a known-good checkpoint
- A batch run (if adopted) produced an unexpected result and the user wants to rewind part of it

## Hot-path performance tags

> *Proactively flag edits on performance-critical code paths.*

- During DAG planning, the agent identifies nodes whose target function lies on a **hot path** and tags them with a `perf` annotation

### Node spec extension

The `perf` field is optional and contains:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `path_heat` | `hot \| warm \| cold` | How performance-critical the code path is |
| `call_frequency` | string | Expected invocation rate (e.g., "once per inbound RPC", "per token in decode loop") |
| `impact_note` | string | What the edit does to performance (e.g., "adds one heap allocation per call") |

### Step header integration

- For nodes with `path_heat: hot`, a prominent line appears at the top of the step header:

    ```
    PERF: hot path (<call_frequency>) — <impact_note>
    ```

- For `warm` paths, the line is present but less urgent in tone
- For `cold` paths (or when `perf` is absent), nothing is emitted

### Interaction with explain keys

- The `t` (thinking) axis, when invoked on a hot-path node, should include **quantitative reasoning**:

    - "This adds one allocation per call; at 100K calls/sec, that is ~100K mallocs/sec, which will pressure the GC"
    - "This lock acquisition widens the critical section by ~200ns per request"

### Classification heuristics

- The agent classifies a function as `hot` when there is clear evidence:

    - Loop body, handler callback, per-request dispatch, per-message processing, per-token inference path

- Default to `cold` unless evidence exists

    - The user can override the classification at any pause point

### When this matters most

- **Inference serving**: per-token latency at microsecond granularity
- **Stream processing**: per-message overhead determines throughput ceilings
- **Consensus protocols**: leader-path latency determines commit latency
- **Any tight inner loop**: allocation pressure, cache behavior, branch prediction

## Insight carry-forward

> *Distill transferable engineering lessons from each session and carry them forward to future sessions.*

- At the end of each micro mode session (or at pause), the agent distills **3-5 transferable insights**

    - Not project-specific facts, but **generalizable engineering lessons**
    - Each insight is tagged with the pattern, language, domain, and project it was learned in

- Insights are written to a **persistent, human-readable file** (not a black-box memory database)

### File format and location

- Insights accumulate in a single file: `~/.config/bureau/micro-mode-insights.md` [^1]

    [^1]: The path is configurable via `local.yml` or `.bureau.yml` if the user prefers a different location.

- The file is append-only (new insights are added at the bottom) and human-editable (the user can curate, rewrite, or delete entries at any time)

- Each insight entry follows this format:

    ```md
    ### MI-<short-hash>: <one-line insight>

    - **Learned from:** <project> / <file::function> (<date>)
    - **Domain:** <e.g., consensus, stream processing, inference serving>
    - **Language:** <e.g., Go, Rust, C++>
    - **Pattern:** <e.g., optimistic locking, retry with backoff> (if applicable)
    - **Detail:** <2-3 sentences explaining the insight, why it matters, and when to apply it>
    ```

### Surfacing in future sessions

- At the start of a micro mode session (during phase 1 planning), the agent reads the insights file and surfaces **relevant entries** as a "Prior insights" block:

    ```md
    Prior insights (from previous sessions):

    - [MI-a3f2] When implementing retry logic in Go, prefer context-based cancellation
      over bare timeouts (learned during etcd session, 2026-03-15)
    - [MI-7c1e] The check-then-act pattern in concurrent code requires holding the lock
      through the act phase, not just the check phase (learned during TiKV session, 2026-03-20)
    ```

- Relevance is determined by matching the current session's **domain, language, and detected patterns** against the insight metadata

### User control

- At session end, the agent presents distilled insights for **review before writing**

    - The user can edit, dismiss, or approve each one
    - Only approved insights are appended to the file

- The user can **dismiss** a stale or incorrect insight at any time:

    - During a session: `dismiss MI-<hash>` removes the entry from the file
    - Outside a session: directly edit the file

### Quality standard

- Insights must be **transferable** — useful outside the specific project they were learned in
- Insights must be **actionable** — "always do X when Y" or "never do X because Z", not vague observations
- The agent should not store insights that are **obvious** to an experienced engineer (e.g., "always handle errors")

## DAG checkpoints

> *Save and restore the exact DAG state across sessions.*

- Introduces a `checkpoint` command, usable at any pause point, that serializes the complete DAG state into a **self-contained JSON file**

### What is saved

- All node specs (including `diff`, `deps`, `status`, `tradeoffs`, and any extended fields like `pattern`, `perf`)
- Completion order (for the undo stack)
- The invariant ledger and decision ledger (if those features are active)
- A manifest of all files touched by `done` nodes, with content hashes for drift detection

### File format and location

- Checkpoints are stored as JSON files in `~/.config/bureau/checkpoints/` [^2]

    [^2]: The path is configurable via `local.yml` or `.bureau.yml`.

- Filename format: `<label>-<timestamp>.json` (e.g., `raft-refactor-2026-03-29T04-15.json`)

- The user provides the label: `checkpoint raft-refactor`

### Restoring a checkpoint

- The user resumes with `MICRO MODE ON, restore <label>` (or `restore latest`)

- The agent:

    1. Loads the checkpoint JSON
    2. **Re-reads all target files** to detect drift since the checkpoint was taken
    3. Runs **stale state detection** against every `done` node (verifying edits are still present)
    4. Reports any discrepancies before resuming:

        ```
        Checkpoint restored: raft-refactor (2026-03-29T04:15)
        Nodes: 12/20 done, 3 ready, 5 planned
        Drift detected:
          - validate_cfg: file modified since checkpoint (lines 42-48 differ)
          - parse_headers: OK
          ...
        ```

    5. For nodes with drift, presents options:

        - **Re-apply** the edit (attempt to merge)
        - **Accept current** file state as authoritative (mark node as needing re-review)
        - **Revert** to checkpoint state

### Difference from fold/unfold

| Concern | Fold/unfold | DAG checkpoints |
|---------|------------|-----------------|
| **Scope** | Entire conversation context (broad, lossy) | Exclusively micro mode DAG state (narrow, lossless) |
| **Purpose** | Preserve conversational reasoning and context | Preserve precise execution state |
| **Resume fidelity** | Agent reconstructs context from dossier (some loss) | Agent loads exact DAG state (no loss) |
| **Drift detection** | None | Content-hash verification on every `done` node |

- The two mechanisms are **complementary**

    - Fold/unfold preserves *why* decisions were made (conversational context)
    - DAG checkpoints preserve *what* state the DAG is in (execution state)

### When to use

- A complex refactor spanning **25+ nodes** that will take multiple sessions over several days
- Before attempting a **risky batch** of edits (checkpoint first, batch, undo-to-checkpoint if it goes wrong)
- When **context-switching** between projects — checkpoint one project's micro mode state, work on another, restore later

## Sketch nodes and node groups

> *Progressive refinement of the DAG without introducing recursive hierarchy.*
>
> This addition solves two related problems: (1) you can't always decompose a task into concrete micro edits upfront, and (2) related edits benefit from logical grouping — without adding structural hierarchy to the DAG.

### Background: why not recursive/hierarchical nodes?

- A natural instinct is to allow DAG nodes to be recursively defined: leaf nodes (concrete edits), interior nodes (containers of children), and unresolved nodes (placeholders that expand into subtrees)

- This is **compatible** with the current spec in the narrow sense that the data model can be extended, but it creates **significant friction** across five protocols:

    - The **execution loop** assumes every node is a concrete micro edit with `file`, `function`, `signature`, and `diff` — interior and unresolved nodes have none of these
    - **Status semantics** would need overloading (`ready` means "ready to execute" for leaves but "ready to be planned" for unresolved nodes — a different verb)
    - The **micro edit constraint** (1 function, ≤30 lines) is meaningless for non-leaf nodes
    - The **scheduling protocol** would need logic to skip non-executable nodes
    - The **step header/footer format** would need branching for three node kinds

- More fundamentally, it **conflicts with micro mode's core contract**: every node is the same kind of thing (a small, concrete code change the user can inspect and approve)

    - Introducing containers and placeholders means the user must track *what kind of node* they're looking at, not just *what the node does*

- The two problems that recursive nodes solve (deferred planning and logical grouping) are better addressed by **two lightweight, independent mechanisms** that preserve the flat DAG:

    - **Sketch nodes** for deferred planning
    - **Node groups** for logical grouping

### Sketch nodes

> *A node whose intent is known but whose concrete edit is not yet determined.*

#### New status value: `sketch`

- A single new addition to the existing `status` enum: `planned | ready | in_progress | done | blocked | cancelled | sketch`

- A `sketch` node has:

    - `id`, `goal`, `deps`, `risk`, `type` — populated as usual
    - `file`, `function`, `signature`, `diff` — **optional** (may be absent entirely)

        - When present, these fields contain **best guesses** (e.g., `file: "src/consensus/raft.rs"`, `function: "handle_append"`) that will be overwritten during resolution
        - When absent, the node's concrete target is unknown
        - `diff`, if present, contains a rough pseudocode description of the intended change (not an applicable patch)

- A sketch node is **not executable** — the execution loop does not attempt to apply it as a micro edit

#### Valid status transitions for `sketch`

| Transition | When it occurs | Side effects |
|------------|---------------|--------------|
| `sketch` → `ready` | Single-edit resolution (fields populated) | Node becomes a normal leaf; standard scheduling applies |
| `sketch` → `cancelled` | Split resolution (sketch replaced by N new nodes) | Standard dep-removal rules apply (remove from all other nodes' `deps` lists) |
| `sketch` → `blocked` | Resolution needs user input | Populate `tradeoffs` with the specific question |
| `sketch` → `cancelled` | Sketch no longer needed | Standard dep-removal rules apply |
| `ready` → `sketch` | **Not permitted** — a previously-concrete node cannot be un-concretized | If replanning is needed, cancel the node and create a new sketch instead |

> [!NOTE]
>
> A resolved sketch is one whose planning work is **done**: its concrete fields are populated (single-edit case) or it has been replaced by new nodes (split case). The sketch itself does not pass through `done`; it either becomes a regular leaf node (and eventually reaches `done` through normal execution) or is `cancelled` in favor of its replacements.

#### Resolution protocol

When the execution loop encounters a `sketch` node as the next candidate (i.e., all its `deps` are satisfied and no concrete `ready` nodes have higher scheduling priority), it triggers a **resolution sub-phase**:

1. The agent reads the codebase to understand what concrete edits are needed to achieve the sketch's `goal`

2. The agent determines one of two outcomes:

    - **Single edit**: the sketch resolves to a single concrete micro edit

        - The agent populates `file`, `function`, `signature`, and `diff` with concrete values
        - The agent changes `status` from `sketch` to `ready`
        - The agent emits a resolution notice:

            ```
            SKETCH RESOLVED: <id> → concrete edit
            - File: <file>::<function>
            - Diff: <summary>
            ```

        - Execution proceeds normally (the node is now a regular leaf node)

    - **Multiple edits**: the sketch needs to be split into 2+ concrete micro edits

        - The agent creates new leaf nodes (with concrete `file`, `function`, `signature`, `diff`)
        - The agent sets the original sketch node's `status` to `cancelled` (it has been replaced)
        - **Dep inheritance rule**: the new nodes inherit the sketch's `deps`; nodes that previously depended on the sketch now depend on **all** of the new nodes by default

            - The agent may narrow this (e.g., only the last node, or a specific subset) if it can determine that not all new nodes are needed to satisfy the downstream dependency

            - If the agent narrows the dep assignment, it **must present the assignment to the user** for confirmation before proceeding, since incorrect narrowing can break ordering guarantees

        - This flows through the existing **DAG change protocol**: the agent logs the change, updates deps/status per the status update protocol, and the user sees the standard `*** DAG CHANGED ***` output

3. If the agent **cannot resolve** the sketch (needs more information, architectural decision required), it sets `status` to `blocked` and populates `tradeoffs` with the specific question — triggering the normal blocked-node resolution dialogue

#### When to create sketch nodes

A node should only be left as a sketch when one of the following conditions holds:

- **Upstream dependency on volatile nodes**: the sketch relies on upstream nodes whose implementation and/or existence itself might change — concretizing the sketch now would be wasted work

    - Example: "We'll need to update the serialization layer, but the exact changes depend on what the new schema looks like after the API step"

- **Scope exceeds planning capacity**: the sketch's scope is wide enough that fully planning it now would consume excessive context (roughly >300K tokens of investigation and planning) — deferring resolution to when upstream work is done and the problem space is narrower is more efficient

    - Example: "Error handling across the consensus module needs a comprehensive overhaul, but we should do the protocol changes first to know what error paths exist"

- During **phase 2 execution**, via the DAG change protocol, when a completed step reveals that additional work is needed but the details are unclear

> [!IMPORTANT]
>
> Sketch nodes are **not** a mechanism for avoiding planning work. If the agent *can* concretize a node during phase 1 (i.e., neither condition above applies), it **must** do so. Unnecessary sketches reduce the user's visibility into the scope of work.

#### Interaction with scheduling

- The scheduling protocol's existing heuristics (**higher `risk` first**, then `API → IMPL → FIX → TEST → DOC`) apply to sketch nodes the same as concrete nodes

    - A `risk: high` sketch is resolved before a `risk: low` concrete node — because surfacing design errors early is the scheduling protocol's entire purpose, and an unresolved high-risk sketch *is* a design error waiting to surface

- Within the same `risk` and `type` priority, **concrete `ready` nodes are preferred over `sketch` nodes**

    - This ensures sketches are resolved **lazily within their priority band** — earlier concrete edits often provide the context needed to resolve later sketches, so deferring resolution avoids premature planning

- The `?` (DAG status) command displays sketch nodes with a distinct marker:

    ```
     update_serial   │ sketch      │ medium │ IMPL │ (unresolved)
    ```

#### Interaction with other features

- **Batch approval**: when a batch encounters a sketch node whose deps are all satisfied, the batch **halts** and prompts the user:

    ```
    BATCH HALTED: sketch node <id> requires resolution
    - Goal: <sketch's goal>
    - Deps satisfied: all done
    - Action needed: resolve this sketch before continuing

    Options:
      (1) Resolve now → enter resolution sub-phase for this sketch
      (2) Skip → continue batch, leave sketch for later
      (3) Cancel batch → stop here, return to single-step mode
    ```

    - This applies to **all** batch modes (`>> N`, `>> low`, `>> all`, `>> group`)
    - Silently skipping a sketch would hide the fact that planning work is needed, defeating the purpose of making sketches visible in the first place

- **Explain keys** are not available on sketch nodes (there is no concrete edit to explain)

    - However, the `?` command with `? <id>` shows the sketch's `goal` and provisional fields

- **DAG checkpoints** serialize sketch nodes alongside concrete nodes, preserving their provisional fields and `goal`

- **Node groups**: sketch nodes **can** have a `group` field (so `? group` shows them for visibility of deferred work within the group)

    - When a sketch resolves and splits into concrete nodes, the new nodes **inherit the group**
    - The batch halt behavior above applies to `>> group` as well — if the group contains a deps-satisfied sketch, the batch halts and prompts

#### What this replaces

- The **DAG change protocol** already supports adding nodes mid-execution, but sketch nodes make deferred planning **explicit and visible** in the DAG from the start

    - Without sketches: the user sees 12 concrete nodes and discovers mid-execution that 5 more are needed (surprise)
    - With sketches: the user sees 12 concrete nodes and 3 sketches, knowing upfront that some planning is deferred (expected)

- This is the key ergonomic improvement: **no surprises about the scope of work**, even when not all details are known yet

### Node groups

> *Logical grouping of related nodes without structural hierarchy.*

#### The `group` field

- Each DAG node gains an optional `group` field *(string)*

    - Nodes with the same `group` value are logically related (e.g., "all edits for the serialization layer refactor")
    - The field is purely **cosmetic and ergonomic** — it does not affect execution order, scheduling, or status propagation

- Groups are **not containers**: they have no parent node, no status of their own, no children list

    - A node can belong to at most one group
    - A group exists implicitly when any node references it — no separate group definition is needed

#### Setting groups

- During **phase 1 planning**, the agent assigns `group` values to related nodes using descriptive, human-readable names:

    - `group: "serialization"` for all nodes touching the serialization layer
    - `group: "error-handling"` for all nodes adjusting error paths
    - `group: "api-v2"` for all nodes implementing the new API version

- The user can **reassign groups** at any pause point (e.g., "move `validate_cfg` to the serialization group")

#### Interaction with `?` (DAG status)

- `? group <name>` filters the DAG table to nodes in a specific group:

    ```
    ?  DAG Status — group: serialization (3/5 done)
    ───────────────────────────────────
     id              │ status │ risk   │ type │ file::function
    ─────────────────┼────────┼────────┼──────┼──────────────────────
     serial_schema   │ done   │ high   │ API  │ src/proto.rs::Schema
     serial_encode   │ done   │ medium │ IMPL │ src/codec.rs::encode
     serial_decode   │ done   │ medium │ IMPL │ src/codec.rs::decode
     serial_compat   │ ready  │ high   │ FIX  │ src/compat.rs::migrate
     serial_tests    │ planned│ low    │ TEST │ tests/codec_test.rs::roundtrip
    ───────────────────────────────────
    ```

- `? groups` lists all groups with a summary:

    ```
    Groups:
      serialization  — 3/5 done
      error-handling — 0/4 done (2 sketch)
      api-v2         — 1/3 done
    ```

#### Interaction with batch approval

- `>> group <name>` batches all `ready` nodes in a specific group:

    - Follows the same halt conditions and compressed-output format as regular batch approval
    - Useful for approving a cluster of related mechanical edits in one command

- If the group contains a **sketch node** whose deps are satisfied, the batch **halts and prompts** the user (see [sketch interaction with batch approval](#interaction-with-other-features) above)

    - This ensures deferred planning work within a group is never silently skipped

#### Interaction with explain keys

- When an explain key is pressed on a node that belongs to a group, the `r` (repo) axis should acknowledge the group context:

    - "This is the 3rd of 5 edits in the serialization group; the prior two established the new schema and encoder"

#### Why groups instead of hierarchy

- Groups give the user **all the ergonomic benefits** of "these edits belong together" (filtered views, batch approval, contextual explanations) without any of the **protocol complexity** of tree traversal, parent-child status propagation, or recursive node definitions

- The flat DAG remains flat: `deps` still encode all ordering constraints, `status` still means the same thing for every node, the execution loop still processes one leaf at a time

- Groups are **purely additive** — removing the `group` field from every node would leave the protocol fully functional, just without the grouping ergonomics
