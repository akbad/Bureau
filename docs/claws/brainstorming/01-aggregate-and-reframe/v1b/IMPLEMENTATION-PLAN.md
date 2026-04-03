# Task 01 `v1b` Artifact Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the full `v1b` artifact package for `01-aggregate-and-reframe`, turning the approved design into a coherent set of five analysis documents under `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/`.

**Architecture:** Build the package in dependency order: first aggregate the exploration corpus by capability layer, then convert that synthesis into a weighted matrix, then explain the matrix in prose, then form up to five end-state architectures, and finally narrow the space in a recommendation memo. Use parallel subagent reads for the major synthesis lanes, but keep the final writing voice and candidate formation in one main thread.

**Tech Stack:** Markdown docs, local repo docs under `docs/claws/exploration/`, Bureau docs/code for context, Git, `rg`, `sed`, and subagent delegation.

---

## File map

- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md`
  - Responsibility: aggregate the independent exploration tracks by capability layer rather than by product.
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md`
  - Responsibility: score ingredients and promising combinations against the agreed weighted criteria.
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md`
  - Responsibility: explain tensions, synergies, unstable signals, and where the matrix is too reductive.
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md`
  - Responsibility: present up to five serious end-state architectures, including synthesized Bureau-superset candidates when justified.
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md`
  - Responsibility: narrow the space and explain the strongest next-step candidates for Bureau.
- Modify: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/README.md`
  - Responsibility: keep the approved design/spec aligned with the actual package once implementation finishes, but only if a small post-implementation note is helpful.

## Source set

Primary source families for all tasks:

- `docs/claws/exploration/README.md`
- `docs/claws/exploration/v1/*.md`
- `docs/claws/exploration/v2/*.md`
- `docs/claws/exploration/v3/*.md`
- `docs/claws/exploration/v4/*.md`
- `docs/claws/README.md`
- `docs/claws/brainstorming/README.md`
- `docs/claws/brainstorming/01-aggregate-and-reframe/README.md`
- `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/README.md`

Secondary Bureau context sources:

- `docs/USAGE.md`
- `docs/plans/2026-04-02-agent-framework-evaluation.md`
- `defaults.yml`
- `concierge/`
- `protocols/context/dynamic/skills/`
- `protocols/context/static/ops/`

### Task 1: Build the capability-stack aggregation

**Files:**
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md`
- Read: `docs/claws/exploration/README.md`
- Read: `docs/claws/exploration/v1/*.md`
- Read: `docs/claws/exploration/v2/*.md`
- Read: `docs/claws/exploration/v3/*.md`
- Read: `docs/claws/exploration/v4/*.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/README.md`

- [ ] **Step 1: Create the file with the agreed section structure**

```md
# Capability Stack

## Inputs and method
- Treat `v1` / `v2` / `v3` / `v4` as independent research tracks, not a progression.
- Aggregate by capability layer first, then note which platforms dominate each layer.
- Keep `deletion` / `hybrid` / `continue` as interpretive lenses only.

## Layer 1: Memory / Intelligence
## Layer 2: Assistant Surface
## Layer 3: SWE Orchestration / Execution
## Layer 4: Autonomy / Evolution
## Layer 5: Governance / Composability

## Cross-layer tensions
## Early architecture implications
```

- [ ] **Step 2: Fill the memory / intelligence section from the strongest recurring signals**

```md
## Layer 1: Memory / Intelligence

### Strongest ingredients
- Letta for explicit memory hierarchy and durable agent state.
- Hermes for procedural learning, user modeling, and episodic recall.
- Bureau-native ingredients worth preserving if replaced at the system level:
  - dossiers / resumability
  - graph-structured facts and provenance discipline
- Memoh and OpenFang as retrieval/storage patterns rather than obvious full-spine winners.

### Agreements across tracks
- Bureau's current memory story is fragmented.
- Letta is consistently strong here.
- Hermes is attractive but evidence stability changes by track.

### Conflicts across tracks
- Whether Hermes is a concrete platform bet or mostly a pattern source.
- Whether Letta is a full replacement spine or a governed memory layer.
```

- [ ] **Step 3: Fill the other four layers using the same pattern**

```md
For each remaining layer, use this subsection template:

### Strongest ingredients
### Agreements across tracks
### Conflicts across tracks
### What Bureau-native pieces still matter
### Implications for candidate architecture formation
```

Run this command to re-open key assistant/SWE/governance sources while drafting:

```bash
rg -n "OpenHands|Letta|Hermes|OpenClaw|Memoh|CoPaw|OpenFang|concierge|dynamic skill|dossier|Qdrant|Memory MCP" docs/claws/exploration docs/plans/2026-04-02-agent-framework-evaluation.md docs/USAGE.md
```

- [ ] **Step 4: Add a cross-layer tensions section that names the real architecture pressure points**

```md
## Cross-layer tensions

- explicit memory governance vs lightweight composition
- best-of-breed layering vs all-in-one platform coherence
- Bureau as policy kernel vs Bureau as a more radical synthesized superset
- preserving current strengths vs replacing them with better end-to-end systems
```

- [ ] **Step 5: Run quality checks**

Run:

```bash
rg -n "TODO|TBD|implement later|fill in details" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md
```

Expected: no output

Run:

```bash
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md && echo OK
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md
git commit -m "docs: add Task 01 capability-stack synthesis"
```

### Task 2: Build the weighted decision matrix

**Files:**
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/README.md`

- [ ] **Step 1: Create the file with the scoring model and weights**

```md
# Decision Matrix

## Scoring model

### Primary weighted criteria
| Criterion | Weight | Why it matters |
|---|---:|---|
| Memory-native, self-improving intelligence | 5 | Lead criterion for long-horizon compounding value |
| Composability into a coherent superset | 5 | Avoid additive mashups |
| Long-term differentiation and moat | 5 | Final architecture must become world-class, not merely practical |

### Secondary criteria
| Criterion | Weight | Why it matters |
|---|---:|---|
| Assistant-surface quality | 3 | Supporting evidence for moat |
| SWE execution depth | 3 | Supporting evidence for moat |
| Open / self-hostable posture | 3 | Grave tradeoff area |
| Elegance / maintainability | 2 | Necessary, but not a lead criterion |
```

- [ ] **Step 2: Add an ingredient-level matrix**

```md
## Ingredient matrix

Columns:
- Letta
- Hermes
- OpenHands
- OpenClaw
- Memoh
- CoPaw
- OpenFang
- Bureau-native memory/governance ingredients
- Bureau-native SWE orchestration ingredients

Rows:
- memory-native intelligence
- composability
- differentiation contribution
- assistant-surface contribution
- SWE contribution
- open/self-hostable posture
- elegance/maintainability
```

- [ ] **Step 3: Add a combination-level matrix for promising stacks**

```md
## Combination matrix

Include only combinations that survive the capability-stack synthesis, for example:
- Bureau-native control stack
- Letta + OpenHands + Bureau governance
- Hermes + OpenHands + Bureau governance
- Bureau-synthesized superset candidate
- one or two additional candidates if justified

For each combination, include:
- score by criterion
- one-sentence justification
- key failure mode
```

- [ ] **Step 4: Add a short matrix-reading section**

```md
## Reading the matrix

- The matrix is a narrowing tool, not the final recommendation.
- Low-confidence platforms may still contribute strong ingredients.
- High raw capability does not automatically imply strong superset fit.
```

- [ ] **Step 5: Run quality checks**

Run:

```bash
rg -n "TODO|TBD|implement later|fill in details" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md
```

Expected: no output

Run:

```bash
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md && echo OK
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md
git commit -m "docs: add Task 01 decision matrix"
```

### Task 3: Write the narrative assessment

**Files:**
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md`

- [ ] **Step 1: Create the file with the required analysis sections**

```md
# Narrative Assessment

## What the matrix gets right
## What the matrix flattens
## Stable signals across the exploration corpus
## Unstable or disputed signals
## What this means for Bureau specifically
## Implications for candidate architecture formation
```

- [ ] **Step 2: Write the “stable signals” section using recurring cross-track findings**

```md
## Stable signals across the exploration corpus

- OpenHands is the strongest grounded SWE execution ingredient.
- Letta is one of the strongest memory-native intelligence ingredients.
- Bureau's comparative advantage is protocol rigor, orchestration, and resumability.
- The strongest future architecture is likely compositional rather than monolithic.
```

- [ ] **Step 3: Write the “unstable signals” section from track disagreement**

```md
## Unstable or disputed signals

- Hermes shifts from frontrunner to lower-confidence candidate depending on track.
- OpenClaw's strongest value may be assistant surface rather than intelligence core.
- Memoh and CoPaw contain useful patterns but unstable platform-level confidence.
- A Bureau-native continuation path should only survive if it remains truly competitive.
```

- [ ] **Step 4: Write the “what this means for Bureau” section**

```md
## What this means for Bureau specifically

The key question is not which platform wins in isolation. The key question is
which combination of layers gives Bureau the best chance of becoming a coherent,
world-class superset with memory-native intelligence as the lead dimension.
```

- [ ] **Step 5: Run quality checks**

Run:

```bash
rg -n "TODO|TBD|implement later|fill in details" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md
```

Expected: no output

Run:

```bash
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md && echo OK
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md
git commit -m "docs: add Task 01 narrative assessment"
```

### Task 4: Form the candidate architecture set

**Files:**
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md`

- [ ] **Step 1: Create the file with the candidate template**

```md
# Candidate Architectures

## Selection rules
- maximum of five candidates
- allow synthesized Bureau-superset candidates
- include Bureau-native only if competitive

## Candidate 1: [name]
### Stack
### Why it could become a world-class superset
### What it does with concierge
### What it does with autonomous skill evolution
### Main risk

## Candidate 2: [name]
...
```

- [ ] **Step 2: Write the first-pass candidate list before pruning**

```md
Possible candidates to evaluate for survival:
- Bureau-native continuation candidate
- Letta + OpenHands + Bureau governance
- Hermes + OpenHands + Bureau governance
- Bureau-synthesized memory-first superset
- plural stack with policy-capsule broker
- any additional candidate justified by the matrix
```

- [ ] **Step 3: Prune to at most five and fully write them up**

```md
For each surviving candidate, state explicitly:
- which layer is primary
- which platforms are ingredients vs system anchors
- whether concierge is deleted, hybridized, transformed, or superseded
- whether dynamic skill evolution is deleted, hybridized, transformed, or superseded
```

- [ ] **Step 4: Add a comparison section**

```md
## Comparison

For each candidate, summarize:
- best-case upside
- coherence risk
- dependency risk
- what unique Bureau moat it could create
```

- [ ] **Step 5: Run quality checks**

Run:

```bash
rg -n "TODO|TBD|implement later|fill in details" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md
```

Expected: no output

Run:

```bash
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md && echo OK
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md
git commit -m "docs: add Task 01 candidate architectures"
```

### Task 5: Write the recommendation memo

**Files:**
- Create: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md`
- Read: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md`

- [ ] **Step 1: Create the memo structure**

```md
# Recommendation Memo

## Executive summary
## Recommended shortlist
## Why these candidates survive
## How to interpret `deletion` / `hybrid` / `continue`
## Specific implications for concierge
## Specific implications for autonomous skill evolution
## Recommended next task
```

- [ ] **Step 2: Write the shortlist**

```md
## Recommended shortlist

Keep only the candidates that:
- maximize memory-native intelligence
- compose into a coherent superset
- offer real long-term differentiation
- avoid becoming an awkward bundle
```

- [ ] **Step 3: Write the concierge and dynamic-skill-evolution implications jointly**

```md
## Specific implications for concierge
- state whether concierge is deleted, hybridized, kept, transformed, or superseded
- explain why in terms of the surviving candidates

## Specific implications for autonomous skill evolution
- state whether the current scaffolding is deleted, hybridized, kept, transformed, or superseded
- explain whether the future unit is skill, memory contract, policy capsule, or a new synthesis
```

- [ ] **Step 4: Name the recommended next task**

```md
## Recommended next task

Choose the single next brainstorming or design task that best sharpens the
surviving architecture space, for example:
- architecture deep dive on the top candidate
- memory-governance design
- concierge replacement / transformation design
- synthesis-layer kernel design
```

- [ ] **Step 5: Run quality checks**

Run:

```bash
rg -n "TODO|TBD|implement later|fill in details" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md
```

Expected: no output

Run:

```bash
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md && echo OK
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md
git commit -m "docs: add Task 01 recommendation memo"
```

### Task 6: Final package consistency pass

**Files:**
- Modify if needed: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md`
- Modify if needed: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md`
- Modify if needed: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md`
- Modify if needed: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md`
- Modify if needed: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md`
- Modify if needed: `docs/claws/brainstorming/01-aggregate-and-reframe/v1b/README.md`

- [ ] **Step 1: Verify the package is internally consistent**

Run:

```bash
rg -n "deletion|hybrid|continue|Letta|Hermes|OpenHands|OpenClaw|Memoh|CoPaw|OpenFang|concierge|autonomous skill evolution" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/*.md
```

Expected: broad coverage across the package, with no obvious contradiction in candidate names or framing.

- [ ] **Step 2: Verify no placeholders remain anywhere in the package**

Run:

```bash
rg -n "TODO|TBD|implement later|fill in details|Similar to Task" docs/claws/brainstorming/01-aggregate-and-reframe/v1b/*.md
```

Expected: no output

- [ ] **Step 3: Verify file set completeness**

Run:

```bash
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/01-capability-stack.md && \
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/02-decision-matrix.md && \
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/03-narrative-assessment.md && \
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/04-candidate-architectures.md && \
test -f docs/claws/brainstorming/01-aggregate-and-reframe/v1b/05-recommendation-memo.md && echo OK
```

Expected: `OK`

- [ ] **Step 4: Commit the package polish**

```bash
git add docs/claws/brainstorming/01-aggregate-and-reframe/v1b
git commit -m "docs: finalize Task 01 v1b artifact package"
```

## Self-review notes

- **Spec coverage:** The plan covers each artifact required by the approved `v1b` design and preserves the capability-stack-first sequencing.
- **Placeholder scan:** Avoid leaving bracketed candidate names or empty comparison tables in the final documents.
- **Consistency risks:** Use the same candidate names and the same interpretation of concierge / autonomous skill evolution across all five documents.
