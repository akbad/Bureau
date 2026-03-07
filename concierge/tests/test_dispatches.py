"""Tests for dispatch candidacy evaluator."""

import json
from datetime import datetime, timezone

from concierge.features.dispatches import evaluate_dispatch_candidates
from concierge.models import FeatureType, SessionState, Suite


class TestDispatchCandidacy:
    def _seed_history(self, data_dir, entries):
        """Write dispatch history entries to the JSONL file."""
        history_file = data_dir / "feature_history.jsonl"
        with open(history_file, "a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_returns_candidate_when_eligible(self, tmp_data_dir):
        """Returns a single candidate when all constraints pass."""
        session = SessionState(current_suite=Suite.WORK)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        candidates = evaluate_dispatch_candidates(
            session, tmp_data_dir, now=now,
        )
        assert len(candidates) == 1
        c = candidates[0]
        assert c.feature_type == FeatureType.DISPATCH
        assert c.domain == "dispatch"
        assert "suite_fit" in c.score_inputs
        assert "freshness" in c.score_inputs

    def test_blocked_by_cooldown(self, tmp_data_dir):
        """Returns empty if last dispatch was within cooldown period."""
        session = SessionState(current_suite=Suite.WORK)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        # Dispatch 6 hours ago (within 12h cooldown)
        self._seed_history(tmp_data_dir, [
            {"feature_type": "dispatch", "domain": "meals",
             "surfaced_at": "2026-03-07T12:00:00+00:00", "outcome": "engaged"},
        ])

        candidates = evaluate_dispatch_candidates(
            session, tmp_data_dir, cooldown_hours=12, now=now,
        )
        assert candidates == []

    def test_blocked_by_weekly_limit(self, tmp_data_dir):
        """Returns empty when weekly limit is reached."""
        session = SessionState(current_suite=Suite.WORK)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        # 3 dispatches within the last week (168h), all outside cooldown
        self._seed_history(tmp_data_dir, [
            {"feature_type": "dispatch", "domain": "d1",
             "surfaced_at": "2026-03-05T10:00:00+00:00", "outcome": "engaged"},
            {"feature_type": "dispatch", "domain": "d2",
             "surfaced_at": "2026-03-06T10:00:00+00:00", "outcome": "engaged"},
            {"feature_type": "dispatch", "domain": "d3",
             "surfaced_at": "2026-03-07T04:00:00+00:00", "outcome": "engaged"},
        ])

        candidates = evaluate_dispatch_candidates(
            session, tmp_data_dir, cooldown_hours=12, max_per_week=3, now=now,
        )
        assert candidates == []

    def test_blocked_during_processing_suite(self, tmp_data_dir):
        """Returns empty when suite is PROCESSING."""
        session = SessionState(current_suite=Suite.PROCESSING)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        candidates = evaluate_dispatch_candidates(
            session, tmp_data_dir, now=now,
        )
        assert candidates == []

    def test_suite_fit_score_varies_by_suite(self, tmp_data_dir):
        """suite_fit is 1.0 for non-PROCESSING suites, 0.0 for PROCESSING."""
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        for suite in [Suite.WORK, Suite.REST, Suite.SOCIAL, Suite.CREATIVE]:
            session = SessionState(current_suite=suite)
            candidates = evaluate_dispatch_candidates(
                session, tmp_data_dir, now=now,
            )
            assert len(candidates) == 1
            assert candidates[0].score_inputs["suite_fit"] == 1.0

    def test_freshness_score_computation(self, tmp_data_dir):
        """freshness = hours_since_last / cooldown_hours, capped at 1.0."""
        session = SessionState(current_suite=Suite.WORK)
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)

        # Dispatch 24 hours ago (double the 12h cooldown)
        self._seed_history(tmp_data_dir, [
            {"feature_type": "dispatch", "domain": "d1",
             "surfaced_at": "2026-03-06T18:00:00+00:00", "outcome": "engaged"},
        ])

        candidates = evaluate_dispatch_candidates(
            session, tmp_data_dir, cooldown_hours=12, now=now,
        )
        assert len(candidates) == 1
        # 24 / 12 = 2.0, but capped at 1.0
        assert candidates[0].score_inputs["freshness"] == 1.0
