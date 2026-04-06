from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPS_HUB = REPO_ROOT / "protocols" / "context" / "static" / "ops-hub.md"
AGENTS_TEMPLATE = REPO_ROOT / "protocols" / "context" / "templates" / "AGENTS.template.md"
CLAUDE_TEMPLATE = REPO_ROOT / "protocols" / "context" / "templates" / "CLAUDE.template.md"


def test_ops_hub_contains_output_style_session_reminder() -> None:
    content = OPS_HUB.read_text(encoding="utf-8")

    assert "output style loaded at session start" in content
    assert "{{PROTOCOLS_DIR}}/output-style.md" in content
    assert "{{PROTOCOLS_DIR}}/code-standards.md" in content


def test_agents_template_exists_and_references_runtime_protocol_files() -> None:
    content = AGENTS_TEMPLATE.read_text(encoding="utf-8")

    assert "{{PROTOCOLS_DIR}}/output-style.md" in content
    assert "{{PROTOCOLS_DIR}}/ops-hub.md" in content
    assert "Global context for Gemini CLI & Codex" in content


def test_claude_template_exists_and_references_ops_hub() -> None:
    content = CLAUDE_TEMPLATE.read_text(encoding="utf-8")

    assert "{{PROTOCOLS_DIR}}/ops-hub.md" in content
    assert "Global context (always read first)" in content
