"""Tests for dossier database creation, schema, and the v3->v4->v5 migrations."""
import sqlite3
from pathlib import Path

import pytest

from operations.dossiers.db import (
    SCHEMA_VERSION,
    _BASE_SCHEMA_SQL,
    _V4_REBUILD_STATEMENTS,
    _V4_SCHEMA_SQL,
    _V5_STATEMENTS,
    _now_iso,
    _user_version,
    connect_dossier_db,
    create_dossier_db,
    escape_md,
    migrate_v3_to_v4,
    safe_db_path,
)

# The pre-migration (v3) registrations shape: ppid (not cli_pid), no
# last_heartbeat, no role CHECK, a plain agent_type index instead of the
# partial orchestrator-slot unique.
_OLD_REGISTRATIONS = """CREATE TABLE registrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id      TEXT NOT NULL UNIQUE,
    agent_type    TEXT NOT NULL,
    ppid          INTEGER,
    role          TEXT NOT NULL DEFAULT 'orchestrator',
    registered_at TEXT NOT NULL
)"""
_OLD_REG_INDEX = "CREATE INDEX idx_registrations_type ON registrations(agent_type)"


def _make_v3_db(path: Path, *, with_orphans: bool = False) -> None:
    """Build a v3-shaped dossier DB (base tables identical to v4 + old regs)."""
    conn = sqlite3.connect(path)
    conn.executescript(_BASE_SCHEMA_SQL)  # identical base tables to fresh-v4
    conn.execute(_OLD_REGISTRATIONS)
    conn.execute(_OLD_REG_INDEX)
    now = _now_iso()
    conn.execute(
        "INSERT INTO metadata (id, hash, name, slug, created_at, updated_at, locked_by) "
        "VALUES (1, 'h', 'n', ?, ?, ?, ?)",
        (path.stem, now, now, "claude-code:old1" if with_orphans else None),
    )
    # a stale v3 registration that drop-and-recreate must discard
    conn.execute(
        "INSERT INTO registrations (agent_id, agent_type, ppid, role, registered_at) "
        "VALUES ('claude-code:old1', 'claude-code', 999, 'orchestrator', ?)",
        (now,),
    )
    if with_orphans:
        conn.execute(
            "INSERT INTO tasks (subject, status, owner) "
            "VALUES ('t1', 'in_progress', 'claude-code:old1')"
        )
    conn.execute("PRAGMA user_version = 3")
    conn.commit()
    conn.close()


def _make_v4_db(path: Path, *, populated: bool = False) -> None:
    """Build a v4-shaped dossier DB: the pre-v5 fresh-create output, stamped 4.

    `_V4_SCHEMA_SQL` is exactly what `create_dossier_db` wrote before v5, so a
    database built this way is indistinguishable from one an older Bureau left
    on disk. `populated` seeds a row in every table the migration touches, so
    the additive-migration tests observe real data rather than empty tables.
    """
    conn = sqlite3.connect(path)
    conn.executescript(_V4_SCHEMA_SQL)
    now = _now_iso()
    conn.execute(
        "INSERT INTO metadata (id, hash, name, slug, created_at, updated_at) "
        "VALUES (1, 'h', 'n', ?, ?, ?)",
        (path.stem, now, now),
    )
    if populated:
        conn.execute(
            "INSERT INTO sessions (folded_at, agent, digest) VALUES (?, 'a', 'D.')",
            (now,),
        )
        conn.execute("INSERT INTO tasks (subject) VALUES ('t1')")
        conn.execute(
            "INSERT INTO decisions (session_id, what, why) VALUES (1, 'w', 'y')"
        )
        conn.execute(
            "INSERT INTO file_interactions (session_id, file_path, action) "
            "VALUES (1, '/f.py', 'read')"
        )
        conn.execute(
            "INSERT INTO registrations "
            "(agent_id, agent_type, role, cli_pid, registered_at, last_heartbeat) "
            "VALUES ('orch-claude-code-abc', 'claude-code', 'orchestrator', 1, ?, ?)",
            (now, now),
        )
    conn.execute("PRAGMA user_version = 4")
    conn.commit()
    conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _schema_objects(path: Path) -> list[tuple]:
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    conn.close()
    return rows


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
        """Every durable table exists after creation."""
        db_path = tmp_path / "test.db"
        create_dossier_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        expected = {
            "metadata", "sessions", "tasks", "decisions", "file_interactions",
            "pinned_findings", "finding_supersessions", "memory_queries",
        }
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


class TestMigrateV3ToV4:
    """v3 -> v4: drop-and-recreate registrations, add reap_log, version-gated."""

    def test_connect_migrates_v3_to_v4_shape(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v3_db(db)
        conn = connect_dossier_db(db)
        try:
            assert _user_version(conn) == SCHEMA_VERSION
            cols = {r[1] for r in conn.execute("PRAGMA table_info(registrations)")}
            assert "cli_pid" in cols and "last_heartbeat" in cols
            assert "ppid" not in cols
            objs = {r[1] for r in conn.execute(
                "SELECT type, name FROM sqlite_master"
            )}
            assert "reap_log" in objs
            assert "idx_registrations_orchestrator_slot" in objs
            assert "idx_registrations_type" not in objs  # dead v2/v3 index
        finally:
            conn.close()

    def test_drops_stale_v3_registration_rows(self, tmp_path: Path):
        # registrations are a cache; the migration invalidates, never backfills
        db = tmp_path / "d.db"
        _make_v3_db(db)
        conn = connect_dossier_db(db)
        try:
            assert conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0
        finally:
            conn.close()

    def test_writes_backup_before_rebuild(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v3_db(db)
        connect_dossier_db(db).close()
        assert (tmp_path / "d.db.pre-v4.bak").exists()

    def test_fresh_and_migrated_schema_converge(self, tmp_path: Path):
        # the classic silent-migration bug: the two paths must agree byte-for-byte
        fresh = tmp_path / "fresh.db"
        create_dossier_db(fresh)

        migrated = tmp_path / "migrated.db"
        _make_v3_db(migrated)
        connect_dossier_db(migrated).close()

        assert _schema_objects(fresh) == _schema_objects(migrated)

    def test_second_connect_is_noop(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v3_db(db)
        connect_dossier_db(db).close()
        # already at v4: a second connect must not re-run / re-drop anything
        conn = connect_dossier_db(db)
        try:
            assert _user_version(conn) == SCHEMA_VERSION
        finally:
            conn.close()

    def test_crash_mid_migration_rolls_back_to_v3(self, tmp_path: Path, monkeypatch):
        # transactional crash safety: a failure after DROP must restore v3,
        # leaving user_version at 3 so the migration re-runs cleanly next time.
        db = tmp_path / "d.db"
        _make_v3_db(db)
        monkeypatch.setattr(
            "operations.dossiers.db._V4_REBUILD_STATEMENTS",
            (_V4_REBUILD_STATEMENTS[0], "THIS IS NOT VALID SQL"),
        )
        with pytest.raises(sqlite3.OperationalError):
            connect_dossier_db(db)

        raw = sqlite3.connect(db)
        try:
            assert raw.execute("PRAGMA user_version").fetchone()[0] == 3
            cols = {r[1] for r in raw.execute("PRAGMA table_info(registrations)")}
            assert "ppid" in cols  # the v3 table is intact (DROP rolled back)
        finally:
            raw.close()

    def test_orphan_report_printed_to_stderr(self, tmp_path: Path, capsys):
        db = tmp_path / "d.db"
        _make_v3_db(db, with_orphans=True)
        connect_dossier_db(db).close()
        err = capsys.readouterr().err
        assert "orphaned owners" in err
        assert "#1" in err
        assert "lock held by a pre-v4 identity" in err

    def test_clean_migration_is_quiet(self, tmp_path: Path, capsys):
        db = tmp_path / "d.db"
        _make_v3_db(db, with_orphans=False)
        connect_dossier_db(db).close()
        assert capsys.readouterr().err == ""


class TestMigrateV4ToV5:
    """v4 -> v5: purely additive columns and tables, nothing dropped.

    The v3->v4 migration rebuilt a table, so it needed a backup and an orphan
    report. This one only ever adds, which is what lets every test below assert
    that pre-existing data is bit-for-bit untouched.
    """

    def test_connect_adds_the_session_scalars(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v4_db(db)
        conn = connect_dossier_db(db)
        try:
            assert {"last_exchange", "next_words", "mood"} <= _columns(conn, "sessions")
        finally:
            conn.close()

    def test_connect_adds_the_decision_provenance_columns(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v4_db(db)
        conn = connect_dossier_db(db)
        try:
            assert {"source", "origin_session"} <= _columns(conn, "decisions")
        finally:
            conn.close()

    def test_connect_creates_the_v5_tables(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v4_db(db)
        conn = connect_dossier_db(db)
        try:
            tables = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            assert {"pinned_findings", "finding_supersessions", "memory_queries"} <= tables
        finally:
            conn.close()

    def test_stamps_the_new_schema_version(self, tmp_path: Path):
        db = tmp_path / "d.db"
        _make_v4_db(db)
        conn = connect_dossier_db(db)
        try:
            assert _user_version(conn) == SCHEMA_VERSION == 5
        finally:
            conn.close()

    def test_preserves_every_row_the_v4_database_held(self, tmp_path: Path):
        """Additive means additive: no rebuild, so nothing is invalidated."""
        db = tmp_path / "d.db"
        _make_v4_db(db, populated=True)
        conn = connect_dossier_db(db)
        try:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "sessions", "tasks", "decisions", "file_interactions",
                    "registrations",
                )
            }
        finally:
            conn.close()

        assert counts == {
            "sessions": 1, "tasks": 1, "decisions": 1, "file_interactions": 1,
            "registrations": 1,
        }

    def test_added_columns_are_null_on_pre_existing_rows(self, tmp_path: Path):
        """No DEFAULT: an old session simply never recorded these fields."""
        db = tmp_path / "d.db"
        _make_v4_db(db, populated=True)
        conn = connect_dossier_db(db)
        try:
            row = conn.execute("SELECT * FROM sessions").fetchone()
        finally:
            conn.close()

        assert (row["last_exchange"], row["next_words"], row["mood"]) == (None, None, None)

    def test_fresh_and_migrated_schema_converge(self, tmp_path: Path):
        """MIGR-2 for v5: one set of DDL constants drives both paths."""
        fresh = tmp_path / "fresh.db"
        create_dossier_db(fresh)

        migrated = tmp_path / "migrated.db"
        _make_v4_db(migrated)
        connect_dossier_db(migrated).close()

        assert _schema_objects(fresh) == _schema_objects(migrated)

    def test_a_v3_database_migrates_all_the_way_to_v5(self, tmp_path: Path):
        """Both migrations run on one connect, in order, without interfering."""
        fresh = tmp_path / "fresh.db"
        create_dossier_db(fresh)

        migrated = tmp_path / "migrated.db"
        _make_v3_db(migrated)
        conn = connect_dossier_db(migrated)
        try:
            assert _user_version(conn) == SCHEMA_VERSION
        finally:
            conn.close()

        assert _schema_objects(fresh) == _schema_objects(migrated)

    def test_second_connect_is_noop(self, tmp_path: Path):
        """Re-running the ALTERs would raise `duplicate column name`."""
        db = tmp_path / "d.db"
        _make_v4_db(db)
        connect_dossier_db(db).close()

        conn = connect_dossier_db(db)
        try:
            assert _user_version(conn) == SCHEMA_VERSION
        finally:
            conn.close()

    def test_writes_no_backup_file(self, tmp_path: Path):
        """v3->v4 backed up because it dropped a table; this one destroys nothing."""
        db = tmp_path / "d.db"
        _make_v4_db(db)
        connect_dossier_db(db).close()

        assert list(tmp_path.glob("*.bak")) == []

    def test_crash_mid_migration_rolls_back_to_v4(self, tmp_path: Path, monkeypatch):
        """A half-applied migration must leave v4 intact and re-runnable."""
        db = tmp_path / "d.db"
        _make_v4_db(db, populated=True)
        monkeypatch.setattr(
            "operations.dossiers.db._V5_STATEMENTS",
            (_V5_STATEMENTS[0], "THIS IS NOT VALID SQL"),
        )
        with pytest.raises(sqlite3.OperationalError):
            connect_dossier_db(db)

        raw = sqlite3.connect(db)
        try:
            assert raw.execute("PRAGMA user_version").fetchone()[0] == 4
            cols = {r[1] for r in raw.execute("PRAGMA table_info(sessions)")}
            assert "last_exchange" not in cols, "a partial ALTER survived the rollback"
        finally:
            raw.close()


class TestMigrationVersionGating:
    """A migration must target a FIXED version, never the moving constant.

    `migrate_v3_to_v4` gated on `SCHEMA_VERSION`, so advancing that constant
    for a later migration would make every v4 database fail the gate, fall
    into the destructive `DROP TABLE registrations` rebuild, and then be
    stamped with the new version without the new migration ever running.
    """

    def test_current_database_is_untouched_when_schema_version_advances(
        self, tmp_path, monkeypatch
    ):
        """Simulate a future version bump; no earlier migration may re-fire."""
        import operations.dossiers.db as db_module

        current_version = db_module.SCHEMA_VERSION
        path = tmp_path / "gated.db"
        db_module.create_dossier_db(path)

        # a live registration is exactly what the destructive rebuild drops
        conn = sqlite3.connect(path)
        conn.execute(
            "INSERT INTO registrations "
            "(agent_id, agent_type, role, cli_pid, registered_at, last_heartbeat) "
            "VALUES ('orch-claude-code-abc', 'claude-code', 'orchestrator', 1, 'T', 'T')"
        )
        conn.commit()
        conn.close()

        # a later migration lands and advances the constant
        monkeypatch.setattr(db_module, "SCHEMA_VERSION", db_module.SCHEMA_VERSION + 1)

        conn = db_module.connect_dossier_db(path)
        try:
            survivors = conn.execute(
                "SELECT COUNT(*) FROM registrations"
            ).fetchone()[0]
            stamped = conn.execute("PRAGMA user_version").fetchone()[0]
        finally:
            conn.close()

        assert survivors == 1, "v3->v4 rebuild fired on a current database and dropped rows"
        assert stamped == current_version, (
            f"database mis-stamped as v{stamped} without a v{stamped} migration"
        )
