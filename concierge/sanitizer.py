"""UX sanitizer — makes outgoing messages feel like they came from a friend, not software."""

# Design rationale:
# Strips machine artifacts (code blocks, tool prompts, thinking tags, terminal
# commands) from outgoing text so Telegram messages read as natural conversation.
# Processing is split into two phases: strip patterns (remove entirely) run
# first, then cleanup patterns (normalize whitespace) run second, so cleanup
# never accidentally collapses content that was about to be stripped.  All
# regexes are compiled at module level to avoid per-call compilation overhead
# since sanitize() is called on every outgoing message.

from __future__ import annotations

import re


# Patterns to strip entirely
_STRIP_PATTERNS: list[re.Pattern] = [
    re.compile(r"```[\s\S]*?```"),           # Code blocks
    re.compile(r"`[^`]+`"),                    # Inline code
    re.compile(r"Allow .+\? \[Y/n\]"),         # Tool approval prompts
    re.compile(r"<thinking>[\s\S]*?</thinking>"),  # Thinking tags
    re.compile(r"Searching\.\.\.|Reading file\.\.\.|Loading\.\.\.", re.IGNORECASE),  # Status indicators
    re.compile(r"\$ .+$", re.MULTILINE),       # Terminal commands
    re.compile(r"<[a-z][a-z0-9]*(?:\s[^>]*)?>[\s\S]*?</[a-z][a-z0-9]*>"),  # HTML tags
    re.compile(r"^\s*\|.*\|.*\|.*$", re.MULTILINE),  # Markdown tables
    re.compile(r"^\s*[-=]{3,}\s*$", re.MULTILINE),    # Horizontal rules / separators
]

# Patterns to clean up (replace, not remove)
_CLEANUP_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\n{3,}"), "\n\n"),           # Excessive newlines
    (re.compile(r"^\s+$", re.MULTILINE), ""),  # Whitespace-only lines
]


def sanitize(text: str) -> str:
    """Clean outgoing text for human consumption.

    Strips:
    - Code blocks, inline code
    - Tool approval prompts
    - Thinking/reasoning traces
    - Status indicators
    - Terminal commands
    - HTML tags
    - Markdown tables
    - Horizontal rules

    Preserves:
    - Natural language
    - Emoji
    - Bullet/numbered lists
    - Links (URLs)
    - Quick-reply option formatting (a/b/c)
    """
    result = text

    for pattern in _STRIP_PATTERNS:
        result = pattern.sub("", result)

    for pattern, replacement in _CLEANUP_PATTERNS:
        result = pattern.sub(replacement, result)

    return result.strip()
