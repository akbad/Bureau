"""Tests for CLI entry point (integration tests).

Covers fold, unfold, list, and the M7 unfold extensions (--fork, --claim,
--worker) as well as the context sub-command.  All tests invoke the CLI
via subprocess to exercise argument parsing and exit codes end-to-end.
"""
import json
import re as _re
import subprocess
import sys
from pathlib import Path


def _fold_via_cli(
    dossiers_dir: Path,
    name: str = "Test",
    agent: str = "claude-code",
    digest: str = "Digest content.",
    tasks: list[dict[str, str]] | None = None,
    decisions: list[dict[str, str]] | None = None,
    files: list[dict[str, str]] | None = None,
    slug: str | None = None,
) -> tuple[subprocess.CompletedProcess, str]:
    """Helper: fold a dossier via CLI over structured stdin, return (result, slug)."""
    payload: dict[str, object] = {
        "agent": agent,
        "digest": digest,
        "tasks": tasks or [],
        "decisions": decisions or [],
        "files": files or [],
    }
    if slug:
        payload["slug"] = slug
    else:
        payload["name"] = name

    cmd = [
        sys.executable, "-m", "operations.dossiers",
        "fold",
        "--input-file", "-",
        "--dossiers-dir", str(dossiers_dir),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=json.dumps(payload),
    )
    slug = ""
    if result.returncode == 0:
        slug_match = _re.search(r"`([^`]+)`", result.stdout)
        if slug_match:
            slug = slug_match.group(1)
    return result, slug


def _run_cli(
    dossiers_dir: Path,
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run the dossiers CLI with a shared dossiers directory."""
    if not args:
        raise ValueError("at least one CLI argument is required")

    return subprocess.run(
        [
            sys.executable, "-m", "operations.dossiers",
            args[0],
            "--dossiers-dir", str(dossiers_dir),
            *args[1:],
        ],
        capture_output=True,
        text=True,
        input=input_text,
    )


def _seed_reap(
    dossiers_dir: Path,
    slug: str,
    *,
    reaped_at: str,
    agent_id: str,
    agent_type: str = "claude-code",
    tasks_reverted: str = "[]",
    lock_released: int = 0,
    reason: str = "pid_dead",
) -> None:
    """Insert a reap_log row directly — there is no write-CLI for the audit log."""
    from operations.dossiers.db import open_dossier_db, safe_db_path

    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO reap_log (reaped_at, agent_id, agent_type, role, "
                "last_heartbeat, stale_by_sec, tasks_reverted, lock_released, reap_reason) "
                "VALUES (?, ?, ?, 'orchestrator', '2026-01-01T00:00:00Z', 7200, ?, ?, ?)",
                (reaped_at, agent_id, agent_type, tasks_reverted, lock_released, reason),
            )


class TestCliFold:
    def test_fold_creates_dossier_from_structured_stdin(self, dossiers_dir: Path):
        result, _ = _fold_via_cli(
            dossiers_dir,
            name="CLI Test",
            digest="Test digest content.",
        )
        assert result.returncode == 0
        assert "Dossier saved:" in result.stdout
        # Should have created a .db file
        db_files = list(dossiers_dir.glob("*.db"))
        assert len(db_files) == 1

    def test_fold_refold_from_structured_stdin_appends_session(self, dossiers_dir: Path):
        first_result, slug = _fold_via_cli(
            dossiers_dir,
            name="CLI Test",
            digest="Session 1",
        )
        assert first_result.returncode == 0, first_result.stderr

        second_result, _ = _fold_via_cli(
            dossiers_dir,
            digest="Session 2",
            slug=slug,
        )
        assert second_result.returncode == 0, second_result.stderr

        unfold_result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--full",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert unfold_result.returncode == 0
        assert "Session 1" in unfold_result.stdout
        assert "Session 2" in unfold_result.stdout

    def test_fold_input_file_dash_requires_valid_json(self, dossiers_dir: Path):
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--input-file", "-",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True,
            text=True,
            input="{not json",
        )
        assert result.returncode == 1
        assert "invalid JSON" in result.stderr

    def test_fold_input_file_dash_requires_stdin_payload(self, dossiers_dir: Path):
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--input-file", "-",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True,
            text=True,
            input="",
        )
        assert result.returncode == 1
        assert "stdin payload is required" in result.stderr

    def test_fold_json_digest_file_outside_dossiers_dir_rejected(self, dossiers_dir: Path, tmp_path: Path):
        """digest_file in JSON input must be within the dossiers directory."""
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("sensitive content")
        payload = json.dumps({
            "name": "Test",
            "agent": "claude-code",
            "digest_file": str(outside_file),
            "tasks": [],
            "decisions": [],
            "files": [],
        })
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--input-file", "-",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
            input=payload,
        )
        assert result.returncode == 1
        assert "digest_file must be within the dossiers directory" in result.stderr

    def test_fold_json_digest_file_inside_dossiers_dir_accepted(self, dossiers_dir: Path):
        """digest_file within the dossiers directory is accepted."""
        digest_file = dossiers_dir / "fold-digest.md"
        digest_file.write_text("Digest from file.")
        payload = json.dumps({
            "name": "Test",
            "agent": "claude-code",
            "digest_file": str(digest_file),
            "tasks": [],
            "decisions": [],
            "files": [],
        })
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--input-file", "-",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
            input=payload,
        )
        assert result.returncode == 0
        assert "Dossier saved:" in result.stdout

    def test_fold_json_digest_file_symlink_to_outside_dir_rejected(self, dossiers_dir: Path, tmp_path: Path):
        """A symlink inside the dossiers dir must not bypass containment checks."""
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("sensitive content")
        digest_symlink = dossiers_dir / "digest-link.md"
        digest_symlink.symlink_to(outside_file)
        payload = json.dumps({
            "name": "Test",
            "agent": "claude-code",
            "digest_file": str(digest_symlink),
            "tasks": [],
            "decisions": [],
            "files": [],
        })

        result = _run_cli(
            dossiers_dir,
            "fold",
            "--input-file", "-",
            input_text=payload,
        )

        assert result.returncode == 1
        assert "digest_file must be within the dossiers directory" in result.stderr

    def test_fold_inline_digest_takes_precedence_over_digest_file(self, dossiers_dir: Path, tmp_path: Path):
        """An inline digest should bypass digest_file validation and content loading."""
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("outside content")
        payload = json.dumps({
            "name": "Test",
            "agent": "claude-code",
            "digest": "Inline digest wins.",
            "digest_file": str(outside_file),
            "tasks": [],
            "decisions": [],
            "files": [],
        })

        result = _run_cli(
            dossiers_dir,
            "fold",
            "--input-file", "-",
            input_text=payload,
        )

        assert result.returncode == 0
        slug = _re.search(r"`([^`]+)`", result.stdout).group(1)
        unfold_result = _run_cli(dossiers_dir, "unfold", slug, "--full")
        assert unfold_result.returncode == 0
        assert "Inline digest wins." in unfold_result.stdout
        assert "outside content" not in unfold_result.stdout


class TestCliUnfold:
    def test_unfold_renders_context(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(
            dossiers_dir,
            name="CLI Test",
            digest="Important context here.",
        )
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--full",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Important context here." in result.stdout


class TestCliList:
    def test_list_empty(self, dossiers_dir: Path):
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "list",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_list_json_format(self, dossiers_dir: Path):
        subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold", "--input-file", "-",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True,
            text=True,
            input=json.dumps({"name": "Test", "agent": "a", "digest": "D.", "tasks": [], "decisions": [], "files": []}),
        )
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "list", "--format", "json",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 1


class TestCliUnfoldFork:
    """M7: unfold --fork creates a fork then renders it."""

    def test_unfold_with_fork(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--fork",
                "--full",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        # fork creates a second .db file
        db_files = list(dossiers_dir.glob("*.db"))
        assert len(db_files) == 2
        # output contains the dossier content (digest in full mode)
        assert "Digest content." in result.stdout


class TestCliUnfoldClaim:
    """M7: unfold --claim acquires the advisory lock."""

    def test_unfold_with_claim(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--claim", "--agent", "test-agent",
                "--full",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Digest content." in result.stdout

        # verify lock is held (--dossiers-dir on the lock sub-command level)
        lock_result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "lock", "--dossiers-dir", str(dossiers_dir),
                slug, "status",
            ],
            capture_output=True, text=True,
        )
        assert "test-agent" in lock_result.stdout

    def test_unfold_claim_without_agent_fails(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--claim",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "--agent is required" in result.stderr

    def test_unfold_claim_conflict(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        # first claim succeeds
        subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--claim", "--agent", "agent-a",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )

        # second claim by different agent fails
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--claim", "--agent", "agent-b",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "[lock-conflict]" in result.stderr


class TestCliContext:
    """M7: context sub-command extracts task-scoped context."""

    def test_context_basic(self, dossiers_dir: Path):
        tasks = [
            {"subject": "Implement auth", "status": "pending"},
            {"subject": "Write tests", "status": "pending", "blocked_by": "1"},
        ]
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tasks=tasks,
        )
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "context", slug,
                "--task", "1",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Implement auth" in result.stdout
        # context includes sections for decisions, files, and sibling tasks
        assert "Decisions" in result.stdout
        assert "Key files" in result.stdout


class TestCliWorker:
    """M7: unfold --worker claims a task and renders focused context."""

    def test_worker_mode(self, dossiers_dir: Path):
        tasks = [
            {"subject": "Build API", "status": "pending"},
        ]
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tasks=tasks,
        )
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--worker", "--task", "1", "--agent", "worker-1",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        # worker framing directives present
        assert "Worker Agent Context" in result.stdout
        assert "Build API" in result.stdout

        # task should now be in_progress owned by worker-1
        task_result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "tasks", "--dossiers-dir", str(dossiers_dir),
                slug, "list",
            ],
            capture_output=True, text=True,
        )
        assert "in_progress" in task_result.stdout
        assert "worker-1" in task_result.stdout

    def test_worker_without_agent_fails(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--worker", "--task", "1",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "--agent is required" in result.stderr

    def test_worker_with_fork_fails(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "unfold", slug,
                "--worker", "--task", "1", "--agent", "x", "--fork",
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "incompatible" in result.stderr.lower()

    def test_worker_include_digest_renders_session_context(self, dossiers_dir: Path):
        tasks = [{"subject": "Build API", "status": "pending"}]
        fold_result, slug = _fold_via_cli(
            dossiers_dir,
            tasks=tasks,
            digest="Critical worker digest.",
        )
        assert fold_result.returncode == 0, fold_result.stderr

        result = _run_cli(
            dossiers_dir,
            "unfold", slug,
            "--worker", "--task", "1", "--agent", "worker-1", "--include-digest",
        )

        assert result.returncode == 0
        assert "## Session context" in result.stdout
        assert "Critical worker digest." in result.stdout

    def test_worker_excludes_session_context_by_default(self, dossiers_dir: Path):
        tasks = [{"subject": "Build API", "status": "pending"}]
        fold_result, slug = _fold_via_cli(
            dossiers_dir,
            tasks=tasks,
            digest="Critical worker digest.",
        )
        assert fold_result.returncode == 0, fold_result.stderr

        result = _run_cli(
            dossiers_dir,
            "unfold", slug,
            "--worker", "--task", "1", "--agent", "worker-1",
        )

        assert result.returncode == 0
        assert "## Session context" not in result.stdout
        assert "Critical worker digest." not in result.stdout

    def test_worker_include_digest_uses_latest_digest_only(self, dossiers_dir: Path):
        tasks = [{"subject": "Build API", "status": "pending"}]
        first_result, slug = _fold_via_cli(
            dossiers_dir,
            tasks=tasks,
            digest="Older digest.",
        )
        assert first_result.returncode == 0, first_result.stderr

        second_result, _ = _fold_via_cli(
            dossiers_dir,
            slug=slug,
            digest="Latest digest.",
        )
        assert second_result.returncode == 0, second_result.stderr

        result = _run_cli(
            dossiers_dir,
            "unfold", slug,
            "--worker", "--task", "1", "--agent", "worker-1", "--include-digest",
        )

        assert result.returncode == 0
        assert "Latest digest." in result.stdout
        assert "Older digest." not in result.stdout


class TestCliLock:
    """CLI coverage for lock release semantics."""

    def test_lock_release_without_agent_or_force_fails(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr
        claim_result = _run_cli(dossiers_dir, "lock", slug, "claim", "--agent", "agent-a")
        assert claim_result.returncode == 0, claim_result.stderr

        result = _run_cli(dossiers_dir, "lock", slug, "release")

        assert result.returncode == 1
        assert "--agent or --force is required" in result.stderr

    def test_lock_force_release_succeeds_for_other_agents_lock(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr
        claim_result = _run_cli(dossiers_dir, "lock", slug, "claim", "--agent", "agent-a")
        assert claim_result.returncode == 0, claim_result.stderr

        release_result = _run_cli(dossiers_dir, "lock", slug, "release", "--force")
        assert release_result.returncode == 0, release_result.stderr

        status_result = _run_cli(dossiers_dir, "lock", slug, "status")
        assert status_result.returncode == 0
        assert "Unlocked." in status_result.stdout


# ── v2 registrations: `who` + --agent flags on tasks ────────────────────


class TestCliWho:
    def test_who_empty_dossier(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir)
        assert fold_result.returncode == 0, fold_result.stderr

        result = _run_cli(dossiers_dir, "who", slug)
        assert result.returncode == 0, result.stderr
        assert "No registered agents." in result.stdout

    def test_who_lists_worker_registered_via_claim(self, dossiers_dir: Path):
        """Claiming a task with a worker label registers the worker."""
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tasks=[{"subject": "A"}]
        )
        assert fold_result.returncode == 0, fold_result.stderr

        worker = "claude-code:worker-1:42"
        claim_result = _run_cli(
            dossiers_dir, "tasks", slug, "claim", "--id", "1", "--agent", worker
        )
        assert claim_result.returncode == 0, claim_result.stderr

        result = _run_cli(dossiers_dir, "who", slug)
        assert result.returncode == 0, result.stderr
        assert worker in result.stdout
        assert "worker" in result.stdout
        assert "claude-code" in result.stdout


class TestCliTaskAgentFlag:
    def test_complete_with_agent_flag_deregisters_worker(self, dossiers_dir: Path):
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tasks=[{"subject": "A"}]
        )
        assert fold_result.returncode == 0, fold_result.stderr
        worker = "claude-code:worker-1:42"

        _run_cli(dossiers_dir, "tasks", slug, "claim", "--id", "1", "--agent", worker)
        _run_cli(
            dossiers_dir, "tasks", slug, "complete",
            "--id", "1", "--agent", worker,
        )

        # `who` no longer lists the worker — it was deregistered on complete
        result = _run_cli(dossiers_dir, "who", slug)
        assert result.returncode == 0, result.stderr
        assert worker not in result.stdout

    def test_update_status_pending_with_agent_enforces_cas(
        self, dossiers_dir: Path
    ):
        """Reassigning a completed task via --agent must fail with CAS guard."""
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tasks=[{"subject": "A"}]
        )
        assert fold_result.returncode == 0, fold_result.stderr
        worker = "claude-code:worker-1:42"

        _run_cli(dossiers_dir, "tasks", slug, "claim", "--id", "1", "--agent", worker)
        _run_cli(dossiers_dir, "tasks", slug, "complete", "--id", "1", "--agent", worker)

        # orchestrator attempts to revert the already-completed task; the rich
        # CAS dispatch surfaces the specific cause with its tag
        result = _run_cli(
            dossiers_dir, "tasks", slug, "update",
            "--id", "1", "--status", "pending",
            "--agent", "claude-code:orch-hex",
        )
        assert result.returncode != 0
        assert "[already-completed]" in result.stderr
        assert "already completed" in result.stderr

    def test_update_without_agent_is_unguarded(self, dossiers_dir: Path):
        """Legacy/manual path (no --agent) still allows status edits freely."""
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tasks=[{"subject": "A"}]
        )
        assert fold_result.returncode == 0, fold_result.stderr

        _run_cli(dossiers_dir, "tasks", slug, "claim", "--id", "1", "--agent", "claude-code:w:1")
        _run_cli(dossiers_dir, "tasks", slug, "complete", "--id", "1")

        # unguarded update (no --agent) may revert status — escape hatch
        result = _run_cli(
            dossiers_dir, "tasks", slug, "update",
            "--id", "1", "--status", "pending",
        )
        assert result.returncode == 0, result.stderr


class TestCliReapLog:
    """Mechanism 3: the `reap-log` forensics subcommand."""

    def test_reap_log_empty_dossier(self, dossiers_dir: Path):
        _fold_result, slug = _fold_via_cli(dossiers_dir)
        result = _run_cli(dossiers_dir, "reap-log", slug)
        assert result.returncode == 0, result.stderr
        assert "No reaps recorded." in result.stdout

    def test_reap_log_table_lists_entries(self, dossiers_dir: Path):
        _fold_result, slug = _fold_via_cli(dossiers_dir)
        _seed_reap(
            dossiers_dir, slug, reaped_at="2026-06-10T14:32:18Z",
            agent_id="claude-code:a7f3c2", tasks_reverted="[7, 8, 11]",
        )
        result = _run_cli(dossiers_dir, "reap-log", slug)
        assert result.returncode == 0, result.stderr
        assert "claude-code:a7f3c2" in result.stdout
        assert "pid_dead" in result.stdout
        assert "[7, 8, 11]" in result.stdout

    def test_reap_log_json_emits_full_row(self, dossiers_dir: Path):
        _fold_result, slug = _fold_via_cli(dossiers_dir)
        _seed_reap(
            dossiers_dir, slug, reaped_at="2026-06-10T14:32:18Z",
            agent_id="claude-code:a7f3c2", tasks_reverted="[7]", lock_released=1,
        )
        result = _run_cli(dossiers_dir, "reap-log", slug, "--format", "json")
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        entry = payload[0]
        assert entry["agent_id"] == "claude-code:a7f3c2"
        assert entry["tasks_reverted"] == [7]   # decoded, not a string
        assert entry["lock_released"] == 1       # full row, beyond the table cols
        assert entry["reap_reason"] == "pid_dead"

    def test_reap_log_agent_type_filter(self, dossiers_dir: Path):
        _fold_result, slug = _fold_via_cli(dossiers_dir)
        _seed_reap(
            dossiers_dir, slug, reaped_at="2026-06-01T00:00:00Z",
            agent_id="cc-orch", agent_type="claude-code",
        )
        _seed_reap(
            dossiers_dir, slug, reaped_at="2026-06-02T00:00:00Z",
            agent_id="cx-orch", agent_type="codex",
        )
        result = _run_cli(dossiers_dir, "reap-log", slug, "--agent-type", "codex")
        assert result.returncode == 0, result.stderr
        assert "cx-orch" in result.stdout
        assert "cc-orch" not in result.stdout
