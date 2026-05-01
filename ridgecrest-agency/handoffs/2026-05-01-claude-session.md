# Session Handoff — 2026-05-01

**Branch:** ridgecrest-audit
**Last commit:** 7d3bcda

---

## What Was Done This Session

### 1. Portfolio featured card gradient — pipeline ordering fix (commit 664b673)
- Root cause: `_inject_gradient_id_overlays` ran BEFORE `_replace_portfolio_featured_grid`, so the grid replacement discarded all injected `--rd-overlay` styles on every page load
- Fixed by moving injection call to after all grid/strip replacements in `preview_server.py`
- Added `portfolio_featured_gradient_serve_time` Playwright test — verifies gradient is baked into served HTML, not just applied client-side

### 2. Sierra Mountain Ranch broken image — restored + guardrail gaps closed (commit 3f125ca)
**Cause:** New Playwright test (`portfolio_featured_gradient_serve_time`) PUT `image: None` to a live card and failed to restore it because `_restore_card_state` was called with swapped arguments (`token` and `original_state`). The inner `except Exception: pass` swallowed the failure silently. The drift check saw the mutation but auto-passed it as "expected" because `pages-card` was in scope.

**Three structural fixes:**
1. **Drift check runs BEFORE Playwright** (Gate 2 before Gate 3) — test-induced DB mutations no longer visible to drift check
2. **`image=None` is always CRITICAL FAIL** in drift check regardless of scope
3. **`_restore_card_state` raises on failure** — never swallows silently. Test also verifies DB state after restore.
4. **Test payload safety** — test now preserves original image in PUT; even if restore fails, card stays visible
5. **CLAUDE.md** updated with three new mandatory rules
6. **Sierra Mountain Ranch image restored** and portfolio page republished

### 3. Sitemap page — all 102 body links were broken (commit 7d3bcda)
**Cause:** `preview/sitemap.html` body used root-relative links (`/sierra-mountain-ranch.html`) written for the live domain. From `/view/sitemap.html`, browser resolves these to the server root which 404s. Had been broken since the file was first created on April 15.

**Fix:** Changed all 102 body `href="/page.html"` → `href="page.html"` (relative). `/blog` preserved as-is (dedicated server route).

**Prevention:** Added `sitemap_links_navigable` Playwright test — loads sitemap in browser, resolves every `.sm-link` via `el.href` (fully browser-resolved URL), HTTP-checks every one. Runs every guardrail post-phase. Added link verification rule to CLAUDE.md.

---

## Open Items (Carried Forward)
- **3 missing Wix CDN images** — need Henry to download from Wix and upload via bat script:
  - `ff5b18_c5cb0ea7` → Pleasanton Custom photo 42 + Pleasanton Cottage Kitchen photo 4
  - `ff5b18_98f97a76` → Pleasanton Custom photo 77
  - `ff5b18_238b56fc` → Sierra Mountain Ranch photo 61 (.jpg)
- **Render review queue** — 62 cards pending Henry's manual review
- **`_NAV_PREFETCH_SLUGS` bug** — `preview_server.py` line 298 has `'whole-home-remodels'` (wrong) and `'therdedit'` (wrong); should be `'whole-house-remodels'` and `'blog'`. Affects hero preload on nav hover for those two pages. Small but real bug.
- **Houzz external link** — `https://www.houzz.com/pro/ridgecrestdesigns` needs manual browser verification; curl times out from server
- **set-version gap** — static non-portfolio pages not updated by set-version (known open gap)
- **pre-commit hook python path** — system python3 vs venv still pending

---

## Infrastructure
- Server: 147.182.242.54:8081
- Branch: ridgecrest-audit
- Last commit: 7d3bcda (2026-05-01)
- All features re-locked
- Server restart: POST /admin/api/server/restart (requires X-Admin-Token)
