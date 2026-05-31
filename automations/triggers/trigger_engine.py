#!/usr/bin/env python3
"""trigger_engine.py — Event-driven trigger system for Projex automations.

Trigger types:
- cron: Time-based (e.g., every hour, daily at 8am)
- file: File change detection
- webhook: HTTP webhook listener (simple)
- condition: Conditional triggers based on script output
- manual: Manually triggered

Usage:
    python trigger_engine.py add --type cron --name "daily_report" --schedule "0 8 * * *" --command "bash automations/report.sh daily"
    python trigger_engine.py list
    python trigger_engine.py fire <id>
    python trigger_engine.py remove <id>
    python trigger_engine.py log [--limit 20]
    python trigger_engine.py check  # Check all triggers
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

TRIGGERS_DIR = "automations/triggers"
CONFIG_FILE = f"{TRIGGERS_DIR}/triggers.json"
LOG_FILE = f"{TRIGGERS_DIR}/trigger_log.jsonl"
PID_FILE = f"{TRIGGERS_DIR}/engine.pid"


def init():
    os.makedirs(TRIGGERS_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"triggers": [], "engine": {"running": False, "check_interval": 60}}, f, indent=2)


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def generate_id():
    return f"trigger_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"


def log_trigger(trigger_id, name, status, output=None, error=None):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {
        "trigger_id": trigger_id,
        "name": name,
        "status": status,
        "output": output,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def execute_command(command, timeout=120):
    """Execute a command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Command timed out", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}


def add_trigger(config, trigger_type, name, command, schedule=None, file_path=None,
                condition=None, enabled=True, cooldown=0, tags=None):
    trigger = {
        "id": generate_id(),
        "type": trigger_type,
        "name": name,
        "command": command,
        "schedule": schedule,
        "file_path": file_path,
        "condition": condition,
        "enabled": enabled,
        "cooldown": cooldown,  # seconds between firings
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
        "last_fired": None,
        "fire_count": 0
    }

    config["triggers"].append(trigger)
    save_config(config)
    return trigger


def list_triggers(config, trigger_type=None, enabled_only=False):
    triggers = config["triggers"]

    if trigger_type:
        triggers = [t for t in triggers if t["type"] == trigger_type]
    if enabled_only:
        triggers = [t for t in triggers if t.get("enabled", True)]

    return triggers


def remove_trigger(config, trigger_id):
    before = len(config["triggers"])
    config["triggers"] = [t for t in config["triggers"] if t["id"] != trigger_id]
    after = len(config["triggers"])
    save_config(config)
    return before - after


def fire_trigger(config, trigger_id):
    trigger = None
    for t in config["triggers"]:
        if t["id"] == trigger_id:
            trigger = t
            break

    if not trigger:
        return False, f"Trigger '{trigger_id}' not found"

    if not trigger.get("enabled", True):
        return False, f"Trigger '{trigger_id}' is disabled"

    # Check cooldown
    if trigger.get("last_fired") and trigger.get("cooldown", 0) > 0:
        last = datetime.fromisoformat(trigger["last_fired"])
        elapsed = (datetime.now() - last).total_seconds()
        if elapsed < trigger["cooldown"]:
            remaining = trigger["cooldown"] - elapsed
            return False, f"Cooldown active: {remaining:.0f}s remaining"

    # Check condition if specified
    if trigger.get("condition"):
        result = execute_command(trigger["condition"], timeout=30)
        if not result["success"]:
            return False, f"Condition failed: {result['stderr']}"

    # Execute the command
    print(f"🔥 Firing trigger: {trigger['name']} ({trigger['id']})")
    print(f"   Command: {trigger['command']}")

    result = execute_command(trigger["command"])

    # Update trigger state
    trigger["last_fired"] = datetime.now().isoformat()
    trigger["fire_count"] = trigger.get("fire_count", 0) + 1
    save_config(config)

    # Log
    log_entry = log_trigger(
        trigger_id,
        trigger["name"],
        "success" if result["success"] else "failed",
        result["stdout"],
        result["stderr"]
    )

    if result["success"]:
        return True, f"Trigger fired successfully. Output: {result['stdout'][:200]}"
    else:
        return False, f"Trigger failed: {result['stderr']}"


def check_cron_triggers(config):
    """Check if any cron triggers should fire now."""
    now = datetime.now()
    fired = []

    for trigger in config["triggers"]:
        if trigger["type"] != "cron" or not trigger.get("enabled", True):
            continue

        if not trigger.get("schedule"):
            continue

        # Check cooldown
        if trigger.get("last_fired") and trigger.get("cooldown", 0) > 0:
            last = datetime.fromisoformat(trigger["last_fired"])
            elapsed = (datetime.now() - last).total_seconds()
            if elapsed < trigger["cooldown"]:
                continue

        # Simple cron parsing: minute hour day month weekday
        try:
            parts = trigger["schedule"].split()
            if len(parts) == 5:
                cron_min, cron_hour, cron_day, cron_month, cron_dow = parts

                match = True
                if cron_min != "*" and int(cron_min) != now.minute:
                    match = False
                if cron_hour != "*" and int(cron_hour) != now.hour:
                    match = False
                if cron_day != "*" and int(cron_day) != now.day:
                    match = False
                if cron_month != "*" and int(cron_month) != now.month:
                    match = False
                # Day of week: 0=Monday, 6=Sunday
                if cron_dow != "*" and int(cron_dow) != now.weekday():
                    match = False

                if match:
                    success, msg = fire_trigger(config, trigger["id"])
                    fired.append({"id": trigger["id"], "name": trigger["name"], "success": success})
        except (ValueError, IndexError) as e:
            log_trigger(trigger["id"], trigger["name"], "error", error=f"Cron parse error: {e}")

    return fired


def get_log(limit=20):
    if not os.path.exists(LOG_FILE):
        return []

    logs = []
    with open(LOG_FILE) as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    return logs[-limit:]


def format_trigger(t):
    type_icons = {"cron": "⏰", "file": "📁", "webhook": "🌐", "condition": "🔀", "manual": "👆"}
    icon = type_icons.get(t["type"], "📌")
    status = "✅" if t.get("enabled", True) else "⛔"
    last_fired = t.get("last_fired", "Never")[:19] if t.get("last_fired") else "Never"

    lines = [f"  {status} {icon} [{t['type']}] {t['name']} ({t['id']})"]
    lines.append(f"     Command: {t['command'][:80]}")
    if t.get("schedule"):
        lines.append(f"     Schedule: {t['schedule']}")
    if t.get("file_path"):
        lines.append(f"     Watch: {t['file_path']}")
    if t.get("condition"):
        lines.append(f"     Condition: {t['condition']}")
    lines.append(f"     Fired: {last_fired} ({t.get('fire_count', 0)} times)")
    if t.get("cooldown"):
        lines.append(f"     Cooldown: {t['cooldown']}s")
    if t.get("tags"):
        lines.append(f"     Tags: {', '.join(t['tags'])}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Trigger Engine")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # add
    add = subparsers.add_parser("add", help="Add a new trigger")
    add.add_argument("--type", "-t", required=True, choices=["cron", "file", "webhook", "condition", "manual"])
    add.add_argument("--name", "-n", required=True, help="Trigger name")
    add.add_argument("--command", "-c", required=True, help="Command to execute")
    add.add_argument("--schedule", "-s", help="Cron schedule (min hour day month dow)")
    add.add_argument("--file", "-f", help="File to watch for changes")
    add.add_argument("--condition", help="Condition command (must succeed to fire)")
    add.add_argument("--cooldown", type=int, default=60, help="Cooldown in seconds")
    add.add_argument("--tags", nargs="*", help="Tags for categorization")
    add.add_argument("--disabled", action="store_true", help="Create disabled")

    # list
    ls = subparsers.add_parser("list", help="List triggers")
    ls.add_argument("--type", "-t", choices=["cron", "file", "webhook", "condition", "manual"])
    ls.add_argument("--enabled", "-e", action="store_true")
    ls.add_argument("--json", "-j", action="store_true")

    # fire
    fire = subparsers.add_parser("fire", help="Manually fire a trigger")
    fire.add_argument("id", help="Trigger ID")

    # remove
    rm = subparsers.add_parser("remove", help="Remove a trigger")
    rm.add_argument("id", help="Trigger ID")

    # log
    log = subparsers.add_parser("log", help="View trigger execution log")
    log.add_argument("--limit", "-l", type=int, default=20)
    log.add_argument("--json", "-j", action="store_true")

    # check
    subparsers.add_parser("check", help="Check and fire due triggers")

    # enable/disable
    toggle = subparsers.add_parser("toggle", help="Enable or disable a trigger")
    toggle.add_argument("id", help="Trigger ID")
    toggle.add_argument("--enable", action="store_true")
    toggle.add_argument("--disable", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    init()
    config = load_config()

    if args.command == "add":
        trigger = add_trigger(
            config, args.type, args.name, args.command,
            args.schedule, args.file, args.condition,
            not args.disabled, args.cooldown, args.tags
        )
        print(f"✅ Trigger added: {trigger['id']}")
        print(f"   Name: {trigger['name']}")
        print(f"   Type: {trigger['type']}")
        if args.schedule:
            print(f"   Schedule: {args.schedule}")

    elif args.command == "list":
        triggers = list_triggers(config, args.type, args.enabled)
        if args.json:
            print(json.dumps(triggers, indent=2))
        elif not triggers:
            print("No triggers found.")
        else:
            print(f"🔀 Triggers ({len(triggers)})\n" + "=" * 50)
            for t in triggers:
                print(format_trigger(t))
                print()

    elif args.command == "fire":
        config = load_config()  # Reload for fresh state
        success, msg = fire_trigger(config, args.id)
        print(f"{'✅' if success else '❌'} {msg}")

    elif args.command == "remove":
        count = remove_trigger(config, args.id)
        if count > 0:
            print(f"🗑️  Removed trigger: {args.id}")
        else:
            print(f"Error: Trigger '{args.id}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == "log":
        logs = get_log(args.limit)
        if args.json:
            print(json.dumps(logs, indent=2))
        elif not logs:
            print("No trigger execution log.")
        else:
            print(f"🔀 Trigger Log (last {len(logs)})\n" + "=" * 50)
            for entry in logs:
                icon = "✅" if entry["status"] == "success" else "❌"
                ts = entry["timestamp"][:19]
                print(f"  {icon} [{ts}] {entry['name']} ({entry['trigger_id']})")
                if entry.get("error"):
                    print(f"     Error: {entry['error'][:100]}")
                if entry.get("output"):
                    print(f"     Output: {entry['output'][:100]}")
                print()

    elif args.command == "check":
        fired = check_cron_triggers(config)
        if fired:
            print(f"🔥 {len(fired)} trigger(s) fired:")
            for f in fired:
                icon = "✅" if f["success"] else "❌"
                print(f"  {icon} {f['name']} ({f['id']})")
        else:
            print("✅ No triggers due for firing")

    elif args.command == "toggle":
        for t in config["triggers"]:
            if t["id"] == args.id:
                if args.enable:
                    t["enabled"] = True
                    print(f"✅ Enabled: {t['name']}")
                elif args.disable:
                    t["enabled"] = False
                    print(f"⛔ Disabled: {t['name']}")
                else:
                    t["enabled"] = not t.get("enabled", True)
                    status = "enabled" if t["enabled"] else "disabled"
                    print(f"{'✅' if t['enabled'] else '⛔'} {t['name']} {status}")
                save_config(config)
                break
        else:
            print(f"Error: Trigger '{args.id}' not found", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
