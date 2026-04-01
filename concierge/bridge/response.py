"""Response generator — composes LLM prompts and produces sanitized replies.

Assembles a system prompt from the Concierge template + memory context,
optionally augments it with a selected feature, calls the LLM, and sanitizes
the output for Telegram delivery.
"""

# Design rationale:
# Wraps call_agent in asyncio.to_thread so the blocking subprocess call
# doesn't stall the PTB event loop.  Fallback responses are keyed by
# MessageClass so the user always gets a contextually appropriate reply
# even when the LLM is unreachable.  The system prompt is assembled from
# the same template used in pre_session hooks, keeping prompt logic DRY.

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from concierge.bridge.adapter import feature_to_prompt_context, truncate_response
from concierge.hooks.pre_session import build_context
from concierge.llm import LLMError, call_agent
from concierge.models import FeatureCandidate, MessageClass, MessageEnvelope
from concierge.sanitizer import sanitize

logger = logging.getLogger(__name__)

# Path to the system prompt template, relative to package root
_PROMPT_TEMPLATE = Path(__file__).resolve().parent.parent / "prompts" / "system.md"

_FALLBACK_RESPONSES: dict[MessageClass, str] = {
    MessageClass.REPLY: "Got it.",
    MessageClass.QUERY: "I couldn't process that right now. Try again in a moment.",
    MessageClass.CONVERSE: "I'm having trouble responding right now.",
    MessageClass.COMMAND: "Command received, but I couldn't process it.",
    MessageClass.MEDIA: "Thanks for sharing that.",
}

# default when classification is unknown
_DEFAULT_FALLBACK = "I'm having trouble responding right now."


def _build_system_prompt(
    data_dir: Path,
    assistant_name: str,
    feature: FeatureCandidate | None,
) -> str:
    """Assemble the full system prompt from template + context + feature."""
    template = _PROMPT_TEMPLATE.read_text() if _PROMPT_TEMPLATE.exists() else ""

    context = build_context(data_dir)
    prompt = template.replace("{{assistant_name}}", assistant_name)
    prompt = prompt.replace("{{context}}", context)

    feature_context = feature_to_prompt_context(feature)
    if feature_context:
        prompt += f"\n\n## Active Feature\n{feature_context}"

    return prompt


async def generate_response(
    envelope: MessageEnvelope,
    feature: FeatureCandidate | None,
    data_dir: Path,
    assistant_name: str = "Concierge",
    backend: str = "claude",
    timeout: int = 60,
) -> str:
    """Generate a response for the given message envelope.

    Builds a system prompt, calls the LLM in a thread, sanitizes the
    output, and truncates it for Telegram.  Returns a fallback string
    on any LLM failure.
    """
    system_prompt = _build_system_prompt(data_dir, assistant_name, feature)
    full_prompt = f"{system_prompt}\n\nUser: {envelope.text}"

    try:
        raw = await asyncio.to_thread(
            call_agent, full_prompt, agent=backend, timeout=timeout,
        )
        sanitized = sanitize(raw)
        return truncate_response(sanitized)
    except (LLMError, Exception) as exc:
        logger.warning("LLM call failed: %s", exc)
        cls = envelope.classification
        return _FALLBACK_RESPONSES.get(cls, _DEFAULT_FALLBACK) if cls else _DEFAULT_FALLBACK
