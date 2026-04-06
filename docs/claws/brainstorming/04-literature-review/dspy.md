# DSPy: Literature Review

**Paper:** "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines"
**Authors:** Khattab et al. (Stanford NLP / Databricks)
**Venue:** ICLR 2024 (Spotlight)
**Relevance to Bureau:** Automated optimization of behavioral protocols against golden datasets

---

## Framework Summary

DSPy (Declarative Self-improving Python) treats prompt engineering as a compilation problem. Instead of hand-crafting prompts, developers write declarative programs using typed modules and signatures; a compiler (optimizer) then searches for the prompt text, few-shot demonstrations, and/or weight updates that maximize a user-defined metric over a training set.

The canonical framing: "programming, not prompting." The system is analogous to PyTorch - you define computation graphs with differentiable-ish components, and an optimizer tunes the parameters.

### Core Abstractions

**Signatures**
- Declarative input/output specs: `"context: list[str], question: str -> answer: str"`
- Class-based signatures allow docstrings and per-field descriptions that guide the LM
- Support Pydantic models for structured outputs
- The docstring/description text is what the optimizer mutates to improve performance
- Cannot enforce computational constraints (they are suggestions to the LM, not hard rules)

**Modules**
Built-in reasoning strategies:
- `dspy.Predict` - basic prediction, no added reasoning
- `dspy.ChainOfThought` - adds a `reasoning` field before the answer
- `dspy.ReAct` - tool-using agent loop
- `dspy.ProgramOfThought` - generates + executes code to derive answers
- `dspy.MultiChainComparison` - samples multiple CoT chains, selects best
- `dspy.Refine` - wraps any module with N-retry loop + reward function threshold

Custom modules extend `dspy.Module` and implement a `forward()` method, enabling arbitrary Python control flow between LM calls.

**Optimizers (formerly "Teleprompters")**
The optimizer takes a program, a trainset, and a metric function, then modifies the program's parameters (prompt instructions, few-shot demonstrations, or weights) to maximize the metric.

---

## How the Compile Step Works Mechanically

### The Optimization Target

DSPy programs have "parameters" - specifically, the instruction text and few-shot demonstration examples attached to each Predictor within the program. The optimizer mutates these parameters while leaving program structure (control flow, module composition) unchanged.

### Optimizer Taxonomy

**Few-Shot Learning Optimizers** (find optimal demonstrations):
- `LabeledFewShot` - randomly samples k labeled examples from trainset
- `BootstrapFewShot` - runs a teacher LM over trainset, collects traces, keeps passing examples as demos; validates with metric
- `BootstrapFewShotWithRandomSearch` - applies BootstrapFewShot N times with different random example subsets, returns highest-scoring program on valset
- `KNNFewShot` - embeds examples, uses nearest-neighbors for per-input few-shot selection

**Instruction Optimizers** (find optimal instruction text):
- `COPRO` - iterative hill-climbing; generates new instructions, evaluates on trainset, keeps better ones; coordinate ascent per module
- `MIPROv2` - the flagship optimizer; three-phase process:
    1. Bootstrap few-shot candidates (runs program over trainset, keeps passing examples)
    2. Propose instruction candidates (LLM reads code + data + traces + tips, generates N instruction variants)
    3. Bayesian Optimization over instruction × demo combinations across num_trials trials on valset
- `SIMBA` - stochastic mini-batch sampling, targets high-variability examples with LLM introspection
- `GEPA` - uses rich textual feedback (not just scalar scores) from a metric that returns `dspy.Prediction(score=..., feedback=...)`; Pareto-based selection

**Fine-tuning Optimizer**:
- `BootstrapFinetune` - converts optimized prompts into training data for weight updates; produces a finetuned model that runs without prompting overhead

**Meta-Optimizers**:
- `BetterTogether` - sequences prompt optimization then weight optimization then prompt optimization again; empirically outperforms either alone
- `Ensemble` - combines multiple programs, optionally with random sampling

### MIPROv2 in Detail (the most capable optimizer)

Phase 1: Bootstrap - randomly sample examples, run program, keep outputs that pass metric as candidate demonstrations.

Phase 2: Propose - an LLM reads (a) a data summary, (b) the program source code and predictor details, (c) bootstrapped few-shot examples, (d) random "tips" (e.g., "be creative", "be concise"). Generates `num_instruct_candidates` instruction variants for each predictor.

Phase 3: Search - Bayesian Optimization evaluates combinations of instructions × demonstrations over `num_trials` trials. Uses mini-batches for efficiency; full valset eval every N steps. Returns the best-performing program configuration.

Data requirements by optimizer:
- BootstrapFewShot: ~10 examples minimum
- BootstrapFewShotWithRandomSearch: ~50 examples
- MIPROv2: 300+ examples recommended (can work with fewer)
- GEPA: standard ML splits, metric must return textual feedback

### What Gets Optimized vs What Stays Fixed

**Can be optimized:**
- Instruction text within each `dspy.Predict`/module signature
- Which few-shot examples appear in each module's prompt
- Model weights (via BootstrapFinetune)

**Cannot be optimized by DSPy:**
- Program control flow, module composition, Python logic
- The program's overall architecture
- Constraints enforced by code outside DSPy (e.g., external validators)

---

## Evaluation and Assertion Framework

### Metric Functions

DSPy metrics are Python functions with signature `(example, pred, trace=None) -> float`. They can be:
- Simple string comparisons (`pred.answer.lower() == example.answer.lower()`)
- Multi-property scorers (average of several boolean checks)
- LLM-judge metrics (a `dspy.Predict` call assessing quality)
- DSPy programs themselves (optimizable metrics)

During compilation, `trace is not None` and metrics can access intermediate LM outputs, enabling validation of reasoning steps, not just final answers.

### Assertions (DEPRECATED as of DSPy 2.x)

`dspy.Assert` (hard constraint) and `dspy.Suggest` (soft constraint) are deprecated and not supported. New code should use `dspy.Refine`.

`dspy.Refine`:
- Wraps any module, runs it up to N times at temperature=1.0
- Evaluates each attempt with `reward_fn(inputs, prediction) -> float`
- Returns first prediction exceeding threshold, or highest-scoring attempt
- If no attempt passes, generates automatic feedback to improve future attempts
- Replaces the old "backtrack and retry" assertion mechanism

---

## Assessment: Applicability to Bureau's Behavioral Protocols

Bureau skills are 200-900 line markdown documents with:
- Activation/deactivation triggers (pattern-matched user phrases)
- Phased execution protocols (e.g., Phase 1: Determine inputs, Phase 2: Review, Phase 3: Audit)
- Hard constraints labeled "non-negotiable" or "IMMUTABLE"
- Rationalization tables and decision trees
- Cross-references to companion files (style.md, TRAINING.json)
- Multi-turn, stateful behavior across an entire conversation

TRAINING.json files contain golden datasets with: scenario descriptions, expected_behavior prose, violation_indicators (strings), and categorization metadata.

### Where DSPy's Model Maps Well

**1. TRAINING.json as trainset**
The `cases` array in TRAINING.json maps directly to DSPy's `trainset` concept. Each case is an `Example` with inputs (scenario, category) and expected outputs (expected_behavior, violation_indicators). A metric function could check agent outputs against expected_behavior descriptions, potentially using an LLM judge.

**2. Metric definition**
Bureau already has implicit metrics embedded in violation_indicators. These could be formalized as a DSPy metric: run the skill protocol against a scenario, extract the agent's actions, check against violation_indicators. This is exactly the pattern DSPy expects.

**3. GEPA's textual feedback loop**
GEPA's requirement for `feedback` in metric return values aligns with Bureau's violation_indicators. A metric that returns both a score and the triggered violation strings could drive GEPA's reflective optimization.

**4. BootstrapFewShot for rationalization examples**
If Bureau skills include rationalization tables (showing example reasoning chains), BootstrapFewShot could automatically generate high-quality examples by running the skill on diverse inputs and keeping the traces that pass the metric.

### Where the Model Breaks Down

**1. The fundamental unit mismatch**
DSPy optimizes signatures and their instruction text. A Bureau skill is not a signature - it is a multi-kiloword specification document that orchestrates multiple tool uses, file reads, metric checks, and output formats over a full conversation. DSPy has no concept of a "protocol document" as an optimization target.

DSPy can optimize: the instruction appended to a single LM call.
Bureau needs to optimize: an entire behavioral specification that governs 20-50 sequential LM calls.

**2. Phase and state awareness**
Bureau protocols have strict phases with state transitions. DSPy's multi-step programs can be optimized module-by-module, but each module's optimization is independent. The interaction between phases - whether Phase 1 output correctly sets up Phase 2, whether deactivation conditions are correctly detected - cannot be captured in per-module metrics.

**3. IMMUTABLE sections**
Bureau protocols contain explicitly non-negotiable constraints (e.g., "these directives are non-negotiable hard constraints"). DSPy's optimizer has no concept of IMMUTABLE vs. mutable sections - it will attempt to optimize all instruction text. There is no mechanism to freeze part of a protocol while optimizing others.

Workaround: one could split a skill into separate modules where immutable sections become fixed Python strings (not DSPy Signature instructions). But this requires a complete rewrite of skill structure into DSPy's module architecture.

**4. Evaluation signal quality**
Bureau's TRAINING.json expected_behavior fields are prose descriptions, not easily reducible to boolean metrics. A DSPy metric that uses an LLM judge to evaluate whether the agent's behavior matched the expected_behavior description introduces:
- LLM-judge unreliability
- Circular dependency (LLM evaluating LLM behavior)
- High cost per optimization trial (full skill execution × multiple agents × metric evaluation)

**5. The compilation cost problem**
MIPROv2 with 300 examples and 50 trials would require ~15,000 LM calls minimum for a single skill optimization. At $0.01/call, that is $150 per optimization run per skill. Bureau has many skills; amortizing this cost is non-trivial.

**6. Context-dependency of optimized outputs**
A critical finding from empirical study (arxiv 2507.03620): "extracting the optimized instructions out of DSPy might not always work as expected." Optimized prompts can become entangled with DSPy's internal inference machinery, degrading when used outside the framework. Bureau skills must work in vanilla LLM calls (no DSPy runtime at inference time).

**7. DSPy operates at the module level; Bureau protocols operate at the document level**
DSPy's optimizer produces an instruction string (typically 50-200 tokens) for each module. A Bureau skill is a structural specification with phases, conditionals, and cross-references. The optimizer would need to generate and evaluate entire protocol documents, not just instruction strings - a task DSPy is not designed for.

---

## Specific Design Implications for Bureau

### What Bureau Can Borrow from DSPy's Architecture

**1. The trainset → metric → optimizer loop as a formal pattern**
DSPy crystallizes a pattern Bureau should adopt: (a) maintain a golden dataset, (b) define an executable metric, (c) run a search procedure over protocol formulations. This is exactly RED-GREEN-REFACTOR at scale. The value is in the pattern, not in using DSPy's specific implementation.

**2. GEPA's feedback loop for REFACTOR**
GEPA's insight - that optimization benefits from rich textual feedback, not just pass/fail scores - is directly applicable to Bureau. When a skill fails a TRAINING.json case, the violation_indicators string is exactly the kind of textual feedback GEPA uses. Bureau could implement a GEPA-inspired loop: run skill → check violation_indicators → feed violations as feedback into a protocol-revision prompt → iterate.

**3. BootstrapFewShot for rationalization tables**
Bureau skills that include rationalization examples could use BootstrapFewShot's approach: run the protocol over diverse inputs, collect passing traces, store as approved examples. This systematizes the "authoring" source in TRAINING.json's `source` field.

**4. Hierarchical optimization**
DSPy decomposes multi-step programs into modules and optimizes each. Bureau could decompose skills into sections and optimize each section independently with its own subset of TRAINING.json cases. This is Bureau-native hierarchical optimization, not a DSPy deployment.

### What Bureau Should NOT Copy

- DSPy's assumption that the optimization target is short instruction text
- DSPy's assumption that program structure is fixed and only instructions/demos vary
- DSPy's module/signature architecture as a replacement for protocol documents

### Whether to Use DSPy as Infrastructure

**Verdict: no.** The mismatch between DSPy's architecture and Bureau's skill structure is fundamental, not incidental. DSPy was designed to optimize LM calls, where the optimization target is instruction text and few-shot examples. Bureau skills are behavioral specifications that govern multi-call conversations; they are the equivalent of a state machine specification, not a prompt.

Using DSPy would require either:
1. Rewriting skills as DSPy programs (abandoning markdown protocol documents, losing human-readability, locking into DSPy's runtime)
2. Wrapping the entire skill evaluation in a single DSPy module (reducing the optimization target to the system prompt text passed to the model, which is a single string - losing all phase and structure awareness)

Both options are worse than implementing Bureau-native optimization.

---

## Comparison with Alternatives

### TextGrad
- Approach: "autograd for text" - iterative instance-level refinement via LLM-generated gradients
- Optimization target: any differentiable component
- Better than DSPy when: individual problem instances are complex and require deep iterative refinement
- Worse than DSPy when: you need scalable, production-ready systems
- Bureau relevance: TextGrad's instance-level refinement could be applied to individual TRAINING.json failures - for each failing case, TextGrad iteratively refines the relevant protocol section. More surgical than DSPy's batch optimization. Potentially more applicable to Bureau's IMMUTABLE section constraint (you could exclude those from TextGrad's search space).

### ARES (Automated RAG Evaluation System)
- From same lab (Khattab/Zaharia)
- Purpose: automated evaluation of RAG pipelines, not optimization
- Builds synthetic training data for evaluation judges
- Bureau relevance: ARES's approach to synthetic evaluation data generation is directly applicable. Bureau could generate additional TRAINING.json cases synthetically using an LLM that has seen a few real cases.

### EvoPrompt
- Evolutionary algorithm for prompt optimization
- Works on single prompts, not multi-module programs
- Less sophisticated than MIPROv2 but conceptually simpler
- Bureau relevance: If Bureau reduces to optimizing a single instruction field per section, EvoPrompt-style mutation could work. But this is less powerful than GEPA.

### APE (Automatic Prompt Engineer)
- Treats prompt optimization as a generation + search problem
- LLM generates candidate prompts, evaluates them
- Simpler than DSPy; no compilation framework required
- Bureau relevance: APE's approach - use an LLM to propose revised protocol sections given feedback, evaluate on TRAINING.json cases - is the closest match to what Bureau actually needs. APE can be implemented without any framework dependency.

### COPRO/MIPROv2 (as standalone techniques, not DSPy framework)
The underlying technique in MIPROv2 (generate instruction candidates via LLM, search via Bayesian Optimization) can be extracted and applied to Bureau's protocol sections without using the DSPy framework itself. This is the most promising "borrow the technique" path.

---

## Limitations for Bureau's Use Case (Summary)

1. **Unit mismatch**: DSPy optimizes instruction strings per module; Bureau needs to optimize protocol sections (hundreds of lines per section).

2. **No IMMUTABLE awareness**: The optimizer does not understand that some sections must not change. Would require significant engineering to freeze certain sections.

3. **No phase/state awareness**: Per-module optimization misses cross-phase interaction effects.

4. **Evaluation cost**: Full skill execution to generate metrics is expensive; DSPy's optimization would require thousands of full-conversation evaluations.

5. **Context dependency**: Optimized prompts may become entangled with DSPy's inference runtime, degrading portability.

6. **Prose metric problem**: TRAINING.json's expected_behavior is prose, not a clean boolean. Building a reliable metric requires an LLM judge, which introduces its own failure modes.

7. **Skill structure incompatibility**: Bureau skills have activation triggers, deactivation conditions, cross-file references - none of which fit DSPy's module model.

8. **Runtime coupling**: Deploying DSPy would require Bureau agents to run inside DSPy's inference framework, not just use the optimized output. This is an infrastructure dependency Bureau has not chosen.

---

## Classification

**Verdict: CITE (study techniques, do not adopt as infrastructure)**

**Reasoning:**

DSPy's core insight - that prompt optimization can be automated given a metric and a trainset - is directly applicable to Bureau's REFACTOR phase. The specific techniques (GEPA-style textual feedback loops, BootstrapFewShot-style trace collection, Bayesian search over candidate formulations) are extractable without adopting the framework.

Bureau should NOT adopt DSPy as infrastructure because:
- Skills are protocol documents, not module programs
- IMMUTABLE sections cannot be expressed in DSPy's model
- Evaluation requires full conversation execution (expensive)
- Context dependency risks degrading skill portability
- Bureau's REFACTOR needs to produce human-readable markdown, not optimized DSPy programs

Bureau SHOULD study DSPy for:
- The formal loop: trainset → metric → optimizer → updated program → re-evaluate
- GEPA's textual feedback incorporation (maps to violation_indicators)
- MIPROv2's instruction proposal technique (LLM reads code + data + examples → generates candidate instructions) → applicable to section-level protocol revision
- BootstrapFewShot's trace-based example collection → applicable to TRAINING.json expansion
- The metric design patterns (multi-property scoring, LLM-judge metrics, trace-aware metrics)

The correct Bureau architecture for automated REFACTOR is a Bureau-native loop using these techniques, not a DSPy wrapper around protocol execution.

---

## Key Sources

- DSPy GitHub: https://github.com/stanfordnlp/dspy
- DSPy docs: https://dspy.ai/
- ICLR 2024 paper: https://arxiv.org/abs/2310.03714
- MIPRO (EMNLP 2024): https://aclanthology.org/2024.emnlp-main.525.pdf
- DSPy Assertions paper: https://arxiv.org/abs/2312.13382
- Multi-use case empirical study: https://arxiv.org/html/2507.03620v1
- MIPROv2 optimizer docs: https://dspy.ai/api/optimizers/MIPROv2/
- GEPA optimizer docs: https://dspy.ai/api/optimizers/GEPA/overview/
- DSPy vs TextGrad comparison: https://medium.com/@adnanmasood/beyond-prompt-engineering-how-llm-optimization-frameworks-like-textgrad-and-dspy-are-building-the-6790d3bf0b34
