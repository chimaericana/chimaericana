#!/usr/bin/env bash
# todo.sh — Simple todo list with priorities and status
# Usage: ./todo.sh add "Task description" [--priority high|medium|low]
#        ./todo.sh list [--status pending|done|all]
#        ./todo.sh done <id>
#        ./todo.sh delete <id>

set -euo pipefail

TODO_FILE="automations/general/todo.jsonl"

init_todo() {
    mkdir -p "$(dirname "$TODO_FILE")"
    if [[ ! -f "$TODO_FILE" ]]; then
        touch "$TODO_FILE"
    fi
}

add_todo() {
    local task="$1"
    local priority="${2:-medium}"
    local id
    id=$(date +%s%N | cut -c1-10)
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M')

    echo "{\"id\":\"$id\",\"task\":\"$task\",\"priority\":\"$priority\",\"status\":\"pending\",\"created\":\"$timestamp\"}" >> "$TODO_FILE"

    local p_icon
    case "$priority" in
        high) p_icon="🔴" ;;
        medium) p_icon="🟡" ;;
        low) p_icon="🟢" ;;
        *) p_icon="⚪" ;;
    esac

    echo "$p_icon Added [$id]: $task (priority: $priority)"
}

list_todos() {
    local status_filter="${1:-pending}"

    if [[ ! -s "$TODO_FILE" ]]; then
        echo "No tasks yet. Use: $0 add \"Task description\""
        return
    fi

    echo "📋 Todo List"
    echo "══════════════════════════════════════════════════"

    local count=0
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue

        local id task priority status
        id=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "0")
        task=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['task'])" 2>/dev/null || echo "unknown")
        priority=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['priority'])" 2>/dev/null || echo "medium")
        status=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" 2>/dev/null || echo "pending")

        # Filter by status
        if [[ "$status_filter" != "all" && "$status" != "$status_filter" ]]; then
            continue
        fi

        local s_icon p_icon
        case "$status" in
            pending) s_icon="⬜" ;;
            done) s_icon="✅" ;;
            *) s_icon="⬜" ;;
        esac
        case "$priority" in
            high) p_icon="🔴" ;;
            medium) p_icon="🟡" ;;
            low) p_icon="🟢" ;;
        esac

        echo "  $s_icon [$id] $p_icon $task"
        count=$((count + 1))
    done < "$TODO_FILE"

    echo "══════════════════════════════════════════════════"
    echo "Total: $count tasks ($status_filter)"
}

complete_todo() {
    local target_id="$1"
    local tmp
    tmp=$(mktemp)

    while IFS= read -r line; do
        local id
        id=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
        if [[ "$id" == "$target_id" ]]; then
            line=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); d['status']='done'; print(json.dumps(d))" 2>/dev/null || echo "$line")
            echo "✅ Completed task [$target_id]"
        fi
        echo "$line"
    done < "$TODO_FILE" > "$tmp"

    mv "$tmp" "$TODO_FILE"
}

delete_todo() {
    local target_id="$1"
    local tmp
    tmp=$(mktemp)

    while IFS= read -r line; do
        local id
        id=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
        if [[ "$id" != "$target_id" ]]; then
            echo "$line"
        else
            echo "🗑️  Deleted task [$target_id]"
        fi
    done < "$TODO_FILE" > "$tmp"

    mv "$tmp" "$TODO_FILE"
}

usage() {
    cat <<EOF
Simple Todo List

Usage:
  $0 add "Task" [--priority high|medium|low]
  $0 list [--status pending|done|all]
  $0 done <id>
  $0 delete <id>
  $0 help
EOF
}

init_todo

if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

case $1 in
    add)
        shift
        task="$1"
        priority="medium"
        shift 2>/dev/null || true
        while [[ $# -gt 0 ]]; do
            case $1 in
                --priority) priority="$2"; shift 2 ;;
                *) shift ;;
            esac
        done
        add_todo "$task" "$priority"
        ;;
    list)
        shift
        list_todos "${1:-pending}"
        ;;
    done)
        shift
        complete_todo "$1"
        ;;
    delete)
        shift
        delete_todo "$1"
        ;;
    help|--help) usage ;;
    *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
