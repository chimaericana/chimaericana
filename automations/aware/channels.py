#!/data/data/com.termux/files/usr/bin/python3
"""Aware Channel Router — delivers engagements through every available channel.

Supported channels:
  - discord    → via bot_bridge (existing infrastructure)
  - sms        → via termux-sms-send (Android SMS/WhatsApp)
  - notify     → via termux-notification (Android notification popups)
  - toast      → via termux-toast (Android toast popups)
  - email      → via curl to email API (SendGrid/Mailgun)
  - direct     → logs for Pi direct conversation engagement
  - clipboard  → via termux-clipboard-set (copy to clipboard for publishing)
  - platform   → social media platform posting (via Echo agent)
"""

import json
import os
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

AWARE_DIR = os.path.expanduser("~/Athena/aware")
COMM_DIR = os.path.expanduser("~/Athena/automations/comm")
NOTIFY_SH = os.path.expanduser("~/Athena/automations/notifications/notify.sh")
BRIDGE_PY = os.path.join(COMM_DIR, "bot_bridge.py")
STATE_FILE = os.path.join(AWARE_DIR, "state.json")
TRACKER_PY = os.path.expanduser("~/Athena/automations/aware/tracker.py")
SMS_SENT_LOG = os.path.join(AWARE_DIR, "sms_sent.jsonl")
EMAIL_SENT_LOG = os.path.join(AWARE_DIR, "email_sent.jsonl")

os.makedirs(AWARE_DIR, exist_ok=True)


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run(cmd_list, timeout=15):
    """Run a command and return result."""
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "Command not found"
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"


def track(engagement_id: str, channel: str, status: str):
    """Log to tracker."""
    try:
        subprocess.run([
            "python3", TRACKER_PY, "status"
        ], capture_output=True, timeout=5)
    except Exception:
        pass


def get_agent_avatar(agent_id: str) -> str:
    """Get the emoji avatar for an agent."""
    avatars = {
        "nexus": "🎯",
        "echo": "📣",
        "press": "📰",
        "shield": "🛡️",
        "signal": "📡",
        "aware": "🧠",
    }
    return avatars.get(agent_id, "🤖")


def get_agent_display_name(agent_id: str) -> str:
    """Get the display name for an agent."""
    names = {
        "nexus": "Nexus",
        "echo": "Echo",
        "press": "Press",
        "shield": "Shield",
        "signal": "Signal",
        "aware": "Aware",
    }
    return names.get(agent_id, "Agent")


# ══════════════════════════════════════════════════════════════
# CHANNEL: Discord
# ══════════════════════════════════════════════════════════════

def send_discord(agent_id: str, title: str, body: str, urgency: str = "info",
                 category: str = "digest") -> bool:
    """Send an engagement through the Discord bot bridge."""
    avatar = get_agent_avatar(agent_id)
    display = get_agent_display_name(agent_id)

    formatted = f"{avatar} **{display}** says:\n\n{body}"

    code, out, err = run([
        "python3", BRIDGE_PY, "send",
        category, title, formatted, urgency
    ])

    if code == 0:
        return True

    # Fallback: try bot_manager send
    code, out, err = run([
        "bash", os.path.join(COMM_DIR, "bot_manager.sh"), "bridge",
        "send", category, formatted
    ])
    return code == 0


# ══════════════════════════════════════════════════════════════
# CHANNEL: SMS / WhatsApp (via termux-sms-send)
# ══════════════════════════════════════════════════════════════

def send_sms(agent_id: str, message: str, phone_number: str = None) -> bool:
    """Send an engagement via SMS (also delivers to WhatsApp on Android)."""
    avatar = get_agent_avatar(agent_id)
    display = get_agent_display_name(agent_id)

    # Truncate for SMS (160 chars x multiple segments = ~480 safe)
    full_message = f"{avatar} {display}: {message}"
    if len(full_message) > 480:
        full_message = full_message[:477] + "..."

    # If no phone number, log and return
    if not phone_number:
        # Store for later sending when number is configured
        log_sms_pending(agent_id, message)
        return False

    code, out, err = run(["termux-sms-send", "-n", phone_number, full_message], timeout=10)

    if code == 0:
        with open(SMS_SENT_LOG, "a") as f:
            f.write(json.dumps({
                "agent": agent_id,
                "to": phone_number[-4:] if len(phone_number) > 4 else phone_number,
                "preview": message[:60],
                "time": datetime.now().isoformat()
            }) + "\n")
        return True
    return False


def log_sms_pending(agent_id: str, message: str):
    """Log SMS for later delivery when phone number is configured."""
    pending_file = os.path.join(AWARE_DIR, "sms_pending.jsonl")
    with open(pending_file, "a") as f:
        f.write(json.dumps({
            "agent": agent_id,
            "message": message,
            "time": datetime.now().isoformat()
        }) + "\n")


# ══════════════════════════════════════════════════════════════
# CHANNEL: Android Notifications
# ══════════════════════════════════════════════════════════════

def send_notification(agent_id: str, title: str, message: str,
                      urgency: str = "info", actions: str = "") -> bool:
    """Send an Android notification via termux-notification."""
    avatar = get_agent_avatar(agent_id)
    display = get_agent_display_name(agent_id)

    notif_title = f"{avatar} {display} — {title}"
    notif_body = message[:200]  # Truncate for notification

    code, out, err = run([
        "bash", NOTIFY_SH, "--type", urgency,
        notif_body, "--title", notif_title,
    ])

    if code != 0:
        # Direct fallback
        code, out, err = run([
            "termux-notification",
            "--title", notif_title,
            "--content", notif_body,
            "--id", f"aware_{agent_id}_{int(time.time())}",
            "--channel", urgency,
        ])
    return code == 0


# ══════════════════════════════════════════════════════════════
# CHANNEL: Toast Popups
# ══════════════════════════════════════════════════════════════

def send_toast(agent_id: str, message: str) -> bool:
    """Send a brief Android toast popup."""
    avatar = get_agent_avatar(agent_id)
    display = get_agent_display_name(agent_id)

    toast = f"{avatar} {display}: {message[:100]}"
    code, out, err = run(["termux-toast", "-b", "white", toast])
    return code == 0


# ══════════════════════════════════════════════════════════════
# CHANNEL: Email (via curl to transactional email API)
# ══════════════════════════════════════════════════════════════

def send_email(agent_id: str, subject: str, body: str, to_email: str = None) -> bool:
    """Send an email via a configured email API (SendGrid/Mailgun format)."""
    if not to_email:
        # Store for later
        log_email_pending(agent_id, subject, body)
        return False

    avatar = get_agent_avatar(agent_id)
    display = get_agent_display_name(agent_id)
    
    html_body = f"""<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
<p style="font-size: 18px;">{avatar} <strong>{display}</strong></p>
<hr>
{body.replace(chr(10), '<br>')}
<hr>
<p style="color: #888; font-size: 12px;">Sent by {display} · Aware Engagement System</p>
</div>"""

    # Try multiple email API approaches
    # 1. SendGrid API
    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
    if sendgrid_key and to_email:
        payload = json.dumps({
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": f"{agent_id}@aware.local", "name": display},
            "subject": subject,
            "text": body,
            "html": html_body,
        })
        code, out, err = run([
            "curl", "-s", "-X", "POST", "https://api.sendgrid.com/v3/mail/send",
            "-H", f"Authorization: Bearer {sendgrid_key}",
            "-H", "Content-Type: application/json",
            "-d", payload
        ], timeout=15)
        if code == 0:
            log_email_sent(agent_id, to_email, subject)
            return True

    # 2. Mailgun API
    mailgun_key = os.environ.get("MAILGUN_API_KEY", "")
    mailgun_domain = os.environ.get("MAILGUN_DOMAIN", "")
    if mailgun_key and mailgun_domain and to_email:
        payload = {
            "from": f"{display} <{agent_id}@{mailgun_domain}>",
            "to": to_email,
            "subject": subject,
            "text": body,
            "html": html_body,
        }
        data = urllib.parse.urlencode(payload)
        code, out, err = run([
            "curl", "-s", "-X", "POST",
            f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
            "-u", f"api:{mailgun_key}",
            "-d", data
        ], timeout=15)
        if code == 0:
            log_email_sent(agent_id, to_email, subject)
            return True

    # 3. SMTP via msmtp if configured
    if os.path.exists(os.path.expanduser("~/.msmtprc")):
        email_file = os.path.join(AWARE_DIR, f"email_{int(time.time())}.eml")
        with open(email_file, "w") as f:
            f.write(f"From: {display} <{agent_id}@aware.local>\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Content-Type: text/plain; charset=utf-8\n\n")
            f.write(body)
        code, out, err = run(["msmtp", to_email], timeout=15)
        if code == 0:
            log_email_sent(agent_id, to_email, subject)
            os.unlink(email_file)
            return True

    # Log the attempt
    log_email_pending(agent_id, subject, body)
    return False


def log_email_sent(agent_id: str, to_email: str, subject: str):
    """Log a sent email."""
    with open(EMAIL_SENT_LOG, "a") as f:
        f.write(json.dumps({
            "agent": agent_id,
            "to": to_email,
            "subject": subject[:80],
            "time": datetime.now().isoformat()
        }) + "\n")


def log_email_pending(agent_id: str, subject: str, body: str):
    """Log email for later sending when email is configured."""
    pending_file = os.path.join(AWARE_DIR, "email_pending.jsonl")
    with open(pending_file, "a") as f:
        f.write(json.dumps({
            "agent": agent_id,
            "subject": subject,
            "body_preview": body[:200],
            "time": datetime.now().isoformat()
        }) + "\n")


# ══════════════════════════════════════════════════════════════
# CHANNEL: Clipboard (for quick publishing)
# ══════════════════════════════════════════════════════════════

def copy_to_clipboard(agent_id: str, content: str) -> bool:
    """Copy content to clipboard for quick publishing."""
    code, out, err = run(["termux-clipboard-set", content])
    return code == 0


# ══════════════════════════════════════════════════════════════
# CHANNEL: Platform Posting (via Echo agent / social scheduler)
# ══════════════════════════════════════════════════════════════

def post_to_platform(agent_id: str, platform: str, content: str, schedule_time: str = None) -> bool:
    """Post content to a social platform via the existing social scheduler."""
    scheduler = os.path.expanduser("~/Athena/automations/social/scheduler.py")
    
    if schedule_time:
        code, out, err = run([
            "python3", scheduler, "schedule",
            "--platform", platform,
            "--content", content,
            "--time", schedule_time
        ], timeout=10)
    else:
        code, out, err = run([
            "python3", scheduler, "publish",
            "--platform", platform,
            "--content", content
        ], timeout=10)
    
    if code == 0:
        track(f"{agent_id}_platform_{platform}_{int(time.time())}", platform, "posted")
        return True
    
    # Fallback: save as draft
    draft_dir = os.path.join(AWARE_DIR, "content", "social")
    os.makedirs(draft_dir, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{agent_id}_{platform}_draft.md"
    with open(os.path.join(draft_dir, filename), "w") as f:
        f.write(f"---\nagent: {agent_id}\nplatform: {platform}\nscheduled: {schedule_time or 'now'}\nstatus: draft\n---\n\n{content}")
    return False


# ══════════════════════════════════════════════════════════════
# CHANNEL ENFORCEMENT — safety net to prevent misrouting
# ══════════════════════════════════════════════════════════════

# Prompt types that are QUESTIONS — need user input, Discord only
_QUESTION_TYPES = {
    "morning", "evening", "checkin", "reflect", "spark",
}

# Prompt types that are INFORMATIONAL UPDATES — no reply needed, notification only
_UPDATE_TYPES = {
    "digest", "notice", "publish",
}

def enforce_channels(prompt_type: str, requested_channels: list) -> list:
    """Enforce channel routing rules as a safety net.

    Rules:
      - QUESTION types → Discord ONLY (strip notify/toast/anything else)
      - UPDATE types  → Notification ONLY (strip discord)
      - Unknown types → Allow as-is (likely ad-hoc / test)
    """
    requested = [c.strip().lower() for c in requested_channels]

    if prompt_type in _QUESTION_TYPES:
        if "discord" in requested:
            return ["discord"]
        # If someone requested notify for a question, block it — fall back to discord
        return ["discord"]

    if prompt_type in _UPDATE_TYPES:
        if "notify" in requested:
            return ["notify"]
        # If someone requested discord for an update, redirect to notify
        return ["notify"]

    return requested


# ══════════════════════════════════════════════════════════════
# MASTER ROUTER — Routes engagement through all enabled channels
# ══════════════════════════════════════════════════════════════

def route_engagement(agent_id: str, prompt_type: str, title: str,
                     body: str, channels: list, urgency: str = "info",
                     phone: str = None, email_addr: str = None) -> dict:
    """Route an engagement through multiple channels and track results.

    Enforces channel rules: questions go to Discord, updates go to notifications.
    """
    # Enforce routing rules as a safety net
    channels = enforce_channels(prompt_type, channels)

    results = {}
    engagement_id = f"{agent_id}_{prompt_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    for channel in channels:
        channel = channel.strip().lower()
        success = False
        error = ""

        try:
            if channel == "discord":
                success = send_discord(agent_id, title, body, urgency)
            elif channel == "notify":
                success = send_notification(agent_id, title, body, urgency)
            elif channel == "sms":
                success = send_sms(agent_id, body[:200], phone)
            elif channel == "toast":
                success = send_toast(agent_id, title)
            elif channel == "email":
                success = send_email(agent_id, title, body, email_addr)
            elif channel == "clipboard":
                success = copy_to_clipboard(agent_id, body[:500])
            elif channel == "platform":
                success = post_to_platform(agent_id, title, body)
            elif channel == "direct":
                # Just log it for Pi direct conversation
                success = True
            else:
                error = f"Unknown channel: {channel}"
        except Exception as e:
            error = str(e)
            success = False

        results[channel] = {"success": success, "error": error}

        # Track it
        try:
            subprocess.run([
                "python3", TRACKER_PY, "log",
                agent_id, prompt_type, channel,
                f"{title}: {body[:80]}..."
            ], capture_output=True, timeout=5)
        except Exception:
            pass

    return {
        "engagement_id": engagement_id,
        "agent": agent_id,
        "prompt_type": prompt_type,
        "title": title,
        "channels": results,
        "all_success": all(r["success"] for r in results.values()),
        "timestamp": datetime.now().isoformat()
    }


def get_channel_availability() -> dict:
    """Check which channels are currently available."""
    channels = {}

    # Discord — check if bot bridge is reachable
    code, out, err = run(["python3", BRIDGE_PY, "status"])
    channels["discord"] = code == 0

    # SMS — check if termux-sms-send exists
    code, _, _ = run(["which", "termux-sms-send"])
    channels["sms"] = code == 0

    # Notifications
    code, _, _ = run(["which", "termux-notification"])
    channels["notify"] = code == 0

    # Toast
    code, _, _ = run(["which", "termux-toast"])
    channels["toast"] = code == 0

    # Email — check if any email API is configured
    channels["email"] = bool(os.environ.get("SENDGRID_API_KEY") or
                             os.environ.get("MAILGUN_API_KEY") or
                             os.path.exists(os.path.expanduser("~/.msmtprc")))

    # Clipboard
    code, _, _ = run(["which", "termux-clipboard-set"])
    channels["clipboard"] = code == 0

    # Platform posting — check if social scheduler exists
    scheduler = os.path.expanduser("~/Athena/automations/social/scheduler.py")
    channels["platform"] = os.path.exists(scheduler)

    # Direct (always available)
    channels["direct"] = True

    return channels


def print_channel_status():
    """Print available channels."""
    avail = get_channel_availability()
    print("\n📡 AVAILABLE CHANNELS")
    print("=" * 45)
    for ch, available in avail.items():
        icon = "🟢" if available else "🔴"
        print(f"  {icon} {ch:12s}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: channels.py <command> [args]")
        print("Commands:")
        print("  send     <agent> <type> <title> <body> <channels> [urgency] [phone] [email]")
        print("  status")
        print("  test     <agent> <channel>")
        print()
        print("Examples:")
        print("  channels.py send nexus morning '☀️ Good Morning!' 'Set your intention' discord,notify,toast")
        print("  channels.py send echo spark '✨ Creative Spark' 'What if...' notify,toast")
        print("  channels.py status")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "send" and len(sys.argv) >= 6:
        agent = sys.argv[2]
        ptype = sys.argv[3]
        title = sys.argv[4]
        body = sys.argv[5]
        channels = sys.argv[6].split(",") if len(sys.argv) > 6 else ["direct"]
        urgency = sys.argv[7] if len(sys.argv) > 7 else "info"
        phone = sys.argv[8] if len(sys.argv) > 8 else None
        email_addr = sys.argv[9] if len(sys.argv) > 9 else None

        result = route_engagement(agent, ptype, title, body, channels, urgency, phone, email_addr)
        print(json.dumps(result, indent=2))

    elif cmd == "status":
        print_channel_status()

    elif cmd == "test" and len(sys.argv) >= 3:
        agent = sys.argv[2]
        channel = sys.argv[3] if len(sys.argv) > 3 else "notify"
        body = f"🧪 This is a test engagement from {get_agent_display_name(agent)} via {channel}"
        result = route_engagement(agent, "test", f"🧪 Test from {agent}", body, [channel])
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
