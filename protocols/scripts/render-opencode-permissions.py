#!/usr/bin/env -S uv run
from __future__ import annotations

import json
from typing import Any, Mapping

from operations.approval_rules import build_opencode_bash_rules
from operations.config_loader import get_config


def render_opencode_permissions(config: Mapping[str, Any]) -> dict[str, Any]:
    auto_approved = config.get("auto_approved", {})
    bash_cfg = auto_approved.get("bash", {})
    enabled = bool(bash_cfg.get("enabled", False))

    if not enabled:
        return {}

    ruleset = bash_cfg.get("ruleset", {})
    allow = ruleset.get("allow", [])
    deny = ruleset.get("deny", [])

    bash_rules = build_opencode_bash_rules(allow, deny)

    return {"permission": {"bash": bash_rules}}


def main() -> None:
    permissions = render_opencode_permissions(get_config())
    print(json.dumps(permissions))


if __name__ == "__main__":
    main()
