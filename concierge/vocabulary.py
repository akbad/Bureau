"""Vocabulary introduction tracker — gradually introduces feature terminology."""

# Design rationale:
# Tracks which feature terms (dispatch, brew, etc.) have been introduced to the user.
# Uses atomic tempfile+rename writes for consistency with state.py, preventing
# corrupt files on crash.  YAML serialization uses safe_dump exclusively.
# Key invariant: terms progress monotonically (unknown -> introduced -> user_has_used).

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class TermState:
    """State of a single vocabulary term."""
    introduced: bool = False
    user_has_used: bool = False
    introduction_context: str | None = None
    introduced_at: datetime | None = None


# All feature terms that can be introduced
FEATURE_TERMS: tuple[str, ...] = (
    "dispatch", "brew", "probe", "valet", "huddle", "suite", "attache",
)


@dataclass
class VocabularyTracker:
    """Tracks which feature terms have been introduced to the user.

    Terms progress through states:
    1. Unknown (not introduced) — describe naturally, never use the term
    2. Introduced — mentioned in passing during a relevant interaction
    3. User has used — the user typed the term themselves
    """
    terms: dict[str, TermState] = field(default_factory=lambda: {
        term: TermState() for term in FEATURE_TERMS
    })

    def is_introduced(self, term: str) -> bool:
        """Check if a term has been introduced to the user."""
        return self.terms.get(term, TermState()).introduced

    def should_introduce(self, term: str, context: str) -> bool:
        """Check if now is a good time to introduce a term.

        A term should be introduced when:
        - It hasn't been introduced yet
        - There's a relevant context (the user is interacting with the feature)
        """
        state = self.terms.get(term)
        if state is None or state.introduced:
            return False
        return bool(context)  # Any context is sufficient

    def introduce(self, term: str, context: str) -> None:
        """Mark a term as introduced."""
        if term not in self.terms:
            self.terms[term] = TermState()
        self.terms[term].introduced = True
        self.terms[term].introduction_context = context
        self.terms[term].introduced_at = datetime.now(timezone.utc)

    def mark_user_used(self, term: str) -> None:
        """Mark that the user has used this term themselves."""
        if term not in self.terms:
            self.terms[term] = TermState()
        self.terms[term].user_has_used = True
        if not self.terms[term].introduced:
            self.terms[term].introduced = True

    def can_use_term(self, term: str) -> bool:
        """Return True if we can freely use this term in responses.

        Only use a term after it's been introduced and the user has seen it.
        """
        state = self.terms.get(term, TermState())
        return state.introduced

    def save(self, path: Path) -> None:
        """Save vocabulary state to YAML file (atomic write)."""
        data = {}
        for term, state in self.terms.items():
            entry: dict[str, object] = {
                "introduced": state.introduced,
                "user_has_used": state.user_has_used,
            }
            if state.introduction_context:
                entry["introduction_context"] = state.introduction_context
            if state.introduced_at:
                entry["introduced_at"] = state.introduced_at.isoformat()
            data[term] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            os.rename(tmp, str(path))
        except BaseException:
            os.unlink(tmp)
            raise

    @classmethod
    def load(cls, path: Path) -> "VocabularyTracker":
        """Load vocabulary state from YAML file."""
        tracker = cls()
        if not path.exists():
            return tracker
        data = yaml.safe_load(path.read_text()) or {}
        for term, entry in data.items():
            state = TermState(
                introduced=entry.get("introduced", False),
                user_has_used=entry.get("user_has_used", False),
                introduction_context=entry.get("introduction_context"),
            )
            if entry.get("introduced_at"):
                state.introduced_at = datetime.fromisoformat(entry["introduced_at"])
            tracker.terms[term] = state
        return tracker
