# Session Handoff — 2026-04-29 (afternoon)

## What Was Done This Session

Four bugs diagnosed (in the earlier morning session) and fixed (this session) across four guardrail runs. All gates passed, all pushed to GitHub on branch `ridgecrest-audit`.

---

### Run 1 — Clear 8 gallery exclusions for danville-hilltop (run_20260429_172219)
- Feature keys: gallery-delete, gallery-add
- Change: Deleted all 8 rows from `gallery_exclusions` where `slug = 'danville-hilltop'`. These were added 2026-04-29 at 16:13. All 8 images are now re-addable.

---

### Run 2 — ICC color profile fix — three call sites (run_20260429_173239)
- Feature keys: server-webp, server-routes, pages-card
- Root cause: `_to_webp()` and two sibling functions used `img.convert('RGB')` which strips ICC profiles without color-space conversion. iPhone P3 / DSLR AdobeRGB photos came out with shifted colors (oversaturated reds, shifted shadows).
- Fix: All three call sites now extract the ICC profile, use `PIL.ImageCms.profileToProfile()` to convert to sRGB, fall back to plain `.convert('RGB')` if the profile data is malformed.
- Locations fixed: `_to_webp()` (line ~4195), `/paste/upload` (line ~5428), `/admin/api/images/adjust` subprocess template (line ~10382).
- Images uploaded BEFORE this fix are already stored as flat sRGB WebPs — the fix applies to new uploads only.

---

### Run 3 — Replace-image endpoint + JS routing (run_20260429_173630)
- Feature keys: gallery-add, pages-card
- Root cause: The "+" upload button on gallery cards sent files to `/admin/api/images/upload` then called `_doSaveCard()`, which bails for `-gal-` card IDs and never writes to `gallery_json`. No replace endpoint existed.
- Fix:
  1. New endpoint `POST /admin/api/gallery/<slug>/replace-image` — saves file, runs `_to_webp()`, generates `_1920w/_960w/_480w/_201w` variants, swaps old hash with new hash in `gallery_json`, re-renders the project HTML.
  2. JS upload handler in the card pill overlay now branches: if `isGalleryItem && _curHash`, routes to replace-image with the old hash; otherwise keeps `/admin/api/images/upload` for non-gallery cards.
  3. After success, updates `data-gallery-hash` on the card element to the new hash.
  4. Playwright test added: `gallery_upload_btn` check verifies the "+" button is present in each gallery item pill.

---

### Run 4 — Media Library upload routing (run_20260429_174237)
- Feature key: gallery-add
- Root cause: The "+ Upload" button in `preview/admin/media.html` always called `/media/receive` (base64 JSON), which saves to `images-opt/` but never touches `gallery_json`.
- Fix: `handleUpload()` in `media.html` now checks `_activeProjectFilter`. If a specific project tab is active, it looks up `gallery_project_slug` from `_libraryItems`, then routes through `/admin/api/gallery/<slug>/add-image` (multipart FormData) so the upload lands in the gallery immediately. Falls back to `/media/receive` on the "All" tab or if no slug is findable. 409 exclusion errors are surfaced with a clear user-facing message.

---

## What Is Still Open

- **DSC_7150** — exclusions are now cleared (Run 1), replace endpoint is live (Run 3). Henry can re-upload DSC_7150 via the gallery card "+" button and it will persist in the gallery.
- **Edit pills invisible on diff__zone investment cards** — z-index stacking bug from prior sessions. Still unresolved.
- **set-version doesn't update static non-portfolio pages** — still a known gap.
- **Upload pipeline: no responsive variants for /media/receive** — the `/media/receive` path (bat file uploads) still doesn't generate variants. Low priority since those images are usually then assigned to galleries, not used as card backgrounds directly.
- **Runs 1–4 are on `ridgecrest-audit` branch** — not merged to master.

## Branch State
- Branch: `ridgecrest-audit`
- Last commit: `817893f Task complete: gallery-add guardrail run run_20260429_174237`
- All clean, no uncommitted changes
