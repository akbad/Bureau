# Proposed Bureau differentiation: honest audit against SOTA

> Of the 50 features enumerated in [differentiation-b-aspirational.md](differentiation-b-aspirational.md), approximately 12-15 are genuinely unprecedented, 15-18 have novel designs within established categories, and 10-12 are good engineering that SOTA already provides or is converging toward. This document stratifies every feature honestly.

**Date:** 2026-04-03
**Scope:** every feature from the evaluation-b architecture, audited against the current state of the art (SOTA) across the 7 evaluated platforms *and* the broader agent ecosystem (LangSmith, Langfuse, Braintrust, Devin, Cursor, GitHub Copilot Workspace, E2B, Daytona, LangGraph, CrewAI, AutoGen, Constitutional AI, Guardrails AI, MemGPT)
**Relationship to other docs:**
- [differentiation-b-aspirational.md](differentiation-b-aspirational.md) enumerates all 50 features without SOTA stratification
- [existing-bureau-differentiation.md](existing-bureau-differentiation.md) enumerates the 30 features Bureau has today
- This document is the honest answer to "which of these actually differentiate from everything else?"

## Stratification method

Each feature is classified into one of four tiers:

| Tier | Meaning | Implication |
|:---|:---|:---|
| **Unprecedented** | No known equivalent in any evaluated platform or the broader SOTA | This is genuine moat; hard to replicate because no one has even attempted it |
| **Novel design** | The *category* exists in SOTA; Bureau's *specific design* within it is new | Differentiation is real but requires articulating *why* Bureau's design is better, not just *that* it exists |
| **Good engineering** | SOTA has equivalent or is converging; Bureau's version is well-designed but not unique | Not a differentiator in a feature comparison; valuable as execution quality |
| **Framing** | Architectural property or conceptual lens; important internally but not externally differentiating | Powerful for coherence and portfolio storytelling; not something a feature evaluator would notice |

## Tier 1: Genuinely unprecedented

These features have no known equivalent. They represent Bureau's irreducible moat.

### 1) Rationalization pre-emption tables as a systematic technique

**What it is**: two-column tables in every skill mapping exact agent rationalizations (written as the precise strings the model would produce during inference) to concrete rebuttals. IMMUTABLE: cannot be weakened by skill evolution. Evidence base: Meincke et al. 2025 (N=28,000) showing rhetorical engineering doubled compliance 33% → 72%.

**Why unprecedented**: no platform, framework, or research prototype systematically pre-empts LLM rationalizations by writing the exact excuse the model would generate and intercepting it with a rebuttal. Constitutional AI (Anthropic) defines principles; Guardrails AI defines rules; neither targets the specific cognitive patterns of rationalization at the inference-time string level. The technique is grounded in empirical research, not intuition.

**What SOTA has instead**: Constitutional AI provides broad behavioral principles. Guardrails AI provides constraint checks on outputs. System prompts provide behavioral instructions. None of these target the *specific moment* where the model generates a rationalization for circumventing its instructions.

**Evaluation-b features**: #19 (rationalization table evolution), plus existing-bureau #15 (rationalization tables)

### 2) CLAIMED vs. VERIFIED epistemology as metadata primitive

**What it is**: every factual assertion an agent makes about code behavior is tagged CLAIMED (agent reasoning) or VERIFIED (sandbox execution confirmed). Tags propagate through composition: a composite claim containing any CLAIMED sub-claim remains CLAIMED. An unverified code review is an opinion; a verified one is a finding.

**Why unprecedented**: no platform distinguishes agent opinion from verified fact at the metadata level. OpenHands runs code but doesn't tag individual claims. Testing frameworks verify developer-written assertions, not agent-generated claims. The propagation rule (weakest-link determines composite tag) prevents presenting agent opinion as verified fact through composition.

**What SOTA has instead**: sandboxes run code; test frameworks verify assertions; neither creates a metadata layer on agent claims. The agent says "this function has O(n^2) complexity" and the user must decide whether to trust it. Bureau says "CLAIMED: O(n^2)" or "VERIFIED: benchmarked at 150ms/n=1000, 6200ms/n=10000, confirmed quadratic."

**Evaluation-b features**: #11

### 3) Emotional sensitivity gating via suite detection and hard rules

**What it is**: the concierge pipeline detects user emotional state (PROCESSING suite: stressed, overwhelmed, anxious, etc.) with highest precedence and structurally blocks feature types (BREWs, DISPATCHes) via hard rules. Processing cooldown extends the block after the emotional state subsides. The system *withholds* rather than acts.

**Why unprecedented**: no evaluated platform, and no known agent system in the broader SOTA, gates feature delivery on detected user emotional state. Chatbots detect sentiment for response tone; Bureau detects emotional state to decide *whether to act at all*. The insight that intelligence includes knowing when NOT to act is not implemented anywhere else.

**What SOTA has instead**: sentiment analysis adjusts response tone. Safety filters block harmful content. Neither suppresses proactive features based on user emotional context.

**Evaluation-b features**: existing-bureau #2 (suite detection), #3 (hard rules), #9 (SessionState processing cooldown)

### 4) Anti-sycophancy gate library with named cognitive failure taxonomy

**What it is**: 5 gates targeting specific high-risk moments during self-review, preceded by a formal taxonomy naming 5 forms of sycophancy (confirmation bias, authority deference, effort justification, anchoring, vague approval). Each gate includes BAD/GOOD calibration examples showing exact output differences. Gate 5 (meta-reflection) forces adversarial inversion: "How would I comply with the letter while violating the intent?"

**Why unprecedented**: LLM sycophancy is a known problem. Anthropic's research documents it. OpenAI's system prompts try to mitigate it. But no one has built a *structured intervention library* with named failure modes, per-gate activation triggers, and calibration examples showing the difference between genuine and sycophantic reflection. The specificity (5 named forms, 5 gates, concrete BAD/GOOD pairs) is the moat.

**What SOTA has instead**: system prompts say "be honest" or "don't just agree." Research papers document sycophancy. Neither provides a structured, gate-by-gate intervention with calibration examples.

**Evaluation-b features**: existing-bureau #21

### 5) Formal composition algebra with phase ordering and interference detection

**What it is**: skills compose declaratively via a phase model (pre-analysis → execution → post-verification → gating). Skills declare which phases they operate in. Contradictory instructions at the same phase are detected and resolved via priorities or mediator skills. Phase coalescence allows verification skills to share analysis (blast-radius caller graph feeds scrimmage attack surface feeds safeguard impact assessment).

**Why unprecedented**: no platform has composable agent behavioral modes with formal semantics. LangGraph has DAGs but they compose *tasks*, not *behavioral protocols*. GitHub Actions compose *steps*, not *agent constraints*. Unix pipes compose *data transformations*, not *cognitive modes*. The distinction: Bureau composes behavioral disciplines (how to think about the task), not execution steps (what to do).

**What SOTA has instead**: workflow engines compose steps. Agent frameworks compose tools. Multi-agent systems compose roles. None compose behavioral protocols with interference detection and phase coalescence.

**Evaluation-b features**: #31, #35, #37, #38

### 6) IMMUTABLE sections as structural constitutional constraints on evolution

**What it is**: certain skill sections (non-negotiable directive notice, rationalization table, red flags, final rule) are marked IMMUTABLE and cannot be altered by any evolution mechanism, meta-skill, or autonomous modification pathway. The IMMUTABLE enforcement mechanism itself is IMMUTABLE.

**Why unprecedented**: Constitutional AI defines principles that guide training; they are not structural barriers within a self-modifying system. Guardrails AI defines runtime rules; they can be reconfigured. Bureau's IMMUTABLE sections are part of the skill template specification and are enforced at the structural level: the evolution mechanism treats them as read-only by design, not by instruction.

**What SOTA has instead**: Constitutional AI (aspirational principles applied during training), Guardrails AI (runtime constraints that can be reconfigured), system prompt instructions ("never do X," which models can rationalize around).

**Evaluation-b features**: #40

### 7) RED-GREEN-REFACTOR authoring discipline for behavioral protocols

**What it is**: TDD-style 3-phase skill development: RED (observe agent failing without skill, document rationalizations), GREEN (write minimal skill addressing failures), REFACTOR (pressure-test under *combined* adversarial conditions: time + sunk cost + authority + scope creep *simultaneously*, loop until no new rationalizations emerge).

**Why unprecedented**: TDD for code is standard. TDD for LLM behavioral compliance is not. The REFACTOR phase's combined adversarial pressure (not one condition at a time) is the critical insight: real-world usage involves multiple pressures simultaneously. The loop termination condition (no new rationalizations) is empirical, not arbitrary.

**What SOTA has instead**: prompt engineering by iterative refinement (intuition-based). Eval suites for measuring LLM outputs (measuring, not authoring). Neither applies systematic adversarial authoring with empirical termination criteria.

**Evaluation-b features**: existing-bureau #17

### 8) TRAINING.json with per-category non-aggregation and 5 measurement categories

**What it is**: golden datasets with basic-compliance, adversarial-pressure, rationalization-resistance, edge-case, regression categories. Rule: "Never aggregate scores across categories. A skill improving in one category while degrading another is a regression, not an improvement." Minimum 3 cases per category.

**Why unprecedented**: eval suites exist (SWE-bench, HumanEval, MMLU). But these measure *model* capability, not *skill protocol* compliance. Bureau's TRAINING.json measures whether a specific behavioral protocol achieves its intended behavioral change, per adversarial condition. The non-aggregation rule is the key: it prevents the common failure where "average compliance improved" masks regression on hard cases.

**What SOTA has instead**: model benchmarks (measure capability, not protocol compliance), A/B testing (measures aggregate performance, not per-category), eval frameworks (Braintrust, LangSmith: measure outputs, not behavioral adherence).

**Evaluation-b features**: existing-bureau #17, evaluation-b #7

### 9) The closed feedback loop as a structural property

**What it is**: the 5 subsystems form a single cycle where every action produces data, every data point improves routing/skills/verification/trust. This requires Bureau ownership of all 5 subsystems. Delegating any one to an external platform breaks the loop.

**Why unprecedented**: individual feedback loops exist (Hermes learns from experience, Letta reflects during sleep-time). But no platform has a **closed** loop where provenance feeds competence, competence feeds evolution, evolution feeds routing, routing feeds execution, execution feeds provenance, verification gates everything. The closedness is the property; any individual leg of the loop has precedent.

**What SOTA has instead**: open loops. Hermes: skill-from-experience (no verification, no competence measurement). Letta: sleep-time reflection (no outcomes, no routing feedback). Devin: learns from user corrections (no formal evolution, no composition algebra).

**Evaluation-b features**: #44

### 10) Activation description as trigger, not documentation (description-shortcutting prevention)

**What it is**: YAML frontmatter descriptions must describe *when* to activate, not *what* the skill does. "If it summarizes the workflow, agents will treat the summary as sufficient and skip the skill body. This is the 'description-shortcutting' failure mode."

**Why unprecedented**: this addresses a specific, measured failure mode in LLM skill systems that no other platform has documented or mitigated. OpenClaw, Hermes, and every other skill system uses descriptions that summarize what skills do, enabling the exact shortcutting behavior Bureau prevents.

**What SOTA has instead**: skill descriptions that summarize functionality (enabling shortcutting).

**Evaluation-b features**: existing-bureau #28

### 11) Redundant mandate placement for context compaction survival

**What it is**: core invariant appears in 4+ structural locations (goal, relevant phase, rationalization table, final rule). "Not repetition for emphasis; redundancy for fault tolerance against context truncation."

**Why unprecedented**: no other platform engineers for the specific failure mode where context compaction (long conversations, system-applied compression) drops important instructions. This is deployment-environment-aware behavioral engineering.

**What SOTA has instead**: system prompts placed once. When context is compressed, instructions may be lost. No platform explicitly engineers for compaction survival.

**Evaluation-b features**: existing-bureau #30

### 12) 5-feature-type taxonomy with independent scheduling, cooldown, and sensitivity semantics

**What it is**: DISPATCH (serendipitous, 12h cooldown, 3/week), BREW (distilled observations, 168h cooldown, 2/month, per-suite fit scores), PROBE (intelligence reports, schedule-gated), VALET (guided routines, NOT blocked during PROCESSING), HUDDLE (structured interviews, 6 subtypes). Each with independent scheduling logic, cooldown periods, and hard-rule interactions.

**Why unprecedented**: no evaluated platform has a typed taxonomy of proactive feature types with per-type scheduling semantics. Hermes has cron. OpenClaw has skills. Neither has "this feature type has a 168h cooldown and a per-suite affinity score of 0.8 for WORK contexts."

**What SOTA has instead**: cron-based scheduling (Hermes), generic skill activation (OpenClaw), notification systems (no scheduling intelligence).

**Evaluation-b features**: existing-bureau #4

## Tier 2: Novel design within established category

These features operate in categories that SOTA addresses, but Bureau's specific design is new and meaningfully better. The differentiation is real but requires explaining *why* the design is better, not just *that* it exists.

### 13) Causal edge taxonomy with 4 relation types and back-patching

**Category (established)**: execution tracing / lineage tracking (LangSmith, Langfuse, Braintrust)

**Bureau's novel design**: 4 typed edges ("caused by," "informed by," "superseded by," "contradicted by") with back-patching of "superseded by" and "contradicted by." Enables querying "what was believed true at time T?" and "when was it discovered wrong?"

**Why the design is better**: existing tracing tools model forward causality only. Back-patching models *retroactive invalidity*, essential for debugging agent reasoning across sessions where earlier conclusions are later disproved.

**Evaluation-b features**: #2

### 14) Dossiers as named subgraph projections (lossless handoff)

**Category (established)**: session handoff / context transfer (every platform has some mechanism)

**Bureau's novel design**: handoff is not a lossy snapshot but a named entry point into the provenance graph. Unfolding reconstructs the full reasoning chain. A resuming agent can answer questions the original author didn't anticipate by traversing the graph.

**Why the design is better**: snapshot-based handoffs lose reasoning context. Graph projection preserves it. The difference matters when the resuming agent needs context the handoff author didn't think to include.

**Evaluation-b features**: #3

### 15) Memory trust scoring via provenance depth and contradiction count

**Category (established)**: memory management / retrieval ranking (Letta memory blocks, Memoh hybrid retrieval, RAG generally)

**Bureau's novel design**: trust = f(provenance_depth, contradiction_count, verification_event_count, age). Trust scores influence retrieval ranking: high-trust memories prioritized. Roles producing low-trust memories get lower competence reliability scores.

**Why the design is better**: existing systems rank by *relevance*. Bureau ranks by *relevance AND reliability*. A highly relevant but frequently contradicted memory is dangerous; Bureau surfaces this.

**Evaluation-b features**: #4, #48

### 16) Four-dimensional competence profiles with specificity dimension

**Category (established)**: agent performance measurement (SWE-bench leaderboards, LMSys Arena)

**Bureau's novel design**: per-role, per-project, per-task-category profiles with accuracy, efficiency, reliability, and *specificity* (was this the right dispatch choice?). Specificity tracks whether a different role was eventually used for the same task.

**Why the design is better**: existing benchmarks measure absolute capability. Bureau measures *dispatch-decision quality*: not just "did the agent succeed?" but "should this agent have been dispatched in the first place?" Every mis-dispatch becomes routing training data.

**Evaluation-b features**: #6

### 17) Earned autonomy gradient with existing modes as levels

**Category (established)**: dynamic permissions / trust levels (Devin adjusts autonomy, Cursor has approval flows)

**Bureau's novel design**: quantitative promotion thresholds (>80%, >90%, >95%), immediate demotion on failure, task-scoped levels, authorization category ceilings. The critical insight: Shadow/Micro/Assess *already are* L0/L1/L3; the gradient makes them automatic.

**Why the design is better**: existing systems have "autonomous" and "supervised" as binary modes, or user-configured trust levels. Bureau's autonomy is *earned through measured performance* with task-scoped granularity and policy ceilings that cannot be overridden by competence.

**Evaluation-b features**: #21-25, #46

### 18) Implicit accept/reject signal extraction from structured editing

**Category (established)**: RLHF / user feedback collection (thumbs up/down, explicit ratings)

**Bureau's novel design**: advancing past a micro-mode step is implicit accept. Reverting is implicit reject. Assess Mode "must fix" is partial reject. Dense reward data from natural user behavior during structured editing without requiring explicit ratings.

**Why the design is better**: RLHF requires explicit feedback (user must click a button). Bureau infers feedback from actions the user is already taking. This produces much denser signal.

**Evaluation-b features**: #9

### 19) Sandbox verification integrated into every editing mode

**Category (established)**: sandboxed code execution (OpenHands, E2B, Daytona, Docker generally)

**Bureau's novel design**: sandbox is not an execution backend but a *verification primitive* woven into Assess Mode (benchmark complexity claims), Scrimmage Mode (execute attack vectors), Clearance Mode (auto-verify MUST criteria), Micro Mode (per-step verification). Verification events feed the competence ledger.

**Why the design is better**: OpenHands uses sandbox for task execution. Bureau uses sandbox for *claim verification*. The distinction: OpenHands asks "did the code run?"; Bureau asks "did the agent's claim about the code hold up?"

**Evaluation-b features**: #10, #12-15, #49

### 20) Skill variant A/B testing via epsilon-greedy

**Category (established)**: prompt A/B testing (Anthropic, OpenAI, Google do this internally; Braintrust, LangSmith provide tooling)

**Bureau's novel design**: the existing epsilon-greedy infrastructure (originally for feature-type selection) extends to skill-variant selection. Variants compete under real conditions with TRAINING.json as the per-category measurement framework. Losing variants are retired.

**Why the design is better**: existing A/B testing operates on prompts (input to models). Bureau operates on *behavioral protocols* (multi-phase structured workflows with rationalization tables). The granularity is fundamentally different.

**Evaluation-b features**: #17

### 21) Graduated context injection with prediction + on-demand fallback

**Category (established)**: context management / tiered memory (Letta context hierarchy, MemGPT tiers, Claude context caching)

**Bureau's novel design**: concierge classification predicts needed context blocks → pre-load only those → provenance real-time trace detects agent searching for unloaded context → inject on-demand → competence ledger accumulates role-context association data → prediction improves over time.

**Why the design is better**: Letta's hierarchy is manually managed. MemGPT's tiers require explicit promotion/demotion. Bureau's prediction is automatic and learning. The on-demand fallback via provenance trace prevents prediction failures from becoming missing-context errors.

**Evaluation-b features**: #30

### 22) Composite mode performance measurement and composite-level autonomy

**Category (established)**: mode composition exists conceptually (users can activate multiple features)

**Bureau's novel design**: composites are measured as *units* (not just individual skills). A hardened composite (clearance + micro + scrimmage + blast-radius) can earn L3 autonomy as a composite even if individual skills are L1. The skill genome evolves optimal compositions for different task types.

**Why the design is better**: no platform measures composite performance or grants autonomy at the composite level.

**Evaluation-b features**: #31 (composite orchestration), #22 (composite autonomy)

### 23) Adaptive delegation topology

**Category (established)**: multi-agent orchestration (LangGraph DAGs, CrewAI crews, AutoGen conversations)

**Bureau's novel design**: dynamic per-task topology selection among hub-and-spoke, pipeline, ensemble, and swarm. Chosen based on competence ledger data and provenance graph outcome history.

**Why the design is better**: existing frameworks fix the topology (LangGraph: DAG; CrewAI: crew structure). Bureau adapts topology per-task based on historical outcome data.

**Evaluation-b features**: #29

### 24) Agents as skill bundles with per-skill competence attribution

**Category (established)**: role-based agents (every multi-agent framework)

**Bureau's novel design**: roles decomposed into skill compositions. "Architect" = blast-radius + clearance + assess. Competence ledger attributes performance to individual skills within roles. When the architect underperforms, Bureau identifies *which skill* degraded.

**Why the design is better**: existing frameworks treat roles as monolithic prompts. Bureau's decomposition enables: new roles from existing skills, per-task tuning by adjusting skill composition, and per-skill performance attribution within roles.

**Evaluation-b features**: #32

### 25) Rationalization table evolution (pruning and growth)

**Category (established)**: prompt refinement / guardrail tuning

**Bureau's novel design**: provenance graph detects novel circumventions → auto-draft new entries. Entries that never fire → flagged for removal. Both directions are data-driven from observed agent behavior.

**Why the design is better**: existing guardrail tuning is manual (human reviews logs and adjusts rules). Bureau's evolution is automated from behavioral data with human review as a gate, not a driver.

**Evaluation-b features**: #19

## Tier 3: Good engineering, not differentiation

These features are well-designed implementations of things SOTA already provides. They matter for execution quality but should not be claimed as differentiators.

### 26) Per-worktree container association

Docker sandboxes are commodity. OpenHands, E2B, Daytona all provide isolated execution. The per-worktree lifecycle is a nice optimization (amortizing setup cost) but the isolation itself is standard.

**Evaluation-b features**: #10

### 27) Speculative pre-computation

GitHub Copilot Workspace pre-computes plans. Cursor predicts next edits. Devin pre-plans implementation. Bureau's provenance-based prediction is a better signal source, but the *category* of "anticipate user's next action" is established.

**Evaluation-b features**: #26

### 28) Role-scoped evolving memory

Hermes does this with USER.md + Honcho. Letta does this with per-agent memory blocks. The concept is established. Bureau's competence-ledger integration adds measurement, which moves this toward Tier 2, but the base capability is not new.

**Evaluation-b features**: from earlier brainstorms (role-scoped memory concept)

### 29) Thin replaceable adapters

The adapter pattern is standard software engineering. The ~200-line budget is a good design constraint. Not a differentiator.

**Evaluation-b features**: #42

### 30) Full state observability

An important architectural property. Critical for the closed feedback loop. But not externally differentiating; users do not evaluate "can the system observe its own state transitions."

**Evaluation-b features**: #43

### 31) Skill performance metrics

Per-skill metrics (activation frequency, completion rate, satisfaction, time-to-completion, rework) are valuable. But execution tracing platforms (LangSmith, Braintrust) provide similar observability for prompts and chains. Bureau's is more granular (per-skill behavioral protocol) but the *category* is established.

**Evaluation-b features**: #16

### 32) Cross-session replay debugging

Causal replay is a stronger capability than log search. But execution tracing (LangSmith traces, Langfuse sessions, Braintrust logs) is converging toward structured replay. Bureau's provenance graph provides richer causal structure, but the gap is narrowing.

**Evaluation-b features**: #28

### 33) Benchmark-verified Assess Mode complexity claims

Auto-generating scaling benchmarks is useful. But property-based testing frameworks (Hypothesis, fast-check) and benchmark suites already exist. The integration into Assess Mode is novel; auto-benchmarking is not.

**Evaluation-b features**: #13

## Tier 4: Framing / architectural properties

Important for internal coherence and portfolio narrative. Not externally differentiating in a feature comparison.

### 34) The behavioral operating system thesis

Powerful framing: skills as processes, composition algebra as scheduler, context window as RAM, provenance as filesystem, IMMUTABLE as kernel-mode, sandbox as process isolation, autonomy as permissions. Makes decades of OS design wisdom applicable. But this is a *lens*, not a *feature*.

**Evaluation-b features**: #50

### 35) Bureau-owned abstraction contracts (Option D dependency inversion)

Critical architectural decision. Preserves ceiling. But "we own the abstractions" is an engineering choice, not a user-facing differentiator.

**Evaluation-b features**: #41

### 36) Cross-platform identity continuity via provenance

"Identity IS the provenance graph" is a beautiful architectural property. But users experience this as "my context persists across sessions," which several platforms already claim.

**Evaluation-b features**: #5

### 37) Verification events as competence signals

An important wiring decision (sandbox results feed into role scoring). But this is plumbing, not a differentiating feature.

**Evaluation-b features**: #15

### 38) Skill evolution constrained by autonomy level

"Variants start at L0 and must earn promotion" is sound safety engineering. But it is an implementation detail of the autonomy gradient, not a separately differentiating capability.

**Evaluation-b features**: #25

### 39) The meta-skill for creating skills

A fixed point in the system: the skill-authoring process is itself a skill, subject to its own rationalization table and measurement. Intellectually elegant. Practically, it is a quality gate for skill authoring, which matters for scaling but is not itself a user-facing differentiator.

**Evaluation-b features**: #39

### 40) Tool orchestration as a skill / Bootstrap as a skill

Formalizing the tools-guide decision tree and the initialization sequence as skills is good architectural consistency. But users do not experience "tool selection is a skill" as a feature; they experience "the system picks the right tool."

**Evaluation-b features**: #33, #34

## Summary: the irreducible moat

If Bureau were to describe its differentiation in a single paragraph to an evaluator who knows the SOTA:

> Bureau is the only agent system that (1) **pre-empts LLM rationalizations** using exact inference-time strings backed by N=28k empirical evidence, (2) distinguishes **agent opinion from verified fact** via a CLAIMED/VERIFIED metadata primitive propagating through compositions, (3) **withholds features during user emotional distress** via sensitivity-aware gating, (4) provides a **structured anti-sycophancy intervention library** with named cognitive failure taxonomy and calibration examples, (5) enables **formal composition of behavioral protocols** with phase ordering, interference detection, and coalescence, (6) enforces **structural constitutional constraints** (IMMUTABLE sections) on autonomous skill evolution, (7) applies **TDD to LLM behavioral compliance** via RED-GREEN-REFACTOR with combined adversarial pressure, (8) measures skill quality via **per-category golden datasets** with a non-aggregation regression rule, and (9) **closes the loop** between provenance, competence, verification, evolution, and autonomy as a single structural property. The first 8 are individually unprecedented. The 9th makes them multiplicative.

### Tier distribution

| Tier | Count | Significance |
|:---|:---|:---|
| **Unprecedented** | 12 | Genuine moat; hard to replicate because no one has attempted these |
| **Novel design** | 13 | Real differentiation; requires explaining why the design is better |
| **Good engineering** | 8 | Execution quality; not differentiating in feature comparison |
| **Framing** | 7 | Internal coherence; not externally differentiating |
| **Total** | 40 | (deduplicated from the 50 in the aspirational inventory) |

### What this means for the build order

The evaluation-b build priorities (P0-P8) should be re-evaluated against these tiers:

| Priority | Component | Tier | Adjusted rationale |
|:---|:---|:---|:---|
| **P0** | TRAINING.json golden datasets | **Unprecedented** (#8) | Highest leverage AND highest differentiation. Build first. |
| **P1** | SkillRuntime + composition algebra | **Unprecedented** (#5) | The kernel AND the moat. Build second. |
| **P2** | Provenance Graph | **Novel design** (#13, #14) | Foundation layer; differentiation in the causal edge taxonomy and back-patching, not in tracing itself. |
| **P3** | Competence Ledger | **Novel design** (#16, #18) | Differentiation in the specificity dimension and implicit signal extraction, not in "measuring agent performance." |
| **P4** | ConciergePipeline contract | **Unprecedented** (#3, #12) | The sensitivity gating and feature taxonomy are unprecedented; the pipeline contract is good engineering. |
| **P5** | ChannelGateway + Hermes adapter | **Good engineering** (#29) | Fills a gap; not differentiating. Build for capability, not moat. |
| **P6** | ExecutionSandbox + verification protocol | **Novel design** (#19) | Differentiation is in CLAIMED/VERIFIED integration, not in "run code in Docker." |
| **P7** | Autonomy Gradient | **Novel design** (#17) | Differentiation is in earned + task-scoped + ceiling-capped; the concept of "dynamic permissions" is not novel. |
| **P8** | Skill Genome | **Novel design** (#20, #25) | Differentiation is in variant A/B testing against behavioral protocols with TRAINING.json measurement. |

**The adjusted build order preserves the evaluation-b recommendation** (P0 → P8 in order). The realization is that P0, P1, and P4 are the highest-differentiation items *and* the highest-leverage items. The alignment between differentiation and leverage is the strongest argument for this build order.
