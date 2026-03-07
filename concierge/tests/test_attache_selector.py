"""Tests for the attache selector (Stage 2)."""

from concierge.pipeline.attache_selector import (
    SUITE_ATTACHE_MAP,
    load_attache_content,
    select_attaches,
)
from concierge.models import Suite


class TestAttacheSelection:
    def test_work_suite_selects_schedule_finance(self):
        result = select_attaches(Suite.WORK)
        assert "schedule" in result
        assert "finance" in result
        assert "wellness" not in result

    def test_rest_suite_selects_wellness_meals(self):
        result = select_attaches(Suite.REST)
        assert "wellness" in result
        assert "meals" in result

    def test_processing_suite_returns_empty(self):
        result = select_attaches(Suite.PROCESSING)
        assert result == []

    def test_load_attache_content(self, tmp_data_dir):
        attaches_dir = tmp_data_dir / "attaches"
        (attaches_dir / "meals.md").write_text("# Meals\nShe likes pasta.")
        content = load_attache_content(["meals"], attaches_dir)
        assert "She likes pasta" in content

    def test_load_missing_attache_skipped(self, tmp_data_dir):
        content = load_attache_content(["nonexistent"], tmp_data_dir / "attaches")
        assert content == ""
