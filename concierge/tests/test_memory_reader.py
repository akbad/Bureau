from concierge.memory.reader import (
    read_topic_distilled, read_topic_raw, read_topic_full,
    read_core, read_personality, list_topics,
)

class TestTopicReader:
    def test_read_distilled_section(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        topic.write_text(
            "# topics/meals.md\n\n"
            "## Distilled\n"
            "- Likes pasta\n"
            "- Shops at Trader Joe's\n\n"
            "## Raw\n"
            "- [2026-03-07] Made pasta\n"
        )
        distilled = read_topic_distilled(topic)
        assert "Likes pasta" in distilled
        assert "Made pasta" not in distilled

    def test_read_raw_section(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        topic.write_text("## Distilled\n- Likes pasta\n\n## Raw\n- [2026-03-07] Made pasta\n")
        raw = read_topic_raw(topic)
        assert "Made pasta" in raw
        assert "Likes pasta" not in raw

    def test_read_raw_with_limit(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        lines = "\n".join(f"- [2026-03-{i:02d}] Entry {i}" for i in range(1, 20))
        topic.write_text(f"## Distilled\n- Summary\n\n## Raw\n{lines}\n")
        raw = read_topic_raw(topic, last_n=5)
        assert "Entry 19" in raw
        assert "[2026-03-01]" not in raw

    def test_list_topics(self, tmp_data_dir):
        (tmp_data_dir / "topics" / "meals.md").write_text("# meals")
        (tmp_data_dir / "topics" / "people.md").write_text("# people")
        topics = list_topics(tmp_data_dir / "topics")
        assert set(topics) == {"meals", "people"}

class TestCoreAndPersonality:
    def test_read_core(self, tmp_data_dir):
        (tmp_data_dir / "core.md").write_text("# Core\nPrefers mornings.")
        assert "Prefers mornings" in read_core(tmp_data_dir)

    def test_read_personality(self, tmp_data_dir):
        (tmp_data_dir / "PERSONALITY.md").write_text("Be warm and friendly.")
        assert "warm" in read_personality(tmp_data_dir)

    def test_read_missing_returns_empty(self, tmp_data_dir):
        assert read_core(tmp_data_dir) == ""
        assert read_personality(tmp_data_dir) == ""
