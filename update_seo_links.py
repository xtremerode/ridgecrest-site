#!/usr/bin/env python3
"""
SEO Internal Linking Update
1. Creates preview/sitemap.html  — full HTML sitemap for crawlers + users
2. Updates footer Service Areas column in ALL HTML pages (adds all 12 cities)
3. Adds Site Map link to every page footer bottom bar
4. Updates generate_portfolio.py footer_html() to match
5. Adds sitemap.html to sitemap.xml
"""
import os, re, sys
from datetime import date

PREVIEW_DIR = '/home/claudeuser/agent/preview'
TODAY = date.today().isoformat()

# ── Canonical data ────────────────────────────────────────────────────────────

CITIES = [
    ('Alamo',       'alamo'),
    ('Danville',    'danville'),
    ('Diablo',      'diablo'),
    ('Dublin',      'dublin'),
    ('Lafayette',   'lafayette'),
    ('Moraga',      'moraga'),
    ('Orinda',      'orinda'),
    ('Pleasanton',  'pleasanton'),
    ('Rossmoor',    'rossmoor'),
    ('San Ramon',   'san-ramon'),
    ('Sunol',       'sunol'),
    ('Walnut Creek','walnut-creek'),
]

SERVICE_TYPES = [
    ('Kitchen Remodel',       'kitchen-remodel',     '$150,000+'),
    ('Bathroom Remodel',      'bathroom-remodel',    '$60,000+'),
    ('Whole House Remodel',   'whole-house-remodel', '$1,000,000+'),
    ('Custom Home Builder',   'custom-home-builder', '$5,000,000+'),
    ('Design-Build Contractor','design-build',        'All sizes'),
]

MAIN_PAGES = [
    ('Home',              '/',                             '1.0'),
    ('About',             '/about',                        '0.8'),
    ('Our Process',       '/process',                      '0.8'),
    ('Services',          '/services',                     '0.8'),
    ('Portfolio',         '/portfolio',                    '0.8'),
    ('All Projects',      '/allprojects',                  '0.7'),
    ('Custom Homes',      '/custom-homes',                 '0.7'),
    ('Kitchen Remodels',  '/kitchen-remodels',             '0.7'),
    ('Bathroom Remodels', '/bathroom-remodels',            '0.7'),
    ('Whole House Remodels','/whole-house-remodels',       '0.7'),
    ('Team',              '/team',                         '0.7'),
    ('Contact',           '/contact',                      '0.7'),
    ('The RD Edit (Blog)','/blog',                         '0.9'),
]

PROJECT_PAGES = [
    ('Sierra Mountain Ranch',       '/sierra-mountain-ranch'),
    ('Napa Retreat',                '/napa-retreat'),
    ('Lakeside Cozy Cabin',         '/lakeside-cozy-cabin'),
    ('Danville Hilltop Estate',     '/danville-hilltop'),
    ('Danville Dream Home',         '/danville-dream'),
    ('Alamo Luxury',                '/alamo-luxury'),
    ('Lafayette Luxury',            '/lafayette-luxury'),
    ('Lafayette Bistro',            '/lafayette-bistro'),
    ('Pleasanton Custom',           '/pleasanton-custom'),
    ('Pleasanton Cottage Kitchen',  '/pleasanton-cottage-kitchen'),
    ('Pleasanton Garage',           '/pleasanton-garage'),
    ('Orinda Kitchen',              '/orinda-kitchen'),
    ('San Ramon Eclectic Bath',     '/san-ramon-eclectic-bath'),
    ('San Ramon',                   '/san-ramon'),
    ('Castro Valley Villa',         '/castro-valley-villa'),
    ('Livermore Farmhouse Chic',    '/livermore-farmhouse-chic'),
    ('Newark Minimal Kitchen',      '/newark-minimal-kitchen'),
    ('Sunol Homestead',             '/sunol-homestead'),
]


# ── Step 1: Create sitemap.html ───────────────────────────────────────────────

def build_sitemap_html():
    sections = []

    # Main pages
    rows = '\n'.join(
        f'      <li><a href="{url}.html" class="sm-link">{name}</a></li>'
        if url != '/' else
        f'      <li><a href="/index.html" class="sm-link">{name}</a></li>'
        for name, url, _ in MAIN_PAGES
    )
    sections.append(f'''  <section class="sm-section">
    <h2 class="sm-heading">Main Pages</h2>
    <ul class="sm-list">
{rows}
    </ul>
  </section>''')

    # Portfolio
    rows = '\n'.join(
        f'      <li><a href="{url}.html" class="sm-link">{name}</a></li>'
        for name, url in PROJECT_PAGES
    )
    sections.append(f'''  <section class="sm-section">
    <h2 class="sm-heading">Portfolio Projects</h2>
    <ul class="sm-list sm-list--grid">
{rows}
    </ul>
  </section>''')

    # Service Areas — city hubs
    rows = '\n'.join(
        f'      <li><a href="/services/{slug}.html" class="sm-link">{name}</a></li>'
        for name, slug in CITIES
    )
    sections.append(f'''  <section class="sm-section">
    <h2 class="sm-heading">Service Areas</h2>
    <ul class="sm-list sm-list--grid">
{rows}
    </ul>
  </section>''')

    # SEO service pages by type
    for svc_name, svc_slug, starting in SERVICE_TYPES:
        rows = '\n'.join(
            f'      <li><a href="/services/{svc_slug}-{city_slug}.html" class="sm-link">{city_name}</a></li>'
            for city_name, city_slug in CITIES
        )
        sections.append(f'''  <section class="sm-section">
    <h2 class="sm-heading">{svc_name} — by City <span class="sm-note">Starting at {starting}</span></h2>
    <ul class="sm-list sm-list--grid">
{rows}
    </ul>
  </section>''')

    sections_html = '\n\n'.join(sections)
    total_pages = len(MAIN_PAGES) + len(PROJECT_PAGES) + len(CITIES) + len(CITIES) * len(SERVICE_TYPES)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Site Map — Ridgecrest Designs</title>
  <meta name="description" content="Complete site map for Ridgecrest Designs — luxury design-build contractor serving the East Bay. All pages, service areas, and project portfolio." />
  <link rel="canonical" href="https://www.ridgecrestdesigns.com/sitemap" />
  <link rel="stylesheet" href="css/main.css" />
  <style>
    .sm-hero {{
      background: var(--charcoal, #0d1a22);
      padding: 80px 0 56px;
      text-align: center;
    }}
    .sm-hero__label {{
      font-size: 11px; font-weight: 700; letter-spacing: .14em;
      text-transform: uppercase; color: var(--gold, #c9a96e);
      margin-bottom: 16px;
    }}
    .sm-hero__title {{
      font-family: 'Cormorant Garamond', Georgia, serif;
      font-size: clamp(2rem, 5vw, 3rem); font-weight: 300;
      color: #e2e8f0; margin: 0 0 12px;
    }}
    .sm-hero__sub {{
      color: #94a3b8; font-size: 14px;
    }}
    .sm-body {{
      max-width: 960px; margin: 0 auto; padding: 48px 24px 80px;
    }}
    .sm-section {{
      margin-bottom: 48px;
    }}
    .sm-heading {{
      font-size: 13px; font-weight: 700; letter-spacing: .1em;
      text-transform: uppercase; color: var(--gold, #c9a96e);
      border-bottom: 1px solid #2a3748; padding-bottom: 10px;
      margin-bottom: 20px; display: flex; align-items: center; gap: 12px;
    }}
    .sm-note {{
      font-size: 11px; font-weight: 400; color: #64748b;
      text-transform: none; letter-spacing: 0;
    }}
    .sm-list {{
      list-style: none; margin: 0; padding: 0;
      display: flex; flex-direction: column; gap: 6px;
    }}
    .sm-list--grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 6px 16px;
    }}
    .sm-link {{
      color: #94a3b8; font-size: 14px; text-decoration: none;
      transition: color .15s;
    }}
    .sm-link:hover {{ color: var(--gold, #c9a96e); }}
    .sm-total {{
      font-size: 12px; color: #64748b; text-align: right;
      margin-bottom: 32px;
    }}
  </style>
</head>
<body>

  <nav class="nav nav--scrolled" id="nav">
    <a href="index.html" class="nav__logo">RIDGECREST DESIGNS</a>
    <button class="nav__toggle" id="navToggle" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav__links" id="navLinks">
      <li><a href="about.html">About</a></li>
      <li><a href="process.html">Process</a></li>
      <li><a href="services.html">Services</a></li>
      <li><a href="portfolio.html">Portfolio</a></li>
      <li><a href="/blog">The RD Edit</a></li>
      <li><a href="team.html">Team</a></li>
      <li><a href="contact.html" class="nav__cta">Start a Project</a></li>
    </ul>
  </nav>

  <div class="sm-hero">
    <p class="sm-hero__label">Ridgecrest Designs</p>
    <h1 class="sm-hero__title">Site Map</h1>
    <p class="sm-hero__sub">Every page on ridgecrestdesigns.com</p>
  </div>

  <div class="sm-body">
    <p class="sm-total">{total_pages} pages total &nbsp;·&nbsp; Last updated {TODAY}</p>

{sections_html}

  </div>

  <footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <span class="footer__logo">RIDGECREST DESIGNS</span>
        <p class="footer__tagline">Luxury Design-Build &middot; Est. 2013</p>
        <p class="footer__tagline" style="font-style:italic; opacity:0.6">Experience the Ridgecrest difference.</p>
        <p class="footer__address">5502 Sunol Blvd, Suite 100<br>Pleasanton, CA 94566</p>
        <p><a href="tel:9257842798">925-784-2798</a> &middot; <a href="mailto:info@ridgecrestdesigns.com">info@ridgecrestdesigns.com</a></p>
      </div>
      <div class="footer__nav">
        <div class="footer__col">
          <p class="footer__col-head">Company</p>
          <a href="about.html">About</a>
          <a href="team.html">Team</a>
          <a href="process.html">Process</a>
          <a href="portfolio.html">Portfolio</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Services</p>
          <a href="services/custom-home-builder-danville.html">Custom Homes</a>
          <a href="services/whole-house-remodel-danville.html">Whole House Remodels</a>
          <a href="services/kitchen-remodel-danville.html">Kitchen Remodels</a>
          <a href="services/bathroom-remodel-danville.html">Bathroom Remodels</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="services/alamo.html">Alamo</a>
          <a href="services/danville.html">Danville</a>
          <a href="services/diablo.html">Diablo</a>
          <a href="services/dublin.html">Dublin</a>
          <a href="services/lafayette.html">Lafayette</a>
          <a href="services/moraga.html">Moraga</a>
          <a href="services/orinda.html">Orinda</a>
          <a href="services/pleasanton.html">Pleasanton</a>
          <a href="services/rossmoor.html">Rossmoor</a>
          <a href="services/san-ramon.html">San Ramon</a>
          <a href="services/sunol.html">Sunol</a>
          <a href="services/walnut-creek.html">Walnut Creek</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Connect</p>
          <a href="https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm">Start a Project</a>
          <a href="contact.html">Contact Us</a>
          <a href="/blog">The RD Edit</a>
          <a href="https://www.instagram.com/ridgecrestdesigns" target="_blank" rel="noopener">Instagram</a>
          <a href="https://www.facebook.com/ridgecrestdesigns" target="_blank" rel="noopener">Facebook</a>
          <a href="https://www.houzz.com/pro/ridgecrestdesigns" target="_blank" rel="noopener">Houzz</a>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <div class="container">
        <p>&copy; 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured &middot; California Contractor &middot; <a href="sitemap.html">Site Map</a></p>
      </div>
    </div>
  </footer>

  <script src="js/main.js"></script>
</body>
</html>
'''
    return html


# ── Step 2: Footer replacement helpers ───────────────────────────────────────

def service_areas_col(prefix):
    """Return the full Service Areas footer__col HTML for a given path prefix."""
    links = '\n'.join(
        f'          <a href="{prefix}{slug}.html">{name}</a>'
        for name, slug in CITIES
    )
    return (
        '        <div class="footer__col">\n'
        '          <p class="footer__col-head">Service Areas</p>\n'
        f'{links}\n'
        '        </div>'
    )


def add_sitemap_link(content, sitemap_href):
    """Add Site Map link to footer bottom bar if not already present."""
    if 'Site Map' in content or 'sitemap.html' in content:
        return content
    old = '<p>Licensed &amp; Insured · California Contractor</p>'
    new = f'<p>Licensed &amp; Insured · California Contractor · <a href="{sitemap_href}">Site Map</a></p>'
    if old in content:
        return content.replace(old, new, 1)
    # Try alternate encoding (entities)
    old2 = '<p>Licensed &amp; Insured &middot; California Contractor</p>'
    new2 = f'<p>Licensed &amp; Insured &middot; California Contractor &middot; <a href="{sitemap_href}">Site Map</a></p>'
    if old2 in content:
        return content.replace(old2, new2, 1)
    return content


SA_PATTERN = re.compile(
    r'<div class="footer__col">\s*<p class="footer__col-head">Service Areas</p>[\s\S]*?</div>',
    re.DOTALL
)


def update_html_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if no footer
    if 'footer__col-head' not in content:
        return False, 'no footer'

    rel = os.path.relpath(filepath, PREVIEW_DIR).replace('\\', '/')
    depth = rel.count('/')

    if depth == 0:
        prefix = 'services/'
        sitemap_href = 'sitemap.html'
    elif depth == 1:
        prefix = ''
        sitemap_href = '../sitemap.html'
    else:
        up = '../' * depth
        prefix = up + 'services/'
        sitemap_href = up + 'sitemap.html'

    new_content = SA_PATTERN.sub(service_areas_col(prefix), content)
    new_content = add_sitemap_link(new_content, sitemap_href)

    if new_content == content:
        return False, 'no change needed'

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True, 'ok'


# ── Step 3: Update generate_portfolio.py footer_html() ───────────────────────

def update_generate_portfolio():
    path = '/home/claudeuser/agent/generate_portfolio.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_sa = '''        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="services/danville.html">Danville</a>
          <a href="services/lafayette.html">Lafayette</a>
          <a href="services/walnut-creek.html">Walnut Creek</a>
          <a href="services/alamo.html">Alamo</a>
          <a href="services/orinda.html">Orinda</a>
          <a href="services/pleasanton.html">Pleasanton</a>
          <a href="services/san-ramon.html">San Ramon</a>
          <a href="services/dublin.html">Dublin</a>
        </div>'''

    new_sa = '''        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="services/alamo.html">Alamo</a>
          <a href="services/danville.html">Danville</a>
          <a href="services/diablo.html">Diablo</a>
          <a href="services/dublin.html">Dublin</a>
          <a href="services/lafayette.html">Lafayette</a>
          <a href="services/moraga.html">Moraga</a>
          <a href="services/orinda.html">Orinda</a>
          <a href="services/pleasanton.html">Pleasanton</a>
          <a href="services/rossmoor.html">Rossmoor</a>
          <a href="services/san-ramon.html">San Ramon</a>
          <a href="services/sunol.html">Sunol</a>
          <a href="services/walnut-creek.html">Walnut Creek</a>
        </div>'''

    old_bottom = '''        <p>&copy; 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured &middot; California Contractor</p>'''

    new_bottom = '''        <p>&copy; 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured &middot; California Contractor &middot; <a href="sitemap.html">Site Map</a></p>'''

    new_content = content.replace(old_sa, new_sa, 1).replace(old_bottom, new_bottom, 1)

    if new_content == content:
        return False, 'no change found in generate_portfolio.py'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True, 'updated'


# ── Step 4: Add sitemap.html to sitemap.xml ───────────────────────────────────

def update_sitemap_xml():
    path = os.path.join(PREVIEW_DIR, 'sitemap.xml')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'sitemap' in content.lower() and '/sitemap<' in content:
        return False, 'already present'

    sitemap_entry = f'''  <url>
    <loc>https://www.ridgecrestdesigns.com/sitemap</loc>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
    <lastmod>{TODAY}</lastmod>
  </url>
'''
    # Insert after the opening <urlset> tag / first <url> block — insert before </urlset>
    new_content = content.replace('</urlset>', sitemap_entry + '</urlset>', 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True, 'added sitemap.html to sitemap.xml'


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=== SEO Internal Linking Update ===\n')

    # 1. Create sitemap.html
    sitemap_path = os.path.join(PREVIEW_DIR, 'sitemap.html')
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(build_sitemap_html())
    print(f'[1] Created sitemap.html ({os.path.getsize(sitemap_path):,} bytes)')

    # 2. Batch update all HTML files
    updated, skipped, errors = [], [], []
    for root, dirs, files in os.walk(PREVIEW_DIR):
        # Skip admin and hidden dirs
        dirs[:] = [d for d in dirs if d not in ('admin', '.git', 'node_modules', 'assets')]
        for fname in sorted(files):
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            # Don't update the sitemap page itself
            if fpath == sitemap_path:
                continue
            try:
                ok, msg = update_html_file(fpath)
                rel = os.path.relpath(fpath, PREVIEW_DIR)
                if ok:
                    updated.append(rel)
                else:
                    skipped.append((rel, msg))
            except Exception as e:
                errors.append((os.path.relpath(fpath, PREVIEW_DIR), str(e)))

    print(f'[2] Footer update: {len(updated)} updated, {len(skipped)} unchanged, {len(errors)} errors')
    for f in sorted(updated):
        print(f'    ✓ {f}')
    for f, r in sorted(skipped):
        print(f'    - {f}: {r}')
    for f, r in sorted(errors):
        print(f'    ✗ {f}: {r}', file=sys.stderr)

    # 3. Update generate_portfolio.py
    ok, msg = update_generate_portfolio()
    print(f'[3] generate_portfolio.py: {msg}')

    # 4. Update sitemap.xml
    ok, msg = update_sitemap_xml()
    print(f'[4] sitemap.xml: {msg}')

    print('\nDone.')
