"""Advisory lock operations for dossiers."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import connect_dossier_db


def get_lock_status(dossiers_dir: Path, slug: str) -> dict[str, Any]:
    """Get current lock status."""
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    meta = conn.execute("SELECT locked_by, locked_at FROM metadata").fetchone()
    conn.close()
    return {"locked_by": meta["locked_by"], "locked_at": meta["locked_at"]}


def claim_lock(dossiers_dir: Path, slug: str, agent: str) -> None:
    """Claim advisory lock. Raises ValueError if already locked by another agent."""
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    meta = conn.execute("SELECT locked_by FROM metadata").fetchone()

    if meta["locked_by"] and meta["locked_by"] != agent:
        holder = meta["locked_by"]
        conn.close()
        raise ValueError(f"Dossier already locked by {holder}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE metadata SET locked_by = ?, locked_at = ?", (agent, now))
    conn.commit()
    conn.close()


def release_lock(dossiers_dir: Path, slug: str) -> None:
    """Release advisory lock."""
    conn = connect_dossier_db(dossiers_dir / f"{slug}.db")
    conn.execute("UPDATE metadata SET locked_by = NULL, locked_at = NULL")
    conn.commit()
    conn.close()
