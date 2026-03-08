"""Epsilon-greedy feature selector with suite-fit floor."""

# Design rationale:
# Epsilon-greedy was chosen over Thompson sampling or UCB because the action
# space is small (typically 2-5 candidates) and the reward signal is sparse
# (user engagement feedback is rare and delayed), making the exploration
# guarantees of UCB/Thompson unnecessary overhead.  The suite_fit_floor
# (default 0.3) acts as a hard gate that prevents the random exploration arm
# from surfacing a feature that is contextually wrong for the current suite.
# Epsilon decays multiplicatively toward min_epsilon so the system shifts from
# exploration to exploitation as it accumulates implicit preference data.

from __future__ import annotations

import random

from ..models import FeatureCandidate


class FeatureSelector:
    def __init__(
        self,
        epsilon: float = 0.12,
        decay: float = 0.995,
        min_epsilon: float = 0.05,
        suite_fit_floor: float = 0.3,
    ):
        self.epsilon = epsilon
        self.decay = decay
        self.min_epsilon = min_epsilon
        self.suite_fit_floor = suite_fit_floor

    def select(
        self,
        candidates: list[FeatureCandidate],
        priority_scores: dict[FeatureCandidate, float],
    ) -> FeatureCandidate | None:
        if not candidates:
            return None

        # Filter: suite_fit floor
        eligible = [
            c for c in candidates
            if c.score_inputs.get("suite_fit", 1.0) >= self.suite_fit_floor
        ]
        if not eligible:
            return None

        if random.random() < self.epsilon:
            # EXPLORE: uniform random from eligible
            winner = random.choice(eligible)
            winner.lottery_promoted = True
            return winner
        else:
            # EXPLOIT: highest priority
            return max(eligible, key=lambda c: priority_scores.get(c, 0.0))

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.min_epsilon, self.epsilon * self.decay)
