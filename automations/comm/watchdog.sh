#!/bin/bash
# Discord Bot Watchdog — Auto-restart if process dies
# Runs as daemon, checks every 30 seconds

COMM_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJEX_ROOT="$(cd "$COMM_DIR/../.." && pwd)"
PID_FILE="$COMM_DIR/.pids/discord.pid"
LOG_FILE="$COMM_DIR/bot.log"
BOT_SCRIPT="$COMM_DIR/discord_bot.py"
WATCHDOG_PID="$COMM_DIR/.pids/watchdog.pid"
CHECK_INTERVAL=30
MAX_RETRIES=5
RETRY_COOLDOWN=60

mkdir -p "$COMM_DIR/.pids"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WATCHDOG] $1" | tee -a "$LOG_FILE"; }

is_bot_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    # Also check by process name
    if pgrep -f "python3.*discord_bot.py" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

start_bot() {
    log "Starting Discord bot..."
    cd "$PROJEX_ROOT"
    setsid python3 "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo "$NEW_PID" > "$PID_FILE"
    log "Bot started with PID $NEW_PID"
    sleep 5

    if is_bot_running; then
        log "✅ Bot confirmed running"
        return 0
    else
        log "❌ Bot failed to start"
        return 1
    fi
}

# Main watchdog loop
restart_count=0
last_restart=0

log "Watchdog started (PID $$), checking every ${CHECK_INTERVAL}s"
echo $$ > "$WATCHDOG_PID"

while true; do
    if is_bot_running; then
        # Bot is alive, reset retry counter if it's been running for a while
        restart_count=0
    else
        log "Bot is DOWN"

        # Check cooldown
        NOW=$(date +%s)
        if [ $((NOW - last_restart)) -lt $RETRY_COOLDOWN ] && [ $restart_count -gt 0 ]; then
            log "Cooldown active, waiting..."
            sleep $CHECK_INTERVAL
            continue
        fi

        if [ $restart_count -ge $MAX_RETRIES ]; then
            log "⚠️ Max retries ($MAX_RETRIES) reached. Will retry after cooldown."
            restart_count=0
            last_restart=$NOW
            sleep $RETRY_COOLDOWN
        fi

        start_bot
        restart_count=$((restart_count + 1))
        last_restart=$(date +%s)
    fi

    sleep $CHECK_INTERVAL
done
