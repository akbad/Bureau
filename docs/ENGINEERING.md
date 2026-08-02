# Engineering invariants

> Rules that constrain how Bureau changes. Every one was earned by a defect that shipped.

## Why this file exists

Bureau had no home for binding rules, and the cost is measurable:

- **Migration machinery decayed twice.** `_ensure_schema_current()` was implemented then deleted during the v3→v4 rework; `migrate_v3_to_v4` then gated on a moving constant. The second instance was found while preparing v5, one bump away from bricking every v4 database.
- **`bin/reset-protocols` was broken on Linux** for as long as it has existed, because `sed -i ''` is BSD-only. Nothing recorded that in-place editing needed a portable spelling.
- **A logging helper emitted invalid UTF-8**, because nothing recorded that `tr` cannot emit a multi-byte character.

A rule that lives only in a commit message, a review comment, or a sprint plan gets rediscovered the expensive way. Sprint plans are archived when the sprint closes; this file is not.

> An invariant without its incident gets deleted by someone who does not know why it is there. Every entry below carries the failure that produced it.

**Each entry states three things:** the rule, the incident that earned it, and what enforces it. If nothing enforces it, that is stated too, because an unenforced rule is a hope.

## Shell portability

Bureau ships to macOS (BSD userland) and runs in Linux containers (GNU userland). Anything in `bin/`, `tools/scripts/`, or `protocols/scripts/` must work on both. The failure mode is asymmetric and nasty: whichever platform the author used passes, and the other breaks silently or not at all.

### Never use `sed -i`

**Rule.** Use `_sed_inplace` from [`bin/lib/fs.sh`](../bin/lib/fs.sh). There is no spelling of `sed -i` that works on both platforms.

**Incident.** `bin/reset-protocols:102` used `sed -i '' <script> <file>`, the BSD form. GNU `sed` reads the empty string as a filename and exits 2, so the command failed outright on Linux. It was never noticed because the test that would have caught it had *copied the same broken line*.

**Enforcement.** `bin/lib/tests/test_fs.py` (13 tests). Not enforced against reintroduction: a new `sed -i` would pass CI. Grep for it in review.

`_sed_inplace` is also safer than `sed -i` on either platform, which is why it is the rule rather than a workaround:

| Property | What `sed -i` does instead |
| :--- | :--- |
| A failing script leaves the original untouched | can leave it truncated or half-rewritten |
| The replacement is atomic | a reader can observe a partial write |
| Permissions are preserved | a fresh temp installs its umask mode, silently widening a `0600` file |
| Symlinks are followed | the link is replaced by a regular file and silently detached |

Atomicity comes from staging the temp file **in the target's own directory**, so the final `mv` is a rename within one filesystem. A temp in `/tmp` would make it a cross-device copy and lose the guarantee.

### Never use `tr` to emit a non-ASCII character

**Rule.** Use bash parameter expansion for character repetition or substitution. `tr` is byte-oriented on both platforms.

**Incident.** `log_banner` built its divider with `printf '%*s' N "" | tr ' ' "━"`. POSIX `tr` truncates SET2 to SET1's length, so the 3-byte `━` collapsed to its first byte and every space became a bare `\xe2`. The helper wrote invalid UTF-8 to stdout, which took out 8 tests that read Bureau's output through `subprocess.run(..., text=True)`.

**Locale is not the cause and cannot be the fix.** GNU `tr` ignores `LC_ALL` here; verified identical under `C` and `C.UTF-8`. BSD `tr` appears to handle it in a UTF-8 locale, which is why this survived on macOS.

```bash
# WRONG: tr is byte-oriented; the multi-byte char is truncated to one byte
divider=$(printf '%*s' "$n" "" | tr ' ' "━")

# CORRECT: parameter expansion is character-aware, and drops a subprocess
printf -v divider '%*s' "$n" ""
divider=${divider// /"━"}
```

**Enforcement.** None automated. The three remaining `tr` call sites are `tr -d ' '` on ASCII and are fine.

### Anchor a relative path before handing it to any command

**Rule.** `[[ "$path" != /* ]] && path="./$path"`, once, before the path reaches `readlink`, `cp`, `mv`, `dirname`, or anything else that parses arguments.

**Incident.** While *fixing* the `sed` portability bug, `_sed_inplace` called `dirname "$file"` on a path beginning with `-`, and `dirname` rejected it as an option. The same option-parsing class the fix was guarding against, reintroduced one line below the guard.

**Why not `--`.** Per-command `--` guards would work on GNU, but BSD support for them cannot be verified from a Linux container, so relying on them trades a known bug for an unverifiable assumption. One normalization removes the need for `--` anywhere in the function.

**Enforcement.** `test_handles_a_path_beginning_with_a_dash`.

### Bound every loop that follows symlinks

**Rule.** Cap symlink resolution at 40 hops (the usual kernel `ELOOP` ceiling) and fail with a named error.

**Incident.** `_sed_inplace`'s `while [[ -L "$file" ]]` resolver spun forever on two links pointing at each other. `readlink -f` is GNU-only, so the portable resolver is a hand-rolled loop, and a hand-rolled loop has no natural termination.

**A setup script that hangs is worse than one that fails.** A failure is diagnosable and exits; a hang blocks the terminal and produces no signal.

**Enforcement.** `test_circular_symlink_fails_instead_of_hanging`, which runs under a `timeout`.

### A portability fix needs its own portability review

**Rule.** When fixing a cross-platform defect, treat the fix as new cross-platform surface. Give it its own tests rather than validating it only through the call site.

**Incident.** Both hazards above (the `dirname` option parsing and the unbounded symlink loop) were introduced *by* the `sed` fix, not by the bug it replaced. Neither would have surfaced from the four `reset-protocols` tests, which pass either way. Both were caught only because `_sed_inplace` got a test file of its own.

## Agent identity and liveness

Rules governing `operations/dossiers/` registration, reaping, and task ownership.

### Resolve identity before the reap, on the same connection

**Rule.** Every identity-bearing connect resolves the caller's identity *before* `_maybe_reap_stale_registrations` runs, on the same connection, and passes the resolved id as `protect_agent_id`. This holds for **both** roles: `resolve_identity` for orchestrators, `resolve_worker_identity` for workers.

**Incident (orchestrators).** The original C1 ordering bug: an agent's own connect could reap it before it identified itself.

**Incident (workers).** `reg-A`. `cli._resolve_agent` short-circuited on the `:` in a worker label and returned without touching the database, so a worker's `last_heartbeat` never moved after registration. Combined with a NULL `cli_pid`, the reap took the timestamp-only path and reverted active workers' in-progress tasks against a 2h TTL. Silent work loss, and strictly worse than the v2 bug it replaced.

**The load-bearing detail:** the worker path is the *counterpart* to the orchestrator path, not a parallel mechanism. Both connect paths now read identically. A third role, if one ever exists, gets the same shape.

**Enforcement.** `test_worker_connect_refreshes_its_own_heartbeat_before_the_reap`, `test_live_worker_survives_a_third_party_cleanup_connect`, and the orchestrator equivalents in `test_cleanup.py`.

### Liveness is the pid oracle, never idleness

**Rule.** Every registration row carries a real ancestor `cli_pid`. A row is reaped only when `_process_alive` proves its process dead. Elapsed time alone is never sufficient.

**Incident.** `claim_task` registered workers with `cli_pid = None`, so the liveness filter had nothing to ask and fell through to reaping on age. The fix records `_get_cli_process_pid()`, the same oracle orchestrators were always protected by.

**Accepted consequence, deliberately.** A worker abandoned by a *live* CLI is now protected until that CLI exits, where it previously reverted after the TTL. This is not a new policy; it is the orchestrator's existing semantics applied consistently. It trades a silent destructive failure (active work reverted mid-flight) for a visible repairable one (a stale `in_progress` row, cleared with `tasks update --status pending`).

**`cli_pid` writes are adoptions, not insert-time values.** Rows written before a fix heal on the agent's next call, so a defect in identity recording never needs a migration.

**Enforcement.** `TestWorkerLiveness` in `test_cleanup.py`, including two guard tests that pin what must be *preserved*: a worker whose CLI died is still reaped (`pid_dead`), and a pre-fix NULL row still reaps on timestamp.

### Prefer atomicity to ordering when the bad state is unrepairable

**Rule.** If interleaving two writes can produce a state nothing can repair, put them in one transaction. Reordering them only narrows the window.

**Incident.** `reg-B`. Fold committed `deregister_agent` inside the dossier context, then opened a second connection to release the lock. A failure in between left `registrations` empty while `metadata.locked_by` still named the deleted agent, and **cleanup can never repair that**: its cascade only iterates registration rows that still exist, so a lock whose holder has no row is invisible to it. `lock release --force` was the only way out.

The filed recommendation was to release before deregistering. Both writes were already on the same connection inside the same context, so one transaction was available and strictly better.

**Order still matters, for the rollback direction.** If only one write could survive, it must be the registration: cleanup reaps a stale registration on TTL, while an orphaned lock is terminal. Choose the ordering so the *recoverable* residue is the one left behind.

**Enforcement.** `TestRefoldExitAtomicity`, which includes a characterisation test that seeds an orphaned lock and proves three cleanup passes cannot clear it. That test passes before and after the fix; it exists to justify the cost of atomicity.

### A safety predicate gets one definition

**Rule.** When a conditional guard *is* the safety property, it gets exactly one definition. Do not copy the SQL to a second call site.

**Incident.** `reg-B`'s fix needed the lock release inside an existing transaction, which tempted an inline copy of `release_lock`'s `WHERE locked_by = ?` UPDATE. Two copies of a safety predicate is how they diverge, and a diverged safety predicate fails silently in exactly the case it exists to catch. Extracted as `release_lock_on_conn`, which `release_lock` now delegates to.

**Precedent in this repo.** The same reasoning produced the shared DDL constants in `db.py` and the single payload declaration in `payload.py`.

### Clearing half of a coupled state leaves the other half broken

**Rule.** When removing state that describes "who is working here", enumerate everything in that category first. Fixing one table and leaving its correlates is not a partial fix, it is a different bug.

**Incident.** `reg-D` was filed as "clear registrations on fork". Doing only that would have left the fork holding `in_progress` tasks whose owners are source-slug-derived ids with no registration row — which is precisely the unrepairable-orphan class `reg-B` had just eliminated, reintroduced through the fork path. `reap_log` was a third correlate, causing false `IDENTITY RESET` warnings citing events in another dossier.

**The rule that unifies them** was already stated for one member of the set: *a fork starts with nobody working on it*. The lock was simply the only piece of in-flight state anyone had remembered to clear.

**Enforcement.** `TestForkRegistrations` and `TestForkClearsInFlightState`, which also pin what must *not* change: completed and deleted tasks survive (a fork inherits history), and the source keeps everything.

### A test that seeds the corrupted state cannot see the corruption

**Rule.** A regression test must reach the defective state through the production path that creates it.

**Incident.** The first draft of the `reg-A` reproduction seeded a registration row with `cli_pid` set by hand, then asserted the worker survived. It passed *before* the fix, because it was exercising the reap logic (already correct) rather than `claim_task`'s NULL write (the actual bug). Rewriting it to register through `claim_task` made it fail correctly.

**Generalization.** If the bug is in what a writer writes, a test that writes the record itself has assumed away the defect. This is the same failure as over-mocking, one layer down.

## Schema migrations

### Gate every migration on a fixed literal version

**Rule.** A migration's version gate is a literal constant pinned to that migration (`_V4_TARGET_VERSION = 4`), never the moving `SCHEMA_VERSION`.

**Incident.** `migrate_v3_to_v4` gated on `SCHEMA_VERSION` in all three places. Bumping it to 5 would make every v4 database fail the gate (`4 >= 5` is false), fall into `DROP TABLE registrations`, hit `CREATE TABLE reap_log` → `already exists` → rollback, and then **raise on every connect**, writing a `.pre-v4.bak` per attempt. Found while preparing v5.

**This is the second decay of the same machinery.** The first was `_ensure_schema_current()`, implemented and then deleted during the v3→v4 rework, leaving no migration path for a `tasks` table predating `context_notes`. Two instances is a pattern, which is why it is a rule rather than a fixed bug.

**Enforcement.** The regression test in `test_db.py` pins both halves: registration rows survive, and the database is never stamped with a version whose migration did not run.

### Build fresh-create and migrate paths from shared DDL constants

**Rule.** Both paths construct schema from the same constants (`_CREATE_REGISTRATIONS`, `_CREATE_REAP_LOG`, ...), and a test diffs `sqlite_schema` between them.

**Why.** Divergence between the two is the classic silent-migration bug: a fresh install and an upgraded install end up with different schema, and only one of them is tested.

## The skill/CLI contract

`protocols/context/static/skills/` documents interfaces that `operations/` implements. Drift between them is invisible by construction, because the consumer is an agent that improvises around gaps rather than reporting them.

### The skill states the contract, never the mechanism

**Rule.** A skill describes what the agent must send, must not do itself, and must relay. It never describes how the CLI works internally. A mechanism claim has an expiry date; a contract statement does not.

**Incident.** The `r2-F2` retention fix left three stale behaviour claims in the skill it was meant to serve. `Prunes old file interactions beyond the retention window` was mechanism, and false the moment retention moved to render time. It became `A fold only ever appends`, which is contract, and permanent.

**Applied, this shrinks documents rather than growing them.** Step 8 stopped restating the confirmation-line format and now says to relay the CLI's output verbatim, which retired one undocumented output line and every future one at once.

**Enforcement.** A rule, not a detector. Prose drift has no key to diff. Two candidate mechanisms were considered and rejected: pinning documented output against the command's print statements (reproduces the manual-registration weakness it was meant to remove) and replacing the restatement with a pointer to `--help` (a `SKILL.md` is injected context read by an agent, not a manpage; a pointer costs a tool call and is silently skippable).

### Warn on unknown payload keys; never reject

**Rule.** A fold warns about keys it cannot persist and proceeds. Reject only when proceeding would produce a *wrong* write, never merely an incomplete one.

**Why the usual instinct is wrong here.** Strict validation with hard failure is the reflex, and it is inverted for this tool: Bureau ships, agents run cached skill copies at differing versions, and a rejected fold destroys the entire session context the command exists to preserve. Asymmetric consequences justify an asymmetric rule.

**Enforcement.** `operations/dossiers/payload.py` plus `test_payload_contract.py`.

### Contract drift has four surfaces, and a key diff catches one

**Rule.** When closing a drift defect, check all four surfaces. A top-level `set(input_data)` diff is necessary and nowhere near sufficient.

| # | Surface | Example | Caught by a top-level key diff? |
| :--- | :--- | :--- | :--- |
| 1 | Key sets, documented vs accepted | `r2-F1`, `G3` | **Yes** |
| 2 | Prose behaviour claims | `s1-A` | No: no key is involved |
| 3 | Mode-conditional handling | `r2-F4`, `s1-C` | No: the key is in *both* sets |
| 4 | Nested element schemas | `ff-slice3` | No: the diff cannot see into an array |

**Incident.** The original `G5` specification covered surface 1 while being described as "the fix that actually prevents recurrence". That was overclaiming: `context_notes` is a key on the task *element* object, and no top-level diff can see inside an array.

**Enforcement.** Surfaces 1, 3 and 4 are tested (`FOLD_PERSISTED_KEYS`/`FOLD_PENDING_KEYS`, `INERT_ON_REFOLD`, `ELEMENT_KEYS`). Surface 2 is the rule above.

## Diagnosis

### "It is the environment" is not a diagnosis until a command has falsified it

**Rule.** Before attributing a failure to the environment, run the command that would disprove it, and record the result.

**Incident.** The 13 `protocols/scripts` failures were recorded as "a locale problem in the environment, not a code defect" and that claim was committed to the sprint plan. Both halves were false. One `LC_ALL=C.UTF-8` run produced byte-identical broken output, which killed the hypothesis immediately, and the real cause was two portability bugs in Bureau's own code.

**The tell was already in the traceback:** it read `encoding = 'utf-8'`. Python was asking for the right codec and receiving bad bytes. A genuine locale fault looks like the opposite, valid bytes decoded with the wrong codec.

**Why this one matters more than its cost suggests.** "It is the environment" is unfalsifiable-sounding and it terminates investigation. It is the cheapest possible explanation and therefore the most expensive mistake.

### Establish the suite baseline before attributing a failure to your change

**Rule.** Run the full suite at `HEAD` with nothing applied, and compare. State the baseline in the progress log.

**Incident.** A sprint entry claimed "875 tests green across all six test directories". It did not reproduce; 13 were failing at that commit. Any later run would have had to guess whether it caused them.

**Note for this repo:** bare `pytest` collects roughly two thirds of the suite, because `pyproject.toml`'s `testpaths` omits `operations/dossiers/tests` and `bin/lib/tests`. The full run is:

```bash
uv run pytest bin/lib/tests operations/cleanup/tests operations/dossiers/tests \
    operations/tests protocols/scripts/tests tools/scripts/tests
```

### Verify a green test was ever red

**Rule.** For a regression test, revert the production change and confirm the test fails. For a guard test that pins preserved behaviour, state explicitly that it passes both before and after.

**Why.** A test written after the fix, or against hand-seeded state, can pass for reasons unrelated to the defect. Reverting is the only cheap proof that the test observes what it claims to.

**Incident.** Reverting the four `reg-A` production files confirmed 9 of the 11 new tests failed. The 2 that passed were the preservation guards, which is the correct outcome and worth recording so a later reader does not mistake them for dead tests.

## Adding to this file

Add an entry when a defect reveals a rule that would have prevented it, and the rule generalizes past the single call site you just fixed. Do not add an entry for a one-off bug with no transferable lesson.

Keep the three-part shape. The incident is not decoration: it is what stops a future contributor from deleting a rule whose cost is invisible.
