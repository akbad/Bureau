"""Valet candidacy evaluator.

Valets are guided, proactive multi-step routines (e.g., Sunday meal prep,
Friday wind-down).  They run on a schedule with specific day/time slots.
"""

# Design rationale:
# The simplest evaluator in the feature family — valets use fixed score_inputs
# (suite_fit=1.0, relevance=0.8, urgency=0.7) because they are user-configured
# routines whose value is inherent, not context-dependent.  Unlike brews and
# dispatches, valets are NOT blocked during the PROCESSING suite; they are
# intentional user-scheduled activities.  The only gate is "another valet is
# already active", preventing overlapping multi-turn routines.

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from concierge.features.schedules import is_due, load_schedules
from concierge.models import FeatureCandidate, FeatureType, SessionState


def evaluate_valet_candidates(
    session: SessionState,
    data_dir: Path,
    now: datetime | None = None,
) -> list[FeatureCandidate]:
    """Check if any scheduled valets are due to run.

    Returns a :class:`FeatureCandidate` for each due valet with fixed
    ``score_inputs``:

    - **suite_fit** — ``1.0`` (valets define their own context).
    - **relevance** — ``0.8`` (scheduled items are highly relevant).
    - **urgency** — ``0.7`` (they have a time slot).

    Valets are **not** blocked during the PROCESSING suite (they are
    user-configured routines), but are blocked when another valet is
    already active.

    Returns an empty list when no valets are due or a valet is active.
    """
    # Block if a valet is already running.
    if session.active_feature is FeatureType.VALET:
        return []

    if now is None:
        now = datetime.now(timezone.utc)

    entries = load_schedules(data_dir, "valets")
    candidates: list[FeatureCandidate] = []

    for entry in entries:
        if not is_due(entry, now):
            continue

        candidates.append(
            FeatureCandidate(
                feature_type=FeatureType.VALET,
                domain=entry.name,
                score_inputs={
                    "suite_fit": 1.0,
                    "relevance": 0.8,
                    "urgency": 0.7,
                },
                metadata={
                    "cadence": entry.cadence,
                    "day": entry.day,
                    "time": entry.time,
                    "last_run": entry.last_run.isoformat() if entry.last_run else None,
                },
            )
        )

    return candidates
