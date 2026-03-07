"""Shared feature history utilities.

Feature history is stored as JSONL at ``data_dir / "feature_history.jsonl"``
with one JSON object per line::

    {"feature_type": "dispatch", "domain": "meals",
     "surfaced_at": "2026-03-07T12:00:00+00:00", "outcome": "engaged"}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_HISTORY_FILENAME = "feature_history.jsonl"


def load_feature_history(data_dir: Path, feature_type: str) -> list[dict]:
    """Load JSONL entries for the given feature type.

    Returns an empty list when the history file does not exist.
    """
    history_file = data_dir / _HISTORY_FILENAME
    if not history_file.exists():
        return []

    entries: list[dict] = []
    with open(history_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("feature_type") == feature_type:
                entries.append(entry)
    return entries


def hours_since_last(history: list[dict], now: datetime) -> float:
    """Hours since most recent entry, or *inf* if no history."""
    if not history:
        return float("inf")

    most_recent = max(
        datetime.fromisoformat(e["surfaced_at"]) for e in history
    )
    delta = now - most_recent
    return delta.total_seconds() / 3600.0


def count_in_period(
    history: list[dict], now: datetime, period_hours: float
) -> int:
    """Count entries within the last *period_hours* hours."""
    cutoff = now - __import__("datetime").timedelta(hours=period_hours)
    return sum(
        1
        for e in history
        if datetime.fromisoformat(e["surfaced_at"]) >= cutoff
    )


def record_feature(
    data_dir: Path,
    feature_type: str,
    domain: str,
    outcome: str = "surfaced",
) -> None:
    """Append a new JSONL entry to the feature history file."""
    history_file = data_dir / _HISTORY_FILENAME
    entry = {
        "feature_type": feature_type,
        "domain": domain,
        "surfaced_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
    }
    with open(history_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
