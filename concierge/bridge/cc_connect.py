"""cc-connect adapter — bridges Telegram messages to CLI tools."""

# Design rationale:
# CLIBackend enum + CLI_COMMANDS dict pattern cleanly separates backend
# identity from invocation details; adding a new backend requires one enum
# member and one dict entry, with zero changes to command-building logic.
# build_headless_command reads prompt text from a file and appends it to the
# base command, producing a fully self-contained argv list suitable for
# subprocess.run — no shell interpolation, no quoting bugs.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CLIBackend(Enum):
    """Supported CLI backends."""
    CODEX = "codex"
    CLAUDE = "claude"
    GEMINI = "gemini"


# CLI-specific invocation patterns
CLI_COMMANDS: dict[CLIBackend, list[str]] = {
    CLIBackend.CODEX: ["codex", "-q"],
    CLIBackend.CLAUDE: ["claude", "-p"],
    CLIBackend.GEMINI: ["gemini", "-p"],
}


@dataclass
class BridgeConfig:
    """Configuration for the cc-connect bridge."""
    backend: CLIBackend
    telegram_token: str
    allowed_user_id: int
    assistant_name: str = "Concierge"
    data_dir: Path = Path.home() / ".config" / "bureau" / "concierge"

    @property
    def session_state_path(self) -> Path:
        """Path to the session state YAML file."""
        return self.data_dir / "state" / "session.yml"

    def get_cli_command(self, prompt: str) -> list[str]:
        """Build the CLI command for a given prompt."""
        base = list(CLI_COMMANDS[self.backend])
        base.append(prompt)
        return base


def build_headless_command(
    backend: CLIBackend,
    prompt_file: Path,
) -> list[str]:
    """Build a headless CLI command for background/scheduled execution.

    Used for probes, valets, dispatches — anything that runs without
    user interaction.
    """
    base = list(CLI_COMMANDS[backend])
    prompt_text = prompt_file.read_text() if prompt_file.exists() else ""
    base.append(prompt_text)
    return base


def validate_config(config: BridgeConfig) -> list[str]:
    """Validate bridge configuration.

    Returns a list of error messages (empty = valid).
    """
    errors = []

    if not config.telegram_token:
        errors.append("Telegram bot token is required")
    elif not config.telegram_token.count(":") == 1:
        errors.append("Telegram bot token format appears invalid (expected 'id:hash')")

    if config.allowed_user_id <= 0:
        errors.append("Telegram user ID must be a positive integer")

    if not config.assistant_name.strip():
        errors.append("Assistant name cannot be empty")

    return errors
