#!/bin/bash
# collab_loop.sh — Polls COLLAB_QUEUE.md and auto-triggers Claude Code when
# Perplexity has written findings (STATUS: WAITING_FOR_CLAUDE).
#
# Run via cron or keep alive in a tmux session.
# Log: /tmp/collab_loop.log

QUEUE="/home/claudeuser/agent/ridgecrest-agency/COLLAB_QUEUE.md"
LOG="/tmp/collab_loop.log"
LOCK="/tmp/collab_loop.lock"
WORKDIR="/home/claudeuser/agent"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "=== collab_loop started ==="

while true; do
  # Skip if another instance is running
  if [ -f "$LOCK" ]; then
    log "Lock held — skipping this cycle"
    sleep 30
    continue
  fi

  STATUS=$(grep -m1 '^## STATUS:' "$QUEUE" 2>/dev/null | sed 's/## STATUS: //')

  if [ "$STATUS" = "WAITING_FOR_CLAUDE" ]; then
    touch "$LOCK"
    log "STATUS=WAITING_FOR_CLAUDE — triggering Claude Code fix session"

    PROMPT="Read /home/claudeuser/agent/ridgecrest-agency/COLLAB_QUEUE.md carefully.
Perplexity has written findings under PERPLEXITY FINDINGS.
Apply whatever fix is needed to resolve the reported issue.
Restart the preview server after applying the fix.
Add a row to the CLAUDE FIX LOG table describing what you fixed.
Change STATUS to WAITING_FOR_PERPLEXITY.
Do NOT change STATUS to DONE — only Perplexity does that.
Work autonomously until the fix is applied and server is restarted."

    cd "$WORKDIR"
    claude --dangerously-skip-permissions -p "$PROMPT" >> "$LOG" 2>&1
    EXIT_CODE=$?
    log "Claude Code session finished (exit $EXIT_CODE)"

    rm -f "$LOCK"
  elif [ "$STATUS" = "DONE" ]; then
    log "STATUS=DONE — loop complete, exiting"
    exit 0
  else
    log "STATUS=$STATUS — waiting"
  fi

  sleep 120  # poll every 2 minutes
done
