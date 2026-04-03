# Task 01 `v1b`: design for aggregation and reframing

## Purpose

This iteration aggregates the independent research in
[`docs/claws/exploration/`](../../exploration/README.md) and reframes it into
Bureau's own architecture-space assessment.

The working assumption for this task is:

- `claude-mem` is dropped.

Under that assumption, this task evaluates **concierge** and **autonomous skill
evolution** together as one coupled architecture problem rather than as two
isolated implementation choices.

## Core question

What future architecture gives Bureau the best chance of becoming a
genius-level, multiplicative, highly differentiated superset of the strongest
ideas in competing "claws" systems, while remaining coherent and brilliantly
designed?

This task is not preservationist. Current Bureau foundations are strengths, not
sacred implementations. Even strong current components may be replaced if a
future stack is clearly better end to end.

## Decision framing

The initial lenses are:

- `deletion`
- `hybrid`
- `continue`

These remain useful framing devices, but they are not mandatory final
categories. If a more compelling and clearer architecture framing emerges, it
may replace them.

The final recommendation space treats concierge and autonomous skill evolution
as one shared strategic choice that may still assign them different roles inside
the same end-state architecture.

## Optimization priorities

Primary weighted criteria:

1. memory-native, self-improving intelligence
2. composability into a coherent superset
3. long-term differentiation and moat

Secondary but important supporting criteria:

- user-facing assistant breadth and quality
- SWE orchestration and execution depth
- openness, self-hostability, and freedom from closed dependencies
- architectural elegance and maintainability

The architecture should optimize first for memory-native, compounding
intelligence on the theory that excellence there improves both assistant-surface
quality and SWE capability over time.

## Candidate-generation rules

- Up to **five** serious end-state candidates may survive this task.
- Multiple claws platforms are allowed if the resulting system is coherent.
- Bureau-native candidates are allowed, but only if they remain genuinely
  competitive after aggregation.
- Bureau-synthesized superset candidates are allowed, including candidates that
  are not identical to any explored platform, as long as they are grounded in
  exploration evidence.
- No platform has a hard disqualifier, but hosted dependence and poor
  composability are especially grave tradeoffs.
- The future synthesis layer does **not** need to be concierge or dynamic skill
  evolution in their current forms. A new synthesis layer may supersede both if
  that yields the strongest system.

## Output package for `v1b/`

This iteration should produce a small ordered package rather than one monolithic
document.

1. `01-capability-stack.md`
   Aggregate the exploration tracks by layer rather than by product.

2. `02-decision-matrix.md`
   Compare promising layers and platform combinations against the weighted
   criteria.

3. `03-narrative-assessment.md`
   Explain tensions, synergies, and weak-evidence areas that the matrix alone
   cannot capture.

4. `04-candidate-architectures.md`
   Present up to five serious end-state architectures.

5. `05-recommendation-memo.md`
   Narrow the field and explain how each surviving candidate treats concierge
   and autonomous skill evolution together.

## Evaluation model

### Pass A: capability-stack scoring

Compare components, platforms, and Bureau-native pieces as **ingredients** by
layer, not yet as whole-system winners.

Suggested layers:

- memory / intelligence
- assistant surface
- SWE orchestration / execution
- autonomy / evolution
- governance / composability

### Pass B: candidate-architecture scoring

After the strongest ingredients are known, evaluate candidate end-state
architectures by:

- multiplicative rather than additive value
- coherence as a designed system rather than an awkward bundle
- plausibility as a world-class superset rather than a mashup
- the quality of their joint treatment of concierge and autonomous skill
  evolution

## Execution workflow

This iteration should run as a parallel synthesis program.

### Main-thread responsibilities

- define the capability-stack frame
- normalize terminology across the exploration tracks
- reconcile contradictions and evidence-quality differences
- construct and compare end-state candidates
- write the final `v1b` package in one coherent voice

### Parallel subagent responsibilities

Use tightly-scoped subagents with exact source bounds and fixed output schemas.
Recommended synthesis lanes:

- memory / intelligence layer
- assistant-surface layer
- SWE execution / orchestration layer
- governance / evolution / composability layer
- cross-track meta-analysis of `v1` / `v2` / `v3` / `v4` as research artifacts

Subagents should synthesize their layer only. They should not jump to whole
system recommendations.

## What success looks like

By the end of `Task 01`, Bureau should have:

- a high-quality aggregation of the independent exploration tracks
- a decision matrix anchored in the right criteria
- a narrative explanation of where the real architectural tension lies
- a narrowed set of end-state architectures worth serious follow-on work

This task does **not** need to force one final winning architecture. Its job is
to reduce the space intelligently and make the next decision much sharper.
