#!/usr/bin/env python3
"""tracker.py — Social media engagement and metrics tracker.

Usage:
    python tracker.py record --platform twitter --metric followers --value 1234
    python tracker.py record --platform twitter --metric engagement --value 150 --post_id "abc"
    python tracker.py stats [--platform twitter] [--days 7]
    python tracker.py mentions --add "Brand mentioned in article" --source "news site"
    python tracker.py mentions [--search "keyword"]
    python tracker.py export [--format csv|json]
"""

import argparse
import csv
import io
import json
import os
import sys
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "automations/social/tracker.db"
PLATFORMS = ["twitter", "linkedin", "facebook", "instagram", "mastodon"]
METRICS = ["followers", "following", "likes", "comments", "shares",
           "impressions", "clicks", "engagement", "retweets", "saves"]


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            post_id TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            text TEXT NOT NULL,
            author TEXT,
            source TEXT,
            url TEXT,
            sentiment TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            text TEXT,
            media TEXT,
            published_at TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def record_metric(conn, platform, metric, value, post_id=None):
    conn.execute(
        "INSERT INTO metrics_snapshots (platform, metric, value, post_id) VALUES (?, ?, ?, ?)",
        (platform, metric, value, post_id)
    )
    conn.commit()
    return True


def get_stats(conn, platform=None, days=7):
    since = (datetime.now() - timedelta(days=days)).isoformat()

    # Get latest metrics per platform
    query = """
        SELECT platform, metric, value, recorded_at
        FROM metrics_snapshots ms1
        WHERE recorded_at = (
            SELECT MAX(recorded_at) FROM metrics_snapshots ms2
            WHERE ms2.platform = ms1.platform AND ms2.metric = ms1.metric
        )
    """
    params = []

    if platform:
        query += " AND platform = ?"
        params.append(platform)

    rows = conn.execute(query, params).fetchall()

    # Get trend data (change over period)
    trend_query = """
        SELECT platform, metric,
               (SELECT value FROM metrics_snapshots WHERE platform = ms.platform
                AND metric = ms.metric AND recorded_at <= ? ORDER BY recorded_at DESC LIMIT 1) as old_value,
               value as new_value,
               recorded_at as latest_at
        FROM metrics_snapshots ms
        WHERE recorded_at = (
            SELECT MAX(recorded_at) FROM metrics_snapshots ms2
            WHERE ms2.platform = ms.platform AND ms2.metric = ms.metric
        )
    """
    trend_params = [since]
    if platform:
        trend_query += " AND platform = ?"
        trend_params.append(platform)

    trend_rows = conn.execute(trend_query, trend_params).fetchall()

    # Build stats
    stats = {}
    for row in rows:
        p = row["platform"]
        if p not in stats:
            stats[p] = {"metrics": {}, "trends": {}}
        stats[p]["metrics"][row["metric"]] = {
            "value": row["value"],
            "recorded_at": row["recorded_at"]
        }

    for row in trend_rows:
        p = row["platform"]
        m = row["metric"]
        if p in stats:
            old = row["old_value"] or 0
            new = row["new_value"] or 0
            change = new - old
            pct = (change / old * 100) if old > 0 else 0
            stats[p]["trends"][m] = {
                "change": round(change, 1),
                "percent": round(pct, 1),
                "direction": "up" if change > 0 else "down" if change < 0 else "flat"
            }

    return stats


def add_mention(conn, text, platform=None, author=None, source=None, url=None, sentiment=None):
    conn.execute(
        """INSERT INTO mentions (platform, text, author, source, url, sentiment)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (platform, text, author, source, url, sentiment)
    )
    conn.commit()


def list_mentions(conn, search=None, platform=None, limit=20):
    query = "SELECT * FROM mentions WHERE 1=1"
    params = []

    if search:
        query += " AND (text LIKE ? OR author LIKE ? OR source LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if platform:
        query += " AND platform = ?"
        params.append(platform)

    query += " ORDER BY recorded_at DESC LIMIT ?"
    params.append(limit)

    return [dict(r) for r in conn.execute(query, params).fetchall()]


def export_data(conn, fmt="json", platform=None):
    stats = get_stats(conn, platform)
    mentions = list_mentions(conn)

    if fmt == "json":
        return json.dumps({"stats": stats, "mentions": mentions}, indent=2)
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["platform", "metric", "value", "recorded_at"])
        for p, data in stats.items():
            for m, v in data["metrics"].items():
                writer.writerow([p, m, v["value"], v["recorded_at"]])
        return output.getvalue()
    else:
        return f"Unknown format: {fmt}"


def format_stats(stats):
    platform_icons = {
        "twitter": "🐦", "linkedin": "💼", "facebook": "📘",
        "instagram": "📷", "mastodon": "🐘"
    }

    lines = ["📊 Social Media Metrics\n" + "=" * 50]

    for platform, data in sorted(stats.items()):
        icon = platform_icons.get(platform, "📱")
        lines.append(f"\n{icon} {platform.title()}")
        lines.append("-" * 30)

        for metric, info in sorted(data["metrics"].items()):
            value = info["value"]
            recorded = info["recorded_at"][:16]
            trend = data["trends"].get(metric, {})

            if trend.get("direction"):
                arrow = {"up": "📈", "down": "📉", "flat": "➡️"}.get(trend["direction"], "")
                pct = f" ({trend['percent']:+.1f}%)"
            else:
                arrow = ""
                pct = ""

            lines.append(f"  {metric}: {value}{pct} {arrow}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Social Media Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # record
    rec = subparsers.add_parser("record", help="Record a metric snapshot")
    rec.add_argument("--platform", "-p", required=True, choices=PLATFORMS)
    rec.add_argument("--metric", "-m", required=True, choices=METRICS)
    rec.add_argument("--value", "-v", type=float, required=True)
    rec.add_argument("--post-id", help="Associated post ID")

    # stats
    stat = subparsers.add_parser("stats", help="Show current metrics")
    stat.add_argument("--platform", "-p", choices=PLATFORMS)
    stat.add_argument("--days", "-d", type=int, default=7)
    stat.add_argument("--json", "-j", action="store_true")

    # mentions
    mention = subparsers.add_parser("mentions", help="Manage brand mentions")
    mention.add_argument("--add", "-a", help="Add a mention")
    mention.add_argument("--platform", "-p", choices=PLATFORMS)
    mention.add_argument("--search", "-s", help="Search mentions")
    mention.add_argument("--author", help="Author of mention")
    mention.add_argument("--source", help="Source of mention")
    mention.add_argument("--url", help="URL of mention")
    mention.add_argument("--sentiment", choices=["positive", "negative", "neutral"])
    mention.add_argument("--limit", "-l", type=int, default=20)

    # export
    exp = subparsers.add_parser("export", help="Export data")
    exp.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    exp.add_argument("--platform", "-p", choices=PLATFORMS)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = get_db()

    try:
        if args.command == "record":
            record_metric(conn, args.platform, args.metric, args.value, args.post_id)
            print(f"✅ Recorded: {args.platform}/{args.metric} = {args.value}")

        elif args.command == "stats":
            stats = get_stats(conn, args.platform, args.days)
            if args.json:
                print(json.dumps(stats, indent=2))
            elif not stats:
                print("No metrics recorded yet. Use 'record' to add metrics.")
            else:
                print(format_stats(stats))

        elif args.command == "mentions":
            if args.add:
                add_mention(conn, args.add, args.platform, args.author,
                           args.source, args.url, args.sentiment)
                print(f"✅ Mention recorded: {args.add[:60]}...")
            else:
                mentions = list_mentions(conn, args.search, args.platform, args.limit)
                if not mentions:
                    print("No mentions found.")
                else:
                    print(f"📰 Brand Mentions ({len(mentions)})\n" + "=" * 50)
                    for m in mentions:
                        sentiment_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(m.get("sentiment"), "⚪")
                        print(f"  {sentiment_icon} [{m.get('platform', '?')}] {m['text'][:80]}...")
                        if m.get("author"):
                            print(f"     by {m['author']}")
                        if m.get("source"):
                            print(f"     via {m['source']}")
                        print(f"     {m['recorded_at'][:16]}")
                        print()

        elif args.command == "export":
            output = export_data(conn, args.format, args.platform)
            print(output)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
