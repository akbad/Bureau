"""Tests for semantic diff validator (Task 8.3)."""

import pytest

from concierge.distillation.validation import (
    ValidationResult,
    extract_facts,
    extract_key_words,
    fact_is_covered,
    validate_distillation,
)


class TestExtractFacts:
    def test_extract_facts_from_bullets(self):
        text = "- Likes pasta\n- Prefers cooking over ordering"
        facts = extract_facts(text)
        assert "likes pasta" in facts
        assert "prefers cooking over ordering" in facts
        assert len(facts) == 2

    def test_extract_facts_strips_dates(self):
        text = "- [2026-03-07] Made a chicken stir-fry\n- [2026-02-20] Ordered pizza"
        facts = extract_facts(text)
        assert "made a chicken stir-fry" in facts
        assert "ordered pizza" in facts
        # Dates should not appear in facts
        for fact in facts:
            assert "[2026" not in fact

    def test_extract_facts_empty(self):
        assert extract_facts("") == set()
        assert extract_facts("No bullets here\nJust plain text") == set()
        assert extract_facts("## Distilled\n## Raw\n") == set()


class TestExtractKeyWords:
    def test_extract_key_words_filters_stop_words(self):
        keywords = extract_key_words("i made a chicken stir-fry for the family")
        assert "chicken" in keywords
        assert "stir-fry" in keywords
        assert "family" in keywords
        # Stop words should be filtered
        assert "i" not in keywords
        assert "a" not in keywords
        assert "the" not in keywords
        assert "for" not in keywords


class TestFactIsCovered:
    def test_fact_is_covered_with_overlap(self):
        raw_fact = "made a chicken stir-fry"
        distilled_facts = {"defaults to pasta when tired", "prefers chicken stir-fry dishes"}
        assert fact_is_covered(raw_fact, distilled_facts) is True

    def test_fact_is_not_covered(self):
        raw_fact = "made risotto for the first time"
        distilled_facts = {"defaults to pasta when tired", "no shellfish allergy"}
        assert fact_is_covered(raw_fact, distilled_facts) is False


class TestValidateDistillation:
    def test_validate_all_covered_passes(self):
        raw = (
            "- [2026-03-07] Made a chicken stir-fry\n"
            "- [2026-02-20] \"I keep defaulting to pasta when I'm tired\"\n"
        )
        proposed = (
            "- Defaults to pasta when tired\n"
            "- Made chicken stir-fry recently\n"
        )
        result = validate_distillation(raw, proposed)
        assert result.passed is True
        assert result.coverage_score == 1.0
        assert result.missing_facts == []

    def test_validate_missing_facts_fails(self):
        raw = (
            "- [2026-03-07] Made a chicken stir-fry\n"
            "- [2026-03-01] Made risotto for the first time\n"
            "- [2026-02-20] \"I keep defaulting to pasta when I'm tired\"\n"
        )
        proposed = (
            "- Defaults to pasta when tired\n"
        )
        result = validate_distillation(raw, proposed)
        assert result.passed is False
        assert result.coverage_score < 1.0
        assert len(result.missing_facts) > 0

    def test_validate_empty_raw_passes(self):
        result = validate_distillation("", "- Some distilled fact")
        assert result.passed is True
        assert result.coverage_score == 1.0
        assert result.missing_facts == []

    def test_validate_reports_coverage_score(self):
        raw = (
            "- Likes pasta\n"
            "- Likes chicken\n"
            "- Likes salads\n"
            "- Likes sushi\n"
        )
        # Only cover 2 out of 4: pasta and chicken
        proposed = (
            "- Enjoys pasta dishes\n"
            "- Enjoys chicken meals\n"
        )
        result = validate_distillation(raw, proposed)
        assert result.passed is False
        assert 0.0 < result.coverage_score < 1.0
        assert len(result.missing_facts) > 0
