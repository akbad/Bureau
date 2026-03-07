"""Tests for the pre-session hook (context builder)."""

from __future__ import annotations

from concierge.hooks.pre_session import build_context, _build_vocabulary_guidance
from concierge.vocabulary import VocabularyTracker


class TestBuildContext:
    def test_build_context_includes_personality(self, tmp_data_dir):
        (tmp_data_dir / "PERSONALITY.md").write_text("You are warm and friendly.")
        ctx = build_context(tmp_data_dir)
        assert "## Personality" in ctx
        assert "warm and friendly" in ctx

    def test_build_context_includes_core(self, tmp_data_dir):
        (tmp_data_dir / "core.md").write_text("User prefers metric units.")
        ctx = build_context(tmp_data_dir)
        assert "## Core Memory" in ctx
        assert "metric units" in ctx

    def test_build_context_includes_vocabulary_guidance(self, tmp_data_dir):
        # Create a vocabulary state file with an introduced term
        tracker = VocabularyTracker()
        tracker.introduce("dispatch", "user asked about routing")
        tracker.save(tmp_data_dir / "state" / "vocabulary.yml")

        ctx = build_context(tmp_data_dir)
        assert "## Vocabulary" in ctx
        assert "dispatch" in ctx

    def test_build_context_includes_topic_distilled(self, tmp_data_dir):
        topic_file = tmp_data_dir / "topics" / "cooking.md"
        topic_file.write_text(
            "## Distilled\nUser enjoys Italian cuisine.\n\n## Raw\n- entry\n"
        )
        ctx = build_context(tmp_data_dir)
        assert "### Cooking" in ctx
        assert "Italian cuisine" in ctx

    def test_build_context_respects_budget(self, tmp_data_dir):
        (tmp_data_dir / "PERSONALITY.md").write_text("Be kind.")
        (tmp_data_dir / "core.md").write_text("Core info.")
        # Create a topic with lots of words that would blow the budget
        big_text = " ".join(["word"] * 5000)
        topic_file = tmp_data_dir / "topics" / "verbose.md"
        topic_file.write_text(f"## Distilled\n{big_text}\n\n## Raw\n- x\n")

        ctx = build_context(tmp_data_dir, context_budget=50)
        # Personality and core are always included, but the huge topic should be skipped
        assert "## Personality" in ctx
        assert "## Core Memory" in ctx
        assert "### Verbose" not in ctx

    def test_build_context_empty_data_dir(self, tmp_data_dir):
        # No files created — everything returns empty
        ctx = build_context(tmp_data_dir)
        # Should not crash, may be empty or just have vocabulary section
        assert isinstance(ctx, str)

    def test_build_context_multiple_topics_budget(self, tmp_data_dir):
        """Topics are loaded in order until the budget is exhausted."""
        (tmp_data_dir / "PERSONALITY.md").write_text("Short.")
        (tmp_data_dir / "core.md").write_text("Short.")

        # Create two topics; the first fits, the second should not.
        # Budget must be large enough for personality + core + vocabulary
        # (~70 words from default terms) + alpha (~4 words) but not beta (~502).
        t1 = tmp_data_dir / "topics" / "alpha.md"
        t1.write_text("## Distilled\nSmall topic content.\n\n## Raw\n- x\n")

        t2 = tmp_data_dir / "topics" / "beta.md"
        big = " ".join(["word"] * 500)
        t2.write_text(f"## Distilled\n{big}\n\n## Raw\n- x\n")

        ctx = build_context(tmp_data_dir, context_budget=90)
        assert "### Alpha" in ctx
        assert "### Beta" not in ctx


class TestBuildVocabularyGuidance:
    def test_vocabulary_guidance_introduced_term(self):
        tracker = VocabularyTracker()
        tracker.introduce("dispatch", "routing context")
        guidance = _build_vocabulary_guidance(tracker)
        assert "'dispatch'" in guidance
        assert "introduced but user hasn't used it yet" in guidance

    def test_vocabulary_guidance_user_used_term(self):
        tracker = VocabularyTracker()
        tracker.introduce("brew", "recipe context")
        tracker.mark_user_used("brew")
        guidance = _build_vocabulary_guidance(tracker)
        assert "'brew'" in guidance
        assert "use freely" in guidance

    def test_vocabulary_guidance_unknown_term(self):
        tracker = VocabularyTracker()
        # Default state — nothing introduced
        guidance = _build_vocabulary_guidance(tracker)
        assert "NOT introduced" in guidance
        assert "describe naturally" in guidance

    def test_vocabulary_guidance_empty_tracker(self):
        tracker = VocabularyTracker(terms={})
        guidance = _build_vocabulary_guidance(tracker)
        assert guidance == ""
