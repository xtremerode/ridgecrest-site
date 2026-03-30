#!/usr/bin/env python3
"""
SEO patch for Ridgecrest Designs preview site.
Adds to every page: canonical tags, Open Graph tags, JSON-LD schema.
Fixes truncated meta descriptions on project pages.
Adds role/aria-label to CSS background-image divs.
"""
import json, re, os

PREVIEW = '/home/claudeuser/agent/preview'
BASE_URL = 'https://www.ridgecrestdesigns.com'
DEFAULT_IMAGE = 'https://static.wixstatic.com/media/ff5b18_3c0cef18e48849089c5ed48614041900~mv2.png'

# ── Shared LocalBusiness schema (injected on every page) ─────────────────────
LOCAL_BIZ = {
  "@context": "https://schema.org",
  "@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
  "name": "Ridgecrest Designs",
  "description": "Luxury design-build firm specializing in custom homes and high-end remodels across Pleasanton, Danville, Walnut Creek, Lafayette, Orinda, Alamo, San Ramon and the East Bay.",
  "url": BASE_URL,
  "telephone": "+19257842798",
  "email": "info@ridgecrestdesigns.com",
  "foundingDate": "2013",
  "founder": {"@type": "Person", "name": "Tyler Ridgecrest"},
  "priceRange": "$$$$$",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "5502 Sunol Blvd Suite 100",
    "addressLocality": "Pleasanton",
    "addressRegion": "CA",
    "postalCode": "94566",
    "addressCountry": "US"
  },
  "geo": {"@type": "GeoCoordinates", "latitude": 37.6624, "longitude": -121.8747},
  "areaServed": [
    {"@type": "City", "name": "Pleasanton"},
    {"@type": "City", "name": "Danville"},
    {"@type": "City", "name": "Walnut Creek"},
    {"@type": "City", "name": "Lafayette"},
    {"@type": "City", "name": "Orinda"},
    {"@type": "City", "name": "Alamo"},
    {"@type": "City", "name": "San Ramon"},
    {"@type": "City", "name": "Dublin"},
    {"@type": "City", "name": "Moraga"},
    {"@type": "City", "name": "Sunol"}
  ],
  "sameAs": [
    "https://www.facebook.com/ridgecrestdesigns",
    "https://www.instagram.com/ridgecrestdesigns",
    "https://www.houzz.com/pro/ridgecrestdesigns"
  ]
}

# ── Page configurations ───────────────────────────────────────────────────────
PAGES = {
  'index.html': {
    'slug': '/',
    'og_title': 'Ridgecrest Designs — Luxury Design-Build | East Bay, California',
    'og_desc': 'Ridgecrest Designs is a full-service luxury design-build firm serving Pleasanton, Walnut Creek, Danville, Lafayette, and the East Bay. Custom homes and high-end remodels.',
    'og_image': DEFAULT_IMAGE,
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Ridgecrest Designs",
        "url": BASE_URL,
        "logo": BASE_URL + "/assets/logo.png",
        "telephone": "+19257842798",
        "email": "info@ridgecrestdesigns.com",
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "5502 Sunol Blvd Suite 100",
          "addressLocality": "Pleasanton",
          "addressRegion": "CA",
          "postalCode": "94566",
          "addressCountry": "US"
        },
        "sameAs": [
          "https://www.facebook.com/ridgecrestdesigns",
          "https://www.instagram.com/ridgecrestdesigns",
          "https://www.houzz.com/pro/ridgecrestdesigns"
        ]
      },
      {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Ridgecrest Designs",
        "url": BASE_URL,
        "potentialAction": {
          "@type": "SearchAction",
          "target": BASE_URL + "/?s={search_term_string}",
          "query-input": "required name=search_term_string"
        }
      }
    ]
  },
  'about.html': {
    'slug': '/about',
    'og_title': 'About — Ridgecrest Designs | Luxury Design-Build, Pleasanton CA',
    'og_desc': 'Ridgecrest Designs was founded in 2013 in Pleasanton, CA. A full-service luxury design-build firm specializing in custom homes and high-end remodels across the Tri-Valley and East Bay.',
    'og_image': DEFAULT_IMAGE,
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "AboutPage",
        "name": "About Ridgecrest Designs",
        "url": BASE_URL + "/about",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "About", "item": BASE_URL + "/about"}
          ]
        }
      }
    ]
  },
  'process.html': {
    'slug': '/process',
    'og_title': 'Our Process — Ridgecrest Designs | Design-Build, Pleasanton CA',
    'og_desc': "Ridgecrest Designs' five-stage California design-build process: consultation, design, budget, permitting, and construction. No surprises from first render to final walkthrough.",
    'og_image': DEFAULT_IMAGE,
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": "The Ridgecrest Designs Design-Build Process",
        "description": "A five-stage luxury design-build process for custom homes and high-end remodels in the East Bay.",
        "step": [
          {"@type": "HowToStep", "position": 1, "name": "Initial Consultation", "text": "We meet to understand your vision, goals, and project scope."},
          {"@type": "HowToStep", "position": 2, "name": "Design & Visualization", "text": "Our team creates photo-realistic renders so you can see your home before we build it."},
          {"@type": "HowToStep", "position": 3, "name": "Budget & Proposal", "text": "We provide a detailed, transparent proposal with no hidden costs."},
          {"@type": "HowToStep", "position": 4, "name": "Permitting & Construction", "text": "We manage all permitting, engineering, and construction under one roof."},
          {"@type": "HowToStep", "position": 5, "name": "Completion & Handover", "text": "Final walkthrough and handover of your completed luxury home or remodel."}
        ],
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Process", "item": BASE_URL + "/process"}
          ]
        }
      }
    ]
  },
  'portfolio.html': {
    'slug': '/portfolio',
    'og_title': 'Portfolio — Ridgecrest Designs | Luxury Homes & Remodels, East Bay CA',
    'og_desc': "Explore Ridgecrest Designs' portfolio of luxury custom homes and high-end remodels across Pleasanton, Danville, Lafayette, Orinda, and the East Bay.",
    'og_image': DEFAULT_IMAGE,
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Portfolio — Ridgecrest Designs",
        "url": BASE_URL + "/portfolio",
        "description": "Luxury custom homes and high-end remodels across Pleasanton, Danville, Lafayette, Orinda, and the East Bay.",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"}
          ]
        },
        "mainEntity": {
          "@type": "ItemList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Danville Dream Home", "url": BASE_URL + "/danville-dream"},
            {"@type": "ListItem", "position": 2, "name": "Danville Hilltop Hideaway", "url": BASE_URL + "/danville-hilltop"},
            {"@type": "ListItem", "position": 3, "name": "Pleasanton Custom Home", "url": BASE_URL + "/pleasanton-custom"},
            {"@type": "ListItem", "position": 4, "name": "Alamo Luxury Home", "url": BASE_URL + "/alamo-luxury"},
            {"@type": "ListItem", "position": 5, "name": "Lafayette Modern Bistro", "url": BASE_URL + "/lafayette-bistro"},
            {"@type": "ListItem", "position": 6, "name": "Lafayette Laid-Back Luxury", "url": BASE_URL + "/lafayette-luxury"},
            {"@type": "ListItem", "position": 7, "name": "San Ramon Custom Home", "url": BASE_URL + "/san-ramon"},
            {"@type": "ListItem", "position": 8, "name": "Orinda Urban Modern Kitchen", "url": BASE_URL + "/orinda-kitchen"},
            {"@type": "ListItem", "position": 9, "name": "Sunol Homestead", "url": BASE_URL + "/sunol-homestead"}
          ]
        }
      }
    ]
  },
  'contact.html': {
    'slug': '/contact',
    'og_title': 'Contact — Ridgecrest Designs | Start Your Project, Pleasanton CA',
    'og_desc': 'Start a luxury custom home or remodel project with Ridgecrest Designs. Submit a project inquiry or call 925-784-2798. Serving Pleasanton, Danville, Lafayette, Walnut Creek, and the East Bay.',
    'og_image': DEFAULT_IMAGE,
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "ContactPage",
        "name": "Contact Ridgecrest Designs",
        "url": BASE_URL + "/contact",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Contact", "item": BASE_URL + "/contact"}
          ]
        }
      }
    ]
  },
  'danville-dream.html': {
    'slug': '/danville-dream',
    'og_title': 'Danville Dream Home — Ridgecrest Designs | Luxury Home Remodel, Danville CA',
    'og_desc': 'Ridgecrest Designs transformed this Danville dream home with a luxury kitchen remodel, spa-style master bath, and custom wine cellar. Photo-realistic renders guided every detail from concept to completion.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_3c0cef18e48849089c5ed48614041900~mv2.png',
    'fix_meta': 'Ridgecrest Designs transformed this Danville dream home with a luxury kitchen remodel, spa-style master bath, and custom wine cellar. Photo-realistic renders guided every detail from concept to completion.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Danville Dream Home",
        "description": "A luxury home remodel in Danville, CA featuring a kitchen remodel, spa-style master bath, and custom wine cellar by Ridgecrest Designs.",
        "url": BASE_URL + "/danville-dream",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Danville", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "luxury home remodel, Danville CA, kitchen remodel, master bath, design-build",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Danville Dream Home", "item": BASE_URL + "/danville-dream"}
          ]
        }
      }
    ]
  },
  'danville-hilltop.html': {
    'slug': '/danville-hilltop',
    'og_title': 'Danville Hilltop Hideaway — Ridgecrest Designs | Modern Home Remodel, Danville CA',
    'og_desc': 'A bespoke hilltop home remodel in Danville combining mid-century architecture, panoramic views, and warm natural materials. Designed and built by Ridgecrest Designs.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab~mv2.jpg',
    'fix_meta': 'A bespoke hilltop home remodel in Danville combining mid-century architecture, panoramic views, and warm natural materials. Designed and built by Ridgecrest Designs.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Danville Hilltop Hideaway",
        "description": "A modern hilltop home remodel in Danville, CA combining mid-century architecture with high-end materials and panoramic views.",
        "url": BASE_URL + "/danville-hilltop",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Danville", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "modern home remodel, Danville CA, hilltop home, mid-century, design-build",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Danville Hilltop Hideaway", "item": BASE_URL + "/danville-hilltop"}
          ]
        }
      }
    ]
  },
  'pleasanton-custom.html': {
    'slug': '/pleasanton-custom',
    'og_title': 'Pleasanton Custom Home — Ridgecrest Designs | Custom Home Builder, Pleasanton CA',
    'og_desc': 'A 5,000 sq ft modern farmhouse custom home built by Ridgecrest Designs in Pleasanton, CA. Photo-realistic renders guided the vision across 1.4 acres in Happy Valley.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_9820c1603a9c414d8cc8009784d1ca7c~mv2.jpg',
    'fix_meta': 'A 5,000 sq ft modern farmhouse custom home built by Ridgecrest Designs in Pleasanton, CA. Photo-realistic renders guided the vision across 1.4 acres in Happy Valley.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Pleasanton Custom Home",
        "description": "A 5,000 sq ft custom modern farmhouse in Pleasanton, CA designed and built by Ridgecrest Designs on a 1.4-acre plot in Happy Valley.",
        "url": BASE_URL + "/pleasanton-custom",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Pleasanton", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "custom home builder, Pleasanton CA, modern farmhouse, design-build, custom home",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Pleasanton Custom Home", "item": BASE_URL + "/pleasanton-custom"}
          ]
        }
      }
    ]
  },
  'alamo-luxury.html': {
    'slug': '/alamo-luxury',
    'og_title': 'Alamo Luxury Home — Ridgecrest Designs | Luxury Remodel, Alamo CA',
    'og_desc': 'Custom architecture, high-end finishes, and timeless craftsmanship in Alamo, CA. A signature Ridgecrest Designs luxury remodel built through close homeowner collaboration.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_39536b28ce0447b9a87797bb4c70ee51~mv2.jpg',
    'fix_meta': 'Custom architecture, high-end finishes, and timeless craftsmanship in Alamo, CA. A signature Ridgecrest Designs luxury remodel built through close homeowner collaboration.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Alamo Luxury Home",
        "description": "A luxury home remodel in Alamo, CA featuring custom architecture, high-end finishes, and timeless craftsmanship by Ridgecrest Designs.",
        "url": BASE_URL + "/alamo-luxury",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Alamo", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "luxury remodel, Alamo CA, custom architecture, design-build, high-end finishes",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Alamo Luxury Home", "item": BASE_URL + "/alamo-luxury"}
          ]
        }
      }
    ]
  },
  'lafayette-bistro.html': {
    'slug': '/lafayette-bistro',
    'og_title': 'Lafayette Modern Bistro — Ridgecrest Designs | Kitchen Remodel, Lafayette CA',
    'og_desc': 'Ridgecrest Designs transformed a cramped Lafayette kitchen into a bright, modern bistro-style space with custom cabinetry, white oak finishes, and an open floor plan.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_94919d08fc9245fc849ac03c4ea2caaf~mv2.jpg',
    'fix_meta': 'Ridgecrest Designs transformed a cramped Lafayette kitchen into a bright, modern bistro-style space with custom cabinetry, white oak finishes, and an open floor plan.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Lafayette Modern Bistro Kitchen Remodel",
        "description": "A modern bistro-style kitchen remodel in Lafayette, CA featuring custom cabinetry, white oak finishes, and an open floor plan by Ridgecrest Designs.",
        "url": BASE_URL + "/lafayette-bistro",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Lafayette", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "kitchen remodel, Lafayette CA, modern bistro, custom cabinetry, white oak, design-build",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Lafayette Modern Bistro", "item": BASE_URL + "/lafayette-bistro"}
          ]
        }
      }
    ]
  },
  'lafayette-luxury.html': {
    'slug': '/lafayette-luxury',
    'og_title': 'Lafayette Laid-Back Luxury — Ridgecrest Designs | Home Remodel, Lafayette CA',
    'og_desc': 'Ridgecrest Designs reimagined this Lafayette home with a relaxed luxury aesthetic — natural materials, custom craftsmanship, and effortless indoor-outdoor flow.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_6eed718eb2ab4ca0887717d1a39285ea~mv2.png',
    'fix_meta': 'Ridgecrest Designs reimagined this Lafayette home with a relaxed luxury aesthetic — natural materials, custom craftsmanship, and effortless indoor-outdoor flow.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Lafayette Laid-Back Luxury",
        "description": "A luxury home remodel in Lafayette, CA with a relaxed aesthetic, natural materials, custom craftsmanship, and indoor-outdoor flow by Ridgecrest Designs.",
        "url": BASE_URL + "/lafayette-luxury",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Lafayette", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "home remodel, Lafayette CA, luxury remodel, natural materials, design-build",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Lafayette Laid-Back Luxury", "item": BASE_URL + "/lafayette-luxury"}
          ]
        }
      }
    ]
  },
  'san-ramon.html': {
    'slug': '/san-ramon',
    'og_title': 'San Ramon Custom Home — Ridgecrest Designs | Custom Home Remodel, San Ramon CA',
    'og_desc': 'Ridgecrest Designs elevated this San Ramon residence with premium materials, a modern-luxury aesthetic, and an integrated design-build process from the inside out.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_eed718eb2ab4ca0887717d1a39285ea~mv2.png',
    'fix_meta': 'Ridgecrest Designs elevated this San Ramon residence with premium materials, a modern-luxury aesthetic, and an integrated design-build process from the inside out.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "San Ramon Custom Home",
        "description": "A custom home remodel in San Ramon, CA with premium materials and a modern-luxury aesthetic by Ridgecrest Designs.",
        "url": BASE_URL + "/san-ramon",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "San Ramon", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "custom home remodel, San Ramon CA, modern luxury, design-build",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "San Ramon Custom Home", "item": BASE_URL + "/san-ramon"}
          ]
        }
      }
    ]
  },
  'orinda-kitchen.html': {
    'slug': '/orinda-kitchen',
    'og_title': 'Orinda Urban Modern Kitchen — Ridgecrest Designs | Kitchen Remodel, Orinda CA',
    'og_desc': 'Ridgecrest Designs transformed an outdated Orinda kitchen into an art-gallery-inspired urban space with four skylights, custom cabinetry, and white oak accents.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_d741bf6a821b40e8b4730181bcf0fc48~mv2.jpg',
    'fix_meta': 'Ridgecrest Designs transformed an outdated Orinda kitchen into an art-gallery-inspired urban space with four skylights, custom cabinetry, and white oak accents.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Orinda Urban Modern Kitchen",
        "description": "An art-gallery-inspired kitchen remodel in Orinda, CA featuring four skylights, custom cabinetry, and white oak accents by Ridgecrest Designs.",
        "url": BASE_URL + "/orinda-kitchen",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Orinda", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "kitchen remodel, Orinda CA, modern kitchen, skylights, custom cabinetry, design-build",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Orinda Urban Modern Kitchen", "item": BASE_URL + "/orinda-kitchen"}
          ]
        }
      }
    ]
  },
  'sunol-homestead.html': {
    'slug': '/sunol-homestead',
    'og_title': 'Sunol Homestead — Ridgecrest Designs | Custom Home Remodel, Sunol CA',
    'og_desc': 'A custom homestead remodel in Sunol, CA by Ridgecrest Designs. Natural materials, precision craftsmanship, and a seamless design-build process from concept to completion.',
    'og_image': 'https://static.wixstatic.com/media/ff5b18_296b1e9ff5d14e128006c21217e3f3e9~mv2.jpg',
    'fix_meta': 'A custom homestead remodel in Sunol, CA by Ridgecrest Designs. Natural materials, precision craftsmanship, and a seamless design-build process from concept to completion.',
    'extra_schema': [
      {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Sunol Homestead",
        "description": "A custom homestead remodel in Sunol, CA featuring natural materials and precision craftsmanship by Ridgecrest Designs.",
        "url": BASE_URL + "/sunol-homestead",
        "creator": {"@type": "Organization", "name": "Ridgecrest Designs"},
        "locationCreated": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Sunol", "addressRegion": "CA", "addressCountry": "US"}},
        "keywords": "custom home remodel, Sunol CA, natural materials, design-build, homestead",
        "breadcrumb": {
          "@type": "BreadcrumbList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": "Portfolio", "item": BASE_URL + "/portfolio"},
            {"@type": "ListItem", "position": 3, "name": "Sunol Homestead", "item": BASE_URL + "/sunol-homestead"}
          ]
        }
      }
    ]
  },
}

# ── Aria-label map for portfolio CSS background images ────────────────────────
# Maps CSS class suffix to descriptive label
PORTFOLIO_ITEM_LABELS = {
  'portfolio-item__bg--1': 'Danville Dream Home — luxury home remodel by Ridgecrest Designs',
  'portfolio-item__bg--2': 'Danville Hilltop Hideaway — modern home remodel by Ridgecrest Designs',
  'portfolio-item__bg--3': 'Pleasanton Custom Home — custom home by Ridgecrest Designs',
  'portfolio-item__bg--4': 'Alamo Luxury Home — luxury remodel by Ridgecrest Designs',
  'portfolio-item__bg--5': 'Lafayette Modern Bistro — kitchen remodel by Ridgecrest Designs',
  'portfolio-item__bg--6': 'Lafayette Laid-Back Luxury — home remodel by Ridgecrest Designs',
  'portfolio-item__bg--7': 'San Ramon Custom Home — custom home remodel by Ridgecrest Designs',
  'portfolio-item__bg--8': 'Orinda Urban Modern Kitchen — kitchen remodel by Ridgecrest Designs',
  'portfolio-item__bg--9': 'Sunol Homestead — custom home remodel by Ridgecrest Designs',
}

PORTFOLIO_CARD_LABELS = {
  'portfolio-card__img--1': 'Danville Dream Home — luxury home remodel by Ridgecrest Designs',
  'portfolio-card__img--2': 'Pleasanton Custom Home — custom home by Ridgecrest Designs',
  'portfolio-card__img--3': 'Lafayette Modern Bistro — kitchen remodel by Ridgecrest Designs',
  'portfolio-card__img--4': 'Alamo Luxury Home — luxury remodel by Ridgecrest Designs',
}

PROJECT_HERO_LABELS = {
  'danville-dream.html':     'Danville Dream Home — luxury kitchen remodel and master bath by Ridgecrest Designs, Danville CA',
  'danville-hilltop.html':   'Danville Hilltop Hideaway — modern hilltop home remodel by Ridgecrest Designs, Danville CA',
  'pleasanton-custom.html':  'Pleasanton Custom Home — 5,000 sq ft modern farmhouse custom build by Ridgecrest Designs, Pleasanton CA',
  'alamo-luxury.html':       'Alamo Luxury Home — high-end home remodel by Ridgecrest Designs, Alamo CA',
  'lafayette-bistro.html':   'Lafayette Modern Bistro — kitchen remodel with white oak finishes by Ridgecrest Designs, Lafayette CA',
  'lafayette-luxury.html':   'Lafayette Laid-Back Luxury — relaxed luxury home remodel by Ridgecrest Designs, Lafayette CA',
  'san-ramon.html':          'San Ramon Custom Home — modern luxury home remodel by Ridgecrest Designs, San Ramon CA',
  'orinda-kitchen.html':     'Orinda Urban Modern Kitchen — art-gallery-inspired kitchen remodel by Ridgecrest Designs, Orinda CA',
  'sunol-homestead.html':    'Sunol Homestead — custom homestead remodel by Ridgecrest Designs, Sunol CA',
}

def build_seo_block(filename, config):
  """Build the SEO <head> injection block for a page."""
  canonical = BASE_URL + config['slug']
  lines = [
    '',
    '  <!-- ── SEO ──────────────────────────────────────────────────── -->',
    f'  <link rel="canonical" href="{canonical}" />',
    f'  <meta property="og:type" content="website" />',
    f'  <meta property="og:site_name" content="Ridgecrest Designs" />',
    f'  <meta property="og:title" content="{config["og_title"]}" />',
    f'  <meta property="og:description" content="{config["og_desc"]}" />',
    f'  <meta property="og:url" content="{canonical}" />',
    f'  <meta property="og:image" content="{config["og_image"]}" />',
    f'  <meta name="twitter:card" content="summary_large_image" />',
    f'  <meta name="twitter:title" content="{config["og_title"]}" />',
    f'  <meta name="twitter:description" content="{config["og_desc"]}" />',
    f'  <meta name="twitter:image" content="{config["og_image"]}" />',
  ]

  # LocalBusiness (every page)
  lines.append(f'  <script type="application/ld+json">')
  lines.append(f'  {json.dumps(LOCAL_BIZ, indent=2, ensure_ascii=False)}')
  lines.append(f'  </script>')

  # Page-specific schema
  for schema in config.get('extra_schema', []):
    lines.append(f'  <script type="application/ld+json">')
    lines.append(f'  {json.dumps(schema, indent=2, ensure_ascii=False)}')
    lines.append(f'  </script>')

  lines.append('  <!-- ─────────────────────────────────────────────────────── -->')
  return '\n'.join(lines)


def add_aria_to_portfolio_items(html):
  """Add role=img and aria-label to portfolio-item__bg and portfolio-card__img divs."""
  for cls, label in {**PORTFOLIO_ITEM_LABELS, **PORTFOLIO_CARD_LABELS}.items():
    # Match: <div class="... portfolio-item__bg--N ..."> (with or without other classes)
    pattern = rf'(<div\s+class="([^"]*{re.escape(cls)}[^"]*)")(>)'
    replacement = rf'\1 role="img" aria-label="{label}"\3'
    html = re.sub(pattern, replacement, html)
  return html


def add_aria_to_project_hero(html, filename):
  """Add role=img and aria-label to project-hero__img div."""
  label = PROJECT_HERO_LABELS.get(filename, 'Luxury project by Ridgecrest Designs')
  pattern = r'(<div\s+class="project-hero__img")'
  replacement = rf'\1 role="img" aria-label="{label}"'
  html = re.sub(pattern, replacement, html)
  return html


def add_aria_to_gallery_items(html, filename):
  """Add role=img and aria-label to gallery-item__img divs."""
  project_name = PROJECT_HERO_LABELS.get(filename, 'Ridgecrest Designs project').split(' — ')[0]
  counter = [0]
  def replacer(m):
    counter[0] += 1
    label = f'{project_name} — gallery photo {counter[0]}'
    return f'{m.group(1)} role="img" aria-label="{label}"'
  pattern = r'(<div\s+class="gallery-item__img")'
  html = re.sub(pattern, replacer, html)
  return html


def fix_meta_description(html, new_desc):
  """Replace truncated meta description with full text."""
  pattern = r'<meta\s+name="description"\s+content="[^"]*"\s*/>'
  replacement = f'<meta name="description" content="{new_desc}" />'
  return re.sub(pattern, replacement, html)


def process_file(filename, config):
  path = os.path.join(PREVIEW, filename)
  with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

  # 1. Fix truncated meta description if needed
  if 'fix_meta' in config:
    html = fix_meta_description(html, config['fix_meta'])

  # 2. Inject SEO block before </head>
  seo_block = build_seo_block(filename, config)
  if '<link rel="canonical"' not in html:
    html = html.replace('</head>', seo_block + '\n</head>')

  # 3. Add aria-labels to portfolio background image divs
  html = add_aria_to_portfolio_items(html)

  # 4. Add aria-label to project hero image (project pages only)
  if filename in PROJECT_HERO_LABELS:
    html = add_aria_to_project_hero(html, filename)
    html = add_aria_to_gallery_items(html, filename)

  with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

  print(f'  ✓  {filename}')


if __name__ == '__main__':
  print('Applying SEO patches to all pages...')
  for filename, config in PAGES.items():
    process_file(filename, config)
  print(f'\nDone. {len(PAGES)} files updated.')
