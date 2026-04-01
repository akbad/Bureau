"""CLI entry point for dossier operations."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import extract_task_context
from .errors import AmbiguousQueryError, DossierNotFoundError, LockConflictError
from .fold import fold_dossier
from .unfold import unfold_dossier, list_dossiers, find_dossier
from .tasks import list_tasks, add_task, update_task, remove_task, claim_task, complete_task
from .lock import claim_lock, release_lock, get_lock_status
from .fork import fork_dossier


DEFAULT_DOSSIERS_DIR = Path(os.path.expanduser("~/.config/bureau/dossiers"))


def _get_dossiers_dir(args: argparse.Namespace) -> Path:
    return Path(args.dossiers_dir) if args.dossiers_dir else DEFAULT_DOSSIERS_DIR


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


def cmd_fold(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    dossiers_dir.mkdir(parents=True, exist_ok=True)

    # --input-file: single JSON blob with all fields (recommended)
    if args.input_file:
        input_data = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
        name = input_data.get("name", args.name)
        slug = input_data.get("slug", args.slug)
        agent = input_data.get("agent", args.agent)
        project = input_data.get("project", args.project)
        branch = input_data.get("branch", args.branch)
        commit = input_data.get("commit", args.commit)
        digest = input_data.get("digest", "")
        if not digest and "digest_file" in input_data:
            # restrict digest_file to the dossiers directory to prevent
            # a compromised agent from exfiltrating arbitrary files
            digest_path = Path(input_data["digest_file"]).resolve()
            if not str(digest_path).startswith(str(dossiers_dir.resolve())):
                print(f"Error: digest_file must be within the dossiers directory ({dossiers_dir})", file=sys.stderr)
                return 1
            digest = digest_path.read_text(encoding="utf-8")
        tasks = input_data.get("tasks")
        decisions = input_data.get("decisions")
        files = input_data.get("files")
    else:
        name = args.name
        slug = args.slug
        agent = args.agent
        project = args.project
        branch = args.branch
        commit = args.commit
        tasks = json.loads(args.tasks_json) if args.tasks_json else None
        decisions = json.loads(args.decisions_json) if args.decisions_json else None
        files = json.loads(args.files_json) if args.files_json else None

        # Read digest from file or stdin
        if args.digest_file:
            digest = Path(args.digest_file).read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            digest = sys.stdin.read()
        else:
            print("Error: --digest-file or --input-file required (or pipe via stdin)", file=sys.stderr)
            return 1

    if not agent:
        print("Error: --agent is required", file=sys.stderr)
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
    )
    print(f"Dossier saved: `{result['slug']}` ({result['task_count']} tasks, {result['decision_count']} decisions)")
    return 0


def _worker_framing(context_output: str, slug: str, task_id: int) -> str:
    """Wrap task context in worker-mode directives for a single-task agent."""
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
    return f"{header}\n{context_output}"


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
            # atomically claim the task
            claim_task(dossiers_dir, slug, args.task, args.agent)
            # extract and render focused context
            output = extract_task_context(
                dossiers_dir, slug, args.task,
                include_digest=getattr(args, "include_digest", False),
            )
            print(_worker_framing(output, slug, args.task))
            return 0

        # Handle --fork: fork first, then unfold the fork
        if getattr(args, "fork", False):
            from .fork import fork_dossier
            fork_result = fork_dossier(dossiers_dir, find_dossier(dossiers_dir, args.query).stem)
            args.query = fork_result["hash"]

        # Handle --claim: acquire lock during unfold
        if getattr(args, "claim", False):
            from .lock import claim_lock
            claim_lock(dossiers_dir, find_dossier(dossiers_dir, args.query).stem, agent=args.agent)

        max_sessions = getattr(args, "max_sessions", 5) or 5
        output = unfold_dossier(dossiers_dir, args.query, max_sessions=max_sessions, full=getattr(args, "full", False))
        print(output)
        return 0
    except DossierNotFoundError:
        print(f'Error [not-found]: No dossier found matching "{args.query}". '
              f'Run `bureau-dossiers list` to see all dossiers.', file=sys.stderr)
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
        update_task(
            dossiers_dir, slug, task_id=args.id,
            subject=args.subject, status=args.status,
            owner=args.owner, blocked_by=args.blocked_by,
            context_notes=getattr(args, "context_notes", None),
            description=args.description,
        )
        print(f"Task #{args.id} updated.")

    elif subcmd == "remove":
        remove_task(dossiers_dir, slug, task_id=args.id)
        print(f"Task #{args.id} removed.")

    elif subcmd == "claim":
        try:
            claim_task(dossiers_dir, slug, task_id=args.id, owner=args.agent)
            print(f"Task #{args.id} claimed by {args.agent}.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif subcmd == "complete":
        try:
            complete_task(dossiers_dir, slug, task_id=args.id)
            print(f"Task #{args.id} completed.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

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
            claim_lock(dossiers_dir, slug, agent=args.agent)
            print(f"Lock claimed by {args.agent}.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif subcmd == "release":
        try:
            release_lock(dossiers_dir, slug, agent=args.agent, force=args.force)
            print("Lock released.")
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
    p_fold.add_argument("--name", help="Dossier name (for new dossiers)")
    p_fold.add_argument("--slug", help="Existing dossier slug (for re-fold)")
    p_fold.add_argument("--agent", help="Agent identifier (required)")
    p_fold.add_argument("--project", help="Git repo root path")
    p_fold.add_argument("--branch", help="Current git branch")
    p_fold.add_argument("--commit", help="Short HEAD hash")
    p_fold.add_argument("--digest-file", help="Path to digest markdown file")
    p_fold.add_argument("--input-file", help="JSON file with all fold fields (recommended)")
    p_fold.add_argument("--tasks-json", help="JSON array of tasks")
    p_fold.add_argument("--decisions-json", help="JSON array of decisions")
    p_fold.add_argument("--files-json", help="JSON array of file interactions")

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

    p_task_remove = tasks_sub.add_parser("remove", help="Remove a task")
    p_task_remove.add_argument("--id", type=int, required=True)

    p_task_claim = tasks_sub.add_parser("claim", help="Claim a pending task (atomic)")
    p_task_claim.add_argument("--id", type=int, required=True)
    p_task_claim.add_argument("--agent", required=True)

    p_task_complete = tasks_sub.add_parser("complete", help="Complete an in-progress task (atomic)")
    p_task_complete.add_argument("--id", type=int, required=True)

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
        "fork": cmd_fork,
        "context": cmd_context,
    }

    return commands[args.command](args)
