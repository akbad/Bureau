# Code review: concierge classifier subsystem

> **Generated:** 2026-03-07 | **Target:** `concierge/classifier/` + tests
> **Standards:** `~/.config/bureau/protocols/code-standards.md`

## Executive summary

- The classifier subsystem implements a well-structured three-stage pipeline (deterministic, model, fuzzy) that faithfully follows the plan's architecture; code is clean, well-documented, and all 20 tests pass.
- Notable deviations from the plan include a significantly improved emoji regex, hardcoded reply tokens that diverge from the config's `exact_match` list, an import style inconsistency in `fuzzy_commands.py`, and a behavioral change in the fuzzy upgrade path that removes the plan's `confidence > 0` guard.
- The most impactful issue is a correctness concern: in `model.py`, the ONNX inference path does not filter tokenizer outputs by session input names in the plan but *does* in the implementation -- a useful improvement, though the session and tokenizer are re-instantiated on every call with no caching, which will be a performance problem once a real model is loaded.

## Architecture

### Component map

The classifier subsystem consists of four source modules in `concierge/classifier/`, ordered by data-flow dependency:

- **`deterministic.py`** -- Stage 0a, fast rule-based classifier

    - No config dependency; hardcodes reply tokens and emoji regex
    - Returns `MessageClass | None` (falls through on `None`)

- **`model.py`** -- Stage 0b, ONNX DistilBERT inference stub

    - Depends on `config.loader.get_classifier_config` for model path and tokenizer name
    - Returns `(MessageClass, float)` tuple; falls back to `(CONVERSE, 0.0)` when model file is absent

- **`fuzzy_commands.py`** -- Stage 0c input, fuzzy verb matcher

    - Depends on `config.loader.get_classifier_config` for verb list and thresholds
    - Returns `str | None` (matched verb or nothing)

- **`classify.py`** -- Orchestrator, chains 0a -> 0b -> 0c

    - Imports all three modules above plus config loader
    - Mutates `MessageEnvelope` in-place and returns it

- **`__init__.py`** -- Empty; no public re-exports

### Dependency graph

```
classify.py
  |-- deterministic.py  -> models.py (MessageClass, MessageEnvelope)
  |-- model.py          -> models.py, config.loader
  |-- fuzzy_commands.py -> config.loader
  `-- config.loader     -> config/defaults/classifier.yml
```

### Per-component detail

#### `deterministic.py` -- Stage 0a

- **Purpose:** Resolve ~60% of messages via cheap checks before any model inference.
- **Design decisions:**

    - Hardcoded `_REPLY_TOKENS` frozenset rather than loading from config's `exact_match` list.

        - The frozenset is a *superset* of the config list (adds `"sure"`, `"nah"`, `"yep"`, `"nope"`), so the config's `exact_match` field is effectively unused.

    - The emoji regex is substantially more comprehensive than the plan's version, covering skin-tone modifiers, ZWJ sequences, keycap sequences, and flag sequences.

        - This is a clear improvement over the plan's naive range-based regex.

    - Rule ordering (attachment -> emoji -> short text with feature -> exact match with feature -> fallthrough) matches the plan.

- **Invariants:**

    - Empty text after stripping is guarded: `0 < len(text)` prevents empty-string classification as REPLY.
    - Single-emoji detection applies *regardless* of active feature (design choice: emojis are always reactions).

#### `model.py` -- Stage 0b

- **Purpose:** Provide ONNX inference interface; currently a stub returning `(CONVERSE, 0.0)`.
- **Design decisions:**

    - The plan separated model loading into a `_load_model` helper; the implementation inlines the path check and defers all heavy imports to the inference branch.

        - This is a reasonable simplification: lazy imports avoid loading `onnxruntime`, `transformers`, and `numpy` unless a model file actually exists.

    - The implementation adds input filtering (`ort_inputs = {k: v for k, v in inputs.items() if k in {i.name for i in session.get_inputs()}}`) that the plan lacked.

        - Beneficial: prevents ONNX runtime errors when the tokenizer produces keys the model does not expect.

    - No caching of the tokenizer or ONNX session -- each call re-instantiates both.

        - Currently irrelevant (stub always returns fallback), but will be a serious performance problem once a model file is present.

- **Invariants:**

    - Always returns a valid `(MessageClass, float)` tuple, never raises.

#### `fuzzy_commands.py` -- Stage 0c input

- **Purpose:** Match the beginning of user text against known command verbs with typo tolerance.
- **Design decisions:**

    - Iterates multiple prefix lengths (`range(len(verb), max_prefix + 1)`) to tolerate length variations.

        - The plan only checked a single prefix length (`text_lower[:len(verb) + 2]`); the implementation tries three lengths. This is a minor improvement for robustness.

    - Uses absolute import (`from concierge.config.loader import ...`) while all other classifier modules use relative imports (`from ..config.loader import ...`).

- **Invariants:**

    - Returns `None` immediately if fuzzy matching is disabled in config.
    - Only returns a verb if its score meets both the `min_score` threshold and is the best among all candidates.

#### `classify.py` -- Orchestrator

- **Purpose:** Chain the three stages and reconcile their outputs.
- **Design decisions:**

    - Behavioral deviation from plan in Stage 0c: the plan conditioned the fuzzy upgrade on `confidence > 0`, meaning the fallback path (`confidence == 0.0`) would *not* upgrade to COMMAND even if a verb was found. The implementation removes this guard, always upgrading to COMMAND when a verb is matched.

        - This is a reasonable change: when the model is stubbed out (`confidence == 0.0`), fuzzy matching is the only signal, so respecting it makes sense. The test `test_command_text_gets_fuzzy_upgraded` explicitly relies on this behavior.
        - The plan's test was more conservative: `assert result.classification in (MessageClass.COMMAND, MessageClass.CONVERSE)`.

    - The fuzzy command call in Stage 0c is made unconditionally (even when model returned COMMAND), whereas the plan only called it when model returned COMMAND or for the upgrade check. This means `match_command_verb` is called once always, which is slightly cleaner.

    - Good use of structured logging at `DEBUG` level at each decision point.

## Findings

| # | File | Severity | Summary |
|---|------|----------|---------|
| 1 | `deterministic.py` | Should fix | `_REPLY_TOKENS` diverges from config `exact_match` list |
| 2 | `fuzzy_commands.py` | Should fix | Absolute import inconsistent with sibling modules |
| 3 | `model.py` | Should fix | No caching of tokenizer or ONNX session |
| 4 | `model.py` | Consider | Incorrect `noqa` comment (`F811` instead of nothing) |
| 5 | `model.py` | Consider | `max_length=128` hardcoded; could be config-driven |
| 6 | `classify.py` | Consider | `confidence` field unchanged on fuzzy upgrade to COMMAND |
| 7 | `classifier/__init__.py` | Consider | No public re-exports for the package API |
| 8 | tests | Should fix | Missing test for empty text input |
| 9 | tests | Should fix | No `cache_clear` fixture for classifier tests |
| 10 | tests | Consider | Test docstrings missing on most test methods |

### Should fix

**#1 -- `_REPLY_TOKENS` diverges from config's `exact_match` list**

- **File:** `concierge/classifier/deterministic.py`, line 19
- The config at `classifier.yml` defines `exact_match: ["yes", "no", "ok", "y", "n"]`, but the code defines `_REPLY_TOKENS` as a superset that also includes `"sure"`, `"nah"`, `"yep"`, `"nope"`.
- This means the config value is *dead configuration* -- changing `exact_match` in the YAML has no effect on behavior.
- **Recommendation:** Either load the token set from config (via `get_classifier_config`) to honor the YAML as the source of truth, or update the YAML to match the code and add a comment explaining the relationship. The config-driven approach is preferred for consistency with how `fuzzy_commands.py` loads its verb list.

**#2 -- Absolute import in `fuzzy_commands.py`**

- **File:** `concierge/classifier/fuzzy_commands.py`, line 11
- Uses `from concierge.config.loader import get_classifier_config` while every other module in the package uses relative imports (`from ..config.loader import ...`).
- **Recommendation:** Change to `from ..config.loader import get_classifier_config` for consistency. The code standards require consistent idioms within a package.

**#3 -- No caching of tokenizer or ONNX session in `model.py`**

- **File:** `concierge/classifier/model.py`, lines 69-71
- Every call to `classify_with_model` would re-instantiate the `AutoTokenizer` and `ort.InferenceSession`. `AutoTokenizer.from_pretrained` involves file I/O and can take hundreds of milliseconds; `InferenceSession` initialization is even more expensive.
- Currently harmless since the model file does not exist, but when a model is eventually provided, this will cause significant latency per message.
- **Recommendation:** Cache both the tokenizer and session at module level (or use a lazy singleton). The plan's version used a separate `_load_model` helper that could serve as the caching point.

**#8 -- Missing test for empty text input**

- **File:** `concierge/tests/test_classifier_deterministic.py`
- No test covers `MessageEnvelope(text="", has_attachment=False)` with an active feature. The code correctly guards against this (`0 < len(text)`), but the guard is untested.
- Edge-case testing is a first-class concern per the code standards.
- **Recommendation:** Add a test `test_empty_text_with_active_feature_falls_through` that verifies empty text does not get classified as REPLY.

**#9 -- No `cache_clear` fixture for classifier tests**

- **File:** `concierge/tests/test_fuzzy_commands.py`, `test_classifier_model.py`, `test_classifier_unified.py`
- The `test_config.py` file properly clears `lru_cache` between tests via an `autouse` fixture, but the classifier test files do not. If test execution order changes or another test mutates the config cache, these tests could see stale or incorrect configuration.
- **Recommendation:** Add a `cache_clear` fixture to `conftest.py` (session- or module-scoped `autouse`) that clears `get_classifier_config.cache_clear()` before and after each test module, or move the existing fixture from `test_config.py` to `conftest.py`.

### Consider

**#4 -- Incorrect `noqa` comment**

- **File:** `concierge/classifier/model.py`, line 58
- `import numpy as np  # noqa: F811` suppresses "redefinition of unused name", but `numpy` is not imported anywhere else in the file. The suppression is unnecessary and misleading.
- **Recommendation:** Remove the `# noqa: F811` comment.

**#5 -- Hardcoded `max_length=128` in tokenizer call**

- **File:** `concierge/classifier/model.py`, line 78
- The tokenizer's `max_length` is hardcoded to 128. While this is a reasonable default for short messages, it could be made configurable through the classifier YAML for consistency with other tuning parameters.
- Per code standards, constants should get descriptive names and justification.
- **Recommendation:** Either extract to a named constant with a comment explaining the choice, or add it to `classifier.yml` under the `model` section.

**#6 -- `confidence` field unchanged on fuzzy upgrade to COMMAND**

- **File:** `concierge/classifier/classify.py`, lines 99-101
- When the fuzzy matcher upgrades a classification to COMMAND, the envelope's `confidence` retains the model's original confidence value (which is `0.0` in the stub case). This means a COMMAND classification can have `confidence=0.0`, which downstream consumers might interpret as "no confidence in this classification."
- **Recommendation:** Consider setting a specific confidence value (e.g., the fuzzy match score normalized to `[0, 1]`) when upgrading via fuzzy match. This would require `match_command_verb` to return the score alongside the verb.

**#7 -- Empty `__init__.py` with no public re-exports**

- **File:** `concierge/classifier/__init__.py`
- The package has no public API surface defined in `__init__.py`. Consumers must import from `concierge.classifier.classify` directly.
- This is fine for internal use but consider re-exporting `classify_message` from `__init__.py` to provide a clean public API: `from concierge.classifier import classify_message`.

**#10 -- Test docstrings mostly absent**

- **Files:** All test files
- Most test methods lack docstrings. The plan's test code included docstrings on some tests (e.g., `test_fallback_when_no_model` had `"""Without a trained model, should return CONVERSE as fallback."""`), but the implementation dropped them.
- The code standards recommend test names that read like mini-specs, which these do, so the docstrings are less critical. But for more complex test scenarios, a brief docstring explaining the *why* would be helpful.

## Summary

**Verdict:** The classifier subsystem is a solid, well-architected implementation that closely follows the plan. The three-stage pipeline is clean, the code is readable, and the emoji regex is a clear improvement over the plan. All 20 tests pass. The issues identified are maintenance and consistency concerns, not correctness bugs.

- **Must fix:** 0 / **Should fix:** 5 / **Consider:** 5
