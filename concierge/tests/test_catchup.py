"""Tests for catch-up policy after wake from sleep."""
from datetime import datetime, timezone, timedelta

import pytest

from concierge.background.catchup import CatchupPolicy
from concierge.background.runner import BackgroundRunner, CheckType


@pytest.fixture
def runner(tmp_path):
    return BackgroundRunner(data_dir=tmp_path)


@pytest.fixture
def policy():
    return CatchupPolicy()


class TestGetCatchupChecks:
    def test_get_catchup_checks_prioritized(self, runner, policy):
        """Catch-up checks should be returned in priority order."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        checks = policy.get_catchup_checks(runner, now)
        # All are due; first 3 should be the highest-priority ones
        assert checks[0] == CheckType.PROBE_DELIVERY
        assert checks[1] == CheckType.VALET_TRIGGER
        assert checks[2] == CheckType.DISPATCH_SCAN

    def test_catchup_respects_max_limit(self, runner, policy):
        """Should return at most max_catchup_checks items."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        checks = policy.get_catchup_checks(runner, now)
        assert len(checks) <= policy.max_catchup_checks

    def test_catchup_only_due_checks(self, runner, policy):
        """Should only include checks that are actually due."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        # Mark all checks as just run
        for ct in CheckType:
            runner.mark_run(ct, now)
        checks = policy.get_catchup_checks(runner, now)
        assert checks == []


class TestEstimateDowntime:
    def test_estimate_downtime(self, runner, policy):
        """Downtime should equal time since the most recent check."""
        base = datetime(2026, 3, 7, 10, 0, tzinfo=timezone.utc)
        runner.mark_run(CheckType.DISPATCH_SCAN, base)
        runner.mark_run(CheckType.PROBE_DELIVERY, base + timedelta(hours=1))
        now = base + timedelta(hours=5)
        downtime = policy.estimate_downtime(runner, now)
        # Most recent was 1h after base, now is 5h after base => 4h downtime
        assert downtime == timedelta(hours=4)


class TestRunCatchup:
    def test_run_catchup_executes_checks(self, runner, policy):
        """run_catchup should execute the prioritized checks."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        results = policy.run_catchup(runner, now)
        assert len(results) == policy.max_catchup_checks
        assert all(r.success for r in results)
        # Verify the checks ran were the highest priority
        assert results[0].check_type == CheckType.PROBE_DELIVERY
        assert results[1].check_type == CheckType.VALET_TRIGGER
        assert results[2].check_type == CheckType.DISPATCH_SCAN
