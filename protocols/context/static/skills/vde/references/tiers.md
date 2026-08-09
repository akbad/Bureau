# The rigor tiers

> *The dial exists for one reason: a protocol that costs the same on every question gets skipped on the questions that matter, because the user learned it was not worth invoking.*

## Why this is the load-bearing rung

- The failure mode of every reasoning protocol is **ceremony**: performing rigor on decisions that did not need it, until the performance is all that survives.
- Tiering is what buys the right to be genuinely heavy at tier 3, because tier 3 is rare.
- **Misclassification is the only way this protocol fails badly.** Both directions cost, but they are not symmetric:

    - *Over-classifying* wastes the user's time and trains them to stop invoking the skill.
    - *Under-classifying* ships a one-way door decision with three rungs of thought behind it, which is the exact outcome the protocol exists to prevent.

## Axis 1: reversibility

**The test:** *does undoing this cost less than doing it?*

| | Definition | Examples |
| :--- | :--- | :--- |
| **Two-way door** | Undoing costs less than doing; the cost of being wrong is bounded by the cost of the redo | Internal refactors, config values, naming inside a module, reversible deploys, draft prose, a reversible personal commitment |
| **One-way door** | Undoing is expensive, slow, or impossible; others have already built on it | Published APIs and wire formats, data migrations that drop information, dependencies with deep integration, anything said publicly, anything users now rely on |

**Common misclassifications, in order of frequency:**

- **Data migrations that "can be rolled back"**: the schema can, the *dropped column's data* cannot. If information is destroyed, it is a one-way door regardless of what the migration tooling claims.
- **Internal APIs with external consumers**: "internal" describes intent, not reality. Count the actual callers.
- **Defaults**: changing a default is a two-way door for you and a one-way door for everyone who inherited it silently.
- **Anything published**: a deleted post, a force-pushed commit, and a retracted claim are all one-way doors, because copies and memory persist.
- **Naming**: cheap to change inside a module, effectively permanent once it enters a public vocabulary others speak.
- **Adding an index**: the read it speeds up is local; the write path is not. Every insert now maintains it, the planner may move unrelated queries onto worse plans, and the build blocks writes unless run concurrently. Two-way but **wide**: tier 2.
- **Hypothetical conversions**: a flag or rollback that could exist but has not been built does not make the door two-way. Classify the door in front of you, not the one rung 5 might construct.

## Doors can be *engineered*

**Reversibility is a design *variable*, not just a reading.** The first question at rung 2 is which door this is; the second, owned by rung 5, is what it would cost to change which door it is.

| Mechanism | Converts | Cost it adds |
| :--- | :--- | :--- |
| **Expand and contract** | A destructive schema or interface change into three reversible steps | Two extra deploys; a window where both shapes are live |
| **Feature flag plus canary** | A global cutover into a per-cohort, revertible one | A branch in the code; a flag someone must retire |
| **Shadow reads or dual writes** | A blind cutover into a measured one | A doubled write path; a divergence you must then explain |
| **Versioning** | A breaking change into an additive one | Every version kept alive until the last caller moves |
| **Strangler fig** | A rewrite into a sequence of two-way doors | A seam, a router, and a migration that outlives its sponsor |

- Outside software the move is the same: a pilot with an end date, a trial period, a draft circulated as a draft, a clause with an exit.
- **The conversion is a rung-5 candidate, not a rung-2 finding.** The tier declared at rung 2 stands; escalation raises tiers, nothing lowers them mid-flight.
- **Name who pays**: conversions export cost outward, to the operator who must remember the flag, the caller who must migrate off the version, the maintainer who inherits the shadow path.
- **Permanent hedging is a way of never deciding.** A flag never removed is debt with a config file; dual writes double the failure surface; optionality nobody exercises was bought for nothing.

## Axis 2: blast radius

**The test:** *what breaks, or has to change, if this turns out wrong?*

| | Definition | Signals |
| :--- | :--- | :--- |
| **Local** | Contained within one module, document, or personal choice; a wrong answer is fixed where it was made | One file or one tightly-held unit; no cross-boundary callers; nobody is going to copy it |
| **Wide** | Crosses a boundary, is consumed by others, or establishes a pattern that will be imitated | Cross-module or cross-service; a shared contract; a template; the first instance of something, which becomes the precedent by default |

> [!NOTE]
>
> **The precedent-setting clause catches what the caller count misses.**
>
> A change with exactly one consumer is still **wide** if it is the first of its kind and the next twenty will copy it. First instances are load-bearing far beyond their dependency graph.

## The tier table

| Tier | Condition | Rungs fired | Typical share of invocations |
| :--- | :--- | :--- | :--- |
| **1: express** | Two-way **and** local | 1, 2, 7 | Most |
| **2: standard** | Exactly one of *one-way* or *wide* | 1-5, 7, 8 | Some |
| **3: full** | One-way **and** wide | All eight | Few |

- **Tier 1** still fires rung 1, because framing is where the cheapest catastrophic errors live, and rung 7, because an uncommitted answer is not an answer.
- **Tier 2** adds invariants, precedent, alternatives, and a falsifier *(the substance)*, but skips the five-lens panel.
- **Tier 3** adds the panel and the premortem, and is the only tier that justifies their cost.

## Ties and escalation

- **When torn between two tiers, take the lower one** and name what would push it higher.

    - This is deliberately asymmetric with the misclassification cost noted above, and the asymmetry is resolved by the escalation rule below: tiers are cheap to raise mid-flight and expensive to lower, because lowering means discarding work already shown.

- **Escalate mid-protocol** the moment a lower rung surfaces evidence the classification was wrong.

    - Say so explicitly: *"rung 3 surfaced a wire-format dependency; this is tier 3, not tier 2. Continuing with the panel."*
    - Do **not** silently upgrade. The tier is a claim the user is entitled to audit.

- **The user's override is final in both directions.**

    - If they say "just answer it", drop to tier 1 and answer, without relitigating.
    - If they say "go deep", run tier 3 without demanding justification.
    - Record the override in the tier line *("tier 3 by the axes, run at tier 1 on your call")*, so the output still shows what was skipped.

- **When the clock genuinely forces the call** before the tier's analysis can run, do not silently downgrade.

    - Say which rungs were truncated and why *("tier 3, ran rungs 1-5 only; the site is down")*.
    - Prefer the most **reversible** viable option; optionality is what the time premium buys.
    - Name the analysis debt **and the date it comes due**; debt with no repayment date is a downgrade wearing a deadline.

## Worked classifications

| Decision | Reversibility | Radius | Tier |
| :--- | :--- | :--- | :--- |
| Rename a private helper function | Two-way | Local | 1 |
| Pick a variable name in a script | Two-way | Local | 1 |
| Choose a retry backoff constant | Two-way | Local | 1 |
| Choose between two equivalent stdlib calls | Two-way | Local | 1 |
| Restructure a module's internals | Two-way | Wide | 2 |
| Choose a test framework for a new repo | One-way in practice | Local | 2 |
| Add a field to an internal shared struct | Two-way | Wide | 2 |
| Word a difficult message to a colleague | One-way | Local | 2 |
| Publish a public API endpoint | One-way | Wide | 3 |
| Migrate a schema, dropping a column | One-way | Wide | 3 |
| Choose the consistency model for a store | One-way | Wide | 3 |
| Adopt a dependency at the core of the system | One-way | Wide | 3 |
| Accept a job offer | One-way | Wide | 3 |

## Anti-patterns

- **Tier inflation**: classifying up to justify a longer answer. If the panel keeps running on reversible local changes, the dial is not being read honestly.
- **Tier laundering**: declaring tier 1 and then informally doing tier 3 work anyway. The declaration must match the output, or it is not a control.
- **Deferring the classification**: deciding the tier after the analysis, so the analysis sets the tier rather than the reverse. Rung 2 comes before rungs 3-8 for exactly this reason.
