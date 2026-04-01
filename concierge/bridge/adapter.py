"""Telegram ↔ Concierge type conversions.

Pure conversion functions that translate between Telegram update primitives
and Concierge domain types.  No Telegram library imports — callers extract
raw fields from Update objects and pass them here, keeping this module
unit-testable without PTB mocking.
"""

# Design rationale:
# Anti-corruption layer between Telegram's Update model and Concierge's
# MessageEnvelope.  Callers extract primitives (str, bool, datetime) from
# the Telegram Update and pass them here; this module never imports
# python-telegram-bot.  Truncation splits at the last sentence boundary
# before the limit so users don't get mid-word cuts.

from __future__ import annotations

from datetime import datetime

from concierge.models import FeatureCandidate, MessageEnvelope


def update_to_envelope(
    text: str,
    has_attachment: bool,
    attachment_type: str | None,
    timestamp: datetime,
) -> MessageEnvelope:
    """Build a :class:`MessageEnvelope` from extracted Telegram update fields."""
    return MessageEnvelope(
        text=text or "",
        has_attachment=has_attachment,
        attachment_type=attachment_type,
        timestamp=timestamp,
    )


def feature_to_prompt_context(feature: FeatureCandidate | None) -> str:
    """Convert a selected feature into a system prompt fragment.

    Returns an empty string when no feature was selected so callers can
    always concatenate the result without conditional checks.
    """
    if feature is None:
        return ""
    return (
        f"Surface this {feature.feature_type.value} about "
        f"{feature.domain} to the user naturally."
    )


# Telegram hard cap on a single message
_TELEGRAM_MAX_LENGTH = 4096
_TRUNCATION_INDICATOR = "..."


def truncate_response(text: str, max_length: int = _TELEGRAM_MAX_LENGTH) -> str:
    """Truncate *text* at a sentence boundary if it exceeds *max_length*.

    Splits at the last period-followed-by-space before the limit so the
    user sees complete sentences.  Falls back to a hard cut if no sentence
    boundary exists within range.
    """
    if len(text) <= max_length:
        return text

    # leave room for the truncation indicator
    budget = max_length - len(_TRUNCATION_INDICATOR)
    chunk = text[:budget]

    # try to break at last sentence boundary
    last_period = chunk.rfind(". ")
    if last_period > 0:
        return chunk[: last_period + 1] + _TRUNCATION_INDICATOR

    return chunk + _TRUNCATION_INDICATOR
