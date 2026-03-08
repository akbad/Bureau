"""Distillation candidate detection — identifies topics ripe for re-summarization."""

# Design rationale:
# Scans topic files for redundancy patterns to decide when re-summarization is needed.
# Uses the shared STOP_WORDS set and DistillationStatus enum for consistency.
# Key invariant: status field uses DistillationStatus enum, not raw strings.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re

import yaml

from . import STOP_WORDS
from .state import DistillationStatus


@dataclass
class CandidateInfo:
    """Information about a distillation candidate."""
    topic: str
    redundancy_score: float
    raw_entries_since_last: int
    detected_patterns: list[str] = field(default_factory=list)
    candidate_since: datetime | None = None
    status: DistillationStatus = DistillationStatus.IDLE


def count_raw_entries(raw_text: str) -> int:
    """Count the number of timestamped entries in raw text."""
    return len(re.findall(r"^- \[\d{4}-\d{2}-\d{2}\]", raw_text, re.MULTILINE))


def extract_key_phrases(raw_text: str) -> list[str]:
    """Extract key phrases from raw entries for redundancy detection.

    Returns lowercased phrases from each entry (after the date).
    """
    phrases = []
    for match in re.finditer(r"^- \[\d{4}-\d{2}-\d{2}\]\s*(.+)$", raw_text, re.MULTILINE):
        phrases.append(match.group(1).strip().lower())
    return phrases


def compute_redundancy_score(phrases: list[str]) -> float:
    """Compute a 0.0-1.0 redundancy score based on phrase similarity.

    Simple approach: count how many phrases share significant words
    with other phrases. Higher overlap = higher redundancy.

    Uses word overlap (Jaccard similarity between entry word sets).
    """
    if len(phrases) < 2:
        return 0.0

    word_sets = [set(p.split()) - STOP_WORDS for p in phrases]

    overlap_count = 0
    pair_count = 0
    for i in range(len(word_sets)):
        for j in range(i + 1, len(word_sets)):
            pair_count += 1
            if word_sets[i] & word_sets[j]:  # Any shared words
                jaccard = len(word_sets[i] & word_sets[j]) / max(len(word_sets[i] | word_sets[j]), 1)
                if jaccard > 0.15:
                    overlap_count += 1

    return min(overlap_count / max(pair_count, 1), 1.0)


def detect_patterns(phrases: list[str]) -> list[str]:
    """Detect repeated patterns/themes in raw entries.

    Returns human-readable pattern descriptions.
    """
    if not phrases:
        return []

    # Count word frequency
    word_freq: dict[str, int] = {}
    for phrase in phrases:
        for word in phrase.split():
            if word not in STOP_WORDS and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1

    patterns = []
    for word, count in sorted(word_freq.items(), key=lambda x: -x[1]):
        if count >= 3:
            patterns.append(f"{word}: {count} mentions")
        if len(patterns) >= 5:
            break

    return patterns


def scan_topic(data_dir: Path, topic: str) -> CandidateInfo:
    """Scan a single topic file for distillation candidacy.

    Reads the ## Raw section and computes redundancy metrics.
    """
    raw_path = data_dir / "topics" / f"{topic}.md"
    if not raw_path.exists():
        return CandidateInfo(topic=topic, redundancy_score=0.0, raw_entries_since_last=0)

    content = raw_path.read_text()

    # Extract raw section
    raw_match = re.search(r"## Raw\n([\s\S]*)", content)
    raw_text = raw_match.group(1) if raw_match else ""

    entry_count = count_raw_entries(raw_text)
    phrases = extract_key_phrases(raw_text)
    redundancy = compute_redundancy_score(phrases)
    patterns = detect_patterns(phrases)

    status = DistillationStatus.CANDIDATE if redundancy > 0.5 and entry_count >= 5 else DistillationStatus.IDLE

    return CandidateInfo(
        topic=topic,
        redundancy_score=round(redundancy, 2),
        raw_entries_since_last=entry_count,
        detected_patterns=patterns,
        candidate_since=datetime.now(timezone.utc) if status == DistillationStatus.CANDIDATE else None,
        status=status,
    )


def scan_all_topics(data_dir: Path) -> list[CandidateInfo]:
    """Scan all topic files and return candidacy info for each."""
    topics_dir = data_dir / "topics"
    if not topics_dir.exists():
        return []

    results = []
    for f in sorted(topics_dir.iterdir()):
        if f.suffix == ".md":
            topic = f.stem
            results.append(scan_topic(data_dir, topic))
    return results


def save_candidates(data_dir: Path, candidates: list[CandidateInfo]) -> None:
    """Save candidate info to distillation-candidates.yml."""
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    data = {}
    for c in candidates:
        data[c.topic] = {
            "redundancy_score": c.redundancy_score,
            "raw_entries_since_last": c.raw_entries_since_last,
            "detected_patterns": c.detected_patterns,
            "candidate_since": c.candidate_since.isoformat() if c.candidate_since else None,
            "status": c.status.value,
        }

    (state_dir / "distillation-candidates.yml").write_text(
        yaml.dump(data, default_flow_style=False)
    )


def load_candidates(data_dir: Path) -> dict[str, CandidateInfo]:
    """Load saved candidate info from YAML."""
    path = data_dir / "state" / "distillation-candidates.yml"
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text()) or {}
    result = {}
    for topic, entry in data.items():
        cs = entry.get("candidate_since")
        result[topic] = CandidateInfo(
            topic=topic,
            redundancy_score=entry.get("redundancy_score", 0.0),
            raw_entries_since_last=entry.get("raw_entries_since_last", 0),
            detected_patterns=entry.get("detected_patterns", []),
            candidate_since=datetime.fromisoformat(cs) if cs else None,
            status=DistillationStatus(entry.get("status", "idle")),
        )
    return result
