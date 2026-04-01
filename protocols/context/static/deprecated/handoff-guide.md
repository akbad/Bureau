<!-- DEPRECATED: Content migrated to ops/ spoke files. See docs/plans/2026-03-29-context-hub-spoke-design.md -->
# *Handoff guidelines:* how and when to delegate to subagents

> **Purpose**: a concise guide for when and how to delegate work vs. when to ask the user for guidance.

## Delegation decision flow

Apply these gates in order. Stop at the *first* gate that determines the next action.

### Gate 1: Ask the user first

Ask the user when:

- requirements are ambiguous
- multiple valid approaches exist and trade-offs are non-obvious
- explicit approval is required

If none apply, continue to Gate 2.

### Gate 2: Handle directly or delegate

Handle directly when one or more of these are true:

- task is simple and well-understood (for example, 1-2 clear file edits)
- task needs tight iteration loops (debugging with rapid hypothesis testing)
- explanation overhead is higher than execution time

Delegate when a different model or role materially improves accuracy, speed, cost, or context handling.

Before delegating, account for delegation costs:

- summarization overhead
- potential loss of nuance
- coordination and review delay
- risk of misunderstood prompt requirements

### Gate 3: If delegating, single or parallel

Use parallel delegation only when all are true:

- tasks are independent
- tasks can run concurrently without coordination
- tasks are time-consuming enough to justify split execution
- outputs are mergeable and can be verified together

If any condition fails, use a single delegate (or return to direct handling).

### Default posture

Ask: "Can this be split into 2+ independent subtasks?"

- if yes, parallelize
- if no, use single delegate or direct handling

Err toward parallelization only after Gate 2 confirms delegation is worth the overhead.

## Subagent lifecycle checklist

Use this lifecycle for every delegated task.

### Phase A: Prompt contract (before spawning)

Always include in subagent prompts:

1. **Relevant file paths** (absolute, not relative)
- Provide exact paths to files the subagent will need
- Example: `/Users/you/project/src/module/file.ts` NOT `./file.ts`

2. **Summarized context** (what you've learned that's relevant)
- Key findings from your investigation so far
- Important constraints or requirements discovered
- Relevant architectural decisions or patterns

3. **Clear success criteria** (what "done" looks like)
- Specific deliverable expected from the subagent
- How you'll verify the work is complete
- What format you need the results in

4. **Explicit constraints** (what NOT to do)
- Actions requiring approval (don't commit, don't delete, etc.)
- Areas to avoid modifying
- Specific approaches to reject

### Phase B: Result reconciliation (after execution)

After every delegated batch, run this checklist:

1. **Collect & normalize:** pull every subagent summary into one workspace (table/list/doc) and record CLI/model/thinking levels plus citations so claims stay traceable.
2. **Compare & detect conflicts:** highlight overlaps, find contradictions or duplicated work, and confirm no component was overlooked.
3. **Validate critical claims:** spot-check referenced files, rerun key commands/tests, and double-check web/API citations before accepting conclusions.
4. **Decide outcomes:** mark each subtask `Accepted` / `Needs follow-up` / `Rejected`; if blockers remain, spawn a focused follow-up subagent or use the [trigger matrix](#trigger-matrix).

### Phase C: Close the loop

1. **Record & broadcast:** update memory tools with the reconciled, distilled truth (and not raw subagent dump) and summarize decisions back to the main thread/user.
2. **Plan next actions:** turn accepted recommendations into concrete edits/tests/commits and explicitly close the loop on rejected paths so future agents don't retry them.

### Hard rule on memory writes

> [!IMPORTANT]
>
> Never ship or store memories until merged results are verified. Raw, unvetted subagent output must not flow into persistent systems.

## Handoff patterns

Use this phase map as a quick navigator. Detailed execution rules live in linked sections.

| Order | Phase name | Primary objective | Use these sections |
| :--- | :--- | :--- | :--- |
| **1** | **Research** | Understand requirements, code, and constraints | [Delegation decision flow](#delegation-decision-flow), [Phase A: Prompt contract](#phase-a-prompt-contract-before-spawning), [Trigger matrix](#trigger-matrix) |
| **2** | **Planning** | Design approach, break down tasks, identify risks | [Delegation decision flow](#delegation-decision-flow), [Phase A: Prompt contract](#phase-a-prompt-contract-before-spawning), [Authorization categories](#authorization-categories-explicit-approval-required) |
| **3** | **Implementation** | Execute changes while controlling risk and coordination overhead | [Delegation decision flow](#delegation-decision-flow), [Phase B: Result reconciliation](#phase-b-result-reconciliation-after-execution), [Authorization categories](#authorization-categories-explicit-approval-required) |
| **4** | **Review/Verification** | Validate outcomes, resolve conflicts, and prepare safe closure | [Phase B: Result reconciliation](#phase-b-result-reconciliation-after-execution), [Phase C: Close the loop](#phase-c-close-the-loop), [Approval workflow](#approval-workflow) |

## When to ask the user (AskUserQuestion)

### Trigger matrix

Use this matrix to decide whether to ask and what kind of ask to perform.

| Trigger type | Use when | Required action |
| :--- | :--- | :--- |
| **Clarify** | Requirements are ambiguous, or critical information is missing (for example, configs or environment details). | Ask focused clarification questions before proceeding. |
| **Choose** | Multiple valid approaches exist with non-obvious trade-offs (including high-impact architecture or breaking-change decisions). | Present 2-4 options with concise trade-offs and request a decision. |
| **Authorize** | The action is in an explicit-approval category, including security/compliance-sensitive operations. | Follow the [approval workflow](#approval-workflow) and wait for explicit approval. |

### Asking format

- Provide 2-4 clear options with concise trade-offs.
- Allow multi-select when appropriate.
- Include context about why you are asking.
- Keep headers short.

### Authorization categories (explicit approval required)

| Category | Includes | Exception |
| :--- | :--- | :--- |
| **Version control operations** | creating commits (unless explicitly told), pushing, merging, rebasing, force pushes, amending commits | User explicitly says "commit this" or "push these changes". |
| **Destructive operations** | deleting files/dirs, truncating databases, dropping tables, purging caches, removing dependencies | User explicitly says "delete X" or removal is part of an explicitly approved refactoring task. |
| **Production/deployment** | prod deploys, prod config changes, service restarts, env var changes, prod migrations | No exception; always ask, even if user says "deploy". |
| **Security/access changes** | authN/Z changes, permission grants, exposing endpoints, disabling security features, handling secrets | No exception. |
| **Breaking changes** | public API removals, signature changes without backward compatibility, schema changes without migrations, config format changes | Proceed only with explicit user approval for the breaking change. |
| **Cost-impacting changes** | adding cloud resources, increasing instance size, storage tier changes, rate-limit changes, adding paid third-party services | No exception. |

### Approval workflow

1. Clearly state what will happen.
2. List affected resources/files.
3. Explain potential risks/impacts.
4. Use `AskUserQuestion` with clear options.
5. Wait for explicit approval.
6. Proceed only after approval.
