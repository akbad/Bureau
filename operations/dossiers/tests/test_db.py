"""Tests for dossier database creation and schema."""
import sqlite3
from pathlib import Path

import pytest

from operations.dossiers.db import (
    SCHEMA_VERSION,
    connect_dossier_db,
    create_dossier_db,
    escape_md,
    safe_db_path,
)


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


class TestSafeDbPath:
    """Tests for slug-to-path containment enforcement."""

    def test_accepts_normal_slug(self, tmp_path: Path):
        """A normal slug resolves under the dossiers directory."""
        dossiers_dir = tmp_path / "dossiers"
        dossiers_dir.mkdir()

        path = safe_db_path(dossiers_dir, "team-plan")

        assert path == (dossiers_dir / "team-plan.db").resolve()

    def test_accepts_slug_with_spaces_and_brackets(self, tmp_path: Path):
        """Containment checks should not over-restrict non-traversal slugs."""
        dossiers_dir = tmp_path / "dossiers"
        dossiers_dir.mkdir()

        path = safe_db_path(dossiers_dir, "name with [brackets] and spaces")

        assert path == (dossiers_dir / "name with [brackets] and spaces.db").resolve()

    @pytest.mark.parametrize(
        "slug",
        ["../evil", "../../etc/passwd", "/tmp/evil"],
        ids=["parent-traversal", "deep-traversal", "absolute-path"],
    )
    def test_rejects_path_escape_attempts(self, tmp_path: Path, slug: str):
        """Escaping the dossiers directory raises ValueError."""
        dossiers_dir = tmp_path / "dossiers"
        dossiers_dir.mkdir()

        with pytest.raises(ValueError, match="Path escapes allowed directory"):
            safe_db_path(dossiers_dir, slug)

    def test_rejects_sibling_prefix_escape(self, tmp_path: Path):
        """Sibling paths that share the old prefix still count as escapes."""
        dossiers_dir = tmp_path / "dossiers"
        dossiers_dir.mkdir()

        with pytest.raises(ValueError, match="Path escapes allowed directory"):
            safe_db_path(dossiers_dir, "../dossiers-evil/escape")


class TestEscapeMd:
    """Tests for markdown escaping of stored dossier content."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("|", "\\|"),
            ("*", "\\*"),
            ("#", "\\#"),
            (">", "\\>"),
            ("`", "\\`"),
            ("[", "\\["),
            ("]", "\\]"),
        ],
        ids=[
            "pipe",
            "asterisk",
            "hash",
            "blockquote",
            "code-span",
            "open-bracket",
            "close-bracket",
        ],
    )
    def test_escapes_each_control_character(self, value: str, expected: str):
        """Every markdown control character should be escaped individually."""
        assert escape_md(value) == expected

    def test_escapes_multiple_control_characters_in_one_string(self):
        """Mixed content should escape every control character without touching safe text."""
        assert escape_md("a|b*c#d>e`f[g]") == "a\\|b\\*c\\#d\\>e\\`f\\[g\\]"

    def test_leaves_plain_text_unchanged(self):
        """Ordinary text should pass through unchanged."""
        assert escape_md("plain text") == "plain text"

    def test_returns_empty_string_for_empty_input(self):
        """Empty strings should remain empty."""
        assert escape_md("") == ""

    def test_returns_empty_string_for_none(self):
        """None input is normalized to an empty string."""
        assert escape_md(None) == ""
