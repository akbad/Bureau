"""Tests for concierge.state — session state persistence."""

from concierge.models import FeatureType, MessageClass, SessionState, Suite
from concierge.state import load_session_state, save_session_state


class TestSessionStatePersistence:
    def test_save_and_load_roundtrip(self, tmp_data_dir):
        state = SessionState(
            current_suite=Suite.WORK,
            processing_cooldown_remaining=2,
        )
        state.record_classification(MessageClass.CONVERSE)
        save_session_state(state, tmp_data_dir / "state" / "session.yml")
        loaded = load_session_state(tmp_data_dir / "state" / "session.yml")
        assert loaded.current_suite == Suite.WORK
        assert loaded.processing_cooldown_remaining == 2
        assert loaded.recent_classifications == [MessageClass.CONVERSE]

    def test_load_missing_file_returns_default(self, tmp_data_dir):
        loaded = load_session_state(tmp_data_dir / "state" / "session.yml")
        assert loaded.current_suite is None
        assert loaded.recent_classifications == []

    def test_roundtrip_with_all_fields(self, tmp_data_dir):
        from datetime import datetime, timezone

        state = SessionState(
            current_suite=Suite.PROCESSING,
            suite_since=datetime(2026, 3, 7, 10, 0, tzinfo=timezone.utc),
            active_feature=FeatureType.HUDDLE,
            active_feature_id="huddle_123",
            feature_started_at=datetime(2026, 3, 7, 10, 5, tzinfo=timezone.utc),
            last_message_at=datetime(2026, 3, 7, 10, 10, tzinfo=timezone.utc),
            processing_cooldown_remaining=3,
        )
        state.record_classification(MessageClass.CONVERSE)
        state.record_suite(Suite.PROCESSING)
        path = tmp_data_dir / "state" / "session.yml"
        save_session_state(state, path)
        loaded = load_session_state(path)
        assert loaded.current_suite == Suite.PROCESSING
        assert loaded.active_feature == FeatureType.HUDDLE
        assert loaded.active_feature_id == "huddle_123"
        assert loaded.recent_suites == [Suite.PROCESSING]
