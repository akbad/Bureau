from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPEN_BUREAU = REPO_ROOT / "bin" / "open-bureau"


def test_open_bureau_sets_up_protocols_before_tools() -> None:
    content = OPEN_BUREAU.read_text(encoding="utf-8")

    assert content.index("protocols/scripts/set-up-protocols.sh") < content.index(
        "tools/scripts/set-up-tools.sh"
    )


def test_open_bureau_uses_protocols_mode_flag() -> None:
    content = OPEN_BUREAU.read_text(encoding="utf-8")

    assert "--protocols|-p" in content
    assert "replace|r" in content
    assert "sync|s" in content
    assert "off|o" in content


def test_open_bureau_does_not_reference_legacy_protocol_flags() -> None:
    content = OPEN_BUREAU.read_text(encoding="utf-8")

    assert "--update-protocols" not in content
    assert "protocols.update" not in content
    assert "protocols.force" not in content
    assert "protocols.bare" not in content
