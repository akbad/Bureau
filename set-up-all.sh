#!/usr/bin/env bash
agents/scripts/set-up-agents.sh && \
configs/scripts/set-up-configs.sh && \
tools/scripts/set-up-tools.sh -y && \
agents/scripts/set-up-claude-slash-commands.sh && \
agents/scripts/set-up-codex-role-launchers.sh && \
agents/scripts/set-up-gemini-role-launchers.sh