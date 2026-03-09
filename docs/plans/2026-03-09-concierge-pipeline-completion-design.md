# Concierge Pipeline Completion Design

> Approved design for completing three remaining concierge subsystems:
> pipeline orchestrator (#37), DistilBERT classifier (#38), and
> LLM-based compression (#39).

## 1. Pipeline Orchestrator (#37)

### Decision: plain function composition (no Burr)

The 6 pipeline stages are a linear chain with no branching, retries, or
persistence needs. A ~30-line orchestrator function replaces the planned
Burr state machine dependency.

**Rejected alternative:** Burr state machine — adds a dependency, boilerplate,
and learning curve for a linear pipeline. Can be added later if the pipeline
gains branching or observability requirements.

### Architecture

```
concierge/pipeline/orchestrator.py
  run_pipeline(envelope, state, queue) -> FeatureCandidate | None

  1. detect_suite(envelope, state)        → Suite
  2. select_attaches(suite)               → list[str]
  3. check_hard_rules(suite, state)       → RuleResult (may block)
  4. evaluate_features(suite, state, ...) → list[FeatureCandidate]
  5. score + queue.push_batch(scored)      → updated queue
  6. run_lottery(queue, suite)            → FeatureCandidate | None
```

- Short-circuits at step 3 if `hard_rules` blocks (returns `None`)
- Each stage is wrapped in try/except; failures log and return safe defaults
- Feature candidates come from the features modules (dispatches, brews,
  probes, valets, huddles, schedules) — evaluated against the current suite

---

## 2. DistilBERT ONNX Classifier (#38)

### Decision: synthetic training data → fine-tune → ONNX export

Generate labeled training examples using an LLM, fine-tune DistilBERT,
export to quantized ONNX. No real user data needed.

**Rejected alternatives:**
- Zero-shot NLI model — lower accuracy (~70-80%), larger model file
- LLM-based classification — 500ms+ latency per message on hot path
- Keep stub — QUERY and CONVERSE remain indistinguishable

### Training data specification

| Class    | Index | Count | Description                                    |
|----------|-------|-------|------------------------------------------------|
| REPLY    | 0     | 500   | Short acknowledgments, reactions, yes/no        |
| QUERY    | 1     | 500   | Questions requiring information                 |
| CONVERSE | 2     | 500   | General conversation, updates, opinions         |
| COMMAND  | 3     | 500   | Imperative instructions to control features     |

**Format:** JSONL — `{"text": "...", "label": "REPLY"}`

**Domain:** Personal assistant (Bureau Concierge) handling daily life topics:
meals, fitness, schedules, music, wellness, travel, weather, social,
work-life balance. The concierge has "features" (dispatches, brews,
probes, valets, huddles) that it proactively suggests.

**Generation method:** LLM-generated, one agent per class, reviewed before
training. No generation script — examples produced directly.

### Training pipeline

**Step 1 — Data preparation**

Combine per-class JSONL files into `training_data.jsonl`. Encode labels:
REPLY=0, QUERY=1, CONVERSE=2, COMMAND=3 (matches `model.py` `_CLASS_MAP`).

**Step 2 — Tokenization**

```python
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
tokens = tokenizer(text, max_length=128, truncation=True,
                   padding="max_length", return_tensors="pt")
# Produces: input_ids (128,) + attention_mask (128,)
```

Parameters match the existing `model.py` inference code exactly.

**Step 3 — Model architecture**

```python
model = DistilBertForSequenceClassification.from_pretrained(
    "distilbert-base-uncased", num_labels=4
)
```

Architecture: DistilBERT (66M params) + linear head (768 → 4).
HuggingFace `DistilBertForSequenceClassification` handles the `[CLS]`
pooling and classification head automatically.

**Step 4 — Training**

| Parameter       | Value                                |
|-----------------|--------------------------------------|
| Train/val split | 80/20, stratified by class           |
| Epochs          | 3-5 (early stopping, patience=2)     |
| Batch size      | 16                                   |
| Learning rate   | 2e-5                                 |
| Optimizer       | AdamW, linear warmup (10% of steps)  |
| Loss            | CrossEntropyLoss                     |
| Hardware        | CPU (Apple Silicon, ~15-30 min)      |

Early stopping monitors validation loss. Training halts if val loss
doesn't improve for 2 consecutive epochs.

**Step 5 — ONNX export**

```python
dummy = tokenizer("hello", return_tensors="pt", max_length=128,
                  padding="max_length", truncation=True)
torch.onnx.export(
    model,
    (dummy["input_ids"], dummy["attention_mask"]),
    "model.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    dynamic_axes={"input_ids": {0: "batch"}, "attention_mask": {0: "batch"},
                  "logits": {0: "batch"}},
    opset_version=14,
)
```

Dynamic axes enable variable batch size at inference time.

**Step 6 — INT8 quantization**

```python
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic("model.onnx", "model_quantized.onnx",
                 weight_type=QuantType.QInt8)
```

Reduces ~250MB → ~60-70MB. ~2x inference speedup. Negligible accuracy
loss for text classification.

**Step 7 — Validation**

- Run quantized ONNX model on held-out val set
- Per-class precision/recall/F1 report
- Verify outputs match PyTorch model (atol=1e-4)
- **Minimum threshold: >85% accuracy on val set before shipping**
- If below threshold: regenerate/augment training data and retrain

### Integration

- Add `onnxruntime`, `transformers`, `numpy`, `torch` to `pyproject.toml`
  as optional dependency group `[ml]`
- Existing `model.py` already has caching, inference, and fallback logic —
  no changes needed except placing the `.onnx` file at the configured path
- Model file: checked into repo (quantized DistilBERT is ~60-70MB) or
  git-lfs for larger files

### File locations

```
concierge/classifier/
  training_data/          # generated JSONL files
    reply.jsonl
    query.jsonl
    converse.jsonl
    command.jsonl
  train.py                # training + export script
  model.onnx              # exported quantized model (generated)
```

---

## 3. LLM-based Compression (#39)

### Decision: call Bureau-configured agent CLI

The compression function calls the user's preferred Bureau-configured
agent (claude, gemini, codex, opencode) in non-interactive mode. Falls
back to the deterministic stub on failure.

### Configuration

Add to `defaults.yml` under `conversations.concierge`:

```yaml
concierge:
  preferred_agent: claude
```

Add to `config_loader.py` `ConversationsConciergeConfig` TypedDict:

```python
preferred_agent: str    # agent CLI for LLM calls, default "claude"
```

**Validation:**
1. `preferred_agent` must be in `{"claude", "gemini", "codex", "opencode"}`
2. `preferred_agent` must be in the resolved config's `agents` list
3. If invalid: log warning, fall back to first enabled agent in `agents`

### Prompt

```
You are a memory distiller. Compress raw timestamped entries about a personal
topic into a concise summary, merging with any existing distilled content.

## Topic: {topic}

## Current distilled summary
{distilled_text or "(empty — first distillation)"}

## New raw entries
{raw_text}

## Rules
1. Preserve ALL facts — losing information is the only failure mode
2. Consolidate repeated observations into patterns
   (e.g., three mentions of pasta → "Enjoys pasta — mentioned repeatedly")
3. Prefer general truths over specific dated instances
   (e.g., "Runs 5K every Tuesday" over "[2026-01-15] Ran 5K, [2026-01-22] Ran 5K")
4. Keep specific dates only when they carry meaning (events, milestones, changes)
5. Output markdown bullets (- prefix), ordered from most to least significant
6. Do not invent, infer, or extrapolate beyond what the entries state

## Output
Return ONLY the updated distilled summary. No preamble, no explanation.
```

### Architecture

```
concierge/llm.py                  # thin wrapper: call agent CLI, return stdout
concierge/distillation/compress.py  # updated: calls llm.call_agent(prompt)
```

**`concierge/llm.py`:**
- `call_agent(prompt: str, agent: str | None = None) -> str`
- Reads `preferred_agent` from config if `agent` not specified
- Validates agent is supported and enabled
- Shells out to agent CLI in non-interactive mode
- Returns stdout (stripped)
- Raises `LLMError` on failure (timeout, non-zero exit, empty output)

**`compress_topic()` updated flow:**
1. Build prompt from template + inputs
2. Call `call_agent(prompt)`
3. Parse response as markdown bullets
4. Run existing `validate_distillation()` check
5. If validation fails: retry once with "You missed these facts: ..." appended
6. If still fails: fall back to deterministic stub, log warning

### Error handling

| Failure mode          | Behavior                                      |
|-----------------------|-----------------------------------------------|
| Agent CLI not found   | Warning + deterministic fallback               |
| CLI timeout (30s)     | Warning + deterministic fallback               |
| CLI non-zero exit     | Warning + deterministic fallback               |
| Empty response        | Warning + deterministic fallback               |
| Validation failure    | One retry with feedback, then fallback         |
| API rate limit        | Caught by CLI timeout, fallback applies        |

The system always produces output — LLM failure never blocks distillation.
