"""Tests for the model-based classifier (Stage 0b)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from concierge.classifier.model import classify_with_model
_has_train_deps = True
try:
    from concierge.classifier.train import LABEL_MAP, load_training_data
except ImportError:
    _has_train_deps = False
from concierge.models import MessageClass

_has_ml_deps = True
try:
    import onnxruntime  # noqa: F401
    import transformers  # noqa: F401
except ImportError:
    _has_ml_deps = False

_model_exists = Path("concierge/classifier/model.onnx").exists()


class TestModelClassifier:
    @pytest.mark.skipif(
        not _has_ml_deps or not _model_exists,
        reason="ML deps not installed or model not trained",
    )
    def test_classifies_query(self):
        result, confidence = classify_with_model("what should I eat for dinner?")
        assert result == MessageClass.QUERY
        assert confidence > 0.5

    def test_returns_tuple_of_class_and_confidence(self):
        result, confidence = classify_with_model("hello")
        assert isinstance(result, MessageClass)
        assert isinstance(confidence, float)


@pytest.mark.skipif(not _has_train_deps, reason="ML training deps not installed")
class TestLoadTrainingData:
    def test_loads_jsonl_files(self, tmp_path):
        """load_training_data parses JSONL files and maps labels to ints."""
        data = [
            {"text": "hello there", "label": "REPLY"},
            {"text": "what time is it?", "label": "QUERY"},
            {"text": "run tests", "label": "COMMAND"},
        ]
        jsonl_file = tmp_path / "sample.jsonl"
        jsonl_file.write_text(
            "\n".join(json.dumps(row) for row in data) + "\n"
        )
        with patch("concierge.classifier.train.TRAINING_DATA_DIR", tmp_path):
            texts, labels = load_training_data()

        assert texts == ["hello there", "what time is it?", "run tests"]
        assert labels == [LABEL_MAP["REPLY"], LABEL_MAP["QUERY"], LABEL_MAP["COMMAND"]]

    def test_empty_directory(self, tmp_path):
        """Returns empty lists when no JSONL files exist."""
        with patch("concierge.classifier.train.TRAINING_DATA_DIR", tmp_path):
            texts, labels = load_training_data()
        assert texts == []
        assert labels == []
