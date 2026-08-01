"""Tests for the get-config CLI — specifically `--list access-paths`.

Drives operations.config_cli:main() end-to-end through the real config load
(find_repo_root → tmp defaults.yml → get_config → resolver → stdout), so it
exercises the same path set-up-tools.sh hits via `uv run get-config`.

The key behavioral contract under test: access paths are emitted NEWLINE-delimited
(not space-joined like `--list agents`), so a path containing spaces survives as a
single line for the bash `mapfile -t` consumer.
"""

import sys
from pathlib import Path

import yaml

from operations.config_cli import main
from operations.config_loader import clear_config_cache


def _expected(path_str: str) -> str:
    """Absolute form a path resolves to, matching the resolver's pipeline."""
    return str(Path(path_str).expanduser().resolve())


def _write_defaults(tmp_path, monkeypatch, data: dict) -> None:
    """Write data as defaults.yml and isolate config discovery to tmp_path."""
    (tmp_path / "defaults.yml").write_text(yaml.dump(data, default_flow_style=False))
    monkeypatch.setattr(
        "operations.config_loader.find_repo_root", lambda *_a, **_kw: tmp_path
    )
    monkeypatch.setattr("operations.config_loader.find_project_config", lambda: None)
    monkeypatch.chdir(tmp_path)
    clear_config_cache()


def _run_list_access_paths(monkeypatch) -> int:
    monkeypatch.setattr(sys, "argv", ["get-config", "--list", "access-paths"])
    return main()


def test_prints_enabled_paths_one_per_line(tmp_path, monkeypatch, capsys):
    """Each enabled path is emitted on its own line, in order, absolute."""
    _write_defaults(tmp_path, monkeypatch, {
        "agent_access": {"paths": {
            "bureau_config": {"enabled": True, "path": "~/.config/bureau"},
            "extra": {"enabled": True, "path": str(tmp_path / "extra")},
        }},
    })

    rc = _run_list_access_paths(monkeypatch)
    out = capsys.readouterr().out

    assert rc == 0
    assert out.splitlines() == [
        _expected("~/.config/bureau"),
        _expected(str(tmp_path / "extra")),
    ]


def test_disabled_entries_are_omitted(tmp_path, monkeypatch, capsys):
    """A default-disabled entry (e.g. workspace) must not appear in the output."""
    _write_defaults(tmp_path, monkeypatch, {
        "workspace": str(tmp_path),
        "agent_access": {"paths": {
            "bureau_config": {"enabled": True, "path": "~/.config/bureau"},
            "workspace": {"enabled": False, "path": "${workspace}"},
        }},
    })

    rc = _run_list_access_paths(monkeypatch)
    out = capsys.readouterr().out

    assert rc == 0
    assert out.splitlines() == [_expected("~/.config/bureau")]


def test_path_with_space_survives_as_single_line(tmp_path, monkeypatch, capsys):
    """A path containing a space stays one line (the reason for newline-delimiting)."""
    spaced = tmp_path / "dir with space"
    _write_defaults(tmp_path, monkeypatch, {
        "agent_access": {"paths": {"spaced": {"enabled": True, "path": str(spaced)}}},
    })

    rc = _run_list_access_paths(monkeypatch)
    lines = capsys.readouterr().out.splitlines()

    assert rc == 0
    assert lines == [_expected(str(spaced))]
    assert " " in lines[0]


def test_empty_agent_access_prints_nothing_and_exits_zero(tmp_path, monkeypatch, capsys):
    """No agent_access block → no output, exit 0 (not an error)."""
    _write_defaults(tmp_path, monkeypatch, {"workspace": str(tmp_path)})

    rc = _run_list_access_paths(monkeypatch)
    out = capsys.readouterr().out

    assert rc == 0
    assert out == ""
