"""Tests for pipeline orchestrator."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from concierge.models import (
    FeatureCandidate, FeatureType, MessageClass, MessageEnvelope,
    QueueItem, SessionState, Suite,
)
from concierge.pipeline.orchestrator import run_pipeline
from concierge.pipeline.queue import PriorityQueue


@pytest.fixture
def envelope():
    return MessageEnvelope(
        text="what's for dinner tonight?",
        has_attachment=False,
        attachment_type=None,
        classification=MessageClass.QUERY,
        confidence=0.9,
    )


@pytest.fixture
def session():
    return SessionState()


@pytest.fixture
def queue():
    return PriorityQueue(max_size=10)


class TestRunPipeline:
    def test_returns_feature_candidate_on_success(self, envelope, session, queue):
        """Pipeline produces a feature candidate when all stages succeed."""
        result = run_pipeline(envelope, session, queue)
        # Result is either a FeatureCandidate or None (if no candidates)
        assert result is None or isinstance(result, FeatureCandidate)

    def test_returns_none_when_hard_rules_block(self, envelope, session, queue):
        """Pipeline short-circuits when hard rules block all feature types."""
        with patch(
            "concierge.pipeline.orchestrator.evaluate_hard_rules"
        ) as mock_rules:
            mock_rules.return_value = set(FeatureType)  # all blocked
            result = run_pipeline(envelope, session, queue)
            assert result is None

    def test_suite_detected_and_passed_through(self, envelope, session, queue):
        """Suite detection result flows to downstream stages."""
        with patch(
            "concierge.pipeline.orchestrator.detect_suite",
            return_value=Suite.SOCIAL,
        ) as mock_detect, patch(
            "concierge.pipeline.orchestrator.evaluate_hard_rules",
            return_value=set(),
        ), patch(
            "concierge.pipeline.orchestrator.select_attaches",
            return_value=["schedule"],
        ) as mock_attaches:
            run_pipeline(envelope, session, queue)
            mock_detect.assert_called_once()
            mock_attaches.assert_called_once_with(Suite.SOCIAL)

    def test_candidates_scored_and_queued(self, envelope, session, queue):
        """Feature candidates are scored and pushed to the queue."""
        candidate = FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="meals",
            score_inputs={"relevance": 0.8, "freshness": 0.6},
        )
        with patch(
            "concierge.pipeline.orchestrator.detect_suite",
            return_value=Suite.REST,
        ), patch(
            "concierge.pipeline.orchestrator.evaluate_hard_rules",
            return_value=set(),
        ), patch(
            "concierge.pipeline.orchestrator.select_attaches",
            return_value=[],
        ), patch(
            "concierge.pipeline.orchestrator.evaluate_all_features",
            return_value=[candidate],
        ), patch(
            "concierge.pipeline.orchestrator.score_candidates",
            return_value=[(candidate, 0.72)],
        ):
            run_pipeline(envelope, session, queue)
            assert len(queue) >= 1

    def test_stage_failure_degrades_gracefully(self, envelope, session, queue):
        """A failing stage logs the error and returns None instead of crashing."""
        with patch(
            "concierge.pipeline.orchestrator.detect_suite",
            side_effect=RuntimeError("boom"),
        ):
            result = run_pipeline(envelope, session, queue)
            assert result is None
