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

import pytest


@pytest.fixture
def dossiers_dir(tmp_path: Path) -> Path:
    d = tmp_path / "dossiers"
    d.mkdir()
    return d


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
