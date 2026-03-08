#!/usr/bin/env bash

# Exits on any:
# - error (-e)
# - undefined variable (-u)
# - failed pipe (-o pipefail)
set -euo pipefail

# Setup script for Claude Code slash commands that inject agent role prompts
# This allows launching agents in the current conversation via /architect-bureau, /frontend-bureau, etc.

# Locate repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$AGENTS_DIR/.." && pwd)"
CLAUDE_SUBAGENTS_DIR="$AGENTS_DIR/claude-subagents"

# Source internal Bureau libraries
source "$REPO_ROOT/bin/lib/agent-selection.sh"    # reads configs to determine enabled agents
source "$REPO_ROOT/bin/lib/logging.sh"            
source "$REPO_ROOT/bin/lib/roles-setup.sh"        # handles cross-CLI role prompt setup

# Detect installed CLIs (exits if none found, logs detected CLIs)
discover_agents
echo "Source: $CLAUDE_SUBAGENTS_DIR"
echo "Target: $HOME/.claude/commands"
log_empty_line

# Check if source directory exists
if [[ ! -d "$CLAUDE_SUBAGENTS_DIR" ]]; then
    log_error "Cannot find claude-subagents/ at the expected path: $CLAUDE_SUBAGENTS_DIR"
    exit 1
fi

# Claude-specific processing function: passed to common role setup orchestration in 
# setup_roles_for_cli (in roles-setup library)
create_claude_cmd_from_role() {
    local role_name="$1"
    local target_dir="$2"
    local role_file="$CLAUDE_SUBAGENTS_DIR/${role_name}.md"

    if [[ ! -f "$role_file" ]]; then
        log_warning "Role file not found: $role_file (skipping)"
        return 1
    fi

    # Target command file to create (filename is suffixed 
    # to avoid collisions with user-created commands)
    local command_file="$target_dir/${role_name}-bureau.md"

    # Extract content after frontmatter (everything after the second ---)
    local role_content
    role_content=$(awk '
        BEGIN { in_frontmatter=0; past_frontmatter=0 }
        /^---$/ {
            if (!past_frontmatter) {
                in_frontmatter = !in_frontmatter;
                if (!in_frontmatter) past_frontmatter = 1;
                next;
            }
        }
        past_frontmatter { print }
    ' "$role_file")

    # Create the slash command file with a preamble
    cat > "$command_file" << EOF
Adopt the role and instructions below for this conversation.

---

$role_content
EOF

    log_info "Created /${role_name}-bureau -> $command_file"
    return 0
}

# Cleanup: remove Bureau commands before re-creating enabled ones
cleanup_claude_commands() {
    local target_dir="$1"
    # Remove current Bureau-suffixed commands
    remove_roles_by_pattern "$target_dir" "*-bureau.md"
    # Migration: remove legacy unsuffixed commands that match source catalog
    local src_basename
    local legacy_count=0
    for src in "$CLAUDE_SUBAGENTS_DIR"/*.md; do
        [[ -f "$src" ]] || continue
        src_basename="$(basename "$src")"
        [[ -f "$target_dir/$src_basename" ]] && rm "$target_dir/$src_basename" && legacy_count=$((legacy_count + 1))
    done
    if [[ $legacy_count -gt 0 ]]; then
        log_info "Cleaned up $legacy_count legacy commands"
    fi
}

# Run setup using common workflow
setup_roles_for_cli "Claude Code" "claude" "$HOME/.claude/commands" create_claude_cmd_from_role cleanup_claude_commands


# Print usage instructions
echo ""
log_success "Setup complete!"
echo ""
echo    "Usage:"
echo -e "  1. Launch Claude Code: ${BLUE}claude${NC}"
echo -e "  2. Use any agent role via slash command, e.g. ${BLUE}/architect-bureau${NC}"
echo ""
echo    "Note: These inject the agent prompt into your current conversation."
echo -e "      For isolated subagent tasks, use the ${BLUE}Task tool${NC} instead."
echo ""
