#!/usr/bin/env python3
"""
Generate 60 service × location landing pages for Ridgecrest Designs.
5 services × 12 cities = 60 pages, each with unique city + service content.
Output: /home/claudeuser/agent/preview/services/[service]-[city-slug].html
"""
import os, json

PREVIEW = '/home/claudeuser/agent/preview'
OUT_DIR  = os.path.join(PREVIEW, 'services')
BASE_URL = 'https://www.ridgecrestdesigns.com'
INQUIRY  = 'https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm'

os.makedirs(OUT_DIR, exist_ok=True)

# ── City data ─────────────────────────────────────────────────────────────────
CITIES = {
  'danville': {
    'name': 'Danville',
    'state': 'CA',
    'zip': '94526',
    'lat': 37.8216, 'lng': -121.9999,
    'character': 'one of the most sought-after communities in the East Bay — known for its tree-lined streets, top-ranked schools, and estate properties that reflect the refined sensibility of its residents',
    'neighborhoods': 'Blackhawk, Sycamore, Green Valley, and the historic downtown village',
    'buyer_profile': 'Danville homeowners are discerning buyers who expect precision, process, and results that reflect their investment',
    'related_project': ('Danville Dream Home', '../danville-dream.html', 'luxury home remodel featuring a custom kitchen, spa-style master bath, and wine cellar'),
    'related_project2': ('Danville Hilltop Hideaway', '../danville-hilltop.html', 'mid-century hilltop remodel with panoramic views and premium natural materials'),
  },
  'lafayette': {
    'name': 'Lafayette',
    'state': 'CA',
    'zip': '94549',
    'lat': 37.8858, 'lng': -122.1180,
    'character': 'a Lamorinda gem that blends walkable village charm with some of the East Bay\'s most beautiful residential properties',
    'neighborhoods': 'Happy Valley, Burton Valley, Springhill, and the vibrant downtown corridor',
    'buyer_profile': 'Lafayette homeowners value authenticity and quality — they want a home that feels both refined and lived-in, where every detail is intentional',
    'related_project': ('Lafayette Modern Bistro', '../lafayette-bistro.html', 'kitchen remodel with custom cabinetry, white oak finishes, and an open bistro-style layout'),
    'related_project2': ('Lafayette Laid-Back Luxury', '../lafayette-luxury.html', 'whole-home remodel with natural materials and effortless indoor-outdoor flow'),
  },
  'walnut-creek': {
    'name': 'Walnut Creek',
    'state': 'CA',
    'zip': '94596',
    'lat': 37.9101, 'lng': -122.0652,
    'character': 'the urban heart of Contra Costa County — offering Broadway Plaza shopping, a thriving arts scene, and residential neighborhoods that range from hillside estates to beautifully updated mid-century homes',
    'neighborhoods': 'Rossmoor, Parkmead, Northgate, and the Lakewood area',
    'buyer_profile': 'Walnut Creek homeowners are sophisticated and quality-driven — they want modern living that doesn\'t sacrifice warmth or character',
    'related_project': None,
    'related_project2': None,
  },
  'pleasanton': {
    'name': 'Pleasanton',
    'state': 'CA',
    'zip': '94566',
    'lat': 37.6624, 'lng': -121.8747,
    'character': 'a thriving Tri-Valley community with a picturesque historic downtown, top-rated schools, and established neighborhoods ranging from custom estates in Happy Valley to newer luxury developments near the Castlewood Country Club',
    'neighborhoods': 'Happy Valley, Ruby Hill, Castlewood, and the historic downtown area',
    'buyer_profile': 'Pleasanton homeowners expect a firm that can handle the complexity of premium residential work — on time, on budget, and to an exacting standard',
    'related_project': ('Pleasanton Custom Home', '../pleasanton-custom.html', '5,000 sq ft modern farmhouse custom build on 1.4 acres in Happy Valley'),
    'related_project2': None,
  },
  'orinda': {
    'name': 'Orinda',
    'state': 'CA',
    'zip': '94563',
    'lat': 37.8771, 'lng': -122.1797,
    'character': 'a quiet, wooded Lamorinda community beloved for its natural beauty, historic Orinda Theatre, and some of the most architecturally interesting residential properties in the East Bay',
    'neighborhoods': 'Sleepy Hollow, Orinda Village, Glorietta, and the hillside estates above Highway 24',
    'buyer_profile': 'Orinda homeowners appreciate design that respects the natural setting — they want thoughtful, architecturally coherent work that enhances rather than overwhelms',
    'related_project': ('Orinda Urban Modern Kitchen', '../orinda-kitchen.html', 'art-gallery-inspired kitchen remodel with four skylights, custom cabinetry, and a hand-painted warehouse wall'),
    'related_project2': None,
  },
  'alamo': {
    'name': 'Alamo',
    'state': 'CA',
    'zip': '94507',
    'lat': 37.8524, 'lng': -122.0327,
    'character': 'an unincorporated community of large-lot estates and gated enclaves that sits between Danville and Walnut Creek — consistently among the most exclusive residential addresses in Contra Costa County',
    'neighborhoods': 'Stone Valley, Roundhill, Alamo Ridge, and the Summit Drive corridor',
    'buyer_profile': 'Alamo homeowners are accustomed to quality and expect a design-build firm that operates at the same level — meticulous, discreet, and completely accountable',
    'related_project': ('Alamo Luxury Home', '../alamo-luxury.html', 'signature luxury remodel with custom architecture, high-end finishes, and timeless craftsmanship'),
    'related_project2': None,
  },
  'san-ramon': {
    'name': 'San Ramon',
    'state': 'CA',
    'zip': '94582',
    'lat': 37.7799, 'lng': -121.9780,
    'character': 'a dynamic Tri-Valley city known for Bishop Ranch business park, excellent schools, and well-established residential neighborhoods with strong property values and an active luxury real estate market',
    'neighborhoods': 'Crow Canyon, Windemere, Bollinger Hills, and Gale Ranch',
    'buyer_profile': 'San Ramon homeowners are growth-minded and results-oriented — they want a firm that brings the same discipline to construction that they bring to their careers',
    'related_project': ('San Ramon Custom Home', '../san-ramon.html', 'elevated home remodel with premium materials and a cohesive modern-luxury aesthetic'),
    'related_project2': None,
  },
  'dublin': {
    'name': 'Dublin',
    'state': 'CA',
    'zip': '94568',
    'lat': 37.7022, 'lng': -121.9358,
    'character': 'a rapidly growing Tri-Valley city with newer luxury communities, top-tier schools, and an increasingly affluent resident base drawn by proximity to both Silicon Valley and Oakland',
    'neighborhoods': 'Fallon Gateway, Jordan Ranch, The Groves, and Positano',
    'buyer_profile': 'Dublin homeowners are forward-thinking and quality-focused — they want their home to reflect where they\'re headed, not where they started',
    'related_project': None,
    'related_project2': None,
  },
  'moraga': {
    'name': 'Moraga',
    'state': 'CA',
    'zip': '94556',
    'lat': 37.8349, 'lng': -122.1299,
    'character': 'a peaceful hillside community in the heart of the Lamorinda area — intimate in scale, surrounded by open space, and home to some of the most private and architecturally distinctive residences in the East Bay',
    'neighborhoods': 'Rheem Valley, Sanders Ranch, Canyon Estates, and the St. Mary\'s College corridor',
    'buyer_profile': 'Moraga homeowners value privacy, craftsmanship, and quiet confidence — they want a design-build firm that lets the work speak for itself',
    'related_project': None,
    'related_project2': None,
  },
  'sunol': {
    'name': 'Sunol',
    'state': 'CA',
    'zip': '94586',
    'lat': 37.5983, 'lng': -121.8808,
    'character': 'a historic rural community tucked into the hills between Pleasanton and Niles Canyon — beloved for its natural beauty, vineyard proximity, and the kind of unhurried, land-connected lifestyle that is increasingly rare in the Bay Area',
    'neighborhoods': 'Sunol Valley, Kilkare Woods, and the historic downtown',
    'buyer_profile': 'Sunol homeowners are drawn to authenticity — they want a design-build partner who can work with the land and the architecture to create something that feels genuinely rooted',
    'related_project': ('Sunol Homestead', '../sunol-homestead.html', 'custom homestead remodel with natural materials and precision craftsmanship that honors the rural setting'),
    'related_project2': None,
  },
  'rossmoor': {
    'name': 'Rossmoor',
    'state': 'CA',
    'zip': '94595',
    'lat': 37.9007, 'lng': -122.0701,
    'character': 'a prestigious gated active adult community in Walnut Creek — known for its immaculate grounds, active social scene, and residents who expect the very best in home design and finishes',
    'neighborhoods': 'Golden Rain Road, Tice Creek, and the Manor House area',
    'buyer_profile': 'Rossmoor homeowners have spent decades building wealth and taste — they want a design-build firm that brings the same level of polish to their home that they bring to everything else',
    'related_project': None,
    'related_project2': None,
  },
  'diablo': {
    'name': 'Diablo',
    'state': 'CA',
    'zip': '94528',
    'lat': 37.8380, 'lng': -121.9571,
    'character': 'one of the most exclusive private communities in Northern California — a gated enclave at the foot of Mount Diablo with an intimate roster of distinguished estate properties and a long tradition of architectural excellence',
    'neighborhoods': 'Diablo Country Club, Mount Diablo Scenic Boulevard, and the private roads surrounding the club',
    'buyer_profile': 'Diablo homeowners operate at the highest level in everything they do — they expect the same from their design-build firm: total accountability, absolute discretion, and results that are above reproach',
    'related_project': None,
    'related_project2': None,
  },
}

# ── Service data ───────────────────────────────────────────────────────────────
SERVICES = {
  'kitchen-remodel': {
    'name': 'Kitchen Remodel',
    'slug': 'kitchen-remodel',
    'h1_template': 'Kitchen Remodel in {city}',
    'title_template': 'Kitchen Remodel {city}, CA — Ridgecrest Designs | Luxury Kitchen Renovation',
    'meta_template': 'Luxury kitchen remodels in {city}, CA by Ridgecrest Designs. Custom cabinetry, photo-realistic renders, integrated design-build process. Starting at $150,000.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_94919d08fc9245fc849ac03c4ea2caaf~mv2.jpg',
    'eyebrow': 'Kitchen Remodeling',
    'tagline': 'Photo-realistic renders. Custom cabinetry. Zero surprises.',
    'intro_template': (
      'A great kitchen is the center of a great home — and in {city}, where quality living is the standard, '
      'the bar for what a kitchen remodel should deliver is exceptionally high. Ridgecrest Designs brings a '
      'luxury design-build approach to every kitchen project we take on: integrated design, photo-realistic '
      'renders before a single cabinet is ordered, and hands-on management from first meeting through final walkthrough.'
    ),
    'service_intro': (
      'Our kitchen remodel projects start at $150,000 and are designed for homeowners who want the full picture '
      'before construction begins. That means custom cabinetry designed around your workflow, appliances specified '
      'to your cooking style, lighting that performs as beautifully as it looks, and finishes — countertops, '
      'backsplash, flooring — selected with the whole space in mind, not in isolation.'
    ),
    'what_included': [
      'Full design consultation and needs analysis',
      'Photo-realistic 3D renders of your finished kitchen',
      'Custom cabinetry design and specification',
      'Appliance selection and coordination',
      'Countertop, backsplash, and flooring specification',
      'Lighting design and electrical planning',
      'Plumbing reconfiguration where needed',
      'Permitting and inspections managed end-to-end',
      'Premium subcontractors hand-selected for each trade',
      'Active project management through completion',
    ],
    'budget_note': 'Kitchen remodel projects with Ridgecrest Designs start at $150,000. We work best with homeowners ready for a comprehensive transformation — not a surface-level refresh.',
    'schema_service': 'Kitchen Remodeling',
    'price_range': '$150,000+',
  },
  'bathroom-remodel': {
    'name': 'Bathroom Remodel',
    'slug': 'bathroom-remodel',
    'h1_template': 'Bathroom Remodel in {city}',
    'title_template': 'Bathroom Remodel {city}, CA — Ridgecrest Designs | Luxury Bathroom Renovation',
    'meta_template': 'Luxury bathroom and master bath remodels in {city}, CA by Ridgecrest Designs. Spa-quality finishes, photo-realistic renders, integrated design-build. Starting at $60,000.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_3c0cef18e48849089c5ed48614041900~mv2.png',
    'eyebrow': 'Bathroom Remodeling',
    'tagline': 'Spa-quality finishes. Flawless execution. Every detail considered.',
    'intro_template': (
      'A luxury bathroom remodel in {city} is one of the highest-return investments a homeowner can make — '
      'and one of the most technically demanding. The combination of waterproofing, tile work, plumbing, electrical, '
      'and finish carpentry demands a level of coordination that separates a great outcome from a merely acceptable one. '
      'Ridgecrest Designs manages the full process under one roof, with photo-realistic renders so you can see the '
      'finished space before any demo begins.'
    ),
    'service_intro': (
      'We specialize in master bathroom remodels ($100,000+) and full bathroom renovations ($60,000+) for '
      '{city} homeowners who want a spa-quality result without the stress of coordinating multiple contractors. '
      'Our process begins with a render — a photorealistic image of your finished bathroom — so every decision '
      'is made with full visual clarity before we touch a tile.'
    ),
    'what_included': [
      'Full design consultation and space planning',
      'Photo-realistic 3D renders of your finished bathroom',
      'Tile selection and layout planning',
      'Fixture, hardware, and vanity specification',
      'Custom shower and freestanding tub design',
      'Lighting and ventilation design',
      'Heated floor and radiant system specification',
      'Plumbing and electrical planning',
      'Permitting and inspections managed end-to-end',
      'Active project management through final walkthrough',
    ],
    'budget_note': 'Bathroom remodels with Ridgecrest Designs start at $60,000, with master bathroom remodels typically starting at $100,000. We are the right firm for comprehensive bathroom transformations — not minor updates.',
    'schema_service': 'Bathroom Remodeling',
    'price_range': '$60,000+',
  },
  'whole-house-remodel': {
    'name': 'Whole House Remodel',
    'slug': 'whole-house-remodel',
    'h1_template': 'Whole House Remodel in {city}',
    'title_template': 'Whole House Remodel {city}, CA — Ridgecrest Designs | Full Home Renovation',
    'meta_template': 'Luxury whole house remodels in {city}, CA by Ridgecrest Designs. Full-home transformations starting at $1M. Integrated design-build, photo-realistic renders, zero surprises.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_39536b28ce0447b9a87797bb4c70ee51~mv2.jpg',
    'eyebrow': 'Whole House Remodeling',
    'tagline': 'One firm. One contract. A completely transformed home.',
    'intro_template': (
      'A whole house remodel in {city} is one of the most complex and consequential projects a homeowner '
      'can undertake. When done right, it transforms not just the aesthetics of a home but the entire '
      'experience of living in it. When done wrong — with misaligned contractors, scope creep, and budget '
      'surprises — it becomes a source of genuine stress. Ridgecrest Designs was built specifically for this '
      'kind of work: comprehensive, integrated, and managed under one roof from day one.'
    ),
    'service_intro': (
      'Our whole house remodel projects start at $1,000,000 and typically span 8 to 18 months depending on '
      'scope. We take on a limited number of whole-home projects each year to ensure every client receives '
      'our full attention. Every project begins with a detailed design phase — including photo-realistic renders '
      'of every major space — so you have complete visual and financial clarity before construction begins.'
    ),
    'what_included': [
      'Comprehensive design consultation and programming',
      'Photo-realistic 3D renders of every major space',
      'Architectural and structural planning',
      'Kitchen, bath, and living area design',
      'Mechanical, electrical, and plumbing coordination',
      'Custom cabinetry and millwork throughout',
      'Flooring, tile, and finish specification',
      'Window, door, and exterior coordination',
      'Full permitting and engineering management',
      'Active project management through final punch list',
    ],
    'budget_note': 'Whole house remodel projects with Ridgecrest Designs start at $1,000,000. This scope demands a firm with the depth, process, and accountability to execute without compromise.',
    'schema_service': 'Whole House Remodeling',
    'price_range': '$1,000,000+',
  },
  'custom-home-builder': {
    'name': 'Custom Home Builder',
    'slug': 'custom-home-builder',
    'h1_template': 'Custom Home Builder in {city}',
    'title_template': 'Custom Home Builder {city}, CA — Ridgecrest Designs | Luxury Custom Homes',
    'meta_template': 'Luxury custom home builder in {city}, CA. Ridgecrest Designs builds custom homes from $5M–$10M with photo-realistic renders, integrated design-build, and flawless execution.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_9820c1603a9c414d8cc8009784d1ca7c~mv2.jpg',
    'eyebrow': 'Custom Home Design & Build',
    'tagline': 'From vision and visualization through permitting and construction.',
    'intro_template': (
      'Building a custom home in {city} — where property values are high, expectations are higher, '
      'and the details matter at every level — requires a design-build firm with the depth to carry '
      'a project from raw land to finished home without losing accountability along the way. Ridgecrest '
      'Designs builds luxury custom homes for discerning homeowners who want a single, trusted partner '
      'managing design, engineering, permitting, and construction under one contract.'
    ),
    'service_intro': (
      'Our custom home projects range from $5,000,000 to $10,000,000 and begin with a design phase that '
      'includes photo-realistic renders of your home before a permit is filed. This is not a rendering '
      'tool — it is a decision-making tool. You will see your home in photographic detail, refine every '
      'room, adjust every material, and arrive at a design you\'re completely confident in before '
      'construction begins. That clarity is what makes a Ridgecrest custom home different.'
    ),
    'what_included': [
      'Site analysis and feasibility assessment',
      'Full architectural design and space planning',
      'Photo-realistic 3D renders of every exterior and interior space',
      'Structural and civil engineering coordination',
      'Full permitting management with {city} building department',
      'Custom cabinetry, millwork, and finish specification',
      'Mechanical, electrical, plumbing, and HVAC design',
      'Landscape and hardscape coordination',
      'Premium subcontractor selection and management',
      'Active construction management through final certificate of occupancy',
    ],
    'budget_note': 'Custom home projects with Ridgecrest Designs start at $5,000,000. We build for homeowners creating a long-term legacy residence — not a speculative flip.',
    'schema_service': 'Custom Home Building',
    'price_range': '$5,000,000+',
  },
  'design-build': {
    'name': 'Design-Build Contractor',
    'slug': 'design-build',
    'h1_template': 'Design-Build Contractor in {city}',
    'title_template': 'Design-Build Contractor {city}, CA — Ridgecrest Designs | Integrated Design & Construction',
    'meta_template': 'Design-build contractor in {city}, CA. Ridgecrest Designs manages design, engineering, permitting, and construction under one roof. Luxury homes and remodels. Photo-realistic renders.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_3c0cef18e48849089c5ed48614041900~mv2.png',
    'eyebrow': 'Integrated Design-Build',
    'tagline': 'One team. One contract. No gaps, no finger-pointing, no surprises.',
    'intro_template': (
      'The design-build model exists to solve the most common problem in residential construction: '
      'the misalignment between design intent and construction reality. In {city}, where projects are '
      'complex and budgets are significant, that misalignment is expensive. Ridgecrest Designs eliminates '
      'it entirely by managing design, engineering, permitting, and construction under one roof — '
      'with one point of accountability for the entire project.'
    ),
    'service_intro': (
      'Our design-build process begins with photo-realistic renders — not sketches or floorplans, but '
      'photographic-quality images of your finished home or remodeled space. Those renders become the '
      'blueprint for everything that follows: the permit set, the construction documents, the subcontractor '
      'scope, and the material specifications. By the time we break ground, every decision has been made, '
      'every cost has been accounted for, and every party knows exactly what is being built.'
    ),
    'what_included': [
      'Integrated design and construction under one contract',
      'Photo-realistic 3D renders before any permits are filed',
      'Full architectural and engineering coordination',
      'Permitting management with {city} building department',
      'Single point of contact and accountability throughout',
      'Budget transparency from design through closeout',
      'Premium subcontractor selection and daily management',
      'No coordination gaps between designer and builder',
      'Active project management and weekly client communication',
      'Final walkthrough and punch list completion',
    ],
    'budget_note': 'Ridgecrest Designs works on design-build projects starting at $60,000 for bathroom remodels, $150,000 for kitchen remodels, $1M+ for whole-home work, and $5M+ for custom homes.',
    'schema_service': 'Design-Build Construction',
    'price_range': '$$$$$',
  },
}

# ── Local business schema (shared) ───────────────────────────────────────────
def local_biz_schema(city_data, service_data):
  return {
    "@context": "https://schema.org",
    "@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
    "name": "Ridgecrest Designs",
    "description": f"Luxury {service_data['name'].lower()} firm serving {city_data['name']}, CA and the East Bay.",
    "url": BASE_URL,
    "telephone": "+19257842798",
    "email": "info@ridgecrestdesigns.com",
    "foundingDate": "2013",
    "founder": {"@type": "Person", "name": "Tyler Ridgecrest"},
    "priceRange": service_data['price_range'],
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "5502 Sunol Blvd Suite 100",
      "addressLocality": "Pleasanton",
      "addressRegion": "CA",
      "postalCode": "94566",
      "addressCountry": "US"
    },
    "geo": {"@type": "GeoCoordinates", "latitude": 37.6624, "longitude": -121.8747},
    "areaServed": {"@type": "City", "name": city_data['name'], "containedInPlace": {"@type": "State", "name": "California"}},
    "sameAs": [
      "https://www.facebook.com/ridgecrestdesigns",
      "https://www.instagram.com/ridgecrestdesigns",
      "https://www.houzz.com/pro/ridgecrestdesigns"
    ]
  }

def service_schema(city_data, service_data, url):
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    "name": f"{service_data['name']} in {city_data['name']}, CA",
    "description": service_data['meta_template'].format(city=city_data['name']),
    "provider": {"@type": "Organization", "name": "Ridgecrest Designs", "url": BASE_URL},
    "areaServed": {
      "@type": "City",
      "name": city_data['name'],
      "containedInPlace": {"@type": "State", "name": "California"}
    },
    "serviceType": service_data['schema_service'],
    "url": url,
    "breadcrumb": {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
        {"@type": "ListItem", "position": 2, "name": "Services", "item": BASE_URL + "/services"},
        {"@type": "ListItem", "position": 3, "name": f"{service_data['name']} in {city_data['name']}", "item": url}
      ]
    }
  }

# ── HTML template ─────────────────────────────────────────────────────────────
def render_page(city_slug, city, service):
  city_name   = city['name']
  svc_name    = service['name']
  filename    = f"{service['slug']}-{city_slug}.html"
  page_slug   = f"/services/{service['slug']}-{city_slug}"
  canonical   = BASE_URL + page_slug
  title       = service['title_template'].format(city=city_name)
  meta_desc   = service['meta_template'].format(city=city_name)
  og_image    = service['og_image']
  h1          = service['h1_template'].format(city=city_name)
  eyebrow     = service['eyebrow']
  tagline     = service['tagline']
  intro       = service['intro_template'].format(city=city_name)
  svc_intro   = service['service_intro'].format(city=city_name)
  included    = service['what_included']
  budget_note = service['budget_note'].format(city=city_name)
  char        = city['character']
  buyer       = city['buyer_profile']
  hoods       = city['neighborhoods']
  proj1       = city['related_project']
  proj2       = city['related_project2']

  # Build included list HTML
  included_html = '\n'.join(f'            <li>{item.format(city=city_name)}</li>' for item in included)

  # Build related project HTML
  proj_html = ''
  if proj1:
    proj_html += f'''
      <div class="service-project">
        <a href="{proj1[1]}" class="service-project__link">
          <div class="service-project__info">
            <p class="section__label">Featured {city_name} Project</p>
            <h3 class="service-project__name">{proj1[0]}</h3>
            <p class="service-project__desc">{proj1[2].capitalize()}.</p>
            <span class="service-project__cta">View Project →</span>
          </div>
        </a>
      </div>'''
  if proj2:
    proj_html += f'''
      <div class="service-project">
        <a href="{proj2[1]}" class="service-project__link">
          <div class="service-project__info">
            <p class="section__label">Also in {city_name}</p>
            <h3 class="service-project__name">{proj2[0]}</h3>
            <p class="service-project__desc">{proj2[2].capitalize()}.</p>
            <span class="service-project__cta">View Project →</span>
          </div>
        </a>
      </div>'''

  proj_section = ''
  if proj_html:
    proj_section = f'''
  <!-- FEATURED PROJECTS -->
  <section class="section section--accent">
    <div class="container">
      <p class="section__label">Our Work in {city_name}</p>
      <h2 class="section__headline">Projects we\'ve completed<br><em>in {city_name}</em></h2>
      <div class="service-projects-grid">
        {proj_html}
      </div>
    </div>
  </section>'''

  # Schema
  lb_schema  = json.dumps(local_biz_schema(city, service), indent=4, ensure_ascii=False)
  svc_schema = json.dumps(service_schema(city, service, canonical), indent=4, ensure_ascii=False)

  return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{meta_desc}" />

  <!-- ── SEO ──────────────────────────────────────────────────── -->
  <link rel="canonical" href="{canonical}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Ridgecrest Designs" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{meta_desc}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="{og_image}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{meta_desc}" />
  <meta name="twitter:image" content="{og_image}" />
  <script type="application/ld+json">
  {lb_schema}
  </script>
  <script type="application/ld+json">
  {svc_schema}
  </script>
  <!-- ─────────────────────────────────────────────────────────── -->

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
      <li><a href="../portfolio.html">Portfolio</a></li>
      <li><a href="../team.html">Team</a></li>
      <li><a href="../contact.html" class="nav__cta">Start a Project</a></li>
    </ul>
  </nav>

  <!-- PAGE HERO -->
  <div class="page-hero page-hero--service">
    <p class="page-hero__eyebrow">{eyebrow} · {city_name}, CA</p>
    <h1 class="page-hero__title">{h1}</h1>
    <p class="page-hero__sub">{tagline}</p>
    <div class="page-hero__actions">
      <a href="{INQUIRY}" class="btn btn--primary btn--lg">Start Your Project Inquiry</a>
      <a href="../portfolio.html" class="btn btn--ghost">View Our Work</a>
    </div>
  </div>

  <!-- INTRO -->
  <section class="section section--accent">
    <div class="container container--narrow">
      <p class="section__label">{svc_name} · {city_name}, CA</p>
      <h2 class="section__headline">Built for {city_name}.<br><em>Built without compromise.</em></h2>
      <div class="service-intro-body">
        <p>{intro}</p>
        <p>{city_name} is {char}. {buyer}.</p>
        <p>{svc_intro}</p>
      </div>
    </div>
  </section>

  <!-- WHAT\'S INCLUDED -->
  <section class="section">
    <div class="container">
      <div class="service-included">
        <div class="service-included__text">
          <p class="section__label">Scope of Work</p>
          <h2 class="section__headline">What\'s included in a<br><em>{svc_name.lower()} with Ridgecrest</em></h2>
          <p>Every project is different — but every Ridgecrest project includes full design-build management, photo-realistic renders before construction begins, and a single point of accountability from first meeting to final walkthrough.</p>
          <p class="service-budget-note">{budget_note}</p>
        </div>
        <div class="service-included__list">
          <ul class="service-checklist">
{included_html}
          </ul>
        </div>
      </div>
    </div>
  </section>
  {proj_section}

  <!-- DIFFERENTIATORS -->
  <section class="section section--dark">
    <div class="container">
      <p class="section__label">Why Ridgecrest Designs</p>
      <h2 class="section__headline">What makes us different<br><em>in {city_name}</em></h2>
      <div class="diff-grid">
        <div class="diff-item">
          <h3 class="diff-item__title">Photo-Realistic Renders</h3>
          <p class="diff-item__body">Before we file a single permit, you\'ll see your finished {svc_name.lower()} in photographic detail. Every material, every fixture, every finish — confirmed before construction begins.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Integrated Design-Build</h3>
          <p class="diff-item__body">One firm manages design, engineering, permitting, and construction. No handoff. No finger-pointing. One contract, one point of accountability, zero coordination gaps.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Permitting Expertise</h3>
          <p class="diff-item__body">We know {city_name}\'s permitting process. We manage every application, response, and inspection — so you never have to wonder where your project stands with the building department.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Premium Teams</h3>
          <p class="diff-item__body">Our subcontractors are selected for quality, not cost. Every trade on a Ridgecrest project is held to the same standard: precise, accountable, and proud of the work they leave behind.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Limited Projects Per Year</h3>
          <p class="diff-item__body">We take on a carefully limited number of projects to ensure every client receives our full attention. If you\'re considering a {svc_name.lower()} in {city_name}, reach out early.</p>
        </div>
        <div class="diff-item">
          <h3 class="diff-item__title">Established Since 2013</h3>
          <p class="diff-item__body">Over a decade of luxury design-build projects across the East Bay. We know what it takes to deliver at this level — and we do it consistently.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- SERVICE AREA -->
  <section class="section section--accent">
    <div class="container container--narrow" style="text-align:center">
      <p class="section__label">Service Area</p>
      <h2 class="section__headline">Serving {city_name}<br><em>and the surrounding East Bay</em></h2>
      <p>Ridgecrest Designs serves {city_name} and the following communities: {hoods}, as well as Danville, Lafayette, Alamo, Orinda, Walnut Creek, Pleasanton, San Ramon, Dublin, Moraga, Sunol, Rossmoor, and Diablo.</p>
      <p style="margin-top:1.5rem">5502 Sunol Blvd Suite 100, Pleasanton CA 94566 · <a href="tel:9257842798">925-784-2798</a></p>
    </div>
  </section>

  <!-- CTA -->
  <section class="cta section section--dark" style="background:var(--charcoal)">
    <div class="container container--narrow cta__inner">
      <h2 class="cta__headline">Ready to start your<br><em>{svc_name.lower()} in {city_name}?</em></h2>
      <p class="cta__sub">Submit a project inquiry and we\'ll follow up within one business day to discuss your vision, timeline, and budget.</p>
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
          <a href="../contact.html">Custom Homes</a>
          <a href="../contact.html">Whole House Remodels</a>
          <a href="../contact.html">Kitchen Remodels</a>
          <a href="../contact.html">Bathroom Remodels</a>
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


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
  count = 0
  for city_slug, city in CITIES.items():
    for svc_slug, service in SERVICES.items():
      html     = render_page(city_slug, city, service)
      filename = f"{service['slug']}-{city_slug}.html"
      path     = os.path.join(OUT_DIR, filename)
      with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
      count += 1
      print(f'  ✓  {filename}')

  print(f'\nGenerated {count} service × location pages → {OUT_DIR}/')
