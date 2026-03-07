"""Feature ownership lifecycle manager.

Tracks which feature currently owns the conversation, handles
claim/release/timeout logic, and determines whether the full
pipeline should run or be short-circuited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from ..models import FeatureType, SessionState


# Features that can own the conversation (multi-turn)
OWNING_FEATURES: frozenset[FeatureType] = frozenset({
    FeatureType.HUDDLE,
    FeatureType.VALET,
})

# Default inactivity timeouts per feature type (in minutes)
DEFAULT_TIMEOUTS: dict[FeatureType, int] = {
    FeatureType.HUDDLE: 30,
    FeatureType.VALET: 60,
}


def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


@dataclass
class OwnershipManager:
    """Manages feature ownership of the conversation.

    Attributes:
        active_feature: Currently owning feature type (or None)
        feature_id: Identifier for the specific feature instance
        claimed_at: When ownership was claimed
        last_activity: When the user last interacted with the feature
        paused: Whether the feature is temporarily paused
    """

    active_feature: FeatureType | None = None
    feature_id: str | None = None
    claimed_at: datetime | None = None
    last_activity: datetime | None = None
    paused: bool = False

    def claim(
        self,
        feature_type: FeatureType,
        feature_id: str,
        now: datetime | None = None,
    ) -> bool:
        """Attempt to claim ownership for a feature.

        Returns True if claim succeeded, False if another feature already owns.
        Only OWNING_FEATURES (HUDDLE, VALET) can claim.
        Non-owning features (DISPATCH, BREW, PROBE) are one-shot and don't claim.
        """
        if feature_type not in OWNING_FEATURES:
            return False
        if self.active_feature is not None:
            return False
        if now is None:
            now = _utcnow()
        self.active_feature = feature_type
        self.feature_id = feature_id
        self.claimed_at = now
        self.last_activity = now
        self.paused = False
        return True

    def release(self) -> FeatureType | None:
        """Release ownership. Returns the released feature type, or None if nothing was active."""
        if self.active_feature is None:
            return None
        released = self.active_feature
        self.active_feature = None
        self.feature_id = None
        self.claimed_at = None
        self.last_activity = None
        self.paused = False
        return released

    def touch(self, now: datetime | None = None) -> None:
        """Update last_activity timestamp (call on each user message while feature is active)."""
        if self.active_feature is None:
            return
        if now is None:
            now = _utcnow()
        self.last_activity = now

    def is_owned(self) -> bool:
        """Return True if a feature currently owns the conversation."""
        return self.active_feature is not None

    def should_skip_candidacy(self) -> bool:
        """Return True if pipeline stages 3-4 should be skipped (feature owns and not paused)."""
        return self.active_feature is not None and not self.paused

    def is_timed_out(self, now: datetime | None = None) -> bool:
        """Check if the active feature has timed out due to inactivity."""
        if self.active_feature is None or self.last_activity is None:
            return False
        timeout_minutes = DEFAULT_TIMEOUTS.get(self.active_feature)
        if timeout_minutes is None:
            return False
        if now is None:
            now = _utcnow()
        elapsed = now - self.last_activity
        return elapsed >= timedelta(minutes=timeout_minutes)

    def check_and_release_timeout(self, now: datetime | None = None) -> FeatureType | None:
        """If timed out, release and return the feature type. Otherwise return None."""
        if self.is_timed_out(now=now):
            return self.release()
        return None

    def pause(self) -> bool:
        """Pause the active feature. Returns True if paused, False if nothing active."""
        if self.active_feature is None:
            return False
        self.paused = True
        return True

    def resume(self) -> bool:
        """Resume a paused feature. Returns True if resumed, False if nothing paused."""
        if self.active_feature is None or not self.paused:
            return False
        self.paused = False
        return True

    def sync_to_session(self, session: SessionState) -> None:
        """Update SessionState fields to reflect current ownership state."""
        session.active_feature = self.active_feature
        session.active_feature_id = self.feature_id
        session.feature_started_at = self.claimed_at

    @classmethod
    def from_session(cls, session: SessionState) -> OwnershipManager:
        """Create an OwnershipManager from existing SessionState fields."""
        return cls(
            active_feature=session.active_feature,
            feature_id=session.active_feature_id,
            claimed_at=session.feature_started_at,
            last_activity=session.feature_started_at,
            paused=False,
        )
