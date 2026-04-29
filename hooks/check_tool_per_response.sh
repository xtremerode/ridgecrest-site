#!/usr/bin/env bash
# Stop hook: blocks any response longer than 300 characters that was produced
# without using any tool (Read, Bash, Grep, etc.) this turn.
#
# Rationale: A substantive response that doesn't verify any current state is
# the failure mode that causes unverified claims to reach the user.
# Monitoring word choices in the response is unreliable — this gate monitors
# behavior (tool use) regardless of what words appear in the output.
#
# Gate logic:
#   prompt_ts  = timestamp written by mark_prompt_pending.sh on UserPromptSubmit
#   tool_ts    = timestamp written by log_tool_used.sh on any PostToolUse
#   If tool_ts > prompt_ts → at least one tool was used this turn → pass
#   If tool_ts ≤ prompt_ts (or missing) → no tool used → check response length
#   If response length > 300 chars → exit 2 (block, force Claude to verify)

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('session_id', 'default'))
" 2>/dev/null || echo "default")

PROMPT_TS_FILE="/tmp/rd_prompt_ts_${SESSION_ID}"
TOOL_TS_FILE="/tmp/rd_tool_ts_${SESSION_ID}"

# No prompt marker — session may have started before this hook was installed
[ ! -f "$PROMPT_TS_FILE" ] && exit 0

PROMPT_TS=$(cat "$PROMPT_TS_FILE" 2>/dev/null || echo 0)
TOOL_TS=$(cat "$TOOL_TS_FILE" 2>/dev/null || echo 0)

# Tool was used after this prompt was submitted — gate passes
[ "$TOOL_TS" -gt "$PROMPT_TS" ] && exit 0

# No tool used this turn — check response length from JSONL transcript
JSONL="/home/claudeuser/.claude/projects/-home-claudeuser-agent/${SESSION_ID}.jsonl"
[ ! -f "$JSONL" ] && exit 0

RESPONSE_LEN=$(python3 - "$JSONL" 2>/dev/null << 'PYEOF'
import sys, json

jsonl_path = sys.argv[1]
try:
    with open(jsonl_path) as f:
        lines = f.readlines()

    # Walk backwards to find the last assistant message with text content
    for line in reversed(lines):
        try:
            obj = json.loads(line.strip())
            if obj.get('type') == 'assistant':
                content = obj.get('message', {}).get('content', [])
                if isinstance(content, list):
                    for block in reversed(content):
                        if block.get('type') == 'text' and block.get('text', '').strip():
                            print(len(block['text']))
                            sys.exit(0)
        except Exception:
            pass
    print(0)
except Exception:
    print(0)
PYEOF
)

RESPONSE_LEN="${RESPONSE_LEN:-0}"

if [ "$RESPONSE_LEN" -gt 300 ]; then
    echo "" >&2
    echo "╔══════════════════════════════════════════════════════════════╗" >&2
    echo "║  VERIFICATION GATE                                           ║" >&2
    echo "║  Substantive response (${RESPONSE_LEN} chars) with no tool use this     ║" >&2
    echo "║  turn. Read relevant files or run a query before responding. ║" >&2
    echo "║  Use Read, Bash, or Grep to verify current state first.      ║" >&2
    echo "╚══════════════════════════════════════════════════════════════╝" >&2
    exit 2
fi

exit 0
