"""Tests for setup wizard."""
from __future__ import annotations

from pathlib import Path

import pytest

from concierge.bridge.cc_connect import BridgeConfig, CLIBackend
from concierge.setup.wizard import (
    SETUP_QUESTIONS,
    SetupAnswers,
    generate_config,
    initialize_data_dir,
    load_config,
    save_config,
    validate_answers,
)


class TestSetupQuestions:
    """Tests for SETUP_QUESTIONS constant."""

    def test_setup_questions_defined(self) -> None:
        assert len(SETUP_QUESTIONS) > 0
        keys = [q["key"] for q in SETUP_QUESTIONS]
        assert "cli_backend" in keys
        assert "telegram_token" in keys
        assert "telegram_user_id" in keys


class TestValidateAnswers:
    """Tests for validate_answers."""

    def test_validate_answers_valid(self) -> None:
        answers = SetupAnswers(
            cli_backend=CLIBackend.CLAUDE,
            telegram_token="123:abc",
            telegram_user_id=42,
            briefing_time="08:30",
        )
        errors = validate_answers(answers)
        assert errors == []

    def test_validate_answers_missing_backend(self) -> None:
        answers = SetupAnswers(
            cli_backend=None,
            telegram_token="123:abc",
            telegram_user_id=42,
        )
        errors = validate_answers(answers)
        assert any("backend" in e.lower() for e in errors)

    def test_validate_answers_missing_token(self) -> None:
        answers = SetupAnswers(
            cli_backend=CLIBackend.CLAUDE,
            telegram_token="",
            telegram_user_id=42,
        )
        errors = validate_answers(answers)
        assert any("token" in e.lower() for e in errors)

    def test_validate_answers_invalid_time(self) -> None:
        answers = SetupAnswers(
            cli_backend=CLIBackend.CLAUDE,
            telegram_token="123:abc",
            telegram_user_id=42,
            briefing_time="25:99",
        )
        errors = validate_answers(answers)
        assert any("time" in e.lower() for e in errors)


class TestGenerateConfig:
    """Tests for generate_config."""

    def test_generate_config(self, tmp_path: Path) -> None:
        answers = SetupAnswers(
            cli_backend=CLIBackend.GEMINI,
            telegram_token="123:abc",
            telegram_user_id=99,
            assistant_name="TestBot",
        )
        cfg = generate_config(answers, tmp_path)
        assert cfg.backend == CLIBackend.GEMINI
        assert cfg.telegram_token == "123:abc"
        assert cfg.allowed_user_id == 99
        assert cfg.assistant_name == "TestBot"
        assert cfg.data_dir == tmp_path


class TestSaveLoadConfig:
    """Tests for save_config and load_config roundtrip."""

    def test_save_and_load_config_roundtrip(self, tmp_path: Path) -> None:
        cfg = BridgeConfig(
            backend=CLIBackend.CODEX,
            telegram_token="111:xyz",
            allowed_user_id=7,
            assistant_name="RoundTrip",
            data_dir=tmp_path / "data",
        )
        config_path = tmp_path / "config.yml"
        save_config(cfg, config_path)

        loaded = load_config(config_path)
        assert loaded is not None
        assert loaded.backend == cfg.backend
        assert loaded.telegram_token == cfg.telegram_token
        assert loaded.allowed_user_id == cfg.allowed_user_id
        assert loaded.assistant_name == cfg.assistant_name
        assert loaded.data_dir == cfg.data_dir

    def test_load_config_missing_file(self, tmp_path: Path) -> None:
        result = load_config(tmp_path / "nope.yml")
        assert result is None


class TestInitializeDataDir:
    """Tests for initialize_data_dir."""

    def test_initialize_data_dir_creates_structure(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "concierge"
        initialize_data_dir(data_dir)

        assert (data_dir / "topics").is_dir()
        assert (data_dir / "auto").is_dir()
        assert (data_dir / "state").is_dir()
        assert (data_dir / "attaches").is_dir()

    def test_initialize_data_dir_creates_personality(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "concierge"
        initialize_data_dir(data_dir)

        personality = data_dir / "PERSONALITY.md"
        assert personality.exists()
        content = personality.read_text()
        assert "Personality" in content

    def test_initialize_data_dir_preserves_existing(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "concierge"
        data_dir.mkdir(parents=True)
        personality = data_dir / "PERSONALITY.md"
        personality.write_text("Custom personality")

        initialize_data_dir(data_dir)

        assert personality.read_text() == "Custom personality"
