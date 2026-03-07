"""Tests for the post-session hook (memory extraction and state update)."""

from __future__ import annotations

import json

from concierge.hooks.post_session import (
    extract_memories,
    _extract_preferences,
    update_session_state,
)


class TestExtractMemories:
    def test_extract_memories_finds_preferences(self, tmp_data_dir):
        transcript = "I like sushi very much."
        # Need a topic file to exist for append_raw_entry to work
        topic_file = tmp_data_dir / "topics" / "general.md"
        topic_file.write_text("## Distilled\n\n## Raw\n")

        results = extract_memories(transcript, tmp_data_dir)
        assert results["preferences"] >= 1

    def test_extract_memories_cooking_topic(self, tmp_data_dir):
        transcript = "I cooked pasta yesterday."
        # Need the meals topic file
        topic_file = tmp_data_dir / "topics" / "meals.md"
        topic_file.write_text("## Distilled\n\n## Raw\n")

        results = extract_memories(transcript, tmp_data_dir)
        assert results["preferences"] >= 1

    def test_extract_memories_creates_auto_entry(self, tmp_data_dir):
        transcript = "Just a regular chat."
        results = extract_memories(transcript, tmp_data_dir)
        assert results["auto_entries"] == 1

        # Verify the auto entry was written
        auto_file = tmp_data_dir / "auto" / "sessions.jsonl"
        assert auto_file.exists()
        entry = json.loads(auto_file.read_text().strip())
        assert entry["type"] == "session"
        assert "timestamp" in entry


class TestExtractPreferences:
    def test_extract_preferences_like_pattern(self):
        transcript = "I like pasta."
        prefs = _extract_preferences(transcript)
        assert len(prefs) >= 1
        assert any("pasta" in p["entry"] for p in prefs)
        assert all(p["topic"] in ("general", "meals", "health") for p in prefs)

    def test_extract_preferences_love_pattern(self):
        transcript = "I love running in the morning."
        prefs = _extract_preferences(transcript)
        assert len(prefs) >= 1
        assert any("running" in p["entry"] for p in prefs)

    def test_extract_preferences_allergic_pattern(self):
        transcript = "I'm allergic to peanuts."
        prefs = _extract_preferences(transcript)
        assert len(prefs) >= 1
        assert any(p["topic"] == "health" for p in prefs)
        assert any("peanuts" in p["entry"] for p in prefs)

    def test_extract_preferences_empty_transcript(self):
        prefs = _extract_preferences("")
        assert prefs == []

    def test_extract_preferences_no_match(self):
        transcript = "The weather is nice today."
        prefs = _extract_preferences(transcript)
        assert prefs == []


class TestUpdateSessionState:
    def test_update_session_state_creates_entry(self, tmp_data_dir):
        update_session_state(tmp_data_dir)
        state_file = tmp_data_dir / "state" / "session_history.jsonl"
        assert state_file.exists()

        entry = json.loads(state_file.read_text().strip())
        assert "ended_at" in entry

    def test_update_session_state_appends(self, tmp_data_dir):
        update_session_state(tmp_data_dir, session_summary={"mood": "happy"})
        update_session_state(tmp_data_dir, session_summary={"mood": "neutral"})

        state_file = tmp_data_dir / "state" / "session_history.jsonl"
        lines = [line for line in state_file.read_text().strip().split("\n") if line]
        assert len(lines) == 2

        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["mood"] == "happy"
        assert second["mood"] == "neutral"

    def test_update_session_state_with_summary(self, tmp_data_dir):
        update_session_state(tmp_data_dir, session_summary={"topics": ["cooking"]})
        state_file = tmp_data_dir / "state" / "session_history.jsonl"
        entry = json.loads(state_file.read_text().strip())
        assert entry["topics"] == ["cooking"]
