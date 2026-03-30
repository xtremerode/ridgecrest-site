#!/usr/bin/env python3
"""
Add hero background images to all 72 service pages (60 service×city + 12 city hub).

Strategy:
  - City-specific project images are used where available (most authentic)
  - Service-specific kitchen images used for kitchen pages in those cities
  - Carefully varied pool for remaining cities to avoid repetition
  - Dark overlay via CSS so white text stays readable
"""

import re
from pathlib import Path

SERVICES_DIR = Path("/home/claudeuser/agent/preview/services")
CSS_FILE = Path("/home/claudeuser/agent/preview/css/main.css")

def webp(stem):
    return f"/assets/images-opt/{stem}.webp"

# ── Image pool ───────────────────────────────────────────────────────────────
# All are real Ridgecrest project photos, sourced from the image library

# City-specific hero shots (from named projects)
CITY_HERO = {
    "danville":     "ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab_mv2",  # Danville Hilltop — exterior/hero
    "lafayette":    "ff5b18_c1e5fd8a13c34fa985b5b84f87a8f7d1_mv2",  # Lafayette Laid-Back Luxury
    "alamo":        "ff5b18_39536b28ce0447b9a87797bb4c70ee51_mv2",  # Alamo Luxury — hero
    "orinda":       "ff5b18_94919d08fc9245fc849ac03c4ea2caaf_mv2",  # Orinda Kitchen — hero
    "pleasanton":   "ff5b18_9820c1603a9c414d8cc8009784d1ca7c_mv2",  # Pleasanton Custom Home
    "sunol":        "ff5b18_296b1e9ff5d14e128006c21217e3f3e9_mv2",  # Sunol Homestead — hero
}

# Service-specific kitchen overrides (kitchen pages get kitchen shots in known cities)
SERVICE_CITY_OVERRIDE = {
    ("kitchen-remodel", "danville"):   "ff5b18_598ba1466dbb45249778e2ea0e0b95e3_mv2",  # Danville navy kitchen
    ("kitchen-remodel", "lafayette"):  "ff5b18_d7eb886d364544c1993777e2db5e8bb6_mv2",  # Lafayette white oak kitchen
    ("kitchen-remodel", "orinda"):     "ff5b18_086efaaaac9f44f9bfebafc043e1a7a2_mv2",  # Farmhouse kitchen w/ window
    ("bathroom-remodel", "danville"):  "ff5b18_894d7faa27664f35862b420c27f51f57_mv2",  # Danville Hilltop kitchen detail
    ("custom-home-builder", "pleasanton"): "ff5b18_9820c1603a9c414d8cc8009784d1ca7c_mv2",  # Pleasanton farmhouse exterior
    ("custom-home-builder", "sunol"):  "ff5b18_17513c9b8f434b90b64b2762c46f3a45_mv2",  # Sierra Mountain stove
    ("whole-house-remodel", "danville"): "ff5b18_3c0cef18e48849089c5ed48614041900_mv2",  # Danville Dream home
    ("whole-house-remodel", "alamo"):  "ff5b18_39536b28ce0447b9a87797bb4c70ee51_mv2",   # Alamo Luxury hero
    ("design-build-contractor", "sunol"): "ff5b18_82e5d2a1febd4d1abc6eecd7aadb0101_mv2", # Sunol Homestead gallery 2
    ("design-build-contractor", "pleasanton"): "ff5b18_53f46b46f9094468addb44305dff0a55_mv2", # Pleasanton Custom gallery 2
}

# Service defaults — one strong image per service type used as fallback
SERVICE_DEFAULT = {
    "kitchen-remodel":          "ff5b18_086efaaaac9f44f9bfebafc043e1a7a2_mv2",  # farmhouse kitchen
    "bathroom-remodel":         "ff5b18_eba842cf7eb641b58bd420804e76cb50_mv2",  # mountain retreat kitchen
    "whole-house-remodel":      "ff5b18_75a9ba9c5a87418daf6d2b69c70f60ff_mv2",  # living room w/ stone fireplace
    "custom-home-builder":      "ff5b18_17513c9b8f434b90b64b2762c46f3a45_mv2",  # Sierra Mountain custom home
    "design-build-contractor":  "ff5b18_3c0cef18e48849089c5ed48614041900_mv2",  # Danville Dream whole-home
}

# Per-city fallbacks for cities with no named project — varied, high-quality shots
# These rotate through different aesthetics so adjacent cities don't look identical
CITY_FALLBACK = {
    "walnut-creek": "ff5b18_9192e5d316c84e40b65fff6dbd4d0e36_mv2",  # Custom home office, bespoke
    "san-ramon":    "ff5b18_0b10882438704be9af57966897e72b37_mv2",  # Custom library, built-ins
    "dublin":       "ff5b18_b246a630ba864e2a8fe67d964745b9b5_mv2",  # Danville Hilltop gallery 2
    "moraga":       "ff5b18_7e0f0e5602694ed280e46ec708e7b068_mv2",  # Danville Hilltop gallery 3
    "rossmoor":     "ff5b18_63757c728db94733b4f60a7102c0f722_mv2",  # Danville Hilltop gallery 4
    "diablo":       "ff5b18_82e5d2a1febd4d1abc6eecd7aadb0101_mv2",  # Sunol Homestead gallery 2
}

def pick_image(service, city):
    """Return WebP path for this service×city combination."""
    # 1. Explicit service+city override
    key = (service, city)
    if key in SERVICE_CITY_OVERRIDE:
        return webp(SERVICE_CITY_OVERRIDE[key])
    # 2. City-specific project hero
    if city in CITY_HERO:
        return webp(CITY_HERO[city])
    # 3. City fallback pool
    if city in CITY_FALLBACK:
        return webp(CITY_FALLBACK[city])
    # 4. Service default
    if service in SERVICE_DEFAULT:
        return webp(SERVICE_DEFAULT[service])
    # 5. Last resort
    return webp("ff5b18_3c0cef18e48849089c5ed48614041900_mv2")


# ── CSS: add overlay support for service hero ─────────────────────────────────

css_text = CSS_FILE.read_text()

OVERLAY_CSS = """
/* ── Service page hero — background image + dark overlay ─────────────────── */
.page-hero--service {
  position: relative;
  background-size: cover;
  background-position: center center;
}
.page-hero--service::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(8, 12, 18, 0.72);
  z-index: 0;
}
.page-hero--service > * {
  position: relative;
  z-index: 1;
}
"""

if "page-hero--service {" not in css_text:
    css_text += OVERLAY_CSS
    CSS_FILE.write_text(css_text)
    print("Added overlay CSS to main.css")
else:
    print("Overlay CSS already present")


# ── Update HTML files ─────────────────────────────────────────────────────────

HERO_DIV_RE = re.compile(
    r'<div class="page-hero page-hero--service"([^>]*)>',
    re.IGNORECASE
)

updated = 0
skipped = 0

all_html = list(SERVICES_DIR.glob("*.html"))

for html_file in sorted(all_html):
    stem = html_file.stem  # e.g. "kitchen-remodel-danville" or "danville"

    # Parse service and city from filename
    parts = stem.split("-")

    # City hub pages (no service prefix): "danville", "walnut-creek", etc.
    # Service×city pages: "kitchen-remodel-danville", "custom-home-builder-alamo", etc.
    known_services = {
        "kitchen-remodel", "bathroom-remodel", "whole-house-remodel",
        "custom-home-builder", "design-build-contractor"
    }

    service = None
    city = None
    for svc in known_services:
        if stem.startswith(svc + "-"):
            service = svc
            city = stem[len(svc)+1:]
            break

    if service is None:
        # It's a city hub page
        city = stem
        service = None

    img_path = pick_image(service or "whole-house-remodel", city)

    text = html_file.read_text(encoding="utf-8")

    # Check if already has a background-image on the hero div
    if "page-hero--service" in text and "background-image" in text.split("page-hero--service")[1][:200]:
        skipped += 1
        continue

    new_text, n = HERO_DIV_RE.subn(
        f'<div class="page-hero page-hero--service" style="background-image:url(\'{img_path}\')"\\1>',
        text
    )

    if n:
        html_file.write_text(new_text, encoding="utf-8")
        updated += 1
        svc_label = service or "(city hub)"
        print(f"  {stem:<45}  {img_path.split('/')[-1][:30]}")
    else:
        print(f"  NO MATCH: {stem}")

print(f"\nDone. Updated: {updated}  Already done: {skipped}")
