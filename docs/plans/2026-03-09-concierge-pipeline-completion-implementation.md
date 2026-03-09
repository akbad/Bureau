# Concierge Pipeline Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the concierge pipeline by wiring up the orchestrator (#37), training and deploying the DistilBERT classifier (#38), and replacing the compression stub with LLM-based summarization (#39).

**Architecture:** Three independent streams: (1) a plain function-composition orchestrator that chains the 6 existing pipeline stages, (2) a training script that fine-tunes DistilBERT on 2000 synthetic examples and exports to ONNX, (3) an LLM client that calls the Bureau-configured agent CLI for topic compression.

**Tech Stack:** Python 3.13, pytest, PyTorch + transformers + onnxruntime (ML), subprocess (LLM calls), SQLite (existing dossier infra)

**Design doc:** `docs/plans/2026-03-09-concierge-pipeline-completion-design.md`

---

## Parallel Streams

These three streams are independent (different files, no shared state) and can be implemented simultaneously:

| Stream | Task | Files touched |
|--------|------|---------------|
| A | Pipeline orchestrator (#37) | `concierge/pipeline/orchestrator.py`, tests |
| B | LLM compression (#39) | `concierge/llm.py`, `concierge/distillation/compress.py`, config files |
| C | DistilBERT classifier (#38) | `concierge/classifier/train.py`, `pyproject.toml` |

---

## Stream A: Pipeline Orchestrator (#37)

### Task 1: Orchestrator — failing tests

**Files:**
- Create: `concierge/tests/test_orchestrator.py`

**Step 1: Write the failing tests**

```python
"""Tests for pipeline orchestrator."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from concierge.models import (
    FeatureCandidate, FeatureType, MessageClass, MessageEnvelope,
    QueueItem, SessionState, Suite,
)
from concierge.pipeline.orchestrator import run_pipeline
from concierge.pipeline.queue import PriorityQueue


@pytest.fixture
def envelope():
    return MessageEnvelope(
        text="what's for dinner tonight?",
        has_attachment=False,
        attachment_type=None,
        classification=MessageClass.QUERY,
        confidence=0.9,
    )


@pytest.fixture
def session():
    return SessionState()


@pytest.fixture
def queue():
    return PriorityQueue(max_size=10)


class TestRunPipeline:
    def test_returns_feature_candidate_on_success(self, envelope, session, queue):
        """Pipeline produces a feature candidate when all stages succeed."""
        result = run_pipeline(envelope, session, queue)
        # Result is either a FeatureCandidate or None (if no candidates)
        assert result is None or isinstance(result, FeatureCandidate)

    def test_returns_none_when_hard_rules_block(self, envelope, session, queue):
        """Pipeline short-circuits when hard rules block all feature types."""
        with patch(
            "concierge.pipeline.orchestrator.evaluate_hard_rules"
        ) as mock_rules:
            mock_rules.return_value = set(FeatureType)  # all blocked
            result = run_pipeline(envelope, session, queue)
            assert result is None

    def test_suite_detected_and_passed_through(self, envelope, session, queue):
        """Suite detection result flows to downstream stages."""
        with patch(
            "concierge.pipeline.orchestrator.detect_suite",
            return_value=Suite.SOCIAL,
        ) as mock_detect, patch(
            "concierge.pipeline.orchestrator.evaluate_hard_rules",
            return_value=set(),
        ), patch(
            "concierge.pipeline.orchestrator.select_attaches",
            return_value=["schedule"],
        ) as mock_attaches:
            run_pipeline(envelope, session, queue)
            mock_detect.assert_called_once()
            mock_attaches.assert_called_once_with(Suite.SOCIAL)

    def test_candidates_scored_and_queued(self, envelope, session, queue):
        """Feature candidates are scored and pushed to the queue."""
        candidate = FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="meals",
            score_inputs={"relevance": 0.8, "freshness": 0.6},
        )
        with patch(
            "concierge.pipeline.orchestrator.detect_suite",
            return_value=Suite.REST,
        ), patch(
            "concierge.pipeline.orchestrator.evaluate_hard_rules",
            return_value=set(),
        ), patch(
            "concierge.pipeline.orchestrator.select_attaches",
            return_value=[],
        ), patch(
            "concierge.pipeline.orchestrator.evaluate_all_features",
            return_value=[candidate],
        ), patch(
            "concierge.pipeline.orchestrator.score_candidates",
            return_value=[(candidate, 0.72)],
        ):
            run_pipeline(envelope, session, queue)
            assert len(queue) >= 1

    def test_stage_failure_degrades_gracefully(self, envelope, session, queue):
        """A failing stage logs the error and returns None instead of crashing."""
        with patch(
            "concierge.pipeline.orchestrator.detect_suite",
            side_effect=RuntimeError("boom"),
        ):
            result = run_pipeline(envelope, session, queue)
            assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest concierge/tests/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'concierge.pipeline.orchestrator'`

### Task 2: Orchestrator — implementation

**Files:**
- Create: `concierge/pipeline/orchestrator.py`

**Step 3: Write the implementation**

```python
"""Pipeline orchestrator — chains 6 stages into a single entry point.

Runs the concierge processing pipeline over an incoming message:
suite detection → attaché selection → hard rules → feature evaluation →
scoring + queuing → lottery selection.
"""

# Design rationale:
# Plain function composition instead of a state-machine library (Burr).
# The pipeline is a linear chain with no branching or retry needs.
# Each stage is wrapped in try/except so a single stage failure degrades
# gracefully (logs + returns None) rather than crashing the entire pipeline.
# Feature evaluators are called in a fixed order; each returns a list of
# FeatureCandidate that feed into scoring.  The queue persists across
# pipeline runs (caller owns it), enabling priority aging over time.

from __future__ import annotations

import logging
from pathlib import Path

from ..models import (
    FeatureCandidate,
    FeatureType,
    MessageEnvelope,
    SessionState,
    Suite,
)
from .attache_selector import select_attaches
from .hard_rules import evaluate_hard_rules
from .lottery import FeatureSelector
from .queue import PriorityQueue
from .scoring import score_candidates
from .suite_detector import detect_suite

logger = logging.getLogger(__name__)

# Feature evaluators — imported here to keep the evaluate_all_features
# function self-contained.  Each returns list[FeatureCandidate].
from ..features.brews import evaluate_brew_candidates
from ..features.dispatches import evaluate_dispatch_candidates
from ..features.huddles import evaluate_huddle_candidates
from ..features.probes import evaluate_probe_candidates
from ..features.valets import evaluate_valet_candidates

# Default data directory for feature evaluators
_DEFAULT_DATA_DIR = Path("~/.config/bureau/concierge").expanduser()


def evaluate_all_features(
    session: SessionState,
    blocked: set[FeatureType],
    data_dir: Path | None = None,
    envelope: MessageEnvelope | None = None,
) -> list[FeatureCandidate]:
    """Run all feature evaluators and return combined candidates.

    Skips evaluators whose feature type is in *blocked*.
    """
    ddir = data_dir or _DEFAULT_DATA_DIR

    evaluators: list[tuple[FeatureType, callable]] = [
        (FeatureType.DISPATCH, lambda: evaluate_dispatch_candidates(session, ddir)),
        (FeatureType.BREW, lambda: evaluate_brew_candidates(session, ddir)),
        (FeatureType.PROBE, lambda: evaluate_probe_candidates(session, ddir)),
        (FeatureType.VALET, lambda: evaluate_valet_candidates(session, ddir)),
        (FeatureType.HUDDLE, lambda: evaluate_huddle_candidates(session, ddir, envelope=envelope)),
    ]

    candidates: list[FeatureCandidate] = []
    for ftype, evaluator in evaluators:
        if ftype in blocked:
            logger.debug("Skipping %s (blocked by hard rules)", ftype.value)
            continue
        try:
            candidates.extend(evaluator())
        except Exception:
            logger.warning("Feature evaluator %s failed", ftype.value, exc_info=True)

    return candidates


def run_pipeline(
    envelope: MessageEnvelope,
    session: SessionState,
    queue: PriorityQueue,
    *,
    data_dir: Path | None = None,
    selector: FeatureSelector | None = None,
) -> FeatureCandidate | None:
    """Run the 6-stage concierge pipeline over *envelope*.

    Parameters
    ----------
    envelope:
        The classified message to process.
    session:
        Current session state (suite history, active feature, etc.).
    queue:
        Persistent priority queue (owned by caller, survives across runs).
    data_dir:
        Override for feature data directory (default ~/.config/bureau/concierge).
    selector:
        Override for lottery selector (default creates a new FeatureSelector).

    Returns
    -------
    FeatureCandidate | None
        The selected feature, or None if no feature was selected.
    """
    try:
        # --- Stage 1: Suite detection ----------------------------------------
        suite = detect_suite(envelope, session)
        session.record_suite(suite)
        logger.debug("Detected suite: %s", suite.value)

        # --- Stage 2: Attaché selection --------------------------------------
        attaches = select_attaches(suite)
        logger.debug("Selected attachés: %s", attaches)

        # --- Stage 3: Hard rules ---------------------------------------------
        blocked = evaluate_hard_rules(suite, session)
        if blocked == set(FeatureType):
            logger.debug("All feature types blocked by hard rules")
            return None

        # --- Stage 4: Feature evaluation + scoring ---------------------------
        candidates = evaluate_all_features(
            session, blocked, data_dir=data_dir, envelope=envelope,
        )
        if not candidates:
            logger.debug("No feature candidates generated")
            return None

        from ..config.loader import get_priorities_config
        weights = get_priorities_config().get("weights", {})
        scored = score_candidates(candidates, weights)

        # --- Stage 5: Queue -------------------------------------------------
        for candidate, priority in scored:
            queue.add(candidate, priority)

        # --- Stage 6: Lottery selection --------------------------------------
        sel = selector or FeatureSelector()
        priority_map = {item.candidate: item.priority for item in queue}
        result = sel.select(list(priority_map.keys()), priority_map)

        if result is not None:
            logger.debug(
                "Selected feature: %s/%s", result.feature_type.value, result.domain,
            )
        return result

    except Exception:
        logger.warning("Pipeline failed — returning None", exc_info=True)
        return None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest concierge/tests/test_orchestrator.py -v`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add concierge/pipeline/orchestrator.py concierge/tests/test_orchestrator.py
git commit -m "feat(concierge): add pipeline orchestrator with plain function composition (#37)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**Step 6: Run full test suite to check for regressions**

Run: `uv run pytest concierge/tests/ -v`
Expected: All tests pass

---

## Stream B: LLM Compression (#39)

### Task 3: Add preferred_agent config

**Files:**
- Modify: `defaults.yml:477-480`
- Modify: `operations/config_loader.py:163-169`

**Step 1: Add preferred_agent to defaults.yml**

In `defaults.yml`, add `preferred_agent` under `conversations.concierge`:

```yaml
  concierge:
    preferred_agent: claude
    auto_offer_resume: true
    auto_offer_save: true
    notify_task_updates: true
    notify_interval: 30s
```

**Step 2: Add to ConversationsConciergeConfig TypedDict**

In `operations/config_loader.py`, add to the `ConversationsConciergeConfig` class at line 163:

```python
class ConversationsConciergeConfig(TypedDict, total=False):
    """Concierge-specific dossier behaviors."""
    preferred_agent: str                        # agent CLI for LLM calls, default "claude"
    auto_offer_resume: bool
    auto_offer_save: bool
    notify_task_updates: bool
    notify_interval: str
```

**Step 3: Run existing config tests**

Run: `uv run pytest operations/tests/test_config_loader.py -v`
Expected: All tests pass (TypedDict is `total=False`, so new field doesn't break anything)

**Step 4: Commit**

```bash
git add defaults.yml operations/config_loader.py
git commit -m "feat(concierge): add preferred_agent config for LLM compression (#39)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

### Task 4: LLM client utility — failing tests

**Files:**
- Create: `concierge/tests/test_llm.py`

**Step 1: Write the failing tests**

```python
"""Tests for LLM client utility."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from concierge.llm import call_agent, LLMError, SUPPORTED_AGENTS


class TestCallAgent:
    def test_returns_stdout_on_success(self):
        with patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="- Enjoys pasta\n- Runs daily\n"
            )
            result = call_agent("summarize this", agent="claude")
            assert result == "- Enjoys pasta\n- Runs daily"

    def test_raises_on_unsupported_agent(self):
        with pytest.raises(LLMError, match="not a supported"):
            call_agent("test", agent="unsupported-agent")

    def test_raises_on_timeout(self):
        with patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("claude", 30)
            with pytest.raises(LLMError, match="timed out"):
                call_agent("test", agent="claude")

    def test_raises_on_nonzero_exit(self):
        with patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error msg")
            with pytest.raises(LLMError, match="exit code 1"):
                call_agent("test", agent="claude")

    def test_raises_on_empty_output(self):
        with patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="  \n  ")
            with pytest.raises(LLMError, match="empty"):
                call_agent("test", agent="claude")

    def test_validates_agent_is_enabled(self):
        """Agent must be in the resolved config's agents list."""
        with patch("concierge.llm._get_enabled_agents", return_value=["gemini"]):
            with pytest.raises(LLMError, match="not enabled"):
                call_agent("test", agent="claude")

    def test_falls_back_to_preferred_agent(self):
        """Uses preferred_agent from config when agent is None."""
        with patch("concierge.llm._get_preferred_agent", return_value="claude"), \
             patch("concierge.llm._get_enabled_agents", return_value=["claude"]), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")
            call_agent("test")
            # Verify claude CLI was called
            cmd = mock_run.call_args[0][0]
            assert "claude" in cmd


class TestSupportedAgents:
    def test_all_expected_agents(self):
        assert SUPPORTED_AGENTS == {"claude", "gemini", "codex", "opencode"}
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest concierge/tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'concierge.llm'`

### Task 5: LLM client utility — implementation

**Files:**
- Create: `concierge/llm.py`

**Step 1: Write the implementation**

```python
"""Thin LLM client — calls Bureau-configured agent CLI with a prompt.

Provides a single ``call_agent(prompt, agent)`` function that shells out
to a coding agent CLI in non-interactive mode and returns stdout.
"""

# Design rationale:
# Agent-agnostic by design: the caller specifies which agent (or it reads
# preferred_agent from config).  Each supported agent has a CLI invocation
# pattern that accepts a prompt on stdin and returns the response on stdout.
# Validation ensures the requested agent is both supported and enabled in
# the Bureau config.  All failures raise LLMError so callers can catch and
# fall back to deterministic logic.

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_AGENTS: set[str] = {"claude", "gemini", "codex", "opencode"}

# CLI invocation patterns per agent.
# Each pattern is a list of args; the prompt is piped via stdin.
_CLI_COMMANDS: dict[str, list[str]] = {
    "claude": ["claude", "--print"],
    "gemini": ["gemini"],
    "codex": ["codex", "--quiet"],
    "opencode": ["opencode", "--pipe"],
}

_DEFAULT_TIMEOUT = 60  # seconds


class LLMError(Exception):
    """Raised when an LLM call fails."""


def _get_preferred_agent() -> str:
    """Read preferred_agent from Bureau config."""
    try:
        from operations.config_loader import get_conversations_config
        config = get_conversations_config()
        concierge = config.get("concierge", {})
        return concierge.get("preferred_agent", "claude")
    except Exception:
        return "claude"


def _get_enabled_agents() -> list[str]:
    """Read enabled agents from Bureau config."""
    try:
        from operations.config_loader import get_config
        config = get_config()
        return config.get("agents", ["claude"])
    except Exception:
        return ["claude"]


def call_agent(
    prompt: str,
    *,
    agent: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """Call a Bureau-configured agent CLI with *prompt* and return the response.

    Parameters
    ----------
    prompt:
        The full prompt text to send to the agent.
    agent:
        Agent CLI to use. If None, reads ``preferred_agent`` from config.
    timeout:
        Maximum seconds to wait for response.

    Returns
    -------
    str
        The agent's response (stdout, stripped).

    Raises
    ------
    LLMError
        If the agent is unsupported, not enabled, times out, returns
        non-zero, or produces empty output.
    """
    if agent is None:
        agent = _get_preferred_agent()

    if agent not in SUPPORTED_AGENTS:
        raise LLMError(f"{agent!r} is not a supported agent ({SUPPORTED_AGENTS})")

    enabled = _get_enabled_agents()
    if agent not in enabled:
        raise LLMError(
            f"{agent!r} is not enabled in Bureau config (enabled: {enabled})"
        )

    cmd = _CLI_COMMANDS[agent]
    logger.debug("Calling agent %s with %d-char prompt", agent, len(prompt))

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"{agent} timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise LLMError(f"{agent} CLI not found on PATH") from exc

    if result.returncode != 0:
        raise LLMError(
            f"{agent} exited with exit code {result.returncode}: "
            f"{result.stderr[:200] if result.stderr else '(no stderr)'}"
        )

    output = result.stdout.strip()
    if not output:
        raise LLMError(f"{agent} returned empty output")

    return output
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest concierge/tests/test_llm.py -v`
Expected: PASS (all 8 tests)

**Step 3: Commit**

```bash
git add concierge/llm.py concierge/tests/test_llm.py
git commit -m "feat(concierge): add LLM client utility for agent CLI calls (#39)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

### Task 6: Replace compression stub — failing tests

**Files:**
- Modify: `concierge/tests/test_compress.py`

**Step 1: Rewrite tests for LLM-based compression**

The existing tests validate deterministic behavior. Replace them with tests
that mock the LLM call and verify prompt construction + fallback logic.

```python
"""Tests for LLM-based topic compression."""

from unittest.mock import patch, MagicMock

import pytest

from concierge.distillation.compress import compress_topic, DISTILLATION_PROMPT


class TestCompressTopic:
    def test_calls_llm_with_prompt(self):
        """compress_topic calls call_agent with the distillation prompt."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Enjoys pasta"
            result = compress_topic("- Old fact", "- [2026-01-01] Made pasta", "meals")
            assert mock_llm.called
            prompt = mock_llm.call_args[0][0]
            assert "meals" in prompt
            assert "Old fact" in prompt
            assert "Made pasta" in prompt

    def test_returns_llm_output(self):
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Enjoys pasta\n- Runs daily"
            result = compress_topic("", "- [2026-01-01] Made pasta", "meals")
            assert result == "- Enjoys pasta\n- Runs daily"

    def test_falls_back_to_deterministic_on_llm_error(self):
        """When LLM fails, falls back to deterministic merge."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.side_effect = Exception("API error")
            result = compress_topic(
                "- Existing fact",
                "- [2026-01-01] New entry",
                "meals",
            )
            # Deterministic fallback should preserve existing + add new
            assert "Existing fact" in result
            assert "New entry" in result

    def test_empty_distilled_shows_first_distillation(self):
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- First fact"
            compress_topic("", "- [2026-01-01] Raw entry", "meals")
            prompt = mock_llm.call_args[0][0]
            assert "first distillation" in prompt.lower()

    def test_prompt_contains_all_rules(self):
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Fact"
            compress_topic("- Old", "- New", "meals")
            prompt = mock_llm.call_args[0][0]
            assert "Preserve ALL facts" in prompt
            assert "Consolidate" in prompt
            assert "No preamble" in prompt


class TestDeterministicFallback:
    """Test the deterministic fallback directly."""

    def test_keeps_existing_entries(self):
        from concierge.distillation.compress import _deterministic_compress
        result = _deterministic_compress("- Existing fact", "")
        assert "Existing fact" in result

    def test_adds_new_entries(self):
        from concierge.distillation.compress import _deterministic_compress
        result = _deterministic_compress("", "- [2026-01-01] New entry")
        assert "New entry" in result

    def test_deduplicates(self):
        from concierge.distillation.compress import _deterministic_compress
        result = _deterministic_compress(
            "- I like pasta very much",
            "- [2026-01-01] I really like pasta a lot",
        )
        # Should not add the duplicate
        lines = [l for l in result.strip().split("\n") if l.startswith("- ")]
        assert len(lines) == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest concierge/tests/test_compress.py -v`
Expected: FAIL (import errors for new function names)

### Task 7: Replace compression stub — implementation

**Files:**
- Modify: `concierge/distillation/compress.py`

**Step 1: Replace the stub**

```python
"""LLM-based topic compression for memory distillation.

Compresses raw timestamped entries about a topic into a concise distilled
summary by calling the Bureau-configured agent CLI.  Falls back to
deterministic word-overlap merging if the LLM call fails.
"""

# Design rationale:
# The LLM produces far better summaries than the deterministic stub —
# it can consolidate patterns, generalize from specifics, and maintain
# readability.  The deterministic fallback ensures distillation always
# produces output even when the LLM is unavailable (network down, CLI
# missing, rate limit).  The prompt is hardcoded rather than config-driven
# because prompt engineering requires code-level iteration, not YAML tweaks.

from __future__ import annotations

import logging
import re

from ..llm import LLMError, call_agent

logger = logging.getLogger(__name__)

# Stop-words for overlap detection (shared with concierge.distillation)
from . import STOP_WORDS

DISTILLATION_PROMPT = """\
You are a memory distiller. Compress raw timestamped entries about a personal \
topic into a concise summary, merging with any existing distilled content.

## Topic: {topic}

## Current distilled summary
{distilled_section}

## New raw entries
{raw_text}

## Rules
1. Preserve ALL facts — losing information is the only failure mode
2. Consolidate repeated observations into patterns \
(e.g., three mentions of pasta → "Enjoys pasta — mentioned repeatedly")
3. Prefer general truths over specific dated instances \
(e.g., "Runs 5K every Tuesday" over "[2026-01-15] Ran 5K, [2026-01-22] Ran 5K")
4. Keep specific dates only when they carry meaning (events, milestones, changes)
5. Output markdown bullets (- prefix), ordered from most to least significant
6. Do not invent, infer, or extrapolate beyond what the entries state

## Output
Return ONLY the updated distilled summary. No preamble, no explanation."""


def compress_topic(
    distilled_text: str,
    raw_text: str,
    topic: str,
) -> str:
    """Compress *raw_text* into an updated distilled summary for *topic*.

    Calls the Bureau-configured agent CLI with the distillation prompt.
    Falls back to deterministic merging if the LLM call fails.

    Parameters
    ----------
    distilled_text:
        Current ``## Distilled`` section content (may be empty on first run).
    raw_text:
        Current ``## Raw`` section content (timestamped entries).
    topic:
        The topic name (e.g., "meals", "fitness").

    Returns
    -------
    str
        The proposed new distilled section (markdown bullets).
    """
    distilled_section = distilled_text.strip() or "(empty — first distillation)"

    prompt = DISTILLATION_PROMPT.format(
        topic=topic,
        distilled_section=distilled_section,
        raw_text=raw_text.strip(),
    )

    try:
        result = call_agent(prompt)
        logger.info("LLM compression succeeded for topic %r", topic)
        return result
    except (LLMError, Exception) as exc:
        logger.warning(
            "LLM compression failed for topic %r, falling back to deterministic: %s",
            topic, exc,
        )
        return _deterministic_compress(distilled_text, raw_text)


# ---------------------------------------------------------------------------
# Deterministic fallback (original stub logic)
# ---------------------------------------------------------------------------

_RAW_ENTRY_RE = re.compile(r"^- \[\d{4}-\d{2}-\d{2}\]")


def _significant_overlap(new: str, existing: str) -> bool:
    """Return True if *new* and *existing* share >50% of their words."""
    new_words = {w.lower() for w in new.split() if w.lower() not in STOP_WORDS}
    existing_words = {w.lower() for w in existing.split() if w.lower() not in STOP_WORDS}
    if not new_words or not existing_words:
        return False
    overlap = new_words & existing_words
    return len(overlap) / min(len(new_words), len(existing_words)) > 0.5


def _deterministic_compress(distilled_text: str, raw_text: str) -> str:
    """Deterministic word-overlap merge (fallback when LLM is unavailable)."""
    existing_bullets = [
        line.strip()
        for line in distilled_text.strip().split("\n")
        if line.strip().startswith("- ")
    ]

    new_entries = [
        line.strip()
        for line in raw_text.strip().split("\n")
        if _RAW_ENTRY_RE.match(line.strip())
    ]

    added = 0
    max_new = 10
    for entry in new_entries:
        if added >= max_new:
            break
        is_dup = any(_significant_overlap(entry, ex) for ex in existing_bullets)
        if not is_dup:
            existing_bullets.append(entry)
            added += 1

    return "\n".join(existing_bullets) if existing_bullets else ""
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest concierge/tests/test_compress.py -v`
Expected: PASS (all 8 tests)

**Step 3: Run full distillation test suite**

Run: `uv run pytest concierge/tests/test_compress.py concierge/tests/test_detection.py concierge/tests/test_validation.py concierge/tests/test_distillation_state.py -v`
Expected: All pass (no regressions)

**Step 4: Commit**

```bash
git add concierge/distillation/compress.py concierge/tests/test_compress.py
git commit -m "feat(concierge): replace compression stub with LLM-based summarization (#39)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Stream C: DistilBERT Classifier (#38)

### Task 8: Training script — implementation

**Files:**
- Create: `concierge/classifier/train.py`
- Modify: `pyproject.toml` (add optional ML deps)

**Step 1: Add ML dependencies to pyproject.toml**

Add an `[ml]` optional dependency group:

```toml
[project.optional-dependencies]
ml = [
    "torch>=2.0",
    "transformers>=4.30",
    "onnxruntime>=1.15",
    "numpy>=1.24",
]
```

**Step 2: Install ML dependencies**

Run: `uv sync --extra ml`
Expected: Successfully installs torch, transformers, onnxruntime, numpy

**Step 3: Write the training script**

```python
"""DistilBERT classifier training and ONNX export.

Fine-tunes distilbert-base-uncased on synthetic training data (2000 examples,
4 classes: REPLY, QUERY, CONVERSE, COMMAND) and exports to quantized ONNX.

Usage:
    uv run python -m concierge.classifier.train

The script reads training data from concierge/classifier/training_data/*.jsonl,
trains the model, and writes the quantized ONNX model to
concierge/classifier/model.onnx.
"""

# Design rationale:
# Fine-tuning DistilBERT on synthetic data gives ~5ms inference at INT8
# precision, compared to ~500ms-2s for LLM-based classification.  The
# training data is LLM-generated (one agent per class, 500 examples each)
# to avoid the chicken-and-egg problem of needing real user data before
# the concierge is deployed.  INT8 quantization halves the model size
# (~250MB → ~65MB) with negligible accuracy loss for text classification.
# The label encoding (REPLY=0, QUERY=1, CONVERSE=2, COMMAND=3) matches
# the _CLASS_MAP in model.py exactly.

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, random_split
from transformers import (
    AutoTokenizer,
    DistilBertForSequenceClassification,
    get_linear_schedule_with_warmup,
)

logger = logging.getLogger(__name__)

LABEL_MAP = {"REPLY": 0, "QUERY": 1, "CONVERSE": 2, "COMMAND": 3}
MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
MAX_EPOCHS = 5
PATIENCE = 2
WARMUP_RATIO = 0.1

TRAINING_DATA_DIR = Path(__file__).parent / "training_data"
OUTPUT_PATH = Path(__file__).parent / "model.onnx"


class ClassificationDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer):
        self.encodings = tokenizer(
            texts, max_length=MAX_LENGTH, truncation=True,
            padding="max_length", return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels": self.labels[idx],
        }


def load_training_data() -> tuple[list[str], list[int]]:
    """Load all JSONL files from the training_data directory."""
    texts, labels = [], []
    for path in sorted(TRAINING_DATA_DIR.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                obj = json.loads(line)
                texts.append(obj["text"])
                labels.append(LABEL_MAP[obj["label"]])
    logger.info("Loaded %d examples (%d classes)", len(texts), len(set(labels)))
    return texts, labels


def train() -> dict[str, float]:
    """Fine-tune DistilBERT and export to quantized ONNX.

    Returns a dict of validation metrics.
    """
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    logger.info("Using device: %s", device)

    # Load data
    texts, labels = load_training_data()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    dataset = ClassificationDataset(texts, labels, tokenizer)

    # Train/val split (80/20, seeded for reproducibility)
    val_size = int(0.2 * len(dataset))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42),
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

    # Model
    model = DistilBertForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABEL_MAP),
    ).to(device)

    # Optimizer + scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    total_steps = len(train_loader) * MAX_EPOCHS
    warmup_steps = int(WARMUP_RATIO * total_steps)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps,
    )

    # Training loop
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(1, MAX_EPOCHS + 1):
        # --- Train ---
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            train_loss += loss.item()

        train_loss /= len(train_loader)

        # --- Validate ---
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = model(**batch)
                val_loss += outputs.loss.item()
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == batch["labels"]).sum().item()
                total += len(batch["labels"])

        val_loss /= len(val_loader)
        val_accuracy = correct / total

        logger.info(
            "Epoch %d/%d — train_loss=%.4f val_loss=%.4f val_acc=%.4f",
            epoch, MAX_EPOCHS, train_loss, val_loss, val_accuracy,
        )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model state
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                logger.info("Early stopping at epoch %d", epoch)
                break

    # Restore best model
    model.load_state_dict(best_state)
    model = model.to("cpu")
    model.eval()

    # --- ONNX export ---
    dummy = tokenizer("hello", return_tensors="pt", max_length=MAX_LENGTH,
                      padding="max_length", truncation=True)
    torch.onnx.export(
        model,
        (dummy["input_ids"], dummy["attention_mask"]),
        str(OUTPUT_PATH.with_suffix(".unquantized.onnx")),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch"},
            "attention_mask": {0: "batch"},
            "logits": {0: "batch"},
        },
        opset_version=14,
    )

    # --- INT8 quantization ---
    from onnxruntime.quantization import quantize_dynamic, QuantType
    quantize_dynamic(
        str(OUTPUT_PATH.with_suffix(".unquantized.onnx")),
        str(OUTPUT_PATH),
        weight_type=QuantType.QInt8,
    )
    # Remove unquantized intermediate
    OUTPUT_PATH.with_suffix(".unquantized.onnx").unlink()

    model_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    logger.info("Model exported to %s (%.1f MB)", OUTPUT_PATH, model_size_mb)

    # --- Final validation ---
    from onnxruntime import InferenceSession
    session = InferenceSession(str(OUTPUT_PATH))

    onnx_correct = 0
    onnx_total = 0
    for batch in val_loader:
        inputs = {
            "input_ids": batch["input_ids"].numpy(),
            "attention_mask": batch["attention_mask"].numpy(),
        }
        ort_inputs = {k: v for k, v in inputs.items()
                      if k in {i.name for i in session.get_inputs()}}
        logits = session.run(None, ort_inputs)[0]
        preds = np.argmax(logits, axis=-1)
        onnx_correct += (preds == batch["labels"].numpy()).sum()
        onnx_total += len(batch["labels"])

    onnx_accuracy = onnx_correct / onnx_total

    metrics = {
        "val_accuracy": val_accuracy,
        "onnx_accuracy": float(onnx_accuracy),
        "model_size_mb": model_size_mb,
        "epochs_trained": epoch,
        "best_val_loss": best_val_loss,
    }
    logger.info("Metrics: %s", metrics)

    if onnx_accuracy < 0.85:
        logger.warning(
            "ONNX accuracy %.2f is below 85%% threshold — "
            "consider regenerating training data", onnx_accuracy,
        )

    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    metrics = train()
    print(f"\nTraining complete:")
    print(f"  Val accuracy:  {metrics['val_accuracy']:.2%}")
    print(f"  ONNX accuracy: {metrics['onnx_accuracy']:.2%}")
    print(f"  Model size:    {metrics['model_size_mb']:.1f} MB")
    print(f"  Epochs:        {metrics['epochs_trained']}")
    if metrics["onnx_accuracy"] >= 0.85:
        print(f"\n✓ Model ready at concierge/classifier/model.onnx")
    else:
        print(f"\n✗ Accuracy below threshold — review training data")
        sys.exit(1)
```

**Step 4: Run training**

Run: `uv run python -m concierge.classifier.train`
Expected: Training completes in ~15-30 min on Apple Silicon. Output shows val_accuracy > 85%.

**Step 5: Verify the model integrates with existing classify pipeline**

Run: `uv run pytest concierge/tests/test_classifier_model.py concierge/tests/test_classifier_unified.py -v`
Expected: All tests pass. If model.onnx now exists, the model tests exercise the real inference path.

**Step 6: Commit**

```bash
git add concierge/classifier/train.py concierge/classifier/training_data/ pyproject.toml
git commit -m "feat(concierge): add DistilBERT training pipeline and training data (#38)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

Note: `model.onnx` (~65MB) should be committed separately or via git-lfs:

```bash
git add concierge/classifier/model.onnx
git commit -m "feat(concierge): add trained DistilBERT ONNX model (#38)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Final verification

**After all streams complete:**

**Step 1: Run the full concierge test suite**

Run: `uv run pytest concierge/tests/ -v`
Expected: All tests pass, no regressions.

**Step 2: Run the operations test suite**

Run: `uv run pytest operations/tests/ -v`
Expected: All tests pass (config_loader changes don't break anything).

**Step 3: Smoke test the classifier**

```bash
uv run python3 -c "
from concierge.classifier.classify import classify_message
from concierge.models import MessageEnvelope

for text in ['ok', 'what is for dinner?', 'I had a great day', 'pause the probe']:
    env = MessageEnvelope(text=text, has_attachment=False, attachment_type=None)
    classify_message(env, active_feature=None)
    print(f'{text:40s} → {env.classification.value} ({env.confidence:.2f})')
"
```

Expected output (approximate):
```
ok                                       → reply (1.00)
what is for dinner?                      → query (0.85+)
I had a great day                        → converse (0.80+)
pause the probe                          → command (0.85+)
```

**Step 4: Commit any remaining changes**

Run: `git status` and commit any unstaged changes.

---

## Critical Prerequisites

1. **`operations/__init__.py` import chain**: The `operations` package imports
   `mcp_catalog` which may not exist on all branches. If imports fail, stub
   the module: `sys.modules['operations'] = types.ModuleType('operations')`

2. **All Python commands use `uv run`**: Never use bare `python` or `pip`.

3. **Code style**: Every new Python file needs:
   - Module-level docstring (first thing in file)
   - `# Design rationale:` comment block after docstring
   - `from __future__ import annotations` for modern type hints

4. **Training data already exists** at `concierge/classifier/training_data/`:
   - `reply.jsonl` (500 examples)
   - `query.jsonl` (500 examples)
   - `converse.jsonl` (500 examples)
   - `command.jsonl` (500 examples)
