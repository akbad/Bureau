"""Trash management for Bureau cleanup."""
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ..config_loader import parse_duration, get_trash_dir as get_base_trash_dir
from .state import now_as_iso

logger = logging.getLogger(__name__)

BASE_TRASH_DIR = get_base_trash_dir()

# ──────────────────────────────────────────────────────────────────────────────
# Manifest path contract
#
# A manifest lives inside the storage directory it describes, so it records
# each trashed file as a path RELATIVE to that directory. An absolute path
# would re-encode the directory's own location, which breaks the moment the
# tree moves: a worktree reorg, a renamed home, or a restore into a different
# checkout all leave the manifest pointing at a location that no longer exists.
#
# Two invariants hold the purge honest:
#   1. A path that cannot be resolved to an existing file deletes nothing and
#      is reported, never assumed already-gone.
#   2. The storage directory is removed only once it is genuinely empty, never
#      inferred from the manifest having no surviving entries. Those are not
#      the same fact, and conflating them destroys files no entry ever listed.
#
# Rejected: resolving stale paths by bare filename. It ignores the project
# subdirectories that Serena memories rely on and can match a same-named file
# belonging to a different project.
# ──────────────────────────────────────────────────────────────────────────────

MANIFEST_FILENAME = ".manifest.json"


def get_trash_dir(backend_name: str) -> Path:
    """
        Find trash directory for a specific memory backend.
        Trash directories are defined per backend: .archives/trash/<backend-name>
    """
    trash_path = BASE_TRASH_DIR / backend_name
    trash_path.mkdir(parents=True, exist_ok=True)
    return trash_path


def generate_trash_filename(item_count: int, extension: str = "json") -> str:
    """Generate a timestamped trash filename."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return f"{timestamp}_{item_count}-items.{extension}"


def relativize_to_storage(path: Path, storage_dir: Path) -> str:
    """Express a trashed file's location for storage in the manifest.

    Args:
        `path`: location of the trashed file, normally under `storage_dir`.
        `storage_dir`: the backend's trash directory, which holds the manifest.

    Returns:
        The path relative to `storage_dir`, or the original path unchanged
        when it lies outside — a caller bug that `resolve_manifest_path`
        reports at read time rather than silently mislocating here.
    """
    try:
        return str(path.relative_to(storage_dir))
    except ValueError:
        return str(path)


def resolve_manifest_path(stored: str, storage_dir: Path) -> Optional[Path]:
    """Locate a manifest-recorded file in the storage dir as it exists now.

    Handles three recorded forms:

    1. Relative (the current contract) — joined onto `storage_dir`.
    2. Absolute and still under `storage_dir` — used as-is.
    3. Absolute from a since-moved tree (legacy entries) — re-anchored by
       splicing the segment after the last `storage_dir.name` component onto
       the current `storage_dir`, which preserves any project subdirectory.

    Args:
        `stored`: the path string exactly as recorded in the manifest.
        `storage_dir`: the backend's trash directory at its current location.

    Returns:
        The resolved path, or `None` when no existing file corresponds to the
        entry. `None` means "unaccounted for", never "already deleted".
    """
    candidate = Path(stored)

    if not candidate.is_absolute():
        resolved = storage_dir / candidate
        return resolved if resolved.exists() else None

    try:
        candidate.relative_to(storage_dir)
        return candidate if candidate.exists() else None
    except ValueError:
        pass

    # re-anchor a path recorded before the trash tree moved
    parts = candidate.parts
    anchor = storage_dir.name
    if anchor not in parts:
        return None
    suffix = parts[len(parts) - 1 - parts[::-1].index(anchor) + 1:]
    if not suffix:
        return None
    resolved = storage_dir.joinpath(*suffix)
    return resolved if resolved.exists() else None


def write_manifest(trash_path: Path, storage_name: str, item_count: int,
                   retention: str, grace_period: str = "30d",
                   files: list[Path] | None = None) -> None:
    """Write manifest file for trashed items."""
    now = now_as_iso()
    grace_delta = parse_duration(grace_period)
    purge_after = datetime.now(timezone.utc) + grace_delta

    manifest = {
        "trashed_at": now,
        "source": storage_name,
        "item_count": item_count,
        "original_retention": retention,
        # isoformat() already carries the +00:00 offset; appending "Z" as well
        # produced a value no ISO parser accepts, which is how the field went
        # unnoticed for as long as nothing read it
        "auto_purge_after": purge_after.isoformat(),
        "files": [relativize_to_storage(f, trash_path) for f in files] if files else [],
    }

    manifest_path = trash_path / MANIFEST_FILENAME

    # append to existing manifest or create new
    existing = []
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = [existing]
        except (json.JSONDecodeError, IOError):
            existing = []

    existing.append(manifest)

    with open(manifest_path, "w") as f:
        json.dump(existing, f, indent=2)


def move_to_trash(source_path: Path, 
                  storage_name: str,
                  project_name: Optional[str] = None  # for memories from Serena
                 ) -> Path:
    """Move an *existing* file/dir to trash (preserving Serena files' structure)."""
    trash_base = get_trash_dir(storage_name)

    if project_name:
        # the file belongs to a Serena project
        trash_dest = trash_base / project_name / source_path.name
        trash_dest.parent.mkdir(parents=True, exist_ok=True)
    else:
        trash_dest = trash_base / source_path.name

    shutil.move(str(source_path), str(trash_dest))
    return trash_dest


def _as_utc(raw: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp from a manifest, assuming UTC if naive.

    Args:
        `raw`: the timestamp string as recorded.

    Returns:
        A timezone-aware datetime, or `None` if `raw` is absent or malformed.
        Historical entries carry an unparseable `+00:00Z` double suffix and
        land here as `None`, which callers treat as "fall back", not "expired".
    """
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def entry_due_at(entry: dict[str, Any], grace_delta: timedelta) -> Optional[datetime]:
    """Determine when a manifest entry becomes eligible for purging.

    The entry's own `auto_purge_after` wins when present and parseable: it is
    the promise made when the items were trashed, and honouring it keeps a
    later change to the grace period from retroactively re-dating items
    already in the trash. `trashed_at` plus the current grace period is the
    fallback for entries written before the field, or with a malformed one.

    Args:
        `entry`: one manifest record.
        `grace_delta`: the currently configured grace period.

    Returns:
        The purge-eligible instant, or `None` when neither timestamp can be
        read — in which case the entry is left alone rather than guessed at.
    """
    recorded = _as_utc(entry.get("auto_purge_after", ""))
    if recorded is not None:
        return recorded

    trashed_at = _as_utc(entry.get("trashed_at", ""))
    return trashed_at + grace_delta if trashed_at is not None else None


def empty_expired_trash(grace_period: str) -> int:
    """Remove items in the trash that are past their purge date,
        returning the count of items removed."""
    if not BASE_TRASH_DIR.exists():
        return 0

    grace_delta = parse_duration(grace_period)
    removed_count = 0

    now = datetime.now(timezone.utc)

    for storage_dir in BASE_TRASH_DIR.iterdir():
        if not storage_dir.is_dir():
            continue

        manifest_path = storage_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            continue

        try:
            with open(manifest_path) as f:
                manifests = json.load(f)
                if not isinstance(manifests, list):
                    manifests = [manifests]
        except (json.JSONDecodeError, IOError):
            continue

        remaining = []
        for entry in manifests:
            # check each trash entry for expiration
            recorded_files = entry.get("files", [])
            due_at = entry_due_at(entry, grace_delta)
            # an entry whose dates are unreadable is never purged: the only
            # safe reading of "we cannot tell when this expires" is "not yet"
            expired = due_at is not None and due_at < now

            if expired:
                if not recorded_files:
                    # an entry that names nothing authorizes nothing. the former
                    # fallback swept the storage dir by content mtime, which is
                    # neither the right clock (shutil.move preserves it, so a
                    # long-written file arrives already "stale") nor the right
                    # scope (it ranged over files belonging to other, unexpired
                    # entries). no record of ownership means no deletion.
                    logger.warning(
                        "trash manifest entry is past due but lists no files; "
                        "nothing deleted (trashed_at=%s, storage_dir=%s)",
                        entry.get("trashed_at", "<unknown>"), storage_dir,
                    )
                for stored in recorded_files:
                    full_path = resolve_manifest_path(stored, storage_dir)
                    if full_path is None:
                        # report rather than assume: an entry we cannot resolve
                        # has not been verified gone, and treating it as gone
                        # is what lets the directory be removed out from under
                        # files that are still present
                        logger.warning(
                            "trash manifest entry could not be resolved; "
                            "nothing deleted for it: %s (storage_dir=%s)",
                            stored, storage_dir,
                        )
                        continue
                    try:
                        if full_path.is_file():
                            full_path.unlink()
                            removed_count += 1
                        elif full_path.is_dir():
                            shutil.rmtree(full_path)
                    except FileNotFoundError:
                        pass  # Already deleted, continue
            else:
                remaining.append(entry)

        # an exhausted manifest is not evidence of an empty directory; ask the
        # filesystem instead, so files no entry listed are never collateral
        leftovers = [p for p in storage_dir.iterdir() if p.name != MANIFEST_FILENAME]

        if not remaining and not leftovers:
            # nothing tracked and nothing on disk: retire the directory
            shutil.rmtree(storage_dir)
            continue

        if not remaining:
            logger.warning(
                "trash storage dir retained: every manifest entry expired but "
                "%d file(s) remain unaccounted for in %s",
                len(leftovers), storage_dir,
            )

        with open(manifest_path, "w") as f:
            json.dump(remaining, f, indent=2)

    return removed_count


def empty_all_trash() -> dict:
    """Immediately empty *all* trash, overriding the default grace period."""
    if not BASE_TRASH_DIR.exists():
        return {"emptied": 0, "message": "Trash directory does not exist"}

    # count items to be permanently deleted (excluding directories & manifest files)
    count = 0
    for storage_dir in BASE_TRASH_DIR.iterdir():
        if storage_dir.is_dir():
            for item in storage_dir.rglob("*"):
                if item.is_file() and item.name != ".manifest.json":
                    count += 1
            shutil.rmtree(storage_dir)

    return {"emptied": count, "message": "All trash emptied"}
