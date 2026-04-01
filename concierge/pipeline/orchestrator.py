"""Pipeline orchestrator — chains 6 stages into a single entry point.

Runs the concierge processing pipeline over an incoming message:
suite detection -> attache selection -> hard rules -> feature evaluation ->
scoring + queuing -> lottery selection.
"""

# Design rationale:
# Plain function composition instead of a state-machine library (Burr).
# The pipeline is a linear chain with no branching or retry needs.
# Each stage is wrapped in try/except so a single stage failure degrades
# gracefully (logs + returns None) rather than crashing the entire pipeline.
# Feature evaluators are called in a fixed order; each returns a list of
# FeatureCandidate that feed into scoring.  The queue persists across
# pipeline runs (caller owns it), enabling priority aging over time.

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from ..models import (
    FeatureCandidate,
    FeatureType,
    MessageEnvelope,
    SessionState,
    Suite,
)
from .attache_selector import select_attaches
from .hard_rules import evaluate_hard_rules
from .lottery import FeatureSelector
from .queue import PriorityQueue
from .scoring import score_candidates
from .suite_detector import detect_suite
from ..config.loader import get_priorities_config

logger = logging.getLogger(__name__)

# Feature evaluators — imported here to keep the evaluate_all_features
# function self-contained.  Each returns list[FeatureCandidate].
from ..features.brews import evaluate_brew_candidates
from ..features.dispatches import evaluate_dispatch_candidates
from ..features.huddles import evaluate_huddle_candidates
from ..features.probes import evaluate_probe_candidates
from ..features.valets import evaluate_valet_candidates

# Default data directory for feature evaluators
_DEFAULT_DATA_DIR = Path("~/.config/bureau/concierge").expanduser()


def evaluate_all_features(
    session: SessionState,
    blocked: set[FeatureType],
    data_dir: Path | None = None,
    envelope: MessageEnvelope | None = None,
) -> list[FeatureCandidate]:
    """Run all feature evaluators and return combined candidates.

    Skips evaluators whose feature type is in *blocked*.
    """
    ddir = data_dir or _DEFAULT_DATA_DIR

    evaluators: list[tuple[FeatureType, Callable[[], list[FeatureCandidate]]]] = [
        (FeatureType.DISPATCH, lambda: evaluate_dispatch_candidates(session, ddir)),
        (FeatureType.BREW, lambda: evaluate_brew_candidates(session, ddir)),
        (FeatureType.PROBE, lambda: evaluate_probe_candidates(session, ddir)),
        (FeatureType.VALET, lambda: evaluate_valet_candidates(session, ddir)),
        (FeatureType.HUDDLE, lambda: evaluate_huddle_candidates(session, ddir, envelope=envelope)),
    ]

    candidates: list[FeatureCandidate] = []
    for ftype, evaluator in evaluators:
        if ftype in blocked:
            logger.debug("Skipping %s (blocked by hard rules)", ftype.value)
            continue
        try:
            candidates.extend(evaluator())
        except Exception:
            logger.warning("Feature evaluator %s failed", ftype.value, exc_info=True)

    return candidates


def run_pipeline(
    envelope: MessageEnvelope,
    session: SessionState,
    queue: PriorityQueue,
    *,
    data_dir: Path | None = None,
    selector: FeatureSelector | None = None,
) -> FeatureCandidate | None:
    """Run the 6-stage concierge pipeline over *envelope*.

    Parameters
    ----------
    envelope:
        The classified message to process.
    session:
        Current session state (suite history, active feature, etc.).
    queue:
        Persistent priority queue (owned by caller, survives across runs).
    data_dir:
        Override for feature data directory (default ~/.config/bureau/concierge).
    selector:
        Override for lottery selector (default creates a new FeatureSelector).

    Returns
    -------
    FeatureCandidate | None
        The selected feature, or None if no feature was selected.
    """
    try:
        # --- Stage 1: Suite detection ----------------------------------------
        suite = detect_suite(envelope, session)
        session.record_suite(suite)
        logger.debug("Detected suite: %s", suite.value)

        # --- Stage 2: Attache selection --------------------------------------
        # NOTE: Attaches are selected here for future use by per-suite agent
        # routing (e.g. filtering feature evaluators or adjusting scoring by
        # attache capabilities).  Currently unused downstream — the result is
        # logged but not passed to later stages.
        attaches = select_attaches(suite)
        logger.debug("Selected attaches: %s", attaches)

        # --- Stage 3: Hard rules ---------------------------------------------
        blocked = evaluate_hard_rules(suite, session)
        # Short-circuit if hard rules block all feature types
        # (defensive; no current rule does this)
        if blocked == set(FeatureType):
            logger.debug("All feature types blocked by hard rules")
            return None

        # --- Stage 4: Feature evaluation + scoring ---------------------------
        candidates = evaluate_all_features(
            session, blocked, data_dir=data_dir, envelope=envelope,
        )
        if not candidates:
            logger.debug("No feature candidates generated")
            return None

        weights = get_priorities_config().get("scoring_weights", {})
        scored = score_candidates(candidates, weights)

        # --- Stage 5: Queue -------------------------------------------------
        snapshot = {
            "suite": session.current_suite.value if session.current_suite else None,
            "suite_since": session.suite_since.isoformat() if session.suite_since else None,
            "active_feature": session.active_feature.value if session.active_feature else None,
        }
        for candidate, priority in scored:
            queue.add(candidate, priority, context_snapshot=snapshot)

        # --- Stage 6: Lottery selection --------------------------------------
        sel = selector or FeatureSelector()
        priority_map = {item.candidate: item.priority for item in queue}
        result = sel.select(list(priority_map.keys()), priority_map)

        if result is not None:
            logger.debug(
                "Selected feature: %s/%s", result.feature_type.value, result.domain,
            )
            sel.decay_epsilon()
        return result

    except Exception:
        logger.warning("Pipeline failed — returning None", exc_info=True)
        return None
