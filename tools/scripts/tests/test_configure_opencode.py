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
