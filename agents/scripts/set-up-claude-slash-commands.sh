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

# Claude-specific processing function
process_claude_command() {
    local role_name="$1"
    local target_dir="$2"
    local role_file="$CLAUDE_SUBAGENTS_DIR/${role_name}.md"

    # Skip if file doesn't exist (configuration error)
    if [[ ! -f "$role_file" ]]; then
        log_warning "Role file not found: $role_file (skipping)"
        return 1
    fi

    # Target command file (suffixed to avoid collisions with user-created commands)
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

$agent_content
EOF

    print_info "Created /$agent_name -> $command_file"
    count=$((count + 1))
done

echo ""
print_success "Generated $count slash commands"

# Print usage instructions
echo ""
log_success "Setup complete!"
echo ""
echo "Usage:"
echo -e "  1. Launch Claude Code: ${BLUE}claude${NC}"
echo "  2. Use any agent role via slash command:"
echo ""
echo -e "     ${BLUE}/architect${NC}              - Principal software architect"
echo -e "     ${BLUE}/frontend${NC}               - Frontend architecture & UX"
echo -e "     ${BLUE}/observability${NC}          - Monitoring & incident response"
echo -e "     ${BLUE}/security-compliance${NC}    - Security & privacy architect"
echo -e "     ${BLUE}/testing${NC}                - Test quality & reliability"
echo "     ... and more"
echo ""
echo -e "  3. List all available commands: ${BLUE}/help${NC}"
echo ""
echo "Note: These inject the agent prompt into your current conversation."
echo "      For isolated subagent tasks, continue using the Task tool."
echo ""
