# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: April 26, 2026

---

## Active Work: AI Render Recovery & Image Mapping

### Recovery Status (2026-04-26)
- filter-repo disaster (2026-04-24) deleted 1,761 WebP variants from disk
- Snapshot recovery complete: 171 base AI renders on disk (was 131, +40 recovered)
- Temp droplet 209.38.153.220 DESTROYED — no further recovery possible from snapshot
- 59 active versions set in DB — all files exist on disk with all variants
- render-review.html queue: 62 cards, all "✦ Render Restored" — **Henry in progress reviewing**

### Render Review Tool Status
- Back button: navigates without undoing Set ✓
- Panel loads with active version on refresh ✓
- Lightbox: click render to open full-screen ✓
- Filter: "⚠ Re-render Only" button hides already-set cards ✓

---

## Open Action Items

### HIGH — Requires Henry
1. **3 missing Wix CDN images** — Wix blocks DO server IP (403), images not on server anywhere:
   - `ff5b18_c5cb0ea7` → Pleasanton Custom photo 42 + Pleasanton Cottage Kitchen photo 4 (farmhouse sink close-up — different angle from hero)
   - `ff5b18_98f97a76` → Pleasanton Custom photo 77 (construction section)
   - `ff5b18_238b56fc` → Sierra Mountain Ranch photo 61 (.jpg format)
   - **Fix**: download from Wix media library → upload via `migrate_missing_gallery_images.bat`

2. **Continue render review queue** — 62 cards, tool working correctly, all showing active version on load

### MEDIUM — DB Cleanup (no display artifact, serve-time handles it)
- 67 `card_settings` records using `_mv2.webp` base path (should be `_960w`)
- 139 `pages.hero_image` records using `_mv2.webp` base path (should be `_1920w`)
- No visual regression — `_upgrade_card_images()` upgrades at serve time

---

## Image Mapping Audit Results (2026-04-26)
- `image_labels.active_version`: 59/59 clean — all files on disk with all size variants
- `portfolio_projects.hero_img`: 18/18 using `_1920w` — clean
- gallery `data-src`: 59 AI renders correctly wired, all match active_version in DB
- QA gate updated to allow AI render base files in data-src (old rule was pre-AI-render era)

---

## Site Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: 3631a8a (2026-04-26)
- All feature locks: locked
- Pre-commit gate: 211 checks passing

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged from prior sessions
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
