from __future__ import annotations

from importlib import util
from pathlib import Path

import tomlkit

module_path = Path(__file__).resolve().parents[1] / "add-grok-auto-approvals.py"
spec = util.spec_from_file_location("add_grok_auto_approvals", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

apply_approvals = module.apply_approvals
merge_permission_rules = module.merge_permission_rules


def test_merge_replaces_previous_managed_only():
    allow, deny = merge_permission_rules(
        existing_allow=["Bash(user *)", "MCPTool(qdrant__*)"],
        existing_deny=["Bash(rm *)"],
        previous_managed={
            "allow": ["MCPTool(qdrant__*)"],
            "deny": ["Bash(rm *)"],
        },
        new_allow=["MCPTool(serena__*)", "Bash(git *)"],
        new_deny=["Bash(sudo *)"],
    )
    assert allow == ["Bash(user *)", "MCPTool(serena__*)", "Bash(git *)"]
    assert deny == ["Bash(sudo *)"]


def test_apply_approvals_writes_toml(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text('[ui]\ntheme = "auto"\n', encoding="utf-8")
    managed = tmp_path / "managed.json"

    apply_approvals(
        config,
        mcp_servers=["qdrant"],
        bash_allow=["git status"],
        bash_deny=["rm"],
        access_paths=["~/.config/bureau"],
        managed_path=managed,
    )

    doc = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert doc["ui"]["theme"] == "auto"
    allow = list(doc["permission"]["allow"])
    deny = list(doc["permission"]["deny"])
    assert "MCPTool(qdrant__*)" in allow
    assert "Bash(git status *)" in allow
    assert "Read(~/.config/bureau/**)" in allow
    assert "Edit(~/.config/bureau/**)" in allow
    assert "Bash(rm *)" in deny
