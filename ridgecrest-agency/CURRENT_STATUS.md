# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: May 4, 2026 (Evening)

---

## Recent Completions (This Session)

### Blog Post Hero Edit Pill — FULLY WORKING (References 10027, 10029)
All three edit pill controls now work correctly on blog post heroes:
- **Gradient overlay** — G panel changes visually apply and save. Fixed by making `.post-hero__overlay` read `var(--rd-overlay, fallback)` from blog.css instead of hardcoded gradient. (commit `9be52eb`)
- **Text alignment** — L/C/R buttons apply to all content including meta row (date/category flex items). Fixed by adding `justify-content` rules for `.post-hero__meta`. (commit `9be52eb`)
- **Text block position** — Selecting left/right alignment physically moves the content block to the left/right edge of the hero. Fixed by overriding `margin: 0 auto` on `.container` with pinned margins per alignment. (commit `9fc196d`)

### Prior Session Completions (still current)
- Guardrail / Hook improvements (Measure Before Fix, research gate, bug-report keywords)
- Start-a-Project Iframe — deferred; Step 3 scrollbar accepted by Henry
- Portfolio Featured Card Gradient — COMPLETE
- Sitemap Page Links — FIXED
- 39 Service Page Hero Settings — SET
- Crop mode in rerender modal — COMPLETE
- danville-hilltop nav CTA — FIXED

---

## Open Action Items

### READY TO EXECUTE — Reference 10030
- **Portfolio section background color** — plan approved, not yet executed
- `<section class="section section--dark">` behind the four portfolio cards uses hardcoded `#1C1C1C`
- Plan: add `data-card-id="portfolio-section-bg"` to that section in `portfolio.html`
- Feature key: `seo-service-pages`
- Next session: execute immediately

### HIGH — Requires Henry
1. **3 missing Wix CDN images** — Wix blocks DO server IP:
   - `ff5b18_c5cb0ea7` → Pleasanton Custom photo 42 + Pleasanton Cottage Kitchen photo 4
   - `ff5b18_98f97a76` → Pleasanton Custom photo 77
   - `ff5b18_238b56fc` → Sierra Mountain Ranch photo 61 (.jpg)
   - **Fix:** download from Wix media library → upload via `migrate_missing_gallery_images.bat`

2. **Continue render review queue** — 62 cards remaining at `/view/admin/render-review.html`

### MEDIUM — Code (small)
- **`_NAV_PREFETCH_SLUGS` bug** — `preview_server.py` line 298: `'whole-home-remodels'` → `'whole-house-remodels'`, `'therdedit'` → `'blog'`
- **Houzz profile link** — needs manual browser verification

### LOW — Known Gaps
- `set-version` does not update static non-portfolio pages
- pre-commit hook python path (system vs venv) — pending
- Start-a-project Step 3 scrollbar — deferred by Henry

---

## Site Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: `9fc196d` (pushed to GitHub, 2026-05-04 evening)
- All feature locks: locked
- Server restart: POST /admin/api/server/restart (X-Admin-Token required)

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
