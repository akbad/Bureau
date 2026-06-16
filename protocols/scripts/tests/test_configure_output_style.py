import json
from importlib import util
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "configure-output-style.py"
spec = util.spec_from_file_location("configure_output_style", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

compile_output_style = module.compile_output_style
install_claude_output_style = module.install_claude_output_style
remove_claude_output_style = module.remove_claude_output_style


def test_compile_output_style_preserves_single_source_body(tmp_path: Path) -> None:
    source = tmp_path / "style.md"
    destination = tmp_path / "output-style.md"
    body = "# Output style\n\n- keep this formatting exactly\n"
    source.write_text(body, encoding="utf-8")

    compile_output_style([source], destination)

    compiled = destination.read_text(encoding="utf-8")
    assert compiled.startswith("<!-- Bureau protocols -->\n\n")
    assert "Source files:" not in compiled
    assert "Do not edit this runtime artifact directly." not in compiled
    assert compiled.endswith(body)


def test_compile_output_style_concatenates_multiple_sources_in_order(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    destination = tmp_path / "output-style.md"
    first.write_text("# First\n\n- alpha\n", encoding="utf-8")
    second.write_text("# Second\n\n- beta\n", encoding="utf-8")

    compile_output_style([first, second], destination)

    compiled = destination.read_text(encoding="utf-8")
    assert compiled.index("# First") < compiled.index("# Second")
    assert compiled.startswith("<!-- Bureau protocols -->\n\n")
    assert "Source files:" not in compiled
    assert "<!-- Bureau source boundary -->" not in compiled


def test_install_claude_output_style_writes_wrapper_and_selects_style(tmp_path: Path) -> None:
    runtime = tmp_path / "output-style.md"
    styles_dir = tmp_path / ".claude" / "output-styles"
    settings_path = tmp_path / ".claude" / "settings.json"
    runtime.write_text("# Style\n\n- be consistent\n", encoding="utf-8")
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"hooks": {"UserPromptSubmit": []}}), encoding="utf-8")

    install_claude_output_style(runtime, styles_dir, settings_path)

    wrapper = styles_dir / "bureau.md"
    assert wrapper.exists()
    content = wrapper.read_text(encoding="utf-8")
    assert "name: Bureau" in content
    assert "keep-coding-instructions: true" in content
    assert content.endswith(runtime.read_text(encoding="utf-8"))

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["outputStyle"] == "Bureau"
    assert settings["hooks"] == {"UserPromptSubmit": []}


def test_remove_claude_output_style_only_clears_bureau_selection(tmp_path: Path) -> None:
    styles_dir = tmp_path / ".claude" / "output-styles"
    settings_path = tmp_path / ".claude" / "settings.json"
    styles_dir.mkdir(parents=True, exist_ok=True)
    (styles_dir / "bureau.md").write_text("placeholder", encoding="utf-8")
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"outputStyle": "Other", "theme": "dark"}), encoding="utf-8")

    remove_claude_output_style(styles_dir, settings_path)

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert not (styles_dir / "bureau.md").exists()
    assert settings["outputStyle"] == "Other"
    assert settings["theme"] == "dark"


def test_remove_claude_output_style_clears_bureau_selection_when_active(tmp_path: Path) -> None:
    styles_dir = tmp_path / ".claude" / "output-styles"
    settings_path = tmp_path / ".claude" / "settings.json"
    styles_dir.mkdir(parents=True, exist_ok=True)
    (styles_dir / "bureau.md").write_text("placeholder", encoding="utf-8")
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"outputStyle": "Bureau", "theme": "dark"}), encoding="utf-8")

    remove_claude_output_style(styles_dir, settings_path)

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "outputStyle" not in settings
    assert settings["theme"] == "dark"
