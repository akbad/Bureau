# Code review: concierge foundation, config, and UX utilities

> **Generated:** 2026-03-07 | **Target:** `concierge/__init__.py`, `concierge/models.py`, `concierge/state.py`, `concierge/config/`, `concierge/sanitizer.py`, `concierge/formatting.py`, `concierge/vocabulary.py`, `pyproject.toml` + tests
> **Standards:** `~/.config/bureau/protocols/code-standards.md`

## Executive summary

- The foundational layer is **well-structured and coherent**: clean data models with value-driven enums, atomic file persistence, layered config loading with deep merge, and purpose-built UX utilities. The code reads as idiomatic, modern Python (3.13+) with a consistent voice.

- **No correctness-critical bugs** were found. The most notable issue is an inconsistency between `yaml.dump` and `yaml.safe_dump` in the persistence layer (`vocabulary.py` uses `yaml.dump` while `state.py` uses `yaml.safe_dump`), which creates a minor security surface and a pattern violation.

- Test coverage is solid for happy paths but could benefit from additional edge-case and failure-mode tests in several modules (sanitizer, formatting, vocabulary persistence), and most files lack the Tier 1 *design rationale comment block* required by the code standards.

## Architecture

### Component map

The files split into **four logical groups** with clear dependency flow:

- **Package root** (`__init__.py`, `pyproject.toml`)

    - Package identity, version, build configuration, dependency declarations

- **Data models** (`models.py`)

    - Core domain types used by every other module: enums (`MessageClass`, `Suite`, `FeatureType`, `QueueItemState`), value objects (`MessageEnvelope`, `FeatureCandidate`, `QueueItem`), and session state (`SessionState`)

- **Persistence and config** (`state.py`, `config/loader.py`, `config/defaults/*.yml`)

    - `state.py` depends on `models.py` for serialization of `SessionState`
    - `config/loader.py` is self-contained, loading YAML defaults and merging user overrides
    - The three YAML defaults (`classifier.yml`, `priorities.yml`, `pipeline.yml`) are data-only

- **UX utilities** (`sanitizer.py`, `formatting.py`, `vocabulary.py`)

    - `sanitizer.py` and `formatting.py` are **leaf modules** with zero internal dependencies
    - `vocabulary.py` is self-contained (its own `TermState` dataclass, YAML persistence)

Dependency direction flows cleanly inward: UX utilities and config have no cross-dependencies; persistence depends on models; nothing in this group depends on pipeline, classifier, or feature modules.

### Per-component detail

#### Data models (`models.py`)

- **Purpose:** Single source of truth for all domain types shared across the concierge system.

- **Design decisions:**

    - Enums use string values for YAML serialization friendliness
    - `Suite.precedence` is backed by a module-level dict (`_SUITE_PRECEDENCE`) rather than member ordering, which decouples the enum definition order from the priority semantics -- a good choice
    - `FeatureCandidate.__hash__` uses `id(self)` (identity-based), which is intentional: candidates are mutable (score_inputs can change) and need to be used as dict keys in the scoring pipeline. The docstring documents this.
    - `SessionState.record_classification` trims history by slice reassignment rather than a `collections.deque(maxlen=N)` -- slightly less efficient but keeps the type as a plain list for serialization simplicity

- **Invariants:** `_SUITE_PRECEDENCE` must cover all `Suite` members or `Suite.precedence` will raise `KeyError` at runtime

#### Session state persistence (`state.py`)

- **Purpose:** Atomic read/write of `SessionState` to YAML files on disk.

- **Design decisions:**

    - Atomic writes via `tempfile.mkstemp` + `os.rename` -- correct pattern for crash-safe persistence on POSIX systems
    - Manual serialization/deserialization rather than a generic approach (e.g., `cattrs`, `dacite`) -- keeps dependencies minimal and serialization logic explicit
    - `load_session_state` gracefully returns a default `SessionState()` for missing or non-dict files

- **Observation:** The `except BaseException` handler in `save_session_state` catches everything including `KeyboardInterrupt` and `SystemExit`, which is appropriate here since the cleanup (unlinking a temp file) is both safe and quick, and the exception is re-raised.

#### Config loader (`config/loader.py`)

- **Purpose:** Load, merge, and cache YAML configuration from bundled defaults and optional user overrides.

- **Design decisions:**

    - `_deep_merge` uses `copy.deepcopy` defensively -- correct for nested dicts that may be mutated downstream, though it does mean every `load_config()` call performs a deep copy of the entire default tree
    - `lru_cache(maxsize=1)` on the three accessors means they only cache the *defaults* (no user overrides), which is fine for the intended use case (runtime lookups of built-in config) but would silently ignore user overrides if called after a `load_config(user_config_dir=...)` call elsewhere

- **Observation:** The cached accessors (`get_classifier_config`, etc.) and the uncached `load_config` function serve different audiences. The cached versions hardcode `load_config()` with no arguments, making them strictly for default config access. This is a reasonable design, but the distinction is not documented and could surprise a future developer who expects `get_classifier_config()` to reflect user overrides.

#### UX sanitizer (`sanitizer.py`)

- **Purpose:** Strip machine artifacts (code blocks, thinking tags, tool prompts) from outgoing text before presenting to the user.

- **Design decisions:**

    - Compiled regex patterns at module level (good for performance)
    - Two-phase approach: strip patterns first, then cleanup patterns -- clear and extensible
    - The HTML tag regex is a simplified matcher, not a full parser -- sufficient for the expected input (LLM output with occasional HTML), and the docstring implicitly scopes the responsibility

#### Quick-reply formatter (`formatting.py`)

- **Purpose:** Format and parse lettered quick-reply options for Telegram inline keyboards.

- **Design decisions:**

    - Letter-based labeling (`a`, `b`, `c`) rather than numbers -- fits the conversational UX goal
    - `parse_quick_reply` accepts multiple input formats (letter, letter with paren, number, full text) -- defensive and user-friendly
    - `QuickReply` dataclass is minimal (label, text, value) -- just enough for downstream keyboard construction

#### Vocabulary tracker (`vocabulary.py`)

- **Purpose:** Track which domain-specific terms (dispatch, brew, probe, etc.) have been introduced to the user, enabling gradual vocabulary familiarization.

- **Design decisions:**

    - Three-state progression (unknown -> introduced -> user-has-used) with `can_use_term` gating whether the system may freely use a term
    - `FEATURE_TERMS` is a module-level tuple -- acts as the canonical list of terms the system manages
    - `mark_user_used` auto-promotes to introduced (idempotent, correct)

- **Observation:** `should_introduce` returns `True` for any non-empty context string. The method exists as a placeholder for future heuristics (e.g., rate-limiting introductions, context relevance scoring). Currently, it is effectively `not introduced and bool(context)`.

## Findings

| # | File | Severity | Summary |
|---|------|----------|---------|
| 1 | `vocabulary.py` | Should fix | Uses `yaml.dump` instead of `yaml.safe_dump` |
| 2 | `vocabulary.py` | Should fix | `save` is not atomic, unlike `state.py` |
| 3 | Multiple files | Should fix | Missing Tier 1 design rationale comment blocks |
| 4 | `formatting.py` | Should fix | No bounds check on letter overflow past `z` |
| 5 | `config/loader.py` | Consider | Cached accessors silently ignore user overrides |
| 6 | `models.py` | Consider | `_SUITE_PRECEDENCE` could drift from `Suite` enum |
| 7 | `sanitizer.py` | Consider | HTML regex may over-match in edge cases |
| 8 | `test_models.py` | Should fix | Missing blank lines between classes |
| 9 | `test_models.py` | Consider | No test for `record_suite` history trimming |
| 10 | `test_state.py` | Consider | Naive datetimes in roundtrip test |
| 11 | `test_sanitizer.py` | Consider | No combined or edge-case sanitizer tests |
| 12 | `test_formatting.py` | Consider | `test_build_keyboard_data` misplaced in wrong class |
| 13 | `conftest.py` | Consider | `sample_config` fixture diverges from actual defaults |

### Should fix

**#1 -- `vocabulary.py` uses `yaml.dump` instead of `yaml.safe_dump`**

- **Category:** Consistency with codebase patterns
- **Details:** `state.py` uses `yaml.safe_dump` for writing, while `vocabulary.py` uses `yaml.dump`. The `safe_dump` variant restricts output to safe YAML types, preventing accidental serialization of Python objects. Since both files perform the same kind of operation (serializing plain dicts to YAML), they should use the same function.
- **Fix:** Replace `yaml.dump` with `yaml.safe_dump` on line 93 of `vocabulary.py`.

**#2 -- `vocabulary.py` persistence is not atomic**

- **Category:** Correctness concerns
- **Details:** `VocabularyTracker.save` writes directly via `path.write_text(...)`, which means a crash mid-write could leave a corrupted or truncated file. By contrast, `state.py` uses the `tempfile.mkstemp` + `os.rename` pattern for atomic writes. Since both store user state that must survive crashes, vocabulary persistence should follow the same atomic pattern.
- **Fix:** Apply the same temp-file-then-rename strategy used in `save_session_state`.

**#3 -- Missing Tier 1 design rationale comment blocks**

- **Category:** Coding style (standards doc compliance)

- **Details:** The code standards require a *design rationale comment block* at the top of any file implementing non-trivial logic (what, why, key invariants). Several files use docstrings but lack the separate comment block:

    - `models.py` -- has a docstring but no comment block explaining design choices (e.g., why identity-based hash, why manual precedence dict)
    - `sanitizer.py` -- has a docstring but no comment block
    - `formatting.py` -- has a docstring but no comment block
    - `vocabulary.py` -- has a docstring but no comment block
    - `config/loader.py` -- has a docstring with basic description, but lacks invariant/rationale documentation

- `state.py` is the one file that does this well -- its module docstring covers the what, why, and key invariant (atomic writes).
- **Fix:** Add comment blocks (distinct from docstrings, per the standard) at the top of each file, covering what the component does, why the chosen approach, and key invariants.

**#4 -- No bounds check on letter overflow in `format_options` and `build_keyboard_data`**

- **Category:** Correctness concerns

- **Details:** Both `format_options` and `build_keyboard_data` compute labels via `chr(ord(start_letter) + i)`. If the options list has more than 26 entries (or `start_letter` is late in the alphabet), the label overflows past `z` into non-letter characters (`{`, `|`, `}`, etc.). While unlikely in practice for quick-reply keyboards, the function's signature accepts any `list[str]` without constraint.

- **Fix:** Either raise a `ValueError` if the computed label exceeds `z`, or document the constraint in the docstring. A guard clause is preferable:

    ```python
    if ord(start_letter) + len(options) - 1 > ord("z"):
        raise ValueError("Too many options for letter-based labeling")
    ```

**#8 -- `test_models.py` missing blank lines between classes**

- **Category:** Coding style
- **Details:** The test classes in `test_models.py` are not separated by blank lines (e.g., `TestMessageClass` flows directly into `TestSuite` with no gap). PEP 8 recommends two blank lines between top-level definitions. The other test files (`test_state.py`, `test_config.py`, etc.) do include proper spacing.
- **Fix:** Add two blank lines between each test class.

### Consider

**#5 -- Cached accessors silently ignore user overrides**

- **Category:** Design fit
- **Details:** `get_classifier_config()`, `get_priorities_config()`, and `get_pipeline_config()` call `load_config()` with no arguments and cache the result. This means they always return defaults, never reflecting user overrides passed to `load_config(user_config_dir=...)`. This is likely intentional but is undocumented and could mislead callers.
- **Suggestion:** Add a brief docstring note to each accessor clarifying it returns *default-only* config, or consider accepting an optional `user_config_dir` parameter that gets incorporated into the cache key.

**#6 -- `_SUITE_PRECEDENCE` could drift from `Suite` enum members**

- **Category:** Correctness concerns
- **Details:** If a new member is added to `Suite` but not to `_SUITE_PRECEDENCE`, calling `.precedence` on the new member will raise a `KeyError` at runtime. There is no compile-time or startup-time check enforcing completeness.
- **Suggestion:** Add a module-level assertion or a test that verifies all `Suite` members are present in `_SUITE_PRECEDENCE`:

    ```python
    assert set(_SUITE_PRECEDENCE) == set(Suite), "precedence map must cover all suites"
    ```

**#7 -- HTML regex may over-match**

- **Category:** Correctness concerns
- **Details:** The HTML stripping pattern `<[a-z]...>...</tag>` uses a non-greedy match across the content, but could match across multiple unrelated `<tag>...</tag>` pairs in the same text if the tags happen to share a name. For the expected input (LLM output with occasional HTML fragments), this is unlikely to cause issues, but a more precise pattern or an HTML parser (e.g., `html.parser`) would be safer.
- **Suggestion:** Acceptable as-is given the use case. If false positives emerge, consider using `re.DOTALL` with a more constrained pattern or switching to a lightweight parser.

**#9 -- No test for `SessionState.record_suite` history trimming**

- **Category:** Test coverage gap
- **Details:** `test_models.py` tests `record_classification` trimming (verifying the list is capped at 5) but has no analogous test for `record_suite`. The two methods have identical logic, so the risk is low, but symmetry in test coverage is good practice.
- **Suggestion:** Add a `test_record_suite_caps_history` test mirroring the classification one.

**#10 -- Naive datetimes in `test_roundtrip_with_all_fields`**

- **Category:** Correctness concerns
- **Details:** In `test_state.py`, `test_roundtrip_with_all_fields` creates datetimes via `datetime(2026, 3, 7, 10, 0)` without timezone info (naive), while the production code's `_utcnow()` returns timezone-aware datetimes. The roundtrip still works because `datetime.fromisoformat` preserves whatever the input had, but mixing naive and aware datetimes in the same codebase is a common source of comparison bugs.
- **Suggestion:** Use `datetime(2026, 3, 7, 10, 0, tzinfo=timezone.utc)` in the test to match production conventions.

**#11 -- Limited sanitizer edge-case coverage**

- **Category:** Test coverage gap

- **Details:** `test_sanitizer.py` tests each strip pattern and cleanup pattern individually but does not test interactions (e.g., a message with both code blocks *and* thinking tags *and* excessive newlines). It also lacks tests for empty input, input that is *entirely* stripped content, or Unicode edge cases.

- **Suggestion:** Add a combined test case and an empty-input test:

    ```python
    def test_fully_stripped_returns_empty(self):
        assert sanitize("```code only```") == ""

    def test_empty_input(self):
        assert sanitize("") == ""
    ```

**#12 -- `test_build_keyboard_data` is misplaced**

- **Category:** Coding style
- **Details:** `test_build_keyboard_data` is defined inside `TestParseQuickReply` rather than in its own class or as a standalone function. Since `build_keyboard_data` is a separate public function from `parse_quick_reply`, the test would be better organized under a `TestBuildKeyboardData` class.
- **Suggestion:** Move to its own test class for organizational clarity.

**#13 -- `sample_config` fixture diverges from actual defaults**

- **Category:** Design fit
- **Details:** The `sample_config` fixture in `conftest.py` defines a config structure (`classifier.model`, `classifier.temperature`, `priorities.levels`) that does not match the actual default YAML files (which have `classifier.model.confidence_threshold`, `priorities.scoring_weights`, etc.). While this fixture is labeled "minimal valid" and may serve a different purpose, the divergence could mislead test authors who assume it mirrors real config shape.
- **Suggestion:** Either align the fixture with the actual config structure or rename it (e.g., `stub_config`) and add a comment clarifying it is intentionally synthetic.

## Summary

**Verdict:** The foundational layer is well-designed and implements clean, idiomatic Python with sensible architectural choices. The dependency graph is acyclic and properly layered, domain types are expressive, and the persistence pattern in `state.py` is a strong reference implementation. The issues found are consistency and style violations rather than correctness bugs.

- **Must fix:** 0 findings
- **Should fix:** 5 findings
- **Consider:** 8 findings
