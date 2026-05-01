# Session Handoff — 2026-04-30

**Time:** 2026-04-30 ~04:50 UTC  
**Branch:** ridgecrest-audit  
**Last commit:** 8ee809f

---

## What Was Done This Session

### 1. Admin Panel Refresh Fix (COMPLETE — run_20260430_032736)
Henry reported the admin panel always loads the home page on hard refresh instead of the last-viewed page. Also requested gallery auto-reorganize on image type reclassify.

- **URL hash persistence** (`pages.html`): `history.replaceState(null, '', '#' + slug)` on every slug change; on init, reads hash before localStorage; `_suppressSlugSync` flag prevents corruption on programmatic nav
- **Gallery auto-sort debounce** (`preview_server.py`): 1-second debounced sort + `location.reload()` fires after every tag type change
- Committed and pushed

### 2. Wire Mesh / Moiré Artifacts Fix (COMPLETE — run_20260430_041722)
Henry shared screenshot 018 showing moiré on portfolio card thumbnails with wire mesh patterns (Danville Hilltop, Pleasanton Custom).

**Root cause fixed:** `_upgrade_card_images()` in `preview_server.py` was upgrading `_960w` → `_1920w` card paths at serve time, contradicting the three-tier image rule. Fixed to normalize only (no upgrades).

**Changes committed:**
- `_upgrade_card_images()` rewritten — no longer upgrades to `_1920w`; normalizes bare `_mv2.webp` → `_960w` only
- 72 `card_settings` rows bulk-updated from bare `_mv2.webp` / `_1920w` → `_960w`
- `check_card_variants()` in `page_state_guard.py` rebuilt to query DB directly (cards are JS-injected, not CSS-in-HTML)
- `card_variant_960w_playwright` test fixed to use `page.evaluate()` for inline styles
- `danville-hilltop.html` nav CTA: `contact.html` → `start-a-project.html` (pre-existing regression fixed)

**Post-investigation:** Henry confirmed "not as bad on the live site." Admin panel iframe scaling (2-3x extra downscale) makes card artifacts look worse than the public site. Issue closed, no further action needed.

---

## Current State

- All features locked (server-render, server-db, pages-card, etc.)
- Branch `ridgecrest-audit` is up to date with `origin/ridgecrest-audit`
- No open tasks

## Open Issues (unchanged)
- Set-version gap: doesn't update static non-portfolio pages
- Blog index preload missing
- Pre-commit hook python path (venv vs system python3)
- AI render review queue: cards 2–23 pending

## Nothing Carried Forward
No pending work items — session closed cleanly.
