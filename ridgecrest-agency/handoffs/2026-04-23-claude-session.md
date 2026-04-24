# Session Handoff — 2026-04-23 (Full Day — Sessions 1–5)

## What Was Done This Session

### Session 1–3 (Earlier Today — Already in Prior Handoff)
See `2026-04-23-claude-session.md` (the earlier file written mid-session). Covered:
- Card image revert on Edit Mode re-entry — fixed (`14ac88a`)
- Project page wiring (orinda-kitchen, pleasanton-cottage-kitchen, danville-dream, lafayette-bistro) — all four re-wired
- Rerender modal adjustment sliders — removed permanently (`fd5a075`)
- Home portfolio CSS hardcoded background-images — removed (`862f08a`)
- 156 services subpages — hero src changed from base `_mv2.webp` to `_mv2_1920w.webp` (`3daa150`)
- `main.js` HERO_FALLBACK — base file → `_1920w` variant (`08973b3`)

### Session 4 (2026-04-23 Afternoon)
See `2026-04-23-claude-session-4.md`.

1. **services.html primary CTA fix** (`bbc476c`) — was pointing to `contact.html`, corrected to `start-a-project.html`; added `primary_cta_destination` QA check
2. **Blog hero CTA fix** (`ba3fd9e`) — `/start-a-project.html` and `/process.html` → `/view/` prefix; both were 404ing
3. **Five-stage process model** (`781fc00`) — all 4 service pages updated from 4-step to 5-stage model matching `process.html`
4. **Service page investment image panels** (`9b7a14e`) — added `.diff__zone--top/bottom` with `data-card-id` to all 4 service pages; seeded 8 card_settings records; added 8 to required_card_records QA guard (31 total)
5. **Dark overlay fix on diff__zone Edit Mode entry** (`eee6dfc`) — initial fix using `display:none` (later revised)

### Session 5 (2026-04-23 Evening)
6. **diff__zone gradient fix** (`937a882`) — replaced `display:none` with `background: var(--rd-overlay, transparent) !important`; also fixed `applyStyle()` in `preview_server.py` to re-apply `--rd-overlay` after image swap. Gradients were silently lost whenever any BG panel image change was made. This fix covers all 17+ cards site-wide with saved gradients.

### Final QA Gate State
- **173 checks, 0 critical failures, 0 warnings**
- All commits on branch `ridgecrest-audit`

---

## What Is Pending

### BLOCKED — Needs Henry Input
- **Start-a-project iframe page 1 URL (§60):** Henry reports iframe loads on Elevate Scheduler "page 2" instead of the first step. Fix is one-liner in `start-a-project.html` + `_INQUIRY_URL` in `preview_server.py`. Blocked: Henry referenced screenshots that don't exist in downloads/ — needs to provide the correct page 1 URL directly.

### HIGH PRIORITY
- **set-version doesn't update static non-portfolio HTML pages (§29):** When a new AI render version is activated, DB + 18 project pages update but `index.html`, `portfolio.html`, `about.html`, `contact.html`, `process.html`, `team.html` are never regenerated. Hardcoded image paths can silently show stale images after AI renders are activated.

### LOW PRIORITY
- **Blog index no preload when no hero saved (§36 Gap 2):** Flash on load if no hero saved for blog index. Low priority — blog not fully live.
- **QA blind spot for server-rendered CTAs (§61):** `primary_cta_destination` check only covers static HTML — doesn't catch template bugs in `preview_server.py`.

### DEFERRED
- Photo Studio nginx command — `/tmp/nginx_ridgecrest.conf` may no longer exist; may need recreating before Henry runs the console command
- Admin panel SSL/subdomain — deferred indefinitely
- Google Ads — on hold pending Claude Co-Work evaluation

---

## What Next Session Should Read First

1. **This file** (you're reading it)
2. `ridgecrest-agency/CURRENT_STATUS.md`
3. `ridgecrest-agency/project_open_issues.md`
4. CLAUDE.md §59 (diff__zone gradient rule — never suppress `::before` with `display:none`)
5. CLAUDE.md §60 (start-a-project iframe URL — ask Henry for page 1 URL immediately)

---

## Decisions Henry Made This Session

- All project page CTAs must route through `start-a-project.html` (not directly to Base44). Base44 is the destination embedded within start-a-project.html.
- `_1920w` variant is the correct variant for ALL hero images everywhere on the site. Base file = lightbox only.
- Adjustment sliders in rerender modal are removed permanently. Color-only edits belong in the lightbox.
- Five-stage process model is canonical — all service pages must match it.
- `::before` on `.diff__zone` must NOT be suppressed with `display:none` — use `var(--rd-overlay, transparent)` so gradient surface is always present but defaults transparent.
- Investment image panels on service pages are fully wired with `data-card-id` and seeded with starter images.
- Henry acknowledged that execution errors (String not found, wrong column names) after context compression are caused by Claude assuming rather than reading first — agreed this should not be a pattern.

---

## Git Summary
Branch: `ridgecrest-audit`
Key commits this session:
- `bb2ee1f` — QA required_card_records fix + orinda-kitchen wiring
- `14ac88a` — Card revert fix + pleasanton-cottage-kitchen
- `fd5a075` — Remove adjustment sliders + danville-dream
- `862f08a` — Remove hardcoded CSS bg-images + lafayette-bistro
- `3daa150` — services subpage heroes → _1920w
- `08973b3` — main.js fallback → _1920w
- `bbc476c` — services.html CTA fix + QA guard
- `ba3fd9e` — Blog hero CTA /view/ prefix fix
- `781fc00` — Five-stage process model all 4 service pages
- `9b7a14e` — Service page investment image panels
- `eee6dfc` — diff__zone dark overlay fix (initial)
- `937a882` — diff__zone gradient rendering + applyStyle() preservation (final)
