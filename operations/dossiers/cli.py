"""CLI entry point for dossier operations."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .context import extract_task_context
from .db import _check_path_containment, list_reap_log, open_dossier_db, safe_db_path
from .errors import (
    AmbiguousQueryError,
    ConcurrentInstanceError,
    DossierNotFoundError,
    IdentityReapedError,
    LockConflictError,
    TaskAlreadyCompletedError,
    TaskDeletedError,
    TaskNotFoundError,
    TaskStateError,
)
from .fold import fold_dossier
from .identity import _orchestrator_agent_id
from .payload import check_fold_payload
from .registration import list_agents
from .unfold import unfold_dossier, list_dossiers, find_dossier
from .tasks import list_tasks, add_task, update_task, remove_task, claim_task, complete_task
from .lock import claim_lock, release_lock, get_lock_status
from .fork import fork_dossier


DEFAULT_DOSSIERS_DIR = Path(os.path.expanduser("~/.config/bureau/dossiers"))


def _get_dossiers_dir(args: argparse.Namespace) -> Path:
    return Path(args.dossiers_dir) if args.dossiers_dir else DEFAULT_DOSSIERS_DIR


def _resolve_agent(args_agent: str, slug: str, dossiers_dir: Path) -> tuple[str, str]:
    """Resolve a bare agent type to its deterministic agent_id; labels pass through.

    The ``:`` discriminator distinguishes the two modes:

      - Bare type (``claude-code``): open the dossier with identity, which runs
        `resolve_identity` *before* cleanup on the same connection (the C1
        ordering fix) and protects the agent's own row from reaping. The
        orchestrator id is deterministic, so it is recomputed here rather than
        threaded out of the context manager.
      - Worker label (``claude-code:worker-1:1743926400``): the id is the label
        itself, so there is nothing to compute — but the connect still happens,
        because that is what refreshes the worker's heartbeat and adopts its
        `cli_pid` before the reap runs (reg-A). Skipping it is what let an
        active worker be reaped on age alone. The prefix before the first ``:``
        is the agent_type.

    Every worker-reachable command (``unfold --worker``, ``tasks
    claim/update/complete``, ``lock claim/release``) funnels through here, so
    this one call site is the whole worker heartbeat surface.

    Returns ``(agent_id, agent_type)``.

    Raises:
        ConcurrentInstanceError: a live other instance of this type owns the
            slot (propagated from `resolve_identity` inside the connect).
    """
    if ":" in args_agent:
        with open_dossier_db(
            safe_db_path(dossiers_dir, slug), worker_agent_id=args_agent
        ):
            pass  # refresh + reap happen inside connect, in the correct order
        return args_agent, args_agent.split(":", 1)[0]
    with open_dossier_db(
        safe_db_path(dossiers_dir, slug), agent_type=args_agent, slug=slug
    ):
        pass  # resolve + reap happen inside connect, in the correct order
    return _orchestrator_agent_id(slug, args_agent), args_agent


def _relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to human-relative string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        if seconds < 604800:
            return f"{seconds // 86400}d ago"
        return f"{seconds // 604800}w ago"
    except (ValueError, TypeError):
        return iso_str


def _load_fold_input(args: argparse.Namespace) -> dict[str, Any]:
    """Load structured fold input from a file path or stdin.

    ``--input-file -`` follows standard Unix CLI behavior and reads the full
    JSON payload from stdin. This avoids shared scratch files when multiple
    agents fold concurrently.
    """
    if args.input_file == "-":
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            raise ValueError("stdin payload is required when using --input-file -")
        input_label = "stdin"
    else:
        input_path = Path(args.input_file)
        try:
            raw_input = input_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"failed to read input file {input_path}: {exc}") from exc
        input_label = str(input_path)

    try:
        return json.loads(raw_input)
    except JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {input_label}: {exc.msg}") from exc


def cmd_fold(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    dossiers_dir.mkdir(parents=True, exist_ok=True)

    input_data = _load_fold_input(args)

    # Report the payload contract before anything can exit early, so an agent
    # running a cached skill copy always learns what this version dropped.
    # Advisory only — the fold proceeds regardless (see payload.py, "Warn,
    # never reject"). Mode is decided by the payload's `slug`, matching
    # `fold_dossier`'s own `is_refold` predicate.
    for warning in check_fold_payload(
        input_data, is_refold=bool(input_data.get("slug"))
    ):
        print(f"Warning: {warning}", file=sys.stderr)

    name = input_data.get("name")
    slug = input_data.get("slug")
    agent = input_data.get("agent")
    project = input_data.get("project")
    branch = input_data.get("branch")
    commit = input_data.get("commit")
    digest = input_data.get("digest", "")
    if not digest and "digest_file" in input_data:
        digest_path = Path(input_data["digest_file"]).resolve()
        try:
            _check_path_containment(digest_path, dossiers_dir)
        except ValueError:
            print(f"Error: digest_file must be within the dossiers directory ({dossiers_dir})", file=sys.stderr)
            return 1
        digest = digest_path.read_text(encoding="utf-8")
    tasks = input_data.get("tasks")
    decisions = input_data.get("decisions")
    files = input_data.get("files")

    if not agent:
        print("Error: 'agent' is required in the JSON payload", file=sys.stderr)
        return 1

    result = fold_dossier(
        dossiers_dir=dossiers_dir,
        name=name,
        slug=slug,
        agent=agent,
        project=project,
        branch=branch,
        commit_hash=commit,
        digest=digest,
        tasks=tasks,
        decisions=decisions,
        files=files,
        max_retained_sessions=args.max_retained_sessions,
    )
    summary = (
        f"Dossier saved: `{result['slug']}` "
        f"({result['task_count']} tasks, {result['decision_count']} decisions)"
    )
    # surface destruction explicitly: retention is opt-in and unrecoverable,
    # so a fold that deleted rows must never look like one that did not
    if result["pruned_file_rows"]:
        summary += (
            f"\nPruned {result['pruned_file_rows']} file-interaction row(s) "
            f"outside the newest {args.max_retained_sessions} sessions."
        )
    print(summary)
    return 0


def _worker_framing(context_output: str, slug: str, task_id: int, agent: str) -> str:
    """Wrap task context in worker-mode directives for a single-task agent."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        "# Worker Agent Context\n"
        "\n"
        "> You are a **worker agent** assigned to a single task from a multi-agent\n"
        "> dossier. Your scope is strictly limited to the task below. You are NOT\n"
        "> an orchestrator.\n"
        ">\n"
        "> **Rules:**\n"
        "> - Complete ONLY the assigned task. Do not work on other tasks.\n"
        "> - Follow ALL decisions listed below. Do not re-propose rejected alternatives.\n"
        "> - When done, mark the task complete:\n"
        f">   `bureau-dossiers tasks {slug} complete --id {task_id}`\n"
        "> - Do not modify the dossier's task list (no adding, removing, or\n"
        ">   reordering) unless you discover blocking sub-work, in which case use:\n"
        f">   `bureau-dossiers tasks {slug} add --subject \"...\" --blocked-by {task_id}`\n"
        "> - If you encounter a blocker that prevents completion, update the task\n"
        ">   and report to the user:\n"
        f">   `bureau-dossiers tasks {slug} update --id {task_id} --status blocked`\n"
        "> - Do NOT acquire dossier-level locks. Your coordination primitive is the\n"
        ">   task claim, which has already been applied.\n"
    )
    confirmation = f"*Task #{task_id} claimed by {agent} at {now}. Dossier: '{slug}'*"
    return f"{header}\n{context_output}\n{confirmation}"


def cmd_unfold(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        # ── Validations (before any side effects) ──

        # C3: --claim requires --agent
        if getattr(args, "claim", False) and not args.agent:
            print("Error: --agent is required when using --claim", file=sys.stderr)
            return 1

        # worker-mode flag validations
        is_worker = getattr(args, "worker", False)
        if is_worker:
            if not args.agent:
                print("Error: --agent is required when using --worker", file=sys.stderr)
                return 1
            if not getattr(args, "task", None):
                print("Error: --task is required when using --worker", file=sys.stderr)
                return 1
            if getattr(args, "full", False):
                print("Error: --worker and --full are incompatible", file=sys.stderr)
                return 1
            if getattr(args, "claim", False):
                print("Error: --worker and --claim are incompatible", file=sys.stderr)
                return 1
            if getattr(args, "fork", False):
                print("Error: --worker and --fork are incompatible", file=sys.stderr)
                return 1

        # ── Worker mode: claim task + extract focused context ──
        if is_worker:
            slug = find_dossier(dossiers_dir, args.query).stem
            # resolve identity so worker labels register in `registrations`;
            # bare types (unusual in worker mode) also map to a unique id
            resolved_owner, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            claim_task(dossiers_dir, slug, args.task, resolved_owner)
            output = extract_task_context(
                dossiers_dir, slug, args.task,
                include_digest=getattr(args, "include_digest", False),
            )
            print(_worker_framing(output, slug, args.task, args.agent))
            return 0

        # Handle --fork: fork first, then unfold the fork
        if getattr(args, "fork", False):
            from .fork import fork_dossier
            fork_result = fork_dossier(dossiers_dir, find_dossier(dossiers_dir, args.query).stem)
            args.query = fork_result["hash"]

        # Handle --claim: acquire lock during unfold
        if getattr(args, "claim", False):
            from .lock import claim_lock
            slug = find_dossier(dossiers_dir, args.query).stem
            resolved_agent, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            claim_lock(dossiers_dir, slug, agent=resolved_agent)

        max_sessions = getattr(args, "max_sessions", 5) or 5
        output = unfold_dossier(dossiers_dir, args.query, max_sessions=max_sessions, full=getattr(args, "full", False))
        print(output)
        return 0
    except DossierNotFoundError:
        print(f'Error [not-found]: No dossier found matching "{args.query}". '
              f'Run `bureau-dossiers list` to see all dossiers.', file=sys.stderr)
        return 1
    except ConcurrentInstanceError as e:
        # subclass of LockConflictError — must be caught FIRST
        print(f"Error [concurrent-instance]: {e}", file=sys.stderr)
        return 1
    except LockConflictError as e:
        print(f"Error [lock-conflict]: {e}. Use --fork to create an independent copy.",
              file=sys.stderr)
        return 1
    except AmbiguousQueryError as e:
        print(f"Error [ambiguous]: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    results = list_dossiers(dossiers_dir)

    if args.format == "json":
        # enrich JSON output with computed relative timestamp
        for r in results:
            r["relative_updated_at"] = _relative_time(r["updated_at"])
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No dossiers found.")
            return 0
        print(f"{'Hash':<8} {'Name':<30} {'Branch':<20} {'Tasks':>5} {'Lock':<15} {'Updated'}")
        print("-" * 95)
        for r in results:
            lock = r['locked_by'] or 'unlocked'
            print(f"{r['hash']:<8} {r['name']:<30} {(r['branch'] or '—'):<20} "
                  f"{r['tasks']:>5} {lock:<15} {_relative_time(r['updated_at'])}")

    return 0


# task-command error → CLI tag, ordered most-specific first so a subclass
# (ConcurrentInstanceError < LockConflictError < ValueError) matches before its
# base. All task errors subclass ValueError, so one `except ValueError` at each
# call site funnels here and this dispatches to the right tag.
_TASK_ERROR_TAGS: list[tuple[type, str]] = [
    (ConcurrentInstanceError, "concurrent-instance"),
    (TaskNotFoundError, "task-not-found"),
    (IdentityReapedError, "identity-reaped"),
    (TaskAlreadyCompletedError, "already-completed"),
    (TaskDeletedError, "task-deleted"),
    (TaskStateError, "task-state"),
]


def _print_task_error(e: ValueError) -> int:
    """Print a task-command error to stderr with its ``[tag]`` and return 1.

    Maps the Mechanism 2 task errors (and `ConcurrentInstanceError` from identity
    resolution) to tagged messages so agents can branch on the failure cause; a
    plain `ValueError` falls through to an untagged message.
    """
    for cls, tag in _TASK_ERROR_TAGS:
        if isinstance(e, cls):
            print(f"Error [{tag}]: {e}", file=sys.stderr)
            return 1
    print(f"Error: {e}", file=sys.stderr)
    return 1


def cmd_tasks(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        slug = find_dossier(dossiers_dir, args.slug).stem
    except (DossierNotFoundError, AmbiguousQueryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    subcmd = args.tasks_command

    if subcmd == "list":
        tasks = list_tasks(dossiers_dir, slug)
        if not tasks:
            print("No tasks.")
            return 0
        print(f"{'ID':>4} {'Subject':<40} {'Status':<12} {'Owner':<15}")
        print("-" * 75)
        for t in tasks:
            print(f"{t['id']:>4} {t['subject']:<40} {t['status']:<12} {(t['owner'] or '—'):<15}")
            if getattr(args, "verbose", False) and t.get("description"):
                print(f"     {t['description']}")

    elif subcmd == "add":
        task_id = add_task(
            dossiers_dir, slug,
            subject=args.subject,
            description=args.description,
            status=args.status or "pending",
            owner=args.owner,
            blocked_by=args.blocked_by,
            context_notes=getattr(args, "context_notes", None),
        )
        print(f"Task #{task_id} created.")

    elif subcmd == "update":
        # resolve --agent only if provided; enables the worker-reassignment
        # CAS guard inside update_task (see tasks.py docstring)
        try:
            resolved_agent = None
            if getattr(args, "agent", None):
                resolved_agent, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            update_task(
                dossiers_dir, slug, task_id=args.id,
                subject=args.subject, status=args.status,
                owner=args.owner, blocked_by=args.blocked_by,
                context_notes=getattr(args, "context_notes", None),
                description=args.description,
                agent=resolved_agent,
            )
            print(f"Task #{args.id} updated.")
        except ValueError as e:
            return _print_task_error(e)

    elif subcmd == "remove":
        try:
            remove_task(dossiers_dir, slug, task_id=args.id)
            print(f"Task #{args.id} removed.")
        except ValueError as e:
            return _print_task_error(e)

    elif subcmd == "claim":
        try:
            resolved_owner, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            claim_task(dossiers_dir, slug, task_id=args.id, owner=resolved_owner)
            print(f"Task #{args.id} claimed by {args.agent}.")
        except ValueError as e:
            return _print_task_error(e)

    elif subcmd == "complete":
        try:
            resolved_agent = None
            if getattr(args, "agent", None):
                resolved_agent, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            complete_task(dossiers_dir, slug, task_id=args.id, agent=resolved_agent)
            print(f"Task #{args.id} completed.")
        except ValueError as e:
            return _print_task_error(e)

    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        slug = find_dossier(dossiers_dir, args.slug).stem
    except (DossierNotFoundError, AmbiguousQueryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    subcmd = args.lock_command

    if subcmd == "claim":
        try:
            resolved_agent, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            claim_lock(dossiers_dir, slug, agent=resolved_agent)
            print(f"Lock claimed by {args.agent}.")
        except ConcurrentInstanceError as e:
            print(f"Error [concurrent-instance]: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif subcmd == "release":
        try:
            # resolve --agent so a bare type released by the owning process
            # matches the resolved id stored in locked_by; --force bypasses
            resolved_agent = args.agent
            if args.agent and not args.force:
                resolved_agent, _ = _resolve_agent(args.agent, slug, dossiers_dir)
            release_lock(dossiers_dir, slug, agent=resolved_agent, force=args.force)
            print("Lock released.")
        except ConcurrentInstanceError as e:
            print(f"Error [concurrent-instance]: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif subcmd == "status":
        status = get_lock_status(dossiers_dir, slug)
        if status["locked_by"]:
            print(f"Locked by {status['locked_by']} since {status['locked_at']}")
        else:
            print("Unlocked.")

    return 0


def cmd_who(args: argparse.Namespace) -> int:
    """List all agents currently registered on a dossier.

    Workers are indented under orchestrators of the same ``agent_type`` for
    readability; timestamps are rendered relative (e.g. ``2h ago``).
    """
    dossiers_dir = _get_dossiers_dir(args)
    try:
        slug = find_dossier(dossiers_dir, args.slug).stem
    except (DossierNotFoundError, AmbiguousQueryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        agents = list_agents(conn)

    if not agents:
        print("No registered agents.")
        return 0

    print(f"{'Agent ID':<38} {'Type':<14} {'Role':<14} {'Last seen':<12} Since")
    # group workers under orchestrators of the same agent_type
    for ag in agents:
        prefix = "  " if ag["role"] == "worker" else ""
        line = (
            f"{prefix}{ag['agent_id']:<{38 - len(prefix)}} "
            f"{ag['agent_type']:<14} {ag['role']:<14} "
            f"{_relative_time(ag['last_heartbeat']):<12} "
            f"{_relative_time(ag['registered_at'])}"
        )
        print(line)
    return 0


def cmd_reap_log(args: argparse.Namespace) -> int:
    """Print the reap audit log for a dossier (Mechanism 3: post-hoc forensics).

    Read-only view over `reap_log`: answers "what got reaped, when, why, and
    which tasks reverted." `--since` / `--agent-type` filter the rows; `--format
    json` emits the full row (including `role`, `last_heartbeat`, `lock_released`)
    for downstream tooling.
    """
    dossiers_dir = _get_dossiers_dir(args)
    try:
        slug = find_dossier(dossiers_dir, args.slug).stem
    except (DossierNotFoundError, AmbiguousQueryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        entries = list_reap_log(
            conn,
            since=getattr(args, "since", None),
            agent_type=getattr(args, "agent_type", None),
        )

    if args.format == "json":
        print(json.dumps(entries, indent=2))
        return 0

    if not entries:
        print("No reaps recorded.")
        return 0

    # table mirrors the five spec columns; the full row is one `--format json` away
    print(f"{'reaped_at':<20} {'agent_id':<29} {'reason':<14} "
          f"{'stale_by':<10} tasks_reverted")
    for e in entries:
        stale_by = f"{e['stale_by_sec']}s"
        print(
            f"{e['reaped_at']:<20} {e['agent_id']:<29} {e['reap_reason']:<14} "
            f"{stale_by:<10} {e['tasks_reverted']}"
        )
    return 0


def cmd_fork(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        slug = find_dossier(dossiers_dir, args.slug).stem
        result = fork_dossier(dossiers_dir, slug, name=args.name)
        print(f"Forked: `{result['slug']}`")
        return 0
    except (DossierNotFoundError, AmbiguousQueryError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_context(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        slug = find_dossier(dossiers_dir, args.slug).stem
        output = extract_task_context(
            dossiers_dir, slug,
            task_id=args.task,
            include_digest=getattr(args, "include_digest", False),
        )
        if args.format == "json":
            # wrap markdown output in a JSON envelope for programmatic use
            print(json.dumps({"format": "markdown", "content": output}, indent=2))
        else:
            print(output)
        return 0
    except (DossierNotFoundError, AmbiguousQueryError):
        print(f'Error [not-found]: No dossier found matching "{args.slug}". '
              f'Run `bureau-dossiers list` to see all dossiers.', file=sys.stderr)
        return 1
    except ValueError as e:
        # task-not-found surfaces as ValueError from extract_task_context
        print(f"Error [task-not-found]: {e}", file=sys.stderr)
        return 1


def main() -> int:
    # Shared parent parser for --dossiers-dir so it can appear before or after subcommand
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--dossiers-dir", help="Override dossiers directory")

    parser = argparse.ArgumentParser(prog="dossiers", description="Bureau dossier CLI",
                                     parents=[parent_parser])
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fold
    p_fold = subparsers.add_parser("fold", help="Create or update a dossier",
                                   parents=[parent_parser])
    p_fold.add_argument(
        "--input-file", required=True,
        help="JSON file with all fold fields, or '-' to read from stdin",
    )
    p_fold.add_argument(
        "--max-retained-sessions", type=int, default=0,
        dest="max_retained_sessions",
        help=(
            "DESTRUCTIVE, opt-in: delete file-interaction rows for sessions "
            "older than the newest N. Default 0 (never delete). Unfold already "
            "windows its output, so this is only for reclaiming storage."
        ),
    )

    # unfold
    p_unfold = subparsers.add_parser("unfold", help="Render dossier for context injection",
                                     parents=[parent_parser])
    p_unfold.add_argument("query", help="Dossier hash or name to find")
    p_unfold.add_argument("--claim", action="store_true", help="Acquire advisory lock during unfold")
    p_unfold.add_argument("--agent", help="Agent name for --claim")
    p_unfold.add_argument("--fork", action="store_true", help="Fork the dossier, then unfold the fork")
    p_unfold.add_argument("--max-sessions", type=int, default=5, dest="max_sessions",
                          help="Max session digests to render (default: 5)")
    p_unfold.add_argument("--full", action="store_true", help="Include session digests in output")
    p_unfold.add_argument("--worker", action="store_true",
                          help="Worker mode: claim a task and get focused context")
    p_unfold.add_argument("--task", type=int, help="Task ID (required with --worker)")
    p_unfold.add_argument("--include-digest", action="store_true", dest="include_digest",
                          help="Include session digest in worker context")

    # list
    p_list = subparsers.add_parser("list", help="List all dossiers",
                                   parents=[parent_parser])
    p_list.add_argument("--format", choices=["table", "json"], default="table")

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="Task operations",
                                    parents=[parent_parser])
    p_tasks.add_argument("slug", help="Dossier slug or hash")
    tasks_sub = p_tasks.add_subparsers(dest="tasks_command", required=True)

    p_task_list = tasks_sub.add_parser("list", help="List tasks")
    p_task_list.add_argument("--verbose", "-v", action="store_true", help="Show task descriptions")

    p_task_add = tasks_sub.add_parser("add", help="Add a task")
    p_task_add.add_argument("--subject", required=True)
    p_task_add.add_argument("--description")
    p_task_add.add_argument("--status", default="pending")
    p_task_add.add_argument("--owner")
    p_task_add.add_argument("--blocked-by", dest="blocked_by")
    p_task_add.add_argument("--context-notes", dest="context_notes",
                            help="Context hints for worker agents (pass \"\" to clear)")

    p_task_update = tasks_sub.add_parser("update", help="Update a task")
    p_task_update.add_argument("--id", type=int, required=True)
    p_task_update.add_argument("--subject")
    p_task_update.add_argument("--status")
    p_task_update.add_argument("--owner")
    p_task_update.add_argument("--blocked-by", dest="blocked_by")
    p_task_update.add_argument("--context-notes", dest="context_notes",
                               help="Context hints for worker agents (pass \"\" to clear)")
    p_task_update.add_argument("--description", help="Update task description (pass empty string to clear)")
    p_task_update.add_argument(
        "--agent",
        help="Acting agent (bare type or worker label). Enables CAS guard "
        "for worker-reassignment transitions.",
    )

    p_task_remove = tasks_sub.add_parser("remove", help="Remove a task")
    p_task_remove.add_argument("--id", type=int, required=True)

    p_task_claim = tasks_sub.add_parser("claim", help="Claim a pending task (atomic)")
    p_task_claim.add_argument("--id", type=int, required=True)
    p_task_claim.add_argument("--agent", required=True)

    p_task_complete = tasks_sub.add_parser("complete", help="Complete an in-progress task (atomic)")
    p_task_complete.add_argument("--id", type=int, required=True)
    p_task_complete.add_argument(
        "--agent",
        help="Completing agent (bare type or worker label). If provided, a "
        "worker with zero remaining in-progress tasks is deregistered.",
    )

    # lock
    p_lock = subparsers.add_parser("lock", help="Advisory lock operations",
                                   parents=[parent_parser])
    p_lock.add_argument("slug", help="Dossier slug or hash")
    lock_sub = p_lock.add_subparsers(dest="lock_command", required=True)

    p_lock_claim = lock_sub.add_parser("claim", help="Claim lock")
    p_lock_claim.add_argument("--agent", required=True)

    p_lock_release = lock_sub.add_parser("release", help="Release lock")
    p_lock_release.add_argument("--agent", help="Verify caller identity before releasing")
    p_lock_release.add_argument("--force", action="store_true", help="Force release regardless of holder")
    lock_sub.add_parser("status", help="Check lock status")

    # who — list registered agents on a dossier
    p_who = subparsers.add_parser("who", help="List registered agents on a dossier",
                                  parents=[parent_parser])
    p_who.add_argument("slug", help="Dossier slug or hash")

    # reap-log — post-hoc forensics over the reap audit trail (Mechanism 3)
    p_reap_log = subparsers.add_parser(
        "reap-log", help="Show the registration reap audit log for a dossier",
        parents=[parent_parser],
    )
    p_reap_log.add_argument("slug", help="Dossier slug or hash")
    p_reap_log.add_argument("--since", help="Only reaps at or after this ISO-8601 timestamp")
    p_reap_log.add_argument("--agent-type", dest="agent_type",
                            help="Only reaps of this CLI type (e.g. claude-code)")
    p_reap_log.add_argument("--format", choices=["table", "json"], default="table",
                            help="Output format (default: table)")

    # fork
    p_fork = subparsers.add_parser("fork", help="Fork a dossier",
                                   parents=[parent_parser])
    p_fork.add_argument("slug", help="Source dossier slug or hash")
    p_fork.add_argument("--name", help="Name for the fork")

    # context — read-only task-scoped context extraction
    p_context = subparsers.add_parser("context", help="Extract task-scoped context",
                                      parents=[parent_parser])
    p_context.add_argument("slug", help="Dossier slug or hash")
    p_context.add_argument("--task", type=int, required=True, help="Task ID to extract context for")
    p_context.add_argument("--include-digest", action="store_true", dest="include_digest",
                           help="Include the latest session digest")
    p_context.add_argument("--format", choices=["markdown", "json"], default="markdown",
                           help="Output format (default: markdown)")

    args = parser.parse_args()

    commands = {
        "fold": cmd_fold,
        "unfold": cmd_unfold,
        "list": cmd_list,
        "tasks": cmd_tasks,
        "lock": cmd_lock,
        "who": cmd_who,
        "reap-log": cmd_reap_log,
        "fork": cmd_fork,
        "context": cmd_context,
    }

    return commands[args.command](args)
