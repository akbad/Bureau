"""Tests for epsilon-greedy feature lottery."""
import random
from concierge.pipeline.lottery import FeatureSelector
from concierge.models import FeatureCandidate, FeatureType


class TestFeatureSelector:
    def _make_candidates(self, n=5):
        return [
            FeatureCandidate(
                feature_type=FeatureType.DISPATCH, domain=f"d{i}",
                score_inputs={"relevance": i / n},
            )
            for i in range(n)
        ]

    def test_exploit_selects_highest(self):
        selector = FeatureSelector(epsilon=0.0)  # Pure exploit
        candidates = self._make_candidates(5)
        scores = {c: float(i) for i, c in enumerate(candidates)}
        winner = selector.select(candidates, scores)
        assert winner is candidates[-1]

    def test_explore_can_select_non_highest(self):
        random.seed(42)
        selector = FeatureSelector(epsilon=1.0)  # Pure explore
        candidates = self._make_candidates(5)
        scores = {c: float(i) for i, c in enumerate(candidates)}
        selections = {selector.select(candidates, scores) for _ in range(100)}
        assert len(selections) > 1  # Not always picking the same one

    def test_suite_fit_floor(self):
        selector = FeatureSelector(epsilon=1.0, suite_fit_floor=0.3)
        c_good = FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain="good",
            score_inputs={"suite_fit": 0.8},
        )
        c_bad = FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain="bad",
            score_inputs={"suite_fit": 0.1},
        )
        scores = {c_good: 0.5, c_bad: 0.9}
        # Even with pure explore, c_bad should be filtered out
        for _ in range(50):
            winner = selector.select([c_good, c_bad], scores)
            assert winner is c_good

    def test_decay_reduces_epsilon(self):
        selector = FeatureSelector(epsilon=0.12, decay=0.5, min_epsilon=0.05)
        selector.decay_epsilon()
        assert selector.epsilon == 0.06
        selector.decay_epsilon()
        assert selector.epsilon == 0.05  # Clamped to min

    def test_statistical_exploration_rate(self):
        """Over many runs, exploration should match epsilon."""
        random.seed(0)
        selector = FeatureSelector(epsilon=0.12)
        candidates = self._make_candidates(3)
        scores = {c: float(i) for i, c in enumerate(candidates)}
        best = candidates[-1]
        n = 10000
        exploit_count = sum(1 for _ in range(n) if selector.select(candidates, scores) is best)
        explore_rate = 1 - (exploit_count / n)
        assert 0.06 < explore_rate < 0.18  # ~12% +/- 6%
