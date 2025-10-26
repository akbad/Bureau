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
if [[ -L ~/.zen/cli_clients/systemprompts/clink-role-prompts ]]; then
    rm ~/.zen/cli_clients/systemprompts/clink-role-prompts
    print_success "Removed existing clink-role-prompts symlink"
fi
ln -s "$AGENTS_DIR/clink-role-prompts" ~/.zen/cli_clients/systemprompts/clink-role-prompts
print_success "Symlinked clink-role-prompts to ~/.zen/cli_clients/systemprompts/"

# Copy JSON configs
cp "$AGENTS_DIR/configs/"*.json ~/.zen/cli_clients/
print_success "Copied CLI configs (*.json) to ~/.zen/cli_clients/"

# Create global context file for Gemini
mkdir -p ~/.gemini
ln -sf "$AGENTS_DIR/configs/AGENTS.md" ~/.gemini/GEMINI.md
print_success "Symlinked AGENTS.md to ~/.gemini/GEMINI.md"

# Create global context file for Codex (via hierarchical discovery)
ln -sf "$AGENTS_DIR/configs/AGENTS.md" ~/AGENTS.md
print_success "Symlinked AGENTS.md to ~/AGENTS.md (discovered by Codex hierarchically)"

echo ""

# ============================================================================
# Step 2: Set up Claude Code subagents
# ============================================================================
print_step "Setting up Claude Code subagents"

# Create directory structure
mkdir -p ~/.claude/agents
print_success "Created ~/.claude/agents"

# Symlink all Claude subagent files individually (ln -s doesn't expand globs)
for agent_file in "$AGENTS_DIR/claude-subagents"/*.md; do
    agent_name="$(basename "$agent_file")"
    ln -sf "$agent_file" ~/.claude/agents/"$agent_name"
done
print_success "Symlinked all Claude subagent files to ~/.claude/agents/"

# Symlink global CLAUDE.md context file
ln -sf "$AGENTS_DIR/configs/CLAUDE.md" ~/.claude/CLAUDE.md
print_success "Symlinked CLAUDE.md to ~/.claude/CLAUDE.md"

echo ""

# ============================================================================
# Done!
# ============================================================================
echo -e "${GREEN}✓ Agent setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Zen MCP server to reload clink configs"
echo "  2. Verify Claude Code agents with: claude (then run /agents)"
echo "  3. Install claude-mem plugin:"
echo "     > /plugin marketplace add thedotmack/claude-mem"
echo "     > /plugin install claude-mem"
echo ""
echo "All three CLIs now have access to:"
echo "  - Handoff guidelines (delegation rules)"
echo "  - Compact MCP list (tool selection guide)"
echo ""
echo "Note: Codex discovers ~/AGENTS.md via hierarchical parent search."
echo "      Works for any project under your home directory."
