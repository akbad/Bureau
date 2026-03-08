# Code review: concierge pipeline subsystem

> **Generated:** 2026-03-07 | **Target:** `concierge/pipeline/` + tests
> **Standards:** `~/.config/bureau/protocols/code-standards.md`

## Executive summary

- The pipeline subsystem implements six components spanning suite detection, attache selection, hard rule enforcement, priority scoring, queue management, and epsilon-greedy feature selection.
- All **29 tests pass** across the six test modules.
- The implementation closely follows the original plan from `docs/plans/2026-03-07-concierge-implementation.md`, with a small number of beneficial deviations and a few items that need attention.
- Overall code quality is **solid**: clean separation of concerns, good use of immutable data structures, clear naming, and well-structured tests.
- Key concerns are a **correctness trade-off** in the queue's eviction logic (diverges from the plan in a necessary but suboptimal way), a **latent pluralization fragility** in scoring, **missing design-rationale blocks** on `lottery.py` and `scoring.py`, and some gaps in negative-path test coverage.

## Architecture

### Component map

The pipeline forms a linear processing chain with the following dependency flow:

```
models.py (Suite, FeatureType, FeatureCandidate, QueueItem, SessionState)
    ^
    |
    +-- suite_detector.py     (Stage 1: message -> Suite)
    +-- attache_selector.py   (Stage 2: Suite -> attache file list)
    +-- hard_rules.py         (Stage 3: Suite + Session -> blocked FeatureTypes)
    +-- scoring.py            (Stage 4: candidates + weights -> ranked scores)
    +-- queue.py              (Stage 5: bounded priority queue with aging)
    +-- lottery.py            (Stage 6: epsilon-greedy final selection)
```

- Every pipeline module depends **only** on `concierge.models` (inward dependency direction, as per standards).
- No pipeline module imports another pipeline module; they are composed at a higher orchestration layer.
- `queue.py` is the sole module with an external dependency (`pqdict`).

### Per-component detail

#### `suite_detector.py`

- **Purpose:** Maps inbound message text + session context + wall clock to a `Suite` enum.
- **Approach:** Keyword-set scanning in precedence order (Processing > Social > Creative > Work), then session persistence, then time-of-day heuristic, then default REST.
- **Plan alignment:** Faithful to the plan. The implementation *inlines* the keyword check rather than extracting a `_has_keyword` helper as the plan specifies; this is a minor structural difference that is arguably *better* (fewer indirections, the `any()` call is simple enough to inline).

    - One subtle deviation: the plan uses `time(9, 0) <= current_time <= time(17, 0)` (inclusive upper bound), while the implementation uses `time(9, 0) <= current_time < time(17, 0)` (exclusive upper bound). The implementation is more correct (5:00 PM should not map to WORK under business-hours logic), so this is a **beneficial** deviation.

- **Observations:**

    - Multi-word keywords like `"burned out"` and `"dinner with"` are stored in `frozenset` but matched via substring (`kw in text_lower`), so they work correctly despite being in a set. Good.
    - The gap window between 7:00 AM and 9:00 AM and between 5:00 PM and 8:00 PM falls through to the default REST. This is intentional and documented in the docstring.

#### `attache_selector.py`

- **Purpose:** Maps a `Suite` to a list of attache filenames, and optionally loads their markdown content from disk.
- **Plan alignment:** Identical to the plan, with two small improvements:

    - The implementation returns `list(SUITE_ATTACHE_MAP.get(suite, []))` (defensive copy) vs. the plan's bare `.get()` return. The copy prevents callers from mutating the canonical mapping. Good.
    - The implementation uses `path.is_file()` vs. the plan's `path.exists()`, which is stricter and avoids accidentally trying to read a directory. Good.

#### `hard_rules.py`

- **Purpose:** Evaluates non-negotiable blocking rules that prevent certain feature types from being surfaced.
- **Plan alignment:** Matches the plan exactly, including the extra Rule 4 (processing cooldown) that the plan includes in the implementation but omits from the initial test. The implementation *also* adds the test for Rule 4, which is a welcome addition.

    - The implementation uses `is` comparisons for enum members (e.g., `suite is Suite.PROCESSING`) whereas the plan uses `==`. Both are correct for Python enums (enum members are singletons), and `is` is marginally more idiomatic and faster.

#### `scoring.py`

- **Purpose:** Scores feature candidates by applying per-feature-type weight tables via dot product.
- **Plan alignment:** Deviates from the plan in the pluralization strategy. The plan uses a simple `value + "s"` suffix (`dispatch -> dispatches`), while the implementation introduces a `_pluralize()` helper with `_ES_SUFFIXES` handling. This is a more general approach, but introduces fragility (see Finding #2).

#### `queue.py`

- **Purpose:** Bounded priority queue backed by `pqdict` (min-heap with negated priorities for max-first semantics).
- **Plan alignment:** Significant deviation in the eviction logic (see Finding #1). The plan calls `self._pq.top()` to get the worst item, which is **incorrect** in a negated min-heap (`.top()` returns the *highest*-priority item, not the lowest). The implementation *corrects* this by using `max(self._pq, key=self._pq.__getitem__)` to find the worst item. However, this correction introduces an O(n) scan on every insertion when the queue is full.

    - The implementation also adds timezone-aware handling in `expire_stale` (checking `tzinfo` and using `now_aware` vs `now_naive` accordingly). The plan only uses `datetime.now()`. This is a good defensive addition.

- **Observations:**

    - The `__iter__` method iterates over `self._items.values()` (implementation) vs. `self._pq` keys mapped to items (plan). The implementation's approach is simpler and equally correct.
    - UUID truncation: `uuid4().hex[:8]` gives 8 hex chars (32 bits of randomness). With `max_queue_size=10`, collision probability is negligible.

#### `lottery.py`

- **Purpose:** Epsilon-greedy selector that occasionally explores (random pick) instead of exploiting (highest-scoring pick), with a suite-fit floor filter.
- **Plan alignment:** Matches the plan exactly in behavior. Identical test suite.
- **Observations:**

    - **Missing design-rationale comment block** at the top of the file (see Finding #3). The one-line docstring does not meet the Tier 1 standard.
    - The class has no docstring (see Finding #4).
    - Uses `random.random()` directly, making tests depend on `random.seed()` for reproducibility. This works but could be fragile across Python versions. Acceptable for now.

## Findings

| # | File | Severity | Summary |
|---|------|----------|---------|
| 1 | `queue.py` | Must fix | Eviction uses O(n) linear scan; needs justification comment or algorithmic fix |
| 2 | `scoring.py` | Must fix | `_pluralize` is fragile for future `FeatureType` values; replace with explicit lookup |
| 3 | `lottery.py` | Should fix | Missing Tier 1 design-rationale comment block |
| 4 | `lottery.py` | Should fix | `FeatureSelector` class has no docstring |
| 5 | `queue.py` | Should fix | `expire_stale` calls both `datetime.now(tz)` and `datetime.now()` unconditionally |
| 6 | `suite_detector.py` | Should fix | Multi-word keywords in frozensets rely on substring matching with no explanatory comment |
| 7 | `attache_selector.py` | Should fix | `load_attache_content` silently skips missing files with no logging |
| 8 | `scoring.py` | Should fix | Missing design-rationale comment block (Tier 1 standard) |
| 9 | `test_queue.py` | Consider | `test_expired_items_removed` uses naive datetime; fragile timezone coupling |
| 10 | `test_lottery.py` | Consider | Widened tolerance band vs. plan weakens statistical assertion |
| 11 | `test_scoring.py` | Consider | No isolated test for `_pluralize` helper |
| 12 | `test_attache_selector.py` | Consider | No test for `load_attache_content` with multiple files |
| 13 | `pipeline/__init__.py` | Consider | Empty file; could re-export public API symbols |

### Must fix

#### #1 -- O(n) eviction scan in `queue.py` when queue is full

- **File:** `concierge/pipeline/queue.py`, line 77
- **Issue:** When the queue is at capacity, `add()` calls `max(self._pq, key=self._pq.__getitem__)` to find the lowest-priority item. This is O(n) and defeats the purpose of using a heap-backed priority queue.
- **Context:** The plan's original code used `self._pq.top()` to find the worst item, but this is incorrect because `pqdict.top()` returns the *minimum* stored value, which in the negated scheme is the *highest*-priority item, not the lowest. The implementation correctly identified this bug, but replaced it with a linear scan.
- **Fix options:**

    - **Option A (pragmatic):** Given that `max_queue_size` is 10, the O(n) scan is acceptable in practice. Add a comment justifying the trade-off, e.g. `# O(n) scan acceptable for small bounded queues (max_size typically <= 10)`.
    - **Option B (algorithmic):** Maintain a second `pqdict` with non-negated priorities to enable O(1) lookup of the worst item. Adds complexity not warranted by the current scale.

    - **Recommendation:** Option A. Add the justifying comment per the "constant justification" standard.

#### #2 -- Latent pluralization fragility in `scoring.py`

- **File:** `concierge/pipeline/scoring.py`, lines 11-18
- **Issue:** `_pluralize` checks `value.endswith(_ES_SUFFIXES)` where `_ES_SUFFIXES = ("s", "sh", "ch", "x", "z")`. This works for all current `FeatureType` values, but is not a general-purpose English pluralizer. If a future `FeatureType` value ends unexpectedly (e.g., `"story"` -> `"storys"` instead of `"stories"`), the weight lookup will silently fail and the candidate will score 0.
- **Fix:** Replace with an explicit lookup dict mapping `FeatureType` values to their plural weight keys. This is simpler, unambiguously correct, and eliminates the need for the `_pluralize` helper entirely:

    ```python
    _TYPE_TO_WEIGHT_KEY: dict[str, str] = {
        "dispatch": "dispatches",
        "brew": "brews",
        "probe": "probes",
        "valet": "valets",
        "huddle": "huddles",
    }
    ```

### Should fix

#### #3 -- Missing design-rationale comment block on `lottery.py`

- **File:** `concierge/pipeline/lottery.py`, line 1
- **Issue:** The Tier 1 commenting standard requires a design-rationale *comment block* (distinct from docstrings) at the top of any file implementing non-trivial logic. The epsilon-greedy algorithm, the suite-fit floor filter, and the decay mechanism all warrant explanation of *why* this approach was chosen.
- **Fix:** Add a comment block explaining:

    - Why epsilon-greedy over other exploration strategies (e.g., Thompson sampling, UCB)
    - What the suite-fit floor protects against (irrelevant features leaking via exploration)
    - How decay balances initial exploration with convergence

#### #4 -- Missing class docstring on `FeatureSelector`

- **File:** `concierge/pipeline/lottery.py`, line 9
- **Issue:** The `FeatureSelector` class has no docstring. Per the code standards, classes with non-obvious field semantics should document their purpose and parameter contracts.
- **Fix:** Add a docstring documenting the class purpose, parameters (`epsilon`, `decay`, `min_epsilon`, `suite_fit_floor`), and their valid value ranges.

#### #5 -- Redundant `datetime.now()` calls in `expire_stale`

- **File:** `concierge/pipeline/queue.py`, lines 125-126
- **Issue:** Both `datetime.now(timezone.utc)` and `datetime.now()` are called unconditionally at the top of the method, even though typically only one branch is needed per item.
- **Fix:** Compute lazily, or standardize on timezone-aware timestamps throughout the codebase (preferred, since `models.py` already defaults to `timezone.utc`).

#### #6 -- Non-obvious keyword-matching strategy undocumented

- **File:** `concierge/pipeline/suite_detector.py`, lines 17-97
- **Issue:** The keyword sets contain multi-word strings like `"burned out"` and `"dinner with"`. These are stored in `frozenset` (which suggests token-level membership testing) but matched via `kw in text_lower` (substring search). This works, but the design choice is non-obvious and warrants a "why, not what" comment.
- **Fix:** Add a brief comment above `_KEYWORD_RULES` or near the `any()` call explaining that substring matching is intentional to support multi-word keywords.

#### #7 -- Silent file-skip in `load_attache_content`

- **File:** `concierge/pipeline/attache_selector.py`, lines 38-44
- **Issue:** Missing attache files are silently skipped. If an attache is configured in `SUITE_ATTACHE_MAP` but its `.md` file does not exist, the system proceeds without it and without logging. This could mask deployment or configuration errors.
- **Fix:** Add a `logger.warning()` call when a configured file is missing.

#### #8 -- Missing design-rationale comment block on `scoring.py`

- **File:** `concierge/pipeline/scoring.py`, line 1
- **Issue:** Same as #3. The module docstring is adequate as a docstring but the Tier 1 standard requires a separate *comment block* explaining design rationale (why weighted dot product, why per-type weights, etc.).

### Consider

#### #9 -- Timezone mismatch in `test_expired_items_removed`

- **File:** `concierge/tests/test_queue.py`, lines 45-53
- **Issue:** The test backdates `item.queued_at` using `datetime.now()` (naive), but `QueueItem`'s default factory uses `datetime.now(timezone.utc)` (aware). The test only works because `expire_stale` has a `tzinfo` check that falls back to naive comparison. This coupling is fragile.
- **Fix:** Use `datetime.now(timezone.utc) - timedelta(hours=2)` in the test to match the model's default behavior.

#### #10 -- Widened tolerance in `test_statistical_exploration_rate`

- **File:** `concierge/tests/test_lottery.py`, line 65
- **Issue:** The plan specifies `0.08 < explore_rate < 0.16`, but the implementation uses `0.06 < explore_rate < 0.18`. The wider band reduces the test's ability to detect regressions.
- **Fix:** Tighten to the plan's bounds, or document why the wider band was necessary.

#### #11 -- No isolated test for `_pluralize`

- **File:** `concierge/tests/test_scoring.py`
- **Issue:** The `_pluralize` helper is only exercised indirectly through `score_candidates`. Adding a few direct tests (especially edge cases like values ending in `s`, `ch`, `x`) would catch regressions faster.

#### #12 -- Missing multi-file test for `load_attache_content`

- **File:** `concierge/tests/test_attache_selector.py`
- **Issue:** Only single-file load and missing-file skip are tested. A test loading 2-3 files and verifying correct concatenation order would strengthen coverage.

#### #13 -- Empty `pipeline/__init__.py`

- **File:** `concierge/pipeline/__init__.py`
- **Issue:** The file is empty. Re-exporting primary public symbols would allow consumers to use `from concierge.pipeline import detect_suite` instead of reaching into submodules.
- **Trade-off:** The current direct-import style is also valid and keeps the dependency graph explicit. Low priority.

## Summary

**Verdict:** **Approve with required changes.** The pipeline subsystem is well-structured, follows domain conventions, maintains clean inward dependency direction, and all 29 tests pass. The two must-fix items are low-severity in practice (the O(n) scan operates on a queue bounded to 10 items; the pluralization fragility does not affect current feature types), but both should be addressed to prevent future regressions. The should-fix items are primarily documentation gaps against the Tier 1 commenting standard. No architectural or design-level concerns.

- **Must fix:** 2 *(#1 queue eviction justification, #2 pluralization robustness)*
- **Should fix:** 6 *(#3-#8, primarily missing design-rationale blocks and minor defensive improvements)*
- **Consider:** 5 *(#9-#13, test improvements and minor polish)*
