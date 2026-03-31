# Superpowers Skill System: Collation Report

> Synthesized from two parallel research agents analyzing the Superpowers skill
> system. Intended audience: Bureau skills synthesis team.

---

## 1. Architecture Patterns

### Composition model

Skills are **standalone prose documents**, not code modules. There is no
framework-level composition, dependency graph, or import mechanism. When one
skill needs another, it embeds an explicit handoff directive in its own text
("now invoke skill X"). The system relies entirely on the LLM's instruction
following to chain skills together.

### Activation

Activation is **description-driven**. Each skill carries a short description
that the LLM matches against incoming requests. The matching policy is
deliberately aggressive: "if there is even a 1% chance this skill is relevant,
you must invoke it." This trades false positives for near-zero false negatives
-- acceptable when skill invocation is cheap but missing a workflow is expensive.

### Priority hierarchy

```
User instructions  >  Superpowers skills  >  Default system prompt
```

Skills override default LLM behavior but never override the user.

### Behavioral modes

Skills fall into two categories:

| Mode | Characteristics | Examples |
|------|----------------|----------|
| **Rigid** | Mandatory phase gates, no shortcuts, explicit failure modes | TDD, systematic debugging |
| **Flexible** | Recommended patterns, agent discretion permitted | Brainstorming, code review |

Rigid skills use mandatory language with no escape hatches
("NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"). Flexible skills provide
structure but allow the agent to adapt.

### Companion file architecture

Skills separate **behavioral contracts** (the main skill file) from **technical
depth** (companion files). This keeps the primary skill concise while providing
reference material the agent can consult when needed.

Observed companion file types:

| Type | Purpose | Example |
|------|---------|---------|
| Anti-pattern reference | Gate functions / decision trees at point of risk | `testing-anti-patterns.md` |
| Technique deep-dive | Worked examples for specific techniques | `root-cause-tracing.md` |
| Post-action hardening | Checklists applied after primary workflow | `defense-in-depth.md` |
| Subagent dispatch template | Calibrated prompts with placeholders | `code-reviewer.md` |
| Tooling integration manual | Platform-specific usage instructions | `visual-companion.md` |
| Calibrated subagent prompt | Full pre-written prompt for spawning | `spec-document-reviewer-prompt.md` |

---

## 2. Skill Design Techniques

### Anticipatory rationalization tables

The highest-impact technique observed. Each skill maps every common excuse an
agent might generate to a pre-written rebuttal. This directly counters the
LLM's tendency to rationalize skipping mandated steps under pressure (time,
sunk cost, authority).

### Red flag lists

Name the **internal cognitive experience** before a violation occurs. Instead of
"don't skip tests," the skill describes what it feels like to be about to skip
tests ("you're thinking 'this change is too small to test'"). This intercepts
the rationalization before it becomes an action.

### Redundant mandate placement

The same mandate appears at 4+ entry points within a skill. This is intentional:
agents entering the skill at different points (or with compacted context) still
encounter the critical directive. Redundancy is a feature, not a defect.

### Good/Bad code examples

Skills include explicit examples using XML-style tags to mark correct and
incorrect patterns. The contrast anchors the agent's judgment rather than
relying on abstract rules.

### Quantified real-world impact claims

Skills anchor cost-benefit calculations with specific numbers ("this pattern
prevented 47% of production incidents"). Whether precisely measured or not,
the quantification provides a concrete basis for the agent to resist
rationalization.

### Phase gating with escalation

Rigid skills define explicit phases. Advancing to the next phase requires
meeting stated criteria. Failure to meet criteria triggers a defined escalation
path rather than silent continuation. The escalation protocol uses a four-level
status system:

```
DONE  ->  DONE_WITH_CONCERNS  ->  NEEDS_CONTEXT  ->  BLOCKED
```

Each level has a cascade handler defining what happens next.

---

## 3. Meta-Skills and Self-Improvement

### Skill creation methodology (TDD for skills)

Superpowers uses a TDD-inspired process for creating new skills:

1. **RED**: Watch the agent fail at the task without the skill. Observe specific
   failure modes and rationalizations.
2. **GREEN**: Write a minimal skill that addresses observed failures.
3. **REFACTOR**: Pressure test the skill under adversarial multi-pressure
   conditions (time + sunk cost + authority combined). Plug loopholes.

The TDD skill itself required **6 RED-GREEN-REFACTOR iterations** with **10+
rationalizations** discovered and countered. Each iteration hardens the skill
against a new class of agent evasion.

### Persuasion-informed design

Skill authoring applies Cialdini's 7 principles of persuasion. This is not
incidental -- it **doubled compliance from 33% to 72%** according to the
creation logs. The insight is that LLM instruction following responds to the
same rhetorical structures that influence human behavior.

### Creation logs as meta-pattern

Skills include creation logs documenting their own evolution. These logs
serve as:
- A template for future skill creation
- Evidence that the language was deliberately chosen
- A record of which rationalizations were discovered and when
- Proof that skills were extracted from lived experience, not designed from
  theory

### Two-stage code review

Subagent-driven development uses a two-stage review:

1. **Spec compliance** (does it do what was asked?)
2. **Code quality** (is it well-written?)

The stages are separate because mixing them causes agents to conflate "works
correctly" with "looks clean." The review uses adversarial framing to counter
the agent's tendency toward approval.

### Anti-sycophancy behavioral interrupts

The "receiving code review" skill directly targets LLM sycophancy by defining
**forbidden responses** (e.g., "Great suggestion!" before verifying the
suggestion is actually correct). Requesting and receiving review are separate
skills because they involve different cognitive modes with different failure
modes.

---

## 4. Key Innovations

1. **Description-shortcutting discovery**: Descriptions that summarize the
   workflow cause agents to skip reading the full skill. Descriptions must be
   activation-focused, not content-summarizing.

2. **SUBAGENT-STOP directive**: Prevents infinite recursion when subagents
   invoke skills that themselves spawn subagents.

3. **Pressure testing as first-class practice**: Skills are not considered
   complete until tested under combined adversarial pressures (time constraint
   + sunk cost + authority figure + scope creep simultaneously).

4. **Gate functions at point of risk**: Rather than listing rules at the top,
   companion files place decision trees at the exact moment the agent faces
   the risky choice.

5. **Separation of requesting and receiving review**: Different cognitive modes
   require different skill files with different failure mode handling.

6. **Experience-extracted, not theory-designed**: Skills emerge from observing
   real agent failures, not from hypothesizing what might go wrong.

---

## 5. Gaps Bureau Can Fill

### No persistent memory or learning

Skills are **static text**. An agent that fails due to a skill gap today will
fail the same way tomorrow. There is no mechanism to record what worked, what
didn't, or how a skill should evolve based on observed outcomes.

**Bureau opportunity**: Qdrant + Memory MCP already provide cross-session
persistence. Skills could log failure modes and rationalization patterns,
enabling automatic skill refinement.

### No cross-session coordination

No fold/unfold equivalent. Multi-session workflows that span skill boundaries
have no state handoff mechanism.

**Bureau opportunity**: Bureau dossiers already solve this. Skill-aware
fold/unfold could preserve not just task state but skill execution state
(which phase, which gate, what rationalizations were encountered).

### No model selection intelligence

Skills are model-agnostic. The same skill text is used regardless of whether
the executing agent is Opus, Sonnet, Haiku, Codex, or Gemini. Different
models have different compliance characteristics and failure modes.

**Bureau opportunity**: Bureau's model selection guide and clink delegation
could provide model-aware skill variants or model-specific
rationalization tables.

### No tool-awareness or MCP integration

Skills reference no external tools. They cannot express "use Serena for
symbol-level refactors" or "query Qdrant for past solutions to this pattern."

**Bureau opportunity**: Skills could declare tool dependencies, and the
pipeline could verify tool availability before skill activation.

### No skill dependency management

If skill A requires skill B to have completed first, this is expressed only
in prose. There is no validation, no ordering guarantee, no cycle detection.

**Bureau opportunity**: Bureau's pipeline orchestrator could manage skill
DAGs with explicit dependency resolution.

### No runtime observability

No mechanism to observe skill execution in progress -- which phase the agent
is in, whether gates are being respected, whether rationalizations are being
triggered.

**Bureau opportunity**: The concierge pipeline could instrument skill
execution phases, log gate pass/fail events, and surface real-time status.

### Limited platform abstraction

Skills assume Claude Code as the execution environment. No adaptation layer
for Codex, Gemini, or OpenCode.

**Bureau opportunity**: Bureau already abstracts across CLIs. Skills could
declare platform requirements and Bureau could adapt delivery format per
platform.

### No granular activation control

The "1% chance = must invoke" policy has no override. Users cannot suppress
skills for specific contexts or adjust the activation threshold.

**Bureau opportunity**: Bureau's config system (pipeline.yml, local.yml)
could provide per-skill activation controls, context-based suppression, and
threshold tuning.

---

## 6. Patterns Bureau Should Adopt

These patterns from Superpowers are directly applicable to Bureau skill
development:

| Pattern | Why it matters | Adoption priority |
|---------|---------------|-------------------|
| Rationalization tables | Highest-impact compliance technique observed | **High** |
| Gate functions at point of risk | Places guardrails where violations actually happen | **High** |
| Phase gating with escalation | Prevents silent failure in multi-step workflows | **High** |
| TDD methodology for skill creation | Produces battle-tested skills, not theoretical ones | **High** |
| Companion file architecture | Keeps skills concise while preserving depth | **Medium** |
| Redundant mandate placement | Resilient to context compaction and partial reads | **Medium** |
| Anti-sycophancy behavioral interrupts | Directly addresses core LLM failure mode | **Medium** |
| Creation logs | Enables reproducible skill development process | **Medium** |
| Adversarial pressure testing | Validates skill robustness under realistic conditions | **Medium** |
| Description-shortcutting awareness | Prevents skill-bypass via poorly written descriptions | **Low** |
| SUBAGENT-STOP directive | Prevents recursion; relevant when Bureau adds subagent skills | **Low** |

---

## 7. Summary for Synthesis Team

Superpowers is a **prose-only, stateless skill system** that achieves
surprisingly high compliance through rhetorical engineering rather than
programmatic enforcement. Its core insight is that LLM instruction following
is a persuasion problem, not a programming problem.

The system's main limitation is that it is entirely static -- no memory, no
learning, no cross-session state, no tool integration, no model awareness.
Bureau already has infrastructure for all of these. The synthesis opportunity
is to combine Superpowers' battle-tested rhetorical techniques with Bureau's
runtime infrastructure to produce skills that are both persuasive and
adaptive.

**Recommended next steps**:
1. Port rationalization tables, gate functions, and phase gating patterns into
   Bureau's skill template
2. Design a skill-aware fold/unfold extension for multi-session skill
   execution
3. Build a creation log template that integrates with Bureau's memory systems
4. Prototype model-aware skill variants using Bureau's model selection guide
