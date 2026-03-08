"""Setup wizard — guides initial Concierge configuration."""

# Design rationale:
# Setup questions are declared as a data-driven list (SETUP_QUESTIONS) rather
# than hard-coded in a procedural flow, making it easy to add, reorder, or
# skip questions without touching control logic.  Validation is a separate
# pure function (validate_answers) that returns a list of error strings,
# keeping it testable independently of I/O.  Directory initialization
# (initialize_data_dir) creates the full expected folder tree and stub files
# up front so downstream code can assume the structure exists.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from concierge.bridge.cc_connect import CLIBackend, BridgeConfig


@dataclass
class SetupAnswers:
    """Collected answers from the setup wizard."""
    cli_backend: CLIBackend | None = None
    telegram_token: str = ""
    telegram_user_id: int = 0
    assistant_name: str = "Concierge"
    briefing_time: str = "08:30"
    install_launchd: bool = True


SETUP_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "cli_backend",
        "prompt": "Which CLI do you use? (codex/claude/gemini)",
        "type": "choice",
        "choices": ["codex", "claude", "gemini"],
        "default": "claude",
    },
    {
        "key": "telegram_token",
        "prompt": "Enter your Telegram bot token (from @BotFather)",
        "type": "string",
        "required": True,
    },
    {
        "key": "telegram_user_id",
        "prompt": "Enter your Telegram user ID (numeric)",
        "type": "int",
        "required": True,
    },
    {
        "key": "assistant_name",
        "prompt": "What should the assistant call itself?",
        "type": "string",
        "default": "Concierge",
    },
    {
        "key": "briefing_time",
        "prompt": "Morning briefing time (HH:MM, 24h format)",
        "type": "string",
        "default": "08:30",
    },
    {
        "key": "install_launchd",
        "prompt": "Install macOS Launch Agent for always-on operation?",
        "type": "bool",
        "default": True,
    },
]


def validate_answers(answers: SetupAnswers) -> list[str]:
    """Validate setup answers. Returns list of error messages."""
    errors = []

    if answers.cli_backend is None:
        errors.append("CLI backend is required")

    if not answers.telegram_token:
        errors.append("Telegram bot token is required")

    if answers.telegram_user_id <= 0:
        errors.append("Telegram user ID must be a positive integer")

    # Validate time format
    try:
        parts = answers.briefing_time.split(":")
        if len(parts) != 2:
            raise ValueError
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        errors.append(f"Invalid briefing time format: '{answers.briefing_time}' (expected HH:MM)")

    return errors


def generate_config(answers: SetupAnswers, data_dir: Path) -> BridgeConfig:
    """Generate a BridgeConfig from setup answers."""
    return BridgeConfig(
        backend=answers.cli_backend or CLIBackend.CLAUDE,
        telegram_token=answers.telegram_token,
        allowed_user_id=answers.telegram_user_id,
        assistant_name=answers.assistant_name,
        data_dir=data_dir,
    )


def save_config(config: BridgeConfig, config_path: Path) -> None:
    """Save bridge configuration to YAML."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "backend": config.backend.value,
        "telegram_token": config.telegram_token,
        "allowed_user_id": config.allowed_user_id,
        "assistant_name": config.assistant_name,
        "data_dir": str(config.data_dir),
    }
    config_path.write_text(yaml.dump(data, default_flow_style=False))


def load_config(config_path: Path) -> BridgeConfig | None:
    """Load bridge configuration from YAML. Returns None if not found."""
    if not config_path.exists():
        return None
    data = yaml.safe_load(config_path.read_text())
    if not data:
        return None
    return BridgeConfig(
        backend=CLIBackend(data["backend"]),
        telegram_token=data["telegram_token"],
        allowed_user_id=data["allowed_user_id"],
        assistant_name=data.get("assistant_name", "Concierge"),
        data_dir=Path(data.get("data_dir", str(Path.home() / ".config/bureau/concierge"))),
    )


def initialize_data_dir(data_dir: Path) -> None:
    """Create the data directory structure for a new installation."""
    dirs = [
        data_dir / "topics",
        data_dir / "auto",
        data_dir / "state",
        data_dir / "attaches",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create stub PERSONALITY.md if not exists
    personality_path = data_dir / "PERSONALITY.md"
    if not personality_path.exists():
        personality_path.write_text(
            "# Personality\n\n"
            "- Warm and friendly\n"
            "- Casual but helpful\n"
            "- Uses emoji occasionally\n"
            "- Keeps messages concise\n"
        )

    # Create stub core.md if not exists
    core_path = data_dir / "core.md"
    if not core_path.exists():
        core_path.write_text(
            "# Core Memory\n\n"
            "<!-- This file is populated as the Concierge learns about you -->\n"
        )
