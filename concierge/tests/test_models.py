"""Tests for concierge data models."""
from concierge.models import (
    MessageClass, Suite, SessionState, FeatureCandidate, FeatureType,
    QueueItem, MessageEnvelope, QueueItemState,
)

class TestMessageClass:
    def test_all_classes_exist(self):
        assert MessageClass.REPLY.value == "reply"
        assert MessageClass.QUERY.value == "query"
        assert MessageClass.CONVERSE.value == "converse"
        assert MessageClass.COMMAND.value == "command"
        assert MessageClass.MEDIA.value == "media"

class TestSuite:
    def test_all_suites_exist(self):
        assert Suite.WORK.value == "work"
        assert Suite.REST.value == "rest"
        assert Suite.SOCIAL.value == "social"
        assert Suite.CREATIVE.value == "creative"
        assert Suite.PROCESSING.value == "processing"

    def test_suite_precedence(self):
        assert Suite.PROCESSING.precedence > Suite.WORK.precedence

class TestSessionState:
    def test_default_state(self):
        state = SessionState()
        assert state.current_suite is None
        assert state.active_feature is None
        assert state.recent_classifications == []
        assert state.processing_cooldown_remaining == 0

    def test_is_in_processing_cooldown(self):
        state = SessionState(processing_cooldown_remaining=2)
        assert state.is_in_processing_cooldown

    def test_record_classification_caps_history(self):
        state = SessionState()
        for _ in range(10):
            state.record_classification(MessageClass.CONVERSE)
        assert len(state.recent_classifications) == 5

class TestFeatureCandidate:
    def test_score_computation(self):
        candidate = FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain="meals",
            score_inputs={"relevance": 0.8, "urgency": 0.5, "suite_fit": 1.0,
                          "freshness": 0.2, "queue_age": 0.0, "domain_match": 1.0},
        )
        weights = {
            "relevance": 0.35, "urgency": 0.25, "suite_fit": 0.20,
            "freshness": -0.10, "queue_age": 0.05, "domain_match": 0.05,
        }
        score = candidate.compute_score(weights)
        expected = (0.35*0.8 + 0.25*0.5 + 0.20*1.0 + (-0.10)*0.2 + 0.05*0.0 + 0.05*1.0)
        assert abs(score - expected) < 1e-9

class TestMessageEnvelope:
    def test_envelope_tracks_reentry(self):
        env = MessageEnvelope(text="hello", has_attachment=False)
        assert env.reentry_count == 0
        env.reentry_count += 1
        assert env.reentry_count == 1
