# Phase 1 reference

> [!IMPORTANT]
> These protocols must be followed **at all times *as soon as* the DAG is created**: from phase 1, all the way through to the very end of phase 2 (i.e., completion of the implementation/changeset represented by the DAG).

## Node specification

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
- `diff` *(string)*: a concrete diff containing the exact changes needed; updated during phase 2 execution if stale state detection reveals the ground truth has changed (see stale state detection in the execution loop)

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

## Status update protocol

> [!IMPORTANT]
>
> - Any time you set a node's `status` field to `cancelled` or `done` from any other status value, you **must** ensure that node is removed from any other nodes' `deps` lists in which it appears.
>
>     - The converse also applies: whenever a node's `status` field is changed from `cancelled` or `done` to any other status value, you **must** carefully ensure the node is added to any other node's `deps` list that depends on it.
>
> - Any time you change a node's `status` from `blocked` to any other value (i.e., since the blocking issue was resolved via resolution/clarification from the user) ensure the `tradeoffs` field's value is cleared (if non-empty).

## DAG persistence protocol

Maintain the DAG explicitly in any structural memory tools available (or, as a last resort, in chat) and update it if needed/as appropriate after every prompt.

> [!IMPORTANT]
>
> **No implicit dependencies allowed**: dependencies between nodes must be **explicitly encoded** in the DAG.

> [!TIP]
>
> The `deps` list does NOT need to be explicitly maintained as a list/array of node IDs; in particular, if the storage tool/mechanism (e.g. a memory storage MCP) natively supports graph (ideally, digraph) or similar operations, `deps` can and should be recorded as edges (ideally, directed edges/arcs).
>
> Optimize for efficiency and native support (by the tool) of the DAG's representation in storage (while maintaining its completeness, of course).

## Scheduling protocol

> *To surface design errors **before** building on top of them.*

When multiple steps are ready (deps satisfied), prefer executing based on the following heuristics in the hierarchy given (unless explicitly told otherwise, or there is a clear reason not to):

1. **Steps with higher `risk` earlier**
2. Nodes prioritized by `type` in this order ***(where `deps` allow)***:

  **`API → IMPL → FIX → TEST → DOC`**
