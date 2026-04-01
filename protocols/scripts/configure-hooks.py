#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────
# Design rationale
#
# Two-tier hook architecture for three coding-agent CLIs (Claude Code,
# Codex, Gemini CLI):
#
#   1. SessionStart hooks: run `cat ops-hub.md` once at session start to
#      inject the full ops-hub content into the agent's context.
#   2. Per-prompt hooks: echo a short XML-tagged reminder on every prompt
#      so the agent remembers the ops-hub was already loaded, without
#      re-reading the entire file each turn.
#
# Each CLI stores its config in a different format (JSON or TOML) and
# uses a different hook schema, so the script dispatches to a per-agent
# handler.  The per-prompt handler internally calls the session-start
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
#   - No third-party deps: stdlib only (no tomli/toml).  The Codex TOML
#     handler uses line-oriented string operations instead of a TOML lib.
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

# sentinel used to identify our per-prompt hook in lists that may contain other hooks
BUREAU_HOOK_NAME = "bureau-ops-hub"

# sentinel used to identify the session-start hook (distinct from per-prompt)
BUREAU_SESSION_HOOK_NAME = "bureau-ops-hub-session"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shared helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cat_command(ops_hub_path: Path) -> str:
    """Build the shell command that cats the ops-hub file."""
    return f"cat {ops_hub_path}"


def _session_start_command(ops_hub_path: Path) -> str:
    """Build the shell command that cats the ops-hub file at session start."""
    return f"cat {ops_hub_path}"


def _reminder_command(ops_hub_path: Path) -> str:
    """Build a short echo reminder for per-prompt hooks (avoids re-reading the full file)."""
    return (
        f"echo '<bureau-reminder>The Bureau ops-hub was loaded at session start "
        f"from {ops_hub_path}. Re-read it when you need task routing or "
        f"governance rules.</bureau-reminder>'"
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Code
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _configure_claude_session_start(ops_hub_path: Path, *, dry_run: bool) -> None:
    """Insert or update the SessionStart hook in Claude Code settings.

    Same JSON structure as UserPromptSubmit: hooks.SessionStart is a list
    of hook groups, each with a "hooks" list of {type, command, timeout}
    objects.  The Bureau hook is identified by "ops-hub.md" in the command.
    """
    config_path = Path.home() / ".claude" / "settings.json"
    data = _load_json_config(config_path)
    command = _session_start_command(ops_hub_path)

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


def _configure_claude(ops_hub_path: Path, *, dry_run: bool) -> None:
    """Insert or update the per-prompt reminder hook and session-start hook.

    The per-prompt hook lives in hooks.UserPromptSubmit and echoes a short
    reminder.  For migration safety, existing hooks are identified by either
    "ops-hub.md" (old style) or "bureau-reminder" (new style) in the command.
    The session-start hook is configured via _configure_claude_session_start.
    """
    # configure both tiers
    _configure_claude_session_start(ops_hub_path, dry_run=dry_run)

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

def _configure_codex_session_start(ops_hub_path: Path, *, dry_run: bool) -> None:
    """Append or update the [[hooks.sessionstart]] block in Codex TOML config.

    Same line-oriented TOML approach as the per-prompt handler.  The Bureau
    hook is identified by "ops-hub.md" in the command line.
    """
    config_path = Path.home() / ".codex" / "config.toml"
    command = _session_start_command(ops_hub_path)

    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
    else:
        text = ""

    # check if a sessionstart block with ops-hub.md already exists
    if "[[hooks.sessionstart]]" in text and "ops-hub.md" in text:
        # walk lines to see if the ops-hub ref is inside a sessionstart block
        in_session_block = False
        found = False
        new_lines: list[str] = []
        changed = False
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped == "[[hooks.sessionstart]]":
                in_session_block = True
                new_lines.append(line)
                continue
            if in_session_block and stripped.startswith("["):
                in_session_block = False
            if in_session_block and stripped.startswith("command") and "ops-hub.md" in stripped:
                found = True
                expected = f'command = "{command}"'
                if stripped != expected:
                    indent = line[: len(line) - len(line.lstrip())]
                    new_lines.append(f"{indent}{expected}\n")
                    changed = True
                    continue
            new_lines.append(line)

        if found:
            if changed:
                LOG.info("codex: updating sessionstart ops-hub command path")
                rendered = "".join(new_lines)
                if dry_run:
                    LOG.info("[dry-run] would write %s:\n%s", config_path, rendered)
                    return
                config_path.write_text(rendered, encoding="utf-8")
                LOG.info("wrote %s", config_path)
            else:
                LOG.info("codex: sessionstart hook already configured, nothing to do")
            return

    # no existing sessionstart hook; append the block
    block = (
        "\n"
        "[[hooks.sessionstart]]\n"
        'type = "command"\n'
        f'command = "{command}"\n'
        f"timeout = {HOOK_TIMEOUT_MS}\n"
    )
    LOG.info("codex: added sessionstart hook")

    if dry_run:
        LOG.info("[dry-run] would append to %s:\n%s", config_path, block)
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("a", encoding="utf-8") as fh:
        fh.write(block)
    LOG.info("wrote %s", config_path)


def _configure_codex(ops_hub_path: Path, *, dry_run: bool) -> None:
    """Append or update the per-prompt reminder hook and session-start hook.

    Codex uses plain TOML.  Rather than pulling in a TOML library we
    operate on the raw text.  For migration safety, both "ops-hub.md"
    (old style) and "bureau-reminder" (new style) are matched when
    searching for existing per-prompt hooks.
    """
    # configure both tiers
    _configure_codex_session_start(ops_hub_path, dry_run=dry_run)

    config_path = Path.home() / ".codex" / "config.toml"
    command = _reminder_command(ops_hub_path)

    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
    else:
        text = ""

    # check for existing per-prompt hook (old-style or new-style) in
    # userpromptsubmit blocks
    has_old = "ops-hub.md" in text and "[[hooks.userpromptsubmit]]" in text
    has_new = "bureau-reminder" in text and "[[hooks.userpromptsubmit]]" in text

    if has_old or has_new:
        # walk lines to find the command inside a userpromptsubmit block
        in_prompt_block = False
        new_lines: list[str] = []
        changed = False
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped == "[[hooks.userpromptsubmit]]":
                in_prompt_block = True
                new_lines.append(line)
                continue
            if in_prompt_block and stripped.startswith("["):
                in_prompt_block = False
            if in_prompt_block and stripped.startswith("command"):
                # check if this is a Bureau hook command (old or new style)
                cmd_val = stripped.split("=", 1)[1].strip().strip('"') if "=" in stripped else ""
                if _is_bureau_per_prompt_hook(cmd_val):
                    expected = f'command = "{command}"'
                    if stripped != expected:
                        indent = line[: len(line) - len(line.lstrip())]
                        new_lines.append(f"{indent}{expected}\n")
                        changed = True
                        continue
            new_lines.append(line)

        if changed:
            LOG.info("codex: updating per-prompt hook to reminder")
            rendered = "".join(new_lines)
        else:
            LOG.info("codex: per-prompt hook already configured, nothing to do")
            rendered = text

        if dry_run:
            LOG.info("[dry-run] would write %s:\n%s", config_path, rendered)
            return
        config_path.write_text(rendered, encoding="utf-8")
        if changed:
            LOG.info("wrote %s", config_path)
        return

    # no existing per-prompt hook; append the block
    block = (
        "\n"
        "[[hooks.userpromptsubmit]]\n"
        'type = "command"\n'
        f'command = "{command}"\n'
        f"timeout = {HOOK_TIMEOUT_MS}\n"
    )
    LOG.info("codex: added userpromptsubmit reminder hook")

    if dry_run:
        LOG.info("[dry-run] would append to %s:\n%s", config_path, block)
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("a", encoding="utf-8") as fh:
        fh.write(block)
    LOG.info("wrote %s", config_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _configure_gemini_session_start(ops_hub_path: Path, *, dry_run: bool) -> None:
    """Insert or update the SessionStart hook in Gemini CLI settings.

    Same JSON structure as BeforeAgent.  Uses name "bureau-ops-hub-session"
    to distinguish from the per-prompt hook which uses "bureau-ops-hub".
    The enable toggle lives under hooksConfig.enabled (separate from hooks).
    """
    config_path = Path.home() / ".gemini" / "settings.json"
    data = _load_json_config(config_path)
    command = _session_start_command(ops_hub_path)

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


def _configure_gemini(ops_hub_path: Path, *, dry_run: bool) -> None:
    """Insert or update the per-prompt reminder hook and session-start hook.

    The per-prompt hook lives under hooks.BeforeAgent and echoes a short
    reminder.  For migration safety, existing hooks are identified by name
    "bureau-ops-hub" (which covers both old and new style commands).
    """
    # configure both tiers
    _configure_gemini_session_start(ops_hub_path, dry_run=dry_run)

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
    """Remove the Bureau [[hooks.sessionstart]] block from Codex TOML config."""
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        LOG.info("codex: no config file found, nothing to remove (sessionstart)")
        return

    text = config_path.read_text(encoding="utf-8")
    if "ops-hub.md" not in text or "[[hooks.sessionstart]]" not in text:
        LOG.info("codex: no Bureau sessionstart hook found, nothing to remove")
        return

    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_bureau_block = False
    found_ops_hub = False
    block_buffer: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "[[hooks.sessionstart]]":
            in_bureau_block = True
            found_ops_hub = False
            block_buffer = [line]
            continue

        if in_bureau_block:
            if stripped.startswith("[") and stripped != "[[hooks.sessionstart]]":
                if found_ops_hub:
                    LOG.info("codex: removed Bureau sessionstart hook block")
                else:
                    result.extend(block_buffer)
                in_bureau_block = False
                result.append(line)
                continue

            block_buffer.append(line)
            if "ops-hub.md" in stripped:
                found_ops_hub = True
            continue

        result.append(line)

    if in_bureau_block:
        if not found_ops_hub:
            result.extend(block_buffer)
        else:
            LOG.info("codex: removed Bureau sessionstart hook block")

    rendered = "".join(result)
    rendered = rendered.rstrip("\n") + "\n" if rendered.strip() else ""

    if dry_run:
        LOG.info("[dry-run] would write %s:\n%s", config_path, rendered)
        return
    config_path.write_text(rendered, encoding="utf-8")
    LOG.info("wrote %s", config_path)


def _remove_codex(*, dry_run: bool) -> None:
    """Remove both Bureau hooks (sessionstart + per-prompt) from Codex TOML config."""
    _remove_codex_session_start(dry_run=dry_run)

    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        LOG.info("codex: no config file found, nothing to remove")
        return

    text = config_path.read_text(encoding="utf-8")
    # match both old-style (ops-hub.md) and new-style (bureau-reminder)
    if "ops-hub.md" not in text and "bureau-reminder" not in text:
        LOG.info("codex: no Bureau per-prompt hook found, nothing to remove")
        return

    # remove [[hooks.userpromptsubmit]] blocks containing Bureau commands
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_bureau_block = False
    found_bureau = False
    block_buffer: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "[[hooks.userpromptsubmit]]":
            in_bureau_block = True
            found_bureau = False
            block_buffer = [line]
            continue

        if in_bureau_block:
            if stripped.startswith("[") and stripped != "[[hooks.userpromptsubmit]]":
                if found_bureau:
                    LOG.info("codex: removed Bureau per-prompt hook block")
                else:
                    result.extend(block_buffer)
                in_bureau_block = False
                result.append(line)
                continue

            block_buffer.append(line)
            if "ops-hub.md" in stripped or "bureau-reminder" in stripped:
                found_bureau = True
            continue

        result.append(line)

    if in_bureau_block:
        if not found_bureau:
            result.extend(block_buffer)
        else:
            LOG.info("codex: removed Bureau per-prompt hook block")

    rendered = "".join(result)
    rendered = rendered.rstrip("\n") + "\n" if rendered.strip() else ""

    if dry_run:
        LOG.info("[dry-run] would write %s:\n%s", config_path, rendered)
        return
    config_path.write_text(rendered, encoding="utf-8")
    LOG.info("wrote %s", config_path)


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
            "Configure per-prompt hooks that re-inject ops-hub.md "
            "for coding-agent CLIs."
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
                handler(ops_hub_path, dry_run=args.dry_run)
            except Exception:
                LOG.exception("failed to configure %s", agent)
                errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
