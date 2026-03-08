"""Semantic diff validator -- ensures distillation doesn't lose information."""

# Design rationale:
# Validates that proposed distilled summaries cover all raw facts by keyword overlap.
# Uses the shared STOP_WORDS set for consistent word filtering across the package.
# Key invariant: validation fails if ANY established fact is lost during distillation.

from __future__ import annotations

import re
from dataclasses import dataclass

from . import STOP_WORDS


@dataclass
class ValidationResult:
    """Result of a semantic diff validation."""

    passed: bool
    coverage_score: float  # 0.0-1.0, fraction of raw facts covered
    missing_facts: list[str]  # Facts from raw not in proposed distilled
    extra_facts: list[str]  # Facts in proposed not traceable to raw


def extract_facts(text: str) -> set[str]:
    """Extract a set of fact phrases from markdown text.

    Works on both distilled bullets and raw entries.
    Normalizes: lowercase, strips dates, strips common filler words.
    Returns a set of simplified fact strings.
    """
    facts = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        # Remove the bullet
        fact = stripped[2:].strip()
        # Remove date prefix if present
        fact = re.sub(r"^\[\d{4}-\d{2}-\d{2}\]\s*", "", fact)
        # Remove frequency annotations like (~weekly)
        fact = re.sub(r"\(~?\w+\)", "", fact)
        # Remove quotes
        fact = fact.strip("\"'")
        # Normalize
        fact = fact.lower().strip()
        if fact:
            facts.add(fact)
    return facts


def extract_key_words(fact: str) -> set[str]:
    """Extract meaningful words from a fact string."""
    return {w for w in fact.split() if w not in STOP_WORDS and len(w) > 1}


def fact_is_covered(raw_fact: str, distilled_facts: set[str]) -> bool:
    """Check if a raw fact is adequately covered by any distilled fact.

    Uses keyword overlap: if 50%+ of the raw fact's key words appear
    in some distilled fact, it's considered covered.
    """
    raw_keywords = extract_key_words(raw_fact)
    if not raw_keywords:
        return True  # Empty fact is trivially covered

    for d_fact in distilled_facts:
        d_keywords = extract_key_words(d_fact)
        overlap = len(raw_keywords & d_keywords)
        if overlap / len(raw_keywords) >= 0.5:
            return True
    return False


def validate_distillation(
    raw_text: str,
    proposed_distilled: str,
) -> ValidationResult:
    """Validate that proposed distilled section covers all raw facts.

    Track A: Semantic Diff (Automated, Immediate)
    1. Extract facts from raw entries
    2. Extract facts from proposed distilled
    3. Check coverage: every raw fact should be represented in distilled
    4. PASS if all established facts covered
    5. FAIL if any information loss detected
    """
    raw_facts = extract_facts(raw_text)
    distilled_facts = extract_facts(proposed_distilled)

    if not raw_facts:
        return ValidationResult(
            passed=True,
            coverage_score=1.0,
            missing_facts=[],
            extra_facts=[],
        )

    missing = []
    for fact in raw_facts:
        if not fact_is_covered(fact, distilled_facts):
            missing.append(fact)

    # Check for extra facts in distilled not traceable to raw
    extra = []
    for fact in distilled_facts:
        if not fact_is_covered(fact, raw_facts):
            extra.append(fact)

    covered = len(raw_facts) - len(missing)
    coverage = covered / len(raw_facts) if raw_facts else 1.0

    return ValidationResult(
        passed=len(missing) == 0,
        coverage_score=round(coverage, 2),
        missing_facts=sorted(missing),
        extra_facts=sorted(extra),
    )
