#!/data/data/com.termux/files/usr/bin/python3
"""Aware Engagement Engine — decides which prompts to fire and when."""

import json
import os
import sys
from datetime import datetime, timedelta

AWARE_DIR = os.path.expanduser("~/Athena/aware")
STATE_FILE = os.path.join(AWARE_DIR, "state.json")
SCHEDULER_FILE = os.path.join(AWARE_DIR, "scheduler.json")
JOURNAL_SCRIPT = os.path.expanduser("~/Athena/automations/aware/journal.py")

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

def is_in_time_window(window):
    """Check if current time is within a time window."""
    start, end = window
    current = current_hour_min()
    return start <= current <= end

def is_quiet_hours(state):
    """Check if currently in quiet hours."""
    prefs = state.get("preferences", {})
    quiet_start = prefs.get("quiet_hours_start", "22:00")
    quiet_end = prefs.get("quiet_hours_end", "08:00")
    current = current_hour_min()

    if quiet_start <= quiet_end:
        return quiet_start <= current <= quiet_end
    else:
        # Overnight window (e.g., 22:00 - 08:00)
        return current >= quiet_start or current <= quiet_end

def has_been_used_today(state, prompt_type):
    """Check if a prompt type has been used today."""
    today = now().strftime("%Y-%m-%d")
    return state.get("last_prompt_date", {}).get(prompt_type) == today

def get_prompt_count_today(state, prompt_type):
    """Get how many times a prompt type was used today."""
    today = now().strftime("%Y-%m-%d")
    count = 0
    for pt, date in state.get("last_prompt_date", {}).items():
        if pt.startswith(prompt_type) and date == today:
            count += 1
    return count

def total_prompts_today(state):
    """Get total prompts used today."""
    today = now().strftime("%Y-%m-%d")
    return sum(1 for date in state.get("last_prompt_date", {}).values() if date == today)

def check_schedule():
    """Check which prompts should be fired based on schedule."""
    state = load_json(STATE_FILE)
    scheduler = load_json(SCHEDULER_FILE)

    if not state.get("proactive_mode", True):
        return []

    if is_quiet_hours(state):
        return []

    max_daily = state.get("preferences", {}).get("max_prompts_per_day", 5)
    if total_prompts_today(state) >= max_daily:
        return []

    today_dow = day_of_week()
    current_time = current_hour_min()
    schedule = scheduler["prompt_schedule"]
    available = []

    for prompt_type, config in schedule.items():
        # Check if prompt type is enabled
        if prompt_type in ("morning", "evening", "notice", "spark", "checkin", "reflect"):
            pref_key = f"{prompt_type}_prompt_enabled"
            enabled_pref = state.get("preferences", {}).get(pref_key, True)
            if not enabled_pref:
                continue

        # Check days of week
        days = config.get("days_of_week", [])
        if today_dow not in days:
            continue

        # Check time window
        if "time_window" in config and not is_in_time_window(config["time_window"]):
            continue

        # Check max per day
        max_per_day = config.get("max_per_day", 1)
        if has_been_used_today(state, prompt_type) and max_per_day <= 1:
            continue
        if get_prompt_count_today(state, prompt_type) >= max_per_day:
            continue

        # Check max per week
        max_per_week = config.get("max_per_week", 999)
        weekly_count = sum(1 for pt in state.get("prompt_counts", {}) if pt.startswith(prompt_type))
        # Approximate weekly count from prompt_counts
        if state.get("prompt_counts", {}).get(prompt_type, 0) >= max_per_week:
            continue

        # Check cooldown
        cooldown = config.get("cooldown_minutes", 0)
        if cooldown > 0:
            last_time = state.get("last_prompt_time", {}).get(prompt_type)
            if last_time:
                try:
                    last_dt = datetime.strptime(last_time, "%H:%M").replace(
                        year=now().year, month=now().month, day=now().day
                    )
                    if now() - last_dt < timedelta(minutes=cooldown):
                        continue
                except ValueError:
                    pass

        # Check if trigger conditions exist for conditional prompts
        if prompt_type == "process":
            trigger_on = config.get("trigger_on_pattern", True)
            if not trigger_on:
                continue
            # Only suggest process prompts if there are patterns to act on
            if len(state.get("recurring_themes", [])) < 2:
                continue

        available.append(prompt_type)

    return available


def get_next_prompt():
    """Get the next prompt type that should be fired."""
    available = check_schedule()
    if not available:
        return None

    # Prioritize morning/evening at appropriate times, then rotate
    current = current_hour_min()

    # Morning priority
    if "morning" in available and "08:00" <= current <= "10:00":
        return "morning"

    # Evening priority
    if "evening" in available and "19:00" <= current <= "21:00":
        return "evening"

    # Otherwise return the first available (variety)
    return available[0]


def record_engagement(prompt_type: str):
    """Record that a prompt was used."""
    state = load_json(STATE_FILE)
    today = now().strftime("%Y-%m-%d")
    time_str = current_hour_min()

    state["last_prompt_date"][prompt_type] = today
    state["last_prompt_time"][prompt_type] = time_str
    state["prompt_counts"][prompt_type] = state["prompt_counts"].get(prompt_type, 0) + 1
    state["total_engagements"] += 1

    save_json(STATE_FILE, state)


def get_status():
    """Get engagement system status."""
    state = load_json(STATE_FILE)
    schedule = load_json(SCHEDULER_FILE)
    available = check_schedule()

    status = []
    status.append("🧠 AWARE SYSTEM STATUS")
    status.append("=" * 45)
    status.append(f"  Mode: {'🟢 Proactive' if state.get('proactive_mode') else '🔴 Passive'}")
    status.append(f"  Total Engagements: {state['total_engagements']}")
    status.append(f"  Journal Entries: {state['total_journal_entries']}")
    status.append(f"  Content Pieces: {state['total_content_pieces']}")
    status.append(f"  Processes Created: {state['total_processes_created']}")
    status.append(f"  Themes Tracked: {len(state.get('recurring_themes', []))}")
    status.append("")
    status.append(f"  Available Now: {', '.join(available) if available else 'None (check schedule)'}")
    status.append("")
    status.append(f"  ⏰ {current_hour_min()} | {day_of_week().title()}")

    active = state.get("active_goals", [])
    if active:
        status.append(f"  🎯 Active Goals: {', '.join(active[:3])}")

    if state.get("last_pattern_analysis"):
        status.append(f"  📊 Last Pattern Analysis: {state['last_pattern_analysis']}")

    print("\n".join(status))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: engage.py <command>")
        print("Commands: check, next, status, record <type>, schedule")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check":
        available = check_schedule()
        if available:
            print(",".join(available))
        else:
            print("")

    elif cmd == "next":
        next_type = get_next_prompt()
        print(next_type or "none")

    elif cmd == "status":
        get_status()

    elif cmd == "record" and len(sys.argv) > 2:
        record_engagement(sys.argv[2])
        print(f"Recorded engagement: {sys.argv[2]}")

    elif cmd == "schedule":
        sched = load_json(SCHEDULER_FILE)
        print("📅 PROMPT SCHEDULE")
        print("=" * 45)
        for ptype, config in sched["prompt_schedule"].items():
            window = config.get("time_window", "anytime")
            max_day = config.get("max_per_day", "unlimited")
            days = config.get("days_of_week", [])
            days_str = ", ".join(d[:3] for d in days)
            print(f"  {ptype:12s} | {window} | {max_day}/day | {days_str}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
