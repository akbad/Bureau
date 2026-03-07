"""Tests for cc-connect bridge adapter."""
from __future__ import annotations

from pathlib import Path

import pytest

from concierge.bridge.cc_connect import (
    BridgeConfig,
    CLIBackend,
    CLI_COMMANDS,
    build_headless_command,
    validate_config,
)


class TestCLIBackendEnum:
    """Tests for CLIBackend enum."""

    def test_cli_backend_enum(self) -> None:
        assert CLIBackend.CODEX.value == "codex"
        assert CLIBackend.CLAUDE.value == "claude"
        assert CLIBackend.GEMINI.value == "gemini"
        # Ensure exactly three backends
        assert len(CLIBackend) == 3


class TestGetCLICommand:
    """Tests for BridgeConfig.get_cli_command."""

    def test_get_cli_command_codex(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CODEX,
            telegram_token="123:abc",
            allowed_user_id=42,
        )
        cmd = cfg.get_cli_command("hello world")
        assert cmd == ["codex", "-q", "hello world"]

    def test_get_cli_command_claude(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CLAUDE,
            telegram_token="123:abc",
            allowed_user_id=42,
        )
        cmd = cfg.get_cli_command("hello world")
        assert cmd == ["claude", "-p", "hello world"]

    def test_get_cli_command_gemini(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.GEMINI,
            telegram_token="123:abc",
            allowed_user_id=42,
        )
        cmd = cfg.get_cli_command("hello world")
        assert cmd == ["gemini", "-p", "hello world"]


class TestBuildHeadlessCommand:
    """Tests for build_headless_command."""

    def test_build_headless_command(self, tmp_path: Path) -> None:
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Run a health check")

        cmd = build_headless_command(CLIBackend.CLAUDE, prompt_file)
        assert cmd == ["claude", "-p", "Run a health check"]

    def test_build_headless_command_missing_file(self, tmp_path: Path) -> None:
        prompt_file = tmp_path / "nonexistent.txt"
        cmd = build_headless_command(CLIBackend.CODEX, prompt_file)
        # Should produce empty prompt for missing file
        assert cmd == ["codex", "-q", ""]


class TestValidateConfig:
    """Tests for validate_config."""

    def test_validate_config_valid(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CLAUDE,
            telegram_token="123456:ABCdefGHIjklMNO",
            allowed_user_id=42,
        )
        errors = validate_config(cfg)
        assert errors == []

    def test_validate_config_missing_token(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CLAUDE,
            telegram_token="",
            allowed_user_id=42,
        )
        errors = validate_config(cfg)
        assert any("token is required" in e for e in errors)

    def test_validate_config_invalid_token_format(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CLAUDE,
            telegram_token="no-colon-here",
            allowed_user_id=42,
        )
        errors = validate_config(cfg)
        assert any("format" in e.lower() for e in errors)

    def test_validate_config_invalid_user_id(self) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CLAUDE,
            telegram_token="123:abc",
            allowed_user_id=0,
        )
        errors = validate_config(cfg)
        assert any("user ID" in e for e in errors)
