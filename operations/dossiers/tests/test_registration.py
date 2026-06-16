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
            "SELECT agent_id, agent_type, cli_pid, role, registered_at, last_heartbeat "
            "FROM registrations"
        ).fetchall()]


class TestRegisterAgent:
    def test_inserts_orchestrator_by_default(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with conn:  # caller owns the txn (register_agent does not commit)
                register_agent(conn, "orch-claude-code-aaaa", "claude-code", 12345)
        rows = _all_rows(tmp_path, slug)
        assert len(rows) == 1
        assert rows[0]["agent_id"] == "orch-claude-code-aaaa"
        assert rows[0]["role"] == "orchestrator"
        assert rows[0]["cli_pid"] == 12345
        # both timestamps stamped at insert
        assert rows[0]["registered_at"] == rows[0]["last_heartbeat"]

    def test_worker_role_persists_with_null_cli_pid(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with conn:  # caller owns the txn (register_agent does not commit)
                register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
        rows = _all_rows(tmp_path, slug)
        assert rows[0]["role"] == "worker"
        assert rows[0]["cli_pid"] is None

    def test_duplicate_agent_id_raises_integrity_error(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "orch-claude-code-aaaa", "claude-code", 1)
            with pytest.raises(sqlite3.IntegrityError):
                register_agent(conn, "orch-claude-code-aaaa", "claude-code", 2)

    def test_second_orchestrator_of_type_violates_partial_unique(
        self, tmp_path, make_dossier
    ):
        # the load-bearing invariant: one orchestrator per agent_type per dossier
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "orch-claude-code-aaaa", "claude-code", 1)
            with pytest.raises(sqlite3.IntegrityError):
                register_agent(conn, "orch-claude-code-bbbb", "claude-code", 2)


class TestDeregisterAgent:
    def test_deletes_matching_row(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with conn:  # caller owns the txn (CRUD does not commit)
                register_agent(conn, "orch-claude-code-aaaa", "claude-code", 1)
                deregister_agent(conn, "orch-claude-code-aaaa")
        assert _all_rows(tmp_path, slug) == []

    def test_missing_agent_is_noop(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            deregister_agent(conn, "nobody")
        assert _all_rows(tmp_path, slug) == []


class TestRefreshHeartbeat:
    def test_refreshes_last_heartbeat_not_registered_at(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "orch-claude-code-aaaa", "claude-code", 1)
            born = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?",
                ("orch-claude-code-aaaa",),
            ).fetchone()["registered_at"]
            # force an old heartbeat, then refresh
            conn.execute(
                "UPDATE registrations SET last_heartbeat = '2020-01-01T00:00:00Z' "
                "WHERE agent_id = ?",
                ("orch-claude-code-aaaa",),
            )
            conn.commit()
            refresh_heartbeat(conn, "orch-claude-code-aaaa")
            row = conn.execute(
                "SELECT registered_at, last_heartbeat FROM registrations WHERE agent_id = ?",
                ("orch-claude-code-aaaa",),
            ).fetchone()
        assert row["last_heartbeat"] > "2020-01-01T00:00:00Z"  # refreshed
        assert row["registered_at"] == born                    # set-once untouched

    def test_missing_agent_is_noop(self, tmp_path, make_dossier):
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
            register_agent(conn, "orch-codex-cccc", "codex", 3)
            register_agent(conn, "orch-claude-code-aaaa", "claude-code", 1)
            register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
            agents = list_agents(conn)

        # claude-code before codex; orchestrator before worker within claude-code
        assert [a["agent_id"] for a in agents] == [
            "orch-claude-code-aaaa",
            "claude-code:worker-1:42",
            "orch-codex-cccc",
        ]
        # display fields present
        assert {"cli_pid", "registered_at", "last_heartbeat"} <= set(agents[0].keys())


class TestMaybeDeregisterWorker:
    def test_noop_when_agent_not_registered(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            assert _maybe_deregister_worker(conn, "nobody") is False

    def test_noop_on_orchestrator(self, tmp_path, make_dossier):
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with conn:  # caller owns the txn (register_agent does not commit)
                register_agent(conn, "orch-claude-code-aaaa", "claude-code", 1)
            assert _maybe_deregister_worker(conn, "orch-claude-code-aaaa") is False
        assert len(_all_rows(tmp_path, slug)) == 1

    def test_deregisters_worker_with_no_in_progress_tasks(self, tmp_path, make_dossier):
        slug = make_dossier(tasks=[{"subject": "t1"}])["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with conn:  # caller owns the txn (CRUD does not commit)
                register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
                assert _maybe_deregister_worker(conn, "claude-code:worker-1:42") is True
        assert _all_rows(tmp_path, slug) == []

    def test_keeps_worker_with_active_in_progress_task(self, tmp_path, make_dossier):
        slug = make_dossier(tasks=[{"subject": "t1"}, {"subject": "t2"}])["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "claude-code:worker-1:42", "claude-code", None, role="worker")
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', owner = ? WHERE id = 1",
                ("claude-code:worker-1:42",),
            )
            conn.commit()
            assert _maybe_deregister_worker(conn, "claude-code:worker-1:42") is False
        assert len(_all_rows(tmp_path, slug)) == 1
