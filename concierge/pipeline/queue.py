"""Priority queue with aging and eviction for the concierge pipeline.

Uses ``pqdict`` (a min-heap priority queue dict) internally.  Priorities are
negated so that **higher** logical priority is dequeued first.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pqdict import pqdict

from concierge.models import FeatureCandidate, QueueItem


class PriorityQueue:
    """Bounded priority queue with time-based aging and expiration.

    Parameters
    ----------
    max_size:
        Maximum number of items the queue will hold.  When full, a new item
        can only enter if its priority exceeds the current lowest.
    aging_rate:
        Priority boost applied per hour of aging (via :meth:`age_items`).
    max_age_hours:
        Items older than this many hours are considered stale and will be
        removed by :meth:`expire_stale`.
    """

    def __init__(
        self,
        max_size: int = 10,
        aging_rate: float = 0.02,
        max_age_hours: float = 168,
    ) -> None:
        self.max_size = max_size
        self.aging_rate = aging_rate
        self.max_age_hours = max_age_hours

        # pqdict is a min-heap keyed by item ID, valued by *negated* priority.
        self._pq: pqdict = pqdict()
        # Parallel dict for O(1) QueueItem lookup by ID.
        self._items: dict[str, QueueItem] = {}

    # ------------------------------------------------------------------
    # Size / iteration
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._pq)

    def __iter__(self):
        return iter(self._items.values())

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add(self, candidate: FeatureCandidate, priority: float) -> str | None:
        """Insert *candidate* with the given *priority*.

        If the queue is full and the new priority is higher than the current
        lowest, the lowest-priority item is evicted.  If the queue is full
        and the new priority is **not** higher, the candidate is silently
        dropped and ``None`` is returned.

        Returns the item ID on success, or ``None`` if the candidate was
        dropped.
        """
        if len(self._pq) >= self.max_size:
            # In our negated scheme the *largest* stored value corresponds
            # to the *lowest* logical priority.  pqdict.top() returns the
            # *minimum* stored value (highest real priority), so we must
            # search for the maximum stored value to find the worst item.
            worst_id = max(self._pq, key=self._pq.__getitem__)
            worst_priority = -self._pq[worst_id]
            if priority <= worst_priority:
                return None
            # Evict the lowest-priority item.
            del self._pq[worst_id]
            del self._items[worst_id]

        item_id = uuid4().hex[:8]
        item = QueueItem(candidate=candidate, priority=priority)
        self._pq[item_id] = -priority
        self._items[item_id] = item
        return item_id

    def peek(self) -> QueueItem | None:
        """Return the highest-priority item without removing it."""
        if not self._pq:
            return None
        # The pqdict stores *negated* priorities, so top() gives the
        # item with the smallest negated value == highest real priority.
        # However, pqdict.top() returns the key with the *minimum* value.
        # Since we negated, the minimum negated value == maximum real
        # priority.  That's exactly what we want.
        top_id = self._pq.top()
        return self._items[top_id]

    def pop(self) -> QueueItem | None:
        """Remove and return the highest-priority item."""
        if not self._pq:
            return None
        top_id = self._pq.pop()
        item = self._items.pop(top_id)
        return item

    # ------------------------------------------------------------------
    # Aging / expiration
    # ------------------------------------------------------------------

    def age_items(self, hours_elapsed: float = 1.0) -> None:
        """Boost every item's priority by ``aging_rate * hours_elapsed``."""
        boost = self.aging_rate * hours_elapsed
        for item_id in list(self._pq):
            new_priority = self._items[item_id].priority + boost
            self._items[item_id].priority = new_priority
            self._pq.updateitem(item_id, -new_priority)

    def expire_stale(self) -> list[QueueItem]:
        """Remove items older than *max_age_hours*.  Return expired items."""
        now_aware = datetime.now(timezone.utc)
        now_naive = datetime.now()
        expired: list[QueueItem] = []
        for item_id in list(self._pq):
            item = self._items[item_id]
            # Support both tz-aware and tz-naive queued_at timestamps.
            now = now_aware if item.queued_at.tzinfo is not None else now_naive
            age_hours = (now - item.queued_at).total_seconds() / 3600
            if age_hours > self.max_age_hours:
                del self._pq[item_id]
                del self._items[item_id]
                expired.append(item)
        return expired
