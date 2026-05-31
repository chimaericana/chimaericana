#!/usr/bin/env bash
# draft_release.sh — Generate a press release from template + briefing
# Usage: ./draft_release.sh --title "Title" --body "Body text" [--headline "Custom headline"] [--city "City, State"]
#        cat briefing.txt | ./draft_release.sh --title "Title"

set -euo pipefail

# Defaults
HEADLINE=""
TITLE=""
BODY=""
CITY=""
DATE=$(date '+%B %d, %Y')
COMPANY=""
CONTACT_NAME=""
CONTACT_EMAIL=""
CONTACT_PHONE=""

usage() {
    cat <<EOF
Usage: $0 --title "Title" --body "Text" [options]

Options:
  --title        Press release title (required)
  --body         Body text or briefing notes (required, or via stdin)
  --headline     Override headline (optional)
  --city         Dateline city, e.g. "NEW YORK" (optional)
  --date         Release date (default: today)
  --company      Company name (optional)
  --contact      Media contact name (optional)
  --email        Media contact email (optional)
  --phone        Media contact phone (optional)
  --help         Show this help
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --title) TITLE="$2"; shift 2 ;;
        --body) BODY="$2"; shift 2 ;;
        --headline) HEADLINE="$2"; shift 2 ;;
        --city) CITY="$2"; shift 2 ;;
        --date) DATE="$2"; shift 2 ;;
        --company) COMPANY="$2"; shift 2 ;;
        --contact) CONTACT_NAME="$2"; shift 2 ;;
        --email) CONTACT_EMAIL="$2"; shift 2 ;;
        --phone) CONTACT_PHONE="$2"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Read body from stdin if not provided
if [[ -z "$BODY" ]] && [[ ! -t 0 ]]; then
    BODY=$(cat)
fi

if [[ -z "$TITLE" ]]; then
    echo "Error: --title is required" >&2
    exit 1
fi

if [[ -z "$BODY" ]]; then
    echo "Error: --body is required (or pipe via stdin)" >&2
    exit 1
fi

# Generate headline if not provided
if [[ -z "$HEADLINE" ]]; then
    HEADLINE=$(echo "$TITLE" | tr '[:lower:]' '[:upper:]')
fi

# Generate press release
cat <<EOF
FOR IMMEDIATE RELEASE

${HEADLINE}

${CITY:+${CITY} — }${DATE} — ${BODY}

###

EOF

if [[ -n "$COMPANY" ]]; then
    echo "About ${COMPANY}:"
    echo "[Company boilerplate]"
    echo ""
fi

echo "Media Contact:"
echo "${CONTACT_NAME:+${CONTACT_NAME}}"
echo "${CONTACT_EMAIL:+${CONTACT_EMAIL}}"
echo "${CONTACT_PHONE:+${CONTACT_PHONE}}"
echo "${CONTACT_NAME:+${CONTACT_EMAIL:+}${CONTACT_PHONE:+}}"

echo ""
echo "---"
echo "Press release template generated. Edit bracketed sections with specific details."
echo "Save to: releases/$(date +%Y-%m-%d)-$(echo "$TITLE" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | head -c 50).md"
