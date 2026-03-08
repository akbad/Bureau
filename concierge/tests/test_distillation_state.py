"""Tests for distillation state machine (Task 8.4)."""

import pytest

from concierge.distillation.state import (
    DistillationStateMachine,
    DistillationStatus,
    TopicDistillationState,
    VALID_TRANSITIONS,
)


class TestTopicDistillationState:
    def test_initial_status_is_idle(self):
        state = TopicDistillationState(topic="food")
        assert state.status == DistillationStatus.IDLE
        assert state.retry_count == 0
        assert state.last_distilled is None

    def test_valid_transition(self):
        state = TopicDistillationState(topic="food")
        state.transition(DistillationStatus.CANDIDATE)
        assert state.status == DistillationStatus.CANDIDATE

    def test_invalid_transition_raises(self):
        state = TopicDistillationState(topic="food")
        # IDLE -> COMPRESSED is not valid
        with pytest.raises(ValueError, match="Invalid transition"):
            state.transition(DistillationStatus.COMPRESSED)

    def test_full_lifecycle_happy_path(self):
        state = TopicDistillationState(topic="food")
        assert state.status == DistillationStatus.IDLE

        state.transition(DistillationStatus.CANDIDATE)
        assert state.status == DistillationStatus.CANDIDATE

        state.transition(DistillationStatus.COMPRESSING)
        assert state.status == DistillationStatus.COMPRESSING

        state.transition(DistillationStatus.COMPRESSED)
        assert state.status == DistillationStatus.COMPRESSED

        state.transition(DistillationStatus.VALIDATED)
        assert state.status == DistillationStatus.VALIDATED
        assert state.semantic_diff_result == "pass"
        assert state.brew_validation == "pending"
        assert state.last_distilled is not None

        state.transition(DistillationStatus.VERIFIED)
        assert state.status == DistillationStatus.VERIFIED
        assert state.brew_validation == "confirmed"

        state.transition(DistillationStatus.IDLE)
        assert state.status == DistillationStatus.IDLE
        assert state.retry_count == 0

    def test_failed_retry_flow(self):
        state = TopicDistillationState(topic="food")
        state.transition(DistillationStatus.CANDIDATE)
        state.transition(DistillationStatus.COMPRESSING)
        state.transition(DistillationStatus.COMPRESSED)

        # Fail
        state.transition(DistillationStatus.FAILED)
        assert state.status == DistillationStatus.FAILED
        assert state.semantic_diff_result == "fail"
        assert state.retry_count == 1

        # Retry: go back to CANDIDATE
        state.transition(DistillationStatus.CANDIDATE)
        assert state.status == DistillationStatus.CANDIDATE

        # Try again
        state.transition(DistillationStatus.COMPRESSING)
        assert state.status == DistillationStatus.COMPRESSING

    def test_should_retry_within_limit(self):
        state = TopicDistillationState(topic="food", max_retries=2)
        state.transition(DistillationStatus.CANDIDATE)
        state.transition(DistillationStatus.COMPRESSING)
        state.transition(DistillationStatus.COMPRESSED)
        state.transition(DistillationStatus.FAILED)
        assert state.retry_count == 1
        assert state.should_retry() is True

    def test_should_not_retry_at_limit(self):
        """retry_count == max_retries must return False (boundary case)."""
        state = TopicDistillationState(topic="food", max_retries=2)
        state.status = DistillationStatus.FAILED
        state.retry_count = 2
        assert state.should_retry() is False

    def test_should_not_retry_beyond_limit(self):
        state = TopicDistillationState(topic="food", max_retries=2)
        state.status = DistillationStatus.FAILED
        state.retry_count = 3
        assert state.should_retry() is False

    def test_needs_brew_validation(self):
        state = TopicDistillationState(topic="food")
        state.transition(DistillationStatus.CANDIDATE)
        state.transition(DistillationStatus.COMPRESSING)
        state.transition(DistillationStatus.COMPRESSED)
        state.transition(DistillationStatus.VALIDATED)

        assert state.needs_brew_validation() is True
        assert state.brew_validation == "pending"


class TestDistillationStateMachine:
    def test_get_candidates(self):
        sm = DistillationStateMachine()
        food = sm.get_or_create("food")
        food.transition(DistillationStatus.CANDIDATE)

        music = sm.get_or_create("music")
        # music stays IDLE

        candidates = sm.get_candidates()
        assert len(candidates) == 1
        assert candidates[0].topic == "food"

    def test_get_pending_validations(self):
        sm = DistillationStateMachine()
        state = sm.get_or_create("food")
        state.transition(DistillationStatus.CANDIDATE)
        state.transition(DistillationStatus.COMPRESSING)
        state.transition(DistillationStatus.COMPRESSED)
        state.transition(DistillationStatus.VALIDATED)

        pending = sm.get_pending_validations()
        assert len(pending) == 1
        assert pending[0].topic == "food"

    def test_save_and_load_roundtrip(self, tmp_path):
        sm = DistillationStateMachine()
        food = sm.get_or_create("food")
        food.transition(DistillationStatus.CANDIDATE)
        food.transition(DistillationStatus.COMPRESSING)
        food.transition(DistillationStatus.COMPRESSED)
        food.transition(DistillationStatus.VALIDATED)

        music = sm.get_or_create("music")
        music.transition(DistillationStatus.CANDIDATE)

        path = tmp_path / "distillation_state.yml"
        sm.save(path)

        loaded = DistillationStateMachine.load(path)
        assert loaded.topics["food"].status == DistillationStatus.VALIDATED
        assert loaded.topics["food"].semantic_diff_result == "pass"
        assert loaded.topics["food"].brew_validation == "pending"
        assert loaded.topics["food"].last_distilled is not None
        assert loaded.topics["music"].status == DistillationStatus.CANDIDATE

    def test_get_retryable(self):
        sm = DistillationStateMachine()
        state = sm.get_or_create("food")
        state.status = DistillationStatus.FAILED
        state.retry_count = 1
        state.max_retries = 2

        retryable = sm.get_retryable()
        assert len(retryable) == 1
        assert retryable[0].topic == "food"

    def test_load_nonexistent_file(self, tmp_path):
        path = tmp_path / "nonexistent.yml"
        sm = DistillationStateMachine.load(path)
        assert sm.topics == {}
