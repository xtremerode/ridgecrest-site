# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: May 4, 2026

---

## Recent Completions (This Session)

### Guardrail / Hook Improvements — COMPLETE
Three permanent guardrail improvements shipped this session:
1. `CLAUDE.md` — "Measure Before Fix — MANDATORY" rule: diagnostic → root cause → fix (no more theorizing)
2. `hooks/detect_analysis_request.sh` — extended to catch bug-report language ("not working", "broken", "scroll bar", "you didn't fix", etc.)
3. `.claude/settings.local.json` — research gate now also satisfied by Bash tool use (not just Read)

### Start-a-Project Iframe Investigation — CLOSED (deferred)
- Root cause confirmed: Base44 ResizeObserver orphaned on wizard step transitions (new DOM node per step, no resize message for Step 3)
- Proxy approach failed: Base44 React Router 404s when path ≠ "/"
- **Final state:** reverted to pre-session state — 600px frame, MIN_H=500, direct Base44 URL
- Step 3 has a scrollbar; Henry accepted this tradeoff — will revisit later
- Do NOT retry without a new plan

### Prior Session Completions (still current)
- Portfolio Featured Card Gradient — FULLY COMPLETE
- Sitemap Page Links — FIXED (all 102 links, Playwright test added)
- 39 Service Page Hero Settings — SET
- Crop mode in rerender modal — COMPLETE
- danville-hilltop nav CTA — PERMANENTLY FIXED

---

## Open Action Items

### HIGH — Requires Henry
1. **3 missing Wix CDN images** — Wix blocks DO server IP:
   - `ff5b18_c5cb0ea7` → Pleasanton Custom photo 42 + Pleasanton Cottage Kitchen photo 4
   - `ff5b18_98f97a76` → Pleasanton Custom photo 77
   - `ff5b18_238b56fc` → Sierra Mountain Ranch photo 61 (.jpg)
   - **Fix:** download from Wix media library → upload via `migrate_missing_gallery_images.bat`

2. **Continue render review queue** — 62 cards remaining, tool working

### MEDIUM — Code (small, no user impact yet)
- **`_NAV_PREFETCH_SLUGS` bug** — `preview_server.py` line 298: `'whole-home-remodels'` should be `'whole-house-remodels'`, `'therdedit'` should be `'blog'`. Affects hero image preload on nav hover for those two pages.
- **Houzz profile link** — needs manual browser verification (server IP blocked)

### LOW — Known Gaps
- `set-version` does not update static non-portfolio pages
- pre-commit hook python path (system vs venv) — still pending
- Start-a-project Step 3 scrollbar — deferred by Henry

---

## Site Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: `fb8fe06` (2026-05-04)
- All feature locks: locked
- Server restart: POST /admin/api/server/restart (X-Admin-Token required)

---

## Agency / Campaigns
- Google Ads: on hold pending Claude Co-Work evaluation
- Meta Ads: status unchanged
- Agency mode: check `ridgecrest-agency/agency_mode.txt`
