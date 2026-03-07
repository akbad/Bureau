"""Pre-session hook -- injects memory, personality, and vocabulary into CLI sessions."""
from __future__ import annotations

from pathlib import Path

from concierge.memory.reader import read_core, read_personality, read_topic_distilled, list_topics
from concierge.vocabulary import VocabularyTracker


def build_context(
    data_dir: Path,
    context_budget: int = 4000,
) -> str:
    """Build the full context string to inject as system prompt prefix.

    Loads in priority order until *context_budget* (approximate word count)
    is reached:

    1. PERSONALITY.md (always loaded, ~100 words)
    2. core.md (always loaded, ~200 words)
    3. Vocabulary state (always loaded, ~50 words)
    4. Topic distilled sections (loaded until budget exhausted)

    Returns a single string ready to prepend to the system prompt.
    """
    parts: list[str] = []
    word_count = 0

    # 1. Personality (always)
    personality = read_personality(data_dir)
    if personality:
        parts.append(f"## Personality\n{personality}")
        word_count += len(personality.split())

    # 2. Core memory (always)
    core = read_core(data_dir)
    if core:
        parts.append(f"## Core Memory\n{core}")
        word_count += len(core.split())

    # 3. Vocabulary guidance
    vocab_path = data_dir / "state" / "vocabulary.yml"
    tracker = VocabularyTracker.load(vocab_path)
    vocab_guidance = _build_vocabulary_guidance(tracker)
    if vocab_guidance:
        parts.append(f"## Vocabulary\n{vocab_guidance}")
        word_count += len(vocab_guidance.split())

    # 4. Topic distilled sections (budget-constrained)
    topics_dir = data_dir / "topics"
    topics = list_topics(topics_dir)
    for topic in topics:
        if word_count >= context_budget:
            break
        topic_path = topics_dir / f"{topic}.md"
        distilled = read_topic_distilled(topic_path)
        if distilled:
            section = f"### {topic.title()}\n{distilled}"
            section_words = len(section.split())
            if word_count + section_words <= context_budget:
                parts.append(section)
                word_count += section_words

    return "\n\n".join(parts)


def _build_vocabulary_guidance(tracker: VocabularyTracker) -> str:
    """Generate vocabulary usage guidance for the system prompt."""
    lines: list[str] = []
    for term in tracker.terms:
        state = tracker.terms[term]
        if state.introduced and state.user_has_used:
            lines.append(f"- '{term}': user knows this term, use freely")
        elif state.introduced:
            lines.append(f"- '{term}': introduced but user hasn't used it yet, use sparingly")
        else:
            lines.append(f"- '{term}': NOT introduced, describe naturally without using the term name")
    return "\n".join(lines) if lines else ""
