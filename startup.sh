#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Athena Startup — Termux-Native Service Launcher
# =============================================================================
# Starts all Athena services with:
#   - Persistent notification (reduces Android killing Termux)
#   - Wake lock during startup
#   - termux-job-scheduler keepalive (survives Termux restarts)
#   - Internal watchdog + heartbeat
#
# Usage:  bash ~/Athena/startup.sh
# =============================================================================

ATHENA="$HOME/Athena"
LOG="$ATHENA/startup.log"
PID_DIR="$ATHENA/automations/comm/.pids"
mkdir -p "$PID_DIR"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"
}

# ─── PRE-STARTUP ────────────────────────────────────────────────────────────
log "=== Athena Startup ==="

# Acquire wake lock to prevent sleep during startup
termux-wake-lock 2>/dev/null
log "🔒 Wake lock acquired"

# Set Termux to stay alive with persistent notification
# This is the KEY trick: Android is less likely to kill Termux
# when it has an ongoing foreground notification
termux-notification \
    --id athena_running \
    --title "🧠 Athena" \
    --content "Pi + Discord Bot active" \
    --priority high \
    --ongoing \
    --alert-once \
    2>/dev/null
log "🔔 Persistent notification shown"

# ─── START SERVICES ─────────────────────────────────────────────────────────

# 1. Start Discord bot + watchdog (bot_manager handles both)
log "Starting Discord bot..."
bash "$ATHENA/automations/comm/bot_manager.sh" start 2>&1 | tee -a "$LOG" || true

# 2. Start heartbeat daemon
log "Starting heartbeat..."
bash "$ATHENA/automations/system/heartbeat.sh" --start 2>&1 | tee -a "$LOG" || true

# 3. Start the Aw Aware engagement system
log "Starting Aware orchestrator..."
cd "$ATHENA"
python3 "$ATHENA/automations/aware/orchestrator.py" status 2>&1 | tee -a "$LOG" || true

# 4. Register keepalive job (persists across reboots)
log "Registering keepalive job..."
termux-job-scheduler \
    --script "$ATHENA/keepalive.sh" \
    --job-id 4243 \
    --period-ms 900000 \
    --persisted true \
    2>&1 | tee -a "$LOG" || true

# 5. Ensure aware daemon job is registered
log "Registering aware daemon job..."
termux-job-scheduler \
    --script "$ATHENA/automations/aware/daemon.sh" \
    --job-id 4242 \
    --period-ms 900000 \
    --persisted true \
    2>&1 | tee -a "$LOG" || true

# ─── POST-STARTUP ───────────────────────────────────────────────────────────

# Release wake lock — services are now running independently
termux-wake-unlock 2>/dev/null
log "🔓 Wake lock released"

# Update notification to show active status
termux-notification \
    --id athena_running \
    --title "🧠 Athena" \
    --content "✅ Pi + Discord Bot active | Keepalive job registered" \
    --priority high \
    --ongoing \
    --alert-once \
    2>/dev/null

log "=== Athena Startup Complete ==="
echo ""
echo "🧠 Athena is running"
echo "   Pi:       $(pgrep -af "node pi" 2>/dev/null | wc -l) processes"
echo "   Discord:  $(pgrep -f "discord_bot.py" >/dev/null 2>&1 && echo '🟢 Running' || echo '🔴 Stopped')"
echo "   Heartbeat: $(cat $ATHENA/automations/system/heartbeat.pid 2>/dev/null && echo '🟢 Running' || echo '⚪ Check status')"
echo "   Keepalive: Job 4243 registered (every 15 min)"
echo ""
echo "   To stop:  bash $ATHENA/stop.sh"
echo "   Status:   bash $ATHENA/automations/comm/bot_manager.sh status"
echo "   Recheck:  bash $ATHENA/keepalive.sh"
