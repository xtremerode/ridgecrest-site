#!/usr/bin/env python3
"""
Full gallery rebuild pipeline:
1. Re-scrape all 18 Wix project pages → update wix_galleries.json
2. Download all missing images → preview/assets/images-opt/
3. Convert every downloaded image to WebP
4. Measure all image dimensions → update img_dims.json
5. Rebuild generate_portfolio.py gallery arrays
6. Regenerate all 18 HTML project pages
"""

import os, json, re, sys, time, urllib.request, io
from pathlib import Path
from playwright.sync_api import sync_playwright
try:
    import psycopg2 as _psycopg2
except ImportError:
    _psycopg2 = None

# ── Paths ──────────────────────────────────────────────────────────────────────
AGENT    = Path('/home/claudeuser/agent')
PREVIEW  = AGENT / 'preview'
OPT_DIR  = PREVIEW / 'assets' / 'images-opt'
DIMS_FILE = PREVIEW / 'assets' / 'img_dims.json'
WIX_JSON = AGENT / 'wix_galleries.json'
GEN_PY   = AGENT / 'generate_portfolio.py'
OPT_DIR.mkdir(parents=True, exist_ok=True)

LOGO_HASH = 'ff5b18_39307a9fb5f448aa8699880d142bb1fe_mv2'

PROJECTS = [
    {'slug': 'sierra-mountain-ranch',       'wix_slug': 'sierramountainranch'},
    {'slug': 'pleasanton-custom',           'wix_slug': 'pleasantoncustomhome'},
    {'slug': 'sunol-homestead',             'wix_slug': 'sunolhomestead'},
    {'slug': 'danville-hilltop',            'wix_slug': 'danvillehilltophideaway'},
    {'slug': 'napa-retreat',                'wix_slug': 'naparetreat'},
    {'slug': 'lafayette-luxury',            'wix_slug': 'lafayette-laid-back-luxury'},
    {'slug': 'orinda-kitchen',              'wix_slug': 'orinda'},
    {'slug': 'danville-dream',              'wix_slug': 'danvilledreamhome'},
    {'slug': 'alamo-luxury',                'wix_slug': 'alamoluxury'},
    {'slug': 'lafayette-bistro',            'wix_slug': 'lafayette-modern-bistro'},
    {'slug': 'san-ramon',                   'wix_slug': 'sanramon'},
    {'slug': 'pleasanton-garage',           'wix_slug': 'pleasanton-garage-renovation'},
    {'slug': 'livermore-farmhouse-chic',    'wix_slug': 'livermorefarmhousechic'},
    {'slug': 'pleasanton-cottage-kitchen',  'wix_slug': 'pleasantoncottagekitchen'},
    {'slug': 'san-ramon-eclectic-bath',     'wix_slug': 'san-ramon-eclectic-bath'},
    {'slug': 'castro-valley-villa',         'wix_slug': 'castro-valley-villa'},
    {'slug': 'lakeside-cozy-cabin',         'wix_slug': 'lakeside-cozy-cabin'},
    {'slug': 'newark-minimal-kitchen',      'wix_slug': 'newarkminimalkitchen'},
]

def extract_hash(url):
    m = re.search(r'(ff5b18_[0-9a-f]+)[~_]?mv2[._](jpg|jpeg|png|webp)', url, re.I)
    if not m:
        return None, None
    return m.group(1) + '_mv2', m.group(2).lower()

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: Scrape Wix pages
# ──────────────────────────────────────────────────────────────────────────────

def scrape_project(page, wix_slug):
    url = f'https://www.ridgecrestdesigns.com/{wix_slug}'
    print(f'  → {url}')
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(3000)

        # Slow scroll to trigger lazy-load
        page.evaluate("""async () => {
            const delay = ms => new Promise(r => setTimeout(r, ms));
            const total = document.body.scrollHeight;
            for (let y = 0; y < total; y += 400) {
                window.scrollTo(0, y);
                await delay(150);
            }
            window.scrollTo(0, 0);
        }""")
        page.wait_for_timeout(2000)

        title = page.title()

        # Strategy 1: DOM images
        dom_imgs = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('img').forEach(img => {
                const src = img.src || img.getAttribute('data-src') || '';
                if (!src.includes('wixstatic.com/media/ff5b18_')) return;
                const srcset = img.getAttribute('srcset') || img.getAttribute('data-srcset') || '';
                const hasLarge = srcset.includes('980') || srcset.includes('1280') || srcset.includes('1920') || srcset.includes('1600');
                const isLargeNat = img.naturalWidth > 300 && img.naturalHeight > 200;
                const isLargeDom = img.offsetWidth > 200 || img.offsetHeight > 150;
                if ((hasLarge || isLargeNat || isLargeDom) && !seen.has(src)) {
                    seen.add(src);
                    results.push({src, w: img.offsetWidth, h: img.offsetHeight});
                }
            });
            // Also background images
            document.querySelectorAll('[style]').forEach(el => {
                const bg = el.style.backgroundImage || '';
                const m = bg.match(/url\\(["']?([^"')]*wixstatic\\.com\\/media\\/ff5b18_[^"')]+)["']?\\)/);
                if (m && !seen.has(m[1]) && (el.offsetWidth > 200 || el.offsetHeight > 150)) {
                    seen.add(m[1]);
                    results.push({src: m[1], w: el.offsetWidth, h: el.offsetHeight});
                }
            });
            return results;
        }""")

        # Strategy 2: All wixstatic URLs in page source
        html = page.content()
        src_urls = re.findall(r'https?://static\.wixstatic\.com/media/ff5b18_[0-9a-f]+~mv2\.[a-z]+', html, re.I)

        # Strategy 3: JSON data embedded in page
        json_uris = re.findall(r'"uri"\s*:\s*"(ff5b18_[0-9a-f]+_mv2\.(?:jpg|jpeg|png|webp))"', html, re.I)

        return {
            'title': title,
            'dom_imgs': dom_imgs,
            'src_urls': src_urls,
            'json_uris': json_uris,
            'ok': True,
        }
    except Exception as e:
        print(f'  ERROR: {e}')
        return {'ok': False, 'error': str(e), 'dom_imgs': [], 'src_urls': [], 'json_uris': []}


def build_image_list(data):
    """Merge all sources, deduplicate, filter logo/nav."""
    seen = set()
    images = []

    def add(hash_mv2, ext, source, dom_w=0, dom_h=0):
        if hash_mv2 == LOGO_HASH:
            return
        if hash_mv2 in seen:
            return
        seen.add(hash_mv2)
        images.append({'hash': hash_mv2, 'ext': ext, 'source': source,
                        'domW': dom_w, 'domH': dom_h})

    for img in data['dom_imgs']:
        h, e = extract_hash(img['src'])
        if h:
            add(h, e, 'dom', img['w'], img['h'])

    for url in data['src_urls']:
        h, e = extract_hash(url)
        if h:
            add(h, e, 'source')

    for uri in data['json_uris']:
        h, e = extract_hash(uri)
        if h:
            add(h, e, 'json')

    return images


def run_scrape():
    print('\n════════════════════════════════════════')
    print('STEP 1: Scraping Wix pages')
    print('════════════════════════════════════════')

    existing = json.loads(WIX_JSON.read_text()) if WIX_JSON.exists() else {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.set_viewport_size({'width': 1440, 'height': 900})

        for proj in PROJECTS:
            slug = proj['slug']
            print(f'\n[{slug}]')
            data = scrape_project(page, proj['wix_slug'])

            if not data['ok']:
                print(f'  RETRY...')
                time.sleep(3)
                data = scrape_project(page, proj['wix_slug'])
                if not data['ok']:
                    print(f'  SKIP (failed twice)')
                    if slug not in existing:
                        existing[slug] = {'done': False, 'images': [], 'wixSlug': proj['wix_slug']}
                    continue

            images = build_image_list(data)
            prev_count = len(existing.get(slug, {}).get('images', []))
            existing[slug] = {
                'done': True,
                'wixSlug': proj['wix_slug'],
                'title': data['title'],
                'images': images,
                'domCount': len(data['dom_imgs']),
                'sourceCount': len(data['src_urls']),
            }
            print(f'  Found {len(images)} images (was {prev_count})')
            # Save after each project
            WIX_JSON.write_text(json.dumps(existing, indent=2))

        browser.close()

    return existing


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2+3: Download missing images and convert to WebP
# ──────────────────────────────────────────────────────────────────────────────

def to_webp(src_path: Path, quality=82) -> Path:
    """Convert image to WebP. Returns final path."""
    if src_path.suffix.lower() == '.webp':
        return src_path
    try:
        from PIL import Image
        with Image.open(src_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            webp_path = src_path.with_suffix('.webp')
            img.save(webp_path, 'WEBP', quality=quality, method=4)
        src_path.unlink()
        return webp_path
    except Exception as e:
        print(f'    WebP convert failed for {src_path.name}: {e}')
        return src_path


def download_image(hash_mv2, ext, retries=2) -> Path | None:
    """Download from Wix CDN. Returns local path or None."""
    webp_path = OPT_DIR / f'{hash_mv2}.webp'
    if webp_path.exists():
        return webp_path  # already have it

    # Try downloading as full-quality original
    hash_clean = hash_mv2.replace('_mv2', '~mv2')
    url = f'https://static.wixstatic.com/media/{hash_clean}.{ext}'
    tmp_path = OPT_DIR / f'{hash_mv2}.{ext}'

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (compatible)',
                'Referer': 'https://www.ridgecrestdesigns.com/',
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            tmp_path.write_bytes(data)
            final = to_webp(tmp_path)
            return final
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f'    FAIL {hash_mv2}: {e}')
                return None


def run_downloads(galleries):
    print('\n════════════════════════════════════════')
    print('STEP 2+3: Download + convert to WebP')
    print('════════════════════════════════════════')

    total_new = 0
    total_skip = 0
    total_fail = 0

    for proj in PROJECTS:
        slug = proj['slug']
        proj_data = galleries.get(slug, {})
        images = proj_data.get('images', [])
        if not images:
            print(f'  [{slug}] No images to download')
            continue

        new_count = 0
        for img in images:
            h = img['hash']
            e = img.get('ext', 'jpg')
            webp_path = OPT_DIR / f'{h}.webp'
            if webp_path.exists():
                total_skip += 1
                continue
            result = download_image(h, e)
            if result:
                new_count += 1
                total_new += 1
            else:
                total_fail += 1

        if new_count:
            print(f'  [{slug}] Downloaded {new_count} new images')

    print(f'\n  Done: {total_new} new, {total_skip} existing, {total_fail} failed')


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4: Measure all image dimensions
# ──────────────────────────────────────────────────────────────────────────────

def run_dimensions():
    print('\n════════════════════════════════════════')
    print('STEP 4: Measuring image dimensions')
    print('════════════════════════════════════════')

    from PIL import Image

    dims = json.loads(DIMS_FILE.read_text()) if DIMS_FILE.exists() else {}
    new_count = 0

    for webp_path in sorted(OPT_DIR.glob('*.webp')):
        key = webp_path.name
        if key in dims:
            continue
        try:
            with Image.open(webp_path) as img:
                dims[key] = list(img.size)  # [width, height]
            new_count += 1
        except Exception as e:
            pass

    DIMS_FILE.write_text(json.dumps(dims, indent=2, sort_keys=True))
    print(f'  Measured {new_count} new images ({len(dims)} total in index)')
    return dims


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5: Update generate_portfolio.py gallery arrays
# ──────────────────────────────────────────────────────────────────────────────

def _load_exclusions():
    """Load manually excluded image hashes from the DB. Returns set of (slug, hash) tuples."""
    excluded = set()
    if not _psycopg2:
        print('  [exclusions] psycopg2 not available — exclusion check skipped')
        return excluded
    try:
        conn = _psycopg2.connect(host='127.0.0.1', dbname='marketing_agent',
                                  user='agent_user', password='StrongPass123!')
        cur = conn.cursor()
        cur.execute("""
            SELECT slug, image_hash FROM gallery_exclusions
        """)
        for row in cur.fetchall():
            excluded.add((row[0], row[1]))
        conn.close()
        if excluded:
            print(f'  [exclusions] Loaded {len(excluded)} exclusion(s) — these images will be skipped')
    except Exception as e:
        print(f'  [exclusions] Could not load exclusions (table may not exist yet): {e}')
    return excluded


def run_update_galleries(galleries):
    print('\n════════════════════════════════════════')
    print('STEP 5: Updating gallery arrays in generate_portfolio.py')
    print('════════════════════════════════════════')

    excluded = _load_exclusions()
    src = GEN_PY.read_text()

    for proj in PROJECTS:
        slug = proj['slug']
        proj_data = galleries.get(slug, {})
        images = proj_data.get('images', [])
        if not images:
            print(f'  [{slug}] No images — skipping')
            continue

        # Filter to only images we actually have locally, skipping manual exclusions
        local_images = []
        for img in images:
            h = img['hash']
            if (slug, h) in excluded:
                print(f'  [{slug}] EXCLUDED (manually deleted): {h[:30]}…')
                continue
            if (OPT_DIR / f'{h}.webp').exists():
                local_images.append(img)

        if not local_images:
            print(f'  [{slug}] No local images — skipping')
            continue

        # Build gallery tuple list
        tuples = []
        for img in local_images:
            h = img['hash']
            e = img.get('ext', 'jpg')
            tuples.append(f"            ('{h}', '{e}'),")
        gallery_str = '\n'.join(tuples)

        # Find and replace the gallery: [...] for this slug in generate_portfolio.py
        # Pattern: find 'slug': 'SLUG' then find 'gallery': [...] after it
        slug_pos = src.find(f"'slug': '{slug}'")
        if slug_pos == -1:
            print(f'  [{slug}] Not found in generate_portfolio.py')
            continue

        # Find gallery: [ ... ] starting from slug position
        gal_start = src.find("'gallery': [", slug_pos)
        if gal_start == -1:
            print(f'  [{slug}] No gallery array found')
            continue

        # Find the matching closing bracket
        bracket_start = src.index('[', gal_start)
        depth = 0
        pos = bracket_start
        while pos < len(src):
            if src[pos] == '[':
                depth += 1
            elif src[pos] == ']':
                depth -= 1
                if depth == 0:
                    bracket_end = pos
                    break
            pos += 1

        old_gallery = src[bracket_start:bracket_end + 1]
        new_gallery = f'[\n{gallery_str}\n        ]'

        old_count = old_gallery.count("'ff5b18_") // 1  # rough count
        src = src[:bracket_start] + new_gallery + src[bracket_end + 1:]
        print(f'  [{slug}] {len(local_images)} images (was ~{old_gallery.count("_mv2")} entries)')

    GEN_PY.write_text(src)
    print('\n  generate_portfolio.py updated')


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6: Regenerate all HTML pages
# ──────────────────────────────────────────────────────────────────────────────

def run_regenerate():
    print('\n════════════════════════════════════════')
    print('STEP 6: Regenerating HTML pages')
    print('════════════════════════════════════════')

    import subprocess
    result = subprocess.run(
        ['python3', str(GEN_PY)],
        capture_output=True, text=True, cwd=str(AGENT)
    )
    if result.returncode != 0:
        print(f'  ERROR: {result.stderr[-500:]}')
        return False
    if result.stdout:
        print(result.stdout[-500:])
    print('  Pages regenerated successfully')
    return True


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    force_scrape = '--force' in sys.argv or '--scrape' in sys.argv
    skip_scrape  = '--no-scrape' in sys.argv

    # Step 1: Scrape
    if skip_scrape:
        print('Skipping scrape (--no-scrape)')
        galleries = json.loads(WIX_JSON.read_text()) if WIX_JSON.exists() else {}
    else:
        # Force re-scrape by clearing done flags
        if WIX_JSON.exists():
            existing = json.loads(WIX_JSON.read_text())
            for v in existing.values():
                v['done'] = False
            WIX_JSON.write_text(json.dumps(existing, indent=2))
        galleries = run_scrape()

    # Step 2+3: Download + convert
    run_downloads(galleries)

    # Step 4: Dimensions
    dims = run_dimensions()

    # Step 5: Update gallery arrays
    run_update_galleries(galleries)

    # Step 6: Regenerate HTML
    run_regenerate()

    print('\n════════════════════════════════════════')
    print('ALL DONE')
    print('════════════════════════════════════════')

    # Final summary
    galleries = json.loads(WIX_JSON.read_text())
    for proj in PROJECTS:
        slug = proj['slug']
        total = len(galleries.get(slug, {}).get('images', []))
        local = sum(1 for img in galleries.get(slug, {}).get('images', [])
                    if (OPT_DIR / f'{img["hash"]}.webp').exists())
        print(f'  {slug}: {local}/{total} images local')
