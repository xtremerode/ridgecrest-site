#!/usr/bin/env bash
# UserPromptSubmit hook: detects analysis/planning/diagnosis requests.
# Sets a timestamped pending flag so the Stop hook can enforce that
# source files are actually read before findings are presented.
# Never blocks the user message — always exits 0.

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('session_id', 'default'))
" 2>/dev/null || echo "default")

PROMPT=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('user_prompt', '').lower())
" 2>/dev/null || echo "")

# Keywords that indicate a diagnosis, root-cause, planning, OR bug-report request.
# Two classes:
#   1. Explicit analysis requests ("diagnose", "root cause", "why did")
#   2. Bug reports ("not working", "scroll bar", "broken", "you didn't fix") —
#      these require the same discipline: measure the actual system before proposing a fix.
KEYWORDS='tell me how|why it happened|how to fix|diagnose|what.s wrong|root cause|how did|what happened|investigation|planning mode|walk me through|explain how|explain why|check for gap|check for gaps|audit|analyze|analysis|inspect|verify|what broke|what is wrong|how does it|what caused|not working|doesn.t work|isn.t working|still not|still showing|still happening|scroll.?bar|scrollbar|broken|regression|you didn.t fix|didn.t fix|new problem|see image|see screenshot|isn.t fixed|not fixed|not resolved|keeps coming back|came back|came back again|keeps breaking'

if echo "$PROMPT" | grep -qiE "$KEYWORDS"; then
    echo "$(date +%s)" > "/tmp/rd_analysis_pending_${SESSION_ID}"
    rm -f "/tmp/rd_research_done_${SESSION_ID}"
fi

exit 0
