"""Shared fixtures for concierge tests."""

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary concierge data directory with standard structure."""
    data_dir = tmp_path / "concierge"
    (data_dir / "topics").mkdir(parents=True)
    (data_dir / "auto").mkdir()
    (data_dir / "state").mkdir()
    (data_dir / "attaches").mkdir()
    return data_dir


@pytest.fixture
def sample_config():
    """Return a minimal valid concierge config dict."""
    return {
        "classifier": {
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": 256,
        },
        "priorities": {
            "levels": ["critical", "high", "normal", "low"],
            "default": "normal",
        },
    }
