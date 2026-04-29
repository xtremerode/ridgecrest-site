# Session Handoff — 2026-04-29

## What Was Done This Session

### 1. Documentation Maintenance Hook + CLAUDE.md Cleanup (commit e286a87)
- Removed 4 stale Known Open Gaps from root CLAUDE.md that were already resolved:
  - Wix CDN missing images (recovered or accepted as lost)
  - Tonya Wilson headshot (confirmed in DB and on disk)
  - AI render queue (Henry confirmed complete — 59 active versions set)
  - services.html / team.html hero restructure (confirmed already done)
- Added verification hints to remaining 5 gaps so future Claude can check without guessing
- Added Documentation Maintenance Protocol section to CLAUDE.md — mandates gap verification after every guardrail run and at session end
- Added `hooks/check_doc_freshness.sh` Stop hook: compares last guardrail run timestamp vs last CLAUDE.md edit; warns if CLAUDE.md is stale
- Wired new hook into `.claude/settings.local.json`

### 2. Behavioral Verification Gate (guardrail run run_20260429_003552, commit 19c933b)
Feature key: `hooks-verification-gate`. Three new hooks now enforce that every substantive response is backed by a tool use in the same turn:
- `hooks/mark_prompt_pending.sh` (UserPromptSubmit) — writes prompt timestamp; clears tool marker
- `hooks/log_tool_used.sh` (PostToolUse: Bash|Read|Write|Edit|Grep|Glob|Agent|WebFetch|WebSearch) — writes tool timestamp
- `hooks/check_tool_per_response.sh` (Stop) — if tool_ts ≤ prompt_ts AND response >300 chars → exits 2 with VERIFICATION GATE error

All 17 infra tests passed, zero Playwright regressions. Pushed to GitHub.

This is behavioral (not keyword-based) — it monitors whether Claude actually touched any file or system, not what words appear in the response.

### 3. CLAUDE.md Updated with Verification Gate Documentation (end-of-session)
Added a new "Behavioral Verification Gate" section to root CLAUDE.md explaining all 3 hooks. This complements the existing "Research Verification Enforcement" section (which only fires on analysis-type prompts via keyword detection; this gate fires on every response).

---

## What Is Pending / Open

### HIGH PRIORITY
- **Edit pills invisible on diff__zone investment section cards** — z-index stacking bug. Two fix options: (A) attach pill to parent `.diff__visual` in `setupCard()`, or (B) remove `z-index:1` from `.diff__zone` in `main.css`. **BLOCKED: Henry must approve Option A or B before any code change.**

### Normal Priority
- **set-version doesn't update static pages** — `index.html`, `portfolio.html`, `about.html`, `contact.html`, `process.html`, `team.html` have hardcoded image paths. Fix: regeneration step in set-version endpoint.

### Low Priority / Deferred
- Blog index preload (dark flash when no hero saved)
- QA blind spot — server-rendered CTA URLs in preview_server.py templates not caught by pre-commit gate
- CSS staging preview system
- Elevate Scheduling wrapper (needs mobile testing)
- Admin panel SSL / subdomain
- Photo Studio nginx config (Henry must run in DO console; /tmp file may need to be recreated)

---

## Decisions Henry Made This Session

- Approved the verification gate hooks system (hooks-verification-gate)
- All guardrail runs PASSED — no rollbacks needed

---

## What Next Session Should Read First

1. `ridgecrest-agency/project_open_issues.md` — start with HIGH PRIORITY diff__zone edit pills item
2. `CLAUDE.md` — review updated Known Open Gaps and new Behavioral Verification Gate section
3. `ridgecrest-agency/CURRENT_STATUS.md` — campaign state
4. Most recent handoff (this file)

## Branch State
- Branch: `ridgecrest-audit`
- All changes committed and pushed to `origin`
- Last commit: `19c933b Task complete: hooks-verification-gate guardrail run run_20260429_003552`
