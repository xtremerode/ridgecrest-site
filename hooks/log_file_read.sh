#!/usr/bin/env bash
# PostToolUse(Read) hook: tracks that source files were actually read.
# Creates a timestamped research_done marker that the Stop hook checks.
# Appends to a session reads log for audit purposes.

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('session_id', 'default'))
" 2>/dev/null || echo "default")

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

if [ -n "$FILE_PATH" ]; then
    echo "$(date +%Y-%m-%dT%H:%M:%S) $FILE_PATH" >> "/tmp/rd_reads_${SESSION_ID}.txt"
    echo "$(date +%s)" > "/tmp/rd_research_done_${SESSION_ID}"
fi

exit 0
