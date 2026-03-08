"""Distillation state machine -- tracks lifecycle per topic."""

# Design rationale:
# Manages the distillation lifecycle (idle -> candidate -> compress -> validate -> verify).
# Enforces valid state transitions via a whitelist and tracks retry counts.
# Key invariant: retry_count < max_retries for retry eligibility (strict less-than).

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml


class DistillationStatus(Enum):
    IDLE = "idle"
    CANDIDATE = "candidate"
    COMPRESSING = "compressing"
    COMPRESSED = "compressed"
    VALIDATED = "validated"
    FAILED = "failed"
    VERIFIED = "verified"


# Valid state transitions
VALID_TRANSITIONS: dict[DistillationStatus, set[DistillationStatus]] = {
    DistillationStatus.IDLE: {DistillationStatus.CANDIDATE},
    DistillationStatus.CANDIDATE: {DistillationStatus.COMPRESSING, DistillationStatus.IDLE},
    DistillationStatus.COMPRESSING: {DistillationStatus.COMPRESSED, DistillationStatus.FAILED},
    DistillationStatus.COMPRESSED: {DistillationStatus.VALIDATED, DistillationStatus.FAILED},
    DistillationStatus.VALIDATED: {DistillationStatus.VERIFIED, DistillationStatus.IDLE},
    DistillationStatus.FAILED: {DistillationStatus.CANDIDATE, DistillationStatus.IDLE},
    DistillationStatus.VERIFIED: {DistillationStatus.IDLE},
}


@dataclass
class TopicDistillationState:
    """Lifecycle state for a single topic's distillation."""

    topic: str
    status: DistillationStatus = DistillationStatus.IDLE
    last_distilled: datetime | None = None
    semantic_diff_result: str | None = None  # "pass" or "fail"
    brew_validation: str | None = None  # "pending", "confirmed", "corrected", None
    brew_attempts: int = 0
    max_brew_attempts: int = 2
    retry_count: int = 0
    max_retries: int = 2

    def can_transition(self, to: DistillationStatus) -> bool:
        """Check if transition is valid."""
        return to in VALID_TRANSITIONS.get(self.status, set())

    def transition(self, to: DistillationStatus) -> None:
        """Transition to a new status. Raises ValueError if invalid."""
        if not self.can_transition(to):
            raise ValueError(
                f"Invalid transition: {self.status.value} -> {to.value}"
            )
        self.status = to

        if to == DistillationStatus.VALIDATED:
            self.last_distilled = datetime.now(timezone.utc)
            self.semantic_diff_result = "pass"
            self.brew_validation = "pending"
        elif to == DistillationStatus.FAILED:
            self.semantic_diff_result = "fail"
            self.retry_count += 1
        elif to == DistillationStatus.VERIFIED:
            self.brew_validation = "confirmed"
        elif to == DistillationStatus.IDLE:
            self.retry_count = 0

    def should_retry(self) -> bool:
        """Check if a failed distillation should be retried."""
        return (
            self.status == DistillationStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def needs_brew_validation(self) -> bool:
        """Check if this topic needs conversational validation via a Brew."""
        return (
            self.status == DistillationStatus.VALIDATED
            and self.brew_validation == "pending"
            and self.brew_attempts < self.max_brew_attempts
        )


@dataclass
class DistillationStateMachine:
    """Manages distillation lifecycle for all topics."""

    topics: dict[str, TopicDistillationState] = field(default_factory=dict)

    def get_or_create(self, topic: str) -> TopicDistillationState:
        """Get existing state or create a new IDLE state."""
        if topic not in self.topics:
            self.topics[topic] = TopicDistillationState(topic=topic)
        return self.topics[topic]

    def get_candidates(self) -> list[TopicDistillationState]:
        """Return all topics in CANDIDATE status."""
        return [t for t in self.topics.values() if t.status == DistillationStatus.CANDIDATE]

    def get_pending_validations(self) -> list[TopicDistillationState]:
        """Return topics needing brew validation."""
        return [t for t in self.topics.values() if t.needs_brew_validation()]

    def get_retryable(self) -> list[TopicDistillationState]:
        """Return failed topics eligible for retry."""
        return [t for t in self.topics.values() if t.should_retry()]

    def save(self, path: Path) -> None:
        """Save state machine to YAML."""
        data = {}
        for topic, state in self.topics.items():
            entry: dict[str, object] = {
                "status": state.status.value,
                "retry_count": state.retry_count,
                "brew_attempts": state.brew_attempts,
            }
            if state.last_distilled:
                entry["last_distilled"] = state.last_distilled.isoformat()
            if state.semantic_diff_result:
                entry["semantic_diff_result"] = state.semantic_diff_result
            if state.brew_validation:
                entry["brew_validation"] = state.brew_validation
            data[topic] = entry

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(data, default_flow_style=False))

    @classmethod
    def load(cls, path: Path) -> DistillationStateMachine:
        """Load state machine from YAML."""
        sm = cls()
        if not path.exists():
            return sm
        data = yaml.safe_load(path.read_text()) or {}
        for topic, entry in data.items():
            state = TopicDistillationState(
                topic=topic,
                status=DistillationStatus(entry.get("status", "idle")),
                retry_count=entry.get("retry_count", 0),
                brew_attempts=entry.get("brew_attempts", 0),
            )
            if entry.get("last_distilled"):
                state.last_distilled = datetime.fromisoformat(entry["last_distilled"])
            state.semantic_diff_result = entry.get("semantic_diff_result")
            state.brew_validation = entry.get("brew_validation")
            sm.topics[topic] = state
        return sm
