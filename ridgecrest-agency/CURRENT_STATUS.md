# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: May 1, 2026

---

## Recent Completions (This Session)

### Portfolio Featured Card Gradient — COMPLETE + REGRESSION FIXED (commits 0692c7d, 19eb24e, 664b673, 3f125ca)
All 4 cards (Sierra Mountain Ranch, Pleasanton Custom, Sunol Homestead, Danville Hilltop):
- G button visible in card pill on hover
- Gradient panel wired: adjusting panel updates overlay in real-time
- Saving persists to DB; serve-time injection applies on next load (pipeline ordering fixed)
- Sierra Mountain Ranch image was corrupted by a Playwright test with a swapped-args bug — fully restored (commit 3f125ca)
- Three structural guardrail gaps closed (see below)

### Guardrail Gaps Closed (commit 3f125ca)
1. **Drift check now runs BEFORE Playwright** — test-induced DB mutations no longer auto-pass as "expected"
2. **`image=None` is always CRITICAL FAIL in drift check** — regardless of which features are in scope
3. **`_restore_card_state` no longer swallows exceptions** — raises `RuntimeError` on failure so test corruption is never silent
4. **`portfolio_featured_gradient_serve_time` test** — now preserves original image in PUT payload (safe even if restore fails), plus verifies DB state after restore
5. **CLAUDE.md updated** with three new mandatory rules for future Claude instances

### Start-a-project iframe scrollbar — FIXED
### 39 Service Page Hero Settings — SET
### danville-hilltop nav CTA — PERMANENTLY FIXED

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
- Last commit: 3f125ca (2026-05-01)
- All feature locks: locked
- Server restart: POST /admin/api/server/restart (X-Admin-Token required; use_reloader=False)
- Portfolio page: republished after image restoration — snapshot is clean

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
