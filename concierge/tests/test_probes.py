"""Tests for the probe candidacy evaluator."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from concierge.features.probes import evaluate_probe_candidates
from concierge.models import FeatureType, SessionState, Suite


def _write_schedules(tmp_path: Path, data: dict) -> Path:
    """Write a schedules.yml and return the directory."""
    path = tmp_path / "schedules.yml"
    path.write_text(yaml.dump(data))
    return tmp_path


def _make_probe_schedule(
    name: str = "skincare",
    cadence: str = "weekly",
    day: str = "sunday",
    time: str = "09:00",
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


class TestProbeEvaluator:
    def test_returns_candidates_for_due_probes(self, tmp_path):
        data = {
            "probes": _make_probe_schedule(
                last_run="2026-03-01T09:00:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        # Sunday 2026-03-08 10:00 UTC
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_probe_candidates(session, data_dir, now=now)

        assert len(candidates) == 1
        c = candidates[0]
        assert c.feature_type == FeatureType.PROBE
        assert c.domain == "skincare"
        assert "suite_fit" in c.score_inputs
        assert "freshness" in c.score_inputs
        assert "queue_age" in c.score_inputs

    def test_no_candidates_when_nothing_due(self, tmp_path):
        data = {
            "probes": _make_probe_schedule(
                last_run="2026-03-07T09:00:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        # Still Sunday but last run was yesterday — too recent
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_probe_candidates(session, data_dir, now=now)
        assert len(candidates) == 0

    def test_suite_fit_zero_during_processing(self, tmp_path):
        data = {
            "probes": _make_probe_schedule(
                last_run="2026-03-01T09:00:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.PROCESSING)

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_probe_candidates(session, data_dir, now=now)

        assert len(candidates) == 1
        assert candidates[0].score_inputs["suite_fit"] == 0.0

    def test_probe_metadata_includes_schedule(self, tmp_path):
        data = {
            "probes": _make_probe_schedule(
                last_run="2026-03-01T09:00:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.REST)

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_probe_candidates(session, data_dir, now=now)

        assert len(candidates) == 1
        meta = candidates[0].metadata
        assert meta is not None
        assert "cadence" in meta
        assert "day" in meta
        assert "time" in meta
        assert meta["cadence"] == "weekly"
        assert meta["day"] == "sunday"

    def test_multiple_due_probes(self, tmp_path):
        probes = {}
        probes.update(
            _make_probe_schedule(
                name="skincare",
                day="sunday",
                last_run="2026-03-01T09:00:00+00:00",
            )
        )
        probes.update(
            _make_probe_schedule(
                name="career",
                cadence="weekly",
                day="sunday",
                time="08:00",
                last_run="2026-03-01T08:00:00+00:00",
            )
        )
        data = {"probes": probes}
        data_dir = _write_schedules(tmp_path, data)
        session = SessionState(current_suite=Suite.WORK)

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_probe_candidates(session, data_dir, now=now)

        assert len(candidates) == 2
        domains = {c.domain for c in candidates}
        assert domains == {"skincare", "career"}

    def test_suite_fit_half_for_mismatched_suite(self, tmp_path):
        data = {
            "probes": _make_probe_schedule(
                last_run="2026-03-01T09:00:00+00:00",
            )
        }
        data_dir = _write_schedules(tmp_path, data)
        # WORK suite doesn't match probe domain "skincare"
        session = SessionState(current_suite=Suite.WORK)

        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        candidates = evaluate_probe_candidates(session, data_dir, now=now)

        assert len(candidates) == 1
        # Non-PROCESSING suite that doesn't match domain -> 0.5
        assert candidates[0].score_inputs["suite_fit"] == 0.5
