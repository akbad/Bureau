"""Tests for distillation candidate detection (Task 8.1)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from concierge.distillation.detection import (
    CandidateInfo,
    compute_redundancy_score,
    count_raw_entries,
    detect_patterns,
    extract_key_phrases,
    load_candidates,
    save_candidates,
    scan_all_topics,
    scan_topic,
)


# ---------------------------------------------------------------------------
# count_raw_entries
# ---------------------------------------------------------------------------

class TestCountRawEntries:
    def test_count_raw_entries(self):
        raw = (
            "- [2026-03-07] Made a chicken stir-fry\n"
            "- [2026-03-01] Made risotto for the first time\n"
            "- [2026-02-20] Defaulted to pasta again\n"
        )
        assert count_raw_entries(raw) == 3

    def test_count_raw_entries_empty(self):
        assert count_raw_entries("") == 0
        assert count_raw_entries("No entries here") == 0


# ---------------------------------------------------------------------------
# extract_key_phrases
# ---------------------------------------------------------------------------

class TestExtractKeyPhrases:
    def test_extract_key_phrases(self):
        raw = (
            "- [2026-03-07] Made a chicken stir-fry\n"
            "- [2026-03-01] Made risotto for the first time\n"
        )
        phrases = extract_key_phrases(raw)
        assert len(phrases) == 2
        assert phrases[0] == "made a chicken stir-fry"
        assert phrases[1] == "made risotto for the first time"


# ---------------------------------------------------------------------------
# compute_redundancy_score
# ---------------------------------------------------------------------------

class TestComputeRedundancy:
    def test_compute_redundancy_low_overlap(self):
        phrases = [
            "made a chicken stir-fry",
            "went to the dentist",
            "bought new shoes",
        ]
        score = compute_redundancy_score(phrases)
        assert 0.0 <= score <= 0.3

    def test_compute_redundancy_high_overlap(self):
        phrases = [
            "made pasta for dinner",
            "cooked pasta again tonight",
            "defaulted to pasta when tired",
            "had pasta because lazy",
            "pasta for dinner again",
        ]
        score = compute_redundancy_score(phrases)
        assert score > 0.3


# ---------------------------------------------------------------------------
# detect_patterns
# ---------------------------------------------------------------------------

class TestDetectPatterns:
    def test_detect_patterns_finds_repeated_words(self):
        phrases = [
            "made pasta for dinner",
            "cooked pasta again tonight",
            "defaulted to pasta when tired",
            "had pasta because lazy",
        ]
        patterns = detect_patterns(phrases)
        assert len(patterns) >= 1
        assert any("pasta" in p for p in patterns)

    def test_detect_patterns_empty(self):
        assert detect_patterns([]) == []


# ---------------------------------------------------------------------------
# scan_topic
# ---------------------------------------------------------------------------

class TestScanTopic:
    def test_scan_topic_with_enough_data(self, tmp_data_dir):
        topic_file = tmp_data_dir / "topics" / "meals.md"
        raw_entries = "\n".join(
            f"- [2026-03-{i:02d}] Made pasta for dinner"
            for i in range(1, 11)
        )
        topic_file.write_text(
            "# topics/meals.md\n\n"
            "## Distilled\n"
            "- Likes cooking\n\n"
            "## Raw\n"
            f"{raw_entries}\n"
        )
        info = scan_topic(tmp_data_dir, "meals")
        assert info.topic == "meals"
        assert info.raw_entries_since_last == 10
        assert info.redundancy_score > 0.0
        # With 10 identical entries it should be a candidate
        assert info.status == "candidate"
        assert info.candidate_since is not None

    def test_scan_topic_missing_file(self, tmp_data_dir):
        info = scan_topic(tmp_data_dir, "nonexistent")
        assert info.redundancy_score == 0.0
        assert info.raw_entries_since_last == 0
        assert info.status == "idle"


# ---------------------------------------------------------------------------
# scan_all_topics
# ---------------------------------------------------------------------------

class TestScanAllTopics:
    def test_scan_all_topics(self, tmp_data_dir):
        (tmp_data_dir / "topics" / "meals.md").write_text(
            "## Distilled\n- Summary\n\n## Raw\n- [2026-03-07] Entry\n"
        )
        (tmp_data_dir / "topics" / "people.md").write_text(
            "## Distilled\n- Summary\n\n## Raw\n- [2026-03-07] Met Alice\n"
        )
        results = scan_all_topics(tmp_data_dir)
        assert len(results) == 2
        topics = {r.topic for r in results}
        assert topics == {"meals", "people"}


# ---------------------------------------------------------------------------
# save / load roundtrip
# ---------------------------------------------------------------------------

class TestSaveLoadCandidates:
    def test_save_and_load_candidates_roundtrip(self, tmp_data_dir):
        now = datetime.now(timezone.utc)
        candidates = [
            CandidateInfo(
                topic="meals",
                redundancy_score=0.72,
                raw_entries_since_last=12,
                detected_patterns=["pasta: 4 mentions"],
                candidate_since=now,
                status="candidate",
            ),
            CandidateInfo(
                topic="people",
                redundancy_score=0.15,
                raw_entries_since_last=3,
                detected_patterns=[],
                candidate_since=None,
                status="idle",
            ),
        ]

        save_candidates(tmp_data_dir, candidates)
        loaded = load_candidates(tmp_data_dir)

        assert set(loaded.keys()) == {"meals", "people"}

        meals = loaded["meals"]
        assert meals.redundancy_score == 0.72
        assert meals.raw_entries_since_last == 12
        assert meals.status == "candidate"
        assert meals.candidate_since is not None
        assert meals.detected_patterns == ["pasta: 4 mentions"]

        people = loaded["people"]
        assert people.redundancy_score == 0.15
        assert people.status == "idle"
        assert people.candidate_since is None
