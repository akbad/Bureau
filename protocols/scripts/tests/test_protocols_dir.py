"""Tests for user-scoped protocols directory logic.

Tests the hub-and-spoke deployment semantics, reset-protocols CLI,
and shell helper functions (resolve_path, display_name_from_path).
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RESET_SCRIPT = REPO_ROOT / "bin" / "reset-protocols"
SET_UP_PROTOCOLS_SCRIPT = REPO_ROOT / "protocols" / "scripts" / "set-up-protocols.sh"
STATIC_DIR = REPO_ROOT / "protocols" / "context" / "static"

# hub file and generated runtime artifacts at top level, spokes inside ops/
HUB_FILE = "ops-hub.md"
OUTPUT_STYLE_FILE = "output-style.md"
CODE_STANDARDS_FILE = "code-standards.md"
OPS_SPOKE_FILES = [
    "session-start.md",
    "task-assessment.md",
    "task-execution.md",
    "task-completion.md",
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# bin/reset-protocols
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestResetProtocols:
    """Tests for the bin/reset-protocols CLI command."""

    def test_creates_dir_if_missing(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / ".config" / "bureau" / "protocols"
        assert not protocols_dir.exists()

        result = subprocess.run(
            ["bash", str(RESET_SCRIPT), "--force"],
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert protocols_dir.exists()
        assert (protocols_dir / HUB_FILE).exists()
        assert (protocols_dir / OUTPUT_STYLE_FILE).exists()
        assert (protocols_dir / CODE_STANDARDS_FILE).exists()
        assert (protocols_dir / "ops").is_dir()
        for spoke in OPS_SPOKE_FILES:
            assert (protocols_dir / "ops" / spoke).exists(), f"Missing spoke: {spoke}"
        assert not (protocols_dir / "ops" / CODE_STANDARDS_FILE).exists()

    def test_deploys_hub_and_spokes(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / ".config" / "bureau" / "protocols"
        protocols_dir.mkdir(parents=True)

        result = subprocess.run(
            ["bash", str(RESET_SCRIPT), "--force"],
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # hub should exist and have resolved paths (no {{PROTOCOLS_DIR}} remaining)
        hub_content = (protocols_dir / HUB_FILE).read_text()
        assert "{{PROTOCOLS_DIR}}" not in hub_content
        assert str(protocols_dir) in hub_content
        output_style_dest = protocols_dir / OUTPUT_STYLE_FILE
        output_style_source = STATIC_DIR / "ops" / OUTPUT_STYLE_FILE
        assert output_style_dest.exists()
        assert output_style_source.read_text() in output_style_dest.read_text()
        code_standards_dest = protocols_dir / CODE_STANDARDS_FILE
        code_standards_source = STATIC_DIR / "ops" / CODE_STANDARDS_FILE
        assert code_standards_dest.exists()
        assert code_standards_source.read_text() in code_standards_dest.read_text()
        # all spokes should match source content
        for spoke in OPS_SPOKE_FILES:
            dest = protocols_dir / "ops" / spoke
            source = STATIC_DIR / "ops" / spoke
            assert dest.exists(), f"Missing spoke: {spoke}"
            assert dest.read_text() == source.read_text(), f"Content mismatch: {spoke}"
        assert not (protocols_dir / "ops" / CODE_STANDARDS_FILE).exists()

    def test_removes_existing_files(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / ".config" / "bureau" / "protocols"
        protocols_dir.mkdir(parents=True)
        custom_file = protocols_dir / "my-custom-guide.md"
        custom_file.write_text("# Custom guide")

        result = subprocess.run(
            ["bash", str(RESET_SCRIPT), "--force"],
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert not custom_file.exists(), "Custom .md file should be removed"
        assert (protocols_dir / HUB_FILE).exists()

    def test_removes_deprecated_dir(self, tmp_path: Path) -> None:
        """Old .deprecated/ archive should be cleaned up on reset."""
        protocols_dir = tmp_path / ".config" / "bureau" / "protocols"
        deprecated_dir = protocols_dir / ".deprecated"
        deprecated_dir.mkdir(parents=True)
        (deprecated_dir / "tools-guide.md").write_text("# Old")

        result = subprocess.run(
            ["bash", str(RESET_SCRIPT), "--force"],
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert not deprecated_dir.exists(), ".deprecated/ should be removed on reset"

    def test_help_flag(self) -> None:
        result = subprocess.run(
            ["bash", str(RESET_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "reset-protocols" in result.stdout
        assert "--force" in result.stdout

    def test_unknown_flag_fails(self) -> None:
        result = subprocess.run(
            ["bash", str(RESET_SCRIPT), "--unknown-flag"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0


class TestSetUpProtocols:
    """Regression tests for the real setup script."""

    def test_replace_mode_removes_legacy_ops_code_standards(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / ".config" / "bureau" / "protocols"
        legacy_file = protocols_dir / "ops" / CODE_STANDARDS_FILE
        legacy_file.parent.mkdir(parents=True)
        legacy_file.write_text("legacy stale file")

        result = subprocess.run(
            ["bash", str(SET_UP_PROTOCOLS_SCRIPT), "--protocols", "replace"],
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert not legacy_file.exists()
        assert (protocols_dir / CODE_STANDARDS_FILE).exists()

    def test_sync_mode_backs_up_legacy_ops_code_standards_before_removal(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / ".config" / "bureau" / "protocols"
        legacy_file = protocols_dir / "ops" / CODE_STANDARDS_FILE
        legacy_file.parent.mkdir(parents=True)
        legacy_file.write_text("legacy stale file")

        result = subprocess.run(
            ["bash", str(SET_UP_PROTOCOLS_SCRIPT), "--protocols", "sync"],
            env={**os.environ, "HOME": str(tmp_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert not legacy_file.exists()
        assert legacy_file.with_name(f"{CODE_STANDARDS_FILE}.bak").read_text() == "legacy stale file"
        assert (protocols_dir / CODE_STANDARDS_FILE).exists()

    def test_custom_code_standards_only_change_generated_skill(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        home.mkdir()
        custom_style = tmp_path / "team-style.md"
        custom_principles = tmp_path / "design-principles.md"
        custom_style.write_text("# Team style\n\n- favor narrow interfaces\n", encoding="utf-8")
        custom_principles.write_text("# Design principles\n\n- preserve invariants\n", encoding="utf-8")

        with tempfile.TemporaryDirectory(dir=REPO_ROOT, prefix=".tmp-bureau-config-") as project_dir_str:
            project_dir = Path(project_dir_str)
            (project_dir / ".bureau.yml").write_text(
                "protocols:\n"
                "  code_standards:\n"
                f"    - {custom_style}\n"
                f"    - {custom_principles}\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["bash", str(SET_UP_PROTOCOLS_SCRIPT), "--protocols", "replace"],
                cwd=project_dir,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
                },
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0, result.stderr

        protocols_dir = home / ".config" / "bureau" / "protocols"
        mindset_text = (protocols_dir / CODE_STANDARDS_FILE).read_text(encoding="utf-8")
        skill_text = (
            home
            / ".config"
            / "bureau"
            / "generated"
            / "skills"
            / "code-standards"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        assert (STATIC_DIR / "ops" / CODE_STANDARDS_FILE).read_text(encoding="utf-8") in mindset_text
        assert "# Team style" not in mindset_text
        assert "# Design principles" not in mindset_text
        assert "# Team style" in skill_text
        assert "# Design principles" in skill_text

    def test_code_standards_off_disables_mindset_artifact_and_generated_skill(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        home.mkdir()

        with tempfile.TemporaryDirectory(dir=REPO_ROOT, prefix=".tmp-bureau-config-") as project_dir_str:
            project_dir = Path(project_dir_str)
            (project_dir / ".bureau.yml").write_text(
                "protocols:\n"
                "  code_standards: off\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["bash", str(SET_UP_PROTOCOLS_SCRIPT), "--protocols", "replace"],
                cwd=project_dir,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
                },
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0, result.stderr

        protocols_dir = home / ".config" / "bureau" / "protocols"
        assert not (protocols_dir / CODE_STANDARDS_FILE).exists()
        assert not (
            home
            / ".config"
            / "bureau"
            / "generated"
            / "skills"
            / "code-standards"
        ).exists()
        assert "Writing or editing code" not in (protocols_dir / HUB_FILE).read_text(encoding="utf-8")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shell helper functions (resolve_path, display_name_from_path)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# We test these by sourcing the relevant portion of set-up-protocols.sh
# in a subshell and calling the functions directly.

SHELL_FUNCTIONS = """
resolve_path() {
    local p="$1"
    case "$p" in
        "~"/*) echo "${HOME}${p#"~"}" ;;
        /*)    echo "$p" ;;
        *)     echo "$REPO_ROOT/$p" ;;
    esac
}

display_name_from_path() {
    local filename
    filename="$(basename "$1" .md)"
    filename="${filename//-/ }"
    filename="${filename//_/ }"
    echo "$(echo "${filename:0:1}" | tr '[:lower:]' '[:upper:]')${filename:1}"
}
"""


def _run_shell_function(func_call: str, env: dict | None = None) -> str:
    """Run a shell function and return its stdout."""
    script = SHELL_FUNCTIONS + f"\n{func_call}"
    default_env = {
        "HOME": "/Users/testuser",
        "REPO_ROOT": "/opt/bureau",
    }
    if env:
        default_env.update(env)
    result = subprocess.run(
        ["bash", "-c", script],
        env=default_env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Shell function failed: {result.stderr}"
    return result.stdout.strip()


class TestResolvePath:
    """Tests for the resolve_path shell function."""

    def test_tilde_path(self) -> None:
        out = _run_shell_function('resolve_path "~/code/my-file.md"')
        assert out == "/Users/testuser/code/my-file.md"

    def test_absolute_path(self) -> None:
        out = _run_shell_function('resolve_path "/etc/some-file.md"')
        assert out == "/etc/some-file.md"

    def test_relative_path(self) -> None:
        out = _run_shell_function('resolve_path "protocols/context/static/code-standards.md"')
        assert out == "/opt/bureau/protocols/context/static/code-standards.md"

    def test_tilde_only_is_not_expanded(self) -> None:
        # "~" alone (no slash) should be treated as relative
        out = _run_shell_function('resolve_path "~"')
        assert out == "/opt/bureau/~"

    def test_custom_home(self) -> None:
        out = _run_shell_function(
            'resolve_path "~/docs/style.md"',
            env={"HOME": "/home/custom"},
        )
        assert out == "/home/custom/docs/style.md"


class TestDisplayNameFromPath:
    """Tests for the display_name_from_path shell function."""

    def test_hyphenated_name(self) -> None:
        out = _run_shell_function('display_name_from_path "/path/to/tools-guide.md"')
        assert out == "Tools guide"

    def test_underscored_name(self) -> None:
        out = _run_shell_function('display_name_from_path "/path/to/code_standards.md"')
        assert out == "Code standards"

    def test_single_word(self) -> None:
        out = _run_shell_function('display_name_from_path "/path/to/overview.md"')
        assert out == "Overview"

    def test_mixed_separators(self) -> None:
        out = _run_shell_function(
            'display_name_from_path "/path/to/my-custom_guide.md"'
        )
        assert out == "My custom guide"

    def test_already_capitalized(self) -> None:
        out = _run_shell_function('display_name_from_path "/path/to/README.md"')
        assert out == "README"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Deploy hub-and-spoke semantics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHubSpokeDeployment:
    """Tests for hub-and-spoke deployment logic extracted from set-up-protocols.sh."""

    DEPLOY_SCRIPT_TEMPLATE = """
    BUREAU_PROTOCOLS_DIR="{protocols_dir}"
    STATIC_DIR="{static_dir}"

    mkdir -p "$BUREAU_PROTOCOLS_DIR/ops"
    cp "$STATIC_DIR/ops-hub.md" "$BUREAU_PROTOCOLS_DIR/ops-hub.md"
    cp "$STATIC_DIR/ops/output-style.md" "$BUREAU_PROTOCOLS_DIR/output-style.md"
    cp "$STATIC_DIR/ops/code-standards.md" "$BUREAU_PROTOCOLS_DIR/code-standards.md"
    for spoke in session-start.md task-assessment.md task-execution.md task-completion.md; do
        cp "$STATIC_DIR/ops/$spoke" "$BUREAU_PROTOCOLS_DIR/ops/$spoke"
    done
    sed -i '' "s|{{{{PROTOCOLS_DIR}}}}|$BUREAU_PROTOCOLS_DIR|g" "$BUREAU_PROTOCOLS_DIR/ops-hub.md"
    echo "DEPLOYED"
    """

    def test_deploys_all_files(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / "protocols"
        script = self.DEPLOY_SCRIPT_TEMPLATE.format(
            protocols_dir=protocols_dir, static_dir=STATIC_DIR
        )
        result = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True
        )
        assert "DEPLOYED" in result.stdout
        assert (protocols_dir / "ops-hub.md").exists()
        assert (protocols_dir / "output-style.md").exists()
        assert (protocols_dir / "code-standards.md").exists()
        assert (protocols_dir / "ops").is_dir()
        for spoke in OPS_SPOKE_FILES:
            assert (protocols_dir / "ops" / spoke).exists(), f"Missing: {spoke}"
        assert not (protocols_dir / "ops" / CODE_STANDARDS_FILE).exists()

    def test_hub_paths_resolved(self, tmp_path: Path) -> None:
        protocols_dir = tmp_path / "protocols"
        script = self.DEPLOY_SCRIPT_TEMPLATE.format(
            protocols_dir=protocols_dir, static_dir=STATIC_DIR
        )
        subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        hub_content = (protocols_dir / "ops-hub.md").read_text()
        assert "{{PROTOCOLS_DIR}}" not in hub_content
        assert str(protocols_dir) in hub_content

    def test_idempotent_deploy(self, tmp_path: Path) -> None:
        """Running deploy twice should produce same result."""
        protocols_dir = tmp_path / "protocols"
        script = self.DEPLOY_SCRIPT_TEMPLATE.format(
            protocols_dir=protocols_dir, static_dir=STATIC_DIR
        )
        subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        first_hub = (protocols_dir / "ops-hub.md").read_text()

        subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        second_hub = (protocols_dir / "ops-hub.md").read_text()

        assert first_hub == second_hub
