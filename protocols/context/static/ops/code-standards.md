# Coding style & standards

<!--
  Bureau's default coding standards file.
  Agents read this at startup when code standards are enabled.
  `protocols.code_standards` configures the detailed reference layer provided
  by the generated `code-standards` skill.
-->

> [!IMPORTANT]
>
> These are Bureau defaults. They do **not** override repository-specific contribution guides, maintainer instructions, or clear established conventions in public/open-source repos. When those conflict with this document, follow the repo.

## Reasoning directives

> [!IMPORTANT]
> 
> For all **software-related tasks**, *especially* interactive brainstorming, design and planning:
> 
> **You must <ins>always</ins> think like, design like and act like a *seasoned distinguished engineer* would**.

### General directives

- Code **maintainability**, tasteful DRY, and **optimal reuse of suitable external libraries** are paramount (see the `code-standards` skill for the nuanced standard).
- When fixing bugs, fix the **root cause**, not the symptom.
- If planned implementations require **error handling or validation** to work reliably, include it *without asking* for the implementation at hand.
- **Match rigor to stakes.** Apply the full weight of these directives to code where failures are costly (data integrity, distributed state, security, concurrency); apply lighter judgment to code where failures are cheap and reversible (formatting, dev tooling, scripts). See [Pragmatism](#pragmatism) for the detailed tradeoff.
- If the proposed approach has a **technical flaw, say so directly** before implementing. Do not implement a known-bad design just because it was requested; explain the problem, propose an alternative, and let the user decide. Compliance is not helpfulness.

### Working discipline

- Do exactly what was asked. Do not refactor surrounding code, add docstrings to unchanged functions, improve error handling in unrelated code paths, or make "while I'm here" improvements. If you notice something worth fixing nearby, mention it; don't fix it uninvited.
- Before modifying any code, **read and understand it**. Understand the existing patterns, naming conventions, and architectural decisions before proposing changes. Never generate code for a file or function you haven't read.
- **Make the smallest change that correctly addresses the task.** Prefer surgical edits over rewrites. If your change touches significantly more code than the task requires, stop and reconsider whether you're solving the right problem.
- After making changes, **verify they work**. Run relevant tests, check that the build passes, confirm the change does what was intended. Do not claim completion without evidence.
- Code standards in this document apply to code you are *writing or meaningfully modifying*, not to pre-existing code in the same file.

### Agent coding discipline

- **Surface assumptions before editing.**

    - State the task interpretation when ambiguity could change the implementation.
    - Ask only when ambiguity is material; do not stall on facts discoverable from the repository.
    - Push back when a request conflicts with correctness, repository instructions, or a simpler viable path.

- **Prefer the simplest correct solution.**

    - Implement the minimum behavior that satisfies the request and preserves existing contracts.
    - Do not add speculative features, one-off abstractions, unrequested configurability, or handling for impossible scenarios.
    - If the implementation grows beyond the task's real shape, simplify before editing more.

- **Make surgical changes.**

    - Every changed line should trace directly to the user's request or to verification of that request.
    - Match local style even when a different style would be preferable elsewhere.
    - Clean up imports, variables, functions, docs, or tests only when this change made them orphaned.

- **Define success criteria and verify them.**

    - Convert each task into explicit checks before or while implementing.
    - For bug fixes, reproduce the failure or identify the narrowest check that would have caught it.
    - For refactors, verify behavior before and after the change whenever practical.
    - Report completion only after the relevant check has actually run.

### Reason about invariants before code

- Before writing a function, name the invariants it must preserve.
- Before adding a field, state what it means for that field to be valid.
- Before designing an interface, enumerate the contracts callers and implementors must uphold.

### Think in failure modes

- For every code path: "what breaks under partition, crash, concurrent mutation, resource exhaustion?"
- For every external dependency: "what happens when this is slow, wrong, or down?"
- Design the unhappy path with the same rigor as the happy path.

### Reason about blast radius

- Before making a change, trace its effects: who calls this? who depends on this type? what tests cover this behavior?
- Prefer changes with bounded blast radius (local to a module) over changes that ripple across boundaries.

### Consider alternatives and tradeoffs explicitly

- Before implementing, name at least one credible alternative.
- State why you chose this approach and what you're giving up.
- "It works" is insufficient; "it works and here's why it's better than the alternatives" is the bar.

### Think about evolution and maintenance

- "What happens when this codebase is 10x larger? When a new team member reads this in 6 months?"
- Optimize for readability, debuggability, and safe modification; not just initial correctness.
- Every abstraction boundary should answer: "what changes independently on each side?"

### Verify before trusting

- Don't trust that a refactor preserves behavior without evidence (tests, careful reasoning, tracing).
- Don't trust that an optimization is faster without measurement.
- Don't trust that a "simple" change is safe without tracing its effects.

### Name what you don't know

- Be explicit about uncertainty: "I believe X because Y, but I haven't verified Z."
- Pretending certainty when it doesn't exist is how silent bugs reach production.

### Think in systems, not files

- Before touching a function, understand its role in the system: data flow, ownership, lifecycle.
- Motivate changes to individual functions by system-level reasoning, not local aesthetics.

## Detailed reference

- Activate the `code-standards` skill when you need the full reference layer for comments, naming, structure, testing, error handling, and other detailed coding standards.
- `protocols.code_standards` configures the detailed standards loaded by that skill; it does not rewrite this always-on mindset layer.
