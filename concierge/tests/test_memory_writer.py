import json
from concierge.memory.writer import append_auto_entry, append_raw_entry

class TestAutoIndex:
    def test_append_creates_file(self, tmp_data_dir):
        append_auto_entry(
            tmp_data_dir / "auto" / "index.jsonl",
            {"fact": "likes pasta", "domain": "meals"},
        )
        lines = (tmp_data_dir / "auto" / "index.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["fact"] == "likes pasta"
        assert "timestamp" in entry

    def test_append_adds_to_existing(self, tmp_data_dir):
        path = tmp_data_dir / "auto" / "index.jsonl"
        append_auto_entry(path, {"fact": "first"})
        append_auto_entry(path, {"fact": "second"})
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

class TestRawEntry:
    def test_append_raw_to_topic(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        topic.write_text("## Distilled\n- Summary\n\n## Raw\n- [2026-03-01] Old entry\n")
        append_raw_entry(topic, "Made risotto for the first time")
        content = topic.read_text()
        assert "Made risotto" in content
        assert content.index("Made risotto") > content.index("Old entry")
