"""Tests for the shared schedule parsing module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from concierge.features.schedules import ScheduleEntry, is_due, load_schedules


def _write_schedules(tmp_path: Path, data: dict) -> Path:
    """Write a schedules.yml and return the directory."""
    path = tmp_path / "schedules.yml"
    path.write_text(yaml.dump(data))
    return tmp_path


class TestLoadSchedules:
    def test_load_schedules_from_file(self, tmp_path):
        data = {
            "probes": {
                "skincare": {
                    "cadence": "weekly",
                    "day": "sunday",
                    "time": "09:00",
                    "enabled": True,
                    "last_run": "2026-03-02T09:00:00+00:00",
                },
                "career": {
                    "cadence": "biweekly",
                    "day": "monday",
                    "time": "08:00",
                    "enabled": True,
                },
            }
        }
        data_dir = _write_schedules(tmp_path, data)
        entries = load_schedules(data_dir, "probes")

        assert len(entries) == 2
        names = {e.name for e in entries}
        assert names == {"skincare", "career"}

        skincare = next(e for e in entries if e.name == "skincare")
        assert skincare.cadence == "weekly"
        assert skincare.day == "sunday"
        assert skincare.time == "09:00"
        assert skincare.enabled is True
        assert skincare.last_run is not None

        career = next(e for e in entries if e.name == "career")
        assert career.last_run is None

    def test_load_schedules_missing_file_returns_empty(self, tmp_path):
        entries = load_schedules(tmp_path, "probes")
        assert entries == []


class TestIsDue:
    def test_is_due_weekly_correct_day(self, tmp_path):
        # Sunday 2026-03-08 10:00 UTC, last run was > 7 days ago
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="skincare",
            cadence="weekly",
            day="sunday",
            time="09:00",
            enabled=True,
            last_run=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry, now) is True

    def test_is_due_weekly_wrong_day(self, tmp_path):
        # Monday 2026-03-09 10:00 UTC — not sunday
        now = datetime(2026, 3, 9, 10, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="skincare",
            cadence="weekly",
            day="sunday",
            time="09:00",
            enabled=True,
            last_run=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry, now) is False

    def test_is_due_already_ran_recently(self):
        # Sunday 2026-03-08 10:00 UTC, but last run was only 3 days ago
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="skincare",
            cadence="weekly",
            day="sunday",
            time="09:00",
            enabled=True,
            last_run=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry, now) is False

    def test_is_due_biweekly(self):
        # Monday 2026-03-09 09:00, last run 14+ days ago
        now = datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="career",
            cadence="biweekly",
            day="monday",
            time="08:00",
            enabled=True,
            last_run=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry, now) is True

        # Only 7 days ago — not enough for biweekly
        entry_recent = ScheduleEntry(
            name="career",
            cadence="biweekly",
            day="monday",
            time="08:00",
            enabled=True,
            last_run=datetime(2026, 3, 16, 8, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry_recent, now) is False

    def test_is_due_daily(self):
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="journal",
            cadence="daily",
            day=None,
            time="08:00",
            enabled=True,
            last_run=datetime(2026, 3, 7, 8, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry, now) is True

        # Ran less than 24 hours ago
        entry_recent = ScheduleEntry(
            name="journal",
            cadence="daily",
            day=None,
            time="08:00",
            enabled=True,
            last_run=datetime(2026, 3, 8, 5, 0, tzinfo=timezone.utc),
        )
        assert is_due(entry_recent, now) is False

    def test_disabled_entry_never_due(self):
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="skincare",
            cadence="weekly",
            day="sunday",
            time="09:00",
            enabled=False,
            last_run=None,
        )
        assert is_due(entry, now) is False

    def test_never_run_entry_is_due(self):
        # Sunday, never run before — should be due
        now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="skincare",
            cadence="weekly",
            day="sunday",
            time="09:00",
            enabled=True,
            last_run=None,
        )
        assert is_due(entry, now) is True

    def test_before_scheduled_time_not_due(self):
        # Sunday but before 09:00
        now = datetime(2026, 3, 8, 8, 30, tzinfo=timezone.utc)
        entry = ScheduleEntry(
            name="skincare",
            cadence="weekly",
            day="sunday",
            time="09:00",
            enabled=True,
            last_run=None,
        )
        assert is_due(entry, now) is False
