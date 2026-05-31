#!/usr/bin/env python3
"""activity_tracker.py — Structured activity logging for all Projex operations.

Logs: agent actions, tool calls, command executions, automation runs,
subagent activity, trigger firings, errors, and system events.

Usage:
    python activity_tracker.py log --type "command" --message "RPR draft" --level info
    python activity_tracker.py tail [--lines 20] [--type command]
    python activity_tracker.py search --query "social" [--days 7]
    python activity_tracker.py stats [--days 30]
    python activity_tracker.py export [--format json|csv] [--days 7]
"""

import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_DIR = "automations/observability"
LOG_FILE = f"{LOG_DIR}/activity.jsonl"
STATS_FILE = f"{LOG_DIR}/stats.json"

# Activity types
ACTIVITY_TYPES = [
    "agent_action", "tool_call", "command_exec", "automation_run",
    "subagent_activity", "trigger_fire", "error", "system_event",
    "notification", "social_action", "pr_action", "voice_action",
    "heartbeat", "recovery", "manual"
]

LEVELS = ["debug", "info", "warning", "error", "critical"]


def init():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_activity(activity_type, message, level="info", source=None, details=None):
    """Log an activity entry."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": activity_type,
        "level": level,
        "message": message,
        "source": source or "manual",
        "details": details or {},
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def load_entries(days=None, activity_type=None, level=None, limit=None):
    """Load log entries with optional filters."""
    if not os.path.exists(LOG_FILE):
        return []

    entries = []
    cutoff = None
    if days:
        cutoff = datetime.now() - timedelta(days=days)

    with open(LOG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            # Apply filters
            if cutoff:
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts < cutoff:
                        continue
                except:
                    pass

            if activity_type and entry.get("type") != activity_type:
                continue

            if level and entry.get("level") != level:
                continue

            entries.append(entry)

    if limit:
        entries = entries[-limit:]

    return entries


def search_entries(query, days=None, limit=20):
    """Search log entries by text."""
    entries = load_entries(days=days)
    query_lower = query.lower()

    results = []
    for entry in entries:
        searchable = json.dumps(entry).lower()
        if query_lower in searchable:
            results.append(entry)

    return results[-limit:]


def get_stats(days=30):
    """Get activity statistics."""
    entries = load_entries(days=days)

    stats = {
        "period_days": days,
        "total_entries": len(entries),
        "by_type": {},
        "by_level": {},
        "by_source": {},
        "by_hour": {},
        "errors": 0,
        "warnings": 0,
    }

    for entry in entries:
        # By type
        t = entry.get("type", "unknown")
        stats["by_type"][t] = stats["by_type"].get(t, 0) + 1

        # By level
        lvl = entry.get("level", "unknown")
        stats["by_level"][lvl] = stats["by_level"].get(lvl, 0) + 1

        # By source
        src = entry.get("source", "unknown")
        stats["by_source"][src] = stats["by_source"].get(src, 0) + 1

        # By hour
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            hour = f"{ts.hour:02d}:00"
            stats["by_hour"][hour] = stats["by_hour"].get(hour, 0) + 1
        except:
            pass

        # Error/warning counts
        if lvl in ("error", "critical"):
            stats["errors"] += 1
        elif lvl == "warning":
            stats["warnings"] += 1

    return stats


def export_entries(fmt="json", days=7):
    """Export activity log."""
    entries = load_entries(days=days)

    if fmt == "json":
        return json.dumps({"period_days": days, "entries": entries}, indent=2)
    elif fmt == "csv":
        output = io.StringIO()
        if not entries:
            return "No entries to export"
        writer = csv.DictWriter(output, fieldnames=["timestamp", "type", "level", "message", "source"])
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "timestamp": entry.get("timestamp", ""),
                "type": entry.get("type", ""),
                "level": entry.get("level", ""),
                "message": entry.get("message", ""),
                "source": entry.get("source", ""),
            })
        return output.getvalue()
    else:
        return f"Unknown format: {fmt}"


def format_entry(entry):
    """Format a single log entry for display."""
    level_icons = {
        "debug": "🔍", "info": "ℹ️", "warning": "⚠️",
        "error": "❌", "critical": "🚨"
    }
    icon = level_icons.get(entry.get("level", "info"), "📝")
    ts = entry.get("timestamp", "")[:19]
    msg = entry.get("message", "")
    source = entry.get("source", "")

    return f"  {icon} [{ts}] [{entry.get('type', '?')}] {msg} (via {source})"


def main():
    parser = argparse.ArgumentParser(description="Activity Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # log
    log = subparsers.add_parser("log", help="Log an activity entry")
    log.add_argument("--type", "-t", required=True, choices=ACTIVITY_TYPES)
    log.add_argument("--message", "-m", required=True)
    log.add_argument("--level", "-l", choices=LEVELS, default="info")
    log.add_argument("--source", "-s", default="cli")
    log.add_argument("--details", "-d", help="JSON details")

    # tail
    tail = subparsers.add_parser("tail", help="View recent entries")
    tail.add_argument("--lines", "-n", type=int, default=20)
    tail.add_argument("--type", "-t", choices=ACTIVITY_TYPES)
    tail.add_argument("--level", "-l", choices=LEVELS)

    # search
    search = subparsers.add_parser("search", help="Search activity log")
    search.add_argument("--query", "-q", required=True)
    search.add_argument("--days", "-d", type=int, default=7)
    search.add_argument("--limit", "-l", type=int, default=20)

    # stats
    st = subparsers.add_parser("stats", help="Show activity statistics")
    st.add_argument("--days", "-d", type=int, default=30)
    st.add_argument("--json", "-j", action="store_true")

    # export
    exp = subparsers.add_parser("export", help="Export activity log")
    exp.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    exp.add_argument("--days", "-d", type=int, default=7)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    init()

    if args.command == "log":
        details = None
        if args.details:
            try:
                details = json.loads(args.details)
            except json.JSONDecodeError:
                details = {"raw": args.details}

        entry = log_activity(args.type, args.message, args.level, args.source, details)
        print(f"✅ Logged: [{args.level}] {args.message}")

    elif args.command == "tail":
        entries = load_entries(activity_type=args.type, level=args.level, limit=args.lines)
        if not entries:
            print("No entries found.")
        else:
            print(f"📋 Activity Log (last {len(entries)})\n" + "=" * 60)
            for entry in entries:
                print(format_entry(entry))

    elif args.command == "search":
        results = search_entries(args.query, args.days, args.limit)
        if not results:
            print(f"No matches for '{args.query}' in last {args.days} days.")
        else:
            print(f"🔍 Search results for '{args.query}' ({len(results)} matches)\n" + "=" * 60)
            for entry in results:
                print(format_entry(entry))

    elif args.command == "stats":
        stats = get_stats(args.days)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"📊 Activity Statistics (last {stats['period_days']} days)")
            print("=" * 60)
            print(f"  Total entries: {stats['total_entries']}")
            print(f"  Errors: {stats['errors']}")
            print(f"  Warnings: {stats['warnings']}")
            print()

            if stats["by_type"]:
                print("  By Type:")
                for t, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
                    print(f"    {t}: {count}")
            print()

            if stats["by_source"]:
                print("  By Source:")
                for s, count in sorted(stats["by_source"].items(), key=lambda x: -x[1])[:10]:
                    print(f"    {s}: {count}")

    elif args.command == "export":
        output = export_entries(args.format, args.days)
        print(output)


if __name__ == "__main__":
    main()
