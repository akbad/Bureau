# Hermes × Bureau integration report

## Platform profile
**Research confidence:** Low-to-medium.

I could not establish a single dominant, clearly canonical “Hermes” agent platform identity with stable, authoritative public technical docs that unambiguously match this exact naming target. In practice, “Hermes” appears across multiple AI/code-adjacent projects and model families.

Given that ambiguity, this report treats Hermes as a **candidate agent platform archetype** and evaluates integration patterns that remain useful even if the eventual Hermes target is narrowed later.

## Functional model (assumed Hermes archetype)
A likely Hermes-style platform in this context would include:
- agent runtime with tool/plugin calls,
- persistent context/memory abstractions,
- looped plan→act→reflect execution,
- potentially user-facing assistant UX and automation hooks.

## Memory architecture fit with Bureau
Potential overlap with Bureau:
- Hermes episodic memory ⇄ Bureau Qdrant semantic memory.
- Hermes structured facts/entities ⇄ Bureau Memory MCP graph memory.
- Hermes runtime scratchpad ⇄ Bureau session-scoped context and skills state.

Likely integration needs:
1. memory schema translation layer,
2. dedupe/merge policy (avoid replaying same memories across stores),
3. provenance metadata (`source=hermes`, confidence, timestamp),
4. recall gating (task-context relevance scoring before injection).

## Autonomous learning loop fit
If Hermes supports self-improving loops (evaluate/revise policies), Bureau can contribute:
- explicit guardrails via skills (`assess-mode`, `clearance-mode`),
- memory distillation checkpoints,
- role-specialized subagent decomposition.

Primary risk: ungoverned self-reinforcement loops poisoning memory with low-quality artifacts.

## Operational memory stack compatibility
Best-practice stack for Hermes+Bureau:
- L0: working memory (prompt-local scratch)
- L1: session memory (task trajectory, intermediate decisions)
- L2: semantic memory (Qdrant)
- L3: structural/knowledge graph memory (Memory MCP)
- L4: dossier memory (fold/unfold continuity)

This maps well to Bureau’s existing philosophy.

## Daily assistant + SWE assistant capabilities fit

### Daily assistant fit
If Hermes includes calendar/reminder/summary orchestration:
- strong fit with Concierge pipeline behaviors,
- can route recurring personal workflows through Bureau’s scheduled/background features.

### SWE assistant fit
If Hermes offers coding autonomy:
- Bureau can provide stronger tool routing discipline and cross-CLI role parity,
- Hermes can contribute richer loop autonomy if currently absent in Bureau workflows.

## Workflow/UX design assessment
Ideal UX blend:
- Bureau as control plane + policy layer,
- Hermes as execution engine with adaptive autonomy,
- explicit operator visibility for every autonomy escalation.

## Integration architecture proposal
1. `hermes-adapter` service translating task/memory/tool calls.
2. Shared event schema (`task_started`, `task_reflection`, `memory_write`, `approval_request`).
3. Bi-directional memory gateway with TTL and confidence tags.
4. Safety envelope requiring Bureau gate-skill pass before high-impact actions.

## Risks
- Identity ambiguity of target Hermes stack,
- over-complexity before stable value proof,
- memory duplication/conflict,
- policy mismatch between Hermes looping and Bureau approval semantics.

## Recommendation
Proceed only as a phased discovery integration:
- Phase 1: read-only memory sync prototype.
- Phase 2: delegated task execution with strict dry-run mode.
- Phase 3: supervised autonomous loops with measurable quality KPIs.

## High-impact merge concepts (subagent brainstorm section)

### 1) Memory arbitration engine
A “Bureau Hermes Memory Arbiter” that ranks candidate memories by recency, correctness, and execution outcomes; only top-scored memories are reinjected.

### 2) Reflexive policy tuning loop
Hermes generates proposed policy refinements after each task; Bureau `assess-mode` validates them before enabling.

### 3) Persona multiplexing
Use Bureau’s role prompts as a persona pack consumed by Hermes, enabling dynamic specialist switching while preserving cross-CLI consistency.

### 4) Assistive-to-autonomous gradient
Single slider UX from “advisor mode” to “hands-off execution mode,” implemented via progressively relaxed Bureau approval gates.

### 5) Outcome-linked memory pruning
Automatically downgrade or prune memories tied to failed task outcomes, preventing stale strategy lock-in.
