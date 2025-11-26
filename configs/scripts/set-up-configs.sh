#!/usr/bin/env bash
set -euo pipefail

# Setup script for global config files
# Generates config files from templates and creates symlinks for portability
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

# Source agent selection library
source "$REPO_ROOT/scripts/lib/agent-selection.sh"

# Detect installed CLIs based on directory existence 
# (exits if none found, logs detected CLIs)
discover_agents

echo -e "${GREEN}User-level agent context files setup${NC}"
echo -e "Repo root: $REPO_ROOT"
echo -e "Selected agents: ${AGENTS[*]}"
echo ""

# Function to print step headers
print_step() {
    echo -e "${YELLOW}==>${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to print error and exit
print_error() {
    echo -e "${RED}✗${NC} $1" >&2
    exit 1
}

# Function to safely create symlink
# Args: $1=source (what the symlink points to), $2=target (symlink location)
# Note: Should only be called for enabled CLIs (check via agent_enabled)
create_safe_symlink() {
    local source="$1"
    local target="$2"

    # Check if target exists
    if [[ -L "$target" ]]; then
        # It's a symlink - check if it points to the right place
        local current_link
        current_link="$(readlink "$target")"
        if [[ "$current_link" == "$source" ]]; then
            print_warning "Symlink already exists: $target -> $source"
            return 0
        else
            # Points to wrong location - remove it
            print_warning "Removing incorrect symlink: $target -> $current_link"
            rm "$target"
        fi
    elif [[ -f "$target" ]]; then
        # It's a regular file - backup before removing
        local backup
        backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
        print_warning "Backing up existing file: $target -> $backup"
        mv "$target" "$backup"
    elif [[ -e "$target" ]]; then
        # Exists but not a file or symlink (directory?)
        print_error "Cannot create symlink: $target exists and is not a file or symlink"
    fi

    # Create the symlink
    ln -s "$source" "$target"
    print_success "Created symlink: $target -> $source"
}

# Check if we're in the right place
if [[ ! -f "$CONFIGS_DIR/AGENTS.md.template" ]] || [[ ! -f "$CONFIGS_DIR/CLAUDE.md.template" ]]; then
    print_error "Cannot find config template files. Please run this script from within the repository."
fi

# ============================================================================
# Generate config files from templates (in repo)
# ============================================================================
print_step "Generating config files from templates"

# Generate AGENTS.md in repo (for Gemini CLI & Codex)
sed "s|{{REPO_ROOT}}|$REPO_ROOT|g" "$CONFIGS_DIR/AGENTS.md.template" > "$CONFIGS_DIR/AGENTS.md"
print_success "Generated $CONFIGS_DIR/AGENTS.md from template"

# Generate CLAUDE.md in repo (for Claude Code)
sed "s|{{REPO_ROOT}}|$REPO_ROOT|g" "$CONFIGS_DIR/CLAUDE.md.template" > "$CONFIGS_DIR/CLAUDE.md"
print_success "Generated $CONFIGS_DIR/CLAUDE.md from template"

echo ""

# ============================================================================
# Create symlinks from CLI config locations to repo files
# ============================================================================
print_step "Creating symlinks to generated config files"

# Symlink for Gemini CLI
if agent_enabled "Gemini CLI"; then
    create_safe_symlink "$CONFIGS_DIR/AGENTS.md" "$HOME/.gemini/GEMINI.md"
else
    print_step "Skipping Gemini symlink (user-scoped CLI directory not found)"
fi

# Symlink for Codex
if agent_enabled "Codex"; then
    create_safe_symlink "$CONFIGS_DIR/AGENTS.md" "$HOME/.codex/AGENTS.md"
else
    print_step "Skipping Codex symlink (user-scoped CLI directory not found)"
fi

# Symlink for Claude Code
if agent_enabled "Claude Code"; then
    create_safe_symlink "$CONFIGS_DIR/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
else
    print_step "Skipping Claude symlink (user-scoped CLI directory not found)"
fi

echo ""

echo -e "${GREEN}✓ Config files setup complete!${NC}"
echo ""

# Show verification steps only for enabled agents
if agent_enabled "Claude Code"; then
    echo "Verification for Claude Code:"
    echo "  - Run '/status' (should show 'Memory: user (~/.claude/CLAUDE.md)')"
    echo ""
fi

if agent_enabled "Gemini CLI"; then
    echo "Verification for Gemini CLI:"
    echo "  - Run '/memory show' (should show GEMINI.md content)"
    echo ""
fi

if agent_enabled "Codex"; then
    echo "Verification for Codex:"
    echo "  - Ask 'What handoff guidelines were you given?' (should mention clink and delegation)"
    echo "    Note: /status shows 'AGENTS files: (none)' due to a display bug, but file IS loaded"
    echo ""
fi

echo "Configured CLIs now have access to:"
echo "  - Handoff guidelines (delegation rules)"
echo "  - Compact MCP list (tool selection guide)"
echo ""
echo "Config files are symlinked from $CONFIGS_DIR/"
echo "To update configs, edit the templates and re-run this script"
echo ""
