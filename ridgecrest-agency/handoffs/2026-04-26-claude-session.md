# Session Handoff — 2026-04-26

## Session Overview
Full AI render recovery and image mapping audit session following the filter-repo disaster (2026-04-24) that deleted 1,761 WebP files from disk.

---

## Completed This Session

### 1. Snapshot Recovery (rsync from April 14 DO snapshot)
- Restored 40 base AI render files + ~160 size variants from temp droplet (209.38.153.220)
- Disk went from 131 → 171 base AI renders
- Temp droplet has since been destroyed — recovery window is closed

### 2. DB Cleanup (`db_render_cleanup.py`)
- Deleted 44 phantom `image_render_prompts` records (files that never existed)
- All stale path references resolved (startup migration had already run)
- Script saved at `/home/claudeuser/agent/db_render_cleanup.py`

### 3. Sierra Mountain Ranch Surgical Edit Recovery
- `_ai_77` recovered from snapshot (the pixel-accurate faucet edit)
- Generated missing `_ai_77_1920w.webp`
- Inserted DB record for the render
- Set as active version — cards_updated: 4, pages_updated: 2

### 4. render-review.html Portal Enhancements
- Added "✦ Render Restored" (green) / "⚠ Re-render Required" (red) badges
- Added "⚠ Re-render Only (N)" filter button to skip already-restored cards
- Added lightbox: click render image to open full-screen overlay (ESC/click to dismiss)
- Fixed Back button: now navigates without undoing the Set (was erroneously reverting active_version)
- Fixed queue endpoint: now returns active_version as render_file on load — panel shows live image immediately on refresh instead of latest render

### 5. Image Mapping Audit
- `image_labels.active_version`: 59/59 clean — all files on disk with all size variants
- `portfolio_projects.hero_img`: 18/18 using `_1920w` — clean
- 67 `card_settings` records using base `_mv2.webp` — upgraded at serve time by `_upgrade_card_images()`, no display artifact
- 139 `pages.hero_image` records using base `_mv2.webp` — non-project pages, not causing artifacts
- AI renders correctly wired in gallery `data-src` and `<img>` srcset — 59 verified

### 6. QA Gate Fix (`visual_overlay_agent.py`)
- `gallery_render_filename` check was blocking `_ai_N.webp` in `data-src` based on pre-AI-render rule
- Fixed: unsized AI render base files are now valid in `data-src` when active version is set
- Only sized variants (`_960w`, `_1920w`, etc.) are still blocked
- Updated `preview/CLAUDE.md` three-tier rule to document correct lightbox behavior

### 7. Missing Wix CDN Images Investigation
Confirmed 3 images genuinely missing from server — not recoverable from snapshot (droplet gone), Wix CDN returns 403 from DO server IP:

| Hash | Projects | Notes |
|---|---|---|
| `ff5b18_c5cb0ea7` | Pleasanton Custom (photo 42) + Pleasanton Cottage Kitchen (photo 4) | Tighter farmhouse sink shot — different angle from hero |
| `ff5b18_98f97a76` | Pleasanton Custom (photo 77, Construction section) | Construction photo |
| `ff5b18_238b56fc` | Sierra Mountain Ranch (photo 61) | .jpg format |

**Action required from Henry**: Download these 3 images from Wix media library, upload via `migrate_missing_gallery_images.bat`

---

## Open Items for Next Session

1. **Wix CDN missing images** — Henry to download and upload via bat script (3 images, details above)
2. **Render review queue** — Henry at image 2 of 62; all 62 show "✦ Render Restored"; tool now works correctly (active version shown on load, Back navigates without undoing)
3. **DB stale path cleanup** — 67 `card_settings` + 139 `pages.hero_image` using base `_mv2.webp`; serve-time upgrade handles display but DB should be cleaned up eventually
4. **`pleasanton-custom.html` data-src** — One gallery item (`ff5b18_9cd0d8a66b`) has `_ai_2.webp` in data-src per DB active_version; QA gate now passes this correctly

---

## Git State
- Branch: `ridgecrest-audit`
- Last commit: `3631a8a` — "Task complete: server-rerender server-routes guardrail run run_20260426_070617"
- All features locked, pushed to origin

## Server State
- Server healthy: HTTP 302
- Port 8081, running latest code
- All feature locks: locked

## Key Files Changed This Session
- `preview_server.py` — render queue endpoint returns active_version as render_file
- `preview/admin/render-review.html` — Back button fix, lightbox, badges, filter
- `visual_overlay_agent.py` — QA gate allows AI render base in data-src
- `preview/CLAUDE.md` — three-tier lightbox rule updated
- Multiple project HTML pages re-rendered with correct AI render wiring
