import json
from pathlib import Path

import pytest

from operations.json_config_utils import (
    load_json_config,
    load_json_text,
    save_json_config,
)


def test_load_json_config_invalid_creates_backup_and_returns_default(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{not valid json", encoding="utf-8")
    default = {"fresh": True}

    result = load_json_config(str(config_path), default=default, create_backup=True)

    backup_path = tmp_path / "config.json.backup"
    assert result == default
    assert not config_path.exists()
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == "{not valid json"


def test_load_json_text_invalid_raises_system_exit() -> None:
    with pytest.raises(SystemExit):
        load_json_text("{not json", source="template.json")


def test_load_json_text_non_object_raises_system_exit() -> None:
    with pytest.raises(SystemExit):
        load_json_text('["not", "object"]', source="template.json")
