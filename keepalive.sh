#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Athena Keepalive — Survives Android Killing Termux
# =============================================================================
# Runs as termux-job-scheduler job 4243 (every 15 min).
# Even if Android kills Termux, JobScheduler restarts it to run this script.
# Detects dead services and restarts everything.
#
# Install:  bash ~/Athena/startup.sh (registers automatically)
# Manual:   bash ~/Athena/keepalive.sh
# =============================================================================

ATHENA="$HOME/Athena"
LOG="$ATHENA/keepalive.log"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"
}

log "=== Keepalive check ==="

# Lock file to prevent concurrent runs
LOCK="$PREFIX/tmp/athena_keepalive.lock"
exec 200>"$LOCK"
flock -n 200 || { log "Already running, skipping"; exit 0; }

needs_restart=false

# Check 1: Pi processes
PI_COUNT=$(pgrep -af "node pi" 2>/dev/null | wc -l)
if [ "$PI_COUNT" -eq 0 ]; then
    log "⛔ Pi is DOWN — needs restart"
    needs_restart=true
else
    log "✅ Pi: $PI_COUNT processes"
fi

# Check 2: Discord bot
if pgrep -f "discord_bot.py" >/dev/null 2>&1; then
    log "✅ Discord bot: Running"
else
    log "⛔ Discord bot: DOWN — needs restart"
    needs_restart=true
fi

# Check 3: Watchdog
if pgrep -f "watchdog.sh" >/dev/null 2>&1; then
    log "✅ Watchdog: Running"
else
    log "⛔ Watchdog: DOWN — will be restarted with startup"
    needs_restart=true
fi

# Check 4: Heartbeat
HEARTBEAT_PID="$ATHENA/automations/system/heartbeat.pid"
if [ -f "$HEARTBEAT_PID" ] && kill -0 "$(cat "$HEARTBEAT_PID")" 2>/dev/null; then
    log "✅ Heartbeat: Running"
else
    log "⛔ Heartbeat: DOWN — needs restart"
    needs_restart=true
fi

# Restart if anything is dead
if [ "$needs_restart" = true ]; then
    log "⚠️  Service failure detected — restarting..."
    bash "$ATHENA/startup.sh" 2>&1 | tee -a "$LOG"
    log "✅ Restart initiated"
else
    log "✅ All services healthy"
fi

log "=== Keepalive complete ==="
exit 0
