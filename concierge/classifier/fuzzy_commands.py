"""Fuzzy command-verb matcher for the concierge classifier.

Uses rapidfuzz to match the beginning of user text against known
command verbs from the classifier config.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from concierge.config.loader import get_classifier_config


def match_command_verb(text: str) -> str | None:
    """Return the best-matching command verb from config, or *None*.

    Logic:
    1. Load verbs from ``get_classifier_config()["fuzzy_commands"]["verbs"]``.
    2. If fuzzy matching is disabled in config, return *None* immediately.
    3. For each verb, compare against a prefix of *text* whose length is
       ``len(verb) + 2`` (tolerance for typos / whitespace).
    4. Return the verb whose score >= *min_score* (default 80) and is the
       highest among all candidates.  If no verb qualifies, return *None*.
    """
    cfg = get_classifier_config()["fuzzy_commands"]

    if not cfg.get("enabled", True):
        return None

    min_score: int = cfg.get("min_score", 80)
    verbs: list[str] = cfg["verbs"]

    best_verb: str | None = None
    best_score: float = 0.0

    text_lower = text.lower()

    for verb in verbs:
        verb_lower = verb.lower()
        max_prefix = len(verb) + 2
        # Try prefix lengths from len(verb) up to len(verb)+2 to tolerate
        # typos that shorten or lengthen the typed verb.
        score = max(
            fuzz.ratio(verb_lower, text_lower[:pl])
            for pl in range(len(verb), max_prefix + 1)
        )
        if score >= min_score and score > best_score:
            best_score = score
            best_verb = verb

    return best_verb
