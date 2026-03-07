"""Tests for shared feature history utilities."""

import json
from datetime import datetime, timedelta, timezone

from concierge.features.history import (
    count_in_period,
    hours_since_last,
    load_feature_history,
    record_feature,
)


class TestLoadFeatureHistory:
    def test_load_empty_history(self, tmp_data_dir):
        """Returns empty list when the JSONL file does not exist."""
        result = load_feature_history(tmp_data_dir, "dispatch")
        assert result == []

    def test_load_filters_by_type(self, tmp_data_dir):
        """Only returns entries matching the requested feature type."""
        history_file = tmp_data_dir / "feature_history.jsonl"
        entries = [
            {"feature_type": "dispatch", "domain": "meals", "surfaced_at": "2026-03-07T10:00:00+00:00", "outcome": "engaged"},
            {"feature_type": "brew", "domain": "sleep", "surfaced_at": "2026-03-07T11:00:00+00:00", "outcome": "engaged"},
            {"feature_type": "dispatch", "domain": "work", "surfaced_at": "2026-03-07T12:00:00+00:00", "outcome": "dismissed"},
        ]
        with open(history_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        dispatches = load_feature_history(tmp_data_dir, "dispatch")
        assert len(dispatches) == 2
        assert all(e["feature_type"] == "dispatch" for e in dispatches)

        brews = load_feature_history(tmp_data_dir, "brew")
        assert len(brews) == 1
        assert brews[0]["domain"] == "sleep"


class TestHoursSinceLast:
    def test_hours_since_last_with_entries(self):
        """Computes correct hours since the most recent entry."""
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        history = [
            {"surfaced_at": "2026-03-07T12:00:00+00:00"},
            {"surfaced_at": "2026-03-07T15:00:00+00:00"},
        ]
        result = hours_since_last(history, now)
        assert result == 3.0

    def test_hours_since_last_empty(self):
        """Returns infinity when there is no history."""
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        result = hours_since_last([], now)
        assert result == float("inf")


class TestCountInPeriod:
    def test_count_in_period(self):
        """Counts only entries within the specified period."""
        now = datetime(2026, 3, 7, 18, 0, 0, tzinfo=timezone.utc)
        history = [
            {"surfaced_at": "2026-03-01T12:00:00+00:00"},  # ~6 days ago
            {"surfaced_at": "2026-03-07T10:00:00+00:00"},  # 8 hours ago
            {"surfaced_at": "2026-03-07T15:00:00+00:00"},  # 3 hours ago
        ]
        # Count within last 24 hours
        assert count_in_period(history, now, 24.0) == 2
        # Count within last 1 hour
        assert count_in_period(history, now, 1.0) == 0
        # Count within last 720 hours (30 days) — all entries
        assert count_in_period(history, now, 720.0) == 3


class TestRecordFeature:
    def test_record_feature_creates_file(self, tmp_data_dir):
        """Creates the JSONL file if it does not exist."""
        record_feature(tmp_data_dir, "dispatch", "meals", outcome="engaged")
        history_file = tmp_data_dir / "feature_history.jsonl"
        assert history_file.exists()
        with open(history_file) as f:
            entry = json.loads(f.readline())
        assert entry["feature_type"] == "dispatch"
        assert entry["domain"] == "meals"
        assert entry["outcome"] == "engaged"
        assert "surfaced_at" in entry

    def test_record_feature_appends(self, tmp_data_dir):
        """Appends to existing file without overwriting."""
        record_feature(tmp_data_dir, "dispatch", "meals")
        record_feature(tmp_data_dir, "brew", "sleep")
        history_file = tmp_data_dir / "feature_history.jsonl"
        with open(history_file) as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["feature_type"] == "dispatch"
        assert json.loads(lines[1])["feature_type"] == "brew"
