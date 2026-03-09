"""Cleanup handler for Bureau dossiers.

Manages retention of conversation dossier databases (.db) and their
SQLite sidecars in ~/.config/bureau/dossiers/.

# Design rationale:
# Dossiers are now single .db files (WAL mode). Companion files are
# the WAL and SHM sidecars created by SQLite.
# During transition, legacy .md + .tasks.db pairs are also scanned
# and cleaned up based on YAML frontmatter timestamps.
# Retention is based on the 'updated_at' metadata timestamp from
# the SQLite database, not filesystem mtime.
"""
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import CleanupHandler, CleanupError
from ..trash import get_trash_dir, move_to_trash, write_manifest
from ...config_loader import get_trash_grace_period


DOSSIERS_DIR = Path(os.path.expanduser("~/.config/bureau/dossiers"))

# Legacy format support (transition period)
_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---", re.DOTALL)
_UPDATED_RE = re.compile(r"^updated:\s*(.+)$", re.MULTILINE)


class DossiersHandler(CleanupHandler):
    """Cleanup handler for Bureau dossiers (.db files, with legacy .md support)."""

    name = "dossiers"

    @staticmethod
    def _read_updated_from_db(db_path: Path) -> datetime | None:
        """Read updated_at from SQLite metadata table."""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT updated_at FROM metadata").fetchone()
            conn.close()
            if not row:
                return None
            dt = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (sqlite3.Error, OSError):
            return None

    @staticmethod
    def _read_updated_from_md(md_path: Path) -> datetime | None:
        """Read updated timestamp from legacy YAML frontmatter."""
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            return None
        fm_match = _FRONTMATTER_RE.search(text)
        if not fm_match:
            return None
        updated_match = _UPDATED_RE.search(fm_match.group(1))
        if not updated_match:
            return None
        try:
            dt = datetime.fromisoformat(updated_match.group(1).strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    @staticmethod
    def _companion_files_db(db_path: Path) -> list[Path]:
        """WAL/SHM sidecars for a .db file."""
        parent = db_path.parent
        stem = db_path.name  # e.g. "slug.db"
        candidates = [
            parent / f"{stem}-wal",
            parent / f"{stem}-shm",
        ]
        return [p for p in candidates if p.exists()]

    @staticmethod
    def _companion_files_legacy(md_path: Path) -> list[Path]:
        """Companion files for legacy .md format."""
        slug = md_path.stem
        parent = md_path.parent
        candidates = [
            parent / f"{slug}.tasks.db",
            parent / f"{slug}.tasks.db-wal",
            parent / f"{slug}.tasks.db-shm",
        ]
        return [p for p in candidates if p.exists()]

    def get_stale_items(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Find stale dossiers (new .db format + legacy .md format)."""
        try:
            items: list[dict[str, Any]] = []
            if not DOSSIERS_DIR.exists():
                return items

            # New format: .db files
            for db_file in DOSSIERS_DIR.glob("*.db"):
                # Skip WAL/SHM sidecars and legacy .tasks.db files
                if db_file.name.endswith(("-wal", "-shm")) or ".tasks." in db_file.name:
                    continue
                updated = self._read_updated_from_db(db_file)
                if updated is None:
                    continue
                if updated < cutoff:
                    companions = self._companion_files_db(db_file)
                    all_files = [db_file] + companions
                    items.append({
                        "path": db_file,
                        "companions": companions,
                        "all_files": all_files,
                        "updated": updated,
                        "size": sum(f.stat().st_size for f in all_files),
                    })

            # Legacy format: .md files (transition period)
            for md_file in DOSSIERS_DIR.glob("*.md"):
                updated = self._read_updated_from_md(md_file)
                if updated is None:
                    continue
                if updated < cutoff:
                    companions = self._companion_files_legacy(md_file)
                    all_files = [md_file] + companions
                    items.append({
                        "path": md_file,
                        "companions": companions,
                        "all_files": all_files,
                        "updated": updated,
                        "size": sum(f.stat().st_size for f in all_files),
                    })

            return items
        except OSError as e:
            raise CleanupError(f"Failed to scan dossiers: {e}") from e

    def export_items_to_trash(self, items: list[dict[str, Any]], retention: str) -> str:
        """Move all dossier files to trash."""
        try:
            trash_dir = get_trash_dir(self.name)
            moved_files: list[Path] = []
            for item in items:
                for file_path in item["all_files"]:
                    if file_path.exists():
                        dest = move_to_trash(file_path, self.name)
                        moved_files.append(dest)
            write_manifest(trash_dir, self.name, len(items), retention,
                           get_trash_grace_period(), files=moved_files)
            return str(trash_dir)
        except OSError as e:
            raise CleanupError(f"Failed to move dossier files to trash: {e}") from e

    def delete_items_from_storage(self, items: list[dict[str, Any]]) -> int:
        """Files already moved by export_items_to_trash."""
        return len(items)

    def _wipe(self, backup: bool) -> dict[str, Any]:
        """Completely erase all dossier files (both formats)."""
        try:
            items: list[dict[str, Any]] = []
            if not DOSSIERS_DIR.exists():
                return {"storage": self.name, "wiped": 0, "message": "no dossier files found"}

            # Collect all .db files (new format)
            for db_file in DOSSIERS_DIR.glob("*.db"):
                if db_file.name.endswith(("-wal", "-shm")) or ".tasks." in db_file.name:
                    continue
                companions = self._companion_files_db(db_file)
                all_files = [db_file] + companions
                items.append({
                    "path": db_file,
                    "companions": companions,
                    "all_files": all_files,
                    "updated": self._read_updated_from_db(db_file),
                    "size": sum(f.stat().st_size for f in all_files),
                })

            # Collect legacy .md files
            for md_file in DOSSIERS_DIR.glob("*.md"):
                companions = self._companion_files_legacy(md_file)
                all_files = [md_file] + companions
                items.append({
                    "path": md_file,
                    "companions": companions,
                    "all_files": all_files,
                    "updated": self._read_updated_from_md(md_file),
                    "size": sum(f.stat().st_size for f in all_files),
                })

            if not items:
                return {"storage": self.name, "wiped": 0, "message": "no dossier files found"}

            backup_path = None
            if backup:
                backup_path = self.export_items_to_trash(items, "wipe")
            else:
                for item in items:
                    for file_path in item["all_files"]:
                        if file_path.exists():
                            file_path.unlink()

            result: dict[str, Any] = {"storage": self.name, "wiped": len(items)}
            if backup_path:
                result["backup_path"] = backup_path
            return result
        except OSError as e:
            raise CleanupError(f"Failed to wipe dossiers: {e}") from e
