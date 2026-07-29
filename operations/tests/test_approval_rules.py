from operations.approval_rules import (
    normalize_prefixes,
    build_claude_bash_rules,
    build_claude_read_rules,
    build_gemini_bash_rules,
    build_opencode_bash_rules,
    build_codex_rule_lines,
)


def test_normalize_prefixes_strips_and_drops_blanks():
    assert normalize_prefixes(["  git ", " ", "", "\t", "uv run"]) == ["git", "uv run"]


def test_build_claude_bash_rules():
    assert build_claude_bash_rules(["git", "uv run"]) == [
        "Bash(git:*)",
        "Bash(uv run:*)",
    ]


def test_build_claude_read_rules_appends_glob_to_bare_path():
    assert build_claude_read_rules(["~/.config/bureau/protocols"]) == [
        "Read(~/.config/bureau/protocols/**)",
    ]


def test_build_claude_read_rules_preserves_existing_glob():
    assert build_claude_read_rules(["~/docs/*", "/tmp/data/**"]) == [
        "Read(~/docs/*)",
        "Read(/tmp/data/**)",
    ]


def test_build_claude_read_rules_handles_multiple_paths():
    result = build_claude_read_rules(["~/.config/bureau/protocols", "/opt/conf"])
    assert result == [
        "Read(~/.config/bureau/protocols/**)",
        "Read(/opt/conf/**)",
    ]


def test_build_gemini_bash_rules():
    assert build_gemini_bash_rules(["git"]) == ["run_shell_command(git)"]


def test_build_opencode_bash_rules():
    rules = build_opencode_bash_rules(["git"], ["rm "])
    assert rules["*"] == "ask"
    assert rules["git*"] == "allow"
    assert rules["rm*"] == "deny"


def test_build_codex_rule_lines():
    lines = build_codex_rule_lines(["git status"], ["rm -rf /"])
    assert lines[0].startswith("prefix_rule(pattern=[")
    assert "decision=\"allow\"" in lines[0]
    assert "decision=\"forbidden\"" in lines[1]


def test_build_grok_bash_rules():
    from operations.approval_rules import build_grok_bash_rules

    assert build_grok_bash_rules(["git status", "rg"]) == [
        "Bash(git status *)",
        "Bash(rg *)",
    ]


def test_build_grok_mcp_rules():
    from operations.approval_rules import build_grok_mcp_rules

    assert build_grok_mcp_rules(["qdrant", "serena"]) == [
        "MCPTool(qdrant__*)",
        "MCPTool(serena__*)",
    ]


def test_build_grok_path_rules():
    from operations.approval_rules import build_grok_path_rules

    assert build_grok_path_rules(["~/.config/bureau", "/tmp/x/**"]) == [
        "Read(~/.config/bureau/**)",
        "Edit(~/.config/bureau/**)",
        "Read(/tmp/x/**)",
        "Edit(/tmp/x/**)",
    ]
