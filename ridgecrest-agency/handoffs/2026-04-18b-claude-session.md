# Session Handoff — April 18, 2026 (Session 2 — Continuation)

> This file covers the second session of the day. See `2026-04-18-claude-session.md` for the first session.

---

## What Was Done This Session

### 1. Section Grab Handles — Full Site Rollout — COMPLETE
**Problem:** Grab handles (green resize bars) were only appearing on the home page. All other pages' sections had `class="section"` as their first class, so all handles on a page shared the same section ID — conflicts, broken persistence.

**Fix:** Added unique semantic first-class names to every section on every inner page (about, contact, process, team, portfolio, services, all 4 service pages, all 9 project pages). Handles now work on all pages.

**What broke:** Initial attempt used `.portfolio-grid` as a class name for the featured section — conflicts with existing CSS rule `display:grid`. Reverted with `git revert`, then re-implemented with safe class names (`portfolio-featured`, `portfolio-items`, `founder-section`, etc.).

**Committed:** Multiple commits — reverted once, then final implementation committed cleanly.

---

### 2. Admin Panel Page-Switching Persistence Bug — COMPLETE
**Problem:** Admin panel kept jumping back to "Danville Dream" or the wrong page mid-session whenever the `siteFrame.src` was assigned. The `_savedSlug` state was being overwritten by a BroadcastChannel message that fired during navigation.

**Fix:**
- `_suppressSlugSync` flag added to all `siteFrame.src` assignment paths: `loadPage()`, BroadcastChannel handler, undo handler, `lbSaveAdjust`, `setDevice()`.
- When `_suppressSlugSync` is true, the BroadcastChannel slug update is ignored.

**Committed:** `5b0f908` + `9431f01`

---

### 3. "↩ Original" Button Removed — COMPLETE
**Problem:** An unasked-for "↩ Original" button appeared in the edit pill overlay for hero sections. It was never requested, not wired up to anything functional, and confused the UI.

**Fix:**
- Removed `heroResetBtn` block from `preview_server.py`
- Removed `window.__RD_HERO_IS_AI` global injection
- Removed `_is_ai` variable
- Removed `rd_reset_original` postMessage handler from `pages.html`

**Committed:** `81a7f61`

---

### 4. AI Re-render Blur — Codex Fix Round 1 — COMMITTED (partial fix)
**Problem:** AI-edited hero images were blurry vs. source. Gemini returns ~1024px output regardless of input; upscaling 1024→1920 inherently softens.

**Codex-generated fix (`b307cbf`):**
- Raised Gemini input cap from 1024px → 2048px
- Added Lanczos upscale after Gemini output to match source dimensions
- Added sharpening pass (UnsharpMask)
- Added size-suffix stripping regex to detect source dimensions for upscale target

**PROBLEM CREATED:** The size-suffix regex stripped `_1920w` from the About hero's filename (`_mv2_1920w.webp`), causing `orig_path_arg` to point to the raw Wix CDN 6131px original — upscaling from the wrong source.

---

### 5. Hard Refresh Page Default Bug — COMPLETE
**Problem:** Admin panel always defaulted to "Danville Dream" on hard refresh (Ctrl+R).

**Root cause:** The saved slug was in `sessionStorage` which is wiped on hard refresh.

**Fix:** Changed to `localStorage`. Slug now persists across hard refreshes and browser restarts.

**Committed:** `891815a`

---

### 6. Site-Wide Breakage — Unclosed `</script>` Tag — FIXED
**Incident:** Codex removed the `__RD_HERO_IS_AI` line from `_apply_hero_to_html` and silently removed the `</script>` closing tag that was on the same line. Every page on the site broke — browsers parsed page HTML as JavaScript.

**Fix:** One line added back: `</script>` closing tag restored in `_apply_hero_to_html`.

**Committed:** `b90e583`

**Guardrail (now in memory):** After ANY change to `_apply_hero_to_html`, run:
```bash
curl -s http://localhost:8081/view/about.html | grep -o 'window.__RD_HERO[^<]*</script>'
```

---

### 7. Admin Boot Loop Fix — COMPLETE
**Problem:** After the localStorage fix was deployed, the panel booted into an infinite redirect loop.

**Root cause:** Codex used `'index'` as the fallback slug (for `index.html`). But `_seed_pages()` converts `index.html` → slug `'home'`. The panel tried to load slug `'index'`, got a 404, and looped.

**Fix:** Changed fallback slug in `pages.html` from `'index'` → `'home'`.

**Committed:** `45711f0`

---

### 8. AI Render Blur — Root Cause Fix (About Hero) — COMPLETE
**Problem:** About hero renders were still blurry. Other images edited fine. Diagnosis: the About hero filename contains `_1920w` as part of the Wix filename (`_mv2_1920w.webp`). The Codex-added regex stripped this suffix, then used the stripped name to look up the source image dimensions — which pointed to the raw Wix original at 6131px. Gemini output at ~1024px would then be "upscaled" to 6131px, producing extreme softness.

**Fix:** One-line surgical change in `preview_server.py`. `orig_path_arg` was built from `base_filename` (post-regex). Changed to use `src_path` — the actual path of the file being edited — which already has correct dimensions.

**Before:** `orig_path_arg = os.path.join(PREVIEW_DIR, 'assets', base_filename)`
**After:** `orig_path_arg = src_path`

**Committed:** `2ceaf27`

**Guardrail:** Upscale target must ALWAYS be derived from the actual source file path (`src_path`), never from a regex-processed filename that may have had suffixes stripped.

---

### 9. Admin Panel Security — Discussion Only, Deferred
**Problem:** Admin panel cannot be accessed from a different computer.

**Root cause:** DigitalOcean cloud firewall is allowing Henry's home IP but blocking other IPs.

**Full solution identified** (not implemented):
1. Install Nginx reverse proxy
2. Add SSL via Let's Encrypt
3. Set up subdomain `admin.ridgecrestdesigns.com`
4. Admin panel accessible at `https://admin.ridgecrestdesigns.com` from anywhere
5. Firewall only needs to allow 443 (HTTPS)

**Decision:** Henry deferred this. Will return to it later.

---

## Pending Actions (Priority Order)

1. **About hero — re-render to fix existing blurry images** — `_ai_1` and `_ai_2` were generated before the fix. They need to be re-rendered once (in admin AI editor) to regenerate at correct 1920px quality. The code fix only affects new renders, not existing files on disk.
2. **Admin panel security / public access** — Nginx + SSL + subdomain (see §9 above)
3. **Section grab handles smoke test** — Henry should verify drag + persist works on: home, about, process, portfolio, contact, team, each service page, and each project page
4. **Secondary server (134.199.224.200)** — Henry needs to enable PasswordAuthentication via DO console to allow Claude to scan for missing AI renders
5. **Filmstrip sequential scan bug** — needs `server-rerender` unlock
6. **BeautifulSoup curly quote prevention** — needs `server-routes` unlock
7. **Google Ads OAuth** — Henry still needs to complete the 5-step reconnect flow at http://147.182.242.54:8081/admin/google-connect

---

## What Next Session Should Read First

1. This file (`2026-04-18b-claude-session.md`)
2. `2026-04-18-claude-session.md` — first session today (section handles, gradient G, blog fixes)
3. `project_current_state.md` in memory — updated with final state
4. CLAUDE.md §21 for server/file structure

---

## Decisions Henry Made

1. **Security deferred** — admin panel subdomain/SSL will be done later, not now
2. **Grab handles must be on all pages** — mandatory for launch
3. **Original button was not wanted and should never have been added** — removed permanently
4. **About hero blur is a real bug** — source was wrong, now fixed
5. **sessionStorage → localStorage** for page persistence approved

---

## Key Commits This Session (chronological)

| Hash | Description |
|---|---|
| `5b0f908` | Fix persistent admin panel page-switching bug |
| `9431f01` | Complete _suppressSlugSync coverage |
| `81a7f61` | Remove unwanted Original button from admin panel overlay |
| `b307cbf` | Fix AI re-render blur (Codex: 2048px input, upscale, sharpening) |
| `891815a` | Fix admin pages editor defaulting to danville-dream on hard refresh |
| `45711f0` | Fix broken admin boot loop (wrong slug fallback 'index' vs 'home') |
| `b90e583` | Fix unclosed script tag in _apply_hero_to_html |
| `2ceaf27` | Fix AI render blur on images with _1920w in original Wix filename |

---

## Campaign State (unchanged)

- Google Ads: Perplexity Test One (ID: 23734851306) — LIVE
- Meta: [PX] Top of Funnel + [PX] Retargeting — ACTIVE
- RMA: `CAMPAIGN_AUTOMATION_ENABLED=false` — manual mode
