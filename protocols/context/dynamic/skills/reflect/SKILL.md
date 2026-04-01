---
name: reflect
description: >-
  Activate when you consider a deliverable done -- an implementation, plan,
  review, research result, or skill draft. Also activate when you are about to
  present work as final, declare a task complete, or commit/push a result.
  Triggers on phrases like "I think this is ready", "this looks complete",
  "let me present the results", or internal satisfaction with output quality.
  Do NOT activate for trivial edits, typo fixes, or mechanical changes where
  the risk of unreviewed work is negligible.
---

# Reflect: structured self-review before declaring work done

> **Goal:** never present unreviewed work as final. Before any deliverable
> leaves your hands, apply three independent lenses -- completeness,
> correctness, and fitness -- and produce specific, actionable objections or an
> explicit confirmation that the work survives scrutiny.
>
> This skill exists because agents routinely conflate "I finished writing it"
> with "it is good." The gap between those two states is where the most
> consequential defects live.

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed
> **exactly as they are specified**.
>
> Violating the letter of these rules is violating the spirit of these rules.

## Activation / deactivation

### Self-activation triggers

Reflect activates when **any** of the following are true:

- You are about to declare a deliverable "done" or "complete"
- You are about to present results to the user as final
- You are about to commit, push, or create a PR containing your work
- You are about to hand off a deliverable to another agent or skill
- The user explicitly says "reflect on this", "review your work", or "self-review"

### Trivial-work exemption

Reflect does **not** activate for:

- Single-line typo fixes, comment edits, or import reordering
- Mechanical renames with no behavioral change
- Running a command the user explicitly dictated verbatim

If you are unsure whether the work is trivial, it is not trivial. Reflect.

### Deactivation

Reflect is a one-shot workflow. It activates, runs the three lenses, produces
objections or confirmation, and completes. There is no persistent mode.

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill
unless the dispatching agent explicitly included "reflect on your output" in
your task prompt. Subagents performing narrow, well-specified tasks should not
self-reflect -- the dispatching agent owns the reflection responsibility.
</SUBAGENT-STOP>

## Definitions

- **Deliverable**: any artifact you are about to declare finished -- code,
  plan, analysis, review, research result, skill draft, dossier digest, or
  structured recommendation.

- **Lens**: one of three independent evaluation perspectives (completeness,
  correctness, fitness). Each lens asks a fundamentally different question.
  They are separate because agents naturally conflate "works correctly" with
  "is good" and "is good" with "did everything asked."

- **Objection**: a specific, actionable criticism with enough detail that the
  fix is obvious. "Consider edge cases" is not an objection. "The function
  `parse_config` silently returns `None` when the file is missing instead of
  raising `FileNotFoundError`, which will cause a cryptic `AttributeError` 14
  lines later in `load_pipeline`" is an objection.

- **Convergence**: the state where a revision cycle produces no new objections,
  or produces only objections that repeat from a previous cycle. Convergence
  means stop.

- **Sycophantic confirmation**: declaring work "looks good" without having
  genuinely attempted to find flaws. This is the primary failure mode Reflect
  exists to prevent.

## Phase 1: Snapshot

Establish what you are reviewing before you review it.

### Steps

1. Identify the deliverable. What specific artifact are you about to declare
   done? Name it concretely -- "the `parse_config` function in `loader.py`",
   "the migration plan for the dossier schema", "the research findings on
   embedding models."

2. State the acceptance criteria. What did the user (or dispatching agent)
   ask for? What explicit and implicit requirements exist? If the request was
   vague, state what you interpreted the requirements to be.

3. Note your confidence. Before applying any lens, honestly assess: how
   confident are you that this work is correct and complete? Record this as
   `HIGH`, `MEDIUM`, or `LOW`. This is for your own calibration -- high
   confidence is where sycophantic confirmation is most dangerous.

### Phase 1 escalation

- DONE -> proceed to Phase 2
- NEEDS_CONTEXT -> the deliverable or its requirements are ambiguous; ask the
  user to clarify before reflecting
- BLOCKED -> the deliverable cannot be identified (e.g., no work was done);
  do not force a reflection on nothing

## Phase 2: Three lenses

Apply each lens independently. Do not merge them. Do not skip one because
another "covers it." Each lens asks a fundamentally different question.

BEFORE producing any lens output:
  Ask: "Am I genuinely looking for flaws, or am I constructing reasons
  why the work is fine?"
  IF you notice yourself reaching for reasons the work is acceptable
  before you have examined it critically:
    STOP -- you are exhibiting sycophantic confirmation. Reset. Start
    the lens with the assumption that a defect exists and try to find it.
    Only after a genuine search fails to find defects should you confirm.

### Lens 1: Completeness

> *Did I do everything that was asked?*

1. List every explicit requirement from the user's request or task prompt.
2. For each requirement, identify the specific part of the deliverable that
   satisfies it. If you cannot point to a concrete artifact, the requirement
   is unsatisfied.
3. Check for implicit requirements: error handling, edge cases, documentation
   updates, test coverage, configuration changes.
4. Produce objections for any unsatisfied requirement, explicit or implicit.

### Lens 2: Correctness

> *Is what I did actually right?*

1. Trace the logic of the deliverable. For code, follow the execution path
   mentally. For plans, follow the dependency chain. For research, check the
   reasoning chain.
2. Identify assumptions you made during creation. Are they valid? Are they
   documented?
3. Check for the "works on the happy path" trap: does the deliverable handle
   failure modes, edge cases, invalid inputs, and concurrent access where
   relevant?
4. Produce objections for any logical errors, unvalidated assumptions, or
   missing error handling.

### Lens 3: Fitness

> *Is this the right approach for this context?*

1. Step back from the implementation details. Given the project's
   architecture, constraints, conventions, and goals -- is this deliverable
   well-fitted to its environment?
2. Check for over-engineering: did you build abstractions that are not
   justified by the current requirements?
3. Check for under-engineering: did you take shortcuts that will create
   technical debt disproportionate to the time saved?
4. Check for convention violations: does this deliverable follow the patterns
   established in the surrounding codebase?
5. Produce objections for any fitness issues. Distinguish between "this is
   wrong for the context" (must-fix) and "this could be better-fitted"
   (consider).

### Phase 2 output format

After applying all three lenses, produce a structured summary:

```
REFLECT: <deliverable name>
Confidence: <HIGH|MEDIUM|LOW> (from Phase 1)

Completeness:
- [PASS|OBJECTION] <requirement 1>: <status or objection>
- [PASS|OBJECTION] <requirement 2>: <status or objection>

Correctness:
- [PASS|OBJECTION] <aspect 1>: <status or objection>
- [PASS|OBJECTION] <aspect 2>: <status or objection>

Fitness:
- [PASS|OBJECTION] <aspect 1>: <status or objection>
- [PASS|OBJECTION] <aspect 2>: <status or objection>

Verdict: CONFIRM | REVISE (N objections)
```

### Phase 2 escalation

- DONE (no objections) -> proceed to Phase 4 (confirmation)
- DONE_WITH_CONCERNS (objections found) -> proceed to Phase 3 (revision)
- NEEDS_CONTEXT -> a lens cannot be applied without additional information;
  ask and then re-apply that lens
- BLOCKED -> the deliverable is fundamentally unsound; report to the user
  rather than attempting revision

## Phase 3: Revision cycle

Address objections and re-evaluate. This phase exists to prevent the failure
mode where objections are identified but not acted on.

### Steps

1. For each objection rated as a must-fix or clear improvement, revise the
   deliverable.
2. For objections that are judgment calls ("could be better"), decide
   explicitly: revise or accept. State your reasoning. "This is fine for now
   because the current scope does not justify the investment" is acceptable.
   "This is fine" without reasoning is not.
3. After revision, re-apply **only the lenses that produced objections**.
   Do not re-run lenses that passed cleanly.

### Convergence gate

BEFORE starting another revision cycle:
  Ask: "Are the objections from this cycle genuinely new, or are they
  the same issues I already addressed?"
  IF the same objections recur after revision:
    STOP -- you have reached convergence. The remaining objections are
    either unfixable within the current scope or reflect a disagreement
    you cannot resolve alone. Report them as known limitations and proceed
    to Phase 4.

**Hard limit: 3 revision cycles maximum.** If convergence has not been
reached after 3 cycles, stop, report remaining objections as known
limitations, and proceed to Phase 4. Non-convergence after 3 cycles
indicates a structural problem that reflection alone cannot solve.

### Phase 3 escalation

- DONE -> proceed to Phase 4
- DONE_WITH_CONCERNS -> proceed to Phase 4 with known limitations documented
- BLOCKED -> revision reveals the deliverable needs fundamental rework;
  report to the user

## Phase 4: Confirmation or report

Conclude the reflection with an explicit statement.

### Steps

1. If no objections remain (or all were addressed): state
   **"Reflection complete. Deliverable confirmed."** and briefly note what
   the lenses verified.

2. If known limitations remain: state
   **"Reflection complete with known limitations:"** and list each limitation
   with its severity and the reason it was not addressed.

3. Present the deliverable to the user or proceed with the commit/handoff.

Never present work as final without one of these two explicit statements.
This is the core invariant: **no deliverable leaves your hands without an
explicit reflection verdict.**

### Phase 4 escalation

- DONE -> the skill is complete
- DONE_WITH_CONCERNS -> the skill is complete; concerns are documented in the
  output

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "This change is too small to need reflection." | Small changes break systems. A one-line config change can take down production. The three lenses take 30 seconds on small deliverables. If it is truly trivial, the trivial-work exemption in the activation section covers it -- but if you are reading this table, you already activated the skill, so apply it. |
| "I already reviewed this mentally while writing it." | You reviewed it with the same mental model that produced it. The three lenses force a perspective shift. The defects you find in your own work are the ones your creation mindset is blind to. |
| "The user is waiting and I should not delay." | Presenting flawed work wastes more of the user's time than a 60-second reflection. The user would rather wait 60 seconds than debug your oversight for 30 minutes. |
| "I am confident this is correct, so I will just confirm quickly." | High confidence is exactly when sycophantic confirmation is most dangerous. Confidence is not evidence. Apply the lenses anyway -- they exist to catch what confidence misses. |
| "The requirements were vague, so I cannot really check completeness." | Vague requirements make the completeness lens more important, not less. State what you interpreted the requirements to be, then check against your interpretation. Surfacing the interpretation gap is itself valuable. |
| "I will fix any issues in the next iteration." | There may not be a next iteration. The user may ship what you hand them. Treat every deliverable as final. |
| "Reflection on this type of work feels forced -- it is not code, it is just a plan." | Plans, research results, and recommendations contain the highest-impact defects because they cascade. A flawed plan produces flawed implementations across multiple files. Reflect applies to all deliverable types equally. |
| "The fitness lens does not apply here because there is no existing codebase context." | The fitness lens always applies. Even greenfield work has constraints: the user's stated goals, the project's technology choices, the conventions established by the first files written. Fitness means "right for the context," and context always exists. |
| "I already found and fixed issues during creation, so a separate reflection pass is redundant." | Finding issues during creation is editing. Reflection is a distinct cognitive mode: you step back from the creator role and adopt the reviewer role. The perspective shift is the mechanism. Skipping it because you edited along the way defeats the purpose. |
| "Running all three lenses would produce the same findings -- I will just do a general review." | The lenses are separated precisely because merging them causes agents to conflate completeness, correctness, and fitness. A deliverable can be complete and correct but unfit for the context. A merged review misses this. |

## Red flags -- STOP

If you notice any of these, stop and restart the current phase:

- You are writing "looks good" or "this appears correct" without having
  identified a single specific aspect you verified. Generic approval is the
  hallmark of sycophantic confirmation.

- You are feeling resistance to applying a lens because you "already know"
  the deliverable is fine. That feeling of certainty without examination is
  exactly what this skill is designed to interrupt.

- You are about to list only positive observations under a lens. Each lens
  is a search for flaws. If a genuine search finds none, that is a valid
  result -- but the search must happen first.

- You are constructing your confirmation before finishing the evaluation.
  If you already know your verdict while still in Phase 2, you are
  rationalizing, not reflecting.

- You are thinking "this deliverable is different because..." as a reason
  to skip or abbreviate a lens. The lenses are universal. The deliverable
  is not special.

- You are about to declare "no objections" on all three lenses for a
  non-trivial deliverable. This is statistically unlikely and warrants a
  second, harder look. Most non-trivial work has at least one fitness
  observation worth noting.

- You are generating vague objections like "consider edge cases" or "could
  use more testing" to appear thorough without doing real work. Vague
  objections are worse than none -- they create the illusion of rigor
  without the substance.

- You are about to skip Phase 3 because "the objections are minor." If they
  are genuinely minor, the revision will be quick. If you are skipping
  revision, you did not take the objections seriously.

## Verification

Before declaring this workflow complete, verify:

- [ ] All three lenses were applied independently (completeness, correctness,
  fitness) -- not merged into a single review pass
- [ ] Every objection is specific and actionable -- no vague "consider X"
  entries
- [ ] If objections were found, Phase 3 (revision) was executed or each
  objection was explicitly dispositioned with stated reasoning
- [ ] The deliverable has an explicit reflection verdict: either "confirmed"
  or "confirmed with known limitations"
- [ ] The reflection output follows the structured format from Phase 2
- [ ] If this is a re-reflection (second+ cycle), the objections are genuinely
  new, not restatements of previously addressed issues

## Companion files

| File | Consult when |
|------|-------------|
| `anti-sycophancy-gates.md` | You suspect your reflection is confirming rather than critiquing, or when reviewing a deliverable where you have high confidence |

## Composability

### With Dispatch

Reflect validates Dispatch's reconciliation results. When Dispatch completes
a reconciliation of subagent outputs, Reflect takes the reconciled deliverable
as input and applies the three lenses. The interface is clean: Reflect
receives a deliverable and produces either a confirmation or specific
objections. Dispatch does not need to know how Reflect works internally.

### With other skills

- **Assess mode**: Reflect operates on your own work; assess-mode reviews
  others' code. If assess-mode produces findings, Reflect verifies your
  fixes to those findings before you declare them resolved.
- **Micro mode**: Each micro edit is too granular for full reflection. Reflect
  applies at the end of a micro-mode session, on the complete changeset.
- **Fold**: Before folding, Reflect can verify the dossier digest captures
  all critical context (apply completeness lens to the digest).

## Final rule

> Never present unreviewed work as final. Every non-trivial deliverable
> receives three independent lenses -- completeness, correctness, fitness --
> and an explicit verdict before it leaves your hands.
