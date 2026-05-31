#!/usr/bin/env python3
"""
Comm Health Checker — Monitors Discord and Mattermost bot processes.
Used by heartbeat system to detect bot crashes.
Returns JSON status for the heartbeat monitor.
"""

import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

COMM_DIR = Path(__file__).parent
PID_DIR = COMM_DIR / ".pids"
CONFIG_PATH = COMM_DIR / "config.json"
LOG_FILE = COMM_DIR / "bot.log"

def check_pid(pid_file: Path) -> dict:
    """Check if a process is running based on PID file."""
    if not pid_file.exists():
        return {"running": False, "pid": None}

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        return {"running": True, "pid": pid}
    except (ValueError, ProcessLookupError, PermissionError):
        pid_file.unlink(missing_ok=True)
        return {"running": False, "pid": None}

def check_config() -> dict:
    """Check if config is properly set up."""
    if not CONFIG_PATH.exists():
        return {"valid": False, "issues": ["config.json not found"]}

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    issues = []
    dc = config.get("discord", {})
    if not dc.get("token") or dc["token"].startswith("YOUR_"):
        issues.append("Discord token not configured")

    mm = config.get("mattermost", {})
    if mm.get("enabled") and (not mm.get("token") or mm["token"].startswith("YOUR_")):
        issues.append("Mattermost token not configured")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "discord_enabled": dc.get("enabled", False),
        "mattermost_enabled": mm.get("enabled", False)
    }

def check_log_health() -> dict:
    """Check recent log entries for errors."""
    if not LOG_FILE.exists():
        return {"recent_errors": 0, "status": "no_logs"}

    try:
        with open(LOG_FILE) as f:
            lines = f.readlines()

        # Check last 50 lines for errors
        recent = lines[-50:] if len(lines) > 50 else lines
        error_count = sum(1 for line in recent if "ERROR" in line or "CRITICAL" in line)

        if error_count > 5:
            return {"recent_errors": error_count, "status": "degraded"}
        elif error_count > 0:
            return {"recent_errors": error_count, "status": "warnings"}
        else:
            return {"recent_errors": 0, "status": "clean"}
    except Exception as e:
        return {"recent_errors": -1, "status": f"check_failed: {e}"}

def main():
    discord = check_pid(PID_DIR / "discord.pid")
    mattermost = check_pid(PID_DIR / "mattermost.pid")
    config = check_config()
    log_health = check_log_health()

    # Determine overall health
    bots_running = sum([discord["running"], mattermost["running"]])
    total_bots = (1 if config.get("discord_enabled") else 0) + (1 if config.get("mattermost_enabled") else 0)

    if total_bots == 0:
        overall = "not_configured"
    elif bots_running == total_bots and log_health["status"] == "clean":
        overall = "healthy"
    elif bots_running > 0:
        overall = "degraded"
    else:
        overall = "down"

    status = {
        "component": "comm_bots",
        "overall_health": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bots": {
            "discord": discord,
            "mattermost": mattermost
        },
        "config": config,
        "log_health": log_health
    }

    if "--json" in sys.argv:
        print(json.dumps(status, indent=2))
    else:
        emoji = {"healthy": "✅", "degraded": "⚠️", "down": "❌", "not_configured": "🔧"}.get(overall, "❓")
        print(f"{emoji} Comm Bots: {overall}")
        print(f"   Discord: {'🟢' if discord['running'] else '🔴'} (PID: {discord['pid'] or 'N/A'})")
        print(f"   Mattermost: {'🟢' if mattermost['running'] else '🔴'} (PID: {mattermost['pid'] or 'N/A'})")
        if config["issues"]:
            for issue in config["issues"]:
                print(f"   ⚠️  {issue}")
        if log_health["recent_errors"] > 0:
            print(f"   ⚠️  {log_health['recent_errors']} errors in recent logs")

    # Exit code for scripts
    sys.exit(0 if overall in ["healthy"] else 1)

if __name__ == "__main__":
    main()
