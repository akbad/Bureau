"""Shared schedule parsing for probes and valets.

Reads ``schedules.yml`` from the data directory and determines which
schedule entries are due to run based on cadence, day-of-week, and
last-run timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

_DAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@dataclass
class ScheduleEntry:
    """A single scheduled item (probe or valet)."""

    name: str
    cadence: str  # "weekly", "biweekly", "daily"
    day: str | None  # "monday", "sunday", etc.
    time: str  # "09:00"
    enabled: bool
    last_run: datetime | None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_schedules(data_dir: Path, section: str) -> list[ScheduleEntry]:
    """Load schedule entries from ``schedules.yml`` for *section*.

    Parameters
    ----------
    data_dir:
        Path to the directory containing ``schedules.yml``.
    section:
        Top-level YAML key to read (``"probes"`` or ``"valets"``).

    Returns an empty list when the file is missing or the section is absent.
    """
    schedules_path = data_dir / "schedules.yml"
    if not schedules_path.exists():
        return []

    with open(schedules_path) as fh:
        raw = yaml.safe_load(fh)

    if not raw or section not in raw:
        return []

    entries: list[ScheduleEntry] = []
    for name, cfg in raw[section].items():
        last_run_raw = cfg.get("last_run")
        last_run: datetime | None = None
        if last_run_raw is not None:
            if isinstance(last_run_raw, datetime):
                last_run = last_run_raw
            else:
                last_run = datetime.fromisoformat(str(last_run_raw))

        entries.append(
            ScheduleEntry(
                name=name,
                cadence=cfg.get("cadence", "weekly"),
                day=cfg.get("day"),
                time=cfg.get("time", "00:00"),
                enabled=cfg.get("enabled", True),
                last_run=last_run,
            )
        )

    return entries


# ---------------------------------------------------------------------------
# Due-checking
# ---------------------------------------------------------------------------


def is_due(entry: ScheduleEntry, now: datetime) -> bool:
    """Return *True* if *entry* should run at time *now*.

    Rules
    -----
    - Must be enabled.
    - Time check: current time must be >= scheduled time.
    - **daily** — ``last_run`` is ``None`` *or* more than 24 h ago.
    - **weekly** — correct day of week *and* (``last_run`` is ``None`` *or*
      more than 7 days ago).
    - **biweekly** — correct day of week *and* (``last_run`` is ``None`` *or*
      more than 14 days ago).
    """
    if not entry.enabled:
        return False

    # Time-of-day gate: current time must be on or after the scheduled time.
    scheduled_hour, scheduled_minute = (int(p) for p in entry.time.split(":"))
    current_time = (now.hour, now.minute)
    if current_time < (scheduled_hour, scheduled_minute):
        return False

    if entry.cadence == "daily":
        return _last_run_older_than(entry.last_run, now, hours=24)

    # Weekly / biweekly: must also match the day of the week.
    if entry.day is not None:
        today_name = _DAY_NAMES[now.weekday()]
        if today_name != entry.day.lower():
            return False

    if entry.cadence == "biweekly":
        return _last_run_older_than(entry.last_run, now, hours=14 * 24)

    # Default: weekly
    return _last_run_older_than(entry.last_run, now, hours=7 * 24)


def _last_run_older_than(
    last_run: datetime | None, now: datetime, *, hours: int
) -> bool:
    """Return *True* if *last_run* is ``None`` or older than *hours* hours."""
    if last_run is None:
        return True
    # Ensure timezone-awareness for comparison
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - last_run) >= timedelta(hours=hours)
