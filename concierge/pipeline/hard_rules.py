"""Hard rules evaluator for the concierge pipeline.

Determines which feature types are blocked based on the current suite
and session state. These are non-negotiable constraints that take
precedence over scoring and soft heuristics.
"""

# Design rationale:
# Hard rules are non-negotiable gates that block feature types before scoring
# ever runs, preventing the lottery from surfacing content at inappropriate
# times (e.g., a brew during an emotional processing episode).  Rules are
# checked in a fixed, numbered order (suite -> active huddle -> active valet
# -> cooldown) so that reasoning about cumulative blocking is straightforward
# and new rules can be appended without reordering concerns.  The function
# returns a set of blocked types rather than a pass/fail bool so callers can
# filter any candidate list in one step.

from __future__ import annotations

from concierge.models import FeatureType, SessionState, Suite


def evaluate_hard_rules(suite: Suite, session: SessionState) -> set[FeatureType]:
    """Return the set of feature types blocked by hard rules.

    Rules (applied cumulatively):
    1. Processing suite -> blocks BREW and DISPATCH.
    2. Active Huddle   -> blocks DISPATCH, BREW, and PROBE.
    3. Active Valet    -> blocks BREW and PROBE.
    4. Processing cooldown active -> blocks BREW.
    """
    blocked: set[FeatureType] = set()

    # Rule 1 — Processing suite
    if suite is Suite.PROCESSING:
        blocked.update({FeatureType.BREW, FeatureType.DISPATCH})

    # Rule 2 — Active Huddle
    if session.active_feature is FeatureType.HUDDLE:
        blocked.update({FeatureType.DISPATCH, FeatureType.BREW, FeatureType.PROBE})

    # Rule 3 — Active Valet
    if session.active_feature is FeatureType.VALET:
        blocked.update({FeatureType.BREW, FeatureType.PROBE})

    # Rule 4 — Processing cooldown
    if session.is_in_processing_cooldown:
        blocked.add(FeatureType.BREW)

    return blocked
