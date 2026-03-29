# Micro Mode Explain Keys — Design Spec

> **Status:** Draft
> **Date:** 2026-03-29
> **Scope:** Additive feature to `protocols/context/static/skills/micro-mode/SKILL.md`

## Context

Micro mode provides step-gated editing with a pause point after every micro edit. Currently, the pause point offers two actions: advance (via resumption tokens `>` / `.`) or course-correct (via revert/redo). There is no mechanism for the user to interrogate *why* a change was made, whether it's optimal, or how it fits into the broader codebase — without breaking out of micro mode.

This spec adds **explain keys**: a set of single-character keys available at every pause point that produce distinguished-engineer-level explanations along four orthogonal axes, with progressive depth on repeat and combinable in a single prompt.

## Goals

- Let users interrogate any micro edit along four axes: repo context, syntax/idioms, design reasoning, and optimality assessment
- Set an uncompromising quality bar via user-agnostic prescriptive directives (not user profiling)
- Support progressive depth via repeat presses and multi-axis queries via key combinations
- Surface flaws or improvements discovered during explanation, without forcing action
- Integrate cleanly into the existing skill file with zero changes to the execution loop, DAG protocols, or scheduling

## Non-goals

- Prescriptive depth tiers or explicit tier counts per axis — frontier models calibrate depth naturally
- User profiling or adaptive difficulty — the quality bar is intrinsic to the spec, not the reader
- Exhaustion boundaries — if the user wants to go deeper, let them; the agent signals naturally when it has nothing new to add

## Design

### 1. Explain keys as an interaction primitive

Five single-character keys, available at every pause point alongside the existing resumption tokens:

| Key | Axis | Mnemonic | Focus |
|-----|------|----------|-------|
| `r` | Repo | **r**epo | Architectural context, design decisions, how this change fits the surrounding codebase |
| `s` | Syntax | **s**yntax | Language-level mechanics, idioms, conventions — whether the edit reflects them and why/why not |
| `t` | Thinking | **t**hinking | DE-level design reasoning, systems thinking, concurrency, hardware considerations |
| `a` | Assessment | **a**ssessment | Optimality verdict — is this change optimal, maintainable, conventional, efficient? |
| `e` | Explain (all) | **e**xplain | Equivalent to `r` + `s` + `t` + `a` combined |

Keyboard ergonomics: all five keys (`r`, `s`, `t`, `a`, `e`) sit in a tight left-hand cluster on QWERTY layouts, enabling fast one-handed input for a feature designed around rapid, repeated single-character interactions.

### 2. Depth counter

Each axis maintains a depth counter scoped to the current pause point:

- Starts at 0 (no explanation requested yet)
- Any key press increments its axis's counter by 1
- Combinations (e.g., `rt`, `sa`) increment all included axes by 1
- `e` increments all four axes by 1
- All counters reset when the user advances with `>` / `.`

### 3. Combination mechanics

- Keys can be combined in any order in a single prompt (e.g., `rt`, `tr`, `sa`, `rsta`)
- Order within a combination does not matter (`rt` = `tr`)
- `rsta` = `e` (incrementing all four is equivalent to the explain-all key)

### 4. Relationship to the pause point

- Explain keys do **not** consume the pause — after receiving the explanation, the user is still at the same pause point and must still use a resumption token (`>` / `.`) to advance
- The user can issue as many explain keys as they want before advancing
- Explain keys are explicitly **not** resumption tokens

### 5. Axis directives

These directives define the purpose, voice, and depth-progression behavior of each axis.

#### `r` — Repo

Explain the change in the context of the surrounding codebase. Where does this code sit in the architecture? What modules, types, or contracts does it interact with? What design decisions in the repo led to this code looking the way it does — and how does the micro edit honor, extend, or intentionally break those decisions?

Each deeper pass should widen the aperture: from the immediate function, to the module, to cross-module interactions, to system-level architectural patterns — revealing context that the previous pass took for granted.

#### `s` — Syntax

Break down the language-level mechanics of the change. What constructs, idioms, and conventions does it use — and are they the right ones? If the edit is idiomatic for the language, say so and explain what makes it idiomatic. If it departs from convention, explain why the departure is justified (or flag it if it isn't). Cover type signatures, control flow, error handling patterns, and any language-specific subtleties (ownership, lifetimes, goroutine semantics, decorator behavior, etc.) that a reader unfamiliar with this language's idioms would miss.

Each deeper pass should become more granular and more foundational: from "what this construct does in context" down to "why this language feature exists and what it compiles/evaluates to."

#### `t` — Thinking

Explain the design reasoning behind the change the way a veteran distinguished engineer would explain it to a peer — not dumbed down, not padded. State the tradeoff that was made, name the alternatives that were not chosen, and explain why this path wins. If systems-level concerns are relevant — concurrency, memory layout, cache behavior, ordering guarantees, failure modes, hardware constraints — they are mandatory, not optional color. This is the axis where "it works" is insufficient; the explanation must address whether it works *for the right reasons* and *under adversarial conditions*.

Each deeper pass should surface reasoning and constraints that the previous pass took for granted — peeling back assumptions until you reach first principles.

#### `a` — Assessment

Deliver a frank verdict on the change's optimality, maintainability, conventionality, and efficiency. Would a distinguished engineer reviewing this change in critical detail and with an eye on the big picture approve it without comment, request modifications, or reject it? Be specific: if optimal, state what makes it so and what would have to change in requirements for it to stop being optimal. If not optimal, name the concrete improvement — not a vague gesture at "could be better," but the specific alternative and why it wins.

Each deeper pass should tighten the lens: from the overall verdict, to specific dimensions (performance, readability, maintainability, robustness), to quantitative or formal reasoning where applicable.

#### `e` — Explain (all)

Equivalent to `r` + `s` + `t` + `a`. Produce a unified explanation that weaves all four axes together where they naturally intersect, rather than presenting four siloed sections. The axes should reinforce each other: architectural context should inform the assessment, syntax should support the design reasoning, and the verdict should be grounded in all three.

#### Cross-axis directive (applies to all axes and combinations)

**Quality bar:** Produce an explanation that would thoroughly pass a veteran distinguished engineer's discerning bullshit radar. No filler. No hedge words used to avoid committing to a position. No "generally speaking" or "it depends" without immediately specifying what it depends *on*. Every sentence must advance the reader's understanding or it does not belong.

**Depth progression:** Each subsequent explanation at a given depth must reveal information not present in any previous explanation at this pause point. Never restate what the step header or step footer already communicated. Never restate what a previous explanation at this pause point already covered — build on it.

**Weaving:** When multiple axes are requested together (via combination keys or `e`), weave them into a cohesive explanation rather than emitting labeled sections. The axes are lenses on the same change, not independent reports.

### 6. Flaw detection protocol

#### When it triggers

During the process of formulating an explanation along any axis, the agent may identify:

- A flaw in the current micro edit (correctness, efficiency, idiom violation, missed edge case)
- A possible improvement to the current micro edit
- An issue with the broader plan (a downstream node's approach is suboptimal given what this explanation revealed, or a missing node that should exist)

#### How it presents

The explanation is emitted first, cleanly and completely. Then, separated by a clear visual break, the flaw/improvement is presented in a distinct block:

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

#### User resolves before advancing

- If the user picks (1): the fix flows into the existing **DAG change protocol** — the agent updates the DAG, logs the change to the user, and the user is still at the same pause point
- If the user picks (2): nothing changes — the user can `>` / `.` to advance or continue exploring with more explain keys
- Multiple findings can each get their own block

#### Integration with DAG change protocol

Flaw detection does not create a parallel change-tracking mechanism. Accepted findings feed directly into the existing DAG change protocol from Phase 2 — same format, same rules, same `deps`/`status` update discipline. Flaw detection is a *discovery* mechanism; the DAG change protocol is the *execution* mechanism.

### 7. Integration points in SKILL.md

The additions are purely additive. No existing content changes semantics.

#### New content

| What | Where in SKILL.md | Rationale |
|------|-------------------|-----------|
| Explain keys definition (keys, axes, depth counter, combinations, pause-point relationship) | New subsection in "Domain-specific terms", after "Resumption tokens" | Same level of interaction primitive |
| Axis directives (table) and cross-axis directive | `###` subsection within "Phase 2: execution", after "End-of-phase verification" and before "Phase 2 protocols" | Phase 2 reference material; directives formatted as table with `<br/>` line breaks |
| Flaw detection protocol | New subsection under "Phase 2 protocols" | Phase 2 behavior that feeds into existing DAG change protocol |

#### Modifications to existing content

| What | Change |
|------|--------|
| Step footer template (execution loop step 7) | Add explain key hint: `Press ">" or "." to continue, or explore with: r · s · t · a · e` |
| Resumption tokens subsection | Add note that explain keys are not resumption tokens and do not advance the DAG |

#### Unchanged

The execution loop, DAG persistence protocol, scheduling protocol, status update protocol, course-correction protocol, revert-by-default rule, and compatibility section all remain untouched.
