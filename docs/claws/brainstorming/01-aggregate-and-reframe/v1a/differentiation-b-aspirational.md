# Proposed Bureau differentiation: exhaustive inventory of the evaluation-b architecture

> If the 5-subsystem behavioral OS described in [evaluation-b.md](evaluation-b.md) were fully implemented, Bureau would possess 50 distinct differentiating features organized into 9 categories. No single competing platform has any one of these features. No combination of competing platforms has all 50.

**Date:** 2026-04-03
**Scope:** every feature, property, and capability that would exist in the fully-implemented evaluation-b architecture, enumerated at the same granularity as [existing-bureau-differentiation.md](existing-bureau-differentiation.md)
**Method:** features are grounded in the concrete subsystem designs from evaluation-b.md, with mechanical specificity about what each feature does and how it interacts with other features

## Category 1: Provenance Graph (foundation layer)

### 1) Structured trace event emission with rationale capture

Every agent action (tool call, file edit, memory write, skill phase transition, delegation, user decision) emits a structured event record containing: action type, input parameters, output summary, **rationale string** (the agent's stated reason for the action), confidence float, wall-clock duration, token cost, and parent-event ID. Events are append-only. The parent-event ID creates a DAG, not a flat log. Events are dual-stored: structurally in Memory MCP graph and as vector embeddings in Qdrant.

**Why genius-level**: the rationale field is the key. Every other platform logs *what happened*; Bureau logs *why the agent thought it should happen*. Combined with outcome data from the competence ledger, you can evaluate not just whether the agent made the right choice, but whether it made the right choice *for the right reason*; distinguishing flukes from genuine competence.

**Subsumes**: OpenHands event stream (actions without rationale), Hermes FTS5 (text search, not structural), claude-mem observations (Claude-Code-only, session-scoped)

### 2) Causal edge taxonomy with four relation types

Edges between provenance nodes are typed: "caused by" (direct trigger), "informed by" (read data from), "superseded by" (output later replaced), "contradicted by" (output later found incorrect). The first two are set at creation time. The latter two are **back-patched** when later events invalidate earlier ones.

**Why genius-level**: back-patching turns the provenance graph into a self-correcting record. You can query "what was believed true at time T?" and "when did we discover it was wrong?" Most lineage systems only model forward causality; Bureau models retroactive invalidity.

**Subsumes**: Letta memory block self-editing (overwrites without recording supersession), any platform's action logs (no contradiction semantics)

### 3) Dossiers as named subgraph projections

Dossiers become named entry points into the provenance graph, not snapshot files. Folding creates a dossier node with edges to every event in the session's causal subtree. Unfolding queries the reachable subgraph, reconstructing the full reasoning chain.

**Why genius-level**: traditional handoffs are lossy compression. Subgraph projection is lossless: the full causal chain is recoverable. A second agent resuming from a dossier can answer questions the original author did not anticipate by traversing the graph.

**Subsumes**: every competing platform's session handoff (all snapshot-based, not graph-based)

### 4) Memory trust scoring via provenance depth

Every memory entry receives a trust score: `trust = f(provenance_depth, contradiction_count, verification_event_count, age)`. Deep provenance chains with few contradictions and multiple verification events score high. Trust scores influence retrieval ranking.

**Why genius-level**: replaces binary "memory exists / does not exist" with a continuous reliability signal. A memory created by a verified, non-contradicted, deep causal chain is trusted; one from a single unverified action with two contradictions is flagged.

**Subsumes**: Letta memory confidence (per-block, not provenance-derived), Memoh hybrid retrieval (relevance without reliability)

### 5) Cross-platform identity continuity via provenance

Agent identity IS the provenance graph. Switching from Claude Code to Gemini CLI does not change identity because the graph persists. Sessions connect through the graph. Dossier fold/unfold becomes subgraph traversal. Identity is forkable: clone a subgraph to create a new agent with a specific subset of experience.

**Why genius-level**: every other platform ties identity to the session or API key. Bureau ties identity to the causal history of work done, surviving platform migrations, auditable by traversal, and forkable for specialization.

**Subsumes**: Hermes state.db per-instance identity (platform-locked), claude-mem cross-session observations (partial identity without causal structure)

## Category 2: Competence Ledger (role intelligence layer)

### 6) Four-dimensional role performance profiles

Per-role, per-project profiles with: (a) accuracy (outputs surviving review without "must fix"), (b) efficiency (tokens per accepted line), (c) reliability (rework rate), (d) **specificity** (was this the right role choice?). Specificity tracks whether a different role was eventually used for the same task after the first role's output was rejected.

**Why genius-level**: specificity is the non-obvious dimension. It converts every mis-dispatch into training data for the concierge pipeline's routing, answering "should the debugger have been dispatched instead of the architect?"

**Subsumes**: Hermes skill-from-experience (captures success but not mis-dispatch data), OpenClaw marketplace (no per-project performance)

### 7) TRAINING.json as calibration set for competence drift detection

Golden datasets become the calibration set for competence measurement. A background process periodically re-runs TRAINING.json scenarios through each role and compares compliance against baselines. Statistically significant decline in any per-category score triggers a regression alert.

**Why genius-level**: solves "silent degradation." Models get updated, prompts drift, memory stales. The calibration set provides a fixed reference point. The Meincke et al. non-aggregation rule (per-category regression detection) is directly operationalized.

**Subsumes**: no competing platform has measurement-oriented skill quality tracking with fixed calibration sets

### 8) Real reward signal for epsilon-greedy routing

The concierge pipeline's existing `FeatureSelector` is wired to the competence ledger's accuracy and specificity dimensions as its reward signal. The exploitation arm chooses the role with highest measured accuracy for the task category. The exploration arm continues trying alternatives, with rewards based on real outcomes.

**Why genius-level**: this is the minimum change that transforms a heuristic routing system into a genuine multi-armed bandit. The existing epsilon-greedy infrastructure (suite_fit_floor, multiplicative decay) is already correctly designed. The only missing piece was a real reward function.

**Subsumes**: Hermes skill-from-experience (qualitative), any platform's static priority routing

### 9) Implicit accept/reject signal extraction

Every user action that evaluates agent output triggers a competence update. Accepts: "looks good," "commit this," applying a shadow-mode proposal, advancing past a micro-mode step. Rejects: "no," "undo that," manual reverts, micro-mode revert-by-default. Assess Mode "must fix" findings count as partial rejections.

**Why genius-level**: implicit accept signals produce dense reward data without requiring explicit ratings. Advancing past a micro-mode step (`>`) is an implicit "acceptable." Reverting is an unambiguous rejection. Bureau infers performance signals from natural user behavior during structured editing.

**Subsumes**: no competing platform infers performance signals from implicit user actions during structured workflows

## Category 3: Sandbox Tribunal (verification layer)

### 10) Per-worktree container association

Each git worktree gets an associated lightweight container with project dependencies pre-cached. Copy-on-write overlay means verification can be destructive without risk. Container lifecycle tied to worktree lifecycle.

**Why genius-level**: the isolation boundary is the git worktree, which is the correct boundary for dev work. OpenHands uses per-task containers (paying startup cost each time). Bureau's per-worktree containers amortize cost across all tasks.

**Subsumes**: OpenHands Docker sandbox (per-task), Memoh per-bot containers (per-bot, not per-project)

### 11) CLAIMED vs. VERIFIED tagging on every agent claim

Every factual assertion about code behavior is tagged CLAIMED or VERIFIED. Verified means the sandbox executed something confirming it. The tag propagates: a composite claim containing any CLAIMED sub-claim remains CLAIMED.

**Why genius-level**: creates an explicit epistemology for agent outputs. "This function has O(n^2) complexity" with CLAIMED means "agent thinks so." With VERIFIED means "benchmarked at 150ms for n=1000, 6200ms for n=10000, confirmed quadratic." The propagation rule prevents presenting agent opinion as verified fact through composition.

**Subsumes**: no competing platform distinguishes between agent opinion and verified fact at the metadata level

### 12) Executable Scrimmage Mode attacks

Attack vectors are literally executed in the container. "Call get_user(user_id=None)" produces actual exception type, stack trace, return value. Result classifications (SURVIVED, BROKEN, POTENTIAL, MITIGATED, ACKNOWLEDGED) grounded in execution evidence, not agent reasoning.

**Why genius-level**: transforms Scrimmage Mode from sophisticated code review into automated security testing. The existing 5-category, 26-vector attack taxonomy provides test generation strategy. The sandbox provides safe execution. This is property-based testing driven by security-informed heuristics with evolving attack vectors.

**Subsumes**: OpenHands SWE-bench execution (task-oriented, not adversarial), static analysis tools (patterns, not runtime exploits)

### 13) Benchmark-verified Assess Mode complexity claims

When Assess Mode identifies efficiency concerns, the sandbox auto-generates scaling benchmarks: runs with n=100, n=1000, n=10000, fits a curve. Finding presented with data: "Benchmarked at 1.5ms (n=100), 150ms (n=1000), 15200ms (n=10000). Growth ratio: ~100x per 10x input. Confirmed quadratic."

**Why genius-level**: closes the gap between "reviewer says it's slow" and "here's the data." When sandboxing makes benchmarking cheap and automatic, every performance observation becomes data-backed.

**Subsumes**: no competing platform auto-generates scaling benchmarks to verify code review claims

### 14) Auto-verified Clearance Mode MUST criteria

Clearance criteria referencing runtime behavior (functional, behavioral, performance, edge-case types) are automatically verified in the sandbox. If the test passes, status moves to SATISFIED with VERIFIED evidence. If it fails, the criterion is FAILED regardless of the agent's self-assessment.

**Why genius-level**: eliminates "agent says it's done but it isn't." The sandbox serves as an independent arbiter uninfluenced by sycophancy, confidence, or rationalization.

**Subsumes**: no competing platform has completion criteria independently verified by an isolated execution environment

### 15) Verification events as competence signals

Every sandbox verification (pass or fail) generates a competence ledger update. Sandbox disproval is a strong negative accuracy signal. Confirmation is a positive signal. Signal strength weighted by claim specificity.

**Why genius-level**: creates a tight feedback loop between claims and evidence. Roles making many disproved claims see accuracy drop, causing routing away from them and autonomy demotion. Roles making consistently verifiable claims earn higher trust.

**Subsumes**: no competing platform feeds verification results back into role routing decisions

## Category 4: Skill Genome (evolution layer)

### 16) Skill performance metrics dashboard

Per-skill, per-project tracking: activation frequency, completion rate, user satisfaction (accept/reject ratio), time-to-completion (wall-clock + tokens), rework rate. Computed from provenance graph events.

**Why genius-level**: skills currently have no quantitative feedback. A skill with 40% completion is broken. A skill with 90% satisfaction and 30% rework produces work that looks good initially but doesn't hold up. Invisible without metrics.

**Subsumes**: no competing platform tracks per-skill performance metrics

### 17) Skill variant A/B testing via epsilon-greedy

When a skill underperforms, the genome generates a variant (modified prompt, different sequencing, added/removed constraints). The concierge's epsilon-greedy mechanism treats original and variant as competing options. After sufficient data, the losing variant is retired.

**Why genius-level**: A/B testing applied to behavioral protocols. The existing epsilon-greedy infrastructure needs minimal changes to extend from feature-type selection to skill-variant selection, enabling empirical discovery of which phrasings and structures produce better compliance.

**Subsumes**: Hermes skill-from-experience (creates skills but doesn't A/B test variants)

### 18) Skill crystallization from ad-hoc patterns

Provenance graph scanned for repeated action sequences. If 8 of 10 refactoring tasks involved Blast Radius → Micro → Scrimmage → Clearance, the system proposes a composite "hardened-refactor" mode. User accepts, rejects, or modifies.

**Why genius-level**: bottom-up skill creation from observed behavior. Repeated ad-hoc patterns are informal skills waiting to be crystallized. Formalization provides SKILL-TEMPLATE benefits (rationalization pre-emption, measurement, hooks) to previously unstructured workflows.

**Subsumes**: Hermes skill-from-experience (similar concept but Bureau produces formal, measured, IMMUTABLE-protected skills)

### 19) Rationalization table evolution

Two directions: (a) **pruning** (entries that never fire after configurable observation window flagged for removal), (b) **growth** (circumvention patterns not in the table → new entry auto-drafted from agent rationale field + observed negative outcome, queued for human review).

**Why genius-level**: currently static; evolution makes them adaptive. Pruning manages context budget (critical at 20+ skills). Growth catches rationalizations the original author couldn't anticipate as models evolve.

**Subsumes**: no competing platform has self-evolving behavioral constraint tables

### 20) Complete testing infrastructure for behavioral protocols

Competence ledger = test oracle (defines "good"). Provenance graph = test inputs (real historical scenarios). Sandbox = execution environment (isolated). TRAINING.json = regression suite. A skill variant is evaluated by replaying provenance scenarios through the variant in the sandbox, measuring against competence thresholds.

**Why genius-level**: CI/CD for agent behavior. Test inputs are real (from provenance), not synthetic. Oracles are quantitative (from ledger), not subjective. Execution is isolated (in sandbox), not production.

**Subsumes**: no competing platform has automated testing infrastructure for agent behavioral protocols

## Category 5: Autonomy Gradient (control layer)

### 21) Five-level earned autonomy spectrum

L0 Shadow (propose only) → L1 Gated (one change, pause) → L2 Batch-gated (logical group, pause) → L3 Audit-after (apply all, post-hoc review) → L4 Autonomous (apply, store evidence, summary only). Roles start at L0. Promotion: >80% acceptance at L0 → L1, >90% at L1 → L2, >95% + sandbox verification → L3, explicit user grant + sustained L3 → L4.

**Why genius-level**: existing modes (Shadow, Micro, Assess) **are already L0, L1, L3**. They were designed independently as user-activated modes; the gradient makes them automatic based on earned trust.

**Subsumes**: CoPaw tool/file guard (static), OpenFang 16-layer security (static), Memoh ACL (static)

### 22) Asymmetric promotion/demotion dynamics

Promotion requires sustained good performance over many interactions. Demotion is **immediate** on: sandbox verification failure, user rejection, safeguard violation, or scrimmage attack success. Trust is earned slowly and lost quickly.

**Why genius-level**: the asymmetry creates a ratchet favoring safety. A role at L3 for 50 sessions gets demoted to L2 on a single failure. The system converges toward the highest autonomy level that is *empirically safe*.

**Subsumes**: no competing platform has dynamic demotion from real-time failure signals

### 23) Task-scoped autonomy

Autonomy levels scoped to the intersection of role and task category. Same "architect" role: L3 for "add docstrings" (low risk, high accuracy), L0 for "modify authentication logic" (high risk, low sample size). Task categories from handoff guide authorization categories.

**Why genius-level**: competence is context-dependent. A role excelling at docs might fail at security. Task-scoped autonomy prevents blanket trust from narrow-domain performance.

**Subsumes**: no competing platform has task-scoped dynamic permissions

### 24) Authorization category ceilings

Existing categories (version control, destructive ops, production, security, breaking changes, cost-impacting) define hard autonomy ceilings regardless of competence. Production capped at L1. Security capped at L0. Cannot be exceeded even with perfect scores.

**Why genius-level**: bridges earned autonomy (data-driven) with policy constraints (risk-driven). Maximally data-driven within safe domains; maximally conservative in dangerous domains. Categories already exist in Bureau's handoff guide; the gradient enforces them structurally.

**Subsumes**: no competing platform combines earned dynamic autonomy with policy-defined ceilings

### 25) Skill evolution constrained by autonomy level

Skill variants cannot deploy at higher autonomy than the original has earned. A variant of an L2 skill starts at L0 and must independently earn promotion. The autonomy gradient IS the staging environment for skill evolution.

**Why genius-level**: solves "deploy untested change to production" for behavioral protocols. A variant goes through L0 Shadow (propose-only) before any level where it can autonomously apply changes. Automated skill improvement is safe by construction.

**Subsumes**: no competing platform has safety-constrained automated behavioral evolution

## Category 6: Emergent features (from 5-subsystem interaction)

### 26) Speculative pre-computation

During idle time, Bureau uses provenance graph patterns to predict likely next tasks and speculatively executes them in the sandbox. After PR merge: pre-run Assess Mode, pre-check CVEs, pre-build competence profiles. Speculative results cached, tagged "speculative"; served instantly on match, discarded otherwise.

**Why genius-level**: provenance graph makes prediction possible. Sandbox makes speculation safe. Competence ledger prioritizes valuable speculations. This is event-driven by causal prediction, not fixed-interval cron.

**Subsumes**: Letta sleep-time reflection (freeform), Hermes cron (fixed-interval), GitHub Copilot (token-level, not workflow-level)

### 27) Contradiction-driven memory reconciliation

New memory entries checked against existing via Qdrant cosine similarity + entailment. Contradictions create contradiction events in provenance graph, trace both memories to causal origins, present reconciliation prompt with full provenance chains. Losing memory superseded, not deleted.

**Why genius-level**: contradictions are not bugs to suppress but signals that understanding is evolving. The provenance chain lets the resolver see *why* each claim was made and what evidence supported it.

**Subsumes**: Letta memory self-editing (provenance-unaware overwrite), any last-write-wins model

### 28) Cross-session causal replay debugging

User asks "why did the agent do X three sessions ago?" Bureau walks backward through provenance graph: user request → memories consulted → tool calls → intermediate results → skill phases → rationale at each decision. Presented as structured causal chain, not log dump.

**Why genius-level**: inverts "agents are ephemeral." Logs show chronological events; replay shows causal structure ("this happened BECAUSE of that"). Essential for auditing decisions at higher autonomy levels.

**Subsumes**: Hermes FTS5 (keyword search, not causal replay), dossier summaries (lossy vs. lossless), OpenHands event stream (no causal links)

### 29) Adaptive delegation topology

Dynamic per-task topology selection: hub-and-spoke (independent workers), pipeline (sequential dependency), ensemble (redundancy for confidence), swarm (parallel exploration). Selected based on competence ledger data about role-configuration compatibility and provenance graph outcome history.

**Why genius-level**: every other platform is locked into a single delegation model. The optimal structure depends on the task: code review (hub-and-spoke) vs. debugging investigation (swarm) vs. migration (pipeline). Topology selection is data-driven and improves over time.

**Subsumes**: LangGraph static DAGs, CrewAI fixed crews, OpenHands single-agent execution. No competing platform has adaptive delegation topology.

### 30) Graduated context injection

Predict needed context blocks via concierge classification; pre-load only those. Provenance real-time trace detects agent searching for unloaded context; inject on-demand. Competence ledger accumulates role-context association data, improving prediction over time.

**Why genius-level**: context budget is the binding constraint. Every other platform loads everything (wasting tokens) or requires manual curation. Bureau automates with prediction + on-demand injection + learning. Turns a constraint into a continuously-improving capability.

**Subsumes**: Letta context hierarchy (manual), Claude Code CLAUDE.md (static), Memoh hybrid retrieval (reactive, not proactive)

### 31) Composite mode orchestration via formal composition algebra

Declarative skill composition: `Clearance + Micro + Scrimmage@paranoid + Blast Radius@standard`. Resolved using phase ordering (pre-analysis → execution → post-verification → gating). Interference detection between skills at same phase. Phase coalescence (shared analysis between verification skills).

**Why genius-level**: the compatibility matrices already exist in every SKILL.md. Formalization enables: (a) interference detection, (b) phase coalescence (one computation serves three skills), (c) emergent guarantees from N-skill composition.

**Subsumes**: no competing platform has composable agent modes with formal composition semantics

## Category 7: Skill-as-kernel architecture

### 32) Agents as skill bundles

66 role prompts re-expressed as pre-composed skill bundles. "Architect" = blast-radius + clearance + assess. Roles dynamically reconfigurable: temporarily add scrimmage@paranoid for security-sensitive work. Competence ledger attributes performance to individual skills within roles.

**Why genius-level**: roles in every other platform are monolithic prompts. Bureau decomposes into orthogonal primitives. New roles composed from existing skills without new prompts. When a role underperforms, Bureau identifies *which skill* degraded.

**Subsumes**: OpenClaw marketplace (standalone skills), Hermes skills (tools, not composable protocols), CrewAI agent roles (static definitions)

### 33) Tool orchestration as a skill

The `tools-guide.md` decision tree (Sourcegraph vs. Serena vs. Brave vs. Tavily) formalized as a skill with activation conditions, execution phases, rationalization table, and TRAINING.json. Tool selection becomes measurable, evolvable, and adversarially tested.

**Why genius-level**: tool selection is one of the highest-variance agent decisions. By making it a skill, Bureau subjects tool selection to the same evolutionary pressure and measurement as every other protocol.

**Subsumes**: Hermes dynamic tool dispatch (heuristic), OpenFang built-in tools (model-dependent selection), CoPaw tool guard (constraints, not optimization)

### 34) Bureau bootstrap as a skill

The initialization sequence (read must-read files, check context, load state, resolve config, hydrate dossiers) formalized as a skill. Measurable (time, tokens, context loaded). Improvable (lazy loading of rarely-needed context). Adversarially testable (graceful failure on missing config).

**Why genius-level**: initialization is typically invisible infrastructure. As a skill, it gets the same rigor as code review. The bootstrap skill can evolve: initial sessions load everything; after the competence ledger reveals rarely-needed blocks, bootstrap learns to defer them.

**Subsumes**: Claude Code CLAUDE.md loading (static), Hermes memory injection (fixed), Gemini GEMINI.md (static)

### 35) Formal phase ordering with interference detection

Strict phase model: pre-analysis → execution → post-verification → gating. Skills declare which phases they operate in. Contradictory instructions at the same phase detected and resolved via priorities or mediator skill.

**Why genius-level**: the difference between "modes that coexist" and "a formal algebra with well-defined composition." As skills grow (10, 20, 50), interference detection prevents combinatorial chaos.

**Subsumes**: no competing platform has interference detection between concurrent modes

### 36) Context budget management via lazy skill loading

Only activation triggers in base context (compact patterns). Full protocol loaded on activation. Deactivated skills release budget. System tracks consumption per skill. Loading order optimized by competence ledger co-activation data.

**Why genius-level**: virtual memory for LLM context. Skills are pages, context window is RAM, triggers are page table entries, co-activation data is the replacement heuristic. No competing platform treats context as a managed resource with a budget.

**Subsumes**: Letta context hierarchy (manual), token-counting libraries (measure but don't manage)

### 37) Phase coalescence across verification skills

Multiple verification skills sharing analysis results instead of redundantly computing them. Blast-radius's caller analysis feeds scrimmage's attack surface, which feeds safeguard's impact assessment. One computation serves three skills.

**Why genius-level**: without coalescence, 4 verification skills means 4 independent analysis passes. With coalescence, shared data dependencies identified at composition time and routed through a shared cache. Makes rich compositions practical, not prohibitively expensive.

**Subsumes**: no competing platform shares analysis between concurrent modes

### 38) Emergent formal verification by triangulation

Composing safeguard (invariant preservation) + clearance (criterion verification) + scrimmage (adversarial attack) + blast-radius (impact analysis) checks code from 4 independent angles. Not provably correct, but checked from so many perspectives that residual risk is very small.

**Why genius-level**: no single skill provides formal guarantees. Composition of 4 independent verification approaches, each from a different epistemological basis, produces qualitatively stronger confidence than any individual analysis.

**Subsumes**: static analysis tools (single methodology), OpenFang 16-layer security (access controls, not analytical perspectives)

### 39) Meta-skill for creating skills

Skill evolution framework expressed as a skill: its own rationalization table, TRAINING.json, compatibility matrix. The system can improve its own improvement process. Convergence via TRAINING.json measurement. IMMUTABLE sections prevent self-modification of safety checks.

**Why genius-level**: creates a fixed point. The recursion is bounded (convergence criteria) and constitutionally constrained (IMMUTABLE). Practically: enables skill authoring to scale beyond one person by defining "quality bar" measurably.

**Subsumes**: Hermes skill-from-experience (ad-hoc), OpenClaw marketplace (unverified). No competing platform has recursive, self-improving skill authoring.

### 40) IMMUTABLE constitutional constraints on self-improvement

Certain skill sections cannot be altered by any evolution mechanism, meta-skill, or autonomous modification pathway. IMMUTABLE covers: safety-critical constraints, verification obligations, and the IMMUTABLE enforcement mechanism itself. Constitutional hierarchy: improve everything except the rules preventing unsafe improvement.

**Why genius-level**: the standard AI safety concern with self-improving systems: improvement objectives optimized at expense of safety. IMMUTABLE sections solve this structurally: the evolution mechanism *cannot* modify marked sections. Not a soft guideline; a structural property.

**Subsumes**: Constitutional AI (aspirational), Guardrails AI (fixed rules). No competing platform has constitutional constraints on skill evolution.

## Category 8: Contract-based integration model (Option D)

### 41) Bureau-owned abstraction contracts

Five internal contracts: SkillRuntime, ConciergePipeline, MemoryFabric (all built natively), ChannelGateway, ExecutionSandbox (contract definitions with external adapters). Relationship: `{Hermes, OpenHands}-implements-Bureau-contracts`, not `Bureau-depends-on-{Hermes, OpenHands}`.

**Why genius-level**: dependency inversion at the system architecture level. Bureau's ceiling limited by implementation velocity, not external platform decisions. When Hermes breaks, replace a 200-line adapter. When Bureau outgrows OpenHands, replace that adapter.

**Subsumes**: Option B (Bureau adapts to externals; limited ceiling), Option C (build everything; slow)

### 42) Thin replaceable adapters (~200 lines each)

Each external adapter is a thin translation layer containing no business logic, state management, or decision-making. All intelligence in Bureau's contracts. The 200-line budget is a design constraint enforcing clean separation. Exceeding it signals leaky abstraction.

**Why genius-level**: the thinness IS the proof that Bureau owns the abstraction. Any external platform implementing a 200-line adapter becomes a Bureau backend. Adapter reliability measurable because Bureau defines "reliable."

**Subsumes**: Hermes gateway (treated as thin adapter), OpenHands sandbox (treated as thin adapter)

### 43) Full state observability (no state flowing around Bureau)

Every state transition (native or adapter) observable by Bureau's fabric. Contract model ensures adapters must emit Bureau-format events. No pathway for state to flow between external platforms without provenance recording. Bureau IS the state bus.

**Why genius-level**: in Option B, state flows between external platforms through their own channels (Hermes passes context that OpenHands never sees). In Option D, every state transition is a Bureau event. This makes the closed feedback loop structurally guaranteed.

**Subsumes**: OpenHands event stream (partial visibility), Hermes session logs (partial visibility). Bureau's observability is a superset.

## Category 9: Higher-order emergent properties

### 44) The closed adaptive loop

The 5 subsystems form a single cycle: ConciergePipeline reads Competence Ledger → Agent Execution writes Provenance Graph → Sandbox verifies claims → Provenance feeds Competence Ledger → Ledger feeds Skill Genome → Genome feeds ConciergePipeline → Ledger feeds Autonomy Gradient → Gradient constrains Execution. Every action produces data. Every data point improves routing, skills, verification, and trust.

**Why genius-level**: the system improves every time it is used, without manual intervention. This is a structural property of the architecture, not a claim about future capabilities. The loop requires Bureau ownership of all 5 subsystems; delegating any one breaks the loop.

**Subsumes**: Hermes learning loop (open; no verification or measured competence), Letta reflection (partial; no outcomes). No competing platform has a closed adaptive loop with verification, measurement, and evolution.

### 45) Concierge as immune system

The concierge pipeline, promoted to kernel subsystem: input sanitization, injection detection, intent classification, context enrichment, capability verification, output validation, feedback collection. Epsilon-greedy with real reward signal. Sensitivity-aware gating (PROCESSING suite) prevents action during inappropriate moments.

**Why genius-level**: most platforms treat input as passthrough. Bureau's concierge is a full immune response: classify, check threats, enrich, route, verify capability, validate output, collect feedback. Recognizing when NOT to act is intelligence no competing platform demonstrates.

**Subsumes**: Hermes gateway (routing without classification or sensitivity), CoPaw tool guard (guards on tools, not interactions)

### 46) Earned autonomy as system property

Not a feature but a system property: agents start cautious and earn freedom through measured performance. Shadow, Micro, Assess become automatic based on earned trust. Combined with policy ceilings, the system mirrors how organizations work: proven employees act independently on routine matters, always need approval for high-risk decisions.

**Why genius-level**: the deepest inversion. Every other platform starts permissive and gets locked down after failures. Bureau starts locked down and opens up after success. The direction matters: the first approach suffers failures before learning; the second prevents failures by requiring proof before trust.

**Subsumes**: every static permission system (CoPaw, OpenFang, Memoh, RBAC generally)

### 47) Failure-driven skill evolution

Competence ledger detects regressions. Provenance graph identifies specific failed invocations and correlates inputs, contexts, and configurations. Skill genome generates targeted variants addressing identified failure patterns. Sandbox tests variants. TRAINING.json captures failures as new regression cases.

**Why genius-level**: the scientific method applied to skill improvement. Observe failure (ledger), hypothesize cause (provenance), test fix (sandbox), measure outcome (TRAINING.json). Most improvement systems optimize for average; Bureau optimizes from failures.

**Subsumes**: manual prompt tuning (reactive, subjective), A/B testing frameworks (test without diagnosing)

### 48) Memory trust scoring as cross-cutting quality signal

Trust scores computed from provenance depth, contradiction count, verification events, age. Influence retrieval ranking (high-trust prioritized). Contribute to competence assessment (roles producing low-trust memories get lower reliability). Gate graduated context injection (high-trust memories injected first when budget constrained).

**Why genius-level**: every other memory system treats all memories as equally valid. Bureau recognizes memories have varying reliability and makes retrieval quality-aware, not just relevance-aware.

**Subsumes**: Letta memory management (no trust differentiation), RAG systems generally (retrieval without trust filtering)

### 49) Verification-as-primitive amplifying everything

Not a feature bolted onto specific modes but a primitive available to every skill. Every claim tagged CLAIMED or VERIFIED. Pervasive and cheap via sandbox. Transforms every skill from "agent thinks X" to "agent proved X."

**Why genius-level**: a single primitive that simultaneously upgrades: Assess Mode (findings → confirmed broken), Scrimmage (attacks → executable proof), Micro Mode (per-step verification), competence accuracy (verification-based signals), memory trust (verification events increase trust), autonomy promotion (verified operations justify faster promotion), skill evolution (verified outcomes = higher-quality training signal).

**Subsumes**: OpenHands execution (task completion, not trust establishment), static analysis (potential issues, not actual behavior)

### 50) The behavioral operating system thesis

Bureau as an OS: skills are processes, composition algebra is the scheduler, context window is RAM (lazy loading), provenance graph is the filesystem, IMMUTABLE sections are kernel-mode protections, sandbox is process isolation, autonomy gradient is the permission system. Every OS concept maps structurally. Decades of OS design wisdom become applicable.

**Why genius-level**: the framing makes every feature coherent. Without it, the features are an impressive collection. With it, they are a unified system architecture where every feature exists for a principled reason and amplifies every other through shared abstractions.

**Subsumes**: OpenFang "Agent Operating System" (monolithic runtime, no kernel/user separation), LangGraph/CrewAI/AutoGen (frameworks, not an OS), Hermes + OpenHands + Letta combined (incompatible abstractions). No competing platform or combination replicates a closed-loop, skill-governed, self-improving behavioral operating system.

## Summary

| Category | Count | Features |
|:---|:---|:---|
| Provenance Graph | 5 | 1-5 |
| Competence Ledger | 4 | 6-9 |
| Sandbox Tribunal | 6 | 10-15 |
| Skill Genome | 5 | 16-20 |
| Autonomy Gradient | 5 | 21-25 |
| Emergent (5-subsystem interaction) | 6 | 26-31 |
| Skill-as-kernel | 9 | 32-40 |
| Contract model (Option D) | 3 | 41-43 |
| Higher-order emergent | 7 | 44-50 |
| **Total** | **50** | |

### Multiplicative structure

- **Provenance graph** is referenced by 42 of 50 features (foundation layer)
- **Competence ledger** is referenced by 38 of 50 features (reward signal for everything)
- **Composition algebra** enables 14 features that cannot exist without it
- **The closed feedback loop** (feature 44) is the single property that makes the system multiplicative
- Every feature amplifies at least 3 other features; no feature exists in isolation
- 22 features explicitly subsume capabilities from specific competing platforms

### Competing platform subsumption

| Platform | Capabilities subsumed | Key differentiator Bureau exceeds them on |
|:---|:---|:---|
| Hermes | 9 | Causal provenance vs. keyword search; measured evolution vs. pattern-matching |
| OpenHands | 5 | Verification-as-primitive in every mode vs. execution-only sandbox |
| Letta | 6 | Provenance-aware memory with trust scoring vs. block-level management |
| OpenFang | 4 | Earned autonomy + analytical triangulation vs. layered access controls |
| CoPaw | 3 | Dynamic autonomy gradient vs. static guards |
| Memoh | 3 | Project-scoped containers + trust scoring vs. bot-scoped isolation |
| OpenClaw | 3 | Measured, composed, evolved skills vs. unmeasured marketplace |
