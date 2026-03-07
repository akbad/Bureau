"""Catch-up policy — determines what to run after wake from sleep."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from .runner import BackgroundRunner, CheckType, CheckResult


@dataclass
class CatchupPolicy:
    """Determines which background checks to run after a period of inactivity.

    When the system wakes from sleep, we don't want to run ALL missed checks
    simultaneously. Instead, prioritize the most important ones.
    """

    # Maximum checks to run in a single catch-up
    max_catchup_checks: int = 3

    # Priority order for catch-up (most important first)
    priority_order: tuple[CheckType, ...] = (
        CheckType.PROBE_DELIVERY,     # Scheduled items first
        CheckType.VALET_TRIGGER,      # Scheduled items
        CheckType.DISPATCH_SCAN,      # Time-sensitive suggestions
        CheckType.DISTILLATION,       # Maintenance
        CheckType.BREW_ANALYSIS,      # Least urgent
    )

    def get_catchup_checks(
        self,
        runner: BackgroundRunner,
        now: datetime | None = None,
    ) -> list[CheckType]:
        """Determine which checks to run after wake.

        Returns at most max_catchup_checks, prioritized by importance.
        Only includes checks that are actually due.
        """
        now = now or datetime.now(timezone.utc)
        due = set(runner.get_due_checks(now))

        prioritized = [ct for ct in self.priority_order if ct in due]
        return prioritized[:self.max_catchup_checks]

    def estimate_downtime(self, runner: BackgroundRunner, now: datetime | None = None) -> timedelta:
        """Estimate how long the system was down based on last-run times.

        Returns the time since the most recent check ran.
        """
        now = now or datetime.now(timezone.utc)
        if not runner.last_runs:
            return timedelta(hours=0)

        most_recent = max(runner.last_runs.values())
        return now - most_recent

    def run_catchup(
        self,
        runner: BackgroundRunner,
        now: datetime | None = None,
    ) -> list[CheckResult]:
        """Execute catch-up checks after wake."""
        now = now or datetime.now(timezone.utc)
        checks = self.get_catchup_checks(runner, now)

        results = []
        for check_type in checks:
            result = runner.run_check(check_type, now)
            results.append(result)
        return results
