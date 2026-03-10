"""Tests for the model-based classifier (Stage 0b)."""

import pytest

from concierge.classifier.model import classify_with_model
from concierge.models import MessageClass

_has_ml_deps = True
try:
    import onnxruntime  # noqa: F401
    import transformers  # noqa: F401
except ImportError:
    _has_ml_deps = False


class TestModelClassifier:
    @pytest.mark.skipif(not _has_ml_deps, reason="ML deps not installed")
    def test_classifies_query(self):
        result, confidence = classify_with_model("what should I eat for dinner?")
        assert result == MessageClass.QUERY
        assert confidence > 0.5

    def test_returns_tuple_of_class_and_confidence(self):
        result, confidence = classify_with_model("hello")
        assert isinstance(result, MessageClass)
        assert isinstance(confidence, float)
