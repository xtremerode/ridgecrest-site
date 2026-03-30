#!/usr/bin/env python3
"""
Master script — builds the complete site structure:
  1. 12 city pages  →  preview/services/[city].html
  2. Services index →  preview/services.html
  3. Nav update     →  adds Services link to all pages
  4. Footer update  →  adds Service Areas column to all pages
  5. Homepage cards →  link to services instead of contact
  6. Sitemap        →  preview/sitemap.xml
"""
import os, re, json, glob

PREVIEW  = '/home/claudeuser/agent/preview'
BASE_URL = 'https://www.ridgecrestdesigns.com'
INQUIRY  = 'https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm'

# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────

CITIES = [
  {'slug': 'danville',     'name': 'Danville',     'zip': '94526',
   'desc': 'Known for its tree-lined streets, top-ranked schools, and estate properties in neighborhoods like Blackhawk and Green Valley.',
   'projects': [('Danville Dream Home', 'danville-dream.html', 'Luxury home remodel — kitchen, master bath, wine cellar'),
                ('Danville Hilltop Hideaway', 'danville-hilltop.html', 'Modern hilltop remodel with panoramic views')]},
  {'slug': 'lafayette',    'name': 'Lafayette',    'zip': '94549',
   'desc': 'A Lamorinda gem blending walkable village charm with some of the East Bay\'s most beautiful residential properties in Happy Valley and Burton Valley.',
   'projects': [('Lafayette Modern Bistro', 'lafayette-bistro.html', 'Kitchen remodel with white oak finishes and open bistro layout'),
                ('Lafayette Laid-Back Luxury', 'lafayette-luxury.html', 'Whole-home remodel with natural materials and indoor-outdoor flow')]},
  {'slug': 'walnut-creek', 'name': 'Walnut Creek', 'zip': '94596',
   'desc': 'The urban heart of Contra Costa County, with Broadway Plaza, a thriving arts scene, and residential neighborhoods from hillside estates to beautifully updated mid-century homes.',
   'projects': []},
  {'slug': 'pleasanton',   'name': 'Pleasanton',   'zip': '94566',
   'desc': 'A thriving Tri-Valley community with a picturesque historic downtown, Ruby Hill, Castlewood, and Happy Valley — home to some of the finest custom estates in the East Bay.',
   'projects': [('Pleasanton Custom Home', 'pleasanton-custom.html', '5,000 sq ft modern farmhouse on 1.4 acres in Happy Valley')]},
  {'slug': 'orinda',       'name': 'Orinda',       'zip': '94563',
   'desc': 'A quiet, wooded Lamorinda community known for its natural beauty, Sleepy Hollow neighborhood, and architecturally interesting hillside residences.',
   'projects': [('Orinda Urban Modern Kitchen', 'orinda-kitchen.html', 'Art-gallery-inspired kitchen with four skylights and hand-painted feature wall')]},
  {'slug': 'alamo',        'name': 'Alamo',        'zip': '94507',
   'desc': 'One of the most exclusive unincorporated communities in Contra Costa County — large-lot estates and gated enclaves including Roundhill and Stone Valley.',
   'projects': [('Alamo Luxury Home', 'alamo-luxury.html', 'Signature luxury remodel with custom architecture and high-end finishes')]},
  {'slug': 'san-ramon',    'name': 'San Ramon',    'zip': '94582',
   'desc': 'A dynamic Tri-Valley city with established neighborhoods including Crow Canyon, Windemere, and Gale Ranch — strong property values and an active luxury real estate market.',
   'projects': [('San Ramon Custom Home', 'san-ramon.html', 'Elevated home remodel with premium materials and modern-luxury aesthetic')]},
  {'slug': 'dublin',       'name': 'Dublin',       'zip': '94568',
   'desc': 'A rapidly growing Tri-Valley city with newer luxury communities including Fallon Gateway, Jordan Ranch, and Positano — close to both Silicon Valley and Oakland.',
   'projects': []},
  {'slug': 'moraga',       'name': 'Moraga',       'zip': '94556',
   'desc': 'A peaceful hillside Lamorinda community surrounded by open space, with private architecturally distinctive residences in Rheem Valley and Sanders Ranch.',
   'projects': []},
  {'slug': 'sunol',        'name': 'Sunol',        'zip': '94586',
   'desc': 'A historic rural community in the hills between Pleasanton and Niles Canyon — vineyard proximity, natural beauty, and an unhurried land-connected lifestyle.',
   'projects': [('Sunol Homestead', 'sunol-homestead.html', 'Custom homestead remodel honoring the rural setting with natural materials')]},
  {'slug': 'rossmoor',     'name': 'Rossmoor',     'zip': '94595',
   'desc': 'A prestigious gated active adult community in Walnut Creek — immaculate grounds, active lifestyle, and residents who expect premium design and finishes.',
   'projects': []},
  {'slug': 'diablo',       'name': 'Diablo',       'zip': '94528',
   'desc': 'One of the most exclusive private communities in Northern California — a gated enclave at the foot of Mount Diablo with a distinguished roster of estate properties.',
   'projects': []},
]

SERVICES = [
  {'slug': 'kitchen-remodel',      'name': 'Kitchen Remodel',           'budget': 'Starting at $150,000'},
  {'slug': 'bathroom-remodel',     'name': 'Bathroom Remodel',          'budget': 'Starting at $60,000'},
  {'slug': 'whole-house-remodel',  'name': 'Whole House Remodel',       'budget': 'Starting at $1,000,000'},
  {'slug': 'custom-home-builder',  'name': 'Custom Home Builder',       'budget': 'Starting at $5,000,000'},
  {'slug': 'design-build',         'name': 'Design-Build Contractor',   'budget': 'All project sizes'},
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. CITY PAGES
# ─────────────────────────────────────────────────────────────────────────────

def generate_city_pages():
  out_dir = os.path.join(PREVIEW, 'services')
  os.makedirs(out_dir, exist_ok=True)

  for city in CITIES:
    slug      = city['slug']
    name      = city['name']
    title     = f"Home Remodeling in {name}, CA — Ridgecrest Designs | Luxury Design-Build"
    meta_desc = f"Luxury home remodeling in {name}, CA by Ridgecrest Designs. Custom homes, kitchen remodels, bathroom remodels, whole house remodels, and design-build services. {city['desc'][:80]}..."
    canonical = f"{BASE_URL}/services/{slug}"

    # Services grid
    svc_cards = ''
    for svc in SERVICES:
      svc_cards += f'''
        <a href="{svc['slug']}-{slug}.html" class="city-service-card">
          <h3 class="city-service-card__name">{svc['name']}</h3>
          <p class="city-service-card__budget">{svc['budget']}</p>
          <span class="city-service-card__link">Learn more →</span>
        </a>'''

    # Portfolio section
    proj_html = ''
    if city['projects']:
      proj_items = ''
      for proj in city['projects']:
        proj_items += f'''
          <a href="../{proj[1]}" class="city-project-item">
            <h3 class="city-project-item__name">{proj[0]}</h3>
            <p class="city-project-item__desc">{proj[2]}</p>
            <span class="city-project-item__link">View project →</span>
          </a>'''
      proj_html = f'''
  <section class="section section--accent">
    <div class="container">
      <p class="section__label">Our Work in {name}</p>
      <h2 class="section__headline">Projects we've completed<br><em>in {name}, CA</em></h2>
      <div class="city-projects-grid">{proj_items}
      </div>
    </div>
  </section>'''

    # Schema
    schema = {
      "@context": "https://schema.org",
      "@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
      "name": "Ridgecrest Designs",
      "description": f"Luxury design-build firm serving {name}, CA. Custom homes, kitchen remodels, bathroom remodels, and whole house remodels.",
      "url": BASE_URL,
      "telephone": "+19257842798",
      "address": {"@type": "PostalAddress", "streetAddress": "5502 Sunol Blvd Suite 100",
                  "addressLocality": "Pleasanton", "addressRegion": "CA", "postalCode": "94566", "addressCountry": "US"},
      "areaServed": {"@type": "City", "name": name, "containedInPlace": {"@type": "State", "name": "California"}},
      "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
        {"@type": "ListItem", "position": 2, "name": "Services", "item": f"{BASE_URL}/services"},
        {"@type": "ListItem", "position": 3, "name": f"Remodeling in {name}", "item": canonical},
      ]}
    }

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{meta_desc}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Ridgecrest Designs" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{meta_desc}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="https://static.wixstatic.com/media/ff5b18_3c0cef18e48849089c5ed48614041900~mv2.png" />
  <script type="application/ld+json">
  {json.dumps(schema, indent=2)}
  </script>
  <link rel="stylesheet" href="../css/main.css" />
  <link rel="stylesheet" href="../css/service-pages.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Jost:wght@300;400;500&display=swap" rel="stylesheet" />
</head>
<body>

  <nav class="nav nav--scrolled" id="nav">
    <a href="../index.html" class="nav__logo">RIDGECREST DESIGNS</a>
    <button class="nav__toggle" id="navToggle" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav__links" id="navLinks">
      <li><a href="../about.html">About</a></li>
      <li><a href="../process.html">Process</a></li>
      <li><a href="../services.html" class="nav__active">Services</a></li>
      <li><a href="../portfolio.html">Portfolio</a></li>
      <li><a href="../team.html">Team</a></li>
      <li><a href="../contact.html" class="nav__cta">Start a Project</a></li>
    </ul>
  </nav>

  <div class="page-hero page-hero--service">
    <p class="page-hero__eyebrow">Service Area · {name}, CA</p>
    <h1 class="page-hero__title">Home Remodeling<br><em>in {name}, CA</em></h1>
    <p class="page-hero__sub">Luxury design-build services tailored to {name} homeowners.</p>
    <div class="page-hero__actions">
      <a href="{INQUIRY}" class="btn btn--primary btn--lg">Start Your Project Inquiry</a>
      <a href="../portfolio.html" class="btn btn--ghost">View Our Work</a>
    </div>
  </div>

  <section class="section section--accent">
    <div class="container container--narrow">
      <p class="section__label">Ridgecrest Designs · {name}, CA</p>
      <h2 class="section__headline">We build in {name}.<br><em>We know {name}.</em></h2>
      <div class="service-intro-body">
        <p>{city['desc']} Ridgecrest Designs has worked with {name} homeowners on projects ranging from high-end kitchen and bathroom remodels to full custom homes and whole-house transformations.</p>
        <p>Every project begins with photo-realistic renders — photographic-quality images of your finished home before a permit is filed. That means you see every detail, confirm every finish, and approve the full scope before a single wall comes down. It is the single most powerful tool for keeping a luxury remodel on track, on budget, and aligned with your vision.</p>
        <p>We take on a limited number of projects each year to ensure every {name} client receives our full attention. If you are considering a remodel or custom home, reach out early.</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <p class="section__label">What We Do in {name}</p>
      <h2 class="section__headline">Services available<br><em>in {name}, CA</em></h2>
      <div class="city-services-grid">{svc_cards}
      </div>
    </div>
  </section>
  {proj_html}

  <section class="section section--dark">
    <div class="container">
      <p class="section__label">Why {name} Homeowners Choose Ridgecrest</p>
      <h2 class="section__headline">What sets us apart<br><em>in {name}</em></h2>
      <div class="diff-grid">
        <div class="diff-item">
          <h3 class="diff-item__title">Photo-Realistic Renders</h3>
          <p class="diff-item__body">See your finished home in photographic detail before construction begins. Every material, every finish, confirmed before we break ground.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">One Firm, Full Scope</h3>
          <p class="diff-item__body">Design, engineering, permitting, and construction under one contract. No handoffs. No finger-pointing. One point of accountability.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Local Permitting Expertise</h3>
          <p class="diff-item__body">We manage every permit application, response, and inspection in {name} — so you never have to wonder where your project stands.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Premium Craftsmanship</h3>
          <p class="diff-item__body">Our subcontractors are selected for quality, not cost. Every trade is held to the same standard of precision and accountability.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Limited Availability</h3>
          <p class="diff-item__body">We take on a carefully limited number of projects per year. Every {name} client receives our full attention from first meeting to final walkthrough.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Est. 2013 in the East Bay</h3>
          <p class="diff-item__body">Over a decade of luxury design-build projects across Pleasanton, Danville, Lafayette, and the broader East Bay. We know what it takes.</p>
        </div>
      </div>
    </div>
  </section>

  <section class="cta section section--dark" style="background:var(--charcoal)">
    <div class="container container--narrow cta__inner">
      <h2 class="cta__headline">Ready to start your<br><em>project in {name}?</em></h2>
      <p class="cta__sub">Submit a project inquiry and we'll follow up within one business day.</p>
      <a href="{INQUIRY}" class="btn btn--primary btn--lg">Submit a Project Inquiry</a>
      <p class="cta__note">Or call <a href="tel:9257842798">925-784-2798</a></p>
    </div>
  </section>

  <footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <span class="footer__logo">RIDGECREST DESIGNS</span>
        <p class="footer__tagline">Luxury Design-Build · Est. 2013</p>
        <p class="footer__address">5502 Sunol Blvd, Suite 100<br>Pleasanton, CA 94566</p>
        <p><a href="tel:9257842798">925-784-2798</a> · <a href="mailto:info@ridgecrestdesigns.com">info@ridgecrestdesigns.com</a></p>
      </div>
      <div class="footer__nav">
        <div class="footer__col">
          <p class="footer__col-head">Company</p>
          <a href="../about.html">About</a>
          <a href="../team.html">Team</a>
          <a href="../process.html">Process</a>
          <a href="../portfolio.html">Portfolio</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Services</p>
          <a href="custom-home-builder-{slug}.html">Custom Homes</a>
          <a href="whole-house-remodel-{slug}.html">Whole House Remodels</a>
          <a href="kitchen-remodel-{slug}.html">Kitchen Remodels</a>
          <a href="bathroom-remodel-{slug}.html">Bathroom Remodels</a>
          <a href="design-build-{slug}.html">Design-Build</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="danville.html">Danville</a>
          <a href="lafayette.html">Lafayette</a>
          <a href="walnut-creek.html">Walnut Creek</a>
          <a href="alamo.html">Alamo</a>
          <a href="orinda.html">Orinda</a>
          <a href="pleasanton.html">Pleasanton</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Connect</p>
          <a href="{INQUIRY}">Start a Project</a>
          <a href="../contact.html">Contact Us</a>
          <a href="https://www.instagram.com/ridgecrestdesigns" target="_blank" rel="noopener">Instagram</a>
          <a href="https://www.facebook.com/ridgecrestdesigns" target="_blank" rel="noopener">Facebook</a>
          <a href="https://www.houzz.com/pro/ridgecrestdesigns" target="_blank" rel="noopener">Houzz</a>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <div class="container">
        <p>© 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured · California Contractor</p>
      </div>
    </div>
  </footer>

  <script src="../js/main.js"></script>
</body>
</html>'''

    path = os.path.join(out_dir, f'{slug}.html')
    with open(path, 'w', encoding='utf-8') as f:
      f.write(html)
    print(f'  ✓  services/{slug}.html')


# ─────────────────────────────────────────────────────────────────────────────
# 2. SERVICES INDEX PAGE  (preview/services.html)
# ─────────────────────────────────────────────────────────────────────────────

def generate_services_index():
  title     = 'Services — Ridgecrest Designs | Luxury Design-Build, East Bay CA'
  meta_desc = 'Luxury design-build services across the East Bay: kitchen remodels, bathroom remodels, whole house remodels, custom homes, and design-build contracting in Danville, Lafayette, Walnut Creek, Pleasanton, Orinda, Alamo, San Ramon, and beyond.'
  canonical = f'{BASE_URL}/services'

  # City cards
  city_cards = ''
  for city in CITIES:
    city_cards += f'''
        <a href="services/{city['slug']}.html" class="services-city-card">
          <h3 class="services-city-card__name">{city['name']}, CA</h3>
          <p class="services-city-card__desc">{city['desc'][:90]}...</p>
          <span class="services-city-card__link">View services →</span>
        </a>'''

  # Service rows
  svc_rows = ''
  for svc in SERVICES:
    city_links = ' · '.join(
      f'<a href="services/{svc["slug"]}-{c["slug"]}.html">{c["name"]}</a>'
      for c in CITIES
    )
    svc_rows += f'''
        <div class="services-svc-row">
          <div class="services-svc-row__header">
            <h3 class="services-svc-row__name">{svc['name']}</h3>
            <span class="services-svc-row__budget">{svc['budget']}</span>
          </div>
          <p class="services-svc-row__cities">{city_links}</p>
        </div>'''

  schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "Services — Ridgecrest Designs",
    "url": canonical,
    "description": meta_desc,
    "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
      {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
      {"@type": "ListItem", "position": 2, "name": "Services", "item": canonical},
    ]}
  }

  html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{meta_desc}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Ridgecrest Designs" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{meta_desc}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="https://static.wixstatic.com/media/ff5b18_3c0cef18e48849089c5ed48614041900~mv2.png" />
  <script type="application/ld+json">
  {json.dumps(schema, indent=2)}
  </script>
  <link rel="stylesheet" href="css/main.css" />
  <link rel="stylesheet" href="css/service-pages.css" />
  <link rel="stylesheet" href="css/services-index.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Jost:wght@300;400;500&display=swap" rel="stylesheet" />
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
      <li><a href="services.html" class="nav__active">Services</a></li>
      <li><a href="portfolio.html">Portfolio</a></li>
      <li><a href="team.html">Team</a></li>
      <li><a href="contact.html" class="nav__cta">Start a Project</a></li>
    </ul>
  </nav>

  <div class="page-hero">
    <p class="page-hero__eyebrow">Luxury Design-Build · East Bay, California</p>
    <h1 class="page-hero__title">Services &amp; Locations</h1>
    <p class="page-hero__sub">Every service. Every community we serve.</p>
  </div>

  <!-- BY LOCATION -->
  <section class="section section--accent">
    <div class="container">
      <p class="section__label">By Location</p>
      <h2 class="section__headline">Find services in<br><em>your community</em></h2>
      <div class="services-cities-grid">{city_cards}
      </div>
    </div>
  </section>

  <!-- BY SERVICE -->
  <section class="section">
    <div class="container">
      <p class="section__label">By Service</p>
      <h2 class="section__headline">Find your service<br><em>in every city</em></h2>
      <div class="services-svc-list">{svc_rows}
      </div>
    </div>
  </section>

  <section class="cta section section--dark" style="background:var(--charcoal)">
    <div class="container container--narrow cta__inner">
      <h2 class="cta__headline">Not sure where to start?<br><em>We'll help.</em></h2>
      <p class="cta__sub">Tell us about your project and we'll follow up within one business day.</p>
      <a href="{INQUIRY}" class="btn btn--primary btn--lg">Submit a Project Inquiry</a>
      <p class="cta__note">Or call <a href="tel:9257842798">925-784-2798</a></p>
    </div>
  </section>

  <footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <span class="footer__logo">RIDGECREST DESIGNS</span>
        <p class="footer__tagline">Luxury Design-Build · Est. 2013</p>
        <p class="footer__address">5502 Sunol Blvd, Suite 100<br>Pleasanton, CA 94566</p>
        <p><a href="tel:9257842798">925-784-2798</a> · <a href="mailto:info@ridgecrestdesigns.com">info@ridgecrestdesigns.com</a></p>
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
          <a href="services/design-build-danville.html">Design-Build</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="services/danville.html">Danville</a>
          <a href="services/lafayette.html">Lafayette</a>
          <a href="services/walnut-creek.html">Walnut Creek</a>
          <a href="services/alamo.html">Alamo</a>
          <a href="services/orinda.html">Orinda</a>
          <a href="services/pleasanton.html">Pleasanton</a>
          <a href="services/san-ramon.html">San Ramon</a>
          <a href="services/dublin.html">Dublin</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Connect</p>
          <a href="{INQUIRY}">Start a Project</a>
          <a href="contact.html">Contact Us</a>
          <a href="https://www.instagram.com/ridgecrestdesigns" target="_blank" rel="noopener">Instagram</a>
          <a href="https://www.facebook.com/ridgecrestdesigns" target="_blank" rel="noopener">Facebook</a>
          <a href="https://www.houzz.com/pro/ridgecrestdesigns" target="_blank" rel="noopener">Houzz</a>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <div class="container">
        <p>© 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured · California Contractor</p>
      </div>
    </div>
  </footer>

  <script src="js/main.js"></script>
</body>
</html>'''

  path = os.path.join(PREVIEW, 'services.html')
  with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
  print('  ✓  services.html')


# ─────────────────────────────────────────────────────────────────────────────
# 3 & 4. NAV + FOOTER UPDATE — all existing HTML files
# ─────────────────────────────────────────────────────────────────────────────

# Footer Service Areas column to inject (root pages — paths relative to root)
FOOTER_AREAS_ROOT = '''        <div class="footer__col">
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

# Footer Service Areas column for services/ subdirectory pages
FOOTER_AREAS_SUB = '''        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="danville.html">Danville</a>
          <a href="lafayette.html">Lafayette</a>
          <a href="walnut-creek.html">Walnut Creek</a>
          <a href="alamo.html">Alamo</a>
          <a href="orinda.html">Orinda</a>
          <a href="pleasanton.html">Pleasanton</a>
          <a href="san-ramon.html">San Ramon</a>
          <a href="dublin.html">Dublin</a>
        </div>'''

def update_nav_footer():
  # Root HTML files
  root_files = glob.glob(os.path.join(PREVIEW, '*.html'))
  # Services subdir HTML files (already have correct nav from generator)
  sub_files  = glob.glob(os.path.join(PREVIEW, 'services', '*.html'))

  # ── Root files ──
  for path in root_files:
    with open(path, 'r', encoding='utf-8') as f:
      html = f.read()

    changed = False

    # Add Services nav link (after process, before portfolio) — skip if already present
    if 'href="services.html"' not in html and '>Services<' not in html:
      html = html.replace(
        '<li><a href="portfolio.html">Portfolio</a></li>',
        '<li><a href="services.html">Services</a></li>\n      <li><a href="portfolio.html">Portfolio</a></li>'
      )
      changed = True

    # Add Service Areas footer column — skip if already present
    if 'Service Areas' not in html:
      # Insert before the Connect column closing + footer__nav closing
      html = html.replace(
        '        <div class="footer__col">\n          <p class="footer__col-head">Connect</p>',
        FOOTER_AREAS_ROOT + '\n        <div class="footer__col">\n          <p class="footer__col-head">Connect</p>'
      )
      changed = True

    if changed:
      with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
      print(f'  ✓  {os.path.basename(path)}')

  # ── Services subdir files ──
  for path in sub_files:
    with open(path, 'r', encoding='utf-8') as f:
      html = f.read()

    # Add Service Areas footer column if missing
    if 'Service Areas' not in html:
      html = html.replace(
        '        <div class="footer__col">\n          <p class="footer__col-head">Connect</p>',
        FOOTER_AREAS_SUB + '\n        <div class="footer__col">\n          <p class="footer__col-head">Connect</p>'
      )
      with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
      print(f'  ✓  services/{os.path.basename(path)}')


# ─────────────────────────────────────────────────────────────────────────────
# 5. HOMEPAGE SERVICE CARDS — link to services index
# ─────────────────────────────────────────────────────────────────────────────

def update_homepage_cards():
  path = os.path.join(PREVIEW, 'index.html')
  with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

  # The 4 service cards currently link to contact.html — update to service pages
  replacements = [
    ('Custom Homes', 'services/custom-home-builder-danville.html'),
    ('Whole House Remodels', 'services/whole-house-remodel-danville.html'),
    ('Kitchen Remodels', 'services/kitchen-remodel-danville.html'),
    ('Bathroom Remodels', 'services/bathroom-remodel-danville.html'),
  ]
  # Also add a "Browse All Services" link to the portfolio strip section label area
  # and update the "View All Work" footer services links
  for name, new_href in replacements:
    # Find the service card anchor that contains this service name and update href
    pattern = r'(<a href=")contact\.html("[^>]*>(?:(?!</a>).)*?' + re.escape(name) + r')'
    html = re.sub(pattern, rf'\g<1>{new_href}\2', html, flags=re.DOTALL)

  with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
  print('  ✓  index.html (service card links updated)')


# ─────────────────────────────────────────────────────────────────────────────
# 6. SITEMAP
# ─────────────────────────────────────────────────────────────────────────────

def generate_sitemap():
  urls = []

  # Priority pages
  urls.append(('/', '1.0', 'weekly'))
  urls.append(('/about', '0.8', 'monthly'))
  urls.append(('/process', '0.8', 'monthly'))
  urls.append(('/portfolio', '0.8', 'weekly'))
  urls.append(('/contact', '0.9', 'monthly'))
  urls.append(('/services', '0.9', 'weekly'))

  # Project pages
  projects = ['danville-dream','danville-hilltop','pleasanton-custom','alamo-luxury',
              'lafayette-bistro','lafayette-luxury','san-ramon','orinda-kitchen','sunol-homestead']
  for p in projects:
    urls.append((f'/{p}', '0.7', 'monthly'))

  # City pages
  for city in CITIES:
    urls.append((f'/services/{city["slug"]}', '0.8', 'monthly'))

  # Service × location pages
  for svc in SERVICES:
    for city in CITIES:
      urls.append((f'/services/{svc["slug"]}-{city["slug"]}', '0.7', 'monthly'))

  lines = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
  for url, priority, freq in urls:
    lines.append(f'''  <url>
    <loc>{BASE_URL}{url}</loc>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>''')
  lines.append('</urlset>')

  path = os.path.join(PREVIEW, 'sitemap.xml')
  with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
  print(f'  ✓  sitemap.xml  ({len(urls)} URLs)')


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
  print('\n── Step 1: City pages ──────────────────────────')
  generate_city_pages()

  print('\n── Step 2: Services index ──────────────────────')
  generate_services_index()

  print('\n── Step 3 & 4: Nav + footer update ────────────')
  update_nav_footer()

  print('\n── Step 5: Homepage card links ─────────────────')
  update_homepage_cards()

  print('\n── Step 6: Sitemap ─────────────────────────────')
  generate_sitemap()

  print('\n✓ All done.')
