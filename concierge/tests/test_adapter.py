"""Tests for the Telegram adapter — pure conversion functions."""

from datetime import datetime, timezone

from concierge.bridge.adapter import (
    feature_to_prompt_context,
    truncate_response,
    update_to_envelope,
)
from concierge.models import FeatureCandidate, FeatureType


class TestUpdateToEnvelope:
    def test_text_message(self):
        ts = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)
        env = update_to_envelope("hello", False, None, ts)
        assert env.text == "hello"
        assert env.has_attachment is False
        assert env.attachment_type is None
        assert env.timestamp == ts

    def test_with_photo_attachment(self):
        ts = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)
        env = update_to_envelope("caption", True, "photo", ts)
        assert env.has_attachment is True
        assert env.attachment_type == "photo"

    def test_empty_text_coerced_to_empty_string(self):
        ts = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)
        env = update_to_envelope("", False, None, ts)
        assert env.text == ""


class TestFeatureToPromptContext:
    def test_with_feature(self):
        feature = FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="meals",
            score_inputs={"relevance": 0.8},
        )
        result = feature_to_prompt_context(feature)
        assert "dispatch" in result
        assert "meals" in result

    def test_none_returns_empty(self):
        assert feature_to_prompt_context(None) == ""


class TestTruncateResponse:
    def test_under_limit_passes_through(self):
        text = "Short message."
        assert truncate_response(text, 100) == text

    def test_over_limit_truncates_at_sentence(self):
        text = "First sentence. Second sentence. Third sentence is very long."
        result = truncate_response(text, 40)
        assert result.endswith("...")
        assert len(result) <= 40
        # should cut at a sentence boundary
        assert "First sentence." in result

    def test_no_sentence_boundary_hard_cuts(self):
        text = "A" * 200
        result = truncate_response(text, 50)
        assert len(result) <= 50
        assert result.endswith("...")
