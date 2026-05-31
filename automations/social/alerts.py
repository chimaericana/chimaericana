#!/usr/bin/env python3
"""alerts.py — Social media engagement alert system.

Monitors for:
- High-engagement posts
- Negative sentiment spikes
- Trending mentions
- Influencer interactions
- Follower milestone changes

Usage:
    python alerts.py check
    python alerts.py config [--set key value]
    python alerts.py history [--limit 20]
    python alerts.py test
"""

import argparse
import json
import os
import sys
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "automations/social/tracker.db"
ALERTS_LOG = "automations/social/alerts.jsonl"
CONFIG_FILE = "automations/social/alerts_config.json"

DEFAULT_CONFIG = {
    "high_engagement_threshold": 100,
    "negative_sentiment_threshold": 3,
    "follower_milestone_interval": 1000,
    "check_interval_minutes": 30,
    "enabled": {
        "high_engagement": True,
        "negative_sentiment": True,
        "trending_mentions": True,
        "follower_milestone": True,
        "influencer_interaction": False
    }
}


def get_config():
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_FILE) as f:
        return json.load(f)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def log_alert(alert_type, message, severity="info", details=None):
    os.makedirs(os.path.dirname(ALERTS_LOG), exist_ok=True)
    entry = {
        "type": alert_type,
        "message": message,
        "severity": severity,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    with open(ALERTS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def check_high_engagement(conn, config):
    """Check for posts exceeding engagement threshold."""
    if not config["enabled"].get("high_engagement", True):
        return []

    threshold = config.get("high_engagement_threshold", 100)

    # Check posts with high total engagement
    rows = conn.execute("""
        SELECT platform, id, text,
               (COALESCE(likes,0) + COALESCE(comments,0) + COALESCE(shares,0)) as total_engagement
        FROM posts
        WHERE (COALESCE(likes,0) + COALESCE(comments,0) + COALESCE(shares,0)) >= ?
        ORDER BY total_engagement DESC
    """, (threshold,)).fetchall()

    alerts = []
    for row in rows:
        alert = log_alert(
            "high_engagement",
            f"🔥 High engagement post on {row['platform']}: {row['total_engagement']} interactions",
            "alert",
            {"platform": row["platform"], "post_id": row["id"], "engagement": row["total_engagement"]}
        )
        alerts.append(alert)

    return alerts


def check_negative_sentiment(conn, config):
    """Check for negative sentiment spikes in mentions."""
    if not config["enabled"].get("negative_sentiment", True):
        return []

    threshold = config.get("negative_sentiment_threshold", 3)
    since = (datetime.now() - timedelta(hours=24)).isoformat()

    # Count negative mentions in last 24h
    count = conn.execute("""
        SELECT COUNT(*) FROM mentions
        WHERE sentiment = 'negative' AND recorded_at >= ?
    """, (since,)).fetchone()[0]

    alerts = []
    if count >= threshold:
        alert = log_alert(
            "negative_sentiment_spike",
            f"⚠️ {count} negative mentions in last 24h (threshold: {threshold})",
            "urgent",
            {"count": count, "threshold": threshold, "period": "24h"}
        )
        alerts.append(alert)

    return alerts


def check_follower_milestones(conn, config):
    """Check for follower milestone achievements."""
    if not config["enabled"].get("follower_milestone", True):
        return []

    interval = config.get("follower_milestone_interval", 1000)

    # Get current and previous follower counts
    rows = conn.execute("""
        SELECT platform, value, recorded_at
        FROM metrics_snapshots
        WHERE metric = 'followers'
        ORDER BY platform, recorded_at DESC
    """).fetchall()

    alerts = []
    platform_latest = {}
    for row in rows:
        p = row["platform"]
        if p not in platform_latest:
            platform_latest[p] = row["value"]

    for platform, current in platform_latest.items():
        milestone = int(current // interval) * interval
        prev_milestone = milestone - interval

        # Check if we crossed a milestone recently
        prev_row = conn.execute("""
            SELECT value FROM metrics_snapshots
            WHERE platform = ? AND metric = 'followers'
            AND recorded_at < datetime('now', '-1 hour')
            ORDER BY recorded_at DESC LIMIT 1
        """, (platform,)).fetchone()

        if prev_row and prev_row["value"] < milestone <= current:
            alert = log_alert(
                "follower_milestone",
                f"🎉 {platform.title()} reached {milestone} followers!",
                "info",
                {"platform": platform, "milestone": milestone, "current": current}
            )
            alerts.append(alert)

    return alerts


def check_trending_mentions(conn, config):
    """Check for sudden increase in mention volume."""
    if not config["enabled"].get("trending_mentions", True):
        return []

    # Compare last hour to previous hour
    recent = conn.execute("""
        SELECT COUNT(*) FROM mentions
        WHERE recorded_at >= datetime('now', '-1 hour')
    """).fetchone()[0]

    previous = conn.execute("""
        SELECT COUNT(*) FROM mentions
        WHERE recorded_at >= datetime('now', '-2 hours')
        AND recorded_at < datetime('now', '-1 hour')
    """).fetchone()[0]

    alerts = []
    if recent > 0 and previous > 0 and recent >= previous * 3:
        alert = log_alert(
            "trending_mentions",
            f"📈 Mention spike: {recent} in last hour vs {previous} previous ({recent/previous:.1f}x increase)",
            "alert",
            {"recent": recent, "previous": previous, "multiplier": round(recent/previous, 1)}
        )
        alerts.append(alert)

    return alerts


def check_all(conn=None):
    """Run all alert checks."""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    config = get_config()
    all_alerts = []

    all_alerts.extend(check_high_engagement(conn, config))
    all_alerts.extend(check_negative_sentiment(conn, config))
    all_alerts.extend(check_follower_milestones(conn, config))
    all_alerts.extend(check_trending_mentions(conn, config))

    if close_conn:
        conn.close()

    return all_alerts


def get_alert_history(limit=20):
    if not os.path.exists(ALERTS_LOG):
        return []

    alerts = []
    with open(ALERTS_LOG) as f:
        for line in f:
            try:
                alerts.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    return alerts[-limit:]


def format_alerts(alerts):
    severity_icons = {
        "urgent": "🚨",
        "alert": "⚠️",
        "info": "ℹ️",
        "warning": "⚠️"
    }

    if not alerts:
        return "✅ No alerts triggered."

    lines = ["🔔 Social Media Alerts\n" + "=" * 50]
    for alert in alerts:
        icon = severity_icons.get(alert.get("severity", "info"), "📱")
        ts = alert.get("timestamp", "")[:16]
        lines.append(f"{icon} [{ts}] {alert['message']}")
        if alert.get("details"):
            for k, v in alert["details"].items():
                lines.append(f"   {k}: {v}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Social Media Alert System")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # check
    subparsers.add_parser("check", help="Run all alert checks")

    # config
    cfg = subparsers.add_parser("config", help="View or update alert config")
    cfg.add_argument("--set", "-s", nargs=2, metavar=("KEY", "VALUE"), action="append")

    # history
    hist = subparsers.add_parser("history", help="View alert history")
    hist.add_argument("--limit", "-l", type=int, default=20)
    hist.add_argument("--json", "-j", action="store_true")

    # test
    subparsers.add_parser("test", help="Send test alerts")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "check":
        alerts = check_all()
        print(format_alerts(alerts))
        print(f"\n{len(alerts)} alert(s) triggered.")

    elif args.command == "config":
        config = get_config()
        if args.set:
            for key, value in args.set:
                # Handle nested keys like enabled.high_engagement
                if "." in key:
                    parts = key.split(".")
                    current = config
                    for p in parts[:-1]:
                        current = current[p]
                    current[parts[-1]] = value
                else:
                    config[key] = value

            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            print("✅ Config updated")

        print("⚙️  Alert Configuration:")
        print(json.dumps(config, indent=2))

    elif args.command == "history":
        alerts = get_alert_history(args.limit)
        if args.json:
            print(json.dumps(alerts, indent=2))
        else:
            print(format_alerts(alerts))

    elif args.command == "test":
        # Generate test alerts
        log_alert("test_high_engagement", "🔥 Test: Post reached 500 engagements on Twitter", "alert",
                  {"platform": "twitter", "engagement": 500})
        log_alert("test_negative", "⚠️ Test: 5 negative mentions detected", "urgent",
                  {"count": 5})
        log_alert("test_milestone", "🎉 Test: LinkedIn reached 10K followers!", "info",
                  {"platform": "linkedin", "milestone": 10000})

        print("🧪 Test alerts sent. Check history with: python alerts.py history")


if __name__ == "__main__":
    main()
