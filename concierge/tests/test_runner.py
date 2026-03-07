"""Tests for background check runner."""
from datetime import datetime, timezone, timedelta

import pytest

from concierge.background.runner import BackgroundRunner, CheckResult, CheckType


@pytest.fixture
def runner(tmp_path):
    return BackgroundRunner(data_dir=tmp_path)


class TestShouldRun:
    def test_should_run_when_never_run(self, runner):
        """A check that has never run should always be due."""
        assert runner.should_run(CheckType.DISPATCH_SCAN) is True

    def test_should_not_run_within_interval(self, runner):
        """A check that ran recently should not be due."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        runner.mark_run(CheckType.DISPATCH_SCAN, now)
        # 1 hour later — DISPATCH_SCAN has 12h interval
        later = now + timedelta(hours=1)
        assert runner.should_run(CheckType.DISPATCH_SCAN, later) is False

    def test_should_run_after_interval(self, runner):
        """A check should be due once its interval has elapsed."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        runner.mark_run(CheckType.DISPATCH_SCAN, now)
        # 13 hours later — exceeds 12h interval
        later = now + timedelta(hours=13)
        assert runner.should_run(CheckType.DISPATCH_SCAN, later) is True


class TestGetDueChecks:
    def test_get_due_checks_all_due_initially(self, runner):
        """All checks should be due when none have ever run."""
        due = runner.get_due_checks()
        assert set(due) == set(CheckType)

    def test_mark_run_updates_last_runs(self, runner):
        """mark_run should record the timestamp."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        runner.mark_run(CheckType.BREW_ANALYSIS, now)
        assert runner.last_runs[CheckType.BREW_ANALYSIS] == now


class TestRunCheck:
    def test_run_check_returns_result(self, runner):
        """run_check should return a successful CheckResult."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        result = runner.run_check(CheckType.DISTILLATION, now)
        assert isinstance(result, CheckResult)
        assert result.check_type == CheckType.DISTILLATION
        assert result.success is True
        assert result.ran_at == now

    def test_run_all_due(self, runner):
        """run_all_due should run all checks when none have run before."""
        now = datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc)
        results = runner.run_all_due(now)
        assert len(results) == len(CheckType)
        assert all(r.success for r in results)
        # After running all, none should be due at the same timestamp
        assert runner.get_due_checks(now) == []
