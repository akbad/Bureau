#!/usr/bin/env bash
set -euo pipefail

# Setup script for global config files
# Run from anywhere in the repo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find the repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CONFIGS_DIR/.." && pwd)"

echo -e "${GREEN}Global Config Files Setup${NC}"
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
if [[ ! -f "$CONFIGS_DIR/AGENTS.md" ]] || [[ ! -f "$CONFIGS_DIR/CLAUDE.md" ]]; then
    print_error "Cannot find config files. Please run this script from within the repository."
fi

# ============================================================================
# Set up global context files for all three CLIs
# ============================================================================
print_step "Setting up global context files"

# Create global context file for Gemini
mkdir -p ~/.gemini
ln -sf "$CONFIGS_DIR/AGENTS.md" ~/.gemini/GEMINI.md
print_success "Symlinked AGENTS.md to ~/.gemini/GEMINI.md"

# Create global context file for Codex
ln -sf "$CONFIGS_DIR/AGENTS.md" ~/.codex/AGENTS.md
print_success "Symlinked AGENTS.md to ~/.codex/AGENTS.md"

# Create global context file for Claude Code
ln -sf "$CONFIGS_DIR/CLAUDE.md" ~/.claude/CLAUDE.md
print_success "Symlinked CLAUDE.md to ~/.claude/CLAUDE.md"

echo ""

# ============================================================================
# Done!
# ============================================================================
echo -e "${GREEN}✓ Config files setup complete!${NC}"
echo ""
echo "Verification:"
echo "  - Claude Code: Run '/status' (should show 'Memory: user (~/.claude/CLAUDE.md)')"
echo "  - Gemini CLI: Run '/memory show' (should show GEMINI.md content)"
echo "  - Codex CLI: Ask 'What handoff guidelines were you given?' (should mention clink and delegation)"
echo "    Note: /status shows 'AGENTS files: (none)' due to a display bug, but file IS loaded"
echo ""
echo "All three CLIs now have access to:"
echo "  - Handoff guidelines (delegation rules)"
echo "  - Compact MCP list (tool selection guide)"
echo ""
