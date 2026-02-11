# *Handoff guidelines:* how and when to delegate to subagents

> **Purpose**: a concise guide for when to delegate work vs. when to ask the user for guidance.

## Table of contents

- [Table of contents](#table-of-contents)
- [Core delegation strategies](#core-delegation-strategies)
  - [Delegation principles](#delegation-principles)
  - [When NOT to delegate](#when-not-to-delegate)
- [Parallel delegation strategies](#parallel-delegation-strategies)
  - [When to parallelize](#when-to-parallelize)
  - [Default mindset](#default-mindset)
- [Merge \& verify results](#merge--verify-results)
- [Subagent context management](#subagent-context-management)
  - [Setting your spawned subagents up for success](#setting-your-spawned-subagents-up-for-success)
- [Handoff patterns](#handoff-patterns)
- [When to ask the user (AskUserQuestion)](#when-to-ask-the-user-askuserquestion)
  - [When to ask](#when-to-ask)
  - [Best practices](#best-practices)
  - [What requires explicit approval, always](#what-requires-explicit-approval-always)

## Core delegation strategies

### Delegation principles

- Delegate when another model or role materially improves accuracy, speed, cost, or context handling.
- Ask the user when requirements are ambiguous, multiple valid options exist, or explicit approval is required.
- Handle directly when the task is within your capability and scope is clear.

### When NOT to delegate

**Handle tasks directly (don't delegate) when:**

- **Task is simple and well-understood:** 1-2 file edits with clear requirements; faster to do than explain
- **Requires tight iteration loops:** Debugging with frequent hypothesis testing; trial-and-error exploration
- **Context loss would be expensive:** Deeply nested state that's hard to summarize; extensive prior conversation history
- **You already have necessary context loaded:** Files read, relationships understood; delegation = wasteful reloading
- **Explanation overhead > execution time:** If describing the task takes longer than doing it

**Cost of delegation:**
- Context summarization overhead (lossy compression of your current understanding)
- Potential information loss (nuances don't survive handoff)
- Coordination time (waiting for subagent, reviewing results)
- Risk of misunderstanding requirements (ambiguity in your prompt)

**Rule of thumb:** If you can complete the task in <2 minutes with context you already have → handle directly.

## Parallel delegation strategies

### When to parallelize

Spawn multiple subagents **concurrently** (not sequentially) when tasks are:
- **Independent**: No data dependencies between them
- **Parallelizable**: Can execute simultaneously without coordination
- **Time-consuming**: Research, analysis, exploration, code search
- **Mergeable**: Results can be combined afterward

### Default mindset

**Before starting work:** Ask "Can I break this into 2+ independent subtasks?"
- If **YES** → Spawn multiple subagents in parallel
- If **NO** → Handle directly or spawn single subagent

**Err toward parallelization.** Coordination overhead is minimal compared to sequential execution time.

## Merge & verify results

Parallel execution only helps if you consolidate the answers rigorously. After every parallel batch, run this checklist:

1. **Collect & normalize:** pull every subagent summary into one workspace (table/list/doc) and record CLI/model/thinking levels plus citations so claims stay traceable.
2. **Compare & detect conflicts:** highlight overlaps, find contradictions or duplicated work, and confirm no component was overlooked.
3. **Validate critical claims:** spot-check referenced files, rerun key commands/tests, and double‑check web/API citations before accepting conclusions.
4. **Decide outcomes:** 

    - Mark each subtask `Accepted` / `Needs follow-up` / `Rejected`
    - If blockers remain, spawn a focused follow-up subagent or use `AskUserQuestion`

5. **Record & broadcast:** update Memory MCP (relationships) and Qdrant (insights/gotchas) with the reconciled truth (and not raw subagent dump) and summarize decisions back to the main thread/user.
6. **Plan next actions:** turn accepted recommendations into concrete edits/tests/commits and explicitly close the loop on rejected paths so future agents don’t retry them.

> **Reminder:** Never ship or store memories until merged results are verified. Raw, unvetted subagent output must not flow into persistent systems.

## Subagent context management

### Setting your spawned subagents up for success

**Always include in subagent prompts:**

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

## Handoff patterns

Follow the sequential flow of phases in the table below (in the order presented):

| Order | Phase name | Objectives | Actions to perform |
| :--- | :--- | :--- | :--- |
| **1** | **Research** | Understand requirements, code, and constraints | Use `Task` Explore (Claude) for codebase exploration; use direct read/glob for known files/symbols; use `clink`→Gemini for long‑context needs (>~400K). If ambiguity remains, see [AskUserQuestion](#when-to-ask-the-user-askuserquestion) |
| **2** | **Planning** | Design the approach, break down tasks, identify risks | Outline steps; note trade‑offs; delegate complex architecture to Claude (`architect`) or refactoring planning to Codex (`migration-refactoring`) via `clink`. For large goals, use `task-decomposer` to produce verifiable substeps and dependencies. Resolve ambiguities via [AskUserQuestion](#when-to-ask-the-user-askuserquestion). See [What requires explicit approval, always](#what-requires-explicit-approval-always) before proceeding. |
| **3** | **Implementation** | Execute the plan and write changes | Track tasks; use Codex for wide refactors/testing; use Claude for coordination; use Gemini for long‑context codebase analysis. Leverage specialist roles as needed (e.g., `schema-evolution`, `auth-specialist`, `caching-specialist`, `event-driven`, `debugger`). Also see [what requires explicit approval, always](#what-requires-explicit-approval-always) before proceeding. |
| **4** | **Review/Verification (optional)** | Verify changes, run tests, prepare for commit | Request code review (use `code-reviewer` for structured guidance); run tests; follow the [Approval pattern](#approval-pattern) as needed. |

## When to ask the user (AskUserQuestion)

### When to ask

Ask the user when:
- Requirements are ambiguous, trade‑offs are uncited, or multiple valid approaches exist.
- High‑impact architectural decisions are involved (system design, stack selection, breaking changes).
- Critical information is missing (configs, environment details).
- Security/compliance sensitivity exists (credentials, access control, retention).
- Before destructive operations or any action listed under “Explicit Approval”.

### Best practices
- Provide 2–4 clear options with concise trade‑offs; allow multi‑select when appropriate.
- Include context about why you’re asking; keep headers short.

### What requires <ins>explicit</ins> approval, <ins>always</ins>

- **Version control operations**: creating commits (unless explicitly told), pushing, merging, rebasing, force pushes, amending commits.

  - Exception: User explicitly says "commit this" or "push these changes".

- **Destructive operations**: deleting files/dirs, truncating databases, dropping tables, purging caches, removing dependencies.

  - *Exception*: User explicitly says "delete X" or removal is part of an explicitly approved refactoring task.

- **Production/deployment**: prod deploys, prod config changes, service restarts, env var changes, prod migrations.

  - Never assume: always ask even if user says "deploy".

- **Security/access changes**: authN/Z changes, permission grants, exposing endpoints, disabling security features, handling secrets.
- **Breaking changes**: public API removals, signature changes without backward compatibility, schema changes without migrations, config format changes.

  - *Exception*: Proceed only with explicit user approval for the breaking change.

- **Cost‑impacting changes**: adding cloud resources, increasing instance size, storage tier changes, rate‑limit changes, adding paid third‑party services.

#### Approval pattern

1. Clearly state what will happen
2. List affected resources/files
3. Explain potential risks/impacts
4. Use AskUserQuestion with clear options
5. Wait for explicit approval
6. Proceed only after approval
