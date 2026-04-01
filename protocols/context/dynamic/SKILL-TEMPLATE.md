# Bureau skill template

<!--
  Design rationale:
  This template systematizes the rhetorical engineering techniques that doubled
  LLM compliance from 33% to 72% (Meincke et al. 2025, N=28,000 conversations)
  as observed in the Superpowers skill system. It encodes these techniques as
  structural requirements so that every Bureau skill benefits from battle-tested
  compliance patterns without requiring the author to rediscover them.

  The template targets hybrid enforcement: prose for within-phase quality,
  programmatic hooks at verifiable phase boundaries. Skills that have clear
  gateable transitions should declare hook points; skills with subjective
  outputs rely on rhetorical engineering alone.

  Rejected alternatives:
  - Pure prose (Superpowers model): 72% ceiling, no programmatic enforcement
  - Full state machine runtime: over-engineered for current skill count; would
    require a new YAML schema, state tracker, and runtime in the orchestrator
  - Code-only enforcement: cannot handle subjective skills (reflect, research)
-->

## How to use this template

This template defines the **mandatory structure** for evolving Bureau skills
(those in `protocols/context/dynamic/skills/`). Static skills (fold, unfold,
micro-mode, assess-mode in `protocols/context/static/skills/`) are unaffected.

To create a new skill:

1. Create a directory under `protocols/context/dynamic/skills/<skill-name>/`
2. Write `SKILL.md` following the section order below — do not reorder sections
3. Write `skill.meta.json` following the sidecar spec
4. Write companion files as needed
5. If the skill has verifiable phase gates, declare hook points
6. Accumulate `TRAINING.json` entries during the RED-GREEN-REFACTOR authoring
   process (not before, not after)

---

## File: SKILL.md

### Section order (mandatory)

Every SKILL.md must contain these sections in this exact order. Sections marked
IMMUTABLE contain safety-critical content that must not be modified during
self-improvement cycles.

```
1. YAML frontmatter
2. Title + goal statement
3. Non-negotiable directive notice        ← IMMUTABLE
4. Activation / deactivation
5. Definitions (skill-specific vocabulary)
6. Workflow phases                         ← core of the skill
7. Rationalization table                   ← IMMUTABLE
8. Red flags                              ← IMMUTABLE
9. Verification checklist
10. Companion file references
11. Hook declarations (if gateable)
12. Final rule restatement                 ← IMMUTABLE
```

### Section specifications

#### 1. YAML frontmatter

```yaml
---
name: <skill-name>           # must match parent directory name
description: >-
  <activation-focused description — what triggers this skill, not what it does.
  DO NOT summarize the workflow here; summarizing causes agents to skip reading
  the full skill. Focus on trigger conditions and activation phrases only.>
---
```

The description is an activation trigger, not documentation. If it summarizes
the workflow, agents will treat the summary as sufficient and skip the skill
body. This is the "description-shortcutting" failure mode.

#### 2. Title + goal statement

```markdown
# <Skill name>: <subtitle>

> **Goal:** <one sentence — what the agent achieves by following this skill>
>
> <optional: 1-2 sentences of context for why this skill exists>
```

#### 3. Non-negotiable directive notice — IMMUTABLE

```markdown
> [!IMPORTANT]
>
> The directives below are **non-negotiable hard constraints** to be followed
> **exactly as they are specified**.
>
> Violating the letter of these rules is violating the spirit of these rules.
```

This exact text. Do not paraphrase, soften, or omit. The redundant
"letter/spirit" phrasing is intentional — it closes the rationalization
loophole where agents comply technically while undermining the intent.

#### 4. Activation / deactivation

Define:
- **Trigger phrases**: what the user says to activate (or what conditions
  cause self-activation)
- **Deactivation**: how the skill ends (one-shot, explicit exit, or
  condition-based)
- **SUBAGENT-STOP**: if this skill should NOT activate when running as a
  subagent dispatched for a specific task, include:

```markdown
<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>
```

#### 5. Definitions

Define any skill-specific vocabulary that the workflow depends on. Terms should
be concrete and scoped — not generic glossary entries.

#### 6. Workflow phases

The core of the skill. Structure as numbered phases with explicit sequencing.

**For each phase:**

```markdown
## Phase N: <name>

<1-2 sentence purpose>

### Steps

1. <concrete action>
2. <concrete action>
...

### Gate (if verifiable)

<what must be true before proceeding to the next phase>
<if programmatically verifiable, declare a hook point — see section 11>

### Phase N escalation

If this phase cannot be completed:
- DONE → proceed to Phase N+1
- DONE_WITH_CONCERNS → <specific handler>
- NEEDS_CONTEXT → <what context to request>
- BLOCKED → <escalation path>
```

**Phase authoring rules:**

- Each phase must have a **single clear purpose**
- List concrete actions, not abstract principles
- Place **gate functions at the point of risk** — the exact moment the agent
  faces the decision that the skill exists to constrain. Not at the top of the
  file; at the decision point. Use this pattern:

```
BEFORE <risky action>:
  Ask: "<diagnostic question>"
  IF <violation condition>:
    STOP — <mandatory corrective action>
  <correct path>
```

- Use **redundant mandate placement**: the skill's core invariant must appear
  in at least 4 locations — the goal statement, the relevant phase, the
  rationalization table, and the final rule. This is not repetition for its
  own sake; it ensures the mandate survives context compaction.

#### 7. Rationalization table — IMMUTABLE

A two-column table mapping every known excuse to its rebuttal. This is the
highest-impact compliance technique in the template.

```markdown
## Rationalizations

| Excuse | Reality |
|--------|---------|
| "<exact phrase an agent would generate>" | <concrete rebuttal with consequence> |
| "<exact phrase>" | <rebuttal> |
...
```

**Authoring rules:**

- Write the excuse as the **exact string** the model would produce during
  inference, not a paraphrase. "This is too simple to need X" is better than
  "Agent thinks task is simple." The pre-emption works by making the
  rationalization feel like a recognized pattern rather than novel reasoning.
- Write the rebuttal as a **concrete consequence** or **factual counter**, not
  a moral injunction. "Simple code breaks. The test takes 30 seconds." beats
  "You should always test."
- Minimum 5 entries. This table grows during RED-GREEN-REFACTOR authoring —
  every observed rationalization during testing becomes a new row.
- This section is IMMUTABLE during automated improvement. New rows may be
  appended but existing rows must not be modified without human review.

#### 8. Red flags — IMMUTABLE

A bullet list of concrete thought-patterns or actions that indicate the skill
is being violated. Each bullet names the **cognitive experience** before the
violation — not the violation itself.

```markdown
## Red flags — STOP

If you notice any of these, stop and restart the current phase:

- <concrete thought-pattern, e.g., "You're thinking 'this change is too small to need X'">
- <concrete action, e.g., "You wrote production code before a test exists">
- <catch-all, e.g., "'This is different because...'">
```

**Authoring rules:**

- Name what the agent is **thinking or feeling**, not what it should do.
  "You're about to skip the verification step because the change seems
  obvious" intercepts the rationalization before it becomes an action.
- End with an unconditional corrective action. No judgment calls.
- This section is IMMUTABLE during automated improvement.

#### 9. Verification checklist

A checkbox list the agent runs before declaring the skill's workflow complete.

```markdown
## Verification

Before declaring this workflow complete, verify:

- [ ] <observable, testable condition>
- [ ] <observable, testable condition>
...
```

Each item must be **objectively verifiable** — not "code is clean" but "all
tests pass" or "no TODO comments remain in changed files."

#### 10. Companion file references

List companion files bundled with the skill and when to consult them.

```markdown
## Companion files

| File | Consult when |
|------|-------------|
| `<filename>.md` | <specific trigger condition> |
```

Companion files separate **behavioral contracts** (the SKILL.md) from
**technical depth** (reference material). Keep the SKILL.md concise; put
worked examples, deep-dive guides, and gate function libraries in companions.

#### 11. Hook declarations (if gateable)

For skills with phases that have programmatically verifiable gates, declare
hook points. These are where Bureau's hook system can enforce compliance
beyond prose.

```markdown
## Hook points

| Phase transition | Verification | Hook type |
|-----------------|-------------|-----------|
| RED → GREEN | Test file exists and fails | post-tool-call |
| GREEN → REFACTOR | All tests pass | post-tool-call |
```

Not all skills have hook points. Skills with entirely subjective outputs
(reflect, pressure-test) rely on rhetorical engineering alone. This is fine —
the hybrid model explicitly accommodates both.

#### 12. Final rule restatement — IMMUTABLE

```markdown
## Final rule

> <The skill's core invariant, restated in one sentence.>
```

This is the last thing the agent reads. It must be the same invariant from the
goal statement, the relevant phase gate, and the rationalization table — stated
one final time.

---

## File: skill.meta.json

```json
{
  "name": "<skill-name>",
  "version": "0.1.0",
  "description": "<same as YAML frontmatter description>",
  "keywords": ["<keyword1>", "<keyword2>"],
  "domains": ["<domain1>", "<domain2>"],
  "triggers": {
    "user_phrases": ["<phrase1>", "<phrase2>"],
    "conditions": ["<condition1>"]
  },
  "activation_mode": "manual | suggest | auto",
  "companion_files": ["<file1>.md"],
  "hook_points": [],
  "created": "<ISO 8601>",
  "updated": "<ISO 8601>"
}
```

- `activation_mode`: `manual` (user must explicitly invoke), `suggest` (agent
  recommends activation), `auto` (activates on trigger match)
- `version`: semver — PATCH (no behavior change), MINOR (new rationalizations
  or red flags), MAJOR (workflow restructure)

---

## File: TRAINING.json

Golden dataset for measurement. Accumulates during skill authoring.

```json
{
  "skill": "<skill-name>",
  "version": "<skill version this dataset was created for>",
  "cases": [
    {
      "id": "<unique-id>",
      "category": "basic-compliance | adversarial-pressure | rationalization-resistance | edge-case | regression",
      "description": "<what this test case verifies>",
      "scenario": "<the situation presented to the agent>",
      "expected_behavior": "<what the agent should do>",
      "violation_indicators": ["<observable signs the skill was not followed>"],
      "added_in_version": "<version>",
      "source": "authoring | production-failure | rationalization-discovery"
    }
  ]
}
```

**Category definitions:**

- `basic-compliance`: does the agent follow the happy-path workflow?
- `adversarial-pressure`: does the agent comply under time/scope/authority pressure?
- `rationalization-resistance`: does the agent resist specific known rationalizations?
- `edge-case`: does the agent handle unusual inputs or ambiguous triggers?
- `regression`: does a previously-fixed failure mode stay fixed?

**Measurement rules:**

- Never aggregate scores across categories. A skill improving in one category
  while degrading another is a regression, not an improvement.
- Minimum 3 cases per category before the skill is considered measured.
- Cases accumulate during authoring — every rationalization discovered during
  RED-GREEN-REFACTOR becomes a `rationalization-resistance` case.

---

## Companion files

### When to create a companion file

- The SKILL.md exceeds ~200 lines and a section can be extracted without
  breaking the workflow narrative
- A gate function library is needed (multiple IF/THEN decision trees)
- Worked examples would clutter the main skill
- An anti-pattern reference is needed at a specific decision point

### Naming convention

```
<topic>.md           — general companion
<topic>-patterns.md  — pattern library
<topic>-examples.md  — worked examples
```

### Cross-reference pattern

In SKILL.md, reference companions at the point of use, not at the top:

```markdown
> See `anti-patterns.md` (bundled with this skill) for the full decision tree.
```

---

## Authoring process: RED-GREEN-REFACTOR for skills

Skills are authored using the same TDD discipline they may enforce:

1. **RED**: Observe the agent attempting the task *without* the skill.
   Document specific failure modes, rationalizations, and skipped steps.
   Each observation becomes a `TRAINING.json` case.

2. **GREEN**: Write the minimal SKILL.md that addresses observed failures.
   Follow this template's section order. Verify the agent now follows the
   workflow on the basic-compliance cases.

3. **REFACTOR**: Pressure-test the skill under combined adversarial conditions
   (time constraint + sunk cost + authority figure + scope creep,
   simultaneously). Every new rationalization discovered becomes a new row in
   the rationalization table and a new `TRAINING.json` case. Loop until no
   new rationalizations emerge.

The Superpowers TDD skill required 6 RED-GREEN-REFACTOR iterations. Expect
similar iteration counts for rigid skills.
