"""Read concierge memory files (topics, core, personality)."""

from __future__ import annotations

import re
from pathlib import Path


def _extract_section(text: str, header: str) -> str:
    """Extract content under a ``## Header`` until the next ``##`` or EOF.

    Returns the trimmed body (without the header line itself), or an empty
    string if the header is not found.
    """
    pattern = rf"^## {re.escape(header)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if match is None:
        return ""
    return match.group(1).strip()


def read_topic_distilled(path: Path) -> str:
    """Return the ``## Distilled`` section of a topic file."""
    if not path.is_file():
        return ""
    return _extract_section(path.read_text(), "Distilled")


def read_topic_raw(path: Path, last_n: int | None = None) -> str:
    """Return the ``## Raw`` section of a topic file.

    If *last_n* is given, only the last *last_n* non-empty lines are returned.
    """
    if not path.is_file():
        return ""
    section = _extract_section(path.read_text(), "Raw")
    if not section:
        return ""
    if last_n is not None:
        lines = [line for line in section.splitlines() if line.strip()]
        section = "\n".join(lines[-last_n:])
    return section


def read_topic_full(path: Path) -> str:
    """Return the full content of a topic file."""
    if not path.is_file():
        return ""
    return path.read_text()


def read_core(data_dir: Path) -> str:
    """Read ``core.md`` from *data_dir*."""
    core = data_dir / "core.md"
    if not core.is_file():
        return ""
    return core.read_text()


def read_personality(data_dir: Path) -> str:
    """Read ``PERSONALITY.md`` from *data_dir*."""
    personality = data_dir / "PERSONALITY.md"
    if not personality.is_file():
        return ""
    return personality.read_text()


def list_topics(topics_dir: Path) -> list[str]:
    """Return topic names (stems of ``.md`` files) in *topics_dir*."""
    if not topics_dir.is_dir():
        return []
    return [p.stem for p in sorted(topics_dir.glob("*.md"))]
