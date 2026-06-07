#!/usr/bin/env bash
#
# Setup script for agent files and configurations
# Run from the agents/ directory (or anywhere in the repo)

set -euo pipefail

# Find the repo root (where this script's ancestor directory is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_AGENTS_DIRNAME="claude-subagents"
ROLE_AGENTS_DIRNAME="role-prompts"
REPO_ROOT="$(cd "$AGENTS_DIR/.." && pwd)"

# Source internal Bureau libraries
source "$REPO_ROOT/bin/lib/agent-selection.sh"
source "$REPO_ROOT/bin/lib/logging.sh"

# Detect installed CLIs based on directory existence (exits if none found, logs detected CLIs)
discover_agents

# Subdirectory name for symlinked agents
AGENTS_SUBDIR="bureau-agents"

log_banner "Setting up Bureau agents"
echo "Repo root: $REPO_ROOT"
echo "Selected agents: ${AGENTS[*]}"
log_empty_line

# Check if we're in the right place
if [[ ! -d "$AGENTS_DIR/$CLAUDE_AGENTS_DIRNAME" ]] || [[ ! -d "$AGENTS_DIR/$ROLE_AGENTS_DIRNAME" ]]; then
    log_error "Cannot find agent directories! ($CLAUDE_AGENTS_DIRNAME/ and $ROLE_AGENTS_DIRNAME within $AGENTS_DIR)"
    exit 1
fi

# ============================================================================
# Step 1: Set up Claude Code subagents
# ============================================================================
if agent_enabled "Claude Code"; then
    log_action "Setting up Claude Code subagents"

    # Symlink Claude subagents folder
    if [[ -L ~/.claude/agents/$AGENTS_SUBDIR ]]; then
        rm ~/.claude/agents/$AGENTS_SUBDIR
        log_success "Removed existing Bureau symlink at ~/.claude/agents/$AGENTS_SUBDIR (to ensure consistency after any reconfiguration)"
    fi
    mkdir -p ~/.claude/agents
    log_success "Ensured/created ~/.claude/agents directory"

    # Symlink all Claude subagent files
    ln -s "$AGENTS_DIR/$CLAUDE_AGENTS_DIRNAME" ~/.claude/agents/$AGENTS_SUBDIR
    log_success "Symlinked Claude subagent templates/role prompts to ~/.claude/agents/$AGENTS_SUBDIR"

    echo ""
else
    log_action "Skipping Claude Code subagents (CLI directory not found)"
    echo ""
fi

# ============================================================================
# Step 2: Set up agent launchers (slash commands and wrapper scripts)
# ============================================================================

# Claude Code slash commands
if agent_enabled "Claude Code"; then
    log_action "Setting up Claude Code slash commands"
    "$AGENTS_DIR/scripts/set-up-claude-slash-commands.sh"
    echo ""
fi

# Codex role launchers
if agent_enabled "Codex"; then
    log_action "Setting up Codex role launchers"
    "$AGENTS_DIR/scripts/set-up-codex-role-launchers.sh"
    echo ""
fi

# Gemini CLI role launchers
if agent_enabled "Gemini CLI"; then
    log_action "Setting up Gemini CLI role launchers"
    "$AGENTS_DIR/scripts/set-up-gemini-role-launchers.sh"
    echo ""
fi

# Antigravity (Gemini CLI) subagents plugin deployment
if agent_enabled "Gemini CLI"; then
    log_action "Setting up Antigravity subagents plugin"
    ANTIGRAVITY_AGENTS_DIR="$HOME/.gemini/config/plugins/bureau/agents"
    
    if [[ -e "$ANTIGRAVITY_AGENTS_DIR" ]]; then
        rm -rf "$ANTIGRAVITY_AGENTS_DIR"
    fi
    mkdir -p "$ANTIGRAVITY_AGENTS_DIR"
    
    count=0
    for agent_file in "$AGENTS_DIR/$ROLE_AGENTS_DIRNAME"/*.md; do
        if [[ -f "$agent_file" ]]; then
            agent_name=$(basename "$agent_file")
            ln -sfn "$agent_file" "$ANTIGRAVITY_AGENTS_DIR/$agent_name"
            count=$((count + 1))
        fi
    done
    
    log_success "Symlinked $count subagents to $ANTIGRAVITY_AGENTS_DIR"
    
    # Create the plugin.json descriptor for Antigravity
    cat <<EOF > "$HOME/.gemini/config/plugins/bureau/plugin.json"
{
  "name": "bureau",
  "version": "0.1.0",
  "description": "Bureau multi-agent orchestration framework capabilities."
}
EOF
    log_success "Generated Antigravity plugin.json"
    echo ""
fi

# OpenCode agents (filtered symlinks for auto-discovery)
if agent_enabled "OpenCode"; then
    log_action "Setting up Bureau agents for OpenCode"
    OPENCODE_AGENTS_DIR="$HOME/.config/opencode/agent/$AGENTS_SUBDIR"

    # Get filtered role list
    AGENTS_ENABLED_FOR_OPENCODE=$(uv run python -m operations.roles_catalog opencode)

    # Remove old directory (may be symlink or real directory) so config always wins
    if [[ -e "$OPENCODE_AGENTS_DIR" ]]; then
        rm -rf "$OPENCODE_AGENTS_DIR"
        log_success "Removed old agent directory at $OPENCODE_AGENTS_DIR"
    fi

    if [[ -z "$AGENTS_ENABLED_FOR_OPENCODE" ]]; then
        log_warning "No agents enabled for OpenCode. Skipping setup and clearing any previously generated OpenCode Bureau agents."
        log_info "To enable agents, update the roles.enabled list in your local.yml"
    else
        # Create directory and populate with symlinks corresponding to the agents
        #   enabled for OpenCode
        mkdir -p "$OPENCODE_AGENTS_DIR"

        count=0
        for agent_name in $AGENTS_ENABLED_FOR_OPENCODE; do
            source_file="$AGENTS_DIR/$ROLE_AGENTS_DIRNAME/${agent_name}.md"
            if [[ -f "$source_file" ]]; then
                ln -s "$source_file" "$OPENCODE_AGENTS_DIR/${agent_name}.md"
                count=$((count + 1))
            else
                log_warning "Agent file not found: $source_file (skipping)"
            fi
        done

        log_success "Created $count filtered agent symlinks in $OPENCODE_AGENTS_DIR"
    fi
    echo ""
fi

log_success "Agent setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run the configs setup script: protocols/scripts/set-up-protocols.sh"
echo "  2. Verify Claude Code agents with: claude (then run /agents)"
echo "  3. Install claude-mem plugin:"
echo "     > /plugin marketplace add thedotmack/claude-mem"
echo "     > /plugin install claude-mem"
