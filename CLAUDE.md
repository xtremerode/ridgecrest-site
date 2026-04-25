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

**Post-phase gates:** server health → Playwright after (regression diff) → git commit + 197-check QA gate → git push → audit log

**Enforcement:** `pre` writes `.task_run_context` — `post` refuses to run without it. Features re-locked via `trap` on any exit including crash. Audit log at `ridgecrest-agency/execution_logs/`.

---

## Playwright Testing Coverage — MANDATORY

When a guardrail execution touches a code path, `visual_overlay_agent.py` MUST include a test for that specific functionality **in the same guardrail execution**.

- New button in card pill → Playwright clicks it and verifies result
- New gallery item behavior → test runs against a gallery item card ID
- New card type or page type → add to `PAGES_TO_TEST`

**Before running post-phase:** list every element/function modified → confirm a test exists for each → add missing tests NOW.

---

## Known Open Gaps

1. **`set-version` gap:** Does NOT update static non-portfolio pages (`index.html`, `portfolio.html`, `about.html`, `contact.html`, `process.html`, `team.html`)
2. **Blog index preload:** No `<link rel="preload">` when no hero is saved — dark flash on first load
3. **QA blind spot:** Server-rendered CTA URLs in `preview_server.py` templates NOT caught by pre-commit gate — verify manually
4. **Admin panel SSL:** Accessible via IP only; no subdomain/SSL — deferred
5. **2 Pleasanton Custom images blocked by Wix CDN:** `ff5b18_98f97a76` and `ff5b18_c5cb0ea7` — return 403. Must be recovered from Wix media library manually.
6. **Tonya Wilson headshot** (team-member-9) — needs re-upload
7. **All AI renders** — lost in filter-repo disaster, must be redone via ✨ Render button
8. **services.html and team.html hero restructure** — still pending (reverted 2026-04-16)
9. **pre-commit hook python path** — system `python3` has Playwright; venv does NOT. Fix pending in `.git/hooks/pre-commit`

---

## Agent Conduct Rules
- **Rule 12 — Full Inventory First:** List all files, grep for pattern, read every match, confirm with Henry before touching anything
- **Rule 13 — No Stale Tasks:** Session summaries are context, not a work queue — only one atomic carry-over per session start, then stop and wait
- **Rule 14 — Single Source of Truth:** Every element has exactly one owner (DB, JS injection, or static HTML) — check what already controls it before adding new logic

---

## Photo Studio
Standalone AI photo color grading app at `/home/claudeuser/photo_studio/` — port 8090, separate venv, zero shared code with RMA. To work on it: `cd ~/photo_studio && claude --dangerously-skip-permissions`
