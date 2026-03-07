"""Tests for feature ownership lifecycle manager."""

from datetime import datetime, timezone, timedelta

import pytest

from concierge.features.ownership import (
    DEFAULT_TIMEOUTS,
    OWNING_FEATURES,
    OwnershipManager,
)
from concierge.models import FeatureType, SessionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fixed(minutes_ago: int = 0) -> datetime:
    """Return a fixed UTC timestamp, optionally shifted into the past."""
    base = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
    return base - timedelta(minutes=minutes_ago)


# ---------------------------------------------------------------------------
# Claim tests
# ---------------------------------------------------------------------------


class TestClaim:
    def test_claim_huddle_succeeds(self):
        mgr = OwnershipManager()
        now = _fixed()
        assert mgr.claim(FeatureType.HUDDLE, "huddle-1", now=now) is True
        assert mgr.active_feature is FeatureType.HUDDLE
        assert mgr.feature_id == "huddle-1"
        assert mgr.claimed_at == now
        assert mgr.last_activity == now

    def test_claim_valet_succeeds(self):
        mgr = OwnershipManager()
        now = _fixed()
        assert mgr.claim(FeatureType.VALET, "valet-1", now=now) is True
        assert mgr.active_feature is FeatureType.VALET

    def test_claim_non_owning_feature_fails(self):
        mgr = OwnershipManager()
        for ft in (FeatureType.DISPATCH, FeatureType.BREW, FeatureType.PROBE):
            assert mgr.claim(ft, f"{ft.value}-1") is False
            assert mgr.active_feature is None

    def test_claim_while_owned_fails(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1")
        assert mgr.claim(FeatureType.VALET, "valet-1") is False
        # Original ownership unchanged
        assert mgr.active_feature is FeatureType.HUDDLE
        assert mgr.feature_id == "huddle-1"


# ---------------------------------------------------------------------------
# Release tests
# ---------------------------------------------------------------------------


class TestRelease:
    def test_release_returns_feature_type(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1")
        released = mgr.release()
        assert released is FeatureType.HUDDLE
        assert mgr.active_feature is None
        assert mgr.feature_id is None
        assert mgr.claimed_at is None
        assert mgr.last_activity is None
        assert mgr.paused is False

    def test_release_when_empty_returns_none(self):
        mgr = OwnershipManager()
        assert mgr.release() is None


# ---------------------------------------------------------------------------
# Ownership queries
# ---------------------------------------------------------------------------


class TestOwnershipQueries:
    def test_is_owned_after_claim(self):
        mgr = OwnershipManager()
        assert mgr.is_owned() is False
        mgr.claim(FeatureType.VALET, "valet-1")
        assert mgr.is_owned() is True

    def test_should_skip_candidacy_when_owned(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1")
        assert mgr.should_skip_candidacy() is True

    def test_should_skip_candidacy_when_paused_is_false(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1")
        mgr.pause()
        assert mgr.should_skip_candidacy() is False

    def test_should_skip_candidacy_when_nothing_active(self):
        mgr = OwnershipManager()
        assert mgr.should_skip_candidacy() is False


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_timeout_huddle_30_minutes(self):
        now = _fixed()
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1", now=now)

        within_window = now + timedelta(minutes=29)
        assert mgr.is_timed_out(now=within_window) is False

        at_boundary = now + timedelta(minutes=30)
        assert mgr.is_timed_out(now=at_boundary) is True

    def test_timeout_valet_60_minutes(self):
        now = _fixed()
        mgr = OwnershipManager()
        mgr.claim(FeatureType.VALET, "valet-1", now=now)

        within_window = now + timedelta(minutes=59)
        assert mgr.is_timed_out(now=within_window) is False

        at_boundary = now + timedelta(minutes=60)
        assert mgr.is_timed_out(now=at_boundary) is True

    def test_not_timed_out_within_window(self):
        now = _fixed()
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1", now=now)

        # Touch resets the timer
        touch_time = now + timedelta(minutes=20)
        mgr.touch(now=touch_time)

        # 25 mins after touch — still within 30-min window
        check_time = touch_time + timedelta(minutes=25)
        assert mgr.is_timed_out(now=check_time) is False

        # 31 mins after touch — past the window
        check_time = touch_time + timedelta(minutes=31)
        assert mgr.is_timed_out(now=check_time) is True

    def test_is_timed_out_when_nothing_active(self):
        mgr = OwnershipManager()
        assert mgr.is_timed_out() is False

    def test_check_and_release_timeout(self):
        now = _fixed()
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1", now=now)

        # Not yet timed out
        assert mgr.check_and_release_timeout(now=now + timedelta(minutes=10)) is None
        assert mgr.is_owned() is True

        # Now timed out
        released = mgr.check_and_release_timeout(
            now=now + timedelta(minutes=31)
        )
        assert released is FeatureType.HUDDLE
        assert mgr.is_owned() is False


# ---------------------------------------------------------------------------
# Pause / Resume
# ---------------------------------------------------------------------------


class TestPauseResume:
    def test_pause_and_resume(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.VALET, "valet-1")

        assert mgr.pause() is True
        assert mgr.paused is True
        assert mgr.is_owned() is True  # still owned, just paused

        assert mgr.resume() is True
        assert mgr.paused is False

    def test_pause_when_nothing_active(self):
        mgr = OwnershipManager()
        assert mgr.pause() is False

    def test_resume_when_nothing_paused(self):
        mgr = OwnershipManager()
        assert mgr.resume() is False

    def test_resume_when_active_but_not_paused(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1")
        assert mgr.resume() is False


# ---------------------------------------------------------------------------
# Touch
# ---------------------------------------------------------------------------


class TestTouch:
    def test_touch_updates_activity(self):
        t0 = _fixed(minutes_ago=10)
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1", now=t0)
        assert mgr.last_activity == t0

        t1 = _fixed()
        mgr.touch(now=t1)
        assert mgr.last_activity == t1

    def test_touch_without_active_feature_is_noop(self):
        mgr = OwnershipManager()
        mgr.touch(now=_fixed())
        assert mgr.last_activity is None


# ---------------------------------------------------------------------------
# Session sync
# ---------------------------------------------------------------------------


class TestSessionSync:
    def test_sync_to_session(self):
        now = _fixed()
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1", now=now)

        session = SessionState()
        mgr.sync_to_session(session)

        assert session.active_feature is FeatureType.HUDDLE
        assert session.active_feature_id == "huddle-1"
        assert session.feature_started_at == now

    def test_sync_to_session_after_release(self):
        mgr = OwnershipManager()
        mgr.claim(FeatureType.HUDDLE, "huddle-1")
        mgr.release()

        session = SessionState()
        mgr.sync_to_session(session)

        assert session.active_feature is None
        assert session.active_feature_id is None
        assert session.feature_started_at is None

    def test_from_session_roundtrip(self):
        now = _fixed()
        session = SessionState(
            active_feature=FeatureType.VALET,
            active_feature_id="valet-42",
            feature_started_at=now,
        )

        mgr = OwnershipManager.from_session(session)
        assert mgr.active_feature is FeatureType.VALET
        assert mgr.feature_id == "valet-42"
        assert mgr.claimed_at == now
        # last_activity should default to feature_started_at
        assert mgr.last_activity == now

        # Now sync back and verify round-trip fidelity
        session2 = SessionState()
        mgr.sync_to_session(session2)
        assert session2.active_feature is FeatureType.VALET
        assert session2.active_feature_id == "valet-42"
        assert session2.feature_started_at == now

    def test_from_session_empty(self):
        session = SessionState()
        mgr = OwnershipManager.from_session(session)
        assert mgr.active_feature is None
        assert mgr.feature_id is None
        assert mgr.is_owned() is False
