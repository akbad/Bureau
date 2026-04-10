# Explain keys reference

## Axis directives

> [!IMPORTANT]
>
> These directives define the **purpose, voice, and depth-progression behavior** of each explain key axis. They are non-negotiable quality standards.

| Axis | Directive |
|------|-----------|
| `r` (*repo*) | Explain the change in the context of the surrounding codebase. Where does this code sit in the architecture? What modules, types, or contracts does it interact with? What design decisions in the repo led to this code looking the way it does, and how does the micro edit honor, extend, or intentionally break those decisions?<br/><br/>*Depth progression:* Each deeper pass should widen the aperture: from the immediate function to the module to cross-module interactions to system-level architectural patterns, revealing context that the previous pass took for granted. |
| `s` (*syntax*) | Break down the language-level mechanics of the change. What constructs, idioms, and conventions does it use, and are they the right ones? If the edit is idiomatic for the language, say so and explain what makes it idiomatic. If it departs from convention, explain why the departure is justified (or flag it if it isn't). Cover type signatures, control flow, error handling patterns, and any language-specific subtleties (ownership, lifetimes, goroutine semantics, decorator behavior, etc.) that a reader unfamiliar with this language's idioms would miss.<br/><br/>*Depth progression:* Each deeper pass should become more granular and more foundational: from "what this construct does in context" down to "why this language feature exists and what it compiles/evaluates to." |
| `t` (*thinking*) | Explain the design reasoning behind the change the way a veteran distinguished engineer would explain it to a peer; not dumbed down, not padded. State the tradeoff that was made, name the alternatives that were not chosen, and explain why this path wins. If systems-level concerns (e.g., concurrency, memory layout, cache behavior, ordering guarantees, failure modes, hardware constraints) are relevant, they are *mandatory* to discuss. The explanation must address whether it works *for the right reasons* and *under adversarial conditions*.<br/><br/>*Depth progression:* Each deeper pass should surface reasoning and constraints that the previous pass took for granted, peeling back assumptions until you reach first principles. |
| `a` (*assessment*) | Deliver a frank verdict on the change's optimality, maintainability, conventionality, and efficiency. Would a distinguished engineer reviewing this change in critical detail and with an eye on the big picture approve it without comment, request modifications, or reject it? Be specific: if optimal, state what makes it so and what would have to change in requirements for it to stop being optimal. If not optimal, name the concrete improvement: a specific alternative and why it wins.<br/><br/>*Depth progression:* Each deeper pass should tighten the lens: from the overall verdict, to specific dimensions (performance, readability, maintainability, robustness), to quantitative or formal reasoning where applicable. |
| `e` (*explain (i.e., all of the above)*) | Produce a unified explanation that weaves all four axes together where they naturally intersect, rather than presenting four siloed sections. The axes should reinforce each other: architectural context should inform the assessment, syntax should support the design reasoning, and the verdict should be grounded in all three. |

## Cross-axis directives

These apply to **all** axes, at **all** depths, for **all** combinations:

1. **Quality bar**

    - Produce an explanation that would thoroughly pass a veteran distinguished engineer's discerning bullshit radar.
    - Every sentence must advance the reader's understanding or it does not belong.

    > **No:**
    >
    > - filler or hedge words used to avoid committing to a position
    > - "generally speaking" or "it depends" without *immediately* specifying what it depends *on*.

2. **Depth progression**

    Each subsequent explanation at a given depth **must:**

    - reveal *new* information not present in any previous explanations at this pause point.
    - build on, and **never** restate (unless the user asks), information in:

        - previous explanations at this pause point
        - the step header
        - the step footer

3. **Weaving**

    When multiple axes are requested together (via combination keys or `e`), weave them into a *cohesive, comprehensive explanation* (rather than emitting labeled sections or independent reports).

## Flaw detection protocol

> Applies when the agent discovers a flaw or improvement opportunity while formulating an explain key response.

- **When this triggers:**

    During the process of formulating an explanation along any axis, the agent may identify:

    - A flaw in the current micro edit (correctness, efficiency, idiom violation, missed edge case)
    - A possible improvement to the current micro edit
    - An issue with the broader plan (a downstream node's approach is suboptimal given what this explanation revealed, or a missing node that should exist)

- **How it presents:**

    1. The explanation is emitted first, cleanly and completely.
    2. Then, **separated by a clear visual break**, the flaw/improvement is presented in a distinct block:

        ```md
        ───────────────────────────────────
        ⚠️ Finding: <one-line summary>

        - What: <description of the flaw or improvement>
        - Impact: <what breaks, degrades, or is left on the table>
        - Suggested fix: <concrete alternative>
        - Scope: <"this edit" | "DAG node <id>" | "new node needed">

        Options:
        (1) Apply fix → [describe what changes]
        (2) Dismiss → continue with current edit as-is
        ───────────────────────────────────
        ```

> [!NOTE]
>
> Multiple findings are presented as *separate blocks*, each with their own options.

### Resolution

- If the user picks **(1)**, the fix flows into the existing DAG change protocol (see `references/phase-2.md`): the agent updates the DAG, logs the change to the user per that protocol's format, and the user remains at the same pause point
- If the user picks **(2)**, nothing changes: the user can advance with `.` or continue exploring with more explain keys

Flaw detection does not create a parallel change-tracking mechanism. It is a *discovery* mechanism; the DAG change protocol is the *execution* mechanism.
