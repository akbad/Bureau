"""Tests for dossier unfold (render for context injection)."""
import re
from pathlib import Path

import pytest

from operations.dossiers.errors import DossierNotFoundError
from operations.dossiers.findings import finding_hash
from operations.dossiers.fold import fold_dossier
from operations.dossiers.unfold import (
    FINDINGS_HEALTH_THRESHOLD,
    find_dossier,
    list_dossiers,
    unfold_dossier,
)


class TestFindDossier:
    """Tests for finding dossiers by hash or name."""

    def test_find_by_hash(self, tmp_path: Path):
        """Finds dossier by its 6-char hash."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="D."
        )
        found = find_dossier(tmp_path, result["hash"])
        assert found is not None
        assert found.name == f"{result['slug']}.db"

    def test_find_by_name_substring(self, tmp_path: Path):
        """Finds dossier by fuzzy name match."""
        fold_dossier(
            dossiers_dir=tmp_path, name="Auth Refactor", agent="claude-code", digest="D."
        )
        found = find_dossier(tmp_path, "auth-refactor")
        assert found is not None

    def test_raises_for_unknown(self, tmp_path: Path):
        """Raises DossierNotFoundError when no match found."""
        with pytest.raises(DossierNotFoundError):
            find_dossier(tmp_path, "nonexistent")


class TestUnfoldDossier:
    """Tests for rendering dossier content for injection."""

    def test_output_contains_metadata(self, tmp_path: Path):
        """Rendered output includes metadata section."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="My Project",
            agent="claude-code",
            project="/path/to/repo",
            branch="main",
            digest="Full digest here.",
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "My Project" in output
        assert "/path/to/repo" in output
        assert "main" in output

    def test_output_contains_digest(self, tmp_path: Path):
        """Rendered output includes session digest when full=True."""
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="This is the important digest content.",
        )
        output = unfold_dossier(tmp_path, result["hash"], full=True)
        assert "This is the important digest content." in output

    def test_output_contains_tasks(self, tmp_path: Path):
        """Rendered output includes task table."""
        tasks = [{"subject": "Fix the bug", "status": "pending"}]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="D.",
            tasks=tasks,
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Fix the bug" in output
        assert "pending" in output

    def test_output_contains_decisions(self, tmp_path: Path):
        """Rendered output includes decisions."""
        decisions = [{"what": "Use Rust", "why": "Performance", "decided_by": "user"}]
        result = fold_dossier(
            dossiers_dir=tmp_path,
            name="Test",
            agent="claude-code",
            digest="D.",
            decisions=decisions,
        )
        output = unfold_dossier(tmp_path, result["hash"])
        assert "Use Rust" in output

    def test_multiple_sessions_rendered(self, tmp_path: Path):
        """All session digests are included when multiple folds exist and full=True."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="claude-code", digest="Session 1."
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="codex", digest="Session 2."
        )
        output = unfold_dossier(tmp_path, result["hash"], full=True)
        assert "Session 1." in output
        assert "Session 2." in output

    def test_caps_rendered_sessions(self, tmp_path: Path):
        """Only last N session digests are rendered when max_sessions is set."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="Session 1."
        )
        for i in range(2, 8):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"Session {i}.",
            )
        output = unfold_dossier(tmp_path, result["hash"], max_sessions=3, full=True)
        assert "Session 5." in output
        assert "Session 7." in output
        assert "Session 1." not in output
        assert "4 older session digests omitted" in output

    def test_raises_on_unknown_dossier(self, tmp_path: Path):
        """Raises FileNotFoundError for unknown dossier."""
        with pytest.raises(FileNotFoundError):
            unfold_dossier(tmp_path, "nonexistent")

    def test_compact_includes_latest_digest_only(self, tmp_path: Path):
        """Compact unfold includes the latest session digest but omits older ones."""
        result = fold_dossier(dossiers_dir=tmp_path, name="Test", agent="a", digest="Old session digest.")
        fold_dossier(dossiers_dir=tmp_path, slug=result["slug"], agent="b", digest="Latest session digest.")
        output = unfold_dossier(tmp_path, "test")  # default full=False

        # latest session digest always rendered under "Latest session context"
        assert "Latest session context" in output
        assert "Latest session digest." in output

        # older session digests are NOT rendered in compact mode
        assert "Session digests" not in output
        assert "Old session digest." not in output

    def test_full_includes_digests(self, tmp_path: Path):
        """Full unfold includes session digests."""
        fold_dossier(dossiers_dir=tmp_path, name="Test", agent="a", digest="My session digest here.")
        output = unfold_dossier(tmp_path, "test", full=True)
        assert "Session digests" in output
        assert "My session digest here" in output

    def test_compact_includes_tasks_and_decisions(self, tmp_path: Path):
        """Compact unfold still includes tasks and decisions."""
        fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            tasks=[{"subject": "Fix bug"}],
            decisions=[{"what": "Use SQLite", "why": "ACID", "decided_by": "user"}],
        )
        output = unfold_dossier(tmp_path, "test")  # default full=False
        assert "Tasks" in output
        assert "Fix bug" in output
        assert "Decisions" in output
        assert "Use SQLite" in output

    @pytest.mark.parametrize("full", [False, True], ids=["compact", "full"])
    def test_omits_deleted_tasks_from_rendered_tasks_table(
        self,
        tmp_path: Path,
        make_dossier_with_deleted_tasks,
        full: bool,
    ):
        """Deleted tasks should not leak into unfold output in either mode."""
        result = make_dossier_with_deleted_tasks(
            name="Deleted",
            tasks=[
                {"subject": "Live task", "status": "pending"},
                {"subject": "Deleted task", "status": "pending"},
            ],
            delete_ids=(2,),
        )

        output = unfold_dossier(tmp_path, result["hash"], full=full)

        assert "Live task" in output
        assert "Deleted task" not in output

    def test_omits_tasks_section_when_all_tasks_are_deleted(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """The tasks section should disappear when no live tasks remain."""
        result = make_dossier_with_deleted_tasks(
            name="Deleted",
            tasks=[{"subject": "Deleted task", "status": "pending"}],
            delete_ids=(1,),
        )

        output = unfold_dossier(tmp_path, result["hash"])

        assert "## Tasks" not in output
        assert "Deleted task" not in output


class TestListDossiers:
    """Tests for listing all dossiers."""

    def test_lists_all(self, tmp_path: Path):
        """Returns all dossiers sorted by updated_at descending."""
        fold_dossier(dossiers_dir=tmp_path, name="Alpha", agent="a", digest="D.")
        fold_dossier(dossiers_dir=tmp_path, name="Beta", agent="b", digest="D.")
        results = list_dossiers(tmp_path)
        assert len(results) == 2

    def test_empty_directory(self, tmp_path: Path):
        """Returns empty list for empty dossiers directory."""
        results = list_dossiers(tmp_path)
        assert results == []

    def test_task_count_excludes_deleted_tasks(self, tmp_path: Path, make_dossier_with_deleted_tasks):
        """List output should count only non-deleted tasks."""
        make_dossier_with_deleted_tasks(
            name="Alpha",
            tasks=[
                {"subject": "Live task 1", "status": "pending"},
                {"subject": "Deleted task", "status": "pending"},
                {"subject": "Live task 2", "status": "completed"},
            ],
            delete_ids=(2,),
        )

        results = list_dossiers(tmp_path)

        assert len(results) == 1
        assert results[0]["tasks"] == 2


class TestFileInteractionRenderWindow:
    """Storage keeps every file row; the render window keeps unfold compact.

    F2 moved retention from write time to render time. These tests pin the
    resulting split: nothing is destroyed, but compact output stays bounded.
    """

    @staticmethod
    def _dossier_with_sessions(tmp_path: Path, count: int) -> str:
        """Fold `count` sessions, each contributing one distinct file row."""
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Windowed", agent="a", digest="S1.",
            files=[{"path": "/f1.py", "action": "read"}],
        )
        for i in range(2, count + 1):
            fold_dossier(
                dossiers_dir=tmp_path, slug=result["slug"], agent="a",
                digest=f"S{i}.",
                files=[{"path": f"/f{i}.py", "action": "read"}],
            )
        return result["slug"]

    def test_compact_unfold_windows_to_recent_sessions(self, tmp_path: Path):
        """Compact output shows only the newest `max_sessions` sessions' rows."""
        slug = self._dossier_with_sessions(tmp_path, 7)
        out = unfold_dossier(tmp_path, slug, max_sessions=5)
        # sessions 3-7 are inside the window; 1-2 fall outside it
        for i in range(3, 8):
            assert f"/f{i}.py" in out
        assert "/f1.py" not in out
        assert "/f2.py" not in out

    def test_full_unfold_renders_every_file_row(self, tmp_path: Path):
        """`--full` renders the complete history, proving nothing was deleted."""
        slug = self._dossier_with_sessions(tmp_path, 7)
        out = unfold_dossier(tmp_path, slug, max_sessions=5, full=True)
        for i in range(1, 8):
            assert f"/f{i}.py" in out, f"/f{i}.py was destroyed or not rendered"


# ── v5 render contract (D6 accounting, D9 copy-safe findings) ───────────
#
# Governing principle: storage is complete, rendering is windowed, nothing is
# silently dropped. Every windowed section therefore ends with an accounting
# line, and pinned findings — which are *constraints*, not provenance — are
# never windowed at all.


def _fold_sessions(tmp_path: Path, count: int, **per_session: object) -> str:
    """Fold `count` sessions, numbering any per-session payload the caller gives.

    Each keyword is a callable taking the 1-based session number and returning
    that session's value for the matching `fold_dossier` argument.
    """
    slug = None
    for i in range(1, count + 1):
        payload = {key: build(i) for key, build in per_session.items()}
        if slug is None:
            result = fold_dossier(
                dossiers_dir=tmp_path, name="Windowed", agent="a", digest=f"S{i}.",
                **payload,
            )
            slug = result["slug"]
        else:
            fold_dossier(
                dossiers_dir=tmp_path, slug=slug, agent="a", digest=f"S{i}.", **payload,
            )
    return slug


def _finding_lines(output: str) -> list[str]:
    """Return the rendered finding bullets, in order (no continuation lines)."""
    section = output.split("## Pinned findings")[1]
    body = section.split("\n##")[0]
    return [line for line in body.splitlines() if line.startswith("- ")]


def _finding_entries(output: str) -> list[list[str]]:
    """Return each finding as its bullet line plus its continuation lines."""
    section = output.split("## Pinned findings")[1]
    body = section.split("\n##")[0]
    entries: list[list[str]] = []
    for line in body.splitlines():
        if line.startswith("- "):
            entries.append([line])
        elif line.startswith("    ") and entries:
            entries[-1].append(line)
    return entries


class TestAccountingFooters:
    """Every windowed section states what it hid, in one shared sentence shape."""

    def test_decisions_are_windowed_to_recent_sessions(self, tmp_path: Path):
        """r2-F10: 65 decisions measured ~44 KB of injected context."""
        slug = _fold_sessions(
            tmp_path, 7,
            decisions=lambda i: [{"what": f"Decision {i}", "why": f"Reason {i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "Decision 7" in out
        assert "Decision 3" in out
        assert "Decision 1" not in out

    def test_full_renders_every_decision(self, tmp_path: Path):
        slug = _fold_sessions(
            tmp_path, 7,
            decisions=lambda i: [{"what": f"Decision {i}", "why": f"Reason {i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5, full=True)

        for i in range(1, 8):
            assert f"Decision {i}" in out, f"Decision {i} was hidden even with --full"

    def test_the_decisions_footer_counts_what_it_hid(self, tmp_path: Path):
        slug = _fold_sessions(
            tmp_path, 7,
            decisions=lambda i: [{"what": f"Decision {i}", "why": f"Reason {i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "2 older decisions omitted; --full shows all." in out

    def test_the_file_interactions_footer_counts_what_it_hid(self, tmp_path: Path):
        """The retrofit: this window has been silent since r2-F2 introduced it."""
        slug = _fold_sessions(
            tmp_path, 7, files=lambda i: [{"path": f"/f{i}.py", "action": "read"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "2 older file interactions omitted; --full shows all." in out

    def test_the_memory_queries_footer_counts_what_it_hid(self, tmp_path: Path):
        slug = _fold_sessions(
            tmp_path, 7, memory_queries=lambda i: [{"tool": "t", "query": f"q{i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "q7" in out
        assert "q1" not in out
        assert "2 older memory queries omitted; --full shows all." in out

    def test_the_sessions_footer_counts_what_it_hid(self, tmp_path: Path):
        slug = _fold_sessions(tmp_path, 7)

        # a cap that reaches every session, so `--full` really is the remedy
        out = unfold_dossier(tmp_path, slug, max_sessions=7)

        assert "6 older session digests omitted; --full shows all." in out

    def test_the_sessions_footer_names_the_cap_when_full_is_already_on(
        self, tmp_path: Path
    ):
        """`--full` cannot be the remedy for a limit `--full` does not lift."""
        slug = _fold_sessions(tmp_path, 7)

        out = unfold_dossier(tmp_path, slug, max_sessions=3, full=True)

        assert "4 older session digests omitted; --max-sessions raises the cap." in out

    @pytest.mark.parametrize(
        "section", ["decisions", "file interactions", "memory queries"],
    )
    def test_a_section_inside_its_window_says_nothing(self, tmp_path: Path, section: str):
        """Silence on the happy path: a footer that always fires is noise."""
        slug = _fold_sessions(
            tmp_path, 3,
            decisions=lambda i: [{"what": f"D{i}", "why": "y"}],
            files=lambda i: [{"path": f"/f{i}.py", "action": "read"}],
            memory_queries=lambda i: [{"query": f"q{i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert f"older {section} omitted" not in out


class TestPinnedFindingsRender:
    """D9: the render must never add characters that need removing."""

    def test_a_finding_renders_as_a_plain_line(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[{"finding": "qdrant must be up before searxng starts"}],
        )

        [line] = _finding_lines(unfold_dossier(tmp_path, result["hash"]))

        digest = finding_hash({"finding": "qdrant must be up before searxng starts"})
        assert line == f"- {digest[:8]} qdrant must be up before searxng starts"

    def test_a_dead_end_renders_tokens_inline_and_free_text_below(self, tmp_path: Path):
        """Only closed-vocabulary tokens share the line the text terminates."""
        element = {
            "finding": "port 8780 is permanently owned by another app",
            "dead_end": True,
            "retry": "DO NOT RETRY",
            "why_abandoned": "the owner cannot be uninstalled",
        }
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [entry] = _finding_entries(unfold_dossier(tmp_path, result["hash"]))

        assert entry == [
            f"- {finding_hash(element)[:8]} [dead end: DO NOT RETRY] "
            f"port 8780 is permanently owned by another app",
            "    why abandoned: the owner cannot be uninstalled",
            "    retry: DO NOT RETRY",
        ]

    def test_a_conditional_retry_is_summarized_inline_and_given_in_full_below(
        self, tmp_path: Path
    ):
        """The token carries the class; the continuation line carries the value."""
        element = {
            "finding": "port 8780 is owned by another app",
            "dead_end": True,
            "retry": "CONDITIONAL: only after [issue 26] lands",
        }
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [entry] = _finding_entries(unfold_dossier(tmp_path, result["hash"]))

        assert entry == [
            f"- {finding_hash(element)[:8]} [dead end: CONDITIONAL] "
            f"port 8780 is owned by another app",
            "    retry: CONDITIONAL: only after [issue 26] lands",
        ]

    def test_a_dead_end_without_a_retry_flag_renders_the_bare_token(self, tmp_path: Path):
        element = {"finding": "an abandoned approach", "dead_end": True}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [line] = _finding_lines(unfold_dossier(tmp_path, result["hash"]))

        assert line == f"- {finding_hash(element)[:8]} [dead end] an abandoned approach"

    def test_the_text_is_never_markdown_escaped(self, tmp_path: Path):
        """An escaped `*` is exactly the character that would need removing."""
        element = {"finding": "pytest's rewriter skips *.pyc fixup [inferred]"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [line] = _finding_lines(unfold_dossier(tmp_path, result["hash"]))

        assert line.endswith("pytest's rewriter skips *.pyc fixup [inferred]")
        assert "\\" not in line

    def test_superseded_findings_are_hidden_from_the_compact_render(self, tmp_path: Path):
        old = {"finding": "the first phrasing"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[old],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{"finding": "the better phrasing",
                              "supersedes": [finding_hash(old)[:8]]}],
        )

        out = unfold_dossier(tmp_path, result["hash"])

        assert "the better phrasing" in out
        assert "the first phrasing" not in out

    def test_tombstones_are_hidden_from_the_compact_render(self, tmp_path: Path):
        """A retraction's text is a *reason*, not a live constraint."""
        dead_end = {"finding": "port 8780 is owned", "dead_end": True}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[dead_end],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{"finding": "the port was freed on 08-12",
                              "kind": "retraction",
                              "supersedes": [finding_hash(dead_end)[:8]]}],
        )

        out = unfold_dossier(tmp_path, result["hash"])

        assert "## Pinned findings" not in out
        assert "port 8780 is owned" not in out
        assert "the port was freed on 08-12" not in out

    def test_full_renders_retired_rows_as_archaeology(self, tmp_path: Path):
        dead_end = {"finding": "port 8780 is owned", "dead_end": True}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[dead_end],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{"finding": "the port was freed on 08-12",
                              "kind": "retraction",
                              "supersedes": [finding_hash(dead_end)[:8]]}],
        )

        out = unfold_dossier(tmp_path, result["hash"], full=True)

        lines = _finding_lines(out)
        assert any("[superseded]" in line and "port 8780 is owned" in line for line in lines)
        assert any("[retraction]" in line for line in lines)

    def test_findings_are_never_recency_windowed(self, tmp_path: Path):
        """A `DO NOT RETRY` from session 1 can be the most important line here."""
        element = {"finding": "the oldest constraint of all", "dead_end": True,
                   "retry": "DO NOT RETRY"}
        slug = None
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="S1.",
            pinned_findings=[element],
        )
        slug = result["slug"]
        for i in range(2, 12):
            fold_dossier(dossiers_dir=tmp_path, slug=slug, agent="a", digest=f"S{i}.")

        out = unfold_dossier(tmp_path, slug, max_sessions=2)

        assert "the oldest constraint of all" in out
        assert "older pinned findings omitted" not in out

    def test_the_health_warning_stays_quiet_at_the_threshold(self, tmp_path: Path):
        findings = [{"finding": f"finding number {i}"} for i in range(FINDINGS_HEALTH_THRESHOLD)]
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=findings,
        )

        assert "consolidate stale ones" not in unfold_dossier(tmp_path, result["hash"])

    def test_the_health_warning_fires_past_the_threshold(self, tmp_path: Path):
        """Not an omission notice — nothing is hidden — but a smell detector."""
        count = FINDINGS_HEALTH_THRESHOLD + 1
        findings = [{"finding": f"finding number {i}"} for i in range(count)]
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=findings,
        )

        out = unfold_dossier(tmp_path, result["hash"])

        assert f"{count} live pinned findings; consolidate stale ones via supersedes." in out


class TestPinnedFindingRoundTrip:
    """D1's named falsifier: render, copy back as an agent would, re-hash.

    Any future "improvement" to the finding render that breaks copy-safety
    fails here instead of quietly forking identities in live dossiers. The
    extractor below is a deliberate re-implementation of the documented
    grammar rather than a call into the renderer: a shared parser would agree
    with the renderer by construction and prove nothing.
    """

    # Closed vocabulary, longest first so `[dead end: ...]` wins over
    # `[dead end]`. Anything else in brackets is text.
    _TOKENS = (
        "[dead end: DO NOT RETRY]", "[dead end: CONDITIONAL]", "[dead end]",
        "[retraction]", "[superseded]",
    )
    _INDENT = "    "
    _CONTINUATION_KEYS = {"why abandoned": "why_abandoned", "retry": "retry"}

    @classmethod
    def _extract(cls, entry: list[str]) -> tuple[str, dict]:
        head, *continuations = entry
        prefix, _, rest = head.removeprefix("- ").partition(" ")
        element: dict = {}
        while True:
            for token in cls._TOKENS:
                if rest == token or rest.startswith(token + " "):
                    if token.startswith("[dead end"):
                        element["dead_end"] = True
                    rest = rest[len(token):].removeprefix(" ")
                    break
            else:
                break
        element["finding"] = rest
        for line in continuations:
            key, _, value = line.removeprefix(cls._INDENT).partition(": ")
            element[cls._CONTINUATION_KEYS[key]] = value
        return prefix, element

    @pytest.mark.parametrize(
        "element",
        [
            {"finding": "qdrant must be up before searxng starts"},
            {"finding": "port 8780 is permanently owned", "dead_end": True,
             "retry": "DO NOT RETRY"},
            {"finding": "redis was ruled out", "dead_end": True,
             "retry": "CONDITIONAL: Bureau adds a daemon",
             "why_abandoned": "too much infrastructure for this use case"},
            {"finding": "[inferred] the local.yml override wins over defaults.yml"},
            {"finding": "café must be NFC-normalized before hashing *.pyc paths"},
            # the four fork classes the amended grammar exists to close
            {"finding": "YAML storage was abandoned", "dead_end": True,
             "why_abandoned": "[inferred] concurrent writes corrupted data"},
            {"finding": "port 8780 is owned", "dead_end": True,
             "retry": "CONDITIONAL: only after [issue 26] lands"},
        ],
        ids=[
            "plain", "dead-end", "conditional", "leading-bracket", "unicode",
            "bracket-in-why-abandoned", "bracket-in-retry",
        ],
    )
    def test_a_rendered_finding_rehashes_to_its_stored_identity(
        self, tmp_path: Path, element: dict
    ):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [entry] = _finding_entries(unfold_dossier(tmp_path, result["hash"]))
        prefix, recovered = self._extract(entry)

        assert finding_hash(recovered) == finding_hash(element)
        assert prefix == finding_hash(element)[:8]

    @pytest.mark.parametrize(
        "element",
        [
            {"finding": "[dead end: DO NOT RETRY] is the tag unfold prints"},
            {"finding": "[superseded] marks a retired row in --full output"},
        ],
        ids=["dead-end-token", "superseded-token"],
    )
    def test_text_beginning_with_a_vocabulary_token_forks_visibly(
        self, tmp_path: Path, element: dict
    ):
        """The accepted residual bound, pinned so nobody mistakes it for closed.

        No delimiter can separate a token from text that *is* that token, so
        this one case cannot be fixed by grammar. What matters is the
        direction it fails in: the extractor drops the leading token and the
        re-hash differs, so a copy-back lands as a new, visible row — never as
        a silent merge into a different finding.
        """
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [entry] = _finding_entries(unfold_dossier(tmp_path, result["hash"]))
        _, recovered = self._extract(entry)

        assert finding_hash(recovered) != finding_hash(element), (
            "the residual bound closed — update the grammar docs and delete this test"
        )
        assert element["finding"].endswith(recovered["finding"]), (
            "the loss must be the token prefix alone, so the fork stays a duplicate"
        )

    def test_a_line_wrapped_copy_back_still_rehashes(self, tmp_path: Path):
        """D7's collapse-and-strip step is what absorbs the wrapping."""
        element = {"finding": "qdrant must be up before searxng starts"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D.",
            pinned_findings=[element],
        )

        [entry] = _finding_entries(unfold_dossier(tmp_path, result["hash"]))
        _, recovered = self._extract(entry)
        wrapped = {"finding": recovered["finding"].replace(" before ", "\n   before ")}

        assert finding_hash(wrapped) == finding_hash(element)

    def test_a_retired_finding_rehashes_from_the_full_render(self, tmp_path: Path):
        """`[superseded]` is a token, so it must not be mistaken for text."""
        element = {"finding": "the first phrasing"}
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
            pinned_findings=[element],
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            pinned_findings=[{"finding": "the better phrasing",
                              "supersedes": [finding_hash(element)[:8]]}],
        )

        entries = _finding_entries(unfold_dossier(tmp_path, result["hash"], full=True))
        recovered = [self._extract(entry)[1] for entry in entries]

        assert finding_hash(element) in {finding_hash(r) for r in recovered}


class TestSessionScalarsRender:
    """The three per-session scalars belong to the resumption context."""

    def test_the_latest_session_scalars_are_rendered(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="The digest.",
            mood="Focused and fast.", next_words="Right, the migration first.",
            last_exchange="user: ship it",
        )

        out = unfold_dossier(tmp_path, result["hash"])

        assert "Focused and fast." in out
        assert "Right, the migration first." in out
        assert "user: ship it" in out

    def test_a_session_without_scalars_renders_no_empty_labels(self, tmp_path: Path):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="The digest."
        )

        out = unfold_dossier(tmp_path, result["hash"])

        assert "Mood:" not in out
        assert "Next words:" not in out
        assert "Last exchange" not in out

    def test_only_the_latest_session_scalars_are_rendered_in_compact_mode(
        self, tmp_path: Path
    ):
        result = fold_dossier(
            dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.", mood="tense",
        )
        fold_dossier(
            dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
            mood="relieved",
        )

        out = unfold_dossier(tmp_path, result["hash"])

        assert "relieved" in out
        assert "tense" not in out


class TestAccountingFooterGrammar:
    """The shared sentence shape still has to read like a sentence at n = 1."""

    def test_a_single_omitted_decision_reads_singular(self, tmp_path: Path):
        slug = _fold_sessions(
            tmp_path, 6,
            decisions=lambda i: [{"what": f"Decision {i}", "why": f"Reason {i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "1 older decision omitted; --full shows all." in out

    def test_a_single_omitted_memory_query_pluralizes_irregularly(self, tmp_path: Path):
        slug = _fold_sessions(
            tmp_path, 6, memory_queries=lambda i: [{"query": f"q{i}"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "1 older memory query omitted; --full shows all." in out


def test_findings_render_in_the_order_they_were_sent(tmp_path: Path):
    """Payload order within a fold, fold order across them — never hash order."""
    result = fold_dossier(
        dossiers_dir=tmp_path, name="Test", agent="a", digest="D1.",
        pinned_findings=[{"finding": "zeta comes first"}, {"finding": "alpha comes second"}],
    )
    fold_dossier(
        dossiers_dir=tmp_path, slug=result["slug"], agent="a", digest="D2.",
        pinned_findings=[{"finding": "later fold, later line"}],
    )

    lines = _finding_lines(unfold_dossier(tmp_path, result["hash"]))

    assert [line.split(" ", 2)[2] for line in lines] == [
        "zeta comes first", "alpha comes second", "later fold, later line",
    ]


class TestAnEmptiedWindowStillAccounts:
    """A window that hides *everything* must still say so.

    The ordinary long-dossier shape: decisions were made early and the newest
    sessions added none. Rendering neither the section nor its footer leaves
    zero signal that a populated table exists, which is invariant 6's failure
    exactly — settled decisions get re-litigated.
    """

    @staticmethod
    def _early_only(tmp_path: Path, **first_session: object) -> str:
        """Fold 7 sessions where only the first carries any payload rows."""
        return _fold_sessions(
            tmp_path, 7,
            **{key: (lambda i, v=value: v if i == 1 else []) for key, value in first_session.items()},
        )

    def test_a_fully_windowed_decisions_table_renders_header_and_footer(
        self, tmp_path: Path
    ):
        slug = self._early_only(
            tmp_path, decisions=[{"what": "Use SQLite", "why": "ACID"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "## Decisions" in out
        assert "1 older decision omitted; --full shows all." in out
        assert "Use SQLite" not in out

    def test_a_fully_windowed_file_table_renders_header_and_footer(self, tmp_path: Path):
        slug = self._early_only(
            tmp_path, files=[{"path": "/early.py", "action": "read"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "## File interactions" in out
        assert "1 older file interaction omitted; --full shows all." in out
        assert "/early.py" not in out

    def test_a_fully_windowed_memory_query_table_renders_header_and_footer(
        self, tmp_path: Path
    ):
        slug = self._early_only(tmp_path, memory_queries=[{"query": "early q"}])

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "## Memory queries" in out
        assert "1 older memory query omitted; --full shows all." in out
        assert "early q" not in out

    @pytest.mark.parametrize(
        "section", ["## Decisions", "## File interactions", "## Memory queries"],
    )
    def test_a_truly_empty_table_renders_no_section(self, tmp_path: Path, section: str):
        """Nothing was hidden, so there is nothing to account for."""
        slug = _fold_sessions(tmp_path, 7)

        assert section not in unfold_dossier(tmp_path, slug, max_sessions=5)

    def test_full_reveals_what_the_emptied_window_accounted_for(self, tmp_path: Path):
        slug = self._early_only(
            tmp_path, decisions=[{"what": "Use SQLite", "why": "ACID"}],
        )

        out = unfold_dossier(tmp_path, slug, max_sessions=5, full=True)

        assert "Use SQLite" in out
        assert "decision omitted" not in out


class TestCompactSessionFooterRemedy:
    """Name `--full` only where `--full` is actually the remedy."""

    def test_it_names_full_when_full_would_show_every_digest(self, tmp_path: Path):
        slug = _fold_sessions(tmp_path, 3)

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "2 older session digests omitted; --full shows all." in out

    def test_it_names_the_cap_when_full_would_still_hide_some(self, tmp_path: Path):
        """`--full` does not lift the session cap, so promising it is a lie."""
        slug = _fold_sessions(tmp_path, 7)

        out = unfold_dossier(tmp_path, slug, max_sessions=5)

        assert "6 older session digests omitted; --max-sessions raises the cap." in out
