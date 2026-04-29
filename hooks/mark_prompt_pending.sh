#!/usr/bin/env bash
# UserPromptSubmit hook: timestamps every new prompt so Stop hook can compare
# whether any tool was used AFTER this prompt (not just earlier in the session).
#
# Flow:
#   1. This hook fires on every user prompt → writes prompt timestamp
#   2. log_tool_used.sh fires on any tool use → writes tool timestamp
#   3. check_tool_per_response.sh Stop hook compares: tool_ts > prompt_ts?
#      If not, and response is long → block and require verification first.

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('session_id', 'default'))
" 2>/dev/null || echo "default")

PROMPT_TS_FILE="/tmp/rd_prompt_ts_${SESSION_ID}"
TOOL_TS_FILE="/tmp/rd_tool_ts_${SESSION_ID}"

# Write current epoch timestamp for this prompt
date +%s > "$PROMPT_TS_FILE"

# Clear the tool-used marker so this turn starts fresh
# (prevents a tool used in turn N from satisfying the gate for turn N+1)
rm -f "$TOOL_TS_FILE"

exit 0
