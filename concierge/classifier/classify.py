"""Unified classifier pipeline (Stage 0a -> 0b -> 0c).

Chains deterministic rules, model inference, and fuzzy command matching
into a single entry point that resolves every incoming message to a
:class:`~concierge.models.MessageClass`.
"""

# Design rationale:
# Classification proceeds through a 3-stage chain: (0a) deterministic rules
# for unambiguous patterns like attachments or single-word commands, (0b) model
# inference for everything else, and (0c) fuzzy command-verb reconciliation to
# catch commands the model misses and demote false-positive COMMANDs.  The
# fuzzy upgrade (0c) deliberately does NOT update envelope.confidence because
# the verb match is a binary signal, not a probability; mixing it into the
# model's confidence would produce a misleading number.  The chain short-
# circuits on stage 0a (confidence=1.0) to avoid unnecessary model loading.

from __future__ import annotations

import logging

from ..config.loader import get_classifier_config
from ..models import MessageClass, MessageEnvelope
from .deterministic import classify_deterministic
from .fuzzy_commands import match_command_verb
from .model import classify_with_model

logger = logging.getLogger(__name__)


def classify_message(
    envelope: MessageEnvelope,
    active_feature: str | None,
) -> MessageEnvelope:
    """Classify *envelope* by chaining the three classifier stages.

    The function mutates *envelope* in-place (setting ``classification``
    and ``confidence``) and returns the same object for convenience.

    Stages
    ------
    0a  **Deterministic** -- fast rule-based check.  If it yields a class,
        the envelope is stamped with ``confidence=1.0`` and returned
        immediately.

    0b  **Model** -- ONNX DistilBERT inference (falls back to
        ``(CONVERSE, 0.0)`` when no model file is present).

    0c  **Fuzzy commands** -- reconciles the model prediction with fuzzy
        verb matching:

        * If the model said COMMAND but no verb is found and confidence
          is below the configured threshold, downgrade to CONVERSE.
        * If the model did *not* say COMMAND but a verb *is* found,
          upgrade to COMMAND.

    Parameters
    ----------
    envelope:
        The incoming message envelope to classify.
    active_feature:
        Identifier of the currently-active feature, or ``None``.

    Returns
    -------
    MessageEnvelope
        The same *envelope* instance, with ``classification`` and
        ``confidence`` populated.
    """
    # --- Stage 0a: deterministic rules -------------------------------------
    deterministic_result = classify_deterministic(envelope, active_feature)
    if deterministic_result is not None:
        envelope.classification = deterministic_result
        envelope.confidence = 1.0
        logger.debug(
            "Deterministic classifier resolved to %s", deterministic_result
        )
        return envelope

    # --- Stage 0b: model inference -----------------------------------------
    model_class, model_confidence = classify_with_model(envelope.text)
    envelope.classification = model_class
    envelope.confidence = model_confidence
    logger.debug(
        "Model classifier returned %s (confidence=%.3f)",
        model_class,
        model_confidence,
    )

    # --- Stage 0c: fuzzy command reconciliation ----------------------------
    config = get_classifier_config()
    confidence_threshold: float = config.get("model", {}).get(
        "confidence_threshold", 0.7
    )

    verb = match_command_verb(envelope.text)

    if model_class == MessageClass.COMMAND:
        # Model thinks it's a command -- verify with fuzzy match.
        if verb is None and model_confidence < confidence_threshold:
            envelope.classification = MessageClass.CONVERSE
            logger.debug(
                "Downgraded COMMAND -> CONVERSE (no verb, confidence %.3f < %.3f)",
                model_confidence,
                confidence_threshold,
            )
    else:
        # Model did NOT say COMMAND -- but if fuzzy finds a verb, upgrade.
        if verb is not None:
            envelope.classification = MessageClass.COMMAND
            logger.debug(
                "Upgraded %s -> COMMAND (fuzzy matched verb %r)",
                model_class,
                verb,
            )

    return envelope
