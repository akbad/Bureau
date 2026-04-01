"""Tests for LLM-based topic compression."""

from unittest.mock import patch, MagicMock

import pytest

from concierge.distillation.compress import compress_topic, DISTILLATION_PROMPT, MAX_PROMPT_CHARS


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
            mock_llm.return_value = "- Enjoys pasta\n- Goes for a daily run"
            result = compress_topic(
                "",
                "- [2026-01-01] Made pasta\n- [2026-01-02] Went for a daily run",
                "meals",
            )
            assert result == "- Enjoys pasta\n- Goes for a daily run"

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

    def test_falls_back_when_llm_loses_facts(self):
        """When LLM output drops facts, falls back to deterministic merge."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            # LLM output covers pasta but drops the risotto fact entirely
            mock_llm.return_value = "- Enjoys pasta dishes"
            result = compress_topic(
                "- Existing note",
                "- [2026-01-01] Made pasta\n- [2026-01-02] Made risotto for the first time",
                "meals",
            )
            # Should get deterministic fallback, not the LLM output
            assert "risotto" in result
            assert mock_llm.called

    def test_falls_back_when_prompt_too_large(self):
        """When prompt exceeds MAX_PROMPT_CHARS, skips LLM entirely."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            huge_raw = "\n".join(
                f"- [2026-01-{i:02d}] Entry number {i} with padding {'x' * 100}"
                for i in range(1, 500)
            )
            result = compress_topic("- Existing fact", huge_raw, "meals")
            mock_llm.assert_not_called()
            assert "Existing fact" in result

    def test_returns_llm_output_when_validation_passes(self):
        """When LLM output covers all facts, returns it directly."""
        with patch("concierge.distillation.compress.call_agent") as mock_llm:
            mock_llm.return_value = "- Loves pasta\n- Tried risotto recently"
            result = compress_topic(
                "",
                "- [2026-01-01] Made pasta\n- [2026-01-02] Made risotto",
                "meals",
            )
            assert result == "- Loves pasta\n- Tried risotto recently"


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
