# Session Handoff — 2026-04-23 (Session 4)

## What Was Done This Session

### 1. services.html Primary CTA Fix (commit `bbc476c`)
- Changed primary CTA from `contact.html` → `start-a-project.html`
- Root cause: services.html was reverted 2026-04-16, stale contact.html CTA survived
- Added `primary_cta_destination` QA check to `html_compliance_agent.py`
- Exempts: `start-a-project.html` (embeds iframe) and `project-inquiry.html` (#anchor CTA)

### 2. Blog Hero CTA Fix (commit `ba3fd9e`)
- Blog hero buttons used `/start-a-project.html` and `/process.html` (no `/view/` prefix) → 404
- Fixed to `/view/start-a-project.html` and `/view/process.html`
- NOTE: `primary_cta_destination` QA check only covers static HTML files, not server-rendered templates in `preview_server.py` — this is a known blind spot

### 3. Five-Stage Process Alignment (commit `781fc00`)
- Updated all 4 service pages from 4-step to 5-stage model matching `process.html`
- Stages: Consultation → Design & Visualization → Budget & Proposal → Permitting & Construction → Completion & Handover
- custom-homes: "Five stages. One team. Zero gaps."
- whole-house-remodels: "Five stages. Complete transformation. Managed entirely by us."
- kitchen-remodels and bathroom-remodels: no stage count in headline, copy updated
- Render callout preserved in bold inside Step 2 body on each page

### 4. Investment Section Image Panels (commit `9b7a14e`)
- All 4 service pages were missing `diff__zone--top/bottom` image layers in investment section
- Added zones with `data-card-id` and starter images to: custom-homes, whole-house-remodels, kitchen-remodels, bathroom-remodels
- Seeded 8 `card_settings` DB records
- Added all 8 to `required_card_records` QA guard in `db_approved_state.py`

### 5. Dark Overlay Fix on Edit Mode Entry (commit `eee6dfc`)
- `.diff__zone.rd-card--image-mode::before` was rendering with 50% black default
- Added suppression rule in `main.css` (display:none) — this was later revised (see #7)

### 6. Gradient Controls Not Working — Root Cause Analysis
- Discussion only session, no changes
- Three issues identified:
  1. `::before` suppressed — gradient rendering surface removed
  2. No default fallback → should be transparent not dark
  3. `applyStyle()` doesn't re-apply `--rd-overlay` → gradient lost on image swap

### 7. Gradient Fix (commit `937a882`)
- Replaced `display:none` with `background: var(--rd-overlay, transparent) !important`
- Added `--rd-overlay` re-application to `applyStyle()` in `preview_server.py`
- Affects all 17 cards site-wide that have saved gradients (global improvement)

## Pending / Incomplete

### Start a Project Page — iframe Starting Page
- Henry reports iframe currently loads on "page 2" of the Elevate Scheduler flow
- Wants it to start on "page 1" (the first step of the Elevate Scheduler)
- Current iframe src: `https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm`
- Fix is one line (`start-a-project.html:152` + `preview_server.py:5645` `_INQUIRY_URL`)
- **BLOCKED: Henry needs to provide the correct page 1 URL**
  - He referenced "image 250" and "image 352" but those files don't exist in downloads/
  - He described image 250 as the current wrong starting view, image 352 as the correct first step
  - Next session: ask Henry for the actual URL of the Base44 app's first step page
- Henry also mentioned wanting a toggle to switch between page 1 and page 2 — simple DB setting

### QA Blind Spot — Server-Rendered CTA URLs
- `primary_cta_destination` QA check only scans static HTML in PREVIEW_DIR
- Server-rendered templates in `preview_server.py` are not checked
- Blog hero CTA was fixed manually but future regressions in server templates won't be caught

## Git State
- Branch: ridgecrest-audit
- All work committed, clean working tree
- Pre-commit gate: 173 checks passing, 0 failures

## Next Session Should Read
1. This file
2. The Start a Project iframe URL question — get correct URL from Henry
3. Check if Henry has tested the gradient controls on the investment panels
