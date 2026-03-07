"""Tests for the hard rules evaluator."""

from concierge.models import FeatureType, SessionState, Suite
from concierge.pipeline.hard_rules import evaluate_hard_rules


class TestHardRules:
    def test_processing_suite_blocks_brews_and_dispatches(self):
        blocked = evaluate_hard_rules(suite=Suite.PROCESSING, session=SessionState())
        assert FeatureType.BREW in blocked
        assert FeatureType.DISPATCH in blocked
        assert FeatureType.PROBE not in blocked

    def test_active_huddle_blocks_most_features(self):
        session = SessionState(active_feature=FeatureType.HUDDLE)
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=session)
        assert FeatureType.DISPATCH in blocked
        assert FeatureType.BREW in blocked
        assert FeatureType.PROBE in blocked

    def test_active_valet_blocks_brews_probes(self):
        session = SessionState(active_feature=FeatureType.VALET)
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=session)
        assert FeatureType.BREW in blocked
        assert FeatureType.PROBE in blocked
        assert FeatureType.DISPATCH not in blocked

    def test_no_blocks_in_normal_state(self):
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=SessionState())
        assert blocked == set()

    def test_processing_cooldown_blocks_brews(self):
        session = SessionState(processing_cooldown_remaining=2)
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=session)
        assert FeatureType.BREW in blocked
