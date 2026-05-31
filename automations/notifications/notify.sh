#!/usr/bin/env bash
# notify.sh — Enhanced notification system with categories, preferences, and history
# Usage: ./notify.sh --type info "Message" [--title "Title"] [--actions "Action1,Action2"]
#        ./notify.sh --type urgent "Server down!"
#        ./notify.sh --history
#        ./notify.sh --config
#        ./notify.sh --test

set -euo pipefail

NOTIFY_DIR="automations/notifications"
HISTORY_FILE="$NOTIFY_DIR/history.jsonl"
CONFIG_FILE="$NOTIFY_DIR/config.json"

init() {
    mkdir -p "$NOTIFY_DIR"
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" <<'EOF'
{
  "quiet_hours": {
    "enabled": false,
    "start": "22:00",
    "end": "07:00"
  },
  "channels": {
    "urgent": { "sound": true, "vibrate": true, "led": true, "notification": true },
    "alert": { "sound": true, "vibrate": false, "led": false, "notification": true },
    "info": { "sound": false, "vibrate": false, "led": false, "notification": true },
    "digest": { "sound": false, "vibrate": false, "led": false, "notification": true }
  },
  "priority_filter": "all",
  "digest_mode": "off"
}
EOF
    fi
}

# Check quiet hours
is_quiet_hours() {
    local enabled
    enabled=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['quiet_hours']['enabled'])" 2>/dev/null || echo "false")
    
    if [[ "$enabled" != "True" ]]; then
        return 1
    fi
    
    local start end now
    start=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['quiet_hours']['start'])")
    end=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['quiet_hours']['end'])")
    now=$(date '+%H:%M')
    
    if [[ "$now" > "$start" || "$now" < "$end" ]]; then
        return 0
    fi
    return 1
}

# Log notification
log_notification() {
    local type="$1" title="$2" message="$3" id="$4"
    local timestamp
    timestamp=$(date -Iseconds)
    
    echo "{\"id\":\"$id\",\"type\":\"$type\",\"title\":\"$(echo "$title" | sed 's/"/\\"/g')\",\"message\":\"$(echo "$message" | sed 's/"/\\"/g')\",\"timestamp\":\"$timestamp\"}" >> "$HISTORY_FILE"
}

# Send notification with category settings
send_notification() {
    local type="${1:-info}"
    local message="$2"
    local title="${3:-Projex}"
    local actions="${4:-}"
    local id
    id=$(date +%s%N | cut -c1-10)
    
    # Check quiet hours
    if is_quiet_hours && [[ "$type" != "urgent" ]]; then
        echo "⏸️  Quiet hours active. Notification queued: [$type] $message"
        # Queue for later
        echo "{\"id\":\"$id\",\"type\":\"$type\",\"title\":\"$title\",\"message\":\"$(echo "$message" | sed 's/"/\\"/g')\",\"queued\":\"$(date -Iseconds)\"}" >> "$NOTIFY_DIR/queue.jsonl"
        return
    fi
    
    # Get channel settings
    local sound vibrate led notification
    sound=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['channels']['${type}']['sound'])" 2>/dev/null || echo "false")
    vibrate=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['channels']['${type}']['vibrate'])" 2>/dev/null || echo "false")
    led=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['channels']['${type}']['led'])" 2>/dev/null || echo "false")
    
    # Build termux-notification command
    local cmd="termux-notification"
    cmd="$cmd --title '$title'"
    cmd="$cmd --content '$message'"
    cmd="$cmd --id '$id'"
    cmd="$cmd --channel '$type'"
    
    if [[ "$sound" == "True" ]]; then
        cmd="$cmd --sound"
    fi
    
    if [[ -n "$actions" ]]; then
        IFS=',' read -ra ACTION_ARRAY <<< "$actions"
        for action in "${ACTION_ARRAY[@]}"; do
            cmd="$cmd --action '$action'"
        done
    fi
    
    # Execute notification
    eval "$cmd" 2>/dev/null || termux-notification --title "$title" --content "$message" --id "$id"
    
    # Vibrate if configured
    if [[ "$vibrate" == "True" ]]; then
        case "$type" in
            urgent) termux-vibrate -d 500 ;;
            alert) termux-vibrate -d 200 ;;
        esac
    fi
    
    # LED if configured
    if [[ "$led" == "True" ]]; then
        case "$type" in
            urgent) termux-led -c red ;;
            alert) termux-led -c amber ;;
            info) termux-led -c green ;;
        esac
        sleep 2
        termux-led -c off
    fi
    
    # Log
    log_notification "$type" "$title" "$message" "$id"
    
    # Feedback
    local icon
    case "$type" in
        urgent) icon="🚨" ;;
        alert) icon="⚠️" ;;
        info) icon="ℹ️" ;;
        digest) icon="📋" ;;
        *) icon="📱" ;;
    esac
    
    echo "$icon Notification sent: [$type] $message"
}

# Show history
show_history() {
    local count="${1:-20}"
    
    if [[ ! -f "$HISTORY_FILE" ]]; then
        echo "No notification history yet."
        return
    fi
    
    echo "📱 Notification History (last $count):"
    echo "══════════════════════════════════════════════════"
    
    tail -n "$count" "$HISTORY_FILE" | tac | while IFS= read -r line; do
        local type title message timestamp
        type=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('type','?'))" 2>/dev/null || echo "?")
        title=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('title',''))" 2>/dev/null || echo "")
        message=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null || echo "")
        timestamp=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('timestamp',''))" 2>/dev/null || echo "")
        
        local icon
        case "$type" in
            urgent) icon="🚨" ;;
            alert) icon="⚠️" ;;
            info) icon="ℹ️" ;;
            digest) icon="📋" ;;
            *) icon="📱" ;;
        esac
        
        echo "$icon [$timestamp] $title: $message"
    done
}

# Show/update config
show_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "No config file. Run with --init first."
        return
    fi
    
    echo "📱 Notification Configuration:"
    echo "══════════════════════════════════════════════════"
    python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
print(f\"Quiet Hours: {'ON' if c['quiet_hours']['enabled'] else 'OFF'} ({c['quiet_hours']['start']} - {c['quiet_hours']['end']})\")
print(f\"Priority Filter: {c['priority_filter']}\")
print(f\"Digest Mode: {c['digest_mode']}\")
print()
print('Channel Settings:')
for ch, settings in c['channels'].items():
    icons = {'True': '✅', 'False': '❌'}
    s = settings
    print(f\"  {ch}: sound={icons[str(s['sound'])]} vibrate={icons[str(s['vibrate'])]} led={icons[str(s['led'])]}\")
" 2>/dev/null || cat "$CONFIG_FILE"
}

# Test notification
test_notification() {
    echo "🧪 Sending test notifications..."
    send_notification "info" "This is a test info notification" "Projex Test"
    sleep 1
    send_notification "alert" "This is a test alert notification" "Projex Test"
    sleep 1
    send_notification "urgent" "This is a test urgent notification" "Projex Test"
    echo "✅ Test complete. Check your notifications."
}

usage() {
    cat <<EOF
Enhanced Notification System

Usage: $0 --type <type> "message" [options]
       $0 --history [count]
       $0 --config
       $0 --test
       $0 --help

Types: urgent, alert, info, digest

Options:
  --type, -t      Notification type (urgent/alert/info/digest)
  --title         Notification title (default: Projex)
  --actions       Comma-separated action buttons
  --history, -H   Show notification history
  --config, -C    Show/update configuration
  --test          Send test notifications
  --help, -h      Show this help

Examples:
  $0 --type info "New press release drafted"
  $0 --type urgent "Crisis detected in media coverage"
  $0 --type alert "Social media engagement spike" --actions "View,Dismiss"
  $0 --history 10
  $0 --config
EOF
}

init

if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

case $1 in
    --type|-t)
        shift
        ntype="$1"
        shift
        message="$1"
        title="Projex"
        actions=""
        shift
        while [[ $# -gt 0 ]]; do
            case $1 in
                --title) title="$2"; shift 2 ;;
                --actions) actions="$2"; shift 2 ;;
                *) shift ;;
            esac
        done
        send_notification "$ntype" "$message" "$title" "$actions"
        ;;
    --history|-H)
        shift
        show_history "${1:-20}"
        ;;
    --config|-C)
        show_config
        ;;
    --test)
        test_notification
        ;;
    --help|-h)
        usage
        ;;
    *)
        # Default: send as info
        send_notification "info" "$*" "Projex"
        ;;
esac
