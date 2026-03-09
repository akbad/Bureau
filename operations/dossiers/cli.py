"""CLI entry point for dossier operations."""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .fold import fold_dossier
from .unfold import unfold_dossier, list_dossiers, find_dossier
from .tasks import list_tasks, add_task, update_task, remove_task
from .lock import claim_lock, release_lock, get_lock_status
from .fork import fork_dossier


DEFAULT_DOSSIERS_DIR = Path(os.path.expanduser("~/.config/bureau/dossiers"))


def _get_dossiers_dir(args: argparse.Namespace) -> Path:
    return Path(args.dossiers_dir) if args.dossiers_dir else DEFAULT_DOSSIERS_DIR


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
            digest = Path(input_data["digest_file"]).read_text(encoding="utf-8")
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
    task_count = len(tasks) if tasks else 0
    decision_count = len(decisions) if decisions else 0
    print(f"Dossier saved: `{result['slug']}` ({task_count} tasks, {decision_count} decisions)")
    return 0


def cmd_unfold(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        # Handle --fork: fork first, then unfold the fork
        if getattr(args, "fork", False):
            from .fork import fork_dossier
            db_path = find_dossier(dossiers_dir, args.query)
            if not db_path:
                print(f"Error: No dossier found matching: {args.query}", file=sys.stderr)
                return 1
            fork_result = fork_dossier(dossiers_dir, db_path.stem)
            args.query = fork_result["hash"]

        # Handle --claim: acquire lock during unfold
        if getattr(args, "claim", False):
            from .lock import claim_lock
            db_path = find_dossier(dossiers_dir, args.query)
            if db_path:
                claim_lock(dossiers_dir, db_path.stem, agent=args.agent)

        max_sessions = getattr(args, "max_sessions", 5) or 5
        output = unfold_dossier(dossiers_dir, args.query, max_sessions=max_sessions)
        print(output)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    results = list_dossiers(dossiers_dir)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No dossiers found.")
            return 0
        print(f"{'Hash':<8} {'Name':<30} {'Branch':<20} {'Tasks':>5} {'Updated'}")
        print("-" * 80)
        for r in results:
            print(f"{r['hash']:<8} {r['name']:<30} {(r['branch'] or '—'):<20} {r['tasks']:>5} {r['updated_at']}")

    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    subcmd = args.tasks_command

    if subcmd == "list":
        tasks = list_tasks(dossiers_dir, args.slug)
        if not tasks:
            print("No tasks.")
            return 0
        print(f"{'ID':>4} {'Subject':<40} {'Status':<12} {'Owner':<15}")
        print("-" * 75)
        for t in tasks:
            print(f"{t['id']:>4} {t['subject']:<40} {t['status']:<12} {(t['owner'] or '—'):<15}")

    elif subcmd == "add":
        task_id = add_task(
            dossiers_dir, args.slug,
            subject=args.subject,
            description=args.description,
            status=args.status or "pending",
            owner=args.owner,
            blocked_by=args.blocked_by,
        )
        print(f"Task #{task_id} created.")

    elif subcmd == "update":
        update_task(
            dossiers_dir, args.slug, task_id=args.id,
            subject=args.subject, status=args.status,
            owner=args.owner, blocked_by=args.blocked_by,
        )
        print(f"Task #{args.id} updated.")

    elif subcmd == "remove":
        remove_task(dossiers_dir, args.slug, task_id=args.id)
        print(f"Task #{args.id} removed.")

    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    subcmd = args.lock_command

    if subcmd == "claim":
        try:
            claim_lock(dossiers_dir, args.slug, agent=args.agent)
            print(f"Lock claimed by {args.agent}.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif subcmd == "release":
        release_lock(dossiers_dir, args.slug)
        print("Lock released.")

    elif subcmd == "status":
        status = get_lock_status(dossiers_dir, args.slug)
        if status["locked_by"]:
            print(f"Locked by {status['locked_by']} since {status['locked_at']}")
        else:
            print("Unlocked.")

    return 0


def cmd_fork(args: argparse.Namespace) -> int:
    dossiers_dir = _get_dossiers_dir(args)
    try:
        result = fork_dossier(dossiers_dir, args.slug, name=args.name)
        print(f"Forked: `{result['slug']}`")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_show(args: argparse.Namespace) -> int:
    """Human-readable on-demand view (replaces auto-generated .md projection)."""
    dossiers_dir = _get_dossiers_dir(args)
    try:
        max_sessions = getattr(args, "max_sessions", 5) or 5
        output = unfold_dossier(dossiers_dir, args.query, max_sessions=max_sessions)
        print(output)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
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

    # list
    p_list = subparsers.add_parser("list", help="List all dossiers",
                                   parents=[parent_parser])
    p_list.add_argument("--format", choices=["table", "json"], default="table")

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="Task operations",
                                    parents=[parent_parser])
    p_tasks.add_argument("slug", help="Dossier slug")
    tasks_sub = p_tasks.add_subparsers(dest="tasks_command", required=True)

    tasks_sub.add_parser("list", help="List tasks")

    p_task_add = tasks_sub.add_parser("add", help="Add a task")
    p_task_add.add_argument("--subject", required=True)
    p_task_add.add_argument("--description")
    p_task_add.add_argument("--status", default="pending")
    p_task_add.add_argument("--owner")
    p_task_add.add_argument("--blocked-by", dest="blocked_by")

    p_task_update = tasks_sub.add_parser("update", help="Update a task")
    p_task_update.add_argument("--id", type=int, required=True)
    p_task_update.add_argument("--subject")
    p_task_update.add_argument("--status")
    p_task_update.add_argument("--owner")
    p_task_update.add_argument("--blocked-by", dest="blocked_by")

    p_task_remove = tasks_sub.add_parser("remove", help="Remove a task")
    p_task_remove.add_argument("--id", type=int, required=True)

    # lock
    p_lock = subparsers.add_parser("lock", help="Advisory lock operations",
                                   parents=[parent_parser])
    p_lock.add_argument("slug", help="Dossier slug")
    lock_sub = p_lock.add_subparsers(dest="lock_command", required=True)

    p_lock_claim = lock_sub.add_parser("claim", help="Claim lock")
    p_lock_claim.add_argument("--agent", required=True)

    lock_sub.add_parser("release", help="Release lock")
    lock_sub.add_parser("status", help="Check lock status")

    # fork
    p_fork = subparsers.add_parser("fork", help="Fork a dossier",
                                   parents=[parent_parser])
    p_fork.add_argument("slug", help="Source dossier slug")
    p_fork.add_argument("--name", help="Name for the fork")

    # show (on-demand human-readable view, replaces auto-generated .md)
    p_show = subparsers.add_parser("show", help="Render human-readable view",
                                   parents=[parent_parser])
    p_show.add_argument("query", help="Dossier hash or name")
    p_show.add_argument("--max-sessions", type=int, default=5, dest="max_sessions",
                        help="Max session digests to render (default: 5)")

    args = parser.parse_args()

    commands = {
        "fold": cmd_fold,
        "unfold": cmd_unfold,
        "list": cmd_list,
        "tasks": cmd_tasks,
        "lock": cmd_lock,
        "fork": cmd_fork,
        "show": cmd_show,
    }

    return commands[args.command](args)
