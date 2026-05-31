#!/data/data/com.termux/files/usr/bin/python3
"""Aware Activity Tracker — records every engagement, response, and channel touchpoint.

Tracks:
- When engagements are sent (per channel)
- When responses come back
- Engagement rates per agent, per channel, per time period
- Weekly/monthly trend reports
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

AWARE_DIR = os.path.expanduser("~/Athena/aware")
TRACKER_FILE = os.path.join(AWARE_DIR, "activity_log.jsonl")
STATE_FILE = os.path.join(AWARE_DIR, "state.json")
os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def log_engagement(agent_id: str, prompt_type: str, channel: str, content: str,
                   scheduled_time: str = None, status: str = "sent"):
    """Log an engagement sent through any channel."""
    entry = {
        "type": "engagement_sent",
        "agent": agent_id,
        "prompt_type": prompt_type,
        "channel": channel,
        "content_preview": content[:120],
        "scheduled_time": scheduled_time or now_iso(),
        "sent_time": now_iso(),
        "status": status,
        "responded": False,
        "response_time": None,
        "engagement_id": f"{agent_id}_{prompt_type}_{channel}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    with open(TRACKER_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["engagement_id"]


def log_response(engagement_id: str, response_text: str, channel: str):
    """Log a response to a previous engagement."""
    entry = {
        "type": "response_received",
        "engagement_id": engagement_id,
        "channel": channel,
        "response_preview": response_text[:200],
        "response_time": now_iso(),
    }
    with open(TRACKER_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Also update the original engagement to mark as responded
    update_engagement(engagement_id, {"responded": True, "response_time": now_iso()})


def log_content_posted(agent_id: str, platform: str, content_type: str, url: str = None):
    """Log when content is posted to a platform."""
    entry = {
        "type": "content_posted",
        "agent": agent_id,
        "platform": platform,
        "content_type": content_type,
        "url": url or "",
        "posted_time": now_iso(),
    }
    with open(TRACKER_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_channel_status(channel: str, status: str, detail: str = ""):
    """Log channel availability status."""
    entry = {
        "type": "channel_status",
        "channel": channel,
        "status": status,
        "detail": detail,
        "timestamp": now_iso(),
    }
    with open(TRACKER_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def update_engagement(engagement_id: str, updates: dict):
    """Update fields on an existing engagement entry."""
    entries = []
    found = False
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("engagement_id") == engagement_id:
                    entry.update(updates)
                    found = True
                entries.append(entry)

    with open(TRACKER_FILE, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return found


def get_stats(days: int = 7, agent: str = None, channel: str = None):
    """Get engagement statistics for a time period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    totals = {
        "engagements_sent": 0,
        "responses": 0,
        "content_posted": 0,
        "by_agent": defaultdict(int),
        "by_channel": defaultdict(int),
        "by_prompt_type": defaultdict(int),
        "by_day": defaultdict(int),
        "response_rate": 0.0,
    }

    if not os.path.exists(TRACKER_FILE):
        return totals

    with open(TRACKER_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            entry_time = entry.get("sent_time") or entry.get("timestamp") or entry.get("response_time", "")
            try:
                et = datetime.fromisoformat(entry_time)
            except (ValueError, TypeError):
                continue
            if et < cutoff:
                continue

            etype = entry.get("type", "")

            if etype == "engagement_sent":
                if agent and entry.get("agent") != agent:
                    continue
                if channel and entry.get("channel") != channel:
                    continue
                totals["engagements_sent"] += 1
                totals["by_agent"][entry.get("agent", "unknown")] += 1
                totals["by_channel"][entry.get("channel", "unknown")] += 1
                totals["by_prompt_type"][entry.get("prompt_type", "unknown")] += 1
                totals["by_day"][entry.get("sent_time", "")[:10]] += 1
                if entry.get("responded"):
                    totals["responses"] += 1

            elif etype == "response_received":
                if agent and not any(1 for e in [entry] if e.get("engagement_id", "").startswith(agent)):
                    continue
                if channel and entry.get("channel") != channel:
                    continue
                totals["responses"] += 1

            elif etype == "content_posted":
                if agent and entry.get("agent") != agent:
                    continue
                totals["content_posted"] += 1

    if totals["engagements_sent"] > 0:
        totals["response_rate"] = round(totals["responses"] / totals["engagements_sent"] * 100, 1)

    return totals


def print_stats(days: int = 7):
    """Print a formatted stats report."""
    stats = get_stats(days)

    print(f"\n📊 ENGAGEMENT STATISTICS — Last {days} Days")
    print("=" * 50)
    print(f"  Engagements Sent:  {stats['engagements_sent']}")
    print(f"  Responses:         {stats['responses']}")
    print(f"  Response Rate:     {stats['response_rate']}%")
    print(f"  Content Posted:    {stats['content_posted']}")
    print()
    print("  By Agent:")
    for agent, count in sorted(stats['by_agent'].items(), key=lambda x: -x[1]):
        pct = round(count / stats['engagements_sent'] * 100, 1) if stats['engagements_sent'] else 0
        print(f"    {agent:12s} {count:4d} ({pct}%)")
    print()
    print("  By Channel:")
    for ch, count in sorted(stats['by_channel'].items(), key=lambda x: -x[1]):
        print(f"    {ch:15s} {count:4d}")
    print()
    print("  By Prompt Type:")
    for pt, count in sorted(stats['by_prompt_type'].items(), key=lambda x: -x[1]):
        print(f"    {pt:15s} {count:4d}")
    print()
    print("  By Day:")
    for day, count in sorted(stats['by_day'].items()):
        print(f"    {day}  {count:4d}")


def print_trend_report():
    """Generate a trend report comparing this week to last week."""
    this_week = get_stats(7)
    last_week = get_stats(14)  # Days 8-14

    # Subtract this week from last 14 days to get last week proper
    for key in ["engagements_sent", "responses", "content_posted"]:
        last_week[key] = max(0, last_week[key] - this_week[key])

    # Same for by_agent
    for agent in list(last_week["by_agent"].keys()):
        last_week["by_agent"][agent] = max(0, last_week["by_agent"].get(agent, 0) - this_week["by_agent"].get(agent, 0))
        if last_week["by_agent"][agent] == 0:
            del last_week["by_agent"][agent]

    print("\n📈 ENGAGEMENT TRENDS — This Week vs Last Week")
    print("=" * 50)
    
    def trend(current, previous):
        if previous == 0:
            return "NEW" if current > 0 else "—"
        change = round((current - previous) / previous * 100, 1)
        if change > 0:
            return f"▲ +{change}%"
        elif change < 0:
            return f"▼ {change}%"
        return "—"

    print(f"  Engagements:      {this_week['engagements_sent']:4d} ({trend(this_week['engagements_sent'], last_week['engagements_sent'])})")
    print(f"  Responses:        {this_week['responses']:4d} ({trend(this_week['responses'], last_week['responses'])})")
    print(f"  Response Rate:    {this_week['response_rate']}%")
    print(f"  Content Posted:   {this_week['content_posted']:4d} ({trend(this_week['content_posted'], last_week['content_posted'])})")

    if this_week["by_agent"]:
        print("\n  Agent Trends:")
        for agent in sorted(set(list(this_week["by_agent"].keys()) + list(last_week["by_agent"].keys()))):
            tw = this_week["by_agent"].get(agent, 0)
            lw = last_week["by_agent"].get(agent, 0)
            print(f"    {agent:12s} {tw:4d} ({trend(tw, lw)})")


def interactive():
    """Interactive CLI for tracking."""
    if len(sys.argv) < 2:
        print("Usage: tracker.py <command> [args]")
        print("Commands:")
        print("  log      <agent> <prompt_type> <channel> <content>")
        print("  respond  <engagement_id> <response> <channel>")
        print("  posted   <agent> <platform> <content_type> [url]")
        print("  stats    [days] [agent] [channel]")
        print("  trends")
        print("  status")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "log" and len(sys.argv) >= 5:
        eid = log_engagement(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
        print(f"✅ Engagement logged: {eid}")

    elif cmd == "respond" and len(sys.argv) >= 4:
        log_response(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "discord")
        print(f"✅ Response logged for {sys.argv[2]}")

    elif cmd == "posted" and len(sys.argv) >= 4:
        url = sys.argv[4] if len(sys.argv) > 4 else None
        log_content_posted(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "post", url)
        print(f"✅ Content posted logged")

    elif cmd == "stats":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        agent = sys.argv[3] if len(sys.argv) > 3 else None
        channel = sys.argv[4] if len(sys.argv) > 4 else None
        s = get_stats(days, agent, channel)
        print(json.dumps(s, indent=2, default=str))

    elif cmd == "trends":
        print_trend_report()

    elif cmd == "status":
        print_stats(7)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    interactive()
