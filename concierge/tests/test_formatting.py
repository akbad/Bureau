"""Tests for the quick-reply formatter."""

from concierge.formatting import format_options, parse_quick_reply, build_keyboard_data, QuickReply


class TestFormatOptions:
    def test_format_options_basic(self):
        result = format_options(["Pasta tonight", "Something new", "Order in"])
        assert result == "a) Pasta tonight\nb) Something new\nc) Order in"

    def test_format_options_custom_start(self):
        result = format_options(["Yes", "No"], start_letter="d")
        assert result == "d) Yes\ne) No"


class TestParseQuickReply:
    def test_parse_single_letter(self):
        options = ["Pasta", "Pizza", "Salad"]
        assert parse_quick_reply("a", options) == 0
        assert parse_quick_reply("b", options) == 1
        assert parse_quick_reply("c", options) == 2

    def test_parse_letter_with_paren(self):
        options = ["Pasta", "Pizza", "Salad"]
        assert parse_quick_reply("a)", options) == 0
        assert parse_quick_reply("b)", options) == 1

    def test_parse_number(self):
        options = ["Pasta", "Pizza", "Salad"]
        assert parse_quick_reply("1", options) == 0
        assert parse_quick_reply("2", options) == 1
        assert parse_quick_reply("3", options) == 2

    def test_parse_full_text_match(self):
        options = ["Pasta tonight", "Something new"]
        assert parse_quick_reply("Pasta tonight", options) == 0
        assert parse_quick_reply("SOMETHING NEW", options) == 1

    def test_parse_invalid_returns_none(self):
        options = ["Pasta", "Pizza"]
        assert parse_quick_reply("hello world", options) is None
        assert parse_quick_reply("z", options) is None
        assert parse_quick_reply("", options) is None

    def test_parse_out_of_range_returns_none(self):
        options = ["Pasta", "Pizza"]
        assert parse_quick_reply("c", options) is None
        assert parse_quick_reply("5", options) is None
        assert parse_quick_reply("0", options) is None

    def test_build_keyboard_data(self):
        options = ["Yes", "No", "Maybe"]
        replies = build_keyboard_data(options)
        assert len(replies) == 3
        assert all(isinstance(r, QuickReply) for r in replies)
        assert replies[0].label == "a"
        assert replies[0].text == "Yes"
        assert replies[0].value == "a"
        assert replies[1].label == "b"
        assert replies[2].label == "c"
        assert replies[2].text == "Maybe"
