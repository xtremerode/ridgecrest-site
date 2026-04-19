# Session Handoff — April 19, 2026

## What Was Done This Session

### 1. Gemini Rerender Quality Improvement — COMPLETE
**Problem:** AI re-renders of architectural photos were degrading quality due to lossy JPEG input and lack of instruction to preserve spatial composition.

**Discussion context:** Henry and Jim (external advisor) proposed a fix. Claude assessed the proposal, approved 3 of the changes, rejected a 4th (`return send_file(png_bytes)`) that would have broken the existing WebP/responsive pipeline.

**Final changes applied to `preview_server.py`:**
1. **PNG input:** `img_rgb.save(buf, 'JPEG', quality=90)` → `img_rgb.save(buf, 'PNG')` — lossless input to Gemini, no DCT block artifacts at high-contrast edges
2. **Mime type:** `mime_type='image/jpeg'` → `mime_type='image/png'` — matching type declaration
3. **Prompt suffix:** Appended to every Gemini rerender prompt at call time: instructs model to preserve focal length, hardware edges (door hinges, trim lines), wood/stone grain, and not to re-center or re-crop the composition

**Rejected change:** `return send_file(png_bytes)` — would have bypassed WebP conversion, responsive size generation (_1920w/_960w/_480w/_201w), and disk save. The existing pipeline must be preserved.

**Commits:**
- Pre-change baseline: `9e134bc` — use this to revert if needed
- Post-change: `b9990ce` — live now

**Testing:** Changes deployed to dev server (auto-reloader confirmed). About page hero image is the primary test target. Henry should test AI rerender on about page hero to validate PNG quality improvement.

---

### 2. Gemini Model Discussion — No Code Change
**Current model:** `gemini-3.1-flash-image-preview` — newest version (Flash 3.1)

**Available image-editing models on this account:**
| Model | Tier | Status |
|---|---|---|
| `gemini-3.1-flash-image-preview` | Flash 3.1 | **Current** |
| `gemini-3-pro-image-preview` | Pro 3.0 | Older version, Pro tier |
| `gemini-2.5-flash-image` | Flash 2.5 | Older generation |
| `imagen-4.0-ultra/generate` | Imagen 4 | Generate-only, no editing |

**Open question:** Henry was considering whether to test `gemini-3-pro-image-preview` (older version but Pro tier = stronger instruction-following for precise edits). No decision made. Session ended before testing.

---

## Pending Actions (Priority Order)

1. **Test PNG rerender quality** — Henry should test AI rerender on about page hero at http://147.182.242.54:8082/ — compare quality to previous JPEG input
2. **Gemini model A/B test (optional)** — If PNG fix doesn't fully resolve sharpness issues, test `gemini-3-pro-image-preview` side-by-side
3. **Section grab handles smoke test** — Henry should test every page type (home, inner pages, service pages, project pages) — carried over from previous session
4. **Gradient G button smoke test on inner pages** — verify gradient saves and appears on published hero images
5. **Blog featured image test** — set a blog post featured image, save, publish, verify it shows on /blog
6. **Secondary server (134.199.224.200)** — Henry needs to enable PasswordAuthentication via DO console so Claude can search for missing AI renders
7. **Filmstrip sequential scan bug** — fix in rerender code to use directory listing instead of sequential scan (requires `server-rerender` unlock)
8. **BeautifulSoup curly quote prevention** — post-write check in `preview_server.py` (requires `server-routes` unlock)
9. **Floating CTA button** — Henry still needs to decide: fixed position vs. in-flow
10. **Google Ads OAuth** — Henry still needs to complete the 5-step reconnect flow at http://147.182.242.54:8081/admin/google-connect

---

## What Next Session Should Read First

1. This file
2. `project_open_issues.md` in memory — full bug/pending list
3. CLAUDE.md §21 for server/file structure

---

## Decisions Henry Made

1. **PNG input for Gemini rerender** — approved over JPEG, lossless is better for architectural detail
2. **Do NOT bypass existing WebP/responsive pipeline** — Jim's `send_file` approach rejected in favor of pipeline-safe change only
3. **Prompt suffix approved** — preserves focal length, hardware edges, grain, prevents recropping
4. **Model question deferred** — will test Pro model after seeing PNG fix results

---

## Feature Lock Status at Session End

Only `preview_server.py` was modified (Gemini rerender section). Other feature locks unchanged from previous session:
- `server-routes` — LOCKED
- `server-render` — may need unlock for PNG test verification
- `frontend-main` — LOCKED
- `frontend-pages-admin` — LOCKED
- `server-rerender` — LOCKED

---

## Campaign State (unchanged)

### Google Ads
- **Perplexity Test One** (ID: 23734851306) — LIVE, $200/day, 246 broad match keywords, 7 ad groups

### Meta
- **[PX] Top of Funnel - Video Views** — ACTIVE, $0/day
- **[PX] Retargeting - Conversions** — ACTIVE, $0/day
- Martinez still in targeting — pending removal

### RMA System
- `CAMPAIGN_AUTOMATION_ENABLED=false` — manual mode
