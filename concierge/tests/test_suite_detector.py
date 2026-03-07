"""Tests for the suite detector pipeline stage."""

from datetime import time

from concierge.models import MessageEnvelope, SessionState, Suite
from concierge.pipeline.suite_detector import detect_suite


class TestSuiteDetection:
    def test_processing_keywords(self):
        env = MessageEnvelope(
            text="I've been really stressed and overwhelmed", has_attachment=False
        )
        assert (
            detect_suite(env, SessionState(), current_time=time(14, 0))
            == Suite.PROCESSING
        )

    def test_work_keywords(self):
        env = MessageEnvelope(
            text="I need to finish my report by Friday", has_attachment=False
        )
        assert (
            detect_suite(env, SessionState(), current_time=time(10, 0)) == Suite.WORK
        )

    def test_evening_defaults_to_rest(self):
        env = MessageEnvelope(text="hey", has_attachment=False)
        assert (
            detect_suite(env, SessionState(), current_time=time(21, 0)) == Suite.REST
        )

    def test_manual_override_persists(self):
        state = SessionState(current_suite=Suite.CREATIVE)
        env = MessageEnvelope(text="just checking in", has_attachment=False)
        assert (
            detect_suite(env, state, current_time=time(14, 0)) == Suite.CREATIVE
        )

    def test_processing_has_highest_precedence(self):
        env = MessageEnvelope(
            text="I'm stressed about my work deadline", has_attachment=False
        )
        assert (
            detect_suite(env, SessionState(), current_time=time(10, 0))
            == Suite.PROCESSING
        )
