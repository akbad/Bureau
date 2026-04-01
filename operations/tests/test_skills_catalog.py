from operations.skills_catalog import resolve_skills_catalog


def test_filters_by_enabled_disabled_and_sources(tmp_path):
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha").mkdir(parents=True)
    (skills_dir / "beta").mkdir(parents=True)

    config = {
        "skills": {
            "enabled": ["alpha"],
            "disabled": ["beta"],
            "sources": [
                {"path": str(skills_dir)},
            ],
        }
    }

    resolved = resolve_skills_catalog(config)
    assert resolved["skills"] == ["alpha"]
