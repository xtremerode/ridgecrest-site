#!/usr/bin/env python3
"""
patch_microsoft_campaigns.py
============================
Patches the Microsoft Ads account WITHOUT re-running the full rebuild.

The rebuild_microsoft_campaigns.py was already run once and created 4 of the
5 consolidated campaigns. Re-running rebuild would archive those 4 campaigns
(Phase 0 conflict detection) and then fail to create replacements (Microsoft
does not allow two campaigns — even one Paused — to share the same name).

This script does only what remains:

  1. Fix budgets on 4 existing campaigns ($10/day → target amounts)
  2. Repurpose old [RMA] Whole House Remodel campaign (msft_524025244)
       → update budget $7 → $35/day, un-archive in DB, create new ad group
  3. Ensure location / age / gender criteria exist on all 5 campaigns
  4. Create keywords (exact + phrase, all 12 cities) for every ad group
  5. Create one RSA per ad group
  6. Create account-level extensions (sitelinks, callouts, structured snippet,
     action) and associate them with all 5 campaigns
  7. Verify bid strategy is EnhancedCpc on all 5 campaigns

Run:
    python patch_microsoft_campaigns.py --dry-run  # preview, no API writes
    python patch_microsoft_campaigns.py            # execute
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
from campaign_setup import AD_COPY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [patch_msft] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Credentials ───────────────────────────────────────────────────────────────

ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))
CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID", "")
DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
REDIRECT_URI  = "https://login.microsoftonline.com/common/oauth2/nativeclient"

LANDING_PAGE = "https://go.ridgecrestdesigns.com"
KEYWORD_BID  = 8.00   # $8.00 floor

# ── Campaign map (from DB after first rebuild run) ────────────────────────────

# 4 existing new campaigns: {msft_id: (name, correct_budget_usd)}
EXISTING_CAMPAIGNS = {
    524039521: ("[RMA] Custom Home & Design Build | Ridgecrest Marketing",   70.0),
    524039522: ("[RMA] Kitchen & Bathroom | Ridgecrest Marketing",           55.0),
    524039523: ("[RMA] Interior & Home Design | Ridgecrest Marketing",       40.0),
    524039524: ("[RMA] Contractors & Builders | Ridgecrest Marketing",       50.0),
}

# Old Whole House Remodel campaign to repurpose
WHR_MSFT_ID  = 524025244
WHR_NAME     = "[RMA] Whole House Remodel | Ridgecrest Marketing"
WHR_BUDGET   = 35.0
WHR_THEME    = "Whole House Remodel"

# All 5 campaigns once setup is complete (msft_id → name)
ALL_CAMP_IDS = list(EXISTING_CAMPAIGNS.keys()) + [WHR_MSFT_ID]

# ── Targeting spec ────────────────────────────────────────────────────────────

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

# NOTE: Microsoft WSDL spells "Fourty" not "Forty" — this is correct
MSFT_AGE_SPEC = [
    ("EighteenToTwentyFour",   -90),
    ("TwentyFiveToThirtyFour", -50),
    ("ThirtyFiveToFourtyNine", +10),
    ("FiftyToSixtyFour",         0),
    ("SixtyFiveAndAbove",       -30),
]

MSFT_GENDER_SPEC = [
    ("Female", +10),
    ("Male",     0),
]

# ── Extensions ────────────────────────────────────────────────────────────────

SITELINKS = [
    {
        "title": "Custom Home Design",
        "desc1": "Luxury custom homes from $5M",
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
    "header": "Services",
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
    "action_type": "GetQuote",   # valid ActionAdExtensionActionType enum value
    "url":         f"{LANDING_PAGE}?utm_content=action_getquote",
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
        logger.warning("Could not resolve customer_id: %s", e)
    return auth


def _svc(auth):
    from bingads import ServiceClient
    return ServiceClient("CampaignManagementService", 13, auth, "production")


# ── Utility ───────────────────────────────────────────────────────────────────

def _word_trim(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed    = text[:max_chars]
    last_space = trimmed.rfind(" ")
    return trimmed[:last_space] if last_space > 0 else trimmed


# ── Step 1: Fix campaign budgets ──────────────────────────────────────────────

def fix_campaign_budgets(svc, dry_run: bool) -> int:
    """Update daily budget on the 4 existing new campaigns to correct amounts."""
    from suds import null as snull
    logger.info("=== Step 1: Fixing campaign budgets ===")
    fixed = 0
    for msft_id, (name, budget_usd) in EXISTING_CAMPAIGNS.items():
        if dry_run:
            logger.info("  [DRY RUN] Would set %s → $%.0f/day", name, budget_usd)
            fixed += 1
            continue
        try:
            c = svc.factory.create("Campaign")
            c.Id               = msft_id
            c.DailyBudget      = budget_usd
            c.BudgetType       = "DailyBudgetStandard"
            c.BiddingScheme    = svc.factory.create("EnhancedCpcBiddingScheme")
            c.BidStrategyScope = "Account"
            # Must set Status explicitly; empty-string enum causes API error
            c.Status           = "Paused"
            # Null out fields we're not changing to avoid serialization errors
            c.Name                   = snull()
            c.CampaignType           = snull()
            c.StartDate              = snull()
            c.EndDate                = snull()
            c.TrackingUrlTemplate    = snull()
            c.UrlCustomParameters    = snull()
            c.ForwardCompatibilityMap = snull()
            svc.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c]})
            # Update DB
            with db.get_db() as (conn, cur):
                cur.execute(
                    "UPDATE campaigns SET daily_budget_micros=%s, updated_at=NOW() "
                    "WHERE google_campaign_id=%s",
                    (int(budget_usd * 1_000_000), f"msft_{msft_id}"),
                )
            logger.info("  Fixed budget: %s → $%.0f/day", name, budget_usd)
            fixed += 1
        except Exception as e:
            logger.error("  Budget fix failed for %s: %s", name, e)
    return fixed


# ── Step 2: Repurpose old Whole House Remodel campaign ────────────────────────

def repurpose_whole_house_remodel(svc, dry_run: bool) -> int | None:
    """
    Update old WHR campaign budget to $35/day and un-archive it in DB.
    Returns the Microsoft ad group ID for WHR (creates one if needed).
    """
    logger.info("=== Step 2: Repurposing Whole House Remodel campaign ===")

    if dry_run:
        logger.info("  [DRY RUN] Would update msft_%d → $%.0f/day, un-archive in DB",
                    WHR_MSFT_ID, WHR_BUDGET)
        logger.info("  [DRY RUN] Would ensure ad group '[RMA] %s' exists", WHR_THEME)
        return None

    # Update campaign budget + ensure EnhancedCpc
    try:
        c = svc.factory.create("Campaign")
        c.Id              = WHR_MSFT_ID
        c.DailyBudget     = WHR_BUDGET
        c.BudgetType      = "DailyBudgetStandard"
        c.BiddingScheme   = svc.factory.create("EnhancedCpcBiddingScheme")
        c.BidStrategyScope = "Account"
        c.Status          = "Paused"  # manager activates on active days
        svc.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c]})
        logger.info("  Updated WHR campaign budget → $%.0f/day", WHR_BUDGET)
    except Exception as e:
        logger.error("  WHR campaign update failed: %s", e)

    # Un-archive in DB
    with db.get_db() as (conn, cur):
        cur.execute(
            """UPDATE campaigns
               SET status='PAUSED', managed_by='claude_code',
                   daily_budget_micros=%s, updated_at=NOW()
               WHERE google_campaign_id=%s""",
            (int(WHR_BUDGET * 1_000_000), f"msft_{WHR_MSFT_ID}"),
        )
        # Get db id
        cur.execute(
            "SELECT id FROM campaigns WHERE google_campaign_id=%s",
            (f"msft_{WHR_MSFT_ID}",),
        )
        row = cur.fetchone()
        whr_camp_db_id = row["id"] if row else None

    logger.info("  WHR campaign un-archived in DB (db_id=%s)", whr_camp_db_id)

    # Check if an ad group already exists for WHR theme
    whr_ag_msft_id = None
    try:
        resp = svc.GetAdGroupsByCampaignId(CampaignId=WHR_MSFT_ID)
        existing_ags = (list(resp.AdGroup.AdGroup)
                        if resp.AdGroup and hasattr(resp.AdGroup, "AdGroup")
                        else list(resp.AdGroup or []))
        theme_ag = next(
            (ag for ag in existing_ags
             if hasattr(ag, "Name") and ag.Name and
             WHR_THEME.lower() in str(ag.Name).lower()),
            None,
        )
        if theme_ag:
            whr_ag_msft_id = int(theme_ag.Id)
            logger.info("  Existing WHR ad group found: id=%d name=%s",
                        whr_ag_msft_id, theme_ag.Name)
    except Exception as e:
        logger.warning("  Could not fetch WHR ad groups: %s", e)

    if whr_ag_msft_id is None:
        # Create the ad group
        try:
            ag = svc.factory.create("AdGroup")
            ag.Name          = f"[RMA] {WHR_THEME}"
            ag.Status        = "Active"
            ag.CpcBid        = svc.factory.create("Bid")
            ag.CpcBid.Amount = KEYWORD_BID
            ag.Language      = "English"
            rot              = svc.factory.create("AdRotation")
            rot.Type         = "OptimizeForClicks"
            ag.AdRotation    = rot
            ag.Network       = "OwnedAndOperatedAndSyndicatedSearch"
            ag.BiddingScheme = svc.factory.create("InheritFromParentBiddingScheme")
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

            resp = svc.AddAdGroups(
                CampaignId=WHR_MSFT_ID, AdGroups={"AdGroup": [ag]}
            )
            whr_ag_msft_id = int(resp.AdGroupIds.long[0])
            logger.info("  Created WHR ad group: id=%d", whr_ag_msft_id)
        except Exception as e:
            logger.error("  WHR ad group creation failed: %s", e)
            return None

    # Upsert in DB
    if whr_camp_db_id and whr_ag_msft_id:
        with db.get_db() as (conn, cur):
            cur.execute(
                """INSERT INTO ad_groups
                   (google_ad_group_id, campaign_id, name, status,
                    cpc_bid_micros, updated_at)
                   VALUES (%s, %s, %s, 'ENABLED', %s, NOW())
                   ON CONFLICT (google_ad_group_id) DO UPDATE SET
                       name           = EXCLUDED.name,
                       cpc_bid_micros = EXCLUDED.cpc_bid_micros,
                       updated_at     = NOW()""",
                (f"msft_ag_{whr_ag_msft_id}", whr_camp_db_id,
                 f"[RMA] {WHR_THEME}", int(KEYWORD_BID * 1_000_000)),
            )
        logger.info("  WHR ad group upserted in DB")

    return whr_ag_msft_id


# ── Step 3: Add location / age / gender criteria ──────────────────────────────

def _criteria_exist(svc, camp_id: int, criterion_type: str) -> bool:
    """Check if a campaign already has criteria of the given type."""
    try:
        resp = svc.GetCampaignCriterionsByIds(
            CampaignId=camp_id,
            CriterionType=criterion_type,
            CampaignCriterionIds=None,
        )
        items = (list(resp.CampaignCriterion.CampaignCriterion)
                 if resp.CampaignCriterion and
                 hasattr(resp.CampaignCriterion, "CampaignCriterion")
                 else [])
        return len(items) > 0
    except Exception:
        return False  # assume absent; add them


def ensure_campaign_criteria(svc, camp_ids: list[int], dry_run: bool) -> None:
    """Add location / age / gender criteria to campaigns that are missing them."""
    from suds import null as snull
    logger.info("=== Step 3: Ensuring location / age / gender criteria ===")

    for camp_id in camp_ids:
        logger.info("  Campaign %d", camp_id)

        # ── Location ──────────────────────────────────────────────────────────
        if dry_run:
            logger.info("    [DRY RUN] Would add %d city criteria + PeopleIn",
                        len(MSFT_LOCATION_IDS))
        else:
            try:
                criterions = []
                for city, loc_id in MSFT_LOCATION_IDS.items():
                    bcc = svc.factory.create("BiddableCampaignCriterion")
                    bcc.CampaignId              = camp_id
                    bcc.Id                      = None
                    bcc.Type                    = snull()
                    bcc.Status                  = snull()
                    bcc.CriterionCashback       = snull()
                    bcc.ForwardCompatibilityMap = snull()
                    bcc.BidMultiplier           = 0
                    lc = svc.factory.create("LocationCriterion")
                    lc.LocationId = loc_id
                    lc.Type       = snull()
                    bcc.Criterion = lc
                    criterions.append(bcc)

                bcc_intent = svc.factory.create("BiddableCampaignCriterion")
                bcc_intent.CampaignId              = camp_id
                bcc_intent.Id                      = None
                bcc_intent.Type                    = snull()
                bcc_intent.Status                  = snull()
                bcc_intent.CriterionCashback       = snull()
                bcc_intent.ForwardCompatibilityMap = snull()
                lic = svc.factory.create("LocationIntentCriterion")
                lic.IntentOption = "PeopleIn"
                lic.Type         = snull()
                bcc_intent.Criterion = lic
                criterions.append(bcc_intent)

                svc.AddCampaignCriterions(
                    CampaignCriterions={"CampaignCriterion": criterions},
                    CriterionType="Targets",
                )
                logger.info("    Added %d location criteria + PeopleIn",
                            len(MSFT_LOCATION_IDS))
            except Exception as e:
                logger.warning("    Location criteria failed (may already exist): %s", e)

        # ── Age ───────────────────────────────────────────────────────────────
        if dry_run:
            logger.info("    [DRY RUN] Would add %d age criteria", len(MSFT_AGE_SPEC))
        else:
            try:
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
                svc.AddCampaignCriterions(
                    CampaignCriterions={"CampaignCriterion": criterions},
                    CriterionType="Targets",
                )
                logger.info("    Added %d age criteria", len(MSFT_AGE_SPEC))
            except Exception as e:
                logger.warning("    Age criteria failed (may already exist): %s", e)

        # ── Gender ────────────────────────────────────────────────────────────
        if dry_run:
            logger.info("    [DRY RUN] Would add %d gender criteria", len(MSFT_GENDER_SPEC))
        else:
            try:
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
                svc.AddCampaignCriterions(
                    CampaignCriterions={"CampaignCriterion": criterions},
                    CriterionType="Targets",
                )
                logger.info("    Added %d gender criteria", len(MSFT_GENDER_SPEC))
            except Exception as e:
                logger.warning("    Gender criteria failed (may already exist): %s", e)


# ── Step 4: Create keywords ───────────────────────────────────────────────────

def create_keywords_for_ad_group(svc, ag_msft_id: int, theme: str,
                                  dry_run: bool) -> int:
    """Create exact + phrase keywords for all 12 cities. Returns count."""
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

    resp    = svc.AddKeywords(AdGroupId=ag_msft_id,
                               Keywords={"Keyword": kw_objects})
    kw_ids  = list(resp.KeywordIds.long) if resp.KeywordIds else []
    created = len([i for i in kw_ids if i and i > 0])
    errors  = (list(resp.PartialErrors.BatchError)
               if resp.PartialErrors and resp.PartialErrors.BatchError else [])
    already = sum(1 for e in errors
                  if "AlreadyExists" in str(getattr(e, "ErrorCode", "")))
    if already:
        logger.info("    %d keywords already existed, %d newly created for '%s'",
                    already, created, theme)
    else:
        logger.info("    Created %d keywords for '%s'", created, theme)

    # Upsert into DB
    with db.get_db() as (conn, cur):
        # Get DB ad group id
        cur.execute(
            "SELECT id FROM ad_groups WHERE google_ad_group_id=%s",
            (f"msft_ag_{ag_msft_id}",),
        )
        ag_row = cur.fetchone()
        if ag_row and resp.KeywordIds and resp.KeywordIds.long:
            for kw_obj, kw_msft_id in zip(kw_objects, resp.KeywordIds.long):
                if not kw_msft_id or kw_msft_id <= 0:
                    continue
                bid_micros = int(KEYWORD_BID * 1_000_000)
                cur.execute(
                    """INSERT INTO keywords
                       (google_keyword_id, ad_group_id, keyword_text, match_type,
                        status, cpc_bid_micros, updated_at)
                       VALUES (%s, %s, %s, %s, 'ENABLED', %s, NOW())
                       ON CONFLICT (google_keyword_id) DO NOTHING""",
                    (f"msft_kw_{kw_msft_id}", ag_row["id"],
                     kw_obj.Text, kw_obj.MatchType.upper(), bid_micros),
                )
    return created


# ── Step 5: Create RSA ────────────────────────────────────────────────────────

def create_rsa_for_ad_group(svc, ag_msft_id: int, theme: str,
                             dry_run: bool) -> int | None:
    """Create one Responsive Search Ad for the given ad group."""
    copy      = AD_COPY.get(theme, AD_COPY.get("Design Build", {}))
    if not copy:
        logger.warning("    No AD_COPY found for theme '%s' — skipping RSA", theme)
        return None

    slug      = theme.lower().replace(" ", "-")
    final_url = (f"{LANDING_PAGE}?utm_source=microsoft&utm_medium=cpc"
                 f"&utm_campaign=rma-{slug}&utm_content=patch_rma")

    if dry_run:
        logger.info("    [DRY RUN] Would create RSA for '%s'", theme)
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

    # Deduplicate headlines (Microsoft rejects RSAs with duplicate text)
    seen_hl: set[str] = set()
    unique_headlines = []
    for text in copy.get("headlines", [])[:15]:
        trimmed = _word_trim(text, 30)
        if trimmed.lower() not in seen_hl:
            seen_hl.add(trimmed.lower())
            unique_headlines.append(trimmed)

    headlines = svc.factory.create("ArrayOfAssetLink")
    for i, text in enumerate(unique_headlines[:15]):
        link  = svc.factory.create("AssetLink")
        asset = svc.factory.create("TextAsset")
        asset.Text       = text
        link.Asset       = asset
        link.EditorialStatus = None
        link.PinnedField = "Headline1" if i == 0 else ("Headline2" if i == 1 else None)
        headlines.AssetLink.append(link)
    rsa.Headlines = headlines

    descriptions = svc.factory.create("ArrayOfAssetLink")
    for text in copy.get("descriptions", [])[:4]:
        link  = svc.factory.create("AssetLink")
        asset = svc.factory.create("TextAsset")
        asset.Text           = _word_trim(text, 90)
        link.Asset           = asset
        link.EditorialStatus = None
        link.PinnedField     = None
        descriptions.AssetLink.append(link)
    rsa.Descriptions = descriptions

    try:
        resp   = svc.AddAds(AdGroupId=ag_msft_id, Ads={"Ad": [rsa]})
        ad_ids = list(resp.AdIds.long) if resp.AdIds and resp.AdIds.long else []
        if not ad_ids or ad_ids[0] is None or int(ad_ids[0]) <= 0:
            # Possibly already exists or partial error
            errors = (list(resp.PartialErrors.BatchError)
                      if resp.PartialErrors and resp.PartialErrors.BatchError else [])
            if errors:
                for err in errors:
                    logger.warning("    RSA partial error for '%s': %s — %s",
                                   theme, getattr(err, "ErrorCode", ""), getattr(err, "Message", ""))
            else:
                logger.warning("    RSA returned no ad ID for '%s' (may already exist)", theme)
            return None
        ad_id = int(ad_ids[0])
        logger.info("    Created RSA id=%d for '%s'", ad_id, theme)
        # Upsert into DB
        import json as _json
        with db.get_db() as (conn, cur):
            cur.execute(
                "SELECT id FROM ad_groups WHERE google_ad_group_id=%s",
                (f"msft_ag_{ag_msft_id}",),
            )
            ag_row = cur.fetchone()
            if ag_row:
                cur.execute(
                    """INSERT INTO ads
                       (google_ad_id, ad_group_id, ad_type, status,
                        headlines, descriptions, updated_at)
                       VALUES (%s, %s, 'RESPONSIVE_SEARCH_AD', 'ENABLED',
                               %s, %s, NOW())
                       ON CONFLICT (google_ad_id) DO NOTHING""",
                    (f"msft_ad_{ad_id}", ag_row["id"],
                     _json.dumps(copy.get("headlines", [])[:15]),
                     _json.dumps(copy.get("descriptions", [])[:4])),
                )
        return ad_id
    except Exception as e:
        logger.error("    RSA creation failed for '%s': %s", theme, e)
        return None


# ── Step 6: Extensions ────────────────────────────────────────────────────────

def create_and_associate_extensions(svc, camp_msft_ids: list[int],
                                     dry_run: bool) -> dict:
    """Create account-level extensions and associate with all campaigns."""
    from suds import null as snull
    logger.info("=== Step 6: Creating and associating extensions ===")
    counts = {"sitelinks": 0, "callouts": 0, "snippets": 0, "action": 0}

    def _null_ext_base(ext):
        """Null out pre-populated complex fields that cause serialization errors."""
        ext.Scheduling              = snull()
        ext.ForwardCompatibilityMap = snull()
        ext.DevicePreference        = snull()
        ext.Status                  = snull()   # defaults to Active server-side
        ext.Type                    = snull()
        ext.Version                 = snull()
        ext.Id                      = snull()

    # Sitelinks
    if dry_run:
        logger.info("  [DRY RUN] Would create %d sitelinks", len(SITELINKS))
        sitelink_ids = []
    else:
        try:
            ext_objects = []
            for sl in SITELINKS:
                ext = svc.factory.create("SitelinkAdExtension")
                _null_ext_base(ext)
                # SitelinkAdExtension uses DisplayText (not SitelinkText)
                ext.DisplayText          = _word_trim(sl["title"], 25)
                ext.Description1         = _word_trim(sl["desc1"],  35)
                ext.Description2         = _word_trim(sl["desc2"],  35)
                ext.FinalUrls            = {"string": [sl["url"]]}
                ext.DestinationUrl       = snull()
                ext.FinalMobileUrls      = snull()
                ext.FinalAppUrls         = snull()
                ext.TrackingUrlTemplate  = snull()
                ext.UrlCustomParameters  = snull()
                ext.FinalUrlSuffix       = snull()
                ext_objects.append(ext)
            resp = svc.AddAdExtensions(
                AccountId=ACCOUNT_ID,
                AdExtensions={"AdExtension": ext_objects},
            )
            sitelink_ids = [int(i.Id) for i in
                            (resp.AdExtensionIdentities.AdExtensionIdentity or [])
                            if hasattr(i, "Id") and i.Id]
            counts["sitelinks"] = len(sitelink_ids)
            logger.info("  Created %d sitelinks", len(sitelink_ids))
        except Exception as e:
            logger.error("  Sitelink creation failed: %s", e)
            sitelink_ids = []

    # Callouts
    if dry_run:
        logger.info("  [DRY RUN] Would create %d callouts", len(CALLOUT_TEXTS))
        callout_ids = []
    else:
        try:
            ext_objects = []
            for text in CALLOUT_TEXTS:
                ext = svc.factory.create("CalloutAdExtension")
                _null_ext_base(ext)
                ext.Text = _word_trim(text, 25)
                ext_objects.append(ext)
            resp = svc.AddAdExtensions(
                AccountId=ACCOUNT_ID,
                AdExtensions={"AdExtension": ext_objects},
            )
            callout_ids = [int(i.Id) for i in
                           (resp.AdExtensionIdentities.AdExtensionIdentity or [])
                           if hasattr(i, "Id") and i.Id]
            counts["callouts"] = len(callout_ids)
            logger.info("  Created %d callouts", len(callout_ids))
        except Exception as e:
            logger.error("  Callout creation failed: %s", e)
            callout_ids = []

    # Structured snippet
    if dry_run:
        logger.info("  [DRY RUN] Would create structured snippet")
        snippet_ids = []
    else:
        try:
            ext = svc.factory.create("StructuredSnippetAdExtension")
            _null_ext_base(ext)
            ext.Header = STRUCTURED_SNIPPET["header"]
            ext.Values = {"string": [_word_trim(v, 25)
                                     for v in STRUCTURED_SNIPPET["values"]]}
            resp = svc.AddAdExtensions(
                AccountId=ACCOUNT_ID,
                AdExtensions={"AdExtension": [ext]},
            )
            snippet_ids = [int(i.Id) for i in
                           (resp.AdExtensionIdentities.AdExtensionIdentity or [])
                           if hasattr(i, "Id") and i.Id]
            counts["snippets"] = len(snippet_ids)
            logger.info("  Created %d structured snippets", len(snippet_ids))
        except Exception as e:
            logger.error("  Structured snippet creation failed: %s", e)
            snippet_ids = []

    # Action extension
    if dry_run:
        logger.info("  [DRY RUN] Would create action extension (%s)",
                    ACTION_EXT["action_type"])
        action_ids = []
    else:
        try:
            ext = svc.factory.create("ActionAdExtension")
            _null_ext_base(ext)
            ext.ActionType          = ACTION_EXT["action_type"]
            ext.FinalUrls           = {"string": [ACTION_EXT["url"]]}
            ext.FinalMobileUrls     = snull()
            ext.FinalUrlSuffix      = snull()
            ext.TrackingUrlTemplate = snull()
            ext.UrlCustomParameters = snull()
            ext.Language            = snull()
            resp = svc.AddAdExtensions(
                AccountId=ACCOUNT_ID,
                AdExtensions={"AdExtension": [ext]},
            )
            action_ids = [int(i.Id) for i in
                          (resp.AdExtensionIdentities.AdExtensionIdentity or [])
                          if hasattr(i, "Id") and i.Id]
            counts["action"] = len(action_ids)
            logger.info("  Created %d action extensions", len(action_ids))
        except Exception as e:
            logger.warning("  Action extension creation failed (may not be available): %s", e)
            action_ids = []

    # Associate all extensions with all 5 campaigns
    def _associate(ext_ids, ext_type):
        if not ext_ids or not camp_msft_ids:
            return
        assocs = []
        for ext_id in ext_ids:
            for camp_id in camp_msft_ids:
                a = svc.factory.create("AdExtensionIdToEntityIdAssociation")
                a.AdExtensionId = ext_id
                a.EntityId      = camp_id
                assocs.append(a)
        try:
            # Note: AdExtensionType is NOT a valid kwarg in this API version
            svc.SetAdExtensionsAssociations(
                AccountId=ACCOUNT_ID,
                AdExtensionIdToEntityIdAssociations={
                    "AdExtensionIdToEntityIdAssociation": assocs
                },
                AssociationType="Campaign",
            )
            logger.info("  Associated %d %s with %d campaigns",
                        len(ext_ids), ext_type, len(camp_msft_ids))
        except Exception as e:
            logger.error("  Association failed for %s: %s", ext_type, e)

    if not dry_run:
        _associate(sitelink_ids, "SitelinkAdExtension")
        _associate(callout_ids,  "CalloutAdExtension")
        _associate(snippet_ids,  "StructuredSnippetAdExtension")
        _associate(action_ids,   "ActionAdExtension")
    else:
        logger.info("  [DRY RUN] Would associate all extensions with %d campaigns",
                    len(camp_msft_ids))

    return counts


# ── Step 7: Verify bid strategies ─────────────────────────────────────────────

def verify_bid_strategies(svc, dry_run: bool) -> None:
    """Fetch all 5 campaigns and confirm each is running EnhancedCpc."""
    logger.info("=== Step 7: Verifying bid strategies ===")
    try:
        resp = svc.GetCampaignsByAccountId(AccountId=ACCOUNT_ID, CampaignType="Search")
        camps = (list(resp.Campaign.Campaign)
                 if resp.Campaign and hasattr(resp.Campaign, "Campaign")
                 else list(resp.Campaign or []))
    except Exception as e:
        logger.error("  GetCampaignsByAccountId failed: %s", e)
        return

    target_ids = set(ALL_CAMP_IDS)
    for c in camps:
        if not hasattr(c, "Id") or c.Id is None:
            continue
        if int(c.Id) not in target_ids:
            continue
        scheme = type(c.BiddingScheme).__name__ if c.BiddingScheme else "None"
        budget = getattr(c, "DailyBudget", "?")
        status = getattr(c, "Status", "?")
        ok = "EnhancedCpc" in scheme
        logger.info("  [%s] %s — bid=%s  budget=$%s  status=%s",
                    "OK" if ok else "WARN", c.Name, scheme, budget, status)
        if not ok and not dry_run:
            # Force-set EnhancedCpc
            try:
                fix = svc.factory.create("Campaign")
                fix.Id             = int(c.Id)
                fix.BiddingScheme  = svc.factory.create("EnhancedCpcBiddingScheme")
                fix.BidStrategyScope = "Account"
                fix.BudgetType     = "DailyBudgetStandard"
                svc.UpdateCampaigns(AccountId=ACCOUNT_ID,
                                    Campaigns={"Campaign": [fix]})
                logger.info("    Fixed bid strategy → EnhancedCpc for %s", c.Name)
            except Exception as e:
                logger.error("    Bid strategy fix failed for %s: %s", c.Name, e)


# ── Main ──────────────────────────────────────────────────────────────────────

def _get_all_ad_groups_from_db() -> list[dict]:
    """
    Return all ad groups for the 5 consolidated campaigns, with their
    theme name (stripped from the ad group name) and msft ag id.

    Handles both external ID formats:
      - new format: msft_ag_<numeric_id>
      - old format: msft_<numeric_id>

    Deduplicates by numeric Microsoft ID so the same ag is not processed twice.
    """
    with db.get_db() as (conn, cur):
        cur.execute("""
            SELECT ag.google_ad_group_id, ag.name as ag_name
            FROM ad_groups ag
            JOIN campaigns c ON c.id = ag.campaign_id
            WHERE c.platform = 'microsoft_ads'
              AND c.managed_by = 'claude_code'
              AND c.status != 'archived'
        """)
        seen_ids: set[int] = set()
        rows = []
        for r in cur.fetchall():
            raw = r["google_ad_group_id"]
            # Strip known prefixes to get the numeric ID
            if raw.startswith("msft_ag_"):
                num_str = raw[len("msft_ag_"):]
            elif raw.startswith("msft_"):
                num_str = raw[len("msft_"):]
            else:
                num_str = raw
            try:
                ag_msft_id = int(num_str)
            except ValueError:
                logger.warning("  Skipping unrecognised ag id: %s", raw)
                continue
            if ag_msft_id in seen_ids:
                continue  # deduplicate (old + new format for same ag)
            seen_ids.add(ag_msft_id)
            # Strip "[RMA] " prefix to get theme name
            theme = r["ag_name"].replace("[RMA] ", "").strip()
            # Prefer the cleaner theme name (no "— All Cities" suffix)
            if " — " in theme:
                theme = theme.split(" — ")[0].strip()
            rows.append({"ag_msft_id": ag_msft_id, "theme": theme})
        return rows


def run(dry_run: bool = False):
    label = "[DRY RUN] " if dry_run else ""
    logger.info("=== Microsoft Ads Campaign Patch %s===", label)

    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    s    = _svc(auth)

    totals = {
        "budgets_fixed":    0,
        "criteria_added":   0,
        "keywords_created": 0,
        "rsas_created":     0,
        "extensions":       {},
        "errors":           [],
    }

    # Step 1: Fix budgets
    totals["budgets_fixed"] = fix_campaign_budgets(s, dry_run)

    # Step 2: Repurpose WHR campaign
    whr_ag_msft_id = repurpose_whole_house_remodel(s, dry_run)

    # Step 3: Ensure criteria on all 5 campaigns
    ensure_campaign_criteria(s, ALL_CAMP_IDS, dry_run)

    # Build ad group list from DB (includes WHR if just created)
    ag_list = _get_all_ad_groups_from_db()
    if dry_run and whr_ag_msft_id is None:
        # In dry-run mode WHR ag won't be in DB yet — add a placeholder
        ag_list.append({"ag_msft_id": WHR_MSFT_ID, "theme": WHR_THEME})

    # Step 4 + 5: Keywords and RSAs for every ad group
    logger.info("=== Steps 4+5: Creating keywords and RSAs for %d ad groups ===",
                len(ag_list))
    for ag in ag_list:
        ag_id = ag["ag_msft_id"]
        theme = ag["theme"]
        logger.info("  Ad group %d — theme: %s", ag_id, theme)

        # Keywords
        try:
            kw_count = create_keywords_for_ad_group(s, ag_id, theme, dry_run)
            totals["keywords_created"] += kw_count
        except Exception as e:
            logger.error("  Keywords failed for '%s': %s", theme, e)
            totals["errors"].append(f"keywords '{theme}': {e}")

        # RSA
        try:
            rsa_id = create_rsa_for_ad_group(s, ag_id, theme, dry_run)
            if rsa_id or dry_run:
                totals["rsas_created"] += 1
        except Exception as e:
            logger.error("  RSA failed for '%s': %s", theme, e)
            totals["errors"].append(f"rsa '{theme}': {e}")

    # Step 6: Extensions
    totals["extensions"] = create_and_associate_extensions(s, ALL_CAMP_IDS, dry_run)

    # Step 7: Verify bid strategies
    verify_bid_strategies(s, dry_run)

    # Summary
    logger.info("=" * 60)
    logger.info("PATCH %sCOMPLETE", label)
    logger.info("  Budgets fixed    : %d", totals["budgets_fixed"])
    logger.info("  Keywords created : %d", totals["keywords_created"])
    logger.info("  RSAs created     : %d", totals["rsas_created"])
    logger.info("  Extensions       : %s", totals["extensions"])
    if totals["errors"]:
        logger.warning("  Errors           : %d", len(totals["errors"]))
        for err in totals["errors"]:
            logger.warning("    - %s", err)
    logger.info("=" * 60)
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Patch Microsoft Ads account without re-running full rebuild"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all actions without making API calls")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
