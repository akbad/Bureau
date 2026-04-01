"""Post-session hook -- extracts memories and updates state after each session."""

# Design rationale:
# Runs after every session to persist noteworthy facts (preferences, people,
# plans) extracted from the conversation transcript. V1 uses regex pattern
# matching; production would use LLM extraction.
# Key invariant: extraction never fails the session -- missing topic files
# are warned about but silently skipped so the user experience is unaffected.

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from concierge.memory.writer import append_raw_entry, append_auto_entry

logger = logging.getLogger(__name__)


def extract_memories(
    session_transcript: str,
    data_dir: Path,
) -> dict[str, int]:
    """Extract and persist noteworthy information from a session transcript.

    Scans the conversation for:
    1. Explicit preferences (likes, dislikes, allergies, etc.)
    2. People mentioned (names, relationships, birthdays)
    3. Plans made (events, reminders, goals)
    4. Emotional context (mood, energy level)

    V1 implementation: simple pattern matching.  Production would use LLM
    extraction.

    Returns dict with counts of items stored.
    """
    results = {"preferences": 0, "people": 0, "plans": 0, "auto_entries": 0}

    # Extract and store preferences
    prefs = _extract_preferences(session_transcript)
    for pref in prefs:
        topic_path = data_dir / "topics" / f"{pref['topic']}.md"
        if topic_path.is_file():
            append_raw_entry(topic_path, pref["entry"])
            results["preferences"] += 1
        else:
            logger.warning("Topic file not found, preference discarded: %s", topic_path)

    # Store a summary auto-entry for every session
    auto_entry = {
        "type": "session",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_count": session_transcript.count("\n") + 1,
        "topics_touched": list({p["topic"] for p in prefs}),
    }
    auto_path = data_dir / "auto" / "sessions.jsonl"
    append_auto_entry(auto_path, auto_entry)
    results["auto_entries"] = 1

    return results


def _extract_preferences(transcript: str) -> list[dict[str, str]]:
    """Extract preference statements from transcript.

    V1: simple keyword matching.  Looks for patterns like:
    - "I like/love/prefer/hate/dislike X"
    - "I'm allergic to X"
    - "My favorite X is Y"
    """
    preferences: list[dict[str, str]] = []

    patterns = [
        (r"(?:i|I)\s+(?:like|love|enjoy|prefer)\s+(.+?)(?:\.|!|$)", "general"),
        (r"(?:i|I)\s+(?:hate|dislike|don't like|can't stand)\s+(.+?)(?:\.|!|$)", "general"),
        (r"(?:i|I)'m\s+allergic\s+to\s+(.+?)(?:\.|!|$)", "health"),
        (r"(?:my|My)\s+favorite\s+(\w+)\s+is\s+(.+?)(?:\.|!|$)", "general"),
        (r"(?:i|I)\s+(?:cook|cooked|made|baked|tried)\s+(.+?)(?:\.|!|$)", "meals"),
    ]

    for pattern, default_topic in patterns:
        for match in re.finditer(pattern, transcript, re.MULTILINE):
            full_match = match.group(0).strip()
            preferences.append({
                "topic": default_topic,
                "entry": full_match,
            })

    return preferences


def update_session_state(data_dir: Path, session_summary: dict[str, object] | None = None) -> None:
    """Update persistent state after a session ends.

    Records:
    - Last session timestamp
    - Session count increment
    """
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    state_file = state_dir / "session_history.jsonl"
    entry = {
        "ended_at": datetime.now(timezone.utc).isoformat(),
        **(session_summary or {}),
    }

    with open(state_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
