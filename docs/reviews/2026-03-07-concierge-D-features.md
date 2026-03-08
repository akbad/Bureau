# Code review: concierge features subsystem

> **Generated:** 2026-03-07 | **Target:** `concierge/features/` + tests
> **Standards:** `~/.config/bureau/protocols/code-standards.md`

## Executive summary

- The features subsystem implements **five feature-type evaluators** (dispatch, brew, probe, valet, huddle), a **shared history tracker**, a **schedule parser**, and an **ownership lifecycle manager** across 9 source files and 8 test files.
- Overall quality is **solid**: clean separation of concerns, consistent patterns across evaluators, injectable `now` parameters for testability, and thorough test coverage (87 tests, all passing).
- **6 findings** were identified: 1 must-fix (correctness bug), 2 should-fix (code quality / standards compliance), and 3 consider-level suggestions.

    - The must-fix is a `__import__` hack in `history.py` that is both a correctness smell and a standards violation.

## Architecture

### Component map

```
concierge/features/
    __init__.py           (empty package marker)
    history.py            (JSONL persistence: load, query, record)
    schedules.py          (YAML schedule parsing + due-checking)
    dispatches.py         (evaluator: spontaneous micro-suggestions)
    brews.py              (evaluator: distilled observations)
    probes.py             (evaluator: scheduled intelligence reports)
    valets.py             (evaluator: guided multi-step routines)
    huddles.py            (evaluator + conversation engine: multi-turn Q&A)
    ownership.py          (lifecycle: claim / release / timeout / pause)
```

- **Dependency direction** flows cleanly inward:

    - `dispatches`, `brews` depend on `history` and `models`
    - `probes`, `valets` depend on `schedules` and `models`
    - `huddles` depends on `models` only (self-contained triggers)
    - `ownership` depends on `models` only (relative import `..models`)
    - No circular dependencies; no feature evaluator imports another evaluator

- **Logical sub-groups**:

    1. **History-gated evaluators** (`dispatches`, `brews`) -- use `history.py` for cooldown/frequency checks
    2. **Schedule-gated evaluators** (`probes`, `valets`) -- use `schedules.py` for due-date checks
    3. **Trigger-gated evaluator** (`huddles`) -- uses filesystem presence checks
    4. **Cross-cutting** (`ownership`) -- manages conversation ownership regardless of feature type

### Per-component detail

#### `history.py`

- Provides four functions: `load_feature_history`, `hours_since_last`, `count_in_period`, `record_feature`
- Persistence is **append-only JSONL** -- simple and correct for low-volume feature events
- `hours_since_last` and `count_in_period` parse ISO timestamps on every call; acceptable at current scale but would not scale to thousands of entries

    - **Design trade-off:** simplicity over indexed storage; justified given the expected volume (a few events per week)

#### `schedules.py`

- Parses `schedules.yml` with `yaml.safe_load` into `ScheduleEntry` dataclasses
- `is_due()` implements daily/weekly/biweekly cadence with time-of-day gating
- Handles timezone-naive datetimes defensively by attaching UTC
- Clean helper `_last_run_older_than` factors out the common last-run comparison

#### `dispatches.py` and `brews.py`

- Nearly identical structure: suite gate, history gates (cooldown + frequency limit), then score-input construction
- Both produce a **single candidate** or empty list
- `brews.py` adds two extra gates: PROCESSING suite *and* processing cooldown, plus a per-suite fit mapping

    - **Design trade-off:** the structural similarity between dispatches and brews is *coincidental* -- they have different cooldowns, different frequency windows, different suite-fit logic, and will likely diverge further. Keeping them separate is the right call per the DRY standards ("coincidence, not duplication").

#### `probes.py`

- Iterates over scheduled probes, produces a candidate per due entry
- `_compute_suite_fit` uses a name-containment heuristic; documented as a placeholder
- `_compute_freshness` is a standalone helper with timezone-safety

#### `valets.py`

- Simplest evaluator: checks active-valet gate, iterates due schedules, returns candidates with fixed score inputs
- Correctly does *not* block during PROCESSING suite (documented and tested)

#### `huddles.py`

- Richest module: combines a state machine (`HuddleState`), question definitions (`HUDDLE_QUESTIONS`), reply processing, and candidacy evaluation
- Three trigger conditions: missing `core.md`, 90-day check-in interval, 3+ topic files without goals
- Question flow is index-based with `advance()` / `record_answer()` -- simple and correct

#### `ownership.py`

- Clean dataclass-based state machine: claim, release, touch, timeout, pause/resume
- `OWNING_FEATURES` frozenset and `DEFAULT_TIMEOUTS` dict control which features can own
- Bidirectional sync with `SessionState` via `sync_to_session` and `from_session`
- `should_skip_candidacy` provides the pipeline short-circuit signal

## Findings

| # | File | Severity | Summary |
|---|------|----------|---------|
| 1 | `history.py:56` | Must fix | Inline `__import__("datetime")` to get `timedelta` |
| 2 | `history.py` | Should fix | Missing design rationale block at file top |
| 3 | `dispatches.py`, `brews.py` | Should fix | `hours_since_last` called twice per evaluation |
| 4 | `ownership.py:150` | Consider | `from_session` loses `last_activity` fidelity |
| 5 | `huddles.py:201` | Consider | Silently swallowed `ValueError`/`OSError` on check-in file |
| 6 | `probes.py:83-92` | Consider | Suite-fit heuristic is fragile and underdocumented |

### Must fix

**#1 -- Inline `__import__` in `count_in_period`** (`history.py:56`)

```python
cutoff = now - __import__("datetime").timedelta(hours=period_hours)
```

- This uses `__import__("datetime")` to access `timedelta` despite `datetime` already being imported at the module level (line 13).
- The module-level import is `from datetime import datetime, timezone` -- it imports the *class* `datetime`, shadowing the *module* `datetime`. The inline `__import__` is a workaround for this shadowing.
- **Fix:** add `timedelta` to the existing import and use it directly.

    ```python
    from datetime import datetime, timedelta, timezone
    ```

    Then replace line 56 with:

    ```python
    cutoff = now - timedelta(hours=period_hours)
    ```

- **Why must-fix:** the `__import__` pattern is non-idiomatic, obscures the dependency, and violates the coding standards' prohibition on magic/hidden imports. It is also fragile -- a reader or linter may not realize `timedelta` is actually needed.

### Should fix

**#2 -- Missing design rationale blocks**

- Per the code standards (Tier 1, always required), every file implementing non-trivial logic must have a **design rationale comment block** at the top, distinct from the docstring.
- The docstrings present in each file serve as API documentation but do not explain *why* the approach was chosen, what alternatives exist, or what invariants the reader must keep in mind.
- **Affected files:** `history.py`, `dispatches.py`, `brews.py`, `schedules.py`, `probes.py`, `valets.py`, `huddles.py`, `ownership.py`

    - `huddles.py` and `ownership.py` come closest with their detailed docstrings but still lack the "why this approach" and "key invariants" content.

- **Recommendation:** add a comment block (not docstring) after the module docstring in each file. Example for `ownership.py`:

    ```python
    # Design rationale:
    # Ownership is modeled as a single-slot state machine rather than a stack
    # because the concierge supports at most one multi-turn feature at a time.
    # Only HUDDLE and VALET can claim -- one-shot features (DISPATCH, BREW,
    # PROBE) are fire-and-forget and never own the conversation.
    #
    # Key invariant: at most one feature is active at any time.
    # Timeout values are conservative defaults; they will become configurable
    # once the preferences subsystem lands.
    ```

**#3 -- Duplicate `hours_since_last` call in dispatches and brews**

- Both `dispatches.py` (lines 49, 58) and `brews.py` (lines 63, 72) call `hours_since_last(history, now)` twice per evaluation -- once for the cooldown gate and once for the freshness score.
- Each call re-parses every ISO timestamp in the history list via `datetime.fromisoformat`.
- **Recommendation:** capture the result in a local variable and reuse it.

    ```python
    hours_elapsed = hours_since_last(history, now)
    if hours_elapsed < cooldown_hours:
        return []
    # ... later ...
    raw_freshness = hours_elapsed / cooldown_hours
    ```

### Consider

**#4 -- `from_session` loses `last_activity` fidelity** (`ownership.py:150`)

- `OwnershipManager.from_session` sets `last_activity = session.feature_started_at`, which is the *claim* time, not the actual last-activity time.
- `SessionState` does not carry a `last_activity` field, so the information is genuinely lost across serialization boundaries.
- If `from_session` is ever called on a long-running session that has been "touched" multiple times, the reconstructed manager will appear to have been inactive since the claim time, potentially triggering a **false timeout** on the very next check.
- **Recommendation:** either add a `last_activity_at` field to `SessionState` and round-trip it, or document this limitation prominently so callers know to call `touch()` immediately after reconstruction.

**#5 -- Silently swallowed exceptions on check-in file** (`huddles.py:201`)

```python
except (ValueError, OSError):
    pass  # Malformed or unreadable file -- skip
```

- While the comment explains the intent, silently skipping a malformed `last-checkin.txt` means the system will never trigger a check-in huddle until the file is manually fixed or deleted.
- Per the coding standards: "Never swallow errors silently; if intentionally ignoring, comment *why*."
- **Recommendation:** add a `logging.warning` call so the issue is observable, or at minimum expand the comment to explain the self-healing behavior (e.g., the check-in trigger will fire on the *next* evaluation once the file is regenerated).

**#6 -- Suite-fit heuristic in probes is fragile** (`probes.py:83-92`)

- `_compute_suite_fit` checks whether the suite name appears *as a substring* of the probe domain (or vice versa).
- This means `Suite.REST` would match a probe named "forest" or "arrested", and `Suite.WORK` would match "network".
- The code documents this as a placeholder ("a richer mapping can be added later"), which is good, but the substring match could produce **silent false positives** in the meantime.
- **Recommendation:** either switch to an explicit mapping dict (like `_BREW_SUITE_FIT` in `brews.py`) or at minimum use exact equality rather than substring containment.

## Summary

**Verdict:** *Approve with required changes*

- **1 must-fix** -- the `__import__` hack in `history.py` is a correctness and style violation that should be resolved before merge.
- **2 should-fix** -- missing design rationale blocks (standards compliance) and a redundant computation that is trivially optimizable.
- **3 consider** -- loss of `last_activity` fidelity in session round-trip, silently swallowed errors, and a fragile substring heuristic. None are blockers but all carry latent risk.

The subsystem is well-architected: clean dependency direction, consistent evaluator patterns, injectable time for testing, and 87 passing tests covering happy paths, gate conditions, edge cases, and round-trip fidelity. Once the must-fix item is addressed, this is ready to merge.
