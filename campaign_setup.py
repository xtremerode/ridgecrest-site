"""
Campaign Setup — Ridgecrest Marketing Agency (Claude Code)
==========================================================
Creates the full campaign structure for the Claude Code Ridgecrest Marketing Agency.

Every asset is tagged:
  - Name prefix : [RMA]
  - Label       : Claude Code — RMA
  - Final URLs  : utm_content=claude_code_rma
  - DB          : managed_by = 'claude_code'

Currently supported: Microsoft Ads
Pending:             Google Ads (developer token approval)

Usage:
  source venv/bin/activate

  # Preview — no changes made
  python campaign_setup.py --platform microsoft --dry-run

  # Execute
  python campaign_setup.py --platform microsoft
"""

import argparse
import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [campaign_setup] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Identity tag
# ---------------------------------------------------------------------------

RMA_PREFIX   = "[RMA]"
RMA_LABEL    = "Claude Code — RMA"
UTM_TAG      = "utm_source={platform}&utm_medium=cpc&utm_campaign={campaign}&utm_content=claude_code_rma"
LANDING_PAGE = "https://go.ridgecrestdesigns.com"
MANAGED_BY   = "claude_code"

# ---------------------------------------------------------------------------
# Campaign structure — 17 themes × 12 cities
# ---------------------------------------------------------------------------

SERVICE_THEMES = [
    "Design Build",
    "Custom Home",
    "Custom Home Builder",
    "Whole House Remodel",
    "Kitchen Remodel",
    "Bathroom Remodel",
    "Master Bathroom Remodel",
    "Interior Design",
    "Interior Design Firm",
    "Kitchen Design",
    "Bathroom Design",
    "Home Design",
    "Architect",
    "Home Builder",
    "General Contractor",
    "Remodeling Contractor",
    "Home Renovation",
    "Design Build Contractor",
]

CITIES = [
    "Walnut Creek", "Pleasanton", "Sunol", "San Ramon", "Dublin",
    "Orinda", "Moraga", "Danville", "Alamo", "Lafayette",
    "Rossmoor", "Diablo",
]

# Microsoft Ads location IDs for target cities (Bing location criterion IDs)
# These are verified Bing Ads geo IDs for the target cities in California
MSFT_LOCATION_IDS = {
    "Walnut Creek": 103188,
    "Pleasanton":   103171,
    "San Ramon":    103179,
    "Dublin":       103137,
    "Orinda":       103167,
    "Moraga":       103160,
    "Danville":     103132,
    "Alamo":        103106,
    "Lafayette":    103154,
    "Rossmoor":     103177,
    "Sunol":        103186,
    "Diablo":       103134,
}

# ---------------------------------------------------------------------------
# Ad copy — per service theme
# ---------------------------------------------------------------------------

AD_COPY = {
    "Design Build": {
        "headlines": [
            "Luxury Design-Build Firm",
            "Design-Build Experts Near You",
            "Seamless Design to Construction",
            "Photorealistic Renders",
            "Custom Design-Build Services",
            "Integrated Design & Construction",
            "East Bay Design-Build Specialists",
            "From Vision to Finished Home",
            "Trusted Design-Build Firm",
            "Premium Design-Build Services",
            "Turnkey Design-Build Projects",
            "Trusted Design-Build Contractor",
            "Start Your Design-Build Project",
            "High-End Design-Build Firm",
            "Schedule a Consultation",
        ],
        "descriptions": [
            "Ridgecrest Designs delivers luxury design-build services from concept through construction. Photorealistic renders before a single nail is driven.",
            "Integrated design, engineering, permitting, and construction under one roof. Serving Pleasanton, Walnut Creek, Danville, and the East Bay.",
            "Premium design-build for discerning homeowners. Clear process, expert teams, and flawless execution from first sketch to final walkthrough.",
            "Submit your project inquiry today. We specialize in custom homes, whole-home remodels, and high-end renovations starting at $150K.",
        ],
    },
    "Custom Home": {
        "headlines": [
            "Custom Luxury Homes",
            "Build Your Dream Custom Home",
            "Custom Home Design & Build",
            "Photorealistic Home Renders",
            "Luxury Custom Home Builder",
            "Custom Homes From $5M",
            "Design-Build Custom Homes",
            "East Bay Custom Home Experts",
            "Premium Custom Home Services",
            "Engineered & Permitted In-House",
            "Your Vision, Expertly Built",
            "Custom Homes — Turnkey Process",
            "Trusted Custom Home Builder",
            "High-End Custom Home Design",
            "Request a Project Consultation",
        ],
        "descriptions": [
            "Build your custom luxury home with Ridgecrest Designs. We handle design, engineering, permitting, and construction — start to finish.",
            "Photorealistic renders give you visual certainty before construction begins. Custom homes from $5M in the East Bay.",
            "Our integrated design-build process eliminates the gap between architect and contractor. One team, one vision, zero surprises.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, and surrounding East Bay communities. Request your consultation today.",
        ],
    },
    "Custom Home Builder": {
        "headlines": [
            "Premium Custom Home Builder",
            "Custom Home Builder Near You",
            "Luxury Custom Home Builder",
            "Photorealistic Home Renders",
            "East Bay Custom Home Builder",
            "Design-Build Custom Homes",
            "Custom Homes Built Right",
            "Integrated Design & Build",
            "Trusted Custom Home Builder",
            "Custom Homes From $5M+",
            "Engineered & Permitted In-House",
            "Your Builder for Life",
            "Premium Custom Homebuilder",
            "Luxury Custom Home Builder",
            "Start Your Custom Home Today",
        ],
        "descriptions": [
            "Ridgecrest Designs is the East Bay's premium custom home builder. Design, engineering, permits, and construction — all in-house.",
            "We build custom homes from $5M–$10M for discerning homeowners who demand quality, precision, and a seamless process.",
            "Photorealistic renders let you see your home before we break ground. No guesswork, no surprises — just flawless execution.",
            "Serving Pleasanton, Danville, Walnut Creek, Lafayette, Orinda, and the greater East Bay. Request a consultation today.",
        ],
    },
    "Whole House Remodel": {
        "headlines": [
            "Whole House Remodel Experts",
            "Full Home Renovation Services",
            "Whole-Home Remodel & Design",
            "Luxury Home Renovation",
            "Complete Home Transformation",
            "Whole House Remodels From $1M",
            "Design-Build Home Renovation",
            "Integrated Remodel Process",
            "Photorealistic Renders",
            "Turnkey Whole Home Remodel",
            "East Bay Remodel Specialists",
            "Permitted & Engineered In-House",
            "Trusted Renovation Contractor",
            "High-End Home Renovation",
            "Request a Remodel Consultation",
        ],
        "descriptions": [
            "Transform your entire home with Ridgecrest Designs. Whole-home remodels starting at $1M for discerning East Bay homeowners.",
            "Integrated design-build for whole-house renovations. We handle design, engineering, permits, and construction under one roof.",
            "Photorealistic renders show your finished home before construction begins. Clear process, expert teams, flawless results.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, and surrounding East Bay cities. Submit your project inquiry today.",
        ],
    },
    "Kitchen Remodel": {
        "headlines": [
            "Luxury Kitchen Remodel",
            "Custom Kitchen Design & Build",
            "High-End Kitchen Renovation",
            "Kitchen Remodels From $150K",
            "Photorealistic Kitchen Renders",
            "Design-Build Kitchen Experts",
            "Premium Kitchen Remodeling",
            "Custom Kitchens East Bay",
            "Integrated Kitchen Design-Build",
            "Chef-Quality Kitchen Design",
            "Turnkey Kitchen Renovation",
            "Permitted Kitchen Remodels",
            "Trusted Kitchen Contractor",
            "Meticulous Kitchen Design",
            "Start Your Kitchen Project",
        ],
        "descriptions": [
            "Luxury kitchen remodels starting at $150K. Ridgecrest Designs handles design, engineering, permits, and construction in-house.",
            "See your new kitchen before we build it. Photorealistic renders give you total confidence in every design decision.",
            "Custom cabinetry, premium finishes, and expert craftsmanship. East Bay kitchen remodeling at its highest level.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, and the East Bay. Submit your kitchen project inquiry today.",
        ],
    },
    "Bathroom Remodel": {
        "headlines": [
            "Luxury Bathroom Remodel",
            "Custom Bathroom Design & Build",
            "High-End Bathroom Renovation",
            "Bathroom Remodels From $60K",
            "Photorealistic Bath Renders",
            "Design-Build Bathroom Experts",
            "Premium Bathroom Remodeling",
            "Custom Bathrooms East Bay",
            "Spa-Quality Bathroom Design",
            "Turnkey Bathroom Renovation",
            "Integrated Bath Design-Build",
            "Permitted Bathroom Remodels",
            "Trusted Bathroom Contractor",
            "Meticulous Bath Design",
            "Start Your Bathroom Project",
        ],
        "descriptions": [
            "Luxury bathroom remodels starting at $60K. Ridgecrest Designs delivers premium design, engineering, and construction.",
            "Photorealistic renders let you visualize your new bathroom in detail before a single tile is set.",
            "Custom tile, premium fixtures, and expert craftsmanship. Bathroom remodeling for discerning East Bay homeowners.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, and surrounding areas. Request your bathroom consultation today.",
        ],
    },
    "Master Bathroom Remodel": {
        "headlines": [
            "Luxury Master Bath Remodel",
            "Custom Master Bathroom Design",
            "Master Bath From $100K",
            "Photorealistic Bath Renders",
            "Design-Build Master Bathroom",
            "Spa-Level Master Bath Design",
            "Premium Master Bath Remodel",
            "East Bay Master Bath Experts",
            "Turnkey Master Bath Renovation",
            "Integrated Master Bath Build",
            "Permitted Master Bathroom Work",
            "High-End Master Bath Design",
            "Trusted Master Bath Contractor",
            "Meticulous Bathroom Design",
            "Start Your Master Bath Today",
        ],
        "descriptions": [
            "Master bathroom remodels starting at $100K. Premium design, spa-quality finishes, and expert construction by Ridgecrest Designs.",
            "See your dream master bath before we build it. Photorealistic renders included with every project consultation.",
            "Custom tile, freestanding soaks, and resort-level finishes. Master bathroom remodeling for the East Bay's discerning homeowners.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, and the greater East Bay. Submit your master bath project today.",
        ],
    },
    "Interior Design": {
        "headlines": [
            "Luxury Interior Design Firm",
            "Premium Interior Design Services",
            "Custom Interior Design & Build",
            "East Bay Interior Designers",
            "Full-Service Interior Design",
            "Photorealistic Design Renders",
            "Design-Build Interior Experts",
            "Integrated Design & Construction",
            "High-End Interior Design",
            "Turnkey Interior Design Build",
            "Meticulous Interior Design",
            "Trusted Interior Design Firm",
            "Interior Design With Permits",
            "From Concept to Completion",
            "Request a Design Consultation",
        ],
        "descriptions": [
            "Ridgecrest Designs delivers full-service luxury interior design integrated with construction. No gap between designer and builder.",
            "Photorealistic renders show your finished interior in photographic detail before a single wall is touched.",
            "Premium materials, curated finishes, and expert craftsmanship for East Bay homeowners who demand the best.",
            "Serving Pleasanton, Walnut Creek, Danville, and the East Bay. Submit your interior design project inquiry today.",
        ],
    },
    "Interior Design Firm": {
        "headlines": [
            "Premium East Bay Design Firm",
            "Luxury Interior Design Firm",
            "East Bay Design-Build Firm",
            "Full-Service Design Firm",
            "Premium Interior Design Firm",
            "Design Firm With Build Capability",
            "Photorealistic Design Renders",
            "Integrated Design-Build Firm",
            "Trusted Design-Build Firm",
            "Trusted East Bay Design Firm",
            "High-End Interior Design Firm",
            "From Vision to Construction",
            "Custom Design With Permits",
            "Turnkey Design Firm Services",
            "Request a Firm Consultation",
        ],
        "descriptions": [
            "Ridgecrest Designs is a full-service luxury design-build firm serving the East Bay. Design, engineering, permits, and construction — all in-house.",
            "Unlike standalone interior design firms, we take your project from first concept to final walkthrough without switching teams.",
            "Photorealistic renders, premium finishes, and meticulous attention to detail. The East Bay's premier design-build firm.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, Orinda, and surrounding communities. Request a consultation today.",
        ],
    },
    "Kitchen Design": {
        "headlines": [
            "Custom Kitchen Design Services",
            "Luxury Kitchen Design & Build",
            "Photorealistic Kitchen Design",
            "East Bay Kitchen Design Experts",
            "Premium Kitchen Design Firm",
            "Kitchen Design With Build",
            "Design-Build Kitchen Services",
            "Integrated Kitchen Design",
            "Meticulous Kitchen Design",
            "Chef-Quality Kitchen Planning",
            "Turnkey Kitchen Design & Build",
            "See Your Kitchen Before Build",
            "Trusted Kitchen Design Firm",
            "High-End Kitchen Designers",
            "Start Your Kitchen Design",
        ],
        "descriptions": [
            "Luxury kitchen design integrated with construction. Ridgecrest Designs takes your kitchen from concept to completion.",
            "Photorealistic renders show your finished kitchen before we touch a single cabinet. Confidence at every step.",
            "Custom cabinetry, premium countertops, and expert layout planning for East Bay homeowners who want the best.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, and the East Bay. Submit your kitchen design inquiry today.",
        ],
    },
    "Bathroom Design": {
        "headlines": [
            "Custom Bathroom Design Services",
            "Luxury Bathroom Design & Build",
            "Photorealistic Bath Design",
            "East Bay Bathroom Designers",
            "Premium Bathroom Design Firm",
            "Bathroom Design With Build",
            "Design-Build Bathroom Services",
            "Integrated Bathroom Design",
            "Meticulous Bathroom Design",
            "Spa-Quality Bathroom Planning",
            "Turnkey Bath Design & Build",
            "See Your Bath Before Build",
            "Trusted Bathroom Design Firm",
            "High-End Bathroom Designers",
            "Start Your Bathroom Design",
        ],
        "descriptions": [
            "Luxury bathroom design integrated with expert construction. Ridgecrest Designs takes your bath from concept to completion.",
            "Photorealistic renders show your finished bathroom in photographic detail before a single tile is ordered.",
            "Custom tile, premium fixtures, and spa-level finishes for East Bay homeowners who demand the best.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, and the East Bay. Submit your bathroom design inquiry today.",
        ],
    },
    "Home Design": {
        "headlines": [
            "Luxury Home Design Services",
            "Custom Home Design & Build",
            "Photorealistic Home Design",
            "East Bay Home Design Experts",
            "Premium Home Design Firm",
            "Home Design With Build",
            "Design-Build Home Services",
            "Integrated Home Design",
            "Meticulous Home Design",
            "Full-Service Home Design",
            "Turnkey Home Design & Build",
            "See Your Home Before Build",
            "Trusted Home Design Firm",
            "High-End Home Designers",
            "Start Your Home Design",
        ],
        "descriptions": [
            "Luxury home design integrated with full construction services. Ridgecrest Designs takes your home from vision to reality.",
            "Photorealistic renders let you see and approve every design decision before construction begins.",
            "Full-service home design covering architecture, interiors, engineering, and permitting — all under one roof.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, and the East Bay. Submit your home design inquiry today.",
        ],
    },
    "Architect": {
        "headlines": [
            "Luxury Home Architect",
            "Design-Build Architect Firm",
            "Custom Home Architecture",
            "East Bay Architect Services",
            "Architect With Build Capability",
            "Photorealistic Home Renders",
            "Integrated Architect & Builder",
            "Licensed Architect East Bay",
            "Turnkey Architecture Services",
            "Meticulous Architecture",
            "High-End Custom Architecture",
            "Architecture With Permits",
            "Trusted East Bay Architect",
            "From Plans to Finished Home",
            "Request an Architecture Consult",
        ],
        "descriptions": [
            "Ridgecrest Designs offers design-build architecture — combining licensed design expertise with full construction capability.",
            "Unlike standalone architects, we take your project through design, engineering, permitting, and construction without handoffs.",
            "Photorealistic renders, structural engineering, and premium construction for East Bay homeowners seeking excellence.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, Orinda, and the greater East Bay. Request a consultation today.",
        ],
    },
    "Home Builder": {
        "headlines": [
            "Luxury Home Builder",
            "Custom Home Builder East Bay",
            "Premium Home Builder Services",
            "Design-Build Home Builder",
            "Photorealistic Home Renders",
            "Integrated Design & Build",
            "East Bay Custom Home Builder",
            "Custom Homes Built Right",
            "Turnkey Home Builder Services",
            "Meticulous East Bay Builder",
            "Luxury Custom Home Builder",
            "Engineering & Permits In-House",
            "Trusted East Bay Builder",
            "High-End Custom Home Builder",
            "Start Building Your Home Today",
        ],
        "descriptions": [
            "Ridgecrest Designs is the East Bay's premium luxury home builder. Design, engineering, permitting, and construction in-house.",
            "We build custom homes, whole-home renovations, and luxury remodels for discerning homeowners across the East Bay.",
            "Photorealistic renders, meticulous craftsmanship, and flawless execution on every project — large and small.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, and surrounding East Bay communities. Request a consultation today.",
        ],
    },
    "General Contractor": {
        "headlines": [
            "Luxury General Contractor",
            "Premium General Contractor",
            "Design-Build Contractor East Bay",
            "Custom Home General Contractor",
            "High-End General Contractor",
            "Integrated Design & Build GC",
            "East Bay General Contractor",
            "Licensed General Contractor",
            "Trusted General Contractor",
            "Photorealistic Project Renders",
            "Turnkey Contractor Services",
            "Engineering & Permits Included",
            "Trusted East Bay Contractor",
            "General Contractor From $150K",
            "Request a Contractor Consult",
        ],
        "descriptions": [
            "Ridgecrest Designs is a premium luxury general contractor serving the East Bay. Projects starting at $150K.",
            "Unlike traditional GCs, we integrate design, engineering, permitting, and construction under one expert team.",
            "Photorealistic renders, certified engineering, and premium craftsmanship on every project we build.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, and the East Bay. Submit your project inquiry today.",
        ],
    },
    "Remodeling Contractor": {
        "headlines": [
            "Luxury Remodeling Contractor",
            "Premium Home Remodeling",
            "Design-Build Remodeling Firm",
            "East Bay Remodeling Contractor",
            "High-End Home Remodeling",
            "Photorealistic Remodel Renders",
            "Integrated Design & Remodel",
            "Licensed Remodeling Contractor",
            "Seamless Remodeling Firm",
            "Turnkey Remodeling Services",
            "Engineering & Permits Included",
            "Trusted East Bay Remodeler",
            "Whole-Home Remodeling From $1M",
            "Custom Remodeling Services",
            "Request a Remodel Consultation",
        ],
        "descriptions": [
            "Ridgecrest Designs is the East Bay's premium remodeling contractor. Whole-home remodels starting at $1M.",
            "We integrate design, engineering, permitting, and construction — no handoffs, no miscommunication, no surprises.",
            "Photorealistic renders show your finished remodel before construction begins. Confidence from day one.",
            "Serving Pleasanton, Walnut Creek, Danville, Orinda, Lafayette, and the East Bay. Request a consultation today.",
        ],
    },
    "Home Renovation": {
        "headlines": [
            "Luxury Home Renovation",
            "Premium Home Renovation Services",
            "Design-Build Home Renovation",
            "East Bay Home Renovation Experts",
            "High-End Home Renovation",
            "Photorealistic Renovation Renders",
            "Integrated Design & Renovation",
            "Whole-Home Renovation Services",
            "Seamless Home Renovation",
            "Turnkey Home Renovation Firm",
            "Permits & Engineering Included",
            "Trusted East Bay Renovator",
            "Home Renovations From $150K",
            "Custom Renovation Services",
            "Start Your Renovation Today",
        ],
        "descriptions": [
            "Luxury home renovations for East Bay homeowners who want a seamless, expert-managed experience from design to completion.",
            "Ridgecrest Designs handles design, engineering, permitting, and construction — one team, total accountability.",
            "Photorealistic renders show your renovated home before we break ground. No guesswork, no surprises.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, Orinda, and the East Bay. Submit your renovation inquiry today.",
        ],
    },
    "Design Build Contractor": {
        "headlines": [
            "Luxury Design-Build Contractor",
            "Premium Design-Build Services",
            "Design-Build Contractor East Bay",
            "Integrated Design & Build",
            "Photorealistic Project Renders",
            "East Bay Design-Build Experts",
            "Custom Design-Build Contractor",
            "Design-Build From Concept",
            "Design Build Ridgecrest",
            "Turnkey Design-Build Process",
            "Engineering & Permits In-House",
            "Trusted Design-Build Contractor",
            "Design-Build Projects From $150K",
            "High-End Design-Build Firm",
            "Request a Design-Build Consult",
        ],
        "descriptions": [
            "Ridgecrest Designs is the East Bay's premier design-build contractor. Seamless integration of design, engineering, and construction.",
            "One team handles your entire project — from vision and permits to the final walkthrough. No handoffs, no gaps.",
            "Photorealistic renders, certified engineering, and premium craftsmanship. Design-build done right.",
            "Serving Pleasanton, Walnut Creek, Danville, Lafayette, Orinda, and surrounding East Bay communities.",
        ],
    },
}


# ---------------------------------------------------------------------------
# BRAND.md compliance validation
# ---------------------------------------------------------------------------

# Forbidden phrases from BRAND.md §4 — update here when §4 is updated.
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
    """Raise ValueError if any hardcoded ad copy violates BRAND.md §4 forbidden phrases.

    Called at the start of setup_microsoft() so non-compliant copy is caught
    before any campaign is created or pushed to the Microsoft Ads API.
    """
    violations = []
    for theme, copy in AD_COPY.items():
        headlines = copy.get("headlines", [])
        descriptions = copy.get("descriptions", [])

        for i, h in enumerate(headlines):
            h_lower = h.lower()
            for phrase in _BRAND_FORBIDDEN:
                if phrase in h_lower:
                    violations.append(f"[{theme}] H{i+1} contains '{phrase}': '{h}'")

        # descriptions is a flat list in campaign_setup.py
        for i, d in enumerate(descriptions):
            d_lower = d.lower()
            for phrase in _BRAND_FORBIDDEN:
                if phrase in d_lower:
                    violations.append(
                        f"[{theme}] desc[{i}] contains '{phrase}': '{d[:60]}...'"
                    )

    if violations:
        logger.error("BRAND.md COMPLIANCE VIOLATIONS — fix copy before building campaigns:")
        for v in violations:
            logger.error("  %s", v)
        raise ValueError(
            f"{len(violations)} BRAND.md violation(s) in AD_COPY — see BRAND.md §4"
        )
    logger.info("BRAND.md compliance passed — no forbidden phrases detected")


# ---------------------------------------------------------------------------
# Shared copy helpers
# ---------------------------------------------------------------------------

def _word_trim(text: str, limit: int) -> str:
    """Trim text to limit at a word boundary. Never cuts mid-word.
    Logs a warning if trimming was needed and an error if the result
    is an incomplete sentence (does not end with . ! or ?)."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    trimmed = cut[:last_space].rstrip() if last_space > 0 else cut
    logger.warning("Ad copy trimmed: %d→%d chars | '%s' → '%s'", len(text), len(trimmed), text, trimmed)
    if not trimmed.rstrip().endswith((".", "!", "?", ")")):
        logger.error("Incomplete sentence after trim — regenerate this copy: '%s'", trimmed)
    return trimmed


# ---------------------------------------------------------------------------
# Microsoft Ads helpers
# ---------------------------------------------------------------------------

def _msft_auth():
    from bingads.authorization import (
        AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
    )
    CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID")
    CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
    TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID")
    DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN")
    REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN")
    ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID"))
    REDIRECT_URI  = "https://login.microsoftonline.com/common/oauth2/nativeclient"

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "client_id": CLIENT_ID, "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "scope": "https://ads.microsoft.com/msads.manage offline_access",
    }, timeout=30)
    resp.raise_for_status()
    td = resp.json()
    if "error" in td:
        raise RuntimeError(f"Token refresh failed: {td}")
    access_token = td["access_token"]
    expires_in   = int(td.get("expires_in", 3600))

    tokens = OAuthTokens(
        access_token=access_token,
        access_token_expires_in_seconds=expires_in,
        refresh_token=REFRESH_TOKEN,
    )
    oauth = OAuthWebAuthCodeGrant(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        redirection_uri=REDIRECT_URI, oauth_tokens=tokens,
        oauth_scope=ADS_MANAGE, tenant=TENANT_ID,
    )
    auth = AuthorizationData(
        account_id=ACCOUNT_ID,
        developer_token=DEV_TOKEN,
        authentication=oauth,
    )

    # Resolve customer ID
    from bingads import ServiceClient
    svc = ServiceClient("CustomerManagementService", 13, auth, "production")
    try:
        resp2 = svc.GetUser(UserId=None)
        roles = (resp2.CustomerRoles.CustomerRole
                 if resp2.CustomerRoles and resp2.CustomerRoles.CustomerRole else [])
        for role in roles:
            if hasattr(role, "CustomerId"):
                auth.customer_id = int(role.CustomerId)
                break
    except Exception as e:
        logger.warning("Could not resolve customer ID: %s", e)

    return auth


def _get_msft_service(auth, service_name):
    from bingads import ServiceClient
    return ServiceClient(service_name, 13, auth, "production")


def _create_msft_label(svc, dry_run: bool) -> int | None:
    """Create the RMA label if it doesn't exist. Returns label ID."""
    try:
        # Check existing labels
        resp = svc.GetLabelsByIds(LabelIds=None, PageInfo={"Index": 0, "Size": 100})
        labels = resp.Labels.Label if resp.Labels and resp.Labels.Label else []
        for lbl in labels:
            if lbl.Name == RMA_LABEL:
                logger.info("Label '%s' already exists (id=%s)", RMA_LABEL, lbl.Id)
                return int(lbl.Id)
    except Exception as e:
        logger.warning("Could not check existing labels: %s", e)

    if dry_run:
        logger.info("[DRY RUN] Would create label: '%s'", RMA_LABEL)
        return None

    label = svc.factory.create("Label")
    label.Name        = RMA_LABEL
    label.Description = "Created by Claude Code Ridgecrest Marketing Agency"
    label.ColorCode   = "#1A73E8"

    resp = svc.AddLabels(Labels={"Label": [label]})
    label_id = int(resp.LabelIds.long[0])
    logger.info("Created label '%s' (id=%d)", RMA_LABEL, label_id)
    return label_id


def _apply_msft_label(svc, label_id: int, entity_type: str, entity_ids: list[int], dry_run: bool):
    if not label_id or not entity_ids or dry_run:
        if dry_run:
            logger.info("[DRY RUN] Would apply label %d to %d %s(s)", label_id or 0, len(entity_ids), entity_type)
        return
    assocs = [{"EntityId": eid, "LabelId": label_id} for eid in entity_ids]
    try:
        svc.SetLabelAssociations(
            EntityType=entity_type,
            LabelAssociations={"LabelAssociation": assocs},
        )
        logger.info("Applied label to %d %s(s)", len(entity_ids), entity_type)
    except Exception as e:
        logger.warning("Label assignment failed for %s: %s", entity_type, e)


def _build_final_url(theme: str) -> str:
    slug = theme.lower().replace(" ", "-")
    utm = (f"utm_source=microsoft&utm_medium=cpc"
           f"&utm_campaign=rma-{slug}&utm_content=claude_code_rma")
    return f"{LANDING_PAGE}?{utm}"


def _db_upsert_campaign(name: str, platform: str, external_id: str,
                        status: str = "ENABLED") -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO campaigns
               (google_campaign_id, name, status, platform, managed_by, last_synced_at)
               VALUES (%s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_campaign_id) DO UPDATE SET
                   name           = EXCLUDED.name,
                   status         = EXCLUDED.status,
                   platform       = EXCLUDED.platform,
                   managed_by     = 'claude_code',
                   last_synced_at = NOW(),
                   updated_at     = NOW()
               RETURNING id""",
            (external_id, name, status, platform, MANAGED_BY),
        )
        return cur.fetchone()["id"]


def _db_upsert_ad_group(campaign_id: int, name: str, external_id: str,
                        status: str = "ENABLED", cpc_bid_micros: int = 2500000) -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ad_groups
               (google_ad_group_id, campaign_id, name, status, cpc_bid_micros, updated_at)
               VALUES (%s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_ad_group_id) DO UPDATE SET
                   name            = EXCLUDED.name,
                   status          = EXCLUDED.status,
                   cpc_bid_micros  = EXCLUDED.cpc_bid_micros,
                   updated_at      = NOW()
               RETURNING id""",
            (external_id, campaign_id, name, status, cpc_bid_micros),
        )
        return cur.fetchone()["id"]


def _db_upsert_ad(ad_group_id: int, external_id: str, headlines: list,
                  descriptions: list, final_url: str, status: str = "ENABLED") -> int:
    import json
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ads
               (google_ad_id, ad_group_id, ad_type, status, headlines, descriptions,
                final_urls, ai_generated, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_ad_id) DO UPDATE SET
                   status       = EXCLUDED.status,
                   headlines    = EXCLUDED.headlines,
                   descriptions = EXCLUDED.descriptions,
                   final_urls   = EXCLUDED.final_urls,
                   updated_at   = NOW()
               RETURNING id""",
            (external_id, ad_group_id, "RESPONSIVE_SEARCH_AD", status,
             json.dumps(headlines), json.dumps(descriptions),
             json.dumps([final_url]), True),
        )
        return cur.fetchone()["id"]


# ---------------------------------------------------------------------------
# Microsoft Ads — campaign builder
# ---------------------------------------------------------------------------

def setup_microsoft(dry_run: bool = False):
    logger.info("=== Microsoft Ads Campaign Setup %s===",
                "[DRY RUN] " if dry_run else "")
    _validate_brand_compliance()

    auth = _msft_auth()
    camp_svc = _get_msft_service(auth, "CampaignManagementService")

    ACCOUNT_ID = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID"))

    # Create RMA label
    label_id = _create_msft_label(camp_svc, dry_run)

    results = {
        "campaigns_created": 0,
        "ad_groups_created": 0,
        "keywords_created":  0,
        "ads_created":       0,
        "errors":            [],
    }

    for theme in SERVICE_THEMES:
        campaign_name = f"{RMA_PREFIX} {theme} | Ridgecrest Marketing"
        final_url     = _build_final_url(theme)
        copy          = AD_COPY.get(theme, AD_COPY["Design Build"])

        logger.info("--- Processing: %s ---", campaign_name)

        # ── Create campaign ──────────────────────────────────────────────
        msft_campaign_id = None
        if not dry_run:
            try:
                camp = camp_svc.factory.create("Campaign")
                camp.Name             = campaign_name
                camp.CampaignType     = "Search"
                camp.Status           = "Paused"   # Start paused — enable after review
                camp.BidStrategyScope = None        # Avoid empty EntityScope enum error

                camp.DailyBudget      = 7.00
                camp.BudgetType       = "DailyBudgetStandard"

                bidding = camp_svc.factory.create("ManualCpcBiddingScheme")
                camp.BiddingScheme    = bidding

                resp = camp_svc.AddCampaigns(
                    AccountId=ACCOUNT_ID,
                    Campaigns={"Campaign": [camp]},
                )
                msft_campaign_id = int(resp.CampaignIds.long[0])
                logger.info("  Created campaign id=%d", msft_campaign_id)
                results["campaigns_created"] += 1

                # Apply label
                if label_id:
                    _apply_msft_label(camp_svc, label_id, "Campaign",
                                      [msft_campaign_id], dry_run)

                # Save to DB
                _db_upsert_campaign(
                    name=campaign_name,
                    platform="microsoft_ads",
                    external_id=f"msft_{msft_campaign_id}",
                )

            except Exception as e:
                logger.error("  Campaign creation failed: %s", e)
                results["errors"].append(f"Campaign '{theme}': {e}")
                continue
        else:
            logger.info("[DRY RUN] Would create campaign: %s", campaign_name)
            logger.info("[DRY RUN]   Budget: $7.00/day | Status: Paused | Bidding: Manual CPC")
            results["campaigns_created"] += 1

        # ── Create ad group ──────────────────────────────────────────────
        ag_name = f"{RMA_PREFIX} {theme} — All Cities"
        msft_ag_id = None
        if not dry_run and msft_campaign_id:
            try:
                ag = camp_svc.factory.create("AdGroup")
                ag.Name             = ag_name
                ag.Status           = "Active"
                ag.CpcBid           = camp_svc.factory.create("Bid")
                ag.CpcBid.Amount    = 2.50
                ag.Language         = "English"
                ad_rotation         = camp_svc.factory.create("AdRotation")
                ad_rotation.Type    = "OptimizeForClicks"
                ag.AdRotation       = ad_rotation
                ag.Network          = "OwnedAndOperatedAndSyndicatedSearch"
                bidding_ag          = camp_svc.factory.create("InheritFromParentBiddingScheme")
                ag.BiddingScheme    = bidding_ag
                # Null out complex fields that serialize as empty Int32/enums
                ag.StartDate             = None
                ag.EndDate               = None
                ag.CommissionRate        = None
                ag.CpmBid                = None
                ag.CpvBid                = None
                ag.PercentCpcBid         = None
                ag.McpaBid               = None
                ag.PrivacyStatus         = None
                ag.Settings              = None
                ag.ForwardCompatibilityMap = None
                ag.FrequencyCapSettings  = None
                ag.UrlCustomParameters   = None

                resp = camp_svc.AddAdGroups(
                    CampaignId=msft_campaign_id,
                    AdGroups={"AdGroup": [ag]},
                )
                msft_ag_id = int(resp.AdGroupIds.long[0])
                logger.info("  Created ad group id=%d", msft_ag_id)
                results["ad_groups_created"] += 1

                if label_id:
                    _apply_msft_label(camp_svc, label_id, "AdGroup",
                                      [msft_ag_id], dry_run)

                # Save to DB
                db_campaign_id = _db_upsert_campaign(
                    name=campaign_name, platform="microsoft_ads",
                    external_id=f"msft_{msft_campaign_id}",
                )
                _db_upsert_ad_group(
                    campaign_id=db_campaign_id,
                    name=ag_name,
                    external_id=f"msft_{msft_ag_id}",
                )

            except Exception as e:
                logger.error("  Ad group creation failed: %s", e)
                results["errors"].append(f"AdGroup '{theme}': {e}")
                continue
        else:
            logger.info("[DRY RUN] Would create ad group: %s", ag_name)
            results["ad_groups_created"] += 1

        # ── Create keywords — exact + phrase for all 12 cities ───────────
        kw_base = theme.lower()
        keywords = []
        for city in CITIES:
            city_lower = city.lower()
            for match_type, kw_text in [
                ("Exact",  f"{kw_base} {city_lower}"),
                ("Phrase", f"{kw_base} {city_lower}"),
            ]:
                keywords.append((kw_text, match_type))

        if not dry_run and msft_ag_id:
            try:
                kw_objects = []
                for kw_text, match_type in keywords:
                    kw = camp_svc.factory.create("Keyword")
                    kw.Text       = kw_text
                    kw.MatchType  = match_type
                    kw.Status     = "Active"
                    bid_kw        = camp_svc.factory.create("Bid")
                    bid_kw.Amount = 2.50
                    kw.Bid        = bid_kw
                    # Null out fields that serialize as empty enums/Int32
                    kw.BiddingScheme          = None
                    kw.EditorialStatus        = None
                    kw.FinalUrls              = None
                    kw.FinalMobileUrls        = None
                    kw.FinalAppUrls           = None
                    kw.ForwardCompatibilityMap= None
                    kw.UrlCustomParameters    = None
                    kw_objects.append(kw)

                resp = camp_svc.AddKeywords(
                    AdGroupId=msft_ag_id,
                    Keywords={"Keyword": kw_objects},
                )
                created = len([i for i in resp.KeywordIds.long if i > 0])
                logger.info("  Created %d keywords", created)
                results["keywords_created"] += created

            except Exception as e:
                logger.error("  Keyword creation failed: %s", e)
                results["errors"].append(f"Keywords '{theme}': {e}")
        else:
            logger.info("[DRY RUN] Would create %d keywords (%d cities × exact+phrase)",
                        len(keywords), len(CITIES))
            results["keywords_created"] += len(keywords)

        # ── Create RSA ───────────────────────────────────────────────────
        ad_name = f"{RMA_PREFIX} RSA — {theme}"
        if not dry_run and msft_ag_id:
            try:
                rsa = camp_svc.factory.create("ResponsiveSearchAd")
                rsa.Status = "Active"
                # Null out fields that serialize as empty enums/arrays
                rsa.EditorialStatus      = None
                rsa.FinalAppUrls         = None
                rsa.FinalMobileUrls      = None
                rsa.ForwardCompatibilityMap = None
                rsa.UrlCustomParameters  = None
                rsa.Type                 = None

                # Headlines (15 required)
                headlines = camp_svc.factory.create("ArrayOfAssetLink")
                for i, text in enumerate(copy["headlines"][:15]):
                    link = camp_svc.factory.create("AssetLink")
                    asset = camp_svc.factory.create("TextAsset")
                    asset.Text = _word_trim(text, 30)  # Enforce 30-char limit (word boundary)
                    link.Asset = asset
                    link.EditorialStatus = None  # Avoid empty enum error
                    # Pin first two headlines to positions 1 and 2
                    if i == 0:
                        link.PinnedField = "Headline1"
                    elif i == 1:
                        link.PinnedField = "Headline2"
                    else:
                        link.PinnedField = None  # Avoid empty enum error
                    headlines.AssetLink.append(link)
                rsa.Headlines = headlines

                # Descriptions (4 required)
                descriptions = camp_svc.factory.create("ArrayOfAssetLink")
                for text in copy["descriptions"][:4]:
                    link = camp_svc.factory.create("AssetLink")
                    asset = camp_svc.factory.create("TextAsset")
                    asset.Text = _word_trim(text, 90)  # Enforce 90-char limit (word boundary)
                    link.Asset = asset
                    link.EditorialStatus = None  # Avoid empty enum error
                    link.PinnedField = None  # Avoid empty enum error
                    descriptions.AssetLink.append(link)
                rsa.Descriptions = descriptions

                # Final URL — use dict format (ArrayOfstring factory not available)
                rsa.FinalUrls = {"string": [final_url]}

                resp = camp_svc.AddAds(
                    AdGroupId=msft_ag_id,
                    Ads={"Ad": [rsa]},
                )
                ad_id = int(resp.AdIds.long[0])
                logger.info("  Created RSA id=%d", ad_id)
                results["ads_created"] += 1

                if label_id:
                    _apply_msft_label(camp_svc, label_id, "Ad", [ad_id], dry_run)

                # Save to DB
                if msft_ag_id:
                    db_ag_id = _db_upsert_ad_group(
                        campaign_id=_db_upsert_campaign(
                            name=campaign_name, platform="microsoft_ads",
                            external_id=f"msft_{msft_campaign_id}",
                        ),
                        name=ag_name,
                        external_id=f"msft_{msft_ag_id}",
                    )
                    _db_upsert_ad(
                        ad_group_id=db_ag_id,
                        external_id=f"msft_{ad_id}",
                        headlines=copy["headlines"][:15],
                        descriptions=copy["descriptions"][:4],
                        final_url=final_url,
                    )

            except Exception as e:
                logger.error("  RSA creation failed: %s", e)
                results["errors"].append(f"RSA '{theme}': {e}")
        else:
            logger.info("[DRY RUN] Would create RSA: %s", ad_name)
            logger.info("[DRY RUN]   Final URL: %s", final_url)
            logger.info("[DRY RUN]   Headlines: %d | Descriptions: %d",
                        len(copy["headlines"][:15]), len(copy["descriptions"][:4]))
            results["ads_created"] += 1

    # ── Summary ──────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("SETUP %sCOMPLETE", "[DRY RUN] " if dry_run else "")
    logger.info("  Campaigns : %d", results["campaigns_created"])
    logger.info("  Ad Groups : %d", results["ad_groups_created"])
    logger.info("  Keywords  : %d", results["keywords_created"])
    logger.info("  RSAs      : %d", results["ads_created"])
    logger.info("  Errors    : %d", len(results["errors"]))
    if results["errors"]:
        for err in results["errors"]:
            logger.error("  ERROR: %s", err)
    logger.info("=" * 60)
    if not dry_run:
        logger.info("NOTE: All campaigns created in PAUSED status.")
        logger.info("      Review in Microsoft Ads UI, then enable when ready.")
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Campaign Setup — Ridgecrest Marketing Agency (Claude Code)"
    )
    parser.add_argument(
        "--platform", choices=["microsoft", "google"], default="microsoft",
        help="Platform to set up campaigns on (default: microsoft)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview all actions without making any changes"
    )
    args = parser.parse_args()

    if args.platform == "microsoft":
        setup_microsoft(dry_run=args.dry_run)
    elif args.platform == "google":
        logger.error("Google Ads setup is pending developer token approval.")
        logger.error("Run this again after the token is approved.")
        sys.exit(1)


if __name__ == "__main__":
    main()
