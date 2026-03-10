"""Tests for LLM-based topic compression."""

from unittest.mock import patch, MagicMock

import pytest

from concierge.distillation.compress import compress_topic, DISTILLATION_PROMPT


class TestCompressTopic:
    def test_calls_llm_with_prompt(self):
        """compress_topic calls call_agent with the distillation prompt."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Enjoys pasta"
            result = compress_topic("- Old fact", "- [2026-01-01] Made pasta", "meals")
            assert mock_llm.called
            prompt = mock_llm.call_args[0][0]
            assert "meals" in prompt
            assert "Old fact" in prompt
            assert "Made pasta" in prompt

    def test_returns_llm_output(self):
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Enjoys pasta\n- Runs daily"
            result = compress_topic("", "- [2026-01-01] Made pasta", "meals")
            assert result == "- Enjoys pasta\n- Runs daily"

    def test_falls_back_to_deterministic_on_llm_error(self):
        """When LLM fails, falls back to deterministic merge."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.side_effect = Exception("API error")
            result = compress_topic(
                "- Existing fact",
                "- [2026-01-01] New entry",
                "meals",
            )
            # Deterministic fallback should preserve existing + add new
            assert "Existing fact" in result
            assert "New entry" in result

    def test_empty_distilled_shows_first_distillation(self):
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- First fact"
            compress_topic("", "- [2026-01-01] Raw entry", "meals")
            prompt = mock_llm.call_args[0][0]
            assert "first distillation" in prompt.lower()

    def test_prompt_contains_all_rules(self):
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Fact"
            compress_topic("- Old", "- New", "meals")
            prompt = mock_llm.call_args[0][0]
            assert "Preserve ALL facts" in prompt
            assert "Consolidate" in prompt
            assert "No preamble" in prompt


class TestDeterministicFallback:
    """Test the deterministic fallback directly."""

    def test_keeps_existing_entries(self):
        from concierge.distillation.compress import _deterministic_compress
        result = _deterministic_compress("- Existing fact", "")
        assert "Existing fact" in result

    def test_adds_new_entries(self):
        from concierge.distillation.compress import _deterministic_compress
        result = _deterministic_compress("", "- [2026-01-01] New entry")
        assert "New entry" in result

    def test_deduplicates(self):
        from concierge.distillation.compress import _deterministic_compress
        result = _deterministic_compress(
            "- I like pasta very much",
            "- [2026-01-01] I really like pasta a lot",
        )
        # Should not add the duplicate
        lines = [l for l in result.strip().split("\n") if l.startswith("- ")]
        assert len(lines) == 1
