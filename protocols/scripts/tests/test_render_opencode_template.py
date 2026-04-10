import sys
from importlib import util
from pathlib import Path

import pytest

module_path = Path(__file__).resolve().parents[1] / "render-opencode-template.py"
spec = util.spec_from_file_location("render_opencode_template", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def _run_main(args):
    argv = ["render-opencode-template.py", *args]
    original = sys.argv
    try:
        sys.argv = argv
        return module.main()
    finally:
        sys.argv = original


def test_invalid_mcp_json_exits(tmp_path: Path) -> None:
    template = tmp_path / "template.json"
    mcp = tmp_path / "mcp.json"
    out = tmp_path / "out.json"
    template.write_text('{"mcp": {}, "path": "{{REPO_ROOT}}"}', encoding="utf-8")
    mcp.write_text("{not json", encoding="utf-8")

    with pytest.raises(SystemExit):
        _run_main(
            [
                "--template",
                str(template),
                "--output",
                str(out),
                "--repo-root",
                "/tmp/repo",
                "--mcp",
                str(mcp),
            ]
        )


def test_render_opencode_template(tmp_path: Path) -> None:
    template = tmp_path / "template.json"
    mcp = tmp_path / "mcp.json"
    out = tmp_path / "out.json"
    template.write_text('{"mcp": {}, "path": "{{REPO_ROOT}}"}', encoding="utf-8")
    mcp.write_text('{"mcp": {"x": 1}}', encoding="utf-8")

    assert (
        _run_main(
            [
                "--template",
                str(template),
                "--output",
                str(out),
                "--repo-root",
                "/tmp/repo",
                "--mcp",
                str(mcp),
            ]
        )
        == 0
    )
    assert out.exists()


def test_replaces_protocols_dir_placeholder(tmp_path: Path) -> None:
    template = tmp_path / "template.json"
    mcp = tmp_path / "mcp.json"
    out = tmp_path / "out.json"
    protocols_dir = tmp_path / "protocols"
    protocols_dir.mkdir()
    (protocols_dir / "output-style.md").write_text("style", encoding="utf-8")
    (protocols_dir / "ops-hub.md").write_text("hub", encoding="utf-8")
    template.write_text(
        '{"instructions": ["{{PROTOCOLS_DIR}}/output-style.md", "{{PROTOCOLS_DIR}}/ops-hub.md"], "mcp": {}}',
        encoding="utf-8",
    )
    mcp.write_text('{"mcp": {"x": 1}}', encoding="utf-8")

    assert (
        _run_main(
            [
                "--template",
                str(template),
                "--output",
                str(out),
                "--repo-root",
                "/tmp/repo",
                "--protocols-dir",
                str(protocols_dir),
                "--mcp",
                str(mcp),
            ]
        )
        == 0
    )

    rendered = out.read_text(encoding="utf-8")
    assert "{{PROTOCOLS_DIR}}" not in rendered
    assert str(protocols_dir / "output-style.md") in rendered
    assert str(protocols_dir / "ops-hub.md") in rendered


def test_skips_output_style_instruction_when_runtime_artifact_is_missing(tmp_path: Path) -> None:
    template = tmp_path / "template.json"
    mcp = tmp_path / "mcp.json"
    out = tmp_path / "out.json"
    protocols_dir = tmp_path / "protocols"
    protocols_dir.mkdir()
    (protocols_dir / "ops-hub.md").write_text("hub", encoding="utf-8")
    template.write_text(
        '{"instructions": ["{{PROTOCOLS_DIR}}/output-style.md", "{{PROTOCOLS_DIR}}/ops-hub.md"], "mcp": {}}',
        encoding="utf-8",
    )
    mcp.write_text('{"mcp": {"x": 1}}', encoding="utf-8")

    assert (
        _run_main(
            [
                "--template",
                str(template),
                "--output",
                str(out),
                "--repo-root",
                "/tmp/repo",
                "--protocols-dir",
                str(protocols_dir),
                "--mcp",
                str(mcp),
            ]
        )
        == 0
    )

    rendered = out.read_text(encoding="utf-8")
    assert str(protocols_dir / "ops-hub.md") in rendered
    assert str(protocols_dir / "output-style.md") not in rendered
