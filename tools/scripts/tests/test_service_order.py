import json
from importlib import util
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "service-order.py"
spec = util.spec_from_file_location("service_order", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def _write_plan(tmp_path: Path, payload: dict) -> str:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(payload), encoding="utf-8")
    return str(plan_path)


def test_reads_services_key_and_outputs_topological_order(tmp_path, monkeypatch, capsys):
    plan_path = _write_plan(
        tmp_path,
        {
            "services": {
                "api": {"depends_on": {"services": ["db"]}},
                "db": {},
            }
        },
    )

    monkeypatch.setattr(module.sys, "argv", ["service-order.py", plan_path])
    code = module.main()
    captured = capsys.readouterr()

    assert code == 0
    assert captured.out.strip().splitlines() == ["db", "api"]


def test_returns_non_zero_on_cycle(tmp_path, monkeypatch, capsys):
    plan_path = _write_plan(
        tmp_path,
        {
            "services": {
                "a": {"depends_on": {"services": ["b"]}},
                "b": {"depends_on": {"services": ["a"]}},
            }
        },
    )

    monkeypatch.setattr(module.sys, "argv", ["service-order.py", plan_path])
    code = module.main()
    captured = capsys.readouterr()

    assert code == 1
    assert "Detected cycle" in captured.err
