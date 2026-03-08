"""Dispatch candidacy evaluator.

Dispatches are spontaneous, perfectly-timed micro-suggestions. They are
not scheduled and not requested. Constraints: max 2-3 per week, 12h
cooldown, suite-aware (no dispatches during Processing).
"""

# Design rationale:
# Dispatches are gated by a 12-hour cooldown and a 3-per-week frequency cap
# to feel serendipitous rather than spammy.  The evaluator returns at most a
# single FeatureCandidate (not a list of options) because dispatch content is
# generated downstream — this stage only decides whether *any* dispatch should
# fire.  The PROCESSING suite gate is checked first to short-circuit cheaply
# before loading history from disk.

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from concierge.features.history import (
    count_in_period,
    hours_since_last,
    load_feature_history,
)
from concierge.models import FeatureCandidate, FeatureType, SessionState, Suite

_WEEK_HOURS = 168.0  # 7 days


def evaluate_dispatch_candidates(
    session: SessionState,
    data_dir: Path,
    cooldown_hours: float = 12,
    max_per_week: int = 3,
    now: datetime | None = None,
) -> list[FeatureCandidate]:
    """Check if dispatch candidates should be generated.

    Returns an empty list if:
    - Cooldown hasn't elapsed (12h since last dispatch)
    - Weekly limit reached (3/week)
    - Suite is PROCESSING

    Otherwise returns a single candidate with computed *score_inputs*.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # --- Suite gate ---
    if session.current_suite is Suite.PROCESSING:
        return []

    # --- History gates ---
    history = load_feature_history(data_dir, "dispatch")

    if hours_since_last(history, now) < cooldown_hours:
        return []

    if count_in_period(history, now, _WEEK_HOURS) >= max_per_week:
        return []

    # --- Compute score_inputs ---
    suite_fit = 1.0  # All non-PROCESSING suites are compatible

    raw_freshness = hours_since_last(history, now) / cooldown_hours
    freshness = min(raw_freshness, 1.0)

    score_inputs: dict[str, float] = {
        "suite_fit": suite_fit,
        "freshness": freshness,
        "relevance": 0.5,
        "urgency": 0.0,
        "queue_age": 0.0,
        "domain_match": 0.5,
    }

    return [
        FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="dispatch",
            score_inputs=score_inputs,
        )
    ]
