"""Quick-reply formatter for Telegram inline keyboards."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuickReply:
    """A single quick-reply option."""
    label: str      # "a", "b", "c"
    text: str       # The option text
    value: str      # What gets sent when selected


def format_options(options: list[str], start_letter: str = "a") -> str:
    """Format a list of options as labeled choices.

    Example:
        format_options(["Pasta tonight", "Something new", "Order in"])
        # Returns:
        # a) Pasta tonight
        # b) Something new
        # c) Order in
    """
    lines = []
    for i, option in enumerate(options):
        letter = chr(ord(start_letter) + i)
        lines.append(f"{letter}) {option}")
    return "\n".join(lines)


def parse_quick_reply(text: str, options: list[str]) -> int | None:
    """Parse a user reply that might be a quick-reply selection.

    Accepts:
    - Single letter: "a", "b", "c"
    - Letter with paren: "a)", "b)"
    - Number: "1", "2", "3"
    - Full option text (exact match, case-insensitive)

    Returns the 0-based index, or None if not a quick reply.
    """
    text = text.strip().lower()

    # Single letter
    if len(text) == 1 and text.isalpha():
        idx = ord(text) - ord("a")
        if 0 <= idx < len(options):
            return idx

    # Letter with paren
    if len(text) == 2 and text[1] == ")" and text[0].isalpha():
        idx = ord(text[0]) - ord("a")
        if 0 <= idx < len(options):
            return idx

    # Number
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return idx

    # Exact text match
    for i, opt in enumerate(options):
        if text == opt.lower():
            return i

    return None


def build_keyboard_data(options: list[str]) -> list[QuickReply]:
    """Build QuickReply objects for Telegram inline keyboard generation.

    Returns a list of QuickReply objects that can later be used
    to construct Telegram InlineKeyboardButtons.
    """
    replies = []
    for i, option in enumerate(options):
        letter = chr(ord("a") + i)
        replies.append(QuickReply(
            label=letter,
            text=option,
            value=letter,
        ))
    return replies
