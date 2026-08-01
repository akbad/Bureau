import json
import subprocess
from importlib import util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "managed-mcp-registry.py"
# repo root, needed so the e2e CLI-boundary test can invoke the script the
# same way set-up-tools.sh does (`uv run python <script>`, run from repo root
# so the script's `from operations...` import resolves)
_REPO_ROOT = Path(__file__).resolve().parents[3]
spec = util.spec_from_file_location("managed_mcp_registry", module_path)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

normalize_entry = module.normalize_entry
normalize_desired_entry = module.normalize_desired_entry
fingerprint_entry = module.fingerprint_entry
compute_prune = module.compute_prune
compute_update = module.compute_update
record_registry = module.record_registry
should_preserve_registry = module.should_preserve_registry
load_cli_entries = module.load_cli_entries
load_registry = module.load_registry
write_registry = module.write_registry


def test_normalize_entries_across_clis():
    assert normalize_entry(
        "claude",
        {"type": "http", "url": "http://x", "headers": {"A": "b"}},
    ) == {"transport": "http", "url": "http://x", "headers": {"A": "b"}}

    assert normalize_entry(
        "gemini",
        {
            "command": "uvx",
            "args": ["mcp"],
            "env": {"A": "b"},
            "timeout": 123,
        },
    ) == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp"],
        "env": {"A": "b"},
        "timeout_ms": 123,
    }

    assert normalize_entry(
        "codex",
        {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp"],
            "env": {"A": "b"},
            "startup_timeout_sec": 5,
            "tool_timeout_sec": 9,
        },
    ) == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp"],
        "env": {"A": "b"},
        "startup_timeout_sec": 5,
        "tool_timeout_sec": 9,
    }

    assert normalize_entry(
        "codex",
        {
            "url": "http://x",
            "bearer_token_env_var": "GITHUB_PAT",
        },
    ) == {
        "transport": "http",
        "url": "http://x",
        "bearer_token_env_var": "GITHUB_PAT",
    }

    assert normalize_entry(
        "codex",
        {
            "command": "uvx",
            "args": ["mcp"],
            "env": {"A": "b"},
        },
    ) == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp"],
        "env": {"A": "b"},
    }

    assert normalize_entry(
        "opencode",
        {
            "type": "local",
            "command": ["uvx", "mcp"],
            "environment": {"A": "b"},
            "timeout": 2500,
        },
    ) == {
        "transport": "stdio",
        "command": ["uvx", "mcp"],
        "env": {"A": "b"},
        "timeout_ms": 2500,
    }

    assert normalize_entry(
        "grok",
        {
            "url": "http://localhost:8782/mcp/",
            "headers": {"Authorization": "Bearer x"},
            "enabled": True,
        },
    ) == {
        "transport": "http",
        "url": "http://localhost:8782/mcp/",
        "headers": {"Authorization": "Bearer x"},
    }

    assert normalize_entry(
        "grok",
        {
            "command": "uvx",
            "args": ["mcp-server-fetch"],
            "env": {"A": "b"},
            "startup_timeout_sec": 30,
        },
    ) == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {"A": "b"},
        "startup_timeout_sec": 30,
    }


def test_fingerprint_stable_for_same_input():
    normalized = {"transport": "http", "url": "http://x"}
    assert fingerprint_entry(normalized) == fingerprint_entry(normalized)


def test_compute_prune_only_removes_matching_fingerprints():
    plan = {"client_configs": {"claude": {"keep": {}}}}
    current_entries = {
        "keep": {"type": "http", "url": "http://keep"},
        "remove": {"type": "http", "url": "http://remove"},
        "changed": {"type": "http", "url": "http://changed"},
    }
    registry = {
        "version": 1,
        "servers": {
            "remove": {
                "fingerprint": fingerprint_entry(
                    normalize_entry("claude", current_entries["remove"])
                )
            },
            "changed": {
                "fingerprint": "not-the-same",
            },
            "missing": {
                "fingerprint": "irrelevant",
            },
        },
    }

    to_remove = compute_prune("claude", plan, registry, current_entries)

    assert to_remove == ["remove"]


def test_normalize_desired_entry_for_codex_stdio():
    desired = normalize_desired_entry(
        "codex",
        {
            "transport": "stdio",
            "command": ["/tmp/mcp-filter", "--include", "read_multiple_files"],
            "env": {"A": "b"},
            "startup_timeout_sec": 5,
            "tool_timeout_sec": 9,
        },
    )

    assert desired == {
        "transport": "stdio",
        "command": "/tmp/mcp-filter",
        "args": ["--include", "read_multiple_files"],
        "env": {"A": "b"},
        "startup_timeout_sec": 5,
        "tool_timeout_sec": 9,
    }


def test_normalize_desired_entry_for_codex_http():
    desired = normalize_desired_entry(
        "codex",
        {
            "transport": "http",
            "url": "https://api.githubcopilot.com/mcp/",
            "bearer_token_env_var": "GITHUB_PAT",
        },
    )

    assert desired == {
        "transport": "http",
        "url": "https://api.githubcopilot.com/mcp/",
        "bearer_token_env_var": "GITHUB_PAT",
    }


def test_normalize_desired_entry_for_grok_http_and_stdio():
    http = normalize_desired_entry(
        "grok",
        {
            "transport": "http",
            "url": "http://localhost:8782/mcp/",
            "headers": {"A": "b"},
        },
    )
    assert http == {
        "transport": "http",
        "url": "http://localhost:8782/mcp/",
        "headers": {"A": "b"},
    }

    stdio = normalize_desired_entry(
        "grok",
        {
            "transport": "stdio",
            "command": ["uvx", "mcp-server-fetch"],
            "env": {"A": "b"},
            "startup_timeout_sec": 30,
            "tool_timeout_sec": 120,
        },
    )
    assert stdio == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {"A": "b"},
        "startup_timeout_sec": 30,
        "tool_timeout_sec": 120,
    }


def test_normalize_desired_entry_for_opencode_stdio():
    desired = normalize_desired_entry(
        "opencode",
        {
            "transport": "stdio",
            "command": ["npx", "-y", "open-websearch@2.1.7"],
            "env": {"MODE": "stdio"},
            "timeout_ms": 45000,
        },
    )

    assert desired == {
        "transport": "stdio",
        "command": ["npx", "-y", "open-websearch@2.1.7"],
        "env": {"MODE": "stdio"},
        "timeout_ms": 45000,
    }


def test_opencode_local_fingerprint_tracks_environment_and_timeout():
    base = normalize_entry(
        "opencode",
        {
            "type": "local",
            "command": ["npx", "-y", "open-websearch@2.1.7"],
            "environment": {"MODE": "stdio"},
            "timeout": 45000,
        },
    )
    changed_env = normalize_entry(
        "opencode",
        {
            "type": "local",
            "command": ["npx", "-y", "open-websearch@2.1.7"],
            "environment": {"MODE": "http"},
            "timeout": 45000,
        },
    )
    changed_timeout = normalize_entry(
        "opencode",
        {
            "type": "local",
            "command": ["npx", "-y", "open-websearch@2.1.7"],
            "environment": {"MODE": "stdio"},
            "timeout": 90000,
        },
    )

    assert fingerprint_entry(base) != fingerprint_entry(changed_env)
    assert fingerprint_entry(base) != fingerprint_entry(changed_timeout)


def test_compute_update_marks_managed_entry_when_desired_changes():
    current_entries = {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-filter", "--include", "read_multiple_files"],
            "startup_timeout_sec": 30,
        }
    }
    plan = {
        "client_configs": {
            "codex": {
                "filesystem": {
                    "transport": "stdio",
                    "command": [
                        "/shared/.mcp-servers/npm-tools/node_modules/.bin/mcp-filter",
                        "--include",
                        "read_multiple_files",
                    ],
                    "startup_timeout_sec": 30,
                }
            }
        }
    }
    registry = {
        "version": 1,
        "servers": {
            "filesystem": {
                "fingerprint": fingerprint_entry(
                    normalize_entry("codex", current_entries["filesystem"])
                )
            }
        },
    }

    to_update = compute_update("codex", plan, registry, current_entries)

    assert to_update == ["filesystem"]


def test_compute_update_skips_user_modified_entry():
    current_entries = {
        "filesystem": {
            "transport": "stdio",
            "command": "custom-wrapper",
            "args": ["filesystem"],
        }
    }
    plan = {
        "client_configs": {
            "codex": {
                "filesystem": {
                    "transport": "stdio",
                    "command": ["/shared/.mcp-servers/npm-tools/node_modules/.bin/mcp-filter"],
                }
            }
        }
    }
    registry = {
        "version": 1,
        "servers": {
            "filesystem": {
                "fingerprint": fingerprint_entry(
                    {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "mcp-filter"],
                    }
                )
            }
        },
    }

    to_update = compute_update("codex", plan, registry, current_entries)

    assert to_update == []


def test_record_from_empty_registry_tracks_present_desired_entries():
    # starting from an empty registry, only a write-confirmed desired entry
    # that actually exists in the live config is recorded (a desired-but-absent
    # entry is skipped even though it's in written_ids)
    plan = {"client_configs": {"gemini": {"keep": {}, "missing": {}}}}
    current_entries = {
        "keep": {"httpUrl": "http://keep"},
    }

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        {"version": 1, "servers": {}},
        written_ids={"keep", "missing"},
        now="2026-01-01T00:00:00+00:00",
    )

    assert recorded["version"] == 1
    assert recorded["updated_at"] == "2026-01-01T00:00:00+00:00"
    assert list(recorded["servers"].keys()) == ["keep"]


def test_record_registry_tracks_legacy_codex_entries():
    plan = {
        "client_configs": {
            "codex": {
                "github": {
                    "transport": "http",
                    "url": "https://api.githubcopilot.com/mcp/",
                    "bearer_token_env_var": "GITHUB_PAT",
                },
                "filesystem": {
                    "transport": "stdio",
                    "command": ["/tmp/mcp-filter", "--include", "read_multiple_files"],
                },
            }
        }
    }
    current_entries = {
        "github": {
            "url": "https://api.githubcopilot.com/mcp/",
            "bearer_token_env_var": "GITHUB_PAT",
        },
        "filesystem": {
            "command": "/tmp/mcp-filter",
            "args": ["--include", "read_multiple_files"],
        },
    }

    recorded = record_registry(
        "codex",
        plan,
        current_entries,
        {"version": 1, "servers": {}},
        written_ids={"github", "filesystem"},
        now="2026-01-01T00:00:00+00:00",
    )

    assert list(recorded["servers"].keys()) == ["filesystem", "github"]


def test_record_retains_undesired_entry_while_still_in_config():
    # regression for C5: an entry dropped from the plan but still physically
    # present in the live config (e.g. its `mcp remove` failed) must stay in the
    # registry so compute_prune can retry it, instead of being forgotten and
    # stranded as a permanently unprunable orphan
    live_foo = {"httpUrl": "http://foo"}
    foo_fp = fingerprint_entry(normalize_entry("gemini", live_foo))
    previous_registry = {
        "version": 1,
        "servers": {
            "keep": {"fingerprint": "irrelevant"},
            "foo": {"fingerprint": foo_fp},
        },
    }
    plan = {"client_configs": {"gemini": {"keep": {}}}}  # foo no longer desired
    current_entries = {
        "keep": {"httpUrl": "http://keep"},
        "foo": live_foo,  # removal failed this run: foo is still present
    }

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids=set(),  # nothing written this run; foo's memory is pure carry-forward
        now="2026-01-01T00:00:00+00:00",
    )

    # foo is retained, flagged retired, and keeps its still-matching fingerprint
    assert "foo" in recorded["servers"]
    assert recorded["servers"]["foo"]["retired"] is True
    assert recorded["servers"]["foo"]["fingerprint"] == foo_fp
    # and it therefore remains prunable on the next reconcile pass
    assert compute_prune("gemini", plan, recorded, current_entries) == ["foo"]


def test_record_forgets_entry_once_absent_from_config():
    # once an undesired entry is actually gone from the live config, the
    # registry drops it so tracked state cannot grow without bound
    previous_registry = {
        "version": 1,
        "servers": {"foo": {"fingerprint": "whatever"}},
    }
    plan = {"client_configs": {"gemini": {"keep": {}}}}
    current_entries = {"keep": {"httpUrl": "http://keep"}}  # foo already removed

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids=set(),
        now="2026-01-01T00:00:00+00:00",
    )

    assert "foo" not in recorded["servers"]


def test_record_reactivates_and_refreshes_redesired_entry():
    # an entry that was retired but becomes desired again is re-fingerprinted
    # from its current live form and loses the retired marker. Becoming
    # desired again means the add loop actually re-added it this run, so it
    # is write-confirmed (in written_ids) — see the update-path invariant.
    live_foo = {"httpUrl": "http://foo-v2"}
    previous_registry = {
        "version": 1,
        "servers": {"foo": {"fingerprint": "stale", "retired": True}},
    }
    plan = {"client_configs": {"gemini": {"foo": {}}}}  # foo desired again
    current_entries = {"foo": live_foo}

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids={"foo"},
        now="2026-01-01T00:00:00+00:00",
    )

    assert "retired" not in recorded["servers"]["foo"]
    assert recorded["servers"]["foo"]["fingerprint"] == fingerprint_entry(
        normalize_entry("gemini", live_foo)
    )


def test_preserve_registry_when_config_empty_but_memory_exists():
    # an empty live config while the registry still tracks entries signals a load
    # failure (e.g. a concurrent rewrite left the file unparseable); memory is kept
    assert should_preserve_registry(
        {}, {"version": 1, "servers": {"foo": {"fingerprint": "f"}}}
    ) is True


def test_do_not_preserve_when_config_has_entries():
    # a non-empty read is trustworthy, so record proceeds normally
    assert should_preserve_registry(
        {"keep": {}}, {"version": 1, "servers": {"foo": {"fingerprint": "f"}}}
    ) is False


def test_do_not_preserve_when_no_prior_memory():
    # nothing to lose: an empty config with an empty/absent registry records normally
    assert should_preserve_registry({}, {"version": 1, "servers": {}}) is False
    assert should_preserve_registry({}, {}) is False


def test_record_never_tracks_foreign_entries():
    # entries Bureau never recorded (user-added servers or CLI built-ins) must
    # never be pulled into the registry, even when present and undesired —
    # otherwise the next reconcile could delete a server Bureau does not own
    previous_registry = {"version": 1, "servers": {}}
    plan = {"client_configs": {"gemini": {"keep": {}}}}
    current_entries = {
        "keep": {"httpUrl": "http://keep"},
        "user_added": {"httpUrl": "http://user"},  # never recorded by Bureau
    }

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids=set(),
        now="2026-01-01T00:00:00+00:00",
    )

    assert "user_added" not in recorded["servers"]


# ─────────────────────────────────────────────────────────────────────────
# C6: only ids Bureau actually WROTE this run may be freshly fingerprinted.
#
# Regression coverage for the bug where an "already exists" skip from the
# per-agent add loop (server present, add step did not touch it) was
# indistinguishable, at record time, from a Bureau-written entry — so a
# user's own hand-added server sharing an id with a Bureau catalog entry
# got adopted into the registry and, once no longer desired, deleted by
# compute_prune. See `record_registry`'s `written_ids` parameter and the
# comment on its fingerprinting loop for the full rationale.
# ─────────────────────────────────────────────────────────────────────────


def test_record_tracks_freshly_written_entry():
    # first write: an id the add step just wrote to the live config this run
    # (present, and in written_ids) is recorded — the ordinary happy path
    plan = {"client_configs": {"gemini": {"keep": {}}}}
    live_keep = {"httpUrl": "http://keep"}
    current_entries = {"keep": live_keep}

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        {"version": 1, "servers": {}},
        written_ids={"keep"},
        now="2026-01-01T00:00:00+00:00",
    )

    assert recorded["servers"]["keep"]["fingerprint"] == fingerprint_entry(
        normalize_entry("gemini", live_keep)
    )


def test_record_carries_forward_desired_entry_unwritten_this_run():
    # a Bureau entry written in a PRIOR run: still desired and still present,
    # but the add step found it already there this run (an "already exists"
    # skip, so it's absent from written_ids) — it must stay tracked via
    # carry-forward, not be dropped merely because this run didn't rewrite it
    live_keep = {"httpUrl": "http://keep"}
    keep_fp = fingerprint_entry(normalize_entry("gemini", live_keep))
    previous_registry = {"version": 1, "servers": {"keep": {"fingerprint": keep_fp}}}
    plan = {"client_configs": {"gemini": {"keep": {}}}}
    current_entries = {"keep": live_keep}

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids=set(),  # add step returned "already exists" this run
        now="2026-01-01T00:00:00+00:00",
    )

    assert recorded["servers"]["keep"]["fingerprint"] == keep_fp
    assert "retired" not in recorded["servers"]["keep"]


def test_record_never_adopts_user_collision_the_add_step_skipped():
    # THE C6 safety property: a desired id present in the live config, but
    # the add step returned "already exists" this run (not in written_ids)
    # and Bureau never tracked the id before (not in previous_registry) —
    # this is a user's own hand-added entry that happens to collide with a
    # Bureau catalog id. It must never be recorded, and — because
    # compute_prune only ever acts on recorded fingerprints — must therefore
    # never become prunable.
    plan = {"client_configs": {"gemini": {"github": {}}}}
    current_entries = {
        "github": {"httpUrl": "http://users-own-github-mcp"},  # user's entry
    }
    previous_registry = {"version": 1, "servers": {}}  # Bureau never wrote "github"

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids=set(),  # add step returned "already exists" this run
        now="2026-01-01T00:00:00+00:00",
    )

    assert "github" not in recorded["servers"]
    assert compute_prune("gemini", plan, recorded, current_entries) == []


def test_record_refingerprints_entry_rewritten_by_reconcile_and_readd():
    # update path: managed_registry_reconcile removed the stale entry (see
    # `remove_managed_servers` in set-up-tools.sh) and the per-agent add loop
    # re-added the new desired form this run, landing "github" in
    # written_ids — it must be re-fingerprinted from the NEW live form, not
    # left at its stale recorded fingerprint from before the update
    previous_registry = {
        "version": 1,
        "servers": {"github": {"fingerprint": "stale-fingerprint"}},
    }
    plan = {"client_configs": {"gemini": {"github": {}}}}
    live_github_v2 = {"httpUrl": "http://github-v2"}
    current_entries = {"github": live_github_v2}

    recorded = record_registry(
        "gemini",
        plan,
        current_entries,
        previous_registry,
        written_ids={"github"},
        now="2026-01-01T00:00:00+00:00",
    )

    assert recorded["servers"]["github"]["fingerprint"] == fingerprint_entry(
        normalize_entry("gemini", live_github_v2)
    )


def test_load_grok_entries_from_toml(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[mcp_servers.qdrant]
url = "http://localhost:8782/mcp/"
enabled = true

[mcp_servers.fetch]
command = "uvx"
args = ["mcp-server-fetch"]
""",
        encoding="utf-8",
    )
    entries = load_cli_entries("grok", str(config_path))
    assert entries["qdrant"]["url"] == "http://localhost:8782/mcp/"
    assert entries["fetch"]["command"] == "uvx"
    assert list(entries["fetch"]["args"]) == ["mcp-server-fetch"]


def test_load_codex_entries_from_toml(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[mcp_servers.alpha]
transport = "http"
url = "http://alpha"
""",
        encoding="utf-8",
    )

    entries = load_cli_entries("codex", str(config_path))

    assert entries["alpha"]["transport"] == "http"
    assert entries["alpha"]["url"] == "http://alpha"


def _run_registry_cli(*extra_args: str) -> dict:
    """Invoke `managed-mcp-registry.py` as a real subprocess, `--mode record`.

    This exercises the CLI boundary end to end — argparse's `--written`
    parsing, comma-splitting into a set, and the on-disk registry write —
    the same way `set-up-tools.sh`'s `managed_registry_record` does
    (`uv run python <script> ...` from the repo root), rather than calling
    `record_registry` directly as the unit tests above do. A unit test could
    pass a mis-shaped `written_ids` and never notice a broken `--written`
    flag; this test would catch that.
    """
    result = subprocess.run(
        ["uv", "run", "python", str(module_path), *extra_args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"managed-mcp-registry.py exited {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def test_record_cli_e2e_never_adopts_collision_but_adopts_real_write(tmp_path):
    # e2e / CLI-boundary version of the C6 safety property: a user's own
    # "github" MCP entry collides with a Bureau catalog id of the same name.
    # The add step would have returned "already exists" (not written), so
    # the shell caller passes no --written flag for it this run.
    plan_path = tmp_path / "plan.json"
    registry_path = tmp_path / "registry.json"
    config_path = tmp_path / "claude.json"

    plan_path.write_text(
        json.dumps({"client_configs": {"claude": {"github": {"transport": "http", "url": "http://bureau-github"}}}}),
        encoding="utf-8",
    )
    registry_path.write_text(json.dumps({"version": 1, "servers": {}}), encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "github": {"type": "http", "url": "http://users-own-github-mcp"},
                }
            }
        ),
        encoding="utf-8",
    )

    record_args = [
        "--mode", "record",
        "--cli", "claude",
        "--plan", str(plan_path),
        "--registry", str(registry_path),
        "--config", str(config_path),
    ]

    # run 1: no --written (the add step skipped "github" as "already exists")
    _run_registry_cli(*record_args)
    on_disk = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "github" not in on_disk["servers"], (
        "a user's colliding entry must never be recorded just because it was desired"
    )

    prune_result = _run_registry_cli(
        "--mode", "prune",
        "--cli", "claude",
        "--plan", str(plan_path),
        "--registry", str(registry_path),
        "--config", str(config_path),
    )
    assert prune_result["to_remove"] == [], (
        "an entry that was never recorded must never be nominated for pruning"
    )

    # run 2: Bureau legitimately writes its own "github" entry this run (the
    # id truly is write-confirmed now) — it must be recorded going forward
    config_path.write_text(
        json.dumps({"mcpServers": {"github": {"type": "http", "url": "http://bureau-github"}}}),
        encoding="utf-8",
    )
    _run_registry_cli(*record_args, "--written", "github")
    on_disk = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "github" in on_disk["servers"], (
        "an id Bureau actually wrote this run must be recorded"
    )
