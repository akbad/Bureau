"""Tests for Neo4jMemoryHandler (Neo4j graph memory cleanup)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from operations.cleanup.handlers.neo4j_memory import Neo4jMemoryHandler


# =============================================================================
# MOCK HELPERS
# =============================================================================


def create_mock_record(data: dict) -> MagicMock:
    """Create a mock Neo4j record that supports dict-style access."""
    record = MagicMock()
    record.__getitem__ = lambda self, key: data.get(key)
    return record


def create_mock_session(query_results: list[dict] = None, delete_count: int = 0):
    """Create a mock Neo4j session with configurable query results.

    Args:
        query_results: List of dicts representing Memory node records.
        delete_count: Count to return for DELETE queries.

    Returns:
        Mock session that can be used as context manager.
    """
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    def mock_run(query, **kwargs):
        mock_result = MagicMock()

        if "DETACH DELETE" in query or "DELETE" in query:
            # Delete query - return count
            delete_record = create_mock_record({"deleted": delete_count})
            mock_result.single.return_value = delete_record
            mock_result.__iter__ = lambda self: iter([])
        elif query_results is not None:
            # Select query - return records
            records = [create_mock_record(r) for r in query_results]
            mock_result.__iter__ = lambda self: iter(records)
            mock_result.single.return_value = None
        else:
            mock_result.__iter__ = lambda self: iter([])
            mock_result.single.return_value = None

        return mock_result

    mock_session.run = mock_run
    return mock_session


def create_mock_driver(session: MagicMock = None):
    """Create a mock Neo4j driver.

    Args:
        session: Optional mock session to return. If None, creates empty session.

    Returns:
        Mock driver with session() method.
    """
    mock_driver = MagicMock()
    mock_driver.session.return_value = session or create_mock_session()
    mock_driver.close = MagicMock()
    return mock_driver


# =============================================================================
# TEST: get_stale_items()
# =============================================================================


class TestNeo4jGetStaleItems:
    """Tests for Neo4jMemoryHandler.get_stale_items()."""

    def test_finds_stale_items(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
        stale_datetime: datetime,
        valid_datetime: datetime,
    ):
        """Correctly identifies items older than cutoff."""
        stale_ts = stale_datetime.isoformat()
        valid_ts = valid_datetime.isoformat()

        query_results = [
            {
                "name": "stale_entity",
                "entityType": "Concept",
                "created_at": stale_ts,
                "observations": ["observation 1"],
            },
        ]

        mock_session = create_mock_session(query_results=query_results)
        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            items = handler.get_stale_items(cutoff_datetime)
            handler.close()

        assert len(items) == 1
        assert items[0]["name"] == "stale_entity"
        assert items[0]["entityType"] == "Concept"

    def test_empty_database_returns_empty_list(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
    ):
        """Empty database returns empty list."""
        mock_session = create_mock_session(query_results=[])
        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            items = handler.get_stale_items(cutoff_datetime)
            handler.close()

        assert items == []

    def test_connection_error_returns_empty_list(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
    ):
        """Connection errors are handled gracefully."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run.side_effect = Exception("Connection refused")

        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            items = handler.get_stale_items(cutoff_datetime)
            handler.close()

        # Returns empty list on error, not crash
        assert items == []

    def test_multiple_stale_items(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
        stale_datetime: datetime,
    ):
        """Correctly retrieves multiple stale items."""
        stale_ts = stale_datetime.isoformat()

        query_results = [
            {"name": f"entity_{i}", "entityType": "Concept", "created_at": stale_ts, "observations": []}
            for i in range(5)
        ]

        mock_session = create_mock_session(query_results=query_results)
        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            items = handler.get_stale_items(cutoff_datetime)
            handler.close()

        assert len(items) == 5
        assert all(item["name"].startswith("entity_") for item in items)

    def test_preserves_observations(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
        stale_datetime: datetime,
    ):
        """Observations are preserved in returned items."""
        stale_ts = stale_datetime.isoformat()
        observations = ["fact 1", "fact 2", "fact 3"]

        query_results = [
            {
                "name": "entity_with_observations",
                "entityType": "Person",
                "created_at": stale_ts,
                "observations": observations,
            },
        ]

        mock_session = create_mock_session(query_results=query_results)
        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            items = handler.get_stale_items(cutoff_datetime)
            handler.close()

        assert items[0]["observations"] == observations


# =============================================================================
# TEST: delete_items_from_storage()
# =============================================================================


class TestNeo4jDeleteItems:
    """Tests for Neo4jMemoryHandler.delete_items_from_storage()."""

    def test_delete_sends_correct_names(
        self,
        apply_mock_patches: dict,
    ):
        """Delete query includes correct entity names."""
        items = [
            {"name": "entity_1", "entityType": "Concept", "created_at": "2024-01-01", "observations": []},
            {"name": "entity_2", "entityType": "Person", "created_at": "2024-01-01", "observations": []},
        ]

        mock_session = create_mock_session(delete_count=2)
        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            deleted = handler.delete_items_from_storage(items)
            handler.close()

        assert deleted == 2

    def test_delete_empty_list_returns_zero(
        self,
        apply_mock_patches: dict,
    ):
        """Deleting empty list returns 0 without query."""
        handler = Neo4jMemoryHandler()
        deleted = handler.delete_items_from_storage([])

        assert deleted == 0

    def test_delete_error_returns_zero(
        self,
        apply_mock_patches: dict,
    ):
        """Database error during delete returns 0."""
        items = [{"name": "entity_1", "entityType": "Concept", "created_at": "2024-01-01", "observations": []}]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run.side_effect = Exception("Database error")

        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            deleted = handler.delete_items_from_storage(items)
            handler.close()

        assert deleted == 0

    def test_delete_uses_detach_delete(
        self,
        apply_mock_patches: dict,
    ):
        """Delete uses DETACH DELETE to remove relationships."""
        items = [{"name": "entity_1", "entityType": "Concept", "created_at": "2024-01-01", "observations": []}]

        captured_query = None

        def capture_query(query, **kwargs):
            nonlocal captured_query
            captured_query = query
            mock_result = MagicMock()
            mock_result.single.return_value = create_mock_record({"deleted": 1})
            return mock_result

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = capture_query

        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            handler.delete_items_from_storage(items)
            handler.close()

        assert "DETACH DELETE" in captured_query


# =============================================================================
# TEST: export_items_to_trash()
# =============================================================================


class TestNeo4jExportToTrash:
    """Tests for Neo4jMemoryHandler.export_items_to_trash()."""

    def test_exports_to_jsonl(
        self,
        apply_mock_patches: dict,
        tmp_path: Path,
    ):
        """Items are exported as JSONL."""
        items = [
            {"name": "entity_1", "entityType": "Concept", "created_at": "2024-01-01", "observations": ["obs1"]},
            {"name": "entity_2", "entityType": "Person", "created_at": "2024-01-02", "observations": ["obs2"]},
        ]

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = create_mock_driver()

            handler = Neo4jMemoryHandler()
            trash_path = handler.export_items_to_trash(items, "30d")

        # Verify file was created
        assert Path(trash_path).exists()

        # Verify content is valid JSONL
        with open(trash_path) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Parse and verify content
        exported_items = [json.loads(line) for line in lines]
        assert exported_items[0]["name"] == "entity_1"
        assert exported_items[1]["name"] == "entity_2"

    def test_creates_manifest(
        self,
        apply_mock_patches: dict,
        tmp_path: Path,
    ):
        """Manifest file is created alongside export."""
        items = [
            {"name": "entity_1", "entityType": "Concept", "created_at": "2024-01-01", "observations": []},
        ]

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = create_mock_driver()

            handler = Neo4jMemoryHandler()
            trash_path = handler.export_items_to_trash(items, "30d")

        # Check manifest exists in same directory (hidden file with leading dot)
        trash_dir = Path(trash_path).parent
        manifest_path = trash_dir / ".manifest.json"
        assert manifest_path.exists()

        # Verify manifest content (manifest is a list of entries)
        with open(manifest_path) as f:
            manifest_list = json.load(f)

        assert len(manifest_list) == 1
        manifest = manifest_list[0]
        assert manifest["source"] == "neo4j-memory"
        assert manifest["item_count"] == 1


# =============================================================================
# TEST: wipe()
# =============================================================================


class TestNeo4jWipe:
    """Tests for Neo4jMemoryHandler.wipe()."""

    def test_wipe_deletes_all_nodes(
        self,
        apply_mock_patches: dict,
    ):
        """Wipe removes all Memory nodes."""
        # First query returns all items, second query deletes them
        all_items = [
            {"name": f"entity_{i}", "entityType": "Concept", "created_at": "2024-01-01", "observations": []}
            for i in range(3)
        ]

        call_count = [0]

        def multi_query_session():
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)

            def mock_run(query, **kwargs):
                call_count[0] += 1
                mock_result = MagicMock()

                if "DETACH DELETE" in query:
                    mock_result.single.return_value = create_mock_record({"deleted": 3})
                    mock_result.__iter__ = lambda self: iter([])
                else:
                    # Select query
                    records = [create_mock_record(r) for r in all_items]
                    mock_result.__iter__ = lambda self: iter(records)

                return mock_result

            mock_session.run = mock_run
            return mock_session

        mock_driver = MagicMock()
        mock_driver.session.return_value = multi_query_session()
        mock_driver.close = MagicMock()

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            result = handler.wipe(backup=True)
            handler.close()

        assert result["storage"] == "neo4j-memory"
        assert result["wiped"] == 3
        assert "backup_path" in result

    def test_wipe_empty_database(
        self,
        apply_mock_patches: dict,
    ):
        """Wipe on empty database returns appropriate message."""
        mock_session = create_mock_session(query_results=[])
        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            result = handler.wipe()
            handler.close()

        assert result["wiped"] == 0
        assert "no entities found" in result.get("message", "")

    def test_wipe_without_backup(
        self,
        apply_mock_patches: dict,
    ):
        """Wipe without backup skips export step."""
        all_items = [{"name": "entity_1", "entityType": "Concept", "created_at": "2024-01-01", "observations": []}]

        def multi_query_session():
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)

            def mock_run(query, **kwargs):
                mock_result = MagicMock()
                if "DETACH DELETE" in query:
                    mock_result.single.return_value = create_mock_record({"deleted": 1})
                    mock_result.__iter__ = lambda self: iter([])
                else:
                    records = [create_mock_record(r) for r in all_items]
                    mock_result.__iter__ = lambda self: iter(records)
                return mock_result

            mock_session.run = mock_run
            return mock_session

        mock_driver = MagicMock()
        mock_driver.session.return_value = multi_query_session()
        mock_driver.close = MagicMock()

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            result = handler.wipe(backup=False)
            handler.close()

        assert result["wiped"] == 1
        assert "backup_path" not in result

    def test_wipe_connection_error(
        self,
        apply_mock_patches: dict,
    ):
        """Wipe handles connection errors gracefully."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run.side_effect = Exception("Connection refused")

        mock_driver = create_mock_driver(session=mock_session)

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            result = handler.wipe()
            handler.close()

        assert result["wiped"] == 0
        assert "error" in result


# =============================================================================
# TEST: Driver management
# =============================================================================


class TestNeo4jDriverManagement:
    """Tests for Neo4j driver lifecycle management."""

    def test_driver_reused_across_calls(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
    ):
        """Driver is reused across multiple method calls."""
        mock_session = create_mock_session(query_results=[])
        mock_driver = create_mock_driver(session=mock_session)

        driver_call_count = [0]

        def count_driver_calls(*args, **kwargs):
            driver_call_count[0] += 1
            return mock_driver

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.side_effect = count_driver_calls

            handler = Neo4jMemoryHandler()
            handler.get_stale_items(cutoff_datetime)
            handler.get_stale_items(cutoff_datetime)
            handler.get_stale_items(cutoff_datetime)
            handler.close()

        # Driver should only be created once
        assert driver_call_count[0] == 1

    def test_close_closes_driver(
        self,
        apply_mock_patches: dict,
    ):
        """close() properly closes the driver."""
        mock_driver = create_mock_driver()

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver

            handler = Neo4jMemoryHandler()
            # Force driver creation
            handler._get_driver()
            handler.close()

        mock_driver.close.assert_called_once()

    def test_close_without_driver_is_safe(
        self,
        apply_mock_patches: dict,
    ):
        """close() is safe to call without driver initialization."""
        handler = Neo4jMemoryHandler()
        # Should not raise
        handler.close()


# =============================================================================
# TEST: Configuration
# =============================================================================


class TestNeo4jConfiguration:
    """Tests for Neo4j configuration handling."""

    def test_uses_config_values(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
    ):
        """Handler uses values from config."""
        mock_session = create_mock_session(query_results=[])
        mock_driver = create_mock_driver(session=mock_session)

        captured_uri = None
        captured_auth = None

        def capture_driver(uri, auth):
            nonlocal captured_uri, captured_auth
            captured_uri = uri
            captured_auth = auth
            return mock_driver

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.side_effect = capture_driver

            handler = Neo4jMemoryHandler()
            handler.get_stale_items(cutoff_datetime)
            handler.close()

        # Should use default config values
        assert "bolt://" in captured_uri or "neo4j://" in captured_uri
        assert captured_auth is not None

    def test_env_vars_override_config(
        self,
        apply_mock_patches: dict,
        cutoff_datetime: datetime,
        monkeypatch,
    ):
        """Environment variables override config values."""
        mock_session = create_mock_session(query_results=[])
        mock_driver = create_mock_driver(session=mock_session)

        # Set environment variables
        monkeypatch.setenv("NEO4J_URI", "bolt://custom-host:9999")
        monkeypatch.setenv("NEO4J_USERNAME", "custom_user")
        monkeypatch.setenv("NEO4J_PASSWORD", "custom_pass")

        captured_uri = None
        captured_auth = None

        def capture_driver(uri, auth):
            nonlocal captured_uri, captured_auth
            captured_uri = uri
            captured_auth = auth
            return mock_driver

        with patch("operations.cleanup.handlers.neo4j_memory.GraphDatabase") as mock_gdb:
            mock_gdb.driver.side_effect = capture_driver

            handler = Neo4jMemoryHandler()
            handler.get_stale_items(cutoff_datetime)
            handler.close()

        assert captured_uri == "bolt://custom-host:9999"
        assert captured_auth == ("custom_user", "custom_pass")
