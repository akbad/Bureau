"""Tests for the priority scoring engine."""

from concierge.pipeline.scoring import score_candidates
from concierge.models import FeatureCandidate, FeatureType


class TestScoring:
    def test_scores_candidates_deterministically(self):
        c1 = FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="meals",
            score_inputs={
                "relevance": 0.9,
                "urgency": 0.5,
                "suite_fit": 1.0,
                "freshness": 0.1,
                "queue_age": 0.0,
                "domain_match": 1.0,
            },
        )
        c2 = FeatureCandidate(
            feature_type=FeatureType.BREW,
            domain="wellness",
            score_inputs={
                "relevance": 0.3,
                "urgency": 0.1,
                "suite_fit": 0.5,
                "freshness": 0.8,
                "queue_age": 0.2,
                "domain_match": 0.0,
            },
        )
        weights = {
            "dispatches": {
                "relevance": 0.35,
                "urgency": 0.25,
                "suite_fit": 0.20,
                "freshness": -0.10,
                "queue_age": 0.05,
                "domain_match": 0.05,
            },
            "brews": {
                "relevance": 0.20,
                "urgency": 0.10,
                "suite_fit": 0.30,
                "freshness": -0.20,
                "queue_age": 0.10,
                "domain_match": 0.10,
            },
        }
        scored = score_candidates([c1, c2], weights)
        assert len(scored) == 2
        assert scored[0][1] > scored[1][1]
        assert scored[0][0] is c1

    def test_empty_candidates(self):
        assert score_candidates([], {}) == []

    def test_unknown_type_uses_empty_weights(self):
        c = FeatureCandidate(
            feature_type=FeatureType.PROBE,
            domain="skincare",
            score_inputs={"suite_fit": 0.8},
        )
        scored = score_candidates([c], {})
        assert scored[0][1] == 0.0  # No weights for "probes" -> score is 0
