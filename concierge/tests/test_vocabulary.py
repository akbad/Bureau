"""Tests for the vocabulary introduction tracker."""

from concierge.vocabulary import VocabularyTracker, FEATURE_TERMS


class TestInitialState:
    def test_initial_state_all_unknown(self):
        tracker = VocabularyTracker()
        for term in FEATURE_TERMS:
            assert not tracker.is_introduced(term)
            assert not tracker.can_use_term(term)


class TestIntroduce:
    def test_introduce_marks_term(self):
        tracker = VocabularyTracker()
        tracker.introduce("dispatch", "user asked about task routing")
        assert tracker.is_introduced("dispatch")
        assert tracker.terms["dispatch"].introduction_context == "user asked about task routing"
        assert tracker.terms["dispatch"].introduced_at is not None

    def test_should_introduce_when_not_introduced(self):
        tracker = VocabularyTracker()
        assert tracker.should_introduce("dispatch", "routing context")

    def test_should_not_introduce_when_already_introduced(self):
        tracker = VocabularyTracker()
        tracker.introduce("dispatch", "first time")
        assert not tracker.should_introduce("dispatch", "second time")


class TestCanUse:
    def test_can_use_after_introduction(self):
        tracker = VocabularyTracker()
        tracker.introduce("brew", "user explored recipes")
        assert tracker.can_use_term("brew")

    def test_cannot_use_before_introduction(self):
        tracker = VocabularyTracker()
        assert not tracker.can_use_term("brew")


class TestUserUsed:
    def test_mark_user_used_auto_introduces(self):
        tracker = VocabularyTracker()
        assert not tracker.is_introduced("probe")
        tracker.mark_user_used("probe")
        assert tracker.is_introduced("probe")
        assert tracker.terms["probe"].user_has_used


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        tracker = VocabularyTracker()
        tracker.introduce("dispatch", "routing context")
        tracker.mark_user_used("brew")

        path = tmp_path / "vocab.yml"
        tracker.save(path)

        loaded = VocabularyTracker.load(path)
        assert loaded.is_introduced("dispatch")
        assert loaded.terms["dispatch"].introduction_context == "routing context"
        assert loaded.terms["dispatch"].introduced_at is not None
        assert loaded.is_introduced("brew")
        assert loaded.terms["brew"].user_has_used

    def test_load_missing_file_returns_defaults(self, tmp_path):
        path = tmp_path / "nonexistent.yml"
        tracker = VocabularyTracker.load(path)
        assert not tracker.is_introduced("dispatch")
        assert isinstance(tracker.terms, dict)
