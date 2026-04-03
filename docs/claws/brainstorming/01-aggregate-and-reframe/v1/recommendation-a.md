# Claws integration evaluation: aggregate analysis and strategic recommendation

> Bureau's unique moat is not channels, not memory, not execution; it is *intelligent orchestration discipline*. The concierge pipeline and the dynamic skill system are the two things no claws platform replicates. Keep those. Let external platforms handle channels, sandboxed execution, and potentially memory evolution.

**Date:** 2026-04-03
**Scope:** aggregation and reframing of 4 independent exploration passes (v1-v4) across 7 platforms, evaluated against the specific decision of whether to drop or keep `concierge/` and `protocols/context/dynamic/skills/` in a post-claude-mem world.

## 1) Decision context

This evaluation addresses three coupled decisions:

1. **Drop claude-mem** (treating this as decided)
2. **Decide** whether to drop, partially keep, or fully keep Bureau's concierge subsystem (~10,249 lines of Python across 11 submodules)
3. **Decide** whether to drop, partially keep, or fully keep the dynamic skill evolution framework (dispatch + reflect skills, SKILL-TEMPLATE.md, TRAINING.json measurement)

The deciding factor is whether these systems' functionality/responsibilities should be:

- **Option A**: subsumed by whichever claws platform(s) Bureau adopts
- **Option B**: partially or completely kept *alongside* 1+ claws platforms
- **Option C**: completely kept, with no claws platforms added, developing Bureau as its own answer

## 2) Source material

This evaluation aggregates findings from 4 independent research passes, each evaluating 7 platforms:

| Pass | Location | Methodology | Key strength |
|:---|:---|:---|:---|
| v1 | `exploration/v1/` | Deep per-platform reports (15-33k each) + ranked synthesis | Most detailed per-platform analysis; strongest feature-level mapping |
| v2 | `exploration/v2/` | Independent deep reports (32-37k each) | Highest raw research depth; independent corroboration of v1 findings |
| v3 | `exploration/v3/` | Focused integration assessments (1.9-3.6k each) + strategy synthesis | Best Bureau-specific fit scoring; strongest merge-concept ideation |
| v4 | `exploration/v4/` | Branch reconnaissance + integration reports (2.2-5.7k each) | Most explicit about Bureau's existing strengths; clearest phased roadmap |

All four passes were conducted **completely independently** of each other (per `exploration/README.md`).

### 2.1) Cross-pass consensus

Despite independence, the passes converge on several key findings:

- **Bureau's orchestration layer is the asset to preserve**, not replace
- **Channels, memory unification, and sandboxed execution** are the three gaps to fill via integration
- **No single platform covers all three gaps**; a 2-platform stack (typically Hermes + OpenHands) is the minimum viable integration
- **Bureau's concierge pipeline and protocol system have no equivalent** in any evaluated platform

### 2.2) Cross-pass divergence

The passes disagree primarily on **platform ranking**, driven by differences in research confidence:

| Platform | v1 rank | v3 rank | v4 rank | Divergence driver |
|:---|:---|:---|:---|:---|
| Hermes | #1 | #1 (9.2/10) | #4 (low-med confidence) | v4 could not confirm canonical docs; v1/v3 found rich documentation |
| OpenHands | #2 | #2 (8.7/10) | #1 (high confidence) | Consistent high confidence across all passes |
| Letta | #3 | #2 (8.9/10) | #2 (med-high confidence) | Consistently strong on memory; varies on integration readiness |
| OpenClaw | #7 (highest risk) | #3 (8.5/10) | #3 (medium confidence) | v1 found 9 CVEs; v3/v4 evaluated without security deep-dive |
| CoPaw | #4 | #4 (6.4/10) | #6 (low confidence) | v1 found strong iMessage + security; v3/v4 found sparse canonical docs |
| OpenFang | #5 | #6 (5.8/10) | #7 (low confidence) | v1 found 40 channels + 16 security layers; v3/v4 found insufficient evidence |
| Memoh | #6 | #5 (8.1/10) | #5 (low confidence) | v1 found container isolation + AGPLv3 concern; v3/v4 had weaker signal |

**Interpretation**: OpenHands and Letta are the most *consistently* validated platforms. Hermes is the most *ambitiously* recommended (v1/v3) but with the widest confidence spread. OpenClaw carries unresolved security risk.

## 3) Dropping claude-mem: confirmed alignment

All four research passes identified Bureau's **fragmented memory stack (Qdrant + Memory MCP + claude-mem with no unified retrieval)** as one of three critical gaps.

### 3.1) What dropping claude-mem removes

- **Session-scoped observation history**: the `get_observations`, `search`, `timeline` tools that record per-session discoveries with facts, narrative, concepts, files_read, and files_modified metadata
- **Smart search**: tree-sitter AST parsing via `smart_search` and `smart_outline`
- **The only Claude-Code-specific memory dependency**: claude-mem only works in Claude Code sessions, violating Bureau's cross-CLI philosophy

### 3.2) What dropping claude-mem preserves

- **Qdrant semantic memory**: vector-based retrieval across agents and CLIs
- **Memory MCP graph memory**: explicit architecture/project facts and entity relationships
- **Dossier system**: fold/unfold workflow state continuity
- **Serena MCP**: already provides AST-aware code navigation (`find_symbol`, `get_symbols_overview`, `find_referencing_symbols`), recovering the smart_search capability through a different mechanism

### 3.3) Why it aligns with the research

- v1: "Hermes's approach (shared Qdrant + FTS5 recall) unifies the retrieval layer without replacing backends"
- v3: "Bureau already has qdrant + memory MCP + dossiers. Letta could provide a cleaner 'memory compiler' layer"
- v4: "Bureau can augment long-horizon memory continuity" via dossiers + structured memory backends

Every recommended integration path assumes a **simpler starting memory stack**. Dropping claude-mem from 3 backends to 2 is a prerequisite for clean integration with any claws platform's memory layer.

### 3.4) Session-start protocol impact

The session-start protocol (`ops/session-start.md`) currently mandates querying all three memory systems before starting any task. Post-drop, this reduces to:

- Qdrant MCP (`qdrant-find`) for past solutions and patterns
- Memory MCP (`read_graph`, `search_nodes`) for architecture and component relationships
- *(removed)* ~~claude-mem (`get_observations`, `search`) for recent session history~~

The session history function transfers to **dossier checkpoints** (already the primary cross-session continuity mechanism) and potentially to **Hermes FTS5 session search** or **Letta long-term memory** if either platform is integrated.

## 4) What concierge actually does

Before evaluating whether to keep it, a precise inventory of what `concierge/` provides:

### 4.1) The classification pipeline (`pipeline/` + `classifier/`)

A 6-stage pipeline for intelligent message triage:

1. **Suite detection** (`suite_detector.py`): classifies message context (work/rest/social/creative/processing)
2. **Attache selection** (`attache_selector.py`): routes to appropriate handler
3. **Hard rules** (`hard_rules.py`): deterministic rules for unambiguous patterns (attachments, single-word commands)
4. **Feature evaluation** (`features/*`): evaluates all 5 feature types against the current message
5. **Scoring and queuing** (`scoring.py`, `queue.py`): configurable priority weights
6. **Lottery selection** (`lottery.py`): epsilon-greedy selection with decaying exploration rate

The classification stage uses a **3-phase approach**: deterministic rules for unambiguous patterns, DistilBERT ONNX model inference for natural language, and fuzzy command verb reconciliation.

### 4.2) The feature system (`features/`)

5 distinct interaction patterns, each with its own scheduling, cooldown, and scoring logic:

| Feature type | Purpose | Scheduling |
|:---|:---|:---|
| DISPATCH | Proactive suggestions based on memory scans | 12h scan interval |
| BREW | Pattern analysis and insights | Weekly |
| PROBE | Scheduled research deliveries | Hourly |
| VALET | Multi-turn task assistance | Hourly trigger check |
| HUDDLE | Structured onboarding conversations | On-demand |

### 4.3) The bridge layer (`bridge/`)

- `telegram.py`: long-polling Telegram I/O with session state persistence (atomic YAML temp-file-then-rename)
- `adapter.py`: generic bridge interface
- `cc_connect.py`: Claude Code connection for delegated execution
- `response.py`: response formatting

### 4.4) Supporting infrastructure

- `background/runner.py`: JobQueue-based periodic scheduling
- `memory/reader.py` and `memory/writer.py`: concierge-specific memory operations
- `config/loader.py`: concierge-specific config
- `sanitizer.py`: input sanitization
- `models.py`: data models (MessageEnvelope, etc.)
- `setup/wizard.py` and `setup/launchd.py`: setup and macOS daemon management

### 4.5) Test coverage

~20 test files covering classification, features, bridge, scheduling, and pipeline components.

## 5) What dynamic skills do

### 5.1) SKILL-TEMPLATE.md: formal LLM compliance engineering

A systematic framework for authoring skills that achieve measurable LLM behavioral compliance:

- **12-section mandatory structure** with explicit ordering
- **IMMUTABLE sections** (non-negotiable directive notice, rationalization table, red flags, final rule) that cannot be modified during automated improvement cycles
- **Rationalization pre-emption tables**: two-column tables mapping exact agent excuses to concrete rebuttals; the "highest-impact compliance technique" per the template's design rationale
- **Red flags**: concrete thought-patterns (not actions) that indicate skill violation, targeting the *cognitive moment before* the violation
- **Redundant mandate placement**: core invariant appears in 4+ locations to survive context compaction
- **Hook point declarations**: programmatic enforcement at verifiable phase boundaries
- **TRAINING.json**: golden datasets with 5 case categories (basic-compliance, adversarial-pressure, rationalization-resistance, edge-case, regression) for measurable skill quality
- **RED-GREEN-REFACTOR authoring**: TDD-style skill development where failure observations drive skill construction

The design rationale cites Meincke et al. 2025 (N=28,000 conversations) where rhetorical engineering techniques doubled LLM compliance from 33% to 72%.

### 5.2) Dispatch skill

**Purpose**: disciplined parallel execution; never spawn parallel subagents without first verifying independence and defining reconciliation.

- 5 phases: Decompose, Verify Independence, Plan Reconciliation, Calibrate and Dispatch, Reconcile and Verify
- Blast-radius analysis, independence matrices, reconciliation strategies
- 10 rationalization entries, 9 red flags
- 3 hook points at phase boundaries
- Composability contract with Reflect

### 5.3) Reflect skill

**Purpose**: structured self-review before declaring work done; never present unreviewed work as final.

- 4 phases: Snapshot, Three Lenses (completeness/correctness/fitness), Revision Cycle, Confirmation
- Anti-sycophancy gates targeting the specific cognitive mode of "confirming rather than critiquing"
- Convergence detection with hard 3-cycle limit
- 10 rationalization entries, 8 red flags
- Composability contracts with Dispatch, Assess Mode, Micro Mode, and Fold

## 6) Overlap analysis: concierge + dynamic skills vs. claws platforms

### 6.1) Concierge vs. platforms

| Bureau capability | Closest claws equivalent | Overlap degree | Analysis |
|:---|:---|:---|:---|
| 6-stage classification pipeline | None | **No overlap** | No evaluated platform attempts intelligent message triage with ML-based classification |
| 5 feature types with probabilistic lottery selection | None | **No overlap** | Feature scheduling with epsilon-greedy exploration is unique |
| 3-stage classifier (deterministic + DistilBERT + fuzzy) | None | **No overlap** | The only evaluated system combining deterministic rules, neural inference, and fuzzy matching |
| Telegram bridge | Hermes (6 channels), OpenClaw (23), OpenFang (40) | **Fully subsumed** | Every channel-capable platform exceeds Telegram-only |
| Background runner (feature evaluation scheduling) | Hermes cron scheduler | **Partially subsumed** | Hermes schedules agent tasks; concierge schedules feature evaluation scans with different semantics (cooldowns, priority weights, exploration decay) |
| Memory reader/writer | Letta memory blocks, Hermes FTS5 | **Partially subsumed** | The memory I/O is generic; the *policy* around what to store/retrieve is concierge-specific |
| Setup wizard + launchd daemon | N/A | **Obsoleted** | If channels move to Hermes, standalone daemon management is unnecessary |

### 6.2) Dynamic skills vs. platforms

| Bureau capability | Closest claws equivalent | Overlap degree | Analysis |
|:---|:---|:---|:---|
| SKILL-TEMPLATE.md (formal compliance engineering) | None | **No overlap** | No platform has systematic rationalization pre-emption or IMMUTABLE section semantics |
| TRAINING.json (golden datasets for measurement) | None | **No overlap** | No platform provides measurement-oriented skill quality tracking |
| Hook-point-based programmatic enforcement | None | **No overlap** | Platforms enforce at the API level; Bureau enforces at the cognitive/behavioral level |
| TDD-style skill authoring (RED-GREEN-REFACTOR) | None | **No overlap** | Novel methodology with no equivalent in evaluated platforms |
| Skill composability contracts | None | **No overlap** | Explicit interfaces between skills (dispatch ↔ reflect) with defined input/output contracts |
| Self-improving skill evolution | Hermes skill-from-experience | **Philosophically related, structurally different** | Hermes creates skills from successful task outcomes; Bureau authors skills through systematic failure observation and rhetorical engineering. These are complementary, not redundant |

### 6.3) Summary

The concierge pipeline and dynamic skills are **~80% orthogonal** to what claws platforms offer:

- The platforms solve **channels** (I/O surfaces), **memory** (persistence/retrieval), and **execution** (sandboxed task completion)
- Bureau's concierge solves **intelligent triage** (what to do with a message), **feature scheduling** (what to proactively surface), and **probabilistic selection** (which feature to activate)
- Bureau's dynamic skills solve **behavioral discipline** (how to make LLMs follow complex workflows reliably)

The ~20% overlap is concentrated in the bridge layer (channels) and background scheduling (execution timing).

## 7) Evaluation of the three options

### 7.1) Option A: subsume by claws platform(s); drop concierge + dynamic skills

**What you gain:**

- Dramatically reduced maintenance surface (~10k lines of Python removed)
- Faster path to channel breadth via Hermes/OpenClaw
- Simpler architecture; fewer moving parts

**What you lose:**

- The **only** intelligent message triage system in the evaluated agent ecosystem
- The **only** formal LLM compliance engineering framework with:

    - rationalization pre-emption (Meincke et al. 2025 evidence base)
    - measurement datasets (TRAINING.json)
    - hook-based enforcement at cognitive decision points
    - IMMUTABLE safety sections that survive self-improvement cycles

- Bureau's **product differentiation** (the 5 feature types represent the concierge's reason for existing)
- The composability layer between skills (dispatch ↔ reflect ↔ assess-mode ↔ micro-mode)

**Research support: zero.**

- None of the 4 independent research passes recommended dropping Bureau's orchestration/protocol layer
- v3 explicitly positions Bureau as "brain/protocol governor" with Hermes as "interface/runtime fabric"
- v4 states "Bureau already excels at orchestration correctness and workflow discipline"
- v1 identifies Bureau's "66 specialized agent roles, structured workflow skills, and cohesive MCP tool ecosystem" as things "no competitor attempts"

**Verdict: not recommended.** The platforms solve channels, memory, and execution. None of them solve classification, feature scheduling, or formal skill evolution. Dropping these capabilities would eliminate Bureau's primary differentiation.

### 7.2) Option B: partially or completely keep alongside claws platform(s)

This is what all four research passes recommend, with varying emphasis. The precise split:

#### What to drop from concierge (because subsumed)

- `bridge/telegram.py`: Telegram-specific I/O; replaced by Hermes messaging gateway (6+ channels)
- `bridge/adapter.py`: generic bridge interface; replaced by Hermes channel adapters
- `setup/launchd.py`: macOS daemon management for standalone Telegram bot; unnecessary when channels are handled by Hermes
- `setup/wizard.py`: interactive setup for Telegram bot; replaced by Hermes adapter-by-adapter onboarding

*Estimated reduction*: ~1,500-2,000 lines (bridge + setup modules)

#### What to keep from concierge (because unique)

- **`pipeline/*`** (orchestrator, suite_detector, attache_selector, hard_rules, scoring, lottery, queue): the core intelligence layer; no platform replicates 6-stage classification with ML inference + probabilistic selection
- **`classifier/*`** (3-stage classification chain): the DistilBERT + deterministic rules + fuzzy matching pipeline is Bureau's inference engine
- **`features/*`** (all 5 feature types): DISPATCH, BREW, PROBE, VALET, HUDDLE represent the product; scheduling logic, cooldown periods, and exploration decay are concierge-specific
- **`background/runner.py`**: rewritten to operate inside Hermes's scheduling infrastructure (cron tick loop) rather than standalone JobQueue; preserves feature evaluation semantics while delegating execution timing to Hermes
- **`memory/*`**: simplified post-claude-mem-drop; reader/writer adapted to work with Qdrant + Memory MCP only (or Qdrant + Letta if Letta is integrated later)
- **`models.py`**: MessageEnvelope and other data models remain as the internal representation regardless of channel source
- **`sanitizer.py`**: input sanitization is always needed
- **`config/loader.py`**: concierge-specific config remains

*Estimated retention*: ~7,000-8,000 lines (pipeline + classifier + features + supporting modules)

#### What to keep entirely from dynamic skills (because nothing subsumes them)

- **`SKILL-TEMPLATE.md`**: the formal compliance engineering framework; no platform equivalent exists
- **`dispatch/`**: disciplined parallel execution with independence matrices, reconciliation plans, and phase-gated hook enforcement
- **`reflect/`**: structured self-review with anti-sycophancy gates, three-lens evaluation, and convergence detection
- **`TRAINING.json` files**: golden measurement datasets; continue accumulating cases through production use

*Estimated retention*: entire directory (~2,500 lines across all files)

#### How the integrated architecture looks

```
User (Telegram / Discord / Slack / WhatsApp / Signal / Email)
    |
    v
Hermes Agent Gateway
    |-- Channel I/O (6+ platforms)
    |-- Session management
    |-- User model (USER.md + Honcho)
    |-- Cron scheduler (hosts Bureau background runner)
    |
    v  (message received)
Bureau Concierge Pipeline
    |-- 3-stage classifier (deterministic + DistilBERT + fuzzy)
    |-- Suite detection + attache selection
    |-- Feature evaluation (DISPATCH/BREW/PROBE/VALET/HUDDLE)
    |-- Scoring + epsilon-greedy lottery
    |
    v  (feature selected; task identified)
Bureau Orchestration Layer
    |-- 66 agent roles
    |-- Dynamic skills (dispatch, reflect, + future catalog)
    |-- Assess Mode / Micro Mode / Clearance Mode
    |-- MCP tool ecosystem (Qdrant, Memory MCP, Serena, Sourcegraph, ...)
    |
    v  (execution needed)
OpenHands Sandbox
    |-- Docker-isolated runtime
    |-- Event stream state
    |-- Verified execution results
    |
    v  (learning loop)
Hermes Learning + Bureau Skill Evolution
    |-- Hermes skill-from-experience -> feeds TRAINING.json cases
    |-- Bureau SKILL-TEMPLATE.md -> formal compliance engineering
    |-- Role-scoped memory evolution (per-role MEMORY.md slices)
```

#### Research support: strong and unanimous

- v1: "Bureau = brain/protocol governor; Hermes = interface/runtime fabric" with OpenHands as execution engine
- v3: "Bureau can contribute protocol rigor, role specialization, and cross-CLI quality controls. Hermes can contribute persistent multi-channel runtime presence"
- v4: "OpenHands for deep SWE execution, Bureau for orchestration protocols, role routing, memory continuity, and cross-platform cohesion"
- All 4 passes recommend a 2-platform integration (Hermes + OpenHands) as the minimum viable stack

#### What makes this option compelling beyond the research

1. **Hermes's skill-from-experience loop can *feed* Bureau's formal skill system** rather than replace it:

    - Hermes observes successful task outcomes -> generates candidate skill proposals
    - Bureau's SKILL-TEMPLATE.md provides the engineering framework to formalize those proposals
    - TRAINING.json captures measurement cases from both production observations and Hermes feedback
    - This creates a **closed-loop skill evolution** that neither system achieves alone

2. **The concierge pipeline becomes more valuable with more channels**, not less:

    - With only Telegram, classification is constrained to one message format
    - With 6+ Hermes channels, the pipeline processes richer input diversity (voice notes, file attachments, thread contexts, reactions)
    - The DistilBERT classifier and feature scoring become *more* useful as input variety increases

3. **Bureau's dynamic skills impose quality discipline on external platform outputs**:

    - Hermes produces results; Bureau's Reflect skill validates them
    - OpenHands produces patches; Bureau's Dispatch skill verifies independence and reconciliation
    - The skills are *quality enforcement on any execution backend*, not tied to Bureau's own execution

**Verdict: recommended.** This option preserves Bureau's unique differentiation (intelligent triage + formal skill evolution) while closing its three gaps (channels via Hermes, execution via OpenHands, potentially memory via Letta later).

### 7.3) Option C: completely keep; no claws platforms; develop Bureau as its own answer

**What you gain:**

- Full architectural control; no integration coordination overhead
- Unified Python codebase; no cross-language boundaries
- Freedom to evolve without external platform roadmap constraints
- Potential to build a *superset* of evaluated platforms' capabilities

**What you lose:**

- Time. The research identified three gaps that are **expensive to build from scratch**:

    - **Channel breadth**: Hermes already has 6 mature channel adapters (Telegram, Discord, Slack, WhatsApp, Signal, Email). Building equivalent adapters from scratch: estimated months of adapter work per channel, plus ongoing maintenance as platform APIs evolve
    - **Sandboxed execution**: OpenHands has Docker isolation + 77.6% SWE-bench score + event stream state management. Building equivalent isolation: requires Docker orchestration, overlay filesystem management, security hardening, and agent-runtime coordination
    - **Learning loops**: Hermes has skill-from-experience + USER.md user modeling + Honcho integration. Building equivalent: requires outcome tracking, feedback signal extraction, and model update pipelines

**Research support: low.**

- All 4 passes explicitly recommended against pure build
- v1: "Integration is faster but adds dependencies and coordination complexity. Recommendation: integrate for channels and learning (Hermes); build if the integration doesn't fit after 2-3 months"
- v3: "Bureau can contribute protocol rigor; Hermes can contribute persistent multi-channel runtime"
- v4: "Integrate for speed; build only what provides defensible differentiation"

**When Option C makes sense (conditions):**

- If evaluated platforms fail to mature (several had "low" research confidence in v3/v4)
- If Bureau's product vision diverges from what any platform supports
- If integration proves more expensive than estimated (cross-system coordination, API churn, debugging across system boundaries)
- If the concierge pipeline evolves to handle capabilities that platforms currently provide (Bureau's MessageEnvelope is already channel-agnostic; the pipeline is decoupled from Telegram-specific I/O)

**Verdict: keep as fallback, not primary strategy.** The concierge pipeline is unique enough to be Bureau's answer to *triage and feature intelligence*, but building channels and sandboxed execution from scratch is not defensible on ROI given the current landscape. Revisit if Option B integration proves untenable.

## 8) Recommendation

**Option B**, with the following specific actions:

### 8.1) Immediate (confirmed decisions)

1. **Drop claude-mem.** Reduce memory stack from 3 backends to 2 (Qdrant + Memory MCP). Update session-start protocol. Transfer session history function to dossier checkpoints.

2. **Drop concierge's Telegram bridge layer** (`bridge/telegram.py`, `bridge/adapter.py`, `setup/launchd.py`, `setup/wizard.py`). These are the ~20% that claws platforms fully subsume.

3. **Keep concierge's pipeline, classifier, features, and background modules.** These are the ~80% that no platform replicates. Refactor to operate as a classification/routing service that receives messages from Hermes's gateway rather than Telegram directly.

4. **Keep the entire dynamic skills framework.** `SKILL-TEMPLATE.md`, `dispatch/`, `reflect/`, and all companion files. No platform equivalent exists. Accelerate the skill catalog.

### 8.2) Short-term (integration phase)

5. **Integrate Hermes** as channel gateway and scheduling host. Bureau's concierge pipeline becomes the intelligent routing layer between Hermes's channel I/O and Bureau's orchestration.

6. **Integrate OpenHands** as execution sandbox. Bureau's dispatch skill governs parallelism; OpenHands provides isolated runtime.

7. **Wire Hermes's learning loop into Bureau's skill evolution.** Hermes skill-from-experience outputs feed TRAINING.json cases. Bureau's SKILL-TEMPLATE.md provides the formal engineering framework for proposed skills.

### 8.3) Medium-term (conditional)

8. **Evaluate Letta** as memory layer *only if* Qdrant + Memory MCP proves insufficient post-claude-mem-drop. Letta's sleep-time background reflection and memory block editing could replace Bureau's `memory/reader.py` and `memory/writer.py`, but only if the simpler 2-backend stack creates measurable friction.

9. **Monitor Option C conditions.** If Hermes's maturity stalls, OpenHands's API churns, or Bureau's concierge evolves to handle channels natively, the pure-build path becomes viable. The pipeline's channel-agnostic MessageEnvelope design preserves this optionality.

### 8.4) Decision criteria for future integrations

Use these gates before committing to any platform beyond Hermes + OpenHands (adapted from v4):

1. **Technical clarity**: canonical docs, stable APIs, active maintenance
2. **Memory interoperability**: explicit model + lifecycle controls compatible with Qdrant + Memory MCP
3. **Governable autonomy**: policy hooks allowing Bureau's dynamic skills to enforce compliance on platform outputs
4. **Bureau complementarity**: net-new value beyond what the current stack provides
5. **Measured impact**: pilot KPIs indicate multiplicative (not additive) benefit

## 9) What Bureau uniquely owns after this recommendation

Regardless of which platforms are integrated, Bureau retains exclusive ownership of:

1. **Cross-CLI orchestration**: 66 specialized roles across Claude Code, Gemini CLI, Codex, and OpenCode; no platform attempts this
2. **Intelligent message triage**: 6-stage pipeline with ML-based classification and probabilistic feature selection
3. **Formal skill evolution**: SKILL-TEMPLATE.md with IMMUTABLE sections, rationalization pre-emption, TRAINING.json measurement, and RED-GREEN-REFACTOR authoring
4. **Dossier workflow**: fold/unfold state continuity for long-lived workstreams
5. **Protocol-aware autonomy governance**: dynamic autonomy level by task risk, enforced through skill phase gates and hook points
6. **Quality enforcement on external outputs**: Reflect validates any execution backend's results; Dispatch governs any delegation mechanism's parallelism

These six capabilities are Bureau's **defensible moat**. The claws platforms extend Bureau's reach (more channels, better memory, safer execution). Bureau's own systems ensure that reach is *disciplined*.

## Appendix A: platform confidence summary

Synthesized from all 4 research passes. Confidence reflects the degree to which the platform's capabilities were verified from primary sources.

| Platform | v1 confidence | v3 confidence | v4 confidence | Aggregate | Key uncertainty |
|:---|:---|:---|:---|:---|:---|
| OpenHands | High | High (8.7/10) | High | **High** | None significant |
| Letta | High | High (8.9/10) | Med-high | **Med-high** | V1 API churn; PostgreSQL dependency |
| Hermes | High | High (9.2/10) | Low-med | **Medium** | Identity ambiguity; v4 could not confirm canonical docs |
| OpenClaw | High (but 9 CVEs) | Medium (8.5/10) | Medium | **Medium (security risk)** | 9 CVEs in 4 days (March 2026); largest attack surface |
| CoPaw | High | Low (6.4/10) | Low | **Low-medium** | v1 found strong features; v3/v4 found sparse canonical docs |
| Memoh | High | Medium (8.1/10) | Low | **Low-medium** | AGPLv3 license; containerd Linux-native vs Bureau macOS |
| OpenFang | High | Low (5.8/10) | Low | **Low** | v1 found 40 channels; v3/v4 found insufficient evidence |

## Appendix B: top 10 merge concepts (cross-pass, deduplicated)

Curated from all 4 passes' brainstorm sections, selected for maximum differentiation and alignment with Bureau's retained capabilities.

1. **Role-scoped evolving memory** (v1 Hermes): each of Bureau's 66 roles gets its own memory slice; the debugger accumulates codebase failure patterns; the architect learns team preferences
2. **Verified code review via sandbox execution** (v1 OpenHands): Assess Mode proves its findings by spinning up an OpenHands sandbox and running the test suite
3. **Self-improving skills via feedback loop** (v1 Hermes + Bureau dynamic skills): Hermes evaluates task outcomes; successful runs feed TRAINING.json; failed runs trigger skill revision proposals
4. **Step-gated editing with sandboxed verification** (v1 OpenHands): Micro Mode's DAG gains a test-run gate after each step via OpenHands container
5. **Memory compiler pipeline** (v3 Letta): Bureau task artifacts become Letta block updates via deterministic transformation rules + confidence scores
6. **Sleep-time QA coach** (v3 Letta): background loops run nightly over Bureau execution traces to generate protocol improvements
7. **Autonomous maintenance loops** (v3 Hermes): Hermes scheduler runs Bureau skills in background windows (nightly safeguard checks, stale task resurfacing, dependency-risk scans)
8. **Bureau-governed OpenHands task router** (v4 OpenHands): Bureau classifies engineering work and dispatches to OpenHands execution profiles (bugfix, refactor, migration, test hardening)
9. **Multi-agent critique swarm** (v4 OpenHands): after OpenHands completes a patch, Bureau spawns role-specialist reviewers (security, performance, architecture, test) before approval
10. **Assistive-to-autonomous gradient** (v4 Hermes): single slider UX from "advisor mode" to "hands-off execution mode," implemented via progressively relaxed Bureau approval gates
