#!/usr/bin/env python3
"""sentiment.py — Analyze text sentiment for media coverage or PR materials.

Usage:
    echo "Text to analyze" | python sentiment.py
    python sentiment.py --file article.txt
    python sentiment.py --json "Article text here"
"""

import argparse
import json
import re
import sys


# Expanded keyword-based sentiment lexicon
POSITIVE_WORDS = {
    "great", "excellent", "amazing", "outstanding", "fantastic", "wonderful",
    "impressive", "innovative", "breakthrough", "success", "successful",
    "leader", "leading", "growth", "growing", "strong", "praised",
    "celebrated", "award", "winning", "positive", "love", "best",
    "remarkable", "exceptional", "superior", "advantage", "opportunity",
    "progress", "milestone", "achievement", "triumph", "beneficial",
    "exciting", "promising", "potential", "valuable", "quality",
    "trusted", "reliable", "efficient", "effective", "popular",
}

NEGATIVE_WORDS = {
    "poor", "terrible", "awful", "disappointing", "failed", "failure",
    "crisis", "scandal", "controversy", "lawsuit", "complaint",
    "concern", "critical", "criticized", "decline", "declining",
    "weak", "struggling", "problem", "issue", "risk", "threat",
    "danger", "investigation", "warning", "alleged", "accused",
    "controversial", "backlash", "boycott", "protest", "negative",
    "worst", "hate", "disaster", "catastrophe", "loss", "lost",
    "damage", "harm", "error", "mistake", "blame",
}

INTENSIFIERS = {
    "very", "extremely", "incredibly", "highly", "remarkably",
    "exceptionally", "absolutely", "utterly", "particularly",
}

DIMINISHERS = {
    "somewhat", "slightly", "barely", "marginally", "hardly",
    "partially", "relatively", "fairly", "rather",
}


def tokenize(text: str) -> list[str]:
    """Extract words from text."""
    return re.findall(r"[a-zA-Z]+(?:'[a-z]+)?", text.lower())


def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of text using lexicon-based approach."""
    words = tokenize(text)
    total_words = len(words)
    
    positive_found = []
    negative_found = []
    intensified = []
    diminished = []
    
    for i, word in enumerate(words):
        if word in POSITIVE_WORDS:
            positive_found.append(word)
            # Check for intensifier before
            if i > 0 and words[i-1] in INTENSIFIERS:
                intensified.append(word)
            # Check for diminisher before
            if i > 0 and words[i-1] in DIMINISHERS:
                diminished.append(word)
        elif word in NEGATIVE_WORDS:
            negative_found.append(word)
            if i > 0 and words[i-1] in INTENSIFIERS:
                intensified.append(word)
            if i > 0 and words[i-1] in DIMINISHERS:
                diminished.append(word)
    
    # Calculate score
    pos_score = len(positive_found)
    neg_score = len(negative_found)
    
    # Apply intensifier/diminisher weights
    for word in intensified:
        if word in positive_found:
            pos_score += 0.5
        else:
            neg_score += 0.5
    
    for word in diminished:
        if word in positive_found:
            pos_score -= 0.3
        else:
            neg_score -= 0.3
    
    # Normalize to -1 to 1 range
    if total_words == 0:
        score = 0
    else:
        score = (pos_score - neg_score) / max(total_words * 0.1, 1)
        score = max(-1, min(1, score))
    
    # Determine label
    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"
    
    # Confidence based on number of sentiment words found
    total_sentiment = len(positive_found) + len(negative_found)
    confidence = min(1.0, total_sentiment * 0.15)
    
    return {
        "label": label,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
        "positive_words": sorted(set(positive_found)),
        "negative_words": sorted(set(negative_found)),
        "intensified_words": sorted(set(intensified)),
        "diminished_words": sorted(set(diminished)),
        "stats": {
            "total_words": total_words,
            "sentiment_words": total_sentiment,
            "positive_count": len(positive_found),
            "negative_count": len(negative_found),
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze text sentiment")
    parser.add_argument("--file", "-f", help="Input file")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("text", nargs="?", help="Text to analyze")
    args = parser.parse_args()

    # Get text
    if args.file:
        try:
            with open(args.file) as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    elif args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    if not text.strip():
        print("Error: No text provided", file=sys.stderr)
        sys.exit(1)

    result = analyze_sentiment(text)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}[result["label"]]
        print(f"{emoji} Sentiment: {result['label'].upper()}")
        print(f"   Score: {result['score']:+.3f} (confidence: {result['confidence']:.0%})")
        print(f"   Words analyzed: {result['stats']['total_words']}")
        print(f"   Sentiment words: {result['stats']['sentiment_words']}")
        if result["positive_words"]:
            print(f"   Positive: {', '.join(result['positive_words'])}")
        if result["negative_words"]:
            print(f"   Negative: {', '.join(result['negative_words'])}")
        if result["intensified_words"]:
            print(f"   Intensified: {', '.join(result['intensified_words'])}")


if __name__ == "__main__":
    main()
