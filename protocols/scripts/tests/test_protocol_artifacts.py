from pathlib import Path

from operations.protocol_artifacts import (
    compile_code_standards_skill,
    compile_runtime_artifact,
    get_code_standards_mindset_source,
    get_default_protocol_sources,
)


def test_compile_runtime_artifact_uses_minimal_bureau_marker(tmp_path: Path) -> None:
    source = tmp_path / "artifact.md"
    destination = tmp_path / "runtime.md"
    body = "# Runtime artifact\n\nbody\n"
    source.write_text(body, encoding="utf-8")

    compile_runtime_artifact("output style", [source], destination)

    compiled = destination.read_text(encoding="utf-8")
    assert compiled.startswith("<!-- Bureau protocols -->\n\n")
    assert "Source files:" not in compiled
    assert "Do not edit this runtime artifact directly." not in compiled
    assert compiled.endswith(body)


def test_compile_runtime_artifact_omits_source_boundaries(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    destination = tmp_path / "runtime.md"
    first.write_text("# First\n", encoding="utf-8")
    second.write_text("# Second\n", encoding="utf-8")

    compile_runtime_artifact("code standards", [first, second], destination)

    compiled = destination.read_text(encoding="utf-8")
    assert compiled.startswith("<!-- Bureau protocols -->\n\n")
    assert compiled.index("# First") < compiled.index("# Second")
    assert "<!-- Bureau source boundary -->" not in compiled


def test_code_standards_default_sources_target_reference_layer() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    [default_source] = get_default_protocol_sources("code_standards", repo_root=repo_root)
    mindset_source = get_code_standards_mindset_source(repo_root=repo_root)

    assert default_source.name == "code-standards-reference.md"
    assert default_source != mindset_source


def test_compile_code_standards_skill_wraps_merged_reference_content(tmp_path: Path) -> None:
    wrapper = tmp_path / "SKILL.wrapper.md"
    destination = tmp_path / "code-standards" / "SKILL.md"
    first = tmp_path / "team-style.md"
    second = tmp_path / "design-principles.md"

    wrapper.write_text(
        "---\n"
        "name: code-standards\n"
        "description: Generated detailed standards skill.\n"
        "---\n\n"
        "# Code standards\n\n"
        "## Detailed standards reference\n\n",
        encoding="utf-8",
    )
    first.write_text("# Team style\n\n- favor simple APIs\n", encoding="utf-8")
    second.write_text("# Design principles\n\n- document invariants\n", encoding="utf-8")

    wrote_skill = compile_code_standards_skill(
        destination,
        source_overrides=[first, second],
        wrapper_source=wrapper,
    )

    compiled = destination.read_text(encoding="utf-8")
    assert wrote_skill is True
    assert compiled.startswith("---\nname: code-standards\n")
    assert "## Detailed standards reference" in compiled
    assert "<!-- Bureau protocols -->\n\n" in compiled
    assert compiled.index("# Team style") < compiled.index("# Design principles")


def test_compile_code_standards_skill_returns_false_when_disabled(tmp_path: Path) -> None:
    wrapper = tmp_path / "SKILL.wrapper.md"
    destination = tmp_path / "code-standards" / "SKILL.md"
    wrapper.write_text(
        "---\n"
        "name: code-standards\n"
        "description: Generated detailed standards skill.\n"
        "---\n",
        encoding="utf-8",
    )

    wrote_skill = compile_code_standards_skill(
        destination,
        config={"protocols": {"code_standards": "off"}},
        repo_root=tmp_path,
        wrapper_source=wrapper,
    )

    assert wrote_skill is False
    assert not destination.exists()
