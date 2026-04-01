"""Tests for the response generator — LLM prompt composition and fallbacks."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from concierge.bridge.response import generate_response
from concierge.llm import LLMError
from concierge.models import (
    FeatureCandidate,
    FeatureType,
    MessageClass,
    MessageEnvelope,
)


def _make_envelope(text: str = "hello", cls: MessageClass | None = MessageClass.CONVERSE) -> MessageEnvelope:
    env = MessageEnvelope(
        text=text,
        has_attachment=False,
        timestamp=datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
    )
    env.classification = cls
    return env


class TestGenerateResponse:
    def test_success(self, tmp_path: Path) -> None:
        envelope = _make_envelope()

        with patch("concierge.bridge.response.call_agent", return_value="Sure, here's a plan."):
            result = asyncio.run(
                generate_response(envelope, None, tmp_path),
            )
        assert "plan" in result.lower()

    def test_llm_timeout_returns_fallback(self, tmp_path: Path) -> None:
        envelope = _make_envelope(cls=MessageClass.QUERY)

        with patch("concierge.bridge.response.call_agent", side_effect=LLMError("timeout")):
            result = asyncio.run(
                generate_response(envelope, None, tmp_path),
            )
        assert result == "I couldn't process that right now. Try again in a moment."

    def test_llm_error_returns_fallback(self, tmp_path: Path) -> None:
        envelope = _make_envelope(cls=MessageClass.COMMAND)

        with patch("concierge.bridge.response.call_agent", side_effect=RuntimeError("boom")):
            result = asyncio.run(
                generate_response(envelope, None, tmp_path),
            )
        assert result == "Command received, but I couldn't process it."

    def test_with_feature_includes_context(self, tmp_path: Path) -> None:
        envelope = _make_envelope()
        feature = FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="meals",
            score_inputs={"relevance": 0.8},
        )

        calls: list[str] = []

        def fake_call_agent(prompt: str, **kwargs: object) -> str:
            calls.append(prompt)
            return "Here's your meal plan."

        with patch("concierge.bridge.response.call_agent", side_effect=fake_call_agent):
            asyncio.run(
                generate_response(envelope, feature, tmp_path),
            )

        assert len(calls) == 1
        assert "meals" in calls[0]
        assert "dispatch" in calls[0]
