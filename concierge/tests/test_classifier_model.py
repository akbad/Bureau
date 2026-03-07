"""Tests for the model-based classifier stub (Stage 0b)."""

from concierge.classifier.model import classify_with_model
from concierge.models import MessageClass


class TestModelClassifier:
    def test_fallback_when_no_model(self):
        result, confidence = classify_with_model("what should I eat for dinner?")
        assert result == MessageClass.CONVERSE
        assert confidence == 0.0

    def test_returns_tuple_of_class_and_confidence(self):
        result, confidence = classify_with_model("hello")
        assert isinstance(result, MessageClass)
        assert isinstance(confidence, float)
