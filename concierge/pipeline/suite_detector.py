"""Suite detector — determines the active Suite from message content and context.

Checks message text against keyword sets in precedence order, falls back to
session state and time-of-day heuristics.
"""

# Design rationale:
# Suite detection uses a keyword-set approach with substring matching (via
# `kw in text_lower`) rather than word-boundary regex so that multi-word
# phrases like "burned out" and "dinner with" are naturally supported.
# Keyword sets are checked in strict precedence order (Processing > Social >
# Creative > Work) because higher-precedence suites represent more sensitive
# states that must not be overridden by a lower-priority match.  When no
# keyword matches, the detector falls back to session persistence (sticky
# suite) and finally to time-of-day heuristics, ensuring the system always
# returns a concrete Suite and never None.

from __future__ import annotations

from datetime import time

from concierge.models import MessageEnvelope, SessionState, Suite

# ---------------------------------------------------------------------------
# Keyword sets (frozensets for immutability and fast membership testing)
# ---------------------------------------------------------------------------

_PROCESSING_KEYWORDS: frozenset[str] = frozenset(
    {
        "stressed",
        "overwhelmed",
        "anxious",
        "upset",
        "frustrated",
        "sad",
        "crying",
        "angry",
        "hurt",
        "scared",
        "worried",
        "depressed",
        "ugh",
        "terrible",
        "awful",
        "exhausted",
        "drained",
        "burned out",
        "burnt out",
    }
)

_SOCIAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "friends",
        "party",
        "dinner with",
        "hanging out",
        "plans with",
        "birthday",
        "wedding",
        "date",
        "meetup",
        "brunch",
        "get together",
    }
)

_CREATIVE_KEYWORDS: frozenset[str] = frozenset(
    {
        "brainstorm",
        "decorat",
        "outfit",
        "writing",
        "painting",
        "craft",
        "design",
        "idea",
        "project",
        "create",
        "inspiration",
    }
)

_WORK_KEYWORDS: frozenset[str] = frozenset(
    {
        "work",
        "meeting",
        "deadline",
        "report",
        "presentation",
        "boss",
        "career",
        "job",
        "salary",
        "resume",
        "interview",
        "task",
        "productivity",
    }
)

# Ordered list of (keyword_set, suite) pairs — checked in precedence order.
_KEYWORD_RULES: list[tuple[frozenset[str], Suite]] = [
    (_PROCESSING_KEYWORDS, Suite.PROCESSING),
    (_SOCIAL_KEYWORDS, Suite.SOCIAL),
    (_CREATIVE_KEYWORDS, Suite.CREATIVE),
    (_WORK_KEYWORDS, Suite.WORK),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_suite(
    envelope: MessageEnvelope,
    session: SessionState,
    current_time: time | None = None,
) -> Suite:
    """Determine the active :class:`Suite` for an incoming message.

    Detection follows a strict precedence order:

    1. **Keyword match** — Processing > Social > Creative > Work.
    2. **Session persistence** — if *session.current_suite* is set and no
       keyword matched, keep the existing suite.
    3. **Time-of-day fallback** — evening/night (8 pm–7 am) -> REST,
       business hours (9 am–5 pm) -> WORK.
    4. **Default** — REST.
    """
    text_lower = envelope.text.lower()

    # 1. Keyword-based detection (precedence order)
    for keywords, suite in _KEYWORD_RULES:
        if any(kw in text_lower for kw in keywords):
            return suite

    # 2. Persist current session suite if no strong signal
    if session.current_suite is not None:
        return session.current_suite

    # 3. Time-of-day fallback
    if current_time is not None:
        # Evening/night: 8 pm (20:00) through 6:59 am -> REST
        if current_time >= time(20, 0) or current_time < time(7, 0):
            return Suite.REST
        # Business hours: 9 am through 4:59 pm -> WORK
        if time(9, 0) <= current_time < time(17, 0):
            return Suite.WORK

    # 4. Default
    return Suite.REST
