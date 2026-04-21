# Session Handoff — 2026-04-20

## What Was Done This Session

### 1. Gemini AI Re-render Pipeline — Major Refactor

**Quality improvements applied to `preview_server.py`:**
- Switched Gemini input from lossy JPEG (quality 90) to lossless PNG
- Updated mime_type to `image/png` to match
- Added prompt suffix: "Preserve the original focal length and perspective. Do not re-center or re-compose. Maintain exact hardware edges, wood grain, stone texture, and surface detail."
- Tested Gemini 3.1 Flash vs Gemini 3 Pro image preview — user confirmed 3 Pro produced better results. Model in use is now `gemini-3-pro-image-preview`.

### 2. Surgical Toggle Workflow — Built, Debugged, and Working

A brand-new "Surgical" editing mode was added to the AI re-render pipeline:

**How it works:**
- Toggle activates "Surgical Mode" in the rerender modal
- User draws a bounding box over the specific region to fix (e.g., glare, shadow)
- Server crops that patch from the full-res master at native resolution
- Gemini edits only the patch (single-image call — no context image, which caused the model to return unchanged images)
- Patch is LANCZOS-resized to exact crop dimensions, pasted back onto a deep copy of the master
- Saved as `[original]_edit_[timestamp].webp` — original never overwritten
- Full responsive size chain regenerated from the new file

**Bugs fixed during implementation:**
1. **Crop region too small after clamping** — Python clamping had sign bug producing negative width; fixed with correct `max(0, min(master_w-1, ...))` clamp
2. **Race condition** — user could draw before `_rerenderFetchDims` returned; fixed with early-bail guard in `cropMouseDown`
3. **Gemini returning unchanged patch** — dual-image context call was invalid for editing models; fixed by sending single image only
4. **Cover-fit coordinate offset** — portrait images (1638×2048) had 191px Y offset error; fixed with proper fitScale + offX/offY cover-fit math
5. **Darkening after paste** — user resolved by selecting larger crop area for proper color match (no code change needed)
6. **Blur in result panel/lightbox** — root cause: server returned 6131px base file as `hero_path`, browser downsampled 15× making it blurry; **fixed** by returning `display_path` (1920w variant) for panel display while keeping `hero_path` as the base file for "Use This Version" logic
7. **Accidental render from responsive-size source** — server now always resolves `_1920w` / `_960w` source filenames up to the master before opening; prevents 1920px renders masking as surgical edits

**Commits:**
- `9e134bc` — pre-PNG-fix baseline
- `b9990ce` — PNG input + mime type + prompt suffix
- `f5400cb` — pre-surgical baseline
- `777da29` — surgical toggle workflow added
- `ff6ef74` — pre-clamping-fix baseline
- `46be506` — Gemini single-image + cover-fit coord fix
- `daaf09c` — clamping + race condition fix
- `0334ee2` — JS size guard + detailed error coords
- `3b25d73` — always render from master
- `736871f` — display_path fix (blur in result panel)

### 3. Gradient (G) Button — Extended to All 16 Pages

**Problem:** G button only appeared on the home page hero (gated by `el.classList.contains('hero__bg')`).

**Fix:** Broadened the condition to check for `data-gradient-id` on the element itself OR a child element — covers all hero structures site-wide.

**Also fixed:**
- Added `var(--rd-overlay, ...)` to `.project-hero__overlay` in CSS
- Added `data-gradient-id` to all 9 project page hero overlays
- Services page was confirmed already implemented but G button wasn't showing — now fixed

**Commit:** `97b845d`

### 4. Hero Text Controls — Built and Committed

New "T button" (teal) added to the edit overlay badge on all hero images, with a full Hero Text Panel in the admin:

**Controls added:**
- **Text Alignment:** left / center / right (segmented control)
- **Text Color:** Light / Dark toggle
- **CTA Visible:** Show / Hide toggle (auto-hides row on pages with no CTA element — services, team)

**Technical implementation:**
- DB: 3 new columns on `card_settings` table (`hero_text_align`, `hero_cta_visible`, `hero_text_color`)
- Server: `_inject_hero_text_controls()` injects `data-hero-text-align`, `data-hero-text-color`, `--hero-cta-display` CSS var at serve time
- CSS: attribute selector rules for all 3 hero types (home, inner pages, project pages)
- Admin: T button in overlay badge, `rd_hero_text_open` message handler, panel with save

**Commits:**
- `d848827` — add `data-hero-id` to all 16 hero root elements
- `369f1b3` — full hero text controls implementation

---

## Status At Session End

**Last known working state:** `369f1b3` — all features committed and implemented.

**What Henry tested and confirmed working:**
- Surgical edit pipeline (ran successfully, quality acceptable)
- Gradient G button now on all pages
- Hero text controls — implementation committed but user had NOT yet tested at session end (context ran out mid-implementation)

**What was NOT yet tested by user:**
- Hero text controls (T button, alignment, color, CTA toggle) — committed but Henry had not yet confirmed working in browser

---

## What Is Pending

1. **Hero text controls — user testing** — Henry needs to open admin, click T button on any hero, test alignment/color/CTA controls and confirm they work as expected
2. **Surgical edit — further iteration** — Henry mentioned glare wasn't fully removed in first pass; subsequent passes worked but blur remained (fixed in `736871f`). Should re-test on about hero with latest build.
3. **Gradient control on project pages** — G button now works on all pages per `97b845d`, but user had not confirmed project page gradients were saving/loading correctly
4. **Hero text controls on project pages** — the audit shows project pages have `.project-hero__right` for CTA; CTA display var is wired to that — needs user confirmation

---

## What Next Session Should Read First

1. **This file** (you're reading it)
2. `project_current_state.md` in memory — has DB schema, admin password, server URLs
3. Git log: `cd /home/claudeuser/agent && git log --oneline -10`
4. The admin panel at http://147.182.242.54:8081/view/admin/pages.html — password: `Hb2425hb+`

---

## Decisions Henry Made

- **Gemini model:** Use `gemini-3-pro-image-preview` (not Flash 3.1) — confirmed better results for surgical edits
- **Surgical non-destructive save:** Named `[original]_edit_[timestamp].webp` — original master never overwritten
- **Context image removed:** Gemini surgical call is single-image only (no downsampled full-frame context) — confirmed this is the right approach after testing
- **Shadow control NOT added:** Henry explicitly said he didn't ask for it; removed from scope
- **CTA control scoping:** Per-hero CTA toggle is independent of text messages; auto-hides on pages with no CTA element

---

## Key Files Modified This Session

- `/home/claudeuser/agent/preview_server.py` — Gemini PNG input, surgical pipeline, G button fix, hero text injection, display_path fix, master-source enforcement
- `/home/claudeuser/agent/preview/admin/pages.html` — surgical modal UI, T button, hero text panel
- `/home/claudeuser/agent/preview/css/main.css` — gradient overlay for project pages, hero text alignment/color/CTA CSS
- All 9 project HTML pages — `data-gradient-id` added to hero overlays
- All 16 pages — `data-hero-id` added to hero root elements
