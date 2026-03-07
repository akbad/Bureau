"""Deterministic message classifier (Stage 0a).

Fast, rule-based classifier that resolves obvious message types before
any model inference is needed.  Returns ``None`` when the message cannot
be classified deterministically and must fall through to the model stage.
"""

from __future__ import annotations

import re

from ..models import MessageClass, MessageEnvelope

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Exact-match tokens that count as a reply when an active feature exists.
_REPLY_TOKENS: frozenset[str] = frozenset(
    {"yes", "no", "ok", "y", "n", "sure", "nah", "yep", "nope"}
)

# Compiled regex that matches a single Unicode emoji (including skin-tone
# modifiers, ZWJ sequences, keycap sequences, and flag sequences).
#
# Since Python's ``re`` module does not support ``\p{Emoji}`` property
# escapes we spell out the major Unicode emoji ranges explicitly.
_EMOJI_CORE = (
    "["
    "\u00A9\u00AE"                   # (c) (r)
    "\u203C\u2049"                   # !! ?!
    "\u2122\u2139"                   # TM, info
    "\u2194-\u2199"                  # arrows
    "\u21A9\u21AA"                   # curved arrows
    "\u231A\u231B"                   # watch, hourglass
    "\u2328"                         # keyboard
    "\u23CF"                         # eject
    "\u23E9-\u23F3"                  # player buttons
    "\u23F8-\u23FA"                  # more player buttons
    "\u24C2"                         # circled M
    "\u25AA\u25AB"                   # small squares
    "\u25B6\u25C0"                   # play buttons
    "\u25FB-\u25FE"                  # squares
    "\u2600-\u27BF"                  # misc symbols & dingbats
    "\u2934\u2935"                   # arrows
    "\u2B05-\u2B07"                  # arrows
    "\u2B1B\u2B1C"                   # squares
    "\u2B50\u2B55"                   # star, circle
    "\u3030\u303D\u3297\u3299"       # CJK symbols
    "\U0001F004"                     # mahjong
    "\U0001F0CF"                     # joker
    "\U0001F170-\U0001F19A"          # squared letters
    "\U0001F1E0-\U0001F1FF"          # regional indicators
    "\U0001F200-\U0001F2FF"          # enclosed ideographic
    "\U0001F300-\U0001F5FF"          # misc symbols & pictographs
    "\U0001F600-\U0001F64F"          # emoticons
    "\U0001F680-\U0001F6FF"          # transport & map
    "\U0001F700-\U0001F77F"          # alchemical
    "\U0001F780-\U0001F7FF"          # geometric shapes ext
    "\U0001F800-\U0001F8FF"          # supplemental arrows-C
    "\U0001F900-\U0001F9FF"          # supplemental symbols
    "\U0001FA00-\U0001FA6F"          # chess symbols
    "\U0001FA70-\U0001FAFF"          # symbols & pictographs ext-A
    "]"
)

_SKIN_TONE = "[\U0001F3FB-\U0001F3FF]"

_SINGLE_EMOJI_RE: re.Pattern[str] = re.compile(
    r"^(?:"
    # Emoji with optional variation selector, optional ZWJ sequences,
    # optional skin-tone modifier
    + _EMOJI_CORE + r"(?:\uFE0F)?"
    r"(?:\u200D" + _EMOJI_CORE + r"(?:\uFE0F)?)*"
    + _SKIN_TONE + r"?"
    # Keycap sequences (e.g. 1️⃣)
    r"|[0-9#*]\uFE0F?\u20E3"
    # Regional indicator flag sequences (e.g. flags)
    r"|[\U0001F1E0-\U0001F1FF]{2}"
    r")$",
    re.UNICODE,
)

# Max character length for "short text" heuristic.
_SHORT_TEXT_MAX: int = 5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_deterministic(
    envelope: MessageEnvelope,
    active_feature: str | None,
) -> MessageClass | None:
    """Classify *envelope* using deterministic rules.

    Parameters
    ----------
    envelope:
        The incoming message envelope.
    active_feature:
        Identifier of the currently-active feature, or ``None`` if no
        feature is active.

    Returns
    -------
    MessageClass | None
        The resolved class, or ``None`` if the message should fall through
        to the model-based classifier.
    """
    # 1. Attachment -> MEDIA
    if envelope.has_attachment:
        return MessageClass.MEDIA

    text = envelope.text.strip()

    # 2. Single emoji -> REPLY
    if _SINGLE_EMOJI_RE.match(text):
        return MessageClass.REPLY

    # Rules 3 & 4 only apply when a feature is active.
    if active_feature is not None:
        # 3. Active feature + short text -> REPLY
        if 0 < len(text) <= _SHORT_TEXT_MAX:
            return MessageClass.REPLY

        # 4. Active feature + exact match in reply set -> REPLY
        if text.lower() in _REPLY_TOKENS:
            return MessageClass.REPLY

    # 5. Otherwise -> falls through to model
    return None
