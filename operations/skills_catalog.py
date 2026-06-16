from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .config_loader import find_repo_root


def resolve_skills_catalog(config: Mapping[str, Any]) -> dict[str, Any]:
    skills_cfg = config.get("skills", {})
    enabled = (
        None
        if skills_cfg.get("enabled") in (None, "all")
        else set(skills_cfg.get("enabled", []))
    )
    disabled = set(skills_cfg.get("disabled", []))
    sources = skills_cfg.get("sources", [])
    try:
        repo_root = find_repo_root()
    except FileNotFoundError:
        repo_root = Path.cwd()

    resolved: list[str] = []
    for source in sources:
        root = Path(source["path"]).expanduser()
        if not root.is_absolute():
            root = repo_root / root
        if not root.exists():
            continue
        for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            name = skill_dir.name
            if enabled is not None and name not in enabled:
                continue
            if name in disabled:
                continue
            resolved.append(name)

    return {"skills": resolved}
