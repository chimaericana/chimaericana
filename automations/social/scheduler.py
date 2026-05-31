#!/usr/bin/env python3
"""scheduler.py — Social media post scheduler with JSON queue.

Usage:
    python scheduler.py add --platform twitter --text "Hello" --schedule "2026-05-28 09:00"
    python scheduler.py queue [--platform twitter] [--status pending]
    python scheduler.py publish <id>
    python scheduler.py cancel <id>
    python scheduler.py stats
"""

import argparse
import json
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "automations/social/scheduler.db"
PLATFORMS = ["twitter", "linkedin", "facebook", "instagram", "mastodon"]
STATUSES = ["pending", "published", "failed", "cancelled"]


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            text TEXT NOT NULL,
            media TEXT,
            scheduled_at TEXT,
            status TEXT DEFAULT 'pending',
            published_at TEXT,
            error TEXT,
            campaign TEXT,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON scheduled_posts(status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_scheduled ON scheduled_posts(scheduled_at)
    """)
    conn.commit()
    return conn


def generate_id():
    return f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"


def add_post(conn, platform, text, scheduled_at=None, media=None, campaign=None, tags=None):
    if platform not in PLATFORMS:
        print(f"Error: Unknown platform '{platform}'. Choose from: {', '.join(PLATFORMS)}", file=sys.stderr)
        sys.exit(1)

    post_id = generate_id()
    if scheduled_at is None:
        scheduled_at = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO scheduled_posts (id, platform, text, media, scheduled_at, campaign, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (post_id, platform, text, media, scheduled_at, campaign, json.dumps(tags or []))
    )
    conn.commit()
    return post_id


def list_posts(conn, platform=None, status=None, limit=20):
    query = "SELECT * FROM scheduled_posts WHERE 1=1"
    params = []

    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY scheduled_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def publish_post(conn, post_id):
    row = conn.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        print(f"Error: Post '{post_id}' not found", file=sys.stderr)
        return False

    if row["status"] != "pending":
        print(f"Error: Post '{post_id}' is already {row['status']}", file=sys.stderr)
        return False

    # TODO: Actual API publishing would go here
    # For now, mark as published
    conn.execute(
        "UPDATE scheduled_posts SET status = 'published', published_at = datetime('now') WHERE id = ?",
        (post_id,)
    )
    conn.commit()
    return True


def cancel_post(conn, post_id):
    row = conn.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        print(f"Error: Post '{post_id}' not found", file=sys.stderr)
        return False

    if row["status"] != "pending":
        print(f"Error: Cannot cancel post that is {row['status']}", file=sys.stderr)
        return False

    conn.execute("UPDATE scheduled_posts SET status = 'cancelled' WHERE id = ?", (post_id,))
    conn.commit()
    return True


def get_stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM scheduled_posts").fetchone()[0]
    by_status = {}
    for status in STATUSES:
        count = conn.execute("SELECT COUNT(*) FROM scheduled_posts WHERE status = ?", (status,)).fetchone()[0]
        by_status[status] = count
    by_platform = {}
    for platform in PLATFORMS:
        count = conn.execute("SELECT COUNT(*) FROM scheduled_posts WHERE platform = ?", (platform,)).fetchone()[0]
        if count > 0:
            by_platform[platform] = count

    return {"total": total, "by_status": by_status, "by_platform": by_platform}


def check_due_posts(conn):
    """Check for posts that are due and should be published."""
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= ?",
        (now,)
    ).fetchall()

    due = []
    for row in rows:
        due.append(dict(row))

    return due


def format_post(post):
    platform_icons = {
        "twitter": "🐦",
        "linkedin": "💼",
        "facebook": "📘",
        "instagram": "📷",
        "mastodon": "🐘"
    }
    status_icons = {
        "pending": "⏳",
        "published": "✅",
        "failed": "❌",
        "cancelled": "⛔"
    }

    icon = platform_icons.get(post["platform"], "📱")
    status_icon = status_icons.get(post["status"], "❓")

    lines = []
    lines.append(f"  {status_icon} {icon} [{post['platform']}] {post['id']}")
    text_preview = post["text"][:100] + ("..." if len(post["text"]) > 100 else "")
    lines.append(f"     {text_preview}")
    lines.append(f"     📅 {post['scheduled_at']}")
    if post.get("campaign"):
        lines.append(f"     📁 Campaign: {post['campaign']}")
    tags = json.loads(post["tags"]) if post["tags"] else []
    if tags:
        lines.append(f"     🏷️  {', '.join(tags)}")
    if post["status"] == "published" and post.get("published_at"):
        lines.append(f"     ✅ Published: {post['published_at']}")
    if post["status"] == "failed" and post.get("error"):
        lines.append(f"     ❌ Error: {post['error']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Social Media Post Scheduler")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # add
    add_parser = subparsers.add_parser("add", help="Schedule a new post")
    add_parser.add_argument("--platform", "-p", required=True, choices=PLATFORMS)
    add_parser.add_argument("--text", "-t", required=True, help="Post text content")
    add_parser.add_argument("--schedule", "-s", help="Schedule time (ISO format or 'YYYY-MM-DD HH:MM')")
    add_parser.add_argument("--media", "-m", help="Media file path or URL")
    add_parser.add_argument("--campaign", "-c", help="Campaign name")
    add_parser.add_argument("--tags", nargs="*", help="Tags for categorization")

    # queue
    queue_parser = subparsers.add_parser("queue", help="List scheduled posts")
    queue_parser.add_argument("--platform", "-p", choices=PLATFORMS)
    queue_parser.add_argument("--status", choices=STATUSES, default="pending")
    queue_parser.add_argument("--limit", "-l", type=int, default=20)
    queue_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # publish
    pub_parser = subparsers.add_parser("publish", help="Publish a scheduled post now")
    pub_parser.add_argument("id", help="Post ID")

    # cancel
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a scheduled post")
    cancel_parser.add_argument("id", help="Post ID")

    # stats
    subparsers.add_parser("stats", help="Show scheduler statistics")

    # due
    subparsers.add_parser("due", help="Check for posts that are due for publishing")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = get_db()

    try:
        if args.command == "add":
            post_id = add_post(
                conn, args.platform, args.text, args.schedule,
                args.media, args.campaign, args.tags
            )
            scheduled = args.schedule or "now"
            print(f"✅ Post scheduled: {post_id}")
            print(f"   Platform: {args.platform}")
            print(f"   Scheduled: {scheduled}")
            if args.campaign:
                print(f"   Campaign: {args.campaign}")

        elif args.command == "queue":
            posts = list_posts(conn, args.platform, args.status, args.limit)
            if args.json:
                print(json.dumps(posts, indent=2))
            elif not posts:
                print(f"No {args.status} posts found" + (f" for {args.platform}" if args.platform else ""))
            else:
                print(f"📋 Scheduled Posts ({args.status}" + (f", {args.platform}" if args.platform else "") + ")\n" + "=" * 50)
                for post in posts:
                    print(format_post(post))
                    print()

        elif args.command == "publish":
            if publish_post(conn, args.id):
                print(f"✅ Published: {args.id}")
            else:
                sys.exit(1)

        elif args.command == "cancel":
            if cancel_post(conn, args.id):
                print(f"⛔ Cancelled: {args.id}")
            else:
                sys.exit(1)

        elif args.command == "stats":
            stats = get_stats(conn)
            print("📊 Scheduler Statistics")
            print("=" * 50)
            print(f"Total posts: {stats['total']}")
            print()
            print("By Status:")
            for status, count in stats["by_status"].items():
                if count > 0:
                    print(f"  {status}: {count}")
            print()
            print("By Platform:")
            for platform, count in stats["by_platform"].items():
                print(f"  {platform}: {count}")

        elif args.command == "due":
            due = check_due_posts(conn)
            if due:
                print(f"⏰ {len(due)} posts due for publishing:")
                for post in due:
                    print(format_post(post))
                    print()
            else:
                print("✅ No posts due for publishing")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
