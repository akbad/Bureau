"""Tests for registration table CRUD (``operations/dossiers/registration.py``)."""
import sqlite3
from pathlib import Path

import pytest

from operations.dossiers.db import open_dossier_db, safe_db_path
from operations.dossiers.registration import (
    _maybe_deregister_worker,
    deregister_agent,
    list_agents,
    refresh_heartbeat,
    register_agent,
)


def _all_rows(tmp_path: Path, slug: str) -> list[dict]:
    with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT agent_id, agent_type, ppid, role, registered_at FROM registrations"
        ).fetchall()]


class TestRegisterAgent:
    def test_inserts_orchestrator_by_default(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:a7f3c2", "claude-code", 12345)
        rows = _all_rows(tmp_path, slug)
        assert len(rows) == 1
        assert rows[0]["agent_id"] == "claude-code:a7f3c2"
        assert rows[0]["role"] == "orchestrator"
        assert rows[0]["ppid"] == 12345

    def test_worker_role_persists(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
        rows = _all_rows(tmp_path, slug)
        assert rows[0]["role"] == "worker"
        assert rows[0]["ppid"] is None

    def test_duplicate_agent_id_raises_integrity_error(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:a7f3c2", "claude-code", 1)
            with pytest.raises(sqlite3.IntegrityError):
                register_agent(conn, "claude-code:a7f3c2", "claude-code", 2)


class TestDeregisterAgent:
    def test_deletes_matching_row(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:a7f3c2", "claude-code", 1)
            deregister_agent(conn, "claude-code:a7f3c2")
        assert _all_rows(tmp_path, slug) == []

    def test_missing_agent_is_noop(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            deregister_agent(conn, "nobody")
        assert _all_rows(tmp_path, slug) == []


class TestRefreshHeartbeat:
    def test_updates_registered_at(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:a7f3c2", "claude-code", 1)
            # force an older timestamp, then refresh
            conn.execute(
                "UPDATE registrations SET registered_at = '2020-01-01T00:00:00Z' "
                "WHERE agent_id = ?",
                ("claude-code:a7f3c2",),
            )
            conn.commit()
            refresh_heartbeat(conn, "claude-code:a7f3c2")
            row = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?",
                ("claude-code:a7f3c2",),
            ).fetchone()
        # refreshed timestamp is later than the seeded value
        assert row["registered_at"] > "2020-01-01T00:00:00Z"

    def test_missing_agent_is_noop(self, tmp_path, make_dossier):
        # refresh on a non-existent agent just matches zero rows, no raise
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            refresh_heartbeat(conn, "nobody")


class TestListAgents:
    def test_empty_when_no_registrations(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert list_agents(conn) == []

    def test_orderings_type_then_role_then_registered(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "codex:b91e3d", "codex", 3)
            register_agent(conn, "claude-code:a7f3c2", "claude-code", 1)
            register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
            agents = list_agents(conn)

        # claude-code before codex; orchestrator before worker within claude-code
        assert [a["agent_id"] for a in agents] == [
            "claude-code:a7f3c2",
            "claude-code:worker-1:42",
            "codex:b91e3d",
        ]


class TestMaybeDeregisterWorker:
    def test_noop_when_agent_not_registered(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert _maybe_deregister_worker(conn, "nobody") is False

    def test_noop_on_orchestrator(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:a7f3c2", "claude-code", 1)
            assert _maybe_deregister_worker(conn, "claude-code:a7f3c2") is False
        assert len(_all_rows(tmp_path, slug)) == 1

    def test_deregisters_worker_with_no_in_progress_tasks(
        self, tmp_path, make_dossier
    ):
        slug = make_dossier(tasks=[{"subject": "t1"}])["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
            assert _maybe_deregister_worker(conn, "claude-code:worker-1:42") is True
        assert _all_rows(tmp_path, slug) == []

    def test_keeps_worker_with_active_in_progress_task(
        self, tmp_path, make_dossier
    ):
        slug = make_dossier(tasks=[{"subject": "t1"}, {"subject": "t2"}])["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
            # simulate the worker owning one in_progress task
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ? WHERE id = 1",
                ("claude-code:worker-1:42",),
            )
            conn.commit()
            assert _maybe_deregister_worker(conn, "claude-code:worker-1:42") is False
        # still registered
        assert len(_all_rows(tmp_path, slug)) == 1
