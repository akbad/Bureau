"""Attache selector — maps Suites to relevant attache context files.

Stage 2 of the concierge pipeline: given the detected Suite, determine
which attache markdown files should be loaded to provide domain-specific
context for downstream generation.
"""

from __future__ import annotations

from pathlib import Path

from concierge.models import Suite

# ---------------------------------------------------------------------------
# Suite -> attache mapping
# ---------------------------------------------------------------------------

SUITE_ATTACHE_MAP: dict[Suite, list[str]] = {
    Suite.WORK: ["schedule", "finance"],
    Suite.REST: ["wellness", "meals", "home"],
    Suite.SOCIAL: ["events", "social", "shopping"],
    Suite.CREATIVE: ["shopping", "learning", "meals"],
    Suite.PROCESSING: [],
}


def select_attaches(suite: Suite) -> list[str]:
    """Return the list of attache names relevant to *suite*."""
    return list(SUITE_ATTACHE_MAP.get(suite, []))


def load_attache_content(attache_names: list[str], attaches_dir: Path) -> str:
    """Load and concatenate markdown files for the given attache names.

    Each attache name is resolved to ``<attaches_dir>/<name>.md``.  Files
    that do not exist are silently skipped.  The loaded contents are joined
    with double newlines.
    """
    parts: list[str] = []
    for name in attache_names:
        path = attaches_dir / f"{name}.md"
        if path.is_file():
            parts.append(path.read_text())
    return "\n\n".join(parts)
