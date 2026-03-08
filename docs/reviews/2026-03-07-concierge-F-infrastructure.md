# Code review: concierge infrastructure and templates

> **Generated:** 2026-03-07 | **Target:** `concierge/background/`, `concierge/setup/`, `concierge/bridge/`, `concierge/hooks/`, templates + tests
> **Standards:** `~/.config/bureau/protocols/code-standards.md`

## Executive summary

- Group F covers the **operational backbone** of the Concierge system: background task scheduling, system installation, CLI bridge adapters, session lifecycle hooks, and all user-facing prompt/attache/huddle templates.
- The code is clean, well-structured, and idiomatic Python.

    - All 111 tests pass, and every source file has corresponding test coverage.
    - Design intent is consistently clear from module docstrings and inline comments.

- **Primary concerns** center on a TOCTOU race in the lockfile, inconsistent timezone handling in a downstream dependency (memory writer), and missing design-rationale comment blocks per the project's own Tier 1 commenting standards.
- **6 findings** total: 1 must fix, 3 should fix, 2 consider.

## Architecture

### Component map

```
concierge/
    background/
        runner.py        -> BackgroundRunner, CheckType, CheckResult
        lockfile.py      -> LockFile (file-based mutual exclusion)
        catchup.py       -> CatchupPolicy (wake-from-sleep throttle)
    setup/
        launchd.py       -> macOS plist generator + installer
        wizard.py        -> First-run configuration wizard
    bridge/
        cc_connect.py    -> CLI backend abstraction (Codex/Claude/Gemini)
    hooks/
        pre_session.py   -> Context injection (personality + memory + vocab)
        post_session.py  -> Memory extraction + session state persistence
    attaches/            -> 10 domain-specialist role descriptions (.md)
    prompts/             -> 5 structured prompt templates (.md)
    huddles/             -> 6 guided-conversation flow scripts (.md)
```

- **Dependency direction** is healthy: `catchup` depends on `runner`, `wizard` depends on `cc_connect`, hooks depend on `memory.reader`/`memory.writer` and `vocabulary`.

    - No circular imports; no upward coupling from infrastructure to domain.

- **Data flow** follows a clear pipeline: `pre_session` assembles context before a CLI session, and `post_session` harvests memories and updates state afterward.

### Per-component detail

#### `background/runner.py`

- Defines `CheckType` (enum of five background check categories), `CheckResult` (outcome record), and `BackgroundRunner` (scheduler that tracks last-run times and respects minimum intervals).
- All time-sensitive methods accept an optional `now` parameter, enabling deterministic tests without mocking clocks.

    - This is a strong design choice that aligns with the code standards' prohibition on `sleep()` and real clocks in tests.

- `run_check` is explicitly a stub (v1) that returns a successful `CheckResult` and marks the check as run.

    - The docstring documents this intentional stub status clearly.

#### `background/lockfile.py`

- Implements file-based mutual exclusion using `os.open` with `O_CREAT | O_EXCL` for atomic creation.
- Includes stale-lock detection (reads the timestamp written into the lock file, breaks locks older than `stale_timeout`).
- Supports context-manager protocol (`__enter__`/`__exit__`).
- **Key concern:** there is a TOCTOU (time-of-check-time-of-use) window between the stale-lock check (`path.exists()` + `path.read_text()` + `path.unlink()`) and the subsequent `os.open` with `O_CREAT | O_EXCL`.

    - A concurrent process could create a new lock in that gap.
    - See Finding #1 below.

#### `background/catchup.py`

- `CatchupPolicy` is a clean data-driven prioritizer: it accepts a runner, filters for due checks, sorts by a static priority tuple, and caps at `max_catchup_checks`.
- `estimate_downtime` correctly uses `max()` over `last_runs.values()` to find the most recent activity.
- `run_catchup` delegates to `runner.run_check` for each selected check.

    - Straightforward composition; no unnecessary abstraction.

#### `setup/launchd.py`

- Uses `string.Template` for plist XML generation with `$variable` substitution.
- `install_plist` writes to `~/Library/LaunchAgents/` but deliberately does *not* call `launchctl load`, documenting this in the docstring.

    - Good separation of write from activation.

- No XML escaping is applied to substituted values.

    - See Finding #4 below.

#### `setup/wizard.py`

- Defines `SetupAnswers` (dataclass), `SETUP_QUESTIONS` (declarative question list), `validate_answers`, `generate_config`, `save_config`/`load_config`, and `initialize_data_dir`.
- `validate_answers` covers all required fields and includes time-format validation for `briefing_time`.
- `save_config` uses `yaml.dump`; `load_config` uses `yaml.safe_load` (safe deserialization).
- `initialize_data_dir` creates the standard directory tree and writes stub `PERSONALITY.md` and `core.md` files, preserving existing content.

#### `bridge/cc_connect.py`

- `CLIBackend` enum maps to `CLI_COMMANDS` dict, which defines the base invocation pattern for each backend.
- `BridgeConfig.get_cli_command` builds a complete command list by appending the prompt to the base command.
- `build_headless_command` reads a prompt file and appends its contents.

    - Handles missing files by substituting an empty string.

- `validate_config` checks token format (expects exactly one `:`), user ID positivity, and non-empty assistant name.

#### `hooks/pre_session.py`

- `build_context` assembles a system-prompt prefix by loading personality, core memory, vocabulary guidance, and topic distilled sections in priority order, respecting a word-count budget.
- Vocabulary guidance is generated by `_build_vocabulary_guidance`, which maps each term's state to a natural-language instruction for the LLM.
- Budget enforcement is correct: personality and core are always included; vocabulary is always included; topics are added in sorted order until the budget would be exceeded.

#### `hooks/post_session.py`

- `extract_memories` runs v1 regex-based preference extraction over session transcripts and writes matches to topic files.
- Hardcodes `datetime.now(timezone.utc)` for timestamps (correctly timezone-aware, unlike the downstream `memory.writer` calls).
- `_extract_preferences` defines five regex patterns for "like/love/hate/dislike/allergic/cook" statements.

    - Patterns use `(?:i|I)` instead of `re.IGNORECASE`, which is fragile.
    - See Finding #5.

- `update_session_state` appends JSONL entries to `state/session_history.jsonl`.

#### Templates (attaches, prompts, huddles)

- **Attaches** (10 files): each defines a domain-specialist role with `## Guidelines` section.

    - Consistent structure across all files.
    - Content is concise and persona-appropriate.

- **Prompts** (5 files): structured prompt templates with `{{variable}}` placeholders.

    - `system.md` is the most detailed, defining core rules, tone, suite-specific behavior, and memory integration.
    - All use `{{context}}` as a tail placeholder.

- **Huddles** (6 files): guided conversation flows with `## Flow` (numbered steps) and `## Rules` sections.

    - Uniform structure; content reads naturally as conversational scripts.

## Findings

| # | File | Severity | Summary |
|---|------|----------|---------|
| 1 | `background/lockfile.py` | Must fix | TOCTOU race between stale-lock check and atomic create |
| 2 | `background/runner.py`, `catchup.py`, `pre_session.py`, `post_session.py`, `cc_connect.py`, `wizard.py`, `launchd.py` | Should fix | Missing Tier 1 design-rationale comment blocks |
| 3 | `hooks/post_session.py` | Should fix | `extract_memories` silently skips topics without files |
| 4 | `setup/launchd.py` | Should fix | No XML escaping on template substitution values |
| 5 | `hooks/post_session.py` | Consider | Regex patterns use `(?:i\|I)` instead of `re.IGNORECASE` |
| 6 | `background/runner.py` | Consider | `BackgroundRunner` uses a dataclass but has mutable behavior |

### Must fix

**#1 -- TOCTOU race in `LockFile.acquire` (`background/lockfile.py:30-51`)**

- The method checks for a stale lock via `self.path.exists()` + `read_text()` + `unlink()` *before* attempting the atomic `os.open(O_CREAT | O_EXCL)`.
- Between the `unlink()` on line 35 and the `os.open()` on line 44, another process could create a new, valid lock file.

    - The current process would then overwrite that lock, resulting in two processes believing they hold the lock simultaneously.

- **Fix:** wrap the stale-lock removal and atomic creation in a single sequence that retries the `O_CREAT | O_EXCL` after breaking the stale lock, or use `fcntl.flock()` / `fcntl.lockf()` for advisory locking which avoids the stale-file problem entirely.

    - At minimum, after `unlink()`, re-attempt `os.open(O_CREAT | O_EXCL)` and handle `FileExistsError` (another process won the race) rather than falling through unconditionally.

- **Test gap:** no test exercises concurrent `acquire()` calls from separate threads or processes, so this race is not caught by the existing suite.

### Should fix

**#2 -- Missing Tier 1 design-rationale comment blocks (all source files)**

- The code standards require a **design rationale comment block** (distinct from the module docstring) at the top of every file implementing non-trivial logic.

    - This block should explain *what* the component does, *why* this approach was chosen, and *key invariants*.

- Every source file in this review uses a module-level docstring (`"""..."""`) which partially fulfills this, but none includes a separate **comment block** explaining the "why" and design invariants as required.

    - For example, `lockfile.py` should document *why* `O_CREAT | O_EXCL` was chosen over `fcntl.flock()` or `filelock` library, and what invariants must hold (single-writer, no NFS, stale-timeout assumption).

- **Fix:** add a `# ------` prefixed comment block above the docstring in each file, covering the required elements.

**#3 -- `extract_memories` silently skips topics without matching files (`hooks/post_session.py:35-37`)**

- When a preference is extracted with `topic="general"`, the code checks `topic_path.is_file()` before calling `append_raw_entry`.

    - If the topic file does not exist, the preference is silently discarded.
    - This means that if the data directory was initialized without a `topics/general.md` file, all "general" preferences are lost without any logging or warning.

- **Fix:** either create missing topic files on demand (with the standard `## Distilled` / `## Raw` skeleton), or log a warning when a preference is discarded.

    - The `initialize_data_dir` function in `wizard.py` creates the `topics/` directory but does not pre-create topic files, so this scenario is the default state for new installations.

**#4 -- No XML escaping on plist template values (`setup/launchd.py:66-74`)**

- `string.Template.substitute` performs raw string interpolation.

    - If any substituted value contains XML-special characters (`<`, `>`, `&`, `"`), the generated plist will be malformed.
    - For example, a `working_dir` path containing `&` would break the XML.

- While this is unlikely in practice for file paths, `assistant_name` (passed through from user input via the wizard) could contain special characters.
- **Fix:** apply `html.escape()` or `xml.sax.saxutils.escape()` to all substituted values before calling `substitute`.

### Consider

**#5 -- Fragile regex case handling in `_extract_preferences` (`hooks/post_session.py:63-69`)**

- Patterns use `(?:i|I)` to match both cases, but only for the first character.

    - A sentence starting with `"i LIKE pasta"` or `"I LIKE pasta"` would not match because `like` is expected lowercase.
    - The `re.MULTILINE` flag is passed to `re.finditer`, but `re.IGNORECASE` is not.

- **Suggestion:** pass `re.IGNORECASE | re.MULTILINE` to `re.finditer` and simplify the patterns by removing the explicit `(?:i|I)` alternation.

**#6 -- `BackgroundRunner` as a `@dataclass` with mutable behavior (`background/runner.py:30-82`)**

- `BackgroundRunner` is decorated with `@dataclass`, which conventionally signals a data-oriented type (record/value object).
- However, it has methods that mutate internal state (`mark_run`, `run_check`, `run_all_due`), making it a stateful service object.
- While Python does not enforce the distinction strictly, this could confuse readers expecting dataclass equality/hashing semantics.
- **Suggestion:** either use a plain class (removing `@dataclass`) or add `eq=False` to the decorator to signal that identity-based comparison is intended.

## Summary

**Verdict:** *Approve with changes* -- 1 must fix, 3 should fix, 2 consider.

- The infrastructure layer is well-designed with clean separation of concerns, healthy dependency direction, and good testability through injectable time parameters.
- The lockfile TOCTOU race (Finding #1) is the only correctness issue that requires a fix before production use.
- Template content is consistent and well-structured across all three template categories (attaches, prompts, huddles).
- Test coverage is thorough at 111 passing tests, though adding a concurrency test for the lockfile would be valuable.
