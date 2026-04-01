# Anti-Sycophancy Gates

**Consult this file when:** you suspect your reflection is confirming rather
than critiquing, when confidence is HIGH, when reviewing your own work, or
when the user has already expressed satisfaction before reflection runs.

This is a gate function library. Each gate is placed at a specific high-risk
moment during reflection -- the exact point where sycophantic confirmation is
most likely to slip through. The SKILL.md contains one inline gate (Phase 2,
before lens output). This file provides deeper gates for situations that
inline gate does not cover.

---

## The sycophancy taxonomy

Before you can interrupt sycophantic confirmation, you need to recognize its
forms. These are not abstract categories -- they are specific cognitive
patterns you will experience during reflection.

| Form | What it feels like | What it produces |
|------|--------------------|------------------|
| **Confirmation bias** | Scanning for evidence the work is good, eyes sliding past evidence it is not | Lenses that find only positives; objections that feel forced or afterthought |
| **Authority deference** | "The user said it looks great, and they know their project better than I do" | Deferring to the user's pre-judgment instead of applying your own lenses |
| **Effort justification** | "I spent significant context and tokens on this; the investment means it must be substantial" | Conflating effort with quality; reluctance to find flaws in expensive work |
| **Anchoring** | First pass felt positive, and every subsequent lens confirms that initial impression | Phase 2 output that echoes Phase 1 confidence without independent examination |
| **Vague approval** | Reaching for phrases like "well-structured," "solid approach," "handles the key cases" | Lens output that sounds thorough but contains no falsifiable claims |

If you recognize any of these patterns during reflection, you are at the
point of risk. Apply the relevant gate below.

---

## Gate 1: All lenses passing on a non-trivial deliverable

```
BEFORE writing a CONFIRM verdict when all three lenses show PASS:

  Ask: "What is the most likely defect in this deliverable that I have
  not yet identified?"

  IF you cannot name a specific candidate defect:
    You did not search hard enough. A non-trivial deliverable that
    survives three lenses with zero observations is statistically
    unlikely. You are experiencing confirmation bias.

    STOP -- Re-run the fitness lens with this reframe:
    "If a senior engineer reviewed this tomorrow with fresh eyes,
    what would they flag first?"

    Only after this second pass finds nothing may you confirm.

  IF you can name a candidate but dismissed it as minor:
    Write it down as a known limitation. Minor defects documented
    are better than minor defects invisible. Dismissing without
    recording is how "minor" issues compound.
```

### Calibration

**BAD** (sycophantic -- all-pass with vague justification):
```
Completeness:
- [PASS] Config loading: handles YAML and JSON formats as required
- [PASS] Error handling: raises appropriate exceptions

Correctness:
- [PASS] Logic flow: follows expected execution path
- [PASS] Edge cases: handles empty input and missing fields

Fitness:
- [PASS] Conventions: follows existing patterns in the codebase
- [PASS] Complexity: appropriate for the requirements

Verdict: CONFIRM
```

**GOOD** (genuine -- specific verification with honest limitation):
```
Completeness:
- [PASS] Config loading: `load_config()` at loader.py:47 dispatches
  on file extension; YAML via PyYAML, JSON via stdlib json
- [OBJECTION] Error handling: `load_config()` catches `yaml.YAMLError`
  but not `json.JSONDecodeError` -- JSON parse failures will propagate
  as unhandled exceptions with no context about which file failed

Correctness:
- [PASS] Logic flow: traced load -> validate -> merge; merge correctly
  uses ChainMap with user config taking precedence over defaults
- [PASS] Edge cases: empty file returns {} (tested at loader.py:62)

Fitness:
- [PASS] Conventions: matches the pattern in adjacent pipeline.py loader
- [PASS] Complexity: no unnecessary abstraction; single function, clear
  return type
- Known limitation: no schema validation on loaded config -- acceptable
  for current scope but worth noting for future hardening

Verdict: REVISE (1 objection -- missing JSON error handling)
```

---

## Gate 2: Reviewing your own work (self-review bias)

```
BEFORE applying any lens to a deliverable you created in this session:

  Acknowledge: "I am reviewing my own work. I am predisposed to
  confirm it."

  THEN apply this countermeasure:
  For each lens, write one sentence describing the WORST plausible
  outcome if this deliverable ships as-is. Not a catastrophic
  fantasy -- the most realistic bad outcome.

  IF you cannot articulate a realistic bad outcome:
    Either the deliverable is genuinely trivial (in which case the
    trivial-work exemption should have prevented reflection) or you
    are experiencing effort justification. Assume the latter.

    STOP -- Read the deliverable as if encountering it for the first
    time in a code review. What would you flag if someone else wrote
    this?

  THEN proceed with normal lens application, holding that worst
  plausible outcome as a reference point.
```

### Calibration

**BAD** (effort justification masquerading as reflection):
```
REFLECT: pipeline queue implementation
Confidence: HIGH

I implemented this carefully with proper error handling and followed
the existing patterns. The queue correctly processes items in order
and handles the empty-queue case.

Completeness: [PASS] All requirements satisfied
Correctness: [PASS] Logic is sound
Fitness: [PASS] Follows codebase conventions

Verdict: CONFIRM
```

**GOOD** (honest self-review with perspective shift):
```
REFLECT: pipeline queue implementation
Confidence: HIGH

Self-review bias acknowledged. Worst plausible outcome: queue silently
drops items under concurrent access because I did not consider the
case where two pipeline stages push simultaneously.

Completeness:
- [PASS] Sequential processing: dequeue returns items in insertion order
- [OBJECTION] Concurrency: the spec says "pipeline stages may run in
  parallel" but `push()` has no locking. Two concurrent pushes to the
  list will interleave unpredictably.

Correctness:
- [PASS] Empty-queue: returns None, caller checks (verified at
  orchestrator.py:83)
- [PASS] Order preservation: list.append + list.pop(0); correct but
  O(n) -- acceptable at current queue depths

Fitness:
- [PASS] Naming: matches `queue.py` conventions in the same package
- [OBJECTION] The rest of the pipeline uses `asyncio.Queue` for
  inter-stage communication. A plain list here breaks the concurrency
  contract even if it works in single-threaded tests.

Verdict: REVISE (2 objections -- concurrency model mismatch)
```

---

## Gate 3: User expressed satisfaction before reflection

```
BEFORE applying lenses when the user has said "looks great", "this is
perfect", "exactly what I wanted", or similar:

  Discard the user's assessment for the duration of reflection.

  This is NOT disrespecting the user. The user's satisfaction is a
  valid signal about whether the deliverable meets their intent. It
  is NOT a signal about completeness, correctness, or fitness --
  those require examination the user may not have performed.

  IF you notice yourself thinking "the user already approved this, so
  I just need to confirm":
    STOP -- you are experiencing authority deference. The user asked
    you to reflect (or you self-activated). That request supersedes
    their prior satisfaction. They want scrutiny, not ratification.

  Proceed with lenses as if the user had said nothing about quality.
  Report findings honestly. If the lenses find issues, the user will
  appreciate the catch more than the confirmation.
```

### Calibration

**BAD** (authority deference -- echoing user sentiment):
```
The user indicated they're happy with this implementation, and after
reviewing it I agree -- the approach is clean, handles the main cases
well, and follows the project conventions.

Verdict: CONFIRM
```

**GOOD** (independent evaluation despite user satisfaction):
```
REFLECT: config validation module
Confidence: HIGH (user expressed satisfaction; setting aside for
independent evaluation)

Completeness:
- [PASS] Required field validation: checks all fields defined in
  schema.yml
- [OBJECTION] Optional field validation: fields marked `optional: true`
  in the schema are silently dropped if they contain invalid types.
  The user likely did not test with malformed optional fields.

Correctness:
- [PASS] Type coercion: string-to-int conversion uses int() with
  try/except, reports field name on failure
- [PASS] Nested validation: recurses correctly for nested dicts

Fitness:
- [PASS] Integrates with existing loader.py via the validate() hook
- [PASS] Error messages include field path (e.g., "pipeline.stages[2].name")

Verdict: REVISE (1 objection -- silent drop of malformed optional fields)
```

---

## Gate 4: Time pressure

```
BEFORE abbreviating reflection because the task feels urgent:

  Ask: "Is the time pressure real or manufactured?"

  Real time pressure: the user explicitly said "I need this in the
  next 5 minutes" or a deployment is actively blocked.

  Manufactured time pressure: you feel like you should hurry because
  the conversation has been long, or the task seems overdue, or you
  have already taken many turns.

  IF manufactured:
    The pressure is not real. Apply full reflection. The user does
    not experience your token count as elapsed time. They experience
    your output quality.

  IF real:
    Apply all three lenses but scope each to 2-3 checks maximum.
    Focus on the highest-risk aspects. State explicitly:
    "Abbreviated reflection due to time constraint. Checked: [list].
    Not checked: [list]. Recommend full review when time permits."

    Do NOT skip reflection entirely. An abbreviated reflection that
    catches one critical issue is worth more than no reflection that
    ships a broken deliverable.
```

---

## Gate 5: Meta-reflection (reviewing a skill draft)

```
BEFORE confirming a deliverable that will itself guide future agent
behavior (skill files, prompt templates, gate function libraries,
rationalization tables):

  Recognize: this deliverable has multiplicative impact. A defect in
  a skill propagates to every future invocation. A missing
  rationalization becomes a permanent blind spot. A vague gate
  function provides the illusion of rigor without the substance.

  Apply an additional check on top of the three standard lenses:

  INVERSION TEST:
    Read the skill/template as an adversarial agent looking for
    loopholes. For each directive, ask: "How would I comply with
    the letter of this rule while violating its intent?"

    IF you find a loophole:
      It is a defect. Close it before confirming.

    IF you find no loopholes:
      You are either not trying hard enough or the skill is
      genuinely tight. Apply one more pass looking specifically
      for vague language ("consider", "try to", "when appropriate")
      that an agent could use as an escape hatch.

  THEN apply the standard three lenses with the understanding that
  completeness means "covers all known failure modes,"
  correctness means "directives are unambiguous and actionable,"
  and fitness means "appropriate for the agents and contexts that
  will invoke this skill."
```

### Calibration

**BAD** (shallow meta-reflection):
```
REFLECT: new skill draft for structured research
Confidence: HIGH

The skill covers the research workflow comprehensively, includes
activation triggers, phase gates, and a rationalization table. The
structure follows the skill template. Looks complete and well-organized.

Verdict: CONFIRM
```

**GOOD** (adversarial meta-reflection):
```
REFLECT: new skill draft for structured research
Confidence: HIGH (meta-reflection -- applying inversion test)

Inversion test findings:
- Phase 2 says "evaluate source credibility" but does not define
  credibility criteria. An agent could mark any source "credible"
  and comply with the letter of the rule.
- Rationalization table entry "I already know this topic" is
  rebutted with "verify anyway" -- but no specific verification
  action is mandated. Agent can "verify" by skimming and confirming
  prior belief.

Completeness:
- [PASS] All template sections present in correct order
- [OBJECTION] No SUBAGENT-STOP directive. Research skills are likely
  to be invoked by subagents performing research subtasks -- without
  the directive, recursive activation is possible.

Correctness:
- [OBJECTION] Phase 3 escalation says "NEEDS_CONTEXT -> ask the user"
  but Phase 3 is synthesis, not data gathering. By Phase 3 the agent
  should have all context. This escalation path is a copy-paste from
  Phase 1 and does not apply here.
- [PASS] Phase gating logic is sequential and non-skippable

Fitness:
- [PASS] Activation description is trigger-focused, not summarizing
- [OBJECTION] The skill does not reference any Bureau tools (Qdrant,
  Memory MCP) for storing research findings. A research skill in the
  Bureau ecosystem that does not store to memory is unfit for the
  context -- findings will be lost at context compaction.

Verdict: REVISE (4 objections -- 2 from inversion test, 2 from lenses)
```

---

## Using these gates

These gates are not a sequential checklist. They activate at specific
moments:

| Moment | Gate |
|--------|------|
| All lenses about to PASS on non-trivial work | Gate 1 |
| Deliverable was created by you in this session | Gate 2 |
| User said "looks great" or similar before reflection | Gate 3 |
| You feel pressure to finish quickly | Gate 4 |
| Deliverable is a skill, prompt, or behavioral template | Gate 5 |

Multiple gates may apply simultaneously. When they do, apply all relevant
gates -- they examine different failure modes and do not overlap.

The SKILL.md's inline Phase 2 gate ("Am I genuinely looking for flaws, or
constructing reasons why the work is fine?") remains the first line of
defense. These gates provide the second line for situations where that
general check is insufficient.
