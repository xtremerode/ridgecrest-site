# Session Handoff — 2026-04-24 Session 5

## What Was Done This Session

### 1. Service Page Gallery Cards — Gradient Fix (commit `c585a6e`)
Removed the default dark gradient from gallery card images on service pages. Default state is now clean (no gradient). Hover state shows a 0.3 opacity dark overlay. Scoped with `.gallery-grid` parent to avoid affecting project page masonry galleries.

### 2. Home Portfolio Cards — Save Blocked Fix (commit `f9bba8e`)
Henry reported home-portfolio-1 through 4 not saving when images were changed in Edit Mode. Root cause: capture-phase click interceptor in `pages.html` was killing all clicks inside anchor-wrapped cards — the camera button click never reached its handler. Fix: allow clicks through if the target is inside `[data-rd-overlay]`.

### 3. Portfolio Card Horizontal Line Artifacts — Removed (commit `3e2c09f`)
Horizontal banding artifacts visible on portfolio card images. Root cause: CSS `::after` pseudo-element with `repeating-linear-gradient` on `.portfolio-card__img::after`. Removed entirely. Added QA guardrail in `css_compliance_agent.py` to block any future pseudo-element background-image on card elements.

### 4. Back-to-Portfolio Link — Tried Pill, Reverted (commits `4172c72`, `a035969`)
Multiple iterations on making the "← Portfolio" back link more visible on project pages. Tried a slate-blue pill approach. Henry ultimately reverted back to original style: `rgba(255,255,255,0.6)` text, full white on hover, no background pill.

### 5. Lafayette Bistro Hero — DB Snapshot Fix
During session, lafayette-bistro published snapshot had stale `mode='color', #1C1C1C` in `cards_json` from back-link color testing. Fixed both `card_settings` and `published_snapshots` tables. Hero image now shows correctly.

### QA Gate State
**197 checks, 0 warnings, 0 critical failures**

---

## What Is Pending

### Back-to-Portfolio Link Visibility
Still not resolved to Henry's satisfaction. Reverted to original. Will revisit — needs a different approach.

### Alamo Luxury Hero — card_settings base-file path warning
QA warns that `alamo-luxury-hero` in card_settings still has base `_mv2.webp` path. Server normalizes at serve time but DB path should be updated:
```sql
UPDATE card_settings SET image='/assets/images-opt/ff5b18_39536b28ce0447b9a87797bb4c70ee51_mv2_960w.webp' WHERE card_id='alamo-luxury-hero';
```

### Screenshot Server Restart
Still saves to `/root/screenshots/` with timestamp names — §42 fix never activated. Requires root/DO console restart.

### Hero Flash Gap 2 — Blog Index Preload
When no hero saved for blog index, no preload injected → dark flash. Still not fixed.

### Filmstrip Sequential Scan Bug
Blocked by `server-rerender` lock.

### Admin Panel SSL/Subdomain — Deferred

### Branch Not Merged
`ridgecrest-audit` not yet merged to master.

---

## What Next Session Should Read First
1. This file
2. ACTIVE_SESSION.md
3. `git log --oneline -8`

---

## Henry's Decisions This Session
- Home portfolio cards save fix approved and committed
- Portfolio card horizontal lines: remove the CSS rule, add QA guard — approved
- Back-to-portfolio pill styling: tried and reverted — back to original
- Lafayette bistro hero fix was a side effect of session; fixed in DB
