"""Cleanup handler for Bureau dossiers.

Manages retention of conversation dossier files (.md) and their associated
task list databases (.tasks.db) in ~/.config/bureau/dossiers/.

# Design rationale:
# Dossiers are paired files: a markdown snapshot and a SQLite task DB.
# Both must be cleaned up together -- orphaned task DBs or headless
# markdown files are both invalid states.
# Retention is based on the dossier's 'updated' frontmatter timestamp,
# not filesystem mtime, to respect logical activity over file access.
"""
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import CleanupHandler, CleanupError
from ..trash import get_trash_dir, move_to_trash, write_manifest
from ...config_loader import get_trash_grace_period


# Dossiers live in a flat directory under ~/.config/bureau/dossiers/
DOSSIERS_DIR = Path(os.path.expanduser("~/.config/bureau/dossiers"))

# Regex to extract YAML frontmatter block delimited by ---
_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---", re.DOTALL)
# Regex to find the 'updated:' line within frontmatter
_UPDATED_RE = re.compile(r"^updated:\s*(.+)$", re.MULTILINE)


class DossiersHandler(CleanupHandler):
    """Cleanup handler for Bureau dossiers (.md + .tasks.db pairs)."""

    name = "dossiers"

    @staticmethod
    def _parse_updated(md_path: Path) -> datetime | None:
        """Extract the 'updated' timestamp from YAML frontmatter.

        Returns None if the file has no frontmatter or no 'updated' field.
        """
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
            # Ensure timezone-aware (assume UTC for naive timestamps)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    @staticmethod
    def _companion_files(md_path: Path) -> list[Path]:
        """Return all companion files for a dossier markdown file.

        For a dossier `slug.md`, companions are:
          - slug.tasks.db
          - slug.tasks.db-wal   (SQLite WAL sidecar)
          - slug.tasks.db-shm   (SQLite shared-memory sidecar)

        Only paths that actually exist on disk are returned.
        """
        slug = md_path.stem  # e.g. "my-dossier" from "my-dossier.md"
        parent = md_path.parent
        candidates = [
            parent / f"{slug}.tasks.db",
            parent / f"{slug}.tasks.db-wal",
            parent / f"{slug}.tasks.db-shm",
        ]
        return [p for p in candidates if p.exists()]

    def get_stale_items(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Find dossiers whose 'updated' frontmatter timestamp is older than cutoff.

        Each returned item includes the markdown path and all companion file paths.

        Raises:
            CleanupError: On file system errors.
        """
        try:
            items: list[dict[str, Any]] = []

            if not DOSSIERS_DIR.exists():
                return items

            for md_file in DOSSIERS_DIR.glob("*.md"):
                updated = self._parse_updated(md_file)
                if updated is None:
                    # Cannot determine age; skip rather than risk deleting active dossier
                    continue

                if updated < cutoff:
                    companions = self._companion_files(md_file)
                    all_files = [md_file] + companions
                    total_size = sum(f.stat().st_size for f in all_files)

                    items.append({
                        "path": md_file,
                        "companions": companions,
                        "all_files": all_files,
                        "updated": updated,
                        "size": total_size,
                    })

            return items
        except OSError as e:
            raise CleanupError(f"Failed to scan dossiers: {e}") from e

    def export_items_to_trash(self, items: list[dict[str, Any]], retention: str) -> str:
        """Move all dossier files (md, task DB, WAL, SHM) to trash.

        Raises:
            CleanupError: On file system errors.
        """
        try:
            trash_dir = get_trash_dir(self.name)
            moved_files: list[Path] = []

            for item in items:
                for file_path in item["all_files"]:
                    if file_path.exists():
                        dest = move_to_trash(file_path, self.name)
                        moved_files.append(dest)

            write_manifest(trash_dir, self.name, len(items), retention,
                           get_trash_grace_period(),
                           files=moved_files)

            return str(trash_dir)
        except OSError as e:
            raise CleanupError(f"Failed to move dossier files to trash: {e}") from e

    def delete_items_from_storage(self, items: list[dict[str, Any]]) -> int:
        """Files already moved by export_items_to_trash, just return count."""
        # Files are moved (not copied) by export_items_to_trash
        return len(items)

    def _wipe(self, backup: bool) -> dict[str, Any]:
        """Completely erase all dossier files.

        Raises:
            CleanupError: On file system errors.
        """
        try:
            items: list[dict[str, Any]] = []

            if not DOSSIERS_DIR.exists():
                return {"storage": self.name, "wiped": 0, "message": "no dossier files found"}

            for md_file in DOSSIERS_DIR.glob("*.md"):
                companions = self._companion_files(md_file)
                all_files = [md_file] + companions
                total_size = sum(f.stat().st_size for f in all_files)
                updated = self._parse_updated(md_file)

                items.append({
                    "path": md_file,
                    "companions": companions,
                    "all_files": all_files,
                    "updated": updated,
                    "size": total_size,
                })

            if not items:
                return {"storage": self.name, "wiped": 0, "message": "no dossier files found"}

            # back up if requested, then delete (files moved via export_items_to_trash)
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
