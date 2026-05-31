#!/data/data/com.termux/files/usr/bin/python3
"""Aware Trigger — integrates with the existing trigger engine.
Registers Aware as a periodic trigger that fires proactive prompts."""

import json
import os
import sys

TRIGGERS_FILE = os.path.expanduser("~/Athena/automations/triggers/triggers.json")
AUTO_ENGAGE = os.path.expanduser("~/Athena/automations/aware/auto_engage.sh")

def register_trigger():
    """Register Aware auto-engage as a trigger in the existing engine."""
    if not os.path.exists(TRIGGERS_FILE):
        print("❌ Trigger engine config not found at:", TRIGGERS_FILE)
        return False

    with open(TRIGGERS_FILE) as f:
        triggers = json.load(f)

    aware_trigger = {
        "id": "aware_auto_engage",
        "name": "Aware Proactive Engagement",
        "description": "Periodically checks if a proactive prompt should be fired",
        "type": "cron",
        "enabled": True,
        "schedule": {
            "interval_minutes": 30,
            "time_window": ["08:00", "22:00"]
        },
        "action": {
            "type": "script",
            "path": AUTO_ENGAGE,
            "args": []
        },
        "cooldown_minutes": 0,
        "max_executions_per_hour": 2,
        "created_at": "2026-05-31",
        "tags": ["aware", "proactive", "life"]
    }

    # Check if already registered
    existing_ids = [t.get("id") for t in triggers.get("triggers", [])]
    if "aware_auto_engage" in existing_ids:
        # Update it
        for i, t in enumerate(triggers.get("triggers", [])):
            if t.get("id") == "aware_auto_engage":
                triggers["triggers"][i] = aware_trigger
                break
        print("✅ Aware trigger updated in trigger engine.")
    else:
        triggers.setdefault("triggers", []).append(aware_trigger)
        print("✅ Aware trigger registered in trigger engine.")

    with open(TRIGGERS_FILE, "w") as f:
        json.dump(triggers, f, indent=2)

    return True


def unregister_trigger():
    """Remove Aware trigger from the engine."""
    if not os.path.exists(TRIGGERS_FILE):
        return False

    with open(TRIGGERS_FILE) as f:
        triggers = json.load(f)

    triggers["triggers"] = [t for t in triggers.get("triggers", []) if t.get("id") != "aware_auto_engage"]

    with open(TRIGGERS_FILE, "w") as f:
        json.dump(triggers, f, indent=2)

    print("✅ Aware trigger removed from trigger engine.")
    return True


def status():
    """Check if Aware trigger is registered."""
    if not os.path.exists(TRIGGERS_FILE):
        print("❌ Trigger engine not found")
        return

    with open(TRIGGERS_FILE) as f:
        triggers = json.load(f)

    for t in triggers.get("triggers", []):
        if t.get("id") == "aware_auto_engage":
            enabled = "🟢 Enabled" if t.get("enabled") else "🔴 Disabled"
            interval = t.get("schedule", {}).get("interval_minutes", "?")
            print(f"✅ Aware auto-engage: {enabled}")
            print(f"   Check interval: every {interval} minutes")
            print(f"   Time window: {t.get('schedule', {}).get('time_window', 'N/A')}")
            return

    print("❌ Aware trigger not registered in trigger engine")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: aware_trigger.py <register|unregister|status>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "register":
        register_trigger()
    elif cmd == "unregister":
        unregister_trigger()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
