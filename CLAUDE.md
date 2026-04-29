# Ridgecrest Designs — Project Governance Rules

> **Directory-scoped rules live closer to the code they govern:**
> - `ridgecrest-agency/CLAUDE.md` — marketing strategy, campaigns, budget, Meta/Google/MSFT
> - `preview/CLAUDE.md` — image serving, HTML editing, card overlays, project page wiring
> - This file — feature locks, git protocol, execution mode, session continuity, guardrail

---

## Feature Lock System

Before editing ANY code, check the lock status:
- Run: `PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -t -c "SELECT feature_key, status FROM feature_locks WHERE status <> 'development' ORDER BY status DESC, feature_key;"`
- If ANY affected feature is **locked**: STOP. Do not edit. Tell the user it is locked.
- If ANY affected feature is **stable**: State exactly what you are changing and why before editing. Do not proceed without explicit confirmation.
- For page edits, also check: `SELECT slug, status FROM page_locks WHERE status <> 'development';`
- **IMPORTANT:** Use `<>` not `!=` in psql — `!=` causes a syntax error in this PostgreSQL version.

### Feature-to-code mapping (what to check before editing):
- Editing gallery tag/sort/delete/add code → check gallery-tag, gallery-sort, gallery-delete, gallery-add
- Editing gallery_exclusions table/logic → check gallery-delete, gallery-add
- Editing gallery.js or masonry → check gallery-masonry
- Editing lightbox.js → check gallery-lightbox
- Editing _CARD_EDIT_OVERLAY_TPL or setupCard → check pages-card
- Editing _EDIT_OVERLAY_TPL → check pages-hero
- Editing _render_project_page → check server-render
- Editing _to_webp → check server-webp
- Editing auth/token code → check server-auth
- Editing undo system → check pages-undo
- Editing toggleEditOverlay or overlay-scripts → check pages-overlay
- Editing postMessage handlers → check pages-postmessage
- Editing main.css → check frontend-css
- Editing gallery.js → check frontend-gallery
- Editing lightbox.js → check frontend-lightbox
- Editing sitemap.xml → check seo-sitemap
- Editing project page HTML files → check seo-project-pages
- Editing service page HTML files → check seo-service-pages
- Editing logo API routes → check server-routes
- Editing main.js logo injection or nav logo code → check frontend-main
- Editing settings.html admin UI → check server-routes, frontend-main
- Editing render button click handler inside `setupCard()` → check server-rerender
- Editing gallery `add-image` endpoint → check gallery-add

---

## Git Commit Protocol — MANDATORY

**Commit after every working feature. No exceptions.**

1. After every feature is tested and working → immediately `git add` the changed files and commit.
2. Never end a session with uncommitted working code.
3. Before any revert or `git checkout HEAD` → first `git stash` or commit current state. Never use `git checkout HEAD -- <files>` on files with untracked improvements.
4. Restore points restore DB + HTML only — they do NOT restore Python, JS, or CSS.
5. When in doubt, commit. A "WIP: partial feature" commit is recoverable. An overwrite is not.

### Binary asset rules
- **Never commit image/video assets to git** — `.gitignore` excludes `preview/assets/images/`, `preview/assets/images-opt/`
- **pre-push hook installed** — blocks any push that deletes tracked `.webp/.jpg/.png` files (prevents repeat of 2026-04-24 filter-repo disaster where `git filter-repo` deleted ~1,761 WebP variants from disk)
- Before ANY `git filter-repo` or history-rewriting command: back up images first, then rewrite

### GitHub remote
- Repo: `git@github.com:xtremerode/ridgecrest-site.git` (SSH key: `ridgecrest-do-server`)
- All commits push to `origin` via post-phase guardrail

---

## Execution Mode Control — MANDATORY

There are two modes: DISCUSSION and EXECUTION.

### DISCUSSION MODE (default when Henry says "discuss", "don't do anything", "just verify", "plan only", "talk to me first")
ALLOWED: Read files, SELECT queries, curl/wget to inspect pages, grep/find to search code
FORBIDDEN: Any write operation — no UPDATE/INSERT/DELETE queries, no git add/commit, no file writes, no POST/PUT/PATCH API calls, no systemctl restart, no pip install, no npm install

When in discussion mode, present findings and a numbered plan. Then stop and wait. Do NOT proceed until Henry explicitly says one of: "go ahead", "approved", "do it", "execute", "proceed".

### EXECUTION MODE (only after Henry explicitly approves)
All operations allowed per existing rules.

### Violation
If you execute in discussion mode, Henry will roll back your changes and you will have wasted both your time and his.

---

## End-to-End Verification — MANDATORY

**NEVER report a change as done until ALL THREE steps pass.**

1. **File on disk** — Confirm the file exists and has correct content.
2. **Browser URL** — Confirm HTTP 200 with correct content size. Do NOT assume a file path equals a server URL — routing may differ.
3. **Rendered effect** — Load the actual page and verify the change is visible/functional.

This applies to ALL changes: CSS, JS, images, HTML, API endpoints.

---

## Session Continuity — MANDATORY

**Every new session MUST begin by reading the full current state before doing anything else.**

### Step 1 — Read these files (in order)
1. `ridgecrest-agency/CURRENT_STATUS.md`
2. `ridgecrest-agency/PX_CHANGE_LOG.md`
3. `ridgecrest-agency/project_open_issues.md`
4. `ridgecrest-agency/handoffs/` — most recently modified file
5. `ridgecrest-agency/agency_mode.txt`
6. Most recent conversation log: `ls -t /home/claudeuser/.claude/projects/-home-claudeuser-agent/*.jsonl | head -1`

### Step 2 — Write session-start summary
Write (or overwrite) `ridgecrest-agency/handoffs/ACTIVE_SESSION.md` with: date/time, what state was found, what is open, what this session will focus on.

### Step 3 — Write session-end handoff
When Henry says "save", "done", or ends the session → write `ridgecrest-agency/handoffs/YYYY-MM-DD-claude-session.md`.

### Step 4 — Update CURRENT_STATUS.md
Before ending any session that changed campaign state, overwrite `ridgecrest-agency/CURRENT_STATUS.md` with the full current picture.

### Quick-start command
```bash
cat /home/claudeuser/agent/ridgecrest-agency/CURRENT_STATUS.md && cat /home/claudeuser/agent/ridgecrest-agency/agency_mode.txt && ls -t /home/claudeuser/agent/ridgecrest-agency/handoffs/*.md | head -3
```

---

## Mandatory Execution Guardrail — REQUIRED FOR ALL CODE CHANGES

**Every code change must go through the two-phase execution guardrail. No exceptions.**

- `./execute_task_pre.sh <feature_key> [feature_key2 ...]` — run BEFORE making any changes
- `./execute_task_post.sh` — run AFTER all changes are made

**Pre-phase gates:** concurrent run check → feature lock check → pg_dump + binary asset backup → baseline git commit → Playwright before

**Post-phase gates:** server health → Gate 2 infra tests (`test_infra.py`: 17 tests, fires every hook with exact Claude Code stdin JSON format) → Playwright after (regression diff) → git commit + 197-check QA gate → git push → audit log

**Enforcement:** `pre` writes `.task_run_context` — `post` refuses to run without it. Features re-locked via `trap` on any exit including crash. Audit log at `ridgecrest-agency/execution_logs/`.

---

## Playwright Testing Coverage — MANDATORY

When a guardrail execution touches a code path, `visual_overlay_agent.py` MUST include a test for that specific functionality **in the same guardrail execution**.

- New button in card pill → Playwright clicks it and verifies result
- New gallery item behavior → test runs against a gallery item card ID
- New card type or page type → add to `PAGES_TO_TEST`

**Before running post-phase:** list every element/function modified → confirm a test exists for each → add missing tests NOW.

**Enforced by pre-commit hook:** `_check_playwright_coverage()` in `web_dev_orchestrator.py` is a CRITICAL gate — blocks commit if `preview_server.py`, `main.js`, `gallery.js`, or `lightbox.js` is staged without `visual_overlay_agent.py` also staged. Bypass only with `--no-verify` + commit note explaining why.

---

## Known Open Gaps

Each item includes a verification hint — run it before declaring the item resolved.

1. **`set-version` gap:** Does NOT update static non-portfolio pages (`index.html`, `portfolio.html`, `about.html`, `contact.html`, `process.html`, `team.html`)
   - *Verify still open:* `grep -c 'set-version' preview/index.html preview/portfolio.html` — if 0, still unimplemented
2. **Blog index preload:** No `<link rel="preload">` when no hero is saved — dark flash on first load
   - *Verify still open:* `grep -c 'rel="preload"' preview/blog.html` — if 0, still missing
3. **QA blind spot:** Server-rendered CTA URLs in `preview_server.py` templates NOT caught by pre-commit gate — verify manually
   - *Verify still open:* check `_EDIT_OVERLAY_TPL` and `_CARD_EDIT_OVERLAY_TPL` in `preview_server.py` for any hardcoded CTA URLs
4. **Admin panel SSL:** Accessible via IP only; no subdomain/SSL — deferred by design
   - *Verify still open:* `curl -sk https://admin.ridgecrestdesigns.com` — if fails, still IP-only
5. **pre-commit hook python path** — system `python3` has Playwright; venv does NOT. Fix pending in `.git/hooks/pre-commit`
   - *Verify still open:* `head -5 .git/hooks/pre-commit | grep python` — if it references the venv, still broken

### Documentation Maintenance Protocol — MANDATORY
**After every guardrail execution and at every session end:** verify each item above against current code/DB/disk state. Remove or update any item that is no longer accurate. Add new gaps as they are discovered — always include a one-line verification hint.

The Stop hook (`hooks/check_doc_freshness.sh`) will remind you if guardrail runs have occurred since this file was last updated.

---

## Agent Conduct Rules
- **Rule 12 — Full Inventory First:** List all files, grep for pattern, read every match, confirm with Henry before touching anything
- **Rule 13 — No Stale Tasks:** Session summaries are context, not a work queue — only one atomic carry-over per session start, then stop and wait
- **Rule 14 — Single Source of Truth:** Every element has exactly one owner (DB, JS injection, or static HTML) — check what already controls it before adding new logic
- **Rule 15 — Audit Findings Must Be Sourced:** Before stating that something is not broken or not referenced, verify against ALL storage locations (`card_settings`, `page_hero_overrides`, rendered HTML files, `page_sections`). Accepting a sub-agent's "all clear" without cross-checking primary sources and reporting it as fact is a violation of this rule.

---

## Photo Studio
Standalone AI photo color grading app at `/home/claudeuser/photo_studio/` — port 8090, separate venv, zero shared code with RMA. To work on it: `cd ~/photo_studio && claude --dangerously-skip-permissions`


---

## Research Verification Enforcement (Hooks)

Analysis/diagnosis/planning responses are gated by three hooks in `.claude/settings.local.json`:

1. **`UserPromptSubmit`** (`hooks/detect_analysis_request.sh`) — detects keywords ("tell me how", "why it happened", "root cause", "diagnose", etc.) and sets a timestamped `/tmp/rd_analysis_pending_<session>` flag. Clears any prior research_done marker so stale reads don't satisfy the check.

2. **`PostToolUse(Read)`** (`hooks/log_file_read.sh`) — fires after every Read tool call. Writes a timestamped `/tmp/rd_research_done_<session>` marker and appends the file path to the session reads log.

3. **`Stop`** (`hooks/check_research_done.sh`) — if `analysis_pending` exists and no `research_done` marker exists (or research_done predates analysis_pending), **exits 2** to block the response with: "RESEARCH REQUIRED: File reads predate this analysis question."

**Why this exists**: 2026-04-26 — presented a full rotate-button diagnosis from session summary context without reading the actual source files. The summary line numbers and code snippets were from a prior Claude instance; no fresh reads were done. Three gaps were missed that only emerged when the code was actually read before the gap-check.

**What this catches**: Any time an analysis/diagnosis question is asked and I attempt to respond without using the Read tool on relevant source files since the question was asked.

## Behavioral Verification Gate — REQUIRED FOR ALL RESPONSES

**Every substantive response must be backed by a tool use in the same turn.** Three hooks enforce this behaviorally (not by keyword):

1. **`UserPromptSubmit`** (`hooks/mark_prompt_pending.sh`) — writes a prompt timestamp to `/tmp/rd_prompt_ts_<session>` and clears the tool-used marker so each turn starts fresh.

2. **`PostToolUse(Bash|Read|Write|Edit|Grep|Glob|Agent|WebFetch|WebSearch)`** (`hooks/log_tool_used.sh`) — writes a tool timestamp to `/tmp/rd_tool_ts_<session>` on any tool use.

3. **`Stop`** (`hooks/check_tool_per_response.sh`) — compares timestamps. If `tool_ts ≤ prompt_ts` (no tool used this turn) AND response length > 300 chars → **exits 2** with: "VERIFICATION GATE: Substantive response with no tool use this turn."

**Why this exists**: 2026-04-29 — complements the keyword-based research gate. The research gate only fires on analysis questions; this gate fires on ALL responses. A response that comes from memory without touching any file or system gets blocked regardless of what words appear in it.

**What this catches**: Any response over ~2-3 sentences generated purely from session context or memory without verifying current state via a tool.

---

## Agent-Added Rules

- render_approved_state QA warning: the db_approved_state.py check in the post-phase QA gate prints 'Could not check render_approved_state: 0' — this is a WARN not a FAIL. Caused by db.get_db() context manager not being available in the standalone QA environment. Does not block commits.

- Session-end protocol step: run 'python3 claude_context_agent.py --outbound "<rule>" --confirm' for any new rules, decisions, or configurations discussed this session. Show dry-run diff first; always write with --confirm. Route to correct directory CLAUDE.md — never dump everything into root CLAUDE.md.

- DO snapshot recovery rule: When recovering files from a DigitalOcean snapshot, NEVER click 'Restore droplet' — that destroys ALL current data on the live droplet. Always click 'Create droplet' to spin up a temporary separate instance from the snapshot. Rsync or copy what you need, then destroy the temp droplet. Cost: ~$0.02/hr while running.

- GitHub remote for the web project: git@github.com:xtremerode/ridgecrest-site.git (SSH). Deploy key: ridgecrest-do-server (ed25519, stored at /home/claudeuser/.ssh/ridgecrest_do). Git remote name: 'origin'. Both master and ridgecrest-audit branches are on GitHub. Future commits should push to origin automatically via post-phase guardrail.

- The Back button in the render review tool is pure navigation — it does NOT undo the Set It action. active_version stays live after clicking Back. (restoreSnapshot was removed from doBack() — 2026-04-26)

- Henry is not a coder. When he describes a system or automated behavior, Claude must identify and fill in any architectural gaps he left out (trigger timing, verification method, failure mode) and surface them explicitly before implementing. Never assume he meant to leave gaps; assume he needs Claude to complete the design.
