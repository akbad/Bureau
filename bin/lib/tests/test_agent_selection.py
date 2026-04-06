from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIB_PATH = REPO_ROOT / "bin" / "lib" / "agent-selection.sh"


def test_agent_selection_lib_can_be_sourced_with_nounset() -> None:
    script = f"""
set -euo pipefail
source "{LIB_PATH}"
printf '%s\\n' "$(_agent_config_name "Claude Code")"
printf '%s\\n' "$(_agent_config_name "Gemini CLI")"
printf '%s\\n' "$(_agent_config_name "Codex")"
"""
    result = subprocess.run(
        ["bash", "-lc", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["claude", "gemini", "codex"]
