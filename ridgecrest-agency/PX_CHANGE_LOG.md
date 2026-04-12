# Perplexity Computer Change Log

All changes made by Perplexity Computer (not Claude Code) to the Ridgecrest server.
Claude: Read this file at the start of every session so you know what was changed outside your context.

---

## 2026-04-12 ~8:00 AM PDT — Service Card Image Quality Fix + Solid Overlay
**Git commit:** 5bdd3c8
**Branch:** ridgecrest-audit

### Image Re-encoding
- Re-encoded 4 service card images (Custom Homes, Whole House, Kitchen, Bathroom) with:
  - Post-resize UnsharpMask (radius=1.0, percent=30, threshold=2) to fix stair-stepping
  - WebP method 6 (was method 4) for maximum encoder quality
  - Quality 92 (unchanged)
- Generated NEW _960w and _480w responsive variants for Custom Homes AI image (ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2_ai_77) — these did not exist before
- Originals backed up at: preview/assets/images-opt/backup_pre_px_sharpen/

### Database Changes
- card_settings: service-custom-homes image → _ai_77_960w.webp (was _ai_77.webp, no responsive variant)
- card_settings: service-kitchen-remodels image → _mv2_960w.webp (was _mv2_1920w.webp)
- DB backup at: /tmp/pre_px_sharpen_db.sql

### CSS Changes (overrides.css ONLY — main.css NOT touched)
1. Added to .service-card:
   - image-rendering: -webkit-optimize-contrast
   - image-rendering: high-quality
2. Changed service card overlay from gradient to solid:
   - Default: rgba(0,0,0,0.4) solid overlay (was gradient from opaque to transparent)
   - Hover: rgba(0,0,0,0.3) solid overlay (was slightly darker gradient)

### Files Modified
- preview/css/overrides.css (appended 2 CSS rules)
- 14 WebP files replaced in preview/assets/images-opt/
- 2 new WebP files added (_ai_77_960w.webp, _ai_77_480w.webp)
- 20 backup files created in backup_pre_px_sharpen/

---

## 2026-04-11 ~10:30 PM PDT — Meta Campaign Funnel Build
**Not a server code change — Meta Ads API only**

### New Campaigns Created
- [PX] Top of Funnel - Video Views (Campaign 6970213843893)
  - Ad Set 6970213856493, 0/day, ThruPlay optimization
  - Ad: Hook 10 (6970213883693)
  - Ad: Hook 2 Forgotten Factor (6970214185893)
- [PX] Retargeting - Conversions (Campaign 6970214205893)
  - Ad Set 6970214492493, 0/day, OFFSITE_CONVERSIONS
  - Custom Audience: Video Viewers 50% (6970214262893)
  - Ad: Hook 3 Fatal Error (6970214525893)
  - Ad: Hook 10 (6970214546893)

### Old Campaigns Paused
- [PX] Home Remodel - Hook 10 (6969359384893) — campaign + ad set paused
- [PX] Custom Home Design-Build - Hook 3 (6969359386493) — campaign + ad set paused

---

## 2026-04-11 — Google Ads Keyword Overhaul
- 246 new keywords across 7 ad groups (documented in campaigns/keyword_strategy_final_2026_04_11.md)
- 198 negative keywords
- 7 RSA ads with themed headlines
- Ad schedule expanded to 7 days with bid adjustments
- Removed Martinez (94553) from geo targeting
- Removed Custom Home Builder campaign

---

## 2026-04-12 ~8:45 AM PDT — Bulk Site-Wide Fixes
**Git commit:** 4a952bf
**Branch:** ridgecrest-audit

### CRITICAL: overrides.css path fix
- Changed injection from relative  to absolute 
- 74 service pages now correctly load overrides (nav overlay, hero height, image quality)

### CRITICAL: Page hero overlay
- Added dark overlay (rgba 0,0,0,0.45) via ::before on .page-hero and .page-hero--service
- Text now readable on Custom Homes, Whole House, Kitchen, Bathroom + all 74 service pages

### CRITICAL: 62 card_settings updated to _960w
- All gallery cards across project pages now use _960w variants
- Eliminates moiré/stair-stepping on all card backgrounds site-wide

### CRITICAL: 776 gallery image refs fixed (24 pages)
- Replaced base-file references with _1920w variants
- Estimated page weight reduction: ~500MB total across all gallery pages
- Pages fixed: all 18 project pages + portfolio + allprojects + 4 service pages

### HIGH: Eyebrow color unified
- .project-hero__eyebrow and .page-hero__eyebrow now use var(--slate-light, #80A4C8)
- All 93 pages with non-homepage eyebrows now match the slate blue theme

### HIGH: Undefined CSS variables
- Added --font-body, --font-serif, --gold to :root in overrides.css
- Fixed 5 references that were falling back to browser defaults

### HIGH: Missing responsive variant
- Generated _201w for ff5b18_238b56fc1f4249de936b8f5175e89dba_mv2 (sierra-mountain-ranch)

### Backups
- DB: /tmp/pre_px_bulk_fixes_db.sql
- Images: preview/assets/images-opt/backup_pre_px_sharpen/
