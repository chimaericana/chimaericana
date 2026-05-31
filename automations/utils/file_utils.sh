#!/usr/bin/env bash
# file_utils.sh — File and directory utility functions for automation scripts
# Source this file: source automations/utils/file_utils.sh
# Or run standalone: ./file_utils.sh <command>

# Ensure a directory exists
ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        echo "📁 Created directory: $dir"
    fi
}

# Generate a unique filename with timestamp
unique_filename() {
    local prefix="${1:-file}"
    local extension="${2:-txt}"
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local rand
    rand=$(head -c 4 /dev/urandom | xxd -p 2>/dev/null || echo "$RANDOM")
    echo "${prefix}_${timestamp}_${rand}.${extension}"
}

# Safe file write (creates backup if file exists)
safe_write() {
    local target="$1"
    local content="$2"

    if [[ -f "$target" ]]; then
        local backup="${target}.bak.$(date +%s)"
        cp "$target" "$backup"
        echo "💾 Backed up: $target → $backup"
    fi

    echo "$content" > "$target"
    echo "✅ Written: $target"
}

# Append to file with separator
append_with_separator() {
    local target="$1"
    local content="$2"
    local separator="${3:---}"

    ensure_dir "$(dirname "$target")"

    if [[ -s "$target" ]]; then
        echo "" >> "$target"
        echo "$separator" >> "$target"
        echo "" >> "$target"
    fi

    echo "$content" >> "$target"
}

# Count files in directory
count_files() {
    local dir="$1"
    local extension="${2:-*}"

    if [[ ! -d "$dir" ]]; then
        echo "0"
        return
    fi

    find "$dir" -name "*.${extension}" -type f 2>/dev/null | wc -l | tr -d ' '
}

# List recent files
recent_files() {
    local dir="$1"
    local count="${2:-10}"
    local extension="${3:-*}"

    if [[ ! -d "$dir" ]]; then
        echo "Directory not found: $dir"
        return
    fi

    echo "📋 Recent files in $dir (last $count):"
    echo "════════════════════════════════════════"
    find "$dir" -name "*.${extension}" -type f -printf '%T+ %p\n' 2>/dev/null | \
        sort -r | head -n "$count" | \
        while read -r date filepath; do
            echo "  📄 $(basename "$filepath")  ($date)"
        done
}

# Clean old files (older than N days)
clean_old_files() {
    local dir="$1"
    local days="${2:-30}"
    local extension="${3:-*}"

    if [[ ! -d "$dir" ]]; then
        return
    fi

    local count
    count=$(find "$dir" -name "*.${extension}" -type f -mtime +${days} 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$count" -gt 0 ]]; then
        echo "🧹 Found $count files older than $days days in $dir"
        find "$dir" -name "*.${extension}" -type f -mtime +${days} -delete 2>/dev/null
        echo "✅ Cleaned up $count files"
    else
        echo "✨ No files older than $days days found"
    fi
}

# File size in human readable format
file_size() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        echo "0B"
        return
    fi

    local bytes
    bytes=$(wc -c < "$file" | tr -d ' ')

    if [[ "$bytes" -lt 1024 ]]; then
        echo "${bytes}B"
    elif [[ "$bytes" -lt 1048576 ]]; then
        echo "$((bytes / 1024))KB"
    elif [[ "$bytes" -lt 1073741824 ]]; then
        echo "$((bytes / 1048576))MB"
    else
        echo "$((bytes / 1073741824))GB"
    fi
}

# Standalone mode
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        recent) recent_files "${2:-.}" "${3:-10}" "${4:-*}" ;;
        clean) clean_old_files "${2:-.}" "${3:-30}" "${4:-*}" ;;
        size) file_size "${2:-}" ;;
        unique) unique_filename "${2:-file}" "${3:-txt}" ;;
        *) echo "Usage: $0 {recent|clean|size|unique} [args...]"; exit 1 ;;
    esac
fi
