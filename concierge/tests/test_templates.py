"""Tests for prompt templates, attache files, and huddle templates."""
from pathlib import Path

import pytest

CONCIERGE_ROOT = Path(__file__).parent.parent


class TestAttacheFiles:
    EXPECTED_ATTACHES = [
        "meals", "schedule", "wellness", "events", "shopping",
        "social", "travel", "learning", "home", "finance",
    ]

    @pytest.mark.parametrize("name", EXPECTED_ATTACHES)
    def test_attache_file_exists(self, name):
        path = CONCIERGE_ROOT / "attaches" / f"{name}.md"
        assert path.exists(), f"Missing attache file: {path}"

    @pytest.mark.parametrize("name", EXPECTED_ATTACHES)
    def test_attache_file_has_content(self, name):
        path = CONCIERGE_ROOT / "attaches" / f"{name}.md"
        content = path.read_text()
        assert len(content) > 50, f"Attache file too short: {path}"
        assert "## Guidelines" in content


class TestPromptTemplates:
    EXPECTED_PROMPTS = [
        "system", "morning-briefing", "evening-checkin",
        "reminder", "weekly-meal-plan",
    ]

    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_prompt_file_exists(self, name):
        path = CONCIERGE_ROOT / "prompts" / f"{name}.md"
        assert path.exists(), f"Missing prompt file: {path}"

    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_prompt_file_has_content(self, name):
        path = CONCIERGE_ROOT / "prompts" / f"{name}.md"
        content = path.read_text()
        assert len(content) > 50, f"Prompt file too short: {path}"


class TestHuddleTemplates:
    EXPECTED_HUDDLES = [
        "initial", "valet-setup", "probe-setup",
        "personality", "goals", "check-in",
    ]

    @pytest.mark.parametrize("name", EXPECTED_HUDDLES)
    def test_huddle_file_exists(self, name):
        path = CONCIERGE_ROOT / "huddles" / f"{name}.md"
        assert path.exists(), f"Missing huddle file: {path}"

    @pytest.mark.parametrize("name", EXPECTED_HUDDLES)
    def test_huddle_file_has_content(self, name):
        path = CONCIERGE_ROOT / "huddles" / f"{name}.md"
        content = path.read_text()
        assert len(content) > 50, f"Huddle file too short: {path}"
        assert "## " in content  # Has at least one section header
