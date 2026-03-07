"""Distillation compression — generates updated summaries from raw entries.

In production, this calls a headless CLI for LLM summarization.
For v1, provides a stub that extracts key facts deterministically.
"""
from __future__ import annotations

import re
from pathlib import Path


def compress_topic(
    distilled_text: str,
    raw_text: str,
    topic: str,
) -> str:
    """Generate a proposed new distilled section from raw entries.

    V1 stub: deterministic extraction. Production would use LLM.

    Strategy:
    1. Keep existing distilled entries
    2. Add new entries from raw that aren't covered
    3. Update frequency counts for repeated patterns
    """
    # Parse existing distilled bullets
    existing = set()
    for line in distilled_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            existing.add(stripped[2:].lower().strip())

    # Extract new entries from raw
    new_entries = []
    for match in re.finditer(r"^- \[\d{4}-\d{2}-\d{2}\]\s*(.+)$", raw_text, re.MULTILINE):
        entry = match.group(1).strip()
        # Check if this is already covered (simple substring check)
        covered = any(
            _significant_overlap(entry.lower(), existing_entry)
            for existing_entry in existing
        )
        if not covered:
            new_entries.append(entry)

    # Build proposed distilled section
    lines = []
    # Keep existing distilled content
    for line in distilled_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lines.append(stripped)

    # Add new unique entries
    for entry in new_entries[:10]:  # Cap at 10 new entries
        lines.append(f"- {entry}")

    return "\n".join(lines)


def _significant_overlap(new: str, existing: str) -> bool:
    """Check if new entry significantly overlaps with existing distilled entry."""
    new_words = set(new.split()) - {"the", "a", "an", "i", "my"}
    existing_words = set(existing.split()) - {"the", "a", "an", "i", "my"}
    if not new_words or not existing_words:
        return False
    overlap = len(new_words & existing_words)
    return overlap / max(len(new_words), 1) > 0.5
