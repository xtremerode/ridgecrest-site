#!/usr/bin/env bash
# Stop hook: blocks response if an analysis question was asked but no
# source files were read in response to it.
#
# Flow:
#   1. UserPromptSubmit detects keywords → writes rd_analysis_pending_<session>
#   2. PostToolUse(Read) fires on each Read → writes rd_research_done_<session>
#   3. Stop fires → this script checks timestamps
#      - If pending exists AND research_done is NEWER than pending → pass, clear pending
#      - If pending exists AND no reads since question → exit 2 (block)

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('session_id', 'default'))
" 2>/dev/null || echo "default")

PENDING_FILE="/tmp/rd_analysis_pending_${SESSION_ID}"
DONE_FILE="/tmp/rd_research_done_${SESSION_ID}"
READS_LOG="/tmp/rd_reads_${SESSION_ID}.txt"

# No pending analysis request — nothing to enforce
if [ ! -f "$PENDING_FILE" ]; then
    exit 0
fi

PENDING_TIME=$(cat "$PENDING_FILE" 2>/dev/null || echo 0)

# No reads at all since session start
if [ ! -f "$DONE_FILE" ]; then
    echo "RESEARCH REQUIRED: Analysis was requested but no source files were read." >&2
    echo "Read the relevant files first, then present your findings." >&2
    exit 2
fi

DONE_TIME=$(cat "$DONE_FILE" 2>/dev/null || echo 0)

# Reads exist but happened BEFORE this analysis question was asked —
# the bug scenario: relying on prior-session summary without re-reading
if [ "$DONE_TIME" -lt "$PENDING_TIME" ]; then
    echo "RESEARCH REQUIRED: File reads predate this analysis question." >&2
    echo "The session summary is not a substitute for reading current source files." >&2
    echo "Read the relevant files for THIS question before stating findings." >&2
    if [ -f "$READS_LOG" ]; then
        echo "" >&2
        echo "Files read earlier this session (now stale for this question):" >&2
        cat "$READS_LOG" >&2
    fi
    exit 2
fi

# Research verified — clear the pending flag, leave reads log for audit
rm -f "$PENDING_FILE"
exit 0
