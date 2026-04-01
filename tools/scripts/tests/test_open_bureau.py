from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPEN_BUREAU = REPO_ROOT / "bin" / "open-bureau"


def test_open_bureau_sets_up_protocols_before_tools() -> None:
    content = OPEN_BUREAU.read_text(encoding="utf-8")

    assert content.index("protocols/scripts/set-up-protocols.sh") < content.index(
        "tools/scripts/set-up-tools.sh"
    )
