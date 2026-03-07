"""Tests for the huddle conversation engine."""

from datetime import datetime, timedelta, timezone

from concierge.features.huddles import (
    HUDDLE_QUESTIONS,
    HuddleState,
    evaluate_huddle_candidates,
    get_current_question,
    get_current_question_key,
    process_huddle_reply,
)
from concierge.models import FeatureType, SessionState


class TestHuddleState:
    def test_huddle_state_initial(self):
        """A new HuddleState starts at index 0, no answers, not completed."""
        state = HuddleState(huddle_type="initial")

        assert state.huddle_type == "initial"
        assert state.question_index == 0
        assert state.answers == {}
        assert state.completed is False
        assert state.started_at is not None

    def test_advance_increments_index(self):
        """advance() increments question_index by 1."""
        state = HuddleState(huddle_type="initial")
        assert state.question_index == 0

        state.advance()
        assert state.question_index == 1

        state.advance()
        assert state.question_index == 2

    def test_record_answer_stores_and_advances(self):
        """record_answer() stores the answer under the key and advances."""
        state = HuddleState(huddle_type="initial")

        state.record_answer("favorite_food", "Sushi")
        assert state.answers["favorite_food"] == "Sushi"
        assert state.question_index == 1

        state.record_answer("daily_routine", "Wake up, coffee, code")
        assert state.answers["daily_routine"] == "Wake up, coffee, code"
        assert state.question_index == 2


class TestGetCurrentQuestion:
    def test_get_current_question_returns_text(self):
        """Returns the question text for the current index."""
        state = HuddleState(huddle_type="initial")
        q = get_current_question(state)
        assert q == HUDDLE_QUESTIONS["initial"][0][1]

    def test_get_current_question_after_advance(self):
        """Returns the next question after advancing."""
        state = HuddleState(huddle_type="initial")
        state.advance()
        q = get_current_question(state)
        assert q == HUDDLE_QUESTIONS["initial"][1][1]

    def test_get_current_question_returns_none_when_done(self):
        """Returns None when all questions have been exhausted."""
        state = HuddleState(huddle_type="initial")
        # Advance past all questions
        for _ in range(len(HUDDLE_QUESTIONS["initial"])):
            state.advance()

        assert get_current_question(state) is None

    def test_get_current_question_key(self):
        """Returns the question key for the current index."""
        state = HuddleState(huddle_type="personality")
        key = get_current_question_key(state)
        assert key == "tone_preference"

    def test_get_current_question_key_none_when_done(self):
        """Returns None for key when all questions exhausted."""
        state = HuddleState(huddle_type="check-in")
        for _ in range(len(HUDDLE_QUESTIONS["check-in"])):
            state.advance()
        assert get_current_question_key(state) is None


class TestProcessHuddleReply:
    def test_process_reply_returns_next_question(self):
        """Processing a reply records the answer and returns the next question."""
        state = HuddleState(huddle_type="initial")

        next_q = process_huddle_reply(state, "Pizza")
        assert state.answers["favorite_food"] == "Pizza"
        assert state.question_index == 1
        assert next_q == HUDDLE_QUESTIONS["initial"][1][1]
        assert state.completed is False

    def test_process_reply_returns_none_when_complete(self):
        """Returns None and sets completed when last question is answered."""
        state = HuddleState(huddle_type="check-in")
        # check-in has 2 questions
        process_huddle_reply(state, "Nothing much changed")
        next_q = process_huddle_reply(state, "Everything is great")

        assert next_q is None
        assert state.completed is True
        assert len(state.answers) == 2

    def test_process_reply_on_already_completed_huddle(self):
        """Returns None if called on an already-completed huddle."""
        state = HuddleState(huddle_type="check-in")
        for q_key, _ in HUDDLE_QUESTIONS["check-in"]:
            process_huddle_reply(state, f"answer for {q_key}")

        assert state.completed is True
        result = process_huddle_reply(state, "extra answer")
        assert result is None


class TestEvaluateHuddleCandidates:
    def test_evaluate_triggers_initial_huddle(self, tmp_data_dir):
        """Returns an initial huddle candidate when core.md is missing."""
        session = SessionState()

        candidates = evaluate_huddle_candidates(session, tmp_data_dir)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.feature_type == FeatureType.HUDDLE
        assert c.domain == "initial"
        assert c.metadata is not None
        assert c.metadata["huddle_type"] == "initial"

    def test_evaluate_no_candidate_when_core_exists(self, tmp_data_dir):
        """Returns no initial huddle candidate when core.md exists."""
        (tmp_data_dir / "core.md").write_text("# User Profile\nName: Test\n")
        session = SessionState()

        candidates = evaluate_huddle_candidates(session, tmp_data_dir)
        # Should be empty (no initial trigger, and no check-in trigger unless
        # enough time has passed)
        initial_candidates = [
            c for c in candidates
            if c.metadata and c.metadata.get("huddle_type") == "initial"
        ]
        assert initial_candidates == []

    def test_evaluate_no_candidate_when_huddle_active(self, tmp_data_dir):
        """Returns empty if a huddle is already active."""
        session = SessionState(
            active_feature=FeatureType.HUDDLE,
            active_feature_id="initial",
        )

        candidates = evaluate_huddle_candidates(session, tmp_data_dir)
        assert candidates == []

    def test_evaluate_checkin_trigger_after_90_days(self, tmp_data_dir):
        """Returns a check-in candidate when last check-in was > 90 days ago."""
        (tmp_data_dir / "core.md").write_text("# User Profile\nName: Test\n")
        # Write a check-in timestamp 91 days ago
        now = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        old_checkin = now - timedelta(days=91)
        checkin_file = tmp_data_dir / "state" / "last-checkin.txt"
        checkin_file.write_text(old_checkin.isoformat())

        session = SessionState()
        candidates = evaluate_huddle_candidates(session, tmp_data_dir, now=now)

        checkin_candidates = [
            c for c in candidates
            if c.metadata and c.metadata.get("huddle_type") == "check-in"
        ]
        assert len(checkin_candidates) == 1

    def test_evaluate_no_checkin_when_recent(self, tmp_data_dir):
        """No check-in candidate when last check-in was < 90 days ago."""
        (tmp_data_dir / "core.md").write_text("# User Profile\nName: Test\n")
        now = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        recent_checkin = now - timedelta(days=30)
        checkin_file = tmp_data_dir / "state" / "last-checkin.txt"
        checkin_file.write_text(recent_checkin.isoformat())

        session = SessionState()
        candidates = evaluate_huddle_candidates(session, tmp_data_dir, now=now)

        checkin_candidates = [
            c for c in candidates
            if c.metadata and c.metadata.get("huddle_type") == "check-in"
        ]
        assert checkin_candidates == []

    def test_evaluate_goals_trigger_with_topics(self, tmp_data_dir):
        """Returns a goals candidate when 3+ topic files exist but no goals."""
        (tmp_data_dir / "core.md").write_text("# User Profile\nName: Test\n")
        # Create 3 topic files
        topics_dir = tmp_data_dir / "topics"
        (topics_dir / "cooking.md").write_text("# Cooking notes")
        (topics_dir / "fitness.md").write_text("# Fitness notes")
        (topics_dir / "reading.md").write_text("# Reading notes")

        session = SessionState()
        candidates = evaluate_huddle_candidates(session, tmp_data_dir)

        goals_candidates = [
            c for c in candidates
            if c.metadata and c.metadata.get("huddle_type") == "goals"
        ]
        assert len(goals_candidates) == 1

    def test_evaluate_no_goals_when_goals_exist(self, tmp_data_dir):
        """No goals candidate when goals.md already exists."""
        (tmp_data_dir / "core.md").write_text("# User Profile\nName: Test\n")
        (tmp_data_dir / "goals.md").write_text("# Goals\n- Learn guitar")
        topics_dir = tmp_data_dir / "topics"
        (topics_dir / "cooking.md").write_text("# Cooking notes")
        (topics_dir / "fitness.md").write_text("# Fitness notes")
        (topics_dir / "reading.md").write_text("# Reading notes")

        session = SessionState()
        candidates = evaluate_huddle_candidates(session, tmp_data_dir)

        goals_candidates = [
            c for c in candidates
            if c.metadata and c.metadata.get("huddle_type") == "goals"
        ]
        assert goals_candidates == []


class TestHuddleQuestionsDefinitions:
    def test_huddle_questions_all_types_defined(self):
        """All six huddle types have question definitions."""
        expected_types = {
            "initial", "personality", "goals", "check-in",
            "valet-setup", "probe-setup",
        }
        assert set(HUDDLE_QUESTIONS.keys()) == expected_types

    def test_all_question_lists_non_empty(self):
        """Every huddle type has at least one question."""
        for huddle_type, questions in HUDDLE_QUESTIONS.items():
            assert len(questions) > 0, f"{huddle_type} has no questions"

    def test_question_entries_are_tuples(self):
        """Each question entry is a (key, text) tuple."""
        for huddle_type, questions in HUDDLE_QUESTIONS.items():
            for entry in questions:
                assert isinstance(entry, tuple), (
                    f"{huddle_type} has non-tuple entry: {entry}"
                )
                assert len(entry) == 2, (
                    f"{huddle_type} has entry with wrong length: {entry}"
                )
                key, text = entry
                assert isinstance(key, str)
                assert isinstance(text, str)
