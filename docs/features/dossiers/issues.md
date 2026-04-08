# Dossier system: open issues

> [!IMPORTANT]
>
> Statuses (in the form of 1/2-liner `>` callouts) should be added under each
> issue's header and maintained accurately. Assume no status = todo/not done.

> Post-implementation findings from the final review sweep (2026-04-01).
> Five agents audited the system in parallel: architecture, concurrency,
> security, correctness, and SKILL/CLI coherence.
>
> **Predecessors:** `docs/FOLD-FIXES.md` (round 1, all resolved),
> `docs/FOLD-FIXES-2.md` (round 2, all resolved).

#### Contents

- [Blockers](#blockers)
  - [K1. `fold.py` bypasses `safe_db_path` on re-fold](#k1-foldpy-bypasses-safe_db_path-on-re-fold)
  - [K2. `unfold.py` crashes on NULL `decided_by`](#k2-unfoldpy-crashes-on-null-decided_by)
  - [K3. Fold SKILL tells agents to write digest to `/tmp/`](#k3-fold-skill-tells-agents-to-write-digest-to-tmp)
  - [K4. Unfold SKILL lock release example missing `--agent`](#k4-unfold-skill-lock-release-example-missing---agent)
  - [K5. CLI `--digest-file` arg bypasses P8 path restriction](#k5-cli---digest-file-arg-bypasses-p8-path-restriction)
- [Should-fix](#should-fix)
  - [S1. `safe_db_path` string-prefix bypass with sibling directories](#s1-safe_db_path-string-prefix-bypass-with-sibling-directories)
  - [S2. `create_dossier_db` connection not in try/finally](#s2-create_dossier_db-connection-not-in-tryfinally)
  - [S3. Fork backup connection not in try/finally](#s3-fork-backup-connection-not-in-tryfinally)
  - [S4. Lazy migration does not bump `user_version`](#s4-lazy-migration-does-not-bump-user_version)
  - [S5. Fold reads counts outside transaction block](#s5-fold-reads-counts-outside-transaction-block)
  - [S6. No status validation on initial fold task insertion](#s6-no-status-validation-on-initial-fold-task-insertion)
  - [S7. No field-length validation on initial fold task insertion](#s7-no-field-length-validation-on-initial-fold-task-insertion)
  - [S8. Worker mode output missing claim confirmation line](#s8-worker-mode-output-missing-claim-confirmation-line)
  - [S9. `escape_md` does not guard against non-string input](#s9-escape_md-does-not-guard-against-non-string-input)
- [Documentation gaps](#documentation-gaps)
  - [D1. `--context-notes` undocumented in SKILLs](#d1---context-notes-undocumented-in-skills)
  - [D2. `--description` on `tasks update` undocumented](#d2---description-on-tasks-update-undocumented)
  - [D3. `--verbose` on `tasks list` undocumented](#d3---verbose-on-tasks-list-undocumented)
  - [D4. Typed error tags undocumented](#d4-typed-error-tags-undocumented)
  - [D5. `--format` on `list` and `context` undocumented](#d5---format-on-list-and-context-undocumented)
  - [D6. `list` output columns mismatch in unfold SKILL](#d6-list-output-columns-mismatch-in-unfold-skill)
  - [D7. `--max-sessions` on `unfold` undocumented](#d7---max-sessions-on-unfold-undocumented)
- [Test coverage gaps](#test-coverage-gaps)
  - [T1. No tests for `safe_db_path`](#t1-no-tests-for-safe_db_path)
  - [T2. No tests for `escape_md`](#t2-no-tests-for-escape_md)
  - [T3. No tests for input validation limits](#t3-no-tests-for-input-validation-limits)
  - [T4. No tests for `release_lock` error paths](#t4-no-tests-for-release_lock-error-paths)
  - [T5. No test for `digest_file` path restriction](#t5-no-test-for-digest_file-path-restriction)
  - [T6. No test for worker mode `--include-digest`](#t6-no-test-for-worker-mode---include-digest)
  - [T7. No tests for deleted task visibility across rendering paths](#t7-no-tests-for-deleted-task-visibility-across-rendering-paths)
- [Priority matrix](#priority-matrix)
- [Implementation order](#implementation-order)
  - [Batch 1: Blockers](#batch-1-blockers)
  - [Batch 2: Tests](#batch-2-tests)


## Blockers

### K1. `fold.py` bypasses `safe_db_path` on re-fold

> **Status:** Fixed. Re-fold path now uses `safe_db_path(dossiers_dir, slug)`.

**Auditor:** Architecture (correctness sweep)

**Location:** `fold.py:63`

**Root cause:** When re-folding (`slug` is provided), the path is constructed as `dossiers_dir / f"{slug}.db"` without calling `safe_db_path()`. Every other module (`tasks.py`, `lock.py`, `context.py`, `fork.py`) uses `safe_db_path()` consistently. The P5 fix in FOLD-FIXES-2 specifically created `safe_db_path` to prevent path traversal, but `fold.py` was not updated.

**Impact:** A crafted `--slug ../../etc/cron.d/evil` on a re-fold command constructs a path outside the dossiers directory. While the `.db` suffix and existing-file check limit exploitability, this is a direct violation of the invariant P5 was designed to enforce.

**Solution:**

Replace line 63 with:

```python
db_path = safe_db_path(dossiers_dir, slug)
```


### K2. `unfold.py` crashes on NULL `decided_by`

> **Status:** Fixed. `escape_md` now guards against `None` input, returning `""`.

**Auditor:** Architecture (correctness sweep)

**Location:** `unfold.py:152`

**Root cause:** The decision rendering calls `escape_md(d['decided_by'])` without a null guard. The `decided_by` column is nullable in the schema (no NOT NULL constraint), and the fold JSON input uses `decision.get("decided_by")` which defaults to `None`. If an agent folds a decision without specifying `decided_by`, the subsequent unfold crashes with `TypeError: argument of type 'NoneType' is not iterable` inside `escape_md()`.

Compare with `context.py:302`, which correctly handles this: `escape_md(d["decided_by"]) if d["decided_by"] else "unknown"`.

**Impact:** Any dossier containing a decision without `decided_by` will fail to unfold entirely -- a crash on a primary read path.

**Solution:**

Apply the same guard as `context.py`:

```python
escape_md(d['decided_by']) if d['decided_by'] else 'unknown'
```


### K3. Fold SKILL tells agents to write digest to `/tmp/`

> **Fixed** (2026-04-06). SKILL now uses inline `"digest"` and pipes the full JSON payload to `bureau-dossiers fold --input-file -`, eliminating the shared `/tmp` staging file from the first-party fold path.

**Auditor:** SKILL/CLI coherence

**Location:** `fold-dossier/SKILL.md:232,249` and `cli.py:62-65`

**Root cause:** The fold SKILL instructs agents to write the digest to `/tmp/fold-digest.md` and reference it in the JSON input as `"digest_file": "/tmp/fold-digest.md"`. But the P8 fix restricted `digest_file` to the dossiers directory (`~/.config/bureau/dossiers`). Any agent following the SKILL instructions exactly will get:

```
Error: digest_file must be within the dossiers directory
```

**Impact:** Every fold operation that uses `digest_file` per SKILL instructions will fail.

**Solution:**

Update the fold SKILL to instruct agents to use the inline `"digest"` field in the JSON input instead of `"digest_file"`. The `digest_file` indirection exists for cases where the digest exceeds shell argument limits, but agents can write arbitrary-length JSON values inline. If `digest_file` must be kept, change the SKILL to write to `~/.config/bureau/dossiers/fold-digest-<slug>.md`.


### K4. Unfold SKILL lock release example missing `--agent`

> **Status:** Fixed. SKILL updated with `--agent <your-agent-id>` on lock release. Also added agent label convention for worker spawning (`<cli-type>:worker-<n>:<unix-timestamp>`) to prevent label collisions.

**Auditors:** Architecture (correctness sweep) + SKILL/CLI coherence

**Location:** `unfold-dossier/SKILL.md:318`

**Root cause:** The unfold SKILL documents the lock release command as:

```bash
bureau-dossiers lock <slug> release
```

But the B6 fix made `--agent` or `--force` required. Running the command without either flag raises `ValueError("--agent or --force is required to release a lock")`.

**Impact:** Every lock release attempt following the SKILL instructions will fail, leaving dossiers permanently locked until manual intervention.

**Solution:**

Update the SKILL to:

```bash
bureau-dossiers lock <slug> release --agent <your-agent-id>
```


### K5. CLI `--digest-file` arg bypasses P8 path restriction

> **Status:** Fixed. `--digest-file` CLI arg removed entirely (the fold SKILL now uses inline `"digest"` via `--input-file -`). The JSON-input `digest_file` fallback now uses the shared `_check_path_containment()` helper (`Path.is_relative_to()`). New tests cover both rejection (outside dossiers dir) and acceptance (inside dossiers dir).

**Auditor:** Architecture (correctness sweep)

**Location:** `cli.py:82-83`

**Root cause:** The P8 fix restricted `digest_file` in the JSON input path (`cli.py:62-65`) to the dossiers directory. However, when `--digest-file` is passed as a direct CLI argument (`cli.py:82-83`), no path restriction is applied. The file is read from any location on disk.

**Impact:** A compromised agent can exfiltrate arbitrary file contents into a dossier via `--digest-file /path/to/secret` when not using `--input-file`. The JSON path was hardened but the CLI argument path was missed.

**Solution:**

Apply the same dossiers-directory-scoped restriction to the CLI `--digest-file` path:

```python
if args.digest_file:
    digest_path = Path(args.digest_file).resolve()
    if not str(digest_path).startswith(str(dossiers_dir.resolve()) + "/"):
        print(f"Error: --digest-file must be within the dossiers directory ({dossiers_dir})",
              file=sys.stderr)
        return 1
    digest = digest_path.read_text(encoding="utf-8")
```


## Should-fix

### S1. `safe_db_path` string-prefix bypass with sibling directories

> **Status:** Fixed. All path containment checks replaced with a shared `_check_path_containment()` helper using `Path.is_relative_to()`, eliminating the string-prefix approach entirely.

**Auditor:** Architecture (correctness sweep)

**Location:** `db.py:28-30`

**Root cause:** The path containment check uses `str(path).startswith(str(dossiers_dir.resolve()))`. If `dossiers_dir` resolves to `/home/user/.config/bureau/dossiers` and a slug constructs a path to `/home/user/.config/bureau/dossiers-evil/file.db`, the string prefix check passes because the longer path starts with the shorter one.

**Impact:** Low in practice -- requires a sibling directory whose name starts with `dossiers`. But the standard secure pattern appends a path separator.

**Solution:**

```python
if not str(path).startswith(str(dossiers_dir.resolve()) + "/"):
```


### S2. `create_dossier_db` connection not in try/finally

> **Status:** Fixed. Connection body wrapped in try/finally.

**Auditor:** Architecture (correctness sweep)

**Location:** `db.py:119-123`

**Root cause:** `create_dossier_db()` uses raw `conn = sqlite3.connect(path)` / `conn.close()` without try/finally. If schema creation raises, the connection leaks. The P1 fix converted all other call sites to `open_dossier_db` but missed this one because it creates the DB file (the context manager's existence check would fail on a new file).

**Solution:**

```python
conn = sqlite3.connect(path)
try:
    conn.executescript(_SCHEMA_SQL)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
finally:
    conn.close()
```


### S3. Fork backup connection not in try/finally

> **Status:** Fixed. `dest_conn` wrapped in try/finally.

**Auditor:** Architecture (correctness sweep)

**Location:** `fork.py:38-40`

**Root cause:** `dest_conn = sqlite3.connect(dest_path)` is created, `source_conn.backup(dest_conn)` is called, then `dest_conn.close()` follows. If `backup()` raises, `dest_conn` leaks. The source connection is managed via `open_dossier_db`, but the destination is not.

**Solution:**

```python
dest_conn = sqlite3.connect(dest_path)
try:
    source_conn.backup(dest_conn)
finally:
    dest_conn.close()
```


### S4. Lazy migration does not bump `user_version`

> **Status:** Fixed. `PRAGMA user_version` now set to `SCHEMA_VERSION` after the `ALTER TABLE` succeeds.

**Auditor:** Architecture (correctness sweep)

**Location:** `db.py:127-144`

**Root cause:** When `_ensure_schema_current` adds `context_notes`, it does not update `PRAGMA user_version` to `SCHEMA_VERSION` (2). The column is added but the version marker stays at 1. On every subsequent connection, the migration code re-runs `PRAGMA table_info(tasks)`, finds `context_notes` present, and skips. Correct but wasteful.

More importantly, future migrations keyed on `user_version` will see version 1 and may mis-sequence upgrades.

**Solution:**

After the `ALTER TABLE` succeeds, within the same transaction:

```python
conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
```


### S5. Fold reads counts outside transaction block

**Auditor:** Architecture (correctness sweep)

**Location:** `fold.py:156-158`

**Root cause:** After the `with conn:` transaction block, two read queries fetch `task_count` and `decision_count`. These reads happen outside the transaction boundary. In WAL mode with concurrent agents, another agent could modify tasks or decisions between the commit and these reads.

**Impact:** Low -- the window is narrow and the counts are informational only. But the fold operation's output should reflect exactly what was committed.

**Solution:**

Move the count queries inside the `with conn:` block.


### S6. No status validation on initial fold task insertion

**Auditor:** Architecture (correctness sweep)

**Location:** `fold.py:104-117`

**Root cause:** When tasks are inserted during initial fold, the `status` field is taken directly from the input dict (`task.get("status", "pending")`). The `_validate_task_fields` function in `tasks.py` validates status against `VALID_STATUSES`, but `fold_dossier` does not call it. A fold with `{"subject": "x", "status": "INVALID"}` would store an invalid status that breaks CAS operations.

**Solution:**

Import `VALID_STATUSES` from `db.py` and validate each task's status during the initial fold loop:

```python
status = task.get("status", "pending")
if status not in VALID_STATUSES:
    raise ValueError(f"Invalid task status: {status}")
```


### S7. No field-length validation on initial fold task insertion

**Auditor:** Architecture (correctness sweep)

**Location:** `fold.py:104-117`

**Root cause:** Same path as S6: the initial fold task insertion does not validate `subject` length against `MAX_SUBJECT_LENGTH`. An extremely long subject (100KB+) would be stored and rendered on every unfold, wasting agent context tokens.

**Solution:**

Import `MAX_SUBJECT_LENGTH` and `MAX_DESCRIPTION_LENGTH` from `db.py` and validate during the fold loop. Or factor validation into a shared function called from both `fold.py` and `tasks.py`.


### S8. Worker mode output missing claim confirmation line

> **Status:** Fixed. `_worker_framing()` now appends the claim confirmation line with task ID, agent, timestamp, and slug.

**Auditor:** Architecture (correctness sweep)

**Location:** `cli.py:111-134`

**Root cause:** The FOLD-FIXES.md spec defines the worker-mode output as ending with a claim confirmation: `*Task #<id> claimed by <agent> at <timestamp>. Dossier: '<slug>'*`. The `_worker_framing()` function does not append this line.

**Impact:** Low -- the claim is implicit in the command succeeding. But the spec says it should be there, and it serves as useful confirmation for the worker agent's context.

**Solution:**

Append the confirmation line to `_worker_framing()` output, passing `agent`, `task_id`, and `slug` as parameters.


### S9. `escape_md` does not guard against non-string input

> **Status:** Fixed (by K2 fix). `escape_md` signature accepts `str | None`, returns `""` for `None`.

**Auditor:** Architecture (correctness sweep)

**Location:** `db.py:40-49`

**Root cause:** `escape_md()` assumes its input is always `str`. Most call sites have explicit null guards (`if value else 'fallback'`), but the K2 crash demonstrates what happens when a guard is missed. The function has no type annotation or defensive check.

**Impact:** K2 is the concrete manifestation. A defensive check would catch future slip-ups.

**Solution:**

Either add a type annotation and make callers responsible (current pattern, mostly followed), or add a coercion:

```python
def escape_md(text: str) -> str:
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    ...
```


## Documentation gaps

### D1. `--context-notes` undocumented in SKILLs

**Location:** `cli.py:428-429,437-438`

The `--context-notes` flag is available on both `tasks add` and `tasks update` but is not mentioned in either SKILL file. This flag provides context hints for worker agents and is rendered in `context` command output.


### D2. `--description` on `tasks update` undocumented

**Location:** `cli.py:424,439`

Both `tasks add` and `tasks update` support `--description`, but only `tasks add` is documented. The update subcommand's description support (including clearing via `--description ""`) is undocumented.


### D3. `--verbose` on `tasks list` undocumented

**Location:** `cli.py:420`

The `tasks list` command supports `--verbose` / `-v` to show task descriptions. Not mentioned in either SKILL.


### D4. Typed error tags undocumented

**Location:** `cli.py:204,208,212,359,364`

The CLI produces structured error tags (`[not-found]`, `[lock-conflict]`, `[ambiguous]`, `[task-not-found]`) that agents could parse for programmatic error handling. Neither SKILL documents these tags.


### D5. `--format` on `list` and `context` undocumented

**Location:** `cli.py:411,478`

Both `list` (supports `table`/`json`) and `context` (supports `markdown`/`json`) have `--format` options. Undocumented.


### D6. `list` output columns mismatch in unfold SKILL

**Location:** `unfold-dossier/SKILL.md:74` vs `cli.py:232`

The unfold SKILL describes the `list` output as containing "hash, name, branch, relative time, and lock status" (5 columns). The CLI actually outputs 6 columns: `Hash, Name, Branch, Tasks, Lock, Updated`. The `Tasks` count column is missing from the description. The example table also reflects the wrong column order.


### D7. `--max-sessions` on `unfold` undocumented

**Location:** `cli.py:399`

The `unfold` command supports `--max-sessions` (default 5) to control how many session digests are rendered in full mode. Not mentioned in the unfold SKILL.


## Test coverage gaps

### T1. No tests for `safe_db_path`

No test exercises the path traversal protection:
- A slug containing `../` being rejected
- A slug resolving within the dossiers directory being accepted
- Edge cases like slugs with special characters


### T2. No tests for `escape_md`

No test exercises the markdown escaping function:
- Each control character being escaped
- Content with multiple control characters
- Empty string input


### T3. No tests for input validation limits

No test exercises `MAX_SUBJECT_LENGTH`, `MAX_DESCRIPTION_LENGTH`, `MAX_DIGEST_LENGTH`, `MAX_TASKS_PER_DOSSIER`, `MAX_CONTEXT_NOTES_LENGTH`, or `VALID_STATUSES`:
- Oversized digest rejected in `fold_dossier`
- Oversized task list rejected in `fold_dossier`
- Oversized subject rejected in `add_task`
- Invalid status rejected in `update_task`


### T4. No tests for `release_lock` error paths

Missing tests for:
- `release_lock` without `--agent` or `--force` raises ValueError
- `release_lock` with wrong `--agent` raises ValueError
- `release_lock --force` succeeds for a different agent's lock
- `release_lock` on an unlocked dossier with `--agent`


### T5. No test for `digest_file` path restriction

> **Status:** Fixed. Two tests added: rejection of `digest_file` outside the dossiers directory, and acceptance of `digest_file` within it.

The JSON-input-file path restriction for `digest_file` has no test coverage. A regression would silently re-enable arbitrary file reads.


### T6. No test for worker mode `--include-digest`

No test verifies that `--include-digest` on unfold in worker mode actually causes the session digest to appear in the output.


### T7. No tests for deleted task visibility across rendering paths

No test verifies that a deleted task:
- Does not appear in `unfold_dossier` output
- Does not appear in `extract_task_context` sibling list
- Is excluded from `list_dossiers` task count


## Priority matrix

| Priority | ID | Issue | Effort |
|----------|----|-------|--------|
| **Blocker** | K1 | `fold.py` bypasses `safe_db_path` | Trivial |
| **Blocker** | K2 | `unfold.py` crashes on NULL `decided_by` | Trivial |
| **Blocker** | K3 | Fold SKILL `digest_file` path mismatch | Low |
| **Blocker** | K4 | Unfold SKILL lock release missing `--agent` | Trivial |
| **Blocker** | K5 | CLI `--digest-file` bypasses P8 | Low |
| **Should-fix** | S1 | `safe_db_path` prefix bypass | Trivial |
| **Should-fix** | S2 | `create_dossier_db` connection leak | Trivial |
| **Should-fix** | S3 | Fork backup connection leak | Trivial |
| **Should-fix** | S4 | Lazy migration `user_version` | Trivial |
| **Should-fix** | S5 | Fold counts outside transaction | Trivial |
| **Should-fix** | S6 | No fold task status validation | Low |
| **Should-fix** | S7 | No fold task length validation | Low |
| **Should-fix** | S8 | Worker claim confirmation missing | Trivial |
| **Should-fix** | S9 | `escape_md` non-string guard | Trivial |
| **Docs** | D1-D7 | SKILL documentation gaps | Low |
| **Tests** | T1-T7 | Coverage for hardening features | Medium |


## Implementation order

### Batch 1: Blockers

All trivial/low effort. Can be parallelized by file:

| Stream | Items | Files |
|--------|-------|-------|
| **A** | K1 (safe_db_path in fold) + S5 (counts inside txn) + S6 + S7 (fold validation) | `fold.py` |
| **B** | K2 (decided_by null guard) + S9 (escape_md guard) | `unfold.py`, `db.py` |
| **C** | K5 (CLI digest-file restriction) + S8 (worker confirmation) | `cli.py` |
| **D** | K3 (fold SKILL digest path) + K4 (unfold SKILL lock release) + D1-D7 (all docs) | `fold-dossier/SKILL.md`, `unfold-dossier/SKILL.md` |
| **E** | S1 (prefix bypass) + S2 (create_dossier_db) + S4 (user_version) | `db.py` |
| **F** | S3 (fork backup) | `fork.py` |

### Batch 2: Tests

After all fixes land:

- T1-T7: unit tests for `safe_db_path`, `escape_md`, input validation, lock error paths, digest restriction, `--include-digest`, deleted task visibility
