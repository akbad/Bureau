# Claws integration evaluation B: ceiling-optimized analysis and the behavioral OS thesis

Bureau is not an agent orchestration layer that should integrate external platforms to fill gaps; it is the embryo of a **behavioral operating system for LLM agents** whose kernel primitive (the skill), scheduler (composition algebra), memory subsystem (provenance graph + competence ledger), and improvement loop (skill genome + TRAINING.json) form a closed-loop adaptive system that no combination of external platforms can replicate, because the multiplicative value comes from every subsystem being skill-governed and every action feeding back into the system's self-improvement.

> - **Date:** 2026-04-03
> - **Scope:** re-evaluation of [evaluation-a.md](evaluation-a.md) under a different optimization function: maximize genius-level, multiplicative, high-impact features that build world-class differentiation and form a coherent, brilliantly-designed system that is ideally a superset of competing platforms.
> - **Relationship to evaluation-a.md:** this document *supersedes* evaluation-a.md's recommendation (Option B) with a revised recommendation (Option D) while preserving evaluation-a.md's research aggregation and overlap analysis, which remain valid.

#### Contents

- [1) Why the optimization function matters](#1-why-the-optimization-function-matters)
- [2) How Option B constrains the ceiling](#2-how-option-b-constrains-the-ceiling)
  - [2.1) Hermes controls the message schema](#21-hermes-controls-the-message-schema)
  - [2.2) Hermes's learning loops compete with Bureau's skill evolution](#22-hermess-learning-loops-compete-with-bureaus-skill-evolution)
  - [2.3) OpenHands's sandbox prevents Bureau from being the system-of-record for execution state](#23-openhandss-sandbox-prevents-bureau-from-being-the-system-of-record-for-execution-state)
- [3) Option D: the reference-implementation strategy](#3-option-d-the-reference-implementation-strategy)
  - [3.1) Core principle](#31-core-principle)
  - [3.2) The 5 internal contracts](#32-the-5-internal-contracts)
  - [3.3) How this differs from Option B and Option C](#33-how-this-differs-from-option-b-and-option-c)
- [4) The 5-subsystem architecture](#4-the-5-subsystem-architecture)
  - [4.1) Provenance Graph (foundation layer)](#41-provenance-graph-foundation-layer)
  - [4.2) Competence Ledger (role intelligence layer)](#42-competence-ledger-role-intelligence-layer)
  - [4.3) Sandbox Tribunal (verification layer)](#43-sandbox-tribunal-verification-layer)
  - [4.4) Skill Genome (evolution layer)](#44-skill-genome-evolution-layer)
  - [4.5) Autonomy Gradient (control layer)](#45-autonomy-gradient-control-layer)
- [5) The closed feedback loop](#5-the-closed-feedback-loop)
- [6) The skill system as kernel](#6-the-skill-system-as-kernel)
  - [6.1) What the existing skills already demonstrate](#61-what-the-existing-skills-already-demonstrate)
  - [6.2) The composition algebra](#62-the-composition-algebra)
  - [6.3) The meta-skill](#63-the-meta-skill)
  - [6.4) Skills as the kernel: what it means for everything else](#64-skills-as-the-kernel-what-it-means-for-everything-else)
- [7) Six emergent features](#7-six-emergent-features)
  - [7.1) Speculative pre-computation](#71-speculative-pre-computation)
  - [7.2) Contradiction-driven memory reconciliation](#72-contradiction-driven-memory-reconciliation)
  - [7.3) Cross-session replay debugging](#73-cross-session-replay-debugging)
  - [7.4) Adaptive delegation topology](#74-adaptive-delegation-topology)
  - [7.5) Graduated context injection](#75-graduated-context-injection)
  - [7.6) Composite mode orchestration](#76-composite-mode-orchestration)
- [8) What Bureau uniquely owns in this design](#8-what-bureau-uniquely-owns-in-this-design)
- [9) Impact on concierge and dynamic skills (revised from evaluation-a.md)](#9-impact-on-concierge-and-dynamic-skills-revised-from-evaluation-amd)
  - [9.1) Concierge: promoted from feature to kernel subsystem](#91-concierge-promoted-from-feature-to-kernel-subsystem)
  - [9.2) Dynamic skills: promoted from scaffolding to kernel primitive](#92-dynamic-skills-promoted-from-scaffolding-to-kernel-primitive)
  - [9.3) What is dropped (same as evaluation-a.md)](#93-what-is-dropped-same-as-evaluation-amd)
- [10) Recommendation: Option D with prioritized build order](#10-recommendation-option-d-with-prioritized-build-order)
  - [10.1) What to build (ordered by leverage and portfolio impact)](#101-what-to-build-ordered-by-leverage-and-portfolio-impact)
  - [10.2) Thin slices](#102-thin-slices)
  - [10.3) Revisit triggers](#103-revisit-triggers)
  - [10.4) Risks](#104-risks)
- [11) Comparison: evaluation-a.md vs. evaluation-b.md](#11-comparison-evaluation-amd-vs-evaluation-bmd)
- [12) The thesis, restated](#12-the-thesis-restated)


## 1) Why the optimization function matters

Evaluation-a.md optimized for **floor**: pragmatic ROI, speed to fill gaps, minimum viable integration. That analysis correctly identified Bureau's three gaps (channels, sandboxed execution, learning loops) and correctly concluded that integrating Hermes + OpenHands was the fastest path to closing them.

This evaluation optimizes for **ceiling**: maximum number of genius-level, multiplicative features that form a coherent system and represent a superset of competing platforms. Under this lens, three things shift:

1. **Who owns the abstractions determines the ceiling.** Option B has Bureau adapting to Hermes's channel schema and OpenHands's execution model. This means Bureau can only implement features that fit within those external abstractions. Features that *cross subsystem boundaries* (e.g., "a scrimmage-mode attack vector discovered during assess-mode review that auto-generates a micro-mode DAG node") become API orchestration problems instead of natural state-sharing.

2. **The skill system is the kernel, not a feature.** If every subsystem (memory, channels, execution, classification) is expressed as or governed by a skill, then the skill evolution framework becomes the mechanism that makes the *entire system* self-improving. This is impossible if execution is delegated to OpenHands (which has its own, incompatible improvement loop) or if channels are delegated to Hermes (which has its own skill-from-experience model that competes for ground truth).

3. **The multiplicative value comes from a closed feedback loop.** The proposed 5-subsystem design (provenance graph, competence ledger, sandbox tribunal, skill genome, autonomy gradient) only works if Bureau owns all five. Delegating any one to an external platform breaks the loop at that point and reduces the system from multiplicative to additive.

## 2) How Option B constrains the ceiling

Three specific coupling risks that evaluation-a.md did not account for:

### 2.1) Hermes controls the message schema

If Hermes owns channel ingestion, Bureau's concierge pipeline receives messages in Hermes's format. Bureau cannot implement features that require raw message metadata, user history, or channel-specific context that Hermes does not expose or exposes in a constraining format.

- **Blocked feature example**: skill-activation confidence scoring, where the concierge pipeline assigns a probability to each skill match and uses that for feature selection, requires access to the full message context including channel-specific affordances (Telegram inline keyboards, Discord threads, Slack block kit). Hermes's abstraction layer would flatten these into a generic message, losing the signal.

### 2.2) Hermes's learning loops compete with Bureau's skill evolution

Hermes has "skill-from-experience learning." Bureau's dynamic skills have TRAINING.json measurement and RED-GREEN-REFACTOR evolution. If both are active:

- Which system is authoritative for "what this skill should do"?
- When Hermes's learning loop modifies a skill that Bureau's TRAINING.json says should behave differently, who wins?
- The coherence problem cannot be solved by integration; it requires one system to be authoritative.

### 2.3) OpenHands's sandbox prevents Bureau from being the system-of-record for execution state

Bureau's skill protocols are observability-first. Micro-mode emits step headers, step footers, diff outputs, and DAG state after every edit. Assess-mode builds dependency graphs and topological orderings. If execution happens inside an OpenHands sandbox:

- Bureau must reconstruct rich intermediate states through OpenHands's API surface
- OpenHands is optimized for "run this and return the result," not for "let me observe every intermediate state so my skill protocol can make decisions"
- This is the classic adapter anti-pattern: the adapter becomes more complex than the thing it adapts
- 77.6% SWE-bench performance is an *OpenHands* achievement; integrating it does not make Bureau better at code execution, it makes Bureau *dependent* on OpenHands continuing to improve

## 3) Option D: the reference-implementation strategy

### 3.1) Core principle

**Build the orchestration fabric yourself. Define clean internal contracts. Use external platforms as the first (replaceable) implementations behind those contracts.**

The relationship is `{Hermes, OpenHands}-implements-Bureau-contracts`, not `Bureau-depends-on-{Hermes, OpenHands}`. Bureau owns the abstractions. External platforms are pluggable backends.

### 3.2) The 5 internal contracts

| Contract | Bureau builds natively | First external adapter | Replaceability |
|:---|:---|:---|:---|
| **SkillRuntime** | Yes (this is the kernel) | N/A | N/A (always native) |
| **ConciergePipeline** | Yes (routing intelligence) | N/A | N/A (always native) |
| **MemoryFabric** | Yes (unification layer) | N/A | N/A (always native) |
| **ChannelGateway** | The contract definition | Hermes adapter (~200 lines) | Swap if Hermes stalls or Bureau builds native channels |
| **ExecutionSandbox** | The contract definition | OpenHands adapter (~200 lines) | Swap if Bureau needs deeper observability |

### 3.3) How this differs from Option B and Option C

- **Option B** says: "Integrate Hermes and OpenHands." Bureau adapts to external abstractions.
- **Option C** says: "Build everything." No external platforms.
- **Option D** says: "Define Bureau's architecture. Build the differentiators. Use existing implementations for the commodities (channel management, sandbox execution) until you have reason to replace them."

Option D respects time constraints while maintaining architectural control. It preserves the *option* to replace external platforms without requiring it upfront.

## 4) The 5-subsystem architecture

The ceiling-optimized design is a single closed-loop adaptive system with five interlocking subsystems. Each one is valuable alone, but the multiplicative power comes from how they compose.

### 4.1) Provenance Graph (foundation layer)

**What it is**: a unified, append-only directed acyclic graph recording the full causal lineage of every artifact Bureau produces. Every code change, memory write, skill invocation, agent delegation, tool call, and user decision gets a node. Edges encode "caused by," "informed by," "superseded by," and "contradicted by."

**Concrete implementation**:

- Every agent session emits structured trace events (not just logs) with: action type, inputs, outputs, rationale, confidence, duration, cost (tokens), and parent-event ID
- Events stored in Memory MCP graph (Neo4j-compatible) with Qdrant vector embeddings for semantic search
- The dossier fold/unfold system becomes the human-readable projection of this graph: a dossier is a named subgraph with an entry point, not a snapshot

**Why it is genius-level**: most platforms log actions for debugging. Bureau logs **causal structure** for learning. Debugging tells you *what happened*; provenance tells you *why it happened and what it depended on*. This inverts the "agents are ephemeral" assumption: in Bureau, no work is ever truly lost because every session's reasoning is recoverable and queryable.

**Multiplicative effects**:

- Makes every other subsystem possible (all read from and write to this graph)
- Dossier auto-hydration becomes trivial: unfold queries the subgraph rooted at a session
- Memory trust scoring becomes computable: trust = f(provenance depth, contradiction count, verification events, age)
- Cross-platform identity continuity is solved: identity *is* the provenance graph

**Subsumes/exceeds**:

| Platform capability | How provenance graph exceeds it |
|:---|:---|
| Hermes FTS5 session search | Provenance supports both semantic search (Qdrant) and structural queries (graph traversal) |
| Letta memory block self-editing | Bureau's graph has richer structure (causal, not key-value) |
| OpenHands event stream | Bureau's events carry rationale and causal links, not just action logs |
| claude-mem observations | Provenance graph is cross-CLI and cross-session by design |

### 4.2) Competence Ledger (role intelligence layer)

**What it is**: each of Bureau's 66 agent roles maintains a per-role, per-project competence profile that evolves based on observed outcomes. Not a prompt; a structured data object that the concierge pipeline reads when making dispatch decisions.

**Concrete implementation**:

- Competence dimensions per role: accuracy (did the output survive review?), efficiency (tokens per accepted line), reliability (rework rate), specificity (was this role the right choice vs. fallback?)
- Updated after every Assess Mode review, Micro Mode completion, or user accept/reject
- TRAINING.json golden datasets from the skill template system become the calibration set for measuring competence drift
- Concierge pipeline's epsilon-greedy selection uses the competence ledger as its **reward signal** (real ground truth, not heuristic priors)

**Why it is genius-level**: the key inversion is that **roles do not just get dispatched to; they get evaluated and improved**. No competing platform closes the loop between "agent did work" and "was the work good?" in a way that feeds back into routing decisions. Bureau's concierge pipeline already has the architecture for probabilistic routing; the competence ledger gives it a real reward function.

**Multiplicative effects**:

- Concierge pipeline becomes a genuine multi-armed bandit with real reward signals
- Role-scoped evolving memory falls out naturally: each role's competence profile IS its evolving memory
- Failure-driven skill evolution becomes data-driven: mine competence regressions to identify which skills need updating
- Autonomy gradient (subsystem 5) can set autonomy levels per role based on measured reliability

**Subsumes/exceeds**:

| Platform capability | How competence ledger exceeds it |
|:---|:---|
| Hermes skill-from-experience | Bureau's is quantitative (measured outcomes), not just pattern-matching |
| OpenClaw 13k skill marketplace | Bureau's 66 roles are curated and measured, which is more valuable than a large unmeasured marketplace |
| Memoh hybrid memory retrieval | Competence ledger provides structured signal that dense/sparse/BM25 retrieval alone cannot |

### 4.3) Sandbox Tribunal (verification layer)

**What it is**: a container-isolated execution environment where Bureau can **prove** claims about code before presenting them to the user. Not just "run tests"; a structured verification protocol integrated into every editing mode.

**Concrete implementation**:

- Per-worktree containers: each git worktree gets an associated lightweight container (containerd or Docker) with project dependencies pre-cached
- Verification protocol: every claim an agent makes about code behavior gets tagged `CLAIMED` or `VERIFIED`. Verified means the sandbox executed something that confirmed it
- Scrimmage Mode: attack vectors are *executed*, not hypothetical ("this input could cause a buffer overflow" becomes "this input DID cause a segfault at address X")
- Assess Mode: "this function has O(n^2) complexity" becomes "benchmarked at 150ms for n=1000, 6200ms for n=10000; confirmed quadratic"
- Clearance Mode: MUST criteria involving runtime behavior get automatically verified in sandbox rather than relying on agent assertion
- Verification events feed back into competence ledger: sandbox disproval of an agent claim is a competence signal

**Why it is genius-level**: **verification is not a feature; it is a trust primitive that makes every other feature more valuable.** An unverified code review is an opinion. A verified code review is a finding. An unverified impact analysis is a guess. A verified one is a proof. By making verification pervasive and cheap, Bureau transforms every skill from "agent thinks X" to "agent proved X."

**Multiplicative effects**:

- Assess Mode findings go from "should fix" to "confirmed broken"
- Scrimmage Mode attacks become executable proof
- Micro Mode step verification can optionally run per-step in sandbox
- Competence ledger gets verification-based accuracy signals
- Parallel debugging swarm becomes practical: N containers, N strategies, real execution

**Subsumes/exceeds**:

| Platform capability | How sandbox tribunal exceeds it |
|:---|:---|
| OpenHands Docker sandbox (77.6% SWE-bench) | Bureau's sandbox is integrated into every editing mode as a verification primitive, not just for execution |
| Memoh per-bot container isolation | Bureau's containers are project-scoped (via worktrees), which is the correct isolation boundary for dev work |
| CoPaw tool guard / file guard | Sandbox isolation is a superset: code literally cannot affect the host |
| OpenFang 16-layer security | Sandbox + Safeguard Mode + Scrimmage Mode is more rigorous than layered access controls |

### 4.4) Skill Genome (evolution layer)

**What it is**: Bureau's skills are not static documents but living artifacts that evolve based on measured outcomes, using the RED-GREEN-REFACTOR discipline already specified in the SKILL-TEMPLATE system, with the loop **closed automatically**.

**Concrete implementation**:

- Skill performance metrics: activation frequency, completion rate, user satisfaction (accept/reject ratio), time-to-completion, rework rate
- Skill variant testing: the concierge pipeline's epsilon-greedy mechanism tests skill *variants*. When a skill underperforms, the system generates a variant (modified prompt, different sequencing, added/removed constraints) and A/B tests it using provenance graph outcome data
- Skill crystallization from ad-hoc patterns: when the provenance graph reveals repeated action sequences (e.g., always running Assess then Scrimmage then Micro on the same diff), the system proposes a composite skill
- Rationalization table evolution: entries that never fire are candidates for removal; circumvention patterns generate new entries
- The competence ledger provides the test oracle, the provenance graph provides test cases, and the sandbox provides the execution environment

**Why it is genius-level**: Bureau's SKILL-TEMPLATE already has the TDD infrastructure for this (TRAINING.json, RED-GREEN-REFACTOR, hook-point enforcement). What is missing is closing the loop automatically. The competence ledger provides the oracle, the provenance graph provides the cases, the sandbox provides the environment. The entire existing skill template architecture was *designed* for this.

**Multiplicative effects**:

- Every skill benefits from evolutionary pressure, not just manually updated ones
- Concierge pipeline epsilon-greedy extends to skill variants, not just skill types
- Competence ledger accuracy improves as skills improve (better skills = better role performance = better competence signal)
- Meincke-style compliance (33% → 72%) can potentially be pushed further by evolutionary optimization of rationalization tables

**Subsumes/exceeds**:

| Platform capability | How skill genome exceeds it |
|:---|:---|
| Hermes skill-from-experience | Bureau's evolution is measured (ledger), tested (sandbox), and disciplined (RED-GREEN-REFACTOR) |
| OpenClaw 13k marketplace | Evolved skills that work for YOUR project are more valuable than 13,000 generic ones |
| Letta sleep-time reflection | Skill evolution IS background reflection, but structured and measurable rather than freeform |

### 4.5) Autonomy Gradient (control layer)

**What it is**: a dynamic, per-task autonomy system where Bureau adjusts oversight based on task risk, role competence, historical verification success, and user trust preferences. Not binary "autonomous vs. supervised"; a continuous gradient with 5 discrete levels.

**Concrete implementation**:

| Level | Name | Behavior | Earned when |
|:---|:---|:---|:---|
| L0 | Shadow | Agent proposes, never applies | Default for new roles, high-risk tasks, or after competence regression |
| L1 | Gated | One change at a time, pause for approval | Role demonstrates >80% acceptance rate at L0 |
| L2 | Batch-gated | Logical group of changes, pause for batch review | Role demonstrates >90% acceptance rate at L1 |
| L3 | Audit-after | Apply all changes, generate Assess Mode report for post-hoc review | >95% acceptance rate AND sandbox verification passes consistently |
| L4 | Autonomous | Apply changes, store verification evidence, report summary only | Explicit user trust grant + sustained L3 performance |

**Dynamic adjustment**:

- Promotion: sustained good competence ledger scores + sandbox verification passes
- Demotion: immediate on sandbox failure, user rejection, safeguard violation, or scrimmage attack success
- Task-scoped: same role can be L3 for "add docstrings" but L0 for "modify authentication logic"
- Existing authorization categories (version control, destructive ops, production, security) define **autonomy ceilings** regardless of competence

**Why it is genius-level**: **autonomy is not a configuration; it is an earned property.** Every other platform has static permission levels. Bureau's autonomy levels are conclusions derived from the competence ledger and provenance graph. The system starts cautious and becomes more autonomous as it proves itself.

**The critical insight**: the existing editing modes (Shadow, Micro, Assess) **are already implementations of autonomy levels L0-L3**. They were designed independently as user-activated modes, but they are a coherent autonomy spectrum. The gradient makes them *automatic* based on earned trust rather than manual activation.

**Multiplicative effects**:

- Shadow, Micro, Assess become autonomy levels rather than manual mode switches
- Competence ledger provides the promotion/demotion signal
- Sandbox tribunal provides verification evidence supporting promotion
- Provenance graph provides the historical record justifying a given level
- Skill genome evolution is constrained by autonomy level (a variant cannot deploy at a higher level than the original until it earns that level)

**Subsumes/exceeds**:

| Platform capability | How autonomy gradient exceeds it |
|:---|:---|
| CoPaw tool guard / file guard | Autonomy gradient adjusts dynamically; CoPaw's guards are static |
| OpenFang 16-layer security | Bureau's security is earned through demonstrated competence, not just layered access |
| Memoh ACL-based access control | Role-based access is one dimension; Bureau's autonomy is multi-dimensional (risk + competence + verification + trust) |

## 5) The closed feedback loop

The 5 subsystems form a single adaptive cycle:

```
User Request
    │
    v
ConciergePipeline ──reads──> Competence Ledger
    │                        (which role? which skill?
    │                         which autonomy level?)
    v
Agent Execution ──writes──> Provenance Graph
    │                       (what happened? why?
    │                        what was the outcome?)
    v
Sandbox Tribunal ──verifies──> Agent Claims
    │                          (is this actually true?)
    v
Provenance Graph ──feeds──> Competence Ledger
    │                       (update role/skill performance)
    v
Competence Ledger ──feeds──> Skill Genome
    │                        (evolve underperforming skills)
    v
Skill Genome ──feeds──> ConciergePipeline
    │                   (new skill variants for routing)
    v
Competence Ledger ──feeds──> Autonomy Gradient
    │                        (adjust oversight level)
    v
Autonomy Gradient ──constrains──> Agent Execution
                                  (how much freedom next?)
```

**This is a closed-loop adaptive system.** Every action produces data. Every data point improves routing, skills, verification, and trust calibration. The system gets better at its job *every time it is used*, without manual intervention.

This loop cannot exist if any subsystem is delegated to an external platform, because external platforms do not emit data in Bureau's provenance format, do not participate in Bureau's competence scoring, and do not respect Bureau's skill constraints. The loop is the product. Breaking it at any point reduces the system from multiplicative to additive.

## 6) The skill system as kernel

### 6.1) What the existing skills already demonstrate

The seven existing skills (micro, assess, scrimmage, blast-radius, clearance, safeguard, shadow) share a richer meta-structure than the original SKILL-TEMPLATE.md anticipated:

- **Configuration axes**: depth, intensity, rigor, format, granularity (each skill picks the relevant ones)
- **Dimensional analysis frameworks**: scrimmage has 5 attack categories; blast-radius has 6 analysis dimensions; clearance has 8 criterion types; safeguard has 8 invariant types
- **Result classifications** with symbol systems
- **Compatibility matrices** between every pair of skills (manually authored)

The compatibility matrices are the most architecturally significant artifact. Every skill *already declares how it composes with every other skill.* This is an embryonic **composition algebra**.

### 6.2) The composition algebra

Each skill operates at specific execution phases:

- **Pre-change hooks**: blast-radius, safeguard (pre-change analysis)
- **Execution modifiers**: micro (granularity), shadow (output mode)
- **Post-change hooks**: scrimmage (attack), safeguard (verify), clearance (track)
- **Completion gates**: clearance (criteria), safeguard (no violations)

The composition is not commutative in all cases. Blast-radius runs pre-change ("what could break?"); scrimmage runs post-change ("can I break what I wrote?"). The algebra respects a phase ordering: pre-analysis → execution → post-verification → gating.

**At N=10-20 skills, emergent properties arise**:

1. **Interference detection**: two skills might issue contradictory instructions at the same phase. The system needs formal conflict resolution (skill priorities or a mediator skill).
2. **Context budget pressure**: each skill adds ~400-800 lines. At 20 skills, this exceeds context windows. The system needs lazy skill loading (full protocol on activation, just triggers in base context).
3. **Phase coalescence**: verification skills can share analysis (blast-radius caller analysis feeds scrimmage's attack surface identification feeds safeguard's impact assessment), eliminating redundant work.
4. **Emergent guarantees**: composing safeguard + clearance + scrimmage + blast-radius produces something approaching **formal verification by triangulation**; not provably correct, but checked from so many angles that residual risk is very small. This is qualitatively different from any single skill.

### 6.3) The meta-skill

The skill evolution framework can itself be expressed as a skill: a meta-skill for creating skills, complete with its own rationalization table:

| Rationalization | Rebuttal |
|:---|:---|
| "This behavior doesn't need a formal skill" | If it has activation conditions, execution phases, and failure modes, it is a skill. Informality is how drift starts. |
| "The compatibility matrix is too much overhead" | Every undeclared skill interaction becomes a bug. The matrix IS the architecture. |
| "We can add TRAINING.json later" | A skill without golden datasets is an untested hypothesis. Red-green-refactor means red comes first. |
| "The existing skill template is too rigid" | The template is the minimum viable structure preventing the failure modes Meincke et al. measured. Removing sections removes protections. |
| "This skill is too simple to need verification" | Simple skills compose into complex behaviors. Unverified components produce unverified compositions. |

**What the recursion buys**: the meta-skill creates a fixed point. The system can improve its own improvement process. Scrimmage mode can attack scrimmage mode's own attack taxonomy. This converges because each iteration produces measurable improvements (via TRAINING.json) and improvements plateau.

More practically: the meta-skill is how skill authoring **scales beyond a single person**. A meta-skill with its own golden datasets means anyone can author a skill that meets the quality bar.

### 6.4) Skills as the kernel: what it means for everything else

If the skill framework is the architecture (not a feature of the architecture):

- **Agents become skill bundles.** The "architect" role prompt is a pre-composed set: blast-radius (always analyze impact) + clearance (define done criteria) + assess (review quality). The 66 role prompts become configurations of which skills are active by default.
- **Tool orchestration becomes a skill.** The `tools-guide.md` decision tree (when to use Sourcegraph vs. Serena vs. Brave) is a skill. The memory storage protocol is a skill. They have not been formalized as such, but they have all the hallmarks.
- **The Bureau bootstrap itself becomes a skill.** Reading must-read files, checking for existing context, loading previous session state: this is the "initialization" skill.

**Every other part of Bureau (agents, tools, memory, configuration) is static infrastructure that executes the same way every time. Skills are the only part that prescribes how to execute, verifies that execution was correct, and has a mechanism for improving over time.** That is what makes the skill system the kernel.

## 7) Six emergent features

These are not separate subsystems; they are natural consequences of the five above. They emerge from the architecture rather than being designed independently.

### 7.1) Speculative pre-computation

During idle time (or on cron), Bureau speculatively runs likely next tasks. After a PR merge: pre-run Assess Mode on the main branch diff, pre-check dependency vulnerabilities, pre-build competence profiles for new code.

- Uses provenance graph to predict likely next actions
- Uses sandbox to execute speculatively and safely
- Uses competence ledger to prioritize which speculations are most valuable
- *Subsumes*: Letta sleep-time reflection, Hermes cron scheduler; but targeted by provenance-based prediction rather than fixed schedules

### 7.2) Contradiction-driven memory reconciliation

When any agent writes a memory that semantically contradicts an existing memory (detected via Qdrant cosine similarity + entailment check), the system creates a **contradiction event** in the provenance graph, traces both memories to their causal origins, and presents a reconciliation prompt with the full provenance chain for both claims.

- Memory trust scoring becomes computable from contradiction count
- Competence ledger uses contradiction frequency as reliability signal
- Skill genome detects if a variant produces more contradictions than the original
- *Subsumes*: Letta memory block self-editing (Bureau's is provenance-aware and contradiction-detecting)

### 7.3) Cross-session replay debugging

When a user asks "why did the agent do X three sessions ago?", Bureau replays the causal chain from the provenance graph: exactly which inputs, memories, tool results, and intermediate reasoning led to that decision. Not a log viewer; a causal debugger for agent behavior.

- Provenance graph makes this possible
- Competence ledger makes it useful (replay reveals where competence assessments went wrong)
- Autonomy gradient makes it necessary (users need to audit decisions at higher autonomy levels)
- *Subsumes*: Hermes FTS5 session search, dossier auto-hydration; replay is a superset of search

### 7.4) Adaptive delegation topology

Instead of hub-and-spoke delegation (one orchestrator dispatches to subagents), the system dynamically constructs the optimal delegation topology based on task structure:

- **Hub-and-spoke**: one orchestrator, N independent workers (current model)
- **Pipeline**: agent A's output feeds agent B (sequential dependency)
- **Ensemble**: 3 agents solve independently, results reconciled (redundancy for confidence)
- **Swarm**: N agents explore different strategies, cross-reference findings (search problem)

Topology chosen based on competence ledger data about which roles work well in which configurations. Provenance graph reveals which patterns historically produced better outcomes.

- *No competing platform has adaptive delegation topology*
- Pure Bureau differentiation built on Bureau's unique multi-CLI, multi-role foundation

### 7.5) Graduated context injection

Instead of loading all context upfront (wasting tokens), Bureau injects context progressively:

- Concierge pipeline predicts which context blocks an agent needs based on task classification
- Pre-loads only those blocks
- Provenance graph's real-time trace detects when the agent searches for information in an unloaded block; injects on-demand
- Competence ledger reveals which roles consistently need which blocks (improving prediction over time)
- *Subsumes*: Letta context hierarchy and block semantics (Bureau's is prediction-driven rather than manually managed)

### 7.6) Composite mode orchestration

Skills compose declaratively. Instead of manually activating "Micro + Scrimmage + Clearance," a user declares:

```
COMPOSITE MODE: "hardened-implementation"
  = Clearance Mode (define done criteria)
  + Micro Mode (step-gated edits)
  + Scrimmage Mode @ depth:paranoid (attack after each step)
  + Blast Radius Mode @ depth:standard (impact before each step)
  + Clearance Mode (verify all criteria at end)
```

The existing compatibility matrices in every SKILL.md become a formal composition algebra.

- Skill genome evolves optimal compositions for different task types
- Competence ledger measures composite performance
- Autonomy gradient adjusts per-composite (a well-tested composite can run at higher autonomy)
- *No competing platform has composable agent modes*

## 8) What Bureau uniquely owns in this design

Regardless of which external adapters are used behind the contracts, Bureau retains exclusive ownership of:

1. **The behavioral type system**: skills as typed, composable, adversarially-robust behavioral protocols with a formal composition algebra
2. **The closed adaptive loop**: provenance → competence → sandbox → skill evolution → autonomy → execution → provenance
3. **Earned autonomy**: the only system where agents start cautious and earn freedom through measured performance, not configuration
4. **Verification-as-primitive**: every claim is tagged CLAIMED or VERIFIED; the sandbox makes verification pervasive and cheap
5. **The meta-skill**: the system can improve its own improvement process, with IMMUTABLE constitutional constraints preventing self-modification of safety-critical sections
6. **Causal memory**: provenance graph stores *why* things happened, not just *what* happened; identity is the graph, not the session
7. **Measured skill evolution**: skills evolve via quantitative outcome data, not ad-hoc pattern matching
8. **Adaptive delegation topology**: hub-and-spoke, pipeline, ensemble, and swarm topologies selected per-task based on historical outcome data

No single competing platform has any one of these. No combination of competing platforms has all eight. Building them requires architectural control over every subsystem, which is why Option D (own the contracts, use external platforms as pluggable backends) is the correct strategy for ceiling optimization.

## 9) Impact on concierge and dynamic skills (revised from evaluation-a.md)

### 9.1) Concierge: promoted from feature to kernel subsystem

Under evaluation-a.md (Option B), the concierge pipeline stayed mostly intact with the Telegram bridge dropped. Under Option D, the concierge is **elevated**:

- The 6-stage pipeline becomes the `ConciergePipeline` contract that every channel adapter feeds into
- The DistilBERT classifier and probabilistic feature selection become core infrastructure
- The epsilon-greedy selection gains a real reward signal (competence ledger) instead of heuristic priors
- The concierge becomes the **immune system** of the platform: input sanitization, injection detection, intent classification, context enrichment, capability verification, output validation, and feedback collection all happen in a single pipeline

### 9.2) Dynamic skills: promoted from scaffolding to kernel primitive

Under evaluation-a.md, dynamic skills were "kept entirely because nothing subsumes them." Under Option D, they become the **fundamental abstraction**:

- Every subsystem behavior is expressed as or governed by a skill
- The composition algebra (currently manual compatibility matrices) is formalized
- TRAINING.json becomes the system-wide quality metric
- The meta-skill enables skill authoring to scale beyond one person
- IMMUTABLE sections become constitutional constraints that survive autonomous self-improvement

### 9.3) What is dropped (same as evaluation-a.md)

- claude-mem (confirmed; reduces memory stack from 3 to 2)
- Telegram bridge layer (`bridge/telegram.py`, `bridge/adapter.py`, `setup/launchd.py`, `setup/wizard.py`); replaced by ChannelGateway contract + Hermes adapter

## 10) Recommendation: Option D with prioritized build order

### 10.1) What to build (ordered by leverage and portfolio impact)

| Priority | Component | Rationale |
|:---|:---|:---|
| **P0** | TRAINING.json golden datasets for 3+ existing skills | The measurement foundation; without this, nothing else can be evaluated. Single highest-leverage investment. |
| **P1** | SkillRuntime contract + composition algebra formalization | The kernel. Currently implicit in compatibility matrices; needs to be explicit. |
| **P2** | Provenance Graph (trace events from existing skill execution) | Foundation for competence ledger, contradiction detection, replay debugging. Start with append-only logging; enrich later. |
| **P3** | Competence Ledger (per-role performance tracking) | Closes the loop between "agent did work" and "was the work good?". Transforms concierge pipeline from heuristic to data-driven. |
| **P4** | ConciergePipeline contract (receiving messages from any ChannelGateway) | Decouples the pipeline from Telegram; enables multi-channel. |
| **P5** | ChannelGateway contract + Hermes adapter | Multi-channel capability via thin adapter. |
| **P6** | ExecutionSandbox contract + container verification protocol | The trust primitive. Start with Docker; can replace OpenHands adapter later. |
| **P7** | Autonomy Gradient (earned trust levels) | Requires competence ledger and sandbox to be functional first. |
| **P8** | Skill Genome (automated evolution) | Requires TRAINING.json, provenance graph, and competence ledger. The capstone. |

### 10.2) Thin slices

Each priority is independently demonstrable:

- **P0** (TRAINING.json): deliverable is golden datasets + compliance measurement for assess-mode, micro-mode, and scrimmage-mode
- **P1** (SkillRuntime): deliverable is a formal phase model (pre-analysis / execution / post-verification / gating) with hook points that replace the manual compatibility matrices
- **P2** (Provenance Graph): deliverable is structured trace events emitted during normal skill execution, queryable via Memory MCP
- **P3** (Competence Ledger): deliverable is a role performance dashboard showing accuracy/efficiency/reliability after N sessions

### 10.3) Revisit triggers

- **Downgrade to Option B** if: Bureau needs a working end-to-end demo in weeks and the contract-first approach is too slow
- **Upgrade to full Option C** if: Bureau gains a second developer, or external platforms introduce breaking changes making adapters more expensive than native implementations
- **Validate P0 first**: if TRAINING.json measurement reveals that skill compliance is already high (>85%) without evolution, the Skill Genome (P8) becomes lower priority and resources shift to other subsystems

### 10.4) Risks

| Risk | Mitigation |
|:---|:---|
| Abstraction astronautics | Every contract must have a concrete implementation within 2 weeks of definition |
| Solo developer bottleneck | Priorities ordered by leverage; completing P0-P3 alone delivers the most differentiated components |
| TRAINING.json authoring cost | Start with 3-5 cases per category per skill; accumulate during normal usage |
| Feedback loop cold-start | Competence ledger needs N sessions of data before it is useful; run in shadow mode (record but don't act on) for the first 50 sessions |
| Portfolio vs. product tension | This analysis informs what to build when Bureau is reactivated; the prioritization respects time constraints |

## 11) Comparison: evaluation-a.md vs. evaluation-b.md

| Dimension | Evaluation A (Option B) | Evaluation B (Option D) |
|:---|:---|:---|
| **Optimization function** | Floor (pragmatic ROI, speed) | Ceiling (maximum differentiation, multiplicative features) |
| **Concierge** | Keep pipeline, drop bridge | Promote to kernel subsystem with real reward signals |
| **Dynamic skills** | Keep entirely | Promote to kernel primitive; formalize composition algebra |
| **External platforms** | Bureau depends on Hermes + OpenHands | Hermes + OpenHands implement Bureau's contracts |
| **Who owns abstractions** | External platforms | Bureau |
| **Learning loop** | Hermes skill-from-experience feeds Bureau | Bureau's closed loop (provenance → competence → sandbox → skill genome → autonomy) |
| **Memory** | Qdrant + Memory MCP (drop claude-mem) | Same backends, unified by MemoryFabric contract + provenance graph overlay |
| **Ceiling constraint** | Limited by external platform abstractions | Limited by implementation velocity |
| **Floor risk** | Low (fast integration) | Higher (more to build before value emerges) |
| **Portfolio story** | "Integrated two platforms efficiently" | "Designed a behavioral operating system for LLM agents" |

## 12) The thesis, restated

Bureau's seven existing skills, with their configuration axes, dimensional analysis frameworks, result classifications, and compatibility matrices, already constitute the embryo of a behavioral type system for LLM agents. The SKILL-TEMPLATE.md with its IMMUTABLE sections, rationalization pre-emption, and TRAINING.json measurement is the kernel's process model. The concierge pipeline with its probabilistic feature selection is the scheduler.

What is missing is the feedback loop: provenance graph (causal memory), competence ledger (measured performance), sandbox tribunal (verification as primitive), skill genome (automated evolution), and autonomy gradient (earned trust). These five subsystems, built around Bureau-owned contracts with external platforms as pluggable adapters, create a closed-loop adaptive system where every action improves future actions.

No competing platform has this architecture. No combination of competing platforms can replicate it. It is multiplicative because every subsystem amplifies every other. It is coherent because the skill is the universal primitive. It is a superset because it subsumes channels (via ChannelGateway), execution (via ExecutionSandbox), memory (via MemoryFabric + provenance), learning (via skill genome), and security (via sandbox + autonomy gradient) while adding dimensions (causal provenance, earned autonomy, formal composition, measured evolution) that no platform offers.

The recommendation is Option D: build this architecture, starting with TRAINING.json (the measurement foundation) and the SkillRuntime contract (the kernel formalization), using Hermes and OpenHands as pluggable first implementations behind Bureau-owned contracts.
