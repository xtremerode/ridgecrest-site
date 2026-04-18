# Session Handoff — April 18, 2026

## What Was Done This Session

### 1. Admin Link Navigation Fix in Edit Mode (pages.html) — COMPLETE
- **Problem:** When editMode was ON in the admin page editor, clicking links inside the iframe caused navigation, breaking the edit session.
- **Fix:** 2 lines added to the existing capture-phase click handler — `e.preventDefault()` + `e.stopPropagation()` when `editMode` is true.
- **Committed:** `331807b`

### 2. Portfolio Card Text Editing Fix (pages.html) — COMPLETE
- **Problem:** Portfolio showcase cards (Sierra Mountain Ranch, Pleasanton Custom, Sunol Homestead, Danville Dream) had h3 text non-editable because the entire card is wrapped in `<a href>`.
- **Fix:** TEXT_EDIT_SCRIPT now strips `href` from anchor wrappers in edit mode, making h3/p/li inside them focusable and editable.
- **Committed:** `b268081`

### 3. AI Re-Render Systems Check — COMPLETE (discussion mode)
- Full verification: Gemini API confirmed live (`gemini-3.1-flash-image-preview`), GEMINI_API_KEY valid, propagation to gallery pages and card_settings working, all 5 responsive variants generate correctly.
- No code changes in this phase.

### 4. Gemini Timeout Fix — COMPLETE
- **Problem:** Large source images (up to 18MB) were taking 120s+ and timing out during AI re-render.
- **Fix:** Images capped at 1024×1024 before sending to Gemini (was sending full-res). Timeout raised to 300s.
- **Committed:** `8414880`

### 5. Section Grab Handles — Extended Across All Pages — COMPLETE (multi-phase)
This was the major multi-session effort. The grab handle (green resize bar) now works on every section of every page.

**Phases:**
- Added `data-rd-section` attributes to all inner pages (about, process, portfolio, contact, team, services, all service pages)
- Fixed `SKIP_SECTIONS` to not skip generic 'section' class — all sections now get handles
- Fixed overlay `inset:0` blocking handle pointer-events on project pages
- **Persistence bug fixed:** `_updateViewportFix()` was injecting `!important` CSS for `.page-hero--service` but section heights were stored under `page-hero` — mismatch caused drag to silently not save. Fixed by proper CSS selector mapping in `_sectionHeightOverrides`.
- Fixed for all page types: hero, project-hero, page-hero, and all named inner sections
- Service page sections also fixed — sections with `class="section"` now get `data-rd-section` added

### 6. Gradient G Button — Full Site Rollout — COMPLETE
The gradient overlay control tool is now on every eligible card and hero across the site.

**Phases:**
- **Removed single-card gate:** G button was behind `cardId === 'service-custom-homes'` guard. Removed. Now applies to all cards except `team-member-*` and `portfolio-featured-*`.
- **Applied to all 10 inner page heroes:** about, contact, process, team, services, project-inquiry, bathroom-remodels, kitchen-remodels, custom-homes, whole-house-remodels — added `data-gradient-id` to hero divs.
- **Portfolio hero:** `data-gradient-id="portfolio-hero"` added.
- **Critical snapshot bug fixed:** `_snapshot_page()` SQL query was missing `gradient_type`, `gradient_tint`, `gradient_opacity` columns → gradient settings never persisted to published pages. Fixed.
- **`gradient_css` null on public pages:** `_apply_cards_to_html` was only computing `gradient_css` from live DB (staging path). Published snapshot path left it null. Fixed: normalizes `gradient_css` on every card before `json.dumps`.

### 7. Blog Admin Fixes — COMPLETE
- **Fix 1 — Browse Media Library button in blog.html:** Added a "Browse" button below the featured image URL text field. Clicking opens a full image picker modal (same grid as media library, live search). Click image → "Use Image" → path auto-fills the featured image field.
- **Fix 2 — Blog page 404 in pages.html:** "Blog (RD Edit)" in the pages dropdown was loading `/view/blog.html` (doesn't exist as a static file). Fixed to load `/blog` (actual Flask route) in three places: `loadPage()`, device toggle handler, device override reset.

### 8. Blog Featured Image Render Fix (discussion mode analysis)
- Diagnosed: when using the render modal on a blog post image, `cardId` is null, so `_notifyRenderActivated` skips propagation.
- `set-version` endpoint already propagates to `blog_posts.featured_image` (step 4, line 8061).
- Root cause: pages.html wasn't reloading the blog page after activation because it used `/view/blog.html` (the 404 path). The blog route fix above resolves this.

---

## Pending Actions (Priority Order)

1. **Section grab handles — full smoke test** — Henry should test every page type (home, inner pages, service pages, project pages) to confirm drag + persist works across all
2. **Gradient G button — smoke test on inner pages** — verify gradient saves and appears on published hero images on about, process, etc.
3. **Blog featured image test** — set a blog post featured image, save, publish, verify it shows on /blog
4. **Secondary server (134.199.224.200)** — Henry needs to enable PasswordAuthentication via DO console so Claude can search for missing AI renders (Lafayette Luxury `_ai_1`, Sierra Mountain Ranch `_ai_1` through `_ai_76`)
5. **Filmstrip sequential scan bug** — fix in rerender code to use directory listing instead of sequential scan for `_ai_N.webp` versions (requires `server-rerender` unlock)
6. **BeautifulSoup curly quote prevention** — post-write check in `preview_server.py` (requires `server-routes` unlock)
7. **Floating CTA button** — Henry still needs to decide: fixed position vs. in-flow
8. **Google Ads OAuth** — Henry still needs to complete the 5-step reconnect flow at http://147.182.242.54:8081/admin/google-connect

---

## What Next Session Should Read First

1. This file (`2026-04-18-claude-session.md`)
2. `project_open_issues.md` in memory — updated with all resolved items
3. CLAUDE.md §21 for server/file structure

---

## Decisions Henry Made

1. **Gradient gate removed from single card** — gradient applies to all cards except team-member and portfolio-featured
2. **Blog iframe should load `/blog` route** — not a static file
3. **Browse media library button added to blog admin** — approved and built
4. **Gemini image capping at 1024px** — approved, solves timeout issue
5. **Section handles must work on all 300+ pages** — full rollout mandatory before launch

---

## Feature Lock Status at Session End

All changed features were re-locked after implementation. Key locks:
- `server-routes` — LOCKED
- `server-render` — LOCKED
- `frontend-main` — LOCKED
- `frontend-pages-admin` — LOCKED
- `server-rerender` — LOCKED

---

## Campaign State (unchanged from last session)

### Google Ads
- **Perplexity Test One** (ID: 23734851306) — LIVE, $200/day, 246 broad match keywords, 7 ad groups

### Meta
- **[PX] Top of Funnel - Video Views** — ACTIVE, $0/day
- **[PX] Retargeting - Conversions** — ACTIVE, $0/day
- Martinez still in targeting — pending removal

### RMA System
- `CAMPAIGN_AUTOMATION_ENABLED=false` — manual mode
