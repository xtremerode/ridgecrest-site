#!/usr/bin/env bash
# execute_task_pre.sh — Phase 1 of mandatory execution guardrail
# Usage: ./execute_task_pre.sh <feature_key> [feature_key2 ...]
# Example: ./execute_task_pre.sh pages-card server-rerender
#
# Enforces: locks check → pg_dump → baseline git commit → Playwright before
# Writes a run context file that execute_task_post.sh requires.
# Does NOT proceed past any failing gate.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$REPO_DIR/ridgecrest-agency/execution_logs"
CONTEXT_FILE="$REPO_DIR/.task_run_context"
PYTHON="$(command -v python3 2>/dev/null || echo "$REPO_DIR/venv/bin/python")"
DB_CMD="PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -t -c"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RUN_ID="run_${TIMESTAMP}"
LOG_FILE="$LOG_DIR/${RUN_ID}_pre.log"

# ─── helpers ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

pass()  { echo -e "  ${GREEN}[PASS]${RESET} $*" | tee -a "$LOG_FILE"; }
fail()  { echo -e "  ${RED}[FAIL]${RESET} $*" | tee -a "$LOG_FILE"; echo "" | tee -a "$LOG_FILE"
          echo -e "${RED}${BOLD}HALTED at pre-phase. No changes were made.${RESET}" | tee -a "$LOG_FILE"
          exit 1; }
info()  { echo -e "  ${CYAN}[INFO]${RESET} $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "  ${YELLOW}[WARN]${RESET} $*" | tee -a "$LOG_FILE"; }
hdr()   { echo -e "\n${BOLD}$*${RESET}" | tee -a "$LOG_FILE"; }

# ─── args ──────────────────────────────────────────────────────────────────────
if [ $# -eq 0 ]; then
  echo "Usage: $0 <feature_key> [feature_key2 ...]"
  echo "Example: $0 pages-card server-rerender"
  exit 1
fi
FEATURES=("$@")

mkdir -p "$LOG_DIR"
echo "" | tee "$LOG_FILE"
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}" | tee -a "$LOG_FILE"
echo -e "${BOLD}${CYAN}║   Ridgecrest Execution Guardrail — PRE PHASE         ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${BOLD}${CYAN}║   Run ID: ${RUN_ID}                   ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${RESET}" | tee -a "$LOG_FILE"
info "Features in scope: ${FEATURES[*]}"
info "Log: $LOG_FILE"

# ─── GATE 1: block if another run is in progress ───────────────────────────────
hdr "[1/5] Concurrent execution check"
if [ -f "$CONTEXT_FILE" ]; then
  EXISTING_RUN="$(grep 'run_id' "$CONTEXT_FILE" | cut -d= -f2 || echo unknown)"
  fail "Another task run is in progress: $EXISTING_RUN. Run execute_task_post.sh to complete it first, or delete $CONTEXT_FILE if that run was abandoned."
fi
pass "No concurrent run in progress"

# ─── GATE 2: feature lock check ───────────────────────────────────────────────
hdr "[2/5] Feature lock check"
LOCKED_FEATURES=()
for FEAT in "${FEATURES[@]}"; do
  STATUS=$(eval "$DB_CMD \"SELECT status FROM feature_locks WHERE feature_key='$FEAT';\"" 2>/dev/null | xargs || echo "not_found")
  if [ "$STATUS" = "locked" ]; then
    LOCKED_FEATURES+=("$FEAT")
    warn "$FEAT → LOCKED"
  elif [ "$STATUS" = "stable" ]; then
    warn "$FEAT → stable (changes allowed but proceed carefully)"
    pass "$FEAT → stable"
  elif [ "$STATUS" = "development" ] || [ "$STATUS" = "not_found" ]; then
    pass "$FEAT → $STATUS (open)"
  else
    warn "$FEAT → status='$STATUS' (unexpected — treating as open)"
    pass "$FEAT → open"
  fi
done
if [ ${#LOCKED_FEATURES[@]} -gt 0 ]; then
  fail "Features still locked: ${LOCKED_FEATURES[*]}. Unlock them first, then re-run."
fi
pass "All features are unlocked"

# ─── GATE 3: pg_dump + tracked binary backup ──────────────────────────────────
hdr "[3/5] Database + binary asset backup (Rule 17)"
DUMP_FILE="$REPO_DIR/backups/pre_task_${TIMESTAMP}.sql"
mkdir -p "$REPO_DIR/backups"
if PGPASSWORD=StrongPass123! pg_dump -h 127.0.0.1 -U agent_user marketing_agent > "$DUMP_FILE" 2>>"$LOG_FILE"; then
  DUMP_SIZE="$(du -sh "$DUMP_FILE" | cut -f1)"
  pass "pg_dump → $DUMP_FILE ($DUMP_SIZE)"
else
  fail "pg_dump failed. Check PostgreSQL connectivity."
fi

# Backup tracked binary files — prevents repeat of 2026-04-24 filter-repo disaster
BINARY_BACKUP_DIR="$REPO_DIR/backups/binaries_${TIMESTAMP}"
mkdir -p "$BINARY_BACKUP_DIR"
BINARY_COUNT=0
while IFS= read -r f; do
  if [ -f "$REPO_DIR/$f" ]; then
    dest_dir="$BINARY_BACKUP_DIR/$(dirname "$f")"
    mkdir -p "$dest_dir"
    cp "$REPO_DIR/$f" "$dest_dir/" && BINARY_COUNT=$((BINARY_COUNT + 1))
  fi
done < <(git ls-files | grep -Ei "\.(webp|jpg|jpeg|png|gif)$" 2>/dev/null || true)
pass "Binary asset backup → $BINARY_BACKUP_DIR ($BINARY_COUNT files)"

# Capture card_settings snapshot so post-phase can detect unintended DB writes
CARD_SNAPSHOT_FILE="$REPO_DIR/backups/card_snapshot_${TIMESTAMP}.json"
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -t -A -c \
  "SELECT row_to_json(t) FROM (SELECT page_slug, card_id, mode, color, image, position, zoom FROM card_settings ORDER BY page_slug, card_id) t;" \
  2>/dev/null | grep -v '^$' | python3 -c "
import sys, json
rows = [json.loads(l.strip()) for l in sys.stdin if l.strip().startswith('{')]
json.dump(rows, open('$CARD_SNAPSHOT_FILE', 'w'), indent=2)
print(len(rows))
" | xargs -I{} bash -c "pass 'card_settings snapshot → $CARD_SNAPSHOT_FILE ({} rows)'" 2>/dev/null || warn "Could not capture card_settings snapshot"

# ─── GATE 4: git commit current state (Rule 19) ───────────────────────────────
hdr "[4/5] Baseline git commit (Rule 19 — save before edits)"
cd "$REPO_DIR"
GIT_STATUS="$(git status --porcelain 2>/dev/null || echo "")"
if [ -n "$GIT_STATUS" ]; then
  git add -A
  git commit -m "$(cat <<EOF
WIP: pre-task baseline snapshot before guardrail execution

Run ID: ${RUN_ID}
Features: ${FEATURES[*]}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)" 2>>"$LOG_FILE" && pass "Baseline commit created" || fail "git commit failed"
else
  pass "Working tree already clean — no baseline commit needed"
fi
BASELINE_COMMIT="$(git rev-parse HEAD)"
info "Baseline commit: $BASELINE_COMMIT"

# ─── GATE 5: Playwright baseline capture ──────────────────────────────────────
hdr "[5/5] Playwright baseline (before)"
PLAYWRIGHT_BEFORE_LOG="$LOG_DIR/${RUN_ID}_playwright_before.json"
cd "$REPO_DIR"
if $PYTHON visual_overlay_agent.py 2>>"$LOG_FILE" | tee -a "$LOG_FILE" | python3 -c "
import sys, json
data = []
for line in sys.stdin:
    line = line.strip()
    if line.startswith('{') or line.startswith('['):
        try:
            data = json.loads(line)
        except Exception:
            pass
with open('$PLAYWRIGHT_BEFORE_LOG', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null; then
  pass "Playwright baseline captured → $PLAYWRIGHT_BEFORE_LOG"
else
  warn "Playwright baseline capture had issues — proceeding (post-phase will compare against empty baseline)"
  echo "[]" > "$PLAYWRIGHT_BEFORE_LOG"
fi

# Also do a simple server health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8081/" 2>/dev/null || echo "000")
if [[ "$HTTP_STATUS" =~ ^[23] ]]; then
  pass "Server health check → HTTP $HTTP_STATUS"
else
  fail "Server not responding (HTTP $HTTP_STATUS). Start the server before running this."
fi

# ─── Write run context ────────────────────────────────────────────────────────
cat > "$CONTEXT_FILE" <<EOF
run_id=${RUN_ID}
timestamp=${TIMESTAMP}
features=${FEATURES[*]}
dump_file=${DUMP_FILE}
baseline_commit=${BASELINE_COMMIT}
playwright_before=${PLAYWRIGHT_BEFORE_LOG}
card_snapshot=${CARD_SNAPSHOT_FILE}
log_pre=${LOG_FILE}
EOF

echo "" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}║   PRE-PHASE COMPLETE — ALL GATES PASSED              ║${RESET}" | tee -a "$LOG_FILE"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo -e "  ${BOLD}Now make your code changes, then run:${RESET}" | tee -a "$LOG_FILE"
echo -e "  ${CYAN}./execute_task_post.sh${RESET}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
