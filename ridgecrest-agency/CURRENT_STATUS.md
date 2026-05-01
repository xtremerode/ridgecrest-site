# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: May 1, 2026

---

## Recent Completions (This Session)

### Start-a-project iframe scrollbar — FIXED (commit 019b7f2)
- Removed collapse/lock mechanism entirely; pure accept-all postMessage resize
- `loading="eager"` added to iframe
- Playwright test added to visual_overlay_agent.py

### Service page hero settings — SET (39 pages)
- Whole House Remodel, Custom Home Builder, Design-Build Contractor × 13 cities
- Gradient bottom→top, black 66%, text left, CTA left — matches screenshots 022/023/024

### danville-hilltop nav CTA — PERMANENTLY FIXED
- Template at preview_server.py line 6610 corrected; all future re-renders write `start-a-project.html`

---

## Pending — Next Session

### Portfolio Featured Card Gradient (APPROVED PENDING EXECUTION)
Henry approved concept; execution not yet approved.
- 4 cards: Sierra Mountain Ranch, Pleasanton Custom, Sunol Homestead, Danville Hilltop
- 3 changes needed (see 2026-05-01 handoff for details)
- Run guardrail on: pages-card, pages-overlay

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
- 67 `card_settings` records using `_mv2.webp` base path
- 139 `pages.hero_image` records using `_mv2.webp` base path

---

## Site Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: 019b7f2 (2026-05-01)
- All feature locks: locked
- Pre-commit gate: 197 checks passing

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
