"""Write concierge memory files (auto index, topic raw entries)."""

# Design rationale:
# Append-only writers for concierge memory: auto-indexed JSONL entries and
# raw topic entries. Separates write concerns from read/query logic.
# Uses UTC timestamps consistently; auto-generated timestamp intentionally
# overwrites any caller-provided 'timestamp' to guarantee consistency.
# Key invariants: parent directories are created on demand; files are
# never truncated.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def append_auto_entry(path: Path, entry: dict[str, object]) -> None:
    """Append a timestamped JSONL entry to *path*.

    Adds a ``"timestamp"`` key with the current UTC ISO-8601 timestamp.
    Creates parent directories if they do not exist.

    Note: auto-generated timestamp overwrites any 'timestamp' key in the entry dict.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}
    with path.open("a") as fh:
        fh.write(json.dumps(stamped) + "\n")


def append_raw_entry(topic_path: Path, text: str) -> None:
    """Append a dated raw entry to the end of a topic file.

    The entry is formatted as ``- [YYYY-MM-DD] text`` and appended at the
    end of the file (which is the end of the ``## Raw`` section).
    Ensures a trailing newline.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = f"- [{date_str}] {text}"

    content = topic_path.read_text()
    if not content.endswith("\n"):
        content += "\n"
    content += line + "\n"
    topic_path.write_text(content)
