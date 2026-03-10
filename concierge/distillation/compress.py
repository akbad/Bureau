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
