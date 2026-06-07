"""Tests for inline registration cleanup in db.py (_maybe_reap_stale_registrations).

v3 primary defense: a row is reaped only if it is *both* stale (by
last_heartbeat) *and* proven dead (by `_process_alive`). Exercised via
`open_dossier_db`, since cleanup runs as a preamble to every connection.
"""
import json
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

# A pid the liveness oracle is told is dead in tests; None means "worker
# without a recorded cli_pid" (timestamp-only path).
_STALE = "2000-01-01T00:00:00Z"


def _seed_stale_registration(
    tmp_path: Path,
    slug: str,
    agent_id: str = "orch-claude-code-stale",
    agent_type: str = "claude-code",
    role: str = "orchestrator",
    cli_pid: int | None = None,
    timestamp: str = _STALE,
) -> None:
    """Insert a registration row with an artificially old `last_heartbeat`.

    Cleanup at the seeding connect ran *before* this insert (it is a connect
    preamble), so the seeded-stale row is never reaped by its own seeding.
    """
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        register_agent(conn, agent_id, agent_type, cli_pid, role=role)
        conn.execute(
            "UPDATE registrations SET last_heartbeat = ? WHERE agent_id = ?",
            (timestamp, agent_id),
        )
        conn.commit()


def _registrations(tmp_path: Path, slug: str) -> list[dict]:
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT agent_id, last_heartbeat FROM registrations"
        ).fetchall()]


def _reap_log(tmp_path: Path, slug: str) -> list[dict]:
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reap_log").fetchall()]


class TestThrottle:
    def test_skips_cleanup_within_interval_window(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(1)

        # Phase 1: interval=0 — every connect runs cleanup. A stale worker
        # (cli_pid None => timestamp-only) is reaped.
        set_cleanup_check_interval(0)
        _seed_stale_registration(tmp_path, slug, role="worker")
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert _registrations(tmp_path, slug) == []

        # Phase 2: tighten the throttle. A newly-seeded stale row must NOT be
        # reaped because the interval window hasn't elapsed.
        set_cleanup_check_interval(3600)
        _seed_stale_registration(
            tmp_path, slug, agent_id="orch-claude-code-stale2", role="worker"
        )
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert any(
            r["agent_id"] == "orch-claude-code-stale2"
            for r in _registrations(tmp_path, slug)
        )

    def test_updates_last_registration_cleanup_even_on_empty_reap(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(99999)
        set_cleanup_check_interval(0)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            row = conn.execute(
                "SELECT last_registration_cleanup FROM metadata"
            ).fetchone()
        assert row["last_registration_cleanup"] is not None


class TestPidLiveness:
    """The primary defense: stale AND proven-dead is the reap predicate."""

    def test_dead_orchestrator_is_reaped(
        self, tmp_path, make_dossier, mock_process_alive,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        slug = make_dossier()["slug"]
        _seed_stale_registration(tmp_path, slug, cli_pid=4242)
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        mock_process_alive({4242: False})  # the stored pid is dead
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert _registrations(tmp_path, slug) == []

    def test_idle_but_alive_orchestrator_is_not_reaped(
        self, tmp_path, make_dossier, mock_process_alive,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        # Scenario B: a live-but-idle orchestrator's row, stale heartbeat, a
        # different CLI's cleanup. PID-liveness must spare it.
        slug = make_dossier()["slug"]
        _seed_stale_registration(tmp_path, slug, cli_pid=4242)
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        mock_process_alive({4242: True})  # the stored pid is still alive
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert any(
            r["agent_id"] == "orch-claude-code-stale"
            for r in _registrations(tmp_path, slug)
        )
        assert _reap_log(tmp_path, slug) == []  # nothing reaped, nothing logged

    def test_worker_without_cli_pid_reaped_by_timestamp(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        _seed_stale_registration(
            tmp_path, slug, agent_id="claude-code:worker-1:42",
            role="worker", cli_pid=None,
        )
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert _registrations(tmp_path, slug) == []
        log = _reap_log(tmp_path, slug)
        assert len(log) == 1
        assert log[0]["reap_reason"] == "timestamp_only"


class TestReapCascade:
    def test_releases_lock_held_by_dead_agent(
        self, tmp_path, make_dossier, mock_process_alive,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        slug = make_dossier()["slug"]
        claim_lock(tmp_path, slug, agent="orch-claude-code-stale")
        _seed_stale_registration(tmp_path, slug, cli_pid=4242)
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        mock_process_alive({4242: False})
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        assert get_lock_status(tmp_path, slug)["locked_by"] is None

    def test_resets_in_progress_tasks_owned_by_dead_agent(
        self, tmp_path, make_dossier, mock_process_alive,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        slug = make_dossier(tasks=[{"subject": "t1"}])["slug"]
        _seed_stale_registration(tmp_path, slug, cli_pid=4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ? WHERE id = 1",
                ("orch-claude-code-stale",),
            )
            conn.commit()
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        mock_process_alive({4242: False})
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            row = conn.execute("SELECT status, owner FROM tasks WHERE id = 1").fetchone()
        assert row["status"] == "pending"
        assert row["owner"] is None

    def test_preserves_non_in_progress_tasks(
        self, tmp_path, make_dossier, mock_process_alive,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        slug = make_dossier(tasks=[{"subject": "done"}])["slug"]
        _seed_stale_registration(tmp_path, slug, cli_pid=4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'completed', owner = ? WHERE id = 1",
                ("orch-claude-code-stale",),
            )
            conn.commit()
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        mock_process_alive({4242: False})
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            row = conn.execute("SELECT status FROM tasks WHERE id = 1").fetchone()
        assert row["status"] == "completed"

    def test_fresh_registration_not_reaped(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(99999)  # effectively never stale
        set_cleanup_check_interval(0)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "orch-claude-code-fresh", "claude-code", 1)
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass
        rows = _registrations(tmp_path, slug)
        assert any(r["agent_id"] == "orch-claude-code-fresh" for r in rows)


class TestReapLogAudit:
    def test_audit_row_captures_cascade(
        self, tmp_path, make_dossier, mock_process_alive,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        slug = make_dossier(tasks=[{"subject": "t1"}])["slug"]
        claim_lock(tmp_path, slug, agent="orch-claude-code-stale")
        _seed_stale_registration(tmp_path, slug, cli_pid=4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ? WHERE id = 1",
                ("orch-claude-code-stale",),
            )
            conn.commit()
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        mock_process_alive({4242: False})
        with open_dossier_db(safe_db_path(tmp_path, slug)):
            pass

        log = _reap_log(tmp_path, slug)
        assert len(log) == 1
        entry = log[0]
        assert entry["agent_id"] == "orch-claude-code-stale"
        assert entry["agent_type"] == "claude-code"
        assert entry["reap_reason"] == "pid_dead"
        assert entry["lock_released"] == 1
        assert json.loads(entry["tasks_reverted"]) == [1]
        assert entry["stale_by_sec"] > 0


class TestProtectAgentId:
    def test_protected_agent_is_never_reaped(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        # a stale worker (cli_pid None => would be reaped by timestamp)...
        _seed_stale_registration(
            tmp_path, slug, agent_id="claude-code:worker-1:42",
            role="worker", cli_pid=None,
        )
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        # Use a raw connection so connect_dossier_db's own (unprotected) reap
        # preamble doesn't fire first; assert via the same connection so the
        # read-back doesn't auto-reap either.
        conn = sqlite3.connect(safe_db_path(tmp_path, slug))
        conn.row_factory = sqlite3.Row
        try:
            _maybe_reap_stale_registrations(
                conn, protect_agent_id="claude-code:worker-1:42"
            )
            remaining = [
                r["agent_id"] for r in conn.execute("SELECT agent_id FROM registrations")
            ]
        finally:
            conn.close()
        assert "claude-code:worker-1:42" in remaining


class TestFailureIsolation:
    def test_uninitialized_metadata_is_noop(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            conn.execute("DELETE FROM metadata")
            conn.commit()
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            _maybe_reap_stale_registrations(conn)  # must not raise

    def test_swallows_sqlite_error_during_reaping(
        self, tmp_path, make_dossier, set_registration_ttl, set_cleanup_check_interval
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(1)
        set_cleanup_check_interval(0)
        _seed_stale_registration(tmp_path, slug, role="worker", cli_pid=None)

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
            _maybe_reap_stale_registrations(wrapped)  # must not raise

    def test_does_not_swallow_non_sqlite_errors(
        self, tmp_path, make_dossier, monkeypatch,
        set_registration_ttl, set_cleanup_check_interval,
    ):
        slug = make_dossier()["slug"]
        set_registration_ttl(1)
        set_cleanup_check_interval(0)

        def _boom():
            raise TypeError("programming bug")

        monkeypatch.setattr("operations.dossiers.db._now_iso", _boom)
        with pytest.raises(TypeError, match="programming bug"):
            with open_dossier_db(safe_db_path(tmp_path, slug)):
                pass
