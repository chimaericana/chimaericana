#!/usr/bin/env bash
# crisis_checklist.sh — Generate crisis communication checklist
# Usage: ./crisis_checklist.sh [--type "data-breach"|"product-recall"|"executive-scandal"|"custom"] [--severity "high"|"medium"|"low"]

set -euo pipefail

TYPE="${1:-generic}"
SEVERITY="${2:-high}"

# Parse named args
while [[ $# -gt 0 ]]; do
    case $1 in
        --type) TYPE="$2"; shift 2 ;;
        --severity) SEVERITY="$2"; shift 2 ;;
        --help) echo "Usage: $0 [--type TYPE] [--severity LEVEL]"; exit 0 ;;
        *) shift ;;
    esac
done

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

cat <<EOF
═══════════════════════════════════════════════
 CRISIS COMMUNICATION CHECKLIST
 Generated: ${TIMESTAMP}
 Type: ${TYPE} | Severity: ${SEVERITY}
═══════════════════════════════════════════════

┌─ PHASE 1: IMMEDIATE RESPONSE (0-2 hours) ──┐
☐ Activate crisis communication team
☐ Designate single spokesperson
☐ Draft holding statement (acknowledge, express concern, state action)
☐ Pause all scheduled social media posts
☐ Notify internal team (employees before public)
☐ Set up monitoring for media coverage and social mentions
☐ Log all facts — no speculation
☐ Identify key stakeholders to notify directly
☐ Establish communication channel for updates
☐ Legal review of all statements

┌─ PHASE 2: ONGOING MANAGEMENT (2-24 hours) ──┐
☐ Issue official statement with facts and actions
☐ Brief customer service team with Q&A
☐ Update website with FAQ / information page
☐ Begin regular update cadence (every 2-4 hours)
☐ Monitor sentiment and adjust messaging
☐ Respond to key media inquiries
☐ Document timeline of events and responses
☐ Identify root cause and corrective actions
☐ Brief board/senior leadership
☐ Prepare for press conference if needed

┌─ PHASE 3: RECOVERY (24-72 hours) ──┐
☐ Release detailed update on corrective actions
☐ Conduct media interview (if appropriate)
☐ Address stakeholder concerns individually
☐ Publish FAQ with latest information
☐ Continue social media monitoring and response
☐ Track sentiment trends
☐ Identify lessons learned
☐ Draft long-term communication plan
☐ Schedule follow-up communications
☐ Begin reputation repair strategy

┌─ PHASE 4: POST-CRISIS (1-4 weeks) ──┐
☐ Publish comprehensive incident report
☐ Announce preventive measures
☐ Conduct team debrief and document learnings
☐ Update crisis communication plan
☐ Rebuild trust through positive communications
☐ Monitor ongoing coverage and sentiment
☐ Review and improve monitoring systems
☐ Conduct crisis simulation for future readiness
☐ Archive all communications for records
☐ Report to board on crisis handling

═══════════════════════════════════════════════
 HOLDING STATEMENT TEMPLATE
═══════════════════════════════════════════════

"We are aware of [situation] and take it very seriously.
Our top priority is [safety/customers/trust/integrity].
We are currently [investigating/taking action] and will
provide an update by [time]. We will share more information
as it becomes available."

═══════════════════════════════════════════════
 DO's and DON'Ts
═══════════════════════════════════════════════

✓ DO acknowledge the situation quickly
✓ DO express empathy and concern
✓ DO state what you're doing about it
✓ DO provide regular updates
✓ DO be transparent about what you know

✗ DON'T speculate or guess
✗ DON'T blame others prematurely
✗ DON'T use legal jargon or deflect
✗ DON'T go silent — absence creates rumors
✗ DON'T respond emotionally or defensively

EOF

echo ""
echo "Checklist saved. Mark items as complete as you progress."
echo "For severity: ${SEVERITY} — escalate to senior leadership immediately if high."
