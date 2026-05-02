"""Tests for identity resolution, session marker files, and liveness checks."""
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from operations.dossiers.db import open_dossier_db, safe_db_path
from operations.dossiers.errors import ConcurrentInstanceError
from operations.dossiers.identity import (
    _delete_session_file,
    _generate_agent_id,
    _get_cli_process_pid,
    _process_alive,
    _read_session_file,
    _write_session_file,
    resolve_identity,
    safe_session_file_path,
)


# ── _get_cli_process_pid ────────────────────────────────────────────────


class TestGetCliProcessPid:
    def test_returns_integer(self):
        pid = _get_cli_process_pid()
        assert isinstance(pid, int)
        assert pid > 0

    def test_falls_back_to_shell_pid_on_ps_failure(self, monkeypatch):
        import subprocess

        def _boom(*args, **kwargs):
            raise subprocess.CalledProcessError(1, args[0] if args else [])

        monkeypatch.setattr("operations.dossiers.identity.subprocess.run", _boom)
        pid = _get_cli_process_pid()
        assert pid == os.getppid()


# ── _process_alive ──────────────────────────────────────────────────────


class TestProcessAlive:
    def test_own_pid_is_alive(self):
        assert _process_alive(os.getpid()) is True

    def test_nonexistent_pid_is_dead(self):
        # PIDs in the 99000s are almost never allocated on macOS (max PID 99999)
        # we pick a high value and verify it reads as not-alive
        assert _process_alive(999_999_999) is False

    def test_zero_pid_is_dead(self):
        # guard against os.kill(0, 0) which targets the process group
        assert _process_alive(0) is False

    def test_negative_pid_is_dead(self):
        assert _process_alive(-1) is False

    def test_permission_error_treated_as_alive(self, monkeypatch):
        def _raise_permission(pid, sig):
            raise PermissionError("not allowed")
        monkeypatch.setattr("operations.dossiers.identity.os.kill", _raise_permission)
        assert _process_alive(12345) is True


# ── safe_session_file_path ──────────────────────────────────────────────


class TestSafeSessionFilePath:
    def test_returns_path_under_sessions_root(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "some-slug", "claude-code")
        assert str(path).startswith(str(sessions_root.resolve()))
        assert path.name == "claude-code"

    def test_rejects_slug_escape(self, sessions_root: Path):
        with pytest.raises(ValueError, match="escapes allowed"):
            safe_session_file_path(sessions_root, "../escape", "claude-code")

    def test_rejects_agent_escape(self, sessions_root: Path):
        with pytest.raises(ValueError, match="escapes allowed"):
            safe_session_file_path(sessions_root, "slug", "../../etc/passwd")


# ── session file I/O ────────────────────────────────────────────────────


class TestSessionFileIO:
    def test_write_then_read_roundtrips(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        payload = {"agent_id": "claude-code:a7f3c2", "pid": 12345, "created_at": "2026-04-14T00:00:00Z"}
        _write_session_file(path, payload)
        assert _read_session_file(path) == payload

    def test_read_missing_returns_none(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        assert _read_session_file(path) is None

    def test_read_invalid_json_returns_none(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json")
        assert _read_session_file(path) is None

    def test_read_non_dict_returns_none(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('["list", "not", "dict"]')
        assert _read_session_file(path) is None

    def test_read_missing_keys_returns_none(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"agent_id": "x"}')  # missing pid and created_at
        assert _read_session_file(path) is None

    def test_write_creates_parent_dir_with_0o700(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        _write_session_file(path, {"agent_id": "x", "pid": 1, "created_at": "t"})
        mode = path.parent.stat().st_mode & 0o777
        assert mode == 0o700

    def test_write_creates_file_with_0o600(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        _write_session_file(path, {"agent_id": "x", "pid": 1, "created_at": "t"})
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_write_is_atomic_no_tempfile_left_on_success(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        _write_session_file(path, {"agent_id": "x", "pid": 1, "created_at": "t"})
        tempfiles = [p for p in path.parent.iterdir() if p.name.startswith(".session-")]
        assert tempfiles == []

    def test_delete_is_idempotent(self, sessions_root: Path):
        path = safe_session_file_path(sessions_root, "slug", "claude-code")
        _delete_session_file(path)  # missing path — should not raise
        _write_session_file(path, {"agent_id": "x", "pid": 1, "created_at": "t"})
        _delete_session_file(path)
        assert not path.exists()


# ── _generate_agent_id ──────────────────────────────────────────────────


class TestGenerateAgentId:
    def test_format_is_type_colon_hex(self):
        agent_id = _generate_agent_id("claude-code")
        assert agent_id.startswith("claude-code:")
        suffix = agent_id.split(":", 1)[1]
        assert len(suffix) == 6
        int(suffix, 16)  # must parse as hex

    def test_ids_are_distinct(self):
        ids = {_generate_agent_id("claude-code") for _ in range(200)}
        assert len(ids) == 200


# ── resolve_identity: the four branches ─────────────────────────────────


class TestResolveIdentityFresh:
    def test_creates_session_file_and_registration(
        self, tmp_path, make_dossier, sessions_root, mock_cli_pid
    ):
        mock_cli_pid(11111)
        result = make_dossier()
        slug = result["slug"]
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            agent_id = resolve_identity(conn, sessions_root, slug, "claude-code")

            assert agent_id.startswith("claude-code:")
            row = conn.execute(
                "SELECT agent_type, ppid, role FROM registrations WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            assert row["agent_type"] == "claude-code"
            assert row["ppid"] == 11111
            assert row["role"] == "orchestrator"

        # session file reflects the same identity + pid
        session = _read_session_file(
            safe_session_file_path(sessions_root, slug, "claude-code")
        )
        assert session["agent_id"] == agent_id
        assert session["pid"] == 11111


class TestResolveIdentitySameSession:
    def test_returns_existing_id_and_refreshes_heartbeat(
        self, tmp_path, make_dossier, sessions_root, mock_cli_pid
    ):
        mock_cli_pid(22222)
        slug = make_dossier()["slug"]

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            first = resolve_identity(conn, sessions_root, slug, "claude-code")
            first_ts = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?",
                (first,),
            ).fetchone()["registered_at"]

        # advance state: same PID, next call should be same-session (no new id)
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            second = resolve_identity(conn, sessions_root, slug, "claude-code")
            second_ts = conn.execute(
                "SELECT registered_at FROM registrations WHERE agent_id = ?",
                (second,),
            ).fetchone()["registered_at"]

        assert first == second
        assert second_ts >= first_ts


class TestResolveIdentityConcurrent:
    def test_raises_when_stored_pid_is_alive_and_different(
        self, tmp_path, make_dossier, sessions_root, mock_cli_pid, mock_process_alive
    ):
        mock_cli_pid(33333)
        slug = make_dossier()["slug"]

        # first call creates session file with pid 33333
        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            resolve_identity(conn, sessions_root, slug, "claude-code")

        # second call: different CLI pid, and the stored pid is still "alive"
        mock_cli_pid(44444)
        mock_process_alive({33333: True})

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            with pytest.raises(ConcurrentInstanceError, match="PID 33333"):
                resolve_identity(conn, sessions_root, slug, "claude-code")


class TestResolveIdentityAdopt:
    def test_adopts_when_stored_pid_is_dead(
        self, tmp_path, make_dossier, sessions_root, mock_cli_pid, mock_process_alive
    ):
        mock_cli_pid(55555)
        slug = make_dossier()["slug"]

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            original_id = resolve_identity(conn, sessions_root, slug, "claude-code")

        # CLI relaunches with a new pid; the old pid is no longer alive
        mock_cli_pid(66666)
        mock_process_alive({55555: False})

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            adopted_id = resolve_identity(conn, sessions_root, slug, "claude-code")
            assert adopted_id == original_id

            # registration.ppid was updated to the new pid
            row = conn.execute(
                "SELECT ppid FROM registrations WHERE agent_id = ?",
                (adopted_id,),
            ).fetchone()
            assert row["ppid"] == 66666

        # session file pid was updated
        session = _read_session_file(
            safe_session_file_path(sessions_root, slug, "claude-code")
        )
        assert session["pid"] == 66666
        assert session["agent_id"] == original_id


class TestResolveIdentityCorruption:
    def test_corrupt_session_file_falls_through_to_fresh(
        self, tmp_path, make_dossier, sessions_root, mock_cli_pid
    ):
        mock_cli_pid(77777)
        slug = make_dossier()["slug"]

        # seed a corrupt session file
        path = safe_session_file_path(sessions_root, slug, "claude-code")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid")

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            agent_id = resolve_identity(conn, sessions_root, slug, "claude-code")

        # fresh branch: new identity minted, registration inserted
        assert agent_id.startswith("claude-code:")


class TestResolveIdentityIndependentTypes:
    def test_different_agent_types_get_independent_identities(
        self, tmp_path, make_dossier, sessions_root, mock_cli_pid
    ):
        mock_cli_pid(88888)
        slug = make_dossier()["slug"]

        with open_dossier_db(safe_db_path(tmp_path, slug)) as conn:
            claude_id = resolve_identity(conn, sessions_root, slug, "claude-code")
            codex_id = resolve_identity(conn, sessions_root, slug, "codex")

        assert claude_id.startswith("claude-code:")
        assert codex_id.startswith("codex:")
        assert claude_id != codex_id
