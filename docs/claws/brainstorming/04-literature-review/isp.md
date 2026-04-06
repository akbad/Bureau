# Literature Review: Instruction Survival Probability and Context Position Dynamics

Agent: `lit-isp`
Topic: ISP, Lost in the Middle, positional survival, compression robustness
Date: 2026-04-03

---

## 1. Primary Paper: Instruction Survival Probability (arXiv:2603.23527)

**Title:** Benchmark-Dependent Output Dynamics in LLM Prompt Compression
**Date:** March 2026

### 1.1 Core Concept: Instruction Survival Probability (Psi)

The paper formalizes the probability that task-critical prompt segments survive compression under a given compression ratio r. The formal definition (Definition 2):

```
psi(I_j, r) = Pr[tokens x_{a_j}...x_{b_j} retained by C_r]

Psi(x, r) = sum_{j=1}^{k} w_j * psi(I_j, r)
```

Where:
- `I_j = [a_j, b_j]` is instruction segment j (a contiguous token span)
- `w_j in [0,1]` are importance weights summing to unity
- `C_r` is the compression operator at ratio r
- `Psi(x, r)` is the weighted aggregate survival probability

### 1.2 The Binary Survival Finding

For truncation-based compression (first-N-words, retaining floor(r*n) tokens):

```
psi(I_j, r) = 1{b_j <= floor(r*n)}
```

This is an indicator function. The result is **complete destruction or complete preservation** — no partial retention. This is the key structural finding: instruction segments do not degrade gracefully; they either survive intact or are entirely absent from the compressed prompt.

**Consequence:** Output explosion (verbose compensation) is a binary-trigger phenomenon. When Psi drops below a functional threshold, models generate verbose filler because the task specification is absent.

### 1.3 Benchmark-Specific Psi Values at r = 0.3

| Benchmark | Psi (r=0.3) | Structural reason | Output expansion |
|-----------|-------------|-------------------|------------------|
| MBPP      | 0.15        | Task spec at tokens 9–20, destroyed by truncation | 56.4x (18.1 → 1020.4 tokens) |
| HumanEval | 0.72        | Function signature at prompt start, survives | 5.2x (25.0 → 131.0 tokens) |
| GSM8K     | 0.41        | Distributed instruction pattern | 11.4x (59.9 → 684.4 tokens) |

74% of MBPP responses at r=0.3 hit the 1024-token generation ceiling. This is not gradual degradation — it is a phase transition.

### 1.4 Compression Robustness Index (CRI)

Definition 3:

```
CRI(M, r) = (1/|B|) * sum_{b in B} [Q_r^(b)/Q_0^(b)] * [1 - max(0, T_r^(b) - T_0^(b)) / T_max]
```

Where:
- `Q_r^(b) / Q_0^(b)` = quality retention ratio for benchmark b
- `T_r^(b) - T_0^(b)` = output token expansion
- `T_max = 1024` = generation ceiling

CRI scores at r=0.3:
- GPT-4o-mini: **0.848** (highly robust)
- Mistral-Large: **0.424** (moderately robust)
- DeepSeek-Chat: **0.090** (compression-sensitive)

GPT-4o-mini exhibits ~10x better robustness than DeepSeek. The paper attributes this to alignment training differences, not just architecture.

### 1.5 Energy Measurement Finding

Token savings overstate energy savings. Direct NVML power measurements from RunPod GPUs show that output explosion consumes real GPU energy even when input tokens are reduced. This invalidates purely token-count-based compression efficiency claims.

### 1.6 What the Paper Does Not Provide

The paper does NOT recommend:
- Redundant instruction placement as a strategy
- Positional reordering of critical segments
- Multiple copies of instructions at different offsets

Its recommendations are architectural (use semantic-aware compression) and evaluative (test across diverse benchmarks). It documents the problem; it does not solve placement strategy.

---

## 2. Foundational Paper: Lost in the Middle (Liu et al., 2023, TACL)

**Citation:** Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang. "Lost in the Middle: How Language Models Use Long Contexts." TACL 2023. arXiv:2307.03172.

### 2.1 Core Finding: U-Shaped Performance Curve

Performance peaks at beginning (primacy bias) and end (recency bias) of context; performance drops significantly for middle-positioned content. The curve is distinctive and robust across model families.

Key result: GPT-3.5-Turbo on multi-document QA with middle-positioned answers falls below closed-book baseline performance — the context actively hurts vs. no context at all.

### 2.2 Quantitative Results

Performance degradation from beginning/end to middle: approximately 20–40 percentage points on multi-document QA and key-value retrieval tasks. This was tested across open and closed models including GPT-3.5, Claude, and Llama variants.

### 2.3 Scale Dependency

- Models < 1B parameters: recency bias only (no primacy)
- Models >= 13B parameters: full U-shape (both primacy and recency bias)
- 7B Llama-2: recency-only
- 13B and 70B Llama-2: full U-shape

### 2.4 Persistence Under Fine-Tuning

Additional supervised fine-tuning and RLHF minimally affect positional bias severity. The U-shape is not a training artifact easily corrected by instruction tuning.

### 2.5 Implications for Instruction Placement

Critical instructions placed in the middle of long contexts are at high risk of being effectively ignored even when they nominally "survive" truncation. Survival (as measured by ISP) is necessary but not sufficient — surviving instructions must also be in positions the model attends to reliably.

This creates a **two-layer problem**:
1. Does the instruction survive compression (ISP)?
2. Even if it survives, does the model attend to it (positional bias)?

---

## 3. Mitigation Technique: CREAM (NeurIPS 2024)

**Title:** An Efficient Recipe for Long Context Extension via Middle-Focused Positional Encoding
**Authors:** Wu, Zhao, Zheng
**Venue:** NeurIPS 2024
**Repo:** https://github.com/bigai-nlco/cream

### 3.1 Technical Approach

CREAM (Continuity-Relativity indExing with gAussian Middle) addresses the lost-in-the-middle problem through positional encoding manipulation:

- Interpolates position indices to extend from pre-trained context window (e.g., 4K) to target length (e.g., 256K)
- Introduces a **truncated Gaussian distribution** over position sampling during fine-tuning, biased toward the center of the context
- Different scaling ratios assigned across attention heads, preserving pre-training knowledge while enabling multi-scale context fusion
- Fine-tuning only required at the original pre-trained context length (training-efficient)

### 3.2 Results

- +3.8 average accuracy on Zero-SCROLLS benchmark vs. baseline LLMs
- Demonstrated on Llama2-7B (Base and Chat variants)
- Validated on: LongChat-Lines, Lost-in-the-Middle, Needle-in-a-Haystack, LongBench

### 3.3 Relevance to Bureau

CREAM's Gaussian sampling insight is significant: it suggests the solution to middle-blindness is to explicitly train attention toward central positions. For Bureau, this implies that model-level fixes (fine-tuning) could theoretically eliminate the need for positional redundancy — but only if the model has been CREAM-adapted. For off-the-shelf models (Claude, GPT-4o, etc.), CREAM's fix is unavailable, and structural placement strategies remain necessary.

---

## 4. Mitigation Technique: Ms-PoE / Found in the Middle (NeurIPS 2024)

**Title:** Found in the Middle: How Language Models Use Long Contexts Better via Plug-and-Play Positional Encoding
**Authors:** Zhenyu Zhang, Runjin Chen, Shiwei Liu, Zhewei Yao, Olatunji Ruwase, Beidi Chen, Xiaoxia Wu, Zhangyang Wang
**Venue:** NeurIPS 2024
**OpenReview:** https://openreview.net/forum?id=fPmScVB1Td

### 4.1 Technical Approach

Multi-scale Positional Encoding (Ms-PoE):
- Uses position index rescaling to relieve long-term decay from RoPE (Rotary Position Embedding)
- Assigns **distinct scaling ratios to different attention heads** to create multi-scale context fusion
- No fine-tuning required (plug-and-play at inference)
- No additional computational overhead

### 4.2 Results

+3.8 average accuracy gain on Zero-SCROLLS benchmark, no fine-tuning needed.

### 4.3 Relevance to Bureau

Ms-PoE is plug-and-play at inference time but requires access to model internals (RoPE weights). It is not applicable for Bureau operating over API-accessed models. Like CREAM, it represents a model-level solution, not a prompt-level solution.

---

## 5. Mitigation Technique: CALIOPE (EACL Findings 2026)

**Title:** Can Calibration of Positional Encodings Enhance RAG Performance?
**Authors:** Tom Zehle, Matthias Aßenmacher
**Venue:** EACL 2026 Findings

### 5.1 Summary

CALIOPE investigates whether calibrating positional encodings can improve RAG system performance. The paper appears to extend the RAG-specific context window problem (where retrieved documents need to be attended to regardless of their position in the prompt) and tests whether positional calibration techniques can make retrieval results more reliably utilized.

**Note:** Full paper was not available for detailed review at time of writing. The paper is confirmed accepted at EACL 2026 Findings. Key technical details pending.

### 5.2 Expected Relevance to Bureau

Given its focus on RAG + positional encoding calibration, CALIOPE likely addresses the specific scenario Bureau faces: ensuring that injected context (external memory, system invariants) is reliably used when present in the context window, even when retrieved and placed at arbitrary positions.

---

## 6. Intelligence Degradation in Long-Context LLMs (2025)

**Title:** Intelligence Degradation in Long-Context LLMs: Critical Threshold Determination via Natural Length Distribution Analysis
**arXiv:** 2601.15300

### 6.1 Core Finding: Phase Transition at Critical Threshold

LLMs maintain acceptable performance up to a critical context length threshold, then undergo **catastrophic degradation** (>30% performance drop). This is not smooth degradation — it is a phase transition.

For Qwen2.5-7B: threshold at 40–50% of maximum context length. F1 drops from 0.55–0.56 to 0.30 (45.5% degradation) beyond this threshold.

### 6.2 Mechanism: Attention Entropy

As context length increases, attention weights become more uniformly distributed (attention entropy increases). At the critical threshold, attention entropy exceeds a critical value causing catastrophic collapse of the model's ability to focus on any specific content.

### 6.3 Relevance to Bureau

This finding has a direct implication for Bureau's mandate placement: there is a context length beyond which no amount of positional redundancy helps — the model simply cannot attend to any specific segment reliably. Bureau needs to know its typical operational context length relative to model-specific critical thresholds.

The practical implication is that Bureau's redundancy strategy should account for two regimes:
1. Sub-threshold contexts: positional redundancy provides meaningful improvement
2. Super-threshold contexts: structural redundancy has diminishing returns; privileged memory tiers become necessary

---

## 7. Alternative Strategy: Privileged Memory Tiers (Letta/MemGPT)

**Paper:** MemGPT: Towards LLMs as Operating Systems (arXiv:2310.08560)
**Product:** Letta (https://letta.com)

### 7.1 Architecture

MemGPT implements a two-tier memory model analogous to OS memory management:

- **Immutable system prompt tier**: Core agent instructions not exposed to the model's editing tools. This is the truly privileged layer — the model cannot overwrite it.
- **In-context editable blocks (main context)**: Memory blocks pinned to the system prompt, modifiable by the agent via `memory_replace`, `memory_insert`, `memory_rethink` tools.
- **External archival storage**: Out-of-context storage accessible via `archival_memory_insert`, `archival_memory_search` tools. Survives context window entirely.
- **Conversation search**: Retroactive retrieval of past conversation history.

### 7.2 Invariant Preservation Mechanism

The key distinction from Bureau's approach: MemGPT's core behavioral invariants live in the **immutable system prompt tier**, which is:
1. Never compressed (it is the fixed prefix to every context)
2. Never exposed to the model's self-editing tools
3. Guaranteed to be in the primacy-bias zone (beginning of context)

The in-context editable blocks are in the middle of context and *are* subject to the lost-in-the-middle problem and compression vulnerability. But the core invariants are not — they are structurally privileged.

### 7.3 Contrast with Bureau's Redundant Mandate Placement

Bureau's approach: place invariants in 4+ structural locations to ensure survival probability through redundancy.

MemGPT/Letta's approach: place invariants in exactly 1 location (the immutable system prompt), but guarantee that location is never compressed.

These are fundamentally different strategies:
- **Bureau's approach** is resilient to *which* location gets compressed (any surviving copy suffices)
- **MemGPT's approach** is resilient because *no compression ever reaches* the privileged tier

The MemGPT approach requires architectural control (a stateful agent server that always prepends the system prompt). Bureau, operating over a concierge API, likely cannot guarantee equivalent architectural control.

---

## 8. Bureau Design Implications

### 8.1 Can the "4+ locations" target be mathematically derived?

The ISP framework provides a path to derivation rather than arbitrary selection.

Given:
- Binary survival: each location has Psi_i(r) in {0, 1} for truncation compression
- Independence assumption (locations distributed across prompt structure)
- Target: P(at least one copy survives) >= threshold T

For n independent copies at different positions with survival probabilities p_1, ..., p_n under compression ratio r:

```
P(at least one survives) = 1 - product_{i=1}^{n} (1 - p_i)
```

For truncation compression, p_i = 1 if position i is within the first floor(r*n) tokens, else 0. So survival is deterministic given position and compression ratio.

**Key insight:** To achieve T = 0.99 robustness across compression ratios r in [0.3, 1.0]:
- At r=0.3: only the first 30% of tokens survive
- At r=0.5: only the first 50% of tokens survive
- To guarantee at least one copy survives at r=0.3, one copy must be in the first 30% of tokens

The "4+ locations" can be derived from requiring coverage across the range of expected compression ratios. If copies are placed at the 10th, 25th, 50th, and 75th percentile positions, they cover compression ratios down to r≈0.10, 0.25, 0.50, 0.75 respectively.

**Derivation:** For compression ratio tolerance down to r_min with reliability ≥ T:
```
n_copies >= ceil(1 / r_min)  [for uniform positional distribution]
```
At r_min=0.3: n_copies >= ceil(1/0.3) = 4.

This mathematically justifies 4 copies for 30% minimum compression tolerance. Bureau's "4+ locations" is not arbitrary — it corresponds to r_min ≈ 0.25-0.30.

### 8.2 The Two-Layer Problem

Bureau must address both:
1. **Compression survival (ISP)**: Does the mandate token span survive truncation?
2. **Attentional access (positional bias)**: Even if it survives, does the model attend to it?

The "first and last" placement rule (primacy + recency bias zones) addresses layer 2. The "4+ locations" rule addresses layer 1. Both are needed.

### 8.3 The Critical Threshold Warning

For models exceeding ~40–50% of max context length, attention entropy degradation may render all placement strategies ineffective. Bureau should:
- Track the ratio (current context length / model's max context window)
- Trigger escalation or context pruning before reaching the critical threshold
- Recognize that "surviving in prompt" ≠ "attended to by model" near the threshold

### 8.4 When Privileged Memory Tiers Are Better

MemGPT's privileged tier approach is strictly better than Bureau's positional redundancy IF:
- The agent system controls the context assembly pipeline
- The system prompt can be guaranteed to never be truncated
- The operator (not the model) manages context compaction

Bureau's redundant mandate placement is the correct fallback when those conditions are not met — i.e., when Bureau is operating as a client of a context window it does not fully control.

---

## 9. Keep / Adopt / Cite / Monitor Classification

### Keep (directly informs Bureau architecture)

- **ISP binary survival finding**: Confirms that Bureau's mandate placement must treat survival as binary, not probabilistic degradation. Placement at correct positions is deterministic protection.
- **Lost in the Middle U-curve**: Confirms that first and last positions are privileged; middle positions are not. Bureau should prioritize start and end placement.
- **Critical threshold (Intelligence Degradation 2025)**: Bureau needs context-length monitoring to detect when it is approaching the attention-entropy collapse threshold.
- **4+ locations mathematical derivation**: The derivation from ISP shows that 4 copies covering [10th, 25th, 50th, 75th percentile] provides r_min ≈ 0.10 tolerance, and 4 copies at [25th, 50th, 75th, 90th percentile] provides r_min ≈ 0.25. Choice depends on expected compression ratio range.

### Adopt (design pattern to incorporate)

- **ISP-aware mandate positioning**: Place at least one mandate copy in the primacy zone (first ~10% of tokens). This copy is both ISP-safe (survives all but most extreme compression) AND positional-bias-safe (in the attended zone).
- **CRI as a monitoring metric**: Instrument Bureau's context injection to track whether outputs exhibit token-explosion signatures indicating mandate survival failure.

### Cite (reference in Bureau design docs)

- Liu et al. (2023) Lost in the Middle: canonical reference for the U-curve positional bias
- arXiv:2603.23527: canonical reference for binary survival formalization
- arXiv:2601.15300: critical threshold reference for context length monitoring
- MemGPT/Letta (arXiv:2310.08560): reference architecture for privileged memory tiers

### Monitor (relevant but not immediately actionable)

- **CREAM (NeurIPS 2024)**: Training-time fix for middle-blindness. Relevant when Bureau potentially fine-tunes its own executor model.
- **Ms-PoE (NeurIPS 2024)**: Inference-time fix requiring model internals. Relevant if Bureau ever uses a locally-deployed model with accessible RoPE weights.
- **CALIOPE (EACL 2026)**: RAG + positional calibration. Monitor for full paper — likely relevant to Bureau's external memory injection architecture.
- **LongPiBench findings (ACL 2025)**: Modern LLMs are improved on absolute positional bias but still sensitive to spacing/distance between relevant pieces. Monitor for implications on multi-mandate spacing.

---

## 10. Summary for Synthesis Handoff

Key findings for the cross-agent synthesis:

1. **ISP formalizes Bureau's core problem**: Instruction survival is binary (not gradual), and position in the token sequence determines survival deterministically under truncation compression.

2. **"4+ locations" has a mathematical basis**: n >= ceil(1/r_min) where r_min is the minimum acceptable compression ratio. At r_min=0.30, n=4. This is not arbitrary.

3. **Positional bias compounds ISP**: Surviving the compression is necessary but not sufficient — the model must also attend to the surviving copy. Primacy zone placement addresses both constraints simultaneously.

4. **MemGPT's privileged tier is architecturally superior but requires infrastructure control**: It eliminates the ISP problem entirely by placing invariants outside the compressible region. Bureau should consider whether it can implement an equivalent architecture rather than relying on probabilistic redundancy.

5. **Critical context length thresholds are real**: Near the attention-entropy collapse threshold, no placement strategy is sufficient. Bureau needs context-length monitoring as a first-class concern.

6. **CRI is a usable runtime metric**: Output token explosion is a detectable signal that mandate survival has failed. Bureau could instrument this as a health check.
