"""Tests for LLM client utility."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from concierge.llm import call_agent, LLMError, SUPPORTED_AGENTS


def _enable_claude():
    """Patch _get_enabled_agents to include 'claude' for tests that mock subprocess."""
    return patch("concierge.llm._get_enabled_agents", return_value=["claude"])


class TestCallAgent:
    def test_returns_stdout_on_success(self):
        with _enable_claude(), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="- Enjoys pasta\n- Runs daily\n"
            )
            result = call_agent("summarize this", agent="claude")
            assert result == "- Enjoys pasta\n- Runs daily"

    def test_raises_on_unsupported_agent(self):
        with pytest.raises(LLMError, match="not a supported"):
            call_agent("test", agent="unsupported-agent")

    def test_raises_on_timeout(self):
        with _enable_claude(), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("claude", 30)
            with pytest.raises(LLMError, match="timed out"):
                call_agent("test", agent="claude")

    def test_raises_on_cli_not_found(self):
        """FileNotFoundError (CLI not on PATH) is wrapped as LLMError."""
        with _enable_claude(), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("claude")
            with pytest.raises(LLMError, match="not found on PATH"):
                call_agent("test", agent="claude")

    def test_raises_on_nonzero_exit(self):
        with _enable_claude(), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error msg")
            with pytest.raises(LLMError, match="exit code 1"):
                call_agent("test", agent="claude")

    def test_raises_on_empty_output(self):
        with _enable_claude(), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="  \n  ")
            with pytest.raises(LLMError, match="empty"):
                call_agent("test", agent="claude")

    def test_validates_agent_is_enabled(self):
        """Agent must be in the resolved config's agents list."""
        with patch("concierge.llm._get_enabled_agents", return_value=["gemini"]):
            with pytest.raises(LLMError, match="not enabled"):
                call_agent("test", agent="claude")

    def test_falls_back_to_preferred_agent(self):
        """Uses preferred_agent from config when agent is None."""
        with patch("concierge.llm._get_preferred_agent", return_value="claude"), \
             patch("concierge.llm._get_enabled_agents", return_value=["claude"]), \
             patch("concierge.llm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")
            call_agent("test")
            # Verify claude CLI was called
            cmd = mock_run.call_args[0][0]
            assert "claude" in cmd


class TestSupportedAgents:
    def test_matches_cli_commands_keys(self):
        from concierge.llm import _CLI_COMMANDS
        assert SUPPORTED_AGENTS == set(_CLI_COMMANDS)
