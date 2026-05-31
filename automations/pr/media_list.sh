#!/usr/bin/env bash
# media_list.sh — Manage and search media contacts database
# Usage: ./media_list.sh [--add|--search|--list|--export] [options]
# Stores contacts in automations/pr/contacts.csv

set -euo pipefail

CONTACTS_FILE="automations/pr/contacts.csv"

# Ensure contacts file exists with header
init_contacts() {
    mkdir -p "$(dirname "$CONTACTS_FILE")"
    if [[ ! -f "$CONTACTS_FILE" ]]; then
        echo "name,outlet,email,phone,beat,notes,tier" > "$CONTACTS_FILE"
    fi
}

usage() {
    cat <<EOF
Media Contact List Manager

Usage: $0 <command> [options]

Commands:
  --add       Add a new contact
  --search    Search contacts
  --list      List all contacts
  --export    Export contacts as CSV
  --delete    Delete a contact by email
  --help      Show this help

Add options:
  --name      Contact name (required)
  --outlet    Media outlet (required)
  --email     Email address
  --phone     Phone number
  --beat      Coverage beat/area
  --notes     Additional notes
  --tier      Priority tier (A, B, C)

Search options:
  --query     Search term (searches name, outlet, beat)
  --tier      Filter by tier

Examples:
  $0 --add --name "Jane Smith" --outlet "TechCrunch" --email "jane@tc.com" --beat "AI" --tier A
  $0 --search --query "AI"
  $0 --search --tier A
  $0 --list
  $0 --export > contacts_backup.csv
EOF
}

add_contact() {
    local name="" outlet="" email="" phone="" beat="" notes="" tier="B"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name) name="$2"; shift 2 ;;
            --outlet) outlet="$2"; shift 2 ;;
            --email) email="$2"; shift 2 ;;
            --phone) phone="$2"; shift 2 ;;
            --beat) beat="$2"; shift 2 ;;
            --notes) notes="$2"; shift 2 ;;
            --tier) tier="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$name" || -z "$outlet" ]]; then
        echo "Error: --name and --outlet are required" >&2
        exit 1
    fi

    # Check for duplicate email
    if [[ -n "$email" ]] && grep -qi "$email" "$CONTACTS_FILE" 2>/dev/null; then
        echo "Warning: Contact with email '$email' already exists. Updating..."
        # Remove old entry
        local tmp=$(mktemp)
        grep -vi "$email" "$CONTACTS_FILE" > "$tmp" || true
        mv "$tmp" "$CONTACTS_FILE"
    fi

    echo "$name,$outlet,$email,$phone,$beat,$notes,$tier" >> "$CONTACTS_FILE"
    echo "✅ Added: $name ($outlet) — Tier $tier"
}

search_contacts() {
    local query="" tier=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --query) query="$2"; shift 2 ;;
            --tier) tier="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$query" && -z "$tier" ]]; then
        echo "Error: Provide --query or --tier" >&2
        exit 1
    fi

    local results
    results=$(tail -n +2 "$CONTACTS_FILE" | while IFS=, read -r name outlet email phone beat notes contact_tier; do
        local match=false
        if [[ -n "$query" ]]; then
            if echo "$name $outlet $beat $notes" | grep -qi "$query"; then
                match=true
            fi
        fi
        if [[ -n "$tier" && "$contact_tier" == "$tier" ]]; then
            match=true
        fi
        if [[ "$match" == "true" ]]; then
            echo "  $name | $outlet | $email | $phone | Beat: $beat | Tier: $contact_tier"
        fi
    done)

    if [[ -z "$results" ]]; then
        echo "No contacts found."
    else
        echo "📋 Search results:"
        echo "$results"
        echo ""
        echo "Total: $(echo "$results" | wc -l | tr -d ' ') contacts"
    fi
}

list_contacts() {
    if [[ ! -f "$CONTACTS_FILE" ]] || [[ $(wc -l < "$CONTACTS_FILE") -le 1 ]]; then
        echo "No contacts yet. Use --add to add one."
        return
    fi

    echo "📋 Media Contacts Database"
    echo "═══════════════════════════════════════════════"
    tail -n +2 "$CONTACTS_FILE" | while IFS=, read -r name outlet email phone beat notes tier; do
        local tier_icon="⚪"
        case "$tier" in
            A) tier_icon="🔴" ;;
            B) tier_icon="🟡" ;;
            C) tier_icon="🟢" ;;
        esac
        echo "  $tier_icon $name | $outlet"
        echo "     📧 $email  📞 $phone"
        echo "     🎯 Beat: $beat"
        [[ -n "$notes" ]] && echo "     📝 $notes"
        echo "  ─────────────────────────────────────────"
    done

    local count=$(tail -n +2 "$CONTACTS_FILE" | wc -l | tr -d ' ')
    echo "Total: $count contacts"
}

export_contacts() {
    if [[ ! -f "$CONTACTS_FILE" ]]; then
        echo "No contacts to export." >&2
        exit 1
    fi
    cat "$CONTACTS_FILE"
}

delete_contact() {
    local email=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --email) email="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$email" ]]; then
        echo "Error: --email required for deletion" >&2
        exit 1
    fi

    local tmp=$(mktemp)
    head -1 "$CONTACTS_FILE" > "$tmp"
    tail -n +2 "$CONTACTS_FILE" | grep -vi "$email" >> "$tmp" || true
    mv "$tmp" "$CONTACTS_FILE"
    echo "✅ Deleted contact with email: $email"
}

# Main
init_contacts

if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

case $1 in
    --add) shift; add_contact "$@" ;;
    --search) shift; search_contacts "$@" ;;
    --list) list_contacts ;;
    --export) export_contacts ;;
    --delete) shift; delete_contact "$@" ;;
    --help) usage ;;
    *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
