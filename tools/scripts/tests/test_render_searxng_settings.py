import json
from importlib import util
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "render-searxng-settings.py"
spec = util.spec_from_file_location("render_searxng_settings", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_render_settings_enables_json_and_disables_google(tmp_path):
    settings_file = tmp_path / "settings.yml"
    secret_file = tmp_path / "secret"
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps({
            "services": {
                "searxng": {
                    "settings": {
                        "settings_file": str(settings_file),
                        "secret_file": str(secret_file),
                        "disabled_engines": [
                            "google",
                            "google scholar",
                        ],
                    }
                }
            }
        }),
        encoding="utf-8",
    )

    result = module.render_settings_from_plan(plan_path, "searxng")

    assert result["settings_file"] == str(settings_file)
    assert settings_file.exists()
    assert secret_file.exists()
    rendered = settings_file.read_text(encoding="utf-8")
    assert "formats:" in rendered
    assert "  - json" in rendered
    assert "limiter: false" in rendered
    assert "public_instance: false" in rendered
    assert "image_proxy: false" in rendered
    assert "name: google\n    disabled: true" in rendered
    assert "name: google scholar\n    disabled: true" in rendered


def test_render_settings_reuses_existing_secret(tmp_path):
    settings_file = tmp_path / "settings.yml"
    secret_file = tmp_path / "secret"
    secret_file.write_text("already-secret\n", encoding="utf-8")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps({
            "services": {
                "searxng": {
                    "settings": {
                        "settings_file": str(settings_file),
                        "secret_file": str(secret_file),
                    }
                }
            }
        }),
        encoding="utf-8",
    )

    module.render_settings_from_plan(plan_path, "searxng")

    assert secret_file.read_text(encoding="utf-8") == "already-secret\n"
    assert "secret_key: already-secret" in settings_file.read_text(encoding="utf-8")
