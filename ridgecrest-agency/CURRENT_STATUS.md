# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: May 1, 2026

---

## Recent Completions (This Session)

### Portfolio Featured Card Gradient — COMPLETE (commits 0692c7d, 19eb24e)
All 4 cards (Sierra Mountain Ranch, Pleasanton Custom, Sunol Homestead, Danville Hilltop):
- G button visible in card pill on hover
- Gradient panel wired: adjusting panel updates overlay in real-time
- Saving persists to DB; serve-time injection applies on next load
- Root cause of "not wired" bug: `_render_portfolio_featured_html()` regenerated overlay divs without `data-gradient-id` on every request — fixed at line 1273

### Start-a-project iframe scrollbar — FIXED
- Removed collapse/lock mechanism; pure accept-all postMessage resize

### 39 Service Page Hero Settings — SET
- Whole House Remodel, Custom Home Builder, Design-Build Contractor × 13 cities
- Gradient bottom→top, black 66%, text left

### danville-hilltop nav CTA — PERMANENTLY FIXED
- Template fixed at preview_server.py line 6610

---

## Open Action Items

### HIGH — Requires Henry
1. **3 missing Wix CDN images** — Wix blocks DO server IP:
   - `ff5b18_c5cb0ea7` → Pleasanton Custom photo 42 + Pleasanton Cottage Kitchen photo 4
   - `ff5b18_98f97a76` → Pleasanton Custom photo 77
   - `ff5b18_238b56fc` → Sierra Mountain Ranch photo 61 (.jpg)
   - **Fix:** download from Wix media library → upload via `migrate_missing_gallery_images.bat`

2. **Continue render review queue** — 62 cards, tool working

### MEDIUM — DB Cleanup (no display artifact, serve-time handles)
- Some `card_settings` image paths may still be base `_mv2.webp` (pre-existing, not from this session)

---

## Site Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: 19eb24e (2026-05-01)
- All feature locks: locked
- Server restart: POST /admin/api/server/restart (X-Admin-Token required; use_reloader=False)

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
