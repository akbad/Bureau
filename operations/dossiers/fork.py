"""Fork operation: create independent copy of a dossier."""
import sqlite3
from pathlib import Path
from typing import Any

from .db import open_dossier_db, safe_db_path
from .fold import _generate_hash, _slugify, _now_iso


def fork_dossier(
    dossiers_dir: Path,
    slug: str,
    name: str | None = None,
) -> dict[str, str]:
    """Create an independent copy of a dossier. Always unlocked.

    Uses sqlite3.backup() for a WAL-safe copy (ensures uncommitted
    WAL transactions are included in the fork).
    """
    source_path = safe_db_path(dossiers_dir, slug)
    if not source_path.exists():
        raise FileNotFoundError(f"Dossier not found: {slug}")

    # Read original metadata for defaults
    with open_dossier_db(source_path) as source_conn:
        meta = source_conn.execute("SELECT * FROM metadata").fetchone()

        fork_name = name or f"{meta['name']} (fork)"
        # collision-safe: retry until we find an unused slug
        while True:
            new_hash = _generate_hash()
            new_slug = f"{_slugify(fork_name)}-{new_hash}"
            dest_path = dossiers_dir / f"{new_slug}.db"
            if not dest_path.exists():
                break

        # WAL-safe copy via sqlite3 backup API
        dest_conn = sqlite3.connect(dest_path)
        source_conn.backup(dest_conn)
        dest_conn.close()
        dest_path.chmod(0o600)  # owner read/write only

    # Update metadata in the fork
    now = _now_iso()
    with open_dossier_db(dest_path) as conn:
        with conn:  # transaction boundary
            conn.execute(
                """UPDATE metadata SET
                   hash = ?, name = ?, slug = ?, updated_at = ?,
                   parent = ?, locked_by = NULL, locked_at = NULL""",
                (new_hash, fork_name, new_slug, now, meta["hash"]),
            )

    return {"slug": new_slug, "hash": new_hash}
