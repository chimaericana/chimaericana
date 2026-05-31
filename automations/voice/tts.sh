#!/usr/bin/env bash
# tts.sh — Text-to-Speech using Termux:API
# Usage: echo "text" | ./tts.sh
#        ./tts.sh "Hello world"
#        ./tts.sh --file text.txt --lang en --rate 1.0

set -euo pipefail

LANG_CODE="en"
RATE="1.0"
STREAM=""
FILE=""
TEXT=""
VOICE_ENGINE=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --lang|-l) LANG_CODE="$2"; shift 2 ;;
        --rate|-r) RATE="$2"; shift 2 ;;
        --stream|-s) STREAM="$2"; shift 2 ;;
        --file|-f) FILE="$2"; shift 2 ;;
        --voice|-v) VOICE_ENGINE="$2"; shift 2 ;;
        --stop) termux-tts-speak --stop 2>/dev/null; echo "TTS stopped"; exit 0 ;;
        --engines) termux-tts-engines 2>/dev/null; exit 0 ;;
        --help|-h)
            cat <<EOF
Text-to-Speech

Usage: $0 [options] [text]
       echo "text" | $0 [options]

Options:
  --lang, -l      Language code (default: en)
  --rate, -r      Speech rate 0.5-2.0 (default: 1.0)
  --stream, -s    Streaming mode: pipe text line-by-line
  --file, -f      Read text from file
  --voice, -v     Voice engine name
  --stop          Stop current speech
  --engines       List available TTS engines
  --help, -h      Show this help

Examples:
  $0 "Hello world"
  echo "Hello" | $0
  $0 --file message.txt --lang es --rate 0.8
  $0 --stream  (then pipe text)
EOF
            exit 0
            ;;
        *) TEXT="$1"; shift ;;
    esac
done

# Build command
CMD="termux-tts-speak"
[[ "$LANG_CODE" != "en" ]] && CMD="$CMD --lang $LANG_CODE"
[[ "$RATE" != "1.0" ]] && CMD="$CMD --rate $RATE"
[[ -n "$VOICE_ENGINE" ]] && CMD="$CMD --voice '$VOICE_ENGINE'"

# Get text from various sources
if [[ -n "$FILE" ]]; then
    if [[ ! -f "$FILE" ]]; then
        echo "Error: File not found: $FILE" >&2
        exit 1
    fi
    TEXT=$(cat "$FILE")
elif [[ -z "$TEXT" ]] && [[ ! -t 0 ]]; then
    TEXT=$(cat)
fi

if [[ -z "$TEXT" ]]; then
    echo "Error: No text provided. Use argument, stdin, or --file." >&2
    exit 1
fi

# Execute TTS
echo "$TEXT" | eval "$CMD"

# Log
LOG_FILE="automations/voice/tts_history.jsonl"
mkdir -p "$(dirname "$LOG_FILE")"
echo "{\"text\":\"$(echo "$TEXT" | head -c 100 | sed 's/"/\\"/g')\",\"lang\":\"$LANG_CODE\",\"rate\":\"$RATE\",\"timestamp\":\"$(date -Iseconds)\"}" >> "$LOG_FILE"

echo "🔊 Speaking..." >&2
