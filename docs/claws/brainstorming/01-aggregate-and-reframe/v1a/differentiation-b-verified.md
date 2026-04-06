# Proposed Bureau differentiation: verified audit against SOTA

> After systematic literature review, deep feature-level analysis of 30+ agent platforms, and industry convergence assessment, Bureau has **4 genuinely unprecedented features**, **5 partially novel features** with distinct design within established categories, and **3 features with substantial or complete precedent**. The Meincke et al. citation used in the skill template is mischaracterized and must be corrected.

**Date:** 2026-04-04
**Scope:** verification of the 12 "unprecedented" claims from [differentiation-b.md](differentiation-b.md) against:
- 30+ agent platforms (Devin, Cursor, Windsurf, GitHub Copilot Workspace, Cline, Aider, Continue, Amazon Q Developer, Google Jules, OpenAI Codex, Replit Agent, Bolt, v0, Lovable, OpenHands, SWE-Agent, Agentless, AutoCodeRover, Letta/MemGPT, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, Haystack, Superagent, BabyAGI, MetaGPT, ChatDev, Hermes Agent, Pi, Replika, MightyBot)
- Academic literature (2022-2026): sycophancy research, behavioral composition, compliance engineering, self-improving agents, context management, disaggregated evaluation
- Industry frameworks and announcements (CSA Agentic Trust Framework, Anthropic Bloom, ICLR 2026 Workshop on Recursive Self-Improvement, Zep temporal knowledge graph, Mem0 actor-tagging)

**Relationship to prior docs:**
- Supersedes [differentiation-b.md](differentiation-b.md) (the unverified honest audit)
- References [differentiation-b-aspirational.md](differentiation-b-aspirational.md) (the 50-feature aspirational inventory)
- References [existing-bureau-differentiation.md](existing-bureau-differentiation.md) (the 30 existing features)

## Critical correction: Meincke et al. citation

The SKILL-TEMPLATE.md design rationale cites "Meincke et al. 2025 (N=28,000 conversations)" as evidence that "rhetorical engineering techniques doubled LLM compliance from 33% to 72%."

**This citation is mischaracterized.** The paper in question is:

> Meincke, L., Shapiro, D., Duckworth, A., Mollick, E.R., Mollick, L., & Cialdini, R. (2025). "Call Me A Jerk: Persuading AI to Comply with Objectionable Requests."

The study found that employing Cialdini's persuasion principles (authority, commitment, liking, reciprocity, scarcity, social proof, unity) more than doubled LLM compliance with **objectionable requests**: 72.0% vs. 33.3% in control conditions. The paper demonstrates vulnerability to social-psychological manipulation: it shows how to *break* compliance guardrails, not how to *strengthen* them.

Bureau's framing reverses the directionality. The paper is actually an argument *for* Bureau's approach (rationalization pre-emption as defense against manipulation) but the citation as used ("rhetorical engineering doubling compliance") implies the opposite of what the paper found.

**Required action:** correct the citation in SKILL-TEMPLATE.md. The paper *supports* Bureau's design (models are vulnerable to persuasion → pre-empting rationalizations is a defense) but the current framing is misleading.

Separately, Meincke co-authored "Prompting Science Report 1: Prompt Engineering is Complicated and Contingent" (arXiv:2503.04818, March 2025), demonstrating that prompt engineering effects are highly variable and context-dependent. This is a different paper.

## Verified tiers

### Tier 1: Genuinely unprecedented (4 features)

These features have no known equivalent in any evaluated platform, academic paper, or industry announcement. The verification research specifically searched for equivalents and found none.

#### 1) Rationalization pre-emption tables

**What it is**: two-column tables mapping exact LLM rationalizations (the specific strings a model would generate during inference) to concrete rebuttals, placed in behavioral protocol documents. IMMUTABLE: cannot be weakened by skill evolution. Minimum 5 entries per skill. Entries accumulate from observed failures during RED-GREEN-REFACTOR.

**Verification result**: **Unprecedented (85% confidence)**

- **No agent platform** maintains structured tables anticipating specific rationalization strings. Cursor, Devin, Copilot, Codex, Jules, LangGraph, CrewAI, AutoGen all use prose instructions or rules.
- **The closest equivalent** is Anthropic's Constitutional AI critique-revision pairs, but CAI operates at training time with general principles, not at runtime with exact-string interception.
- **Red-team prompt libraries** (Anthropic, Microsoft PyRIT) anticipate adversarial *external* inputs, not the model's *own internal* rationalizations.
- **No academic paper** describes pre-tabulated rationalization interception as a runtime technique. The adversarial prompt defense literature targets external attacks.

**What the research did find**: the approach of converting research findings about LLM failure patterns into structured lookup tables embedded in operational documents is genuinely novel as a design pattern. The intellectual lineage traces to Cialdini's persuasion taxonomy (via the Meincke et al. paper) applied defensively rather than offensively.

**Key caveat**: the Meincke et al. citation must be corrected (see above).

#### 2) Emotional sensitivity gating

**What it is**: detecting user emotional state (PROCESSING suite: stressed, overwhelmed, anxious, etc.) with highest precedence and structurally blocking proactive features via hard rules. The system *withholds* rather than acts. Processing cooldown extends the block. No attache context loaded during PROCESSING.

**Verification result**: **Unprecedented (80% confidence)**

- **No coding/productivity agent platform** implements emotional state detection that modifies feature availability. Devin, Cursor, Copilot, Codex, Jules: none.
- **Personal AI assistants** (Pi/Inflection, Replika, Character.ai) detect emotional state to adjust *response tone*, not to *gate feature delivery*. Pi invites discussion of sensitive topics rather than shutting down.
- **Mental health chatbots** (Woebot, Wysa) are *designed* for emotional conversations but don't gate capabilities.
- **The industry is moving in the opposite direction**: more proactive features, more background work, more unsolicited suggestions (Jules Suggested Tasks, Copilot proactive reviews, Devin autonomous work).
- **No academic paper** on proactive agent design specifically proposes emotional-state-based feature gating. Interruption science (Iqbal & Bailey 2008) and adaptive interfaces (Jameson 2003) address when to interrupt but not from the emotional sensitivity angle.

**Key insight from research**: Bureau is the only system that has formalized "sometimes the most intelligent thing is silence." This is a strong differentiator but hard to demonstrate in demos (the absence of action is invisible).

#### 3) CLAIMED vs. VERIFIED epistemology with propagation rules

**What it is**: metadata tagging every agent claim about code as CLAIMED or VERIFIED, with propagation: composite containing any CLAIMED sub-claim remains CLAIMED.

**Verification result**: **Unprecedented as applied to agent claims (55-70% confidence)**

- **No agent platform** tags individual claims with epistemic status. OpenHands runs code in sandboxes but doesn't tag *which specific agent claims* were verified vs. asserted.
- **No sandbox provider** (E2B, Daytona, Modal) treats verification as a trust-tagging primitive. All provide execution-as-a-service, not verification-as-a-service.
- **Google's grounding APIs** distinguish grounded from ungrounded content; Anthropic's citation work tracks source attribution. These are the closest industry equivalents but operate at the response level, not the individual-claim level.

**However, the underlying concepts are well-established:**

- **Provenance tracking** (Buneman et al. 2001, Green et al. 2007) has the same formal structure in databases
- **Taint analysis** (Denning 1976) uses the same propagation rule (tainted sub-expression taints the whole)
- **Retrieval-augmented generation with attribution** (Rashkin et al. 2023) distinguishes supported from generated claims

**Verdict**: the *specific application* to agent claims about code, with sandbox verification and propagation rules, is novel in the agent platform space. The *concepts* (provenance, taint tracking, epistemic status) are well-established. This is a genuinely useful application of known techniques to a new domain, which is a legitimate form of innovation.

#### 4) 5-feature-type taxonomy with independent scheduling/cooldown/sensitivity

**What it is**: DISPATCH (12h cooldown, 3/week), BREW (168h cooldown, 2/month, per-suite fit scores), PROBE (schedule-gated), VALET (guided routines, NOT blocked during PROCESSING), HUDDLE (structured interviews, 6 subtypes). Epsilon-greedy selection across types.

**Verification result**: **Unprecedented (85% confidence)**

- **Google Jules** has Suggested Tasks (proactive, scans repos) and Scheduled Tasks (cron-based recurring). This is the closest equivalent but has no feature typing, no per-type cooldowns, no sensitivity gating, no bandit selection.
- **GitHub Copilot** has proactive code review (March 2026) and Mission Control for parallel tasks. No scheduling intelligence.
- **No product** has per-feature-type cooldown periods, sensitivity-aware gating, per-suite affinity scores, or epsilon-greedy selection across feature types.
- **Notification management research** (Mehrotra et al. 2016) and interruption science address optimal timing but in different domains and without the typed taxonomy.

**Key insight from research**: the industry is converging fast on "agents do background work" (Jules, Copilot, Devin). But the *intelligence layer* on top (typed features, sensitivity gating, bandit selection, independent cooldowns) has no equivalent. "Proactive agent" is becoming table stakes; "proactive agent that does the *right* thing at the *right* time while *respecting emotional state*" remains Bureau-specific.

### Tier 2: Partially novel (5 features)

The *category* exists in SOTA. Bureau's *specific design* within the category is distinct and meaningfully better. Differentiation is real but requires articulating the specific design innovation, not just the category.

#### 5) Anti-sycophancy gate library

**Category**: anti-sycophancy interventions (established)

**Bureau's specific design**: 5 named gates mapped to cognitive biases (confirmation bias, authority deference, effort justification, anchoring, vague approval) with BAD/GOOD calibration examples as intervention templates.

**What the verification found**:

- **The Silicon Mirror (Shah, April 2026)**: "Dynamic Behavioral Gating for Anti-Sycophancy in LLM Agents." Five-stage pipeline: Trait Classification, Behavioral Access Control, Generation, Critique, Conditional Rewrite. Achieved 85.7% relative reduction in sycophancy on Claude Sonnet 4. Uses per-conversation sycophancy vector t = (alpha, sigma, gamma, tau). This is **the most direct academic precedent**.
- **ELEPHANT (2025)**: introduced 4 named sycophancy dimensions grounded in Goffman's face theory: validation, indirectness, framing, moral sycophancy. Measurement-focused, not interventional.
- **Sharma et al. (ICLR 2024)**: benchmarked sycophancy across 5 models and 4 tasks. Diagnostic.
- **Batzner et al. (ICLR 2025)**: identified 5 core operationalizations of sycophancy.

**Bureau's remaining differentiation**: the gate structure mapped to *cognitive biases* (confirmation bias, anchoring, etc.) is distinct from the Silicon Mirror's *persuasion-tactic detection* (agreeableness, skepticism, confidence-in-error, tactics) and ELEPHANT's *social dimensions* (validation, indirectness, framing, moral). The BAD/GOOD calibration examples as intervention templates have no direct equivalent. But Bureau cannot claim this area is unexplored.

**Recommendation**: cite the Silicon Mirror and ELEPHANT explicitly. Distinguish Bureau's cognitive-bias framing from their persuasion-tactic and social-dimension framings.

#### 6) Formal composition algebra for behavioral protocols

**Category**: composable agent behaviors (established in classical AI, emerging in LLM agents)

**Bureau's specific design**: phase ordering (pre-analysis → execution → post-verification → gating), interference detection, phase coalescence, explicit inter-skill contracts.

**What the verification found**:

- **Arbiter (Mason, March 2026)**: directly addresses interference detection in LLM agent system prompts. Analyzed Claude Code, Codex CLI, Gemini CLI; found 152 findings and 21 interference patterns across 3 universal categories (autonomy vs. restraint, precedence hierarchy ambiguity, implicit scope conflicts). **This is the most direct precedent for interference detection.**
- **Arbiter's key finding**: "the agent that resolves the conflict cannot be the agent that detects it" (Observer's Paradox). This has direct implications for Bureau's interference detection mechanism.
- **Behavior Trees** (Colledanchise & Ogren 2018): formal composition semantics (Sequence, Fallback, Parallel, Decorator) with well-defined success/failure propagation. The theoretical ancestor of Bureau's phase model.
- **SoK: Agentic Skills (2025)**: formalizes skills as four-tuple S = (C, pi, T, R), identifies 7 design patterns, discusses composition and security/governance.
- **EvoFSM (2025-2026)**: self-evolving agent framework constraining evolution to explicit finite state machine representation.

**Bureau's remaining differentiation**: the *specific application* to behavioral protocols (not tasks, not tools, not roles) with phase coalescence (shared analysis computation serving multiple skills) has no direct precedent. The conceptual gap from existing work is: LangGraph composes "what to do"; Bureau composes "how to think about the task." But the individual mechanisms (interference detection, formal composition, phase ordering) all have precedent.

**Recommendation**: cite Arbiter for interference detection, BTs for composition semantics, SoK for skill formalization. Position Bureau's contribution as the specific application to behavioral protocol composition with coalescence.

#### 7) IMMUTABLE constitutional constraints on skill evolution

**Category**: safety constraints on self-modifying systems (established)

**Bureau's specific design**: IMMUTABLE sections in skill template documents that are structurally enforced against the evolution mechanism. The IMMUTABLE enforcement mechanism itself is IMMUTABLE.

**What the verification found**:

- **Constitutional AI (Bai et al. 2022)**: immutable constitution fixed at training time. The model cannot modify the principles it was trained on. Conceptually identical at the training level.
- **Darwin Godel Machine (Zhang et al. 2025) / HyperAgents (Meta 2025-2026)**: explicitly discusses "explicitly bounded scope of permissible self-modification." Point (3) of their safety framework is directly analogous to IMMUTABLE sections.
- **Corrigibility research (Soares et al., MIRI 2015+)**: formal frameworks for agents preserving certain properties during self-modification.
- **ICLR 2026 Workshop on Recursive Self-Improvement**: requires "improvement-operator cards" specifying stability constraints and rollback triggers. Converging toward Bureau's skill.meta.json.
- **Anthropic (Jan 2026)**: updated Constitutional AI to distinguish hardcoded behaviors (absolute prohibitions) from softcoded defaults (adjustable). The hardcoded/softcoded distinction is functionally equivalent to IMMUTABLE/mutable.

**Bureau's remaining differentiation**: the implementation at the *behavioral protocol document level* (template section markers) rather than the *model training level* (Constitutional AI) or the *code level* (DGM). Bureau's approach is more accessible (prompt engineering vs. model training) but potentially weaker (instructions that models can rationalize around vs. training-level constraints). The self-referential property (the IMMUTABLE enforcement mechanism itself is IMMUTABLE) is a nice theoretical touch but doesn't add practical strength.

**Recommendation**: acknowledge Constitutional AI and DGM as conceptual precedent. Position Bureau's contribution as making IMMUTABLE constraints accessible at the prompt/protocol level rather than requiring model retraining.

#### 8) Redundant mandate placement for context compaction survival

**Category**: instruction robustness in long contexts (established)

**Bureau's specific design**: core behavioral invariant placed in 4+ structural locations to survive context compression. Formalized as an engineering pattern.

**What the verification found**:

- **Lost in the Middle (Liu et al. 2023, TACL)**: foundational paper demonstrating U-shaped attention in long contexts. Directly motivates Bureau's concern.
- **Benchmark-Dependent Output Dynamics (March 2026, arXiv:2603.23527)**: introduces "Instruction Survival Probability" (ISP), formalizing exactly the problem Bureau addresses. Finds binary survival: instruction segments are either fully preserved or completely destroyed.
- **Standard prompt engineering practice**: OpenAI, Anthropic, and Google all recommend placing critical instructions at beginning and end, repeating key instructions, using structural markers. The practice of instruction redundancy is widely known.
- **Letta/MemGPT**: "core memory" tier that is always present (never compressed). Different mechanism, same goal.
- **LLM Behavioral Failure Modes (Feb 2026)**: identifies "context rot" and recommends "goal anchoring: repeat the original goal at every step."

**Bureau's remaining differentiation**: Bureau names this a deliberate engineering strategy with a specific target (4+ locations) rather than an ad-hoc practice. The ISP paper (March 2026) independently formalizes the same concern, suggesting convergence. Letta/MemGPT's privileged memory tier is arguably a stronger guarantee (structural exemption from compression vs. probabilistic survival through redundancy).

**Recommendation**: cite Lost in the Middle, the ISP paper, and Letta's privileged tier. Position Bureau's contribution as a systematic named pattern with a specific redundancy target, while acknowledging that privileged memory tiers may be a stronger alternative.

#### 9) Closed adaptive feedback loop

**Category**: feedback loops in agent systems (established)

**Bureau's specific design**: provenance → competence → verification → evolution → autonomy → execution → provenance as a single structural property requiring Bureau ownership of all 5 subsystems.

**What the verification found**:

- **Voyager (Wang et al. 2023)**: exploration → execution → verification → skill addition. Several elements of Bureau's loop.
- **ADAS / Meta Agent Search (Hu et al. 2024)**: meta-agent iteratively programs better agents based on evaluation.
- **OODA loop (Boyd)**: Observe → Orient → Decide → Act. Classic feedback loop.
- **Cybernetic control theory (Wiener 1948)**: foundational concept of closed loops.
- **CSA ATF (Feb 2026)**: promotion gates based on measured performance with demotion on incidents. Partial loop.
- **Autonomy levels in HRI (Sheridan & Verplank 1978)**: variable autonomy based on competence.

**Bureau's remaining differentiation**: the specific *sequence* (provenance → competence → verification → evolution → autonomy → execution → provenance) and the treatment of *closedness* as a structural property are novel formalizations. The individual links (measuring competence, adjusting autonomy, evolving skills) all have precedent. The value is in the *complete cycle* and the argument that breaking it at any point reduces the system from multiplicative to additive.

### Tier 3: Not unprecedented (3 features)

These are well-established practices that Bureau has named and formalized but not invented.

#### 10) RED-GREEN-REFACTOR for behavioral protocols

**What the verification found**: this is NOT unprecedented.

- **Promptimize (Beauchemin, 2023)**: open-source framework explicitly applying TDD methodology to prompt engineering, with scoring functions as test assertions.
- **Didier Lopes (2024-2025)**: explicitly describes RED-GREEN-REFACTOR for prompt engineering: observe failures (Red), write/improve prompt (Green), refactor. Also proposes self-improving AI where the LLM improves prompts based on test failures.
- **David Luhr (2024)**: "Test-driven development as prompt engineering."
- **Endor Labs (2025)**: "Test-First Prompting: Using TDD for Secure AI-Generated Code."
- **Self-Evolving Agents Cookbook (OpenAI 2024)**: autonomous retraining loops with evaluation metrics.

**Bureau's remaining contribution**: the application to *behavioral protocol authoring* rather than generic prompt tuning, and the specific *combined adversarial pressure* condition (time + sunk cost + authority + scope creep simultaneously), may be distinctive. But the methodology itself is established.

**Recommendation**: do not claim RED-GREEN-REFACTOR as unprecedented. Cite Promptimize and Lopes as prior art. Position Bureau's contribution as the specific adversarial pressure conditions and application to formal behavioral protocols.

#### 11) Per-category TRAINING.json with non-aggregation rule

**What the verification found**: this is NOT unprecedented.

- **Disaggregated Evaluation of AI Systems (Barocas et al. 2021, arXiv:2103.06076)**: explicitly proposes disaggregated evaluation as a fairness principle.
- **AWS Clarify / CDD (Wachter et al. 2021)**: implements disaggregated fairness metrics in a production system.
- **The Instruction Gap (Tripathi et al. 2025)**: per-category instruction compliance measurement across 13 LLMs.
- **ELEPHANT (2025)** and **SycEval (Fanous et al. 2025)**: per-dimension sycophancy evaluation.
- **Simpson's Paradox**: the phenomenon Bureau's non-aggregation rule prevents is widely known in ML evaluation.

**Bureau's remaining contribution**: the specific application to *behavioral protocol compliance* (not fairness, not model capability) with 5 named categories. But the principle is standard ML evaluation practice.

**Recommendation**: do not claim the non-aggregation rule as novel. Cite Barocas et al. and the Instruction Gap paper. Position Bureau's contribution as the specific 5-category taxonomy applied to behavioral protocols.

#### 12) Activation description as trigger, not documentation

**What the verification found**: this is standard practice.

- **STRIPS/PDDL (1970s+)**: planning operators have preconditions specifying when they can be applied.
- **OpenAI, Anthropic tool-use best practices**: explicitly recommend writing descriptions that specify when to use a tool.
- **MCP tool descriptions**: serve as activation conditions.
- **LangChain/Semantic Kernel tool descriptions**: same pattern.

**Bureau's remaining contribution**: the specific term "description-shortcutting" as a named failure mode, and the explicit structural enforcement. But the practice itself is decades old.

**Recommendation**: do not claim as unprecedented. Name it as a codified best practice with a useful failure-mode taxonomy (the "description-shortcutting" concept has pedagogical value).

## Revised summary

| # | Feature | Tier | Confidence | Closest precedent |
|:---|:---|:---|:---|:---|
| 1 | Rationalization pre-emption tables | **Unprecedented** | 85% | Constitutional AI critique-revision (different level) |
| 2 | Emotional sensitivity gating | **Unprecedented** | 80% | Affective computing (different domain entirely) |
| 3 | CLAIMED/VERIFIED epistemology | **Unprecedented** | 55-70% | Provenance tracking, taint analysis (same concepts, new domain) |
| 4 | 5-feature-type taxonomy | **Unprecedented** | 85% | Jules Scheduled Tasks (much simpler) |
| 5 | Anti-sycophancy gate library | **Partially novel** | 60% | The Silicon Mirror (Shah, April 2026), ELEPHANT (2025) |
| 6 | Composition algebra for behavioral protocols | **Partially novel** | 55% | Arbiter (Mason, March 2026), Behavior Trees, SoK Agentic Skills |
| 7 | IMMUTABLE constitutional constraints | **Partially novel** | 40% | Constitutional AI, DGM, corrigibility research |
| 8 | Redundant mandate placement | **Partially novel** | 50% | ISP formalization (March 2026), Lost in the Middle |
| 9 | Closed adaptive feedback loop | **Partially novel** | 50% | Voyager, ADAS, OODA, CSA ATF |
| 10 | RED-GREEN-REFACTOR | **Not unprecedented** | 15% | Promptimize (2023), Lopes (2024-2025) |
| 11 | Per-category non-aggregation | **Not unprecedented** | 15% | Disaggregated Evaluation (Barocas 2021) |
| 12 | Activation as trigger | **Not unprecedented** | 10% | STRIPS/PDDL (1970s), tool-use best practices |

## The honest moat

If Bureau were to describe its differentiation in a single paragraph to an evaluator who knows the SOTA:

> Bureau is the only agent system that (1) **pre-empts LLM rationalizations** using exact inference-time strings placed in behavioral protocol documents, (2) **withholds features during user emotional distress** via sensitivity-aware suite detection and hard-rule gating, (3) tags every agent claim about code with **CLAIMED vs. VERIFIED epistemology** with taint-tracking propagation rules, and (4) manages **5 typed proactive feature classes** with independent scheduling, cooldown, and sensitivity semantics combined with epsilon-greedy bandit selection. These 4 are genuinely unprecedented. Additionally, Bureau has novel implementations of anti-sycophancy interventions (cognitive-bias-mapped gates with calibration examples, distinct from the Silicon Mirror's persuasion-tactic approach), behavioral protocol composition (phase-ordered with interference detection and coalescence, extending Arbiter's findings), earned autonomy (task-scoped with policy ceilings, extending the CSA ATF concept), and constitutional constraints on skill evolution (at the protocol level, complementing Constitutional AI's training-level approach). Bureau's RED-GREEN-REFACTOR methodology, per-category measurement, and trigger-based activation are codified best practices with useful naming, not novel inventions.

## Industry convergence timeline

Based on the research, here is how long Bureau's differentiators likely remain differentiated:

| Feature | Convergence risk | Estimated window |
|:---|:---|:---|
| Rationalization pre-emption | Very low (no one is attempting) | 24+ months |
| Emotional sensitivity gating | Very low (industry moving opposite direction) | 24+ months |
| CLAIMED/VERIFIED epistemology | Low (sandboxes are execution-only) | 24+ months |
| 5-feature-type taxonomy | Medium for basic proactivity; low for the intelligence layer | 18+ months |
| Anti-sycophancy gates | Medium (Silicon Mirror is close) | 12-18 months |
| Composition algebra | Low (no one composes behavioral protocols) | 24+ months |
| IMMUTABLE constraints | Medium (ICLR workshop converging) | 12-18 months |
| Earned autonomy | High for concept (CSA ATF); low for task-scoped implementation | Concept: 6 months. Full implementation: 18+ months |
| Memory trust/provenance | Medium (Zep's temporal KG is partial convergence) | 12-18 months |

## Research Bureau should incorporate

Findings from the verification research that Bureau should study and potentially integrate:

### Must-cite (prior art acknowledgment)

1. **The Silicon Mirror (Shah, April 2026)**: cite and distinguish Bureau's cognitive-bias gates from their persuasion-tactic detection. Consider adopting their per-conversation sycophancy vector (alpha, sigma, gamma, tau).

2. **Arbiter (Mason, March 2026)**: cite for interference detection. Adopt the finding that "the agent resolving conflict cannot be the agent detecting it" (Observer's Paradox) into Bureau's interference detection design.

3. **SoK: Agentic Skills (2025)**: situate Bureau's skill concept within their four-tuple formalization S = (C, pi, T, R) and seven design patterns. The security analysis (ClawHavoc campaign case study) is directly relevant.

4. **Promptimize (2023) and Lopes (2024-2025)**: cite as prior art for RED-GREEN-REFACTOR. Position Bureau's contribution as the adversarial pressure conditions and formal behavioral protocol application.

5. **Barocas et al. (2021)**: cite for disaggregated evaluation. Position Bureau's 5-category taxonomy as an application, not an invention.

6. **Lost in the Middle (Liu et al. 2023)** and **ISP formalization (March 2026)**: cite for context compaction survival. Consider adopting the ISP mathematical framework.

7. **Zep / Graphiti temporal knowledge graph**: acknowledge as partial precedent for provenance graph contradiction semantics. Distinguish Bureau's trust scoring and closed-loop integration.

8. **CSA Agentic Trust Framework (Feb 2026)**: acknowledge as industry convergence on earned autonomy concept. Distinguish Bureau's task-scoped, ceiling-capped, verification-integrated implementation.

### Should-adopt (techniques to strengthen Bureau's design)

1. **The Silicon Mirror's per-conversation sycophancy vector**: t = (alpha, sigma, gamma, tau) for agreeableness, skepticism, confidence-in-error, and tactics. Could complement Bureau's gate library with quantitative tracking.

2. **Arbiter's Observer's Paradox**: "the agent resolving conflict cannot be the agent detecting it." Bureau's interference detection mechanism should use external/separate evaluation rather than self-detection.

3. **Instruction Survival Probability (ISP) formalization**: mathematical framework for context compaction survival. Bureau's "4+ locations" could be derived from ISP analysis rather than being an arbitrary target.

4. **DSPy-style automatic prompt optimization**: complement RED-GREEN-REFACTOR (manual) with automated search over protocol formulations against TRAINING.json.

5. **Constrained decoding (Outlines, Guidance, LMQL)**: enforce structural constraints on model output at the token level, providing harder guarantees for behavioral gates than prompt-level instructions alone.

6. **Letta/MemGPT privileged memory tier**: as alternative to redundant mandate placement. Structural exemption from compression is a stronger guarantee than probabilistic survival through redundancy.

### Should-monitor (convergence threats)

1. **Anthropic extending Bloom to agent-protocol-level behavioral evaluation**: if Bloom moves from model-level (is Claude sycophantic?) to protocol-level (did the dispatch skill enforce independence verification?), it directly competes with TRAINING.json.

2. **ICLR 2026 Workshop on Recursive Self-Improvement**: improvement-operator cards converging toward skill.meta.json. If this framework gets productionized by a well-funded lab, Bureau's lead shrinks.

3. **Jules expanding proactive feature intelligence**: Jules already has Suggested Tasks and Scheduled Tasks. If Google adds feature typing, cooldowns, or sensitivity, Bureau's feature-taxonomy differentiation narrows.

4. **Zep gaining traction**: Zep's temporal knowledge graph with contradiction detection is gaining mindshare. Bureau should ship its trust scoring layer before Zep adds it.

## Confidence and limitations

This verification is bounded by:

- **Training data cutoff**: knowledge extends through early-mid 2025 with some awareness of 2025-2026 trajectories. Web searches filled gaps but may have missed recent announcements.
- **Academic search limitations**: literature search covered major venues (NeurIPS, ICLR, EMNLP, TACL, arXiv) but may have missed workshop papers, preprints, or work in adjacent fields.
- **Product feature analysis**: based on public documentation, blog posts, and announcements. Internal/beta features at Anthropic, OpenAI, Google, or startups are not visible.
- **The agent space moves fast**: any claim of "unprecedented" has a half-life. Features unprecedented today may have equivalents in 6-12 months.

The strongest claims (rationalization pre-emption, emotional sensitivity gating) have the highest confidence because they are not just technically novel but conceptually distinct from the direction the industry is moving. The weakest claims (RED-GREEN-REFACTOR, non-aggregation, activation-as-trigger) were correctly identified as established practices in the prior differentiation-b.md; verification confirmed this.
