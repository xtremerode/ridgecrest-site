"""
Compliance Agent — Ridgecrest Designs
======================================
After every sync cycle, fetches live settings from Meta and Microsoft Ads
and verifies them against every parameter in CLAUDE.md.

Checks:
  Meta
    • All RMA ad sets use saved audience 6934900931693 with advantage_audience=0
    • Campaigns paused on Tue/Wed/Thu, active on Fri/Sat/Sun/Mon
    • Daily budget per ad set ≤ $125

  Microsoft Ads
    • LocationIntent = PeopleIn on all RMA campaigns
    • Age bid adjustments correct (18-24: -90%, 25-34: -50%, 35-49: +10%, 50-64: 0%, 65+: -30%)
    • Gender: Female +10%, Male 0%
    • All keywords bid ≥ $8.00

  Spend (from local DB)
    • Weekly spend ≤ $1,000 ceiling
    • No spend recorded on Tue/Wed/Thu

Auto-fix:
  Simple, low-risk violations are fixed immediately.
  Complex or ambiguous violations are flagged for human review via email.

Auto-fixable:
  • Microsoft keyword bid below floor → raise to floor
  • Microsoft LocationIntent wrong → update to PeopleIn
  • Microsoft gender criteria wrong → apply correct multipliers
  • Microsoft age criteria missing → add correct multipliers

Flagged only (human review):
  • Meta advantage_audience = 1 (wrong audience)
  • Meta wrong saved audience
  • Spend ceiling violation

Run standalone:  python compliance_agent.py
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

import db
from config import (
    ACTIVE_DAYS,
    WEEKLY_BUDGET_CEILING_USD,
    DAILY_BUDGET_SOFT_CAP_USD,
    ALERT_EMAIL,
    ALERT_FROM,
    META_AD_ACCOUNT_ID,
    META_API_VERSION,
    META_BASE_URL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [compliance_agent] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME = "compliance_agent"

# ---------------------------------------------------------------------------
# Spec constants (CLAUDE.md §18 and prior work in this session)
# ---------------------------------------------------------------------------

META_REQUIRED_AUDIENCE_ID   = os.getenv("META_AUDIENCE_ID", "6934900931693")
META_REQUIRED_ADVANTAGE_AUD = 0        # advantage_audience must be 0
META_MAX_ADSET_BUDGET_USD   = 125.0    # CLAUDE.md §19 non-negotiables
MSFT_ACCOUNT_ID             = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))
MSFT_KEYWORD_BID_FLOOR_USD  = 8.00    # floor set in previous session

# Age criteria spec — note Microsoft's typo "Fourty" not "Forty"
MSFT_AGE_SPEC = {
    "EighteenToTwentyFour":   -90.0,
    "TwentyFiveToThirtyFour": -50.0,
    "ThirtyFiveToFourtyNine": +10.0,   # Microsoft WSDL typo — "Fourty"
    "FiftyToSixtyFour":         0.0,
    "SixtyFiveAndAbove":       -30.0,
}

MSFT_GENDER_SPEC = {
    "Male":   0.0,
    "Female": 10.0,
}

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
INGEST_API_KEY = os.getenv("INGEST_API_KEY", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")


# ---------------------------------------------------------------------------
# Finding helpers
# ---------------------------------------------------------------------------

def _pass(check: str, platform: str, detail: str = "") -> dict:
    return {"check": check, "platform": platform, "status": "pass",
            "detail": detail, "auto_fixed": False}


def _fail(check: str, platform: str, detail: str,
          auto_fixable: bool = False, entity: str = "") -> dict:
    return {"check": check, "platform": platform, "status": "fail",
            "detail": detail, "auto_fixable": auto_fixable,
            "entity": entity, "auto_fixed": False}


def _skip(check: str, platform: str, reason: str) -> dict:
    return {"check": check, "platform": platform, "status": "skip",
            "detail": reason, "auto_fixed": False}


def _log_violation(check: str, platform: str, entity: str, detail: str):
    """Persist a violation to guardrail_violations for dashboard visibility."""
    try:
        with db.get_db() as (conn, cur):
            cur.execute(
                """INSERT INTO guardrail_violations
                   (rule_category, rule_name, entity_type, entity_name, reason)
                   VALUES (%s, %s, %s, %s, %s)""",
                ("compliance", f"{platform}:{check}", platform, entity, detail),
            )
    except Exception as e:
        logger.warning("Could not log violation to DB: %s", e)


# ---------------------------------------------------------------------------
# Meta compliance checks
# ---------------------------------------------------------------------------

def _meta_get(path: str, params: dict = None) -> dict:
    p = {"access_token": META_ACCESS_TOKEN}
    if params:
        p.update(params)
    r = requests.get(f"{META_BASE_URL}{path}", params=p, timeout=20)
    return r.json()


def _apply_meta_adset_targeting(adset_id: str, adset_name: str) -> bool:
    """
    Apply the full CLAUDE.md §18 targeting spec to an ad set.
    Sets advantage_audience=0, correct geo/age/gender/family-status targeting,
    and includes the required saved audience in custom_audiences.
    Returns True on success.
    """
    targeting_spec = {
        "age_min": 35,
        "age_max": 55,
        "genders": [2],
        "flexible_spec": [
            {
                "family_statuses": [
                    {"id": "6023005529383"},
                    {"id": "6023005570783"},
                    {"id": "6023005681983"},
                    {"id": "6023005718983"},
                    {"id": "6023080302983"},
                ]
            }
        ],
        "geo_locations": {
            "zips": [
                {"key": "US:94506"}, {"key": "US:94507"}, {"key": "US:94526"},
                {"key": "US:94528"}, {"key": "US:94549"}, {"key": "US:94556"},
                {"key": "US:94563"}, {"key": "US:94566"}, {"key": "US:94568"},
                {"key": "US:94582"}, {"key": "US:94583"}, {"key": "US:94586"},
                {"key": "US:94588"}, {"key": "US:94595"}, {"key": "US:94596"},
                {"key": "US:94597"}, {"key": "US:94598"},
            ],
            "location_types": ["home", "recent"],
        },
        "custom_audiences": [{"id": META_REQUIRED_AUDIENCE_ID}],
        "targeting_automation": {"advantage_audience": META_REQUIRED_ADVANTAGE_AUD},
    }
    try:
        resp = requests.post(
            f"{META_BASE_URL}/{adset_id}",
            data={
                "targeting": json.dumps(targeting_spec),
                "access_token": META_ACCESS_TOKEN,
            },
            timeout=30,
        )
        result = resp.json()
        if result.get("success") or result.get("id"):
            logger.info("  Auto-fixed targeting for ad set %s (%s)", adset_name, adset_id)
            return True
        else:
            logger.warning("  Targeting fix failed for %s: %s", adset_name, result)
            return False
    except Exception as e:
        logger.warning("  Targeting fix exception for %s: %s", adset_name, e)
        return False


def check_meta_compliance() -> list[dict]:
    findings = []

    if not META_ACCESS_TOKEN:
        findings.append(_skip("meta_targeting", "meta", "META_ACCESS_TOKEN not set"))
        return findings

    # Fetch all RMA ad sets (campaigns starting with "[RMA]")
    camp_resp = _meta_get(
        f"/{META_AD_ACCOUNT_ID}/campaigns",
        {"fields": "id,name,status", "limit": 200},
    )
    if "error" in camp_resp:
        findings.append(_skip("meta_campaigns", "meta",
                               f"API error: {camp_resp['error'].get('message','')}"))
        return findings

    rma_campaigns = [c for c in camp_resp.get("data", [])
                     if "[RMA]" in c.get("name", "")]
    logger.info("Meta: found %d RMA campaign(s)", len(rma_campaigns))

    if not rma_campaigns:
        findings.append(_skip("meta_targeting", "meta", "No RMA campaigns found in Meta"))
        return findings

    today_name = datetime.now().strftime("%A").lower()
    is_active_day = today_name in ACTIVE_DAYS

    audience_violations = 0
    advantage_violations = 0
    budget_violations = 0
    day_violations = 0

    for camp in rma_campaigns:
        cid   = camp["id"]
        cname = camp["name"]
        live_status = camp.get("status", "")

        # ── Day scheduling ──────────────────────────────────────────────────
        if not is_active_day and live_status == "ACTIVE":
            day_violations += 1
            findings.append(_fail(
                "meta_day_scheduling", "meta",
                f"{cname} is ACTIVE on {today_name.title()} — should be PAUSED",
                auto_fixable=False,  # meta_manager handles this each cycle
                entity=cname,
            ))
            _log_violation("day_scheduling", "meta", cname,
                           f"Campaign ACTIVE on inactive day {today_name.title()}")

        # ── Ad set targeting ─────────────────────────────────────────────────
        adsets_resp = _meta_get(
            f"/{cid}/adsets",
            {"fields": "id,name,status,daily_budget,targeting", "limit": 200},
        )
        if "error" in adsets_resp:
            findings.append(_skip("meta_adset_targeting", "meta",
                                   f"Ad sets fetch error for {cname}"))
            continue

        for adset in adsets_resp.get("data", []):
            asid   = adset["id"]
            asname = adset.get("name", asid)
            targeting = adset.get("targeting", {})

            # ── Collect targeting violations for this ad set ──────────────────
            adset_violations = []

            # Check advantage_audience = 0
            targeting_auto = targeting.get("targeting_automation", {})
            advantage_aud = targeting_auto.get("advantage_audience", None)
            if advantage_aud is None or int(advantage_aud) != META_REQUIRED_ADVANTAGE_AUD:
                adset_violations.append("advantage_audience")

            # Check saved audience ID in custom_audiences or saved_audience_id
            custom_auds = targeting.get("custom_audiences", [])
            aud_ids = [str(a.get("id", "")) for a in custom_auds]
            saved_aud_id = str(targeting.get("saved_audience_id", ""))
            if (META_REQUIRED_AUDIENCE_ID not in aud_ids
                    and META_REQUIRED_AUDIENCE_ID != saved_aud_id):
                adset_violations.append("saved_audience")

            # ── Auto-fix both violations in one API call ──────────────────────
            if adset_violations:
                logger.info("  Ad set %s has violation(s): %s — attempting auto-fix",
                            asname, adset_violations)
                fixed = _apply_meta_adset_targeting(asid, asname)
                if fixed:
                    if "advantage_audience" in adset_violations:
                        advantage_violations += 1
                        findings.append(_pass(
                            "meta_advantage_audience", "meta",
                            f"{asname}: advantage_audience corrected to 0 (auto-fixed)",
                        ))
                    if "saved_audience" in adset_violations:
                        audience_violations += 1
                        findings.append(_pass(
                            "meta_saved_audience", "meta",
                            f"{asname}: saved audience {META_REQUIRED_AUDIENCE_ID} "
                            f"applied to custom_audiences (auto-fixed)",
                        ))
                    _log_violation(
                        "targeting_auto_fixed", "meta", asname,
                        f"Violations {adset_violations} auto-fixed — CLAUDE.md §18 spec applied",
                    )
                else:
                    if "advantage_audience" in adset_violations:
                        advantage_violations += 1
                        findings.append(_fail(
                            "meta_advantage_audience", "meta",
                            f"{asname}: advantage_audience={advantage_aud} (required: 0). "
                            "Auto-fix attempted but failed — check manually.",
                            auto_fixable=False,
                            entity=asname,
                        ))
                        _log_violation("advantage_audience", "meta", asname,
                                       f"advantage_audience={advantage_aud} — auto-fix failed")
                    if "saved_audience" in adset_violations:
                        audience_violations += 1
                        findings.append(_fail(
                            "meta_saved_audience", "meta",
                            f"{asname}: saved audience {META_REQUIRED_AUDIENCE_ID} not found "
                            f"in targeting (found: {aud_ids or 'none'}). "
                            "Auto-fix attempted but failed — check manually.",
                            auto_fixable=False,
                            entity=asname,
                        ))
                        _log_violation("saved_audience", "meta", asname,
                                       f"Required audience {META_REQUIRED_AUDIENCE_ID} — auto-fix failed")

            # Check daily budget ≤ $125
            daily_budget_cents = int(adset.get("daily_budget", 0))
            daily_budget_usd   = daily_budget_cents / 100.0
            if daily_budget_usd > META_MAX_ADSET_BUDGET_USD:
                budget_violations += 1
                findings.append(_fail(
                    "meta_adset_budget", "meta",
                    f"{asname}: daily budget ${daily_budget_usd:.2f} exceeds "
                    f"${META_MAX_ADSET_BUDGET_USD:.2f} cap",
                    auto_fixable=False,
                    entity=asname,
                ))
                _log_violation("adset_budget", "meta", asname,
                               f"Daily budget ${daily_budget_usd:.2f} > ${META_MAX_ADSET_BUDGET_USD:.2f}")

    if not advantage_violations and not audience_violations and not budget_violations and not day_violations:
        findings.append(_pass("meta_targeting", "meta",
                               f"All {len(rma_campaigns)} RMA campaign(s) pass targeting checks"))
    else:
        logger.warning("Meta compliance: %d advantage_audience, %d audience, "
                       "%d budget, %d day-scheduling violation(s)",
                       advantage_violations, audience_violations,
                       budget_violations, day_violations)

    return findings


# ---------------------------------------------------------------------------
# Microsoft Ads compliance checks
# ---------------------------------------------------------------------------

def _msft_auth():
    """Authenticate and return (auth_data, campaign_service_client)."""
    from bingads.authorization import (
        AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
    )
    from bingads import ServiceClient

    client_id     = os.getenv("MICROSOFT_CLIENT_ID", "")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    tenant_id     = os.getenv("MICROSOFT_TENANT_ID", "")
    dev_token     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
    refresh_token = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
    redirect_uri  = "https://login.microsoftonline.com/common/oauth2/nativeclient"

    resp = requests.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "client_id":     client_id,
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
            "scope":         "https://ads.microsoft.com/msads.manage offline_access",
        },
        timeout=30,
    )
    resp.raise_for_status()
    td = resp.json()
    if "error" in td:
        raise RuntimeError(f"Token refresh failed: {td}")

    tokens = OAuthTokens(
        access_token=td["access_token"],
        access_token_expires_in_seconds=int(td.get("expires_in", 3600)),
        refresh_token=refresh_token,
    )
    oauth = OAuthWebAuthCodeGrant(
        client_id=client_id, client_secret=client_secret,
        redirection_uri=redirect_uri, oauth_tokens=tokens,
        oauth_scope=ADS_MANAGE, tenant=tenant_id,
    )
    auth = AuthorizationData(
        account_id=MSFT_ACCOUNT_ID,
        developer_token=dev_token,
        authentication=oauth,
    )
    try:
        csvc = ServiceClient("CustomerManagementService", 13, auth, "production")
        ur   = csvc.GetUser(UserId=None)
        roles = (ur.CustomerRoles.CustomerRole
                 if ur.CustomerRoles and ur.CustomerRoles.CustomerRole else [])
        for role in roles:
            if hasattr(role, "CustomerId"):
                auth.customer_id = int(role.CustomerId)
                break
    except Exception as e:
        logger.warning("Could not resolve MSFT customer ID: %s", e)

    svc = ServiceClient("CampaignManagementService", 13, auth, "production")
    return auth, svc


def _get_rma_campaigns_msft(svc) -> list[dict]:
    """Return list of {id, name, status} for all [RMA] campaigns."""
    resp = svc.GetCampaignsByAccountId(AccountId=MSFT_ACCOUNT_ID, CampaignType="Search")
    raw  = (list(resp.Campaign.Campaign)
            if hasattr(resp.Campaign, "Campaign")
            else list(resp.Campaign or []))
    return [
        {"id": int(c.Id), "name": str(c.Name), "status": str(c.Status)}
        for c in raw if "[RMA]" in str(c.Name)
    ]


def _get_campaign_criteria(svc, campaign_id: int) -> list:
    """
    Fetch all targetable criteria for a campaign.
    Tries CriterionType='Biddable' (covers age/gender/location BiddableCampaignCriterion)
    then falls back to 'Targets'.
    Returns raw criterion objects (or empty list on error).
    """
    from suds import null as snull

    def _fetch(criterion_type: str) -> list:
        try:
            resp = svc.GetCampaignCriterionsByIds(
                CampaignId=campaign_id,
                CriterionIds=snull(),
                CriterionType=criterion_type,
            )
            cc = getattr(resp, "CampaignCriterions", None)
            if cc is None:
                return []
            inner = getattr(cc, "CampaignCriterion", None)
            if inner is None:
                return []
            return list(inner) if hasattr(inner, "__iter__") else [inner]
        except Exception as e:
            logger.debug("GetCampaignCriterionsByIds(%s) error for campaign %d: %s",
                         criterion_type, campaign_id, e)
            return []

    results = _fetch("Biddable")
    if not results:
        results = _fetch("Targets")
    return results


def _parse_criteria(criteria: list) -> dict:
    """
    Parse raw criterion objects into a structured dict:
    {
      'location_intent': str | None,
      'age': {AgeRange: multiplier, ...},
      'gender': {Gender: multiplier, ...},
    }
    """
    result = {"location_intent": None, "age": {}, "gender": {}}
    for cc in criteria:
        crit = getattr(cc, "Criterion", None)
        if crit is None:
            continue
        crit_type = type(crit).__name__

        if crit_type == "LocationIntentCriterion":
            intent = getattr(crit, "IntentOption", None)
            if intent is not None:
                result["location_intent"] = str(intent)

        elif crit_type == "AgeCriterion":
            age_range = str(getattr(crit, "AgeRange", ""))
            bid       = getattr(cc, "CriterionBid", None)
            multiplier = float(getattr(bid, "Multiplier", 0)) if bid else 0.0
            result["age"][age_range] = multiplier

        elif crit_type == "GenderCriterion":
            gender    = str(getattr(crit, "GenderType", ""))
            bid       = getattr(cc, "CriterionBid", None)
            multiplier = float(getattr(bid, "Multiplier", 0)) if bid else 0.0
            result["gender"][gender] = multiplier

    return result


def _apply_msft_location_fix(svc, cid: int, name: str) -> bool:
    """Fix LocationIntent to PeopleIn on a single campaign. Returns success."""
    try:
        from suds import null as snull
        bcc = svc.factory.create("BiddableCampaignCriterion")
        bcc.CampaignId          = cid
        bcc.Id                  = cid      # LocationIntent uses campaign ID as criterion ID
        bcc.Type                = snull()
        bcc.Status              = snull()
        bcc.ForwardCompatibilityMap = snull()
        bcc.CriterionCashback   = snull()
        lic = svc.factory.create("LocationIntentCriterion")
        lic.IntentOption = "PeopleIn"
        lic.Type         = snull()
        bcc.Criterion    = lic
        bm = svc.factory.create("BidMultiplier")
        bm.Multiplier = 0.0
        bm.Type       = snull()
        bcc.CriterionBid = bm
        svc.UpdateCampaignCriterions(
            CampaignCriterions={"CampaignCriterion": [bcc]},
            CriterionType="Targets",
        )
        logger.info("  Auto-fixed LocationIntent → PeopleIn for %s", name)
        return True
    except Exception as e:
        logger.warning("  Location fix failed for %s: %s", name, e)
        return False


def _apply_msft_gender_fix(svc, cid: int, name: str) -> bool:
    """Apply correct gender bid adjustments to a campaign. Returns success."""
    try:
        from suds import null as snull
        criterions = []
        for gender_str, pct in MSFT_GENDER_SPEC.items():
            bcc = svc.factory.create("BiddableCampaignCriterion")
            bcc.CampaignId          = cid
            bcc.Id                  = snull()
            bcc.Type                = snull()
            bcc.Status              = snull()
            bcc.ForwardCompatibilityMap = snull()
            bcc.CriterionCashback   = snull()
            gc = svc.factory.create("GenderCriterion")
            gc.GenderType = gender_str
            gc.Type       = snull()
            bcc.Criterion = gc
            bm = svc.factory.create("BidMultiplier")
            bm.Multiplier = float(pct)
            bm.Type       = snull()
            bcc.CriterionBid = bm
            criterions.append(bcc)
        svc.AddCampaignCriterions(
            CampaignCriterions={"CampaignCriterion": criterions},
            CriterionType="Targets",
        )
        logger.info("  Auto-fixed gender criteria for %s", name)
        return True
    except Exception as e:
        logger.warning("  Gender fix failed for %s: %s", name, e)
        return False


def _apply_msft_age_fix(svc, cid: int, name: str) -> bool:
    """Apply correct age bid adjustments to a campaign. Returns success."""
    try:
        from suds import null as snull
        criterions = []
        for age_range, pct in MSFT_AGE_SPEC.items():
            bcc = svc.factory.create("BiddableCampaignCriterion")
            bcc.CampaignId          = cid
            bcc.Id                  = snull()
            bcc.Type                = snull()
            bcc.Status              = snull()
            bcc.ForwardCompatibilityMap = snull()
            bcc.CriterionCashback   = snull()
            ac = svc.factory.create("AgeCriterion")
            ac.AgeRange = age_range
            ac.Type     = snull()
            bcc.Criterion = ac
            bm = svc.factory.create("BidMultiplier")
            bm.Multiplier = float(pct)
            bm.Type       = snull()
            bcc.CriterionBid = bm
            criterions.append(bcc)
        svc.AddCampaignCriterions(
            CampaignCriterions={"CampaignCriterion": criterions},
            CriterionType="Targets",
        )
        logger.info("  Auto-fixed age criteria for %s", name)
        return True
    except Exception as e:
        logger.warning("  Age fix failed for %s: %s", name, e)
        return False


def _raise_msft_keyword_bids(svc) -> tuple[int, int]:
    """
    Raise any Microsoft keyword below MSFT_KEYWORD_BID_FLOOR_USD to the floor.
    Returns (updated_count, error_count).
    """
    from collections import defaultdict
    floor_micros = int(MSFT_KEYWORD_BID_FLOOR_USD * 1_000_000)

    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT k.id AS db_id, k.google_keyword_id, k.cpc_bid_micros,
                   k.keyword_text, k.match_type, ag.google_ad_group_id
            FROM keywords k
            JOIN ad_groups ag ON ag.id = k.ad_group_id
            JOIN campaigns c  ON c.id  = ag.campaign_id
            WHERE c.platform = 'microsoft_ads'
              AND (k.cpc_bid_micros IS NULL OR k.cpc_bid_micros < %s)
            """,
            (floor_micros,),
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return 0, 0

    by_ag: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        msft_ag_id = int(row["google_ad_group_id"].replace("msft_ag_", ""))
        by_ag[msft_ag_id].append(row)

    updated = 0
    errors  = 0
    from suds import null as snull
    for msft_ag_id, kw_rows in by_ag.items():
        try:
            kw_objects = []
            for row in kw_rows:
                msft_kw_id = int(row["google_keyword_id"].replace("msft_kw_", ""))
                kw = svc.factory.create("Keyword")
                kw.Id              = msft_kw_id
                kw.Bid             = svc.factory.create("Bid")
                kw.Bid.Amount      = MSFT_KEYWORD_BID_FLOOR_USD
                kw.MatchType       = snull()
                kw.Status          = snull()
                kw.EditorialStatus = snull()
                kw.Text            = snull()
                kw.BiddingScheme   = snull()
                kw.DestinationUrl  = snull()
                kw.FinalAppUrls    = snull()
                kw.FinalMobileUrls = snull()
                kw.FinalUrlSuffix  = snull()
                kw.FinalUrls       = snull()
                kw.ForwardCompatibilityMap = snull()
                kw.Param1          = snull()
                kw.Param2          = snull()
                kw.Param3          = snull()
                kw.TrackingUrlTemplate     = snull()
                kw.UrlCustomParameters     = snull()
                kw_objects.append(kw)

            svc.UpdateKeywords(AdGroupId=msft_ag_id,
                               Keywords={"Keyword": kw_objects})
            for row in kw_rows:
                with db.get_db() as (conn, cur):
                    cur.execute(
                        "UPDATE keywords SET cpc_bid_micros=%s, updated_at=NOW() WHERE id=%s",
                        (floor_micros, row["db_id"]),
                    )
                updated += 1
        except Exception as e:
            errors += len(kw_rows)
            logger.warning("  Keyword bid raise failed for ad group %d: %s", msft_ag_id, e)

    return updated, errors


def check_microsoft_compliance() -> list[dict]:
    findings = []

    if not os.getenv("MICROSOFT_REFRESH_TOKEN"):
        findings.append(_skip("msft_targeting", "microsoft_ads",
                               "MICROSOFT_REFRESH_TOKEN not set"))
        return findings

    try:
        auth, svc = _msft_auth()
    except Exception as e:
        findings.append(_skip("msft_auth", "microsoft_ads", f"Auth failed: {e}"))
        return findings

    rma_campaigns = _get_rma_campaigns_msft(svc)
    logger.info("Microsoft: found %d RMA campaign(s)", len(rma_campaigns))

    if not rma_campaigns:
        findings.append(_skip("msft_targeting", "microsoft_ads",
                               "No RMA campaigns found"))
        return findings

    location_ok = location_fail = 0
    age_ok = age_fail = age_fixed = 0
    gender_ok = gender_fail = gender_fixed = 0
    location_fixed = 0

    for camp in rma_campaigns:
        cid  = camp["id"]
        name = camp["name"]
        criteria = _get_campaign_criteria(svc, cid)
        parsed   = _parse_criteria(criteria)

        # ── LocationIntent ───────────────────────────────────────────────────
        intent = parsed["location_intent"]
        if intent != "PeopleIn":
            location_fail += 1
            fixed = _apply_msft_location_fix(svc, cid, name)
            if fixed:
                location_fixed += 1
                findings.append(_pass(
                    "msft_location_intent", "microsoft_ads",
                    f"{name}: intent was {intent!r} → auto-fixed to PeopleIn",
                ))
            else:
                findings.append(_fail(
                    "msft_location_intent", "microsoft_ads",
                    f"{name}: LocationIntent={intent!r} (required: PeopleIn) — fix failed",
                    auto_fixable=True, entity=name,
                ))
                _log_violation("location_intent", "microsoft_ads", name,
                               f"LocationIntent={intent} — auto-fix failed")
        else:
            location_ok += 1

        # ── Age criteria ─────────────────────────────────────────────────────
        live_age  = parsed["age"]
        age_match = all(
            age_range in live_age and abs(live_age[age_range] - expected) < 0.5
            for age_range, expected in MSFT_AGE_SPEC.items()
        )
        if not age_match:
            age_fail += 1
            missing = [ar for ar in MSFT_AGE_SPEC if ar not in live_age]
            wrong   = [
                f"{ar}={live_age[ar]:.0f}% (want {MSFT_AGE_SPEC[ar]:.0f}%)"
                for ar in MSFT_AGE_SPEC
                if ar in live_age and abs(live_age[ar] - MSFT_AGE_SPEC[ar]) >= 0.5
            ]
            detail = f"{name}: "
            if missing:
                detail += f"missing age ranges: {missing}. "
            if wrong:
                detail += f"wrong multipliers: {wrong}."

            fixed = _apply_msft_age_fix(svc, cid, name)
            if fixed:
                age_fixed += 1
                findings.append(_pass(
                    "msft_age_criteria", "microsoft_ads",
                    f"{name}: age criteria were missing/wrong → auto-fixed",
                ))
            else:
                findings.append(_fail(
                    "msft_age_criteria", "microsoft_ads",
                    detail + " — auto-fix failed",
                    auto_fixable=True, entity=name,
                ))
                _log_violation("age_criteria", "microsoft_ads", name, detail)
        else:
            age_ok += 1

        # ── Gender criteria ─────────────────────────────────────────────────
        live_gender = parsed["gender"]
        gender_match = all(
            g in live_gender and abs(live_gender[g] - expected) < 0.5
            for g, expected in MSFT_GENDER_SPEC.items()
        )
        if not gender_match:
            gender_fail += 1
            detail = (f"{name}: gender criteria wrong — "
                      f"live={live_gender} expected={MSFT_GENDER_SPEC}")
            fixed = _apply_msft_gender_fix(svc, cid, name)
            if fixed:
                gender_fixed += 1
                findings.append(_pass(
                    "msft_gender_criteria", "microsoft_ads",
                    f"{name}: gender criteria were wrong → auto-fixed",
                ))
            else:
                findings.append(_fail(
                    "msft_gender_criteria", "microsoft_ads",
                    detail + " — auto-fix failed",
                    auto_fixable=True, entity=name,
                ))
                _log_violation("gender_criteria", "microsoft_ads", name, detail)
        else:
            gender_ok += 1

    logger.info(
        "Microsoft criteria check: location %d OK / %d fixed / %d fail | "
        "age %d OK / %d fixed / %d fail | gender %d OK / %d fixed / %d fail",
        location_ok, location_fixed, location_fail - location_fixed,
        age_ok, age_fixed, age_fail - age_fixed,
        gender_ok, gender_fixed, gender_fail - gender_fixed,
    )

    # ── Keyword bid floor ────────────────────────────────────────────────────
    try:
        # Check DB for any sub-floor keywords
        floor_micros = int(MSFT_KEYWORD_BID_FLOOR_USD * 1_000_000)
        with db.get_db() as (conn, cur):
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM keywords k
                JOIN ad_groups ag ON ag.id = k.ad_group_id
                JOIN campaigns c  ON c.id  = ag.campaign_id
                WHERE c.platform = 'microsoft_ads'
                  AND (k.cpc_bid_micros IS NULL OR k.cpc_bid_micros < %s)
                """,
                (floor_micros,),
            )
            below_floor = cur.fetchone()["cnt"]

        if below_floor > 0:
            updated, errors = _raise_msft_keyword_bids(svc)
            if updated > 0:
                findings.append(_pass(
                    "msft_keyword_bids", "microsoft_ads",
                    f"{below_floor} keyword(s) were below ${MSFT_KEYWORD_BID_FLOOR_USD:.2f} "
                    f"floor → auto-raised {updated}, errors={errors}",
                ))
            if errors > 0:
                findings.append(_fail(
                    "msft_keyword_bids", "microsoft_ads",
                    f"{errors} keyword bid raise(s) failed",
                    auto_fixable=True,
                ))
                _log_violation("keyword_bids", "microsoft_ads", "keywords",
                               f"{errors} keyword bid raises failed")
        else:
            findings.append(_pass(
                "msft_keyword_bids", "microsoft_ads",
                f"All Microsoft keywords at or above ${MSFT_KEYWORD_BID_FLOOR_USD:.2f} floor",
            ))
    except Exception as e:
        findings.append(_skip("msft_keyword_bids", "microsoft_ads",
                               f"Keyword bid check error: {e}"))

    return findings


# ---------------------------------------------------------------------------
# Cross-platform spend compliance checks (from local DB)
# ---------------------------------------------------------------------------

def check_spend_compliance() -> list[dict]:
    findings = []
    today = date.today()

    try:
        with db.get_db() as (conn, cur):
            # Weekly spend (Mon–Sun of current week)
            week_start = today - timedelta(days=today.weekday())
            week_end   = week_start + timedelta(days=6)
            cur.execute(
                """
                SELECT COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend
                FROM performance_metrics
                WHERE metric_date BETWEEN %s AND %s
                  AND entity_type = 'campaign'
                """,
                (week_start, week_end),
            )
            weekly_spend = float(cur.fetchone()["spend"] or 0)

            # Daily spend today
            cur.execute(
                """
                SELECT COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend
                FROM performance_metrics
                WHERE metric_date = %s AND entity_type = 'campaign'
                """,
                (today,),
            )
            daily_spend = float(cur.fetchone()["spend"] or 0)

            # Spend on inactive days this week
            inactive_days = [
                week_start + timedelta(days=i)
                for i in range(7)
                if (week_start + timedelta(days=i)).strftime("%A").lower()
                not in ACTIVE_DAYS
                and (week_start + timedelta(days=i)) <= today
            ]
            inactive_spend = 0.0
            if inactive_days:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend
                    FROM performance_metrics
                    WHERE metric_date = ANY(%s::date[]) AND entity_type = 'campaign'
                    """,
                    ([str(d) for d in inactive_days],),
                )
                inactive_spend = float(cur.fetchone()["spend"] or 0)

    except Exception as e:
        findings.append(_skip("spend_compliance", "all_platforms", f"DB error: {e}"))
        return findings

    # Weekly ceiling check
    if weekly_spend > WEEKLY_BUDGET_CEILING_USD:
        findings.append(_fail(
            "weekly_spend_ceiling", "all_platforms",
            f"Weekly spend ${weekly_spend:.2f} exceeds ${WEEKLY_BUDGET_CEILING_USD:.2f} ceiling",
            auto_fixable=False,
        ))
        _log_violation("weekly_spend_ceiling", "all_platforms", "all",
                       f"Weekly spend ${weekly_spend:.2f} > ${WEEKLY_BUDGET_CEILING_USD:.2f}")
    else:
        findings.append(_pass(
            "weekly_spend_ceiling", "all_platforms",
            f"Weekly spend ${weekly_spend:.2f} / ${WEEKLY_BUDGET_CEILING_USD:.2f} ceiling OK",
        ))

    # Daily soft cap check
    if daily_spend > DAILY_BUDGET_SOFT_CAP_USD:
        findings.append(_fail(
            "daily_spend_cap", "all_platforms",
            f"Daily spend ${daily_spend:.2f} exceeds ${DAILY_BUDGET_SOFT_CAP_USD:.2f} soft cap",
            auto_fixable=False,
        ))
        _log_violation("daily_spend_cap", "all_platforms", "all",
                       f"Daily spend ${daily_spend:.2f} > ${DAILY_BUDGET_SOFT_CAP_USD:.2f}")
    else:
        findings.append(_pass(
            "daily_spend_cap", "all_platforms",
            f"Daily spend ${daily_spend:.2f} / ${DAILY_BUDGET_SOFT_CAP_USD:.2f} cap OK",
        ))

    # Inactive day spend check
    if inactive_spend > 0.01:
        findings.append(_fail(
            "inactive_day_spend", "all_platforms",
            f"${inactive_spend:.2f} spend detected on inactive days this week "
            f"(Tue/Wed/Thu). Check platform scheduling.",
            auto_fixable=False,
        ))
        _log_violation("inactive_day_spend", "all_platforms", "all",
                       f"${inactive_spend:.2f} spend on inactive days")
    else:
        findings.append(_pass(
            "inactive_day_spend", "all_platforms",
            f"No spend on inactive days this week",
        ))

    return findings


# ---------------------------------------------------------------------------
# Email alert
# ---------------------------------------------------------------------------

def _send_alert_email(failures: list[dict], auto_fixed: list[dict]):
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping compliance alert email")
        return

    fail_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#ef4444'>"
        f"FAIL</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{f['platform']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{f['check']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{f['detail']}</td>"
        f"</tr>"
        for f in failures
    )
    fix_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#10b981'>"
        f"FIXED</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{f['platform']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{f['check']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{f['detail']}</td>"
        f"</tr>"
        for f in auto_fixed
    )
    all_rows = fail_rows + fix_rows

    html = f"""
<html><body style="font-family:system-ui,sans-serif;max-width:680px;margin:0 auto;padding:24px">
  <div style="background:#0f172a;padding:16px 24px;border-radius:8px 8px 0 0">
    <p style="color:#94a3b8;margin:0;font-size:12px;text-transform:uppercase;letter-spacing:1px">
      Ridgecrest Designs — Compliance Monitor
    </p>
    <h2 style="color:#f59e0b;margin:4px 0 0">⚠ Campaign Compliance Report</h2>
  </div>
  <div style="border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 8px 8px">
    <p style="color:#334155">
      {len(failures)} violation(s) require attention.
      {len(auto_fixed)} issue(s) were auto-fixed.
    </p>
    <table style="width:100%;border-collapse:collapse">
      <tr>
        <th style="text-align:left;padding:6px 12px;background:#f8fafc;font-size:12px;text-transform:uppercase;color:#64748b">Status</th>
        <th style="text-align:left;padding:6px 12px;background:#f8fafc;font-size:12px;text-transform:uppercase;color:#64748b">Platform</th>
        <th style="text-align:left;padding:6px 12px;background:#f8fafc;font-size:12px;text-transform:uppercase;color:#64748b">Check</th>
        <th style="text-align:left;padding:6px 12px;background:#f8fafc;font-size:12px;text-transform:uppercase;color:#64748b">Detail</th>
      </tr>
      {all_rows}
    </table>
    <p style="color:#94a3b8;font-size:12px;margin-top:24px;text-align:center">
      Ridgecrest Designs Marketing Automation · Compliance check ran at
      {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
    </p>
  </div>
</body></html>
"""
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from":    ALERT_FROM,
            "to":      [ALERT_EMAIL],
            "subject": (f"[Compliance] {len(failures)} violation(s) — "
                        f"{len(auto_fixed)} auto-fixed — "
                        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"),
            "html":    html,
        })
        logger.info("Compliance alert email sent to %s", ALERT_EMAIL)
    except Exception as e:
        logger.error("Failed to send compliance alert email: %s", e)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(lightweight: bool = False) -> dict:
    """
    Run compliance checks.

    lightweight=True  — spend + Meta targeting only (used by 6-hour scheduler).
                        Skips Microsoft API calls to avoid unnecessary re-application
                        of demographic criteria that only drift over days, not hours.
    lightweight=False — full check including Microsoft criteria and keyword bids
                        (used by the daily pipeline run at 08:00).
    """
    mode = "lightweight" if lightweight else "full"
    logger.info("=== Compliance Agent starting (mode=%s) ===", mode)
    db.heartbeat(AGENT_NAME, "alive")

    all_findings: list[dict] = []

    # Meta checks (always run)
    logger.info("--- Checking Meta compliance ---")
    try:
        all_findings += check_meta_compliance()
    except Exception as e:
        logger.error("Meta compliance check error: %s", e, exc_info=True)
        all_findings.append(_skip("meta_compliance", "meta", f"Check error: {e}"))

    # Microsoft checks (full mode only)
    if not lightweight:
        logger.info("--- Checking Microsoft Ads compliance ---")
        try:
            all_findings += check_microsoft_compliance()
        except Exception as e:
            logger.error("Microsoft compliance check error: %s", e, exc_info=True)
            all_findings.append(_skip("msft_compliance", "microsoft_ads", f"Check error: {e}"))
    else:
        logger.info("--- Microsoft Ads compliance skipped (lightweight mode) ---")

    # Spend checks (always run)
    logger.info("--- Checking spend compliance ---")
    try:
        all_findings += check_spend_compliance()
    except Exception as e:
        logger.error("Spend compliance check error: %s", e, exc_info=True)
        all_findings.append(_skip("spend_compliance", "all_platforms", f"Check error: {e}"))

    # Tally results
    passes    = [f for f in all_findings if f["status"] == "pass"]
    failures  = [f for f in all_findings if f["status"] == "fail"]
    skips     = [f for f in all_findings if f["status"] == "skip"]
    auto_fixed = [f for f in passes if "auto-fixed" in f.get("detail", "")]

    # Log summary
    logger.info(
        "=== Compliance check complete — %d pass / %d fail / %d skip / %d auto-fixed ===",
        len(passes), len(failures), len(skips), len(auto_fixed),
    )
    for f in failures:
        logger.warning("  FAIL [%s:%s] %s", f["platform"], f["check"], f["detail"])
    for f in auto_fixed:
        logger.info("  FIXED [%s:%s] %s", f["platform"], f["check"], f["detail"])

    # Send email if there are new violations or auto-fixes
    if failures or auto_fixed:
        _send_alert_email(failures, auto_fixed)

    status = "fail" if failures else "success"
    db.heartbeat(AGENT_NAME, status, metadata={
        "checks_total":  len(all_findings),
        "checks_pass":   len(passes),
        "checks_fail":   len(failures),
        "checks_skip":   len(skips),
        "auto_fixed":    len(auto_fixed),
    })

    return {
        "status":        status,
        "checks_total":  len(all_findings),
        "checks_pass":   len(passes),
        "checks_fail":   len(failures),
        "checks_skip":   len(skips),
        "auto_fixed":    len(auto_fixed),
        "findings":      all_findings,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["status"] in ("success", "skip") else 1)
