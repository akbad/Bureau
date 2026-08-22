#!/usr/bin/env bash
#
# Install Bureau roles for Grok Build as:
#   - agent definitions under ~/.grok/agents/bureau-<role>.md (subagent / agent types)
#   - slash commands under ~/.grok/commands/<role>-bureau.md (interactive activation)
#
# Role bodies come from agents/role-prompts/ (same as Codex/Gemini/OpenCode).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$AGENTS_DIR/.." && pwd)"
ROLE_PROMPTS_DIR="$AGENTS_DIR/role-prompts"

source "$REPO_ROOT/bin/lib/agent-selection.sh"
source "$REPO_ROOT/bin/lib/logging.sh"
source "$REPO_ROOT/bin/lib/roles-setup.sh"

discover_agents

GROK_AGENTS_DIR="$HOME/.grok/agents"
GROK_COMMANDS_DIR="$HOME/.grok/commands"

log_action "Setting up Grok Build roles"
echo "Source: $ROLE_PROMPTS_DIR"
echo "Agents target: $GROK_AGENTS_DIR"
echo "Commands target: $GROK_COMMANDS_DIR"
log_empty_line

if [[ ! -d "$ROLE_PROMPTS_DIR" ]]; then
    log_error "Cannot find role-prompts/ at $ROLE_PROMPTS_DIR"
    exit 1
fi

# Extract a one-line description from a role prompt body (first non-empty line).
_role_description() {
    local role_file="$1"
    awk '
        BEGIN { in_fm=0; past=0 }
        /^---$/ {
            if (!past) { in_fm = !in_fm; if (!in_fm) past=1; next }
        }
        past || !in_fm {
            line=$0
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
            if (line != "") { print line; exit }
        }
    ' "$role_file"
}

# Strip YAML frontmatter from a role file; print body only.
_role_body() {
    local role_file="$1"
    awk '
        BEGIN { in_frontmatter=0; past_frontmatter=0 }
        /^---$/ {
            if (!past_frontmatter) {
                in_frontmatter = !in_frontmatter
                if (!in_frontmatter) past_frontmatter = 1
                next
            }
        }
        past_frontmatter { print }
        !past_frontmatter && !in_frontmatter { print }
    ' "$role_file"
}

create_grok_role_artifacts() {
    local role_name="$1"
    local _target_dir="$2"  # unused; we write to fixed Grok dirs
    local role_file="$ROLE_PROMPTS_DIR/${role_name}.md"

    if [[ ! -f "$role_file" ]]; then
        log_warning "Role file not found: $role_file (skipping)"
        return 1
    fi

    mkdir -p "$GROK_AGENTS_DIR" "$GROK_COMMANDS_DIR"

    local desc
    desc="$(_role_description "$role_file")"
    if [[ -z "$desc" ]]; then
        desc="Bureau ${role_name} role"
    fi
    # YAML-safe single-line description
    desc="${desc//$'\n'/ }"
    desc="${desc//\"/\'}"

    local agent_file="$GROK_AGENTS_DIR/bureau-${role_name}.md"
    {
        cat <<EOF
---
name: bureau-${role_name}
description: "${desc}"
model: inherit
prompt_mode: full
permission_mode: default
agents_md: true
---

EOF
        _role_body "$role_file"
    } > "$agent_file"
    log_info "Created Grok agent bureau-${role_name} -> $agent_file"

    local command_file="$GROK_COMMANDS_DIR/${role_name}-bureau.md"
    {
        cat <<'EOF'
Adopt the role and instructions below for this conversation.

---

EOF
        _role_body "$role_file"
    } > "$command_file"
    log_info "Created Grok command /${role_name}-bureau -> $command_file"

    return 0
}

cleanup_grok_roles() {
    local _target_dir="$1"
    local count=0
    local f

    for f in "$GROK_AGENTS_DIR"/bureau-*.md; do
        [[ -e "$f" ]] || continue
        rm -f "$f"
        count=$((count + 1))
    done
    for f in "$GROK_COMMANDS_DIR"/*-bureau.md; do
        [[ -e "$f" ]] || continue
        rm -f "$f"
        count=$((count + 1))
    done
    if [[ $count -gt 0 ]]; then
        log_info "Cleaned up $count existing Bureau Grok role artifacts"
    fi
}

# setup_roles_for_cli requires a target dir; we use GROK_AGENTS_DIR as the
# primary and create commands as a side effect in the process callback.
setup_roles_for_cli "Grok Build" "grok" "$GROK_AGENTS_DIR" create_grok_role_artifacts cleanup_grok_roles

log_success "Grok Build roles setup complete"
