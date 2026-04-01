import json
import sys
from importlib import util
from pathlib import Path

import pytest


module_path = Path(__file__).resolve().parents[1] / "configure-claude-output-style.py"
spec = util.spec_from_file_location("configure_claude_output_style", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def _run_main(args):
    argv = ["configure-claude-output-style.py", *args]
    original = sys.argv
    try:
        sys.argv = argv
        return module.main()
    finally:
        sys.argv = original


def test_installs_bureau_style_and_selects_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    source = tmp_path / "protocols" / "output-style.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Style\n\nKeep answers tight.\n", encoding="utf-8")

    assert _run_main(["--source", str(source)]) == 0

    installed = tmp_path / ".claude" / "output-styles" / "bureau.md"
    settings = tmp_path / ".claude" / "settings.json"

    assert installed.exists()
    text = installed.read_text(encoding="utf-8")
    assert "name: Bureau" in text
    assert "keep-coding-instructions: true" in text
    assert "Keep answers tight." in text

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["outputStyle"] == "Bureau"


def test_remove_clears_selected_bureau_style_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    output_styles = tmp_path / ".claude" / "output-styles"
    output_styles.mkdir(parents=True)
    (output_styles / "bureau.md").write_text("bureau", encoding="utf-8")
    (output_styles / "other.md").write_text("other", encoding="utf-8")
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir(exist_ok=True)
    (settings_dir / "settings.json").write_text(
        json.dumps({"outputStyle": "Bureau", "theme": "dark"}),
        encoding="utf-8",
    )

    assert _run_main(["--remove"]) == 0

    assert not (output_styles / "bureau.md").exists()
    assert (output_styles / "other.md").exists()
    data = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
    assert "outputStyle" not in data
    assert data["theme"] == "dark"


def test_remove_preserves_non_bureau_selected_style(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    output_styles = tmp_path / ".claude" / "output-styles"
    output_styles.mkdir(parents=True)
    (output_styles / "bureau.md").write_text("bureau", encoding="utf-8")
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir(exist_ok=True)
    (settings_dir / "settings.json").write_text(
        json.dumps({"outputStyle": "Other"}),
        encoding="utf-8",
    )

    assert _run_main(["--remove"]) == 0

    data = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
    assert data["outputStyle"] == "Other"
