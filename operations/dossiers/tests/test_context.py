"""Tests for task-scoped context extraction.

Covers the core extraction logic in context.py: basic rendering,
dependency chain resolution (transitive, cycles, dangling references,
malformed values), digest inclusion, and task-not-found error handling.
"""
from pathlib import Path

import pytest

from operations.dossiers.context import extract_task_context
from operations.dossiers.findings import finding_hash
from operations.dossiers.fold import fold_dossier
from operations.dossiers.tasks import add_task, update_task, claim_task


# ─────────────────────────────────────────────────────────────────────
# Basic extraction
# ─────────────────────────────────────────────────────────────────────

class TestBasicExtraction:
    def test_renders_task_with_description(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test Project", agent="a",
            digest="Session digest content.",
            project="/code/proj", branch="main", commit_hash="abc123",
            tasks=[{
                "subject": "Implement feature X",
                "description": "Add retry logic with exponential backoff",
                "status": "pending",
            }],
            decisions=[{
                "what": "Use SQLite",
                "why": "Embedded, zero config",
                "alternatives": ["Postgres", "MySQL"],
                "decided_by": "danny",
            }],
            files=[{
                "path": "/code/proj/src/main.py",
                "action": "modified",
                "annotation": "added retry loop",
            }],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        # header
        assert "# Task Context: Implement feature X" in output
        assert "`Test Project`" in output
        assert "`main`" in output

        # task detail table
        assert "| ID | 1 |" in output
        assert "| Subject | Implement feature X |" in output
        assert "| Status | pending |" in output
        assert "| Owner | unassigned |" in output

        # description rendered as paragraph
        assert "Add retry logic with exponential backoff" in output

        # decisions included unconditionally
        assert "**Use SQLite**" in output
        assert "*(rejected: Postgres, MySQL)*" in output
        assert "*(decided by: danny)*" in output

        # file interactions
        assert "`/code/proj/src/main.py`" in output
        assert "modified" in output

        # session digest NOT included by default
        assert "Session digest content." not in output

    def test_renders_task_without_description(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Bare", agent="a",
            digest="D.",
            tasks=[{"subject": "Simple task", "status": "pending"}],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "# Task Context: Simple task" in output
        # no description paragraph — just the table
        assert "## Dependencies" in output

    def test_renders_sibling_tasks(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Multi", agent="a",
            digest="D.",
            tasks=[
                {"subject": "Task A", "status": "pending"},
                {"subject": "Task B", "status": "in_progress"},
                {"subject": "Task C", "status": "completed"},
            ],
        )
        # extract context for task #2 — siblings are #1 and #3
        output = extract_task_context(tmp_path, result["slug"], task_id=2)

        assert "## Other tasks in this dossier" in output
        assert "| 1 | Task A | pending |" in output
        assert "| 3 | Task C | completed |" in output
        # task #2 should NOT be in the sibling table
        assert "| 2 |" not in output.split("## Other tasks")[1]

    def test_sibling_table_omits_deleted_tasks(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """Deleted siblings should not appear in task context output."""
        result = make_dossier_with_deleted_tasks(
            name="Multi",
            tasks=[
                {"subject": "Target task", "status": "pending"},
                {"subject": "Live sibling", "status": "in_progress"},
                {"subject": "Deleted sibling", "status": "completed"},
            ],
            delete_ids=(3,),
        )

        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "| 2 | Live sibling | in_progress |" in output
        assert "Deleted sibling" not in output

    def test_deleted_siblings_yield_no_other_tasks_message(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """The sibling empty state should trigger once only deleted siblings remain."""
        result = make_dossier_with_deleted_tasks(
            name="Multi",
            tasks=[
                {"subject": "Target task", "status": "pending"},
                {"subject": "Deleted sibling", "status": "completed"},
            ],
            delete_ids=(2,),
        )

        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "No other tasks." in output
        assert "Deleted sibling" not in output


# ─────────────────────────────────────────────────────────────────────
# Dependency chain resolution
# ─────────────────────────────────────────────────────────────────────

class TestDependencyChain:
    def test_resolves_single_dependency(self, tmp_path: Path):
        """Task B blocked_by task A => dependency table shows A."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Deps", agent="a",
            digest="D.",
            tasks=[
                {"subject": "Task A", "status": "completed"},
                {"subject": "Task B", "status": "pending", "blocked_by": "1"},
            ],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=2)

        assert "These tasks were completed before yours" in output
        assert "| 1 | Task A | completed |" in output

    def test_resolves_transitive_chain(self, tmp_path: Path):
        """C blocked_by B, B blocked_by A => both appear as dependencies."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Chain", agent="a",
            digest="D.",
            tasks=[
                {"subject": "Task A", "status": "completed"},
                {"subject": "Task B", "status": "completed", "blocked_by": "1"},
                {"subject": "Task C", "status": "pending", "blocked_by": "2"},
            ],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=3)

        assert "| 2 | Task B | completed |" in output
        assert "| 1 | Task A | completed |" in output

    def test_detects_circular_dependency(self, tmp_path: Path):
        """A blocked_by B, B blocked_by A => warning, no infinite loop."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Cycle", agent="a",
            digest="D.",
            tasks=[
                {"subject": "Task A", "status": "pending", "blocked_by": "2"},
                {"subject": "Task B", "status": "pending", "blocked_by": "1"},
            ],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "Circular dependency" in output

    def test_handles_dangling_reference(self, tmp_path: Path):
        """blocked_by references a task ID that doesn't exist."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Dangling", agent="a",
            digest="D.",
            tasks=[
                {"subject": "Task A", "status": "pending", "blocked_by": "99"},
            ],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "does not exist" in output

    def test_handles_malformed_blocked_by(self, tmp_path: Path):
        """blocked_by value is not a valid integer."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Bad Ref", agent="a",
            digest="D.",
            tasks=[
                {"subject": "Task A", "status": "pending", "blocked_by": "foo"},
            ],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "not a valid task ID" in output

    def test_no_dependencies_message(self, tmp_path: Path):
        """Task with no blocked_by shows the 'no dependencies' message."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="NoDeps", agent="a",
            digest="D.",
            tasks=[{"subject": "Standalone", "status": "pending"}],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "This task has no dependencies." in output


# ─────────────────────────────────────────────────────────────────────
# Digest inclusion
# ─────────────────────────────────────────────────────────────────────

class TestDigestInclusion:
    def test_include_digest_renders_session_context(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Digest", agent="agent-1",
            digest="This is the session digest with important context.",
            tasks=[{"subject": "Task A", "status": "pending"}],
        )
        output = extract_task_context(
            tmp_path, result["slug"], task_id=1, include_digest=True,
        )

        assert "## Session context" in output
        assert "This is the session digest with important context." in output
        assert "agent-1" in output

    def test_default_excludes_digest(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="NoDigest", agent="a",
            digest="Should not appear in output.",
            tasks=[{"subject": "Task A", "status": "pending"}],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "## Session context" not in output
        assert "Should not appear in output." not in output


# ─────────────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_task_not_found_raises(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Err", agent="a",
            digest="D.",
            tasks=[{"subject": "Only task", "status": "pending"}],
        )
        with pytest.raises(ValueError, match="does not exist"):
            extract_task_context(tmp_path, result["slug"], task_id=999)

    def test_dossier_not_found_raises(self, tmp_path: Path):
        from operations.dossiers.errors import DossierNotFoundError
        with pytest.raises(DossierNotFoundError):
            extract_task_context(tmp_path, "nonexistent-slug", task_id=1)

    def test_deleted_target_task_raises(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """Deleted target tasks should not be directly renderable."""
        result = make_dossier_with_deleted_tasks(
            name="Err",
            tasks=[{"subject": "Deleted task", "status": "pending"}],
            delete_ids=(1,),
        )

        with pytest.raises(ValueError, match="does not exist"):
            extract_task_context(tmp_path, result["slug"], task_id=1)


# ─────────────────────────────────────────────────────────────────────
# Context notes (Slice 3)
# ─────────────────────────────────────────────────────────────────────

class TestContextNotes:
    def test_renders_context_notes_when_present(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Notes", agent="a",
            digest="D.",
            tasks=[{
                "subject": "Task with notes",
                "status": "pending",
                "context_notes": "Check the webhook sender at line 80.",
            }],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "**Context notes:** Check the webhook sender at line 80." in output

    def test_omits_context_notes_when_absent(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="NoNotes", agent="a",
            digest="D.",
            tasks=[{"subject": "Plain task", "status": "pending"}],
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "**Context notes:**" not in output

    def test_add_task_with_context_notes(self, tmp_path: Path):
        """context_notes can be set via add_task and retrieved."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="AddNotes", agent="a",
            digest="D.",
        )
        add_task(
            tmp_path, result["slug"],
            subject="Enriched task",
            context_notes="Important: use WAL mode.",
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)

        assert "**Context notes:** Important: use WAL mode." in output

    def test_update_task_context_notes(self, tmp_path: Path):
        """context_notes can be updated and cleared."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="UpdateNotes", agent="a",
            digest="D.",
            tasks=[{"subject": "Task", "status": "pending"}],
        )
        # set context_notes
        update_task(
            tmp_path, result["slug"], task_id=1,
            context_notes="Initial notes",
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)
        assert "**Context notes:** Initial notes" in output

        # clear context_notes via empty string sentinel
        update_task(
            tmp_path, result["slug"], task_id=1,
            context_notes="",
        )
        output = extract_task_context(tmp_path, result["slug"], task_id=1)
        assert "**Context notes:**" not in output


# ─────────────────────────────────────────────────────────────────────
# Pinned findings reach the worker
# ─────────────────────────────────────────────────────────────────────

class TestPinnedFindingsInTaskContext:
    """A worker that gets every decision and no constraints is the bug.

    Task context already carries 100% of the decisions; omitting findings
    hands a worker the record of what was chosen and none of the dead ends it
    must not re-walk.
    """

    @staticmethod
    def _dossier_with(tmp_path: Path, findings: list[dict]) -> str:
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "Do the work"}],
            pinned_findings=findings,
        )
        return result["slug"]

    def test_a_live_finding_reaches_the_worker(self, tmp_path: Path):
        element = {"finding": "qdrant must be up before searxng starts"}
        slug = self._dossier_with(tmp_path, [element])

        output = extract_task_context(tmp_path, slug, task_id=1)

        assert "## Pinned findings" in output
        assert f"- {finding_hash(element)[:8]} qdrant must be up before searxng starts" in output

    def test_a_dead_end_reaches_the_worker_with_its_retry_rule(self, tmp_path: Path):
        element = {"finding": "port 8780 is owned", "dead_end": True,
                   "retry": "DO NOT RETRY", "why_abandoned": "the owner is pinned"}
        slug = self._dossier_with(tmp_path, [element])

        output = extract_task_context(tmp_path, slug, task_id=1)

        assert "[dead end: DO NOT RETRY]" in output
        assert "    why abandoned: the owner is pinned" in output

    def test_a_superseded_finding_does_not_reach_the_worker(self, tmp_path: Path):
        old = {"finding": "the first phrasing"}
        slug = self._dossier_with(tmp_path, [old])
        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[{"finding": "the better phrasing",
                              "supersedes": [finding_hash(old)[:8]]}],
        )

        output = extract_task_context(tmp_path, slug, task_id=1)

        assert "the better phrasing" in output
        assert "the first phrasing" not in output

    def test_a_retracted_finding_and_its_tombstone_do_not_reach_the_worker(
        self, tmp_path: Path
    ):
        dead_end = {"finding": "port 8780 is owned", "dead_end": True}
        slug = self._dossier_with(tmp_path, [dead_end])
        fold_dossier(
            dossiers_dir=tmp_path, slug=slug, agent="a", digest="D2.",
            pinned_findings=[{"finding": "the port was freed on 08-12",
                              "kind": "retraction",
                              "supersedes": [finding_hash(dead_end)[:8]]}],
        )

        output = extract_task_context(tmp_path, slug, task_id=1)

        assert "## Pinned findings" not in output
        assert "port 8780 is owned" not in output
        assert "the port was freed on 08-12" not in output

    def test_findings_are_never_windowed_out_of_task_context(self, tmp_path: Path):
        """Unlike file interactions, constraints are not scoped to a session."""
        element = {"finding": "the oldest constraint of all"}
        slug = self._dossier_with(tmp_path, [element])
        for i in range(2, 8):
            fold_dossier(dossiers_dir=tmp_path, slug=slug, agent="a", digest=f"D{i}.")

        output = extract_task_context(tmp_path, slug, task_id=1)

        assert "the oldest constraint of all" in output

    def test_a_dossier_without_findings_renders_no_section(self, tmp_path: Path):
        slug = self._dossier_with(tmp_path, [])

        assert "## Pinned findings" not in extract_task_context(tmp_path, slug, task_id=1)
