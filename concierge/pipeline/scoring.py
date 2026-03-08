"""Priority scoring engine for feature candidates.

Computes deterministic scores for each candidate by looking up
per-feature-type weights and delegating to ``FeatureCandidate.compute_score``.
"""

# Design rationale:
# Deterministic scoring engine that maps each FeatureCandidate to a numeric
# score using per-feature-type weight tables.
# An explicit lookup dict maps singular feature type values to their plural
# weight keys, avoiding fragile English pluralisation heuristics.
# Key invariants: unknown feature types score 0.0; output is sorted descending.

from __future__ import annotations

from concierge.models import FeatureCandidate

_TYPE_TO_WEIGHT_KEY: dict[str, str] = {
    "dispatch": "dispatches",
    "brew": "brews",
    "probe": "probes",
    "valet": "valets",
    "huddle": "huddles",
}


def score_candidates(
    candidates: list[FeatureCandidate],
    weights_by_type: dict[str, dict[str, float]],
) -> list[tuple[FeatureCandidate, float]]:
    """Score and rank *candidates* using the provided weight tables.

    For each candidate the weight key is derived from an explicit lookup
    (e.g. ``"dispatch"`` -> ``"dispatches"``).  If no weights exist for a
    given type the candidate receives a score of ``0.0``.

    Returns a list of ``(candidate, score)`` tuples sorted by score descending.
    """
    scored: list[tuple[FeatureCandidate, float]] = []
    for candidate in candidates:
        type_key = _TYPE_TO_WEIGHT_KEY.get(candidate.feature_type.value)
        weights = weights_by_type.get(type_key, {}) if type_key else {}
        score = candidate.compute_score(weights)
        scored.append((candidate, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
