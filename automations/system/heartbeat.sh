#!/usr/bin/env bash
# heartbeat.sh — System heartbeat monitor
# Usage: ./heartbeat.sh [--check|--status|--log|--config]
# Records health checks to system/heartbeats.jsonl

set -euo pipefail

HEARTBEAT_DIR="automations/system"
HEARTBEAT_FILE="$HEARTBEAT_DIR/heartbeats.jsonl"
CONFIG_FILE="$HEARTBEAT_DIR/heartbeat_config.json"
PID_FILE="$HEARTBEAT_DIR/heartbeat.pid"

init() {
    mkdir -p "$HEARTBEAT_DIR"
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" <<'EOF'
{
  "interval_seconds": 300,
  "missed_threshold": 3,
  "checks": {
    "disk_space": true,
    "memory": true,
    "network": true,
    "processes": true,
    "automations": true
  },
  "alert_on_miss": true
}
EOF
    fi
}

# Log a heartbeat entry
log_heartbeat() {
    local status="$1" details="$2"
    local timestamp
    timestamp=$(date -Iseconds)

    echo "{\"timestamp\":\"$timestamp\",\"status\":\"$status\",\"details\":$details}" >> "$HEARTBEAT_FILE"
}

# Check disk space
check_disk() {
    local usage
    usage=$(df "$PWD" | tail -1 | awk '{print $5}' | tr -d '%')
    local status="ok"
    if [[ "$usage" -gt 90 ]]; then
        status="critical"
    elif [[ "$usage" -gt 75 ]]; then
        status="warning"
    fi
    echo "{\"disk\":{\"usage_percent\":$usage,\"status\":\"$status\"}}"
}

# Check memory
check_memory() {
    if command -v free &>/dev/null; then
        local total used pct
        total=$(free | grep Mem | awk '{print $2}')
        used=$(free | grep Mem | awk '{print $3}')
        if [[ "$total" -gt 0 ]]; then
            pct=$((used * 100 / total))
        else
            pct=0
        fi
        echo "{\"memory\":{\"total_kb\":$total,\"used_kb\":$used,\"percent\":$pct}}"
    else
        echo "{\"memory\":{\"available\":false}}"
    fi
}

# Check network
check_network() {
    if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
        echo "{\"network\":{\"connected\":true}}"
    else
        echo "{\"network\":{\"connected\":false}}"
    fi
}

# Check running processes
check_processes() {
    local proc_count
    proc_count=$(ps aux 2>/dev/null | wc -l || echo "0")
    echo "{\"processes\":{\"count\":$proc_count}}"
}

# Check automations directory health
check_automations() {
    local script_count db_count
    script_count=$(find automations -name "*.sh" -o -name "*.py" -o -name "*.ts" 2>/dev/null | wc -l)
    db_count=$(find automations -name "*.db" 2>/dev/null | wc -l)
    echo "{\"automations\":{\"scripts\":$script_count,\"databases\":$db_count}}"
}

# Run all checks
run_checks() {
    local disk mem network procs automations
    disk=$(check_disk)
    mem=$(check_memory)
    network=$(check_network)
    procs=$(check_processes)
    automations=$(check_automations)

    # Merge all checks
    local details="{$(echo "$disk" | tr -d '{}'),$(echo "$mem" | tr -d '{}'),$(echo "$network" | tr -d '{}'),$(echo "$procs" | tr -d '{}'),$(echo "$automations" | tr -d '{}')}"

    # Determine overall status
    local status="healthy"
    if echo "$details" | grep -q '"status":"critical"'; then
        status="critical"
    elif echo "$details" | grep -q '"status":"warning"'; then
        status="warning"
    fi
    if echo "$details" | grep -q '"connected":false'; then
        if [[ "$status" == "healthy" ]]; then
            status="degraded"
        fi
    fi

    log_heartbeat "$status" "$details"
    echo "$status"
}

# Show status
show_status() {
    if [[ ! -f "$HEARTBEAT_FILE" ]]; then
        echo "💓 No heartbeat records yet. Run with --check first."
        return
    fi

    local last_heartbeat
    last_heartbeat=$(tail -1 "$HEARTBEAT_FILE")

    local timestamp status
    timestamp=$(echo "$last_heartbeat" | python3 -c "import sys,json; print(json.load(sys.stdin)['timestamp'][:19])" 2>/dev/null || echo "unknown")
    status=$(echo "$last_heartbeat" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")

    local status_icon
    case "$status" in
        healthy) status_icon="💚" ;;
        warning) status_icon="⚠️" ;;
        critical) status_icon="🚨" ;;
        degraded) status_icon="📶" ;;
        *) status_icon="❓" ;;
    esac

    local total_heartbeats
    total_heartbeats=$(wc -l < "$HEARTBEAT_FILE")

    # Count recent statuses (last 10)
    local recent_ok recent_warn recent_crit
    recent_ok=$(tail -10 "$HEARTBEAT_FILE" | grep -c '"healthy"' || echo "0")
    recent_warn=$(tail -10 "$HEARTBEAT_FILE" | grep -c '"warning"' || echo "0")
    recent_crit=$(tail -10 "$HEARTBEAT_FILE" | grep -c '"critical"' || echo "0")

    echo "💓 Heartbeat Status"
    echo "══════════════════════════════════════════"
    echo "  $status_icon Last: $status ($timestamp)"
    echo "  Total checks: $total_heartbeats"
    echo ""
    echo "  Recent (last 10):"
    echo "    💚 Healthy: $recent_ok"
    echo "    ⚠️  Warning: $recent_warn"
    echo "    🚨 Critical: $recent_crit"
    echo ""

    # Check if heartbeat daemon is running
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  🔄 Daemon: Running (PID $pid)"
        else
            echo "  ⛔ Daemon: Stale (PID $pid not found)"
            rm -f "$PID_FILE"
        fi
    else
        echo "  ⏸️  Daemon: Not running"
    fi
}

# Show log
show_log() {
    local count="${1:-10}"

    if [[ ! -f "$HEARTBEAT_FILE" ]]; then
        echo "No heartbeat records yet."
        return
    fi

    echo "💓 Heartbeat Log (last $count):"
    echo "══════════════════════════════════════════"

    tail -n "$count" "$HEARTBEAT_FILE" | tac | while IFS= read -r line; do
        local ts status
        ts=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['timestamp'][:19])" 2>/dev/null || echo "?")
        status=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "?")

        local icon
        case "$status" in
            healthy) icon="💚" ;;
            warning) icon="⚠️" ;;
            critical) icon="🚨" ;;
            degraded) icon="📶" ;;
            *) icon="❓" ;;
        esac

        echo "  $icon [$ts] $status"
    done
}

# Start heartbeat daemon (background loop)
start_daemon() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "⚠️  Heartbeat daemon already running (PID $pid)"
            return
        fi
        rm -f "$PID_FILE"
    fi

    local interval
    interval=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['interval_seconds'])" 2>/dev/null || echo "300")

    echo "💓 Starting heartbeat daemon (every ${interval}s)..."

    (
        echo $$ > "$PID_FILE"
        while true; do
            status=$(run_checks 2>/dev/null)
            if [[ "$status" == "critical" || "$status" == "warning" ]]; then
                bash automations/notifications/notify.sh --type alert "Heartbeat: $status" --title "System Health" 2>/dev/null || true
            fi
            sleep "$interval"
        done
    ) &

    disown
    sleep 1
    if [[ -f "$PID_FILE" ]]; then
        echo "✅ Heartbeat daemon started (PID $(cat "$PID_FILE"))"
    else
        echo "⚠️  Daemon may have failed to start"
    fi
}

# Stop heartbeat daemon
stop_daemon() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "⏸️  Heartbeat daemon stopped (PID $pid)"
        else
            echo "⚠️  Stale PID file removed"
        fi
        rm -f "$PID_FILE"
    else
        echo "ℹ️  No daemon running"
    fi
}

usage() {
    cat <<EOF
System Heartbeat Monitor

Usage: $0 <command>

Commands:
  --check       Run a health check and log it
  --status      Show current heartbeat status
  --log [count] Show recent heartbeat log
  --start       Start heartbeat daemon (background)
  --stop        Stop heartbeat daemon
  --config      Show configuration
  --help        Show this help
EOF
}

init

if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

case $1 in
    --check)
        status=$(run_checks)
        echo "💓 Health check: $status"
        ;;
    --status) show_status ;;
    --log) show_log "${2:-10}" ;;
    --start) start_daemon ;;
    --stop) stop_daemon ;;
    --config) cat "$CONFIG_FILE" 2>/dev/null || echo "No config found" ;;
    --help) usage ;;
    *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
