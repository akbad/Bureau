# Code review: concierge memory and distillation subsystems

> **Generated:** 2026-03-07 | **Target:** `concierge/memory/`, `concierge/distillation/` + tests
> **Standards:** `~/.config/bureau/protocols/code-standards.md`

## Executive summary

- The **memory subsystem** (reader + writer) is clean, compact, and faithfully implements the plan
- The **distillation subsystem** (detection, compression, validation, state machine) delivers a complete pipeline with a well-designed state machine and sensible V1 stubs
- Both subsystems are fully tested and match their planned specifications closely
- **8 findings** total: 1 must-fix (timezone inconsistency in writer that silently produces naive datetimes), 4 should-fix, and 3 consider-level items
- Overall the code is well-structured and production-ready pending the issues below

## Architecture

### Component map

```
concierge/memory/
    __init__.py            (empty)
    reader.py              (topic/core/personality file reads)
    writer.py              (auto-index JSONL + topic raw entry appends)

concierge/distillation/
    __init__.py            (empty)
    detection.py           (candidate scanning, redundancy scoring, YAML persistence)
    compress.py            (deterministic compression stub)
    validation.py          (semantic diff / fact coverage validator)
    state.py               (lifecycle state machine with YAML persistence)
```

- **Dependency flow:** `hooks/pre_session.py` --> `memory/reader.py`; `hooks/post_session.py` --> `memory/writer.py`

    - The distillation modules are self-contained and not yet wired into hooks (consistent with phased plan)

- **Data flow:**

    - `reader.py` extracts markdown sections via regex and serves content to the pre-session hook for context injection
    - `writer.py` appends structured entries (JSONL for auto-index, dated bullets for topic files)
    - `detection.py` scans topic files, computes redundancy via pairwise Jaccard similarity, persists candidates to YAML
    - `compress.py` merges raw entries into the distilled section (V1 deterministic stub)
    - `validation.py` validates that compression preserves all facts via keyword coverage
    - `state.py` models the full lifecycle (`IDLE` --> `CANDIDATE` --> `COMPRESSING` --> `COMPRESSED` --> `VALIDATED` --> `VERIFIED` --> `IDLE`, with `FAILED` and retry paths)

### Per-component detail

#### `memory/reader.py`

- **Purpose:** read markdown-based memory files (topic files with `## Distilled` / `## Raw` sections, `core.md`, `PERSONALITY.md`)
- **Design:** regex-based section extraction (`_extract_section`) with `Path.is_file()` guards; returns empty string on missing files
- **Observations:**

    - Clean, idiomatic Python
    - Good use of `re.escape(header)` for safety
    - `read_topic_raw` supports a `last_n` parameter for context budget trimming
    - All public functions consistently guard against missing files

#### `memory/writer.py`

- **Purpose:** append entries to JSONL auto-index files and dated raw entries to topic files
- **Design:** two functions -- `append_auto_entry` (JSONL with auto-timestamp) and `append_raw_entry` (markdown bullet with date prefix)
- **Observations:**

    - `append_auto_entry` creates parent dirs automatically -- good defensive programming
    - Both functions use `datetime.now()` (naive, local time) rather than UTC-aware timestamps, which is inconsistent with the rest of the codebase (see finding #1)

#### `distillation/detection.py`

- **Purpose:** scan topic files for distillation candidacy by computing redundancy scores
- **Design:** extracts phrases from raw entries, computes pairwise Jaccard similarity, tags topics as `"candidate"` when redundancy > 0.5 and entry count >= 5
- **Observations:**

    - `CandidateInfo` uses a string `status` field instead of the `DistillationStatus` enum from `state.py` (see finding #3)
    - Stop-word lists are duplicated across detection, compress, and validation (see finding #4)
    - `compute_redundancy_score` is O(n^2) in phrase count, acceptable for the expected small data volumes
    - `save_candidates` / `load_candidates` provide YAML round-trip persistence

#### `distillation/compress.py`

- **Purpose:** generate an updated distilled section from raw entries (V1 deterministic stub)
- **Design:** preserves existing distilled bullets, adds new entries that don't significantly overlap (50% word overlap threshold), caps at 10 new entries
- **Observations:**

    - Well-documented as a stub with clear production path (LLM summarization)
    - The `topic` parameter is accepted but unused (see finding #6)
    - The 10-entry cap is a magic number without a named constant or comment (see finding #7)

#### `distillation/validation.py`

- **Purpose:** semantic diff validator -- ensures distillation doesn't lose information
- **Design:** extracts facts from both raw and proposed distilled text, checks keyword coverage (50% threshold), reports missing and extra facts
- **Observations:**

    - Clean separation: `extract_facts` --> `extract_key_words` --> `fact_is_covered` --> `validate_distillation`
    - `ValidationResult` dataclass is well-designed with clear semantics
    - The validation is deliberately one-directional: it checks that raw facts are covered in distilled, and separately reports "extra" facts (hallucination detection)
    - Good edge-case handling for empty raw text

#### `distillation/state.py`

- **Purpose:** lifecycle state machine for per-topic distillation
- **Design:** `DistillationStatus` enum with explicit `VALID_TRANSITIONS` dict; `TopicDistillationState` enforces transitions and auto-sets metadata; `DistillationStateMachine` manages all topics with YAML persistence
- **Observations:**

    - This is the best-designed module in the group -- explicit transition validation, side-effect assignment on transitions, retry logic, brew validation tracking
    - YAML round-trip via `save()` / `load()` is clean
    - `should_retry()` uses `<=` comparison (see finding #5)

## Findings

| # | File | Severity | Summary |
|---|------|----------|---------|
| 1 | `memory/writer.py` | **Must fix** | `datetime.now()` produces naive local-time timestamps |
| 2 | `memory/writer.py` | Should fix | `append_auto_entry` puts timestamp before user keys, plan puts it after |
| 3 | `distillation/detection.py` | Should fix | `CandidateInfo.status` is a plain string, not `DistillationStatus` enum |
| 4 | `detection.py`, `compress.py`, `validation.py` | Should fix | Stop-word sets duplicated three times with slight variations |
| 5 | `distillation/state.py` | Should fix | `should_retry()` allows `retry_count == max_retries` (off-by-one) |
| 6 | `distillation/compress.py` | Consider | `topic` parameter is accepted but unused |
| 7 | `distillation/compress.py` | Consider | Magic number `10` for new-entry cap lacks named constant |
| 8 | Tests (all) | Consider | Missing design-rationale comment blocks at file tops |

### Must fix

**#1 -- Naive local-time timestamps in writer**

- **File:** `/Users/danielakbarzadeh/code/bureau-concierge/concierge/memory/writer.py`
- **Lines:** 17, 29
- **Issue:** Both `append_auto_entry` and `append_raw_entry` use `datetime.now()`, which produces a naive, local-timezone timestamp.

    - Every other datetime in the codebase uses `datetime.now(timezone.utc)` (see `models._utcnow`, `detection.py` line 119, `state.py` line 61, `post_session.py` line 42)
    - This means timestamps written by `writer.py` will be inconsistent with timestamps in the distillation state, detection candidates, and session history
    - In `append_auto_entry`, the ISO string will lack a `+00:00` suffix, making round-trip parsing ambiguous

- **Fix:**

    ```python
    # In append_auto_entry:
    stamped = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}

    # In append_raw_entry:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ```

    - Also add `timezone` to the import: `from datetime import datetime, timezone`

### Should fix

**#2 -- Timestamp key ordering differs from plan**

- **File:** `/Users/danielakbarzadeh/code/bureau-concierge/concierge/memory/writer.py`, line 17
- **Issue:** The implementation puts `timestamp` *after* the user-supplied keys:

    ```python
    stamped = {**entry, "timestamp": datetime.now().isoformat()}
    ```

    The plan specifies it *before*:

    ```python
    entry_with_ts = {"timestamp": datetime.now().isoformat(), **entry}
    ```

- **Impact:** If the caller's `entry` dict contains a `"timestamp"` key, the implementation silently *overwrites* it (user key wins in plan version; auto-generated key wins in implementation).

    - Neither behavior is clearly documented
    - The implementation's approach (auto-generated wins) is arguably safer, but the deviation should be intentional and documented

- **Recommendation:** choose one ordering explicitly, document the override behavior in the docstring, and add a test that confirms the timestamp is always auto-generated

**#3 -- String status instead of enum in CandidateInfo**

- **File:** `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/detection.py`, line 20
- **Issue:** `CandidateInfo.status` is typed as `str` with a comment listing valid values:

    ```python
    status: str = "idle"  # idle, candidate, compressing, compressed, validated, verified
    ```

    Meanwhile, `state.py` defines a proper `DistillationStatus` enum with exactly these values

- **Impact:**

    - No compile-time or runtime type safety for status values
    - Violates the code standard: "make invalid states unrepresentable"
    - Risk of typo-based bugs (e.g., `"candidte"` vs `"candidate"`)

- **Recommendation:** import and use `DistillationStatus` from `state.py`, or at minimum use a shared enum

    - This would also align `detection.py`'s string comparisons (`info.status == "candidate"`) with proper enum comparisons

**#4 -- Duplicated stop-word sets across three files**

- **Files:**

    - `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/detection.py` (lines 50, 76)
    - `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/compress.py` (line 63)
    - `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/validation.py` (lines 47-50)

- **Issue:** Four separate stop-word set definitions exist across three files, each with *slightly different* contents:

    - `detection.compute_redundancy_score`: `{"the", "a", "an", "i", "my", "was", "is", "it", "to", "and", "of", "in", "for"}`
    - `detection.detect_patterns`: same plus `"that"`, `"with"`
    - `compress._significant_overlap`: `{"the", "a", "an", "i", "my"}`
    - `validation.extract_key_words`: adds `"on"`, `"at"`, `"by"`, `"from"`, `"she"`, `"he"`, `"her"`, `"his"`, `"been"`

- **Impact:** this is genuine "divergence risk" per the code standards -- the same semantic concept (English stop words for NLP-lite processing) is defined four times and will inevitably drift further apart

- **Recommendation:** extract a single `STOP_WORDS` constant in a shared location (e.g., `distillation/__init__.py` or a small `distillation/text_utils.py`) and import it everywhere

    - If different functions genuinely need different sets, make the base set explicit and document why each function extends or narrows it

**#5 -- Off-by-one in `should_retry()`**

- **File:** `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/state.py`, line 77
- **Issue:** The retry guard uses `<=`:

    ```python
    def should_retry(self) -> bool:
        return (
            self.status == DistillationStatus.FAILED
            and self.retry_count <= self.max_retries
        )
    ```

    With `max_retries=2`, this returns `True` when `retry_count` is 0, 1, or **2** -- meaning the topic will actually be retried up to **3** times (the initial attempt + 2 retries + 1 more because of `<=`)

- **Impact:** topics get one more retry attempt than `max_retries` suggests

    - The test at line 87-91 (`test_should_not_retry_beyond_limit`) only checks `retry_count=3` against `max_retries=2`, which passes but doesn't catch the boundary case at `retry_count=2`

- **Recommendation:** change to `self.retry_count < self.max_retries`, or document that `max_retries` means "maximum total attempts including retries"

    - Add a boundary test: `retry_count == max_retries` should return `False` if the intent is "at most N retries"

### Consider

**#6 -- Unused `topic` parameter in `compress_topic`**

- **File:** `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/compress.py`, line 15
- **Issue:** the `topic: str` parameter is never referenced in the function body

    - It exists as a forward-compatibility placeholder for the planned LLM-based production version (which would include the topic name in the prompt)

- **Recommendation:** either add a `# noqa` / `_ = topic` acknowledgment, or remove it and add it back when the LLM version is implemented

    - The code standard advises against "feature flags or plugin systems for hypothetical future requirements"

**#7 -- Magic number for new-entry cap**

- **File:** `/Users/danielakbarzadeh/code/bureau-concierge/concierge/distillation/compress.py`, line 54
- **Issue:** `new_entries[:10]` uses a bare literal

    ```python
    for entry in new_entries[:10]:  # Cap at 10 new entries
    ```

- **Recommendation:** extract to a named constant with a justification comment per the code standard:

    ```python
    # empirical cap -- prevents distilled section from growing unboundedly
    # in a single compression pass; tunable based on topic complexity
    MAX_NEW_ENTRIES_PER_COMPRESSION = 10
    ```

**#8 -- Missing design-rationale blocks at tops of test files**

- **Files:** all six test files
- **Issue:** the code standard requires a "design rationale block" at the top of any file implementing non-trivial logic

    - The source files have docstrings but most lack the fuller rationale block (approach chosen, alternatives, invariants)
    - Test files have no docstrings at all (only `test_memory_reader.py`, `test_memory_writer.py`) or brief one-liners (detection, compress, validation, state)

- **Recommendation:** add brief module-level comments to test files explaining what subsystem they cover and any test strategy decisions (e.g., "uses `tmp_data_dir` fixture for filesystem isolation")

    - Source files like `reader.py` and `writer.py` would benefit from a one-line rationale comment explaining the markdown format contract

## Summary

**Verdict:** *Approve with required changes.* The memory and distillation subsystems are well-structured, cleanly implemented, and faithfully follow the phased plan. The state machine in `state.py` is particularly well-designed. The one must-fix item (naive timestamps in `writer.py`) is a real consistency bug that will produce ambiguous data in production. The four should-fix items address type safety, DRY violations, and an off-by-one boundary in retry logic. The three consider items are quality-of-life improvements. Total: **1 must-fix, 4 should-fix, 3 consider**.
