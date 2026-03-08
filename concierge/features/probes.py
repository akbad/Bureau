"""Probe candidacy evaluator.

Probes are personalized intelligence reports — deep dives into topics the
user cares about.  They run on a schedule (weekly / biweekly) with a 24-hour
cooldown between runs.
"""

# Design rationale:
# Probes are schedule-gated: each configured probe is checked independently
# via is_due(), so multiple probes can become candidates in a single cycle if
# their schedules align.  Suite-fit is a placeholder heuristic (0.5 default,
# 0.0 during PROCESSING) because a richer domain-to-suite mapping requires
# user configuration that does not yet exist.  Per-due-probe candidates let
# the lottery pick the best one when several are due simultaneously.

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from concierge.features.schedules import is_due, load_schedules
from concierge.models import FeatureCandidate, FeatureType, SessionState, Suite


def evaluate_probe_candidates(
    session: SessionState,
    data_dir: Path,
    cooldown_hours: float = 24,
    now: datetime | None = None,
) -> list[FeatureCandidate]:
    """Check if any scheduled probes are due for delivery.

    Returns a :class:`FeatureCandidate` for each due probe with
    ``score_inputs``:

    - **suite_fit** — ``1.0`` if the current suite matches the probe domain,
      ``0.0`` during ``PROCESSING``, ``0.5`` otherwise.
    - **queue_age** — always ``0.0`` (fresh candidates).
    - **freshness** — ``hours_since_last_run / cooldown_hours``, capped at
      ``1.0``.

    Returns an empty list when no probes are due.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    entries = load_schedules(data_dir, "probes")
    candidates: list[FeatureCandidate] = []

    for entry in entries:
        if not is_due(entry, now):
            continue

        # --- score_inputs ---------------------------------------------------
        suite_fit = _compute_suite_fit(session, entry.name)
        freshness = _compute_freshness(entry.last_run, now, cooldown_hours)

        candidates.append(
            FeatureCandidate(
                feature_type=FeatureType.PROBE,
                domain=entry.name,
                score_inputs={
                    "suite_fit": suite_fit,
                    "queue_age": 0.0,
                    "freshness": freshness,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_suite_fit(session: SessionState, domain: str) -> float:
    """Return suite_fit score based on the current suite.

    - ``0.0`` during PROCESSING (probes shouldn't interrupt batch work).
    - ``1.0`` if the suite name matches the probe domain (heuristic).
    - ``0.5`` otherwise.
    """
    if session.current_suite is Suite.PROCESSING:
        return 0.0

    # Simple heuristic: if the suite name appears in the probe domain
    # (e.g., suite=REST and domain="skincare" doesn't match,
    #  suite=WORK and domain="career" doesn't match either unless explicit).
    # For now, default to 0.5 — a richer mapping can be added later.
    if session.current_suite is not None:
        suite_name = session.current_suite.value.lower()
        if suite_name in domain.lower() or domain.lower() in suite_name:
            return 1.0

    return 0.5


def _compute_freshness(
    last_run: datetime | None,
    now: datetime,
    cooldown_hours: float,
) -> float:
    """Return freshness as ``hours_since_last_run / cooldown_hours``, capped at 1.0."""
    if last_run is None:
        return 1.0

    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    hours_since = (now - last_run).total_seconds() / 3600.0
    return min(hours_since / cooldown_hours, 1.0)
