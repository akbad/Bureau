"""Tests for concierge config loader."""

import pytest

from concierge.config.loader import (
    get_classifier_config,
    get_pipeline_config,
    get_priorities_config,
    load_config,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear lru_cache between tests so overrides don't leak."""
    get_classifier_config.cache_clear()
    get_priorities_config.cache_clear()
    get_pipeline_config.cache_clear()
    yield
    get_classifier_config.cache_clear()
    get_priorities_config.cache_clear()
    get_pipeline_config.cache_clear()


class TestLoadConfig:
    def test_loads_default_classifier_config(self):
        config = load_config()
        assert "classifier" in config
        assert config["classifier"]["model"]["confidence_threshold"] == 0.7

    def test_loads_default_priorities_config(self):
        config = load_config()
        assert "priorities" in config
        assert config["priorities"]["lottery"]["epsilon"] == 0.12

    def test_loads_default_pipeline_config(self):
        config = load_config()
        assert "pipeline" in config
        assert config["pipeline"]["session"]["timeout_minutes"] == 10

    def test_user_overrides_merge(self, tmp_path):
        override = tmp_path / "priorities.yml"
        override.write_text("lottery:\n  epsilon: 0.20\n")
        config = load_config(user_config_dir=tmp_path)
        assert config["priorities"]["lottery"]["epsilon"] == 0.20
        assert config["priorities"]["lottery"]["decay"] == 0.995

    def test_user_overrides_do_not_affect_unrelated_keys(self, tmp_path):
        override = tmp_path / "classifier.yml"
        override.write_text("model:\n  confidence_threshold: 0.9\n")
        config = load_config(user_config_dir=tmp_path)
        # Overridden value
        assert config["classifier"]["model"]["confidence_threshold"] == 0.9
        # Unrelated key preserved
        assert config["classifier"]["model"]["tokenizer"] == "distilbert-base-uncased"


class TestAccessors:
    def test_get_classifier_config(self):
        cc = get_classifier_config()
        assert cc["model"]["tokenizer"] == "distilbert-base-uncased"

    def test_get_priorities_config(self):
        pc = get_priorities_config()
        assert "scoring_weights" in pc
        assert "hard_rules" in pc

    def test_get_pipeline_config(self):
        pc = get_pipeline_config()
        assert pc["media"]["max_processing_time_seconds"] == 30
        assert pc["background"]["schedule_hours"] == [6, 14]
