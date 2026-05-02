#!/usr/bin/env bash
#
# Tools setup script for Bureau (for MCP servers, backing Docker containers, etc.)
#
# Prerequisites:
#   Dependencies:
#       - Node.js/npm
#       - uv/uvx with Python 3.12+
#       - Docker daemon (Docker Desktop or Rancher Desktop)
#
#   API keys (for cloud-based MCP servers, note **all offer free tiers**):
#       - Tavily API key in $TAVILY_API_KEY
#       - Brave Search API key in $BRAVE_API_KEY
#       - Context7 API key in $CONTEXT7_API_KEY
#
# Usage: ./set-up-tools.sh

set -e  # exit on error

# setup flags
MODE_BARE=false
for arg in "$@"; do
    case "$arg" in
        --bare) MODE_BARE=true ;;
    esac
done

# --- CONFIG ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Helper to read from merged config (merge order: defaults.yml → .bureau.yml → local.yml → env)
cfg() {
    local key="$1"
    (cd "$REPO_ROOT" && uv run get-config "$key" 2>/dev/null) || true
}

SERVER_START_TIMEOUT="$(cfg startup_timeout_for.mcp_servers)"
DOCKER_TIMEOUT="$(cfg startup_timeout_for.docker_daemon)"

# Source internal Bureau libraries
source "$REPO_ROOT/bin/lib/agent-selection.sh"
source "$REPO_ROOT/bin/lib/logging.sh"

# Supported agents' printable string names
CLAUDE="Claude Code"
CODEX="Codex"
GEMINI="Gemini CLI"

# User-level config locations for supported coding CLIs
GEMINI_CONFIG="$HOME/.gemini/settings.json"
CODEX_CONFIG="$HOME/.codex/config.toml"
CLAUDE_CONFIG="$HOME/.claude/settings.json"
CLAUDE_CLI_STATE="$HOME/.claude.json"
OPENCODE_CONFIG="$HOME/.config/opencode/opencode.json"

# Contains the list of agents to be configured by this script to use Bureau and its tools
# Populated later by discover_agents() based on the YML configs
AGENTS=()

# --- CONFIG VALUES ---

# Detect enabled agents based on YML configs (exits if none found, logs detected CLIs)
discover_agents

# Render resolved MCP setup plan (used throughout the script)
SETUP_PLAN_JSON="$(uv run python "$REPO_ROOT/tools/scripts/render-mcp-setup.py")"
SETUP_PLAN_FILE="$(mktemp)"
echo "$SETUP_PLAN_JSON" > "$SETUP_PLAN_FILE"

declare -A HTTP_SERVICE_PIDS
declare -A HTTP_SERVICE_PORTS
declare -A HTTP_SERVICE_LOGS
DOCKER_CONTAINERS=()

# --- HELPERS ---

plan_jq() {
    local query=$1
    jq -r "$query" "$SETUP_PLAN_FILE"
}

AUTO_APPROVE_MCP=false
if [[ "$(plan_jq '.auto_approved.mcp_tools // false')" == "true" ]]; then
    AUTO_APPROVE_MCP=true
fi

AUTO_CLEAN_MCP=false
if [[ "$(plan_jq '.prune_disabled_mcps // false')" == "true" ]]; then
    AUTO_CLEAN_MCP=true
fi


expand_tilde() {
    local value=$1
    if [[ "$value" == "~"* ]]; then
        echo "${value/#\~/$HOME}"
    else
        echo "$value"
    fi
}

# Parse common stdio MCP arguments into global variables
# Sets: _STDIO_ENV_PAIRS, _STDIO_TIMEOUT_MS, _STDIO_STARTUP_TIMEOUT, _STDIO_TOOL_TIMEOUT, _STDIO_CMD_ARGS
# Usage: parse_stdio_mcp_args "$@"
parse_stdio_mcp_args() {
    _STDIO_ENV_PAIRS=()
    _STDIO_TIMEOUT_MS=""
    _STDIO_STARTUP_TIMEOUT=""
    _STDIO_TOOL_TIMEOUT=""
    _STDIO_CMD_ARGS=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                # Expand shell variables in env values so they're resolved at
                # setup time, not left as literals in configs.
                _STDIO_ENV_PAIRS+=("$(eval echo "$2")")
                shift 2
                ;;
            --timeout-ms)
                _STDIO_TIMEOUT_MS=$2
                shift 2
                ;;
            --startup-timeout-sec)
                _STDIO_STARTUP_TIMEOUT=$2
                shift 2
                ;;
            --tool-timeout-sec)
                _STDIO_TOOL_TIMEOUT=$2
                shift 2
                ;;
            --)
                shift
                _STDIO_CMD_ARGS+=("$@")
                break
                ;;
            *)
                _STDIO_CMD_ARGS+=("$1")
                shift
                ;;
        esac
    done
}

MANAGED_MCP_REGISTRY_DIR="$HOME/.config/bureau/internal"
SERVICE_REGISTRY_PATH="$MANAGED_MCP_REGISTRY_DIR/managed-services.json"

managed_registry_path() {
    local cli=$1
    echo "$MANAGED_MCP_REGISTRY_DIR/managed-mcps.$cli.json"
}

remove_opencode_servers() {
    local target=$1
    shift
    local servers=("$@")
    if [[ ${#servers[@]} -eq 0 ]]; then
        return 0
    fi

    uv run "$SCRIPT_DIR/remove-opencode-servers.py" "$target" "${servers[@]}"
}

remove_managed_servers() {
    local cli=$1
    shift
    local servers=("$@")
    if [[ ${#servers[@]} -eq 0 ]]; then
        return 0
    fi

    case "$cli" in
        claude)
            for server_id in "${servers[@]}"; do
                claude mcp remove "$server_id" --scope user
            done
            ;;
        gemini)
            for server_id in "${servers[@]}"; do
                gemini mcp remove "$server_id"
            done
            ;;
        codex)
            for server_id in "${servers[@]}"; do
                codex mcp remove "$server_id"
            done
            ;;
        opencode)
            remove_opencode_servers "$OPENCODE_CONFIG" "${servers[@]}"
            ;;
        *)
            log_warning "Unknown CLI for managed MCP cleanup: $cli"
            ;;
    esac
}

managed_registry_reconcile() {
    local cli=$1
    local config_path=$2
    local allow_prune=$3
    local registry_path
    registry_path="$(managed_registry_path "$cli")"

    local reconcile_json
    reconcile_json="$(uv run python "$REPO_ROOT/tools/scripts/managed-mcp-registry.py" \
        --mode reconcile \
        --cli "$cli" \
        --plan "$SETUP_PLAN_FILE" \
        --registry "$registry_path" \
        --config "$config_path")"

    local -a to_update
    local -a to_remove
    local -a servers_to_remove
    mapfile -t to_update < <(echo "$reconcile_json" | jq -r '.to_update[]?')
    if [[ "$allow_prune" == "true" ]]; then
        mapfile -t to_remove < <(echo "$reconcile_json" | jq -r '.to_remove[]?')
    else
        to_remove=()
    fi
    servers_to_remove=("${to_update[@]}" "${to_remove[@]}")

    if [[ ${#to_update[@]} -gt 0 ]]; then
        log_info "Refreshing Bureau-managed MCPs for $cli: ${to_update[*]}"
    fi
    if [[ ${#to_remove[@]} -gt 0 ]]; then
        log_info "Removing disabled Bureau-managed MCPs for $cli: ${to_remove[*]}"
    fi

    remove_managed_servers "$cli" "${servers_to_remove[@]}"
}

managed_registry_record() {
    local cli=$1
    local config_path=$2
    local registry_path
    registry_path="$(managed_registry_path "$cli")"

    uv run python "$REPO_ROOT/tools/scripts/managed-mcp-registry.py" \
        --mode record \
        --cli "$cli" \
        --plan "$SETUP_PLAN_FILE" \
        --registry "$registry_path" \
        --config "$config_path" >/dev/null
}

# Check if a port is already in use 
# (If it is, it's assumed to be by what this script intends to launch on it)
check_port() {
    local port=$1
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}


wait_for_tcp() {
    local service_name=$1
    local port=$2
    local timeout=$3
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))
        if check_port "$port"; then
            log_success "$service_name is ready on port $port"
            return 0
        fi
    done

    log_error "$service_name did not open port $port within ${timeout}s"
    return 1
}

wait_for_http() {
    local service_id=$1
    local service_name=$2
    local url=$3
    local timeout=$4
    local elapsed=0
    local -a curl_headers=()
    local header

    while IFS= read -r header; do
        if [[ -n "$header" ]]; then
            curl_headers+=(-H "$header")
        fi
    done < <(
        plan_jq ".services[\"$service_id\"].healthcheck.http_headers // {} | to_entries[] | \"\\(.key): \\(.value)\""
    )

    while [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))
        if curl -fsS --max-time 2 "${curl_headers[@]}" "$url" >/dev/null 2>&1; then
            log_success "$service_name HTTP healthcheck passed: $url"
            return 0
        fi
    done

    log_error "$service_name HTTP healthcheck failed within ${timeout}s: $url"
    return 1
}

has_mcp_tool_healthcheck() {
    local service_id=$1
    jq -e --arg service "$service_id" \
        '.services[$service].healthcheck.mcp_tool? != null' \
        "$SETUP_PLAN_FILE" >/dev/null
}

run_mcp_tool_healthcheck() {
    local service_id=$1
    local service_name=$2
    local timeout=$3
    local elapsed=0
    local url
    local tool
    local arguments_json
    local expected_server_name
    local probe_output=""

    url=$(jq -r --arg service "$service_id" \
        '.services[$service].healthcheck.mcp_tool.url' "$SETUP_PLAN_FILE")
    tool=$(jq -r --arg service "$service_id" \
        '.services[$service].healthcheck.mcp_tool.tool' "$SETUP_PLAN_FILE")
    arguments_json=$(jq -c --arg service "$service_id" \
        '.services[$service].healthcheck.mcp_tool.arguments' "$SETUP_PLAN_FILE")
    expected_server_name=$(jq -r --arg service "$service_id" \
        '.services[$service].healthcheck.mcp_tool.expected_server_name // empty' \
        "$SETUP_PLAN_FILE")

    local probe_args=(
        --url "$url"
        --tool "$tool"
        --arguments-json "$arguments_json"
        --timeout-seconds 5
    )
    if [[ -n "$expected_server_name" ]]; then
        probe_args+=(--expected-server-name "$expected_server_name")
    fi

    while [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))
        if probe_output="$(uv run python "$SCRIPT_DIR/probe-mcp-tool.py" "${probe_args[@]}" 2>&1)"; then
            log_success "$service_name MCP tool healthcheck passed: $tool"
            return 0
        fi
    done

    log_error "$service_name MCP tool healthcheck failed within ${timeout}s: $tool"
    if [[ -n "$probe_output" ]]; then
        log_error "Last MCP probe error: $probe_output"
    fi
    return 1
}

run_service_healthchecks() {
    local service_id=$1
    local service_name=$2
    local tcp_port
    local http_url

    tcp_port=$(plan_jq ".services[\"$service_id\"].healthcheck.tcp // empty")
    if [[ -n "$tcp_port" && "$tcp_port" != "null" ]]; then
        if ! wait_for_tcp "$service_name" "$tcp_port" "$SERVER_START_TIMEOUT"; then
            return 1
        fi
    fi

    http_url=$(plan_jq ".services[\"$service_id\"].healthcheck.http // empty")
    if [[ -n "$http_url" && "$http_url" != "null" ]]; then
        if ! wait_for_http "$service_id" "$service_name" "$http_url" "$SERVER_START_TIMEOUT"; then
            return 1
        fi
    fi

    if has_mcp_tool_healthcheck "$service_id"; then
        if ! run_mcp_tool_healthcheck "$service_id" "$service_name" "$SERVER_START_TIMEOUT"; then
            return 1
        fi
    fi
}

port_listener_pid() {
    local port=$1
    lsof -ti:"$port" -sTCP:LISTEN 2>/dev/null | head -1
}

assess_managed_service() {
    local service_id=$1
    local port_listening=$2

    uv run python "$REPO_ROOT/tools/scripts/managed-service-registry.py" \
        --mode assess \
        --plan "$SETUP_PLAN_FILE" \
        --registry "$SERVICE_REGISTRY_PATH" \
        --service "$service_id" \
        --port-listening "$port_listening"
}

record_managed_service() {
    local service_id=$1
    local pid=$2
    local log_file=$3
    local last_action=$4
    local args=(
        --mode record-managed
        --plan "$SETUP_PLAN_FILE"
        --registry "$SERVICE_REGISTRY_PATH"
        --service "$service_id"
        --last-action "$last_action"
    )

    if [[ -n "$pid" ]]; then
        args+=(--pid "$pid")
    fi
    if [[ -n "$log_file" ]]; then
        args+=(--log-file "$log_file")
    fi

    uv run python "$REPO_ROOT/tools/scripts/managed-service-registry.py" "${args[@]}" >/dev/null
}

record_adopted_service() {
    local service_id=$1
    local pid=$2
    local log_file=$3
    local args=(
        --mode record-adopted
        --plan "$SETUP_PLAN_FILE"
        --registry "$SERVICE_REGISTRY_PATH"
        --service "$service_id"
    )

    if [[ -n "$pid" ]]; then
        args+=(--pid "$pid")
    fi
    if [[ -n "$log_file" ]]; then
        args+=(--log-file "$log_file")
    fi

    uv run python "$REPO_ROOT/tools/scripts/managed-service-registry.py" "${args[@]}" >/dev/null
}

stop_port_process() {
    local service_name=$1
    local port=$2
    local kill_parent=${3:-false}
    local pid
    local ppid
    local elapsed=0

    pid=$(port_listener_pid "$port")
    if [[ -z "$pid" ]]; then
        return 0
    fi

    log_info "Stopping $service_name listener on port $port (PID: $pid)..."
    ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ' || true)
    kill "$pid" 2>/dev/null || true
    if [[ "$kill_parent" == "true" && "$ppid" =~ ^[0-9]+$ && "$ppid" -gt 1 ]]; then
        kill "$ppid" 2>/dev/null || true
    fi

    while [ $elapsed -lt 10 ]; do
        if ! check_port "$port"; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    log_error "$service_name listener on port $port did not stop"
    return 1
}

prepare_docker_service_files() {
    local service_id=$1

    case "$service_id" in
        searxng)
            log_info "Rendering managed SearXNG settings..."
            uv run python "$SCRIPT_DIR/render-searxng-settings.py" \
                --plan "$SETUP_PLAN_FILE" \
                --service "$service_id" >/dev/null
            ;;
    esac
}

start_docker_container() {
    local service_id=$1
    local container_name
    local image
    local host_bind
    local host_port
    local container_port
    local recreate_on_setup
    local publish_arg

    container_name=$(plan_jq ".services[\"$service_id\"].container_name // \"$service_id\"")
    image=$(plan_jq ".services[\"$service_id\"].image")
    host_bind=$(plan_jq ".services[\"$service_id\"].host_bind // empty")
    host_port=$(plan_jq ".services[\"$service_id\"].host_port")
    container_port=$(plan_jq ".services[\"$service_id\"].container_port")
    recreate_on_setup=$(plan_jq ".services[\"$service_id\"].recreate_on_setup // false")

    prepare_docker_service_files "$service_id"

    if [[ -n "$host_bind" ]]; then
        publish_arg="${host_bind}:${host_port}:${container_port}"
    else
        publish_arg="${host_port}:${container_port}"
    fi

    if [[ "$recreate_on_setup" == "true" ]] && \
       docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        log_info "Recreating $service_id container to apply managed configuration..."
        docker rm -f "$container_name" >/dev/null
    fi

    # Check if container exists and is running
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        log_success "$service_id container already running"
    elif docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        log_info "Starting existing $service_id container..."
        docker start "$container_name" >/dev/null
        sleep 2
        log_success "$service_id container started"
    else
        log_info "Creating and starting $service_id container..."
        local env_args=()
        while IFS= read -r env_pair; do
            env_args+=(-e "$env_pair")
        done < <(plan_jq ".services[\"$service_id\"].env // {} | to_entries[] | \"\(.key)=\(.value)\"")

        local mount_args=()
        while IFS= read -r mount; do
            local host_path
            local container_path
            local mount_type
            host_path=$(echo "$mount" | jq -r '.host_path')
            container_path=$(echo "$mount" | jq -r '.container_path')
            mount_type=$(echo "$mount" | jq -r '.type // "directory"')
            host_path=$(expand_tilde "$host_path")
            if [[ "$mount_type" == "file" ]]; then
                mkdir -p "$(dirname "$host_path")"
                [[ -f "$host_path" ]] || touch "$host_path"
            else
                mkdir -p "$host_path"
            fi
            mount_args+=(-v "$host_path:$container_path")
        done < <(plan_jq ".services[\"$service_id\"].mounts // [] | .[] | @json")

        docker run -d \
            --name "$container_name" \
            -p "$publish_arg" \
            "${env_args[@]}" \
            "${mount_args[@]}" \
            "$image" >/dev/null

        sleep 2
        log_success "$service_id container started on port $host_port"
    fi

    DOCKER_CONTAINERS+=("$container_name")
    run_service_healthchecks "$service_id" "$service_id"
}

# Wait for a server process to open its port or exit (success/failure)
wait_for_server_startup() {
    local server_name=$1
    local pid=$2
    local port=$3
    local timeout=$4
    local log_file=$5
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))

        # Process exited - capture exit code and fail fast
        if ! kill -0 "$pid" 2>/dev/null; then
            local exit_code
            wait "$pid"
            exit_code=$?
            if [[ $exit_code -eq 0 ]]; then
                log_error "$server_name exited cleanly before opening port $port"
            else
                log_error "$server_name exited with code $exit_code before opening port $port"
            fi
            log_empty_line
            log_error "Log file saved at: $log_file"
            return 1
        fi

        # Port became available → server ready
        if check_port "$port"; then
            log_success "$server_name started (PID: $pid) after ${elapsed}s"
            return 0
        fi
    done

    log_error "$server_name did not open port $port within ${timeout}s (process still running)"
    log_empty_line
    log_error "Log file saved at: $log_file"
    return 1
}

# Start HTTP server idempotently (returns PID via variable name passed as arg)
start_http_server() {
    local server_name=$1
    local port=$2
    local pid_var=$3  # Variable name to store PID
    shift 3
    local start_cmd=("$@")
    local log_file="/tmp/mcp-${server_name}-server.log"
    local pid

    if check_port "$port"; then
        log_error "$server_name cannot start; port $port is already in use"
        return 1
    fi

    log_info "Starting $server_name on port $port with ${SERVER_START_TIMEOUT}sec timeout..."
    log_info "  → launch command: ${start_cmd[*]}"

    # Start tail first (waits for file creation)
    tail -f "$log_file" 2>/dev/null &
    local tail_pid=$!

    # Start server with output to log file (nohup ensures survival after terminal closes)
    nohup "${start_cmd[@]}" > "$log_file" 2>&1 &
    pid=$!

    local startup_ok=true
    if wait_for_server_startup "$server_name" "$pid" "$port" "$SERVER_START_TIMEOUT" "$log_file"; then
        eval "$pid_var=$pid"
    else
        startup_ok=false
    fi

    # Stop showing output
    kill "$tail_pid" 2>/dev/null

    # Wait for the process to be fully killed, while ignoring exit code (returns 143 after being killed)
    wait "$tail_pid" 2>/dev/null || true

    if [[ "$startup_ok" == true ]]; then
        return 0
    else
        exit 1
    fi
}

clean_fastembed_cache_if_corrupt() {
    # If a fastembed model download was interrupted, the cache contains .incomplete
    # blob files and an empty onnx/ dir. ONNX runtime then fails with NoSuchFile.
    # Detect this and wipe the model cache so fastembed re-downloads cleanly.
    local env_pairs=("$@")
    local provider="" model=""
    for pair in "${env_pairs[@]}"; do
        case "$pair" in
            EMBEDDING_PROVIDER=*) provider="${pair#*=}" ;;
            EMBEDDING_MODEL=*)    model="${pair#*=}" ;;
        esac
    done
    [[ "$provider" == "fastembed" && -n "$model" ]] || return 0

    local cache_dir="$HOME/.cache/fastembed/models--${model//\//--}"
    [[ -d "$cache_dir" ]] || return 0

    if compgen -G "$cache_dir/blobs/*.incomplete" > /dev/null 2>&1; then
        log_warning "Detected incomplete fastembed model download for $model — clearing cache to re-download"
        rm -rf "$cache_dir"
    fi
}

register_http_service_runtime() {
    local service_id=$1
    local service_name=$2
    local health_port=$3
    local pid_var=$4
    local pid

    # Always resolve to the actual port-binding PID (the process holding the
    # LISTEN socket), not the PID from $! which may be a parent wrapper (e.g.
    # uv/uvx forks a child Python process rather than exec'ing into it).
    # This keeps PID reporting consistent across first-run and reuse paths.
    pid=$(port_listener_pid "$health_port")
    if [[ -z "$pid" ]]; then
        # Fallback to the PID from start_http_server (should not happen if
        # the server started or was found successfully).
        pid=$(eval "echo \${$pid_var:-}")
    fi
    HTTP_SERVICE_PIDS["$service_id"]="$pid"
    HTTP_SERVICE_PORTS["$service_id"]="$health_port"
    HTTP_SERVICE_LOGS["$service_id"]="/tmp/mcp-${service_name}-server.log"
}

start_and_record_http_service() {
    local service_id=$1
    local service_name=$2
    local health_port=$3
    local pid_var=$4
    local last_action=$5
    shift 5
    local start_cmd=("$@")
    local log_file="/tmp/mcp-${service_name}-server.log"
    local pid

    start_http_server "$service_name" "$health_port" "$pid_var" "${start_cmd[@]}"
    register_http_service_runtime "$service_id" "$service_name" "$health_port" "$pid_var"

    if ! run_service_healthchecks "$service_id" "$service_name"; then
        log_error "$service_name failed healthchecks after launch; stopping it"
        stop_port_process "$service_name" "$health_port" true || true
        exit 1
    fi

    pid="${HTTP_SERVICE_PIDS[$service_id]}"
    record_managed_service "$service_id" "$pid" "$log_file" "$last_action"
}

start_http_process() {
    local service_id=$1
    local service_name=$2

    local port
    local health_port
    local port_listening=false
    local assessment_json
    local action
    local status
    port=$(plan_jq ".services[\"$service_id\"].port")
    health_port=$(plan_jq ".services[\"$service_id\"].healthcheck.tcp // .services[\"$service_id\"].port")

    mapfile -t cmd_args < <(plan_jq ".services[\"$service_id\"].command[]")
    mapfile -t env_pairs < <(plan_jq ".services[\"$service_id\"].env // {} | to_entries[] | \"\(.key)=\(.value)\"")

    clean_fastembed_cache_if_corrupt "${env_pairs[@]}"

    local start_cmd=("${cmd_args[@]}")
    if [[ ${#env_pairs[@]} -gt 0 ]]; then
        start_cmd=("env" "${env_pairs[@]}" "${cmd_args[@]}")
    fi

    local pid_var="HTTP_PID_${service_id}"
    local log_file="/tmp/mcp-${service_name}-server.log"
    local pid

    if check_port "$health_port"; then
        port_listening=true
    fi

    assessment_json=$(assess_managed_service "$service_id" "$port_listening")
    action=$(echo "$assessment_json" | jq -r '.action')
    status=$(echo "$assessment_json" | jq -r '.status')

    case "$action" in
        start)
            start_and_record_http_service "$service_id" "$service_name" "$health_port" \
                "$pid_var" "started" "${start_cmd[@]}"
            ;;
        reuse)
            pid=$(port_listener_pid "$health_port")
            eval "$pid_var=$pid"
            register_http_service_runtime "$service_id" "$service_name" "$health_port" "$pid_var"
            log_success "$service_name managed listener already running on port $health_port (PID: $pid)"
            if run_service_healthchecks "$service_id" "$service_name"; then
                record_managed_service "$service_id" "$pid" "$log_file" "reused"
            else
                log_warning "$service_name managed listener failed healthchecks; restarting it"
                stop_port_process "$service_name" "$health_port" true
                start_and_record_http_service "$service_id" "$service_name" "$health_port" \
                    "$pid_var" "restarted" "${start_cmd[@]}"
            fi
            ;;
        restart)
            log_info "Restarting $service_name because registry status is $status"
            local kill_parent=true
            if [[ "$status" == "adopted_unverified" ]]; then
                kill_parent=false
            fi
            stop_port_process "$service_name" "$health_port" "$kill_parent"
            start_and_record_http_service "$service_id" "$service_name" "$health_port" \
                "$pid_var" "restarted" "${start_cmd[@]}"
            ;;
        adopt)
            pid=$(port_listener_pid "$health_port")
            eval "$pid_var=$pid"
            register_http_service_runtime "$service_id" "$service_name" "$health_port" "$pid_var"
            log_warning "$service_name has an unregistered listener on port $health_port; verifying before reuse"
            if run_service_healthchecks "$service_id" "$service_name"; then
                log_warning "$service_name listener is healthy but unverified; Bureau will restart it on the next run"
                record_adopted_service "$service_id" "$pid" "$log_file"
            else
                log_error "$service_name has an unregistered listener on port $health_port that failed Bureau healthchecks"
                log_error "Leaving the process untouched. Stop it manually or run bin/close-bureau if it was launched by Bureau."
                exit 1
            fi
            ;;
        *)
            log_error "Unknown managed-service action '$action' for $service_name"
            exit 1
            ;;
    esac
}

ensure_file_dependency() {
    local service_id=$1
    local storage_path
    storage_path=$(plan_jq ".services[\"$service_id\"].path")
    storage_path=$(expand_tilde "$storage_path")
    mkdir -p "$(dirname "$storage_path")"
    if [[ ! -f "$storage_path" ]]; then
        touch "$storage_path"
    fi
}

# Add or update Gemini MCP entry (supports HTTP and stdio transports)
add_mcp_to_gemini() {
    local transport=$1
    local server_name=$2

    # shift past the args so that the remaining ones can be passed to the script at the end of the function
    shift 2

    mkdir -p "$HOME/.gemini"

    # Initialize file if it doesn't exist
    if [[ ! -f "$GEMINI_CONFIG" ]]; then
        echo '{"mcpServers":{}}' > "$GEMINI_CONFIG"
    fi

    uv run "$SCRIPT_DIR/add-mcp-to-gemini.py" "$transport" "$server_name" "$GEMINI_CONFIG" "$@"
}

# Add server to Codex config file
add_mcp_to_codex() {
    local server_name=$1
    local transport=$2
    shift 2

    mkdir -p "$HOME/.codex"
    [[ ! -f "$CODEX_CONFIG" ]] && touch "$CODEX_CONFIG"

    if grep -q "^\[mcp_servers.$server_name\]" "$CODEX_CONFIG" 2>/dev/null; then
        return 1  # Already exists
    fi

    if [[ "$transport" == "http" ]]; then
        local url=$1
        local bearer_env=${2:-}  # optional bearer_token_env_var
        cat >> "$CODEX_CONFIG" << EOF

[mcp_servers.$server_name]
url = "$url"
transport = "http"
EOF
        # Codex uses bearer_token_env_var instead of custom HTTP headers for auth
        if [[ -n "$bearer_env" ]]; then
            cat >> "$CODEX_CONFIG" << EOF
bearer_token_env_var = "$bearer_env"
EOF
        fi
    else  # stdio server
        parse_stdio_mcp_args "$@"

        # Build TOML args array with proper escaping (inner quotes → \")
        local toml_args_str="" sep=""
        for arg in "${_STDIO_CMD_ARGS[@]:1}"; do
            local escaped="${arg//\\/\\\\}"  # escape backslashes first
            escaped="${escaped//\"/\\\"}"    # then escape double quotes
            toml_args_str+="${sep}\"${escaped}\""
            sep=", "
        done

        cat >> "$CODEX_CONFIG" << EOF

[mcp_servers.$server_name]
command = "${_STDIO_CMD_ARGS[0]}"
args = [$toml_args_str]
transport = "stdio"
EOF
        if [[ -n "$_STDIO_STARTUP_TIMEOUT" ]]; then
            cat >> "$CODEX_CONFIG" << EOF
startup_timeout_sec = $_STDIO_STARTUP_TIMEOUT
EOF
        fi
        if [[ -n "$_STDIO_TOOL_TIMEOUT" ]]; then
            cat >> "$CODEX_CONFIG" << EOF
tool_timeout_sec = $_STDIO_TOOL_TIMEOUT
EOF
        fi
        if [[ ${#_STDIO_ENV_PAIRS[@]} -gt 0 ]]; then
            cat >> "$CODEX_CONFIG" << EOF

[mcp_servers.$server_name.env]
EOF
            for env_pair in "${_STDIO_ENV_PAIRS[@]}"; do
                local key=${env_pair%%=*}
                local value=${env_pair#*=}
                cat >> "$CODEX_CONFIG" << EOF
$key = "$value"
EOF
            done
        fi
    fi
}

# Idempotently configure an agent to use an HTTP MCP (at user scope) 
add_http_mcp_to_agent() {
    local agent=$1
    local server=$2
    local url=$3
    shift 3
    local headers=("$@")  # Remaining args are headers (format: KEY:value)

    case $agent in
        "$GEMINI")
            # Use direct JSON manipulation to add server with headers
            add_mcp_to_gemini "http" "$server" "$url" "${headers[@]}"
            ;;
        "$CLAUDE")
            # Check user scope config directory for existing server
            if grep -q "\"$server\"" "$CLAUDE_CLI_STATE"; then
                return 1  # Already exists
            fi

            # Build header flags if provided (format: KEY:value)
            local header_args=()
            for header in "${headers[@]}"; do
                if [[ "$header" == *":"* ]]; then
                    header_args+=(--header "$header")
                fi
            done

            echo "Adding $server as remote HTTP to Claude with the command:"
            local claude_cmd=(claude mcp add --transport http "$server" --scope user "$url" "${header_args[@]}")
            printf '  %q' "${claude_cmd[@]}"
            log_empty_line
            "${claude_cmd[@]}"
            ;;
        "$CODEX")
            # Codex HTTP mode doesn't support custom headers — it uses
            # bearer_token_env_var for auth instead.  Try to derive the env
            # var from an Authorization: Bearer header when present; otherwise
            # fall back to the explicit bearer_token_env_var passed by the
            # caller.  If neither is available and headers exist, we cannot
            # configure this server on Codex.
            local bearer_env=""
            for header in "${headers[@]}"; do
                # match "Authorization:Bearer ${VAR}" or "Authorization:Bearer $VAR"
                if [[ "$header" =~ ^Authorization:Bearer[[:space:]]*\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$ ]]; then
                    bearer_env="${BASH_REMATCH[1]}"
                    break
                fi
            done

            if [[ -z "$bearer_env" && ${#headers[@]} -gt 0 ]]; then
                return 2  # Cannot configure - unsupported headers
            fi
            add_mcp_to_codex "$server" "http" "$url" "$bearer_env"
            ;;
    esac
}

# Idempotently configure an agent to use a stdio MCP (at user scope)
add_stdio_mcp_to_agent() {
    local agent=$1
    local server=$2
    shift 2
    parse_stdio_mcp_args "$@"

    case $agent in
        "$GEMINI")
            local gemini_args=("${_STDIO_CMD_ARGS[@]}")
            if [[ -n "$_STDIO_TIMEOUT_MS" ]]; then
                gemini_args+=("--timeout" "$_STDIO_TIMEOUT_MS")
            fi
            for env_pair in "${_STDIO_ENV_PAIRS[@]}"; do
                gemini_args+=("--env" "$env_pair")
            done
            add_mcp_to_gemini "stdio" "$server" "${gemini_args[@]}"
            ;;
        "$CLAUDE")
            # Check user scope config directory for existing server
            if grep -q "\"$server\"" "$CLAUDE_CLI_STATE"; then
                return 1 # Already exists
            fi

            local env_args=()
            for env_pair in "${_STDIO_ENV_PAIRS[@]}"; do
                env_args+=(-e "$env_pair")
            done

            echo "Adding $server as local stdio to Claude with the command:"
            local claude_cmd=(claude mcp add --transport stdio "$server" --scope user "${env_args[@]}" -- "${_STDIO_CMD_ARGS[@]}")
            printf '  %q' "${claude_cmd[@]}"
            log_empty_line
            "${claude_cmd[@]}"
            ;;
        "$CODEX")
            local codex_args=()
            for env_pair in "${_STDIO_ENV_PAIRS[@]}"; do
                codex_args+=("--env" "$env_pair")
            done
            if [[ -n "$_STDIO_STARTUP_TIMEOUT" ]]; then
                codex_args+=("--startup-timeout-sec" "$_STDIO_STARTUP_TIMEOUT")
            fi
            if [[ -n "$_STDIO_TOOL_TIMEOUT" ]]; then
                codex_args+=("--tool-timeout-sec" "$_STDIO_TOOL_TIMEOUT")
            fi
            add_mcp_to_codex "$server" "stdio" "${codex_args[@]}" -- "${_STDIO_CMD_ARGS[@]}"
            ;;
    esac
}


# Check for required environment variable and warn if not set
check_env_var() {
    local var_name=$1
    local description=$2

    if [[ -z "${!var_name}" ]]; then
        log_warning "$var_name not set. $description"
        return 1
    fi
    return 0
}

# Check if Rancher Desktop is running and start it if needed
ensure_rancher_running() {
    # Check if Docker daemon is already running
    if docker info &> /dev/null; then
        log_success "Docker daemon is already running"
        return 0
    fi

    # Check if rdctl is available
    if ! command -v rdctl &> /dev/null; then
        log_warning "rdctl not found. Cannot auto-start Rancher Desktop."
        log_info "Please ensure Rancher Desktop is running manually."
        return 1
    fi

    # Rancher/Docker is not running; attempt to start it
    log_info "Docker daemon is not running. Starting Rancher Desktop..."

    if rdctl start; then
        log_info "Waiting for Docker daemon to become ready..."
        local elapsed=0

        while [ $elapsed -lt $DOCKER_TIMEOUT ]; do
            sleep 3
            elapsed=$((elapsed + 3))

            # Check if Docker daemon is responsive
            if docker info &> /dev/null; then
                log_success "Docker daemon is ready after ${elapsed}s"
                return 0
            fi
        done

        log_error "Docker daemon did not become ready within ${DOCKER_TIMEOUT}s"
        log_info "You may need to wait a bit longer and run the script again."
        return 1
    else
        log_error "Failed to start Rancher Desktop"
        return 1
    fi
}

setup_requires_docker() {
    jq -e '
        ([.services[]? | select(.kind == "docker_container")] | length > 0)
        or
        ([.dependencies[]?.post_clone[]?[]? | select(type == "string" and contains("docker"))] | length > 0)
    ' "$SETUP_PLAN_FILE" >/dev/null
}

# Install or update a Python package from git using uv tool
install_or_update_pip_pkg_from_git() {
    local git_url=$1
    local package_name=$2

    # Upgrade package if already installed; otherwise, install 
    if uv tool list | grep -q "^$package_name "; then
        log_info "$package_name is already installed. Updating to latest version..."
        if uv tool install "$package_name" --force --from "git+$git_url"; then
            log_success "$package_name updated successfully"
        else
            log_error "Failed to update $package_name"
            return 1
        fi
    else
        log_info "$package_name not found. Installing from $git_url..."
        if uv tool install "$package_name" --from "git+$git_url"; then
            log_success "$package_name installed successfully"
        else
            log_error "Failed to install $package_name from $git_url"
            return 1
        fi
    fi
}

sync_npm_runtime() {
    local sync_json
    sync_json="$(uv run python "$REPO_ROOT/tools/scripts/sync-npm-runtime.py" --plan "$SETUP_PLAN_FILE")"

    local installed
    local reason
    installed="$(echo "$sync_json" | jq -r '.installed')"
    reason="$(echo "$sync_json" | jq -r '.reason')"

    case "$reason" in
        disabled)
            return 0
            ;;
        up_to_date)
            log_success "Shared local npm MCP runtime already up to date"
            ;;
        manifest_changed)
            log_success "Shared local npm MCP runtime installed/updated from manifest"
            ;;
        missing_binaries)
            log_warning "Shared local npm MCP runtime repaired missing binaries"
            ;;
        *)
            if [[ "$installed" == "true" ]]; then
                log_success "Shared local npm MCP runtime synced"
            else
                log_warning "Shared local npm MCP runtime returned unexpected status: $reason"
            fi
            ;;
    esac
}

render_search_router_configs() {
    local bureau_search_included
    bureau_search_included=$(plan_jq '[.client_configs[]? | has("bureau-search")] | any')
    if [[ "$bureau_search_included" != "true" ]]; then
        return 0
    fi

    log_info "Rendering bureau-search router config..."
    uv run python "$SCRIPT_DIR/render-search-router-config.py" \
        --plan "$SETUP_PLAN_FILE" \
        --client bureau-search >/dev/null
}

# Ensure a git repository is cloned to a target path
ensure_git_repo_cloned() {
    local repo_name=$1
    local repo_url=$2
    local target_path=$3
    local branch=${4:-""}  # Optional branch parameter

    log_info "Checking $repo_name availability..."

    if [[ -d "$target_path" ]]; then
        log_success "$repo_name repository found at $target_path"
        return 0
    fi

    log_warning "$repo_name repository not found at $target_path"
    log_info "Cloning $repo_name repository..."

    # Create parent directory if it doesn't exist
    mkdir -p "$(dirname "$target_path")"

    # Build git clone command with optional branch
    local clone_cmd=(git clone)
    if [[ -n "$branch" ]]; then
        clone_cmd+=(-b "$branch")
    fi
    clone_cmd+=("$repo_url" "$target_path")

    if "${clone_cmd[@]}"; then
        log_success "Repository cloned successfully"
        return 0
    else
        log_error "Failed to clone $repo_name repository"
        return 1
    fi
}

run_post_clone_commands() {
    local service_id=$1
    local repo_path
    repo_path=$(plan_jq ".services[\"$service_id\"].path")
    repo_path=$(expand_tilde "$repo_path")

    while IFS= read -r cmd_json; do
        mapfile -t cmd_args < <(echo "$cmd_json" | jq -r '.[]')
        log_info "Running post-clone command: ${cmd_args[*]}"
        (cd "$repo_path" && "${cmd_args[@]}")
    done < <(plan_jq ".services[\"$service_id\"].post_clone // [] | .[] | @json")
}

# Returns sorted list of keys of the `dependencies` obj in the file given
dependency_order() {
    jq -r '.dependencies | keys | sort[]' "$SETUP_PLAN_FILE"
}

service_order() {
    uv run "$SCRIPT_DIR/service-order.py" "$SETUP_PLAN_FILE"
}

# Configure auto-approval for all agents
configure_auto_approve() {
    log_info "Configuring auto-approval for agents..."
    log_empty_line

    mapfile -t claude_auto_approve < <(plan_jq '.auto_approved.mcp_servers.claude // [] | .[]')
    mapfile -t gemini_auto_approve < <(plan_jq '.auto_approved.mcp_servers.gemini // [] | .[]')
    mapfile -t codex_auto_approve < <(plan_jq '.auto_approved.mcp_servers.codex // [] | .[]')

    # Configure each agent
    for agent in "${AGENTS[@]}"; do
        log_info "→ Configuring $agent..."
        case "$agent" in
            "$CLAUDE")
                # auto-approve reading Bureau's user-scoped protocol files
                uv run "$SCRIPT_DIR/add-claude-auto-approvals.py" "$CLAUDE_CONFIG" "${claude_auto_approve[@]}" \
                    --read-allow "~/.config/bureau/protocols"
                ;;
            "$CODEX")
                uv run "$SCRIPT_DIR/add-codex-auto-approvals.py" "$CODEX_CONFIG" --plan "$SETUP_PLAN_FILE" "${codex_auto_approve[@]}"
                ;;
            "$GEMINI")
                uv run "$SCRIPT_DIR/add-gemini-auto-approvals.py" "$GEMINI_CONFIG" "${gemini_auto_approve[@]}"
                ;;
            *)
                log_warning "  Unknown agent: $agent (skipping)"
                ;;
        esac
    done

    log_empty_line
    log_success "Agent auto-approvals successfully configured."
    log_info "MCP tools will now be auto-approved without permission prompts"
}

configure_bash_approvals() {
    local approvals_enabled
    approvals_enabled="$(plan_jq '.auto_approved.bash.enabled // false')"
    if [[ "$approvals_enabled" != "true" ]]; then
        return 0
    fi

    log_separator
    log_info "Configuring Bash allow/deny approvals..."

    local -a approvals_allow
    local -a approvals_deny
    mapfile -t approvals_allow < <(plan_jq '.auto_approved.bash.ruleset.allow[]?')
    mapfile -t approvals_deny < <(plan_jq '.auto_approved.bash.ruleset.deny[]?')

    for agent in "${AGENTS[@]}"; do
        log_info "→ Configuring $agent Bash approvals..."
        case "$agent" in
            "$CLAUDE")
                local -a claude_bash_args
                claude_bash_args=()
                for prefix in "${approvals_allow[@]}"; do
                    claude_bash_args+=(--bash-allow "$prefix")
                done
                for prefix in "${approvals_deny[@]}"; do
                    claude_bash_args+=(--bash-deny "$prefix")
                done
                uv run "$SCRIPT_DIR/add-claude-auto-approvals.py" "$CLAUDE_CONFIG" "${claude_bash_args[@]}"
                ;;
            "$GEMINI")
                local -a gemini_bash_args
                gemini_bash_args=()
                for prefix in "${approvals_allow[@]}"; do
                    gemini_bash_args+=(--bash-allow "$prefix")
                done
                for prefix in "${approvals_deny[@]}"; do
                    gemini_bash_args+=(--bash-deny "$prefix")
                done
                uv run "$SCRIPT_DIR/add-gemini-auto-approvals.py" "$GEMINI_CONFIG" "${gemini_bash_args[@]}"
                ;;
            "$CODEX")
                local -a codex_bash_args
                codex_bash_args=()
                for prefix in "${approvals_allow[@]}"; do
                    codex_bash_args+=(--allow "$prefix")
                done
                for prefix in "${approvals_deny[@]}"; do
                    codex_bash_args+=(--deny "$prefix")
                done
                uv run "$SCRIPT_DIR/write-codex-exec-policy.py" "${codex_bash_args[@]}"
                ;;
            *)
                log_warning "  Unknown agent: $agent (skipping)"
                ;;
        esac
    done

    log_success "Bash allow/deny approvals successfully configured."
}

# --- CHECK DEPENDENCIES ---

log_info "Checking prerequisites..."

# Use centralized prereq checker (exits with error if any missing)
if ! "$REPO_ROOT/bin/ensure-prereqs"; then
    log_error "Missing prerequisites. Please install them and try again."
    exit 1
fi

log_success "All prerequisites available."

# Install Semgrep via uv (works on all platforms)
log_info "Installing/updating Semgrep..."
uv tool install semgrep

log_info "Checking/installing optional tools..."
log_empty_line
log_info "→ Installing/checking for update for GitHub Spec Kit CLI..."
install_or_update_pip_pkg_from_git "https://github.com/github/spec-kit.git" "specify-cli"

sync_npm_runtime

if setup_requires_docker; then
    log_info "Ensuring Rancher Desktop is running..."
    ensure_rancher_running
fi

log_info "Preparing MCP dependencies..."

# Prepare dependencies before services. Some dependency post-clone commands
# build Docker images, so Docker readiness is checked above when required.
while IFS= read -r dep_id; do
    dep_kind=$(plan_jq ".dependencies[\"$dep_id\"].kind")
    case "$dep_kind" in
        git_repo)
            log_info "Ensuring git repo dependency: $dep_id"
            repo_url=$(plan_jq ".dependencies[\"$dep_id\"].repo_url")
            repo_branch=$(plan_jq ".dependencies[\"$dep_id\"].branch // empty")
            repo_path=$(plan_jq ".dependencies[\"$dep_id\"].path")
            repo_path=$(expand_tilde "$repo_path")
            if [[ -n "$repo_branch" ]]; then
                ensure_git_repo_cloned "$dep_id" "$repo_url" "$repo_path" "$repo_branch"
            else
                ensure_git_repo_cloned "$dep_id" "$repo_url" "$repo_path"
            fi
            # Run post-clone commands if any
            while IFS= read -r cmd_json; do
                mapfile -t cmd_args < <(echo "$cmd_json" | jq -r '.[]')
                log_info "Running post-clone command for $dep_id: ${cmd_args[*]}"
                (cd "$repo_path" && "${cmd_args[@]}")
            done < <(plan_jq ".dependencies[\"$dep_id\"].post_clone // [] | .[] | @json")
            ;;
        file)
            log_info "Ensuring file dependency: $dep_id"
            storage_path=$(plan_jq ".dependencies[\"$dep_id\"].path")
            storage_path=$(expand_tilde "$storage_path")
            mkdir -p "$(dirname "$storage_path")"
            if [[ ! -f "$storage_path" ]]; then
                touch "$storage_path"
            fi
            ;;
        *)
            log_warning "Unknown dependency kind '$dep_kind' for $dep_id (skipping)"
            ;;
    esac
done < <(dependency_order)

log_info "Starting MCP services from catalog..."

while IFS= read -r service_id; do
    service_kind=$(plan_jq ".services[\"$service_id\"].kind")
    case "$service_kind" in
        docker_container)
            log_info "Starting container service: $service_id"
            start_docker_container "$service_id"
            ;;
        http_process)
            log_info "Starting HTTP service: $service_id"
            start_http_process "$service_id" "$service_id"
            ;;
        *)
            log_warning "Unknown service kind '$service_kind' for $service_id (skipping)"
            ;;
    esac
done < <(service_order)

render_search_router_configs

log_separator
log_info "Configuring agents to use MCP servers..."

log_separator
if [[ "$AUTO_CLEAN_MCP" == true ]]; then
    log_info "Reconciling Bureau-managed MCPs and pruning disabled entries..."
else
    log_info "Reconciling Bureau-managed MCPs..."
fi
if agent_enabled "$CLAUDE"; then
    managed_registry_reconcile "claude" "$CLAUDE_CLI_STATE" "$AUTO_CLEAN_MCP"
fi
if agent_enabled "$GEMINI"; then
    managed_registry_reconcile "gemini" "$GEMINI_CONFIG" "$AUTO_CLEAN_MCP"
fi
if agent_enabled "$CODEX"; then
    managed_registry_reconcile "codex" "$CODEX_CONFIG" "$AUTO_CLEAN_MCP"
fi
if agent_enabled "$OPENCODE"; then
    managed_registry_reconcile "opencode" "$OPENCODE_CONFIG" "$AUTO_CLEAN_MCP"
fi

apply_claude_post_config() {
    local server_id=$1
    local env_json=$2
    if [[ -z "$env_json" || "$env_json" == "null" ]]; then
        return 0
    fi

    if [[ -f "$CLAUDE_CONFIG" ]]; then
        local tmp_file
        tmp_file=$(mktemp)
        jq --argjson env "$env_json" '.env = (.env // {}) | .env += $env' "$CLAUDE_CONFIG" > "$tmp_file" && mv "$tmp_file" "$CLAUDE_CONFIG"
        log_success "Claude MCP settings updated for $server_id"
    else
        log_warning "Claude settings.json not found - post_config not applied for $server_id"
    fi
}

already_exists_count=0

for agent in "${AGENTS[@]}"; do
    if [[ "$agent" == "$OPENCODE" ]]; then
        log_info "Skipping OpenCode MCP setup in per-agent loop (configured separately)"
        continue
    fi
    agent_key="$(_agent_config_name "$agent")"
    if [[ -z "$agent_key" ]]; then
        log_warning "Skipping unknown agent: $agent"
        continue
    fi

    while IFS= read -r entry_json; do
        server_id=$(echo "$entry_json" | jq -r '.key')
        client_cfg=$(echo "$entry_json" | jq -c '.value')
        transport=$(echo "$client_cfg" | jq -r '.transport')

        if [[ "$transport" == "http" ]]; then
            url=$(echo "$client_cfg" | jq -r '.url')
            mapfile -t headers < <(echo "$client_cfg" | jq -r '.headers // {} | to_entries[] | "\(.key):\(.value)"')
            # If the client config has bearer_token_env_var (Codex-specific field)
            # but no explicit Authorization header, synthesize one so
            # add_http_mcp_to_agent can extract the env var name uniformly
            bearer_token_env_var=$(echo "$client_cfg" | jq -r '.bearer_token_env_var // empty')
            if [[ -n "$bearer_token_env_var" ]]; then
                has_auth=false
                for h in "${headers[@]}"; do
                    [[ "$h" == Authorization:* ]] && has_auth=true && break
                done
                if [[ "$has_auth" == false ]]; then
                    headers+=("Authorization:Bearer \${${bearer_token_env_var}}")
                fi
            fi
            if add_http_mcp_to_agent "$agent" "$server_id" "$url" "${headers[@]}"; then
                log_success "$agent configured ($server_id)"
            else
                case $? in
                    1) already_exists_count=$((already_exists_count + 1)) ;;
                    2) log_warning "Skipping $agent ($server_id): headers not supported" ;;
                    *) log_warning "Failed to configure $agent ($server_id)" ;;
                esac
            fi
        else
            mapfile -t command < <(echo "$client_cfg" | jq -r '.command[]')
            mapfile -t env_pairs < <(echo "$client_cfg" | jq -r '.env // {} | to_entries[] | "\(.key)=\(.value)"')
            timeout_ms=$(echo "$client_cfg" | jq -r '.timeout_ms // empty')
            startup_timeout=$(echo "$client_cfg" | jq -r '.startup_timeout_sec // empty')
            tool_timeout=$(echo "$client_cfg" | jq -r '.tool_timeout_sec // empty')

            stdio_args=()
            for env_pair in "${env_pairs[@]}"; do
                stdio_args+=(--env "$env_pair")
            done
            if [[ -n "$timeout_ms" ]]; then
                stdio_args+=(--timeout-ms "$timeout_ms")
            fi
            if [[ -n "$startup_timeout" ]]; then
                stdio_args+=(--startup-timeout-sec "$startup_timeout")
            fi
            if [[ -n "$tool_timeout" ]]; then
                stdio_args+=(--tool-timeout-sec "$tool_timeout")
            fi
            stdio_args+=(-- "${command[@]}")

            if add_stdio_mcp_to_agent "$agent" "$server_id" "${stdio_args[@]}"; then
                log_success "$agent configured ($server_id)"
            else
                case $? in
                    1) already_exists_count=$((already_exists_count + 1)) ;;
                    *) log_warning "Failed to configure $agent ($server_id)" ;;
                esac
            fi
        fi

        if [[ "$agent" == "$CLAUDE" ]]; then
            post_env=$(echo "$client_cfg" | jq -c '.post_config.claude_settings_env // empty')
            apply_claude_post_config "$server_id" "$post_env"
        fi
    done < <(plan_jq ".client_configs[\"$agent_key\"] // {} | to_entries[] | @json")

done

if [[ $already_exists_count -gt 0 ]]; then
    log_info "Already configured: $already_exists_count (suppressed)"
fi

if agent_enabled "$CLAUDE"; then
    managed_registry_record "claude" "$CLAUDE_CLI_STATE"
fi
if agent_enabled "$GEMINI"; then
    managed_registry_record "gemini" "$GEMINI_CONFIG"
fi
if agent_enabled "$CODEX"; then
    managed_registry_record "codex" "$CODEX_CONFIG"
fi

# Configure MCP auto-approvals if requested
configure_bash_approvals
if [[ "$AUTO_APPROVE_MCP" == true ]]; then
    log_separator
    configure_auto_approve
fi

# ============================================================================
#   Completion output
# ============================================================================

log_empty_line
log_success "Setup complete."
log_empty_line
if [[ ${#HTTP_SERVICE_PIDS[@]} -gt 0 ]]; then
    log_info "Local HTTP services running:"
    for service_id in "${!HTTP_SERVICE_PIDS[@]}"; do
        local_port="${HTTP_SERVICE_PORTS[$service_id]}"
        local_pid="${HTTP_SERVICE_PIDS[$service_id]}"
        log_info "  • ${service_id}: http://localhost:${local_port} (PID: ${local_pid})"
    done
    log_empty_line
fi

if [[ ${#DOCKER_CONTAINERS[@]} -gt 0 ]]; then
    log_info "Docker containers:"
    for container_name in "${DOCKER_CONTAINERS[@]}"; do
        log_info "  • ${container_name}"
    done
    log_empty_line
fi

if [[ ${#HTTP_SERVICE_LOGS[@]} -gt 0 ]]; then
    log_info "Logs:"
    for service_id in "${!HTTP_SERVICE_LOGS[@]}"; do
        log_info "  • ${service_id}: ${HTTP_SERVICE_LOGS[$service_id]}"
    done
    log_empty_line
fi

if agent_enabled "OpenCode"; then
    log_separator
    log_info "Syncing OpenCode MCP config"
    TEMPLATE_OC="$REPO_ROOT/protocols/config/templates/opencode.json"
    GENERATED_OC="$REPO_ROOT/protocols/config/generated/opencode.generated.json"
    TARGET_OC="$HOME/.config/opencode/opencode.json"

    if [[ -f "$TEMPLATE_OC" ]]; then
        mkdir -p "$(dirname "$GENERATED_OC")"
        MCP_OC_TMP="$(mktemp)"
        if ! uv run python "$REPO_ROOT/protocols/scripts/render-opencode-mcp.py" > "$MCP_OC_TMP"; then
            log_warning "Failed to render OpenCode MCP config; skipping OpenCode sync"
            GENERATED_OC=""
        else
            PERMS_OC_TMP="$(mktemp)"
            if ! uv run python "$REPO_ROOT/protocols/scripts/render-opencode-permissions.py" > "$PERMS_OC_TMP"; then
                log_warning "Failed to render OpenCode permissions; skipping permission updates"
                PERMS_OC_TMP=""
            fi

            if ! uv run "$REPO_ROOT/protocols/scripts/render-opencode-template.py" \
                --template "$TEMPLATE_OC" \
                --output "$GENERATED_OC" \
                --repo-root "$REPO_ROOT" \
                --protocols-dir "$HOME/.config/bureau/protocols" \
                --mcp "$MCP_OC_TMP" \
                ${PERMS_OC_TMP:+--permissions "$PERMS_OC_TMP"}; then
                log_warning "Failed to render OpenCode template; skipping OpenCode sync"
                GENERATED_OC=""
            fi
        fi
        mkdir -p "$(dirname "$TARGET_OC")"

        if [[ -n "$GENERATED_OC" && -f "$GENERATED_OC" ]]; then
            OPENCODE_ARGS=(--target "$TARGET_OC" --generated "$GENERATED_OC")
            if [[ "$MODE_BARE" == true ]]; then
                OPENCODE_ARGS+=(--bare)
            fi
            if uv run "$SCRIPT_DIR/configure-opencode.py" "${OPENCODE_ARGS[@]}"; then
                log_success "OpenCode config merged into $TARGET_OC (preserved user overrides)"
            else
                log_warning "OpenCode merge failed; leaving $TARGET_OC unchanged"
            fi
        else
            log_warning "OpenCode template render failed or generated file missing; skipping OpenCode sync"
        fi
    else
        log_warning "OpenCode config template not found at $TEMPLATE_OC; skipping OpenCode sync"
    fi
    managed_registry_record "opencode" "$OPENCODE_CONFIG"
fi

if agent_enabled "$CODEX"; then
    log_separator
    log_info "Ensuring Superpowers skills are installed for Codex..."
    "$REPO_ROOT/agents/scripts/set-up-codex-superpowers.sh"
fi

log_empty_line
log_info "To verify setup:"
log_info "  1. cd into a git repo"
log_info "  2. Run 'gemini', 'claude', or 'codex', according to which CLI(s) you have available"
log_info "  3. Type '/mcp' to see available tools"

# Build running PID list in startup order, only including set PIDs
log_empty_line
log_info "To stop local HTTP servers:"
pidlist=""
for pid in "${HTTP_SERVICE_PIDS[@]}"; do
    pidlist+=" $pid"
done

# Trim leading space and create kill command
pidlist="${pidlist# }"
if [[ -n "$pidlist" ]]; then
    KILL_HTTPS_CMD="kill ${pidlist}"
    log_info "  $KILL_HTTPS_CMD"
else
    KILL_HTTPS_CMD=""
    log_info "  (none)"
fi

log_empty_line
docker_stop_cmd=""
if [[ ${#DOCKER_CONTAINERS[@]} -gt 0 ]]; then
    docker_stop_cmd="docker stop ${DOCKER_CONTAINERS[*]}"
fi
log_info "To stop Docker containers:"
if [[ -n "$docker_stop_cmd" ]]; then
    log_info "  $docker_stop_cmd"
else
    log_info "  (none)"
fi

log_empty_line
TAKE_DOWN_FILE="$REPO_ROOT/bin/close-bureau"
{
    echo "#!/usr/bin/env bash"
    echo "# Stop servers and containers launched by Bureau's tools script"
    echo "#"
    echo "# Port-based shutdown: finds the actual port-binding process at run time"
    echo "# rather than relying on stale PIDs that may have been recycled by the OS."
    echo "# Also kills the parent wrapper (uv/uvx) to avoid orphaned processes."
    echo ""
    if [[ ${#HTTP_SERVICE_PORTS[@]} -gt 0 ]]; then
        echo "for port in ${HTTP_SERVICE_PORTS[*]}; do"
        # Use heredoc-style indentation for clarity in the generated script
        cat <<'SHUTDOWN_BODY'
    pid=$(lsof -ti:"$port" -sTCP:LISTEN 2>/dev/null)
    if [[ -n "$pid" ]]; then
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        kill "$pid" 2>/dev/null
        # Kill the wrapper parent (e.g. uv/uvx) if it's not init/launchd
        if [[ -n "$ppid" && "$ppid" -gt 1 ]]; then
            kill "$ppid" 2>/dev/null
        fi
    fi
done
SHUTDOWN_BODY
    fi
    if [[ -n "$docker_stop_cmd" ]]; then
        echo "$docker_stop_cmd"
    fi
} > "$TAKE_DOWN_FILE"
chmod +x "$TAKE_DOWN_FILE"
log_info "Stop commands saved to $RED$TAKE_DOWN_FILE$NC for convenience"

if [[ "$AUTO_APPROVE_MCP" == true ]]; then
    log_empty_line
    log_success "All agents configured to auto-approve MCP tools (auto_approved.mcp_tools: true)"
    log_info "  → Updated: ~/.claude/settings.json"
    log_info "  → Updated: ~/.codex/config.toml"
    log_info "  → Updated: ~/.gemini/settings.json"
    log_info "  → MCP tools will no longer require permission prompts"
fi
