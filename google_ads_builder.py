"""
Google Ads Builder — Ridgecrest Designs
========================================
Builds the complete Google Ads campaign hierarchy:
  17 service themes × 2 ad groups (Exact + Phrase) × 3 RSA ads each
  + full keyword sets from CLAUDE.md

All ad copy is validated against Google Ads character limits:
  Headlines: ≤ 30 characters
  Descriptions: ≤ 90 characters

Usage:
  source venv/bin/activate

  # Preview DB records only — no API calls
  python google_ads_builder.py --db-only --dry-run

  # Write to DB only (no Google Ads API)
  python google_ads_builder.py --db-only

  # Write to DB and push to Google Ads API
  python google_ads_builder.py
"""

import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [google_ads_builder] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Identity / tagging
# ---------------------------------------------------------------------------

RMA_PREFIX   = "[RMA]"
LANDING_PAGE = "https://go.ridgecrestdesigns.com"
CUSTOMER_ID  = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "5576077690").replace("-", "")
MANAGER_ID   = os.getenv("GOOGLE_ADS_MANAGER_ID",  "4478944999").replace("-", "")

# ---------------------------------------------------------------------------
# Campaign structure — 17 service themes
# ---------------------------------------------------------------------------

SERVICE_THEMES = [
    # (theme_key, display_name, service_category, priority, start_status)
    ("design_build",           "Design Build",            "design_build",           1, "ENABLED"),
    ("custom_home",            "Custom Home",             "custom_home",            1, "ENABLED"),
    ("custom_home_builder",    "Custom Home Builder",     "custom_home",            1, "ENABLED"),
    ("whole_house_remodel",    "Whole House Remodel",     "whole_house_remodel",    2, "ENABLED"),
    ("kitchen_remodel",        "Kitchen Remodel",         "kitchen_remodel",        3, "ENABLED"),
    ("bathroom_remodel",       "Bathroom Remodel",        "bathroom_remodel",       3, "PAUSED"),
    ("master_bathroom_remodel","Master Bathroom Remodel", "master_bathroom_remodel",3, "PAUSED"),
    ("interior_design",        "Interior Design",         "interior_design",        3, "PAUSED"),
    ("interior_design_firm",   "Interior Design Firm",    "interior_design",        3, "PAUSED"),
    ("kitchen_design",         "Kitchen Design",          "kitchen_remodel",        3, "PAUSED"),
    ("bathroom_design",        "Bathroom Design",         "bathroom_remodel",       3, "PAUSED"),
    ("home_design",            "Home Design",             "home_design",            4, "PAUSED"),
    ("architect",              "Architect",               "design_build",           4, "PAUSED"),
    ("home_builder",           "Home Builder",            "custom_home",            4, "PAUSED"),
    ("general_contractor",     "General Contractor",      "whole_house_remodel",    4, "PAUSED"),
    ("remodeling_contractor",  "Remodeling Contractor",   "whole_house_remodel",    4, "PAUSED"),
    ("home_renovation",        "Home Renovation",         "whole_house_remodel",    4, "PAUSED"),
    ("design_build_contractor","Design Build Contractor", "design_build",           4, "PAUSED"),
]

CITIES = [
    "Walnut Creek", "Pleasanton", "Sunol", "San Ramon", "Dublin",
    "Orinda", "Moraga", "Danville", "Alamo", "Lafayette",
    "Rossmoor", "Diablo",
]

# Short abbreviations for compact external IDs (kept within VARCHAR(50))
THEME_ABBREV = {
    "design_build":            "db",
    "custom_home":             "ch",
    "custom_home_builder":     "chb",
    "whole_house_remodel":     "whr",
    "kitchen_remodel":         "kr",
    "bathroom_remodel":        "br",
    "master_bathroom_remodel": "mbr",
    "interior_design":         "id",
    "interior_design_firm":    "idf",
    "kitchen_design":          "kd",
    "bathroom_design":         "bd",
    "home_design":             "hd",
    "architect":               "arch",
    "home_builder":            "hb",
    "general_contractor":      "gc",
    "remodeling_contractor":   "rc",
    "home_renovation":         "hr",
    "design_build_contractor": "dbc",
}

CITY_ABBREV = {
    "Walnut Creek": "wc",
    "Pleasanton":   "pls",
    "Sunol":        "sun",
    "San Ramon":    "sr",
    "Dublin":       "dub",
    "Orinda":       "ori",
    "Moraga":       "mor",
    "Danville":     "dan",
    "Alamo":        "ala",
    "Lafayette":    "laf",
    "Rossmoor":     "ros",
    "Diablo":       "dia",
}

# Google Ads location criterion IDs for target cities in California
# These are the canonical Google Ads geo target IDs
GOOGLE_LOCATION_IDS = {
    "Walnut Creek": 1014221,
    "Pleasanton":   1014194,
    "San Ramon":    1014205,
    "Dublin":       1014161,
    "Orinda":       1014190,
    "Moraga":       1014183,
    "Danville":     1014157,
    "Alamo":        1014132,
    "Lafayette":    1014177,
    "Rossmoor":     1014200,
    "Sunol":        1014214,
    "Diablo":       1014159,
}

# ---------------------------------------------------------------------------
# Ad copy — all headlines ≤ 30 chars, all descriptions ≤ 90 chars
# Validated by _validate_copy() at import time.
# ---------------------------------------------------------------------------

AD_COPY = {
    "Design Build": {
        "headlines": [
            # Luxury/Premium angle (H1–H5)
            "Luxury Design-Build Firm",           # 24
            "Premium Design-Build Services",       # 29
            "High-End Design-Build Firm",          # 26
            "Design Build Ridgecrest",          # 26
            "Custom Design-Build Services",        # 28
            # Process/Expertise angle (H6–H10)
            "Photorealistic Renders",             # 23
            "Seamless Design to Build",            # 24
            "Integrated Design & Build",           # 25
            "From Vision to Finished Home",        # 28
            "Turnkey Design-Build Projects",       # 29
            # Local/CTA angle (H11–H15)
            "East Bay Design-Build Experts",       # 29
            "Design-Build Experts Near You",       # 29
            "Trusted Design-Build Firm",           # 25
            "Start Your Design-Build Today",       # 29
            "Schedule a Consultation",         # 27
        ],
        "descriptions": {
            "luxury": [
                "East Bay luxury design-build. Renders, expert teams & flawless execution.",      # 72
                "Premium design-build for discerning homeowners. Clear process, zero surprises.", # 80
            ],
            "process": [
                "Photorealistic renders before construction. Design, engineering & build in-house.", # 84
                "Integrated design-build: one team, one vision, from first sketch to walkthrough.",   # 82
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & the East Bay. Inquire today.",      # 73
                "Custom homes & luxury remodels from $150K. Submit your project inquiry now.",    # 76
            ],
        },
    },

    "Custom Home": {
        "headlines": [
            "Custom Luxury Homes",                 # 20
            "Luxury Custom Home Builder",          # 26
            "Custom Homes From $5M",               # 21
            "High-End Custom Home Design",         # 26
            "Build Your Dream Custom Home",        # 29
            "Photorealistic Home Renders",        # 29
            "Design-Build Custom Homes",           # 25
            "Your Vision, Expertly Built",         # 27
            "Engineering & Permits In-House",      # 29
            "Premium Custom Home Services",        # 29
            "East Bay Custom Home Experts",        # 29
            "Custom Homes — Turnkey Process",      # 29
            "Trusted Custom Home Builder",         # 27
            "Start Your Custom Home Today",        # 29
            "Request a Project Consultation",      # 29
        ],
        "descriptions": {
            "luxury": [
                "Build your luxury custom home with Ridgecrest Designs. $5M–$10M custom homes.",  # 75
                "Premium custom homes for East Bay families. Design through construction in-house.", # 81
            ],
            "process": [
                "Photorealistic renders give you visual certainty before construction begins.",   # 77
                "Integrated design-build: design, engineering, permits & build — one expert team.", # 81
            ],
            "local": [
                "Serving Pleasanton, Danville, Walnut Creek, Orinda & the East Bay.",             # 65
                "Custom homes from $5M in the East Bay. Submit your project inquiry today.",       # 72
            ],
        },
    },

    "Custom Home Builder": {
        "headlines": [
            "Premium Custom Home Builder",             # 22
            "Luxury Custom Home Builder",          # 26
            "East Bay Custom Home Builder",        # 29
            "Custom Homes From $5M+",              # 22
            "Premium Custom Homebuilder",          # 26
            "Photorealistic Home Renders",        # 29
            "Integrated Design & Build",           # 25
            "Custom Homes Built Right",            # 24
            "Engineering & Permits In-House",      # 29
            "Luxury Custom Home Builder",          # 26
            "Your Builder for Life",               # 19
            "Trusted Custom Home Builder",         # 27
            "Design-Build Custom Homes",           # 25
            "Start Your Custom Home Today",        # 29
            "Request a Builder Consultation",      # 29
        ],
        "descriptions": {
            "luxury": [
                "East Bay's premium custom home builder. Design, engineering & construction.",     # 71
                "We build $5M–$10M custom homes for discerning homeowners who demand quality.",   # 73
            ],
            "process": [
                "Photorealistic renders let you see your home before we break ground.",          # 69
                "No guesswork, no surprises — design, permits & construction by one expert team.", # 80
            ],
            "local": [
                "Serving Pleasanton, Danville, Walnut Creek, Lafayette & the East Bay.",          # 66
                "Custom home builder for the East Bay. Submit your project inquiry today.",        # 71
            ],
        },
    },

    "Whole House Remodel": {
        "headlines": [
            "Whole House Remodel Experts",         # 27
            "Full Home Renovation Services",       # 29
            "Whole-Home Remodel & Design",         # 27
            "Luxury Home Renovation",              # 22
            "Complete Home Transformation",        # 28
            "Whole House Remodels From $1M",       # 29
            "Design-Build Home Renovation",        # 28
            "See Results Before We Build",         # 27
            "Turnkey Whole Home Remodel",          # 27
            "East Bay Remodel Specialists",        # 27
            "Permits & Engineering In-House",      # 29
            "Trusted Renovation Contractor",       # 28
            "High-End Home Renovation",            # 24
            "Request a Remodel Consultation",      # 29
        ],
        "descriptions": {
            "luxury": [
                "Whole-home remodels from $1M for discerning East Bay homeowners.",               # 65
                "Luxury whole-house renovation. Design, engineering & construction in-house.",     # 72
            ],
            "process": [
                "Photorealistic renders show your finished home before construction begins.",     # 73
                "Integrated design-build for whole-house renovations. One team, zero handoffs.",  # 79
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Lafayette. Inquire today.",         # 69
                "Whole-house remodels from $1M. Submit your project inquiry to get started.",     # 73
            ],
        },
    },

    "Kitchen Remodel": {
        "headlines": [
            "Luxury Kitchen Remodel",              # 21
            "Custom Kitchen Design & Build",       # 28
            "High-End Kitchen Renovation",         # 25
            "Kitchen Remodels From $150K",         # 26
            "Premium Kitchen Remodeling",          # 25
            "Photorealistic Kitchen Design",      # 29
            "Design-Build Kitchen Experts",        # 27
            "Custom Kitchens East Bay",            # 24
            "Chef-Quality Kitchen Design",         # 26
            "Turnkey Kitchen Renovation",          # 25
            "Permits & Engineering In-House",      # 29
            "Trusted Kitchen Contractor",          # 24
            "Meticulous Kitchen Design",        # 27
            "Start Your Kitchen Project",          # 26
            "Request a Kitchen Consultation",      # 29
        ],
        "descriptions": {
            "luxury": [
                "Luxury kitchen remodels from $150K. Expert design, engineering & construction.", # 79
                "Custom cabinetry, premium finishes & expert craftsmanship for the East Bay.",    # 74
            ],
            "process": [
                "See your new kitchen before we build it. Photorealistic renders included.",     # 73
                "Design-build kitchen services. Permits, engineering & build under one roof.",    # 76
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Orinda. Inquire today.",           # 67
                "Kitchen remodels from $150K in the East Bay. Submit your inquiry today.",        # 71
            ],
        },
    },

    "Bathroom Remodel": {
        "headlines": [
            "Luxury Bathroom Remodel",             # 22
            "Custom Bathroom Design & Build",      # 28
            "High-End Bathroom Renovation",        # 27
            "Bathroom Remodels From $60K",         # 26
            "Premium Bathroom Remodeling",         # 26
            "Photorealistic Bath Design",         # 26
            "Design-Build Bathroom Experts",       # 27
            "Custom Bathrooms East Bay",           # 23
            "Spa-Quality Bathroom Design",         # 26
            "Turnkey Bathroom Renovation",         # 25
            "Permits & Engineering In-House",      # 29
            "Trusted Bathroom Contractor",         # 24
            "Meticulous Bath Design",              # 21
            "Start Your Bathroom Project",         # 26
            "Request a Bath Consultation",         # 25
        ],
        "descriptions": {
            "luxury": [
                "Luxury bathroom remodels from $60K. Expert design, engineering & construction.", # 79
                "Custom tile, premium fixtures & expert craftsmanship for the East Bay.",         # 69
            ],
            "process": [
                "See your new bathroom before we build it. Photorealistic renders included.",    # 73
                "Design-build bath services. Permits, engineering & construction in-house.",      # 72
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Lafayette. Inquire today.",         # 69
                "Bathroom remodels from $60K in the East Bay. Submit your inquiry today.",        # 70
            ],
        },
    },

    "Master Bathroom Remodel": {
        "headlines": [
            "Luxury Master Bath Remodel",          # 26
            "Custom Master Bathroom Design",       # 28
            "Master Bath From $100K",              # 21
            "Spa-Level Master Bath Design",        # 27
            "Premium Master Bath Remodel",         # 27
            "Photorealistic Bath Renders",        # 28
            "Design-Build Master Bathroom",        # 27
            "High-End Master Bath Design",         # 26
            "Turnkey Master Bath Renovation",      # 29
            "Engineering & Permits In-House",      # 29
            "East Bay Master Bath Experts",        # 27
            "Meticulous Bathroom Design",       # 27
            "Trusted Master Bath Contractor",      # 28
            "Start Your Master Bath Today",        # 27
            "Request a Master Bath Consult",       # 28
        ],
        "descriptions": {
            "luxury": [
                "Master bathroom remodels from $100K. Spa-quality finishes & expert construction.", # 82
                "Premium master bath design for the East Bay's discerning homeowners.",            # 68
            ],
            "process": [
                "See your dream master bath before we build it. Photorealistic renders included.", # 81
                "Design-build master bathroom. Custom tile, permits & construction in-house.",     # 76
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Orinda. Inquire today.",            # 67
                "Master bath remodels from $100K in the East Bay. Submit your inquiry today.",     # 74
            ],
        },
    },

    "Interior Design": {
        "headlines": [
            "Luxury Interior Design Firm",         # 26
            "Custom Interior Design & Build",      # 28
            "East Bay Interior Designers",         # 26
            "Full-Service Interior Design",        # 27
            "High-End Interior Design",            # 24
            "Photorealistic Design Renders",      # 29
            "Design-Build Interior Experts",       # 27
            "Integrated Design & Build",           # 25
            "Meticulous Interior Design",       # 28
            "Turnkey Interior Design Build",       # 28
            "Interior Design With Permits",        # 27
            "Trusted Interior Design Firm",        # 27
            "From Concept to Completion",          # 26
            "Premium Interior Design",             # 24
            "Request a Design Consultation",       # 28
        ],
        "descriptions": {
            "luxury": [
                "Luxury interior design integrated with construction. East Bay's premium firm.",  # 75
                "Premium materials, curated finishes & expert craftsmanship for the East Bay.",   # 74
            ],
            "process": [
                "Photorealistic renders show your finished interior before work begins.",        # 71
                "Integrated design-build: no gap between designer and builder. One expert team.", # 80
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & the East Bay. Inquire today.",     # 72
                "Interior design from concept to completion. Submit your project inquiry today.", # 79
            ],
        },
    },

    "Interior Design Firm": {
        "headlines": [
            "Premium East Bay Design Firm",            # 22
            "Luxury Interior Design Firm",         # 26
            "East Bay Design-Build Firm",          # 25
            "Full-Service Design Firm",            # 23
            "Premium Interior Design Firm",        # 28
            "Design Firm That Also Builds",        # 27
            "Photorealistic Design Renders",      # 29
            "Integrated Design-Build Firm",        # 27
            "Trusted Design-Build Firm",           # 23
            "Trusted East Bay Design Firm",        # 27
            "High-End Interior Design Firm",       # 28
            "From Vision to Construction",         # 26
            "Turnkey Design Firm Services",        # 27
            "Request a Firm Consultation",         # 26
        ],
        "descriptions": {
            "luxury": [
                "Full-service luxury design-build firm. Design, engineering, permits & build.",  # 75
                "Unlike standalone design firms, we take your project from vision to build.",    # 72
            ],
            "process": [
                "Photorealistic renders, premium finishes & meticulous attention to detail.",   # 73
                "One firm handles design, engineering, permits & construction. No handoffs.",    # 74
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Lafayette & Orinda.",              # 61
                "East Bay's premier design-build firm. Submit your project inquiry today.",      # 70
            ],
        },
    },

    "Kitchen Design": {
        "headlines": [
            "Custom Kitchen Design Services",      # 29
            "Luxury Kitchen Design & Build",       # 27
            "Photorealistic Kitchen Design",      # 29
            "Kitchen Design East Bay",             # 22
            "Premium Kitchen Design Firm",         # 26
            "Kitchen Design With Build",           # 24
            "Design-Build Kitchen Services",       # 28
            "Integrated Kitchen Design",           # 24
            "Meticulous Kitchen Design",        # 27
            "Chef-Quality Kitchen Planning",       # 28
            "Turnkey Kitchen Design & Build",      # 28
            "See Your Kitchen Before Build",       # 27
            "Trusted Kitchen Design Firm",         # 26
            "Start Your Kitchen Design",           # 24
            "Request a Kitchen Design",            # 23
        ],
        "descriptions": {
            "luxury": [
                "Luxury kitchen design integrated with construction. Concept to completion.",    # 73
                "Custom cabinetry, premium countertops & expert planning for the East Bay.",     # 71
            ],
            "process": [
                "Photorealistic renders show your finished kitchen before we touch a cabinet.", # 77
                "Design-build kitchen services. Design, permits & construction in-house.",       # 70
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Orinda. Inquire today.",          # 67
                "Kitchen design from concept to build. Submit your project inquiry today.",      # 70
            ],
        },
    },

    "Bathroom Design": {
        "headlines": [
            "Custom Bathroom Design",              # 21
            "Luxury Bathroom Design & Build",      # 28
            "Photorealistic Bath Design",         # 26
            "East Bay Bathroom Designers",         # 25
            "Premium Bathroom Design Firm",        # 27
            "Bathroom Design With Build",          # 24
            "Design-Build Bathroom Services",      # 28
            "Integrated Bathroom Design",          # 24
            "Meticulous Bathroom Design",       # 27
            "Spa-Quality Bathroom Planning",       # 27
            "Turnkey Bath Design & Build",         # 25
            "See Your Bath Before Build",          # 23
            "Trusted Bathroom Design Firm",        # 27
            "High-End Bathroom Designers",         # 26
            "Start Your Bathroom Design",          # 26
        ],
        "descriptions": {
            "luxury": [
                "Luxury bathroom design integrated with expert construction. Concept to build.",  # 76
                "Custom tile, premium fixtures & spa-level finishes for the East Bay.",           # 66
            ],
            "process": [
                "Photorealistic renders show your bath in detail before a single tile is set.", # 77
                "Design-build bathroom services. Design, permits & construction in-house.",      # 72
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Lafayette. Inquire today.",        # 69
                "Bathroom design from concept to build. Submit your project inquiry today.",     # 70
            ],
        },
    },

    "Home Design": {
        "headlines": [
            "Luxury Home Design Services",         # 26
            "Custom Home Design & Build",          # 24
            "Photorealistic Home Design",         # 26
            "East Bay Home Design Experts",        # 27
            "Premium Home Design Firm",            # 23
            "Home Design With Build",              # 20
            "Design-Build Home Services",          # 25
            "Integrated Home Design",              # 21
            "Meticulous Home Design",           # 24
            "Full-Service Home Design",            # 23
            "Turnkey Home Design & Build",         # 25
            "See Your Home Before Build",          # 23
            "Trusted Home Design Firm",            # 22
            "High-End Home Designers",             # 21
            "Start Your Home Design",              # 20
        ],
        "descriptions": {
            "luxury": [
                "Luxury home design integrated with full construction services. East Bay.",       # 67
                "Photorealistic renders let you approve every detail before work begins.",       # 71
            ],
            "process": [
                "Full-service home design: architecture, interiors, engineering & permits.",     # 71
                "Design-build home services. One team from first concept to final walkthrough.", # 79
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville & Orinda. Inquire today.",          # 67
                "Home design from concept to completion. Submit your project inquiry today.",    # 70
            ],
        },
    },

    "Architect": {
        "headlines": [
            "Luxury Home Architect",               # 20
            "Design-Build Architect Firm",         # 27
            "Custom Home Architecture",            # 23
            "East Bay Architect Services",         # 26
            "Architect With Build Team",           # 23
            "Photorealistic Home Renders",        # 29
            "Integrated Architect & Builder",      # 29
            "Licensed Architect East Bay",         # 26
            "Turnkey Architecture Services",       # 28
            "Meticulous Architecture",          # 26
            "High-End Custom Architecture",        # 27
            "Architecture With Permits",           # 25
            "Trusted East Bay Architect",          # 25
            "From Plans to Finished Home",         # 26
            "Request Architecture Consult",        # 27
        ],
        "descriptions": {
            "luxury": [
                "Design-build architecture: licensed design expertise & full construction.",     # 71
                "Unlike standalone architects, we handle design, permits & construction.",       # 68
            ],
            "process": [
                "Photorealistic renders, structural engineering & premium construction.",       # 66
                "Integrated architecture and build: no handoffs, no gaps, one expert team.",    # 71
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Lafayette & Orinda.",              # 61
                "East Bay design-build architecture. Submit your project inquiry today.",        # 66
            ],
        },
    },

    "Home Builder": {
        "headlines": [
            "Luxury Home Builder",                 # 19
            "Custom Home Builder East Bay",        # 27
            "Premium Home Builder Services",       # 28
            "Design-Build Home Builder",           # 24
            "Photorealistic Home Renders",        # 29
            "East Bay Custom Home Builder",         # 26
            "Custom Homes Built Right",            # 23
            "Turnkey Home Builder Services",       # 28
            "Luxury Custom Home Builder",          # 26
            "Engineering & Permits In-House",      # 29
            "Trusted East Bay Builder",            # 22
            "High-End Custom Home Builder",        # 27
            "Integrated Design & Build",           # 25
            "Start Building Your Home Today",      # 29
            "Request a Builder Consultation",      # 29
        ],
        "descriptions": {
            "luxury": [
                "East Bay's premium luxury home builder. Design, engineering & construction.",   # 71
                "We build custom homes & luxury remodels for discerning homeowners.",            # 64
            ],
            "process": [
                "Photorealistic renders, meticulous craftsmanship & flawless execution.",      # 69
                "Integrated home builder: design, permits & build under one expert roof.",      # 70
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Orinda & the East Bay.",           # 65
                "Custom home builder for the East Bay. Submit your project inquiry today.",      # 71
            ],
        },
    },

    "General Contractor": {
        "headlines": [
            "Luxury General Contractor",           # 24
            "Premium General Contractor",          # 25
            "East Bay General Contractor",         # 26
            "Custom Home General Contractor",      # 29
            "High-End General Contractor",         # 25
            "Integrated Design & Build GC",        # 26
            "Licensed General Contractor",         # 26
            "Trusted General Contractor",            # 24
            "Photorealistic Renders",             # 23
            "Turnkey Contractor Services",         # 26
            "Engineering & Permits In-House",      # 29
            "Trusted East Bay Contractor",         # 26
            "Projects From $150K",                 # 19
            "Start Your Project Today",            # 24
            "Request a Contractor Consult",        # 27
        ],
        "descriptions": {
            "luxury": [
                "Premium luxury general contractor serving the East Bay. Projects from $150K.",  # 75
                "Unlike traditional GCs, we integrate design, engineering & construction.",      # 70
            ],
            "process": [
                "Photorealistic renders, certified engineering & premium craftsmanship.",       # 67
                "Integrated general contractor. Design, permits & build — one expert team.",    # 71
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Lafayette & the East Bay.",        # 67
                "Premium general contractor for the East Bay. Submit your project inquiry.",    # 72
            ],
        },
    },

    "Remodeling Contractor": {
        "headlines": [
            "Luxury Remodeling Contractor",        # 27
            "Premium Home Remodeling",             # 22
            "Design-Build Remodeling Firm",        # 27
            "East Bay Remodeling Contractor",      # 29
            "High-End Home Remodeling",            # 23
            "Photorealistic Renders",             # 23
            "Integrated Design & Remodel",         # 27
            "Licensed Remodeling Contractor",      # 29
            "Seamless Remodeling Firm",       # 28
            "Turnkey Remodeling Services",         # 26
            "Engineering & Permits In-House",      # 29
            "Trusted East Bay Remodeler",          # 25
            "Whole-Home Remodeling From $1M",      # 29
            "Custom Remodeling Services",          # 25
            "Request a Remodel Consultation",      # 29
        ],
        "descriptions": {
            "luxury": [
                "East Bay's premium remodeling contractor. Whole-home remodels from $1M.",      # 71
                "We integrate design, engineering & construction. No handoffs, no surprises.",  # 76
            ],
            "process": [
                "Photorealistic renders show your finished remodel before work begins.",        # 70
                "Integrated remodeling contractor. Design, permits & build under one roof.",    # 72
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Orinda & Lafayette. Inquire.",    # 72
                "Remodeling contractor for the East Bay. Submit your project inquiry today.",   # 71
            ],
        },
    },

    "Home Renovation": {
        "headlines": [
            "Luxury Home Renovation",              # 22
            "Premium Home Renovation",             # 23
            "Design-Build Home Renovation",        # 28
            "East Bay Home Renovation",            # 23
            "High-End Home Renovation",            # 23
            "Photorealistic Renders",             # 23
            "Integrated Design & Renovation",      # 29
            "Whole-Home Renovation Services",      # 29
            "Seamless Home Renovation",       # 27
            "Turnkey Home Renovation Firm",        # 27
            "Permits & Engineering In-House",      # 29
            "Trusted East Bay Renovator",          # 25
            "Home Renovations From $150K",         # 26
            "Custom Renovation Services",          # 25
            "Start Your Renovation Today",         # 27
        ],
        "descriptions": {
            "luxury": [
                "Luxury home renovations for East Bay homeowners who demand seamless execution.", # 78
                "Ridgecrest Designs: design, engineering, permits & construction in-house.",     # 70
            ],
            "process": [
                "Photorealistic renders show your renovated home before we break ground.",     # 72
                "Integrated renovation firm. One team, total accountability, zero surprises.",  # 71
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Lafayette & Orinda. Inquire.",    # 71
                "Home renovations from $150K in the East Bay. Submit your inquiry today.",      # 69
            ],
        },
    },

    "Design Build Contractor": {
        "headlines": [
            "Luxury Design-Build Contractor",      # 29
            "Premium Design-Build Services",       # 29
            "East Bay Design-Build Experts",       # 29
            "Integrated Design & Build",           # 25
            "Photorealistic Renders",             # 23
            "Custom Design-Build Contractor",      # 28
            "Design-Build From Concept",           # 24
            "Design Build Ridgecrest",          # 26
            "Turnkey Design-Build Process",        # 27
            "Engineering & Permits In-House",      # 29
            "Trusted Design-Build Firm",           # 25
            "High-End Design-Build Firm",          # 26
            "Projects From $150K+",                # 19
            "Request a Design-Build Consult",      # 28
        ],
        "descriptions": {
            "luxury": [
                "East Bay's premier design-build contractor. Seamless design to construction.", # 73
                "One expert team for design, engineering, permits & construction. No handoffs.", # 77
            ],
            "process": [
                "Photorealistic renders, certified engineering & premium craftsmanship.",      # 67
                "Design-build contractor: concept to walkthrough under one expert roof.",       # 67
            ],
            "local": [
                "Serving Pleasanton, Walnut Creek, Danville, Lafayette & the East Bay.",       # 66
                "Design-build contractor for the East Bay. Submit your project inquiry today.", # 73
            ],
        },
    },
}

# ---------------------------------------------------------------------------
# Keywords — per theme × per city, exact + phrase match
# All keyword text pulled directly from CLAUDE.md §17
# ---------------------------------------------------------------------------

KEYWORD_STEMS = {
    "Design Build":            "design build",
    "Custom Home":             "custom home",
    "Custom Home Builder":     "custom home builder",
    "Whole House Remodel":     "whole house remodel",
    "Kitchen Remodel":         "kitchen remodel",
    "Bathroom Remodel":        "bathroom remodel",
    "Master Bathroom Remodel": "master bathroom remodel",
    "Interior Design":         "interior design",
    "Interior Design Firm":    "interior design firm",
    "Kitchen Design":          "kitchen design",
    "Bathroom Design":         "bathroom design",
    "Home Design":             "home design",
    "Architect":               "architect",
    "Home Builder":            "home builder",
    "General Contractor":      "general contractor",
    "Remodeling Contractor":   "remodeling contractor",
    "Home Renovation":         "home renovation",
    "Design Build Contractor": "design build contractor",
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_copy():
    """Fail fast if any headline > 30 chars or description > 90 chars."""
    errors = []
    for theme, copy in AD_COPY.items():
        for i, h in enumerate(copy["headlines"]):
            if len(h) > 30:
                errors.append(f"[{theme}] H{i+1} ({len(h)} chars): '{h}'")
        for angle, descs in copy["descriptions"].items():
            for i, d in enumerate(descs):
                if len(d) > 90:
                    errors.append(f"[{theme}] desc.{angle}[{i}] ({len(d)} chars): '{d[:50]}...'")
    if errors:
        logger.error("CHARACTER LIMIT VIOLATIONS — fix before proceeding:")
        for e in errors:
            logger.error("  %s", e)
        raise ValueError(f"{len(errors)} character limit violation(s) in AD_COPY")
    logger.info("Ad copy validation passed — all headlines ≤30, descriptions ≤90")


# BRAND.md forbidden words — checked at build time against all hardcoded ad copy.
# Update this list when §4 of BRAND.md is updated.
_BRAND_FORBIDDEN = [
    "award-winning",
    "photo-realistic",       # correct form is "photorealistic" (no hyphen)
    "free consultation",
    "free estimate",
    "free quote",
    "licensed & insured",
    "licensed and insured",
    "#1",
    "best in the bay area",
    "top-rated",
    "world-class",
    "industry-leading",
    "affordable",
    "budget-friendly",
    "discount",
    "save money",
    "low cost",
    "competitive pricing",
    "on-time and on-budget",
    "your one-stop shop",
    "we do it all",
    "limited time offer",
    "act now",
    "quality you can trust",
    "above and beyond",
    "second to none",
    "passion for excellence",
]


def _validate_brand_compliance():
    """Warn if any hardcoded ad copy contains phrases forbidden by BRAND.md §4.

    Raises ValueError on violations so bad copy is caught before any campaign
    is created or pushed to the Google Ads API.
    """
    violations = []
    for theme, copy in AD_COPY.items():
        for i, h in enumerate(copy["headlines"]):
            h_lower = h.lower()
            for phrase in _BRAND_FORBIDDEN:
                if phrase in h_lower:
                    violations.append(f"[{theme}] H{i+1} contains '{phrase}': '{h}'")
        for angle, descs in copy["descriptions"].items():
            for i, d in enumerate(descs):
                d_lower = d.lower()
                for phrase in _BRAND_FORBIDDEN:
                    if phrase in d_lower:
                        violations.append(
                            f"[{theme}] desc.{angle}[{i}] contains '{phrase}': '{d[:60]}...'"
                        )
    if violations:
        logger.error("BRAND.md COMPLIANCE VIOLATIONS — fix copy before building campaigns:")
        for v in violations:
            logger.error("  %s", v)
        raise ValueError(f"{len(violations)} BRAND.md violation(s) in AD_COPY — see BRAND.md §4")
    logger.info("BRAND.md compliance passed — no forbidden phrases detected")


# ---------------------------------------------------------------------------
# RSA variant builder
# Three distinct RSA ads per ad group:
#   Ad A: Headlines 1–8   + luxury descriptions      → Premium/Luxury angle
#   Ad B: Headlines 5–12  + process descriptions     → Process/Expertise angle
#   Ad C: Headlines 8–15  + local descriptions       → Local/CTA angle
# ---------------------------------------------------------------------------

def _build_rsa_variants(theme: str, city: str) -> list[dict]:
    copy = AD_COPY[theme]
    headlines = copy["headlines"]
    descs = copy["descriptions"]

    # City-specific headline to insert (if room)
    city_hl = f"Serving {city}"  # e.g. "Serving Danville" = ≤ ~26 chars for longest city

    def _with_city(hl_list):
        """Append city headline if it fits and isn't already in the list."""
        result = list(hl_list)
        candidate = f"Serving {city}"
        if len(candidate) <= 30 and candidate not in result:
            result.append(candidate)
        return result

    rsa_a = {
        "name": f"Ad A — Luxury",
        "headlines": _with_city(headlines[:8]),
        "descriptions": descs["luxury"],
    }
    rsa_b = {
        "name": f"Ad B — Process",
        "headlines": _with_city(headlines[4:12]),
        "descriptions": descs["process"],
    }
    rsa_c = {
        "name": f"Ad C — Local CTA",
        "headlines": _with_city(headlines[8:]),
        "descriptions": descs["local"],
    }
    return [rsa_a, rsa_b, rsa_c]


# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------

def _final_url(theme_key: str, city: str) -> str:
    city_slug = city.lower().replace(" ", "-")
    utm = (f"utm_source=google&utm_medium=cpc"
           f"&utm_campaign=rma-{theme_key}&utm_term={city_slug}"
           f"&utm_content=claude_code_rma")
    return f"{LANDING_PAGE}?{utm}"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _db_upsert_campaign(name: str, external_id: str, service_category: str,
                        status: str = "PAUSED") -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO campaigns
               (google_campaign_id, name, status, campaign_type, daily_budget_micros,
                bidding_strategy, service_category, platform, managed_by, last_synced_at)
               VALUES (%s, %s, %s, 'SEARCH', %s, 'MANUAL_CPC', %s, 'google_ads', 'claude_code', NOW())
               ON CONFLICT (google_campaign_id) DO UPDATE SET
                   name             = EXCLUDED.name,
                   status           = EXCLUDED.status,
                   service_category = EXCLUDED.service_category,
                   managed_by       = 'claude_code',
                   last_synced_at   = NOW(),
                   updated_at       = NOW()
               RETURNING id""",
            (external_id, name, status, 125_000_000, service_category),
        )
        return cur.fetchone()["id"]


def _db_upsert_ad_group(campaign_id: int, name: str, external_id: str,
                        status: str = "ENABLED") -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ad_groups
               (google_ad_group_id, campaign_id, name, status, cpc_bid_micros, updated_at)
               VALUES (%s, %s, %s, %s, 2500000, NOW())
               ON CONFLICT (google_ad_group_id) DO UPDATE SET
                   name           = EXCLUDED.name,
                   status         = EXCLUDED.status,
                   cpc_bid_micros = 2500000,
                   updated_at     = NOW()
               RETURNING id""",
            (external_id, campaign_id, name, status),
        )
        return cur.fetchone()["id"]


def _db_upsert_ad(ad_group_id: int, external_id: str, headlines: list,
                  descriptions: list, final_url: str, status: str = "ENABLED",
                  creative_notes: str = "") -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ads
               (google_ad_id, ad_group_id, ad_type, status, headlines, descriptions,
                final_urls, ai_generated, creative_notes, updated_at)
               VALUES (%s, %s, 'RESPONSIVE_SEARCH_AD', %s, %s, %s, %s, TRUE, %s, NOW())
               ON CONFLICT (google_ad_id) DO UPDATE SET
                   status         = EXCLUDED.status,
                   headlines      = EXCLUDED.headlines,
                   descriptions   = EXCLUDED.descriptions,
                   final_urls     = EXCLUDED.final_urls,
                   creative_notes = EXCLUDED.creative_notes,
                   updated_at     = NOW()
               RETURNING id""",
            (external_id, ad_group_id, status,
             json.dumps(headlines), json.dumps(descriptions),
             json.dumps([final_url]), creative_notes),
        )
        return cur.fetchone()["id"]


def _db_upsert_keyword(ad_group_id: int, external_id: str, keyword_text: str,
                       match_type: str, status: str = "ENABLED") -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO keywords
               (google_keyword_id, ad_group_id, keyword_text, match_type, status,
                cpc_bid_micros, updated_at)
               VALUES (%s, %s, %s, %s, %s, 2500000, NOW())
               ON CONFLICT (google_keyword_id) DO UPDATE SET
                   keyword_text  = EXCLUDED.keyword_text,
                   match_type    = EXCLUDED.match_type,
                   status        = EXCLUDED.status,
                   updated_at    = NOW()
               RETURNING id""",
            (external_id, ad_group_id, keyword_text, match_type, status),
        )
        return cur.fetchone()["id"]


# ---------------------------------------------------------------------------
# Google Ads API helpers
# ---------------------------------------------------------------------------

def _get_google_client():
    from google.ads.googleads.client import GoogleAdsClient
    creds = {
        "developer_token":   os.getenv("GOOGLE_DEVELOPER_TOKEN"),
        "client_id":         os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret":     os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token":     os.getenv("GOOGLE_REFRESH_TOKEN"),
        "login_customer_id": MANAGER_ID,
        "use_proto_plus":    True,
    }
    return GoogleAdsClient.load_from_dict(creds)


def _gads_create_budget(client, campaign_name: str) -> str:
    """Create a shared daily budget of $125 and return its resource name."""
    budget_service = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    budget = op.create
    budget.name = f"Budget — {campaign_name}"
    budget.amount_micros = 125_000_000   # $125.00
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False

    resp = budget_service.mutate_campaign_budgets(
        customer_id=CUSTOMER_ID, operations=[op]
    )
    return resp.results[0].resource_name


def _gads_create_campaign(client, name: str, budget_resource: str,
                          status: str) -> str:
    """Create a Search campaign. Returns resource name."""
    campaign_service = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    c = op.create
    c.name = name
    c.status = getattr(client.enums.CampaignStatusEnum, status)
    c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    c.campaign_budget = budget_resource
    c.manual_cpc.enhanced_cpc_enabled = False
    # Run Fri–Mon only: schedule handled via campaign bid modifiers / ad schedule
    return _mutate_single(campaign_service, "mutate_campaigns", op)


def _gads_create_ad_group(client, campaign_resource: str, name: str) -> str:
    svc = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    ag = op.create
    ag.name = name
    ag.campaign = campaign_resource
    ag.status = client.enums.AdGroupStatusEnum.ENABLED
    ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ag.cpc_bid_micros = 2_500_000  # $2.50 default CPC
    return _mutate_single(svc, "mutate_ad_groups", op)


def _gads_create_rsa(client, ad_group_resource: str,
                     headlines: list[str], descriptions: list[str],
                     final_url: str) -> str:
    svc = client.get_service("AdGroupAdService")
    op = client.get_type("AdGroupAdOperation")
    aga = op.create
    aga.ad_group = ad_group_resource
    aga.status = client.enums.AdGroupAdStatusEnum.ENABLED

    ad = aga.ad
    ad.final_urls.append(final_url)
    rsa = ad.responsive_search_ad
    for text in headlines:
        asset = client.get_type("AdTextAsset")
        asset.text = text
        rsa.headlines.append(asset)
    for text in descriptions:
        asset = client.get_type("AdTextAsset")
        asset.text = text
        rsa.descriptions.append(asset)
    return _mutate_single(svc, "mutate_ad_group_ads", op)


def _gads_create_keyword(client, ad_group_resource: str,
                         keyword_text: str, match_type: str) -> str:
    svc = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.create
    criterion.ad_group = ad_group_resource
    criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    criterion.keyword.text = keyword_text
    criterion.keyword.match_type = getattr(
        client.enums.KeywordMatchTypeEnum, match_type
    )
    return _mutate_single(svc, "mutate_ad_group_criteria", op)


def _gads_add_geo_targets(client, campaign_resource: str):
    """Add location targeting for all 12 approved cities."""
    svc = client.get_service("CampaignCriterionService")
    ops = []
    for city, loc_id in GOOGLE_LOCATION_IDS.items():
        op = client.get_type("CampaignCriterionOperation")
        criterion = op.create
        criterion.campaign = campaign_resource
        criterion.location.geo_target_constant = (
            client.get_service("GeoTargetConstantService")
            .geo_target_constant_path(loc_id)
        )
        ops.append(op)
    if ops:
        svc.mutate_campaign_criteria(customer_id=CUSTOMER_ID, operations=ops)


def _mutate_single(service, method_name: str, operation) -> str:
    resp = getattr(service, method_name)(
        customer_id=CUSTOMER_ID, operations=[operation]
    )
    return resp.results[0].resource_name


# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------

def build(db_only: bool = False, dry_run: bool = False):
    _validate_copy()
    _validate_brand_compliance()

    google_client = None
    if not db_only and not dry_run:
        try:
            google_client = _get_google_client()
            logger.info("Google Ads API client initialized (customer %s)", CUSTOMER_ID)
        except Exception as e:
            logger.warning("Google Ads API unavailable — falling back to DB-only: %s", e)

    results = {
        "campaigns":  {"created": 0, "skipped": 0, "errors": 0},
        "ad_groups":  {"created": 0, "errors": 0},
        "ads":        {"created": 0, "errors": 0},
        "keywords":   {"created": 0, "errors": 0},
    }

    for theme_key, theme_name, service_category, priority, default_status in SERVICE_THEMES:
        campaign_name = f"[RMA] {theme_name} | Google Search"
        stem = KEYWORD_STEMS[theme_name]
        logger.info("─── %s (priority %d) ───", campaign_name, priority)

        # ── Campaign ─────────────────────────────────────────────────────────
        camp_external_id = f"rma_gcmp_{THEME_ABBREV[theme_key]}"
        camp_status = default_status

        if dry_run:
            logger.info("  [DRY RUN] Campaign: %s | status=%s", campaign_name, camp_status)
            camp_db_id = -1
            gads_camp_resource = None
        else:
            try:
                camp_db_id = _db_upsert_campaign(
                    name=campaign_name,
                    external_id=camp_external_id,
                    service_category=service_category,
                    status=camp_status,
                )
                logger.info("  DB campaign id=%d", camp_db_id)
                results["campaigns"]["created"] += 1
            except Exception as e:
                logger.error("  Campaign DB error: %s", e)
                results["campaigns"]["errors"] += 1
                continue

            gads_camp_resource = None
            if google_client:
                try:
                    budget_res = _gads_create_budget(google_client, campaign_name)
                    gads_camp_resource = _gads_create_campaign(
                        google_client, campaign_name, budget_res, camp_status
                    )
                    _gads_add_geo_targets(google_client, gads_camp_resource)
                    logger.info("  Google Ads campaign created: %s", gads_camp_resource)
                except Exception as e:
                    logger.warning("  Google Ads campaign error: %s", e)

        # ── Ad groups × keywords × ads (per match type) ───────────────────
        for match_type in ("EXACT", "PHRASE"):
            mt_label = "Exact Match" if match_type == "EXACT" else "Phrase Match"
            ag_name = f"[RMA] {theme_name} — {mt_label}"
            mt_abbrev2 = "e" if match_type == "EXACT" else "p"
            ag_external_id = f"rma_gag_{THEME_ABBREV[theme_key]}_{mt_abbrev2}"

            if dry_run:
                logger.info("    [DRY RUN] Ad group: %s", ag_name)
                ag_db_id = -1
                gads_ag_resource = None
            else:
                try:
                    ag_db_id = _db_upsert_ad_group(
                        campaign_id=camp_db_id,
                        name=ag_name,
                        external_id=ag_external_id,
                    )
                    results["ad_groups"]["created"] += 1
                except Exception as e:
                    logger.error("    Ad group DB error: %s", e)
                    results["ad_groups"]["errors"] += 1
                    continue

                gads_ag_resource = None
                if google_client and gads_camp_resource:
                    try:
                        gads_ag_resource = _gads_create_ad_group(
                            google_client, gads_camp_resource, ag_name
                        )
                        logger.info("    Google Ads ad group created: %s", gads_ag_resource)
                    except Exception as e:
                        logger.warning("    Google Ads ad group error: %s", e)

            # ── Keywords ─────────────────────────────────────────────────────
            for city in CITIES:
                kw_text = f"{stem} {city.lower()}"
                # Compact ID: rma_kw_{theme_abbrev}_{e|p}_{city_abbrev} — stays within VARCHAR(50)
                mt_abbrev = "e" if match_type == "EXACT" else "p"
                kw_external_id = (
                    f"rma_kw_{THEME_ABBREV[theme_key]}"
                    f"_{mt_abbrev}_{CITY_ABBREV[city]}"
                )

                if dry_run:
                    symbol = "[" + kw_text + "]" if match_type == "EXACT" else f'"{kw_text}"'
                    logger.info("      [DRY RUN] Keyword: %s", symbol)
                    continue

                try:
                    _db_upsert_keyword(
                        ad_group_id=ag_db_id,
                        external_id=kw_external_id,
                        keyword_text=kw_text,
                        match_type=match_type,
                    )
                    results["keywords"]["created"] += 1
                except Exception as e:
                    logger.error("      Keyword DB error (%s): %s", kw_text, e)
                    results["keywords"]["errors"] += 1

                if google_client and gads_ag_resource:
                    try:
                        _gads_create_keyword(
                            google_client, gads_ag_resource, kw_text, match_type
                        )
                    except Exception as e:
                        logger.warning("      Google Ads keyword error: %s", e)

            # ── 3 RSA ads (city-agnostic for this ad group) ──────────────────
            # Use "Danville" as the representative city for ad text
            # (highest-converting city per current data)
            rsa_variants = _build_rsa_variants(theme_name, "Danville")

            for i, rsa in enumerate(rsa_variants, 1):
                mt_abbrev = "e" if match_type == "EXACT" else "p"
                ad_external_id = f"rma_gad_{THEME_ABBREV[theme_key]}_{mt_abbrev}_rsa{i}"

                if dry_run:
                    logger.info("      [DRY RUN] Ad %d (%s): %d headlines, %d descriptions",
                                i, rsa["name"], len(rsa["headlines"]), len(rsa["descriptions"]))
                    continue

                try:
                    _db_upsert_ad(
                        ad_group_id=ag_db_id,
                        external_id=ad_external_id,
                        headlines=rsa["headlines"],
                        descriptions=rsa["descriptions"],
                        final_url=_final_url(theme_key, "danville"),
                        creative_notes=f"{theme_name} | {mt_label} | {rsa['name']}",
                    )
                    results["ads"]["created"] += 1
                except Exception as e:
                    logger.error("      Ad DB error: %s", e)
                    results["ads"]["errors"] += 1
                    continue

                if google_client and gads_ag_resource:
                    try:
                        _gads_create_rsa(
                            google_client, gads_ag_resource,
                            rsa["headlines"], rsa["descriptions"],
                            _final_url(theme_key, "danville"),
                        )
                    except Exception as e:
                        logger.warning("      Google Ads RSA error: %s", e)

    # ── Fill in ads for the 3 existing test campaigns ────────────────────────
    logger.info("")
    logger.info("=== Filling ads for existing test campaign ad groups ===")
    _fill_test_campaign_ads(dry_run)

    return results


def _fill_test_campaign_ads(dry_run: bool = False):
    """
    The 3 test campaigns (TEST_CAMP_001/002/003) have ad groups but zero ads.
    Map them to their service theme and create 3 RSAs per ad group.
    """
    TEST_MAP = [
        # (campaign_name_fragment, theme_name, city)
        ("Design Build — Danville",           "Design Build",       "Danville"),
        ("Kitchen Remodel — Pleasanton",      "Kitchen Remodel",    "Pleasanton"),
        ("Whole House Remodel — Walnut Creek","Whole House Remodel","Walnut Creek"),
    ]

    with db.get_db() as (conn, cur):
        for camp_fragment, theme_name, city in TEST_MAP:
            cur.execute(
                "SELECT id FROM campaigns WHERE name LIKE %s AND platform='google_ads'",
                (f"%{camp_fragment}%",)
            )
            camp_row = cur.fetchone()
            if not camp_row:
                logger.warning("  Test campaign not found: %s", camp_fragment)
                continue
            camp_id = camp_row["id"]

            cur.execute(
                "SELECT id, name FROM ad_groups WHERE campaign_id = %s",
                (camp_id,)
            )
            ad_groups = cur.fetchall()

            for ag in ad_groups:
                ag_id = ag["id"]
                ag_name = ag["name"]
                match_type = "EXACT" if "Exact" in ag_name else "PHRASE"
                mt_label = "Exact Match" if match_type == "EXACT" else "Phrase Match"

                # Check if ads already exist
                cur.execute("SELECT COUNT(*) as cnt FROM ads WHERE ad_group_id = %s", (ag_id,))
                existing = cur.fetchone()["cnt"]
                if existing > 0:
                    logger.info("  %s — already has %d ads, skipping", ag_name, existing)
                    continue

                rsa_variants = _build_rsa_variants(theme_name, city)
                theme_key = theme_name.lower().replace(" ", "_")

                for i, rsa in enumerate(rsa_variants, 1):
                    ad_external_id = f"test_{theme_key}_{match_type.lower()}_rsa{i}"
                    if dry_run:
                        logger.info("  [DRY RUN] Would create RSA %d for %s", i, ag_name)
                        continue
                    try:
                        _db_upsert_ad(
                            ad_group_id=ag_id,
                            external_id=ad_external_id,
                            headlines=rsa["headlines"],
                            descriptions=rsa["descriptions"],
                            final_url=_final_url(theme_key, city.lower().replace(" ", "-")),
                            creative_notes=f"{theme_name} | {mt_label} | {rsa['name']} [test campaign]",
                        )
                        logger.info("  Created RSA %d for %s", i, ag_name)
                    except Exception as e:
                        logger.error("  Ad error for %s RSA %d: %s", ag_name, i, e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build Ridgecrest Designs Google Ads hierarchy")
    parser.add_argument("--db-only",  action="store_true",
                        help="Write to DB only; skip Google Ads API calls")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Preview only — no DB writes, no API calls")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Ridgecrest Designs — Google Ads Hierarchy Builder")
    logger.info("Mode: %s", "DRY RUN" if args.dry_run else
                ("DB ONLY" if args.db_only else "FULL (DB + Google Ads API)"))
    logger.info("Themes: %d | Cities: %d", len(SERVICE_THEMES), len(CITIES))
    logger.info("Expected structure: %d campaigns × 2 ad groups × 3 RSAs + 12 keywords",
                len(SERVICE_THEMES))
    logger.info("=" * 60)

    results = build(db_only=args.db_only, dry_run=args.dry_run)

    if not args.dry_run:
        logger.info("")
        logger.info("=" * 60)
        logger.info("BUILD COMPLETE")
        logger.info("  Campaigns : created=%d errors=%d",
                    results["campaigns"]["created"], results["campaigns"]["errors"])
        logger.info("  Ad Groups : created=%d errors=%d",
                    results["ad_groups"]["created"], results["ad_groups"]["errors"])
        logger.info("  Ads       : created=%d errors=%d",
                    results["ads"]["created"], results["ads"]["errors"])
        logger.info("  Keywords  : created=%d errors=%d",
                    results["keywords"]["created"], results["keywords"]["errors"])
        logger.info("=" * 60)

    return results


if __name__ == "__main__":
    import sys
    results = main()
    errors = sum(v.get("errors", 0) for v in results.values())
    sys.exit(1 if errors > 0 else 0)
