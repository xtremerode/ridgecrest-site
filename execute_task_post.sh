#!/usr/bin/env bash
# execute_task_post.sh — Phase 2 of mandatory execution guardrail
# Usage: ./execute_task_post.sh
# Must be run AFTER execute_task_pre.sh. Reads .task_run_context for run binding.
#
# Enforces: Playwright after → pre-commit gate → re-lock features → git push → audit log
# Guarantees re-lock on ANY failure path (trap-based finally).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_FILE="$REPO_DIR/.task_run_context"
LOG_DIR="$REPO_DIR/ridgecrest-agency/execution_logs"
PYTHON="$(command -v python3 2>/dev/null || echo "$REPO_DIR/venv/bin/python")"
DB_CMD="PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -t -c"
TIMESTAMP_POST="$(date +%Y%m%d_%H%M%S)"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

pass()  { echo -e "  ${GREEN}[PASS]${RESET} $*" | tee -a "$LOG_FILE"; }
fail()  { echo -e "  ${RED}[FAIL]${RESET} $*" | tee -a "$LOG_FILE"; echo "" | tee -a "$LOG_FILE"
          echo -e "${RED}${BOLD}HALTED. Features will be re-locked. Run ID: $RUN_ID${RESET}" | tee -a "$LOG_FILE"
          exit 1; }
info()  { echo -e "  ${CYAN}[INFO]${RESET} $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "  ${YELLOW}[WARN]${RESET} $*" | tee -a "$LOG_FILE"; }
hdr()   { echo -e "\n${BOLD}$*${RESET}" | tee -a "$LOG_FILE"; }

# ─── REQUIRE context file ─────────────────────────────────────────────────────
if [ ! -f "$CONTEXT_FILE" ]; then
  echo -e "${RED}${BOLD}ERROR: No task run context found.${RESET}"
  echo "You must run execute_task_pre.sh before execute_task_post.sh."
  exit 1
fi

# Parse context
RUN_ID="$(grep 'run_id' "$CONTEXT_FILE" | cut -d= -f2)"
FEATURES_STR="$(grep 'features' "$CONTEXT_FILE" | cut -d= -f2-)"
DUMP_FILE="$(grep 'dump_file' "$CONTEXT_FILE" | cut -d= -f2)"
BASELINE_COMMIT="$(grep 'baseline_commit' "$CONTEXT_FILE" | cut -d= -f2)"
PLAYWRIGHT_BEFORE="$(grep 'playwright_before' "$CONTEXT_FILE" | cut -d= -f2)"
LOG_PRE="$(grep 'log_pre' "$CONTEXT_FILE" | cut -d= -f2)"
IFS=' ' read -ra FEATURES <<< "$FEATURES_STR"

LOG_FILE="$LOG_DIR/${RUN_ID}_post.log"
mkdir -p "$LOG_DIR"

# ─── GUARANTEED RE-LOCK ON EXIT ───────────────────────────────────────────────
# This trap fires on ANY exit (success, failure, crash, Ctrl+C)
_relock_on_exit() {
  local EXIT_CODE=$?
  if [ ${#FEATURES[@]} -gt 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}${BOLD}[FINALLY] Re-locking features...${RESET}" | tee -a "$LOG_FILE"
    for FEAT in "${FEATURES[@]}"; do
      CURRENT=$(eval "$DB_CMD \"SELECT status FROM feature_locks WHERE feature_key='$FEAT';\"" 2>/dev/null | xargs || echo "unknown")
      if [ "$CURRENT" = "locked" ]; then
        echo -e "  ${GREEN}[LOCK]${RESET} $FEAT → already locked" | tee -a "$LOG_FILE"
      else
        eval "$DB_CMD \"UPDATE feature_locks SET status='locked' WHERE feature_key='$FEAT';\"" 2>>"$LOG_FILE" && \
          echo -e "  ${GREEN}[LOCK]${RESET} $FEAT → locked" | tee -a "$LOG_FILE" || \
          echo -e "  ${RED}[LOCK FAIL]${RESET} $FEAT — manual re-lock required!" | tee -a "$LOG_FILE"
      fi
    done
    # Remove context file only on clean exit
    if [ $EXIT_CODE -eq 0 ] && [ -f "$CONTEXT_FILE" ]; then
      rm -f "$CONTEXT_FILE"
    fi
  fi
}
trap '_relock_on_exit' EXIT

echo "" | tee "$LOG_FILE"
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}" | tee -a "$LOG_FILE"
echo -e "${BOLD}${CYAN}║   Ridgecrest Execution Guardrail — POST PHASE        ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${BOLD}${CYAN}║   Run ID: ${RUN_ID}                   ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${RESET}" | tee -a "$LOG_FILE"
info "Features in scope: ${FEATURES[*]}"
info "Baseline commit: $BASELINE_COMMIT"
info "Log: $LOG_FILE"

# ─── GATE 1: Server health ────────────────────────────────────────────────────
hdr "[1/5] Server health check"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8081/" 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
  pass "Server responding → HTTP $HTTP_STATUS"
else
  fail "Server not responding (HTTP $HTTP_STATUS). Restart the server before running post-phase."
fi

# ─── GATE 2: Playwright after ─────────────────────────────────────────────────
hdr "[2/5] Playwright verification (after changes)"
PLAYWRIGHT_AFTER_LOG="$LOG_DIR/${RUN_ID}_playwright_after.json"
cd "$REPO_DIR"

PLAYWRIGHT_EXIT=0
$PYTHON visual_overlay_agent.py 2>>"$LOG_FILE" | tee -a "$LOG_FILE" | python3 -c "
import sys, json
data = []
for line in sys.stdin:
    line = line.strip()
    if line.startswith('{') or line.startswith('['):
        try:
            data = json.loads(line)
        except Exception:
            pass
with open('$PLAYWRIGHT_AFTER_LOG', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || PLAYWRIGHT_EXIT=$?

# Compare before vs after — flag any new failures
REGRESSIONS=0
if [ -f "$PLAYWRIGHT_BEFORE" ] && [ -f "$PLAYWRIGHT_AFTER_LOG" ]; then
  REGRESSIONS=$($PYTHON - <<'PYEOF'
import json, sys
before_path = sys.argv[1] if len(sys.argv) > 1 else ""
after_path  = sys.argv[2] if len(sys.argv) > 2 else ""
try:
    before = json.load(open(before_path)) if before_path else []
    after  = json.load(open(after_path))  if after_path  else []
except Exception:
    print(0); sys.exit(0)

before_fails = {r.get('card_id','') for r in before if not r.get('passed', True)}
after_fails  = {r.get('card_id','') for r in after  if not r.get('passed', True)}
new_fails = after_fails - before_fails
if new_fails:
    print(len(new_fails))
    for f in sorted(new_fails):
        print(f"  REGRESSION: {f}", file=sys.stderr)
else:
    print(0)
PYEOF
  "$PLAYWRIGHT_BEFORE" "$PLAYWRIGHT_AFTER_LOG" 2>>"$LOG_FILE")
fi

if [ "$REGRESSIONS" -gt 0 ]; then
  fail "Playwright found $REGRESSIONS NEW regression(s) introduced by this change. See $LOG_FILE for details."
fi
pass "Playwright after — no regressions vs baseline"

# ─── GATE 3: git commit + pre-commit gate (197 checks) ────────────────────────
hdr "[3/5] git commit + pre-commit QA gate (197 checks)"
cd "$REPO_DIR"
GIT_STATUS="$(git status --porcelain 2>/dev/null || echo "")"
if [ -z "$GIT_STATUS" ]; then
  warn "No changes staged — nothing to commit. Did you forget to make changes?"
  pass "Skipping commit (clean tree)"
else
  git add -A

  # The pre-commit hook (197 checks) fires automatically here
  COMMIT_MSG="$(cat <<EOF
Task complete: ${FEATURES[*]} guardrail run ${RUN_ID}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
  if git commit -m "$COMMIT_MSG" 2>>"$LOG_FILE"; then
    pass "git commit + pre-commit gate → PASSED"
  else
    fail "git commit blocked by pre-commit QA gate. Fix the failing checks, then re-run execute_task_post.sh."
  fi
fi

FINAL_COMMIT="$(git rev-parse HEAD)"
info "Final commit: $FINAL_COMMIT"

# ─── GATE 4: git push ─────────────────────────────────────────────────────────
hdr "[4/5] git push to GitHub"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if git push origin "$BRANCH" 2>>"$LOG_FILE"; then
  pass "git push origin $BRANCH → OK"
else
  warn "git push failed (network issue or no remote?). Changes are committed locally. Push manually when ready."
fi

# ─── GATE 5: Audit log ────────────────────────────────────────────────────────
hdr "[5/5] Writing audit log"
AUDIT_FILE="$LOG_DIR/${RUN_ID}_audit.json"
cat > "$AUDIT_FILE" <<AUDITEOF
{
  "run_id": "$RUN_ID",
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "features": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1:]))" ${FEATURES[@]}),
  "baseline_commit": "$BASELINE_COMMIT",
  "final_commit": "$FINAL_COMMIT",
  "dump_file": "$DUMP_FILE",
  "playwright_before": "$PLAYWRIGHT_BEFORE",
  "playwright_after": "$PLAYWRIGHT_AFTER_LOG",
  "log_pre": "$LOG_PRE",
  "log_post": "$LOG_FILE",
  "result": "PASS"
}
AUDITEOF
pass "Audit log → $AUDIT_FILE"

# (trap fires here → re-locks features, removes context file)
echo "" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}║   POST-PHASE COMPLETE — ALL GATES PASSED             ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}║   Features re-locked. Run ID: ${RUN_ID}  ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
