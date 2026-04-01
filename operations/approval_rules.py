# Per-CLI auto-approval rule builders.
#
# Each supported coding agent (Claude Code, Gemini CLI, Codex, OpenCode) has
# its own permission format for auto-approving tool invocations.
# 
# The builder functions here translate a common input (a list of human-readable 
# prefixes or paths) into the agent-specific permission strings that get written 
# into each coding agent's user-scoped settings file by the corresponding 
# `add-<agent>-auto-approvals.py` script.
#
# Key invariant: every builder must be idempotent, producing the same output
# for the same input. This is because the callers append rules only when they are 
# not already present in the settings file.

from __future__ import annotations

import json
from typing import Iterable


def normalize_prefixes(prefixes: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for prefix in prefixes:
        value = str(prefix).strip()
        if value:
            normalized.append(value)
    return normalized


def build_claude_bash_rules(prefixes: Iterable[str]) -> list[str]:
    return [f"Bash({prefix}:*)" for prefix in normalize_prefixes(prefixes)]


def build_claude_read_rules(paths: Iterable[str]) -> list[str]:
    """
    Build Claude Code Read permission rules (format: `Read(<path>/**)`) from 
    directory/file paths to allow reading all files within it.
    
    - Paths starting with `~` are kept as-is (Claude Code expands at runtime).
    - Paths already ending with a glob suffix (``/**`` or ``/*``) are preserved.
    """
    rules: list[str] = []
    for path in normalize_prefixes(paths):
        # append recursive glob when caller passed a bare directory path,
        # but preserve explicit globs to avoid double-suffixing
        if not path.endswith("/**") and not path.endswith("/*"):
            path = f"{path}/**"
        rules.append(f"Read({path})")
    return rules


def build_gemini_bash_rules(prefixes: Iterable[str]) -> list[str]:
    return [f"run_shell_command({prefix})" for prefix in normalize_prefixes(prefixes)]


def build_opencode_bash_rules(
    allow: Iterable[str],
    deny: Iterable[str],
) -> dict[str, str]:
    rules: dict[str, str] = {"*": "ask"}
    for prefix in normalize_prefixes(allow):
        rules[f"{prefix}*"] = "allow"
    for prefix in normalize_prefixes(deny):
        rules[f"{prefix}*"] = "deny"
    return rules


def tokenize_prefix(prefix: str) -> list[str]:
    return [part for part in prefix.strip().split() if part]


def build_codex_rule_lines(
    allow: Iterable[str],
    deny: Iterable[str],
) -> list[str]:
    lines: list[str] = []
    for prefix in normalize_prefixes(allow):
        if not tokenize_prefix(prefix):
            continue
        pattern = json.dumps(tokenize_prefix(prefix))
        lines.append(f"prefix_rule(pattern={pattern}, decision=\"allow\")")
    for prefix in normalize_prefixes(deny):
        if not tokenize_prefix(prefix):
            continue
        pattern = json.dumps(tokenize_prefix(prefix))
        lines.append(f"prefix_rule(pattern={pattern}, decision=\"forbidden\")")
    return lines
