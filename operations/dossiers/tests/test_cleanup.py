"""Tests for inline registration cleanup in db.py (_maybe_reap_stale_registrations).

Exercised indirectly via `connect_dossier_db` / `open_dossier_db`, since
cleanup runs as a preamble to every dossier connection.
"""
import sqlite3
from pathlib import Path

import pytest

from operations.dossiers.db import (
    _maybe_reap_stale_registrations,
    open_dossier_db,
    safe_db_path,
)
from operations.dossiers.lock import claim_lock, get_lock_status
from operations.dossiers.registration import register_agent


def _seed_stale_registration(
    tmp_path: Path,
    slug: str,
    agent_id: str = "claude-code:stale1",
    agent_type: str = "claude-code",
    role: str = "orchestrator",
    timestamp: str = "2000-01-01T00:00:00Z",
) -> None:
    """Insert a registration row with an artificially old `registered_at`."""
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        register_agent(conn, agent_id, agent_type, 1, role=role)
        conn.execute(
            "UPDATE registrations SET registered_at = ? WHERE agent_id = ?",
            (timestamp, agent_id),
        )
        conn.commit()


def _registrations(tmp_path: Path, slug: str) -> list[dict]:
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT agent_id, registered_at FROM registrations"
        ).fetchall()]


class TestThrottle:
    def test_skips_cleanup_within_interval_window(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(1)

        # Phase 1: interval=0 — every connect runs cleanup. Seed a stale row,
        # connect, expect it to be reaped so `last_registration_cleanup`
        # is freshly set.
        set_cleanup_check_interval(0)
        _seed_stale_registration(tmp_path, slug)
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert _registrations(tmp_path, slug) == []

        # Phase 2: tighten the throttle. A newly-seeded stale row must NOT be
        # reaped because the interval window hasn't elapsed.
        set_cleanup_check_interval(3600)
        _seed_stale_registration(tmp_path, slug, agent_id="claude-code:stale2")
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert any(
            r["agent_id"] == "claude-code:stale2"
            for r in _registrations(tmp_path, slug)
        )

    def test_runs_after_interval_elapses(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(1)
        set_cleanup_check_interval(0)  # never throttled

        _seed_stale_registration(tmp_path, slug)
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert _registrations(tmp_path, slug) == []

    def test_updates_last_registration_cleanup_even_on_empty_reap(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(99999)
        set_cleanup_check_interval(0)

        # no stale rows exist; cleanup runs, bumps throttle timestamp
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            row = conn.execute(
                "SELECT last_registration_cleanup FROM metadata"
            ).fetchone()
        assert row["last_registration_cleanup"] is not None


class TestReaping:
    def test_deletes_stale_registration_row(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(1)
        set_cleanup_check_interval(0)

        _seed_stale_registration(tmp_path, slug)
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert _registrations(tmp_path, slug) == []

    def test_releases_lock_held_by_stale_agent(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        # register + lock under the future-stale id, then re-mark as stale
        claim_lock(tmp_path, slug, agent="claude-code:stale1")
        _seed_stale_registration(tmp_path, slug)

        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass

        status = get_lock_status(tmp_path, slug)
        assert status["locked_by"] is None

    def test_resets_in_progress_tasks_owned_by_stale_agent(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier(tasks=[{"subject": "t1"}])["slug"]
        _seed_stale_registration(tmp_path, slug, agent_id="claude-code:stale1")

        # assign the stale agent as owner on an in_progress task directly in DB
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ? WHERE id = 1",
                ("claude-code:stale1",),
            )
            conn.commit()

        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            row = conn.execute(
                "SELECT status, owner FROM tasks WHERE id = 1"
            ).fetchone()
        assert row["status"] == "pending"
        assert row["owner"] is None

    def test_preserves_non_in_progress_tasks(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier(tasks=[{"subject": "done"}])["slug"]
        _seed_stale_registration(tmp_path, slug, agent_id="claude-code:stale1")

        # mark task completed with stale agent as owner — cleanup must NOT revert
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'completed', owner = ? WHERE id = 1",
                ("claude-code:stale1",),
            )
            conn.commit()

        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            row = conn.execute(
                "SELECT status FROM tasks WHERE id = 1"
            ).fetchone()
        assert row["status"] == "completed"

    def test_fresh_registration_not_reaped(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(99999)  # effectively never stale
        set_cleanup_check_interval(0)

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:fresh1", "claude-code", 1)

        # trigger cleanup again
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass

        rows = _registrations(tmp_path, slug)
        assert any(r["agent_id"] == "claude-code:fresh1" for r in rows)


class TestFailureIsolation:
    def test_uninitialized_metadata_is_noop(self, tmp_path, make_dossier):
        """cleanup silently skips if metadata row is absent."""
        slug = make_dossier()["slug"]
        # wipe metadata after creation — simulates an inconsistent state
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute("DELETE FROM metadata")
            conn.commit()
        # cleanup must not raise
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            _maybe_reap_stale_registrations(conn)

    def test_swallows_sqlite_error_during_reaping(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        """Simulate a reaping-phase sqlite3 failure by proxying `execute`."""
        slug = make_dossier()["slug"]
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        _seed_stale_registration(tmp_path, slug)

        class _FailingConn:
            """Transparent proxy that raises on a DELETE targeting registrations."""

            def __init__(self, real):
                self._real = real

            def execute(self, sql, *args, **kwargs):
                if "DELETE FROM registrations" in sql:
                    raise sqlite3.OperationalError("simulated failure")
                return self._real.execute(sql, *args, **kwargs)

            def __enter__(self):
                return self._real.__enter__()

            def __exit__(self, *exc):
                return self._real.__exit__(*exc)

            def __getattr__(self, name):
                return getattr(self._real, name)

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            wrapped = _FailingConn(conn)
            # must not raise — cleanup's sqlite3.Error handler swallows this
            _maybe_reap_stale_registrations(wrapped)

    def test_does_not_swallow_non_sqlite_errors(
        self, tmp_path, make_dossier, monkeypatch, set_registration_ttl, set_cleanup_check_interval
    ):
        """TypeError / AttributeError must propagate — v1's bug was bare `except Exception`."""
        slug = make_dossier()["slug"]
        set_registration_ttl(1)
        set_cleanup_check_interval(0)

        # patch _now_iso to raise a non-sqlite error during cleanup
        def _boom():
            raise TypeError("programming bug")

        monkeypatch.setattr("operations.dossiers.db._now_iso", _boom)

        with pytest.raises(TypeError, match="programming bug"):
            with open_dossier_db(safe_db_path(tmp_path, slug)):
                pass
