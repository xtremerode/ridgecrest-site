# Session Handoff — 2026-04-29

## What Was Done This Session

### 1. Documentation Maintenance Hook + CLAUDE.md Cleanup (commit e286a87)
- Removed 4 stale Known Open Gaps from root CLAUDE.md that were already resolved:
  - Wix CDN missing images (recovered or accepted as lost)
  - Tonya Wilson headshot (confirmed in DB and on disk)
  - AI render queue (Henry confirmed complete — 59 active versions set)
  - services.html / team.html hero restructure (confirmed already done)
- Added verification hints to remaining 5 gaps so future Claude can check without guessing
- Added Documentation Maintenance Protocol section to CLAUDE.md — mandates gap verification after every guardrail run and at session end
- Added `hooks/check_doc_freshness.sh` Stop hook: compares last guardrail run timestamp vs last CLAUDE.md edit; warns if CLAUDE.md is stale
- Wired new hook into `.claude/settings.local.json`

### 2. Behavioral Verification Gate (guardrail run run_20260429_003552, commit 19c933b)
Feature key: `hooks-verification-gate`. Three new hooks now enforce that every substantive response is backed by a tool use in the same turn:
- `hooks/mark_prompt_pending.sh` (UserPromptSubmit) — writes prompt timestamp; clears tool marker
- `hooks/log_tool_used.sh` (PostToolUse: Bash|Read|Write|Edit|Grep|Glob|Agent|WebFetch|WebSearch) — writes tool timestamp
- `hooks/check_tool_per_response.sh` (Stop) — if tool_ts ≤ prompt_ts AND response >300 chars → exits 2 with VERIFICATION GATE error

All 17 infra tests passed, zero Playwright regressions. Pushed to GitHub.

This is behavioral (not keyword-based) — it monitors whether Claude actually touched any file or system, not what words appear in the response.

### 3. CLAUDE.md Updated with Verification Gate Documentation (end-of-session)
Added a new "Behavioral Verification Gate" section to root CLAUDE.md explaining all 3 hooks. This complements the existing "Research Verification Enforcement" section (which only fires on analysis-type prompts via keyword detection; this gate fires on every response).

---

## Morning Session (2026-04-29, resumed after Henry went to bed)

### Discussion Only — No Code Changes

Henry resumed with three issues from the overnight danville-hilltop upload diagnosis:

### Issue 1 — DSC_7150 not in gallery (confirmed, unresolved)
Verified against live DB and disk:
- `DSC_7150.webp` is on disk in `images-opt/` (plus two `upload_*` copies)
- **Zero responsive variants** (`_480w`, `_960w`, `_1920w`) exist
- **Not in danville-hilltop's `gallery_json`** — 13 items, all using `ff5b18_hash_mv2` convention
- Prior session diagnosis confirmed accurate. Fix plan (Parts 1–3) still pending Henry approval.

### Issue 2 — "Hilltop Hideaway" cannot replace or add images
Henry reports images cannot be replaced or added on a project called "Hilltop Hideaway."
**BLOCKER: No project named "Hilltop Hideaway" exists in the DB.** The 18 projects on record include Danville Hilltop but no Hilltop Hideaway. Henry must clarify which project he means before this can be diagnosed.

When identity is confirmed, most likely failure mode to check first:
- `gallery_exclusions` table: if an image was manually deleted, it's blocklisted and `add-image` returns 409 with "This image was manually removed from this gallery"
- Replace button (`/admin/api/images/upload`) does not check locks or exclusions — if this is also broken, it points to auth or a JS error in the UI

### Issue 3 — Color alteration on upload — ROOT CAUSE IDENTIFIED (no code change yet)
**Location:** `_to_webp()` in `preview_server.py` line 4182.

**Root cause:** PIL's `.convert('RGB')` drops the embedded ICC color profile without applying the color space transform. Images from iPhones and DSLRs commonly embed Display P3, Adobe RGB, or ProPhoto RGB profiles. When PIL re-interprets those pixel values as sRGB without converting them, colors shift — reds oversaturate, shadows shift, overall image looks "off."

```python
# Current (broken for non-sRGB sources):
img = img.convert('RGB')
img.save(webp_path, 'WEBP', quality=quality, method=4)
# Result: ICC profile is stripped; pixel values are misinterpreted as sRGB
```

**Fix:** Use `PIL.ImageCms.profileToProfile()` to convert pixel values from the embedded profile to sRGB before saving. This is a one-function change in `_to_webp()`, no side effects. The AI Editor pipeline is separate and would be untouched.

**Affects:** All upload paths that call `_to_webp()`:
- `/admin/api/images/upload` (Replace button in card pills)
- `/admin/api/gallery/<slug>/add-image` (Add image to gallery)
- `/media/receive` (Media Library Upload button)

**Does NOT affect:** Images already on disk that went through the Wix pipeline (already sRGB-normalized). Only new uploads going forward.

---

## What Is Pending / Open

### NEEDS HENRY ANSWER FIRST
- **Which project is "Hilltop Hideaway"?** Cannot diagnose upload failure until project identity is confirmed.

### HIGH PRIORITY (ready to execute once Henry approves)
- **Color alteration on upload** — ICC profile fix in `_to_webp()` — single function change, needs guardrail run through `server-webp` feature key
- **DSC_7150 fix (danville-hilltop)** — rename + generate variants + add to gallery_json + re-render (Part 1 of prior plan)
- **Edit pills invisible on diff__zone investment section cards** — z-index stacking bug. Two fix options: (A) attach pill to parent `.diff__visual` in `setupCard()`, or (B) remove `z-index:1` from `.diff__zone` in `main.css`. **BLOCKED: Henry must approve Option A or B.**

### Normal Priority
- **set-version doesn't update static pages** — `index.html`, `portfolio.html`, `about.html`, `contact.html`, `process.html`, `team.html` have hardcoded image paths.
- **Upload pipeline: no responsive variants generated** — `/media/receive` and `/admin/api/images/upload` save full-res only; no `_480w/_960w/_1920w` variants. Part 2 of prior plan.
- **Media Library Upload context routing** — when filtered to a project, Upload should route through `add-image` not `media/receive`. Part 3 of prior plan.

### Low Priority / Deferred
- Blog index preload (dark flash when no hero saved)
- QA blind spot — server-rendered CTA URLs in preview_server.py templates not caught by pre-commit gate
- CSS staging preview system
- Elevate Scheduling wrapper (needs mobile testing)
- Admin panel SSL / subdomain
- Photo Studio nginx config (Henry must run in DO console; /tmp file may need to be recreated)

---

## Decisions Henry Made This Session
- Approved the verification gate hooks system (hooks-verification-gate)
- Discussion mode only — no code changes approved this session

---

## What Next Session Should Read First

1. This handoff — confirm "Hilltop Hideaway" project identity before anything else
2. `ridgecrest-agency/CURRENT_STATUS.md` — campaign state
3. `ridgecrest-agency/project_open_issues.md`
4. `CLAUDE.md` — Known Open Gaps section

## Branch State
- Branch: `ridgecrest-audit`
- Last commit: `11d3fb9 Task complete: portfolio-featured server-routes pages-card pages-overlay guardrail run run_20260429_064356`
- No uncommitted changes from this session (discussion only)
