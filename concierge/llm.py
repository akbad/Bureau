"""Thin LLM client — calls Bureau-configured agent CLI with a prompt.

Provides a single ``call_agent(prompt, agent)`` function that shells out
to a coding agent CLI in non-interactive mode and returns stdout.
"""

# Design rationale:
# Agent-agnostic by design: the caller specifies which agent (or it reads
# preferred_agent from config).  Each supported agent has a CLI invocation
# pattern that accepts a prompt on stdin and returns the response on stdout.
# Validation ensures the requested agent is both supported and enabled in
# the Bureau config.  All failures raise LLMError so callers can catch and
# fall back to deterministic logic.

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_AGENTS: set[str] = {"claude", "gemini", "codex", "opencode"}

# CLI invocation patterns per agent.
# Each pattern is a list of args; the prompt is piped via stdin.
_CLI_COMMANDS: dict[str, list[str]] = {
    "claude": ["claude", "--print"],
    "gemini": ["gemini"],
    "codex": ["codex", "--quiet"],
    "opencode": ["opencode", "--pipe"],
}

_DEFAULT_TIMEOUT = 60  # seconds


class LLMError(Exception):
    """Raised when an LLM call fails."""


def _get_preferred_agent() -> str:
    """Read preferred_agent from Bureau config."""
    try:
        from operations.config_loader import get_conversations_config
        config = get_conversations_config()
        concierge = config.get("concierge", {})
        return concierge.get("preferred_agent", "claude")
    except Exception:
        return "claude"


def _get_enabled_agents() -> list[str]:
    """Read enabled agents from Bureau config."""
    try:
        from operations.config_loader import get_enabled_agents
        return get_enabled_agents()
    except Exception:
        return ["claude"]


def call_agent(
    prompt: str,
    *,
    agent: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """Call a Bureau-configured agent CLI with *prompt* and return the response.

    Parameters
    ----------
    prompt:
        The full prompt text to send to the agent.
    agent:
        Agent CLI to use. If None, reads ``preferred_agent`` from config.
    timeout:
        Maximum seconds to wait for response.

    Returns
    -------
    str
        The agent's response (stdout, stripped).

    Raises
    ------
    LLMError
        If the agent is unsupported, not enabled, times out, returns
        non-zero, or produces empty output.
    """
    if agent is None:
        agent = _get_preferred_agent()

    if agent not in SUPPORTED_AGENTS:
        raise LLMError(f"{agent!r} is not a supported agent ({SUPPORTED_AGENTS})")

    enabled = _get_enabled_agents()
    if agent not in enabled:
        raise LLMError(
            f"{agent!r} is not enabled in Bureau config (enabled: {enabled})"
        )

    cmd = _CLI_COMMANDS[agent]
    logger.debug("Calling agent %s with %d-char prompt", agent, len(prompt))

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"{agent} timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise LLMError(f"{agent} CLI not found on PATH") from exc

    if result.returncode != 0:
        raise LLMError(
            f"{agent} exited with exit code {result.returncode}: "
            f"{result.stderr[:200] if result.stderr else '(no stderr)'}"
        )

    output = result.stdout.strip()
    if not output:
        raise LLMError(f"{agent} returned empty output")

    return output
