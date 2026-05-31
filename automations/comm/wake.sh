#!/bin/bash
# Wake Script — Starts Discord bot + watchdog on demand
# Usage: bash wake.sh
# Can be triggered via: Termux widget, notification tap, SSH, or manual

COMM_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJEX_ROOT="$(cd "$COMM_DIR/../.." && pwd)"
PID_DIR="$COMM_DIR/.pids"
LOG_FILE="$COMM_DIR/bot.log"

mkdir -p "$PID_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WAKE] $1" | tee -a "$LOG_FILE"; }

# Acquire wake lock to prevent Android from killing us
if command -v termux-wake-lock &>/dev/null; then
    termux-wake-lock 2>/dev/null
    log "Wake lock acquired"
fi

# Kill any existing instances
pkill -f "python3.*discord_bot.py" 2>/dev/null
pkill -f "watchdog.sh" 2>/dev/null
sleep 1

# Start watchdog (which starts the bot)
log "Starting watchdog daemon..."
setsid bash "$COMM_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 &
WATCHDOG_PID=$!
echo "$WATCHDOG_PID" > "$PID_DIR/watchdog.pid"

log "Watchdog PID: $WATCHDOG_PID"

# Wait for bot to come up
log "Waiting for bot to connect..."
for i in $(seq 1 15); do
    sleep 2
    if pgrep -f "python3.*discord_bot.py" >/dev/null 2>&1; then
        log "✅ Bot is running!"
        break
    fi
done

# Final status
if pgrep -f "python3.*discord_bot.py" >/dev/null 2>&1; then
    BOT_PID=$(pgrep -f "python3.*discord_bot.py")
    log "✅ Goode bot online (PID: $BOT_PID)"
    log "✅ Watchdog running (PID: $WATCHDOG_PID)"
    
    # Show notification
    if command -v termux-notification &>/dev/null; then
        termux-notification \
            --title "🤖 Goode Bot Online" \
            --content "Discord bot + watchdog running. Tap to stop." \
            --action "bash $COMM_DIR/sleep.sh" \
            --id "goode-bot" 2>/dev/null
    fi
    
    echo ""
    echo "🟢 Goode bot is online"
    echo "   Bot PID:     $BOT_PID"
    echo "   Watchdog:    $WATCHDOG_PID"
    echo "   Bot will auto-restart if it crashes"
else
    log "❌ Bot failed to start. Check logs:"
    tail -5 "$LOG_FILE"
    echo "❌ Bot failed to start"
fi
