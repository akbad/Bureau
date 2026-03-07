"""Priority scoring engine for feature candidates.

Computes deterministic scores for each candidate by looking up
per-feature-type weights and delegating to ``FeatureCandidate.compute_score``.
"""

from __future__ import annotations

from concierge.models import FeatureCandidate

_ES_SUFFIXES = ("s", "sh", "ch", "x", "z")


def _pluralize(value: str) -> str:
    """Return a naive English plural of *value*."""
    if value.endswith(_ES_SUFFIXES):
        return value + "es"
    return value + "s"


def score_candidates(
    candidates: list[FeatureCandidate],
    weights_by_type: dict[str, dict[str, float]],
) -> list[tuple[FeatureCandidate, float]]:
    """Score and rank *candidates* using the provided weight tables.

    For each candidate the weight key is derived by pluralising the feature
    type value (e.g. ``"dispatch"`` -> ``"dispatches"``).  If no weights
    exist for a given type the candidate receives a score of ``0.0``.

    Returns a list of ``(candidate, score)`` tuples sorted by score descending.
    """
    scored: list[tuple[FeatureCandidate, float]] = []
    for candidate in candidates:
        type_key = _pluralize(candidate.feature_type.value)
        weights = weights_by_type.get(type_key, {})
        score = candidate.compute_score(weights)
        scored.append((candidate, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
