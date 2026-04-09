from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPS_HUB = REPO_ROOT / "protocols" / "context" / "static" / "ops-hub.md"


def test_ops_hub_contains_output_style_session_reminder() -> None:
    content = OPS_HUB.read_text(encoding="utf-8")

    assert "output style loaded at session start" in content
    assert "{{PROTOCOLS_DIR}}/output-style.md" in content
    assert "Activate the `code-standards` skill" in content
