#!/usr/bin/env bash
# notes.sh — Quick note-taking with date and tags
# Usage: ./notes.sh "Your note here" --tags tag1,tag2
#        ./notes.sh --list [--tags tag1]
#        ./notes.sh --search "keyword"

set -euo pipefail

NOTES_DIR="automations/general/notes"
NOTES_FILE="$NOTES_DIR/notes.md"

init_notes() {
    mkdir -p "$NOTES_DIR"
    if [[ ! -f "$NOTES_FILE" ]]; then
        echo "# Notes" > "$NOTES_FILE"
        echo "" >> "$NOTES_FILE"
    fi
}

add_note() {
    local note="$1"
    local tags="${2:-}"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M')
    local tag_str=""
    if [[ -n "$tags" ]]; then
        tag_str=" [$(echo "$tags" | sed 's/,/](#) [/g')]"
    fi

    echo "## ${timestamp}${tag_str}" >> "$NOTES_FILE"
    echo "" >> "$NOTES_FILE"
    echo "${note}" >> "$NOTES_FILE"
    echo "" >> "$NOTES_FILE"
    echo "---" >> "$NOTES_FILE"
    echo "" >> "$NOTES_FILE"

    echo "✅ Note saved at ${timestamp}"
    if [[ -n "$tags" ]]; then
        echo "   Tags: ${tags}"
    fi
}

list_notes() {
    local filter_tags="${1:-}"
    if [[ ! -f "$NOTES_FILE" ]]; then
        echo "No notes yet."
        return
    fi

    if [[ -n "$filter_tags" ]]; then
        echo "📋 Notes tagged with: ${filter_tags}"
        echo "════════════════════════════════════════"
        grep -A 10 -i "$filter_tags" "$NOTES_FILE" || echo "No matching notes."
    else
        echo "📋 All Notes"
        echo "════════════════════════════════════════"
        cat "$NOTES_FILE"
    fi
}

search_notes() {
    local query="$1"
    if [[ ! -f "$NOTES_FILE" ]]; then
        echo "No notes to search."
        return
    fi

    echo "🔍 Searching for: '${query}'"
    echo "════════════════════════════════════════"
    grep -n -i -B 2 -A 5 "$query" "$NOTES_FILE" || echo "No matches found."
}

usage() {
    cat <<EOF
Quick Notes Manager

Usage:
  $0 "Note text" [--tags tag1,tag2]   Add a note
  $0 --list [--tags tag]              List notes
  $0 --search "keyword"               Search notes
  $0 --help                           Show this help
EOF
}

init_notes

if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

case $1 in
    --list)
        shift
        list_notes "${1:-}"
        ;;
    --search)
        shift
        search_notes "$1"
        ;;
    --help)
        usage
        ;;
    *)
        # Parse note and tags
        note="$1"
        tags=""
        shift
        while [[ $# -gt 0 ]]; do
            case $1 in
                --tags) tags="$2"; shift 2 ;;
                *) shift ;;
            esac
        done
        add_note "$note" "$tags"
        ;;
esac
