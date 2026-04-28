#!/bin/bash
# Stop hook: remind Claude to update Known Open Gaps if guardrail runs have
# occurred since CLAUDE.md was last committed.
# Non-blocking (exit 0) — prints a reminder only.

AGENT_DIR="/home/claudeuser/agent"
EXEC_LOGS="$AGENT_DIR/ridgecrest-agency/execution_logs"

# Timestamp of last git commit that touched CLAUDE.md
LAST_DOC_COMMIT=$(git -C "$AGENT_DIR" log -1 --format="%ct" -- CLAUDE.md 2>/dev/null)
if [ -z "$LAST_DOC_COMMIT" ]; then
    exit 0
fi

# Most recent execution log file
LATEST_LOG=$(ls -t "$EXEC_LOGS"/*_audit.json 2>/dev/null | head -1)
if [ -z "$LATEST_LOG" ]; then
    exit 0
fi

LATEST_LOG_TIME=$(stat -c %Y "$LATEST_LOG" 2>/dev/null || echo "0")

if [ "$LATEST_LOG_TIME" -gt "$LAST_DOC_COMMIT" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  DOC AUDIT REMINDER                                          ║"
    echo "║  Guardrail runs have occurred since CLAUDE.md was last       ║"
    echo "║  updated. Before ending this session:                        ║"
    echo "║  1. Verify each Known Open Gap in CLAUDE.md still applies    ║"
    echo "║  2. Remove or update any items that are now resolved         ║"
    echo "║  3. Update ridgecrest-agency/project_open_issues.md          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
fi

exit 0
