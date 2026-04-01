from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "write-codex-exec-policy.py"
spec = util.spec_from_file_location("write_codex_exec_policy", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
write_exec_policy = module.write_exec_policy


def test_writes_prefix_rules(tmp_path):
    rules_path = tmp_path / "rules" / "bureau.rules"

    write_exec_policy(["git status"], ["rm"], rules_path=rules_path)

    content = rules_path.read_text(encoding="utf-8")

    assert 'prefix_rule(pattern=["git", "status"], decision="allow")' in content
    assert 'prefix_rule(pattern=["rm"], decision="forbidden")' in content


def test_skips_empty_prefixes(tmp_path):
    rules_path = tmp_path / "rules" / "bureau.rules"

    write_exec_policy(["", "   ", "git status"], ["", "rm"], rules_path=rules_path)

    content = rules_path.read_text(encoding="utf-8")

    assert 'prefix_rule(pattern=["git", "status"], decision="allow")' in content
    assert 'prefix_rule(pattern=["rm"], decision="forbidden")' in content
    assert "pattern=[]" not in content
