#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# AWARE DAEMON — Truly Independent Proactive Engagement Engine
# =============================================================================
# This runs as a real Android background job via termux-job-scheduler.
# It fires Android notifications directly to your phone WITHOUT needing Pi.
#
# How it runs:
#   - termux-job-scheduler calls this every 15 minutes (Android minimum)
#   - On boot, ~/.termux/boot/aware_boot.sh starts the job
#   - Even when Pi is closed, this fires real notifications
#
# Install:  bash automations/aware/daemon.sh --install
# Status:   bash automations/aware/daemon.sh --status
# Test:     bash automations/aware/daemon.sh --test
# =============================================================================

AWARE_DIR="$HOME/Athena/aware"
ORCHESTRATOR="$HOME/Athena/automations/aware/orchestrator.py"
STATE_FILE="$AWARE_DIR/state.json"
LOG_FILE="$AWARE_DIR/daemon.log"
LOCK_FILE="$PREFIX/tmp/aware_daemon.lock"

# Prevent concurrent runs
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    # Keep log under 500 lines
    tail -n 500 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
}

notify() {
    local title="$1" message="$2" urgency="${3:-info}" id="$4"
    termux-notification \
        --title "$title" \
        --content "$message" \
        --id "aware_${id}" \
        --channel "aware_${urgency}" \
        --priority "$urgency" \
        --led-color "${urgency}" \
        --vibrate "$([ "$urgency" = "urgent" ] && echo 500 || echo 0)" \
        2>/dev/null
    log "NOTIFICATION: $title"
}

# ─── INSTALL ────────────────────────────────────────────────────────────────
install() {
    echo "🔧 Installing Aware Daemon..."
    
    DAEMON_SCRIPT="/data/data/com.termux/files/home/Athena/automations/aware/daemon.sh"
    
    # 1. Register with Android JobScheduler (runs every 15 min)
    termux-job-scheduler \
        --script "$DAEMON_SCRIPT" \
        --job-id 4242 \
        --period-ms 900000  # 15 minutes (Android minimum)
    
    echo "   ✅ Job 4242 registered — runs every 15 minutes"
    
    # 2. Create boot script
    mkdir -p "$HOME/.termux/boot"
    cat > "$HOME/.termux/boot/aware_boot.sh" << BOOTEOF
#!/data/data/com.termux/files/usr/bin/bash
# Aware Daemon — starts on device boot
termux-job-scheduler \
    --script $DAEMON_SCRIPT \
    --job-id 4242 \
    --period-ms 900000
BOOTEOF
    chmod +x "$HOME/.termux/boot/aware_boot.sh"
    echo "   ✅ Boot script created at ~/.termux/boot/aware_boot.sh"
    
    # 3. Create Android notification channels (required for Android 8+)
    termux-notification --channel "aware_info" --title "Aware" --content "Info channel created" --id aware_channel_setup 2>/dev/null
    termux-notification --channel "aware_urgent" --title "Aware" --content "Urgent channel created" --id aware_urgent_setup 2>/dev/null
    termux-notification --channel "aware_alert" --title "Aware" --content "Alert channel created" --id aware_alert_setup 2>/dev/null
    
    # 4. Test it
    notify "🧠 Aware Daemon Installed" "Proactive engagement system is now running. You'll get notifications every 15 minutes when something's due." "info" "install_test"
    
    echo ""
    echo "✅ Aware Daemon is LIVE on your device."
    echo "   It will run even when Pi is closed."
    echo "   To verify: termux-job-scheduler -p"
}

uninstall() {
    echo "🗑️ Uninstalling Aware Daemon..."
    termux-job-scheduler --cancel --job-id 4242 2>/dev/null
    termux-job-scheduler --cancel-all 2>/dev/null
    rm -f "$HOME/.termux/boot/aware_boot.sh"
    echo "✅ Uninstalled"
}

status() {
    echo "🧠 AWARE DAEMON STATUS"
    echo "========================"
    
    # Check if job is registered
    PENDING=$(termux-job-scheduler -p 2>/dev/null)
    if echo "$PENDING" | grep -q "4242"; then
        echo "  Job:     🟢 Registered (ID 4242, every 15 min)"
    else
        echo "  Job:     🔴 NOT registered"
    fi
    
    # Check boot script
    if [ -f "$HOME/.termux/boot/aware_boot.sh" ]; then
        echo "  Boot:    🟢 Auto-starts on reboot"
    else
        echo "  Boot:    ⚪ No boot script"
    fi
    
    # Check wake lock
    WAKELOCK=$(dumpsys deviceidle | grep -i aware 2>/dev/null || echo "")
    if [ -n "$WAKELOCK" ]; then
        echo "  Wake:    🟢 Active"
    fi
    
    # Show recent activity
    if [ -f "$LOG_FILE" ]; then
        LAST=$(tail -3 "$LOG_FILE" 2>/dev/null)
        echo ""
        echo "  Recent:"
        echo "$LAST" | while read line; do echo "    $line"; done
    fi
    
    # Show orchestrator status
    echo ""
    python3 "$ORCHESTRATOR" status 2>/dev/null || echo "  Orchestrator unavailable"
}

# ─── MAIN DAEMON LOOP ───────────────────────────────────────────────────────
tick() {
    log "Daemon tick starting..."
    
    # 1. Run the orchestrator to check for due engagements
    RESULT=$(python3 "$ORCHESTRATOR" tick 2>&1)
    EXIT_CODE=$?
    
    if echo "$RESULT" | grep -q "✅"; then
        # Engagements were fired — notify the user
        FIRED=$(echo "$RESULT" | grep "✅\|⚠️" | sed 's/.*✅ //; s/.*⚠️ //')
        notify "🧠 Aware Engagements Fired" "$FIRED" "info" "engagement_tick"
        log "Engagements fired: $FIRED"
    elif echo "$RESULT" | grep -q "proactive_mode_disabled"; then
        log "Proactive mode disabled — skipping"
    else
        log "No engagements due"
    fi
    
    # 2. Also run the Aware prompt checker
    NEXT=$(python3 "$HOME/Athena/automations/aware/engage.py" next 2>/dev/null)
    if [ -n "$NEXT" ] && [ "$NEXT" != "none" ]; then
        # Map prompt type to notification
        case "$NEXT" in
            morning)   notify "🌅 Morning Reflection" "Time to set your intentions. Open Pi and use /aware morning" "info" "morning" ;;
            evening)   notify "🌙 Evening Check-In" "How was your day? Open Pi and use /aware evening" "info" "evening" ;;
            spark)     notify "✨ Creative Spark" "Quick thought experiment waiting. Use /aware spark" "info" "spark" ;;
            notice)    notify "👀 Notice Something?" "What have you noticed today? Use /aware notice" "info" "notice" ;;
            checkin)   notify "🎯 Goal Check-In" "Time for a goal pulse. Use /aware checkin" "info" "checkin" ;;
            reflect)   notify "🔮 Deep Reflection" "Quiet moment? Use /aware reflect" "info" "reflect" ;;
        esac
        log "Aware prompt notification sent: $NEXT"
    fi
    
    log "Daemon tick complete"
}

# ─── COMMAND DISPATCH ───────────────────────────────────────────────────────
case "${1:-tick}" in
    --install|-i)
        install
        ;;
    --uninstall|-u)
        uninstall
        ;;
    --status|-s)
        status
        ;;
    --test|-t)
        echo "🧪 Sending test notification..."
        notify "🧪 Aware Test Notification" "If you see this, the daemon is working. It will check for engagements every 15 minutes automatically." "info" "test"
        echo "✅ Test notification sent. Check your phone."
        ;;
    --log|-l)
        tail -n 50 "$LOG_FILE" 2>/dev/null || echo "No log yet"
        ;;
    tick|*)
        tick
        ;;
esac
