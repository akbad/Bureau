"""Brew candidacy evaluator.

Brews are observations distilled over time -- patterns the user might
never notice. Constraints: max 1-2 per month, 168h (1 week) cooldown,
need significant raw data accumulated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from concierge.features.history import (
    count_in_period,
    hours_since_last,
    load_feature_history,
)
from concierge.models import FeatureCandidate, FeatureType, SessionState, Suite

_MONTH_HOURS = 720.0  # ~30 days

# Suite-fit mapping for brew candidates.
_BREW_SUITE_FIT: dict[Suite, float] = {
    Suite.REST: 1.0,
    Suite.CREATIVE: 1.0,
    Suite.WORK: 0.8,
    Suite.SOCIAL: 0.8,
    Suite.PROCESSING: 0.0,
}


def evaluate_brew_candidates(
    session: SessionState,
    data_dir: Path,
    cooldown_hours: float = 168,
    max_per_month: int = 2,
    now: datetime | None = None,
) -> list[FeatureCandidate]:
    """Check if brew candidates should be generated.

    Returns an empty list if:
    - Cooldown hasn't elapsed (168h = 1 week since last brew)
    - Monthly limit reached (2/month = 720h period)
    - Suite is PROCESSING
    - Processing cooldown is active

    Otherwise returns a single candidate with computed *score_inputs*.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # --- Suite gate ---
    if session.current_suite is Suite.PROCESSING:
        return []

    # --- Processing cooldown gate ---
    if session.is_in_processing_cooldown:
        return []

    # --- History gates ---
    history = load_feature_history(data_dir, "brew")

    if hours_since_last(history, now) < cooldown_hours:
        return []

    if count_in_period(history, now, _MONTH_HOURS) >= max_per_month:
        return []

    # --- Compute score_inputs ---
    suite_fit = _BREW_SUITE_FIT.get(session.current_suite, 0.5)  # type: ignore[arg-type]

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
            feature_type=FeatureType.BREW,
            domain="brew",
            score_inputs=score_inputs,
        )
    ]
