#!/usr/bin/env bash
# stt.sh — Speech-to-Text using Termux:API or fallback
# Usage: ./stt.sh [--language en] [--prompt "context"] [--timeout 30]
#        ./stt.sh --file audio.wav  (if using whisper fallback)

set -euo pipefail

LANGUAGE="${1:-en}"
PROMPT=""
TIMEOUT=30
OUTPUT_FORMAT="text"  # text or json
LOG_FILE="automations/voice/stt_history.jsonl"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --language|-l) LANGUAGE="$2"; shift 2 ;;
        --prompt|-p) PROMPT="$2"; shift 2 ;;
        --timeout|-t) TIMEOUT="$2"; shift 2 ;;
        --json|-j) OUTPUT_FORMAT="json"; shift ;;
        --help|-h) 
            cat <<EOF
Speech-to-Text

Usage: $0 [options]

Options:
  --language, -l    Language code (default: en)
  --prompt, -p      Context hint for better recognition
  --timeout, -t     Recording timeout in seconds (default: 30)
  --json, -j        Output as JSON
  --help, -h        Show this help

Examples:
  $0
  $0 --language es
  $0 --prompt "PR campaign meeting notes"
  $0 --json
EOF
            exit 0
            ;;
        *) shift ;;
    esac
done

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Try Termux:API speech-to-text
stt_termux() {
    local result
    result=$(termux-speech-to-text 2>/dev/null) || true
    
    if [[ -z "$result" ]]; then
        echo "Error: No speech input received. Make sure Termux:API app is installed and microphone permission is granted." >&2
        return 1
    fi
    
    echo "$result"
}

# Format output
format_output() {
    local text="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        cat <<EOF
{
  "text": "$(echo "$text" | sed 's/"/\\"/g')",
  "language": "$LANGUAGE",
  "timestamp": "$timestamp",
  "engine": "termux-api"
}
EOF
    else
        echo "$text"
    fi
    
    # Log to history
    echo "{\"text\":\"$(echo "$text" | sed 's/"/\\"/g')\",\"language\":\"$LANGUAGE\",\"timestamp\":\"$timestamp\",\"engine\":\"termux-api\"}" >> "$LOG_FILE"
}

# Main
echo "🎤 Listening... (timeout: ${TIMEOUT}s, language: $LANGUAGE)" >&2

if [[ -n "$PROMPT" ]]; then
    echo "   Context hint: $PROMPT" >&2
fi

text=$(stt_termux)

if [[ $? -ne 0 || -z "$text" ]]; then
    echo "Error: Speech recognition failed" >&2
    exit 1
fi

format_output "$text"
