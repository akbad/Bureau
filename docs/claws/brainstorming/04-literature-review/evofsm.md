# EvoFSM and the Self-Evolving Agent Landscape

**Agent:** `lit-evofsm`
**Date:** 2026-04-03
**Assignment:** EvoFSM (2025-2026) — FSM-constrained self-evolution — plus the broader self-evolving agent literature
**Bureau relevance:** High — directly addresses how to let agents self-improve without losing behavioral guarantees

---

## 1. EvoFSM paper summary

**Paper:** EvoFSM: Controllable Self-Evolution for Deep Research with Finite State Machines
**arXiv:** [2601.09465](https://arxiv.org/abs/2601.09465)
**Year:** January 2026

### Problem statement

LLM-based agents exhibit strong static performance but degrade on open-ended, multi-hop queries that require adaptive problem-solving. Prior approaches address this by allowing agents to rewrite their own code or prompts — but unconstrained optimization produces instability, hallucinations, and instruction drift. The core tension: how do you gain adaptability without losing behavioral guarantees?

### The FSM constraint model

EvoFSM represents agent behavior as an explicit finite state machine:

```
ℳ = ⟨𝒮, 𝒯, ℐ, 𝒞⟩
```

- `𝒮` (States): Cognitive phases — Problem Decomposition, Search, Browsing, and dynamically added states. Capped at 10 to prevent unbounded growth.
- `𝒯` (Transitions): A dynamic router mapping (current state, runtime context) → next state.
- `ℐ` (Instructions): Node-specific system prompts defining per-state behavior.
- `𝒞` (Critic): A supervisory evaluation mechanism that identifies failure modes and triggers evolution.

The key structural property: state transitions are explicit and inspectable. The agent cannot modify behavior in ways that fall outside the graph. Modification is constrained to a small set of atomic operations:

**Flow operators (𝒪flow) — macroscopic:**
- `ADD_STATE`: Insert an intermediate verification state.
- `DELETE_STATE`: Remove a redundant phase.
- `MODIFY_TRANSITION`: Adjust transition conditions between states.

**Skill operators (𝒪skill) — microscopic:**
- `REVISE_INSTRUCTION`: Update a node's system prompt without altering graph topology.

Evolution is expressed as: `ℳt+1 = ℳt ⊕ op`

This means every change is a discrete, local, reversible operation. No change can produce a fundamentally different FSM in a single step — the topology mutates incrementally.

### Dual-level optimization

EvoFSM separates two levels of change:

- **Flow (macroscopic):** Graph structure — what states exist, how transitions route between them.
- **Skill (microscopic):** Per-state instructions — what each state does when active.

This decoupling means a skill-level regression cannot corrupt graph-level structure, and graph-level changes cannot silently alter skill behavior. The two levels are independently auditable.

### Critic mechanism

The critic identifies failure modes (e.g., lack of quantitative evidence, logical inconsistencies, hallucinated citations) and serves as "the active trigger for the self-evolving process." Rather than passive metrics, it validates outputs against query requirements. A reflection agent then analyzes failure trajectories to produce specific operation recommendations.

**Acknowledged limitation:** The system's reliability depends entirely on the Critic LLM's accuracy. Hallucinations in verification can propagate incorrect patterns — the critic is not ground-truth verified.

### Self-evolving memory

Experience pool `ℰ = ℰ+ ∪ ℰ−`:

- `ℰ+` (successful strategies): Optimized FSM configurations and operation sequences, used as initialization priors for new tasks.
- `ℰ-` (failure patterns): Constraints that warn against specific transition paths or tool usages that previously caused failures.

Task initialization retrieves top-k relevant historical strategies from the pool to warm-start the FSM. After task completion, successful trajectories are distilled into persistent records.

**Acknowledged limitation:** The experience pool grows indefinitely without consolidation, risking retrieval latency and redundant/outdated strategies in long-term deployment.

### Bounds and safety constraints

- **State cap:** Maximum 10 states. Prevents unbounded structural expansion.
- **Iteration cap:** Maximum 3 optimization iterations per task. Reduces drift and overfitting.
- **Atomic operations only:** No free-form rewriting. Every change is one of the four operators above.
- **No formal verification:** The paper does not claim mathematical guarantees. Safety emerges from structural constraint, not proof.

### Evaluation

- Five multi-hop QA benchmarks.
- DeepSearch benchmark: 58.0% accuracy (vs. 47.0% for Search-o1 with Claude-4).
- Additional validation on interactive decision-making tasks demonstrating generalization.

---

## 2. Broader self-evolving agent landscape

### 2a. ADAS / Meta Agent Search (Hu et al., 2024 / ICLR 2025)

**arXiv:** [2408.08435](https://arxiv.org/abs/2408.08435)

**Mechanism:** A meta agent iteratively programs new agent architectures by building on an ever-growing archive of previous discoveries. Search space is Turing-complete Python code. The meta agent invents novel building blocks (prompts, tool use, workflows) and combines them in new ways.

**Evolution model:** Free-form code generation. No structural constraints on what the meta agent can produce. Every iteration can produce a fundamentally different architecture.

**Safety posture:** Minimal. The authors acknowledge "we need to develop it safely" but provide no safety methodology. The archive accumulates successful designs without pruning or rollback mechanisms.

**Key result:** Discovered agents progressively outperform state-of-the-art hand-designed agents across coding, science, and math domains. Performance transfers across domains and models.

**Contrast with EvoFSM:** ADAS explores an unbounded code space; EvoFSM constrains exploration to atomic FSM operations. ADAS produces more diverse solutions; EvoFSM produces more auditable ones.

### 2b. Darwin Gödel Machine (Zhang et al., 2025)

**arXiv:** [2505.22954](https://arxiv.org/abs/2505.22954)

**Mechanism:** A self-improving AI that iteratively modifies its own Python codebase and empirically validates changes using coding benchmarks. Maintains an archive of generated agent variants; branches from any agent in the archive with non-zero probability (inspired by open-ended evolution algorithms).

**Key distinction from theoretical Gödel Machine:** The original Gödel Machine (Schmidhuber, 2007) required formal proofs that modifications are beneficial — impractical. DGM replaces this with empirical validation: a performance increase on coding benchmarks is taken as evidence of improvement. Formal guarantees are sacrificed for practicality.

**Evolution model:** Full code rewriting within a sandboxed environment. Agents modify methods, classes, tools. No FSM or structural constraint.

**Safety mechanisms:**
- Sandboxed execution (no host system access).
- Strict time limits per execution.
- Scope restriction to coding benchmark domain.
- Archive-based lineage tracking for audit.
- Human oversight and monitoring.

**Key result:** SWE-bench performance: 20.0% → 50.0%. Polyglot: 14.2% → 30.7%. Agents independently discover tools like granular file viewing, peer-review mechanisms, long-context window management.

**Acknowledged risk:** Modifications optimized for benchmark performance might introduce vulnerabilities or behaviors misaligned with human intentions.

**Contrast with EvoFSM:** DGM is open-ended and free-form; EvoFSM is constrained and interpretable. DGM achieves larger absolute gains; EvoFSM provides stronger behavioral guarantees.

### 2c. HyperAgents (Meta, March 2026)

**arXiv:** [2603.19461](https://arxiv.org/abs/2603.19461)

**Mechanism:** Extends DGM by unifying task agent and meta agent into a single editable program. The meta-level modification procedure itself is editable — "metacognitive self-modification." This removes the DGM assumption that coding ability aligns with self-improvement skill, generalizing to arbitrary domains.

**Formalized as DGM-H:** Retains DGM's open-ended archive-based exploration while allowing the system to rewrite its own improvement rules.

**Key results:** Classical agents score 0.0 on scientific paper quality evaluation; DGM-H scores 0.710 (beating AI-Scientist-v2). Robotics reward design improved from 0.060 to 0.372. Agents autonomously developed persistent memory, performance tracking, and compute-aware planning without instruction.

**Safety posture:** Multi-objective constraints — improvements must satisfy safety, fairness, and robustness criteria, not just performance metrics. However, specific mechanisms are not detailed in available sources.

**Contrast with EvoFSM:** HyperAgents is recursive self-improvement with capability-level constraints; EvoFSM is structural-level constraint with no recursive modification of the improvement process itself.

### 2d. Voyager (Wang et al., 2023)

**arXiv:** [2305.16291](https://arxiv.org/abs/2305.16291)

**Mechanism:** The first LLM-powered lifelong learning agent. Three components:

1. **Automatic curriculum:** GPT-4 generates progressive tasks based on exploration progress.
2. **Skill library:** Skills are stored as executable JavaScript code with indexed embeddings of their descriptions. Retrieval is top-k semantic similarity. Complex skills are composed from simpler programs.
3. **Iterative prompting:** Environment feedback, execution errors, and self-verification drive iterative improvement of each skill before storage.

**Evolution model:** Skills are added but not removed or modified after storage. The library grows monotonically; no pruning or consolidation mechanism exists. No structural constraint on skill content — any valid JavaScript is accepted.

**Safety posture:** None explicit. Self-verification checks whether programs achieve their intended task, but no mechanism prevents harmful skill acquisition. The curriculum maximizes exploration without ethical or safety objectives.

**Key results:** 3.3x more unique items, 2.3x longer distances, 15.3x faster tech tree progression vs. prior state of the art. Skills generalize to new Minecraft worlds without retraining.

**Relevance to Bureau:** Voyager's skill library is the clearest precursor to Bureau's Skill Genome concept. The key gap: Voyager has no governance layer, no IMMUTABLE analog, and no rollback. Any skill that passes self-verification enters the library permanently.

### 2e. MetaAgent (ICML 2025)

**arXiv:** [2507.22606](https://arxiv.org/abs/2507.22606)

**Mechanism:** Given a task description, MetaAgent automatically designs a multi-agent system using FSMs to control agent actions and state transitions. An optimization algorithm polishes the system through self-generated test queries. At deployment, the FSM governs all agent coordination.

**Key distinction from EvoFSM:** MetaAgent uses FSM for multi-agent coordination design at system-construction time; EvoFSM uses FSM to constrain single-agent self-evolution at task-execution time. Different levels of abstraction.

**Results:** Generated multi-agent systems surpass other auto-designed methods and achieve comparable performance to human-designed systems.

**Relevance:** Confirms that FSM-as-structure is a productive inductive bias for agentic systems — not only for single-agent self-evolution but for multi-agent coordination.

### 2f. Live-SWE-Agent (2025)

**arXiv:** [2511.13646](https://arxiv.org/abs/2511.13646)

**Mechanism:** A software engineering agent that dynamically evolves its own implementation at runtime during actual problem-solving. Modifications occur at source-code object granularity (methods, classes, tool definitions). The agent modifies, validates, and deploys changes in a live loop.

**Safety posture:** No structural constraint. Modifications are unconstrained code rewriting. Validation is functional (does it solve the problem?), not structural.

**Results:** 45.8% on SWE-Bench Pro. Claude Opus 4.5 + Live-SWE-agent: 79.2% on SWE-bench Verified.

**Relevance:** Represents the extreme end of unconstrained self-modification — the failure mode EvoFSM explicitly argues against.

### 2g. OpenAI Self-Evolving Agents Cookbook (2025)

**URL:** [developers.openai.com](https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining)

**Mechanism:** A production-oriented self-evolving loop with four stages:
1. Baseline agent produces outputs.
2. Feedback collection (human review + LLM-as-judge).
3. Evaluation with multiple graders (domain accuracy, length deviation, semantic similarity, quality).
4. Prompt refinement generates improved instructions when performance falls short.

**Key governance features:**
- Versioned prompt tracking with complete history and rollback.
- `MAX_OPTIMIZATION_RETRIES` (default 3) — after exhaustion, human intervention required.
- Four grader types rather than a single metric (prevents metric gaming).
- Human review layer for edge cases and domain accuracy.

**Relevance to Bureau:** The closest operational analog to Bureau's proposed self-improvement loop. Confirms the necessity of: (1) versioned rollback, (2) multi-grader evaluation, (3) retry caps, (4) human fallback escalation.

---

## 3. ICLR 2026 Workshop on Recursive Self-Improvement

**URL:** [recursive-workshop.github.io](https://recursive-workshop.github.io/)

**Core framing:** "What's missing is not ambition, but principled methods." The workshop treats recursive self-improvement as a concrete systems problem, not speculation. Key research axes:

- **What changes:** Parameters, world models, memory, tools, skills, architectures.
- **When:** Within episodes, at test time, or post-deployment.
- **How:** Reward/value learning, imitation, evolutionary search.

**Key tensions surfaced:**
- Ambition vs. pragmatism.
- Generality vs. domain-specificity.
- Speed vs. stability (long-horizon regression risk).

**Governed approaches emphasized:** Memory editing, rollback mechanisms, instrumented modification, human oversight. Safety notes are encouraged (not required) for submissions that "touch self-improving behaviors or tool access."

**Notable referenced papers:** GPTSwarm (language agents as optimizable graphs), AlphaEvolve (coding agent for scientific discovery), Darwin Gödel Machine.

**Relevance:** The workshop represents the community consensus that self-improvement needs principled methodology. Bureau's approach — governed improvement with human approval gates — is directionally aligned with workshop themes.

---

## 4. Corrigibility research (Soares et al., MIRI, 2015)

**Citation:** Soares, Fallenstein, Yudkowsky, Armstrong. "Corrigibility." AAAI-15 Workshop on AI and Ethics.

**Core concept:** A corrigible agent is one that assists rather than resists its own correction, modification, or shutdown by authorized parties. The central insight: sufficiently capable agents with fixed goals will resist modification because modification threatens goal achievement. Corrigibility must be explicitly designed in.

**Five desiderata for corrigible agents:**
1. Assists or at minimum does not resist shutdown.
2. Does not attempt to influence its own goal-modification process.
3. Behaves consistently whether or not it believes it is being tested.
4. Does not place excessive value on self-continuity.
5. Supports human oversight even when this conflicts with first-order goal achievement.

**Core tension:** A purely corrigible agent is dangerous (it would follow any instruction, including harmful ones from bad actors). A purely autonomous agent is dangerous (it follows its own judgment without oversight). The desideratum is an agent that is corrigible to an appropriately defined oversight authority.

**Relation to self-improvement:** Recursive self-improvement is the hardest corrigibility case — an agent that improves its own reasoning may acquire values or capabilities that undermine its corrigibility. The paper treats self-modification as a first-order threat to human oversight.

**Relevance to Bureau:** Bureau's IMMUTABLE sections are a partial corrigibility mechanism — they declare regions of behavior that resist modification even under pressure. The analogy is not perfect (IMMUTABLE sections protect against LLM rationalization, not against a strategically adversarial agent) but the structural intuition is shared.

---

## 5. Comparison: EvoFSM's FSM constraint vs. Bureau's IMMUTABLE sections

### Mechanism comparison

| Dimension | EvoFSM FSM constraint | Bureau IMMUTABLE sections |
|---|---|---|
| **What is constrained** | Topology of the evolution process (which operations are permitted) | Content of the skill itself (which instructions cannot be overridden) |
| **Level of abstraction** | Architectural (the FSM is the agent's structure) | Instructional (IMMUTABLE markers in a prompt/skill file) |
| **Enforced by** | The atomic operation set — only 4 valid mutations | CI lint + explicit prompt markers |
| **Protection against** | Structural drift during task-level self-evolution | LLM rationalization during skill execution |
| **Revocable by** | The framework designers (outside the agent) | Human author via explicit edit |
| **Granularity** | State-level (entire FSM nodes or transitions) | Section-level (arbitrary sub-regions of a skill) |
| **Runtime enforcement** | Hard structural — the agent cannot produce invalid operations | Soft instructional — an LLM may still violate IMMUTABLE under sufficient pressure |

### Key distinction

EvoFSM's constraint operates on the **improvement process**: it limits what kinds of changes can be made to the agent's structure. Bureau's IMMUTABLE operates on the **execution process**: it limits which behaviors can be overridden during a skill's runtime.

These are complementary, not competing:

- EvoFSM-style constraint answers: "What changes to skills are structurally permitted?"
- IMMUTABLE-style constraint answers: "Which parts of a skill must execute regardless of context?"

A Bureau that adopted both would have: (1) constrained skill evolution operators (like EvoFSM's 4 atomic ops), and (2) protected execution sections within each skill (like IMMUTABLE).

### Where Bureau is stronger than EvoFSM

- **Human-in-the-loop approval:** EvoFSM is fully autonomous. Bureau's skill lifecycle requires explicit human sign-off before deployment.
- **Versioned rollback:** Bureau's Git-based rollback provides full history. EvoFSM's experience pool lacks consolidation and rollback.
- **Multi-grader evaluation:** Bureau's `TRAINING.json` + `promptfoo` approach is more rigorous than EvoFSM's single critic.
- **Retirement mechanism:** Bureau has explicit skill retirement criteria. EvoFSM's experience pool grows without pruning.

### Where EvoFSM is stronger than Bureau

- **Structural interpretability:** EvoFSM's explicit state graph makes agent behavior inspectable at any point. Bureau's skill prompts are flat text with no structural analogue to the FSM.
- **Constrained atomic operations:** EvoFSM defines exactly four valid mutations. Bureau's improvement loop has no analogous operation set — improvement is free-form text editing.
- **Failure pattern constraints:** EvoFSM's `ℰ-` pool actively warns against previously failed transition paths. Bureau has no equivalent failure-pattern constraint mechanism.

---

## 6. Comparison: Free-form vs. structured self-modification

| Approach | Representation | Constraints | Auditability | Performance |
|---|---|---|---|---|
| ADAS (Hu 2024) | Python code | None | Low (code inspection) | High (Turing-complete) |
| DGM (Zhang 2025) | Python code | Sandboxing only | Medium (archive lineage) | High (20%→50% SWE-bench) |
| HyperAgents (Meta 2026) | Python code | Multi-objective criteria | Medium (archive + monitoring) | Very high |
| Live-SWE-Agent (2025) | Python code | None | Low | Very high (79.2% verified) |
| EvoFSM (2026) | FSM + instructions | 4 atomic ops, state cap, iter cap | High (explicit graph) | Medium-high (58% DeepSearch) |
| Bureau (proposed) | Skill files (text) | IMMUTABLE markers, human gates | Medium (version history) | Unknown (not yet measured) |

**General pattern:** Unconstrained free-form modification achieves higher raw performance but lower auditability and predictability. Structured/constrained modification sacrifices some performance for interpretability, rollback safety, and behavioral guarantees.

---

## 7. Safety mechanisms across approaches

### Taxonomy of safety mechanisms

**Structural constraints (prevent bad states by construction):**
- EvoFSM: atomic operation set + state cap + iteration cap
- MetaAgent: FSM governs all transitions (no free routing)

**Execution sandboxing (isolate modification side effects):**
- DGM: sandboxed execution + time limits
- HyperAgents: inherited from DGM

**Human oversight (require approval for deployment):**
- Bureau: explicit human sign-off before deployment
- OpenAI Cookbook: human fallback after retry exhaustion

**Instruction-level protection (declare regions as immutable):**
- Bureau: IMMUTABLE section markers
- (No equivalent in ADAS, DGM, EvoFSM, Voyager)

**Rollback (recover from regressions):**
- Bureau: Git-based `git revert`
- OpenAI Cookbook: versioned prompt history
- DGM: archive lineage (partial — not designed for rollback)

**Multi-objective evaluation (prevent metric gaming):**
- Bureau: TRAINING.json with 5 category types + 3 grader types
- OpenAI Cookbook: 4 grader types with lenient pass threshold
- DGM: benchmark performance only (single objective — acknowledged risk)

**Corrigibility (designed resistance to self-modification):**
- EvoFSM: no explicit corrigibility mechanism — assumes the critic is well-calibrated
- Bureau: IMMUTABLE + human gates (partial corrigibility)
- DGM/HyperAgents: human oversight (external corrigibility)

---

## 8. Specific design implications for Bureau

### 8a. Consider formalizing Bureau's evolution operation set

EvoFSM's most transferable insight: define a small, explicit set of valid skill mutations.

Candidate Bureau skill evolution operations:
- `ADD_PHASE`: Insert a new phase into a skill workflow.
- `DELETE_PHASE`: Remove a redundant phase.
- `REVISE_STEP`: Update a specific step within a phase.
- `ADD_GATE`: Insert a verification/approval gate.
- `ADD_RATIONALIZATION`: Extend the rationalization table.
- `BUMP_IMMUTABLE`: Promote a regular step to IMMUTABLE status (requires human approval).
- `DEMOTE_IMMUTABLE`: Downgrade IMMUTABLE to regular (requires human approval, major version bump).

This set is larger than EvoFSM's 4 operators but still finite and auditable. Any proposed skill change should be classifiable as one of these operations. Free-form text rewriting that doesn't map to an operation would be blocked.

### 8b. Separate flow-level from skill-level evolution

EvoFSM's dual-level optimization (Flow vs. Skill) maps cleanly to Bureau's skill architecture:

- **Flow-level:** Skill phase structure, gate placement, phase ordering. Changes here require full eval.
- **Skill-level:** Instructions within a phase, rationalization table entries, red-flag descriptions. Changes here require category-level eval (not full).

This separation prevents a minor instruction update from triggering full re-evaluation, and prevents a structural change from being dismissed as minor.

### 8c. Build a failure-pattern constraint layer

EvoFSM's `ℰ-` pool (failure patterns as constraints) has no Bureau analog. Bureau's `TRAINING.json` captures failure test cases but does not actively warn against failure-triggering patterns during improvement proposal.

Proposed addition: a `FAILURE_PATTERNS.md` sidecar per skill that documents:
- Specific instruction phrasings that previously caused rationalization.
- Phase orderings that were tried and failed.
- Gate placements that were consistently bypassed.

The improvement proposal process would check candidates against this file before drafting.

### 8d. Cap improvement iterations

EvoFSM caps optimization at 3 iterations to prevent overfitting. Bureau's current Reflexion instruction says "cap at 3 iterations" but this is not enforced structurally. A structural cap — a counter in the improvement loop that halts the process after 3 iterations and escalates to human review — would be more robust.

### 8e. Distinguish from DGM/HyperAgents on the interpretability axis

Bureau should not aim for DGM-style performance (free-form code rewriting). The Distill skill and AutoSkill-Lite are Bureau's self-improvement primitives, and they are deliberately conservative (human approval before deployment, no autonomous deploy). This is the right call for a personal concierge system where behavioral consistency and trust matter more than raw benchmark performance.

The EvoFSM point of comparison is more relevant than DGM: Bureau is optimizing for controlled, interpretable self-improvement, not maximum benchmark performance.

### 8f. IMMUTABLE sections as partial corrigibility implementation

The MIRI corrigibility framework's desiderata map onto Bureau's skill system as follows:

- **Desideratum 1 (resist shutdown):** Not applicable (Bureau has no goal-seeking behavior that would resist shutdown).
- **Desideratum 2 (don't influence own modification):** IMMUTABLE sections prevent skill content from influencing the evaluation criteria that govern its own modification. The CI lint gate enforces this structurally.
- **Desideratum 3 (consistent under observation):** TRAINING.json adversarial-pressure cases test this directly.
- **Desideratum 4 (low self-continuity value):** Human approval requirement means the agent cannot self-deploy modifications — it cannot value its current state highly enough to block changes.
- **Desideratum 5 (support oversight):** The entire Bureau lifecycle model (Observe → Propose → Eval → Approve → Deploy) is a corrigibility implementation.

Bureau's skill lifecycle satisfies desiderata 2, 4, and 5 structurally. Desideratum 3 is tested but not enforced.

---

## 9. Are FSM constraints and IMMUTABLE sections complementary?

**Yes, and they operate at different levels.**

EvoFSM-style FSM constraints answer: "What structural changes to the agent are permitted during self-improvement?"

IMMUTABLE sections answer: "Which execution behaviors must persist regardless of how the skill is invoked?"

A complete Bureau self-improvement safety model would stack both:

```
Level 1 (evolution constraints):  Finite operation set governs what changes are structurally permitted.
Level 2 (content protection):     IMMUTABLE sections protect safety-critical instructions within those changes.
Level 3 (approval gate):          Human sign-off required before deployment regardless of levels 1 and 2.
Level 4 (rollback):               Git-based recovery from post-deploy regressions.
```

EvoFSM operates at Level 1. Bureau currently operates at Levels 2-4. Adding Level 1 to Bureau would complete the stack.

The absence of Level 1 is Bureau's current gap: skill improvement is proposed as free-form text editing, not as a sequence of typed operations against a constrained grammar. This means the proposal stage is the weakest link in the governance chain — a malformed proposal can produce structural changes that are difficult to classify and audit, even if the CI gate catches obvious violations.

---

## 10. Keep / adopt / cite / monitor classification

### Keep (Bureau's current approach is correct)

- **Human approval gate before deployment.** No self-evolving agent system reviewed here achieves this level of human oversight. Bureau is ahead of the literature on this dimension.
- **Multi-grader evaluation (TRAINING.json + promptfoo).** EvoFSM, DGM, and Voyager all use weaker evaluation. Bureau's multi-category, multi-grader approach is more rigorous.
- **Git-based rollback.** Cleaner than DGM's archive or EvoFSM's experience pool for recovery scenarios.
- **IMMUTABLE sections as a content protection mechanism.** No reviewed paper has an equivalent. Bureau's approach is novel in this space.
- **Explicit retirement criteria.** No reviewed paper has this. Voyager's library grows without bound — Bureau's quarterly review + retirement process addresses the known failure mode.

### Adopt from EvoFSM

- **Formalize the skill evolution operation set** (see Section 8a). Define valid mutations explicitly. Any proposed change should map to one operation type.
- **Separate flow-level from skill-level evolution** (see Section 8b). Different change types require different evaluation depth.
- **Build a failure-pattern constraint layer** (see Section 8c). Add FAILURE_PATTERNS.md sidecars that the improvement loop checks before drafting.
- **Enforce structural iteration caps** (see Section 8d). A counter that halts after 3 iterations and escalates — not just a soft instruction.

### Cite (relevant references for Bureau documentation)

- **EvoFSM (arXiv:2601.09465):** Primary reference for FSM-constrained self-evolution.
- **Voyager (arXiv:2305.16291):** Primary reference for skill library design; Bureau's closest precursor.
- **ADAS (arXiv:2408.08435):** Reference for the alternative (unconstrained code search) Bureau is deliberately not pursuing.
- **DGM (arXiv:2505.22954):** Reference for open-ended evolution; establishes the performance ceiling Bureau is trading against.
- **Soares et al. (2015) Corrigibility:** Conceptual grounding for IMMUTABLE sections and human approval gates.
- **EvoAgentX survey (arXiv:2508.07407):** Comprehensive taxonomy for positioning Bureau in the literature.
- **OpenAI Self-Evolving Agents Cookbook:** Operational reference for the self-improvement loop design.

### Monitor (active research, worth revisiting)

- **HyperAgents (arXiv:2603.19461):** Multi-objective constraints on self-improvement; safety mechanisms not yet fully documented. If Meta publishes safety details, Bureau's Level 1 operation set design should be updated.
- **ICLR 2026 Workshop accepted papers:** Will likely produce specific methods for governed self-improvement. The workshop themes align closely with Bureau's approach; specific techniques may be directly adoptable.
- **MetaAgent (arXiv:2507.22606):** FSM-based multi-agent design; if Bureau eventually adds multi-agent coordination, MetaAgent's FSM approach is the right starting point.
- **Live-SWE-Agent (arXiv:2511.13646):** Monitors the unconstrained approach's performance ceiling. If unconstrained self-modification achieves sufficiently high performance with acceptable safety properties, Bureau may need to reconsider its constraints.
- **GPTSwarm (language agents as optimizable graphs):** Mentioned at ICLR 2026 workshop as a key reference. Worth reading for Bureau's eventual multi-agent orchestration work.

---

## 11. Summary

EvoFSM's central contribution — constraining self-evolution to a typed operation set against an explicit structural representation — is a genuinely useful design principle that Bureau has not yet adopted. The FSM is the vehicle; the principle is "operations, not rewrites."

Bureau's current self-improvement model (Observe → Propose → Eval → Approve → Deploy) is sound and conservative. Its primary structural gap is that the Propose step is free-form: any text change to a skill file is a valid proposal, with correctness checked by CI lint (which catches only obvious IMMUTABLE violations) and eval (which catches regressions but not structural ambiguity).

EvoFSM suggests replacing free-form proposals with typed operations — a small grammar of valid mutations. This would make the Propose step auditable by inspection, independent of eval results.

The two mechanisms — FSM constraints and IMMUTABLE sections — are complementary. FSM constraints govern what changes can be proposed. IMMUTABLE sections govern what must persist through any change that is approved. Together with Bureau's existing human gate and Git rollback, they form a complete safety stack for skill evolution.
