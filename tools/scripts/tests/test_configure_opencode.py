import json
import sys
from importlib import util
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "configure-opencode.py"
spec = util.spec_from_file_location("configure_opencode", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def _run_main(args):
    argv = ["configure-opencode.py", *args]
    original = sys.argv
    try:
        sys.argv = argv
        return module.main()
    finally:
        sys.argv = original


def test_reconciles_bureau_managed_instruction_entries(tmp_path: Path) -> None:
    target = tmp_path / "opencode.json"
    generated = tmp_path / "generated.json"
    target.write_text(
        json.dumps(
            {
                "instructions": [
                    "/custom/user.md",
                    "/repo/protocols/context/static/tools-guide.md",
                    "/repo/protocols/context/static/handoff-guide.md",
                ],
                "theme": "existing",
            }
        ),
        encoding="utf-8",
    )
    generated.write_text(
        json.dumps(
            {
                "instructions": [
                    "/Users/test/.config/bureau/protocols/output-style.md",
                    "/Users/test/.config/bureau/protocols/ops-hub.md",
                ],
                "theme": "generated",
            }
        ),
        encoding="utf-8",
    )

    assert _run_main(["--target", str(target), "--generated", str(generated)]) == 0

    merged = json.loads(target.read_text(encoding="utf-8"))
    assert merged["instructions"] == [
        "/Users/test/.config/bureau/protocols/output-style.md",
        "/Users/test/.config/bureau/protocols/ops-hub.md",
        "/custom/user.md",
    ]
    assert merged["theme"] == "existing"


def test_bare_mode_removes_only_bureau_managed_instruction_entries(tmp_path: Path) -> None:
    target = tmp_path / "opencode.json"
    generated = tmp_path / "generated.json"
    target.write_text(
        json.dumps(
            {
                "instructions": [
                    "/Users/test/.config/bureau/protocols/output-style.md",
                    "/Users/test/.config/bureau/protocols/ops-hub.md",
                    "/custom/user.md",
                ],
                "theme": "existing",
            }
        ),
        encoding="utf-8",
    )
    generated.write_text(json.dumps({"instructions": []}), encoding="utf-8")

    assert _run_main(
        [
            "--target",
            str(target),
            "--generated",
            str(generated),
            "--bare",
        ]
    ) == 0

    merged = json.loads(target.read_text(encoding="utf-8"))
    assert merged["instructions"] == ["/custom/user.md"]
    assert merged["theme"] == "existing"


def test_reconciles_bureau_managed_agent_entries(tmp_path: Path) -> None:
    target = tmp_path / "opencode.json"
    generated = tmp_path / "generated.json"
    target.write_text(
        json.dumps(
            {
                "agent": {
                    "accessibility-auditor": {
                        "mode": "all",
                        "description": "Bureau agent: accessibility-auditor",
                        "prompt": "{file:/Users/test/.config/opencode/agent/bureau-agents/accessibility-auditor.md}",
                    },
                    "custom-agent": {
                        "mode": "all",
                        "description": "My custom agent",
                        "prompt": "{file:/Users/test/.config/opencode/agent/custom-agent.md}",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    generated.write_text(json.dumps({"agent": {}}), encoding="utf-8")

    assert _run_main(["--target", str(target), "--generated", str(generated)]) == 0

    merged = json.loads(target.read_text(encoding="utf-8"))
    assert merged["agent"] == {
        "custom-agent": {
            "mode": "all",
            "description": "My custom agent",
            "prompt": "{file:/Users/test/.config/opencode/agent/custom-agent.md}",
        }
    }


def test_newly_written_mcp_ids_reports_only_new_entries() -> None:
    # merge_missing preserves a pre-existing id (only overwriting its command), so
    # only ids absent from the user's config beforehand count as Bureau-written;
    # reporting a pre-existing (possibly user-owned) id would let a later prune
    # delete the user's entry (issue C6)
    original_mcp = {"foo": {"type": "local", "command": ["user-foo"]}}
    generated_mcp = {
        "foo": {"type": "local", "command": ["bureau-foo"]},
        "bar": {"type": "local", "command": ["bureau-bar"]},
    }
    assert module.newly_written_mcp_ids(original_mcp, generated_mcp) == ["bar"]


def test_newly_written_mcp_ids_treats_null_placeholder_as_writable() -> None:
    # merge_missing writes when base[k] is None, so a null placeholder is a write
    assert module.newly_written_mcp_ids(
        {"foo": None}, {"foo": {"type": "local", "command": ["bureau-foo"]}}
    ) == ["foo"]


def test_main_reports_newly_written_mcp_ids_on_last_stdout_line(tmp_path: Path, capsys) -> None:
    target = tmp_path / "opencode.json"
    generated = tmp_path / "generated.json"
    target.write_text(
        json.dumps({"mcp": {"foo": {"type": "local", "command": ["user-foo"]}}}),
        encoding="utf-8",
    )
    generated.write_text(
        json.dumps(
            {
                "mcp": {
                    "foo": {"type": "local", "command": ["bureau-foo"]},
                    "bar": {"type": "local", "command": ["bureau-bar"]},
                }
            }
        ),
        encoding="utf-8",
    )

    assert _run_main(["--target", str(target), "--generated", str(generated)]) == 0

    # the last stdout line is the marker + CSV of newly-written ids — only "bar";
    # the user's pre-existing "foo" is preserved (command refreshed) but NOT written
    last_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert last_line == f"{module.OC_WRITTEN_MARKER}bar"
    merged = json.loads(target.read_text(encoding="utf-8"))
    assert set(merged["mcp"]) == {"foo", "bar"}
    assert merged["mcp"]["foo"]["command"] == ["bureau-foo"]


def test_bare_mode_removes_only_bureau_managed_agent_entries(tmp_path: Path) -> None:
    target = tmp_path / "opencode.json"
    generated = tmp_path / "generated.json"
    target.write_text(
        json.dumps(
            {
                "agent": {
                    "architecture-audit": {
                        "mode": "all",
                        "description": "Bureau agent: architecture-audit",
                        "prompt": "{file:/Users/test/.config/opencode/agent/bureau-agents/architecture-audit.md}",
                    },
                    "custom-agent": {
                        "mode": "all",
                        "description": "My custom agent",
                        "prompt": "{file:/Users/test/.config/opencode/agent/custom-agent.md}",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    generated.write_text(json.dumps({"agent": {}}), encoding="utf-8")

    assert _run_main(
        [
            "--target",
            str(target),
            "--generated",
            str(generated),
            "--bare",
        ]
    ) == 0

    merged = json.loads(target.read_text(encoding="utf-8"))
    assert merged["agent"] == {
        "custom-agent": {
            "mode": "all",
            "description": "My custom agent",
            "prompt": "{file:/Users/test/.config/opencode/agent/custom-agent.md}",
        }
    }
