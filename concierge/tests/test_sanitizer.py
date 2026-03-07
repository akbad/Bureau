"""Tests for the UX sanitizer."""

from concierge.sanitizer import sanitize


class TestStripPatterns:
    def test_strips_code_blocks(self):
        text = "Here is some info\n```python\nprint('hello')\n```\nEnd."
        result = sanitize(text)
        assert "```" not in result
        assert "print" not in result
        assert "Here is some info" in result
        assert "End." in result

    def test_strips_inline_code(self):
        text = "Run the `pip install` command to proceed."
        result = sanitize(text)
        assert "`" not in result
        assert "pip install" not in result
        assert "Run the" in result

    def test_strips_tool_approval_prompts(self):
        text = "Allow read_file? [Y/n]\nHere is your answer."
        result = sanitize(text)
        assert "[Y/n]" not in result
        assert "Here is your answer." in result

    def test_strips_thinking_tags(self):
        text = "Hello!<thinking>internal reasoning here</thinking> Goodbye!"
        result = sanitize(text)
        assert "<thinking>" not in result
        assert "internal reasoning" not in result
        assert "Hello!" in result
        assert "Goodbye!" in result

    def test_strips_status_indicators(self):
        text = "Searching...\nHere are the results."
        result = sanitize(text)
        assert "Searching..." not in result
        assert "Here are the results." in result

    def test_strips_terminal_commands(self):
        text = "I found the answer.\n$ grep -r 'foo' .\nIt was in file.py."
        result = sanitize(text)
        assert "$ grep" not in result
        assert "I found the answer." in result

    def test_strips_html_tags(self):
        text = "Check this <div class=\"info\">some content</div> out."
        result = sanitize(text)
        assert "<div" not in result
        assert "</div>" not in result
        assert "Check this" in result

    def test_strips_markdown_tables(self):
        text = "Summary:\n| Name | Value |\n| --- | --- |\n| foo | bar |\nDone."
        result = sanitize(text)
        assert "|" not in result
        assert "Done." in result


class TestPreservation:
    def test_preserves_natural_text(self):
        text = "Hey! I found a great Italian place near your office."
        assert sanitize(text) == text

    def test_preserves_emoji(self):
        text = "Sounds great! 🎉 Let's do it 👍"
        assert sanitize(text) == text

    def test_preserves_bullet_lists(self):
        text = "Options:\n- Pasta\n- Pizza\n- Salad"
        assert sanitize(text) == text

    def test_preserves_links(self):
        text = "Check out https://example.com/menu for the full menu."
        assert sanitize(text) == text

    def test_preserves_quick_reply_options(self):
        text = "What would you like?\na) Pasta tonight\nb) Something new\nc) Order in"
        assert sanitize(text) == text


class TestCleanup:
    def test_collapses_excessive_newlines(self):
        text = "First paragraph.\n\n\n\n\nSecond paragraph."
        result = sanitize(text)
        assert "\n\n\n" not in result
        assert "First paragraph.\n\nSecond paragraph." == result
