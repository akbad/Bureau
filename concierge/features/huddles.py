"""Huddle conversation engine — guided multi-turn Q&A sessions.

Huddles are structured interview-style conversations where the Concierge
learns about the user.  There are six huddle types:

- **initial**: getting-to-know-you (triggered when core.md is absent)
- **valet-setup**: configure a new valet
- **probe-setup**: configure a new probe
- **personality**: adjust tone and communication preferences
- **goals**: discover and record user goals
- **check-in**: periodic catch-up (every 90 days)
"""

# Design rationale:
# Manages multi-turn structured conversations that onboard and periodically
# re-engage the user. A dataclass tracks state so huddles can survive across
# session boundaries without requiring a database.
# Key invariant: at most one huddle is active per session; candidate evaluation
# gates on active_feature to prevent overlapping huddles.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from concierge.models import FeatureCandidate, FeatureType, MessageEnvelope, SessionState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Huddle state
# ---------------------------------------------------------------------------


@dataclass
class HuddleState:
    """Tracks the state of an active huddle conversation."""

    huddle_type: str  # "initial", "valet-setup", "probe-setup", "personality", "goals", "check-in"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    question_index: int = 0  # Current question in the sequence
    answers: dict[str, str] = field(default_factory=dict)  # question_key -> user's answer
    completed: bool = False

    def advance(self) -> None:
        """Move to the next question in the sequence."""
        self.question_index += 1

    def record_answer(self, key: str, answer: str) -> None:
        """Store an answer and advance."""
        self.answers[key] = answer
        self.advance()


# ---------------------------------------------------------------------------
# Question definitions
# ---------------------------------------------------------------------------

# Huddle type -> list of (question_key, question_text) pairs
HUDDLE_QUESTIONS: dict[str, list[tuple[str, str]]] = {
    "initial": [
        ("favorite_food", "What's your favorite thing to cook — or order?"),
        ("daily_routine", "Walk me through a typical day for you"),
        ("free_time", "What do you do when you have a free afternoon?"),
        ("important_people", "Who are the people you'd never want to forget a birthday for?"),
        ("communication", "How chatty do you want me to be — should I check in daily or just when you text me?"),
    ],
    "personality": [
        ("tone_preference", "Right now I can be warm, playful, or crisp. What sounds right?"),
        ("emoji_level", "How about emoji — more, less, or about the same?"),
        ("detail_level", "Do you prefer short messages or is it OK if I'm detailed sometimes?"),
        ("proactivity", "Should I suggest things before you ask, or wait for you?"),
    ],
    "goals": [
        ("current_goal", "What's something you're working toward right now — big or small?"),
        ("goal_domain", "Is that more of a career thing, personal, social, or learning?"),
        ("check_in_pref", "Want me to check in on this periodically, or just keep it in mind?"),
    ],
    "check-in": [
        ("changes", "It's been a while — anything changed? New interests, new goals, different schedule?"),
        ("satisfaction", "How's everything been working? Anything I should do differently?"),
    ],
    "valet-setup": [
        ("purpose", "What would you like this to help you with?"),
        ("schedule", "When should I run it? Any specific day/time?"),
        ("intensity", "How hands-on should I be — light suggestions or step-by-step guidance?"),
    ],
    "probe-setup": [
        ("topics", "What topics are you interested in? Can be broad or specific"),
        ("depth", "How deep should I go — quick headlines or detailed analysis?"),
        ("frequency", "How often — weekly, bi-weekly, or only when something noteworthy happens?"),
        ("context", "What's your current situation with this topic?"),
    ],
}


# ---------------------------------------------------------------------------
# Question accessors
# ---------------------------------------------------------------------------


def get_current_question(state: HuddleState) -> str | None:
    """Return the current question text, or None if huddle is complete."""
    questions = HUDDLE_QUESTIONS.get(state.huddle_type, [])
    if state.question_index >= len(questions):
        return None
    return questions[state.question_index][1]


def get_current_question_key(state: HuddleState) -> str | None:
    """Return the current question key, or None if huddle is complete."""
    questions = HUDDLE_QUESTIONS.get(state.huddle_type, [])
    if state.question_index >= len(questions):
        return None
    return questions[state.question_index][0]


# ---------------------------------------------------------------------------
# Reply processing
# ---------------------------------------------------------------------------


def process_huddle_reply(state: HuddleState, reply_text: str) -> str | None:
    """Process a user reply in an active huddle.

    Records the answer, advances to next question.
    Returns the next question text, or None if huddle is complete.
    """
    key = get_current_question_key(state)
    if key is None:
        state.completed = True
        return None

    state.record_answer(key, reply_text)

    next_q = get_current_question(state)
    if next_q is None:
        state.completed = True
    return next_q


# ---------------------------------------------------------------------------
# Candidacy evaluation
# ---------------------------------------------------------------------------

_CHECKIN_INTERVAL_DAYS = 90
_GOALS_TOPIC_THRESHOLD = 3


def evaluate_huddle_candidates(
    session: SessionState,
    data_dir: Path,
    envelope: MessageEnvelope | None = None,
    now: datetime | None = None,
) -> list[FeatureCandidate]:
    """Check if a huddle should be initiated.

    Triggers:
    1. Initial huddle: core.md doesn't exist (first use)
    2. Check-in: last check-in > 90 days ago (from state/last-checkin.txt)
    3. Goals: user has 3+ topic files but no goals recorded

    Does NOT return candidates if a huddle is already active.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # --- Gate: huddle already active ---
    if session.active_feature is FeatureType.HUDDLE:
        return []

    candidates: list[FeatureCandidate] = []

    # --- Trigger 1: initial huddle (core.md missing) ---
    core_file = data_dir / "core.md"
    if not core_file.exists():
        candidates.append(
            FeatureCandidate(
                feature_type=FeatureType.HUDDLE,
                domain="initial",
                score_inputs={
                    "urgency": 1.0,
                    "relevance": 1.0,
                },
                metadata={"huddle_type": "initial"},
            )
        )
        # If no core.md, the initial huddle is the priority — skip other checks
        return candidates

    # --- Trigger 2: check-in (> 90 days since last) ---
    checkin_file = data_dir / "state" / "last-checkin.txt"
    if checkin_file.exists():
        try:
            last_checkin = datetime.fromisoformat(checkin_file.read_text().strip())
            if now - last_checkin > timedelta(days=_CHECKIN_INTERVAL_DAYS):
                candidates.append(
                    FeatureCandidate(
                        feature_type=FeatureType.HUDDLE,
                        domain="check-in",
                        score_inputs={
                            "urgency": 0.5,
                            "relevance": 0.8,
                        },
                        metadata={"huddle_type": "check-in"},
                    )
                )
        except (ValueError, OSError) as exc:
            logger.warning("Malformed or unreadable check-in file, skipping: %s", exc)

    # --- Trigger 3: goals (3+ topic files, no goals.md) ---
    topics_dir = data_dir / "topics"
    goals_file = data_dir / "goals.md"
    if topics_dir.exists() and not goals_file.exists():
        topic_files = [f for f in topics_dir.iterdir() if f.is_file() and f.suffix == ".md"]
        if len(topic_files) >= _GOALS_TOPIC_THRESHOLD:
            candidates.append(
                FeatureCandidate(
                    feature_type=FeatureType.HUDDLE,
                    domain="goals",
                    score_inputs={
                        "urgency": 0.3,
                        "relevance": 0.7,
                    },
                    metadata={"huddle_type": "goals"},
                )
            )

    return candidates
