#!/bin/bash
# Bot Manager — Start/Stop/Restart Discord, Mattermost bots & Agent Queue Processor
# Usage: bot_manager.sh [start|stop|restart|status|logs|agents|queue]

set -e

COMM_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJEX_ROOT="$(cd "$COMM_DIR/../.." && pwd)"
PID_DIR="$COMM_DIR/.pids"
LOG_FILE="$COMM_DIR/bot.log"
DISCORD_BOT="$COMM_DIR/discord_bot.py"
BRIDGE="$COMM_DIR/bot_bridge.py"
AGENT_QUEUE_PROC="$COMM_DIR/agent_queue_processor.py"
AGENT_ROUTER="$COMM_DIR/agent_router.py"

mkdir -p "$PID_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

start_discord() {
    if [ -f "$PID_DIR/discord.pid" ] && kill -0 "$(cat "$PID_DIR/discord.pid")" 2>/dev/null; then
        echo "⚠️  Discord bot already running (PID $(cat "$PID_DIR/discord.pid"))"
        return 1
    fi

    # Check token is configured (supports .env or token_env)
    TOKEN=$(python3 -c "
import json, os
from pathlib import Path
cfg = json.load(open('$COMM_DIR/config.json'))
# Try .env first
env_path = Path('$COMM_DIR') / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())
token_env = cfg.get('discord',{}).get('token_env', 'DISCORD_BOT_TOKEN')
token = os.environ.get(token_env, '')
if not token:
    token = cfg.get('discord',{}).get('token', '')
print(token)
" 2>/dev/null)
    if [ -z "$TOKEN" ] || echo "$TOKEN" | grep -q "YOUR_"; then
        echo "❌ Discord token not configured. Check .env or config.json."
        return 1
    fi

    echo "🚀 Starting Discord bot..."
    nohup python3 "$DISCORD_BOT" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_DIR/discord.pid"
    sleep 2

    if kill -0 "$(cat "$PID_DIR/discord.pid")" 2>/dev/null; then
        log "Discord bot started (PID $(cat "$PID_DIR/discord.pid"))"
        echo "✅ Discord bot running"
    else
        echo "❌ Discord bot failed to start. Check logs:"
        tail -5 "$LOG_FILE"
        return 1
    fi
}

stop_discord() {
    if [ -f "$PID_DIR/discord.pid" ]; then
        PID=$(cat "$PID_DIR/discord.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log "Discord bot stopped (PID $PID)"
            echo "✅ Discord bot stopped"
        else
            echo "⚠️  Discord bot was not running"
        fi
        rm -f "$PID_DIR/discord.pid"
    else
        echo "⚠️  No Discord bot PID file found"
    fi
}

start_mattermost() {
    if [ -f "$PID_DIR/mattermost.pid" ] && kill -0 "$(cat "$PID_DIR/mattermost.pid")" 2>/dev/null; then
        echo "⚠️  Mattermost bot already running (PID $(cat "$PID_DIR/mattermost.pid"))"
        return 1
    fi

    MM_ENABLED=$(python3 -c "import json; c=json.load(open('$COMM_DIR/config.json')); print(str(c.get('mattermost',{}).get('enabled',False)).lower())" 2>/dev/null)
    if [ "$MM_ENABLED" != "true" ]; then
        echo "⚠️  Mattermost bot is disabled in config.json"
        return 0
    fi

    echo "🚀 Starting Mattermost bot..."
    nohup python3 "$COMM_DIR/mattermost_bot.py" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_DIR/mattermost.pid"
    sleep 2

    if kill -0 "$(cat "$PID_DIR/mattermost.pid")" 2>/dev/null; then
        log "Mattermost bot started (PID $(cat "$PID_DIR/mattermost.pid"))"
        echo "✅ Mattermost bot running"
    else
        echo "❌ Mattermost bot failed to start. Check logs:"
        tail -5 "$LOG_FILE"
        return 1
    fi
}

stop_mattermost() {
    if [ -f "$PID_DIR/mattermost.pid" ]; then
        PID=$(cat "$PID_DIR/mattermost.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log "Mattermost bot stopped (PID $PID)"
            echo "✅ Mattermost bot stopped"
        else
            echo "⚠️  Mattermost bot was not running"
        fi
        rm -f "$PID_DIR/mattermost.pid"
    else
        echo "⚠️  No Mattermost bot PID file found"
    fi
}

start_agent_queue() {
    if [ -f "$PID_DIR/agent_queue.pid" ] && kill -0 "$(cat "$PID_DIR/agent_queue.pid")" 2>/dev/null; then
        echo "⚠️  Agent queue processor already running (PID $(cat "$PID_DIR/agent_queue.pid"))"
        return 1
    fi

    AGENTS_ENABLED=$(python3 -c "import json; c=json.load(open('$COMM_DIR/config.json')); print(str(c.get('agents',{}).get('enabled',False)).lower())" 2>/dev/null)
    if [ "$AGENTS_ENABLED" != "true" ]; then
        echo "⚠️  Agents are disabled in config.json"
        return 0
    fi

    INTERVAL=$(python3 -c "import json; c=json.load(open('$COMM_DIR/config.json')); print(c.get('agents',{}).get('queue_check_interval_seconds',10))" 2>/dev/null)

    echo "🚀 Starting agent queue processor (interval: ${INTERVAL}s)..."
    nohup python3 "$AGENT_QUEUE_PROC" --interval "$INTERVAL" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_DIR/agent_queue.pid"
    sleep 2

    if kill -0 "$(cat "$PID_DIR/agent_queue.pid")" 2>/dev/null; then
        log "Agent queue processor started (PID $(cat "$PID_DIR/agent_queue.pid"))"
        echo "✅ Agent queue processor running"
    else
        echo "❌ Agent queue processor failed to start. Check logs:"
        tail -5 "$LOG_FILE"
        return 1
    fi
}

stop_agent_queue() {
    if [ -f "$PID_DIR/agent_queue.pid" ]; then
        PID=$(cat "$PID_DIR/agent_queue.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log "Agent queue processor stopped (PID $PID)"
            echo "✅ Agent queue processor stopped"
        else
            echo "⚠️  Agent queue processor was not running"
        fi
        rm -f "$PID_DIR/agent_queue.pid"
    else
        echo "⚠️  No agent queue PID file found"
    fi
}

show_status() {
    echo "📡 Projex Communication Bot Status"
    echo "═══════════════════════════════════"

    # Discord
    if [ -f "$PID_DIR/discord.pid" ] && kill -0 "$(cat "$PID_DIR/discord.pid")" 2>/dev/null; then
        echo "Discord:      🟢 Running (PID $(cat "$PID_DIR/discord.pid"))"
    else
        echo "Discord:      🔴 Stopped"
    fi

    # Mattermost
    if [ -f "$PID_DIR/mattermost.pid" ] && kill -0 "$(cat "$PID_DIR/mattermost.pid")" 2>/dev/null; then
        echo "Mattermost:   🟢 Running (PID $(cat "$PID_DIR/mattermost.pid"))"
    else
        echo "Mattermost:   🔴 Stopped"
    fi

    # Agent Queue Processor
    if [ -f "$PID_DIR/agent_queue.pid" ] && kill -0 "$(cat "$PID_DIR/agent_queue.pid")" 2>/dev/null; then
        echo "Agent Queue:  🟢 Running (PID $(cat "$PID_DIR/agent_queue.pid"))"
    else
        echo "Agent Queue:  🔴 Stopped"
    fi

    echo ""

    # Bridge stats
    if command -v python3 &>/dev/null; then
        python3 "$BRIDGE" status 2>/dev/null || echo "Bridge: unable to query (bots may be offline)"
    fi

    echo ""

    # Agent status
    if command -v python3 &>/dev/null; then
        python3 "$AGENT_ROUTER" 2>/dev/null || echo "Agent router: unable to query"
    fi

    echo ""
    echo "Log file: $LOG_FILE"
    echo "Config:   $COMM_DIR/config.json"
    echo "Profiles: $PROJEX_ROOT/profiles/"
}

show_logs() {
    LINES=${2:-50}
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Last $LINES lines of bot.log:"
        echo "═══════════════════════════════"
        tail -"$LINES" "$LOG_FILE"
    else
        echo "📋 No log file yet"
    fi
}

show_agents() {
    echo "🤖 Projex Agent Profiles"
    echo "═════════════════════════"
    python3 "$PROJEX_ROOT/profiles/profile_manager.py" tree 2>/dev/null || echo "Unable to load profiles"
}

process_queue() {
    echo "📬 Processing agent queue..."
    python3 "$AGENT_QUEUE_PROC" --once
}

case "${1}" in
    start)
        start_discord
        start_mattermost
        start_agent_queue
        ;;
    stop)
        stop_discord
        stop_mattermost
        stop_agent_queue
        ;;
    restart)
        stop_discord 2>/dev/null
        stop_mattermost 2>/dev/null
        stop_agent_queue 2>/dev/null
        sleep 1
        start_discord
        start_mattermost
        start_agent_queue
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$@"
        ;;
    agents)
        show_agents
        ;;
    queue)
        process_queue
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|agents|queue}"
        echo ""
        echo "Commands:"
        echo "  start        — Start Discord, Mattermost, and agent queue"
        echo "  stop         — Stop all services"
        echo "  restart      — Restart all services"
        echo "  status       — Show running services and agent profiles"
        echo "  logs [lines] — Show recent log entries"
        echo "  agents       — List all agent profiles"
        echo "  queue        — Process pending agent queue items"
        exit 1
        ;;
esac
