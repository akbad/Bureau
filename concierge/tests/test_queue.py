"""Tests for the priority queue with aging and eviction."""

from datetime import datetime, timedelta, timezone

from concierge.models import FeatureCandidate, FeatureType, QueueItem
from concierge.pipeline.queue import PriorityQueue


class TestPriorityQueue:
    def _make_candidate(self, domain="meals", score=0.5):
        return FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain=domain,
            score_inputs={"relevance": score},
        )

    def test_add_and_peek(self):
        q = PriorityQueue(max_size=10)
        q.add(self._make_candidate(), priority=0.8)
        item = q.peek()
        assert item is not None
        assert item.priority == 0.8

    def test_ordering_by_priority(self):
        q = PriorityQueue(max_size=10)
        q.add(self._make_candidate("a"), priority=0.3)
        q.add(self._make_candidate("b"), priority=0.9)
        q.add(self._make_candidate("c"), priority=0.6)
        item = q.pop()
        assert item is not None
        assert item.candidate.domain == "b"

    def test_eviction_when_full(self):
        q = PriorityQueue(max_size=2)
        q.add(self._make_candidate("low"), priority=0.1)
        q.add(self._make_candidate("mid"), priority=0.5)
        q.add(self._make_candidate("high"), priority=0.9)
        assert len(q) == 2
        domains = {item.candidate.domain for item in q}
        assert "low" not in domains

    def test_aging_boosts_priority(self):
        q = PriorityQueue(max_size=10, aging_rate=0.1)
        q.add(self._make_candidate(), priority=0.5)
        item = q.peek()
        assert item is not None
        initial = item.priority
        q.age_items(hours_elapsed=5)
        aged = q.peek()
        assert aged is not None
        assert aged.priority > initial

    def test_expired_items_removed(self):
        q = PriorityQueue(max_size=10, max_age_hours=1)
        q.add(self._make_candidate(), priority=0.5)
        # Manually backdate the item
        for item in q:
            item.queued_at = datetime.now(timezone.utc) - timedelta(hours=2)
        expired = q.expire_stale()
        assert len(expired) == 1
        assert len(q) == 0

    def test_drop_when_full_and_lower_priority(self):
        q = PriorityQueue(max_size=2)
        q.add(self._make_candidate("a"), priority=0.5)
        q.add(self._make_candidate("b"), priority=0.8)
        result = q.add(self._make_candidate("c"), priority=0.3)
        assert result is None  # Dropped
        assert len(q) == 2
