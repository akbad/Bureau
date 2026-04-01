# Dossier system: extension proposals

> Synthesized from three independent architect brainstorms (2026-04-01).
> Each architect was given a different lens: high-impact innovation,
> cross-agent workflows, and developer experience. Ideas that multiple
> architects independently converged on are marked with their convergence
> count.
>
> **Evaluation criteria:** high-signal (solves a real pain point),
> architecturally elegant (builds on the SQLite + CLI + SKILL.md
> foundation), feasible (days not months), and novel (not obvious).

#### Contents

- [Tier 1: High convergence, high impact](#tier-1-high-convergence-high-impact)
  - [E1. Event log with causal ordering](#e1-event-log-with-causal-ordering)
  - [E2. Heartbeat leases with dead-agent reclamation](#e2-heartbeat-leases-with-dead-agent-reclamation)
  - [E3. Session diff](#e3-session-diff)
  - [E4. Context budget planner](#e4-context-budget-planner)
- [Tier 2: High impact, unique insight](#tier-2-high-impact-unique-insight)
  - [E5. Reactive task DAG with auto-unblock](#e5-reactive-task-dag-with-auto-unblock)
  - [E6. Integrity verification](#e6-integrity-verification)
  - [E7. Operational dashboard](#e7-operational-dashboard)
  - [E8. Dossier garbage collection](#e8-dossier-garbage-collection)
  - [E9. Conflict fences](#e9-conflict-fences)
  - [E10. Causal artifacts with drift detection](#e10-causal-artifacts-with-drift-detection)
- [Tier 3: Novel, higher effort](#tier-3-novel-higher-effort)
  - [E11. Quorum gates](#e11-quorum-gates)
  - [E12. Scratch channels](#e12-scratch-channels)
  - [E13. Dossier merge](#e13-dossier-merge)
  - [E14. Cross-dossier federation](#e14-cross-dossier-federation)
  - [E15. Decision ledger](#e15-decision-ledger)
  - [E16. Dossier lineage graph](#e16-dossier-lineage-graph)
  - [E17. Session replay anchors](#e17-session-replay-anchors)
- [Summary matrix](#summary-matrix)
- [Recommended sequencing](#recommended-sequencing)


## Tier 1: High convergence, high impact

These ideas were independently proposed by multiple architects.
They represent the strongest signal for what the system needs next.


### E1. Event log with causal ordering

**Convergence:** 3/3 architects

**Pitch:** An append-only `events` table that records every mutation across all agents with Lamport timestamps, enabling time-travel debugging and conflict attribution.

**The problem:** When three agents work on the same dossier concurrently and something goes wrong -- a task was completed that should not have been, a decision was recorded with wrong rationale, a lock was force-released -- there is no audit trail. The `sessions` table records fold snapshots, but it misses all inter-fold mutations (claim, complete, add, update, lock/release). Debugging multi-agent coordination failures is currently impossible.

**Scenario:** Agent A claims task #3 and starts working. Agent B force-releases the dossier lock (mistakenly thinking it is stale), then claims task #3 itself. Both agents complete the task, but only B's work is correct. Without an event log, the orchestrator sees "task #3 completed" with no indication that it was double-claimed or that a forced lock release preceded the confusion.

**How it works:**

1. New `events` table:

    ```sql
    CREATE TABLE IF NOT EXISTS events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp    TEXT NOT NULL,
        agent        TEXT NOT NULL,
        event_type   TEXT NOT NULL,
        entity_type  TEXT,
        entity_id    INTEGER,
        old_value    TEXT,
        new_value    TEXT,
        lamport_clock INTEGER
    );
    ```

    Event types: `task.claim`, `task.complete`, `task.add`, `task.update`, `lock.claim`, `lock.release`, `session.fold`, `decision.add`.

2. Each agent maintains a Lamport counter: increment on every write, adopt any observed higher counter on read. This gives a partial causal order across agents without synchronized clocks.

3. Instrument every write function to append an event row inside the same transaction as the mutation. Zero additional round-trips.

4. New CLI subcommand:

    ```
    bureau-dossiers events <slug> [--since <timestamp>] [--agent <agent>] [--type <type>]
    ```

5. On unfold, optionally render a "recent events" section showing the last N mutations.

**Why it is genius:** Most multi-agent systems either log nothing (losing causal history) or use a centralized log server (adding infrastructure). This embeds causal ordering *inside the SQLite file itself*, making the dossier fully self-contained and portable. The Lamport clock is the simplest correct solution for partial ordering without requiring synchronized clocks -- a subtlety that 99% of agent frameworks get wrong by relying on wall-clock timestamps alone.

**Effort:** M

**Files affected:** `db.py` (schema), `tasks.py`, `lock.py`, `fold.py` (instrumentation), `cli.py` (subcommand), new `events.py`

**Foundation for:** E3 (session diff), E6 (integrity verification), E17 (replay anchors)


### E2. Heartbeat leases with dead-agent reclamation

**Convergence:** 2/3 architects

**Pitch:** Replace indefinite task claims with time-bounded leases that auto-expire, enabling the system to reclaim work from crashed, stalled, or abandoned agents without manual intervention.

**The problem:** When an agent crashes, its context window fills up, or the user kills a session, any locks and task claims it holds become orphaned. A subsequent orchestrator sees task #4 as `in_progress` owned by `worker-codex` and cannot tell whether that agent is still alive. The only recourse is manual `--force` release or `tasks update`. In a system designed for autonomous multi-agent coordination, this manual step is a critical gap.

**Scenario:** An orchestrator dispatches 4 workers at 2pm. Worker 3 hits a context limit and dies at 2:15pm, holding task #6 as `in_progress`. At 2:30pm, the orchestrator checks progress and sees task #6 still in progress. It waits. At 3pm, still waiting. With heartbeat leases, the system detects at 2:20pm (5-minute timeout) that worker 3 is dead and automatically resets task #6 to `pending`.

**How it works:**

1. Add `lease_expires_at TEXT` to both `tasks` and `metadata` tables.

2. `claim_task` accepts `lease_duration_seconds` (default: 3600). Sets `lease_expires_at = now + duration`. The CAS condition becomes:

    ```sql
    WHERE id = ? AND (status = 'pending'
      OR (status = 'in_progress' AND lease_expires_at < datetime('now')))
    ```

    Expired leases are automatically reclaimable -- no manual intervention.

3. New `bureau-dossiers tasks <slug> heartbeat --id <id>` extends the lease. Worker agents call this periodically.

4. `claim_lock` gets the same treatment: `--lease <seconds>` and a `heartbeat` subcommand under `lock`.

5. `list_tasks` and `unfold_dossier` annotate expired leases: `in_progress (lease expired 47m ago)`.

**Why it is genius:** Failure detection in distributed systems is one of the hardest problems. Most solutions require a central coordinator, gossip protocol, or heartbeat network. By embedding leases *into the SQLite file*, you get failure detection with zero additional infrastructure. Expired leases are reclaimed *lazily* -- the next `claim_task` call simply notices and takes ownership. This works perfectly with SQLite's single-writer model.

**Effort:** S-M

**Files affected:** `db.py` (schema), `tasks.py` (lease logic, heartbeat), `lock.py` (lease logic, heartbeat), `cli.py` (heartbeat subcommand, lease flags), `unfold.py` (expired lease annotation), `context.py` (expired lease warning)


### E3. Session diff

**Convergence:** 2/3 architects

**Pitch:** Show exactly what changed between two sessions -- tasks added/completed, decisions made, files touched -- so a resuming agent can skip the unchanged 90% and focus on the 10% that moved.

**The problem:** When a dossier accumulates 3+ sessions, the unfolding agent receives a wall of context that grows linearly. Most is unchanged between sessions. There is no way to answer "what changed since I last looked?" without manually diffing the entire dossier.

**Scenario:** An orchestrator folds, dispatches 3 workers, then unfolds to check progress. The dossier now has 4 sessions. The orchestrator needs to know: which tasks moved from `pending` to `completed`, what new decisions were added, whether any new tasks were created. Today, they must re-read everything and mentally diff.

**How it works:**

1. `--since-session <N>` flag on `bureau-dossiers unfold`. Queries for mutations between session N and current state.

2. For tasks: compare snapshot at session N against current state. Emit deltas: `Task #3: pending -> completed (by worker-codex)`, `Task #7: [new]`.

3. For decisions: show only those with `session_id > N`.

4. For file interactions: show only those from sessions after N.

5. Render the diff at the top of the unfold output, before the full state.

**Why it is genius:** This is the `git diff` insight applied to agent state. Every version control system learned that showing the *delta* is more useful than showing the *full state*. No multi-agent system does this for conversation persistence.

**Effort:** S-M

**Files affected:** `unfold.py` (rendering), `cli.py` (flag), new `diff.py`

**Enhanced by:** E1 (event log provides richer diff data)


### E4. Context budget planner

**Convergence:** 2/3 architects

**Pitch:** At unfold time, estimate the token cost of each dossier section and let the agent specify a budget, so the renderer produces the densest possible context that fits within a target window.

**The problem:** As dossiers accumulate sessions, unfold output grows unboundedly. An agent with a 200K context window cannot afford 50K of dossier context. Today the only knobs are `--full` (everything) and the default (omit digests). There is no awareness of how much context budget the dossier is consuming.

**How it works:**

1. Simple token estimator (4 chars per token, sufficient for planning).

2. Priority ordering: tasks > decisions > latest digest > file interactions > older digests. Higher-priority sections are never dropped before lower-priority ones.

3. `--budget <N>` flag: render all sections, compute estimates, prune from the bottom of the priority stack until the total fits.

4. Append a "context budget report" showing what was included, what was omitted, and the total estimate.

**Why it is genius:** This is "backpressure" from systems engineering applied to context engineering. Context windows are the bandwidth constraint of AI agents, but nobody treats them that way. By making context budgeting a first-class feature of the persistence layer, dossiers work correctly with any model -- from Haiku's 200K to Gemini's 1M -- without agent-side logic changes.

**Effort:** S

**Files affected:** `unfold.py` (budget-aware rendering), `cli.py` (`--budget` flag), optionally new `budget.py`


## Tier 2: High impact, unique insight

These were proposed by one architect but address clearly important problems.


### E5. Reactive task DAG with auto-unblock

**Pitch:** Replace the single `blocked_by` field with a proper dependency DAG, and automatically transition tasks from `blocked` to `pending` when their dependencies complete.

**The problem:** The current `blocked_by` is a single integer. Real plans have diamond dependencies: "task C depends on both A and B." Worse, when a blocking task completes, the blocked task stays `blocked` forever -- someone must manually update it.

**How it works:**

1. `task_dependencies` junction table: `(task_id, depends_on)`.

2. `--depends-on 3,5` flag on `tasks add` and `tasks update`.

3. In `complete_task`, after marking completed, run a trigger query that finds tasks whose ALL dependencies are now completed and transitions them to `pending`. This runs inside the same transaction -- atomic with the completion.

4. Update `_resolve_dependency_chain` for DAG traversal.

**Why it is genius:** The reactive unblocking is the key insight. Every other multi-agent task system requires the orchestrator to poll and manually unblock. By embedding the DAG *inside* the CAS transaction boundary, unblocking happens atomically at zero coordination cost. The orchestrator can fire-and-forget workers.

**Effort:** M

**Files affected:** `db.py` (schema), `tasks.py` (reactive unblock), `context.py` (DAG traversal), `cli.py` (flags), `fold.py` (migration)


### E6. Integrity verification

**Pitch:** A pre-unfold health check that validates the dossier is consistent and the resuming agent can trust it.

**The problem:** If a previous agent wrote a corrupt fold -- dangling `blocked_by` references, tasks stuck in `in_progress` with no lock, orphaned decisions -- the resuming agent inherits broken state and makes incorrect assumptions. The system has zero verification today.

**How it works:**

```
bureau-dossiers verify <slug> [--fix] [--format json|table]
```

Checks: schema version, task reference integrity, circular dependencies, stale in_progress tasks with no lock, decision session references, file interaction session references, lock coherence, metadata/filename consistency.

With `--fix`: auto-repair safe issues (reset stale locks, clear dangling refs).

**Why it is genius:** This is the missing "trust layer" between fold and unfold. An agent can tell the user "this dossier has a stale lock, should I force-release it?" instead of silently proceeding or failing with a cryptic error.

**Effort:** S-M

**Files affected:** `cli.py` (subcommand), new `verify.py`


### E7. Operational dashboard

**Pitch:** A single-command overview of all active dossiers -- the `kubectl get pods` moment for agent work streams.

**The problem:** `bureau-dossiers list` shows a flat table. It does not answer: which dossiers have stalled? Which have blocked tasks? Which are fully complete? With 5+ active dossiers, the developer must run `list`, then `tasks list` on each one, then mentally classify.

**How it works:**

```
bureau-dossiers dash [--format table|json]
```

Computes derived health status per dossier:

- `ACTIVE`: at least one task in_progress or last updated < 24h
- `COMPLETE`: all tasks completed (or no tasks)
- `STALE`: no in_progress tasks and last updated > configurable threshold
- `BLOCKED`: has blocked tasks with no in_progress tasks working on their blockers

Output includes per-dossier task summary and an overall summary line.

**Effort:** S-M

**Files affected:** `cli.py` (subcommand), new `dash.py`


### E8. Dossier garbage collection

**Pitch:** Identify abandoned, completed, and stale dossiers -- then help the developer decide what to archive, resume, or delete.

**The problem:** Dossiers accumulate. A developer using the system daily for a month will have 20-30 `.db` files. Some are completed, some abandoned, some have stale locks. There is no mechanism to distinguish "active and important" from "dead weight."

**How it works:**

```
bureau-dossiers gc [--dry-run] [--archive] [--unlock] [--stale-threshold 7d]
```

Classification logic mirrors E7's health states. `--archive` moves completed dossiers to `~/.config/bureau/dossiers/archive/`. `--unlock` force-releases stale locks. Both are non-destructive.

**Effort:** S-M

**Files affected:** `cli.py` (subcommand), new `gc.py`


### E9. Conflict fences

**Pitch:** File-level "fences" that let agents declare which paths they intend to modify, with collision detection at claim time rather than merge time.

**The problem:** Two agents claim different tasks and start editing. Because tasks have no declared file scope, nothing prevents both from editing `middleware.py`. The conflict is discovered only at git merge time -- by which point both agents have done substantial work.

**How it works:**

1. `fences` table: `(task_id, file_glob, agent, claimed_at, released_at)`.

2. When claiming a task: `--fence "src/auth/*.py" --fence "middleware.py"`. The claim checks active fences from other tasks using `fnmatch`. Overlaps fail with `FenceConflictError`.

3. On task completion, fences auto-release.

4. Fences are advisory -- `--force-fence` overrides, but the conflict is logged.

**Why it is genius:** This moves conflict detection from post-hoc (git merge) to pre-hoc (task claim). It is the spatial analog of what CAS does for temporal coordination.

**Effort:** M

**Files affected:** `db.py` (schema), new `fences.py`, `tasks.py` (claim integration), `context.py` (rendering), `cli.py` (flags), `errors.py`


### E10. Causal artifacts with drift detection

**Pitch:** Tasks declare what they *produced* (files, commits, snippets) with checksums, and downstream tasks know exactly what to consume. Drift is detected automatically.

**The problem:** When Agent B claims a task that was `blocked_by` task 3, it knows task 3 is complete -- but has no idea *what* task 3 produced, *where* the output landed, or *whether the output is still valid*.

**How it works:**

1. `artifacts` table: `(task_id, kind, ref, checksum, produced_at)`. Kinds: `file`, `commit`, `decision`, `snippet`.

2. On `tasks complete`: `--artifact file:/path/to/output.py --artifact commit:abc123f`. Artifacts are registered in the same transaction as completion.

3. `extract_task_context` renders dependency artifacts: file paths, commit hashes, checksums.

4. `bureau-dossiers verify <slug>` recomputes checksums and flags drift since production.

**Why it is genius:** This turns the dossier from a task tracker into a data-flow ledger. The causal chain is explicit, verifiable, and survives across sessions. Checksum-based drift detection is cheap and gives something no existing multi-agent framework offers: automated staleness detection across a DAG of agent outputs.

**Effort:** M

**Files affected:** `db.py` (schema), `tasks.py` (artifact registration), `context.py` (rendering), `cli.py` (complete `--artifact`, verify artifacts)


## Tier 3: Novel, higher effort

These are architecturally ambitious ideas that would make the system
uniquely powerful but require more design and implementation work.


### E11. Quorum gates

**Pitch:** Task completion gates that require N-of-M agents to independently approve before a task transitions to "completed."

**Scenario:** A security-sensitive schema migration requires both Claude (who implemented it) and Codex (who reviews it) to approve before the task is considered done.

**How it works:**

1. `quorum` column on tasks (default 1) and `approvals` table: `(task_id, agent, verdict, reason)`.

2. When `complete_task` is called on a quorum > 1 task, it inserts an `approve` row. If approval count reaches quorum, the task transitions. A `reject` verdict moves the task to `blocked` with the rejection reason.

3. `bureau-dossiers tasks <slug> approve --id <id>` and `reject --id <id> --reason "..."`.

**Effort:** M

**Files affected:** `db.py`, `tasks.py`, `cli.py`, `context.py`


### E12. Scratch channels

**Pitch:** Structured inter-agent messaging within a dossier -- scoped, tagged, read-tracked, auto-pruned.

**Scenario:** Agent A discovers that "the auth middleware uses a non-standard header format." Today, this finding goes into a task description (wrong semantics), `context_notes` (only visible to one task's owner), or the session digest (too late for agents currently running).

**How it works:**

1. `messages` table: `(from_agent, to_scope, body, tag, read_by, created_at)`. Scopes: `all`, `task:<id>`, `agent:<name>`. Tags: `warning`, `discovery`, `question`, `fyi`.

2. `bureau-dossiers msg <slug> send/read` CLI commands.

3. `extract_task_context` includes unread messages scoped to the target task.

4. Pruned on fold: messages older than 24h or read by all agents are deleted.

**Effort:** M

**Files affected:** `db.py`, new `messages.py`, `context.py`, `cli.py`, `fold.py` (pruning)


### E13. Dossier merge

**Pitch:** Three-way merge for forked dossiers, applying merge semantics to tasks, decisions, and metadata.

**The problem:** `fork` creates a one-way copy. When two agents fork and both produce valuable results, there is no way to recombine. One fork is abandoned. This is `git branch` without `git merge`.

**How it works:**

1. Three-way merge using the `parent` field as the common ancestor.

2. Tasks: compare by `updated_at`, flag conflicts when both sides modified. New tasks union-merged.

3. Decisions: union-merge with deduplication by `what + why`.

4. Sessions: append with "merged from" annotation.

5. `bureau-dossiers merge <source> <target> [--dry-run]`.

**Effort:** L

**Files affected:** new `merge.py`, `db.py`, `cli.py`, `unfold.py`


### E14. Cross-dossier federation

**Pitch:** Tasks in one dossier can declare dependencies on tasks in a different dossier. Completion of work in dossier A automatically unblocks work in dossier B.

**How it works:**

1. Extended `blocked_by` syntax: `<slug>:#<task-id>`.

2. Global `_federation.db` with `cross_references` table.

3. `complete_task` checks federation DB for cross-dossier dependents and triggers unblock.

4. `bureau-dossiers federation status` shows all cross-dossier links.

**Why it is genius:** Transforms dossiers from isolated records into a federated coordination substrate. The dossier directory *is* the distributed system, with each `.db` file as a node and `_federation.db` as the routing table.

**Effort:** M-L

**Files affected:** new `federation.py`, `tasks.py`, `context.py`, `cli.py`, `db.py`


### E15. Decision ledger

**Pitch:** A queryable, cross-dossier decision registry that prevents any agent from ever re-debating a settled question.

**How it works:**

1. Add `confidence` (`directive`/`agreed`/`inferred`) and `scope` (`dossier`/`project`/`global`) columns to `decisions`.

2. `bureau-dossiers decisions [--project <path>] [--scope project] [--search <term>]` scans all dossier DBs and renders a unified decision table.

**Effort:** M

**Files affected:** `db.py`, `fold.py`, `cli.py`, new `decisions.py`, `fold-dossier/SKILL.md`


### E16. Dossier lineage graph

**Pitch:** Cross-dossier parent-child-sibling relationship tracking with supersession warnings.

**How it works:**

1. Global `_lineage.db` with `edges` table: `(from_hash, to_hash, relation)`. Relations: `continues`, `forks`, `supersedes`, `merges`.

2. `fold_dossier` writes `continues` edges. `fork_dossier` writes `forks` edges. Manual `lineage link` for `supersedes`.

3. On unfold, check for supersession and warn.

4. `bureau-dossiers lineage <hash>` renders the ancestry graph.

**Effort:** M

**Files affected:** new `lineage.py`, `db.py`, `fold.py`, `fork.py`, `unfold.py`, `cli.py`


### E17. Session replay anchors

**Pitch:** Named coordination-state checkpoints for rollback without rewinding git.

**Scenario:** An agent makes a bad decision at step 3 of 10. You want to roll back coordination state to "right after task 4 completed but before task 5 started" without reverting code.

**How it works:**

1. `checkpoints` table: `(session_id, label, snapshot, created_at)`. Snapshot is JSON of task statuses, decision IDs, lock state.

2. `bureau-dossiers checkpoint <slug> --label "after-auth-refactor"` captures current state.

3. `bureau-dossiers checkpoint <slug> --restore <label>` resets coordination state from the snapshot. Does NOT touch git -- only resets tasks/decisions/locks.

4. Auto-checkpoint `pre-fold-<session-id>` on every fold.

**Why it is genius:** Separates *coordination state rollback* from *code state rollback*. One agent's failure should not invalidate another agent's completed work.

**Effort:** M

**Files affected:** `db.py`, new `checkpoint.py`, `fold.py`, `cli.py`


## Summary matrix

| # | Extension | Convergence | Effort | Impact | Moat depth |
|---|-----------|-------------|--------|--------|------------|
| E1 | Event log | 3/3 | M | Very high | Very high |
| E2 | Heartbeat leases | 2/3 | S-M | Very high | High |
| E3 | Session diff | 2/3 | S-M | High | Medium-high |
| E4 | Context budget | 2/3 | S | Medium-high | Medium |
| E5 | Reactive task DAG | 1/3 | M | Very high | High |
| E6 | Integrity verify | 1/3 | S-M | High | Medium |
| E7 | Dashboard | 1/3 | S-M | High | Medium |
| E8 | GC | 1/3 | S-M | Medium-high | Medium |
| E9 | Conflict fences | 1/3 | M | High | High |
| E10 | Causal artifacts | 1/3 | M | High | High |
| E11 | Quorum gates | 1/3 | M | Medium-high | Medium |
| E12 | Scratch channels | 1/3 | M | Medium-high | Medium |
| E13 | Dossier merge | 1/3 | L | High | Very high |
| E14 | Cross-dossier federation | 1/3 | M-L | High | Very high |
| E15 | Decision ledger | 1/3 | M | Medium-high | Medium |
| E16 | Lineage graph | 1/3 | M | Medium | Medium |
| E17 | Replay anchors | 1/3 | M | Medium | Medium |


## Recommended sequencing

The extensions form a natural dependency graph. Sequencing maximizes
early value while building toward the more ambitious capabilities.

### Wave 1: Foundation + quick wins (no schema changes for E4/E6/E7/E8)

| Extension | Why first |
|-----------|-----------|
| **E4** Context budget | Lowest effort, immediate daily utility, zero schema change |
| **E7** Dashboard | Transforms `list` from tool to command center, zero schema change |
| **E6** Integrity verify | Trust enabler, unblocks autonomous unfold, zero schema change |
| **E8** GC | Prevents system decay, zero schema change |

### Wave 2: Core coordination primitives

| Extension | Why now |
|-----------|---------|
| **E2** Heartbeat leases | Unblocks autonomous multi-agent operation (dead-agent recovery) |
| **E1** Event log | Observability foundation. Enables E3 to produce richer diffs |
| **E5** Reactive task DAG | Eliminates the largest source of coordination friction |

### Wave 3: Advanced coordination

| Extension | Why now |
|-----------|---------|
| **E3** Session diff | Builds on E1 event data for structured deltas |
| **E9** Conflict fences | Spatial coordination, prevents the most expensive class of wasted work |
| **E10** Causal artifacts | Data-flow provenance, drift detection |

### Wave 4: Multi-dossier + consensus

| Extension | Why now |
|-----------|---------|
| **E11** Quorum gates | Cross-model verification workflows |
| **E12** Scratch channels | Real-time inter-agent messaging |
| **E15** Decision ledger | Cross-dossier institutional memory |

### Wave 5: Architectural capstones

| Extension | Why now |
|-----------|---------|
| **E13** Dossier merge | Completes the branch-and-merge paradigm |
| **E14** Cross-dossier federation | Inter-project coordination substrate |
| **E16** Lineage graph | Temporal composition across dossier lifetimes |
| **E17** Replay anchors | Coordination-state rollback |
