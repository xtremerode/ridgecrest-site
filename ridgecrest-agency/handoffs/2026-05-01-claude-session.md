# Session Handoff — 2026-05-01

**Branch:** ridgecrest-audit
**Last commit:** 019b7f2

---

## What Was Done This Session

### 1. Start-a-project iframe scrollbar — FIXED (commit 019b7f2)
- **Problem:** Iframe was showing a scrollbar whenever the user clicked a field or navigated between form steps inside the Base44 embedded form.
- **Root cause:** Two mechanisms in the resize script — `locked` (500ms block after resize) and `doCollapse()` (fired on `window.blur`) — were fighting Base44's resize messages. Step 2 resize was blocked by the lock; collapse triggered on every field click.
- **Fix:** Removed collapse and lock entirely. New script accepts every `elevate-resize` postMessage unconditionally with no debounce, no collapse, no lock. Also added `loading="eager"` on the iframe.
- **Three guardrail runs** to get here (first two approaches didn't fully resolve it).
- Playwright test `start_a_project_iframe_resize` added to `visual_overlay_agent.py`.

### 2. danville-hilltop.html nav CTA regression — PERMANENTLY FIXED
- **Problem:** Every guardrail run was resetting nav CTA from `start-a-project.html` back to `contact.html`.
- **Root cause:** `gallery_type_badge_cycle` Playwright test triggers `_render_project_page()`, which was writing from the template at line 6610 of `preview_server.py` — template had `contact.html`.
- **Fix:** Changed template at line 6610 to `start-a-project.html`. All future re-renders of any project page now write the correct CTA.

### 3. 39 service page hero settings — COMPLETE
- **Task:** Set gradient and text alignment for all 39 service pages (Whole House Remodel, Custom Home Builder, Design-Build Contractor × 13 cities each).
- **Settings applied:** gradient bottom→top, tint black, opacity 66%, text left-aligned, CTA visible, hero_cta_align left — matching screenshots 022/023/024.
- **Method:** Single DB UPSERT via guardrail run. All 39 pages verified.

---

## Pending — Ready to Execute Next Session

### Portfolio featured card gradient feature
**Henry asked:** Can gradient button/tool be added to the 4 portfolio featured cards (Sierra Mountain Ranch, Pleasanton Custom, Sunol Homestead, Danville Hilltop)?

**Risk assessment delivered: LOW.** Three targeted changes:
1. Remove `cardId.indexOf('portfolio-featured-') !== 0` exclusion from gradient button condition in `preview_server.py` ~line 2213
2. Add `data-gradient-id="portfolio-featured-N"` to 4 card divs in `portfolio.html` (lines 205/214/223/232 area)
3. Update `.portfolio-featured__overlay` CSS (inline block in portfolio.html lines 113–119) to use `var(--rd-overlay, rgba(0,0,0,var(--card-overlay,0.5)))` instead of hardcoded `rgba(0,0,0,var(--card-overlay,0.5))`

**Henry has not yet approved execution.** When he says go ahead, run guardrail on `pages-card, pages-overlay`.

---

## Open Items (Carried Forward)
- **3 missing Wix CDN images** — still need Henry to download from Wix and upload via bat script
- **Render review queue** — 62 cards, tool working, Henry reviewing manually
- **DB path cleanup** — 67 card_settings + 139 pages.hero_image using base `_mv2.webp` (serve-time handles, no visual regression)
- **set-version gap** — static non-portfolio pages not updated by set-version (known gap)
- **pre-commit hook python path** — system python3 vs venv still pending

---

## Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- All features re-locked after guardrail runs
