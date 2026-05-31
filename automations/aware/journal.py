#!/data/data/com.termux/files/usr/bin/python3
"""Aware Journal Engine — log, search, and manage journal entries."""

import json
import os
import sys
from datetime import datetime

AWARE_DIR = os.path.expanduser("~/Athena/aware")
JOURNAL_DIR = os.path.join(AWARE_DIR, "journal", "entries")
PATTERNS_DIR = os.path.join(AWARE_DIR, "journal", "patterns")
INSIGHTS_DIR = os.path.join(AWARE_DIR, "journal", "insights")
STATE_FILE = os.path.join(AWARE_DIR, "state.json")

os.makedirs(JOURNAL_DIR, exist_ok=True)
os.makedirs(PATTERNS_DIR, exist_ok=True)
os.makedirs(INSIGHTS_DIR, exist_ok=True)


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def today_file():
    return os.path.join(JOURNAL_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.md")


def log_entry(prompt_type: str, prompt_used: str, response: str, tags: list = None):
    """Log a journal entry from a prompt response."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    filepath = today_file()

    entry = f"""
## {date_str} {time_str} — {prompt_type}

**Prompt:** {prompt_used}

**Response:**
{response}

"""
    if tags:
        entry += f"**Tags:** {', '.join(tags)}\n"

    entry += f"---\n"

    with open(filepath, "a") as f:
        f.write(entry)

    # Update state
    state = load_state()
    state["total_journal_entries"] += 1
    state["last_prompt_date"][prompt_type] = date_str
    state["last_prompt_time"][prompt_type] = time_str
    state["prompt_counts"][prompt_type] = state["prompt_counts"].get(prompt_type, 0) + 1
    state["total_engagements"] += 1
    save_state(state)

    print(f"✅ Journal entry logged for {date_str} ({prompt_type})")
    return filepath


def list_entries(days: int = 7):
    """List recent journal entries."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    entries = []

    for fname in sorted(os.listdir(JOURNAL_DIR), reverse=True):
        if not fname.endswith(".md"):
            continue
        date_str = fname.replace(".md", "")
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if entry_date < cutoff:
            continue

        with open(os.path.join(JOURNAL_DIR, fname)) as f:
            content = f.read()

        # Count entries in the file
        entry_count = content.count("## ")
        entries.append(f"{date_str} — {entry_count} entries")

    if not entries:
        print("📝 No journal entries found in the last {} days.".format(days))
        return

    print(f"📝 Journal — Last {days} Days")
    print("=" * 40)
    for e in entries:
        print(f"  {e}")
    print(f"\nTotal: {len(entries)} days")


def read_entry(date_str: str = None):
    """Read a specific day's journal entry."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(JOURNAL_DIR, f"{date_str}.md")

    if not os.path.exists(filepath):
        print(f"📝 No journal entry for {date_str}")
        return

    with open(filepath) as f:
        print(f.read())


def search_entries(query: str):
    """Search journal entries for a term."""
    results = []
    for fname in sorted(os.listdir(JOURNAL_DIR), reverse=True):
        if not fname.endswith(".md"):
            continue
        filepath = os.path.join(JOURNAL_DIR, fname)
        with open(filepath) as f:
            content = f.read()
        if query.lower() in content.lower():
            date_str = fname.replace(".md", "")
            # Find matching sections
            sections = content.split("## ")
            matches = [s.split("\n")[0] for s in sections if query.lower() in s.lower()]
            results.append(f"{date_str}: {', '.join(matches)}")

    if results:
        print(f"🔍 Search results for '{query}':")
        print("=" * 40)
        for r in results[:20]:
            print(f"  {r}")
    else:
        print(f"🔍 No matches for '{query}'")


def save_content(content_type: str, title: str, body: str, platform: str = None):
    """Save generated content ready for publishing."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    if content_type == "social":
        target_dir = os.path.join(AWARE_DIR, "content", "social")
    elif content_type == "note":
        target_dir = os.path.join(AWARE_DIR, "content", "notes")
    elif content_type == "voice":
        target_dir = os.path.join(AWARE_DIR, "content", "voice")
    else:
        target_dir = os.path.join(AWARE_DIR, "content", "notes")

    os.makedirs(target_dir, exist_ok=True)

    # Create safe filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:50]
    platform_str = f"_{platform}" if platform else ""
    filename = f"{date_str}{platform_str}_{safe_title}.md"
    filepath = os.path.join(target_dir, filename)

    metadata = f"""---
type: {content_type}
platform: {platform or 'general'}
created: {date_str}
status: draft
published: false
---

"""
    with open(filepath, "w") as f:
        f.write(metadata + body)

    # Update state
    state = load_state()
    state["total_content_pieces"] += 1
    state["content_pipeline"]["drafts"].append({
        "file": filename,
        "type": content_type,
        "platform": platform,
        "date": date_str
    })
    save_state(state)

    print(f"📄 Content saved: {filepath}")
    return filepath


def list_content(content_type: str = None, limit: int = 10):
    """List generated content."""
    if content_type == "social":
        target_dir = os.path.join(AWARE_DIR, "content", "social")
    elif content_type == "note":
        target_dir = os.path.join(AWARE_DIR, "content", "notes")
    elif content_type == "voice":
        target_dir = os.path.join(AWARE_DIR, "content", "voice")
    elif content_type:
        print(f"Unknown content type: {content_type}")
        return
    else:
        # List all
        for t in ["social", "notes", "voice"]:
            list_content(t, limit)
        return

    if not os.path.exists(target_dir):
        print(f"  No {content_type} content yet.")
        return

    files = sorted(os.listdir(target_dir), reverse=True)[:limit]
    print(f"📄 {content_type.upper()} Content ({len(files)} items):")
    print("-" * 40)
    for f in files[:limit]:
        filepath = os.path.join(target_dir, f)
        mtime = os.path.getmtime(filepath)
        size = os.path.getsize(filepath)
        print(f"  {f} ({size} bytes)")


def analyze_patterns():
    """Analyze journal entries for recurring themes and patterns."""
    from collections import Counter
    import re

    entries_text = ""
    for fname in sorted(os.listdir(JOURNAL_DIR)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(JOURNAL_DIR, fname)) as f:
            entries_text += f.read().lower() + "\n"

    if not entries_text.strip():
        print("📊 No journal entries to analyze.")
        return

    # Simple keyword frequency
    common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
                    "for", "of", "with", "by", "from", "is", "was", "are", "were",
                    "be", "been", "being", "have", "has", "had", "do", "does", "did",
                    "will", "would", "could", "should", "may", "might", "shall",
                    "can", "need", "want", "like", "just", "also", "very", "really",
                    "that", "this", "these", "those", "it", "its", "i", "my", "me",
                    "we", "our", "you", "your", "he", "she", "they", "them", "their",
                    "not", "no", "so", "up", "out", "about", "into", "over", "after",
                    "all", "each", "every", "some", "any", "more", "most", "other",
                    "such", "only", "own", "same", "too", "very", "than", "now",
                    "then", "here", "there", "when", "where", "why", "how", "what",
                    "which", "who", "whom"}

    words = re.findall(r'\b[a-z]{3,}\b', entries_text)
    word_freq = Counter(w for w in words if w not in common_words)

    # Extract themes (top 20 significant words)
    themes = [word for word, count in word_freq.most_common(20) if count >= 2]

    # Count entries per day
    entry_dates = sorted([f.replace(".md", "") for f in os.listdir(JOURNAL_DIR) if f.endswith(".md")])

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    analysis = f"""# Pattern Analysis — {date_str}

**Generated:** {date_str} {time_str}
**Entries analyzed:** {len(entry_dates)} days
**Total content:** {len(entry_dates)} days

## Recurring Themes

{', '.join(themes[:15]) if themes else 'Not enough data yet. Keep journaling!'}

## Activity

- Active journal days: {len(entry_dates)}
- Date range: {entry_dates[0] if entry_dates else 'N/A'} → {entry_dates[-1] if entry_dates else 'N/A'}

---

*Auto-generated analysis — use insights to guide reflection.*
"""

    filepath = os.path.join(PATTERNS_DIR, f"patterns_{date_str}.md")
    with open(filepath, "w") as f:
        f.write(analysis)

    # Update state
    state = load_state()
    state["last_pattern_analysis"] = date_str
    state["recurring_themes"] = themes[:15]
    save_state(state)

    print(f"📊 Pattern analysis saved: {filepath}")
    print(f"  Themes detected: {', '.join(themes[:10])}")
    return filepath


def mark_published(filename: str):
    """Mark a content piece as published."""
    state = load_state()
    for d in state["content_pipeline"]["drafts"]:
        if d["file"] == filename:
            state["content_pipeline"]["drafts"].remove(d)
            state["content_pipeline"]["published"].append({**d, "published_at": datetime.now().isoformat()})
            save_state(state)
            print(f"✅ Marked '{filename}' as published.")
            return
    print(f"❌ Content '{filename}' not found in drafts.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: journal.py <command> [args]")
        print("Commands: log, list, read, search, content, patterns, publish")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "log":
        if len(sys.argv) < 4:
            print("Usage: journal.py log <type> <prompt> <response> [tags]")
            sys.exit(1)
        log_entry(sys.argv[2], sys.argv[3], sys.argv[4], tags=sys.argv[5:] if len(sys.argv) > 5 else None)

    elif cmd == "list":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        list_entries(days)

    elif cmd == "read":
        date_str = sys.argv[2] if len(sys.argv) > 2 else None
        read_entry(date_str)

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: journal.py search <query>")
            sys.exit(1)
        search_entries(sys.argv[2])

    elif cmd == "content":
        ctype = sys.argv[2] if len(sys.argv) > 2 else None
        list_content(ctype)

    elif cmd == "patterns":
        analyze_patterns()

    elif cmd == "publish":
        if len(sys.argv) < 3:
            print("Usage: journal.py publish <filename>")
            sys.exit(1)
        mark_published(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
