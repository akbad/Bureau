"""Tests for the unified classifier pipeline (Stage 0a -> 0b -> 0c)."""

import pytest

from concierge.classifier.classify import classify_message
from concierge.models import MessageClass, MessageEnvelope

_has_ml_deps = True
try:
    import onnxruntime  # noqa: F401
    import transformers  # noqa: F401
except ImportError:
    _has_ml_deps = False


class TestUnifiedClassifier:
    def test_attachment_short_circuits_to_media(self):
        env = MessageEnvelope(text="", has_attachment=True)
        result = classify_message(env, active_feature=None)
        assert result.classification == MessageClass.MEDIA

    def test_emoji_short_circuits_to_reply(self):
        env = MessageEnvelope(text="\U0001f44d", has_attachment=False)
        result = classify_message(env, active_feature=None)
        assert result.classification == MessageClass.REPLY

    @pytest.mark.skipif(not _has_ml_deps, reason="ML deps not installed")
    def test_normal_text_falls_through_to_model(self):
        env = MessageEnvelope(text="what should I eat for dinner?", has_attachment=False)
        result = classify_message(env, active_feature=None)
        assert result.classification == MessageClass.QUERY  # model classifies as QUERY

    def test_command_text_gets_fuzzy_upgraded(self):
        env = MessageEnvelope(text="pause the fitness probe", has_attachment=False)
        result = classify_message(env, active_feature=None)
        # Fuzzy matcher finds "pause" -> COMMAND
        assert result.classification == MessageClass.COMMAND

    def test_envelope_updated_in_place(self):
        env = MessageEnvelope(text="hello", has_attachment=False)
        result = classify_message(env, active_feature=None)
        assert result is env
        assert result.classification is not None
