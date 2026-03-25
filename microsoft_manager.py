"""
Microsoft Manager Agent
=======================
Manages the live Microsoft Ads account for Ridgecrest Designs.
Two primary responsibilities:

1. CAMPAIGN ACTIVATION
   Enables priority campaigns that are PAUSED in Microsoft but marked
   ENABLED in the DB (set by google_ads_builder.py per CLAUDE.md priority).
   Priority order matches CLAUDE.md §6:
     Priority 1: Design Build, Custom Home, Custom Home Builder
     Priority 2: Whole House Remodel
     Priority 3: Kitchen Remodel, Bathroom Remodel, Master Bathroom Remodel

2. BID OPTIMIZATION
   Reads ad group performance from DB (written by microsoft_sync) and applies
   CPL-based bid adjustments via the Microsoft Ads API.

All actions are logged to optimization_actions with applied=False unless
MSFT_MANAGER_AUTO_APPLY=true is set.

Run standalone:  python microsoft_manager.py
"""

import json
import logging
import os
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [microsoft_manager] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME    = "microsoft_manager"
PLATFORM      = "microsoft_ads"
ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))
CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID", "")
DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
REDIRECT_URI  = "https://login.microsoftonline.com/common/oauth2/nativeclient"
AUTO_APPLY    = os.getenv("MSFT_MANAGER_AUTO_APPLY", "false").lower() == "true"

# Strategy constants (CLAUDE.md)
TARGET_CPL_LOW    = 150.0
TARGET_CPL_HIGH   = 500.0
TARGET_CPL_IDEAL  = 300.0
PAUSE_SPEND_FLOOR = 30.0     # matches CLAUDE.md §11
BID_INCREASE_PCT  = 0.15     # +15%
BID_DECREASE_PCT  = 0.20     # −20%
LOOKBACK_DAYS     = 7

# Ad schedule — pause on Tue/Wed/Thu, active on Fri/Sat/Sun/Mon (CLAUDE.md §8)
# Microsoft Ads DayTime bid modifier criteria are not compatible with
# EnhancedCpc bidding. Use campaign-level pause/resume by day of week
# (same approach as meta_manager.py).
ACTIVE_DAYS = {"friday", "saturday", "sunday", "monday"}

# Campaigns that should be ENABLED (Priority 1–3 per CLAUDE.md §6)
PRIORITY_ENABLED_THEMES = {
    "Design Build",
    "Custom Home",
    "Custom Home Builder",
    "Whole House Remodel",
    "Kitchen Remodel",
    "Bathroom Remodel",
    "Master Bathroom Remodel",
}


# ---------------------------------------------------------------------------
# Microsoft Ads API auth
# ---------------------------------------------------------------------------

def _refresh_token() -> tuple[str, int]:
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
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
    # Resolve customer ID
    from bingads import ServiceClient
    try:
        svc = ServiceClient("CustomerManagementService", 13, auth, "production")
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


def _get_camp_service(auth):
    from bingads import ServiceClient
    return ServiceClient("CampaignManagementService", 13, auth, "production")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_rma_campaigns() -> list[dict]:
    """
    Return all [RMA] Microsoft campaigns from DB with their current status
    and the theme name (extracted from campaign name).
    """
    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, google_campaign_id, name, status
            FROM campaigns
            WHERE platform = 'microsoft_ads'
              AND managed_by = 'claude_code'
              AND name LIKE '[RMA]%%'
            ORDER BY name
            """,
        )
        rows = []
        for r in cur.fetchall():
            # Extract theme: "[RMA] Design Build | Ridgecrest Marketing" → "Design Build"
            name = r["name"]
            theme = name.replace("[RMA] ", "").split(" | ")[0].strip()
            rows.append({
                "db_id":       r["id"],
                "external_id": r["google_campaign_id"],   # e.g. "msft_524025145"
                "name":        name,
                "theme":       theme,
                "db_status":   r["status"],
                "msft_id":     int(r["google_campaign_id"].replace("msft_", "")),
            })
        return rows


def _get_adgroup_performance(lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """7-day aggregated performance per Microsoft ad group."""
    since = date.today() - timedelta(days=lookback_days)
    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT
                ag.id                          AS ag_db_id,
                ag.google_ad_group_id          AS external_id,
                ag.name                        AS name,
                ag.cpc_bid_micros              AS current_bid_micros,
                c.id                           AS camp_db_id,
                c.name                         AS campaign_name,
                COALESCE(SUM(pm.clicks),0)                AS clicks,
                COALESCE(SUM(pm.conversions),0)           AS conversions,
                COALESCE(SUM(pm.cost_micros)/1000000.0,0) AS spend_usd
            FROM ad_groups ag
            JOIN campaigns c ON c.id = ag.campaign_id
            LEFT JOIN performance_metrics pm
                   ON pm.entity_id = ag.id
                  AND pm.entity_type = 'ad_group'
                  AND pm.metric_date >= %s
            WHERE c.platform = 'microsoft_ads'
              AND c.managed_by = 'claude_code'
            GROUP BY ag.id, ag.google_ad_group_id, ag.name, ag.cpc_bid_micros,
                     c.id, c.name
            """,
            (since,),
        )
        return [dict(r) for r in cur.fetchall()]


def _update_db_campaign_status(db_id: int, status: str):
    with db.get_db() as (conn, cur):
        cur.execute(
            "UPDATE campaigns SET status=%s, updated_at=NOW() WHERE id=%s",
            (status, db_id),
        )


def _update_db_adgroup_bid(ag_db_id: int, new_bid_micros: int):
    with db.get_db() as (conn, cur):
        cur.execute(
            "UPDATE ad_groups SET cpc_bid_micros=%s, updated_at=NOW() WHERE id=%s",
            (new_bid_micros, ag_db_id),
        )


# ---------------------------------------------------------------------------
# Campaign activation
# ---------------------------------------------------------------------------

def _get_live_campaign_statuses(auth, msft_ids: list[int]) -> dict[int, str]:
    """Fetch current status for a list of Microsoft campaign IDs."""
    if not msft_ids:
        return {}
    try:
        svc = _get_camp_service(auth)
        resp = svc.GetCampaignsByIds(
            AccountId=ACCOUNT_ID,
            CampaignIds={"long": msft_ids},
            CampaignType="Search",
        )
        # GetCampaignsByIds returns resp.Campaigns (plural); fall back to
        # resp.Campaign in case SDK version differs from GetCampaignsByAccountId.
        camps_obj = getattr(resp, "Campaigns", None) or getattr(resp, "Campaign", None)
        if not camps_obj:
            return {}
        raw = (list(camps_obj.Campaign)
               if hasattr(camps_obj, "Campaign")
               else list(camps_obj or []))
        return {int(c.Id): str(c.Status) for c in raw if c and getattr(c, "Id", None)}
    except Exception as e:
        logger.warning("Could not fetch campaign statuses: %s", e)
        return {}


def _activate_campaign(auth, msft_id: int, name: str, db_id: int,
                        auto_apply: bool) -> dict:
    """Set a Microsoft campaign status to Active."""
    action = {
        "type":    "activate_campaign",
        "target":  name,
        "msft_id": msft_id,
        "applied": False,
    }
    if auto_apply:
        try:
            svc = _get_camp_service(auth)
            camp = svc.factory.create("Campaign")
            camp.Id     = msft_id
            camp.Status = "Active"
            # Suds initializes enum-wrapper objects (EntityScope, BudgetLimitType)
            # with value=None, which Microsoft serializes as '' and rejects as invalid.
            # Set them to valid enum strings so the SOAP request is well-formed.
            camp.BidStrategyScope = "Account"
            camp.BudgetType       = "DailyBudgetStandard"
            camp.BiddingScheme    = svc.factory.create("EnhancedCpcBiddingScheme")
            svc.UpdateCampaigns(AccountId=ACCOUNT_ID,
                                Campaigns={"Campaign": [camp]})
            action["applied"] = True
            _update_db_campaign_status(db_id, "ENABLED")
            logger.info("  Activated campaign: %s (msft_id=%d)", name, msft_id)
        except Exception as e:
            action["error"] = str(e)
            logger.error("  Failed to activate %s: %s", name, e)
    else:
        logger.info("  [PENDING] Would activate: %s (msft_id=%d)", name, msft_id)

    # Only log to optimization_actions if not already pending (prevents accumulation)
    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT id FROM optimization_actions
               WHERE action_type='activate_campaign' AND entity_id=%s AND applied=false
               LIMIT 1""",
            (db_id,),
        )
        already_pending = cur.fetchone()

    if not already_pending:
        db.log_action(
            agent_name=AGENT_NAME, action_type="activate_campaign",
            entity_type="campaign", entity_id=db_id,
            before={"status": "Paused"}, after={"status": "Active"},
            reason="Priority campaign in CLAUDE.md ENABLED list",
            google_entity_id=f"msft_{msft_id}",
        )
    return action


def activate_priority_campaigns(auth, auto_apply: bool) -> list[dict]:
    """
    Find RMA campaigns that should be ENABLED per CLAUDE.md priority
    but are currently Paused in Microsoft, and activate them.
    Only runs on active days (Fri/Sat/Sun/Mon) — skips on Tue/Wed/Thu.
    """
    from datetime import date as _date
    today = _date.today().strftime("%A").lower()
    if today not in ACTIVE_DAYS:
        logger.info("Campaign activation skipped — today (%s) is an inactive day", today.title())
        return []

    rma_campaigns = _get_rma_campaigns()
    priority_camps = [c for c in rma_campaigns
                      if c["theme"] in PRIORITY_ENABLED_THEMES]

    if not priority_camps:
        logger.info("No priority campaigns found in DB")
        return []

    msft_ids = [c["msft_id"] for c in priority_camps]
    live_statuses = _get_live_campaign_statuses(auth, msft_ids)

    actions = []
    for camp in priority_camps:
        mid   = camp["msft_id"]
        live  = live_statuses.get(mid, "Unknown")
        logger.info("  [%s] %s — live=%s db=%s",
                    camp["theme"], camp["name"], live, camp["db_status"])

        if live in ("Paused", "Unknown") and camp["db_status"] == "ENABLED":
            actions.append(
                _activate_campaign(auth, mid, camp["name"], camp["db_id"], auto_apply)
            )
        elif live == "Active":
            logger.info("    Already active — no action needed")

    return actions


# ---------------------------------------------------------------------------
# Day scheduling — pause/resume by day of week (mirrors meta_manager.py)
# ---------------------------------------------------------------------------

def _enforce_active_days(auth, auto_apply: bool) -> list[dict]:
    """
    Pause all RMA campaigns on inactive days (Tue/Wed/Thu).
    Active days (Fri/Sat/Sun/Mon) are handled by activate_priority_campaigns.

    Microsoft Ads DayTimeCriterion bid modifiers are incompatible with
    EnhancedCpc bidding, so campaign-level pause/resume is used instead
    (same approach as meta_manager.py, CLAUDE.md §8).
    """
    from datetime import date as _date
    today = _date.today().strftime("%A").lower()
    is_active_day = today in ACTIVE_DAYS

    # On active days, activation is handled by activate_priority_campaigns.
    # On inactive days, pause all RMA campaigns.
    if is_active_day:
        logger.info("  Active day (%s) — no day-schedule pauses needed", today.title())
        return []

    rma_campaigns = _get_rma_campaigns()
    if not rma_campaigns:
        return []

    # Fetch live statuses
    msft_ids = [c["msft_id"] for c in rma_campaigns]
    live_statuses = _get_live_campaign_statuses(auth, msft_ids)

    actions = []
    svc = _get_camp_service(auth)

    for camp in rma_campaigns:
        msft_id    = camp["msft_id"]
        name       = camp["name"]
        live_status = live_statuses.get(msft_id, "Unknown")

        if live_status == "Paused":
            continue  # already paused, nothing to do

        action = {
            "type":    "day_schedule_pause",
            "target":  name,
            "msft_id": msft_id,
            "reason":  f"CLAUDE.md §8 — today is {today.title()}, inactive day (Tue/Wed/Thu)",
            "applied": False,
        }

        if auto_apply:
            try:
                c_obj = svc.factory.create("Campaign")
                c_obj.Id            = msft_id
                c_obj.Status        = "Paused"
                c_obj.BidStrategyScope = "Account"
                c_obj.BudgetType    = "DailyBudgetStandard"
                c_obj.BiddingScheme = svc.factory.create("EnhancedCpcBiddingScheme")
                svc.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c_obj]})
                action["applied"] = True
                logger.info("  Paused (inactive day): %s (msft_id=%d)", name, msft_id)
            except Exception as e:
                action["error"] = str(e)
                logger.warning("  Pause failed for %s: %s", name, e)
        else:
            logger.info("  [PENDING] Would pause (inactive day): %s", name)

        db.log_action(
            agent_name=AGENT_NAME, action_type="day_schedule_pause",
            entity_type="campaign", entity_id=camp["db_id"],
            before={"status": live_status}, after={"status": "Paused"},
            reason=action["reason"],
            google_entity_id=f"msft_{msft_id}",
        )
        actions.append(action)

    logger.info("Day schedule (%s, inactive): %d campaign(s) paused", today.title(), len(actions))
    return actions


# ---------------------------------------------------------------------------
# Bid optimization
# ---------------------------------------------------------------------------

def _apply_keyword_bid(auth, ag_db_id: int, external_id: str,
                        current_bid_micros: int, new_bid_micros: int,
                        direction: str, reason: str, auto_apply: bool) -> dict:
    action = {
        "type":      f"bid_{direction}",
        "target":    external_id,
        "before":    f"${current_bid_micros/1_000_000:.2f}",
        "after":     f"${new_bid_micros/1_000_000:.2f}",
        "reason":    reason,
        "applied":   False,
    }
    if auto_apply:
        try:
            msft_ag_id = int(external_id.replace("msft_ag_", ""))
            svc = _get_camp_service(auth)
            ag = svc.factory.create("AdGroup")
            ag.Id          = msft_ag_id
            ag.CpcBid      = svc.factory.create("Bid")
            ag.CpcBid.Amount = new_bid_micros / 1_000_000
            svc.UpdateAdGroups(CampaignId=None, AdGroups={"AdGroup": [ag]})
            action["applied"] = True
            _update_db_adgroup_bid(ag_db_id, new_bid_micros)
            logger.info("  Bid %s for %s: $%.2f → $%.2f",
                        direction, external_id,
                        current_bid_micros/1_000_000, new_bid_micros/1_000_000)
        except Exception as e:
            action["error"] = str(e)
            logger.error("  Bid update failed for %s: %s", external_id, e)
    else:
        logger.info("  [PENDING] Would %s bid for %s: $%.2f → $%.2f",
                    direction, external_id,
                    current_bid_micros/1_000_000, new_bid_micros/1_000_000)

    db.log_action(
        agent_name=AGENT_NAME, action_type=f"bid_{direction}",
        entity_type="ad_group", entity_id=ag_db_id,
        before={"cpc_bid_micros": current_bid_micros},
        after={"cpc_bid_micros": new_bid_micros},
        reason=reason,
    )
    return action


def optimize_bids(auth, auto_apply: bool) -> list[dict]:
    """Apply CPL-based bid adjustments to Microsoft ad groups with enough data."""
    ag_perf = _get_adgroup_performance()
    actions = []

    for row in ag_perf:
        spend   = float(row["spend_usd"])
        clicks  = int(row["clicks"])
        convs   = float(row["conversions"])
        bid     = int(row["current_bid_micros"])
        ext_id  = row["external_id"]
        name    = row["name"]
        cpl     = spend / convs if convs > 0 else None

        # Need minimum spend data before making bid changes
        if spend < PAUSE_SPEND_FLOOR or clicks < 20:
            continue

        # Rule 1: Pause ad group — $30+ spend, 0 conversions
        if convs == 0 and spend >= PAUSE_SPEND_FLOOR:
            reason = (f"${spend:.2f} spent over {LOOKBACK_DAYS}d with 0 conversions "
                      f"— pausing to stop waste")
            logger.warning("  [PAUSE ADGROUP] %s — %s", name, reason)
            # Log as pause action (actual pause not applied here as adgroup pauses
            # can affect all keywords; flag for human review)
            db.log_action(
                agent_name=AGENT_NAME, action_type="flag_pause_adgroup",
                entity_type="ad_group", entity_id=row["ag_db_id"],
                before={"spend": spend, "conversions": 0},
                after={},
                reason=reason,
            )
            actions.append({"type": "flag_pause_adgroup", "target": name,
                             "reason": reason, "applied": False})
            continue

        # Rule 2: Bid decrease — CPL > $500
        if cpl is not None and cpl > TARGET_CPL_HIGH and bid > 500_000:
            new_bid = max(int(bid * (1 - BID_DECREASE_PCT)), 500_000)  # floor $0.50
            reason  = (f"CPL ${cpl:.2f} > ceiling ${TARGET_CPL_HIGH:.0f}; "
                       f"decreasing bid by {int(BID_DECREASE_PCT*100)}%")
            actions.append(_apply_keyword_bid(
                auth, row["ag_db_id"], ext_id, bid, new_bid,
                "decrease", reason, auto_apply,
            ))

        # Rule 3: Bid increase — CPL $150–$300 sweet spot
        elif cpl is not None and TARGET_CPL_LOW <= cpl <= TARGET_CPL_IDEAL:
            new_bid = int(bid * (1 + BID_INCREASE_PCT))
            reason  = (f"CPL ${cpl:.2f} in sweet spot (${TARGET_CPL_LOW:.0f}–"
                       f"${TARGET_CPL_IDEAL:.0f}); increasing bid by "
                       f"{int(BID_INCREASE_PCT*100)}%")
            actions.append(_apply_keyword_bid(
                auth, row["ag_db_id"], ext_id, bid, new_bid,
                "increase", reason, auto_apply,
            ))

    return actions


# ---------------------------------------------------------------------------
# Manual controls — budget, pause, resume, list
# ---------------------------------------------------------------------------

def _get_all_campaigns(auth) -> list[dict]:
    """Fetch all campaigns with name, status, and budget from Microsoft Ads."""
    from bingads import ServiceClient
    svc  = ServiceClient("CampaignManagementService", 13, auth, "production")
    resp = svc.GetCampaignsByAccountId(AccountId=ACCOUNT_ID, CampaignType="Search")
    raw  = (resp.Campaign.Campaign
            if resp.Campaign and hasattr(resp.Campaign, "Campaign")
            else list(resp.Campaign or []))
    campaigns = []
    for c in raw:
        budget_usd = None
        try:
            if hasattr(c, "DailyBudget") and c.DailyBudget is not None:
                budget_usd = float(c.DailyBudget)
            elif hasattr(c, "Budget") and c.Budget is not None:
                b = c.Budget
                if hasattr(b, "Amount") and b.Amount is not None:
                    budget_usd = float(b.Amount)
        except Exception:
            pass
        campaigns.append({
            "id":         int(c.Id),
            "name":       c.Name,
            "status":     str(c.Status),
            "budget_usd": budget_usd,
        })
    return campaigns


def _set_campaign_status_by_id(auth, msft_id: int, status: str, name: str):
    svc = _get_camp_service(auth)
    c   = svc.factory.create("Campaign")
    c.Id             = msft_id
    c.Status         = status
    c.BidStrategyScope = "Account"
    c.BudgetType     = "DailyBudgetStandard"
    c.BiddingScheme  = svc.factory.create("EnhancedCpcBiddingScheme")
    svc.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c]})
    logger.info("Set %s → %s", name, status)


def _set_campaign_budget_by_id(auth, msft_id: int, daily_budget_usd: float, name: str,
                               current_status: str = "Active"):
    svc = _get_camp_service(auth)
    c   = svc.factory.create("Campaign")
    c.Id               = msft_id
    c.DailyBudget      = daily_budget_usd
    c.Status           = current_status   # must be set to avoid empty enum error
    c.BidStrategyScope = "Account"
    c.BudgetType       = "DailyBudgetStandard"
    c.BiddingScheme    = svc.factory.create("EnhancedCpcBiddingScheme")
    svc.UpdateCampaigns(AccountId=ACCOUNT_ID, Campaigns={"Campaign": [c]})
    logger.info("Set budget %s → $%.2f/day", name, daily_budget_usd)


def list_campaigns():
    """Print all campaigns with live status and budget."""
    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    campaigns = _get_all_campaigns(auth)
    print(f"\n{'Status':<10} {'Budget/day':>12}  Campaign")
    print("-" * 70)
    total_daily = 0.0
    for c in sorted(campaigns, key=lambda x: x["name"]):
        budget_str = f"${c['budget_usd']:.2f}" if c["budget_usd"] is not None else "unknown"
        if c["status"].lower() == "active" and c["budget_usd"]:
            total_daily += c["budget_usd"]
        print(f"{c['status']:<10} {budget_str:>12}  {c['name']}")
    print(f"\nTotal campaigns: {len(campaigns)}")
    print(f"Active daily budget: ${total_daily:.2f}/day = ${total_daily*4:.2f}/week (4 active days)")


def pause_campaign(name_fragment: str):
    """Pause campaign(s) matching name fragment."""
    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    campaigns = _get_all_campaigns(auth)
    matched = [c for c in campaigns if name_fragment.lower() in c["name"].lower()]
    if not matched:
        logger.error("No campaigns matching '%s'", name_fragment)
        return
    for c in matched:
        _set_campaign_status_by_id(auth, c["id"], "Paused", c["name"])


def resume_campaign(name_fragment: str):
    """Resume campaign(s) matching name fragment."""
    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    campaigns = _get_all_campaigns(auth)
    matched = [c for c in campaigns if name_fragment.lower() in c["name"].lower()]
    if not matched:
        logger.error("No campaigns matching '%s'", name_fragment)
        return
    for c in matched:
        _set_campaign_status_by_id(auth, c["id"], "Active", c["name"])


def set_budget(name_fragment: str, daily_budget_usd: float):
    """Set daily budget for campaign(s) matching name fragment."""
    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    campaigns = _get_all_campaigns(auth)
    matched = [c for c in campaigns if name_fragment.lower() in c["name"].lower()]
    if not matched:
        logger.error("No campaigns matching '%s'", name_fragment)
        return
    for c in matched:
        _set_campaign_budget_by_id(auth, c["id"], daily_budget_usd, c["name"],
                                   current_status=c["status"])


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(auto_apply: bool | None = None) -> dict:
    if auto_apply is None:
        auto_apply = AUTO_APPLY

    logger.info("=== Microsoft Manager starting (auto_apply=%s) ===", auto_apply)
    db.heartbeat(AGENT_NAME, "alive")

    # Authenticate
    try:
        access_token, expires_in = _refresh_token()
        auth = _build_auth(access_token, expires_in)
        logger.info("Microsoft Ads auth OK (account %d)", ACCOUNT_ID)
    except Exception as e:
        err = f"Auth failed: {e}"
        logger.error(err)
        db.heartbeat(AGENT_NAME, "error", error=err)
        return {"platform": PLATFORM, "status": "error", "error": err}

    all_actions: list[dict] = []

    # Step 0: Enforce active days (pause on Tue/Wed/Thu; activation on active days handled in Step 1)
    logger.info("--- Step 0: Enforce Fri/Sat/Sun/Mon active days ---")
    try:
        all_actions += _enforce_active_days(auth, auto_apply)
    except Exception as e:
        logger.error("Day schedule step failed: %s", e)

    # Step 1: Activate priority campaigns
    logger.info("--- Step 1: Campaign activation ---")
    try:
        all_actions += activate_priority_campaigns(auth, auto_apply)
    except Exception as e:
        logger.error("Campaign activation failed: %s", e)

    # Step 2: Bid optimization (only useful once campaigns have data)
    logger.info("--- Step 2: Bid optimization ---")
    try:
        all_actions += optimize_bids(auth, auto_apply)
    except Exception as e:
        logger.error("Bid optimization failed: %s", e)

    # Summary
    action_counts: dict[str, int] = {}
    for a in all_actions:
        action_counts[a["type"]] = action_counts.get(a["type"], 0) + 1

    applied = sum(1 for a in all_actions if a.get("applied"))
    pending = len(all_actions) - applied

    db.heartbeat(AGENT_NAME, "success", metadata={
        "actions_total":   len(all_actions),
        "actions_applied": applied,
        "actions_pending": pending,
        "action_counts":   action_counts,
        "auto_apply":      auto_apply,
    })

    logger.info(
        "=== Microsoft Manager done — actions=%d applied=%d pending=%d ===",
        len(all_actions), applied, pending,
    )
    if action_counts:
        logger.info("  Action breakdown: %s", action_counts)

    if not auto_apply and all_actions:
        logger.info(
            "  AUTO_APPLY is off — %d action(s) logged for review. "
            "Set MSFT_MANAGER_AUTO_APPLY=true to execute automatically.",
            pending,
        )

    db.send_message(
        from_agent=AGENT_NAME,
        to_agent="orchestrator",
        message_type="optimization_complete",
        payload={
            "platform":        PLATFORM,
            "actions_total":   len(all_actions),
            "actions_applied": applied,
            "actions_pending": pending,
            "action_counts":   action_counts,
        },
    )

    return {
        "platform":        PLATFORM,
        "status":          "success",
        "actions_total":   len(all_actions),
        "actions_applied": applied,
        "actions_pending": pending,
        "action_counts":   action_counts,
        "auto_apply":      auto_apply,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Microsoft Ads Manager")
    parser.add_argument("command", nargs="?", default="run",
                        choices=["run", "list", "pause", "resume", "budget"])
    parser.add_argument("name",   nargs="?", help="Campaign name fragment")
    parser.add_argument("value",  nargs="?", help="Budget value in USD (for budget command)")
    args = parser.parse_args()

    if args.command == "list":
        list_campaigns()
    elif args.command == "pause":
        if not args.name:
            print("Usage: python microsoft_manager.py pause 'campaign name fragment'")
        else:
            pause_campaign(args.name)
    elif args.command == "resume":
        if not args.name:
            print("Usage: python microsoft_manager.py resume 'campaign name fragment'")
        else:
            resume_campaign(args.name)
    elif args.command == "budget":
        if not args.name or not args.value:
            print("Usage: python microsoft_manager.py budget 'campaign name fragment' 45.00")
        else:
            set_budget(args.name, float(args.value))
    else:
        result = run()
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result["status"] == "success" else 1)
