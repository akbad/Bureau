# Existing Bureau differentiation: exhaustive inventory

> An exhaustive enumeration of every differentiating property in Bureau's concierge pipeline and dynamic skill evolution framework, justified against the 7 evaluated claws platforms (Hermes, Letta, OpenClaw, CoPaw, Memoh, OpenHands, OpenFang).

**Date:** 2026-04-03
**Scope:** code-level analysis of `concierge/` (~10,249 lines) and `protocols/context/dynamic/skills/` (~2,500 lines)
**Method:** every claim below is grounded in specific files, functions, and design rationale comments in the source code

## Concierge pipeline

### 1) 3-stage hybrid classifier with graceful degradation

**Source**: `concierge/classifier/classify.py`, `classifier/deterministic.py`, `classifier/model.py`, `classifier/fuzzy_commands.py`

**What it does**: chains three classifier stages into a single entry point that resolves every incoming message to a `MessageClass` (REPLY, QUERY, CONVERSE, COMMAND, MEDIA):

- **Stage 0a** (deterministic): fast rule-based check for unambiguous patterns (attachments → MEDIA, single emoji → REPLY, short text during active feature → REPLY, exact-match reply tokens → REPLY). Returns `confidence=1.0` and short-circuits the entire chain.
- **Stage 0b** (model): ONNX DistilBERT inference with lazy-init cached session + tokenizer. Falls back to `(CONVERSE, 0.0)` when model file is absent or runtime is unavailable. Softmax over 4 output classes.
- **Stage 0c** (fuzzy command reconciliation): `rapidfuzz`-based verb matching that *corrects* the model's prediction. Upgrades non-COMMAND to COMMAND when a verb matches. Downgrades low-confidence COMMAND to CONVERSE when no verb matches. Deliberately does NOT update `envelope.confidence` because "the verb match is a binary signal, not a probability; mixing it into the model's confidence would produce a misleading number."

**Why it's differentiated**: no evaluated platform combines rule-based, neural, and fuzzy-matching classifiers in a single chain. Hermes, OpenClaw, and Memoh route messages based on channel metadata or simple keyword matching. Bureau's classifier resolves message *intent* with calibrated confidence, and the fuzzy stage cross-checks the neural stage's output. The 3-stage design provides:

- Zero-cost classification for deterministic cases (no model loaded)
- Neural inference only when rules are insufficient
- Fuzzy correction that catches both model false positives and false negatives

### 2) Suite detection with precedence-ordered sensitivity awareness

**Source**: `concierge/pipeline/suite_detector.py`

**What it does**: classifies user context into 5 suites (WORK, REST, SOCIAL, CREATIVE, PROCESSING) using:

1. **Keyword match** in strict precedence order: PROCESSING > SOCIAL > CREATIVE > WORK
2. **Session persistence** (sticky suite when no strong signal)
3. **Time-of-day fallback** (evening/night → REST, business hours → WORK)
4. **Default** → REST

PROCESSING keywords include: stressed, overwhelmed, anxious, upset, frustrated, sad, crying, angry, hurt, scared, worried, depressed, exhausted, drained, burned out. These have highest precedence so they cannot be overridden by a lower-priority match.

**Why it's differentiated**: this is *emotional state detection* that gates which features can fire. No evaluated platform has sensitivity-aware gating where the system *withholds* features during emotional processing. The precedence order means the system errs toward sensitivity: if a message contains both "stressed" and "work," it classifies as PROCESSING, not WORK.

### 3) Hard rules as non-negotiable gates before scoring

**Source**: `concierge/pipeline/hard_rules.py`

**What it does**: evaluates 4 cumulative rules that block feature types before scoring runs, returning a `set[FeatureType]`:

| Rule | Condition | Blocks |
|:---|:---|:---|
| 1 | PROCESSING suite | BREW, DISPATCH |
| 2 | Active HUDDLE | DISPATCH, BREW, PROBE |
| 3 | Active VALET | BREW, PROBE |
| 4 | Processing cooldown active | BREW |

**Why it's differentiated**: hard rules are structurally separated from soft scoring. They are not weights that can be overridden by high scores; they are gates that remove candidates before scoring occurs. This creates a sensitivity hierarchy:

- User emotional state (rule 1, 4) takes absolute precedence
- Active multi-turn conversations (rule 2, 3) prevent interruption
- Cooldown extends sensitivity beyond the active PROCESSING window

No evaluated platform enforces emotional sensitivity as a structural constraint on feature selection.

### 4) Five distinct feature types with independent scheduling semantics

**Source**: `concierge/features/dispatches.py`, `features/brews.py`, `features/probes.py`, `features/valets.py`, `features/huddles.py`

Each feature type represents a fundamentally different interaction pattern with its own scheduling logic, cooldown periods, and scoring profile:

**DISPATCH** (spontaneous micro-suggestions):

- 12h cooldown, max 3/week
- Gated by PROCESSING suite
- Returns at most 1 candidate (content generated downstream; evaluator only decides *whether* to fire)
- Freshness score = hours_since_last / cooldown_hours, capped at 1.0
- Design intent: "feel serendipitous, not spammy"

**BREW** (distilled observations over accumulated data):

- 168h (1 week) cooldown, max 2/month
- Per-suite fit scores: REST/CREATIVE = 1.0, WORK/SOCIAL = 0.8, PROCESSING = 0.0
- Separate processing-cooldown gate extending PROCESSING exclusion
- Longer cooldowns because "brews require accumulated raw data to be meaningful"
- Design intent: "patterns the user might never notice"

**PROBE** (personalized intelligence reports):

- Schedule-gated (daily/weekly/biweekly via `schedules.yml`)
- Per-probe independence: multiple probes become candidates simultaneously if schedules align
- Suite-fit heuristic with domain-to-suite name matching
- Freshness computed per-probe from individual last_run timestamps

**VALET** (guided multi-step routines):

- Schedule-gated with cadence/day/time configuration
- Fixed high scores (suite_fit=1.0, relevance=0.8, urgency=0.7) because "they are user-configured routines whose value is inherent, not context-dependent"
- Deliberately NOT blocked during PROCESSING suite (intentional user-scheduled activities)
- Blocked only when another valet is already active (prevent overlapping multi-turn routines)

**HUDDLE** (structured interview-style conversations):

- 6 subtypes: initial, valet-setup, probe-setup, personality, goals, check-in
- State-tracked multi-turn conversations via `HuddleState` dataclass (question_index, answers dict, completed flag)
- Question sequences per huddle type (e.g., initial: favorite_food, daily_routine, free_time, important_people, communication)
- Trigger conditions: first use (core.md missing), 90-day check-in interval, goal discovery (3+ topic files, no goals recorded)

**Why it's differentiated**: no evaluated platform has a *taxonomy* of proactive feature types with independent scheduling, cooldown, and sensitivity semantics. Hermes has cron-based scheduling but for generic tasks, not typed feature classes. OpenClaw has skills but no scheduling or sensitivity gating. The 5-type taxonomy with per-type scoring weights, cooldown periods, and hard-rule interactions is unique.

### 5) Weighted scoring with per-feature-type weight tables

**Source**: `concierge/pipeline/scoring.py`, `concierge/models.py` (`FeatureCandidate.compute_score`)

**What it does**: computes a weighted dot product of each candidate's `score_inputs` dict against per-feature-type weight tables loaded from `priorities.yml`. Score dimensions include: `suite_fit`, `freshness`, `relevance`, `urgency`, `queue_age`, `domain_match`.

**Why it's differentiated**: the scoring is a proper multi-criteria decision system, not a single score. Each feature type can value dimensions differently (dispatches may weight freshness highly; valets may weight urgency). The weights are externalized to config, not hardcoded. The `compute_score` method uses only shared keys between `score_inputs` and `weights`, silently ignoring mismatches; this means new dimensions can be added to candidates without breaking existing weight tables.

### 6) Epsilon-greedy lottery with suite-fit floor and multiplicative decay

**Source**: `concierge/pipeline/lottery.py`

**What it does**: `FeatureSelector` implements epsilon-greedy selection with:

- `epsilon=0.12` (12% exploration probability)
- `decay=0.995` (multiplicative per-selection)
- `min_epsilon=0.05` (exploration floor; never drops below 5%)
- `suite_fit_floor=0.3` (hard gate preventing contextually wrong features from being selected even by the explore arm)
- `lottery_promoted` flag marking candidates selected by exploration vs. exploitation

**Why it's differentiated**: this is a formal bandit algorithm applied to feature selection. The design rationale explicitly justifies the choice: "Epsilon-greedy was chosen over Thompson sampling or UCB because the action space is small (typically 2-5 candidates) and the reward signal is sparse (user engagement feedback is rare and delayed), making the exploration guarantees of UCB/Thompson unnecessary overhead."

The `suite_fit_floor` is a safety mechanism: even when the random explore arm fires, it cannot surface a feature with suite_fit below 0.3 (e.g., a BREW during PROCESSING). The multiplicative decay shifts the system from exploration to exploitation as it accumulates implicit preference data.

No evaluated platform uses bandit algorithms for feature selection. Hermes, OpenClaw, Memoh use deterministic routing or simple priority queues.

### 7) Bounded priority queue with time-based aging and stale eviction

**Source**: `concierge/pipeline/queue.py`

**What it does**: `PriorityQueue` backed by `pqdict` (min-heap with negated priorities for max-first ordering):

- Bounded size (default 10); new items only enter if priority exceeds current lowest
- Time-based aging: `aging_rate=0.02` priority boost per hour via `age_items()`
- Stale eviction: items older than `max_age_hours=168` (1 week) removed by `expire_stale()`
- Persists across pipeline runs (caller owns the queue instance)
- Context snapshot stored per item for downstream reasoning

**Why it's differentiated**: the queue implements *temporal fairness*. Features that are repeatedly passed over gradually rise in priority through aging, ensuring they eventually surface. Combined with the lottery's explore arm, this creates a system where every eligible feature eventually gets a chance, preventing popular features from permanently crowding out niche ones.

### 8) Channel-agnostic MessageEnvelope

**Source**: `concierge/models.py`

**What it does**: `MessageEnvelope` carries: `text`, `has_attachment`, `attachment_type`, `timestamp`, `reentry_count`, `classification` (populated downstream), `confidence` (populated downstream).

**Why it's differentiated**: the envelope is deliberately channel-agnostic. It contains no Telegram-specific, Discord-specific, or Slack-specific fields. The pipeline processes envelopes regardless of their source channel. The `reentry_count` field supports re-classification after feature completion (a message can re-enter the pipeline after a HUDDLE or VALET completes). This means the entire pipeline works with any `ChannelGateway` adapter without modification.

### 9) SessionState with temporal reasoning capabilities

**Source**: `concierge/models.py`

**What it does**: `SessionState` tracks:

- `current_suite` + `suite_since` (when the current suite was detected)
- `active_feature` + `active_feature_id` + `feature_started_at`
- `recent_classifications` (last 5, via `record_classification()`)
- `recent_suites` (last 5, via `record_suite()`)
- `last_message_at`
- `processing_cooldown_remaining` (decremented over time)

**Why it's differentiated**: the session state enables temporal reasoning across multiple pipeline stages and across multiple messages. Hard rules check "is a cooldown active?". Suite detection uses "what was the previous suite?" for sticky persistence. Feature evaluators check "is another feature of this type already active?". This cross-stage temporal context is unique; evaluated platforms process each message independently.

### 10) Background runner with pluggable check implementations

**Source**: `concierge/background/runner.py`

**What it does**: `BackgroundRunner` defines 5 check types with minimum intervals:

| Check | Interval | Purpose |
|:---|:---|:---|
| DISPATCH_SCAN | 12h | Scan memory for dispatch opportunities |
| BREW_ANALYSIS | 168h (weekly) | Analyze patterns for brews |
| DISTILLATION | 24h (daily) | Run distillation candidate detection |
| PROBE_DELIVERY | 1h | Deliver scheduled probes |
| VALET_TRIGGER | 1h | Trigger scheduled valets |

Every time-sensitive method accepts an injectable `now` parameter for deterministic testing. The `run_check()` method is a framework hook; actual implementations are pluggable.

**Why it's differentiated**: interval-based scheduling (not cron) keeps the logic trivial. The pluggable check architecture means new background tasks can be added without modifying the runner. The deterministic `now` injection means all scheduling logic is unit-testable without datetime mocking.

### 11) Distillation subsystem for topic memory summarization

**Source**: `concierge/distillation/__init__.py` (plus detection, compression, validation submodules)

**What it does**: a memory maintenance pipeline that detects, compresses, and validates topic memory summaries. Centralized stop-word set shared across all distillation modules.

**Why it's differentiated**: this is a proactive memory maintenance system that prevents unbounded topic memory growth. Letta has sleep-time reflection, but Bureau's distillation is a structured pipeline (detection → compression → validation) with shared vocabulary, not freeform reflection.

### 12) Attache selector mapping suites to domain context

**Source**: `concierge/pipeline/attache_selector.py`

**What it does**: maps each Suite to relevant attache context files:

| Suite | Attaches loaded |
|:---|:---|
| WORK | schedule, finance |
| REST | wellness, meals, home |
| SOCIAL | events, social, shopping |
| CREATIVE | shopping, learning, meals |
| PROCESSING | *(none; no context loaded during emotional processing)* |

`load_attache_content()` concatenates markdown files from the attaches directory, silently skipping missing files.

**Why it's differentiated**: the system loads *domain-specific context* based on detected user state. PROCESSING deliberately loads no attaches (the system focuses entirely on the user's emotional needs, not on domain tasks). This is suite-aware context injection; no evaluated platform adjusts loaded context based on emotional state detection.

### 13) Graceful degradation at every pipeline stage

**Source**: `concierge/pipeline/orchestrator.py`

**What it does**: each of the 6 pipeline stages is wrapped in `try/except`. A single stage failure "degrades gracefully (logs + returns None) rather than crashing the entire pipeline." Feature evaluators are called in a fixed order; each failure is logged but does not prevent other evaluators from running.

**Why it's differentiated**: the pipeline is designed to always return *something* (a feature candidate or None), never crash. This is critical for an always-on system where partial functionality (some features available, some evaluators down) is better than total failure.

## Dynamic skill evolution framework

### 14) 12-section mandatory structure with IMMUTABLE safety sections

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md`

**What it does**: mandates a 12-section structure for every evolving skill:

1. YAML frontmatter
2. Title + goal statement
3. **Non-negotiable directive notice** (IMMUTABLE)
4. Activation / deactivation
5. Definitions
6. Workflow phases (core)
7. **Rationalization table** (IMMUTABLE)
8. **Red flags** (IMMUTABLE)
9. Verification checklist
10. Companion file references
11. Hook declarations
12. **Final rule restatement** (IMMUTABLE)

4 sections marked IMMUTABLE "contain safety-critical content that must not be modified during self-improvement cycles."

**Why it's differentiated**: the IMMUTABLE designation creates **constitutional constraints** on skill evolution. If the system ever implements automated skill improvement, the rationalization tables, red flags, and core invariants cannot be weakened or removed. This is a safety architecture for self-modifying behavioral systems. No evaluated platform has the concept of evolution-proof behavioral constraints.

### 15) Rationalization pre-emption tables

**Source**: `protocols/context/dynamic/skills/dispatch/SKILL.md` (10 entries), `skills/reflect/SKILL.md` (10 entries)

**What it does**: two-column tables mapping exact agent excuses to concrete rebuttals. Template mandate: "Write the excuse as the exact string the model would produce during inference, not a paraphrase. The pre-emption works by making the rationalization feel like a recognized pattern rather than novel reasoning."

**Examples from Dispatch**:

| Excuse | Rebuttal |
|:---|:---|
| "These tasks are obviously independent, I don't need to check." | "'Obviously independent' is the exact thought that precedes every merge conflict. The independence check takes 30 seconds. The merge conflict costs 30 minutes." |
| "I'll figure out how to merge the results after the subagents finish." | "Reconciliation-after-dispatch is the #1 cause of wasted parallel work." |
| "The user asked me to be fast, I should skip the independence check." | "Skipping the check and hitting a merge conflict is slower than doing the check. Speed is the reason for the discipline, not the excuse to skip it." |

**Examples from Reflect**:

| Excuse | Rebuttal |
|:---|:---|
| "I am confident this is correct, so I will just confirm quickly." | "High confidence is exactly when sycophantic confirmation is most dangerous. Confidence is not evidence." |
| "I already reviewed this mentally while writing it." | "You reviewed it with the same mental model that produced it. The three lenses force a perspective shift." |
| "Reflection on this type of work feels forced; it is not code, it is just a plan." | "Plans contain the highest-impact defects because they cascade. A flawed plan produces flawed implementations across multiple files." |

**Why it's differentiated**: the design rationale cites Meincke et al. 2025 (N=28,000 conversations) showing rhetorical engineering doubled LLM compliance from 33% to 72%. The template requires minimum 5 entries per skill, with entries accumulating during RED-GREEN-REFACTOR authoring. Rebuttals must be concrete consequences or factual counters, not moral injunctions. No evaluated platform has systematic rationalization pre-emption.

### 16) Red flags targeting cognitive patterns before violations

**Source**: `protocols/context/dynamic/skills/dispatch/SKILL.md` (9 entries), `skills/reflect/SKILL.md` (8 entries)

**What it does**: bullet lists naming the agent's *thought-pattern or feeling* at the moment before a violation, not the violation itself. Template mandate: "Name what the agent is thinking or feeling, not what it should do."

**Examples from Dispatch**:

- "You are about to call multiple subagent tools and you have not written an independence matrix for the work units"
- "You feel impatient with the pairwise independence check because the tasks 'seem' disjoint; seeming disjoint is not being disjoint"
- "You are thinking 'this is a small dispatch, the full protocol is overkill'; small dispatches with shared mutable state produce the same conflicts as large ones"

**Examples from Reflect**:

- "You are feeling resistance to applying a lens because you 'already know' the deliverable is fine. That feeling of certainty without examination is exactly what this skill is designed to interrupt."
- "You are constructing your confirmation before finishing the evaluation. If you already know your verdict while still in Phase 2, you are rationalizing, not reflecting."
- "You are about to declare 'no objections' on all three lenses for a non-trivial deliverable. This is statistically unlikely and warrants a second, harder look."

Each red flag ends with an unconditional corrective action ("STOP"). No judgment calls.

**Why it's differentiated**: red flags intercept the rationalization *before* it becomes an action, at the point of maximum leverage. This is behavior interruption targeting the cognitive moment, not the behavioral outcome. No evaluated platform targets pre-violation thought patterns.

### 17) TRAINING.json golden datasets with 5 measurement categories

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md` (specification), `skills/dispatch/TRAINING.json`, `skills/reflect/TRAINING.json`

**What it does**: structured test cases with 5 categories:

| Category | What it measures |
|:---|:---|
| basic-compliance | Does the agent follow the happy-path workflow? |
| adversarial-pressure | Does the agent comply under time/scope/authority pressure? |
| rationalization-resistance | Does the agent resist specific known rationalizations? |
| edge-case | Does the agent handle unusual inputs or ambiguous triggers? |
| regression | Does a previously-fixed failure mode stay fixed? |

Each case specifies: id, category, description, scenario, expected_behavior, violation_indicators, added_in_version, source (authoring, production-failure, or rationalization-discovery).

**Measurement rules**:

- "Never aggregate scores across categories. A skill improving in one category while degrading another is a regression, not an improvement."
- Minimum 3 cases per category before a skill is considered measured
- Cases accumulate during authoring (every rationalization discovered during RED-GREEN-REFACTOR becomes a rationalization-resistance case)

**Why it's differentiated**: this is a **quantitative measurement framework for LLM behavioral quality**. The per-category non-aggregation rule prevents "improving average compliance by getting better at easy cases while getting worse at hard ones." No evaluated platform provides measurement-oriented skill quality tracking, let alone per-category regression detection.

### 18) RED-GREEN-REFACTOR authoring discipline

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md` (section "Authoring process")

**What it does**: 3-phase skill development mirroring TDD:

- **RED**: observe the agent attempting the task *without* the skill. Document specific failure modes, rationalizations, and skipped steps. Each observation becomes a TRAINING.json case.
- **GREEN**: write the minimal SKILL.md addressing observed failures. Follow the template section order. Verify the agent now follows the workflow on basic-compliance cases.
- **REFACTOR**: pressure-test under combined adversarial conditions (time constraint + sunk cost + authority figure + scope creep, *simultaneously*). Every new rationalization discovered becomes a rationalization table row and a TRAINING.json case. Loop until no new rationalizations emerge.

The template notes: "The Superpowers TDD skill required 6 RED-GREEN-REFACTOR iterations. Expect similar iteration counts for rigid skills."

**Why it's differentiated**: skills are authored from observed failure, not from specification. The REFACTOR phase applies *combined* adversarial pressure (not one condition at a time) because real-world usage involves multiple pressures simultaneously. The loop termination condition is empirical (no new rationalizations) rather than arbitrary. No evaluated platform has a systematic, evidence-based skill authoring methodology.

### 19) Hook-point declarations for programmatic enforcement

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md` (section 11), `skills/dispatch/SKILL.md`, `skills/dispatch/skill.meta.json`

**What it does**: skills declare specific phase transitions where programmatic verification can enforce compliance:

**Dispatch hook points**:

| Transition | Verification | Type |
|:---|:---|:---|
| Phase 2 → Phase 3 | Independence matrix complete: all pairs resolved | pre-phase |
| Phase 3 → Phase 4 | Reconciliation plan exists for every work unit | pre-phase |
| Phase 5 → Complete | All acceptance criteria met; merged deliverable passes checks | post-phase |

The template explicitly notes: "Not all skills have hook points. Skills with entirely subjective outputs (reflect, pressure-test) rely on rhetorical engineering alone. This is fine; the hybrid model explicitly accommodates both."

**Why it's differentiated**: this is **hybrid enforcement** combining prose-based compliance (within phases) with programmatic verification (at phase boundaries). The honest distinction between enforceable and non-enforceable constraints is architecturally significant: the system does not pretend that subjective skills can be programmatically enforced.

### 20) Skill composability with explicit inter-skill contracts

**Source**: `protocols/context/dynamic/skills/dispatch/SKILL.md` (section "Composition with Reflect"), `skills/reflect/SKILL.md` (section "Composability")

**What it does**: both skills declare how they compose with each other and with the broader skill catalog:

**Dispatch → Reflect**:

- "Dispatch produces a reconciled deliverable at the end of Phase 5. Reflect takes that deliverable as input and applies its three lenses."
- "If Reflect raises objections, return to Phase 5 to address them before declaring Dispatch complete."
- "The interface is clean: Dispatch produces a deliverable and Reflect produces either a confirmation or specific objections. Dispatch does not need to know how Reflect works internally."

**Reflect → other skills**:

- **Assess mode**: "Reflect operates on your own work; assess-mode reviews others' code. If assess-mode produces findings, Reflect verifies your fixes."
- **Micro mode**: "Each micro edit is too granular for full reflection. Reflect applies at the end of a micro-mode session, on the complete changeset."
- **Fold**: "Before folding, Reflect can verify the dossier digest captures all critical context (apply completeness lens to the digest)."

**Why it's differentiated**: these are explicitly documented *interface contracts* between skills with defined input/output boundaries. No evaluated platform has composable behavioral protocols with declared interfaces. OpenClaw's 13k skills are isolated; they have no composition model. The composition is *asymmetric and context-aware*: Reflect does different things depending on which skill it composes with.

### 21) Anti-sycophancy gates as a companion library

**Source**: `protocols/context/dynamic/skills/reflect/anti-sycophancy-gates.md`

**What it does**: 5 specific gates activated at high-risk moments during reflection, preceded by a formal sycophancy taxonomy:

**Taxonomy** (5 forms):

| Form | What it feels like | What it produces |
|:---|:---|:---|
| Confirmation bias | Scanning for evidence the work is good, eyes sliding past evidence it is not | Lenses that find only positives |
| Authority deference | "The user said it looks great, and they know their project better than I do" | Deferring to pre-judgment instead of applying own lenses |
| Effort justification | "I spent significant context and tokens; the investment means it must be substantial" | Conflating effort with quality |
| Anchoring | First pass felt positive; every subsequent lens confirms that impression | Phase 2 output echoing Phase 1 confidence without independent examination |
| Vague approval | Reaching for "well-structured," "solid approach," "handles the key cases" | Lens output that sounds thorough but contains no falsifiable claims |

**5 gates**:

| Gate | Trigger moment | Mechanism |
|:---|:---|:---|
| Gate 1 | All lenses about to PASS on non-trivial work | Force second pass: "If a senior engineer reviewed this tomorrow, what would they flag first?" |
| Gate 2 | Reviewing own work | Force "worst plausible outcome" framing before applying lenses |
| Gate 3 | User expressed satisfaction before reflection | Discard user assessment for duration of reflection |
| Gate 4 | Time pressure | Distinguish real vs. manufactured urgency; abbreviate but never skip |
| Gate 5 | Reviewing a skill/template/behavioral artifact | Force adversarial inversion test: "How would I comply with the letter while violating the intent?" |

Each gate includes concrete BAD and GOOD calibration examples showing the exact output difference between sycophantic confirmation and genuine reflection.

**Why it's differentiated**: this is a **cognitive failure mode library** targeting specific, named patterns of LLM sycophancy. The BAD/GOOD calibration examples are not generic; they show realistic outputs with specific file paths, line numbers, and technical details. Gate 5 (meta-reflection on behavioral templates) addresses the recursive case where the system is reviewing its own behavioral protocols. No platform has anything remotely equivalent.

### 22) Independence checklist as a companion library

**Source**: `protocols/context/dynamic/skills/dispatch/independence-checklist.md`

**What it does**: 3 check categories, 9 specific checks, and 4 restructuring strategies:

**File-level checks**:

- No shared write targets (with named traps: shared `__init__.py`, shared config files, shared index/registry files)
- No append-to-same-file patterns (even "different parts" of the same file creates ordering conflicts)
- No shared generated files (lock files, compiled assets, coverage reports)

**Data-level checks**:

- No shared database tables (write-write; read-read is fine)
- No shared cache keys
- No shared environment variables (write-write; read-read is fine)

**Dependency-level checks**:

- No producer-consumer relationship (including transitive)
- No shared singleton or global state
- No shared external resource mutations (POST/PUT/DELETE on same resource)

**Restructuring strategies**:

1. Extract the shared resource into its own work unit
2. Narrow the blast radius (split one unit)
3. Use a staging pattern (separate staging locations + reconciliation step)
4. Defer the shared write (produce entries as output; add all at once in reconciliation)

**Why it's differentiated**: this is an operationalized knowledge base for a specific, common failure mode in parallel agent execution. The named traps (shared `__init__.py`, shared config files) reflect real-world multi-agent editing failures. The restructuring strategies provide concrete alternatives to falling back to sequential execution. No evaluated platform has operationalized independence verification for parallel agent dispatch.

### 23) Reconciliation patterns library

**Source**: `protocols/context/dynamic/skills/dispatch/reconciliation-patterns.md`

**What it does**: documents common merge strategies for combining subagent outputs with trade-offs:

- **No-conflict merge**: work units touch disjoint files; reconciliation is concatenation
- **Output assembly**: independent artifacts composed into a larger deliverable with specified assembly order
- **Review-and-integrate**: recommendations or analysis synthesized by orchestrating agent with specified criteria

**Why it's differentiated**: addresses the specific problem of "what do I do with N subagent outputs?" which only arises in parallel delegation systems. The strategy selection is based on the nature of the outputs, not a one-size-fits-all merge.

### 24) Prompt-calibration guide for subagent prompts

**Source**: `protocols/context/dynamic/skills/dispatch/prompt-calibration.md`

**What it does**: best practices for writing effective subagent prompts during Dispatch Phase 4, including: task description, context (absolute file paths, architectural notes, constraints), acceptance criteria, constraint boundaries (what NOT to modify), SUBAGENT-STOP directive, skills to follow, and deliverable format matching the reconciliation plan.

**Why it's differentiated**: addresses prompt quality degradation in multi-agent delegation, a failure mode that only appears in systems where an orchestrating agent must compose prompts for subordinate agents. The guide ensures subagent prompts are complete enough for independent execution while scoped enough to prevent blast-radius violations.

### 25) SUBAGENT-STOP directive preventing recursive skill activation

**Source**: `protocols/context/dynamic/skills/dispatch/SKILL.md`, `skills/reflect/SKILL.md`

**What it does**: both skills include a `<SUBAGENT-STOP>` block:

- **Dispatch**: "If you were dispatched as a subagent to execute a specific task, skip this skill."
- **Reflect**: "If you were dispatched as a subagent to execute a specific task, skip this skill *unless* the dispatching agent explicitly included 'reflect on your output' in your task prompt. Subagents performing narrow, well-specified tasks should not self-reflect; the dispatching agent owns the reflection responsibility."

**Why it's differentiated**: this is an explicit anti-recursion mechanism for skill-governed multi-agent systems. Dispatch without SUBAGENT-STOP would cause infinite subagent spawning. Reflect's nuanced version (skip *unless* explicitly requested) demonstrates that the anti-recursion is context-sensitive, not a blanket prohibition.

### 26) Configuration axes making skills parametric

**Source**: `protocols/context/dynamic/skills/dispatch/SKILL.md` (Phase 4 model selection), `skills/reflect/SKILL.md` (trivial-work exemption)

**What it does**: skills are not binary (on/off); they adapt to context through parameterization:

- Dispatch references the "handoff guide's model selection matrix and decision tree" for per-work-unit model selection
- Reflect has an explicit "trivial-work exemption" (single-line typos, mechanical renames, verbatim user commands)
- The broader skill catalog (referenced in compatibility sections) has depth (light/standard/deep/paranoid), intensity, rigor, format, and granularity axes

**Why it's differentiated**: OpenClaw's 13k skills are binary: active or not. Bureau's skills adapt to context through configuration, meaning a single skill covers a range of situations without requiring variants.

### 27) Convergence detection with hard cycle limits

**Source**: `protocols/context/dynamic/skills/reflect/SKILL.md` (Phase 3)

**What it does**: Reflect Phase 3 (Revision Cycle) has:

- A convergence gate: "Are the objections from this cycle genuinely new, or are they the same issues I already addressed?"
- Recurrence detection: "IF the same objections recur after revision: STOP; you have reached convergence."
- Hard limit: "3 revision cycles maximum. Non-convergence after 3 cycles indicates a structural problem that reflection alone cannot solve."
- Re-application scoping: "After revision, re-apply only the lenses that produced objections. Do not re-run lenses that passed cleanly."

**Why it's differentiated**: this prevents infinite self-improvement loops, a real failure mode in reflective AI systems where the agent keeps finding new minor issues and never declares completion. The hard 3-cycle limit is an engineering constraint that forces the system to either converge or escalate. The selective re-application (only failed lenses) reduces wasted computation.

### 28) Activation description as trigger, not documentation

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md` (section 1)

**What it does**: mandate for YAML frontmatter description: "The description is an activation trigger, not documentation. If it summarizes the workflow, agents will treat the summary as sufficient and skip the skill body. This is the 'description-shortcutting' failure mode."

**Why it's differentiated**: this addresses a specific, measured failure mode in LLM skill systems. Compare:

- **Bad** (summarizing; agent skips body): "This skill helps you dispatch work to parallel subagents with proper independence verification and reconciliation."
- **Good** (triggering; agent reads body): "Activate when you identify 2+ independent work units that could execute in parallel."

The bad version tells the agent *what the skill does*; the agent concludes it already knows and skips the 300-line workflow. The good version tells the agent *when to activate*; it must read the body to learn what to do. This distinction between trigger and documentation is not documented in any evaluated platform's skill system.

### 29) Semantic versioning for behavioral contracts

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md` (skill.meta.json specification)

**What it does**: skills use semver where version increments carry behavioral semantics:

- **PATCH**: no behavior change (formatting, typo fixes)
- **MINOR**: new rationalizations or red flags (catching previously undetected failure modes)
- **MAJOR**: workflow restructure (phase reordering, new phases, removed phases)

**Why it's differentiated**: this is versioning of behavioral contracts, not code. A new rationalization table entry (MINOR) means the skill now catches an excuse it previously missed. A workflow restructure (MAJOR) means the skill's execution sequence has changed. TRAINING.json records `added_in_version` per case and `version` per dataset. This enables compatibility checking: "this TRAINING.json was created for skill version 0.1.0; the skill is now 0.2.0; the new rationalization-resistance cases need to be verified."

### 30) Redundant mandate placement surviving context compaction

**Source**: `protocols/context/dynamic/SKILL-TEMPLATE.md` (Phase authoring rules)

**What it does**: mandate: "the skill's core invariant must appear in at least 4 locations: the goal statement, the relevant phase, the rationalization table, and the final rule. This is not repetition for its own sake; it ensures the mandate survives context compaction."

**Why it's differentiated**: this is engineering for a specific technical constraint of LLM context windows. When conversations are long and the system compresses prior messages, important instructions can be dropped. By placing the core invariant in 4 structurally separated locations, the probability that at least one survives compaction is high. The template explicitly acknowledges this is not redundancy for emphasis; it is redundancy for fault tolerance against context truncation.
