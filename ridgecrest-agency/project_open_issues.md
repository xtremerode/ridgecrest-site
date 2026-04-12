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

## Deferred (Not Yet Rebuilt)

- [ ] CSS staging preview system — approve/discard wrapper for CSS changes before going live
- [ ] Section resize drag handles — server API done, frontend JS pending
- [ ] Elevate Scheduling wrapper — page built, needs user testing on mobile

## Known Limitations

- 104 of 105 pages are locked — by design (Henry's guardrail). Unlock via lock button before editing.
- Feature locks block all editing tools — unlock in admin Locks panel.
- Cross-origin iframe (Elevate) can't auto-resize — uses fixed 1200px height on mobile.
