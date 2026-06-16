#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────
# Design rationale
#
# Two-tier hook architecture for supported coding-agent CLIs, including Codex:
#
#   1. SessionStart hooks: run `cat ops-hub.md` once at session start to
#      inject the full ops-hub content into the agent's context.
#   2. Per-prompt hooks: echo a short XML-tagged reminder on every prompt
#      so the agent remembers the ops-hub was already loaded, without
#      re-reading the entire file each turn.
#   3. Codex routing: enable the `features.codex_hooks` flag in
#      `config.toml`, write Bureau hook entries to `hooks.json`, and migrate
#      away any legacy top-level `[[hooks.*]]` TOML blocks.
#
# Each CLI stores its config in a different format (JSON or TOML) and
# uses a different hook schema, so the script dispatches to a per-agent
# handler. Supported per-prompt handlers internally call the session-start
# handler so that a single dispatch sets up both tiers.
#
# Key invariants:
#   - Idempotent: running twice produces the same on-disk state.
#   - Merge-safe: existing hooks from other plugins/user config are
#     preserved.  Only the Bureau ops-hub hook is inserted or updated.
#   - Migration-safe: when searching for existing per-prompt hooks,
#     both old-style ("ops-hub.md" in command) and new-style
#     ("bureau-reminder" in command) patterns are matched so that
#     re-running upgrades the old hook in place.
#   - Codex-safe: configuring Codex enables the supported feature flag,
#     preserves unrelated hooks in `hooks.json`, and removes only Bureau's
#     legacy TOML hook blocks.
#   - No third-party deps: stdlib only (no tomli/toml). The Codex TOML
#     cleanup handler uses line-oriented string operations instead of a TOML lib.
# ─────────────────────────────────────────────────────────────────────
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

LOG = logging.getLogger("configure-hooks")

# hook command timeout in milliseconds, shared across all CLIs
HOOK_TIMEOUT_MS = 5000
HOOK_TIMEOUT_SECONDS = max(1, HOOK_TIMEOUT_MS // 1000)

# sentinel used to identify our per-prompt hook in lists that may contain other hooks
BUREAU_HOOK_NAME = "bureau-ops-hub"

# sentinel used to identify the session-start hook (distinct from per-prompt)
BUREAU_SESSION_HOOK_NAME = "bureau-ops-hub-session"
CODEX_SESSION_STATUS_MESSAGE = "Loading Bureau ops hub"
CODEX_PROMPT_STATUS_MESSAGE = "Loading Bureau reminder"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shared helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cat_command(ops_hub_path: Path) -> str:
    """Build the shell command that cats the ops-hub file."""
    return f"cat {ops_hub_path}"


def _session_start_command(
    ops_hub_path: Path,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
) -> str:
    """Build the shell command that cats all Bureau protocol files at session start.

    Always includes: ops-hub, session-start, task-assessment, task-execution,
    task-completion. Conditionally includes code-standards when provided, and prepends output-style when provided
    (used by Codex/Gemini; Claude handles output style separately).
    """
    ops_dir = ops_hub_path.parent / "ops"
    spoke_files = [
        ops_dir / "session-start.md",
        ops_dir / "task-assessment.md",
        ops_dir / "task-execution.md",
        ops_dir / "task-completion.md",
    ]
    startup_files: list[Path] = []
    if code_standards_path is not None:
        startup_files.append(code_standards_path)
    startup_files.append(ops_hub_path)
    startup_files.extend(spoke_files)
    cat_args = " ".join(str(f) for f in startup_files)
    if output_style_path is not None:
        return f"cat {output_style_path} && cat {cat_args}"
    return f"cat {cat_args}"


def _reminder_command(ops_hub_path: Path) -> str:
    """Build a short echo reminder for per-prompt hooks (avoids re-reading full files)."""
    return (
        "echo '<bureau-reminder>"
        "Bureau protocols loaded at session start. Key rules: "
        "factual accuracy >> speed; query all memory systems before work; "
        "use tool selection table for MCP routing; "
        "activate the `code-standards` skill for code-writing or code-editing tasks; "
        "explicit approval before commits/pushes/deletions; "
        "/fold-dossier to save, /unfold-dossier to resume. "
        "Full details in your session-start context above."
        "</bureau-reminder>'"
    )


def _is_bureau_per_prompt_hook(command: str) -> bool:
    """Return True if *command* belongs to a Bureau per-prompt hook.

    Matches both old-style (contains "ops-hub.md") and new-style (contains
    "bureau-reminder") commands so that re-running the script upgrades the
    old hook in place.
    """
    return "ops-hub.md" in command or "bureau-reminder" in command


def _load_json_config(path: Path) -> dict[str, Any]:
    """Load a JSON config file, returning an empty dict if it does not exist."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    # handle empty files gracefully
    if not text.strip():
        return {}
    return json.loads(text)


def _write_json_config(path: Path, data: dict[str, Any], *, dry_run: bool) -> None:
    """Write a dict to a JSON config file with a trailing newline."""
    rendered = json.dumps(data, indent=2) + "\n"
    if dry_run:
        LOG.info("[dry-run] would write %s:\n%s", path, rendered)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    LOG.info("wrote %s", path)


def _write_text_config(path: Path, text: str, *, dry_run: bool) -> None:
    """Write plain text config content with parent creation and dry-run support."""
    rendered = text if not text or text.endswith("\n") else f"{text}\n"
    if dry_run:
        LOG.info("[dry-run] would write %s:\n%s", path, rendered)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    LOG.info("wrote %s", path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Code
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _configure_claude_session_start(
    ops_hub_path: Path,
    *,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
    dry_run: bool,
) -> None:
    """Insert or update the SessionStart hook in Claude Code settings.

    Same JSON structure as UserPromptSubmit: hooks.SessionStart is a list
    of hook groups, each with a "hooks" list of {type, command, timeout}
    objects.  The Bureau hook is identified by "ops-hub.md" in the command.
    """
    config_path = Path.home() / ".claude" / "settings.json"
    data = _load_json_config(config_path)
    command = _session_start_command(ops_hub_path, code_standards_path=code_standards_path)

    hooks_section: dict[str, Any] = data.setdefault("hooks", {})
    hook_groups: list[Any] = hooks_section.setdefault("SessionStart", [])

    for group in hook_groups:
        inner_hooks = group.get("hooks", [])
        for hook in inner_hooks:
            if "ops-hub.md" in hook.get("command", ""):
                if hook["command"] != command:
                    LOG.info("claude: updating SessionStart ops-hub command path")
                    hook["command"] = command
                else:
                    LOG.info("claude: SessionStart hook already configured, nothing to do")
                _write_json_config(config_path, data, dry_run=dry_run)
                return

    hook_groups.append(
        {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": HOOK_TIMEOUT_MS,
                }
            ]
        }
    )
    LOG.info("claude: added SessionStart hook")
    _write_json_config(config_path, data, dry_run=dry_run)


def _configure_claude(
    ops_hub_path: Path,
    *,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
    dry_run: bool,
) -> None:
    """Insert or update the per-prompt reminder hook and session-start hook.

    The per-prompt hook lives in hooks.UserPromptSubmit and echoes a short
    reminder.  For migration safety, existing hooks are identified by either
    "ops-hub.md" (old style) or "bureau-reminder" (new style) in the command.
    The session-start hook is configured via _configure_claude_session_start.
    """
    # configure both tiers
    _configure_claude_session_start(
        ops_hub_path,
        output_style_path=output_style_path,
        code_standards_path=code_standards_path,
        dry_run=dry_run,
    )

    config_path = Path.home() / ".claude" / "settings.json"
    data = _load_json_config(config_path)
    command = _reminder_command(ops_hub_path)

    hooks_section: dict[str, Any] = data.setdefault("hooks", {})
    hook_groups: list[Any] = hooks_section.setdefault("UserPromptSubmit", [])

    # search for an existing Bureau hook group (old-style or new-style)
    for group in hook_groups:
        inner_hooks = group.get("hooks", [])
        for hook in inner_hooks:
            if _is_bureau_per_prompt_hook(hook.get("command", "")):
                if hook["command"] != command:
                    LOG.info("claude: updating per-prompt hook to reminder")
                    hook["command"] = command
                else:
                    LOG.info("claude: per-prompt hook already configured, nothing to do")
                _write_json_config(config_path, data, dry_run=dry_run)
                return

    # no existing hook found; append a new group
    hook_groups.append(
        {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": HOOK_TIMEOUT_MS,
                }
            ]
        }
    )
    LOG.info("claude: added UserPromptSubmit reminder hook")
    _write_json_config(config_path, data, dry_run=dry_run)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Codex
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def _codex_hooks_path() -> Path:
    return Path.home() / ".codex" / "hooks.json"


def _normalize_text_config(text: str) -> str:
    return f"{text.rstrip()}\n" if text.strip() else ""


def _remove_codex_toml_hook_blocks(
    text: str,
    *,
    header: str,
    block_predicate: Any,
) -> tuple[str, bool]:
    """Remove matching legacy Codex TOML hook blocks from *text*."""
    if not text.strip():
        return "", False

    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_target_block = False
    block_buffer: list[str] = []
    removed = False

    for line in lines:
        stripped = line.strip()

        if stripped == header:
            in_target_block = True
            block_buffer = [line]
            continue

        if in_target_block:
            if stripped.startswith("[") and stripped != header:
                if block_predicate("".join(block_buffer)):
                    removed = True
                else:
                    result.extend(block_buffer)
                in_target_block = False
                result.append(line)
                continue

            block_buffer.append(line)
            continue

        result.append(line)

    if in_target_block:
        if block_predicate("".join(block_buffer)):
            removed = True
        else:
            result.extend(block_buffer)

    return _normalize_text_config("".join(result)), removed


def _is_codex_table_header(stripped: str) -> bool:
    return stripped.startswith("[")


def _ensure_codex_feature_flag(text: str) -> str:
    """Ensure [features].codex_hooks = true exists in Codex config TOML."""
    if not text.strip():
        return "[features]\ncodex_hooks = true\n"

    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_features = False
    features_seen = False
    codex_hooks_seen = False

    for line in lines:
        stripped = line.strip()

        if _is_codex_table_header(stripped):
            if in_features and not codex_hooks_seen:
                result.append("codex_hooks = true\n")
                codex_hooks_seen = True
            in_features = stripped == "[features]"
            if in_features:
                features_seen = True
            result.append(line)
            continue

        if in_features and stripped.startswith("codex_hooks"):
            result.append("codex_hooks = true\n")
            codex_hooks_seen = True
            continue

        result.append(line)

    if in_features and not codex_hooks_seen:
        result.append("codex_hooks = true\n")
        codex_hooks_seen = True

    if not features_seen:
        if result and result[-1].strip():
            result.append("\n")
        result.extend(["[features]\n", "codex_hooks = true\n"])

    return _normalize_text_config("".join(result))


def _update_codex_config(
    *,
    ensure_feature_flag: bool,
    remove_sessionstart_block: bool,
    remove_userpromptsubmit_block: bool,
    dry_run: bool,
) -> None:
    """Update Codex config.toml in place, migrating away legacy hook blocks."""
    config_path = _codex_config_path()
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    original = text

    if remove_sessionstart_block:
        text, removed = _remove_codex_toml_hook_blocks(
            text,
            header="[[hooks.sessionstart]]",
            block_predicate=lambda block: "ops-hub.md" in block,
        )
        if removed:
            LOG.info("codex: removed legacy sessionstart TOML hook block")

    if remove_userpromptsubmit_block:
        text, removed = _remove_codex_toml_hook_blocks(
            text,
            header="[[hooks.userpromptsubmit]]",
            block_predicate=lambda block: (
                "ops-hub.md" in block or "bureau-reminder" in block
            ),
        )
        if removed:
            LOG.info("codex: removed legacy userpromptsubmit TOML hook block")

    if ensure_feature_flag:
        text = _ensure_codex_feature_flag(text)

    if text == original and not (ensure_feature_flag and not config_path.exists()):
        return

    _write_text_config(config_path, text, dry_run=dry_run)


def _codex_session_entry(
    ops_hub_path: Path,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "matcher": "startup|resume",
        "hooks": [
            {
                "type": "command",
                "command": _session_start_command(
                    ops_hub_path,
                    output_style_path=output_style_path,
                    code_standards_path=code_standards_path,
                ),
                "timeout": HOOK_TIMEOUT_SECONDS,
                "statusMessage": CODEX_SESSION_STATUS_MESSAGE,
            }
        ],
    }


def _codex_prompt_entry(ops_hub_path: Path) -> dict[str, Any]:
    return {
        "hooks": [
            {
                "type": "command",
                "command": _reminder_command(ops_hub_path),
                "timeout": HOOK_TIMEOUT_SECONDS,
                "statusMessage": CODEX_PROMPT_STATUS_MESSAGE,
            }
        ],
    }


def _is_codex_session_hook_entry(entry: dict[str, Any]) -> bool:
    for hook in entry.get("hooks", []):
        command = hook.get("command", "")
        if "ops-hub.md" in command or hook.get("statusMessage") == CODEX_SESSION_STATUS_MESSAGE:
            return True
    return False


def _is_codex_prompt_hook_entry(entry: dict[str, Any]) -> bool:
    for hook in entry.get("hooks", []):
        command = hook.get("command", "")
        if _is_bureau_per_prompt_hook(command) or hook.get("statusMessage") == CODEX_PROMPT_STATUS_MESSAGE:
            return True
    return False


def _upsert_codex_hooks_json(
    event_name: str,
    entry: dict[str, Any],
    *,
    is_bureau_entry: Any,
    dry_run: bool,
) -> None:
    """Insert or replace the Bureau matcher group for a Codex hook event."""
    hooks_path = _codex_hooks_path()
    data = _load_json_config(hooks_path)
    hooks_section: dict[str, Any] = data.setdefault("hooks", {})
    event_entries: list[Any] = hooks_section.get(event_name, [])
    filtered = [existing for existing in event_entries if not is_bureau_entry(existing)]
    filtered.append(entry)
    hooks_section[event_name] = filtered
    _write_json_config(hooks_path, data, dry_run=dry_run)


def _remove_codex_hooks_json_entries(
    event_name: str,
    *,
    is_bureau_entry: Any,
    dry_run: bool,
) -> None:
    """Remove Bureau-managed entries for a Codex hook event from hooks.json."""
    hooks_path = _codex_hooks_path()
    if not hooks_path.exists():
        LOG.info("codex: no hooks.json found, nothing to remove for %s", event_name)
        return

    data = _load_json_config(hooks_path)
    hooks_section: dict[str, Any] = data.setdefault("hooks", {})
    event_entries: list[Any] = hooks_section.get(event_name, [])
    filtered = [existing for existing in event_entries if not is_bureau_entry(existing)]

    if len(filtered) == len(event_entries):
        LOG.info("codex: no Bureau %s hook found in hooks.json", event_name.lower())
        return

    if filtered:
        hooks_section[event_name] = filtered
    else:
        hooks_section.pop(event_name, None)

    _write_json_config(hooks_path, data, dry_run=dry_run)


def _configure_codex_session_start(
    ops_hub_path: Path,
    *,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
    dry_run: bool,
) -> None:
    """Configure Codex SessionStart via hooks.json and migrate old TOML hooks."""
    _update_codex_config(
        ensure_feature_flag=True,
        remove_sessionstart_block=True,
        remove_userpromptsubmit_block=False,
        dry_run=dry_run,
    )
    _upsert_codex_hooks_json(
        "SessionStart",
        _codex_session_entry(
            ops_hub_path,
            output_style_path=output_style_path,
            code_standards_path=code_standards_path,
        ),
        is_bureau_entry=_is_codex_session_hook_entry,
        dry_run=dry_run,
    )


def _configure_codex(
    ops_hub_path: Path,
    *,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
    dry_run: bool,
) -> None:
    """Configure both Codex Bureau hooks via hooks.json and migrate old TOML hooks."""
    _configure_codex_session_start(
        ops_hub_path,
        output_style_path=output_style_path,
        code_standards_path=code_standards_path,
        dry_run=dry_run,
    )
    _update_codex_config(
        ensure_feature_flag=True,
        remove_sessionstart_block=False,
        remove_userpromptsubmit_block=True,
        dry_run=dry_run,
    )
    _upsert_codex_hooks_json(
        "UserPromptSubmit",
        _codex_prompt_entry(ops_hub_path),
        is_bureau_entry=_is_codex_prompt_hook_entry,
        dry_run=dry_run,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _configure_gemini_session_start(
    ops_hub_path: Path,
    *,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
    dry_run: bool,
) -> None:
    """Insert or update the SessionStart hook in Gemini CLI settings.

    Same JSON structure as BeforeAgent.  Uses name "bureau-ops-hub-session"
    to distinguish from the per-prompt hook which uses "bureau-ops-hub".
    The enable toggle lives under hooksConfig.enabled (separate from hooks).
    """
    config_path = Path.home() / ".gemini" / "settings.json"
    data = _load_json_config(config_path)
    command = _session_start_command(
        ops_hub_path,
        output_style_path=output_style_path,
        code_standards_path=code_standards_path,
    )

    hooks_section: dict[str, Any] = data.setdefault("hooks", {})
    # Gemini uses a separate top-level "hooksConfig" for the enable toggle
    hooks_config: dict[str, Any] = data.setdefault("hooksConfig", {})
    hooks_config["enabled"] = True

    hook_list: list[Any] = hooks_section.setdefault("SessionStart", [])

    bureau_entry = {
        "name": BUREAU_SESSION_HOOK_NAME,
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": HOOK_TIMEOUT_MS,
                "description": "Inject full ops hub at session start",
            }
        ],
    }

    for idx, entry in enumerate(hook_list):
        if entry.get("name") == BUREAU_SESSION_HOOK_NAME:
            existing_cmd = ""
            for hook in entry.get("hooks", []):
                if "ops-hub.md" in hook.get("command", ""):
                    existing_cmd = hook["command"]
                    break

            if existing_cmd == command:
                LOG.info("gemini: SessionStart hook already configured, nothing to do")
            else:
                LOG.info("gemini: updating SessionStart ops-hub hook entry")
                hook_list[idx] = bureau_entry

            _write_json_config(config_path, data, dry_run=dry_run)
            return

    hook_list.append(bureau_entry)
    LOG.info("gemini: added SessionStart hook")
    _write_json_config(config_path, data, dry_run=dry_run)


def _configure_gemini(
    ops_hub_path: Path,
    *,
    output_style_path: Path | None = None,
    code_standards_path: Path | None = None,
    dry_run: bool,
) -> None:
    """Insert or update the per-prompt reminder hook and session-start hook.

    The per-prompt hook lives under hooks.BeforeAgent and echoes a short
    reminder.  For migration safety, existing hooks are identified by name
    "bureau-ops-hub" (which covers both old and new style commands).
    """
    # configure both tiers
    _configure_gemini_session_start(
        ops_hub_path,
        output_style_path=output_style_path,
        code_standards_path=code_standards_path,
        dry_run=dry_run,
    )

    config_path = Path.home() / ".gemini" / "settings.json"
    data = _load_json_config(config_path)
    command = _reminder_command(ops_hub_path)

    hooks_section: dict[str, Any] = data.setdefault("hooks", {})
    # Gemini uses a separate top-level "hooksConfig" for the enable toggle
    hooks_config: dict[str, Any] = data.setdefault("hooksConfig", {})
    hooks_config["enabled"] = True

    hook_list: list[Any] = hooks_section.setdefault("BeforeAgent", [])

    bureau_entry = {
        "name": BUREAU_HOOK_NAME,
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": HOOK_TIMEOUT_MS,
                "description": "Remind agent that ops hub was loaded at session start",
            }
        ],
    }

    # search for an existing Bureau entry by name
    for idx, entry in enumerate(hook_list):
        if entry.get("name") == BUREAU_HOOK_NAME:
            # check whether the command needs updating (old cat -> new reminder)
            existing_cmd = ""
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if _is_bureau_per_prompt_hook(cmd):
                    existing_cmd = cmd
                    break

            if existing_cmd == command:
                LOG.info("gemini: per-prompt hook already configured, nothing to do")
            else:
                LOG.info("gemini: updating per-prompt hook to reminder")
                hook_list[idx] = bureau_entry

            _write_json_config(config_path, data, dry_run=dry_run)
            return

    # no existing entry; append
    hook_list.append(bureau_entry)
    LOG.info("gemini: added BeforeAgent reminder hook")
    _write_json_config(config_path, data, dry_run=dry_run)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Removal functions (bare mode)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _remove_claude_session_start(*, dry_run: bool) -> None:
    """Remove the Bureau SessionStart hook from Claude Code settings."""
    config_path = Path.home() / ".claude" / "settings.json"
    data = _load_json_config(config_path)

    hooks_section = data.get("hooks", {})
    hook_groups: list[Any] = hooks_section.get("SessionStart", [])

    filtered = [
        group for group in hook_groups
        if not any(
            "ops-hub.md" in hook.get("command", "")
            for hook in group.get("hooks", [])
        )
    ]

    if len(filtered) == len(hook_groups):
        LOG.info("claude: no Bureau SessionStart hook found, nothing to remove")
        return

    hooks_section["SessionStart"] = filtered
    LOG.info("claude: removed Bureau SessionStart hook")
    _write_json_config(config_path, data, dry_run=dry_run)


def _remove_claude(*, dry_run: bool) -> None:
    """Remove both Bureau hooks (SessionStart + per-prompt) from Claude Code settings."""
    _remove_claude_session_start(dry_run=dry_run)

    config_path = Path.home() / ".claude" / "settings.json"
    data = _load_json_config(config_path)

    hooks_section = data.get("hooks", {})
    hook_groups: list[Any] = hooks_section.get("UserPromptSubmit", [])

    # filter out any hook group matching old-style or new-style Bureau commands
    filtered = [
        group for group in hook_groups
        if not any(
            _is_bureau_per_prompt_hook(hook.get("command", ""))
            for hook in group.get("hooks", [])
        )
    ]

    if len(filtered) == len(hook_groups):
        LOG.info("claude: no Bureau per-prompt hook found, nothing to remove")
        return

    hooks_section["UserPromptSubmit"] = filtered
    LOG.info("claude: removed Bureau per-prompt hook")
    _write_json_config(config_path, data, dry_run=dry_run)


def _remove_codex_session_start(*, dry_run: bool) -> None:
    """Remove the Bureau SessionStart hook from Codex hooks.json and legacy TOML."""
    _update_codex_config(
        ensure_feature_flag=False,
        remove_sessionstart_block=True,
        remove_userpromptsubmit_block=False,
        dry_run=dry_run,
    )
    _remove_codex_hooks_json_entries(
        "SessionStart",
        is_bureau_entry=_is_codex_session_hook_entry,
        dry_run=dry_run,
    )


def _remove_codex(*, dry_run: bool) -> None:
    """Remove both Bureau hooks from Codex hooks.json and legacy TOML."""
    _remove_codex_session_start(dry_run=dry_run)
    _update_codex_config(
        ensure_feature_flag=False,
        remove_sessionstart_block=False,
        remove_userpromptsubmit_block=True,
        dry_run=dry_run,
    )
    _remove_codex_hooks_json_entries(
        "UserPromptSubmit",
        is_bureau_entry=_is_codex_prompt_hook_entry,
        dry_run=dry_run,
    )


def _remove_gemini_session_start(*, dry_run: bool) -> None:
    """Remove the Bureau SessionStart hook from Gemini CLI settings."""
    config_path = Path.home() / ".gemini" / "settings.json"
    data = _load_json_config(config_path)

    hooks_section = data.get("hooks", {})
    hook_list: list[Any] = hooks_section.get("SessionStart", [])

    filtered = [
        entry for entry in hook_list
        if entry.get("name") != BUREAU_SESSION_HOOK_NAME
    ]

    if len(filtered) == len(hook_list):
        LOG.info("gemini: no Bureau SessionStart hook found, nothing to remove")
        return

    hooks_section["SessionStart"] = filtered
    LOG.info("gemini: removed Bureau SessionStart hook")
    _write_json_config(config_path, data, dry_run=dry_run)


def _remove_gemini(*, dry_run: bool) -> None:
    """Remove both Bureau hooks (SessionStart + per-prompt) from Gemini CLI settings."""
    _remove_gemini_session_start(dry_run=dry_run)

    config_path = Path.home() / ".gemini" / "settings.json"
    data = _load_json_config(config_path)

    hooks_section = data.get("hooks", {})
    hook_list: list[Any] = hooks_section.get("BeforeAgent", [])

    filtered = [
        entry for entry in hook_list
        if entry.get("name") != BUREAU_HOOK_NAME
    ]

    if len(filtered) == len(hook_list):
        LOG.info("gemini: no Bureau per-prompt hook found, nothing to remove")
        return

    hooks_section["BeforeAgent"] = filtered
    LOG.info("gemini: removed Bureau per-prompt hook")
    _write_json_config(config_path, data, dry_run=dry_run)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dispatch tables
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGENT_HANDLERS: dict[str, Any] = {
    "claude": _configure_claude,
    "codex": _configure_codex,
    "gemini": _configure_gemini,
}

REMOVE_HANDLERS: dict[str, Any] = {
    "claude": _remove_claude,
    "codex": _remove_codex,
    "gemini": _remove_gemini,
}

VALID_AGENTS = sorted(AGENT_HANDLERS)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Configure Bureau hook-based ops-hub reinforcement for supported "
            "coding-agent CLIs, including Codex hooks.json plus legacy TOML "
            "migration."
        ),
    )
    parser.add_argument(
        "--protocols-dir",
        type=Path,
        default=None,
        help="Absolute path to the protocols directory containing ops-hub.md. "
             "Required unless --remove is set.",
    )
    parser.add_argument(
        "--output-style-path",
        type=Path,
        default=None,
        help="Path to output-style.md. When provided, Gemini/Codex session-start "
             "hooks inject it before ops-hub.",
    )
    parser.add_argument(
        "--code-standards-path",
        type=Path,
        default=None,
        help="Path to code-standards.md. When provided, SessionStart hooks inject it alongside ops-hub.",
    )
    parser.add_argument(
        "--agent",
        action="append",
        required=True,
        choices=VALID_AGENTS,
        dest="agents",
        help="Agent CLI to configure (repeatable).",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        default=False,
        help="Remove Bureau hooks from all specified agents (bare mode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print what would be done without making changes.",
    )
    args = parser.parse_args(argv)

    # --protocols-dir is required unless --remove is set
    if not args.remove and args.protocols_dir is None:
        parser.error("--protocols-dir is required unless --remove is set")

    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.dry_run else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # validate --protocols-dir when not in remove mode
    if not args.remove:
        protocols_dir: Path = args.protocols_dir
        if not protocols_dir.is_absolute():
            LOG.error("--protocols-dir must be an absolute path: %s", protocols_dir)
            return 1

        ops_hub_path = protocols_dir / "ops-hub.md"
        output_style_path: Path | None = args.output_style_path
        code_standards_path: Path | None = args.code_standards_path
        if not ops_hub_path.exists():
            LOG.warning(
                "ops-hub.md does not exist yet at %s; hooks will reference this path",
                ops_hub_path,
            )

    errors = 0
    # deduplicate while preserving order
    seen: set[str] = set()
    for agent in args.agents:
        if agent in seen:
            continue
        seen.add(agent)

        if args.remove:
            handler = REMOVE_HANDLERS[agent]
            try:
                handler(dry_run=args.dry_run)
            except Exception:
                LOG.exception("failed to remove hooks for %s", agent)
                errors += 1
        else:
            handler = AGENT_HANDLERS[agent]
            try:
                handler(
                    ops_hub_path,
                    output_style_path=output_style_path,
                    code_standards_path=code_standards_path,
                    dry_run=args.dry_run,
                )
            except Exception:
                LOG.exception("failed to configure %s", agent)
                errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
