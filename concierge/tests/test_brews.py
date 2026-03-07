"""Tests for brew candidacy evaluator."""

import json
from datetime import datetime, timezone

from concierge.features.brews import evaluate_brew_candidates
from concierge.models import FeatureType, SessionState, Suite


class TestBrewCandidacy:
    def _seed_history(self, data_dir, entries):
        """Write brew history entries to the JSONL file."""
        history_file = data_dir / "feature_history.jsonl"
        with open(history_file, "a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_returns_candidate_when_eligible(self, tmp_data_dir):
        """Returns a single candidate when all constraints pass."""
        session = SessionState(current_suite=Suite.REST)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        candidates = evaluate_brew_candidates(
            session, tmp_data_dir, now=now,
        )
        assert len(candidates) == 1
        c = candidates[0]
        assert c.feature_type == FeatureType.BREW
        assert c.domain == "brew"
        assert "suite_fit" in c.score_inputs
        assert "freshness" in c.score_inputs

    def test_blocked_by_cooldown(self, tmp_data_dir):
        """Returns empty if last brew was within cooldown period (168h)."""
        session = SessionState(current_suite=Suite.REST)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        # Brew 48 hours ago (within 168h cooldown)
        self._seed_history(tmp_data_dir, [
            {"feature_type": "brew", "domain": "sleep",
             "surfaced_at": "2026-03-05T18:00:00+00:00", "outcome": "engaged"},
        ])

        candidates = evaluate_brew_candidates(
            session, tmp_data_dir, cooldown_hours=168, now=now,
        )
        assert candidates == []

    def test_blocked_by_monthly_limit(self, tmp_data_dir):
        """Returns empty when monthly limit (2 per 720h) is reached."""
        session = SessionState(current_suite=Suite.REST)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        # 2 brews within the last month, but outside cooldown
        self._seed_history(tmp_data_dir, [
            {"feature_type": "brew", "domain": "b1",
             "surfaced_at": "2026-02-20T10:00:00+00:00", "outcome": "engaged"},
            {"feature_type": "brew", "domain": "b2",
             "surfaced_at": "2026-02-27T10:00:00+00:00", "outcome": "engaged"},
        ])

        candidates = evaluate_brew_candidates(
            session, tmp_data_dir, cooldown_hours=168, max_per_month=2, now=now,
        )
        assert candidates == []

    def test_blocked_during_processing_suite(self, tmp_data_dir):
        """Returns empty when suite is PROCESSING."""
        session = SessionState(current_suite=Suite.PROCESSING)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        candidates = evaluate_brew_candidates(
            session, tmp_data_dir, now=now,
        )
        assert candidates == []

    def test_blocked_during_processing_cooldown(self, tmp_data_dir):
        """Returns empty when processing cooldown is active."""
        session = SessionState(
            current_suite=Suite.REST,
            processing_cooldown_remaining=3,
        )
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        candidates = evaluate_brew_candidates(
            session, tmp_data_dir, now=now,
        )
        assert candidates == []

    def test_suite_fit_varies_by_suite(self, tmp_data_dir):
        """suite_fit differs per suite: 1.0 for REST/CREATIVE, 0.8 for WORK/SOCIAL."""
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        expected = {
            Suite.REST: 1.0,
            Suite.CREATIVE: 1.0,
            Suite.WORK: 0.8,
            Suite.SOCIAL: 0.8,
        }
        for suite, expected_fit in expected.items():
            session = SessionState(current_suite=suite)
            candidates = evaluate_brew_candidates(
                session, tmp_data_dir, now=now,
            )
            assert len(candidates) == 1, f"Expected candidate for suite {suite}"
            assert candidates[0].score_inputs["suite_fit"] == expected_fit, (
                f"Expected suite_fit={expected_fit} for {suite}, "
                f"got {candidates[0].score_inputs['suite_fit']}"
            )
