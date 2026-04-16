# Session Handoff — 2026-04-16 Claude Code

## What Was Done This Session

### Admin Panel Bugs Fixed
1. **Wrong-page hero save bug (root cause fixed)** — `currentSlug` was stale when iframe navigated internally (e.g. footer links). Added save-flush before slug update plus full pending state clearing in iframe `load` handler.
2. **Publish race condition fixed** — Publish button now awaits `saveNow()` before running snapshot.
3. **Card image active versions in snapshots** — `_snapshot_page()` now resolves active versions for card images (was doing raw query before).
4. **Page lock UI/DB sync fixed** — `loadPage()` now awaits `/admin/api/locks/check` synchronously instead of fire-and-forget background fetch. DB truth applied before user can interact.
5. **423 error handling in saveNow()** — Added `_putAPI()` wrapper that surfaces HTTP 423. Shows "Page is locked — unlock it first" in status bar instead of silently failing.
6. **All 103 page locks reset** — `UPDATE page_locks SET status = 'development' WHERE status = 'locked'` — pages had been locked since April 3.

### Hero Restructure
Applied left-aligned hero + "Start Your Project" button to secondary pages:
- `about.html` ✓, `process.html` ✓, `contact.html` ✓, `portfolio.html` ✓
- Portfolio had stale `hero_text_x=-33, hero_text_y=159` in both `pages` and `published_snapshots` tables — reset to 0.
- `services.html` and `team.html` still pending (doing one page at a time per Henry's instruction)
- Service category pages (kitchen, bathroom, whole-house, custom) skipped — Henry likes them as-is
- All 9 project pages skipped — already have correct layout

### Rules Added
- **Rule 12: Full Inventory Before Touching Any Files** — added to `ridgecrest-agency/rules/AGENT_RULES.md`. Must list all files, grep for pattern, read every match, confirm with Henry before writing any code.

### CSS/JS Architecture Changes
- `main.css`: Added `.page-hero--left` modifier + `.page-hero__inner` styles + mobile transform resets
- `main.js`: Extended `__RD_HERO_TEXT_X/Y` querySelector to include `.page-hero__inner`
- `preview_server.py`: Overlay drag handle targets `.hero__content, .page-hero__inner` — **requires server restart to activate** (`sudo systemctl restart preview_server.service`)

## Pending / Incomplete
- `services.html` — needs inner wrapper + left-align + CTA (do next, one page at a time)
- `team.html` — needs same
- Server restart needed for drag handle to work on secondary pages in admin edit mode

## What Next Session Should Read First
1. This file
2. `CLAUDE.md` Section 24 — hero restructure status table
3. `memory/project_current_state.md`

## Key Decisions Henry Made
- Service category pages (kitchen, bathroom, whole-house, custom): leave hero as-is — he likes the existing structure
- Individual project pages: leave as-is — already have correct layout
- Fix one page at a time after the portfolio fix
- `start-a-project.html` is the CTA destination for all new hero buttons
