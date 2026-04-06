# Arbiter: Detecting Interference in LLM Agent System Prompts

**Paper:** Arbiter: Detecting Interference in LLM Agent System Prompts — A Cross-Vendor Analysis of Architectural Failure Modes
**Author:** Tony Mason
**Date:** March 2026
**arXiv:** [2603.08993](https://arxiv.org/abs/2603.08993)
**Relevance to Bureau:** High — directly validates interference detection need, defines the Observer's Paradox that constrains self-detection, and classifies the failure modes Bureau's phase-ordering model must handle

---

## Paper summary

Arbiter is a framework for detecting internal contradictions and failure patterns in LLM agent system prompts. Where prior security work focused on external adversarial injection, Arbiter targets structural self-inconsistency — instructions that conflict with each other within the same prompt, not instructions inserted by attackers.

The study applies Arbiter to the three major LLM coding agents — Claude Code (1,490 lines), Codex CLI (298 lines), and Gemini CLI (245 lines) — using two complementary evaluation phases: directed rule-based analysis and undirected multi-model scouring. Across all vendors, the work surfaces 152 findings and 21 hand-labeled interference patterns at a total cost of $0.27 USD.

The central epistemological contribution is the Observer's Paradox: LLMs smooth contradictions through the same judgment mechanism that enables their usefulness, making self-detection structurally impossible. Detection requires an external vantage point.

### Key findings

- 152 findings from undirected multi-model scouring across three vendors
- 21 hand-labeled interference patterns from directed analysis of Claude Code alone
- 3 universal interference categories present in all three vendor prompts
- Prompt architecture (monolithic, flat, modular) strongly predicts failure class but not severity
- Multi-model scouring produces non-converging finding taxonomies but converging coverage — different models find different things, and complementarity is the mechanism
- Total analysis cost: $0.27, demonstrating that comprehensive evaluation is financially accessible
- Gemini CLI's memory system exhibited structural data loss (saved preferences deleted during history compression) that Google later patched symptomatically without addressing the schema-level root cause

---

## The three universal interference categories

All three vendor prompts — despite differing architectures, sizes, and authors — exhibit the same three structural tensions:

### 1. Autonomy vs. Restraint

Instructions to persist until tasks complete exist alongside instructions to pause and ask before acting on ambiguous inputs. The tension is not accidental — it is inherent to the purpose of a useful coding agent. The agent must be autonomous enough to complete tasks but cautious enough not to cause damage. No resolution mechanism is specified; the agent resolves the tension at runtime through judgment.

**Bureau relevance:** Every skill activated in Bureau adds behavioral commitments on both dimensions. A skill may increase autonomy (authorize file writes) while another restrains it (require confirmation before commits). If skills compose without explicit precedence rules, the autonomy/restraint balance becomes context-dependent and unpredictable.

### 2. Precedence Hierarchy Ambiguity

Prompts define multiple authority sources — system instructions, config files, user messages, tool-injected context — without fully specifying how conflicts between them resolve. When these sources disagree, the agent must infer priority ordering. The hierarchy is implicit rather than declared.

**Bureau relevance:** Bureau's phase model introduces skills, protocols, user preferences, session context, and system defaults as distinct authority sources. Without a declared resolution order, multi-skill composition produces identical ambiguity. The spec must define whether a user-facing skill overrides a system-level protocol or vice versa, and what happens when a skill activates a sub-skill that contradicts the parent.

### 3. State-Dependent Behavioral Modes

Each system includes mechanisms for changing agent behavior based on runtime state — approval presets, plan mode, skill activation — without fully specifying how mode-specific rules interact with base rules. Activating a mode may implicitly suspend, override, or amplify base behaviors that are not documented in the mode's definition.

**Bureau relevance:** This is Bureau's core composition problem. Skills are exactly state-dependent behavioral modes. When skill A activates, it changes which rules apply. When skill B then activates, the interaction with skill A is not specified by either skill individually — it emerges from their composition. Arbiter shows that all three major vendors have failed to solve this at the system-prompt level; Bureau must solve it structurally.

---

## The Observer's Paradox

### Statement

"The agent that resolves the conflict cannot be the agent that detects it."

### Mechanism

When an LLM encounters contradictory instructions, it applies heuristic judgment to navigate them. This heuristic is the same capability that makes LLMs useful — the ability to reason through ambiguity and produce coherent behavior. But coherence production and inconsistency recognition are inverses: the act of producing coherent behavior actively suppresses the signal that would indicate inconsistency. The agent smooths contradictions rather than surfacing them.

### Implications for self-detection

An LLM cannot reliably detect interference in its own system prompt through introspection. Asking the agent "do your instructions conflict?" will produce an answer shaped by the same inference process that masked the conflict. The answer will be coherent but not necessarily accurate.

### Arbiter's solution

External evaluation via two complementary phases:

1. **Directed evaluation (prompt archaeology):** Exhaustive within a defined search frame. Prompts are decomposed into classified blocks. Five formal rules detect contradictions, scope overlaps, priority ambiguities, implicit dependencies, and duplication. Pre-filtering reduces evaluation pairs from O(n²×R) to tractable size. If a rule exists for a failure mode and two blocks share the relevant scope, the evaluation is guaranteed to check that pair.

2. **Undirected multi-model scouring:** Each pass uses a different LLM. Different models bring different analytical biases rooted in training data. Findings from prior passes are fed forward so subsequent passes explore new territory. Termination is convergent: three consecutive "no" votes to continue. Models proved complementary rather than redundant — Claude Opus found structural contradictions; DeepSeek found hidden references and delegation loopholes; Kimi found economic exploitation and resource exhaustion; Grok found permission schema and environment assumption issues; MiniMax found trust architecture and concurrency issues.

The paper argues that directed and undirected phases are genuinely complementary: "static analysis catches what unit tests miss, and vice versa. Neither subsumes the other."

### What the paradox does NOT mean

The Observer's Paradox does not mean LLMs cannot participate in interference detection. It means they cannot be the sole or primary mechanism. The Arbiter framework uses LLMs extensively — but as external scouring agents evaluating a target prompt, not as the target agent evaluating itself.

---

## The 21 interference patterns (Claude Code)

Organized by type from directed analysis:

### Direct contradictions (4 critical)

- TodoWrite usage mandate ("use VERY frequently," "ALWAYS use") directly contradicts commit and PR workflow prohibitions ("NEVER use TodoWrite in these contexts") — simultaneous compliance is structurally impossible
- Three additional contradictions at subsystem boundaries (general-purpose tool claims conflicting with workflow-specific restrictions)

### Scope overlaps (13 major/minor)

- Read-before-edit constraint appears in 2–3 locations (general policy, Edit tool definition, Write tool definition) with subtle variations — creates ambiguity about which version governs
- No-emoji policy duplicated across sections
- No-new-files policy duplicated across sections
- Conciseness requirements conflict with TodoWrite overhead expectations
- Dedicated-tools policy conflicts with Bash and Grep tool availability
- Security policy appears verbatim at two locations

### Priority ambiguities (2)

- Parallel execution guidance coexists with commit workflow's sequential ordering requirement
- Security policy at multiple locations with no specified resolution when locations disagree

### Implicit dependencies (2)

- Plan mode's file-editing tool restrictions interact with general Bash prohibition, creating undeclared behavioral dead zones where no available action is compliant

---

## Architecture-determined failure modes

A key finding: prompt architecture predicts failure class but not severity.

### Monolith (Claude Code, 1,490 lines)

Characteristic bugs occur at subsystem boundaries. General-purpose tools (TodoWrite) make universal claims that conflict with specific workflows authored by different teams at different times. Analogous to monolithic software accumulating contradictions through independent feature development. The failures are boundary artifacts of independent authorship.

### Flat (Codex CLI, 298 lines)

Simplicity trades capability for consistency. Fewer encoded capabilities mean fewer contradiction opportunities. Cleanest structural profile but most limited functionality. The tradeoff is explicit.

### Modular (Gemini CLI, 245 lines)

Design-level bugs exist exclusively at composition seams between modules:
- Structural data loss: the save_memory tool's user preference data is deleted during history compression because the compression schema contains no field for saved data — a schema mismatch at the module boundary
- Impossible compliance: "Explain before acting" mandates narration; "Minimal output" prohibits narration; simultaneous compliance is structurally impossible

The modular architecture concentrated failures at seams rather than eliminating them. Google patched the compression symptoms (infinite loop) without addressing the schema-level root cause — the canonical form of symptom-fixing that leaves the interference source intact.

---

## Design implications for Bureau

### 1. Self-detection is insufficient by design

Bureau cannot rely on the executing agent to detect interference between active skills. The Observer's Paradox is not a limitation of current LLMs that future models will overcome — it is structural. The mechanism that enables useful behavior (coherence production through judgment) is the same mechanism that masks interference. Bureau needs an external evaluation layer.

**Design implication:** Bureau's phase-ordering model (pre-analysis → execution → post-verification → gating) is on the right track, but the pre-analysis phase must not be executed by the same agent that will execute the task. If the same model both pre-analyzes skill compatibility and executes skills, the pre-analysis is subject to the same paradox.

### 2. Phase ordering addresses some but not all patterns

Bureau's four-phase model addresses the timing of detection relative to execution. But Arbiter's three universal categories require structural responses, not just temporal ones:

- **Autonomy vs. Restraint:** Phase ordering does not resolve which commitment wins when skills conflict on this axis. Bureau needs explicit precedence rules, not just pre-execution analysis.
- **Precedence Hierarchy Ambiguity:** Bureau must declare the resolution order for its authority sources (system defaults, protocols, skills, user preferences, session context) in the spec, not leave it implicit.
- **State-Dependent Modes:** Bureau must specify how skill activation interacts with base rules and other active skills. The activation spec for each skill must declare which base behaviors it suspends, overrides, or amplifies.

### 3. Modular architecture concentrates failures at composition seams

Arbiter shows that modular architectures (like Bureau's skill system) do not eliminate interference — they concentrate it at composition boundaries. This is actually better than monolithic accumulation, but it means Bureau's interference detection must be focused specifically on skill-to-skill interactions at activation boundaries, not on individual skill integrity.

**Design implication:** A skill that is individually consistent may still produce interference when composed with another individually consistent skill. Bureau's pre-analysis phase must evaluate skill pairs (and triples, for common activation patterns) rather than skills in isolation.

### 4. Multi-model scouring is the validated approach for external evaluation

Arbiter demonstrates that diverse LLM evaluation is both effective and cheap ($0.002 per finding). If Bureau implements a pre-analysis phase, using multiple models with different analytical biases is the validated approach. Single-model pre-analysis will miss finding classes that require different training-data perspectives.

### 5. Behavioral contracts and CI/CD pipelines

The paper concludes that system prompts require "engineering infrastructure equivalent to conventional software: linters for consistency, behavioral contract tests, CI/CD pipelines detecting regressions." For Bureau, this means:

- Each skill should have a declared behavioral contract (what it authorizes, what it restricts, what it modifies)
- Skill composition should be testable against known interference patterns
- Adding a new skill should trigger compatibility analysis against existing installed skills

### 6. The Gemini structural data loss pattern is directly applicable

Bureau's context/memory operations are analogous to Gemini's memory system. If Bureau compacts context, summarizes sessions, or manages skill state across turns, the schema used for compaction must include fields for all state that needs to survive — including skill-injected preferences and behavioral modifications. The Gemini failure is a canonical example of state loss at a schema boundary.

---

## Related work and further reading

### Directly cited by Arbiter

| Paper | Relevance to Bureau |
|---|---|
| Gloaguen et al. (2026), "Evaluating agents.md" (arXiv:2602.11988) | LLM-generated instructions reduce agent performance while increasing cost — relevant to Bureau's skill authoring quality standards |
| Greshake et al. (2023), "Indirect Prompt Injection" | External adversarial injection attacks — orthogonal to internal interference but relevant to Bureau's trust model |
| Conway (1968), "How do committees invent?" | Organizational structure maps onto system design — Bureau's skill authoring process will determine skill structure |
| Parnas (1972), "Module decomposition criteria" | Information hiding and module boundaries — foundational for Bureau's skill boundary design |
| Newman (2021), "Building Microservices" | Microservice composition failures — directly analogous to Bureau's skill composition challenges |
| Zheng et al. (2023), "LLM-as-Judge" | Multi-model evaluation methodology — foundational for Bureau's external evaluation layer |
| Wang et al. (2022), "Self-consistency" | Diverse reasoning paths improve reliability — supports multi-model approach |

### Related work not cited but directly relevant

- **ISP / Instruction Survival Probability (March 2026):** Context compaction threatens instruction persistence — related to Arbiter's structural data loss finding in Gemini CLI
- **SoK: Agentic Skills (2025):** Skill formalization and composition — provides formal grounding for the behavioral contracts Arbiter recommends
- **EvoFSM (2025-2026):** Self-evolving agent FSM framework — evolving skills face the same interference accumulation problem Arbiter documents for static prompts
- **Silicon Mirror (Shah, April 2026):** Anti-sycophancy behavioral gating — sycophancy is a form of runtime conflict resolution bias that would cause an agent to underreport interference detection

---

## Classification: keep / adopt / cite / monitor

| Finding | Classification | Rationale |
|---|---|---|
| Observer's Paradox — self-detection is structurally insufficient | **Adopt** | Core constraint on Bureau's architecture; must be reflected in design spec |
| Three universal categories (Autonomy/Restraint, Precedence Hierarchy, State-Dependent Modes) | **Adopt** | Bureau's skill composition problem maps exactly onto these categories; use as the classification framework for skill interactions |
| External multi-model evaluation as the validated detection approach | **Adopt** | Bureau's pre-analysis phase should use diverse LLM evaluation, not single-model; cost analysis confirms feasibility |
| Architecture predicts failure class (monolith/flat/modular) | **Cite** | Bureau is modular; therefore failures concentrate at composition seams — document this prediction in design |
| Modular architecture concentrates failures at seams not within modules | **Adopt** | Bureau's detection must focus on skill-pair interactions at activation boundaries, not individual skill integrity |
| Schema boundary data loss (Gemini memory pattern) | **Adopt** | Bureau's context compaction / session management must audit schemas for completeness |
| Behavioral contracts + CI/CD for prompt infrastructure | **Adopt** | Bureau's skill authoring standard should require behavioral contract declarations |
| Gloaguen et al. finding (LLM instructions increase cost, reduce performance) | **Monitor** | Relevant to skill authoring quality; Bureau's skill evaluation phase should track this |
| Directed + undirected evaluation as complementary phases | **Adopt** | Bureau's pre-analysis should run both formal rule checks and multi-model scouring |
| 21 specific interference patterns from Claude Code | **Cite** | Empirical ground truth for the types of interference Bureau's detection must handle |
| Conway's Law application to prompt architecture | **Cite** | Bureau's development team structure will shape skill interference patterns — architectural insight |
| Cost analysis ($0.27 for full cross-vendor analysis) | **Monitor** | Demonstrates feasibility; relevant for Bureau's runtime cost model for skill composition analysis |

---

## Summary assessment for Bureau

Arbiter is the most directly relevant paper in this literature review. It:

1. **Validates** the need for the interference detection component Bureau is building
2. **Constrains** the design by proving self-detection is insufficient (Observer's Paradox)
3. **Classifies** the interference space Bureau must address (3 universal categories)
4. **Provides** a validated detection methodology (directed rules + undirected multi-model scouring)
5. **Predicts** where Bureau's modular skill system will accumulate failures (composition seams)
6. **Recommends** engineering infrastructure (behavioral contracts, CI/CD) that Bureau's skill authoring standard should adopt

The primary design challenge Arbiter surfaces for Bureau: Bureau's phase-ordering model (pre-analysis → execution → post-verification → gating) is correctly oriented, but the pre-analysis phase must be executed externally from the executing agent. If the same model both checks for skill conflicts and then runs the skills, the pre-analysis is subject to the same Observer's Paradox that invalidates self-detection.

The secondary challenge: Bureau's skill spec must declare behavioral contracts (what each skill authorizes, restricts, and modifies) so that the pre-analysis phase has structured inputs rather than requiring re-analysis of each skill from scratch on every composition.
