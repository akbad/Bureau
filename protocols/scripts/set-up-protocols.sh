#!/usr/bin/env bash
#
# Setup script for global/user-scoped config/context files
# Deploys protocol files and configures SessionStart hooks for context delivery
#
# Architecture: hub-and-spoke context routing
# - ops-hub.md: minimal routing table (always loaded, re-injected via hooks)
# - ops/*.md: task-specific spokes (read on-demand by agents)
# See docs/plans/2026-03-29-context-hub-spoke-design.md for design details.
#
# Protocol deployment modes:
#   (default)  First-run-only: deploy if directory is empty, skip if files exist
#   --update   Re-copy Bureau-managed files; back up modified ones to .bak
#   --force    Re-copy Bureau-managed files; overwrite without backup (implies --update)
#   --bare     Remove all protocol files and hooks; user manages their own context

set -euo pipefail

# Retrieve absolute paths
CONFIGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # protocols dir
REPO_ROOT="$(cd "$CONFIGS_DIR/.." && pwd)"

# Source internal Bureau libraries
source "$REPO_ROOT/bin/lib/agent-selection.sh"
source "$REPO_ROOT/bin/lib/logging.sh"

# ── Parse deployment mode flags ─────────────────────────────────────────────
MODE_UPDATE=false
MODE_FORCE=false
MODE_BARE=false

for arg in "$@"; do
    case "$arg" in
        --update) MODE_UPDATE=true ;;
        --force)  MODE_FORCE=true; MODE_UPDATE=true ;;  # force implies update
        --bare)   MODE_BARE=true ;;
    esac
done

# conflict check: update + bare is contradictory
if [[ "$MODE_UPDATE" == true && "$MODE_BARE" == true ]]; then
    echo "ERROR: --update/--force and --bare are contradictory" >&2
    exit 1
fi

# Detect installed CLIs based on directory existence
# (exits if none found, logs detected CLIs)
discover_agents

# Build --agent args for configure-hooks.py (expects lowercase config names,
# not display names like "Claude Code"; only agents that support hooks)
HOOK_SUPPORTED_AGENTS=(claude codex gemini)
HOOK_AGENT_ARGS=()
for agent in "${AGENTS[@]}"; do
    config_name="$(_agent_config_name "$agent")"
    for supported in "${HOOK_SUPPORTED_AGENTS[@]}"; do
        if [[ "$config_name" == "$supported" ]]; then
            HOOK_AGENT_ARGS+=(--agent "$config_name")
            break
        fi
    done
done

log_banner "User-level agent context files setup"
echo "Repo root: $REPO_ROOT"
echo "Selected agents: ${AGENTS[*]}"
if [[ "$MODE_BARE" == true ]]; then
    echo "Mode: bare (removing protocol files and hooks)"
elif [[ "$MODE_FORCE" == true ]]; then
    echo "Mode: force update (overwriting without backup)"
elif [[ "$MODE_UPDATE" == true ]]; then
    echo "Mode: update (backing up modified files)"
else
    echo "Mode: default (first-run-only)"
fi
log_empty_line

# ============================================================================
# Populate user-scoped protocols directory (~/.config/bureau/protocols/)
# ============================================================================

BUREAU_PROTOCOLS_DIR="$HOME/.config/bureau/protocols"
STATIC_DIR="$REPO_ROOT/protocols/context/static"

# Bureau-managed file manifest — single source of truth for what Bureau "owns"
BUREAU_HUB_FILE="ops-hub.md"
BUREAU_OUTPUT_STYLE="output-style.md"
BUREAU_SPOKE_FILES=("session-start.md" "task-assessment.md" "task-execution.md" "task-completion.md" "code-standards.md")

# resolve a single path to an absolute path
# rules: ~ → $HOME, / → absolute, else → relative to $REPO_ROOT
resolve_path() {
    local p="$1"
    case "$p" in
        "~"/*) echo "${HOME}${p#"~"}" ;;
        /*)    echo "$p" ;;
        *)     echo "$REPO_ROOT/$p" ;;
    esac
}

# ── Migration: move old-structure files to .deprecated/ ──────────────────────
migrate_old_files() {
    local deprecated_dir="$BUREAU_PROTOCOLS_DIR/.deprecated"
    local migrated=false

    for old_file in "tools-guide.md" "handoff-guide.md"; do
        if [[ -f "$BUREAU_PROTOCOLS_DIR/$old_file" ]]; then
            mkdir -p "$deprecated_dir"
            mv "$BUREAU_PROTOCOLS_DIR/$old_file" "$deprecated_dir/$old_file"
            log_warning "Migrated $old_file to .deprecated/ (replaced by ops/ spoke files)"
            migrated=true
        fi
    done

    if [[ "$migrated" == true ]]; then
        log_action "Old protocol files archived. See docs/plans/2026-03-29-context-hub-spoke-design.md"
    fi
}

# ── Copy a single Bureau-managed file with optional backup ───────────────────
# Args: $1=source $2=destination
# Behavior depends on MODE_UPDATE and MODE_FORCE globals
_copy_managed_file() {
    local src="$1" dest="$2"

    if [[ -f "$dest" ]]; then
        # for hub file: resolve placeholder in-memory before comparing
        local resolved_src
        if [[ "$(basename "$src")" == "$BUREAU_HUB_FILE" ]]; then
            resolved_src=$(sed "s|{{PROTOCOLS_DIR}}|$BUREAU_PROTOCOLS_DIR|g" "$src")
        else
            resolved_src=$(cat "$src")
        fi

        # compare source (resolved) vs destination
        if echo "$resolved_src" | diff -q - "$dest" > /dev/null 2>&1; then
            # identical — overwrite silently (no-op effectively)
            cp "$src" "$dest"
            return
        fi

        # files differ
        if [[ "$MODE_FORCE" == true ]]; then
            log_warning "Overwriting (force): $(basename "$dest")"
        else
            # backup mode — save .bak before overwriting
            cp "$dest" "${dest}.bak"
            log_warning "Backed up modified file: $(basename "$dest") → $(basename "$dest").bak"
        fi
    fi

    cp "$src" "$dest"
}

compile_output_style_artifact() {
    local output_style_raw
    local -a configured_sources
    local -a output_style_sources
    local -a command

    output_style_raw=$(uv run python -m operations.config_cli output_style 2>/dev/null || echo "")
    if [[ -n "$output_style_raw" ]]; then
        read -ra configured_sources <<< "$output_style_raw"
        for raw_path in "${configured_sources[@]}"; do
            output_style_sources+=("$(resolve_path "$raw_path")")
        done
    fi

    if [[ ${#output_style_sources[@]} -eq 0 ]]; then
        output_style_sources=("$STATIC_DIR/ops/$BUREAU_OUTPUT_STYLE")
    fi

    command=(
        uv run python "$REPO_ROOT/protocols/scripts/configure-output-style.py"
        --runtime-output "$BUREAU_PROTOCOLS_DIR/$BUREAU_OUTPUT_STYLE"
    )
    for source in "${output_style_sources[@]}"; do
        command+=(--source "$source")
    done
    if agent_enabled "Claude Code"; then
        command+=(--install-claude)
    fi

    "${command[@]}"
    log_success "Compiled Bureau output style to $BUREAU_PROTOCOLS_DIR/$BUREAU_OUTPUT_STYLE"
}

# ── Deploy hub and spoke files ───────────────────────────────────────────────
deploy_protocols() {
    mkdir -p "$BUREAU_PROTOCOLS_DIR/ops"

    # migrate old files if upgrading from pre-hub-spoke structure
    migrate_old_files

    if [[ "$MODE_UPDATE" == true ]]; then
        # update mode: use manifest-based copy with backup logic
        _copy_managed_file "$STATIC_DIR/$BUREAU_HUB_FILE" "$BUREAU_PROTOCOLS_DIR/$BUREAU_HUB_FILE"
        for spoke in "${BUREAU_SPOKE_FILES[@]}"; do
            _copy_managed_file "$STATIC_DIR/ops/$spoke" "$BUREAU_PROTOCOLS_DIR/ops/$spoke"
        done
    else
        # default mode: fresh copy (only reached when directory was empty)
        cp "$STATIC_DIR/$BUREAU_HUB_FILE" "$BUREAU_PROTOCOLS_DIR/$BUREAU_HUB_FILE"
        for spoke in "${BUREAU_SPOKE_FILES[@]}"; do
            cp "$STATIC_DIR/ops/$spoke" "$BUREAU_PROTOCOLS_DIR/ops/$spoke"
        done
    fi

    # resolve {{PROTOCOLS_DIR}} placeholder in deployed hub
    sed -i '' "s|{{PROTOCOLS_DIR}}|$BUREAU_PROTOCOLS_DIR|g" "$BUREAU_PROTOCOLS_DIR/$BUREAU_HUB_FILE"

    log_success "Deployed hub + spoke files to $BUREAU_PROTOCOLS_DIR"
}

# ── Bare mode: remove all protocol files and hooks ───────────────────────────
bare_protocols() {
    if [[ -d "$BUREAU_PROTOCOLS_DIR" ]]; then
        rm -rf "$BUREAU_PROTOCOLS_DIR"
        log_success "Removed protocols directory: $BUREAU_PROTOCOLS_DIR"
    else
        log_info "Protocols directory already absent: $BUREAU_PROTOCOLS_DIR"
    fi

    # remove Bureau hooks from all CLI configs
    log_action "Removing Bureau hooks from agent configurations..."
    if uv run python "$REPO_ROOT/protocols/scripts/configure-hooks.py" \
        --remove \
        "${HOOK_AGENT_ARGS[@]}"; then
        log_success "Bureau hooks removed"
    else
        log_warning "Failed to remove some hooks"
    fi

    if uv run python "$REPO_ROOT/protocols/scripts/configure-output-style.py" --remove-claude; then
        log_success "Removed Bureau Claude output style"
    else
        log_warning "Failed to remove Bureau Claude output style"
    fi
}

# ── Mode dispatch ────────────────────────────────────────────────────────────
if [[ "$MODE_BARE" == true ]]; then
    bare_protocols
elif [[ "$MODE_UPDATE" == true ]]; then
    # update/force: always re-deploy
    deploy_protocols
else
    # default: deploy only if directory is empty or missing
    if [[ ! -d "$BUREAU_PROTOCOLS_DIR" ]] || [[ -z "$(ls -A "$BUREAU_PROTOCOLS_DIR" 2>/dev/null)" ]]; then
        deploy_protocols
    else
        # still run migration for old-structure files
        migrate_old_files
        log_info "Protocol files already exist; skipping deployment (use --update to refresh)"
    fi
fi

# ============================================================================
# Compile output-style runtime artifact (and Claude native wrapper)
# Skipped in bare mode
# ============================================================================

if [[ "$MODE_BARE" != true ]]; then
    compile_output_style_artifact
fi

# ============================================================================
# Inject custom code_standards paths into hub (if configured)
# Skipped in bare mode (hub file doesn't exist)
# ============================================================================

if [[ "$MODE_BARE" != true ]]; then
    CODE_STANDARDS_RAW=$(uv run python -m operations.config_cli code_standards 2>/dev/null || echo "")

    if [[ -n "$CODE_STANDARDS_RAW" ]]; then
        read -ra CODE_STANDARDS_PATHS <<< "$CODE_STANDARDS_RAW"
        for raw_path in "${CODE_STANDARDS_PATHS[@]}"; do
            resolved="$(resolve_path "$raw_path")"
            # skip if it points to the default code-standards already in ops/
            if [[ "$resolved" == "$BUREAU_PROTOCOLS_DIR/ops/code-standards.md" ]] || \
               [[ "$resolved" == "$BUREAU_PROTOCOLS_DIR/code-standards.md" ]] || \
               [[ "$resolved" == "$STATIC_DIR/ops/code-standards.md" ]]; then
                continue
            fi
            # inject additional read-file-when entry before closing tag
            sed -i '' "s|</bureau:required-context-by-task>|  <read-file-when task=\"writing or editing code (additional standards)\" path=\"$resolved\" />\n\n</bureau:required-context-by-task>|" \
                "$BUREAU_PROTOCOLS_DIR/ops-hub.md"
        done
        log_success "Added custom code_standards paths to ops-hub.md"
    fi
fi

# ============================================================================
# Clean up stale context file symlinks from previous Bureau versions
# (context is now delivered via hooks, not symlinked files)
# ============================================================================

STALE_SYMLINK_PATHS=(
    "$HOME/.claude/CLAUDE.md"
    "$HOME/.gemini/GEMINI.md"
    "$HOME/.codex/AGENTS.md"
)

for symlink_path in "${STALE_SYMLINK_PATHS[@]}"; do
    if [[ -L "$symlink_path" ]]; then
        link_target="$(readlink "$symlink_path")"
        if [[ "$link_target" == *bureau-concierge* ]]; then
            log_warning "Removing stale Bureau symlink: $symlink_path -> $link_target"
            rm "$symlink_path"
        fi
    fi
done

# ============================================================================
# Configure per-prompt hub re-injection hooks
# Skipped in bare mode (hooks already removed by bare_protocols)
# ============================================================================
if [[ "$MODE_BARE" != true ]]; then
    log_action "Configuring per-prompt hub re-injection hooks"

    if uv run python "$REPO_ROOT/protocols/scripts/configure-hooks.py" \
        --protocols-dir "$BUREAU_PROTOCOLS_DIR" \
        "${HOOK_AGENT_ARGS[@]}"; then
        log_success "Hub re-injection hooks configured"
    else
        log_warning "Failed to configure hooks - agents will still read hub at session start"
    fi

    echo ""

    # Show verification steps only for enabled agents
    if agent_enabled "Claude Code"; then
        echo "Verification for Claude Code:"
        echo "  - Start a new session and ask 'What operational context were you given?'"
        echo "    (should mention ops-hub and Bureau protocols)"
        echo ""
    fi

    if agent_enabled "Gemini CLI"; then
        echo "Verification for Gemini CLI:"
        echo "  - Start a new session and ask 'What operational context were you given?'"
        echo "    (should mention ops-hub and Bureau protocols)"
        echo ""
    fi

    if agent_enabled "Codex"; then
        echo "Verification for Codex:"
        echo "  - Start a new session and ask 'What operational context were you given?'"
        echo "    (should mention ops-hub and Bureau protocols)"
        echo ""
    fi

    echo "Configured CLIs now have access to (via SessionStart hooks):"
    echo "  - Hub routing table: $BUREAU_PROTOCOLS_DIR/ops-hub.md"
    echo "  - Task-specific spokes: $BUREAU_PROTOCOLS_DIR/ops/"
    echo ""
    echo "To customize agent context:"
    echo "  1. Edit spoke files in $BUREAU_PROTOCOLS_DIR/ops/"
    echo "  2. Re-run this script (or bin/open-bureau)"
    echo "  To restore defaults: bin/reset-protocols"
    echo ""
fi

# ============================================================================
# Set up Bureau-managed skills
# ============================================================================
log_action "Setting up Bureau-managed skills"

SCRIPTS_DIR="$(dirname "${BASH_SOURCE[0]}")"
if [[ -x "$SCRIPTS_DIR/set-up-skills.sh" ]]; then
    "$SCRIPTS_DIR/set-up-skills.sh"
else
    log_warning "set-up-skills.sh not found or not executable; skipping skill setup"
fi

echo ""

echo "────────────────────────────────────────────────────────────────────────────────"
echo "⚠️ IMPORTANT SECURITY NOTE"
echo
echo "Headless CLI invocations and subagents run with permissive flags."
echo "  • Claude:  --allowedTools or --permission-mode acceptEdits"
echo "  • Codex:   --full-auto"
echo "  • Gemini:  --yolo"
echo ""
echo "This is intentional for automation, especially given subagents are only spawned"
echo "by *users* from within agents that they've launched. However, remain aware:"
echo ""
echo "  • Review changes after delegation completes (git diff)"
echo "  • Don't delegate tasks you wouldn't run yourself"
echo "  • Use fresh git worktrees for maximum isolation when delegating"
echo "────────────────────────────────────────────────────────────────────────────────"
