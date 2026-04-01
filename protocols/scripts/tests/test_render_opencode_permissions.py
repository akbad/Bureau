from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "render-opencode-permissions.py"
spec = util.spec_from_file_location("render_opencode_permissions", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
render_opencode_permissions = module.render_opencode_permissions


def test_orders_bash_permissions_last_match_wins():
    config = {
        "auto_approved": {
            "bash": {
                "enabled": True,
                "ruleset": {
                    "allow": ["git status"],
                    "deny": ["rm"],
                },
            }
        }
    }

    rendered = render_opencode_permissions(config)
    bash_rules = rendered["permission"]["bash"]

    assert list(bash_rules.keys()) == ["*", "git status*", "rm*"]
    assert bash_rules["*"] == "ask"
    assert bash_rules["git status*"] == "allow"
    assert bash_rules["rm*"] == "deny"


def test_skips_empty_bash_prefixes():
    config = {
        "auto_approved": {
            "bash": {
                "enabled": True,
                "ruleset": {
                    "allow": ["", "   ", "git status"],
                    "deny": ["", "rm"],
                },
            }
        }
    }

    rendered = render_opencode_permissions(config)
    bash_rules = rendered["permission"]["bash"]

    assert list(bash_rules.keys()) == ["*", "git status*", "rm*"]
    assert bash_rules["*"] == "ask"
    assert bash_rules["git status*"] == "allow"
    assert bash_rules["rm*"] == "deny"


def test_disabled_bash_approvals_emit_no_bash_permissions():
    config = {"auto_approved": {"bash": {"enabled": False}}}

    rendered = render_opencode_permissions(config)

    assert "bash" not in rendered.get("permission", {})
