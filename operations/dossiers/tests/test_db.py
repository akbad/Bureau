"""Tests for dossier database creation and schema."""
import sqlite3
from pathlib import Path

import pytest

from operations.dossiers.db import create_dossier_db, connect_dossier_db, SCHEMA_VERSION


class TestCreateDossierDb:
    """Tests for create_dossier_db()."""

    def test_creates_db_file(self, tmp_path: Path):
        """Creates a .db file at the given path."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        assert db_path.exists()

    def test_wal_mode_enabled(self, tmp_path: Path):
        """Database uses WAL journal mode."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_all_tables_created(self, tmp_path: Path):
        """All 5 tables exist after creation."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        expected = {"metadata", "sessions", "tasks", "decisions", "file_interactions"}
        assert expected.issubset(tables)

    def test_schema_version_stored(self, tmp_path: Path):
        """Schema version is stored for future migrations."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
        assert version == SCHEMA_VERSION


class TestConnectDossierDb:
    """Tests for connect_dossier_db()."""

    def test_returns_connection(self, tmp_path: Path):
        """Returns a sqlite3 Connection with row_factory set."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = connect_dossier_db(db_path)
        assert isinstance(conn, sqlite3.Connection)
        # row_factory should be sqlite3.Row for dict-like access
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_raises_on_missing_db(self, tmp_path: Path):
        """Raises FileNotFoundError for non-existent DB."""
        db_path = tmp_path / "nonexistent.db"
        with pytest.raises(FileNotFoundError):
            connect_dossier_db(db_path)
