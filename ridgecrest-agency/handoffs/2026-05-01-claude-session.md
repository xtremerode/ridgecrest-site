# Session Handoff — 2026-05-01

**Branch:** ridgecrest-audit
**Last commit:** 664b673

---

## What Was Done This Session

### 1. Start-a-project iframe scrollbar — FIXED (commit 019b7f2)
- Removed collapse/lock mechanism entirely; pure accept-all postMessage resize
- `loading="eager"` added to iframe
- Playwright test added to visual_overlay_agent.py

### 2. danville-hilltop nav CTA regression — PERMANENTLY FIXED
- Template at preview_server.py line 6610 corrected; all future re-renders write `start-a-project.html`

### 3. 39 service page hero settings — COMPLETE
- Whole House Remodel, Custom Home Builder, Design-Build Contractor × 13 cities
- Gradient bottom→top, black 66%, text left, CTA left — matches screenshots 022/023/024

### 4. Portfolio featured card gradient feature — COMPLETE (commits 0692c7d, 19eb24e, 664b673)

**Part 1 (0692c7d) — G button visible:**
- Removed `cardId.indexOf('portfolio-featured-') !== 0` exclusion from G button condition in `preview_server.py`
- Added `data-gradient-id="portfolio-featured-N"` to overlay divs in `portfolio.html` (static file — superseded by Part 2)
- Updated `.portfolio-featured__overlay` CSS to `var(--rd-overlay, rgba(0,0,0,var(--card-overlay,0.5)))` in `portfolio.html`
- Added Playwright tests: `portfolio_featured_gradient_btn` and `portfolio_featured_gradient_wired`

**Part 2 (19eb24e) — Panel wiring fixed:**
- Root cause: `_render_portfolio_featured_html()` dynamically regenerates the card grid HTML on every request, overwriting the static `portfolio.html` overlay divs without `data-gradient-id`
- Fixed by adding `data-gradient-id="portfolio-featured-{slot}"` to the render function at preview_server.py line 1273
- Without this, the client-side `rd_set_gradient` listener had no `data-gradient-id` elements to attach to

**Part 3 (664b673) — Gradient persists after publish/reload:**
- Root cause: `_inject_gradient_id_overlays` ran at ~line 4944, BEFORE `_replace_portfolio_featured_grid` at ~line 5006. The grid replacement discarded all injected `--rd-overlay` styles.
- Fixed by removing the early injection call and adding it AFTER all grid/strip replacements with a comment explaining why ordering matters
- Added regression test `portfolio_featured_gradient_serve_time`: saves a gradient via PUT API, fetches public page, verifies `--rd-overlay` is in the served HTML — this test would have caught the original bug on first pass
- Fixed arg-order bug in test (`token` and `original_state` were swapped in `_restore_card_state` call)

**Also fixed during this session:**
- 65 service hero `card_settings` rows were left in `mode='color'` test artifact state by previous guardrail Playwright run — reset to `mode='image'` with correct hero_image
- 57 `card_settings` image paths normalized from bare `_mv2.webp` and `_1920w.webp` → `_960w.webp` to pass QA gate
- Server restart protocol identified: endpoint is `/admin/api/server/restart` (POST) — server runs with `use_reloader=False`, changes to `preview_server.py` require explicit restart

---

## How the Portfolio Gradient Feature Works (End State)
1. Admin opens portfolio page in admin panel → `_render_portfolio_featured_html()` generates the grid with `data-gradient-id="portfolio-featured-N"` on each overlay div
2. User hovers card → pill appears with G button (exclusion removed)
3. User clicks G → `rd_gradient_open` postMessage → `pages.html` opens gradient panel
4. User adjusts gradient → `rd_set_gradient` postMessage → client-side listener sets `--rd-overlay` on `[data-gradient-id="portfolio-featured-N"]` (live preview)
5. User clicks Save → `/admin/api/cards/portfolio/portfolio-featured-N` PUT → gradient saved to `card_settings`
6. On next page load: `_inject_gradient_id_overlays()` runs AFTER all grid replacements → reads `card_settings`, injects `--rd-overlay` as inline style on the overlay div

---

## Open Items (Carried Forward)
- **3 missing Wix CDN images** — still need Henry to download from Wix and upload via bat script
- **Render review queue** — 62 cards, tool working, Henry reviewing manually
- **set-version gap** — static non-portfolio pages not updated by set-version (known gap)
- **pre-commit hook python path** — system python3 vs venv still pending

---

## Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- All features re-locked after guardrail runs
- Server restart endpoint: POST /admin/api/server/restart (requires X-Admin-Token)
