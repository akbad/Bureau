"""Core data models for the Bureau Concierge system.

Defines message types, session state, feature candidates, and queue items
used throughout the concierge pipeline.
"""

# Design rationale:
# Central domain types shared across every pipeline stage and feature evaluator.
# FeatureCandidate uses identity-based __hash__ (id(self)) because mutable
# score_inputs make value-based hashing unsafe, yet candidates must be usable
# as dict keys in the lottery's priority_scores map.  Suite precedence is kept
# in a manual dict (_SUITE_PRECEDENCE) rather than auto-numbering so that
# reordering enum members never silently changes priority semantics.  All Enum
# values are lowercase strings to stay YAML-friendly (serialised configs and
# schedule files reference these values directly).

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MessageClass(Enum):
    """Classification of an incoming message."""

    REPLY = "reply"
    QUERY = "query"
    CONVERSE = "converse"
    COMMAND = "command"
    MEDIA = "media"


class Suite(Enum):
    """Operational suite — determines which features are eligible."""

    WORK = "work"
    REST = "rest"
    SOCIAL = "social"
    CREATIVE = "creative"
    PROCESSING = "processing"

    @property
    def precedence(self) -> int:
        """Return the numeric precedence for this suite (higher = more urgent)."""
        return _SUITE_PRECEDENCE[self]


_SUITE_PRECEDENCE: dict[Suite, int] = {
    Suite.REST: 1,
    Suite.WORK: 2,
    Suite.CREATIVE: 3,
    Suite.SOCIAL: 4,
    Suite.PROCESSING: 5,
}


class FeatureType(Enum):
    """Kind of feature that can be surfaced to the user."""

    DISPATCH = "dispatch"
    BREW = "brew"
    PROBE = "probe"
    VALET = "valet"
    HUDDLE = "huddle"


class QueueItemState(Enum):
    """Lifecycle state of an item in the delivery queue."""

    QUEUED = "queued"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    DISMISSED = "dismissed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MessageEnvelope:
    """Wraps a single inbound message with routing metadata."""

    text: str
    has_attachment: bool
    attachment_type: str | None = None
    timestamp: datetime = field(default_factory=_utcnow)
    reentry_count: int = 0
    classification: MessageClass | None = None
    confidence: float = 0.0


@dataclass
class SessionState:
    """Tracks the current user session context across the pipeline."""

    current_suite: Suite | None = None
    suite_since: datetime | None = None
    active_feature: FeatureType | None = None
    active_feature_id: str | None = None
    feature_started_at: datetime | None = None
    recent_classifications: list[MessageClass] = field(default_factory=list)
    recent_suites: list[Suite] = field(default_factory=list)
    last_message_at: datetime | None = None
    processing_cooldown_remaining: int = 0

    @property
    def is_in_processing_cooldown(self) -> bool:
        """Return *True* while the processing cooldown is active."""
        return self.processing_cooldown_remaining > 0

    def record_classification(
        self, cls: MessageClass, *, max_history: int = 5
    ) -> None:
        """Append *cls* to recent history, trimming to *max_history*."""
        self.recent_classifications.append(cls)
        if len(self.recent_classifications) > max_history:
            self.recent_classifications = self.recent_classifications[
                -max_history:
            ]

    def record_suite(self, suite: Suite, *, max_history: int = 5) -> None:
        """Record *suite* as the current suite and append to recent history."""
        self.current_suite = suite
        self.suite_since = _utcnow()
        self.recent_suites.append(suite)
        if len(self.recent_suites) > max_history:
            self.recent_suites = self.recent_suites[-max_history:]


@dataclass
class FeatureCandidate:
    """A scored candidate for feature delivery."""

    feature_type: FeatureType
    domain: str
    score_inputs: dict[str, float]
    content: str | None = None
    metadata: dict[str, Any] | None = None
    lottery_promoted: bool = False

    def __hash__(self) -> int:
        """Identity-based hash so candidates can be used as dict keys."""
        return id(self)

    def compute_score(self, weights: dict[str, float]) -> float:
        """Compute a weighted score (dot product of *score_inputs* and *weights*).

        Keys present in *score_inputs* but absent from *weights* (and vice
        versa) are silently ignored — only shared keys contribute.
        """
        return sum(
            self.score_inputs[k] * weights[k]
            for k in self.score_inputs
            if k in weights
        )


@dataclass
class QueueItem:
    """An item sitting in the delivery queue awaiting presentation."""

    candidate: FeatureCandidate
    queued_at: datetime = field(default_factory=_utcnow)
    state: QueueItemState = QueueItemState.QUEUED
    priority: float = 0.0
    context_snapshot: dict[str, Any] | None = None
