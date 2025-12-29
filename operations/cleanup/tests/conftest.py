"""
Shared pytest fixtures for cleanup handler tests.

- Fixtures are reusable setup/teardown providers for tests, returning 
  ready-to-use objs (e.g. temp files, mock configs).
- Pytest:
    - builds and injects fixtures into tests (who request them via args)  
    - handles cleanup
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# DATETIME FIXTURES - Fixed dates for deterministic testing
# =============================================================================

@pytest.fixture
def cutoff_datetime() -> datetime:
    """
    Fixed UTC cutoff datetime for consistent boundary testing.

    All tests use this as the reference point:
    - Items created BEFORE this are stale and should be moved to trash
    - Items created AT or AFTER this are valid and should be preserved

    Resolves to January 15, 2024, 12:00:00 UTC
    """
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def stale_datetime() -> datetime:
    """Date earlier than cutoff (i.e. items with this date should be considered stale).
    
    Resolves to January 1, 2024, 00:00:00 UTC
    """
    return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def valid_datetime() -> datetime:
    """Date later than cutoff (i.e. items with this date should be considered valid).
    
    Resolves to February 1, 2024, 00:00:00 UTC
    """
    return datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def boundary_datetime(cutoff_datetime: datetime) -> datetime:
    """Exact boundary datetime (should NOT be expired: stale items should have dates strictly less than the cutoff)."""
    return cutoff_datetime


# =============================================================================
# CONFIG FIXTURES
# =============================================================================

@pytest.fixture
def mock_config() -> dict[str, Any]:
    """Base configuration structure matching directives.yml."""
    return {
        "agents": ["claude", "gemini"],
        "retention_period_for": {
            "claude_mem": "30d",
            "serena": "90d",
            "qdrant": "180d",
            "neo4j_memory": "365d",
        },
        "cleanup": {
            "min_interval": "24h",
        },
        "trash": {
            "grace_period": "30d",
        },
        "path_to": {
            "workspace": "~/code",
        },
    }


# =============================================================================
# SQLITE FIXTURES (claude_mem handler)
# =============================================================================

@pytest.fixture
def sqlite_db(tmp_path: Path) -> Path:
    """Create temporary SQLite database consisting of 2 tables matching claude-mem's schema."""
    db_path = tmp_path / "claude-mem.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables matching claude-mem schema
    # Note created_at is expected to be an ISO 8601 timestamp string
    cursor.execute("""
        CREATE TABLE session_summaries (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            summary TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE observations (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            content TEXT
        )
    """)

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def with_sqlite_data(
    sqlite_db: Path,
    stale_datetime: datetime,
    valid_datetime: datetime,
) -> Path:
    """
    Receives a SQLite database initialized by sqlite_db() to match claude-mem's schema
    and pre-populates it with test data.
    """
    conn = sqlite3.connect(str(sqlite_db))
    cursor = conn.cursor()

    # Format with Z suffix to match claude-mem's ISO 8601 format for the created_at
    #   timestamp string (created in JS via toISOString())
    stale_ts = stale_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    valid_ts = valid_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Add stale session summary record
    cursor.execute(
        "INSERT INTO session_summaries (id, created_at, summary) VALUES (?, ?, ?)",
        ("session_stale", stale_ts, "Stale session summary")
    )

    # Add valid session summary record
    cursor.execute(
        "INSERT INTO session_summaries (id, created_at, summary) VALUES (?, ?, ?)",
        ("session_valid", valid_ts, "Valid session summary")
    )

    # Add stale observation record
    cursor.execute(
        "INSERT INTO observations (id, created_at, content) VALUES (?, ?, ?)",
        ("obs_stale", stale_ts, "Stale observation")
    )

    # Add valid observation record
    cursor.execute(
        "INSERT INTO observations (id, created_at, content) VALUES (?, ?, ?)",
        ("obs_valid", valid_ts, "Valid observation")
    )

    conn.commit()
    conn.close()
    return sqlite_db


# =============================================================================
# SERENA FIXTURES (filesystem)
# =============================================================================

@pytest.fixture
def serena_projects(tmp_path: Path) -> Path:
    """Realistic Serena project structure including symlink edge case.

    Creates:
    - 2 regular projects with .serena/memories/ (2 memory files each)
    - 1 symlinked project pointing to external directory

    The external directory is at tmp_path / "external" for tests that need
    to verify it wasn't touched.
    """
    projects_dir = tmp_path / "projects"

    # Create two regular projects with .serena/memories/
    for i in range(2):
        project_dir = projects_dir / f"project_{i}"
        memories_dir = project_dir / ".serena" / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)

        # Create memory files
        for j in range(2):
            memory_file = memories_dir / f"memory_{j}.md"
            memory_file.write_text(f"# Memory {j}\n\nProject {i} memory content.")

    # Create external directory (outside projects_dir) with memories
    external_dir = tmp_path / "external"
    external_memories = external_dir / ".serena" / "memories"
    external_memories.mkdir(parents=True)
    (external_memories / "external_memory.md").write_text("External memory")

    # Create symlink inside projects_dir pointing to external
    symlinked_project = projects_dir / "symlinked_project"
    symlinked_project.symlink_to(external_dir)

    return projects_dir


# =============================================================================
# QDRANT FIXTURES (HTTP API mocking)
# =============================================================================

@pytest.fixture
def qdrant_base_url() -> str:
    """Base URL for Qdrant API."""
    return "http://127.0.0.1:8780"


@pytest.fixture
def qdrant_collection() -> str:
    """Qdrant collection name."""
    return "coding-memory"


# =============================================================================
# NEO4J FIXTURES (graph memory)
# =============================================================================

@pytest.fixture
def neo4j_uri() -> str:
    """Neo4j connection URI."""
    return "bolt://127.0.0.1:7687"


@pytest.fixture
def neo4j_auth() -> tuple[str, str]:
    """Neo4j authentication credentials."""
    return ("neo4j", "bureau")


# =============================================================================
# TRASH/STATE FIXTURES
# =============================================================================

@pytest.fixture
def archives_dir(tmp_path: Path) -> Path:
    """Create temporary .archives directory for state and trash."""
    archives = tmp_path / ".archives"
    archives.mkdir()
    return archives


@pytest.fixture
def trash_dir(archives_dir: Path) -> Path:
    """Create trash subdirectory."""
    trash = archives_dir / "trash"
    trash.mkdir()
    return trash


@pytest.fixture
def state_file(archives_dir: Path) -> Path:
    """Path to state.json (may or may not exist)."""
    return archives_dir / "state.json"


# =============================================================================
# SETTINGS MOCK FIXTURE
# =============================================================================

@pytest.fixture
def apply_mock_patches(
    tmp_path: Path,
    sqlite_db: Path,
    serena_projects: Path,
    archives_dir: Path,
    qdrant_base_url: str,
    qdrant_collection: str,
    mock_config: dict,
    monkeypatch,
):
    """Monkeypatch all settings functions to use test paths.

    Note monkeypatching is distinct from stubbing: it allows runtime
    replacement of *any* attribute in *any* module.

    Args:
    - monkeypatch: pytest's built-in patching tool
    - all others: other fixtures, injected as deps

    Note patches are made at the import location (where it's used, i.e.
    the importing module) and *not* at the source (i.e. the module 
    originally defining the imported function). 
    
    This is because Python's import system makes a separate, local 
    reference to the original function when a module imports it.
    
    Patching at the source would leave the reference in the 
    point of use, i.e. the importing module (where we want the 
    patch to actually take effect), pointing to the original 
    function and not the patched version meant for testing.

    Patches made:
    - get_path() to return test paths
    - get_qdrant_url() to return test URL
    - get_qdrant_collection() to return test collection
    - get_config() to return mock_config
    - get_archives_dir() to return test archives dir
    - get_trash_dir() to return test trash dir
    - get_state_path() to return test state path
    """

    # define replacement functions
    def mock_get_path(path_name: str) -> Path:
        paths = {
            "serena_projects": serena_projects,
        }
        return paths.get(path_name, tmp_path / path_name)

    def mock_get_storage(storage_name: str) -> Path:
        storages = {
            "claude_mem": sqlite_db,
        }
        return storages.get(storage_name, tmp_path / storage_name)

    # patch handlers' function imports
    #   (and *not* the source's definitions)
    monkeypatch.setattr(
        "operations.cleanup.handlers.claude_mem.get_storage",
        mock_get_storage
    )
    monkeypatch.setattr(
        "operations.cleanup.handlers.serena.get_path",
        mock_get_path
    )
    monkeypatch.setattr(
        "operations.cleanup.handlers.qdrant.get_qdrant_url",
        lambda: qdrant_base_url
    )
    monkeypatch.setattr(
        "operations.cleanup.handlers.qdrant.get_qdrant_collection",
        lambda: qdrant_collection
    )

    # patch state module
    monkeypatch.setattr(
        "operations.cleanup.state.get_archives_dir",
        lambda: archives_dir
    )
    monkeypatch.setattr(
        "operations.cleanup.state.get_state_path",
        lambda: archives_dir / "state.json"
    )
    monkeypatch.setattr(
        "operations.cleanup.state.ARCHIVES_DIR",
        archives_dir
    )
    monkeypatch.setattr(
        "operations.cleanup.state.STATE_PATH",
        archives_dir / "state.json"
    )

    # Patch trash module
    trash_dir = archives_dir / "trash"
    monkeypatch.setattr(
        "operations.cleanup.trash.get_base_trash_dir",
        lambda: trash_dir
    )
    monkeypatch.setattr(
        "operations.cleanup.trash.BASE_TRASH_DIR",
        trash_dir
    )

    return mock_config
