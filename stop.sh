#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Athena Stop — Clean Shutdown
# =============================================================================
# Stops all Athena services cleanly.
# Usage:  bash ~/Athena/stop.sh
# =============================================================================

ATHENA="$HOME/Athena"

echo "🧠 Athena Shutdown"
echo "═══════════════════"

# Stop Discord bot, Mattermost, agent queue
bash "$ATHENA/automations/comm/bot_manager.sh" stop 2>/dev/null || true
echo "  ✅ Bot services stopped"

# Stop heartbeat daemon
bash "$ATHENA/automations/system/heartbeat.sh" --stop 2>/dev/null || true
echo "  ✅ Heartbeat stopped"

# Cancel keepalive job
termux-job-scheduler --cancel --job-id 4243 2>/dev/null || true
echo "  ✅ Keepalive job cancelled (4243)"

# Cancel aware daemon job
termux-job-scheduler --cancel --job-id 4242 2>/dev/null || true
echo "  ✅ Aware daemon job cancelled (4242)"

# Remove persistent notification
termux-notification-remove athena_running 2>/dev/null || true
echo "  ✅ Notification removed"

echo ""
echo "🛑 Athena stopped"
echo "   To restart: bash $ATHENA/startup.sh"
