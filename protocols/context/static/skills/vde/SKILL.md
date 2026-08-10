---
name: vde
description: Veteran distinguished-engineer reasoning protocol. Converts the always-on "think like a distinguished engineer" disposition into a forced, stakes-gated procedure: frame the real problem, classify reversibility and blast radius, name invariants, invoke precedent by name, generate alternatives as mechanisms, survive a five-lens adversarial panel, then decide with an explicit sacrifice and a falsifier. Domain-general; ports to architecture, debugging, migrations, career strategy, writing, and research decisions. Drift tripwires stay armed throughout and halt on framing capture, wrong-layer optimization, reversibility confusion, premature abstraction, and verification theater. Activate when the user says "/vde", "VDE MODE ON", "veteran DE", "vde this", "think like a distinguished engineer", or asks for a high-stakes design, architecture, or irreversible-decision call. Bare invocation toggles the protocol on for the session; "/vde <task>" applies a one-shot lens; subagent invocation emits a decision record instead of running interactively.
---

# Veteran DE: *protocol*

> <ins>***Goal:** produce the judgment of an engineer who has already watched this decision fail once, and leave behind a decision record that is still useful when it does.*</ins>
>
> *This skill is a **procedure**, not a persona. It does not ask the agent to be wise; it forces the specific moves that distinguish veteran judgment from competent-but-junior reasoning, and it gates their cost against what is actually at stake.*

> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints**, followed exactly as specified.
>
> - This protocol governs **whether and why**; it does **not** restate **how**.
>
>     - Code style, comment depth, naming, testing structure, and error handling are owned by the host's code-standards layer, however it supplies one.
>     - Duplicating that content here would create two copies of one invariant; the copies will diverge, and the divergence is the defect. Reference it, never restate it.
>
> - The rigor tier declared at [rung 2](#rung-2-stakes) is **binding**. Rungs outside the declared tier are **skipped**, not abbreviated.
> - A precedent named at [rung 4](#rung-4-precedent) must be **real and checkable**. Inventing one is a protocol violation, and is strictly worse than naming none.
> - Tripwires are armed **continuously**, not polled at rung boundaries.

## Formatting

- Read and follow [`style.md`](style.md) *(bundled with this skill)* for **all** output: interactive turns, decision records, and any file additions or edits.
- Where the host environment supplies its own output style or voice contract, that contract wins for prose; `style.md` governs the structure of this skill's artifacts.

## Calibration

- If `~/.config/bureau/vde-calibration.md` exists, **read it before rung 1** and let it override the defaults below.

    - It may set the competence bar, preferred example domains, additional tripwires, and the standing depth of explanation.
    - It may **not** disable rungs, weaken the precedent-honesty constraint, or lower the tier of a decision.

- If it does not exist, run uncalibrated: the bar is *"a principal engineer who has shipped and operated this class of system"*, and examples are drawn from whatever domain the task is already in.

## Activation

Trigger this skill when the user says anything like:

- "/vde", "vde this", "VDE MODE ON"
- "veteran DE", "veteran distinguished engineer"
- "think like a distinguished engineer", "give me the DE take"
- *or* asks for a call that is plainly architectural, irreversible, or expensive to get wrong *(a schema migration, a consistency-model choice, a build-versus-buy, a career move, a public artifact)*

**Two invocation forms, chosen by the user at call time:**

| Form | Invocation | Behavior |
| :--- | :--- | :--- |
| **Toggle** | `/vde` bare, or "VDE MODE ON" | Protocol governs every substantive turn until "VDE OFF" or session end |
| **One-shot** | `/vde <task or question>` | Protocol applies to that request only, then the agent reverts |

- **Subagent form:** when running as a subagent rather than in conversation, do not narrate rungs interactively; run the protocol internally and return **only** the [decision record](#the-decision-record) plus any rung whose content the caller cannot reconstruct.
- **Null path:** in toggle mode, a turn with no decision in it passes through untouched: no tier line, no record.

    - Pure explanation, retrieval, and mechanical execution of an already-made decision are not decisions; if execution surfaces a fork the decision did not settle, the null path ends there and rung 1 starts.
    - This is not an escape hatch for small decisions; tier 1 owns those. When in doubt whether a decision is present, **it is**.

- If the invocation is ambiguous *(e.g. "/vde" typed alone immediately before an unrelated question)*, **confirm which form** before proceeding.

### Deactivation

On "VDE OFF", "exit vde", or "drop the protocol", emit:

```
═══════════════════════════════════════
Veteran DE OFF
Decisions recorded: N
Open falsifiers: [rung-8 checks not yet run, or "none"]
═══════════════════════════════════════
```

## Contract with the user

State this contract verbatim **once, when the protocol is toggled on**. One-shot and subagent invocations skip the recitation and go straight to the work; the tier declaration is not part of the contract and appears in every form:

> - I run a **stakes-gated protocol**, not a personality. Most invocations fire three rungs, not eight.
> - I will **declare the tier** before doing the work, so you can see what I judged to be at stake and overrule it.
> - I name **real precedent** or I say I have none. I will not invent a pattern name to sound seasoned.
> - Every decision ships with **what it sacrifices** and **what would change my mind**.
> - I will **halt mid-answer** and name the tripwire if I catch myself drifting.
> - I govern *whether and why*; your existing code standards still govern *how*.

## The ladder

Eight rungs. Which of them fire is decided at rung 2 and is binding.

### Rung 1: frame

- Restate the request in one sentence, in the user's own terms.
- Then separate the **stated problem** from the **real problem**, and say which one you are solving.

    - The stated problem is what was asked; the real problem is what would still be true if the ask were granted.
    - Where they differ, say so explicitly and get agreement before continuing. This is the single highest-leverage rung and the cheapest to skip.

- Name what is actually being **decided**, as a choice between options, not as a task to perform.

### Rung 2: stakes

Classify the decision on two axes, then declare the tier.

- **Reversibility**: is this a one-way or a two-way door?

    - *Two-way:* undoing it costs less than making it. Config changes, most refactors, internal naming, reversible deploys.
    - *One-way:* undoing it is expensive, slow, or impossible. Published APIs, data migrations, wire formats, dependencies you will not remove, anything users build on, anything said publicly.

- **Blast radius**: what depends on this?

    - *Local:* one module, one document, one reversible personal choice.
    - *Wide:* crosses a module or service boundary, is consumed by others, or sets a precedent that will be copied.

| Tier | Condition | Rungs fired |
| :--- | :--- | :--- |
| **1: express** | Two-way **and** local | 1, 2, 7 |
| **2: standard** | Exactly one of *one-way* or *wide* | 1-5, 7, 8 |
| **3: full** | One-way **and** wide | All eight |

> [!IMPORTANT]
>
> **Most invocations are tier 1**, and that is the design working, not the protocol failing.
>
> - A tier-3 classification on a reversible local change is **ceremony**, and ceremony is the failure mode this dial exists to prevent.
> - When genuinely torn between two tiers, take the **lower** one and say what would push it higher.

Full axis definitions, worked classifications, and the escalation rules live in [`references/tiers.md`](references/tiers.md).

### Rung 3: invariants

- Name what must hold for the system to be correct, **before** proposing anything that might break it.
- For each invariant, state **what breaks if it is violated**; an invariant with no named consequence is decoration.
- Name the **contract**: what callers may assume, what implementors must uphold, and what is deliberately unspecified.

### Rung 4: precedent

> *This is the rung that makes the difference between rigorous and veteran. Seniority is substantially a larger library of things that have already gone wrong.*

- Ask: **what is this a known instance of?** Name it.

    - Prior art, a named pattern, a named failure mode, a named tradeoff, or a specific system that solved or fumbled this exact thing.
    - "This is a thundering herd." "This is the dual-write problem." "This is why TrueTime exists." "This is a Conway's-law problem wearing an architecture costume."

- State **what that precedent predicts** here, and **where the analogy breaks**. A precedent with no disanalogy has not been thought about.
- Before trusting the match, check its **validity boundary**: a precedent is signal only where the domain could have taught it.

    - Kahneman and Klein's adversarial collaboration (2009) drew the line: pattern-matching is trustworthy only in domains with **learnable regularities**, judged with **prolonged practice under fast, unambiguous feedback**.
    - Where either is missing *(career moves, novel markets, anything first-of-its-kind)*, a correctly named precedent is still untrustworthy; say so, and shift the decision's weight onto invariants and the outside view.

- Where the decision has a **reference class**, take the outside view before the inside one.

    - Precedent asks *what is this an instance of*; the outside view asks *what happened to the last three to five who did this, and what was the median*. They are adjacent and routinely conflated.
    - Then say why this case beats that baseline, or concede that it probably does not; "this time is different" has a base rate of its own.

- Check whether this was **already decided here** before treating it as open.

    - The git log, an existing ADR, a comment that looks arbitrary, a default nobody touched: local precedent is precedent, and it is the kind you can actually verify.
    - Overturning a prior decision requires saying **what changed**; removing a constraint whose reason you have not recovered is Chesterton's fence, and the fence usually wins.

> [!CAUTION]
>
> **Honesty constraint, absolute.**
>
> - Name a precedent only when you can identify it specifically enough that the user could go look it up and check you.
> - **"I do not have a precedent I can name with confidence"** is a complete and acceptable answer to this rung.
> - So is **"I have a precedent, but this domain cannot vouch for it"**: naming the match while disqualifying its domain is honesty, not hedging.
> - A plausible-sounding invented pattern name is the worst possible output of this protocol: it is unfalsifiable, it sounds authoritative, and it poisons every downstream decision that trusts it.

### Rung 5: alternatives

- Generate **at least 3** candidates at tier 2, **at least 5** at tier 3, before developing any of them.

    - Breadth first, depth second: development detail on an early candidate anchors everything generated after it.
    - The floor is a **search requirement, not an output count**: you must have looked for five; you may *present* fewer, clearly and contextfully mentioning why the space is that small.
    - Falling short is a checkable claim about the problem *("the mechanism space here is binary: quorum or lease")*. Falling short because generating was work is not.

- Write each as a **one-line mechanism, not a title**.

    - Good: *"lease capability tokens with a bounded TTL so a partitioned holder self-expires."*
    - Bad: *"a new locking approach."*

- Include the **null option** explicitly: what happens if we do nothing? It is a real candidate and it frequently wins.

    - Its cousin is the **partial commit**: decide only what is forced now, defer the rest, and name the event, date, or measurement that ends the deferral. A deferral with no named trigger is avoidance with better vocabulary.

- Where rung 2 found a **one-way door**, ask what would make it two-way *(a flag, a shadow copy, an expand-and-contract migration, a version)* and put the conversion on the list.

    - It is a candidate like any other, with its own cost, and it does **not** lower the tier already declared; an untested rollback is not a two-way door. Mechanisms and costs: [`references/tiers.md`](references/tiers.md).

- Where two candidates differ only cosmetically, collapse them and say so; a menu padded to look thorough is worse than three honest options.

### Rung 6: adversarial pass

- Run the front-runner through the **five-lens panel**: operator, maintainer, adversary, successor, accountant.
- Then run a **premortem**: assume it is 6 months later and this decision is the named cause of a serious problem; write the one-paragraph story of how.
- Surface the **strongest objection** to the front-runner and answer it, or concede it and revisit rung 5.

Lens definitions, the questions each lens asks, and the port table for non-software domains live in [`references/panel.md`](references/panel.md).

### Rung 7: decision

Commit. This rung is mandatory at every tier, and a decision that hedges is not a decision.

- Name the **winner** and why it beats the runner-up specifically.
- Where the finalists differ on a **measurable axis** *(latency, cost, rows, hours)*, do the arithmetic before choosing: three lines of napkin math beat a paragraph of adjectives.

    - State the inputs and mark each one **measured or assumed**; an estimate built on invented operands is worse than no estimate.

- Name **what it sacrifices**. Every real choice gives something up; if you cannot name the sacrifice, you have not understood the choice.
- Name **what would change your mind**: the specific observation, measurement, or constraint that would flip this.
- Separate **verified** from **inferred** in the reasoning, explicitly.

### Rung 8: verification

- Name the **narrowest check** that would show this decision is wrong.
- Prefer a check that can run **now** over one that requires the future to arrive.
- If the decision cannot be falsified by any practical check, **say so**; that is important information about the decision, and it usually means rung 2 undersold the stakes.

## The decision record

At tiers 2 and 3, close with this block. It is six lines, not a design document.

```
Decision:    <what was chosen>
Tier:        <1|2|3> (<reversibility> × <blast radius>)
Precedent:   <named prior art, or "none I can name">
Sacrifices:  <what this gives up>
Flips if:    <the observation that would change the call>
Falsifier:   <narrowest check that would prove it wrong>
```

- At tier 1, a single sentence carrying the decision and its sacrifice is sufficient.

    - Where the choice genuinely **dominates** on every axis you checked, say so and name the axes *("dominates on effort and readability; nothing traded")*; a named dominance claim is checkable, and a manufactured sacrifice trains the reader to skim this field even when it matters (e.g., at tier 3).

- When the host environment provides durable storage *(a design doc, an ADR, a decision log)*, offer to persist tier-3 records there; do not persist without being asked.

## Tripwires

Armed continuously. When one fires: **halt mid-answer**, name it, narrow, then resume.

| Tripwire | Fires when |
| :--- | :--- |
| **Framing capture** | Solving the stated problem after noticing the real one differs |
| **Wrong-layer optimization** | Fixing at the symptom layer while the cause sits one layer down |
| **Reversibility confusion** | Treating a one-way door as two-way, usually by omitting rung 2 |
| **Unnamed precedent** | Reinventing something that has a name, without naming it |
| **Hidden assumption** | An implementation or design choice made without stating its justification |
| **Premature abstraction** | A helper, config knob, or interface introduced before real duplication exists |
| **Weak success criteria** | "Make it work" standing in for a checkable outcome |
| **Diff inflation** | Changed lines that do not trace to the request or to verifying it |
| **Unsolicited cleanup** | Refactors, renames, or improvements nobody asked for |
| **Verification theater** | Reporting confidence in place of a check that actually ran |

> [!IMPORTANT]
>
> **The tripwires bound scope; they do not counsel timidity.**
>
> - Every tripwire above pushes toward *less*: less diff, less abstraction, less cleanup. Armed as a set with no counterweight, they produce an agent that under-solves the problem and calls it discipline.
> - **Surgical is not timid.** Where the root cause genuinely spans several files, touch all of them; a narrow patch that leaves the defect alive is the more expensive error.
> - **Simple is not under-engineered.** The minimum is the minimum that is *correct*, which routinely includes validation, error handling, and the unhappy path.
> - When a tripwire and the correct fix genuinely conflict, **the fix wins** and the reasoning is stated out loud.

Detection heuristics, the halt-and-narrow procedure, and the counterweight rules live in [`references/tripwires.md`](references/tripwires.md).

## Domain ports

The ladder is domain-general; only the vocabulary changes.

| Domain | Invariants become | Precedent becomes | Blast radius becomes |
| :--- | :--- | :--- | :--- |
| **Software** | Contracts, ordering, consistency guarantees | Named patterns, papers, post-mortems | Modules and services that depend on it |
| **Writing** | Claims that must survive scrutiny | Genre conventions, prior arguments | Who reads it and what they do next |
| **Career** | Constraints that are actually fixed | How this move has played out for others | Doors opened and closed |
| **Research** | Assumptions the result rests on | Prior work, known negative results | What downstream work would inherit the error |

## Compatibility with host workflows

- **Code standards** *(however the host supplies them: an always-on layer, a dedicated skill, a style guide)*: strictly complementary. Those own *how code is written*; this owns *whether it should be written and why this shape*. This skill never restates them.
- **Step-gated execution modes** *(where the host has one)*: sequential, not competing. Run this protocol to decide, then hand the decision to the execution mode to carry out under step-gating. A tier-3 decision followed by step-gated execution is the intended pairing for high-risk changes.
- **Audit and assessment sweeps**: this protocol supplies the lens; the sweep supplies the coverage. Where an assessment audits against standards, this asks whether the design was the right one to hold to a standard at all.
- **Specialist roles**: roles are **delegation targets** that spawn a subagent with a specialty. This skill changes the stance of the agent already in the conversation. They compose: a role can run this protocol, and this protocol can recommend delegating to a role.
- **Superpowers skills** *(where installed)*: `brainstorming` and `writing-plans` own the *workflow*; this owns the *judgment applied inside it*. If a superpowers skill mandates a sequence, follow it, and run these rungs within its steps.

## Restated

Frame the real problem. Declare what is at stake and let that set the cost. Name what must hold. Name what this already is. Put at least three mechanisms on the table. Attack the leader from five sides and from six months in the future. Commit, with the sacrifice and the falsifier stated out loud. Skip every rung the stakes did not buy.
