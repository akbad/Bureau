from concierge.classifier.deterministic import classify_deterministic
from concierge.models import MessageClass, MessageEnvelope


class TestMediaDetection:
    def test_attachment_classified_as_media(self):
        env = MessageEnvelope(text="", has_attachment=True, attachment_type="image")
        assert classify_deterministic(env, active_feature=None) == MessageClass.MEDIA

    def test_attachment_with_text_still_media(self):
        env = MessageEnvelope(text="check this out", has_attachment=True)
        assert classify_deterministic(env, active_feature=None) == MessageClass.MEDIA


class TestReplyDetection:
    def test_single_emoji_is_reply(self):
        env = MessageEnvelope(text="\U0001f44d", has_attachment=False)
        assert classify_deterministic(env, active_feature=None) == MessageClass.REPLY

    def test_short_text_with_active_feature_is_reply(self):
        env = MessageEnvelope(text="yes", has_attachment=False)
        assert classify_deterministic(env, active_feature="huddle_123") == MessageClass.REPLY

    def test_exact_match_is_reply(self):
        env = MessageEnvelope(text="ok", has_attachment=False)
        assert classify_deterministic(env, active_feature="valet_1") == MessageClass.REPLY

    def test_short_text_without_active_feature_is_not_reply(self):
        env = MessageEnvelope(text="yes", has_attachment=False)
        assert classify_deterministic(env, active_feature=None) is None


class TestEmptyText:
    def test_empty_text_with_active_feature_falls_through(self):
        env = MessageEnvelope(text="", has_attachment=False)
        result = classify_deterministic(env, active_feature="huddle_123")
        assert result is None


class TestFallthrough:
    def test_normal_text_returns_none(self):
        env = MessageEnvelope(text="what should I have for dinner?", has_attachment=False)
        assert classify_deterministic(env, active_feature=None) is None

    def test_long_text_with_active_feature_returns_none(self):
        env = MessageEnvelope(
            text="actually I was thinking about something completely different",
            has_attachment=False,
        )
        assert classify_deterministic(env, active_feature="huddle_1") is None
