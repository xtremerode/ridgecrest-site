# Project Open Issues — Ridgecrest Designs

Tracking file for known issues, lost features, and pending work.
Updated by both Perplexity Computer and Claude Code.

---

## Resolved (April 12, 2026)

- [x] AI rerender button opens media library in new tab → Fixed: uses postMessage to open modal on current page
- [x] Back button cycles endlessly through pool → Fixed: history stack, stops at original
- [x] Forward cycling inconsistent order → Pool populated from pages/images API, order consistent
- [x] Gallery images missing Browse All + back button → Added to gallery items
- [x] <img> tag AI pill opens media library → Fixed: uses postMessage
- [x] _pickVariant / _swapBg responsive image swap → Rebuilt in main.js
- [x] 776 gallery image refs pointing to oversized originals → Fixed to _1920w
- [x] 62 card_settings using full-size files → Fixed to _960w
- [x] Eyebrow color inconsistent across site → Fixed in source CSS
- [x] --font-body, --font-serif, --gold undefined → Added to :root
- [x] overrides.css not loading on service pages → Fixed path
- [x] Service card overlay was gradient → Fixed to solid 0.5/0.3
- [x] Favicon was invisible → Rebuilt from RD monogram JPG

## Resolved (April 2026 — verified 2026-04-28)

- [x] Section resize drag handles — fully built: `_SECTION_RESIZE_TPL` injected via `preview_server.py`, postMessage saves heights per device
- [x] services.html and team.html hero restructure — both pages use correct `page-hero page-hero--service` structure
- [x] Tonya Wilson headshot (team-member-9) — photo uploaded, in DB (`team_members.photo`), file on disk at `images-opt/upload_1777247683_Tonya_Wilson...`
- [x] AI render review queue (filter-repo recovery) — render review complete per Henry (2026-04-28); 59 active versions set in DB
- [x] Wix CDN missing images — `ff5b18_c5cb0ea7` and `ff5b18_238b56fc` recovered to `images-opt/`; `ff5b18_98f97a76` accepted as lost and removed from gallery HTML

## Deferred (Not Yet Built)

- [ ] CSS staging preview system — approve/discard wrapper for CSS changes before going live
- [ ] Elevate Scheduling wrapper — page built, needs user testing on mobile

## Known Limitations

- 104 of 105 pages are locked — by design (Henry's guardrail). Unlock via lock button before editing.
- Feature locks block all editing tools — unlock in admin Locks panel.
- Cross-origin iframe (Elevate) can't auto-resize — uses fixed 1200px height on mobile.
