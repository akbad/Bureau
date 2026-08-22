"""Tests for v3 single-store identity resolution and liveness checks."""
import os

import pytest

from operations.dossiers.db import _process_alive, open_dossier_db, safe_db_path
from operations.dossiers.errors import ConcurrentInstanceError
from operations.dossiers.identity import (
    MAX_RESOLVE_ATTEMPTS,
    _get_cli_process_pid,
    _orchestrator_agent_id,
    _ppid_via_proc,
    _ppid_via_ps,
    resolve_identity,
    resolve_worker_identity,
)
from operations.dossiers.registration import register_agent


# ── _get_cli_process_pid: the layered chain ─────────────────────────────


class TestGetCliProcessPid:
    def test_returns_positive_integer(self):
        pid = _get_cli_process_pid()
        assert isinstance(pid, int)
        assert pid > 0

    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("BUREAU_CLI_PID", "424242")
        assert _get_cli_process_pid() == 424242

    def test_non_integer_env_is_ignored(self, monkeypatch):
        monkeypatch.setenv("BUREAU_CLI_PID", "not-a-pid")
        # falls through to the ancestor chain / degrade; just needs to be valid
        assert _get_cli_process_pid() > 0

    def test_degrades_to_shell_pid_when_proc_and_ps_fail(self, monkeypatch):
        monkeypatch.delenv("BUREAU_CLI_PID", raising=False)
        monkeypatch.setattr("operations.dossiers.identity._ppid_via_proc", lambda pid: None)
        monkeypatch.setattr("operations.dossiers.identity._ppid_via_ps", lambda pid: None)
        assert _get_cli_process_pid() == os.getppid()

    def test_prefers_proc_over_ps(self, monkeypatch):
        monkeypatch.delenv("BUREAU_CLI_PID", raising=False)
        monkeypatch.setattr("operations.dossiers.identity._ppid_via_proc", lambda pid: 31337)
        monkeypatch.setattr("operations.dossiers.identity._ppid_via_ps", lambda pid: 9999)
        assert _get_cli_process_pid() == 31337


class TestPpidParsers:
    def test_ps_returns_int_or_none(self):
        # the shell's parent should resolve to a positive pid on this host
        result = _ppid_via_ps(os.getppid())
        assert result is None or result > 0

    def test_proc_handles_missing_path(self):
        # macOS has no /proc; on Linux a bogus pid has no stat file
        assert _ppid_via_proc(999_999_999) is None


# ── _process_alive (oracle lives in db, re-exported via identity) ────────


class TestProcessAlive:
    def test_own_pid_is_alive(self):
        assert _process_alive(os.getpid()) is True

    def test_nonexistent_pid_is_dead(self):
        assert _process_alive(999_999_999) is False

    def test_none_pid_is_dead(self):
        # worker with no recorded cli_pid => timestamp-only handling
        assert _process_alive(None) is False

    def test_zero_and_negative_pid_are_dead(self):
        assert _process_alive(0) is False
        assert _process_alive(-1) is False

    def test_permission_error_treated_as_alive(self, monkeypatch):
        def _raise_permission(pid, sig):
            raise PermissionError("not allowed")
        monkeypatch.setattr("operations.dossiers.db.os.kill", _raise_permission)
        assert _process_alive(12345) is True


# ── _orchestrator_agent_id: deterministic, slot-keyed ───────────────────


class TestOrchestratorAgentId:
    def test_format(self):
        agent_id = _orchestrator_agent_id("my-slug", "claude-code")
        assert agent_id.startswith("orch-claude-code-")
        suffix = agent_id.rsplit("-", 1)[1]
        assert len(suffix) == 16
        int(suffix, 16)  # parses as hex

    def test_deterministic(self):
        assert _orchestrator_agent_id("s", "claude-code") == _orchestrator_agent_id("s", "claude-code")

    def test_distinct_per_slug_and_type(self):
        ids = {
            _orchestrator_agent_id("s1", "claude-code"),
            _orchestrator_agent_id("s2", "claude-code"),
            _orchestrator_agent_id("s1", "codex"),
        }
        assert len(ids) == 3


# ── resolve_identity: the collapsed state machine ───────────────────────


class TestResolveIdentityFresh:
    def test_inserts_orchestrator_row_with_split_timestamps(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        mock_cli_pid(11111)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            agent_id = resolve_identity(conn, slug, "claude-code")

            assert agent_id == _orchestrator_agent_id(slug, "claude-code")
            row = conn.execute(
                "SELECT agent_type, cli_pid, role, registered_at, last_heartbeat "
                "FROM registrations WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            assert row["agent_type"] == "claude-code"
            assert row["cli_pid"] == 11111
            assert row["role"] == "orchestrator"
            # set-once registered_at == first last_heartbeat on a fresh insert
            assert row["registered_at"] == row["last_heartbeat"]


class TestResolveIdentitySameSession:
    def test_same_id_refreshes_heartbeat_not_registered_at(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        mock_cli_pid(22222)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            first = resolve_identity(conn, slug, "claude-code")
            born = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?", (first,)
            ).fetchone()["registered_at"]
            # force a later heartbeat so the timestamps would differ if touched
            conn.execute(
                "UPDATE registrations SET last_heartbeat = '2000-01-01T00:00:00Z' "
                "WHERE agent_id = ?",
                (first,),
            )
            conn.commit()
            second = resolve_identity(conn, slug, "claude-code")
            row = conn.execute(
                "SELECT registered_at, last_heartbeat FROM registrations WHERE agent_id = ?",
                (second,),
            ).fetchone()

        assert first == second
        assert row["registered_at"] == born          # set-once preserved
        assert row["last_heartbeat"] > "2000-01-01T00:00:00Z"  # heartbeat refreshed


class TestResolveIdentityConcurrent:
    def test_raises_when_other_pid_alive(
        self, tmp_path, make_dossier, mock_cli_pid, mock_process_alive
    ):
        mock_cli_pid(33333)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            resolve_identity(conn, slug, "claude-code")

        mock_cli_pid(44444)
        mock_process_alive({33333: True})
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with pytest.raises(ConcurrentInstanceError, match="cli_pid=33333"):
                resolve_identity(conn, slug, "claude-code")


class TestResolveIdentityAdopt:
    def test_adopts_dead_pid_preserving_id_and_registered_at(
        self, tmp_path, make_dossier, mock_cli_pid, mock_process_alive
    ):
        mock_cli_pid(55555)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            original = resolve_identity(conn, slug, "claude-code")
            born = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?", (original,)
            ).fetchone()["registered_at"]

        # CLI relaunches with a new pid; the old pid is dead
        mock_cli_pid(66666)
        mock_process_alive({55555: False})
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            adopted = resolve_identity(conn, slug, "claude-code")
            row = conn.execute(
                "SELECT cli_pid, registered_at FROM registrations WHERE agent_id = ?",
                (adopted,),
            ).fetchone()

        assert adopted == original           # deterministic id is continuous
        assert row["cli_pid"] == 66666       # cli_pid taken over
        assert row["registered_at"] == born  # identity birth time preserved


class TestResolveIdentityIndependentTypes:
    def test_distinct_types_coexist(self, tmp_path, make_dossier, mock_cli_pid):
        mock_cli_pid(88888)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            claude = resolve_identity(conn, slug, "claude-code")
            codex = resolve_identity(conn, slug, "codex")

        assert claude.startswith("orch-claude-code-")
        assert codex.startswith("orch-codex-")
        assert claude != codex


class TestResolveIdentityMechanism1:
    def test_identity_reset_warning_on_insert_after_recent_reap(
        self, tmp_path, make_dossier, mock_cli_pid, caplog
    ):
        mock_cli_pid(99999)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            # simulate a reap of this agent_type moments ago
            conn.execute(
                "INSERT INTO reap_log (reaped_at, agent_id, agent_type, role, "
                "last_heartbeat, stale_by_sec, tasks_reverted, lock_released, reap_reason) "
                "VALUES (datetime('now'), 'orch-claude-code-deadbeefdeadbeef', "
                "'claude-code', 'orchestrator', '2020-01-01T00:00:00Z', 9000, "
                "'[7, 8]', 1, 'pid_dead')",
            )
            conn.commit()
            with caplog.at_level("WARNING"):
                resolve_identity(conn, slug, "claude-code")

        assert "IDENTITY RESET" in caplog.text
        assert "[7, 8]" in caplog.text

    def test_no_warning_on_clean_fresh_insert(
        self, tmp_path, make_dossier, mock_cli_pid, caplog
    ):
        mock_cli_pid(99999)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with caplog.at_level("WARNING"):
                resolve_identity(conn, slug, "claude-code")
        assert "IDENTITY RESET" not in caplog.text


class TestResolveIdentityConvergence:
    def test_raises_runtime_error_when_adopt_loop_never_converges(
        self, tmp_path, make_dossier, mock_cli_pid, mock_process_alive
    ):
        # Seed a dead-pid slot so every attempt enters the adopt branch, then
        # make every adopt CAS miss (proxy skips the UPDATE and reports
        # rowcount 0) — simulating perpetual adopt-race contention. The slot's
        # cli_pid stays dead across iterations, so the bounded loop must give up.
        mock_cli_pid(70000)
        slug = make_dossier()["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            resolve_identity(conn, slug, "claude-code")
            conn.execute("UPDATE registrations SET cli_pid = 12345")  # a dead pid
            conn.commit()
            mock_cli_pid(70001)
            mock_process_alive({12345: False})

            class _AdoptNeverWins:
                """Proxy that never lets the adopt CAS succeed (rowcount 0)."""

                def __init__(self, real):
                    self._real = real

                def execute(self, sql, *args, **kwargs):
                    if sql.lstrip().upper().startswith("UPDATE REGISTRATIONS SET CLI_PID"):
                        class _Zero:
                            rowcount = 0
                        return _Zero()  # skip the write entirely; slot stays dead
                    return self._real.execute(sql, *args, **kwargs)

                def commit(self):
                    return self._real.commit()

                def __getattr__(self, name):
                    return getattr(self._real, name)

            with pytest.raises(RuntimeError, match="did not converge"):
                resolve_identity(_AdoptNeverWins(conn), slug, "claude-code")


# ── resolve_worker_identity: the worker-role counterpart ─────────────────


class TestResolveWorkerIdentity:
    """Workers get the same connect-time refresh orchestrators already had.

    `resolve_identity` establishes and refreshes an orchestrator's row before
    the reap can consider it. Without an equivalent for workers their heartbeat
    never moves and their `cli_pid` stays NULL, which is the pair of gaps that
    lets an active worker be reaped.
    """

    def _seed_worker(self, conn, agent_id="claude-code:worker-1:42", cli_pid=None):
        register_agent(conn, agent_id, agent_id.split(":", 1)[0], cli_pid, role="worker")
        conn.execute(
            "UPDATE registrations SET last_heartbeat = '2020-01-01T00:00:00Z' "
            "WHERE agent_id = ?",
            (agent_id,),
        )
        conn.commit()

    def test_refreshes_heartbeat_and_adopts_cli_pid(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        slug = make_dossier()["slug"]
        mock_cli_pid(4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            self._seed_worker(conn)
            returned = resolve_worker_identity(conn, "claude-code:worker-1:42")
            row = conn.execute(
                "SELECT cli_pid, last_heartbeat FROM registrations WHERE agent_id = ?",
                ("claude-code:worker-1:42",),
            ).fetchone()
        assert returned == "claude-code:worker-1:42"
        assert row["cli_pid"] == 4242                          # NULL row healed
        assert row["last_heartbeat"] > "2020-01-01T00:00:00Z"  # heartbeat moved

    def test_leaves_registered_at_untouched(self, tmp_path, make_dossier, mock_cli_pid):
        slug = make_dossier()["slug"]
        mock_cli_pid(4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            self._seed_worker(conn)
            born = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?",
                ("claude-code:worker-1:42",),
            ).fetchone()["registered_at"]
            resolve_worker_identity(conn, "claude-code:worker-1:42")
            row = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?",
                ("claude-code:worker-1:42",),
            ).fetchone()
        assert row["registered_at"] == born  # set-once birth time

    def test_never_touches_an_orchestrator_row(self, tmp_path, make_dossier, mock_cli_pid):
        # the role guard: routing an orchestrator id through the worker path must
        # not stomp its cli_pid, which would bypass the concurrent-instance check
        slug = make_dossier()["slug"]
        mock_cli_pid(4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            register_agent(conn, "orch-claude-code-aaaa", "claude-code", 999)
            conn.commit()
            resolve_worker_identity(conn, "orch-claude-code-aaaa")
            row = conn.execute(
                "SELECT cli_pid FROM registrations WHERE agent_id = ?",
                ("orch-claude-code-aaaa",),
            ).fetchone()
        assert row["cli_pid"] == 999  # untouched

    def test_missing_row_is_noop_and_still_returns_the_id(
        self, tmp_path, make_dossier, mock_cli_pid
    ):
        # `unfold --worker` resolves the label BEFORE claim_task inserts the row
        slug = make_dossier()["slug"]
        mock_cli_pid(4242)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            returned = resolve_worker_identity(conn, "claude-code:worker-9:42")
            rows = conn.execute("SELECT * FROM registrations").fetchall()
        assert returned == "claude-code:worker-9:42"
        assert rows == []
