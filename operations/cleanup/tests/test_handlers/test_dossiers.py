"""Tests for DossiersHandler (new .db format)."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from operations.cleanup.handlers.dossiers import DossiersHandler
from operations.dossiers.db import create_dossier_db, connect_dossier_db


@pytest.fixture
def dossiers_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "dossiers"
    d.mkdir()
    monkeypatch.setattr(
        "operations.cleanup.handlers.dossiers.DOSSIERS_DIR", d
    )
    return d


def _create_dossier(dossiers_dir: Path, slug: str, updated_at: str) -> Path:
    """Helper to create a test dossier DB with given updated_at."""
    db_path = dossiers_dir / f"{slug}.db"
    create_dossier_db(db_path)
    conn = connect_dossier_db(db_path)
    conn.execute(
        "INSERT INTO metadata (hash, name, slug, created_at, updated_at, agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("abc123", slug, slug, updated_at, updated_at, "test"),
    )
    conn.commit()
    conn.close()
    return db_path


class TestDossiersHandlerGetStaleItems:
    def test_finds_stale_dossiers(
        self, dossiers_dir: Path, cutoff_datetime: datetime
    ):
        _create_dossier(dossiers_dir, "old-dossier", "2024-01-01T00:00:00Z")
        _create_dossier(dossiers_dir, "new-dossier", "2024-02-01T00:00:00Z")
        handler = DossiersHandler()
        stale = handler.get_stale_items(cutoff_datetime)
        assert len(stale) == 1
        assert "old-dossier" in str(stale[0]["path"])

    def test_no_stale_when_all_fresh(
        self, dossiers_dir: Path, cutoff_datetime: datetime
    ):
        _create_dossier(dossiers_dir, "fresh", "2024-02-01T00:00:00Z")
        handler = DossiersHandler()
        stale = handler.get_stale_items(cutoff_datetime)
        assert len(stale) == 0
