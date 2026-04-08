#!/usr/bin/env bash
#
# Setup script for global/user-scoped config/context files
# Deploys protocol files, regenerates startup context files, and configures
# supported hook-based reinforcement where available.
#
# Architecture: hub-and-spoke context routing
# - ops-hub.md: minimal routing table (loaded via generated context files and
#   reinforced via hooks where the target CLI supports them)
# - ops/*.md: task-specific spokes (read on-demand by agents)
# See docs/plans/2026-03-29-context-hub-spoke-design.md for design details.
#
# Protocol deployment modes:
#   replace            Reconcile Bureau-managed files in place without backup
#   sync               Reconcile Bureau-managed files, backing up replaced files
#   off                Remove Bureau-managed files, hooks, and context wiring

set -euo pipefail

# Retrieve absolute paths
CONFIGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # protocols dir
REPO_ROOT="$(cd "$CONFIGS_DIR/.." && pwd)"
# Source internal Bureau libraries
source "$REPO_ROOT/bin/lib/agent-selection.sh"
source "$REPO_ROOT/bin/lib/logging.sh"

# ── Parse deployment mode flags ─────────────────────────────────────────────
MODE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --protocols|-p)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --protocols/-p requires a mode: replace|r, sync|s, off|o" >&2
                exit 1
            fi
            case "$2" in
                replace|r) MODE="replace" ;;
                sync|s) MODE="sync" ;;
                off|o) MODE="off" ;;
                *)
                    echo "ERROR: invalid protocols mode '$2' (expected replace|r, sync|s, or off|o)" >&2
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        *)
            echo "ERROR: unknown option '$1' (expected --protocols/-p)" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$MODE" ]]; then
    MODE="$(_get_config protocols.mode 2>/dev/null || echo "replace")"
fi

case "$MODE" in
    replace|sync|off) ;;
    *)
        echo "ERROR: invalid protocols.mode '$MODE' in config (expected replace, sync, or off)" >&2
        exit 1
        ;;
esac

# Detect installed CLIs based on directory existence
# (exits if none found, logs detected CLIs)
discover_agents

# Build --agent args for configure-hooks.py (expects lowercase config names,
# not display names like "Claude Code")
CONFIGURE_HOOK_SUPPORTED_AGENTS=(claude codex gemini)
CONFIGURE_HOOK_AGENT_ARGS=()
REMOVE_HOOK_SUPPORTED_AGENTS=(claude codex gemini)
REMOVE_HOOK_AGENT_ARGS=()
for agent in "${AGENTS[@]}"; do
    config_name="$(_agent_config_name "$agent")"
    for supported in "${CONFIGURE_HOOK_SUPPORTED_AGENTS[@]}"; do
        if [[ "$config_name" == "$supported" ]]; then
            CONFIGURE_HOOK_AGENT_ARGS+=(--agent "$config_name")
            break
        fi
    done
    for supported in "${REMOVE_HOOK_SUPPORTED_AGENTS[@]}"; do
        if [[ "$config_name" == "$supported" ]]; then
            REMOVE_HOOK_AGENT_ARGS+=(--agent "$config_name")
            break
        fi
    done
done

log_banner "User-level agent context files setup"
echo "Repo root: $REPO_ROOT"
echo "Selected agents: ${AGENTS[*]}"
echo "Mode: $MODE"
log_empty_line

# ============================================================================
# Populate user-scoped protocols directory (~/.config/bureau/protocols/)
# ============================================================================

BUREAU_PROTOCOLS_DIR="$HOME/.config/bureau/protocols"
STATIC_DIR="$REPO_ROOT/protocols/context/static"

# Bureau-managed file manifest — single source of truth for what Bureau "owns"
BUREAU_HUB_FILE="ops-hub.md"
BUREAU_OUTPUT_STYLE="output-style.md"
BUREAU_CODE_STANDARDS="code-standards.md"
BUREAU_SPOKE_FILES=("session-start.md" "task-assessment.md" "task-execution.md" "task-completion.md")

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

create_safe_symlink() {
    local source="$1"
    local target="$2"

    mkdir -p "$(dirname "$target")"

    if [[ -L "$target" ]]; then
        local current_link
        current_link="$(readlink "$target")"
        if [[ "$current_link" == "$source" ]]; then
            log_info "Symlink already up to date: $target -> $source"
            return 0
        fi
        log_warning "Removing incorrect symlink: $target -> $current_link"
        rm "$target"
    elif [[ -f "$target" ]]; then
        local backup
        backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
        log_warning "Backing up existing file: $target -> $backup"
        mv "$target" "$backup"
    elif [[ -e "$target" ]]; then
        log_error "Cannot create symlink: $target exists and is not a file or symlink"
        exit 1
    fi

    ln -s "$source" "$target"
    log_success "Created symlink: $target -> $source"
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

# ── Reconcile one Bureau-managed file with mode-aware backup behavior ────────
# Args: $1=source $2=destination
_install_managed_file() {
    local src="$1" dest="$2"

    mkdir -p "$(dirname "$dest")"

    if [[ -f "$dest" ]] && cmp -s "$src" "$dest"; then
        return 0
    fi

    if [[ -f "$dest" ]]; then
        if [[ "$MODE" == "sync" ]]; then
            cp "$dest" "${dest}.bak"
            log_warning "Backed up replaced file: $(basename "$dest") → $(basename "$dest").bak"
        else
            log_warning "Replacing Bureau-managed file: $(basename "$dest")"
        fi
    fi

    cp "$src" "$dest"
}

remove_managed_file() {
    local dest="$1"

    if [[ ! -e "$dest" ]]; then
        return 0
    fi

    if [[ "$MODE" == "sync" ]]; then
        cp "$dest" "${dest}.bak"
        log_warning "Backed up removed file: $(basename "$dest") → $(basename "$dest").bak"
    fi

    rm -f "$dest"
}

reconcile_protocol_artifact() {
    local setting="$1"
    local destination="$2"
    local label="$3"
    local tmp_artifact
    local status

    tmp_artifact="$(mktemp)"
    if uv run python "$REPO_ROOT/protocols/scripts/compile-protocol-artifact.py" \
        --setting "$setting" \
        --destination "$tmp_artifact"; then
        _install_managed_file "$tmp_artifact" "$destination"
        rm -f "$tmp_artifact"
        log_success "Compiled Bureau $label to $destination"
        return 0
    fi

    status=$?
    rm -f "$tmp_artifact"

    if [[ "$status" -eq 3 ]]; then
        remove_managed_file "$destination"
        log_info "Disabled Bureau $label runtime artifact"
        return 1
    fi

    return "$status"
}

tailor_deployed_hub() {
    local output_style_enabled="$1"
    local code_standards_enabled="$2"
    local hub_path="$BUREAU_PROTOCOLS_DIR/$BUREAU_HUB_FILE"

    HUB_PATH="$hub_path" \
    OUTPUT_STYLE_ENABLED="$output_style_enabled" \
    CODE_STANDARDS_ENABLED="$code_standards_enabled" \
    uv run python - <<'PY'
from pathlib import Path
import os
import re

hub_path = Path(os.environ["HUB_PATH"])
text = hub_path.read_text(encoding="utf-8")

if os.environ["CODE_STANDARDS_ENABLED"] != "true":
    text = re.sub(
        r'(?m)^\| Writing or editing code \| `[^`]+/code-standards\.md` \|\n',
        "",
        text,
    )

if os.environ["OUTPUT_STYLE_ENABLED"] != "true":
    text = re.sub(
        r"### Output style\n\n.*?\n\n(?=### )",
        "",
        text,
        flags=re.S,
    )

hub_path.write_text(text, encoding="utf-8")
PY
}

# ── Deploy hub and spoke files ───────────────────────────────────────────────
deploy_protocols() {
    local rendered_hub

    mkdir -p "$BUREAU_PROTOCOLS_DIR/ops"

    # migrate old files if upgrading from pre-hub-spoke structure
    migrate_old_files

    rendered_hub="$(mktemp)"
    sed "s|{{PROTOCOLS_DIR}}|$BUREAU_PROTOCOLS_DIR|g" \
        "$STATIC_DIR/$BUREAU_HUB_FILE" > "$rendered_hub"
    _install_managed_file "$rendered_hub" "$BUREAU_PROTOCOLS_DIR/$BUREAU_HUB_FILE"
    rm -f "$rendered_hub"

    for spoke in "${BUREAU_SPOKE_FILES[@]}"; do
        _install_managed_file "$STATIC_DIR/ops/$spoke" "$BUREAU_PROTOCOLS_DIR/ops/$spoke"
    done

    log_success "Deployed hub + spoke files to $BUREAU_PROTOCOLS_DIR"
}

# ── Off mode: remove all protocol files and hooks ────────────────────────────
remove_protocols() {
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
        "${REMOVE_HOOK_AGENT_ARGS[@]}"; then
        log_success "Bureau hooks removed"
    else
        log_warning "Failed to remove some hooks"
    fi

    # Remove legacy context-file symlinks (may be dangling after generated dir removal)
    for old_symlink in "$HOME/.gemini/GEMINI.md" "$HOME/.codex/AGENTS.md" "$HOME/.claude/CLAUDE.md"; do
        if [[ -L "$old_symlink" ]]; then
            rm "$old_symlink"
            log_success "Removed legacy context symlink: $old_symlink"
        fi
    done

    if uv run python "$REPO_ROOT/protocols/scripts/configure-output-style.py" --remove-claude; then
        log_success "Removed Bureau Claude output style"
    else
        log_warning "Failed to remove Bureau Claude output style"
    fi
}

# ── Mode dispatch ────────────────────────────────────────────────────────────
OUTPUT_STYLE_ENABLED=false
CODE_STANDARDS_ENABLED=false

if [[ "$MODE" == "off" ]]; then
    remove_protocols
else
    deploy_protocols

    if reconcile_protocol_artifact \
        "output_style" \
        "$BUREAU_PROTOCOLS_DIR/$BUREAU_OUTPUT_STYLE" \
        "output style"; then
        OUTPUT_STYLE_ENABLED=true
        if agent_enabled "Claude Code"; then
            uv run python "$REPO_ROOT/protocols/scripts/configure-output-style.py" \
                --runtime-output "$BUREAU_PROTOCOLS_DIR/$BUREAU_OUTPUT_STYLE" \
                --install-claude
        fi
    else
        if uv run python "$REPO_ROOT/protocols/scripts/configure-output-style.py" --remove-claude; then
            log_success "Removed Bureau Claude output style"
        else
            log_warning "Failed to remove Bureau Claude output style"
        fi
    fi

    if reconcile_protocol_artifact \
        "code_standards" \
        "$BUREAU_PROTOCOLS_DIR/$BUREAU_CODE_STANDARDS" \
        "code standards"; then
        CODE_STANDARDS_ENABLED=true
    fi

    tailor_deployed_hub "$OUTPUT_STYLE_ENABLED" "$CODE_STANDARDS_ENABLED"
fi

# ============================================================================
# Configure hook-based hub reinforcement where the CLI supports it.
# Codex uses hooks.json plus the codex_hooks feature flag.
# ============================================================================
if [[ "$MODE" != "off" ]]; then
    if [[ ${#CONFIGURE_HOOK_AGENT_ARGS[@]} -gt 0 ]]; then
        log_action "Configuring hook-based hub reinforcement"

        HOOK_ARGS=(--protocols-dir "$BUREAU_PROTOCOLS_DIR" "${CONFIGURE_HOOK_AGENT_ARGS[@]}")
        if [[ "$OUTPUT_STYLE_ENABLED" == true ]]; then
            HOOK_ARGS+=(--output-style-path "$BUREAU_PROTOCOLS_DIR/$BUREAU_OUTPUT_STYLE")
        fi

        if uv run python "$REPO_ROOT/protocols/scripts/configure-hooks.py" \
            "${HOOK_ARGS[@]}"; then
            log_success "Hook-based context injection configured"
        else
            log_warning "Failed to configure hooks"
        fi
    else
        log_info "No hook-capable CLIs detected; skipping hook-based reinforcement"
    fi

    echo ""

    if agent_enabled "Claude Code"; then
        echo "Verification for Claude Code:"
        echo "  - Start a new session and ask 'What operational context were you given?'"
        echo "    (should mention ops-hub and Bureau protocols)"
        echo ""
    fi

    if agent_enabled "Gemini CLI"; then
        echo "Verification for Gemini CLI:"
        echo "  - Start a new session and ask 'What operational context were you given?'"
        echo "    (should mention output-style and ops-hub)"
        echo ""
    fi

    if agent_enabled "Codex"; then
        echo "Verification for Codex:"
        echo "  - Start a new session and ask 'What operational context were you given?'"
        echo "    (should mention output-style and ops-hub)"
        echo ""
    fi

    echo "Configured CLIs now have access to:"
    echo "  - Hub routing table: $BUREAU_PROTOCOLS_DIR/ops-hub.md"
    if [[ "$OUTPUT_STYLE_ENABLED" == true ]]; then
        echo "  - Runtime output style: $BUREAU_PROTOCOLS_DIR/$BUREAU_OUTPUT_STYLE"
    fi
    if [[ "$CODE_STANDARDS_ENABLED" == true ]]; then
        echo "  - Runtime code standards: $BUREAU_PROTOCOLS_DIR/$BUREAU_CODE_STANDARDS"
    fi
    echo "  - Task-specific spokes: $BUREAU_PROTOCOLS_DIR/ops/"
    echo ""
    echo "To customize Bureau-managed protocol content:"
    echo "  1. Update protocols.output_style and/or protocols.code_standards in your config"
    echo "  2. Re-run this script (or bin/open-bureau)"
    echo "  To restore Bureau defaults: bin/reset-protocols"
    echo ""
fi

# ============================================================================
# Set up Bureau-managed skills
# ============================================================================
log_action "Setting up Bureau-managed skills"

SCRIPTS_DIR="$(dirname "${BASH_SOURCE[0]}")"
if [[ -x "$SCRIPTS_DIR/set-up-skills.sh" ]]; then
    "$SCRIPTS_DIR/set-up-skills.sh" --mode "$MODE"
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
