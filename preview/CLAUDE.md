# Ridgecrest Designs — Web & Preview Rules

> This file is auto-loaded when working in the `preview/` directory.
> Marketing strategy lives in `ridgecrest-agency/CLAUDE.md`.
> Code governance, git rules, and execution guardrail live in the root `agent/CLAUDE.md`.

---

## Image Serving Rules — THREE-TIER SYSTEM (MANDATORY)

**Never use the base file for display. It exists only as a source for the lightbox.**

| Use | Variant | Why |
|---|---|---|
| Project page hero (`project-hero__img`) | `_mv2_1920w.webp` | Hero is ~1440px wide; base file (5000-6000px) causes GPU downscale artifacts |
| Service/blog page hero | `_mv2_1920w.webp` | Same reason |
| Card/thumbnail backgrounds (`proj-card__img`, `portfolio-featured__img`, `portfolio-item__bg`, `portfolio-card__img`, `gallery-item__img`, `featured-home__img`) | `_mv2_960w.webp` | Cards are 350-720px; base file at 15:1 downscale causes moiré on fine patterns (wire mesh, grilles, tile) |
| Lightbox / `data-src` / srcset full-res slot | `_mv2.webp` (base) OR `_mv2_ai_N.webp` (active AI render) | If no active render: original base. If active render is set: AI render base shows in both thumbnail AND lightbox — same image, full res |
| `<img srcset>` smallest slot | `_mv2_480w.webp` | Correct |

### Server-side
- Card thumbnails: use `_portfolio_thumb_src(hash, ext)` — returns `_960w`, falls back to base
- Hero backgrounds: use `portfolio_projects.hero_img` (already updated to `_1920w` for all 18 projects)
- Do NOT use `_portfolio_img_src()` for card backgrounds — it returns the base file

### Feature-to-code mapping
- Editing card/thumbnail background-image URLs → check seo-project-pages, seo-service-pages, frontend-css
- Editing `_portfolio_thumb_src` or `_portfolio_img_src` → check server-render

---

## Hero Restructure — Pending Pages
- `services.html` and `team.html` hero restructure still **PENDING** (reverted 2026-04-16)
- Pattern for secondary pages:
```html
<div class="page-hero page-hero--service page-hero--left">
  <div class="page-hero__inner">
    <p class="page-hero__eyebrow">...</p>
    <h1 class="page-hero__title">...</h1>
    <p class="page-hero__sub">...</p>
    <div class="hero__actions">
      <a class="btn btn--primary" href="start-a-project.html">Start Your Project</a>
    </div>
  </div>
</div>
```
- Before deploying, check DB for stale offsets: `SELECT slug, hero_text_x, hero_text_y FROM pages WHERE slug IN ('services','team');` — reset both to 0 if non-zero.

---

## Card Editability — Conflict Check (MANDATORY before adding data-card-id)
1. Does element already have `data-card-id`? → **SKIP**
2. Does element use `.hero__bg` + `__RD_HERO` injection? → **SKIP** — hero system owns it
3. Does element have existing JS event listeners? → **Flag first**

---

## Image and Card Rules
- **Never hardcode `background-image`** in `main.css` for any `data-card-id` element — DB is the single source of truth
- **`diff__zone::before`:** Never suppress with `display:none` — use `background: var(--rd-overlay, transparent) !important`
- **Panel saves (T/G/BG):** Always fetch-merge-put — fetch current DB state, merge only UI fields, PUT — never write from stale cardState
- **Card path normalization:** `_upgrade_card_images()` in `preview_server.py` normalizes bare `_mv2.webp` → `_960w` and unsized `_ai_N.webp` → `_ai_N_960w.webp` at serve time. Cards already stored with a size suffix (`_960w` or `_1920w`) are left unchanged. The former `_960w → _1920w` upgrade was **removed 2026-04-30** — it caused wire mesh / moiré on 350-720 px card slots.

---

## HTML Editing Rules
- **Never use `sed` for HTML attribute insertion** — corrupts quote characters (curly quotes vs straight); use Edit tool or Python only
- After any bulk HTML edit, verify: `grep -P '[\x80-\xFF]' file.html`

---

## Project Page Wiring (MANDATORY — enforced by pre-commit gate)
Every project page HTML must have:
| Attribute | Element | Value |
|---|---|---|
| `data-hero-id` | Hero root div (`.project-hero`) | `"[slug]-hero"` |
| `data-gradient-id` | Overlay div (`.project-hero__overlay`) | `"[slug]-hero"` |
| `data-cta-id` | CTA container | `"[slug]-hero"` |
| All CTA `href` | CTA buttons | `start-a-project.html` (NOT Base44 URL) |

---

## CSS Specificity — CTA Alignment on Service Pages
CTA-align rules on `.page-hero--service` must score **(0,3,0)**:
```css
[data-hero-cta-align="right"].page-hero--service .page-hero__actions { ... }
```
Must be placed **after** all text-align rules in `main.css`. See §46 in `CLAUDE_HISTORY.md`.

---

## Pre-Commit QA Gate
- **197 checks** run automatically before every `git commit` — never skip
- **System `python3`** has Playwright (Chromium) — the venv does NOT
- **Pre-commit hook** must prefer system `python3` over venv (one-line fix still pending in `.git/hooks/pre-commit`)
- Any new `data-card-id` element must pass `visual_overlay_agent.py` Playwright hover check — extend the agent if the page type isn't covered

---

## Section Height DB Rule — MANDATORY

When clearing or updating `page_sections.height_px` in the DB, you MUST also re-publish the page immediately after:
```
curl -X POST http://147.182.242.54:8081/admin/api/pages/publish \
  -H "Content-Type: application/json" -H "X-Admin-Token: <token>" \
  -d '{"slugs":["<slug>"]}'
```
**Why:** The live site serves pages from `published_snapshots`, not the live `page_sections` table. Updating `page_sections` without re-publishing has no visible effect — the snapshot still contains the old height value. Verified 2026-05-03: portfolio-featured had `height_px=1165` in `page_sections` but the snapshot still injected `height:1165px` until re-publish was triggered.

---

## Visual Truth Rule — MANDATORY

**The live site at 1440px browser width is the source of truth for all spacing and layout decisions.**

The admin preview panel scales the iframe by ~55% using CSS `transform: scale()`. A 96px gap on the live site looks like ~53px in the admin — nearly half the real size. Spacing that looks right in the admin can be significantly oversized on the live site.

**Before declaring any CSS `padding`, `margin`, or `gap` change done:**
1. Load the live URL (e.g. `http://147.182.242.54:8081/portfolio.html`) in a browser at 1440px viewport width
2. Verify the spacing looks proportional relative to surrounding content
3. The admin preview is correct for text, image, color, and overlay decisions — NOT for spacing judgments

**The admin iframe is correct for:** text content, image selection, color, overlays, card settings
**The admin iframe is misleading for:** padding, margin, gap, section height, whitespace amounts

---

## Screenshot Sharing
- Henry uploads at: `http://147.182.242.54:8081/paste` (POST multipart or raw body)
- Files save to: `/home/claudeuser/agent/downloads/screenshot_001.jpg`, `_002.jpg`, etc.
- Claude reads directly: `Read("/home/claudeuser/agent/downloads/screenshot_001.jpg")`
- **When Henry says a 3-digit number (e.g. "001"):** read that file directly — do NOT fetch via URL


---

## Agent-Added Rules

- Concurrent render race condition: when admin_image_rerender runs in parallel, use _RENDER_INDEX_LOCK mutex around the _ai_N index allocation and touch a stub file to reserve the slot before spawning the Gemini subprocess. On failure, clean up the stub if it is zero bytes. This prevents two concurrent render requests from claiming the same version index.

- Rotate image API: /admin/api/images/rotate endpoint rotates source file + all 5 size variants in-place (CW or CCW). Used by render-review.html rotate buttons. When editing image rotation code, check server-routes feature lock.

- render-review.html (/view/admin/render-review.html) is the AI render re-do tool. Features: side-by-side Original+AI panel, editable prompt, filmstrip of all _ai_N versions, From-original/From-render source toggle, reference image upload, delete rejected renders, rotate buttons on both panels (CCW/CW), auto-render on arrival (Gemini+GPT), back button. 63 cards in queue. Set It = DB-only, does NOT delete source files.

- Image quality degradation rule: If Gemini renders look cartoonish/non-photorealistic, check image_render_api.py for model version changes. Previously generated photorealistic renders using Gemini imagen; degraded output likely means model or prompt changed. Validate render quality matches 'real photo' standard before accepting.

- When downloading Wix images via bat or ps1 script, ALWAYS include the Referer header: Referer: https://www.ridgecrestdesigns.com/ — without it, Wix CDN returns 403 Forbidden. Also check file extension: some Wix images are .png not .jpg. The working script pattern is in migrate_missing_gallery_images.ps1.

- The gallery add-image upload endpoint had a bug: it returned 'already in gallery' without checking whether the actual file exists on disk, causing uploaded files to be silently dropped on retry. Fixed 2026-04-26 — server now saves the file if missing from disk even when hash is already in gallery_json.

- The screenshot paste endpoint is now native in preview_server.py (port 8081). Screenshots upload to /home/claudeuser/agent/downloads/screenshot_NNN.jpg. Files are compressed to 1920px JPEG on upload. Naming is sequential per server restart. Henry tells Claude the filename (e.g. 001) and Claude reads it directly — no root process, no crashes on large files.

- The render button bug: card_settings rows that store state.image as a _960w variant path (instead of the base path) cause setupCard to skip the data-src reset and the render button opens the wrong image. Fix is to delete stale card_settings rows for gallery items (they should not have a saved state.image at all) and fix setupCard to always reset state.image from data-src for gallery items regardless of state.mode.

- gallery_data.json gallery_count field must match the actual number of images for each project in the DB. Found multiple projects with stale counts after migration/audit work. gallery_count is shown on the portfolio page as the photo count badge.

- When HTML project gallery files (pleasanton-custom.html, sierra-mountain-ranch.html, etc.) contain images pointing directly at Wix CDN URLs (https://static.wixstatic.com/media/...), always check if those images now exist locally at /assets/images-opt/ and update the HTML to use local paths with proper srcset. Wix CDN direct URLs in static HTML are fragile — they can return 403 from DO server IP during batch operations.

- portrait-container image variant selection in _pickVariant() must use AND logic — both width AND height must clear the threshold — not OR. A portrait card (246px wide, 400px tall) needs height-based threshold to prevent serving undersized 480px image that would upscale 1.42x and appear blurry. Fix deployed 2026-04-29 in main.js and main.css (removed hardcoded background-image CSS overrides for portfolio-card__img--2 and --4). Feature keys: frontend-main, frontend-css.

- ICC profile stripping in _to_webp(): when PIL converts images via .convert('RGB') it drops embedded ICC color profiles (Display P3, Adobe RGB, ProPhoto RGB) without applying the color space transform. Fix must use PIL.ImageCms.profileToProfile() to convert to sRGB before saving. This affects all upload paths: /admin/api/images/upload, /admin/api/gallery/<slug>/add-image, and /media/receive. ICC call sites are at lines 4195, 5428, and 10382 in preview_server.py. Confirmed by both Claude analysis and Codex second-opinion review 2026-04-29.

- Admin pages.html iframe scroll architecture rule (discovered 2026-04-29): #siteFrame must be position:sticky (not position:absolute). Using absolute causes a dark block to appear below the iframe when scrolling because the proxy scroll container grows but the iframe doesn't anchor. The frameScrollProxy height formula must account for the sticky container offset: Math.max(0, Math.ceil(iframeH * scale) + frameWrap.clientHeight - Math.ceil(frameWrap.clientHeight / scale)) — do not simplify this back to Math.ceil(iframeH * scale) or the scroll will be wrong.
