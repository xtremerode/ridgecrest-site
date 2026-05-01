# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: May 1, 2026

---

## Recent Completions (This Session)

### Portfolio Featured Card Gradient — FULLY COMPLETE (commits 0692c7d, 19eb24e, 664b673, 3f125ca)
All 4 cards (Sierra Mountain Ranch, Pleasanton Custom, Sunol Homestead, Danville Hilltop):
- G button visible in card pill on hover
- Gradient panel wired and updates overlay in real-time
- Gradient persists after publish + page reload (pipeline ordering fixed)
- Sierra Mountain Ranch image broken by Playwright test artifact — restored
- Three structural guardrail gaps closed (drift check ordering, image=None severity, restore verification)

### Sitemap Page Links — FIXED (commit 7d3bcda)
- All 102 body links were broken (root-relative hrefs, 404 from /view/ context) since April 15
- Fixed to relative paths — all links now navigate correctly
- `sitemap_links_navigable` Playwright test added — enforced on every future guardrail run

### Other (prior sessions)
- Start-a-project iframe scrollbar — FIXED
- 39 Service Page Hero Settings — SET
- danville-hilltop nav CTA — PERMANENTLY FIXED

---

## Open Action Items

### HIGH — Requires Henry
1. **3 missing Wix CDN images** — Wix blocks DO server IP:
   - `ff5b18_c5cb0ea7` → Pleasanton Custom photo 42 + Pleasanton Cottage Kitchen photo 4
   - `ff5b18_98f97a76` → Pleasanton Custom photo 77
   - `ff5b18_238b56fc` → Sierra Mountain Ranch photo 61 (.jpg)
   - **Fix:** download from Wix media library → upload via `migrate_missing_gallery_images.bat`

2. **Continue render review queue** — 62 cards, tool working

### MEDIUM — Code (small, no user impact yet)
- **`_NAV_PREFETCH_SLUGS` bug** — `preview_server.py` line 298: `'whole-home-remodels'` should be `'whole-house-remodels'`, `'therdedit'` should be `'blog'`. Affects hero image preload on nav hover for those two pages. No visible broken links.
- **Houzz profile link** — `https://www.houzz.com/pro/ridgecrestdesigns` — needs manual browser verification (server IP blocked by Houzz)

### LOW — Known Gaps
- `set-version` does not update static non-portfolio pages
- pre-commit hook python path (system vs venv) — still pending

---

## Site Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: 7d3bcda (2026-05-01)
- All feature locks: locked
- Server restart: POST /admin/api/server/restart (X-Admin-Token required)

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
