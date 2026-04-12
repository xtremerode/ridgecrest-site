# Perplexity Computer — Complete Revert Guide
Generated: April 12, 2026 10:40 AM PDT

## How to Revert All PX Changes

### Option 1: Revert to Claude's last baseline
The last Claude commit before any PX changes to pages.html:


To revert ALL files to before PX touched anything:

(This is the BASELINE commit from April 11, 8:46 PM PDT)

Then restore the DB:


### Option 2: Cherry-pick what to keep vs revert
See file-by-file list below.

---

## All PX Commits (chronological)

| Commit | Description |
|--------|-------------|
| 5bdd3c8 | Service card image quality fix + solid overlay |
| df8a662 | Add PX_CHANGE_LOG.md |
| 3c75ed8 | Service card overlay 0.4 → 0.5 |
| 12f964e | Section height API routes + view injection |
| 4a952bf | Bulk site-wide fixes: images, CSS, typography, overlays |
| f9d0a5b | Update change log |
| d5ec24a | Favicon from logo + og:image from hero house |
| 98ec3e1 | Favicon replace with RD monogram |
| 4e80df0 | Favicon transparent background |
| 694355d | Fix overrides.css path /css/ → /view/css/ |
| 13e4d9f | Rule 22: End-to-End Verification |
| 3194c76 | Eyebrow fix: higher specificity for service pages |
| 2940b3b | Favicon rebuilt proper multi-size ICO |
| c3abde1 | Portfolio featured cards theme |
| 40c2316 | PRE: before proper source-file fixes |
| 7d1fff2 | Proper source-file implementation of all theme fixes |
| cbddbb6 | Elevate Scheduling wrapper + CTA links updated (33 files) |
| bb83e0d | Elevate wrapper: floating iframe design |
| 9fed9b9 | Elevate wrapper: mobile/tablet full-width |
| 28df816 | PRE: before edit mode fixes |
| f71e822 | Edit mode fixes: 8 bugs (AI modal, history stack, gallery tools, _pickVariant) |
| a1bf4be | Update change log |
| 888a7b6 | PRE: before admin nav + scroll fixes |
| d6beabd | Admin nav + scroll fixes (auto-load removed, iframe load event) |
| e5ed6c3 | Scroll proxy polling attempt |
| a8892e3 | REVERT pages.html to Claude baseline |
| 01414b5 | Scroll proxy: Math.max + MutationObserver |

---

## Files Modified by PX

### preview_server.py
- AI rerender buttons: window.open → postMessage (hero + img tags)
- History stack for back button (hero + card overlays)
- Gallery images get Browse All + back button
- Section height API: 2 new endpoints + _apply_section_heights()
- _safe_js() function body restored
- Favicon + apple-touch-icon injection
- overrides.css path fix

### preview/admin/pages.html
- Removed sessionStorage auto-load
- Scroll proxy height: Math.max + MutationObserver
- Multiple attempted fixes (some reverted)

### preview/css/main.css
- :root: added --font-body, --font-serif, --gold
- Card overlay: gradient → solid 0.5/0.3
- .project-hero__eyebrow: rgba white → var(--slate-light)
- .project-hero__title: weight 300 → 400

### preview/css/overrides.css
- Stripped to layout-only (nav overlay, mobile hero, iPad breakpoint, image-rendering)

### preview/css/service-pages.css
- Eyebrow: var(--accent) → var(--slate-light)

### preview/portfolio.html
- Inline styles: overlay gradient → solid, loc color → slate-light

### preview/js/main.js
- Added _pickVariant/_swapBg (57 lines)

### preview/start-a-project.html
- NEW: Elevate wrapper page

### 33 HTML files
- CTA links: external Elevate URL → start-a-project.html

### 24 HTML files
- 776 gallery image refs: base files → _1920w

### 16 WebP files
- Re-encoded with sharpening + method 6

### New files
- preview/start-a-project.html
- preview/assets/favicon.ico
- preview/assets/apple-touch-icon.png
- preview/assets/icon-192.png
- preview/assets/icon-512.png
- preview/assets/favicon-32.png
- preview/assets/images/og-image.jpg
- preview/assets/images-opt/backup_pre_px_sharpen/ (20 files)
- preview/assets/images-opt/ff5b18_*_ai_77_960w.webp
- preview/assets/images-opt/ff5b18_*_ai_77_480w.webp
- preview/assets/images-opt/ff5b18_238b56fc*_201w.webp
- ridgecrest-agency/PX_CHANGE_LOG.md
- ridgecrest-agency/PX_REVERT_GUIDE.md
- ridgecrest-agency/project_open_issues.md
- CLAUDE.md (Rule 22 added)
- ridgecrest-agency/rules/AGENT_RULES.md (Rule 11 added)

### Database changes
- card_settings: 62 rows → _960w variants
- pages home: hero_image restored to house exterior
- page_locks home: set to locked

### DB backups
- /tmp/pre_px_sharpen_db.sql
- /tmp/pre_px_bulk_fixes_db.sql
- /tmp/pre_px_section_handles_db.sql
- /tmp/pre_px_editmode_fixes_db.sql
- /tmp/pre_px_proper_fixes_db.sql
