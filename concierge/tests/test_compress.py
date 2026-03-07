"""Tests for distillation compression (Task 8.2)."""

from concierge.distillation.compress import compress_topic, _significant_overlap


# ---------------------------------------------------------------------------
# compress_topic
# ---------------------------------------------------------------------------

class TestCompressTopic:
    def test_compress_keeps_existing(self):
        distilled = "- Likes pasta\n- Shops at Trader Joe's"
        raw = "- [2026-03-07] Made a chicken stir-fry\n"
        result = compress_topic(distilled, raw, "meals")
        assert "Likes pasta" in result
        assert "Shops at Trader Joe's" in result

    def test_compress_adds_new_entries(self):
        distilled = "- Likes pasta"
        raw = (
            "- [2026-03-07] Started a sourdough starter\n"
            "- [2026-03-06] Bought a new cast iron pan\n"
        )
        result = compress_topic(distilled, raw, "meals")
        assert "Likes pasta" in result
        assert "Started a sourdough starter" in result
        assert "Bought a new cast iron pan" in result

    def test_compress_skips_duplicates(self):
        distilled = "- Likes pasta"
        raw = "- [2026-03-07] Likes pasta a lot\n"
        result = compress_topic(distilled, raw, "meals")
        # The raw entry overlaps significantly with the existing distilled
        lines = [l for l in result.splitlines() if l.strip().startswith("- ")]
        # Should not double up - the original bullet stays, but the raw one is skipped
        assert lines.count("- Likes pasta") == 1

    def test_compress_empty_distilled(self):
        distilled = ""
        raw = (
            "- [2026-03-07] Made a chicken stir-fry\n"
            "- [2026-03-06] Tried sushi for the first time\n"
        )
        result = compress_topic(distilled, raw, "meals")
        assert "Made a chicken stir-fry" in result
        assert "Tried sushi for the first time" in result

    def test_compress_empty_raw(self):
        distilled = "- Likes pasta\n- Shops at Trader Joe's"
        raw = ""
        result = compress_topic(distilled, raw, "meals")
        assert "Likes pasta" in result
        assert "Shops at Trader Joe's" in result


# ---------------------------------------------------------------------------
# _significant_overlap
# ---------------------------------------------------------------------------

class TestSignificantOverlap:
    def test_significant_overlap(self):
        assert _significant_overlap("likes pasta a lot", "likes pasta") is True
        assert _significant_overlap(
            "started a sourdough starter",
            "likes pasta",
        ) is False
