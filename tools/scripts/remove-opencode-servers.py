#!/usr/bin/env -S uv run
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        return 1

    path = Path(sys.argv[1]).expanduser()
    servers = sys.argv[2:]
    if not servers or not path.exists():
        return 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0

    mcp = data.get("mcp")
    if not isinstance(mcp, dict):
        return 0

    changed = False
    for server_id in servers:
        if server_id in mcp:
            mcp.pop(server_id)
            changed = True

    if changed:
        data["mcp"] = mcp
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
