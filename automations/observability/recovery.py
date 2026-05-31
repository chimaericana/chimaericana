#!/usr/bin/env python3
"""recovery.py — Auto-recovery engine for Projex.

Detects failures, classifies them (transient vs permanent),
attempts recovery, maintains checkpoints, and logs all actions.

Usage:
    python recovery.py check
    python recovery.py status
    python recovery.py log [--limit 20]
    python recovery.py checkpoint --name "daily_report" --data '{"status": "partial"}'
    python recovery.py restore --name "daily_report"
    python recovery.py test
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

RECOVERY_DIR = "automations/observability"
RECOVERY_LOG = f"{RECOVERY_DIR}/recovery.jsonl"
CHECKPOINTS_DIR = f"{RECOVERY_DIR}/checkpoints"
RECOVERY_CONFIG = f"{RECOVERY_DIR}/recovery_config.json"

MAX_RETRIES = 3
DEFAULT_CONFIG = {
    "max_retries": MAX_RETRIES,
    "retry_delay_seconds": 30,
    "auto_recover": True,
    "checkpoint_ttl_hours": 24,
}


def init():
    os.makedirs(RECOVERY_DIR, exist_ok=True)
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    if not os.path.exists(RECOVERY_CONFIG):
        with open(RECOVERY_CONFIG, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)


def load_config():
    with open(RECOVERY_CONFIG) as f:
        return json.load(f)


def log_recovery(event_type, name, status, details=None, error=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "name": name,
        "status": status,
        "details": details or {},
        "error": error,
    }
    with open(RECOVERY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def save_checkpoint(name, data, metadata=None):
    path = os.path.join(CHECKPOINTS_DIR, f"{name}.json")
    checkpoint = {
        "name": name,
        "data": data,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    with open(path, "w") as f:
        json.dump(checkpoint, f, indent=2)
    return checkpoint


def load_checkpoint(name):
    path = os.path.join(CHECKPOINTS_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def list_checkpoints(config=None):
    if not os.path.exists(CHECKPOINTS_DIR):
        return []
    checkpoints = []
    for filename in os.listdir(CHECKPOINTS_DIR):
        if filename.endswith(".json"):
            path = os.path.join(CHECKPOINTS_DIR, filename)
            with open(path) as f:
                cp = json.load(f)
                # Check TTL
                if config:
                    ttl = config.get("checkpoint_ttl_hours", 24)
                    created = datetime.fromisoformat(cp["created_at"])
                    age = (datetime.now() - created).total_seconds() / 3600
                    if age > ttl:
                        cp["expired"] = True
                    else:
                        cp["expired"] = False
                checkpoints.append(cp)
    return sorted(checkpoints, key=lambda c: c["updated_at"], reverse=True)


def check_system():
    """Run system checks and classify any issues found."""
    issues = []
    config = load_config()

    # Check if databases exist
    db_files = [
        "automations/social/scheduler.db",
        "automations/social/tracker.db",
    ]
    for db in db_files:
        if not os.path.exists(db):
            issues.append({
                "type": "missing_db",
                "severity": "warning",
                "name": db,
                "message": f"Database not found: {db}",
                "recoverable": True,
                "action": "Recreate database on next use",
            })

    # Check for stale lock files
    lock_files = [
        "automations/system/heartbeat.pid",
        "automations/triggers/engine.pid",
    ]
    for lock in lock_files:
        if os.path.exists(lock):
            with open(lock) as f:
                pid = f.read().strip()
            try:
                pid_int = int(pid)
                os.kill(pid_int, 0)  # Check if process exists
            except (ValueError, ProcessLookupError):
                issues.append({
                    "type": "stale_pid",
                    "severity": "info",
                    "name": lock,
                    "message": f"Stale PID file: {lock} (PID {pid} not running)",
                    "recoverable": True,
                    "action": "Remove stale PID file",
                })

    # Check log file sizes
    log_files = [
        "automations/observability/activity.jsonl",
        "automations/observability/recovery.jsonl",
        "automations/social/alerts.jsonl",
    ]
    for log in log_files:
        if os.path.exists(log):
            size = os.path.getsize(log)
            if size > 10 * 1024 * 1024:  # 10MB
                issues.append({
                    "type": "large_log",
                    "severity": "warning",
                    "name": log,
                    "message": f"Large log file: {log} ({size / 1024 / 1024:.1f}MB)",
                    "recoverable": True,
                    "action": "Rotate/truncate log file",
                })

    return issues


def attempt_recovery(issue):
    """Attempt to recover from a detected issue."""
    name = issue.get("name", "unknown")
    itype = issue.get("type", "unknown")

    try:
        if itype == "stale_pid":
            os.remove(name)
            log_recovery("auto_recover", name, "success",
                        details={"action": "removed_stale_pid"})
            return True, f"Removed stale PID file: {name}"

        elif itype == "missing_db":
            # Database will be recreated on next use
            log_recovery("auto_recover", name, "skipped",
                        details={"action": "will_recreate_on_use"})
            return True, f"Database will be recreated: {name}"

        elif itype == "large_log":
            # Rotate log
            backup = f"{name}.bak.{datetime.now().strftime('%Y%m%d')}"
            os.rename(name, backup)
            with open(name, "w") as f:
                f.write("")
            log_recovery("auto_recover", name, "success",
                        details={"action": "rotated", "backup": backup})
            return True, f"Rotated log: {name} → {backup}"

        else:
            log_recovery("auto_recover", name, "skipped",
                        details={"reason": "unknown_issue_type", "type": itype})
            return False, f"Unknown issue type: {itype}"

    except Exception as e:
        log_recovery("auto_recover", name, "failed",
                    error=str(e))
        return False, f"Recovery failed: {e}"


def get_recovery_log(limit=20):
    if not os.path.exists(RECOVERY_LOG):
        return []
    entries = []
    with open(RECOVERY_LOG) as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except:
                continue
    return entries[-limit:]


def format_issue(issue):
    severity_icons = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
    icon = severity_icons.get(issue.get("severity", "info"), "❓")
    recoverable = "✅ Recoverable" if issue.get("recoverable") else "❌ Not recoverable"

    lines = [f"  {icon} [{issue['severity']}] {issue['name']}"]
    lines.append(f"     {issue['message']}")
    lines.append(f"     {recoverable}")
    if issue.get("action"):
        lines.append(f"     Action: {issue['action']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Recovery System")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # check
    subparsers.add_parser("check", help="Check for issues and attempt recovery")

    # status
    subparsers.add_parser("status", help="Show recovery system status")

    # log
    log = subparsers.add_parser("log", help="View recovery log")
    log.add_argument("--limit", "-l", type=int, default=20)

    # checkpoint
    cp = subparsers.add_parser("checkpoint", help="Save a checkpoint")
    cp.add_argument("--name", "-n", required=True)
    cp.add_argument("--data", "-d", required=True, help="JSON data")
    cp.add_argument("--metadata", "-m", help="JSON metadata")

    # restore
    restore = subparsers.add_parser("restore", help="Restore from checkpoint")
    restore.add_argument("name", help="Checkpoint name")
    restore.add_argument("--json", "-j", action="store_true")

    # list-checkpoints
    subparsers.add_parser("list-checkpoints", help="List all checkpoints")

    # test
    subparsers.add_parser("test", help="Run recovery tests")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    init()
    config = load_config()

    if args.command == "check":
        print("🔍 Checking system for issues...")
        issues = check_system()

        if not issues:
            print("✅ No issues found. System is healthy.")
            log_recovery("check", "system", "healthy")
        else:
            print(f"\n⚠️  Found {len(issues)} issue(s):\n")
            for issue in issues:
                print(format_issue(issue))
                print()

                if issue.get("recoverable") and config.get("auto_recover", True):
                    success, msg = attempt_recovery(issue)
                    icon = "✅" if success else "❌"
                    print(f"  {icon} Recovery: {msg}")
                    print()

            log_recovery("check", "system", "issues_found",
                        details={"count": len(issues)})

    elif args.command == "status":
        issues = check_system()
        checkpoints = list_checkpoints(config)
        recovery_log = get_recovery_log(limit=5)
        recent_errors = sum(1 for r in recovery_log if r.get("status") == "failed")

        print("🛡️  Recovery System Status")
        print("=" * 50)
        print(f"  Active issues: {len(issues)}")
        print(f"  Checkpoints: {len(checkpoints)}")
        print(f"  Recent recovery errors: {recent_errors}")
        print(f"  Auto-recovery: {'ON' if config.get('auto_recover') else 'OFF'}")
        print(f"  Max retries: {config.get('max_retries', MAX_RETRIES)}")
        print(f"  Checkpoint TTL: {config.get('checkpoint_ttl_hours', 24)}h")

    elif args.command == "log":
        entries = get_recovery_log(args.limit)
        if not entries:
            print("No recovery log entries.")
        else:
            print(f"🛡️  Recovery Log (last {len(entries)})\n" + "=" * 50)
            for entry in entries:
                icon = {"success": "✅", "failed": "❌", "skipped": "⏭️"}.get(entry.get("status"), "📝")
                ts = entry.get("timestamp", "")[:19]
                print(f"  {icon} [{ts}] {entry.get('event', '?')} — {entry.get('name', '?')}")
                if entry.get("error"):
                    print(f"     Error: {entry['error']}")
                print()

    elif args.command == "checkpoint":
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            data = {"value": args.data}

        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except:
                metadata = {"raw": args.metadata}

        cp = save_checkpoint(args.name, data, metadata)
        print(f"✅ Checkpoint saved: {args.name}")
        print(f"   Updated: {cp['updated_at'][:19]}")

    elif args.command == "restore":
        cp = load_checkpoint(args.name)
        if not cp:
            print(f"Error: Checkpoint '{args.name}' not found", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(cp, indent=2))
        else:
            print(f"📦 Checkpoint: {args.name}")
            print(f"   Created: {cp['created_at'][:19]}")
            print(f"   Updated: {cp['updated_at'][:19]}")
            if cp.get("metadata"):
                print(f"   Metadata: {json.dumps(cp['metadata'])}")
            print(f"\n   Data:\n{json.dumps(cp['data'], indent=4)}")

    elif args.command == "list-checkpoints":
        checkpoints = list_checkpoints(config)
        if not checkpoints:
            print("No checkpoints saved.")
        else:
            print(f"📦 Checkpoints ({len(checkpoints)})\n" + "=" * 50)
            for cp in checkpoints:
                expired = "⏰ EXPIRED" if cp.get("expired") else "✅ Valid"
                print(f"  {expired} {cp['name']}")
                print(f"     Updated: {cp['updated_at'][:19]}")
                print()

    elif args.command == "test":
        print("🧪 Running recovery tests...")

        # Test 1: Create checkpoint
        save_checkpoint("test_recovery", {"step": 1, "progress": 50}, {"test": True})
        print("  ✅ Test 1: Checkpoint created")

        # Test 2: Load checkpoint
        cp = load_checkpoint("test_recovery")
        assert cp is not None
        assert cp["data"]["step"] == 1
        print("  ✅ Test 2: Checkpoint loaded")

        # Test 3: Recovery check
        issues = check_system()
        print(f"  ✅ Test 3: System check completed ({len(issues)} issues)")

        # Cleanup
        os.remove(os.path.join(CHECKPOINTS_DIR, "test_recovery.json"))

        log_recovery("test", "recovery_system", "success")
        print("\n✅ All recovery tests passed.")


if __name__ == "__main__":
    main()
