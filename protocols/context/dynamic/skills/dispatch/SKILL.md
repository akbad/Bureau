---
name: dispatch
description: >-
  Activate when you identify 2+ independent work units that could execute in
  parallel. Triggers include phrases like "do these in parallel", "split this
  into subagents", "dispatch these tasks", or self-recognition that a workload
  decomposes into units with no shared mutable state. Also activates when you
  are about to spawn multiple subagents for concurrent execution.
---

# Dispatch: disciplined parallel execution

> **Goal:** never spawn parallel subagents without first verifying independence and defining reconciliation.
>
> Parallel execution is Bureau's primary performance multiplier. But parallelism
> without structural discipline produces merge conflicts, duplicated work, and
> wasted tokens. This skill imposes the discipline that makes delegation safe:
> prove the work units are independent, commit to a reconciliation plan, and
> only then dispatch.

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed
> **exactly as they are specified**.
>
> Violating the letter of these rules is violating the spirit of these rules.

## Activation / deactivation

### Trigger phrases

- "do these in parallel"
- "split this into subagents"
- "dispatch these tasks"
- "parallelize this"
- "fan out"

### Self-activation

This skill **also activates automatically** when you identify 2+ work units
that could execute concurrently. If you are about to spawn multiple subagents,
this skill applies whether or not the user explicitly invoked it.

### Deactivation

One-shot. The skill completes when reconciliation is verified in Phase 5.

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

## Definitions

| Term | Meaning |
|------|---------|
| **Work unit** | A discrete task with defined inputs, outputs, and acceptance criteria that can be assigned to a single subagent |
| **Independence** | Two work units are independent if and only if they share no mutable state: no files written by both, no database rows mutated by both, no config modified by both |
| **Shared mutable state** | Any resource that two or more work units would both write to. Read-only shared resources (reading the same config, importing the same module) do NOT violate independence |
| **Reconciliation plan** | A concrete specification, written before dispatch, of how subagent outputs will be merged into a single coherent deliverable |
| **Acceptance criteria** | Observable, testable conditions that define "done" for each work unit. Not "make it good" -- specific checks a verifier can run |
| **Blast radius** | The set of files, symbols, and state a work unit will modify. Two work units with overlapping blast radii are NOT independent |

## Phase 1: Decompose

Identify the candidate work units from the current task.

### Steps

1. List every discrete subtask in the current workload.
2. For each subtask, enumerate its **blast radius**: the specific files, database tables, config keys, or shared state it will read and write.
3. Group subtasks into candidate work units. A work unit should be large enough to justify subagent overhead but small enough to have a clear blast radius.
4. Write down each candidate work unit with:
   - A one-sentence task description
   - Input resources (what it reads)
   - Output artifacts (what it creates or modifies)
   - Acceptance criteria (how to verify it succeeded)

### Phase 1 escalation

- DONE -> proceed to Phase 2
- DONE_WITH_CONCERNS -> if fewer than 2 work units emerge, the task does not need Dispatch; handle directly
- NEEDS_CONTEXT -> if the blast radius of any subtask is unclear, read the relevant code before proceeding
- BLOCKED -> if the task is fundamentally sequential (each step depends on the prior step's output), Dispatch does not apply; handle directly or use sequential delegation

## Phase 2: Verify independence

This is the critical gate. The #1 failure mode of parallel dispatch is shared mutable state causing conflicts. Two subagents editing the same file produces a reconciliation nightmare that costs more than sequential execution would have.

### Steps

1. For every **pair** of candidate work units, check:
   - Do their blast radii overlap on any **writable** resource? (Files, DB tables, config keys, environment variables)
   - Does one produce output that the other consumes as input?
   - Do they share any mutable global state (singletons, caches, lock files)?

2. Build an **independence matrix**: a table where each cell records whether two work units are independent, conflicting, or sequentially dependent.

3. For any pair that is NOT independent:
   - Can the conflict be eliminated by narrowing the blast radius (e.g., splitting a shared file into two, or having one unit produce output to a temp location)?
   - If yes, restructure and re-verify.
   - If no, those units must execute sequentially, not in parallel. Merge them into a single work unit or establish an explicit ordering dependency.

> See `independence-checklist.md` (bundled with this skill) for the concrete checks.

### Gate

BEFORE proceeding to Phase 3:
  Ask: "Have I verified independence for every pair of work units?"
  IF any pair has unresolved shared mutable state:
    STOP -- resolve the conflict by restructuring or sequencing before continuing.
  Every cell in the independence matrix must be "independent" or "sequenced."

**Never dispatch work units with unverified independence. This is the invariant that justifies this skill's existence.**

### Phase 2 escalation

- DONE -> all pairs verified independent (or explicitly sequenced); proceed to Phase 3
- DONE_WITH_CONCERNS -> some pairs required restructuring; document what changed and proceed
- NEEDS_CONTEXT -> blast radius unclear; read more code before verifying
- BLOCKED -> fundamental conflicts that cannot be restructured; fall back to sequential execution

## Phase 3: Plan reconciliation

Define how subagent outputs will be merged BEFORE any subagent is spawned. This is the behavioral inversion that distinguishes disciplined dispatch from ad-hoc parallelism. Agents naturally dispatch first and figure out merging later. This phase forces the merge plan to exist first.

### Steps

1. For each work unit, specify the **deliverable format**: what the subagent produces (files created, files modified, test results, analysis document, etc.).

2. Define the **reconciliation strategy**:
   - **No-conflict merge**: work units touch disjoint files; reconciliation is concatenation. Verify no unexpected overlaps.
   - **Output assembly**: work units produce independent artifacts that must be composed into a larger deliverable. Specify the assembly order and any glue logic.
   - **Review-and-integrate**: work units produce recommendations or analysis that the orchestrating agent must synthesize. Specify the synthesis criteria.

3. Define **conflict resolution**: what happens if a subagent's output unexpectedly overlaps with another's despite the independence check. The default is: STOP, do not auto-merge, flag for manual review.

4. Define **verification checks** to run after reconciliation:
   - Tests that must pass
   - Lint checks
   - Manual inspections
   - Cross-reference checks (does the merged output have internal consistency?)

> See `reconciliation-patterns.md` (bundled with this skill) for common patterns.

### Gate

BEFORE proceeding to Phase 4:
  Ask: "Do I have a written reconciliation plan for every work unit's output?"
  IF any work unit lacks a reconciliation strategy:
    STOP -- define the strategy before dispatching.
  The reconciliation plan must exist before any subagent is spawned.

**Never dispatch without a reconciliation plan. Dispatching first and figuring out merging later is the failure mode this skill exists to prevent.**

### Phase 3 escalation

- DONE -> reconciliation plan complete for all work units; proceed to Phase 4
- DONE_WITH_CONCERNS -> some reconciliation strategies are complex; flag for extra scrutiny during Phase 5
- NEEDS_CONTEXT -> unclear how outputs should compose; clarify with user before proceeding
- BLOCKED -> outputs cannot be reconciled without sequential coordination; restructure the work units

## Phase 4: Calibrate and dispatch

Prepare subagent prompts and execute.

### Steps

1. For each work unit, compose a subagent prompt containing:
   - **Task**: the one-sentence description from Phase 1
   - **Context**: relevant file paths (absolute), architectural notes, and constraints
   - **Acceptance criteria**: the specific checks from Phase 1
   - **Constraints**: what NOT to modify (files outside the blast radius)
   - **SUBAGENT-STOP**: include this directive so subagents do not recursively invoke Dispatch
   - **Skills**: list any Bureau or Superpowers skills the subagent should follow (e.g., TDD)
   - **Deliverable format**: what to produce, matching the reconciliation plan from Phase 3

2. Select the delegation mechanism and model for each work unit. Reference the handoff guide's model selection matrix and decision tree -- do not reinvent model selection here. The discipline is in the dispatch structure, not in model recommendations.

> See `prompt-calibration.md` (bundled with this skill) for subagent prompt best practices.

3. **Dispatch all independent work units simultaneously** using multiple tool calls in a single response. Sequential dispatch of independent units defeats the purpose of this skill.

4. For work units with explicit ordering dependencies (identified in Phase 2), dispatch them in dependency order, waiting for the predecessor to complete before dispatching the successor.

### Phase 4 escalation

- DONE -> all subagents dispatched; proceed to Phase 5
- DONE_WITH_CONCERNS -> some subagent prompts required compromise on context (too much state to summarize); flag for extra reconciliation scrutiny
- NEEDS_CONTEXT -> insufficient information to write a clear subagent prompt; gather more context before dispatching
- BLOCKED -> delegation mechanism unavailable (tool failure, rate limit); retry or fall back to sequential execution

## Phase 5: Reconcile and verify

Collect subagent outputs and execute the reconciliation plan from Phase 3.

### Steps

1. **Collect** all subagent outputs. For each, verify it meets the acceptance criteria defined in Phase 1. Record: `Accepted`, `Needs follow-up`, or `Rejected`.

2. **Detect conflicts**: even with independence verification, check for unexpected overlaps:
   - Did any subagent modify files outside its declared blast radius?
   - Do any outputs contradict each other?
   - Are there integration issues at the boundaries?

3. **Execute reconciliation** according to the plan from Phase 3:
   - Apply the merge strategy (no-conflict merge, output assembly, or review-and-integrate)
   - Run the verification checks defined in Phase 3 (tests, lint, manual inspection)
   - If conflicts are detected, follow the conflict resolution strategy from Phase 3

4. **Verify the merged deliverable**:
   - All tests pass
   - No unresolved conflicts
   - Cross-references are consistent
   - The merged result achieves the original task's objective, not just the individual work unit objectives

5. **Store reconciliation insights**: update Qdrant and Memory MCP with:
   - What parallelized well and what didn't
   - Any unexpected conflicts and how they were resolved
   - Effective subagent prompts for future reference

### Gate

BEFORE declaring Dispatch complete:
  Ask: "Has every subagent output been verified against its acceptance criteria, and has the merged deliverable been tested as a whole?"
  IF any verification failed:
    STOP -- diagnose and fix before declaring completion.

### Phase 5 escalation

- DONE -> reconciliation complete, all checks pass; Dispatch is complete
- DONE_WITH_CONCERNS -> reconciliation required manual intervention; document what happened for future reference
- NEEDS_CONTEXT -> subagent output is ambiguous; re-query the subagent or inspect directly
- BLOCKED -> reconciliation failed; outputs are irreconcilable. Escalate to user

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "These tasks are obviously independent, I don't need to check." | "Obviously independent" is the exact thought that precedes every merge conflict. The independence check takes 30 seconds. The merge conflict costs 30 minutes. Check every pair. |
| "I'll figure out how to merge the results after the subagents finish." | Reconciliation-after-dispatch is the #1 cause of wasted parallel work. If you cannot define the merge strategy now, you do not understand the task well enough to parallelize it. |
| "Checking every pair is O(n^2), that's too many comparisons." | If you have so many work units that pairwise checking is burdensome, you have too many work units. Reduce granularity until the matrix is manageable. Five work units = ten pairs = two minutes. |
| "The independence check passed, so conflicts are impossible." | The check reduces conflict probability; it does not eliminate it. Subagents can produce unexpected outputs. Phase 5 verification exists because Phase 2 is necessary but not sufficient. |
| "I'll add the reconciliation plan after I see what the subagents produce." | This is dispatching without a plan. The reconciliation plan constrains what you ask subagents to produce. Without it, subagents produce whatever format they choose, and you inherit an integration problem instead of solving a merge problem. |
| "This is just two subagents, the overhead of this full protocol isn't justified." | Two subagents editing the same file is the most common dispatch failure. The protocol is lightest at two units and most valuable at two units. |
| "The user asked me to be fast, I should skip the independence check." | Skipping the check and hitting a merge conflict is slower than doing the check. Speed is the reason for the discipline, not the excuse to skip it. |
| "I can dispatch sequentially and still get some benefit from delegation." | Sequential dispatch of independent units is not delegation -- it is serialization with extra overhead. Dispatch simultaneously or justify the sequential ordering with a real dependency. |
| "One subagent can just overwrite the other's changes if there's a conflict." | Overwriting is data loss. If outputs conflict, the correct response is STOP and diagnose, not silently discard work. |
| "I already know the right model for each subagent, I don't need the handoff guide." | The handoff guide is updated with current model capabilities and rate limits. Your training data may reflect a different model landscape. Reference the guide. |

## Red flags -- STOP

If you notice any of these, stop and restart the current phase:

- You are about to call multiple subagent tools and you have not written an independence matrix for the work units
- You are composing a subagent prompt and realize you have not defined what the subagent should produce or how its output will be merged with others
- You are thinking "I'll reconcile the outputs when I see them" -- this means you skipped Phase 3
- You feel impatient with the pairwise independence check because the tasks "seem" disjoint -- seeming disjoint is not being disjoint
- You are about to dispatch subagents one at a time, waiting for each to finish before starting the next, even though they are independent
- You are thinking "this is a small dispatch, the full protocol is overkill" -- small dispatches with shared mutable state produce the same conflicts as large ones
- You finished dispatching and realize you have no plan for what to do with the outputs
- You are about to auto-merge conflicting subagent outputs without flagging the conflict
- You are thinking "the user is waiting, I should just dispatch now and plan later" -- planning later means re-doing work now

## Verification

Before declaring this workflow complete, verify:

- [ ] Every pair of dispatched work units was checked for shared mutable state (independence matrix exists)
- [ ] A reconciliation plan was written before any subagent was spawned
- [ ] All independent work units were dispatched simultaneously (not sequentially)
- [ ] Every subagent prompt included: task, acceptance criteria, constraints, SUBAGENT-STOP, and deliverable format
- [ ] Every subagent output was verified against its acceptance criteria
- [ ] The merged deliverable was tested as a whole (not just individual pieces)
- [ ] Any unexpected conflicts were flagged and resolved, not silently overwritten
- [ ] Reconciliation insights were stored in memory for future dispatches

## Companion files

| File | Consult when |
|------|-------------|
| `independence-checklist.md` | Running Phase 2 -- use this checklist for every pair of work units |
| `reconciliation-patterns.md` | Running Phase 3 -- reference common merge strategies and their trade-offs |
| `prompt-calibration.md` | Running Phase 4 -- best practices for writing effective subagent prompts |

## Hook points

| Phase transition | Verification | Hook type |
|-----------------|-------------|-----------|
| Phase 2 -> Phase 3 | Independence matrix complete: all pairs resolved as "independent" or "sequenced" | pre-phase |
| Phase 3 -> Phase 4 | Reconciliation plan exists for every work unit | pre-phase |
| Phase 5 -> Complete | All acceptance criteria met; merged deliverable passes verification checks | post-phase |

## Composition with Reflect

When the Reflect skill is active, it validates Dispatch's reconciliation results.
The interface is clean: Dispatch produces a reconciled deliverable at the end of
Phase 5. Reflect takes that deliverable as input and applies its three lenses
(completeness, correctness, fitness). If Reflect raises objections, return to
Phase 5 to address them before declaring Dispatch complete.

## Final rule

> Never spawn parallel subagents without first verifying independence and defining reconciliation. The discipline before dispatch is what makes the dispatch safe.
