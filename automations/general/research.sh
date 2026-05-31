#!/usr/bin/env bash
# research.sh — Save research findings with source metadata
# Usage: ./research.sh --title "Topic" --source "URL" --notes "Findings" [--tags "tag1,tag2"]

set -euo pipefail

RESEARCH_DIR="automations/general/research"
INDEX_FILE="$RESEARCH_DIR/index.md"

init_research() {
    mkdir -p "$RESEARCH_DIR/entries"
    if [[ ! -f "$INDEX_FILE" ]]; then
        cat > "$INDEX_FILE" <<'EOF'
# Research Index

| Date | Title | Source | Tags |
|------|-------|--------|------|
EOF
    fi
}

save_research() {
    local title="" source="" notes="" tags=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --title) title="$2"; shift 2 ;;
            --source) source="$2"; shift 2 ;;
            --notes) notes="$2"; shift 2 ;;
            --tags) tags="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$title" ]]; then
        echo "Error: --title is required" >&2
        exit 1
    fi

    local timestamp
    timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    local slug
    slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | head -c 40)
    local filename="entries/${timestamp}_${slug}.md"

    cat > "$RESEARCH_DIR/$filename" <<EOF
# ${title}

**Date:** $(date '+%Y-%m-%d %H:%M')
**Source:** ${source:-N/A}
**Tags:** ${tags:-none}

---

## Findings

${notes:-No notes provided.}

---
EOF

    # Update index
    echo "| $(date '+%Y-%m-%d') | [${title}]($filename) | ${source:-N/A} | ${tags:-} |" >> "$INDEX_FILE"

    echo "✅ Research saved: $filename"
    echo "   Title: $title"
    [[ -n "$source" ]] && echo "   Source: $source"
    [[ -n "$tags" ]] && echo "   Tags: $tags"
}

list_research() {
    if [[ ! -f "$INDEX_FILE" ]]; then
        echo "No research entries yet."
        return
    fi
    echo "📚 Research Archive"
    echo "════════════════════════════════════════"
    cat "$INDEX_FILE"
}

usage() {
    cat <<EOF
Research Manager

Usage:
  $0 --title "Topic" --source "URL" --notes "Findings" [--tags "tags"]
  $0 --list
  $0 --help
EOF
}

init_research

if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

case $1 in
    --list) list_research ;;
    --help) usage ;;
    *) save_research "$@" ;;
esac
