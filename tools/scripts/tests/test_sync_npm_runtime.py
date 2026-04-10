import json
from importlib import util
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "sync-npm-runtime.py"
spec = util.spec_from_file_location("sync_npm_runtime", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

MANIFEST_FILENAME = module.MANIFEST_FILENAME
sync_runtime = module.sync_runtime


def _plan(runtime_dir: Path) -> dict:
    return {
        "npm_runtime": {
            "runtime_dir": str(runtime_dir),
            "cache_dir": str(runtime_dir / ".npm-cache"),
            "packages": ["mcp-filter"],
            "binaries": ["mcp-filter"],
        }
    }


def test_sync_runtime_skips_when_disabled(tmp_path):
    result = sync_runtime({})
    assert result == {"installed": False, "reason": "disabled"}


def test_sync_runtime_installs_when_manifest_missing(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, check, env, **kwargs):
        calls.append((cmd, check, env["NPM_CONFIG_CACHE"]))
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "mcp-filter").write_text("", encoding="utf-8")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = sync_runtime(_plan(tmp_path))

    assert result["installed"] is True
    assert result["reason"] == "manifest_changed"
    assert calls[0][0][:3] == ["npm", "install", "--prefix"]
    manifest = json.loads((tmp_path / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["packages"] == ["mcp-filter"]


def test_sync_runtime_skips_when_manifest_and_binaries_match(tmp_path, monkeypatch):
    manifest_path = tmp_path / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps({"packages": ["mcp-filter"], "binaries": ["mcp-filter"]}),
        encoding="utf-8",
    )
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "mcp-filter").write_text("", encoding="utf-8")

    def fail_run(*args, **kwargs):
        raise AssertionError("npm install should not run")

    monkeypatch.setattr(module.subprocess, "run", fail_run)

    result = sync_runtime(_plan(tmp_path))

    assert result == {"installed": False, "reason": "up_to_date"}


def test_sync_runtime_reinstalls_when_binary_missing(tmp_path, monkeypatch):
    manifest_path = tmp_path / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps({"packages": ["mcp-filter"], "binaries": ["mcp-filter"]}),
        encoding="utf-8",
    )
    calls = []

    def fake_run(cmd, check, env, **kwargs):
        calls.append(cmd)
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "mcp-filter").write_text("", encoding="utf-8")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = sync_runtime(_plan(tmp_path))

    assert result["installed"] is True
    assert result["reason"] == "missing_binaries"
    assert result["missing_binaries"] == ["mcp-filter"]
    assert calls
