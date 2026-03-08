"""Background check runner — orchestrates periodic background tasks."""

# Design rationale:
# The CheckType enum defines the full catalogue of periodic background jobs;
# each type carries a minimum interval (in hours) so the runner never re-fires
# a check before its cooldown expires.  Interval-based scheduling (rather than
# cron expressions) keeps the logic trivial and avoids a cron parser
# dependency.  Every time-sensitive method accepts an injectable `now`
# parameter so unit tests can exercise scheduling logic deterministically
# without mocking datetime.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class CheckType(Enum):
    """Types of background checks."""
    DISPATCH_SCAN = "dispatch_scan"      # Scan memory for dispatch opportunities
    BREW_ANALYSIS = "brew_analysis"       # Analyze patterns for brews
    DISTILLATION = "distillation"        # Run distillation candidate detection
    PROBE_DELIVERY = "probe_delivery"    # Deliver scheduled probes
    VALET_TRIGGER = "valet_trigger"      # Trigger scheduled valets


@dataclass
class CheckResult:
    """Result of a background check."""
    check_type: CheckType
    ran_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    items_generated: int = 0
    error: str | None = None


@dataclass
class BackgroundRunner:
    """Runs periodic background checks for the Concierge.

    Each check type has a minimum interval to prevent excessive runs.
    The runner tracks last-run times and skips checks that ran recently.
    """
    data_dir: Path
    min_intervals: dict[CheckType, float] = field(default_factory=lambda: {
        CheckType.DISPATCH_SCAN: 12.0,    # hours
        CheckType.BREW_ANALYSIS: 168.0,   # weekly
        CheckType.DISTILLATION: 24.0,     # daily
        CheckType.PROBE_DELIVERY: 1.0,    # hourly (checks schedule)
        CheckType.VALET_TRIGGER: 1.0,     # hourly (checks schedule)
    })
    last_runs: dict[CheckType, datetime] = field(default_factory=dict)

    def should_run(self, check_type: CheckType, now: datetime | None = None) -> bool:
        """Check if enough time has elapsed since last run."""
        now = now or datetime.now(timezone.utc)
        last = self.last_runs.get(check_type)
        if last is None:
            return True
        interval = self.min_intervals.get(check_type, 1.0)
        elapsed = (now - last).total_seconds() / 3600
        return elapsed >= interval

    def mark_run(self, check_type: CheckType, now: datetime | None = None) -> None:
        """Record that a check type was just run."""
        self.last_runs[check_type] = now or datetime.now(timezone.utc)

    def get_due_checks(self, now: datetime | None = None) -> list[CheckType]:
        """Return list of check types that are due to run."""
        now = now or datetime.now(timezone.utc)
        return [ct for ct in CheckType if self.should_run(ct, now)]

    def run_check(self, check_type: CheckType, now: datetime | None = None) -> CheckResult:
        """Run a single background check.

        This is a framework method — actual check implementations are pluggable.
        For v1, returns a successful stub result.
        """
        now = now or datetime.now(timezone.utc)
        self.mark_run(check_type, now)
        return CheckResult(check_type=check_type, ran_at=now, success=True)

    def run_all_due(self, now: datetime | None = None) -> list[CheckResult]:
        """Run all checks that are due."""
        now = now or datetime.now(timezone.utc)
        results = []
        for check_type in self.get_due_checks(now):
            result = self.run_check(check_type, now)
            results.append(result)
        return results
