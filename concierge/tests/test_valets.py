"""Tests for the valet candidacy evaluator."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from concierge.features.valets import evaluate_valet_candidates
from concierge.models import FeatureType, SessionState, Suite


def _write_schedules(tmp_path: Path, data: dict) -> Path:
    """Write a schedules.yml and return the directory."""
    path = tmp_path / "schedules.yml"
    path.write_text(yaml.dump(data))
    return tmp_path


def _make_valet_schedule(
    name: str = "meal-prep",
    cadence: str = "weekly",
    day: str = "sunday",
    time: str = "09:30",
    enabled: bool = True,
    last_run: str | None = None,
) -> dict:
    entry = {
        "cadence": cadence,
        "day": day,
        "time": time,
        "enabled": enabled,
    }
    if last_run is not None:
        entry["last_run"] = last_run
    return {name: entry}


class TestValetEvaluator:
    def test_returns_candidate_for_due_valet(self, tmp_path):
        data = {
            "valets": _make_valet_schedule(
                last_run="2026-03-01T09:30:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        # Sunday 2026-03-08 10:00 UTC
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_valet_candidates(session, data_dir, now=now)

        assert len(candidates) == 1
        c = candidates[0]
        assert c.feature_type == FeatureType.VALET
        assert c.domain == "meal-prep"
        assert c.score_inputs["suite_fit"] == 1.0
        assert c.score_inputs["relevance"] == 0.8
        assert c.score_inputs["urgency"] == 0.7

    def test_no_candidates_when_nothing_due(self, tmp_path):
        data = {
            "valets": _make_valet_schedule(
                last_run="2026-03-07T09:30:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        # Sunday but ran yesterday — too recent for weekly
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_valet_candidates(session, data_dir, now=now)
        assert len(candidates) == 0

    def test_blocked_when_valet_already_active(self, tmp_path):
        data = {
            "valets": _make_valet_schedule(
                last_run="2026-03-01T09:30:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(
            current_suite=Suite.REST,
            active_feature=FeatureType.VALET,
        )

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_valet_candidates(session, data_dir, now=now)
        assert len(candidates) == 0

    def test_valet_metadata_includes_schedule(self, tmp_path):
        data = {
            "valets": _make_valet_schedule(
                last_run="2026-03-01T09:30:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_valet_candidates(session, data_dir, now=now)

        assert len(candidates) == 1
        meta = candidates[0].metadata
        assert meta is not None
        assert "cadence" in meta
        assert "day" in meta
        assert "time" in meta
        assert meta["cadence"] == "weekly"
        assert meta["day"] == "sunday"

    def test_multiple_due_valets(self, tmp_path):
        valets = {}
        valets.update(
            _make_valet_schedule(
                name="meal-prep",
                day="sunday",
                last_run="2026-03-01T09:30:00+00:00",
            )
        )
        valets.update(
            _make_valet_schedule(
                name="wind-down",
                day="sunday",
                time="18:00",
                last_run="2026-03-01T18:00:00+00:00",
            )
        )
        data = {"valets": valets}
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        # Sunday 2026-03-08 19:00 UTC — both are past their time
        now = datetime(2026, 3, 8, 19, 0, tzinfo=timezone.utc)
        candidates = evaluate_valet_candidates(session, data_dir, now=now)

        assert len(candidates) == 2
        domains = {c.domain for c in candidates}
        assert domains == {"meal-prep", "wind-down"}

    def test_not_blocked_during_processing_suite(self, tmp_path):
        """Valets are NOT blocked during PROCESSING suite."""
        data = {
            "valets": _make_valet_schedule(
                last_run="2026-03-01T09:30:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.PROCESSING)

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_valet_candidates(session, data_dir, now=now)

        # Valets should still be produced during PROCESSING
        assert len(candidates) == 1
