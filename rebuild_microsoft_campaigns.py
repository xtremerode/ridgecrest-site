#!/usr/bin/env python3
"""
rebuild_microsoft_campaigns.py
================================
Restructures the Microsoft Ads account for Ridgecrest Designs.

WHAT THIS DOES
--------------
1.  Creates 5 consolidated Search campaigns (replaces 18 single-theme campaigns)
2.  Adds location targeting — 12 East Bay city criteria + PeopleIn intent
3.  Adds age bid adjustments (ICP: 35-50)
4.  Adds gender bid adjustments (female +10%)
5.  Creates one ad group per service theme inside each campaign
6.  Creates exact + phrase keywords (all 12 cities) per ad group
7.  Creates a Responsive Search Ad per ad group
8.  Creates account-level extensions: sitelinks, callouts, structured snippets, action
9.  Associates all extensions with every new campaign
10. Pauses all old single-theme [RMA] campaigns and marks them archived in DB

Day scheduling (Fri-Mon only) is handled by microsoft_manager.py pause/resume.
No DayTimeCriterion are set here.

RUN
---
    python rebuild_microsoft_campaigns.py --dry-run   # preview, no API writes
    python rebuild_microsoft_campaigns.py             # execute
"""

import argparse
import logging
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
import db
from campaign_setup import AD_COPY  # reuse carefully crafted ad copy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [rebuild_msft] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))
CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID", "")
DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
REDIRECT_URI  = "https://login.microsoftonline.com/common/oauth2/nativeclient"
PLATFORM      = "microsoft_ads"

LANDING_PAGE  = "https://go.ridgecrestdesigns.com"
KEYWORD_BID   = 8.00   # $8.00 floor per CLAUDE.md

# 12 East Bay target cities with verified Microsoft Ads location IDs
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
CITIES = list(MSFT_LOCATION_IDS.keys())

# Age bid adjustments — ICP: 35-50 (CLAUDE.md §3)
# NOTE: Microsoft WSDL spells "Fourty" not "Forty" — this is correct
MSFT_AGE_SPEC = [
    ("EighteenToTwentyFour",   -90),
    ("TwentyFiveToThirtyFour", -50),
    ("ThirtyFiveToFourtyNine", +10),
    ("FiftyToSixtyFour",         0),
    ("SixtyFiveAndAbove",       -30),
]

# Gender bid adjustments — female decision-maker bias (CLAUDE.md §18)
MSFT_GENDER_SPEC = [
    ("Female", +10),
    ("Male",     0),
]

# ── New 5-campaign structure ──────────────────────────────────────────────────
# Total daily budget: $70+$35+$55+$40+$50 = $250 (matches CLAUDE.md daily cap)
# Active days: Fri/Sat/Sun/Mon (enforced by microsoft_manager.py pause/resume)

NEW_CAMPAIGNS = [
    {
        "name":       "[RMA] Custom Home & Design Build | Ridgecrest Marketing",
        "budget_usd": 70.0,
        "themes": [
            "Custom Home Builder",
            "Custom Home",
            "Design Build",
            "Design Build Contractor",
        ],
    },
    {
        "name":       "[RMA] Whole House Remodel | Ridgecrest Marketing",
        "budget_usd": 35.0,
        "themes": ["Whole House Remodel"],
    },
    {
        "name":       "[RMA] Kitchen & Bathroom | Ridgecrest Marketing",
        "budget_usd": 55.0,
        "themes": [
            "Kitchen Remodel",
            "Kitchen Design",
            "Bathroom Remodel",
            "Bathroom Design",
            "Master Bathroom Remodel",
        ],
    },
    {
        "name":       "[RMA] Interior & Home Design | Ridgecrest Marketing",
        "budget_usd": 40.0,
        "themes": [
            "Interior Design",
            "Interior Design Firm",
            "Home Design",
        ],
    },
    {
        "name":       "[RMA] Contractors & Builders | Ridgecrest Marketing",
        "budget_usd": 50.0,
        "themes": [
            "Home Builder",
            "General Contractor",
            "Remodeling Contractor",
            "Home Renovation",
            "Architect",
        ],
    },
]

# ── Account-level extensions ──────────────────────────────────────────────────

SITELINKS = [
    {
        "title": "Custom Home Design",         # ≤25 chars
        "desc1": "Luxury custom homes from $5M",       # ≤35 chars
        "desc2": "Photo-realistic renders included",
        "url":   f"{LANDING_PAGE}?utm_content=sl_custom_home",
    },
    {
        "title": "Kitchen Remodel",
        "desc1": "Premium kitchen remodels from $150K",
        "desc2": "Design, permits & build in-house",
        "url":   f"{LANDING_PAGE}?utm_content=sl_kitchen",
    },
    {
        "title": "Whole House Remodel",
        "desc1": "Complete home renovations from $1M",
        "desc2": "Integrated design-build process",
        "url":   f"{LANDING_PAGE}?utm_content=sl_whole_house",
    },
    {
        "title": "Our Process",
        "desc1": "See how Ridgecrest works",
        "desc2": "From renders to move-in day",
        "url":   f"{LANDING_PAGE}?utm_content=sl_process",
    },
    {
        "title": "Request a Consultation",
        "desc1": "Submit your project inquiry",
        "desc2": "No-pressure, expert guidance",
        "url":   f"{LANDING_PAGE}?utm_content=sl_consult",
    },
    {
        "title": "Bathroom Remodel",
        "desc1": "Luxury bathroom remodels from $60K",
        "desc2": "Spa-quality design and build",
        "url":   f"{LANDING_PAGE}?utm_content=sl_bathroom",
    },
]

# Callout text ≤25 chars each
CALLOUT_TEXTS = [
    "Photo-Realistic Renders",
    "Integrated Design-Build",
    "Serving the East Bay",
    "Projects From $150K",
    "Expert Permitting Process",
    "Flawless Execution",
    "East Bay Specialists",
    "Licensed & Insured",
]

STRUCTURED_SNIPPET = {
    "header": "Services",   # must be from Microsoft's predefined list
    "values": [
        "Custom Homes",
        "Whole House Remodels",
        "Kitchen Remodels",
        "Bathroom Remodels",
        "Design-Build",
        "Interior Design",
    ],
}

ACTION_EXT = {
    "action_type": "GetAQuote",
    "url":         f"{LANDING_PAGE}?utm_content=action_getaquote",
}


# ── Auth ──────────────────────────────────────────────────────────────────────

def _refresh_token() -> tuple[str, int]:
    url  = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "client_id":     CLIENT_ID,
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "scope":         "https://ads.microsoft.com/msads.manage offline_access",
    }, timeout=30)
    resp.raise_for_status()
    td = resp.json()
    if "error" in td:
        raise RuntimeError(f"Token refresh failed: {td}")
    return td["access_token"], int(td.get("expires_in", 3600))


def _build_auth(access_token: str, expires_in: int):
    from bingads.authorization import (
        AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
    )
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
    from bingads import ServiceClient
    try:
        svc  = ServiceClient("CustomerManagementService", 13, auth, "production")
        resp = svc.GetUser(UserId=None)
        roles = (resp.CustomerRoles.CustomerRole
                 if resp.CustomerRoles and resp.CustomerRoles.CustomerRole else [])
        for role in roles:
            if hasattr(role, "CustomerId"):
                auth.customer_id = int(role.CustomerId)
                break
    except Exception as e:
        logger.warning("Could not resolve customer ID: %s", e)
    return auth


def _svc(auth):
    from bingads import ServiceClient
    return ServiceClient("CampaignManagementService", 13, auth, "production")


# ── DB helpers ────────────────────────────────────────────────────────────────

def _upsert_campaign_db(msft_id: int, name: str, budget_usd: float,
                         status: str = "ENABLED") -> int:
    external_id   = f"msft_{msft_id}"
    budget_micros = int(budget_usd * 1_000_000)
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO campaigns
               (google_campaign_id, name, status, platform,
                daily_budget_micros, managed_by, last_synced_at)
               VALUES (%s,%s,%s,%s,%s,'claude_code',NOW())
               ON CONFLICT (google_campaign_id) DO UPDATE SET
                   name               = EXCLUDED.name,
                   status             = EXCLUDED.status,
                   daily_budget_micros= EXCLUDED.daily_budget_micros,
                   managed_by         = 'claude_code',
                   last_synced_at     = NOW(),
                   updated_at         = NOW()
               RETURNING id""",
            (external_id, name, status, PLATFORM, budget_micros),
        )
        return cur.fetchone()["id"]


def _upsert_ag_db(camp_db_id: int, msft_ag_id: int, name: str) -> int:
    external_id = f"msft_ag_{msft_ag_id}"
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ad_groups
               (google_ad_group_id, campaign_id, name, status,
                cpc_bid_micros, updated_at)
               VALUES (%s,%s,%s,'ENABLED',%s,NOW())
               ON CONFLICT (google_ad_group_id) DO UPDATE SET
                   name           = EXCLUDED.name,
                   cpc_bid_micros = EXCLUDED.cpc_bid_micros,
                   updated_at     = NOW()
               RETURNING id""",
            (external_id, camp_db_id, name, int(KEYWORD_BID * 1_000_000)),
        )
        return cur.fetchone()["id"]


def _archive_old_campaign_db(external_id: str):
    """Mark old campaign as archived so manager and compliance skip it."""
    with db.get_db() as (conn, cur):
        cur.execute(
            """UPDATE campaigns
               SET status='PAUSED', managed_by='archived', updated_at=NOW()
               WHERE google_campaign_id=%s""",
            (external_id,),
        )


# ── Utility ───────────────────────────────────────────────────────────────────

def _word_trim(text: str, max_chars: int) -> str:
    """Trim text to max_chars at the nearest word boundary."""
    if len(text) <= max_chars:
        return text
    trimmed   = text[:max_chars]
    last_space = trimmed.rfind(" ")
    return trimmed[:last_space] if last_space > 0 else trimmed


# ── Campaign creation ─────────────────────────────────────────────────────────

def _create_campaign(svc, name: str, budget_usd: float, dry_run: bool) -> int | None:
    """Create a Search campaign with EnhancedCpc + DailyBudgetStandard. Returns msft_id."""
    if dry_run:
        logger.info("  [DRY RUN] Would create campaign: %s ($%.2f/day)", name, budget_usd)
        return None
    camp = svc.factory.create("Campaign")
    camp.Name             = name
    camp.CampaignType     = "Search"
    camp.Status           = "Paused"        # manager activates on active days
    camp.DailyBudget      = budget_usd
    camp.BudgetType       = "DailyBudgetStandard"
    camp.BiddingScheme    = svc.factory.create("EnhancedCpcBiddingScheme")
    camp.BidStrategyScope = "Account"
    camp.TimeZone         = "PacificTimeUSCanadaTijuana"
    camp.Languages        = {"string": ["English"]}
    # Null out complex fields to avoid empty-enum serialization errors
    camp.BudgetId                = None
    camp.StartDate               = None
    camp.EndDate                 = None
    camp.TrackingUrlTemplate     = None
    camp.UrlCustomParameters     = None
    camp.ForwardCompatibilityMap = None

    resp = svc.AddCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [camp]})
    msft_id = int(resp.CampaignIds.long[0])
    logger.info("  Created campaign id=%d  '%s'", msft_id, name)
    return msft_id


# ── Location criteria ─────────────────────────────────────────────────────────

def _add_location_criteria(svc, camp_id: int, dry_run: bool):
    """Add LocationCriterion for all 12 target cities + PeopleIn intent."""
    if dry_run:
        logger.info("    [DRY RUN] Would add %d location criteria + PeopleIn intent",
                    len(MSFT_LOCATION_IDS))
        return
    from suds import null as snull

    criterions = []

    # One BiddableCampaignCriterion per city
    for city, loc_id in MSFT_LOCATION_IDS.items():
        bcc = svc.factory.create("BiddableCampaignCriterion")
        bcc.CampaignId           = camp_id
        bcc.Id                   = None
        bcc.Type                 = snull()
        bcc.Status               = snull()
        bcc.CriterionCashback    = snull()
        bcc.ForwardCompatibilityMap = snull()
        bcc.BidMultiplier        = 0   # no adjustment — just targeting

        lc = svc.factory.create("LocationCriterion")
        lc.LocationId = loc_id
        lc.Type       = snull()
        bcc.Criterion = lc
        criterions.append(bcc)

    # LocationIntentCriterion = PeopleIn
    bcc_intent = svc.factory.create("BiddableCampaignCriterion")
    bcc_intent.CampaignId           = camp_id
    bcc_intent.Id                   = None
    bcc_intent.Type                 = snull()
    bcc_intent.Status               = snull()
    bcc_intent.CriterionCashback    = snull()
    bcc_intent.ForwardCompatibilityMap = snull()
    lic = svc.factory.create("LocationIntentCriterion")
    lic.IntentOption = "PeopleIn"
    lic.Type         = snull()
    bcc_intent.Criterion = lic
    criterions.append(bcc_intent)

    try:
        svc.AddCampaignCriterions(
            CampaignCriterions={"CampaignCriterion": criterions},
            CriterionType="Targets",
        )
        logger.info("    Added %d city criteria + PeopleIn for campaign %d",
                    len(MSFT_LOCATION_IDS), camp_id)
    except Exception as e:
        logger.error("    Location criteria failed for campaign %d: %s", camp_id, e)


# ── Age / gender criteria ─────────────────────────────────────────────────────

def _add_age_criteria(svc, camp_id: int, dry_run: bool):
    if dry_run:
        logger.info("    [DRY RUN] Would add age bid criteria")
        return
    from suds import null as snull
    criterions = []
    for age_range, pct in MSFT_AGE_SPEC:
        bcc = svc.factory.create("BiddableCampaignCriterion")
        bcc.CampaignId              = camp_id
        bcc.Id                      = None
        bcc.Type                    = snull()
        bcc.Status                  = snull()
        bcc.CriterionCashback       = snull()
        bcc.ForwardCompatibilityMap = snull()
        bcc.BidMultiplier           = pct
        ac = svc.factory.create("AgeCriterion")
        ac.AgeRange = age_range
        ac.Type     = snull()
        bcc.Criterion = ac
        criterions.append(bcc)
    try:
        svc.AddCampaignCriterions(
            CampaignCriterions={"CampaignCriterion": criterions},
            CriterionType="Targets",
        )
        logger.info("    Added %d age criteria for campaign %d", len(criterions), camp_id)
    except Exception as e:
        logger.error("    Age criteria failed for campaign %d: %s", camp_id, e)


def _add_gender_criteria(svc, camp_id: int, dry_run: bool):
    if dry_run:
        logger.info("    [DRY RUN] Would add gender bid criteria")
        return
    from suds import null as snull
    criterions = []
    for gender, pct in MSFT_GENDER_SPEC:
        bcc = svc.factory.create("BiddableCampaignCriterion")
        bcc.CampaignId              = camp_id
        bcc.Id                      = None
        bcc.Type                    = snull()
        bcc.Status                  = snull()
        bcc.CriterionCashback       = snull()
        bcc.ForwardCompatibilityMap = snull()
        bcc.BidMultiplier           = pct
        gc = svc.factory.create("GenderCriterion")
        gc.GenderType = gender
        gc.Type       = snull()
        bcc.Criterion = gc
        criterions.append(bcc)
    try:
        svc.AddCampaignCriterions(
            CampaignCriterions={"CampaignCriterion": criterions},
            CriterionType="Targets",
        )
        logger.info("    Added %d gender criteria for campaign %d", len(criterions), camp_id)
    except Exception as e:
        logger.error("    Gender criteria failed for campaign %d: %s", camp_id, e)


# ── Ad group ──────────────────────────────────────────────────────────────────

def _create_ad_group(svc, camp_id: int, theme: str, dry_run: bool) -> int | None:
    if dry_run:
        logger.info("    [DRY RUN] Would create ad group: %s", theme)
        return None
    ag = svc.factory.create("AdGroup")
    ag.Name          = f"[RMA] {theme}"
    ag.Status        = "Active"
    ag.CpcBid        = svc.factory.create("Bid")
    ag.CpcBid.Amount = KEYWORD_BID
    ag.Language      = "English"
    rot              = svc.factory.create("AdRotation")
    rot.Type         = "OptimizeForClicks"
    ag.AdRotation    = rot
    ag.Network       = "OwnedAndOperatedAndSyndicatedSearch"
    ag.BiddingScheme = svc.factory.create("InheritFromParentBiddingScheme")
    # Null out fields that cause empty-enum errors
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

    resp = svc.AddAdGroups(CampaignId=camp_id, AdGroups={"AdGroup": [ag]})
    ag_id = int(resp.AdGroupIds.long[0])
    logger.info("    Created ad group id=%d  '%s'", ag_id, theme)
    return ag_id


# ── Keywords ──────────────────────────────────────────────────────────────────

def _create_keywords(svc, ag_id: int, theme: str, dry_run: bool) -> int:
    """Create exact + phrase keyword for each city. Returns count created."""
    kw_base = theme.lower()
    kw_objects = []
    for city in CITIES:
        city_lower = city.lower()
        for match_type, kw_text in [
            ("Exact",  f"{kw_base} {city_lower}"),
            ("Phrase", f"{kw_base} {city_lower}"),
        ]:
            kw = svc.factory.create("Keyword")
            kw.Text      = kw_text
            kw.MatchType = match_type
            kw.Status    = "Active"
            bid          = svc.factory.create("Bid")
            bid.Amount   = KEYWORD_BID
            kw.Bid       = bid
            kw.BiddingScheme           = None
            kw.EditorialStatus         = None
            kw.FinalUrls               = None
            kw.FinalMobileUrls         = None
            kw.FinalAppUrls            = None
            kw.ForwardCompatibilityMap = None
            kw.UrlCustomParameters     = None
            kw_objects.append(kw)

    if dry_run:
        logger.info("    [DRY RUN] Would create %d keywords for '%s'",
                    len(kw_objects), theme)
        return len(kw_objects)

    resp = svc.AddKeywords(AdGroupId=ag_id, Keywords={"Keyword": kw_objects})
    created = len([i for i in resp.KeywordIds.long if i and i > 0])
    logger.info("    Created %d keywords for '%s'", created, theme)
    return created


# ── RSA ───────────────────────────────────────────────────────────────────────

def _create_rsa(svc, ag_id: int, theme: str, dry_run: bool) -> int | None:
    """Create a Responsive Search Ad using AD_COPY for this theme."""
    copy      = AD_COPY.get(theme, AD_COPY["Design Build"])
    slug      = theme.lower().replace(" ", "-")
    final_url = (f"{LANDING_PAGE}?utm_source=microsoft&utm_medium=cpc"
                 f"&utm_campaign=rma-{slug}&utm_content=claude_code_rma")

    if dry_run:
        logger.info("    [DRY RUN] Would create RSA for '%s'  url=%s", theme, final_url)
        return None

    rsa = svc.factory.create("ResponsiveSearchAd")
    rsa.Status              = "Active"
    rsa.EditorialStatus     = None
    rsa.FinalAppUrls        = None
    rsa.FinalMobileUrls     = None
    rsa.ForwardCompatibilityMap = None
    rsa.UrlCustomParameters = None
    rsa.Type                = None
    rsa.FinalUrls           = {"string": [final_url]}

    headlines = svc.factory.create("ArrayOfAssetLink")
    for i, text in enumerate(copy["headlines"][:15]):
        link  = svc.factory.create("AssetLink")
        asset = svc.factory.create("TextAsset")
        asset.Text       = _word_trim(text, 30)
        link.Asset       = asset
        link.EditorialStatus = None
        # Pin the first two headlines so the brand name and primary
        # service always appear in positions 1 and 2
        if i == 0:
            link.PinnedField = "Headline1"
        elif i == 1:
            link.PinnedField = "Headline2"
        else:
            link.PinnedField = None
        headlines.AssetLink.append(link)
    rsa.Headlines = headlines

    descriptions = svc.factory.create("ArrayOfAssetLink")
    for text in copy["descriptions"][:4]:
        link  = svc.factory.create("AssetLink")
        asset = svc.factory.create("TextAsset")
        asset.Text           = _word_trim(text, 90)
        link.Asset           = asset
        link.EditorialStatus = None
        link.PinnedField     = None
        descriptions.AssetLink.append(link)
    rsa.Descriptions = descriptions

    resp  = svc.AddAds(AdGroupId=ag_id, Ads={"Ad": [rsa]})
    ad_id = int(resp.AdIds.long[0])
    logger.info("    Created RSA id=%d for '%s'", ad_id, theme)
    return ad_id


# ── Extensions ────────────────────────────────────────────────────────────────

def _create_sitelinks(svc, dry_run: bool) -> list[int]:
    """Create account-level SitelinkAdExtension objects. Returns list of IDs."""
    if dry_run:
        logger.info("  [DRY RUN] Would create %d sitelinks", len(SITELINKS))
        return []
    from suds import null as snull
    ext_objects = []
    for sl in SITELINKS:
        ext = svc.factory.create("SitelinkAdExtension")
        ext.SitelinkText = _word_trim(sl["title"], 25)
        ext.Description1 = _word_trim(sl["desc1"], 35)
        ext.Description2 = _word_trim(sl["desc2"], 35)
        ext.FinalUrls    = {"string": [sl["url"]]}
        ext.Status       = "Active"
        ext.DevicePreference         = None
        ext.FinalMobileUrls          = None
        ext.FinalAppUrls             = None
        ext.TrackingUrlTemplate      = None
        ext.UrlCustomParameters      = None
        ext.ForwardCompatibilityMap  = snull()
        ext_objects.append(ext)

    resp = svc.AddAdExtensions(
        AccountId=ACCOUNT_ID,
        AdExtensions={"AdExtension": ext_objects},
    )
    ids = []
    for item in (resp.AdExtensionIdentities.AdExtensionIdentity or []):
        if hasattr(item, "Id") and item.Id:
            ids.append(int(item.Id))
    logger.info("  Created %d sitelinks: %s", len(ids), ids)
    return ids


def _create_callouts(svc, dry_run: bool) -> list[int]:
    """Create account-level CalloutAdExtension objects. Returns list of IDs."""
    if dry_run:
        logger.info("  [DRY RUN] Would create %d callouts", len(CALLOUT_TEXTS))
        return []
    from suds import null as snull
    ext_objects = []
    for text in CALLOUT_TEXTS:
        ext = svc.factory.create("CalloutAdExtension")
        ext.Text   = _word_trim(text, 25)
        ext.Status = "Active"
        ext.ForwardCompatibilityMap = snull()
        ext_objects.append(ext)

    resp = svc.AddAdExtensions(
        AccountId=ACCOUNT_ID,
        AdExtensions={"AdExtension": ext_objects},
    )
    ids = []
    for item in (resp.AdExtensionIdentities.AdExtensionIdentity or []):
        if hasattr(item, "Id") and item.Id:
            ids.append(int(item.Id))
    logger.info("  Created %d callouts: %s", len(ids), ids)
    return ids


def _create_structured_snippets(svc, dry_run: bool) -> list[int]:
    """Create one StructuredSnippetAdExtension. Returns list with one ID."""
    if dry_run:
        logger.info("  [DRY RUN] Would create structured snippet")
        return []
    from suds import null as snull
    ext = svc.factory.create("StructuredSnippetAdExtension")
    ext.Header = STRUCTURED_SNIPPET["header"]
    ext.Values = {"string": [_word_trim(v, 25) for v in STRUCTURED_SNIPPET["values"]]}
    ext.Status = "Active"
    ext.ForwardCompatibilityMap = snull()

    resp = svc.AddAdExtensions(
        AccountId=ACCOUNT_ID,
        AdExtensions={"AdExtension": [ext]},
    )
    ids = []
    for item in (resp.AdExtensionIdentities.AdExtensionIdentity or []):
        if hasattr(item, "Id") and item.Id:
            ids.append(int(item.Id))
    logger.info("  Created structured snippet: %s", ids)
    return ids


def _create_action_extension(svc, dry_run: bool) -> list[int]:
    """Create one ActionAdExtension. Returns list with one ID."""
    if dry_run:
        logger.info("  [DRY RUN] Would create action extension (%s)",
                    ACTION_EXT["action_type"])
        return []
    from suds import null as snull
    ext = svc.factory.create("ActionAdExtension")
    ext.ActionType = ACTION_EXT["action_type"]
    ext.FinalUrls  = {"string": [ACTION_EXT["url"]]}
    ext.Status     = "Active"
    ext.ForwardCompatibilityMap = snull()

    try:
        resp = svc.AddAdExtensions(
            AccountId=ACCOUNT_ID,
            AdExtensions={"AdExtension": [ext]},
        )
        ids = []
        for item in (resp.AdExtensionIdentities.AdExtensionIdentity or []):
            if hasattr(item, "Id") and item.Id:
                ids.append(int(item.Id))
        logger.info("  Created action extension: %s", ids)
        return ids
    except Exception as e:
        # ActionAdExtension may not be available on all account tiers
        logger.warning("  Action extension creation failed (may not be available): %s", e)
        return []


def _associate_extensions(svc, camp_ids: list[int],
                           ext_ids: list[int], ext_type: str,
                           dry_run: bool):
    """Associate a list of extensions with a list of campaigns."""
    if dry_run or not ext_ids or not camp_ids:
        if dry_run:
            logger.info("  [DRY RUN] Would associate %d %s with %d campaigns",
                        len(ext_ids), ext_type, len(camp_ids))
        return
    assocs = []
    for ext_id in ext_ids:
        for camp_id in camp_ids:
            a = svc.factory.create("AdExtensionIdToEntityIdAssociation")
            a.AdExtensionId = ext_id
            a.EntityId      = camp_id
            assocs.append(a)
    try:
        svc.SetAdExtensionsAssociations(
            AccountId=ACCOUNT_ID,
            AdExtensionIdToEntityIdAssociations={
                "AdExtensionIdToEntityIdAssociation": assocs
            },
            AssociationType="Campaign",
            AdExtensionType=ext_type,
        )
        logger.info("  Associated %d %s with %d campaigns",
                    len(ext_ids), ext_type, len(camp_ids))
    except Exception as e:
        logger.error("  Association failed for %s: %s", ext_type, e)


# ── Old campaign cleanup ───────────────────────────────────────────────────────

def _get_existing_campaign_names(svc) -> dict[str, int]:
    """Return {name: msft_id} for all existing [RMA] campaigns in the account."""
    try:
        resp = svc.GetCampaignsByAccountId(AccountId=ACCOUNT_ID, CampaignType="Search")
        raw  = (list(resp.Campaign.Campaign)
                if resp.Campaign and hasattr(resp.Campaign, "Campaign")
                else list(resp.Campaign or []))
    except Exception as e:
        logger.error("Could not fetch existing campaigns: %s", e)
        return {}
    return {
        str(c.Name): int(c.Id)
        for c in raw
        if hasattr(c, "Id") and c.Id and hasattr(c, "Name") and c.Name
        and str(c.Name).startswith("[RMA]")
    }


def _get_old_rma_campaigns(svc, new_camp_names: set[str]) -> list[dict]:
    """Return all existing [RMA] campaigns that are NOT in new_camp_names."""
    try:
        resp = svc.GetCampaignsByAccountId(AccountId=ACCOUNT_ID, CampaignType="Search")
        raw  = (list(resp.Campaign.Campaign)
                if resp.Campaign and hasattr(resp.Campaign, "Campaign")
                else list(resp.Campaign or []))
    except Exception as e:
        logger.error("Could not fetch existing campaigns: %s", e)
        return []

    results = []
    for c in raw:
        if not hasattr(c, "Id") or c.Id is None:
            continue
        name = str(c.Name) if hasattr(c, "Name") and c.Name else ""
        if not name.startswith("[RMA]"):
            continue
        if name in new_camp_names:
            continue   # this old campaign shares a name with a new one — handled separately
        results.append({
            "msft_id":     int(c.Id),
            "name":        name,
            "external_id": f"msft_{c.Id}",
        })
    return results


def _pause_and_archive_old_campaigns(svc, new_camp_names: set[str], dry_run: bool):
    """Pause all old single-theme [RMA] campaigns and mark them archived in DB."""
    old_camps = _get_old_rma_campaigns(svc, new_camp_names)
    if not old_camps:
        logger.info("No old campaigns to archive.")
        return

    logger.info("Archiving %d old campaign(s)...", len(old_camps))
    for camp in old_camps:
        if dry_run:
            logger.info("  [DRY RUN] Would pause and archive: %s", camp["name"])
            continue
        try:
            c = svc.factory.create("Campaign")
            c.Id             = camp["msft_id"]
            c.Status         = "Paused"
            c.BidStrategyScope = "Account"
            c.BudgetType     = "DailyBudgetStandard"
            c.BiddingScheme  = svc.factory.create("EnhancedCpcBiddingScheme")
            svc.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c]})
            _archive_old_campaign_db(camp["external_id"])
            logger.info("  Paused + archived: %s", camp["name"])
        except Exception as e:
            logger.warning("  Failed to pause %s: %s", camp["name"], e)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False):
    label = "[DRY RUN] " if dry_run else ""
    logger.info("=== Microsoft Ads Campaign Rebuild %s===", label)

    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    s    = _svc(auth)

    totals = {
        "campaigns":  0,
        "ad_groups":  0,
        "keywords":   0,
        "rsas":       0,
        "extensions": 0,
        "archived":   0,
        "errors":     [],
    }

    new_camp_msft_ids: list[int] = []
    new_camp_names = {spec["name"] for spec in NEW_CAMPAIGNS}

    # ─── Phase 0: Fetch existing campaign names to detect conflicts ───────────
    logger.info("=== Phase 0: Checking for existing campaign name conflicts ===")
    existing_names = _get_existing_campaign_names(s)
    conflicts = {name: cid for name, cid in existing_names.items()
                 if name in new_camp_names}
    if conflicts:
        logger.info("  Found %d name conflict(s) with new campaigns: %s",
                    len(conflicts), list(conflicts.keys()))
        # Archive conflicting old campaigns first so we can reuse their names
        logger.info("  Archiving conflicting campaigns before creating new ones...")
        for name, msft_id in conflicts.items():
            if dry_run:
                logger.info("  [DRY RUN] Would archive conflicting: %s", name)
                continue
            try:
                c = s.factory.create("Campaign")
                c.Id             = msft_id
                c.Status         = "Paused"
                c.BidStrategyScope = "Account"
                c.BudgetType     = "DailyBudgetStandard"
                c.BiddingScheme  = s.factory.create("EnhancedCpcBiddingScheme")
                s.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c]})
                _archive_old_campaign_db(f"msft_{msft_id}")
                logger.info("  Archived conflicting campaign: %s (id=%d)", name, msft_id)
            except Exception as e:
                logger.warning("  Could not archive conflicting campaign %s: %s", name, e)

    # ─── Phase 1: Build 5 new campaigns ──────────────────────────────────────
    logger.info("=== Phase 1: Creating %d consolidated campaigns ===", len(NEW_CAMPAIGNS))
    for camp_spec in NEW_CAMPAIGNS:
        camp_name   = camp_spec["name"]
        budget_usd  = camp_spec["budget_usd"]
        themes      = camp_spec["themes"]

        logger.info("--- Campaign: %s ($%.0f/day, %d themes) ---",
                    camp_name, budget_usd, len(themes))

        # Create campaign
        try:
            msft_camp_id = _create_campaign(s, camp_name, budget_usd, dry_run)
        except Exception as e:
            logger.error("Campaign creation failed: %s", e)
            totals["errors"].append(f"create_campaign '{camp_name}': {e}")
            continue

        if msft_camp_id:
            totals["campaigns"] += 1
            new_camp_msft_ids.append(msft_camp_id)
            camp_db_id = _upsert_campaign_db(msft_camp_id, camp_name, budget_usd)

            # Add location + intent criteria
            _add_location_criteria(s, msft_camp_id, dry_run)
            # Add age + gender criteria
            _add_age_criteria(s, msft_camp_id, dry_run)
            _add_gender_criteria(s, msft_camp_id, dry_run)
        else:
            camp_db_id = None  # dry run

        # Create ad groups + keywords + RSAs for each theme
        for theme in themes:
            logger.info("  Theme: %s", theme)
            try:
                ag_id = _create_ad_group(s, msft_camp_id or 0, theme, dry_run)
            except Exception as e:
                logger.error("  Ad group failed '%s': %s", theme, e)
                totals["errors"].append(f"ad_group '{theme}': {e}")
                continue

            totals["ad_groups"] += 1

            if ag_id and camp_db_id:
                _upsert_ag_db(camp_db_id, ag_id, f"[RMA] {theme}")

            try:
                kw_count = _create_keywords(s, ag_id or 0, theme, dry_run)
                totals["keywords"] += kw_count
            except Exception as e:
                logger.error("  Keywords failed '%s': %s", theme, e)
                totals["errors"].append(f"keywords '{theme}': {e}")

            try:
                rsa_id = _create_rsa(s, ag_id or 0, theme, dry_run)
                if rsa_id or dry_run:
                    totals["rsas"] += 1
            except Exception as e:
                logger.error("  RSA failed '%s': %s", theme, e)
                totals["errors"].append(f"rsa '{theme}': {e}")

    # ─── Phase 2: Create and associate extensions ─────────────────────────────
    logger.info("=== Phase 2: Creating account-level extensions ===")

    try:
        sitelink_ids = _create_sitelinks(s, dry_run)
    except Exception as e:
        logger.error("Sitelink creation failed: %s", e)
        sitelink_ids = []

    try:
        callout_ids = _create_callouts(s, dry_run)
    except Exception as e:
        logger.error("Callout creation failed: %s", e)
        callout_ids = []

    try:
        snippet_ids = _create_structured_snippets(s, dry_run)
    except Exception as e:
        logger.error("Structured snippet creation failed: %s", e)
        snippet_ids = []

    try:
        action_ids = _create_action_extension(s, dry_run)
    except Exception as e:
        logger.error("Action extension creation failed: %s", e)
        action_ids = []

    totals["extensions"] = (len(sitelink_ids) + len(callout_ids) +
                             len(snippet_ids)  + len(action_ids))

    if new_camp_msft_ids:
        logger.info("Associating extensions with %d campaigns...", len(new_camp_msft_ids))
        _associate_extensions(s, new_camp_msft_ids, sitelink_ids,
                               "SitelinkAdExtension",          dry_run)
        _associate_extensions(s, new_camp_msft_ids, callout_ids,
                               "CalloutAdExtension",           dry_run)
        _associate_extensions(s, new_camp_msft_ids, snippet_ids,
                               "StructuredSnippetAdExtension", dry_run)
        _associate_extensions(s, new_camp_msft_ids, action_ids,
                               "ActionAdExtension",            dry_run)

    # ─── Phase 3: Pause and archive old campaigns ─────────────────────────────
    logger.info("=== Phase 3: Archiving old single-theme campaigns ===")
    try:
        _pause_and_archive_old_campaigns(s, new_camp_names, dry_run)
    except Exception as e:
        logger.error("Archive step failed: %s", e)
        totals["errors"].append(f"archive: {e}")

    # ─── Summary ──────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("REBUILD %sCOMPLETE", label)
    logger.info("  Campaigns : %d", totals["campaigns"])
    logger.info("  Ad Groups : %d", totals["ad_groups"])
    logger.info("  Keywords  : %d", totals["keywords"])
    logger.info("  RSAs      : %d", totals["rsas"])
    logger.info("  Extensions: %d", totals["extensions"])
    if totals["errors"]:
        logger.warning("  Errors    : %d", len(totals["errors"]))
        for err in totals["errors"]:
            logger.warning("    - %s", err)
    logger.info("=" * 60)
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rebuild Microsoft Ads campaign structure for Ridgecrest Designs"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all actions without making API calls")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
