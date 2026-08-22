"""Tests for the fold payload contract and its drift detector.

The fold payload schema is declared once in `operations.dossiers.payload`, and
the tests below diff that declaration against `fold-dossier/SKILL.md` **in both
directions**, so a key added to either side without the other fails the suite.

Three of the four drift surfaces are covered here:

  - key sets (top level)      → `test_field_reference_*`
  - mode-conditional handling → `test_refold_inert_keys_*`
  - nested element schemas    → `test_payload_example_element_keys_*`

The fourth (prose behaviour claims restating CLI mechanism) is not
mechanically detectable; it is governed by the rule stated in `payload.py`.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from operations.dossiers import payload
from operations.dossiers.db import open_dossier_db, safe_db_path
from operations.dossiers.fold import fold_dossier
from operations.dossiers.payload import (
    ELEMENT_KEYS,
    FOLD_DOCUMENTED_KEYS,
    FOLD_PENDING_KEYS,
    FOLD_PERSISTED_KEYS,
    INERT_ON_REFOLD,
    check_fold_payload,
)

# ── Skill-document parsing ──────────────────────────────────────────────
# The skill is the *documented* half of the contract. Located by walking up
# from this file (deterministic) rather than from cwd, and asserted to exist
# so a moved skill fails loudly instead of silently skipping every diff.

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = (
    _REPO_ROOT / "protocols/context/static/skills/fold-dossier/SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    """Return the fold skill's markdown source."""
    assert _SKILL_PATH.is_file(), (
        f"fold-dossier SKILL.md not found at {_SKILL_PATH}; the contract test "
        f"cannot run. Update _SKILL_PATH if the skill moved."
    )
    return _SKILL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def payload_example(skill_text: str) -> dict:
    """Return the parsed JSON payload example from the skill.

    Asserts the skill carries exactly one ``json`` fence. More than one means
    the payload has been duplicated, which is the divergence risk this whole
    module exists to remove.
    """
    blocks = re.findall(r"```json\n(.*?)```", skill_text, re.S)
    assert len(blocks) == 1, (
        f"expected exactly 1 json block in SKILL.md, found {len(blocks)}; "
        f"a duplicated payload example will drift"
    )
    return json.loads(blocks[0])


@pytest.fixture(scope="module")
def field_reference_keys(skill_text: str) -> frozenset[str]:
    """Return the top-level keys named in the skill's field-reference table.

    The table is the authoritative field list (it can document keys the JSON
    example cannot show, such as `digest_file`, which is mutually exclusive
    with `digest`).
    """
    start = skill_text.index("**Field reference:**")
    section = skill_text[start:]
    table = section[: section.index("\n### ")]
    return frozenset(re.findall(r"^\|\s*`([a-z_]+)`\s*\|", table, re.M))


def _fold_cli(dossiers_dir: Path, payload: dict) -> subprocess.CompletedProcess:
    """Run `fold` with `payload` on stdin and return the completed process."""
    return subprocess.run(
        [
            sys.executable, "-m", "operations.dossiers", "fold",
            "--input-file", "-", "--dossiers-dir", str(dossiers_dir),
        ],
        capture_output=True,
        text=True,
        input=json.dumps(payload),
    )


def _read_project(dossiers_dir: Path, slug: str) -> str | None:
    """Return `metadata.project` for a dossier."""
    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        return conn.execute("SELECT project FROM metadata").fetchone()["project"]


# ── The checker: top-level keys ─────────────────────────────────────────


def test_should_warn_when_payload_key_is_unrecognized():
    warnings = check_fold_payload({"agent": "a", "sparkle": 1}, is_refold=False)

    assert any("sparkle" in w for w in warnings), warnings


def test_should_stay_silent_when_every_key_is_persisted():
    payload = {"name": "N", "agent": "a", "digest": "d", "project": "/p"}

    assert check_fold_payload(payload, is_refold=False) == []


def test_no_documented_key_is_still_waiting_for_storage():
    """The v5 migration's definition of done, pinned so it stays done."""
    assert FOLD_PENDING_KEYS == frozenset()


def test_should_warn_that_a_pending_key_is_not_persisted(monkeypatch):
    """The mechanism outlives the fields it was built for.

    `FOLD_PENDING_KEYS` is empty today, but the next field documented ahead of
    its schema must warn as "cannot store this yet" rather than as a typo — so
    the branch is exercised against a stand-in rather than deleted.
    """
    monkeypatch.setattr(payload, "FOLD_PENDING_KEYS", frozenset({"telemetry"}))
    monkeypatch.setattr(
        payload, "FOLD_DOCUMENTED_KEYS", FOLD_DOCUMENTED_KEYS | {"telemetry"}
    )

    warnings = payload.check_fold_payload(
        {"agent": "a", "telemetry": {}}, is_refold=False
    )

    assert len(warnings) == 1, warnings
    assert "telemetry" in warnings[0]
    assert "not yet persisted" in warnings[0]


def test_should_not_report_a_persisted_array_key_as_unrecognized():
    warnings = check_fold_payload({"pinned_findings": []}, is_refold=False)

    assert not any("unrecognized" in w for w in warnings), warnings


# ── The checker: mode-conditional handling (surface 3) ──────────────────


def test_should_warn_when_tasks_are_sent_on_refold():
    warnings = check_fold_payload(
        {"slug": "s", "agent": "a", "tasks": [{"subject": "x"}]}, is_refold=True
    )

    assert len(warnings) == 1, warnings
    assert "tasks" in warnings[0]
    assert "re-fold" in warnings[0]


def test_should_stay_silent_when_tasks_are_sent_on_new_fold():
    payload = {"name": "N", "agent": "a", "tasks": [{"subject": "x"}]}

    assert check_fold_payload(payload, is_refold=False) == []


def test_should_warn_when_name_is_sent_on_refold():
    warnings = check_fold_payload({"slug": "s", "name": "New"}, is_refold=True)

    assert any("name" in w and "re-fold" in w for w in warnings), warnings


# ── The checker: nested element schemas (surface 4) ─────────────────────


def test_should_warn_when_a_task_element_key_is_unrecognized():
    payload = {"name": "N", "tasks": [{"subject": "x"}, {"subject": "y", "notes": "z"}]}

    warnings = check_fold_payload(payload, is_refold=False)

    assert len(warnings) == 1, warnings
    assert "tasks[1]" in warnings[0]
    assert "notes" in warnings[0]


def test_should_accept_context_notes_on_a_task_element():
    payload = {"name": "N", "tasks": [{"subject": "x", "context_notes": "hint"}]}

    assert check_fold_payload(payload, is_refold=False) == []


def test_should_warn_when_a_file_element_key_is_unrecognized():
    payload = {"name": "N", "files": [{"path": "/p", "action": "read", "size": 3}]}

    warnings = check_fold_payload(payload, is_refold=False)

    assert any("files[0]" in w and "size" in w for w in warnings), warnings


def test_should_not_inspect_elements_of_a_key_that_is_inert_on_refold():
    """A key the fold ignores wholesale should not also warn about its contents."""
    payload = {"slug": "s", "tasks": [{"subject": "x", "notes": "z"}]}

    warnings = check_fold_payload(payload, is_refold=True)

    assert len(warnings) == 1, warnings
    assert "re-fold" in warnings[0]


def test_should_accept_the_documented_pinned_finding_element_keys():
    """Both halves: the four hashed into identity, plus the two lifecycle keys."""
    element = {
        "finding": "f", "dead_end": True, "why_abandoned": "w", "retry": "DO NOT RETRY",
        "kind": "dead_end", "supersedes": ["a3f91c2e"],
    }

    assert check_fold_payload({"agent": "a", "pinned_findings": [element]},
                              is_refold=False) == []


def test_should_warn_when_a_pinned_finding_element_key_is_unrecognized():
    """`source_session` left the payload with v5: provenance is the CLI's job."""
    fold_payload = {
        "agent": "a",
        "pinned_findings": [{"finding": "f", "source_session": "inherited"}],
    }

    warnings = check_fold_payload(fold_payload, is_refold=False)

    assert any(
        "pinned_findings[0]" in w and "source_session" in w for w in warnings
    ), warnings


def test_should_warn_when_a_memory_query_element_key_is_unrecognized():
    fold_payload = {"agent": "a", "memory_queries": [{"query": "q", "latency": 3}]}

    warnings = check_fold_payload(fold_payload, is_refold=False)

    assert any("memory_queries[0]" in w and "latency" in w for w in warnings), warnings


def test_should_tolerate_an_array_key_that_is_not_a_list():
    assert check_fold_payload({"name": "N", "tasks": "oops"}, is_refold=False) == []


def test_should_tolerate_an_element_that_is_not_an_object():
    assert check_fold_payload({"name": "N", "tasks": ["oops"]}, is_refold=False) == []


# ── The contract vs the skill ───────────────────────────────────────────


def test_field_reference_documents_every_persisted_key(field_reference_keys):
    """Accepted-but-undocumented is how `digest_file` went unused for months."""
    undocumented = FOLD_PERSISTED_KEYS - field_reference_keys

    assert not undocumented, (
        f"payload key(s) the CLI persists but SKILL.md's field reference never "
        f"mentions: {sorted(undocumented)}"
    )


def test_field_reference_documents_no_key_the_cli_ignores(field_reference_keys):
    """Documented-but-dropped means agents send fields into a void."""
    unaccepted = field_reference_keys - FOLD_DOCUMENTED_KEYS

    assert not unaccepted, (
        f"SKILL.md documents payload key(s) the CLI neither persists nor "
        f"tracks as pending: {sorted(unaccepted)}"
    )


def test_pending_keys_are_documented(field_reference_keys):
    """A pending key nobody documents is dead weight, not a tracked gap."""
    assert FOLD_PENDING_KEYS <= field_reference_keys


def test_payload_example_keys_are_all_in_the_field_reference(
    payload_example, field_reference_keys
):
    assert set(payload_example) <= field_reference_keys


def test_payload_example_element_keys_match_the_accepted_element_keys(
    payload_example,
):
    """Nested schemas drift too — `context_notes` lived in this blind spot."""
    for key, accepted in ELEMENT_KEYS.items():
        documented = {k for element in payload_example.get(key, []) for k in element}

        assert documented == accepted, (
            f"element schema drift in `{key}[]`: documented={sorted(documented)}, "
            f"accepted={sorted(accepted)}"
        )


def test_refold_inert_keys_are_named_in_the_skill(skill_text):
    """The skill must tell agents which keys a re-fold ignores."""
    start = skill_text.index("### Step 7")
    section = skill_text[start: skill_text.index("### Step 8")]

    for key in INERT_ON_REFOLD:
        assert f"`{key}`" in section, (
            f"`{key}` is ignored on re-fold but Step 7 never says so"
        )


# ── End to end through the CLI ──────────────────────────────────────────


def test_fold_warns_on_an_unrecognized_key_but_still_succeeds(dossiers_dir):
    result = _fold_cli(
        dossiers_dir, {"name": "N", "agent": "claude-code", "digest": "d", "sparkle": 1}
    )

    assert result.returncode == 0, result.stderr
    assert "sparkle" in result.stderr
    assert "Dossier saved" in result.stdout


_COMPLETE_PAYLOAD = {
    "name": "N", "agent": "claude-code", "digest": "d", "project": "/p",
    "branch": "main", "commit": "abc1234",
    "tasks": [{"subject": "t", "context_notes": "hint"}],
    "decisions": [{"what": "w", "why": "y"}],
    "files": [{"path": "/p/f.py", "action": "modified"}],
    "last_exchange": "user: ship it",
    "next_words": "Right, the migration first.",
    "mood": "Focused and fast.",
    "pinned_findings": [{"finding": "qdrant must be up before searxng"}],
    "memory_queries": [{"tool": "qdrant-find", "query": "dossier schema"}],
}


def test_fold_emits_no_stderr_for_a_clean_payload(dossiers_dir):
    """A channel that cries wolf on the happy path is a dead channel."""
    result = _fold_cli(dossiers_dir, _COMPLETE_PAYLOAD)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_fold_persists_every_documented_key(dossiers_dir):
    """`FOLD_PENDING_KEYS` is empty; this is that claim proven end to end."""
    result = _fold_cli(dossiers_dir, _COMPLETE_PAYLOAD)
    slug = re.search(r"`([^`]+)`", result.stdout).group(1)

    with open_dossier_db(safe_db_path(dossiers_dir, slug)) as conn:
        session = conn.execute("SELECT * FROM sessions").fetchone()
        stored = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("pinned_findings", "memory_queries", "decisions", "tasks")
        }

    assert session["last_exchange"] == "user: ship it"
    assert session["next_words"] == "Right, the migration first."
    assert session["mood"] == "Focused and fast."
    assert stored == {
        "pinned_findings": 1, "memory_queries": 1, "decisions": 1, "tasks": 1,
    }


def test_refold_warns_that_the_tasks_array_is_ignored(dossiers_dir):
    created = _fold_cli(dossiers_dir, {"name": "N", "agent": "claude-code", "digest": "d"})
    slug = re.search(r"`([^`]+)`", created.stdout).group(1)

    result = _fold_cli(
        dossiers_dir,
        {"slug": slug, "agent": "claude-code", "digest": "d2",
         "tasks": [{"subject": "ignored"}]},
    )

    assert result.returncode == 0, result.stderr
    assert "tasks" in result.stderr and "re-fold" in result.stderr


# ── `project` is refreshed on re-fold, never clobbered ──────────────────


def test_refold_updates_project_when_provided(tmp_path):
    created = fold_dossier(
        dossiers_dir=tmp_path, name="N", agent="a", digest="d", project="/old"
    )

    fold_dossier(
        dossiers_dir=tmp_path, slug=created["slug"], agent="a", digest="d2",
        project="/new",
    )

    assert _read_project(tmp_path, created["slug"]) == "/new"


def test_refold_preserves_project_when_omitted(tmp_path):
    """An older cached skill may omit `project`; that must not erase it."""
    created = fold_dossier(
        dossiers_dir=tmp_path, name="N", agent="a", digest="d", project="/old"
    )

    fold_dossier(dossiers_dir=tmp_path, slug=created["slug"], agent="a", digest="d2")

    assert _read_project(tmp_path, created["slug"]) == "/old"
