#!/data/data/com.termux/files/usr/bin/bash
# Aware Auto-Engagement Trigger
# Run this periodically (e.g., every 30 min via trigger engine) to check
# if a proactive prompt should be fired.
# 
# Fire manually: bash automations/aware/auto_engage.sh
# Dry run:       bash automations/aware/auto_engage.sh --dry-run

AWARE_DIR="$HOME/Athena/aware"
ENGAGE_PY="$HOME/Athena/automations/aware/engage.py"
STATE_FILE="$AWARE_DIR/state.json"
LOCK_FILE="$PREFIX/tmp/aware_engage.lock"

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
    if [ "$LOCK_AGE" -lt 300 ]; then
        # Lock is recent (under 5 min) — skip
        exit 0
    fi
    # Stale lock — remove it
    rm -f "$LOCK_FILE"
fi
touch "$LOCK_FILE"

cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

# Source notification helper if available
NOTIFY_SCRIPT="$HOME/Athena/automations/notifications/notify.sh"

send_notification() {
    local title="$1"
    local message="$2"
    local level="${3:-info}"
    
    if [ -f "$NOTIFY_SCRIPT" ]; then
        bash "$NOTIFY_SCRIPT" "$level" "$title" "$message" 2>/dev/null || true
    fi
    
    # Also log it
    echo "[$(date '+%Y-%m-%d %H:%M')] [$level] $title — $message" >> "$AWARE_DIR/engage.log"
}

# Check schedule
NEXT_TYPE=$(python3 "$ENGAGE_PY" next 2>/dev/null)

if [ "$1" = "--dry-run" ]; then
    echo "🧠 Aware Auto-Engage (dry run)"
    echo "  Time: $(date '+%Y-%m-%d %H:%M')"
    if [ -n "$NEXT_TYPE" ] && [ "$NEXT_TYPE" != "none" ]; then
        echo "  Would fire: $NEXT_TYPE"
        echo "  Prompt category: $NEXT_TYPE"
        echo ""
        echo "To see available prompts: cat aware/prompts/${NEXT_TYPE}.md"
    else
        echo "  No prompts due (schedule satisfied or quiet hours)"
        echo "  Status:"
        python3 "$ENGAGE_PY" status 2>/dev/null || true
    fi
    exit 0
fi

if [ -n "$NEXT_TYPE" ] && [ "$NEXT_TYPE" != "none" ]; then
    # A prompt is due — send notification
    case "$NEXT_TYPE" in
        morning)
            send_notification "🌅 Morning Reflection" "Time to set your intentions. Use /aware morning when you're ready." "info"
            ;;
        evening)
            send_notification "🌙 Evening Check-In" "How was your day? Use /aware evening to reflect." "info"
            ;;
        spark)
            send_notification "✨ Creative Spark" "Got a minute for a thought experiment? Use /aware spark" "info"
            ;;
        notice)
            send_notification "👀 Notice Something?" "What have you noticed today? Use /aware notice <thing>" "info"
            ;;
        checkin)
            send_notification "🎯 Goal Check-In" "Time for a quick goal pulse. Use /aware checkin" "info"
            ;;
        reflect)
            send_notification "🔮 Deep Reflection" "Quiet moment? Use /aware reflect for a deeper question." "info"
            ;;
        *)
            send_notification "🧠 Aware Check-In" "Use /aware to see what's available" "info"
            ;;
    esac
    
    echo "[$(date '+%Y-%m-%d %H:%M')] Fired proactive prompt: $NEXT_TYPE" >> "$AWARE_DIR/engage.log"
fi
