#!/data/data/com.termux/files/usr/bin/bash
# Aware Auto-Engagement Trigger
# Run this periodically (e.g., every 30 min via trigger engine) to:
#   1. Run the orchestrator tick (day/week/month scheduled engagements)
#   2. Fire any due engagements through the correct channels
#
# CHANNEL RULES (enforced by orchestrator):
#   QUESTION prompts (morning, evening, checkin, reflect, spark) → Discord ONLY
#   UPDATE prompts  (digest, notice, publish)                   → Notification ONLY
#   NEVER ask questions through notifications.
#   NEVER send general updates through Discord.
#
# Fire manually: bash automations/aware/auto_engage.sh
# Dry run:       bash automations/aware/auto_engage.sh --dry-run

AWARE_DIR="$HOME/Athena/aware"
ENGAGE_PY="$HOME/Athena/automations/aware/engage.py"
ORCHESTRATOR_PY="$HOME/Athena/automations/aware/orchestrator.py"
STATE_FILE="$AWARE_DIR/state.json"
LOCK_FILE="$PREFIX/tmp/aware_engage.lock"
LOG_FILE="$AWARE_DIR/engage.log"

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
    if [ "$LOCK_AGE" -lt 300 ]; then
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi
touch "$LOCK_FILE"

cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

log() {
    echo "[$(date '+%Y-%m-%d %H:%M')] $1" >> "$LOG_FILE"
}

# ─── DRY RUN ──────────────────────────────────────────────────
if [ "$1" = "--dry-run" ]; then
    echo "🧠 Aware Auto-Engage (dry run)"
    echo "  Time: $(date '+%Y-%m-%d %H:%M')"
    echo ""
    
    # Show Aware prompt status
    echo "── Aware Prompts ──"
    python3 "$ENGAGE_PY" status 2>/dev/null || true
    
    echo ""
    
    # Show Orchestrator schedule
    echo "── Orchestrator Schedule ──"
    python3 "$ORCHESTRATOR_PY" status 2>/dev/null || true
    
    echo ""
    
    # Show available channels
    echo "── Channel Status ──"
    python3 "$HOME/Athena/automations/aware/channels.py" status 2>/dev/null || true
    
    exit 0
fi

# ─── RUN ORCHESTRATOR TICK ────────────────────────────────────
# The orchestrator handles ALL scheduling, channel routing, and dispatch.
# It enforces the rule: questions → Discord, updates → notifications.
ORCHESTRATOR_RESULT=$(python3 "$ORCHESTRATOR_PY" tick 2>&1)

if echo "$ORCHESTRATOR_RESULT" | grep -q "Fired"; then
    log "Orchestrator fired engagements"
elif echo "$ORCHESTRATOR_RESULT" | grep -q "No engagements due"; then
    log "Orchestrator: no engagements due"
elif echo "$ORCHESTRATOR_RESULT" | grep -q "proactive_mode_disabled"; then
    log "Orchestrator: proactive mode disabled"
else
    log "Orchestrator result: $ORCHESTRATOR_RESULT"
fi

# ─── TRIM LOG ─────────────────────────────────────────────────
tail -n 100 "$LOG_FILE" > "${LOG_FILE}.tmp" 2>/dev/null && mv "${LOG_FILE}.tmp" "$LOG_FILE"

exit 0
