#!/data/data/com.termux/files/usr/bin/python3
"""Aware Orchestrator — the central engine that coordinates scheduling, agent
engagement generation, multi-channel delivery, and activity tracking.

This is the brain that makes the system proactively reach out through
Discord, SMS, notifications, email, and direct prompts — through the
personalities of Nexus, Echo, Press, Shield, and Signal.
"""

import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

AWARE_DIR = os.path.expanduser("~/Athena/aware")
STATE_FILE = os.path.join(AWARE_DIR, "state.json")
SCHEDULER_FILE = os.path.join(AWARE_DIR, "scheduler.json")
SCHEDULE_RUNS_FILE = os.path.join(AWARE_DIR, "schedule_runs.json")
CHANNELS_PY = os.path.expanduser("~/Athena/automations/aware/channels.py")
TRACKER_PY = os.path.expanduser("~/Athena/automations/aware/tracker.py")
ENGAGE_PY = os.path.expanduser("~/Athena/automations/aware/engage.py")
PROMPTS_DIR = os.path.join(AWARE_DIR, "prompts")

os.makedirs(AWARE_DIR, exist_ok=True)

# Prompt types that are QUESTIONS — they need user input, route to Discord only
QUESTION_TYPES = {
    "morning", "evening", "checkin", "reflect", "spark",
}

# Prompt types that are INFORMATIONAL UPDATES — no reply needed, route to notifications only
UPDATE_TYPES = {
    "digest", "notice", "publish",
}

# Agent definitions with their personalities and default channel preferences.
# NOTE: The orchestrator's generate_engagement() overrides these per-prompt-type
# based on QUESTION_TYPES vs UPDATE_TYPES — agents' default "channels" here are
# just fallbacks for ad-hoc / unclassified prompt types.
AGENTS = {
    "nexus": {
        "name": "Nexus",
        "emoji": "🎯",
        "role": "Communications Coordinator",
        "channels": ["discord"],
        "tone": "clear, structured, decisive",
        "signoff": "— Nexus",
    },
    "echo": {
        "name": "Echo",
        "emoji": "📣",
        "role": "Social Media Manager",
        "channels": ["discord"],
        "tone": "conversational, platform-native, engaging",
        "signoff": "— Echo 📣",
    },
    "press": {
        "name": "Press",
        "emoji": "📰",
        "role": "PR Specialist",
        "channels": ["discord"],
        "tone": "professional, articulate, newsworthy",
        "signoff": "— Press 📰",
    },
    "shield": {
        "name": "Shield",
        "emoji": "🛡️",
        "role": "Crisis Communications",
        "channels": ["discord", "notify"],
        "tone": "calm, measured, transparent",
        "signoff": "— Shield 🛡️",
    },
    "signal": {
        "name": "Signal",
        "emoji": "📡",
        "role": "Media Relations",
        "channels": ["discord"],
        "tone": "professional, warm, relationship-focused",
        "signoff": "— Signal 📡",
    },
    "aware": {
        "name": "Aware",
        "emoji": "🧠",
        "role": "Life Engagement System",
        "channels": ["discord"],
        "tone": "thoughtful, observant, encouraging",
        "signoff": "— Aware 🧠",
    },
}

# Cadence definitions for day/week/month scheduling.
#
# CHANNEL RULES (enforced by orchestrator, repeated here for schedule authoring reference):
#   QUESTION prompts (morning, evening, checkin, reflect, spark) → Discord ONLY
#   UPDATE prompts  (digest, notice, publish)                   → Notification ONLY
#   NEVER send questions through notifications.
#   NEVER send general updates through Discord.
#
# "direct" means Pi sees it in-conversation (always safe, no side effects).
CADENCES = {
    "daily": [
        # morning = question → discord
        {"time": "09:00", "agent": "aware", "type": "morning", "channels": ["discord"]},
        # spark = question → discord
        {"time": "12:00", "agent": "echo", "type": "spark", "channels": ["discord"]},
        # evening = question → discord
        {"time": "18:00", "agent": "aware", "type": "evening", "channels": ["discord"]},
        # digest = update → notification
        {"time": "21:00", "agent": "nexus", "type": "digest", "channels": ["notify"]},
    ],
    "weekly": {
        "monday": [
            # checkin = question → discord
            {"time": "10:00", "agent": "aware", "type": "checkin", "channels": ["discord"]},
            # spark = question → discord
            {"time": "14:00", "agent": "echo", "type": "spark", "channels": ["discord"]},
        ],
        "tuesday": [
            # publish = update → notification
            {"time": "11:00", "agent": "press", "type": "publish", "channels": ["notify"]},
        ],
        "wednesday": [
            # reflect = question → discord
            {"time": "10:00", "agent": "nexus", "type": "reflect", "channels": ["discord"]},
            # notice = update → notification
            {"time": "15:00", "agent": "signal", "type": "notice", "channels": ["notify"]},
        ],
        "thursday": [
            # publish = update → notification
            {"time": "11:00", "agent": "echo", "type": "publish", "channels": ["notify"]},
        ],
        "friday": [
            # checkin = question → discord
            {"time": "10:00", "agent": "aware", "type": "checkin", "channels": ["discord"]},
            # spark = question → discord
            {"time": "16:00", "agent": "echo", "type": "spark", "channels": ["discord"]},
        ],
        "saturday": [
            # reflect = question → discord
            {"time": "11:00", "agent": "aware", "type": "reflect", "channels": ["discord"]},
        ],
        "sunday": [
            # digest = update → notification
            {"time": "10:00", "agent": "nexus", "type": "digest", "channels": ["notify"]},
            # reflect = question → discord
            {"time": "18:00", "agent": "aware", "type": "reflect", "channels": ["discord"]},
        ],
    },
    "monthly": {
        "1": [
            # reflect = question → discord
            {"time": "10:00", "agent": "aware", "type": "reflect", "channels": ["discord"]},
            # digest = update → notification
            {"time": "14:00", "agent": "nexus", "type": "digest", "channels": ["notify"]},
        ],
        "15": [
            # checkin = question → discord
            {"time": "10:00", "agent": "echo", "type": "checkin", "channels": ["discord"]},
            # publish = update → notification
            {"time": "14:00", "agent": "press", "type": "publish", "channels": ["notify"]},
        ],
    },
}

# Template prompts per agent/type combination
PROMPT_TEMPLATES = {
    "aware_morning": [
        "Good morning. What's the one thing you want to make true today? I'm here to help you follow through.",
        "Morning check: What kind of energy are you working with today? Let me know and I'll match the vibe.",
    ],
    "aware_evening": [
        "How did today land for you? What's one win and one thing you'd carry differently into tomorrow?",
        "Evening reflection: What moment from today would you want to remember? I've logged our activity and patterns are forming.",
    ],
    "aware_checkin": [
        "I've been tracking our interactions. How are your goals feeling this week? On track, stalled, or shifted?",
        "Weekly pulse: What's the one thing that, if you focused on it, would make everything else feel easier?",
    ],
    "aware_reflect": [
        "What chapter of your life are you in right now? Give it a title — the answer reveals more than you'd expect.",
        "You've been journaling for a while now. What pattern have you noticed that surprised you?",
    ],
    "nexus_morning": [
        "🎯 Nexus here. All communication channels are online. I've queued today's prompts based on your preferences. What's our priority today?",
    ],
    "nexus_digest": [
        "🎯 **Nexus Digest** — Here's what I'm tracking:\n{stats}\n\n{insight}",
    ],
    "nexus_reflect": [
        "🎯 Nexus routing report: Our engagement patterns show {pattern}. Worth noticing?",
    ],
    "echo_spark": [
        "📣 **Echo here.** I've been watching the patterns. Here's a thought: {spark}\n\nWant me to turn this into something publishable?",
    ],
    "echo_publish": [
        "📣 **Content opportunity detected.** You've had {count} notable reflections this week. Want me to compile them into posts? I can handle Twitter, LinkedIn, or whatever format you want.",
    ],
    "press_publish": [
        "📰 **Press here.** I've been tracking your insights. There's a narrative forming around {theme}. Want me to draft something?",
    ],
    "signal_notice": [
        "📡 **Signal check.** What conversations or interactions stood out to you this week? Sometimes the small dynamics carry the most signal.",
    ],
    "shield_checkin": [
        "🛡️ **Shield scanning.** I monitor for friction. Anything feeling off or stuck? Even a small irritant is worth flagging.",
    ],
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def now():
    return datetime.now()


def current_hour_min():
    return now().strftime("%H:%M")


def day_of_week():
    return now().strftime("%A").lower()


def day_of_month():
    return now().day


# ══════════════════════════════════════════════════════════════
# SCHEDULE ENGINE
# ══════════════════════════════════════════════════════════════

def load_schedule_runs():
    """Load record of which schedule items have been triggered."""
    if os.path.exists(SCHEDULE_RUNS_FILE):
        with open(SCHEDULE_RUNS_FILE) as f:
            return json.load(f)
    return {"daily": {}, "weekly": {}, "monthly": {}, "last_date": ""}


def save_schedule_runs(runs):
    save_json(SCHEDULE_RUNS_FILE, runs)


def get_due_items():
    """Get all schedule items that are due right now."""
    runs = load_schedule_runs()
    today = now().strftime("%Y-%m-%d")
    current_time = current_hour_min()
    dow = day_of_week()
    dom = str(day_of_month())
    due = []

    # — Daily cadence —
    daily_key = f"daily_{today}"
    if runs.get("daily", {}).get(daily_key) != "done":
        daily_items = CADENCES.get("daily", [])
        for item in daily_items:
            if item["time"] <= current_time:
                due.append({**item, "cadence": "daily"})
        if due:
            runs.setdefault("daily", {})[daily_key] = "done"
            save_schedule_runs(runs)

    # — Weekly cadence —
    weekly_schedule = CADENCES.get("weekly", {}).get(dow, [])
    weekly_key = f"weekly_{today}"
    if runs.get("weekly", {}).get(weekly_key) != "done":
        for item in weekly_schedule:
            if item["time"] <= current_time:
                due.append({**item, "cadence": "weekly"})
        if any(item["time"] <= current_time for item in weekly_schedule):
            runs.setdefault("weekly", {})[weekly_key] = "done"
            save_schedule_runs(runs)

    # — Monthly cadence —
    monthly_schedule = CADENCES.get("monthly", {}).get(dom, [])
    monthly_key = f"monthly_{today}"
    if runs.get("monthly", {}).get(monthly_key) != "done":
        for item in monthly_schedule:
            if item["time"] <= current_time:
                due.append({**item, "cadence": "monthly"})
        if any(item["time"] <= current_time for item in monthly_schedule):
            runs.setdefault("monthly", {})[monthly_key] = "done"
            save_schedule_runs(runs)

    # Reset daily runs on new day
    if runs.get("last_date") != today:
        runs["daily"] = {}
        runs["weekly"] = {}
        runs["monthly"] = {}
        runs["last_date"] = today
        save_schedule_runs(runs)

    return due


# ══════════════════════════════════════════════════════════════
# ENGAGEMENT GENERATOR
# ══════════════════════════════════════════════════════════════

def get_stats_blurb():
    """Generate a brief stats summary."""
    try:
        result = subprocess.run(
            ["python3", TRACKER_PY, "stats", "7"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            stats = json.loads(result.stdout)
            return (
                f"📊 This week: {stats.get('engagements_sent', 0)} engagements, "
                f"{stats.get('responses', 0)} responses, "
                f"{stats.get('response_rate', 0)}% response rate"
            )
    except Exception:
        pass
    return "📊 Engagements are being tracked."


def get_pattern_blurb():
    """Get a brief pattern insight from journal."""
    state = load_json(STATE_FILE)
    themes = state.get("recurring_themes", [])
    if themes:
        return f"your recurring themes include: {', '.join(themes[:5])}"
    return "patterns are still forming as we log more entries."


def get_active_goals_blurb():
    """Get active goals summary."""
    state = load_json(STATE_FILE)
    goals = state.get("active_goals", [])
    if goals:
        return f"you're tracking {len(goals)} active goals: {', '.join(goals[:3])}"
    return "no active goals set yet. Use `/aware goals` to set some."


def generate_engagement(agent_id: str, prompt_type: str, cadence: str = "adhoc") -> dict:
    """Generate an engagement message for a given agent and prompt type."""
    agent = AGENTS.get(agent_id, AGENTS["aware"])
    template_key = f"{agent_id}_{prompt_type}"

    # Try specific template, fall back to agent-generic
    body = None

    if template_key in PROMPT_TEMPLATES:
        templates = PROMPT_TEMPLATES[template_key]
        template = random.choice(templates)

        # Fill template variables
        state = load_json(STATE_FILE)
        template = template.replace("{stats}", get_stats_blurb())
        template = template.replace("{pattern}", get_pattern_blurb())
        template = template.replace("{insight}", get_pattern_blurb())
        template = template.replace("{goals}", get_active_goals_blurb())
        template = template.replace("{count}", str(state.get("total_journal_entries", 0)))
        template = template.replace("{theme}", get_pattern_blurb())

        if "{spark}" in template:
            sparks = [
                "what if you had zero constraints for a day?",
                "what's something you believe that you never chose to believe?",
                "what would 5-years-from-now you be grateful you started today?",
                "what's the smallest change that would have the biggest impact?",
            ]
            template = template.replace("{spark}", random.choice(sparks))

        body = template
    else:
        # Generic fallback
        body = f"{agent['emoji']} **{agent['name']}** here ({agent['role']}). "

        if prompt_type == "morning":
            body += "Morning check: What's your intention for today? I'm tracking our interactions and ready to help."
        elif prompt_type == "evening":
            body += f"How did today go for you? {get_stats_blurb()}. I've been logging everything."
        elif prompt_type == "spark":
            body += "Quick spark for you: what's one question you'd love to explore right now?"
        elif prompt_type == "checkin":
            body += f"Check-in time. {get_active_goals_blurb()}. How's everything feeling?"
        elif prompt_type == "reflect":
            body += f"Time for a wider lens. {get_pattern_blurb()}. What's this telling you?"
        elif prompt_type == "publish":
            body += "You've had some good thoughts lately. Want me to turn something into a post?"
        elif prompt_type == "notice":
            body += "What have you been noticing lately? I track these and patterns emerge."
        elif prompt_type == "digest":
            body += f"Here's your digest. {get_stats_blurb()}. {get_pattern_blurb()}"
        else:
            body += f"Checking in. {get_stats_blurb()}"

    # Build title
    emoji = agent["emoji"]
    name = agent["name"]
    titles = {
        "morning": f"{emoji} {name} — Morning Intention",
        "evening": f"{emoji} {name} — Evening Reflection",
        "spark": f"{emoji} {name} — Creative Spark",
        "checkin": f"{emoji} {name} — Goal Check-In",
        "reflect": f"{emoji} {name} — Reflection Time",
        "publish": f"{emoji} {name} — Content Opportunity",
        "notice": f"{emoji} {name} — What Are You Noticing?",
        "digest": f"{emoji} {name} — Weekly Digest",
    }
    title = titles.get(prompt_type, f"{emoji} {name} — {prompt_type.title()}")

    # ── Determine enforced channels based on prompt type ──
    # Questions need input → Discord only (the interview channel)
    # Updates are informational → Notification only (no reply expected)
    enforced_channels = resolve_channels(prompt_type)

    return {
        "agent": agent_id,
        "agent_name": name,
        "agent_emoji": emoji,
        "prompt_type": prompt_type,
        "title": title,
        "body": body,
        "cadence": cadence,
        "urgency": "info",
        "channels": enforced_channels,
    }


# ══════════════════════════════════════════════════════════════
# DISPATCH ENGINE
# ══════════════════════════════════════════════════════════════

def resolve_channels(prompt_type: str) -> list:
    """Determine which channels a prompt type should use.

    Rules:
      - QUESTION types (morning, evening, checkin, reflect, spark) → Discord ONLY
        These are conversations — they need a reply. Discord is the interview floor.
      - UPDATE types (digest, notice, publish) → Notification ONLY
        These are informational — no reply needed. Android notification is the right surface.
      - Unknown types default to direct only (Pi conversation, no side effects).
    """
    if prompt_type in QUESTION_TYPES:
        return ["discord"]
    if prompt_type in UPDATE_TYPES:
        return ["notify"]
    return ["direct"]


def dispatch_engagement(engagement: dict):
    """Send an engagement through the channel router."""
    agent_id = engagement["agent"]
    prompt_type = engagement["prompt_type"]
    title = engagement["title"]
    body = engagement["body"]
    channels = engagement["channels"]
    urgency = engagement.get("urgency", "info")

    # Record the engagement
    subprocess.run([
        "python3", ENGAGE_PY, "record", prompt_type
    ], capture_output=True, timeout=5)

    # Route through channels
    channels_str = ",".join(channels)
    result = subprocess.run([
        "python3", CHANNELS_PY, "send",
        agent_id, prompt_type, title, body,
        channels_str, urgency
    ], capture_output=True, text=True, timeout=30)

    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {"error": result.stdout[:500] if result.stdout else result.stderr[:500]}


# ══════════════════════════════════════════════════════════════
# MAIN TICK — Called periodically by the trigger engine
# ══════════════════════════════════════════════════════════════

def tick():
    """Main tick function — checks schedule and fires due engagements."""
    due = get_due_items()
    results = []

    if not due:
        return []

    state = load_json(STATE_FILE)
    if not state.get("proactive_mode", True):
        return [{"status": "proactive_mode_disabled"}]

    for item in due:
        engagement = generate_engagement(
            item["agent"],
            item["type"],
            item.get("cadence", "adhoc")
        )

        # Override channels if specified in schedule, but enforce the
        # question-vs-update rule so notifications never get questions
        # and Discord never gets passive updates.
        if "channels" in item:
            schedule_channels = item["channels"]
        else:
            schedule_channels = None

        if schedule_channels is not None:
            # Still enforce: if schedule says notify+today but it's a question
            # type, strip non-discord channels. If schedule says discord but
            # it's an update type, replace with notify.
            enforced = resolve_channels(item["type"])
            if enforced == ["discord"] and "discord" in schedule_channels:
                engagement["channels"] = ["discord"]
            elif enforced == ["notify"] and "notify" in schedule_channels:
                engagement["channels"] = ["notify"]
            elif enforced == ["notify"]:
                # Schedule didn't include notify but this is an update → force notify
                engagement["channels"] = ["notify"]
            elif enforced == ["discord"]:
                # Schedule didn't include discord but this is a question → force discord
                engagement["channels"] = ["discord"]
            else:
                engagement["channels"] = schedule_channels
        # else: channels already set correctly by generate_engagement → resolve_channels

        result = dispatch_engagement(engagement)

        # Update state
        state["total_engagements"] += 1
        state["last_prompt_date"][item["type"]] = now().strftime("%Y-%m-%d")
        state["last_prompt_time"][item["type"]] = current_hour_min()
        save_json(STATE_FILE, state)

        results.append({
            "agent": item["agent"],
            "type": item["type"],
            "cadence": item.get("cadence", "adhoc"),
            "time": item["time"],
            "channels": item.get("channels", []),
            "dispatch_result": result,
        })

    return results


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def show_schedule():
    """Display the full schedule."""
    print("\n📅 ENGAGEMENT SCHEDULE")
    print("=" * 50)

    print("\n  DAILY:")
    for item in CADENCES["daily"]:
        agent = AGENTS.get(item["agent"], {})
        ch = ", ".join(item["channels"])
        print(f"    {item['time']} — {agent.get('emoji','')} {agent.get('name','')} ({item['type']}) → {ch}")

    print("\n  WEEKLY:")
    for dow, items in CADENCES["weekly"].items():
        print(f"    {dow.title()}:")
        for item in items:
            agent = AGENTS.get(item["agent"], {})
            ch = ", ".join(item["channels"])
            print(f"      {item['time']} — {agent.get('emoji','')} {agent.get('name','')} ({item['type']}) → {ch}")

    print("\n  MONTHLY:")
    for dom, items in CADENCES["monthly"].items():
        print(f"    Day {dom}:")
        for item in items:
            agent = AGENTS.get(item["agent"], {})
            ch = ", ".join(item["channels"])
            print(f"      {item['time']} — {agent.get('emoji','')} {agent.get('name','')} ({item['type']}) → {ch}")

    print()


def show_status():
    """Show orchestrator status."""
    state = load_json(STATE_FILE)
    due = get_due_items()
    runs = load_schedule_runs()

    print("\n🧠 ORCHESTRATOR STATUS")
    print("=" * 50)
    print(f"  Mode: {'🟢 Proactive' if state.get('proactive_mode') else '🔴 Passive'}")
    print(f"  Time:  {now().strftime('%Y-%m-%d %H:%M')} ({day_of_week().title()})")
    print(f"  Total Engagements: {state['total_engagements']}")
    print(f"  Due Now: {len(due)} items")

    if due:
        for item in due:
            agent = AGENTS.get(item["agent"], {})
            print(f"    ⏰ {item['time']} — {agent.get('emoji','')} {agent.get('name','')} ({item['type']}) → {', '.join(item['channels'])}")

    # Active agents
    print(f"\n  Active Agents:")
    for aid, agent in AGENTS.items():
        ch = ", ".join(agent["channels"])
        print(f"    {agent['emoji']} {agent['name']:8s} ({agent['role']:25s}) → {ch}")

    print()


def interactive():
    if len(sys.argv) < 2:
        print("Usage: orchestrator.py <command> [args]")
        print("Commands:")
        print("  tick          — Check schedule and fire due engagements")
        print("  test <agent> <type> [channels] — Send a test engagement")
        print("  schedule      — Show full engagement schedule")
        print("  status        — Show orchestrator status")
        print("  agent <id>    — Show agent configuration")
        print()
        print("Examples:")
        print("  orchestrator.py tick")
        print("  orchestrator.py test echo spark")
        print("  orchestrator.py test aware morning discord,notify")
        print("  orchestrator.py schedule")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "tick":
        results = tick()
        if results:
            print(f"\n✅ Fired {len(results)} engagements:")
            for r in results:
                status = "✅" if r.get("dispatch_result", {}).get("all_success") else "⚠️"
                print(f"  {status} {r['agent']} → {r['type']} ({r['cadence']}) via {', '.join(r.get('channels', []))}")
        else:
            print("\n⏸️  No engagements due right now.")

    elif cmd == "test" and len(sys.argv) >= 3:
        agent_id = sys.argv[2]
        prompt_type = sys.argv[3] if len(sys.argv) > 3 else "spark"
        channels = sys.argv[4].split(",") if len(sys.argv) > 4 else None

        if agent_id not in AGENTS:
            print(f"❌ Unknown agent: {agent_id}")
            print(f"   Available: {', '.join(AGENTS.keys())}")
            sys.exit(1)

        engagement = generate_engagement(agent_id, prompt_type)
        if channels:
            engagement["channels"] = channels

        print(f"\n🧪 TEST ENGAGEMENT")
        print(f"   Agent:  {engagement['agent_emoji']} {engagement['agent_name']}")
        print(f"   Type:   {engagement['prompt_type']}")
        print(f"   Title:  {engagement['title']}")
        print(f"   Body:   {engagement['body'][:200]}...")
        print(f"   Via:    {', '.join(engagement['channels'])}")
        print(f"\n   Dispatching...")

        result = dispatch_engagement(engagement)
        print(f"\n   Result: {json.dumps(result, indent=4)}")

    elif cmd == "schedule":
        show_schedule()

    elif cmd == "status":
        show_status()

    elif cmd == "agent" and len(sys.argv) > 2:
        aid = sys.argv[2]
        if aid in AGENTS:
            agent = AGENTS[aid]
            print(f"\n{agent['emoji']} {agent['name']} — {agent['role']}")
            print(f"  Tone: {agent['tone']}")
            print(f"  Channels: {', '.join(agent['channels'])}")
            print(f"  Signoff: {agent['signoff']}")
        else:
            print(f"Unknown agent: {aid}")
            print(f"Available: {', '.join(AGENTS.keys())}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    interactive()
