"""Model-based message classifier stub (Stage 0b).

Provides ONNX DistilBERT inference for message classification.
When the model file is not available (the usual case during early
development), the function returns a safe fallback of
``(MessageClass.CONVERSE, 0.0)``.
"""

# Design rationale:
# Wraps ONNX DistilBERT inference behind a lazy-init cache so the tokenizer
# and session are loaded once and reused across calls.
# Falls back to CONVERSE with 0.0 confidence when model/runtime is unavailable.
# Key invariant: never raises — all errors are caught and produce fallback output.

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..config.loader import get_classifier_config
from ..models import MessageClass
from . import MAX_LENGTH

logger = logging.getLogger(__name__)

# Maps model output indices to MessageClass values.
_CLASS_MAP: dict[int, MessageClass] = {
    0: MessageClass.REPLY,
    1: MessageClass.QUERY,
    2: MessageClass.CONVERSE,
    3: MessageClass.COMMAND,
}

_FALLBACK: tuple[MessageClass, float] = (MessageClass.CONVERSE, 0.0)

# Module-level cache for tokenizer and ONNX session
_cached_session = None
_cached_tokenizer = None


def _get_model(model_path: str | Path, tokenizer_name: str) -> tuple[Any, Any]:
    """Return cached (session, tokenizer), loading on first call."""
    global _cached_session, _cached_tokenizer
    if _cached_session is None:
        from onnxruntime import InferenceSession
        from transformers import AutoTokenizer
        _cached_session = InferenceSession(str(model_path))
        _cached_tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    return _cached_session, _cached_tokenizer


def classify_with_model(text: str) -> tuple[MessageClass, float]:
    """Classify *text* using the ONNX DistilBERT model.

    Parameters
    ----------
    text:
        The raw message text to classify.

    Returns
    -------
    tuple[MessageClass, float]
        A ``(message_class, confidence)`` pair.  When the model file is
        missing or cannot be loaded, the fallback
        ``(MessageClass.CONVERSE, 0.0)`` is returned.
    """
    config = get_classifier_config()
    model_cfg = config.get("model", {})
    model_path = Path(model_cfg.get("path", "concierge/classifier/model.onnx"))

    if not model_path.exists():
        logger.warning(
            "ONNX model not found at %s — returning fallback classification",
            model_path,
        )
        return _FALLBACK

    # --- ONNX inference path (requires onnxruntime + transformers) ----------
    try:
        import numpy as np  # noqa: F811
        import onnxruntime  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        logger.warning(
            "onnxruntime and/or transformers not installed — "
            "returning fallback classification"
        )
        return _FALLBACK

    try:
        tokenizer_name = model_cfg.get("tokenizer", "distilbert-base-uncased")
        session, tokenizer = _get_model(model_path, tokenizer_name)

        inputs = tokenizer(
            text,
            return_tensors="np",
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
        )

        ort_inputs = {k: v for k, v in inputs.items() if k in {i.name for i in session.get_inputs()}}
        logits = session.run(None, ort_inputs)[0]

        # softmax
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probabilities = exp_logits / exp_logits.sum(axis=-1, keepdims=True)

        predicted_idx = int(np.argmax(probabilities, axis=-1)[0])
        confidence = float(probabilities[0][predicted_idx])

        message_class = _CLASS_MAP.get(predicted_idx, MessageClass.CONVERSE)
        return message_class, confidence

    except Exception:
        logger.warning(
            "ONNX inference failed — returning fallback classification",
            exc_info=True,
        )
        return _FALLBACK
