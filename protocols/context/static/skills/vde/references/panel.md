# The five-lens panel

> *Seniority is largely a matter of how many people you have already been. The panel loads those people on demand.*

- **Fires at tier 3 only.** At tier 2, the adversarial weight is carried by rung 5's null option and rung 7's *"what would change my mind"*.
- Run the panel on the **front-runner**, not on every candidate; the point is to stress the choice you are about to commit to.
- A lens that finds nothing should say so in **one clause**, not a paragraph. Manufacturing an objection to look thorough is its own failure.

## The lenses

### The operator

*The person paged at 3am when this misbehaves.*

- How does this fail, and what does the failure **look like from outside**?
- What is the **first signal** that something is wrong, and how long after the fact does it arrive?
- Can they **diagnose it from what is emitted**, without attaching a debugger to production?
- What is the **recovery action**, and can it be taken by someone who did not build this?

**Catches:** silent failure modes, missing signals, recovery paths that only the author could execute.

### The maintainer

*The person changing this in six months, possibly you, without today's context.*

- What must they **understand before they can safely touch it**, and is that written down where they will look?
- Which parts look **arbitrary but are load-bearing**? Those are the ones that get "cleaned up" into an outage.
- Does the structure make the **next likely change easy**, or does it make it a rewrite?

**Catches:** undocumented invariants, cleverness with no comment, designs optimized for being written rather than changed.

### The adversary

*Anyone whose interests run against the happy path: an attacker, an abusive user, or just a hostile input.*

- What happens under **malice**, not just error?
- What is the **worst input** that is still technically valid?
- What does this **trust that it has not verified**, and what is reachable if that trust is misplaced?
- Under **resource exhaustion or contention**, what degrades and what collapses?

**Catches:** implicit trust boundaries, unvalidated assumptions about callers, failure modes that only appear under pressure.

### The successor

*The engineer who inherits this after you are gone, with no access to you.*

- Can they tell **why** this was chosen, or only **what** was chosen?
- Which decisions will look **wrong without their context**, and is that context recoverable?
- What would they have to **re-derive from scratch** to make a confident change?

**Catches:** missing rationale, decisions whose justification lived only in a conversation, work that cannot be safely modified by anyone else.

### The accountant

*Whoever pays for this, in money, time, attention, or complexity budget.*

- What does this **cost to run**, and how does that scale with usage?
- What does it cost to **keep**, in maintenance and cognitive load?
- What is the **opportunity cost**; what does choosing this prevent?
- Is the cost **proportionate** to the value, or are we buying rigor nobody asked for?

**Catches:** solutions that outgrow their problem, unbounded costs, complexity charged to a budget nobody is tracking.

## The premortem

After the lenses, run this once:

> *It is six months from now. This decision is the named root cause of a serious problem. Write the one-paragraph story of how we got here.*

- Write it as **narrative**, not as a risk list; the narrative form surfaces causal chains that bulleted risks flatten.
- Name the **specific first domino**, not the general category.
- If the story is **hard to write**, that is evidence for the decision. If it writes itself, revisit rung 5.

## Port table

The lenses are roles, not job titles; each maps onto a counterpart in non-software domains.

| Lens | Writing | Career | Research |
| :--- | :--- | :--- | :--- |
| **Operator** | The reader encountering this cold, with no context | Your future self living the day-to-day of this choice | The person who has to reproduce the result |
| **Maintainer** | Future-you revising this draft | Whoever renegotiates this arrangement later | The next author building on the method |
| **Adversary** | The hostile or motivated-to-misread reader | The competing candidate, or the counterparty | The reviewer looking for the fatal flaw |
| **Successor** | Someone quoting this out of context | Whoever fills the role after you | A replication attempt years later |
| **Accountant** | The reader's time and attention | Opportunity cost, doors closed | Effort per unit of confidence gained |

## Anti-patterns

- **Panel theater**: running all five and reporting "no concerns" from each. If four lenses are silent, run two and say why the others do not apply.
- **Lens collapse**: letting one lens's voice answer for all five, usually the adversary's. Each lens exists because it catches what the others structurally cannot.
- **Objection without weight**: surfacing a concern and neither answering nor conceding it. Every objection raised at rung 6 exits either answered or as a reason to revisit rung 5.
