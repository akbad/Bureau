#!/usr/bin/env bash
#
# Purpose:
# - Installs Bureau's skills to all supported coding agents
# - Handles all Bureau-supported coding agents using the following user-scoped skills dirs:
#     - Claude Code:  ~/.claude/skills/
#     - OpenCode:     ~/.config/opencode/skill/
#     - Codex:        ~/.agents/skills/
#     - Gemini CLI:   ~/.agents/skills/  (shared with Codex)
#
# Args:
#    --dry-run      Show what would be done without making changes
#    --uninstall    Remove all Bureau skill installs

set -e

# Constants for functionality
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # we are in protocols/scripts/, so move up 2 parents

# Source internal Bureau libraries
source "$REPO_ROOT/bin/lib/logging.sh"

DRY_RUN=false
UNINSTALL=false
SKILLS_CONFIG_PATH="$REPO_ROOT/protocols/context/generated/skills-config.generated.json"
SKILLS_CONFIG_GENERATOR="$REPO_ROOT/protocols/scripts/generate-skills-config.py"

# Skill directory locations for each CLI
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
OPENCODE_SKILLS_DIR="$HOME/.config/opencode/skill"
CODEX_GEMINI_SKILLS_DIR="$HOME/.agents/skills"
LEGACY_CODEX_SKILLS_DIR="$HOME/.codex/skills"
LEGACY_BUREAU_SKILL_PREFIX="bureau-"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -u|--uninstall)
            UNINSTALL=true
            shift
            ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# //g'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

ensure_dir() {
    local dir=$1

    if [[ "$DRY_RUN" == true ]]; then
        log_action "Would create:" "$dir"
    else
        mkdir -p "$dir"
    fi
}

is_bureau_skill_symlink() {
    local entry=$1
    local target
    local source_root

    if [[ ! -L "$entry" ]]; then
        return 1
    fi

    target="$(readlink "$entry")"
    for source_root in "${SKILL_SOURCE_ROOTS[@]}"; do
        if [[ "$target" == "$source_root"/* ]]; then
            return 0
        fi
    done

    return 1
}

set_up_bureau_skill_dirs() {
    local skill_conf_dir=$1
    ensure_dir "$skill_conf_dir"

    for ((i = 0; i < ${#SKILL_SOURCE_DIRS[@]}; i++)); do
        local skill_name
        local skill_install_dir
        local skill_source_dir

        skill_name="${SKILL_NAMES[$i]}"
        skill_source_dir="${SKILL_SOURCE_DIRS[$i]}"

        if [[ ! -d "$skill_source_dir" ]]; then
            log_warning "Skipped missing skill dir: $skill_source_dir"
            continue
        fi

        skill_install_dir="$skill_conf_dir/$skill_name"

        if [[ $DRY_RUN == true ]]; then
            log_action "Would link from:" "$skill_install_dir"
            continue
        fi

        # skip foreign content instead of clobbering unprefixed skill names
        if [[ -e "$skill_install_dir" && ! -L "$skill_install_dir" ]]; then
            log_warning "Skipped conflicting non-symlink path: $skill_install_dir"
            continue
        fi

        if [[ -L "$skill_install_dir" ]] && ! is_bureau_skill_symlink "$skill_install_dir"; then
            log_warning "Skipped conflicting foreign symlink: $skill_install_dir"
            continue
        fi

        ln -sfn "$skill_source_dir" "$skill_install_dir"
        log_success "$skill_install_dir"
    done
}

remove_legacy_bureau_skill_dirs() {
    local skill_conf_dir=$1
    local entry

    if [[ ! -d "$skill_conf_dir" ]]; then
        return
    fi

    for entry in "$skill_conf_dir"/${LEGACY_BUREAU_SKILL_PREFIX}*; do
        if [[ ! -e "$entry" ]]; then
            continue
        fi

        if [[ "$DRY_RUN" == true ]]; then
            log_action "Would remove:" "$entry"
        else
            rm -rf "$entry"
            log_success "Removed: $entry"
        fi
    done
}

remove_bureau_skill_dirs() {
    local skill_conf_dir=$1
    local entry

    if [[ ! -d "$skill_conf_dir" ]]; then
        return
    fi

    # remove only symlinks Bureau owns; legacy bureau-* names are cleaned
    #   separately to avoid deleting foreign content at canonical names
    for entry in "$skill_conf_dir"/*; do
        if [[ ! -e "$entry" && ! -L "$entry" ]]; then
            continue
        fi

        if [[ "$(basename "$entry")" == ${LEGACY_BUREAU_SKILL_PREFIX}* ]]; then
            continue
        fi

        if is_bureau_skill_symlink "$entry"; then
            if [[ "$DRY_RUN" == true ]]; then
                log_action "Would remove:" "$entry"
            else
                rm -f "$entry"
                log_success "Removed: $entry"
            fi
        fi
    done

    remove_legacy_bureau_skill_dirs "$skill_conf_dir"
}

# Ensure jq is available
if ! command -v jq >/dev/null 2>&1; then
    log_error "jq is required to parse $SKILLS_CONFIG_PATH"
    exit 1
fi

# Generate skills config
if ! uv run python "$SKILLS_CONFIG_GENERATOR"; then
    log_error "Failed to generate skills config: $SKILLS_CONFIG_GENERATOR"
    exit 1
fi

if [[ ! -f "$SKILLS_CONFIG_PATH" ]]; then
    log_error "Skills config not found: $SKILLS_CONFIG_PATH"
    exit 1
fi

SKILL_NAMES=()
SKILL_SOURCE_DIRS=()
SKILL_SOURCE_ROOTS=()

while IFS=$'\t' read -r name source_path; do
    if [[ -z "$name" || -z "$source_path" ]]; then
        continue
    fi
    SKILL_NAMES+=("$name")
    SKILL_SOURCE_DIRS+=("$source_path")
done < <(jq -r '.skills[] | [.name, .source_path] | @tsv' "$SKILLS_CONFIG_PATH")

while IFS= read -r source_root; do
    if [[ -z "$source_root" ]]; then
        continue
    fi
    SKILL_SOURCE_ROOTS+=("$source_root")
done < <(jq -r '.source_roots[]?' "$SKILLS_CONFIG_PATH")

if [[ ${#SKILL_NAMES[@]} -eq 0 ]]; then
    log_error "No skills found in $SKILLS_CONFIG_PATH"
    exit 1
fi

log_empty_line
log_banner "Bureau skill installation"
echo "Config: $SKILLS_CONFIG_PATH"
echo "Skills found: ${#SKILL_NAMES[@]}"
log_empty_line

if [[ "$DRY_RUN" == true ]]; then
    log_warning "Dry run mode: no changes will be made"
    log_empty_line
fi

log_warning "Removing existing Bureau-owned skill installs..."
log_empty_line

remove_bureau_skill_dirs "$CLAUDE_SKILLS_DIR"
remove_bureau_skill_dirs "$OPENCODE_SKILLS_DIR"
remove_bureau_skill_dirs "$CODEX_GEMINI_SKILLS_DIR"
remove_bureau_skill_dirs "$LEGACY_CODEX_SKILLS_DIR"

log_empty_line
log_success "Bureau skills uninstalled."
log_empty_line

if [[ "$UNINSTALL" == true ]]; then
    exit 0
fi

log_info "Setting up fresh skill installs..."
log_empty_line

log_header "Claude Code" "$CLAUDE_SKILLS_DIR"
set_up_bureau_skill_dirs "$CLAUDE_SKILLS_DIR"
echo ""

log_header "OpenCode" "$OPENCODE_SKILLS_DIR"
set_up_bureau_skill_dirs "$OPENCODE_SKILLS_DIR"
echo ""

log_header "Codex / Gemini CLI" "$CODEX_GEMINI_SKILLS_DIR"
set_up_bureau_skill_dirs "$CODEX_GEMINI_SKILLS_DIR"
echo ""

log_divider
if [[ "$DRY_RUN" == true ]]; then
    log_warning "Dry run complete. Run without --dry-run to apply changes."
else
    log_success "Bureau skills setup complete!"
fi
