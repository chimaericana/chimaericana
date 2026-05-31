#!/usr/bin/env python3
"""report.py — Daily/weekly report generator for Projex.

Compiles system health, social metrics, activity summary,
pending tasks, upcoming schedule, and error events.

Usage:
    python report.py daily [--format text|json|html] [--output file]
    python report.py weekly [--format text|json|html] [--output file]
    python report.py custom --type scheduler --days 7
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta

REPORTS_DIR = "automations/observability/reports"


def init():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def read_file(path):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except:
                continue
    return entries


def get_heartbeat_summary():
    entries = read_file("automations/system/heartbeats.jsonl")
    if not entries:
        return {"status": "no_data", "total_checks": 0}

    total = len(entries)
    recent = entries[-10:] if len(entries) >= 10 else entries
    healthy = sum(1 for e in recent if e.get("status") == "healthy")
    warnings = sum(1 for e in recent if e.get("status") == "warning")
    critical = sum(1 for e in recent if e.get("status") == "critical")
    degraded = sum(1 for e in recent if e.get("status") == "degraded")

    last = entries[-1]
    return {
        "status": last.get("status", "unknown"),
        "total_checks": total,
        "recent_healthy": healthy,
        "recent_warnings": warnings,
        "recent_critical": critical,
        "recent_degraded": degraded,
        "last_check": last.get("timestamp", "")[:19],
    }


def get_social_summary():
    summary = {}

    # Scheduler stats
    sched_db = "automations/social/scheduler.db"
    if os.path.exists(sched_db):
        conn = sqlite3.connect(sched_db)
        total = conn.execute("SELECT COUNT(*) FROM scheduled_posts").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM scheduled_posts WHERE status='pending'").fetchone()[0]
        published = conn.execute("SELECT COUNT(*) FROM scheduled_posts WHERE status='published'").fetchone()[0]
        conn.close()
        summary["scheduler"] = {"total": total, "pending": pending, "published": published}

    # Tracker stats
    tracker_db = "automations/social/tracker.db"
    if os.path.exists(tracker_db):
        conn = sqlite3.connect(tracker_db)
        mentions = conn.execute("SELECT COUNT(*) FROM mentions").fetchone()[0]
        metrics = conn.execute("SELECT COUNT(*) FROM metrics_snapshots").fetchone()[0]
        conn.close()
        summary["tracker"] = {"mentions": mentions, "metrics_snapshots": metrics}

    return summary


def get_activity_summary(days=1):
    entries = read_file("automations/observability/activity.jsonl")
    since = datetime.now() - timedelta(days=days)

    recent = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["timestamp"])
            if ts >= since:
                recent.append(e)
        except:
            pass

    by_type = {}
    for e in recent:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    errors = sum(1 for e in recent if e.get("level") in ("error", "critical"))

    return {"total": len(recent), "by_type": by_type, "errors": errors}


def get_recovery_summary():
    entries = read_file("automations/observability/recovery.jsonl")
    if not entries:
        return {"total_events": 0, "failures": 0}

    failures = sum(1 for e in entries if e.get("status") == "failed")
    successes = sum(1 for e in entries if e.get("status") == "success")

    return {
        "total_events": len(entries),
        "failures": failures,
        "successes": successes,
        "last_event": entries[-1].get("timestamp", "")[:19] if entries else None,
    }


def get_trigger_summary():
    config_path = "automations/triggers/triggers.json"
    if not os.path.exists(config_path):
        return {"total_triggers": 0, "enabled": 0}

    with open(config_path) as f:
        config = json.load(f)

    triggers = config.get("triggers", [])
    enabled = sum(1 for t in triggers if t.get("enabled", True))

    return {"total_triggers": len(triggers), "enabled": enabled, "disabled": len(triggers) - enabled}


def get_todo_summary():
    todo_file = "automations/general/todo.jsonl"
    if not os.path.exists(todo_file):
        return {"total": 0, "pending": 0, "done": 0}

    todos = read_file(todo_file)
    pending = sum(1 for t in todos if t.get("status") == "pending")
    done = sum(1 for t in todos if t.get("status") == "done")

    return {"total": len(todos), "pending": pending, "done": done}


def get_alerts_summary():
    alerts = read_file("automations/social/alerts.jsonl")
    recent = alerts[-20:] if len(alerts) > 20 else alerts

    return {
        "total": len(alerts),
        "recent": len(recent),
        "recent_types": list(set(a.get("type", "unknown") for a in recent)),
    }


def generate_daily_report(fmt="text"):
    now = datetime.now()
    report = {
        "type": "daily",
        "generated": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "heartbeat": get_heartbeat_summary(),
        "social": get_social_summary(),
        "activity": get_activity_summary(days=1),
        "recovery": get_recovery_summary(),
        "triggers": get_trigger_summary(),
        "todos": get_todo_summary(),
        "alerts": get_alerts_summary(),
    }

    if fmt == "json":
        return json.dumps(report, indent=2)
    elif fmt == "html":
        return generate_html_report(report)
    else:
        return generate_text_report(report)


def generate_text_report(report):
    lines = []
    lines.append("=" * 60)
    lines.append(f"  PROJEX DAILY REPORT — {report['date']}")
    lines.append(f"  Generated: {report['generated'][:19]}")
    lines.append("=" * 60)
    lines.append("")

    # System Health
    hb = report["heartbeat"]
    hb_icon = {"healthy": "💚", "warning": "⚠️", "critical": "🚨", "degraded": "📶", "no_data": "❓"}.get(hb["status"], "❓")
    lines.append(f"💓 SYSTEM HEALTH {hb_icon}")
    lines.append(f"   Status: {hb['status']}")
    lines.append(f"   Total checks: {hb['total_checks']}")
    lines.append(f"   Recent: {hb.get('recent_healthy', 0)} healthy, {hb.get('recent_warnings', 0)} warnings, {hb.get('recent_critical', 0)} critical")
    lines.append(f"   Last check: {hb.get('last_check', 'N/A')}")
    lines.append("")

    # Social Media
    soc = report["social"]
    lines.append("📊 SOCIAL MEDIA")
    if "scheduler" in soc:
        s = soc["scheduler"]
        lines.append(f"   Posts: {s['total']} total, {s['pending']} pending, {s['published']} published")
    if "tracker" in soc:
        t = soc["tracker"]
        lines.append(f"   Mentions tracked: {t['mentions']}")
        lines.append(f"   Metrics snapshots: {t['metrics_snapshots']}")
    lines.append("")

    # Activity
    act = report["activity"]
    lines.append("📋 ACTIVITY (24h)")
    lines.append(f"   Total events: {act['total']}")
    lines.append(f"   Errors: {act['errors']}")
    if act["by_type"]:
        lines.append("   By type:")
        for t, c in sorted(act["by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"     {t}: {c}")
    lines.append("")

    # Triggers
    trig = report["triggers"]
    lines.append("🔀 TRIGGERS")
    lines.append(f"   Total: {trig['total_triggers']} ({trig['enabled']} enabled, {trig['disabled']} disabled)")
    lines.append("")

    # Recovery
    rec = report["recovery"]
    lines.append("🛡️  RECOVERY")
    lines.append(f"   Total events: {rec['total_events']}")
    lines.append(f"   Successes: {rec['successes']}")
    lines.append(f"   Failures: {rec['failures']}")
    lines.append("")

    # Todos
    todos = report["todos"]
    lines.append("✅ TASKS")
    lines.append(f"   Total: {todos['total']} ({todos['pending']} pending, {todos['done']} done)")
    lines.append("")

    # Alerts
    alerts = report["alerts"]
    lines.append("🔔 ALERTS")
    lines.append(f"   Total: {alerts['total']} ({alerts['recent']} recent)")
    lines.append("")
    lines.append("=" * 60)
    lines.append("  END OF REPORT")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_html_report(report):
    date = report["date"]
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Projex Daily Report — {date}</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f0f0f;color:#e0e0e0;padding:2rem;max-width:800px;margin:0 auto;}}
h1{{font-size:1.5rem;margin-bottom:0.5rem;}}
.meta{{color:#888;font-size:0.85rem;margin-bottom:2rem;}}
.card{{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:1rem;margin-bottom:1rem;}}
.card h2{{margin-top:0;font-size:1.1rem;}}
.stat{{display:flex;justify-content:space-between;padding:0.5rem 0;border-bottom:1px solid #222;}}
.stat:last-child{{border-bottom:none;}}
.label{{color:#888;}}
.value{{font-weight:600;}}
.good{{color:#22c55e;}}.warn{{color:#eab308;}}.bad{{color:#ef4444;}}
</style></head><body>
<h1>📊 Projex Daily Report</h1>
<div class="meta">{date} · Generated {report['generated'][:19]}</div>
<div class="card"><h2>💓 System Health</h2>
<div class="stat"><span class="label">Status</span><span class="value {'good' if report['heartbeat']['status']=='healthy' else 'bad'}">{report['heartbeat']['status']}</span></div>
<div class="stat"><span class="label">Total Checks</span><span class="value">{report['heartbeat']['total_checks']}</span></div>
<div class="stat"><span class="label">Last Check</span><span class="value">{report['heartbeat'].get('last_check','N/A')}</span></div>
</div>
<div class="card"><h2>📊 Social Media</h2>
<div class="stat"><span class="label">Posts Total</span><span class="value">{report['social'].get('scheduler',{}).get('total',0)}</span></div>
<div class="stat"><span class="label">Pending</span><span class="value">{report['social'].get('scheduler',{}).get('pending',0)}</span></div>
<div class="stat"><span class="label">Mentions</span><span class="value">{report['social'].get('tracker',{}).get('mentions',0)}</span></div>
</div>
<div class="card"><h2>📋 Activity (24h)</h2>
<div class="stat"><span class="label">Total Events</span><span class="value">{report['activity']['total']}</span></div>
<div class="stat"><span class="label">Errors</span><span class="value {'bad' if report['activity']['errors']>0 else 'good'}">{report['activity']['errors']}</span></div>
</div>
<div class="card"><h2>✅ Tasks</h2>
<div class="stat"><span class="label">Total</span><span class="value">{report['todos']['total']}</span></div>
<div class="stat"><span class="label">Pending</span><span class="value">{report['todos']['pending']}</span></div>
<div class="stat"><span class="label">Done</span><span class="value good">{report['todos']['done']}</span></div>
</div>
</body></html>"""


def save_report(content, report_type="daily", fmt="text"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = {"text": "txt", "json": "json", "html": "html"}.get(fmt, "txt")
    filename = f"{REPORTS_DIR}/{report_type}_{timestamp}.{ext}"
    with open(filename, "w") as f:
        f.write(content)
    return filename


def main():
    parser = argparse.ArgumentParser(description="Report Generator")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # daily
    daily = subparsers.add_parser("daily", help="Generate daily report")
    daily.add_argument("--format", "-f", choices=["text", "json", "html"], default="text")
    daily.add_argument("--output", "-o", help="Output file path")
    daily.add_argument("--notify", "-n", action="store_true", help="Send via notification")

    # weekly
    weekly = subparsers.add_parser("weekly", help="Generate weekly report")
    weekly.add_argument("--format", "-f", choices=["text", "json", "html"], default="text")
    weekly.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    init()

    report = generate_daily_report(args.format)

    if args.output:
        filename = save_report(report, args.command, args.format)
        print(f"✅ Report saved: {filename}")
    else:
        print(report)


if __name__ == "__main__":
    main()
