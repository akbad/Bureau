"""Tests for the filesystem helper library (``bin/lib/fs.sh``).

`_sed_inplace` replaces `sed -i`, whose in-place flag is spelled
incompatibly across BSD and GNU (`sed -i ''` vs `sed -i`). These pin the
behaviours that make the replacement safe to reach for, not merely portable:
the original survives a failed edit, permissions survive a successful one,
and a symlinked target is followed rather than overwritten.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIB_PATH = REPO_ROOT / "bin" / "lib" / "fs.sh"


def _run(body: str) -> subprocess.CompletedProcess:
    """Source the lib under the same strict mode every Bureau script uses."""
    script = f'set -euo pipefail\nsource "{LIB_PATH}"\n{body}'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def test_lib_can_be_sourced_under_nounset() -> None:
    # every consumer runs `set -euo pipefail`; an unguarded ${var} would
    # abort the sourcing script rather than this helper
    result = _run('declare -f _sed_inplace >/dev/null && echo ok')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_substitutes_in_place(tmp_path: Path) -> None:
    target = tmp_path / "hub.md"
    target.write_text("root is {{PROTOCOLS_DIR}} here\n")
    result = _run(f'_sed_inplace "s|{{{{PROTOCOLS_DIR}}}}|/opt/x|g" "{target}"')
    assert result.returncode == 0, result.stderr
    assert target.read_text() == "root is /opt/x here\n"


def test_preserves_file_mode(tmp_path: Path) -> None:
    # `mv` of a fresh temp file installs the temp's umask-derived mode; a
    # private file silently becoming world-readable is the failure this pins
    target = tmp_path / "secret.conf"
    target.write_text("token = OLD\n")
    target.chmod(0o600)
    result = _run(f'_sed_inplace "s|OLD|NEW|" "{target}"')
    assert result.returncode == 0, result.stderr
    assert target.read_text() == "token = NEW\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_failed_edit_leaves_the_original_untouched(tmp_path: Path) -> None:
    target = tmp_path / "hub.md"
    target.write_text("original\n")
    result = _run(f'_sed_inplace "s|unterminated" "{target}"')
    assert result.returncode != 0
    assert target.read_text() == "original\n"  # not truncated, not mangled


def test_failed_edit_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    target = tmp_path / "hub.md"
    target.write_text("original\n")
    _run(f'_sed_inplace "s|unterminated" "{target}"')
    assert [p.name for p in tmp_path.iterdir()] == ["hub.md"]


def test_follows_symlinks_instead_of_replacing_them(tmp_path: Path) -> None:
    # Bureau deploys symlinks widely; `sed -i` on either platform would
    # replace the link with a regular file and silently detach it
    real = tmp_path / "real.md"
    real.write_text("value OLD\n")
    link = tmp_path / "link.md"
    link.symlink_to(real)

    result = _run(f'_sed_inplace "s|OLD|NEW|" "{link}"')
    assert result.returncode == 0, result.stderr
    assert link.is_symlink()             # still a link
    assert real.read_text() == "value NEW\n"  # target edited


def test_handles_paths_with_spaces(tmp_path: Path) -> None:
    target = tmp_path / "a dir with spaces"
    target.mkdir()
    target = target / "file name.md"
    target.write_text("OLD\n")
    result = _run(f'_sed_inplace "s|OLD|NEW|" "{target}"')
    assert result.returncode == 0, result.stderr
    assert target.read_text() == "NEW\n"


def test_missing_file_fails_with_a_named_error(tmp_path: Path) -> None:
    result = _run(f'_sed_inplace "s|a|b|" "{tmp_path}/nope.md"')
    assert result.returncode != 0
    assert "nope.md" in result.stderr


def test_directory_target_fails_rather_than_corrupting(tmp_path: Path) -> None:
    result = _run(f'_sed_inplace "s|a|b|" "{tmp_path}"')
    assert result.returncode != 0


def test_content_is_byte_exact_without_trailing_newline(tmp_path: Path) -> None:
    # redirection copies sed's output verbatim; a file with no final newline
    # must not acquire one
    target = tmp_path / "hub.md"
    target.write_bytes(b"no trailing newline")
    result = _run(f'_sed_inplace "s|no|NO|" "{target}"')
    assert result.returncode == 0, result.stderr
    assert target.read_bytes() == b"NO trailing newline"


def test_handles_a_path_beginning_with_a_dash(tmp_path: Path) -> None:
    # the input is redirected rather than passed as an argument, so a leading
    # dash is the shell's problem and never reaches sed's option parsing
    target = tmp_path / "-weird.md"
    target.write_text("OLD\n")
    result = _run(f'cd "{tmp_path}" && _sed_inplace "s|OLD|NEW|" "-weird.md"')
    assert result.returncode == 0, result.stderr
    assert target.read_text() == "NEW\n"


def test_sed_own_diagnostic_reaches_stderr(tmp_path: Path) -> None:
    # our wrapper line says *that* it failed; sed says *why*. Both are needed.
    target = tmp_path / "hub.md"
    target.write_text("original\n")
    result = _run(f'_sed_inplace "s|unterminated" "{target}"')
    assert "_sed_inplace: sed failed" in result.stderr
    assert "unterminated" in result.stderr.lower()


def test_circular_symlink_fails_instead_of_hanging(tmp_path: Path) -> None:
    # `while [[ -L ]]` over a cycle never terminates; the hop limit is what
    # turns an unkillable script into a named error
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.symlink_to(b)
    b.symlink_to(a)
    result = subprocess.run(
        ["bash", "-c", f'set -euo pipefail\nsource "{LIB_PATH}"\n'
                       f'_sed_inplace "s|x|y|" "{a}"'],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "symlink" in result.stderr.lower()
