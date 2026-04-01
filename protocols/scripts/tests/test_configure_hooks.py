"""Tests for configure-hooks.py — idempotent hook configuration across CLIs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# import the module under test (filename uses hyphens, so importlib is needed)
import importlib
import sys

_scripts_dir = str(Path(__file__).resolve().parents[1])
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

# the file is named configure-hooks.py (hyphenated), so standard import won't work
_loader = importlib.util.spec_from_file_location(
    "configure_hooks",
    Path(__file__).resolve().parents[1] / "configure-hooks.py",
)
_mod = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(_mod)

_configure_claude = _mod._configure_claude
_configure_codex = _mod._configure_codex
_configure_gemini = _mod._configure_gemini
_configure_claude_session_start = _mod._configure_claude_session_start
_configure_codex_session_start = _mod._configure_codex_session_start
_configure_gemini_session_start = _mod._configure_gemini_session_start
_remove_claude = _mod._remove_claude
_remove_codex = _mod._remove_codex
_remove_gemini = _mod._remove_gemini
_remove_claude_session_start = _mod._remove_claude_session_start
_remove_codex_session_start = _mod._remove_codex_session_start
_remove_gemini_session_start = _mod._remove_gemini_session_start
_cat_command = _mod._cat_command
_session_start_command = _mod._session_start_command
_reminder_command = _mod._reminder_command
main = _mod.main


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Code per-prompt hooks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClaudeHook:
    """Tests for Claude Code UserPromptSubmit (per-prompt) and SessionStart hooks."""

    def test_creates_settings_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude(ops_hub, dry_run=False)

        settings = tmp_path / ".claude" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert "hooks" in data

        # per-prompt hook should contain bureau-reminder
        assert "UserPromptSubmit" in data["hooks"]
        prompt_hooks = data["hooks"]["UserPromptSubmit"]
        assert len(prompt_hooks) == 1
        assert "bureau-reminder" in prompt_hooks[0]["hooks"][0]["command"]

        # session-start hook should contain ops-hub.md (cat command)
        assert "SessionStart" in data["hooks"]
        session_hooks = data["hooks"]["SessionStart"]
        assert len(session_hooks) == 1
        assert "ops-hub.md" in session_hooks[0]["hooks"][0]["command"]

    def test_preserves_existing_hooks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        # pre-existing hook from another plugin
        existing = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": "echo existing", "timeout": 3000}]}
                ]
            }
        }
        (settings_dir / "settings.json").write_text(json.dumps(existing))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude(ops_hub, dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        hook_groups = data["hooks"]["UserPromptSubmit"]
        # should have both the existing and the new hook
        assert len(hook_groups) == 2
        commands = [g["hooks"][0]["command"] for g in hook_groups]
        assert "echo existing" in commands
        assert any("bureau-reminder" in c for c in commands)

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude(ops_hub, dry_run=False)
        first = (tmp_path / ".claude" / "settings.json").read_text()

        _configure_claude(ops_hub, dry_run=False)
        second = (tmp_path / ".claude" / "settings.json").read_text()

        assert first == second

    def test_updates_path_when_changed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)

        old_hub = tmp_path / "old" / "ops-hub.md"
        old_hub.parent.mkdir(parents=True)
        old_hub.touch()

        _configure_claude(old_hub, dry_run=False)

        new_hub = tmp_path / "new" / "ops-hub.md"
        new_hub.parent.mkdir(parents=True)
        new_hub.touch()

        _configure_claude(new_hub, dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        hook_groups = data["hooks"]["UserPromptSubmit"]
        # should still be just one hook group, with updated path
        assert len(hook_groups) == 1
        assert str(new_hub) in hook_groups[0]["hooks"][0]["command"]

        # session-start hook should also be updated
        session_hooks = data["hooks"]["SessionStart"]
        assert len(session_hooks) == 1
        assert str(new_hub) in session_hooks[0]["hooks"][0]["command"]

    def test_migrates_old_cat_to_reminder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """An old-style cat hook should be upgraded to a reminder in place."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        # simulate old-style hook (cat command in UserPromptSubmit)
        old_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": f"cat {ops_hub}", "timeout": 5000}]}
                ]
            }
        }
        (settings_dir / "settings.json").write_text(json.dumps(old_data))

        _configure_claude(ops_hub, dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        prompt_hooks = data["hooks"]["UserPromptSubmit"]
        # should still be one group, upgraded to reminder
        assert len(prompt_hooks) == 1
        assert "bureau-reminder" in prompt_hooks[0]["hooks"][0]["command"]
        assert "cat " not in prompt_hooks[0]["hooks"][0]["command"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Code SessionStart hooks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClaudeSessionStart:
    """Tests for Claude Code SessionStart hook configuration."""

    def test_creates_settings_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude_session_start(ops_hub, dry_run=False)

        settings = tmp_path / ".claude" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert "hooks" in data
        assert "SessionStart" in data["hooks"]
        hooks = data["hooks"]["SessionStart"]
        assert len(hooks) == 1
        assert "ops-hub.md" in hooks[0]["hooks"][0]["command"]
        assert hooks[0]["hooks"][0]["command"].startswith("cat ")

    def test_preserves_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        existing = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo other", "timeout": 3000}]}
                ]
            }
        }
        (settings_dir / "settings.json").write_text(json.dumps(existing))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude_session_start(ops_hub, dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        hook_groups = data["hooks"]["SessionStart"]
        assert len(hook_groups) == 2
        commands = [g["hooks"][0]["command"] for g in hook_groups]
        assert "echo other" in commands
        assert any("ops-hub.md" in c for c in commands)

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude_session_start(ops_hub, dry_run=False)
        first = (tmp_path / ".claude" / "settings.json").read_text()

        _configure_claude_session_start(ops_hub, dry_run=False)
        second = (tmp_path / ".claude" / "settings.json").read_text()

        assert first == second

    def test_updates_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        old_hub = tmp_path / "old" / "ops-hub.md"
        old_hub.parent.mkdir(parents=True)
        old_hub.touch()

        _configure_claude_session_start(old_hub, dry_run=False)

        new_hub = tmp_path / "new" / "ops-hub.md"
        new_hub.parent.mkdir(parents=True)
        new_hub.touch()

        _configure_claude_session_start(new_hub, dry_run=False)

        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        hooks = data["hooks"]["SessionStart"]
        assert len(hooks) == 1
        assert str(new_hub) in hooks[0]["hooks"][0]["command"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Codex per-prompt hooks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCodexHook:
    """Tests for Codex userpromptsubmit (per-prompt) and sessionstart hooks."""

    def test_creates_config_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex(ops_hub, dry_run=False)

        config = tmp_path / ".codex" / "config.toml"
        assert config.exists()
        text = config.read_text()
        # per-prompt hook should contain bureau-reminder
        assert "[[hooks.userpromptsubmit]]" in text
        assert "bureau-reminder" in text
        # session-start hook should contain ops-hub.md
        assert "[[hooks.sessionstart]]" in text
        assert "ops-hub.md" in text

    def test_preserves_existing_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / "config.toml").write_text('approval_policy = "never"\n')

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex(ops_hub, dry_run=False)

        text = (codex_dir / "config.toml").read_text()
        assert 'approval_policy = "never"' in text
        assert "bureau-reminder" in text
        assert "ops-hub.md" in text

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex(ops_hub, dry_run=False)
        first = (tmp_path / ".codex" / "config.toml").read_text()

        _configure_codex(ops_hub, dry_run=False)
        second = (tmp_path / ".codex" / "config.toml").read_text()

        assert first == second

    def test_updates_path_when_changed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        old_hub = tmp_path / "old" / "ops-hub.md"
        old_hub.parent.mkdir(parents=True)
        old_hub.touch()

        _configure_codex(old_hub, dry_run=False)

        new_hub = tmp_path / "new" / "ops-hub.md"
        new_hub.parent.mkdir(parents=True)
        new_hub.touch()

        _configure_codex(new_hub, dry_run=False)

        text = (tmp_path / ".codex" / "config.toml").read_text()
        assert str(new_hub) in text
        assert str(old_hub) not in text

    def test_migrates_old_cat_to_reminder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """An old-style cat hook in userpromptsubmit should be upgraded to a reminder."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        # simulate old-style config
        old_text = (
            '[[hooks.userpromptsubmit]]\n'
            'type = "command"\n'
            f'command = "cat {ops_hub}"\n'
            'timeout = 5000\n'
        )
        (codex_dir / "config.toml").write_text(old_text)

        _configure_codex(ops_hub, dry_run=False)

        text = (codex_dir / "config.toml").read_text()
        assert "bureau-reminder" in text
        # sessionstart block should be appended
        assert "[[hooks.sessionstart]]" in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Codex SessionStart hooks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCodexSessionStart:
    """Tests for Codex sessionstart hook configuration."""

    def test_creates_config_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex_session_start(ops_hub, dry_run=False)

        config = tmp_path / ".codex" / "config.toml"
        assert config.exists()
        text = config.read_text()
        assert "[[hooks.sessionstart]]" in text
        assert "ops-hub.md" in text

    def test_preserves_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / "config.toml").write_text('approval_policy = "never"\n')

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex_session_start(ops_hub, dry_run=False)

        text = (codex_dir / "config.toml").read_text()
        assert 'approval_policy = "never"' in text
        assert "[[hooks.sessionstart]]" in text

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex_session_start(ops_hub, dry_run=False)
        first = (tmp_path / ".codex" / "config.toml").read_text()

        _configure_codex_session_start(ops_hub, dry_run=False)
        second = (tmp_path / ".codex" / "config.toml").read_text()

        assert first == second

    def test_updates_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        old_hub = tmp_path / "old" / "ops-hub.md"
        old_hub.parent.mkdir(parents=True)
        old_hub.touch()

        _configure_codex_session_start(old_hub, dry_run=False)

        new_hub = tmp_path / "new" / "ops-hub.md"
        new_hub.parent.mkdir(parents=True)
        new_hub.touch()

        _configure_codex_session_start(new_hub, dry_run=False)

        text = (tmp_path / ".codex" / "config.toml").read_text()
        assert str(new_hub) in text
        assert str(old_hub) not in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini CLI per-prompt hooks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGeminiHook:
    """Tests for Gemini CLI BeforeAgent (per-prompt) and SessionStart hooks."""

    def test_creates_settings_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini(ops_hub, dry_run=False)

        settings = tmp_path / ".gemini" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert data["hooksConfig"]["enabled"] is True

        # per-prompt hook should contain bureau-reminder
        assert len(data["hooks"]["BeforeAgent"]) == 1
        entry = data["hooks"]["BeforeAgent"][0]
        assert entry["name"] == "bureau-ops-hub"
        assert "bureau-reminder" in entry["hooks"][0]["command"]

        # session-start hook should contain ops-hub.md
        assert len(data["hooks"]["SessionStart"]) == 1
        session_entry = data["hooks"]["SessionStart"][0]
        assert session_entry["name"] == "bureau-ops-hub-session"
        assert "ops-hub.md" in session_entry["hooks"][0]["command"]

    def test_enables_hooks_feature(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Gemini hooks use hooksConfig.enabled — script must set it to true."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        (gemini_dir / "settings.json").write_text(json.dumps({"hooksConfig": {"enabled": False}}))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini(ops_hub, dry_run=False)

        data = json.loads((gemini_dir / "settings.json").read_text())
        assert data["hooksConfig"]["enabled"] is True

    def test_preserves_existing_hooks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        existing = {
            "hooksConfig": {"enabled": True},
            "hooks": {
                "BeforeAgent": [
                    {"name": "other-hook", "hooks": [{"type": "command", "command": "echo other"}]}
                ],
            },
        }
        (gemini_dir / "settings.json").write_text(json.dumps(existing))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini(ops_hub, dry_run=False)

        data = json.loads((gemini_dir / "settings.json").read_text())
        hooks = data["hooks"]["BeforeAgent"]
        assert len(hooks) == 2
        names = [h["name"] for h in hooks]
        assert "other-hook" in names
        assert "bureau-ops-hub" in names

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini(ops_hub, dry_run=False)
        first = (tmp_path / ".gemini" / "settings.json").read_text()

        _configure_gemini(ops_hub, dry_run=False)
        second = (tmp_path / ".gemini" / "settings.json").read_text()

        assert first == second

    def test_migrates_old_cat_to_reminder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """An old-style cat hook should be upgraded to a reminder in place."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        old_data = {
            "hooksConfig": {"enabled": True},
            "hooks": {
                "BeforeAgent": [
                    {
                        "name": "bureau-ops-hub",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"cat {ops_hub}",
                                "timeout": 5000,
                                "description": "Re-inject ops hub routing table before each prompt",
                            }
                        ],
                    }
                ],
            },
        }
        (gemini_dir / "settings.json").write_text(json.dumps(old_data))

        _configure_gemini(ops_hub, dry_run=False)

        data = json.loads((gemini_dir / "settings.json").read_text())
        before_agent = data["hooks"]["BeforeAgent"]
        assert len(before_agent) == 1
        assert "bureau-reminder" in before_agent[0]["hooks"][0]["command"]
        # session-start should also be present
        assert "SessionStart" in data["hooks"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini CLI SessionStart hooks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGeminiSessionStart:
    """Tests for Gemini CLI SessionStart hook configuration."""

    def test_creates_settings_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini_session_start(ops_hub, dry_run=False)

        settings = tmp_path / ".gemini" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert data["hooksConfig"]["enabled"] is True
        assert len(data["hooks"]["SessionStart"]) == 1
        entry = data["hooks"]["SessionStart"][0]
        assert entry["name"] == "bureau-ops-hub-session"
        assert "ops-hub.md" in entry["hooks"][0]["command"]

    def test_preserves_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        existing = {
            "hooksConfig": {"enabled": True},
            "hooks": {
                "SessionStart": [
                    {"name": "other-session-hook", "hooks": [{"type": "command", "command": "echo init"}]}
                ],
            },
        }
        (gemini_dir / "settings.json").write_text(json.dumps(existing))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini_session_start(ops_hub, dry_run=False)

        data = json.loads((gemini_dir / "settings.json").read_text())
        hooks = data["hooks"]["SessionStart"]
        assert len(hooks) == 2
        names = [h["name"] for h in hooks]
        assert "other-session-hook" in names
        assert "bureau-ops-hub-session" in names

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini_session_start(ops_hub, dry_run=False)
        first = (tmp_path / ".gemini" / "settings.json").read_text()

        _configure_gemini_session_start(ops_hub, dry_run=False)
        second = (tmp_path / ".gemini" / "settings.json").read_text()

        assert first == second

    def test_updates_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        old_hub = tmp_path / "old" / "ops-hub.md"
        old_hub.parent.mkdir(parents=True)
        old_hub.touch()

        _configure_gemini_session_start(old_hub, dry_run=False)

        new_hub = tmp_path / "new" / "ops-hub.md"
        new_hub.parent.mkdir(parents=True)
        new_hub.touch()

        _configure_gemini_session_start(new_hub, dry_run=False)

        data = json.loads((tmp_path / ".gemini" / "settings.json").read_text())
        hooks = data["hooks"]["SessionStart"]
        assert len(hooks) == 1
        assert str(new_hub) in hooks[0]["hooks"][0]["command"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCLI:
    """Tests for the configure-hooks.py CLI."""

    def test_dry_run_makes_no_changes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        protocols_dir = tmp_path / "protocols"
        protocols_dir.mkdir()
        (protocols_dir / "ops-hub.md").touch()

        result = main([
            "--protocols-dir", str(protocols_dir),
            "--agent", "claude",
            "--dry-run",
        ])

        assert result == 0
        # no settings.json should be created in dry-run
        assert not (tmp_path / ".claude" / "settings.json").exists()

    def test_rejects_relative_path(self, tmp_path: Path) -> None:
        result = main([
            "--protocols-dir", "relative/path",
            "--agent", "claude",
        ])
        assert result == 1

    def test_remove_without_protocols_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--remove should work without --protocols-dir."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = main(["--remove", "--agent", "claude"])
        assert result == 0

    def test_remove_all_agents(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--remove should process all specified agents and remove both hook tiers."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # first configure hooks for all agents
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        main([
            "--protocols-dir", str(ops_hub.parent),
            "--agent", "claude", "--agent", "codex", "--agent", "gemini",
        ])

        # verify hooks were added
        assert (tmp_path / ".claude" / "settings.json").exists()
        assert (tmp_path / ".codex" / "config.toml").exists()
        assert (tmp_path / ".gemini" / "settings.json").exists()

        # now remove
        result = main([
            "--remove",
            "--agent", "claude", "--agent", "codex", "--agent", "gemini",
        ])
        assert result == 0

        # verify Claude hooks removed (both tiers)
        claude_data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(claude_data["hooks"]["UserPromptSubmit"]) == 0
        assert len(claude_data["hooks"]["SessionStart"]) == 0

        # verify Codex hooks removed (both tiers)
        codex_text = (tmp_path / ".codex" / "config.toml").read_text()
        assert "ops-hub.md" not in codex_text
        assert "bureau-reminder" not in codex_text
        assert "[[hooks.userpromptsubmit]]" not in codex_text
        assert "[[hooks.sessionstart]]" not in codex_text

        # verify Gemini hooks removed (both tiers)
        gemini_data = json.loads((tmp_path / ".gemini" / "settings.json").read_text())
        assert len(gemini_data["hooks"]["BeforeAgent"]) == 0
        assert len(gemini_data["hooks"]["SessionStart"]) == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude hook removal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClaudeRemoval:
    """Tests for Claude Code hook removal (both tiers)."""

    def test_removes_bureau_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude(ops_hub, dry_run=False)
        _remove_claude(dry_run=False)

        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(data["hooks"]["UserPromptSubmit"]) == 0
        assert len(data["hooks"]["SessionStart"]) == 0

    def test_preserves_other_hooks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        existing = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": "echo other", "timeout": 3000}]},
                    {"hooks": [{"type": "command", "command": _reminder_command(ops_hub), "timeout": 5000}]},
                ],
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo session-other", "timeout": 3000}]},
                    {"hooks": [{"type": "command", "command": f"cat {ops_hub}", "timeout": 5000}]},
                ],
            }
        }
        (settings_dir / "settings.json").write_text(json.dumps(existing))

        _remove_claude(dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        prompt_hooks = data["hooks"]["UserPromptSubmit"]
        assert len(prompt_hooks) == 1
        assert prompt_hooks[0]["hooks"][0]["command"] == "echo other"

        session_hooks = data["hooks"]["SessionStart"]
        assert len(session_hooks) == 1
        assert session_hooks[0]["hooks"][0]["command"] == "echo session-other"

    def test_noop_when_no_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(json.dumps({"hooks": {"UserPromptSubmit": []}}))

        _remove_claude(dry_run=False)
        # should not crash, file unchanged

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude(ops_hub, dry_run=False)
        _remove_claude(dry_run=False)
        first = (tmp_path / ".claude" / "settings.json").read_text()
        _remove_claude(dry_run=False)
        second = (tmp_path / ".claude" / "settings.json").read_text()
        assert first == second

    def test_removes_old_style_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Removal should clean up old-style cat hooks too."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        old_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": f"cat {ops_hub}", "timeout": 5000}]},
                ]
            }
        }
        (settings_dir / "settings.json").write_text(json.dumps(old_data))

        _remove_claude(dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        assert len(data["hooks"]["UserPromptSubmit"]) == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude SessionStart removal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClaudeSessionStartRemoval:
    """Tests for Claude Code SessionStart hook removal."""

    def test_removes_bureau_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_claude_session_start(ops_hub, dry_run=False)
        _remove_claude_session_start(dry_run=False)

        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(data["hooks"]["SessionStart"]) == 0

    def test_preserves_others(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        existing = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo other-session", "timeout": 3000}]},
                    {"hooks": [{"type": "command", "command": f"cat {ops_hub}", "timeout": 5000}]},
                ]
            }
        }
        (settings_dir / "settings.json").write_text(json.dumps(existing))

        _remove_claude_session_start(dry_run=False)

        data = json.loads((settings_dir / "settings.json").read_text())
        hooks = data["hooks"]["SessionStart"]
        assert len(hooks) == 1
        assert hooks[0]["hooks"][0]["command"] == "echo other-session"

    def test_noop_when_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(json.dumps({"hooks": {}}))

        _remove_claude_session_start(dry_run=False)
        # should not crash


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Codex hook removal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCodexRemoval:
    """Tests for Codex hook removal (both tiers)."""

    def test_removes_bureau_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex(ops_hub, dry_run=False)
        _remove_codex(dry_run=False)

        text = (tmp_path / ".codex" / "config.toml").read_text()
        assert "ops-hub.md" not in text
        assert "bureau-reminder" not in text
        assert "[[hooks.userpromptsubmit]]" not in text
        assert "[[hooks.sessionstart]]" not in text

    def test_preserves_existing_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / "config.toml").write_text('approval_policy = "never"\n')

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex(ops_hub, dry_run=False)
        _remove_codex(dry_run=False)

        text = (codex_dir / "config.toml").read_text()
        assert 'approval_policy = "never"' in text
        assert "ops-hub.md" not in text
        assert "bureau-reminder" not in text

    def test_noop_when_no_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / "config.toml").write_text('approval_policy = "never"\n')

        _remove_codex(dry_run=False)
        text = (codex_dir / "config.toml").read_text()
        assert 'approval_policy = "never"' in text

    def test_noop_when_no_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        _remove_codex(dry_run=False)  # should not crash

    def test_removes_old_style_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Removal should clean up old-style cat hooks from userpromptsubmit."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        old_text = (
            '[[hooks.userpromptsubmit]]\n'
            'type = "command"\n'
            f'command = "cat {ops_hub}"\n'
            'timeout = 5000\n'
        )
        (codex_dir / "config.toml").write_text(old_text)

        _remove_codex(dry_run=False)

        text = (codex_dir / "config.toml").read_text()
        assert "ops-hub.md" not in text
        assert "[[hooks.userpromptsubmit]]" not in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Codex SessionStart removal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCodexSessionStartRemoval:
    """Tests for Codex sessionstart hook removal."""

    def test_removes_bureau_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex_session_start(ops_hub, dry_run=False)
        _remove_codex_session_start(dry_run=False)

        text = (tmp_path / ".codex" / "config.toml").read_text()
        assert "ops-hub.md" not in text
        assert "[[hooks.sessionstart]]" not in text

    def test_preserves_others(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / "config.toml").write_text('approval_policy = "never"\n')

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_codex_session_start(ops_hub, dry_run=False)
        _remove_codex_session_start(dry_run=False)

        text = (codex_dir / "config.toml").read_text()
        assert 'approval_policy = "never"' in text
        assert "ops-hub.md" not in text

    def test_noop_when_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True)
        (codex_dir / "config.toml").write_text('approval_policy = "never"\n')

        _remove_codex_session_start(dry_run=False)
        # should not crash


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini hook removal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGeminiRemoval:
    """Tests for Gemini CLI hook removal (both tiers)."""

    def test_removes_bureau_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini(ops_hub, dry_run=False)
        _remove_gemini(dry_run=False)

        data = json.loads((tmp_path / ".gemini" / "settings.json").read_text())
        assert len(data["hooks"]["BeforeAgent"]) == 0
        assert len(data["hooks"]["SessionStart"]) == 0

    def test_preserves_other_hooks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        existing = {
            "hooks": {
                "enabled": True,
                "BeforeAgent": [
                    {"name": "other-hook", "hooks": [{"type": "command", "command": "echo other"}]},
                ],
                "SessionStart": [
                    {"name": "other-session-hook", "hooks": [{"type": "command", "command": "echo session"}]},
                ],
            }
        }
        (gemini_dir / "settings.json").write_text(json.dumps(existing))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini(ops_hub, dry_run=False)
        _remove_gemini(dry_run=False)

        data = json.loads((gemini_dir / "settings.json").read_text())
        before_agent = data["hooks"]["BeforeAgent"]
        assert len(before_agent) == 1
        assert before_agent[0]["name"] == "other-hook"

        session_hooks = data["hooks"]["SessionStart"]
        assert len(session_hooks) == 1
        assert session_hooks[0]["name"] == "other-session-hook"

    def test_noop_when_no_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        _remove_gemini(dry_run=False)  # should not crash (no settings file)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini SessionStart removal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGeminiSessionStartRemoval:
    """Tests for Gemini CLI SessionStart hook removal."""

    def test_removes_bureau_hook(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini_session_start(ops_hub, dry_run=False)
        _remove_gemini_session_start(dry_run=False)

        data = json.loads((tmp_path / ".gemini" / "settings.json").read_text())
        assert len(data["hooks"]["SessionStart"]) == 0

    def test_preserves_others(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        existing = {
            "hooks": {
                "enabled": True,
                "SessionStart": [
                    {"name": "other-session-hook", "hooks": [{"type": "command", "command": "echo init"}]},
                ],
            }
        }
        (gemini_dir / "settings.json").write_text(json.dumps(existing))

        ops_hub = tmp_path / "protocols" / "ops-hub.md"
        ops_hub.parent.mkdir(parents=True)
        ops_hub.touch()

        _configure_gemini_session_start(ops_hub, dry_run=False)
        _remove_gemini_session_start(dry_run=False)

        data = json.loads((gemini_dir / "settings.json").read_text())
        hooks = data["hooks"]["SessionStart"]
        assert len(hooks) == 1
        assert hooks[0]["name"] == "other-session-hook"

    def test_noop_when_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        _remove_gemini_session_start(dry_run=False)
        # should not crash (no settings file)
