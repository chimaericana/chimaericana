#!/usr/bin/env python3
"""monitor_coverage.py — Fetch and summarize media mentions from RSS feeds or URLs.

Usage:
    python monitor_coverage.py --url https://example.com/feed.xml
    python monitor_coverage.py --feed-file feeds.txt
    python monitor_coverage.py --json  # Output as JSON for piping
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Try to import feedparser, fall back to basic parsing
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False


def parse_feed_basic(url: str) -> list[dict]:
    """Basic XML parsing when feedparser is not available."""
    # Simple fallback - just return the URL for manual review
    return [{
        "title": f"Manual review needed",
        "link": url,
        "published": datetime.now().isoformat(),
        "source": url,
        "summary": "feedparser not installed. Run: pip install feedparser"
    }]


def fetch_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed."""
    if HAS_FEEDPARSER:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:20]:  # Limit to 20 most recent
            items.append({
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": feed.feed.get("title", url),
                "summary": entry.get("summary", "")[:500] if entry.get("summary") else "",
                "author": entry.get("author", ""),
            })
        return items
    return parse_feed_basic(url)


def load_feeds_from_file(filepath: str) -> list[str]:
    """Load feed URLs from a text file (one per line)."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: Feed file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    urls = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def analyze_sentiment(text: str) -> str:
    """Very basic sentiment analysis based on keyword matching."""
    positive_words = ["great", "excellent", "positive", "innovative", "leading", 
                      "impressive", "success", "breakthrough", "award", "praised",
                      "growth", "opportunity", "strong", "best", "love"]
    negative_words = ["crisis", "scandal", "controversy", "failed", "lawsuit",
                      "complaint", "concern", "critical", "poor", "decline",
                      "investigation", "warning", "risk", "problem", "fail"]
    
    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    else:
        return "neutral"


def main():
    parser = argparse.ArgumentParser(description="Monitor media coverage from RSS feeds")
    parser.add_argument("--url", help="Single RSS feed URL")
    parser.add_argument("--feed-file", help="File containing feed URLs (one per line)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--keywords", "-k", nargs="*", help="Keywords to highlight")
    args = parser.parse_args()

    if not args.url and not args.feed_file:
        parser.print_help()
        sys.exit(1)

    # Collect feed URLs
    urls = []
    if args.url:
        urls.append(args.url)
    if args.feed_file:
        urls.extend(load_feeds_from_file(args.feed_file))

    # Fetch all feeds
    all_items = []
    for url in urls:
        try:
            items = fetch_feed(url)
            all_items.extend(items)
        except Exception as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            all_items.append({
                "title": f"Error fetching feed",
                "link": url,
                "published": "",
                "source": url,
                "summary": str(e),
                "error": True,
            })

    # Add sentiment analysis
    for item in all_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        item["sentiment"] = analyze_sentiment(text)

    # Filter by keywords if provided
    if args.keywords:
        keyword_lower = [k.lower() for k in args.keywords]
        all_items = [
            item for item in all_items
            if any(kw in item.get("title", "").lower() or kw in item.get("summary", "").lower()
                   for kw in keyword_lower)
        ]

    # Output
    output_data = {
        "generated": datetime.now().isoformat(),
        "total_items": len(all_items),
        "sentiment_summary": {
            "positive": sum(1 for i in all_items if i.get("sentiment") == "positive"),
            "negative": sum(1 for i in all_items if i.get("sentiment") == "negative"),
            "neutral": sum(1 for i in all_items if i.get("sentiment") == "neutral"),
        },
        "items": all_items,
    }

    if args.json:
        output_text = json.dumps(output_data, indent=2)
    else:
        output_text = f"Media Coverage Report\n{'='*50}\nGenerated: {output_data['generated']}\n"
        output_text += f"Total items: {output_data['total_items']}\n"
        output_text += f"Sentiment: {output_data['sentiment_summary']['positive']} positive, "
        output_text += f"{output_data['sentiment_summary']['negative']} negative, "
        output_text += f"{output_data['sentiment_summary']['neutral']} neutral\n"
        output_text += f"{'='*50}\n\n"
        
        for item in all_items:
            sentiment_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(item.get("sentiment", "neutral"), "⚪")
            output_text += f"{sentiment_icon} {item['title']}\n"
            output_text += f"   Source: {item.get('source', 'Unknown')}\n"
            if item.get("published"):
                output_text += f"   Date: {item['published']}\n"
            if item.get("summary"):
                output_text += f"   Summary: {item['summary'][:200]}{'...' if len(item.get('summary', '')) > 200 else ''}\n"
            if item.get("link"):
                output_text += f"   Link: {item['link']}\n"
            output_text += "\n"

    # Write output
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output_text)
        print(f"Report saved to: {args.output}", file=sys.stderr)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
