#!/usr/bin/env bash
set -euo pipefail

# Setup script for agent files and configurations
# Run from the agents/ directory (or anywhere in the repo)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find the repo root (where this script's ancestor directory is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$AGENTS_DIR/.." && pwd)"

# Subdirectory name for symlinked agents
AGENTS_SUBDIR="ecosystem-agents"

echo -e "${GREEN}Agent Ecosystem Setup${NC}"
echo -e "Repo root: $REPO_ROOT"
echo ""

# Function to print step headers
print_step() {
    echo -e "${YELLOW}==>${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error and exit
print_error() {
    echo -e "${RED}✗${NC} $1" >&2
    exit 1
}

# Check if we're in the right place
if [[ ! -d "$AGENTS_DIR/claude-subagents" ]] || [[ ! -d "$AGENTS_DIR/clink-role-prompts" ]]; then
    print_error "Cannot find agent directories. Please run this script from within the repository."
fi

# ============================================================================
# Step 1: Set up clink subagents (for Zen MCP with Gemini/Codex/Claude CLIs)
# ============================================================================
print_step "Setting up clink subagents for Zen MCP"

# Create directory structure
mkdir -p ~/.zen/cli_clients/systemprompts
print_success "Created ~/.zen/cli_clients/systemprompts"

# Symlink role prompts folder
if [[ -L ~/.zen/cli_clients/systemprompts/$AGENTS_SUBDIR ]]; then
    rm ~/.zen/cli_clients/systemprompts/$AGENTS_SUBDIR
    print_success "Removed existing $AGENTS_SUBDIR symlink"
fi
ln -s "$AGENTS_DIR/clink-role-prompts" ~/.zen/cli_clients/systemprompts/$AGENTS_SUBDIR
print_success "Symlinked clink-role-prompts to ~/.zen/cli_clients/systemprompts/$AGENTS_SUBDIR"

# Copy JSON configs
cp "$REPO_ROOT/configs/"*.json ~/.zen/cli_clients/
print_success "Copied CLI configs (*.json) to ~/.zen/cli_clients/"

echo ""

# ============================================================================
# Step 2: Set up Claude Code subagents
# ============================================================================
print_step "Setting up Claude Code subagents"

# Symlink Claude subagents folder
if [[ -L ~/.claude/agents/$AGENTS_SUBDIR ]]; then
    rm ~/.claude/agents/$AGENTS_SUBDIR
    print_success "Removed old symlink at ~/.claude/agents/$AGENTS_SUBDIR"
fi
mkdir -p ~/.claude/agents
print_success "Created ~/.claude/agents directory"

# Symlink all Claude subagent files
ln -s "$AGENTS_DIR/claude-subagents" ~/.claude/agents/$AGENTS_SUBDIR
print_success "Symlinked claude-subagents to ~/.claude/agents/$AGENTS_SUBDIR"

echo ""

# ============================================================================
# Done!
# ============================================================================
echo -e "${GREEN}✓ Agent setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Run the configs setup script: configs/scripts/set-up-configs.sh"
echo "  2. Restart Zen MCP server to reload clink configs"
echo "  3. Verify Claude Code agents with: claude (then run /agents)"
echo "  4. Install claude-mem plugin:"
echo "     > /plugin marketplace add thedotmack/claude-mem"
echo "     > /plugin install claude-mem"
