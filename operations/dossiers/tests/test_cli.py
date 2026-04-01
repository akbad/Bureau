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
    tmp_path: Path,
    name: str = "Test",
    agent: str = "claude-code",
    digest: str = "Digest content.",
    tasks_json: str | None = None,
) -> tuple[subprocess.CompletedProcess, str]:
    """Helper: fold a dossier via CLI, return (result, slug)."""
    digest_file = tmp_path / "digest.md"
    digest_file.write_text(digest)
    cmd = [
        sys.executable, "-m", "operations.dossiers",
        "fold",
        "--name", name,
        "--agent", agent,
        "--digest-file", str(digest_file),
        "--dossiers-dir", str(dossiers_dir),
    ]
    if tasks_json:
        cmd += ["--tasks-json", tasks_json]
    result = subprocess.run(cmd, capture_output=True, text=True)
    slug = ""
    if result.returncode == 0:
        slug_match = _re.search(r"`([^`]+)`", result.stdout)
        if slug_match:
            slug = slug_match.group(1)
    return result, slug


class TestCliFold:
    def test_fold_creates_dossier(self, dossiers_dir: Path, tmp_path: Path):
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("Test digest content.")
        result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--name", "CLI Test",
                "--agent", "claude-code",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Dossier saved:" in result.stdout
        # Should have created a .db file
        db_files = list(dossiers_dir.glob("*.db"))
        assert len(db_files) == 1


class TestCliUnfold:
    def test_unfold_renders_context(self, dossiers_dir: Path, tmp_path: Path):
        # First, fold something
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("Important context here.")
        fold_result = subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold",
                "--name", "CLI Test",
                "--agent", "claude-code",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
        )
        assert fold_result.returncode == 0, fold_result.stderr
        # Extract slug from output: "Dossier saved: `<slug>` (..."
        import re as _re
        slug_match = _re.search(r"`([^`]+)`", fold_result.stdout)
        assert slug_match, f"Could not parse slug from: {fold_result.stdout}"
        slug = slug_match.group(1)

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

    def test_list_json_format(self, dossiers_dir: Path, tmp_path: Path):
        digest_file = tmp_path / "digest.md"
        digest_file.write_text("D.")
        subprocess.run(
            [
                sys.executable, "-m", "operations.dossiers",
                "fold", "--name", "Test", "--agent", "a",
                "--digest-file", str(digest_file),
                "--dossiers-dir", str(dossiers_dir),
            ],
            capture_output=True, text=True,
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

    def test_unfold_with_fork(self, dossiers_dir: Path, tmp_path: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir, tmp_path)
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

    def test_unfold_with_claim(self, dossiers_dir: Path, tmp_path: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir, tmp_path)
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

    def test_unfold_claim_without_agent_fails(self, dossiers_dir: Path, tmp_path: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir, tmp_path)
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

    def test_unfold_claim_conflict(self, dossiers_dir: Path, tmp_path: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir, tmp_path)
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

    def test_context_basic(self, dossiers_dir: Path, tmp_path: Path):
        tasks_json = json.dumps([
            {"subject": "Implement auth", "status": "pending"},
            {"subject": "Write tests", "status": "pending", "blocked_by": "1"},
        ])
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tmp_path, tasks_json=tasks_json,
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

    def test_worker_mode(self, dossiers_dir: Path, tmp_path: Path):
        tasks_json = json.dumps([
            {"subject": "Build API", "status": "pending"},
        ])
        fold_result, slug = _fold_via_cli(
            dossiers_dir, tmp_path, tasks_json=tasks_json,
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

    def test_worker_without_agent_fails(self, dossiers_dir: Path, tmp_path: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir, tmp_path)
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

    def test_worker_with_fork_fails(self, dossiers_dir: Path, tmp_path: Path):
        fold_result, slug = _fold_via_cli(dossiers_dir, tmp_path)
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
