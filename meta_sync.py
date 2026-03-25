"""
Meta Sync Agent
===============
Pulls the last 30 days of campaign performance data from the Meta Ads API
for account act_58393749 and writes it into performance_metrics
with platform='meta'.

Run standalone:  python meta_sync.py
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
    format="%(asctime)s [meta_sync] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME    = "meta_sync"
PLATFORM      = "meta"
API_VERSION   = "v21.0"
BASE_URL      = f"https://graph.facebook.com/{API_VERSION}"
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "act_58393749")
ACCESS_TOKEN  = os.getenv("META_ACCESS_TOKEN", "")
DAYS_BACK     = 30


def _get(path: str, params: dict = None) -> dict:
    p = {"access_token": ACCESS_TOKEN}
    if params:
        p.update(params)
    r = requests.get(f"{BASE_URL}{path}", params=p, timeout=30)
    return r.json()


def _upsert_campaign(meta_campaign_id: str, name: str, status: str) -> int:
    """Upsert a Meta campaign into the campaigns table using meta_<id> as key."""
    external_id = f"meta_{meta_campaign_id}"
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO campaigns
               (google_campaign_id, name, status, platform, last_synced_at)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (google_campaign_id) DO UPDATE SET
                   name           = EXCLUDED.name,
                   status         = EXCLUDED.status,
                   platform       = EXCLUDED.platform,
                   last_synced_at = NOW(),
                   updated_at     = NOW()
               RETURNING id""",
            (external_id, name, status, PLATFORM),
        )
        return cur.fetchone()["id"]


def _upsert_metric(metric_date, entity_id: int, external_campaign_id: str,
                   impressions: int, clicks: int, conversions: float,
                   cost_micros: int, ctr: float, cpc_avg_micros: int):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO performance_metrics
               (metric_date, entity_type, entity_id, google_entity_id,
                impressions, clicks, conversions, cost_micros,
                ctr, cpc_avg_micros, platform)
               VALUES (%s,'campaign',%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                   impressions    = EXCLUDED.impressions,
                   clicks         = EXCLUDED.clicks,
                   conversions    = EXCLUDED.conversions,
                   cost_micros    = EXCLUDED.cost_micros,
                   ctr            = EXCLUDED.ctr,
                   cpc_avg_micros = EXCLUDED.cpc_avg_micros,
                   platform       = EXCLUDED.platform""",
            (metric_date, entity_id, external_campaign_id,
             impressions, clicks, conversions, cost_micros,
             ctr, cpc_avg_micros, PLATFORM),
        )


def _upsert_ad_group(campaign_db_id: int, adset_id: str, name: str, status: str,
                     daily_budget_cents: int = 0) -> int:
    """Upsert a Meta ad set into the ad_groups table."""
    external_id = f"meta_adset_{adset_id}"
    bid_micros  = daily_budget_cents * 10  # cents → micros
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ad_groups
               (google_ad_group_id, campaign_id, name, status, cpc_bid_micros, updated_at)
               VALUES (%s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_ad_group_id) DO UPDATE SET
                   name           = EXCLUDED.name,
                   status         = EXCLUDED.status,
                   cpc_bid_micros = EXCLUDED.cpc_bid_micros,
                   updated_at     = NOW()
               RETURNING id""",
            (external_id, campaign_db_id, name, status, bid_micros),
        )
        return cur.fetchone()["id"]


def _upsert_adset_metric(metric_date, ag_db_id: int, adset_id: str,
                          impressions: int, clicks: int, conversions: float,
                          cost_micros: int, ctr: float, cpc_avg_micros: int):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO performance_metrics
               (metric_date, entity_type, entity_id, google_entity_id,
                impressions, clicks, conversions, cost_micros,
                ctr, cpc_avg_micros, platform)
               VALUES (%s,'ad_group',%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                   impressions    = EXCLUDED.impressions,
                   clicks         = EXCLUDED.clicks,
                   conversions    = EXCLUDED.conversions,
                   cost_micros    = EXCLUDED.cost_micros,
                   ctr            = EXCLUDED.ctr,
                   cpc_avg_micros = EXCLUDED.cpc_avg_micros,
                   platform       = EXCLUDED.platform""",
            (metric_date, ag_db_id, f"meta_adset_{adset_id}",
             impressions, clicks, conversions, cost_micros,
             ctr, cpc_avg_micros, PLATFORM),
        )


def _sync_ad_sets(campaign_map: dict) -> dict[str, int]:
    """
    Fetch all ad sets for every known campaign and upsert into ad_groups.
    Returns {adset_id: ad_group_db_id}.
    """
    adset_map: dict[str, int] = {}
    fields = "id,name,status,daily_budget,campaign_id"

    for meta_cid, camp_info in campaign_map.items():
        resp = _get(f"/{meta_cid}/adsets", {"fields": fields, "limit": 200})
        if "error" in resp:
            logger.warning("Ad sets fetch error for campaign %s: %s",
                           meta_cid, resp["error"].get("message", resp["error"]))
            continue
        for adset in resp.get("data", []):
            adset_id    = adset["id"]
            adset_name  = adset.get("name", adset_id)
            adset_status = adset.get("status", "UNKNOWN")
            daily_budget = int(adset.get("daily_budget", 0))   # in cents
            ag_db_id = _upsert_ad_group(
                campaign_db_id=camp_info["db_id"],
                adset_id=adset_id,
                name=adset_name,
                status=adset_status,
                daily_budget_cents=daily_budget,
            )
            adset_map[adset_id] = ag_db_id

    logger.info("Ad set sync: upserted %d ad sets", len(adset_map))
    return adset_map


def _sync_adset_metrics(adset_map: dict, start_date: date, end_date: date) -> int:
    """
    Pull daily ad set level insights and write into performance_metrics.
    Returns number of rows written.
    """
    if not adset_map:
        return 0

    insight_fields = ",".join([
        "adset_id", "adset_name",
        "impressions", "inline_link_clicks", "ctr", "cpc",
        "spend", "actions",
    ])
    params = {
        "fields":         insight_fields,
        "level":          "adset",
        "time_range":     json.dumps({"since": str(start_date), "until": str(end_date)}),
        "time_increment": 1,
        "limit":          500,
    }
    resp = _get(f"/{AD_ACCOUNT_ID}/insights", params)
    if "error" in resp:
        logger.warning("Ad set insights error: %s",
                       resp["error"].get("message", resp["error"]))
        return 0

    rows = resp.get("data", [])
    paging = resp.get("paging", {})
    while paging.get("next"):
        page = requests.get(paging["next"], timeout=30).json()
        rows.extend(page.get("data", []))
        paging = page.get("paging", {})

    written = 0
    for row in rows:
        try:
            adset_id  = row.get("adset_id", "")
            date_str  = row.get("date_start")
            if not date_str or adset_id not in adset_map:
                continue

            impressions = int(row.get("impressions", 0))
            clicks      = int(row.get("inline_link_clicks", 0))
            spend_usd   = float(row.get("spend", 0))
            cost_micros = int(spend_usd * 1_000_000)
            ctr         = round(float(row.get("ctr", 0)) / 100, 6)
            cpc_usd     = float(row.get("cpc", 0))
            cpc_micros  = int(cpc_usd * 1_000_000)

            conversions = 0.0
            for action in row.get("actions", []):
                at = action.get("action_type", "")
                if at in {
                    "lead",
                    "complete_registration",
                    "onsite_conversion.lead_grouped",
                    "offsite_conversion.fb_pixel_lead",
                    "offsite_conversion.fb_pixel_purchase",
                    "submit_application",
                } or at.startswith("offsite_conversion.custom."):
                    conversions += float(action.get("value", 0))

            _upsert_adset_metric(
                metric_date    = date_str,
                ag_db_id       = adset_map[adset_id],
                adset_id       = adset_id,
                impressions    = impressions,
                clicks         = clicks,
                conversions    = conversions,
                cost_micros    = cost_micros,
                ctr            = ctr,
                cpc_avg_micros = cpc_micros,
            )
            written += 1
        except Exception as e:
            logger.warning("Ad set metric row error: %s", e)

    logger.info("Ad set metrics: wrote %d rows", written)
    return written


def run() -> dict:
    logger.info("=== Meta Sync starting (last %d days) ===", DAYS_BACK)
    db.heartbeat(AGENT_NAME, "alive")

    end_date   = date.today()
    start_date = end_date - timedelta(days=DAYS_BACK - 1)

    if not ACCESS_TOKEN:
        err = "META_ACCESS_TOKEN not set"
        logger.error(err)
        db.heartbeat(AGENT_NAME, "error", error=err)
        return {"platform": PLATFORM, "status": "error", "error": err}

    # Fetch campaign list
    fields = "id,name,status,objective"
    camp_resp = _get(f"/{AD_ACCOUNT_ID}/campaigns", {"fields": fields, "limit": 200})
    if "error" in camp_resp:
        err = camp_resp["error"].get("message", str(camp_resp["error"]))
        logger.error("Campaign list error: %s", err)
        db.heartbeat(AGENT_NAME, "error", error=err)
        return {"platform": PLATFORM, "status": "error", "error": err}

    campaigns = camp_resp.get("data", [])
    logger.info("Found %d campaign(s) in Meta account", len(campaigns))

    # Build campaign id → db id map
    campaign_map: dict[str, dict] = {}
    for c in campaigns:
        cid = c["id"]
        db_id = _upsert_campaign(cid, c.get("name", cid), c.get("status", "UNKNOWN"))
        campaign_map[cid] = {"db_id": db_id, "name": c.get("name", cid)}

    # Fetch daily insights for the date range
    insight_fields = ",".join([
        "campaign_id", "campaign_name",
        "impressions", "inline_link_clicks", "ctr", "cpc",
        "spend", "actions",
    ])
    params = {
        "fields":         insight_fields,
        "level":          "campaign",
        "time_range":     json.dumps({"since": str(start_date), "until": str(end_date)}),
        "time_increment": 1,
        "limit":          500,
    }
    ins_resp = _get(f"/{AD_ACCOUNT_ID}/insights", params)
    if "error" in ins_resp:
        err = ins_resp["error"].get("message", str(ins_resp["error"]))
        logger.error("Insights error: %s", err)
        db.heartbeat(AGENT_NAME, "error", error=err)
        return {"platform": PLATFORM, "status": "error", "error": err}

    rows = ins_resp.get("data", [])
    # Handle pagination
    paging = ins_resp.get("paging", {})
    while paging.get("next"):
        page = requests.get(paging["next"], timeout=30).json()
        rows.extend(page.get("data", []))
        paging = page.get("paging", {})

    logger.info("Fetched %d daily insight row(s) from Meta", len(rows))

    rows_written = 0
    errors = []

    for row in rows:
        try:
            cid        = row.get("campaign_id", "")
            date_str   = row.get("date_start")      # YYYY-MM-DD
            if not date_str:
                continue

            impressions = int(row.get("impressions", 0))
            clicks      = int(row.get("inline_link_clicks", 0))
            spend_usd   = float(row.get("spend", 0))
            cost_micros = int(spend_usd * 1_000_000)
            ctr         = round(float(row.get("ctr", 0)) / 100, 6)  # Meta returns % string
            cpc_usd     = float(row.get("cpc", 0))
            cpc_micros  = int(cpc_usd * 1_000_000)

            # Count lead/purchase/submit actions as conversions.
            # Includes offsite_conversion.custom.* for URL-based Meta custom conversions
            # (e.g. custom conversion IDs 1274199281573639 / 2010554443142598).
            # Also counts complete_registration (Booking Confirmed pixel event) and
            # onsite_conversion.lead_grouped (Meta's grouped on-site lead reporting),
            # both confirmed missing from Ads Manager reconciliation on 2026-03-22.
            conversions = 0.0
            for action in row.get("actions", []):
                at = action.get("action_type", "")
                if at in {
                    "lead",
                    "complete_registration",
                    "onsite_conversion.lead_grouped",
                    "offsite_conversion.fb_pixel_lead",
                    "offsite_conversion.fb_pixel_purchase",
                    "submit_application",
                } or at.startswith("offsite_conversion.custom."):
                    conversions += float(action.get("value", 0))

            # Upsert campaign if not already seen (covers campaigns not in initial list)
            if cid not in campaign_map:
                name = row.get("campaign_name", cid)
                db_id = _upsert_campaign(cid, name, "UNKNOWN")
                campaign_map[cid] = {"db_id": db_id, "name": name}

            _upsert_metric(
                metric_date          = date_str,
                entity_id            = campaign_map[cid]["db_id"],
                external_campaign_id = f"meta_{cid}",
                impressions          = impressions,
                clicks               = clicks,
                conversions          = conversions,
                cost_micros          = cost_micros,
                ctr                  = ctr,
                cpc_avg_micros       = cpc_micros,
            )
            rows_written += 1
        except Exception as e:
            errors.append(str(e))
            logger.warning("Row error: %s", e)

    # ── Ad set level sync ─────────────────────────────────────────────────
    adset_map = {}
    adset_rows = 0
    try:
        adset_map  = _sync_ad_sets(campaign_map)
        adset_rows = _sync_adset_metrics(adset_map, start_date, end_date)
    except Exception as e:
        logger.warning("Ad set sync failed (non-fatal): %s", e)

    status = "error" if errors and rows_written == 0 else "success"
    db.heartbeat(AGENT_NAME, status, metadata={
        "rows_written":     rows_written,
        "adset_rows":       adset_rows,
        "campaigns_synced": len(campaign_map),
        "adsets_synced":    len(adset_map),
        "date_range":       f"{start_date} to {end_date}",
    })
    logger.info(
        "=== Meta Sync done — campaigns=%d adsets=%d camp_rows=%d adset_rows=%d errors=%d ===",
        len(campaign_map), len(adset_map), rows_written, adset_rows, len(errors),
    )
    return {
        "platform":         PLATFORM,
        "status":           status,
        "campaigns_synced": len(campaign_map),
        "adsets_synced":    len(adset_map),
        "rows_written":     rows_written,
        "adset_rows":       adset_rows,
        "date_range":       f"{start_date} to {end_date}",
        "errors":           errors,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["status"] == "success" else 1)
