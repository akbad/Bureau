"""Distillation package — summarization lifecycle for topic memory."""

# Shared stop-word set used by detection, compression, and validation modules.
# Centralised here to avoid drift between modules.
STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "i", "my", "was", "is", "it", "to", "and", "of",
    "in", "for", "that", "with", "on", "at", "by", "from", "she", "he",
    "her", "his", "been",
})
