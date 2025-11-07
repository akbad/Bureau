#!/usr/bin/env bash

# Bootstrap: Initial setup for Bedrock across Claude Code, Codex CLI, and Gemini CLI
# > Run once: ./bootstrap.sh
# > Idempotent (safe to re-run; won't duplicate resources)
#
# Prerequisites: Node.js, Python 3.8+, git

# Change to repo root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

agents/scripts/set-up-agents.sh && \
configs/scripts/set-up-configs.sh && \
tools/scripts/set-up-tools.sh -y && \
agents/scripts/set-up-claude-slash-commands.sh && \
agents/scripts/set-up-codex-role-launchers.sh && \
agents/scripts/set-up-gemini-role-launchers.sh