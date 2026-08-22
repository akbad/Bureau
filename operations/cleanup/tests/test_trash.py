"""Tests for trash management (soft-delete with grace period)."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


from operations.cleanup.trash import (
    empty_expired_trash,
    empty_all_trash,
    generate_trash_filename,
    get_trash_dir,
    move_to_trash,
    write_manifest,
)


class TestGetTrashDir:
    """Tests for get_trash_dir()."""

    def test_creates_directory_if_missing(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Creates trash directory if it doesn't exist."""
        trash_base = tmp_path / ".archives" / "trash"
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        result = get_trash_dir("claude_mem")

        assert result.exists()
        assert result.name == "claude_mem"
        assert result.parent == trash_base

    def test_returns_existing_directory(
        self,
        trash_dir: Path,
        monkeypatch,
    ):
        """Returns existing directory without error."""
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_dir
        )

        backend_dir = trash_dir / "qdrant"
        backend_dir.mkdir()

        result = get_trash_dir("qdrant")
        assert result == backend_dir


class TestGenerateTrashFilename:
    """Tests for generate_trash_filename()."""

    def test_format_with_timestamp(self):
        """Generates timestamped filename with item count."""
        filename = generate_trash_filename(42)

        # format: YYYY-MM-DDTHH-MM-SS_42-items.json
        assert "_42-items.json" in filename
        assert filename.startswith("20")  # year starts with 20xx

    def test_custom_extension(self):
        """Supports custom file extension."""
        filename = generate_trash_filename(10, extension="jsonl")
        assert filename.endswith("_10-items.jsonl")


class TestWriteManifest:
    """Tests for write_manifest()."""

    def test_creates_new_manifest(
        self,
        tmp_path: Path,
    ):
        """Creates new manifest file if none exists."""
        trash_path = tmp_path / "backend"
        trash_path.mkdir()

        write_manifest(
            trash_path=trash_path,
            storage_name="claude_mem",
            item_count=5,
            retention="30d",
            grace_period="7d",
            files=[Path("/fake/file1.db"), Path("/fake/file2.db")],
        )

        # verify manifest was created with expected structure
        manifest_path = trash_path / ".manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["source"] == "claude_mem"
        assert data[0]["item_count"] == 5
        assert data[0]["original_retention"] == "30d"
        assert "auto_purge_after" in data[0]
        assert len(data[0]["files"]) == 2

    def test_appends_to_existing_manifest(
        self,
        tmp_path: Path,
    ):
        """Appends to existing manifest rather than overwriting."""
        trash_path = tmp_path / "backend"
        trash_path.mkdir()

        # add first entry
        write_manifest(trash_path, "claude_mem", 3, "30d")

        # add second entry
        write_manifest(trash_path, "qdrant", 10, "90d")

        manifest_path = trash_path / ".manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["source"] == "claude_mem"
        assert data[1]["source"] == "qdrant"

    def test_converts_legacy_single_object(
        self,
        tmp_path: Path,
    ):
        """Converts legacy single-object manifest to list format."""
        trash_path = tmp_path / "backend"
        trash_path.mkdir()

        # write legacy format (single object, not list)
        manifest_path = trash_path / ".manifest.json"
        legacy = {
            "trashed_at": "2024-01-01T00:00:00+00:00",
            "source": "legacy",
            "item_count": 1,
            "files": [],
        }
        with open(manifest_path, "w") as f:
            json.dump(legacy, f)

        # append new entry
        write_manifest(trash_path, "new_backend", 5, "30d")

        with open(manifest_path) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["source"] == "legacy"
        assert data[1]["source"] == "new_backend"

    def test_handles_corrupt_manifest(
        self,
        tmp_path: Path,
    ):
        """Handles corrupt manifest gracefully by starting fresh."""
        trash_path = tmp_path / "backend"
        trash_path.mkdir()

        # write corrupt JSON
        manifest_path = trash_path / ".manifest.json"
        manifest_path.write_text("not valid json {{{")

        # starts fresh without raising
        write_manifest(trash_path, "backend", 1, "30d")

        with open(manifest_path) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["source"] == "backend"


class TestMoveToTrash:
    """Tests for move_to_trash()."""

    def test_moves_file_to_trash(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """File is moved (not copied) to trash directory."""
        trash_base = tmp_path / ".archives" / "trash"
        trash_base.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create source file
        source = tmp_path / "source" / "file.db"
        source.parent.mkdir()
        source.write_text("content")

        result = move_to_trash(source, "claude_mem")

        assert not source.exists()  # original moved
        assert result.exists()  # new location exists
        assert result.read_text() == "content"

    def test_moves_with_project_name(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Creates project subdirectory for Serena memories."""
        trash_base = tmp_path / ".archives" / "trash"
        trash_base.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create source file
        source = tmp_path / "memories" / "memory.md"
        source.parent.mkdir()
        source.write_text("# Memory")

        result = move_to_trash(source, "serena", project_name="my_project")

        assert result.parent.name == "my_project"
        assert result.name == "memory.md"


class TestEmptyExpiredTrash:
    """Tests for empty_expired_trash()."""

    def test_deletes_expired_items(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Files older than grace period are deleted."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create old file
        old_file = storage_dir / "old.json"
        old_file.write_text("{}")

        # create manifest with old entry
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        manifest = [{
            "trashed_at": old_time,
            "source": "backend",
            "item_count": 1,
            "files": [str(old_file)],
        }]
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        removed = empty_expired_trash("30d")

        assert removed == 1
        assert not old_file.exists()

    def test_preserves_non_expired_items(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Files newer than grace period are preserved."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create new file
        new_file = storage_dir / "new.json"
        new_file.write_text("{}")

        # create manifest with recent entry
        recent_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        manifest = [{
            "trashed_at": recent_time,
            "source": "backend",
            "item_count": 1,
            "files": [str(new_file)],
        }]
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        removed = empty_expired_trash("30d")

        assert removed == 0
        assert new_file.exists()

    def test_handles_missing_trash_dir(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Returns 0 when trash directory doesn't exist."""
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            tmp_path / "nonexistent"
        )

        removed = empty_expired_trash("30d")
        assert removed == 0

    def test_skips_corrupt_manifest(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Skips storage directories with corrupt manifests."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # write corrupt manifest
        (storage_dir / ".manifest.json").write_text("not json")
        (storage_dir / "file.json").write_text("{}")

        removed = empty_expired_trash("30d")

        # skips this directory without crashing
        assert removed == 0

    # note: TOCTOU = Time-Of-Check-To-Time-Of-Use race condition
    def test_toctou_file_not_found(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Regression test: handles FileNotFoundError (Issue TOCTOU race)."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create manifest referencing non-existent file
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        manifest = [{
            "trashed_at": old_time,
            "source": "backend",
            "item_count": 1,
            "files": [str(storage_dir / "already_deleted.json")],
        }]
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        # continues without raising
        removed = empty_expired_trash("30d")
        assert removed == 0

    def test_entry_without_files_list_deletes_nothing(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """An entry that names no files authorizes no deletions.

        Replaces an mtime-based fallback that guessed ownership from content
        modification time. `shutil.move` preserves mtime, so the guess was
        wrong on arrival, and it ranged over the whole storage dir rather
        than the entry, letting one entry delete another's unexpired files.
        """
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        old_file = storage_dir / "old.json"
        old_file.write_text("{}")
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=60)).timestamp()
        # note: os.utime takes (atime, mtime) tuple; we set both to same value
        os.utime(old_file, (old_timestamp, old_timestamp))

        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        manifest = [{
            "trashed_at": old_time,
            "source": "backend",
            "item_count": 1,
            "files": [],
        }]
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        removed = empty_expired_trash("30d")

        assert removed == 0
        assert old_file.exists()

    def test_entry_without_files_list_spares_another_entrys_files(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """One entry's missing file list cannot purge a live entry's files."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # trashed moments ago, but written long ago: mtime is not the clock
        recent_file = storage_dir / "recently_trashed.db"
        recent_file.write_text("{}")
        stale_mtime = (datetime.now(timezone.utc) - timedelta(days=365)).timestamp()
        os.utime(recent_file, (stale_mtime, stale_mtime))

        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        now_time = datetime.now(timezone.utc).isoformat()
        (storage_dir / ".manifest.json").write_text(json.dumps([
            {"trashed_at": old_time, "files": []},
            {"trashed_at": now_time, "files": ["recently_trashed.db"]},
        ]))

        empty_expired_trash("30d")

        assert recent_file.exists()

    def test_removes_empty_storage_dir(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Removes storage directory when all entries are purged."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create old file
        old_file = storage_dir / "old.json"
        old_file.write_text("{}")

        # create manifest with single old entry
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        manifest = [{
            "trashed_at": old_time,
            "source": "backend",
            "item_count": 1,
            "files": [str(old_file)],
        }]
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        empty_expired_trash("30d")

        # entire storage directory should be removed
        assert not storage_dir.exists()

    def test_preserves_storage_dir_with_remaining_entries(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Preserves storage directory when some entries remain."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create files
        old_file = storage_dir / "old.json"
        old_file.write_text("{}")
        new_file = storage_dir / "new.json"
        new_file.write_text("{}")

        # create manifest with mixed entries
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        new_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        manifest = [
            {
                "trashed_at": old_time,
                "source": "backend",
                "item_count": 1,
                "files": [str(old_file)],
            },
            {
                "trashed_at": new_time,
                "source": "backend",
                "item_count": 1,
                "files": [str(new_file)],
            },
        ]
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        empty_expired_trash("30d")

        # storage directory should remain with new file
        assert storage_dir.exists()
        assert new_file.exists()
        assert not old_file.exists()

        # manifest should be updated
        with open(storage_dir / ".manifest.json") as f:
            remaining = json.load(f)
        assert len(remaining) == 1

    def test_handles_legacy_single_object_manifest(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Handles legacy single-object manifest format."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        old_file = storage_dir / "old.json"
        old_file.write_text("{}")

        # legacy single object (not list)
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        manifest = {
            "trashed_at": old_time,
            "source": "backend",
            "item_count": 1,
            "files": [str(old_file)],
        }
        (storage_dir / ".manifest.json").write_text(json.dumps(manifest))

        removed = empty_expired_trash("30d")

        assert removed == 1


class TestEmptyAllTrash:
    """Tests for empty_all_trash()."""

    def test_empties_all_items(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Deletes all trash items regardless of age."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        # create multiple files
        (storage_dir / "file1.json").write_text("{}")
        (storage_dir / "file2.json").write_text("{}")
        (storage_dir / ".manifest.json").write_text("[]")

        result = empty_all_trash()

        assert result["emptied"] == 2  # excludes .manifest.json
        assert not storage_dir.exists()

    def test_handles_missing_trash_dir(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Returns appropriate message when trash doesn't exist."""
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            tmp_path / "nonexistent"
        )

        result = empty_all_trash()

        assert result["emptied"] == 0
        assert "does not exist" in result["message"]


class TestManifestPathsAreRelocatable:
    """Manifest paths must survive the trash directory moving on disk.

    The manifest lives inside the directory it describes, so an absolute
    path in it re-encodes that directory's location and breaks the moment
    the tree is relocated (a worktree reorg, a renamed home, a restore
    into a different checkout).
    """

    def test_write_manifest_stores_paths_relative_to_storage_dir(
        self,
        tmp_path: Path,
    ):
        """Recorded paths carry no absolute prefix."""
        storage_dir = tmp_path / ".archives" / "trash" / "backend"
        storage_dir.mkdir(parents=True)
        trashed = storage_dir / "a.db"
        trashed.write_text("{}")

        write_manifest(storage_dir, "backend", 1, "30d", "30d", files=[trashed])

        entry = json.loads((storage_dir / ".manifest.json").read_text())[0]
        assert entry["files"] == ["a.db"]

    def test_write_manifest_keeps_subdirectory_structure(
        self,
        tmp_path: Path,
    ):
        """Serena-style project subdirectories survive relativization."""
        storage_dir = tmp_path / ".archives" / "trash" / "serena"
        nested = storage_dir / "proj"
        nested.mkdir(parents=True)
        trashed = nested / "mem.md"
        trashed.write_text("x")

        write_manifest(storage_dir, "serena", 1, "30d", "30d", files=[trashed])

        entry = json.loads((storage_dir / ".manifest.json").read_text())[0]
        assert entry["files"] == [str(Path("proj") / "mem.md")]

    def test_expiry_deletes_files_recorded_relatively(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """A relative entry resolves against the storage dir at read time."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        old_file = storage_dir / "old.json"
        old_file.write_text("{}")
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": old_time,
            "files": ["old.json"],
        }]))

        removed = empty_expired_trash("30d")

        assert removed == 1
        assert not old_file.exists()

    def test_expiry_reanchors_legacy_absolute_path_from_another_checkout(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """A pre-existing absolute path from a moved tree still resolves."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "dossiers"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        old_file = storage_dir / "old.db"
        old_file.write_text("{}")
        # the path as it was recorded before the worktree moved
        stale = "/somewhere/else/entirely/.archives/trash/dossiers/old.db"
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": old_time,
            "files": [stale],
        }]))

        removed = empty_expired_trash("30d")

        assert removed == 1
        assert not old_file.exists()


class TestStorageDirRemovalIsAccountedFor:
    """The storage dir may only be removed once it is genuinely empty.

    An empty `remaining` list means every manifest entry expired, not that
    every file was accounted for. Treating the two as equivalent destroys
    files no entry ever listed.
    """

    def test_preserves_files_no_manifest_entry_listed(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Untracked files outlive the purge of every tracked entry."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        tracked = storage_dir / "tracked.db"
        tracked.write_text("{}")
        untracked = storage_dir / "untracked.db"
        untracked.write_text("{}")

        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": old_time,
            "files": ["tracked.db"],
        }]))

        removed = empty_expired_trash("30d")

        assert removed == 1
        assert not tracked.exists()
        assert untracked.exists(), "a file no entry listed was destroyed"

    def test_empty_manifest_does_not_purge_the_directory(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """A manifest with zero entries authorizes zero deletions."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        precious = storage_dir / "precious.db"
        precious.write_text("{}")
        (storage_dir / ".manifest.json").write_text(json.dumps([]))

        removed = empty_expired_trash("30d")

        assert removed == 0
        assert precious.exists(), "an empty manifest purged the directory"

    def test_unresolvable_entry_does_not_authorize_removal(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """A path that resolves to nothing must not take the dir with it."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        bystander = storage_dir / "bystander.db"
        bystander.write_text("{}")
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": old_time,
            "files": ["gone-without-trace.db"],
        }]))

        empty_expired_trash("30d")

        assert bystander.exists()

    def test_removes_storage_dir_once_truly_empty(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """The happy path still cleans up after itself."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        only_file = storage_dir / "only.db"
        only_file.write_text("{}")
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": old_time,
            "files": ["only.db"],
        }]))

        empty_expired_trash("30d")

        assert not storage_dir.exists()


class TestPurgeDateIsHonoured:
    """The recorded purge date is the contract, not a decoration.

    `auto_purge_after` was written and never read, so expiry was recomputed
    from the grace period in force at purge time. Shortening that period
    retroactively re-dated everything already in the trash.
    """

    def test_write_manifest_records_a_parseable_purge_date(
        self,
        tmp_path: Path,
    ):
        """The stored timestamp round-trips through fromisoformat."""
        storage_dir = tmp_path / "backend"
        storage_dir.mkdir(parents=True)

        write_manifest(storage_dir, "backend", 0, "30d", "30d", files=[])

        entry = json.loads((storage_dir / ".manifest.json").read_text())[0]
        parsed = datetime.fromisoformat(entry["auto_purge_after"])
        assert parsed.tzinfo is not None

    def test_entry_not_yet_due_survives_a_shortened_grace_period(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Shrinking the grace config cannot retroactively expire an entry."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        protected = storage_dir / "promised-90d.db"
        protected.write_text("{}")
        trashed = datetime.now(timezone.utc) - timedelta(days=60)
        due = trashed + timedelta(days=90)
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": trashed.isoformat(),
            "auto_purge_after": due.isoformat(),
            "files": ["promised-90d.db"],
        }]))

        removed = empty_expired_trash("30d")

        assert removed == 0
        assert protected.exists()

    def test_entry_past_its_recorded_date_is_purged(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """A lengthened grace config cannot revive an already-due entry."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        due_file = storage_dir / "due.db"
        due_file.write_text("{}")
        trashed = datetime.now(timezone.utc) - timedelta(days=40)
        due = trashed + timedelta(days=30)
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": trashed.isoformat(),
            "auto_purge_after": due.isoformat(),
            "files": ["due.db"],
        }]))

        removed = empty_expired_trash("365d")

        assert removed == 1
        assert not due_file.exists()

    def test_falls_back_to_grace_period_when_date_is_absent(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Entries predating the field still expire on the configured grace."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        legacy = storage_dir / "legacy.db"
        legacy.write_text("{}")
        trashed = datetime.now(timezone.utc) - timedelta(days=60)
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": trashed.isoformat(),
            "files": ["legacy.db"],
        }]))

        removed = empty_expired_trash("30d")

        assert removed == 1
        assert not legacy.exists()

    def test_falls_back_when_recorded_date_is_malformed(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """The historical '+00:00Z' double suffix must not wedge the purge."""
        trash_base = tmp_path / ".archives" / "trash"
        storage_dir = trash_base / "backend"
        storage_dir.mkdir(parents=True)
        monkeypatch.setattr(
            "operations.cleanup.trash.BASE_TRASH_DIR",
            trash_base
        )

        legacy = storage_dir / "legacy.db"
        legacy.write_text("{}")
        trashed = datetime.now(timezone.utc) - timedelta(days=60)
        (storage_dir / ".manifest.json").write_text(json.dumps([{
            "trashed_at": trashed.isoformat(),
            "auto_purge_after": trashed.isoformat() + "Z",
            "files": ["legacy.db"],
        }]))

        removed = empty_expired_trash("30d")

        assert removed == 1
        assert not legacy.exists()
