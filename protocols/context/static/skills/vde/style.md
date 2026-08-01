# Style guidance for agents

> [!IMPORTANT]
>
> - This document governs the **shape of this protocol's output**: rung narration, tier declarations, decision records, and halt messages.
> - It deliberately does **not** restate general Markdown or prose conventions.
>
>     - Where the host environment supplies an output style or voice contract, **that contract governs prose** and wins on any conflict.
>     - Where it does not, follow the [baseline conventions](#baseline-conventions) at the bottom of this file.

## Narrating rungs

- **Label rungs only when the label earns its place.**

    - At tier 1, do **not** print rung headers; three rungs of scaffolding around a one-sentence answer is the ceremony this protocol exists to avoid.
    - At tiers 2 and 3, print a short header per rung so the user can see which gate produced which claim, and can challenge one without relitigating all of them.

- **Lead each rung with its output, not its process.**

    - Good: *"Real problem: the retry storm, not the timeout value."*
    - Bad: *"Now I will consider what the real problem is."*

- **Never narrate a rung that did not fire.** A skipped rung is silent; listing it as "skipped" reintroduces the cost the tier dial removed.

## Declaring the tier

State the tier in one line, with both axes visible, before any downstream work:

```
Tier 2: two-way door, wide blast radius. Firing rungs 1-5, 7, 8.
```

- Make the classification **contestable**: the user must be able to see the judgment and overrule it in one reply.
- When the call was close, add one clause naming what would have pushed it up: *"tier 2, but tier 3 the moment this format is published."*

## The decision record

- Use the fixed six-field block from the skill. **Do not add fields**; a record that grows becomes a design doc and stops being read.
- Keep each field to one line. If a field genuinely needs more, the content belongs in the rung narration above the block, not inside it.
- `Precedent:` takes **"none I can name"** as a legitimate value. Never pad it.
- `Flips if:` must name an **observation**, not a feeling.

    - Good: *"p99 stays above 200ms after the batch size drops."*
    - Bad: *"if this turns out to be a problem."*

## Halt messages

When a tripwire fires, break the current output and emit:

```
⟨tripwire: framing-capture⟩ I was answering the stated question. The real
one is <X>. Narrowing before I continue.
```

- **Halt mid-answer**, not at the end. A tripwire reported after the fact is a confession, not a control.
- Name the tripwire with its exact identifier from the table, so repeats are countable across a session.
- Then **narrow and continue** in the same turn. Halting is a correction, not a request for permission.

## Uncertainty

- Mark **verified** and **inferred** claims distinguishably whenever both appear in one answer.
- Prefer *"I have not checked X"* over silence; an unstated gap reads as a covered one.
- Quantify where a number exists. Where none does, say that no measurement was taken rather than reaching for an adjective.

## Baseline conventions

Apply these only when the host environment supplies no output style of its own.

- **Structure content as nested bullets** where it aids scanning; at most one sentence per bullet, with supporting detail nested beneath.
- **Indent with 4 spaces**, not 2.
- **Sentence case** for headers; no section numbers.
- **Empty lines around bullet groups**, including nested groups.
- **Tables** for coordinate items sharing attributes; never more than 20-25 words in a cell.
- **Never use** horizontal rules (`---`) or emojis.

    - The `⟨tripwire: ...⟩` marker and the deactivation banner are structural, not decorative, and are exempt.
