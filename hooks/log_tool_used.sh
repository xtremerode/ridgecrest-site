#!/usr/bin/env bash
# PostToolUse hook: records that at least one tool was used this turn.
# Fires on all tool types (Bash, Read, Write, Edit, Grep, Glob, etc.).
#
# The Stop hook check_tool_per_response.sh compares this timestamp against
# the prompt timestamp to determine if any tool was used THIS turn.

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('session_id', 'default'))
" 2>/dev/null || echo "default")

TOOL_TS_FILE="/tmp/rd_tool_ts_${SESSION_ID}"

# Write current epoch timestamp — overwrites on each tool call (last wins, all we need)
date +%s > "$TOOL_TS_FILE"

exit 0
