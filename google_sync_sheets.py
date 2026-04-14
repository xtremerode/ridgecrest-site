"""
google_sync_sheets.py
=====================
Reads Google Ads performance data from a Google Sheet (populated by a
Google Ads Script running on schedule) and upserts it into performance_metrics.

No developer token required. Uses the spreadsheets OAuth scope only.

Run standalone:  python3 google_sync_sheets.py
"""
import logging
import os
import sys
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import db
import urllib.request as ur
import urllib.parse as up

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [google_sync_sheets] %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

PLATFORM    = "google_ads"
SHEETS_ID   = os.getenv("GOOGLE_SHEETS_ID", "")
CLIENT_ID   = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SEC  = os.getenv("GOOGLE_CLIENT_SECRET", "")
REFRESH_TOK = os.getenv("GOOGLE_REFRESH_TOKEN", "")


def _get_access_token():
    """Exchange refresh token for access token."""
    data = up.urlencode({
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SEC,
        "refresh_token": REFRESH_TOK,
        "grant_type":    "refresh_token",
    }).encode()
    req = ur.Request("https://oauth2.googleapis.com/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with ur.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode()).get("access_token", "")


def _sheets_get(access_token, sheet_id, range_name):
    """Fetch a range from Google Sheets API v4."""
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        + up.quote(sheet_id, safe="")
        + "/values/"
        + up.quote(range_name, safe="")
    )
    req = ur.Request(url, headers={"Authorization": "Bearer " + access_token})
    try:
        with ur.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except ur.HTTPError as e:
        body = e.read().decode()
        logger.error("Sheets API error %s: %s", e.code, body[:300])
        return None


def _upsert_campaign(google_campaign_id, name, status, daily_budget_micros,
                     bidding_strategy):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO campaigns
               (google_campaign_id, name, status, daily_budget_micros,
                bidding_strategy, platform, last_synced_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_campaign_id) DO UPDATE SET
                   name                = EXCLUDED.name,
                   status              = EXCLUDED.status,
                   daily_budget_micros = EXCLUDED.daily_budget_micros,
                   bidding_strategy    = EXCLUDED.bidding_strategy,
                   platform            = EXCLUDED.platform,
                   last_synced_at      = NOW(),
                   updated_at          = NOW()
               RETURNING id""",
            (google_campaign_id, name, status, daily_budget_micros,
             bidding_strategy, PLATFORM),
        )
        return cur.fetchone()["id"]


def _upsert_metric(metric_date, entity_id, google_entity_id,
                   impressions, clicks, conversions, cost_micros,
                   ctr, cpc_avg_micros, cpa_micros, conversion_rate,
                   impression_share):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO performance_metrics
               (metric_date, entity_type, entity_id, google_entity_id,
                impressions, clicks, conversions, cost_micros,
                ctr, cpc_avg_micros, cpa_micros, conversion_rate,
                impression_share, platform, created_at)
               VALUES (%s,'campaign',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
               ON CONFLICT (metric_date, entity_type, entity_id)
               DO UPDATE SET
                   impressions      = EXCLUDED.impressions,
                   clicks           = EXCLUDED.clicks,
                   conversions      = EXCLUDED.conversions,
                   cost_micros      = EXCLUDED.cost_micros,
                   ctr              = EXCLUDED.ctr,
                   cpc_avg_micros   = EXCLUDED.cpc_avg_micros,
                   cpa_micros       = EXCLUDED.cpa_micros,
                   conversion_rate  = EXCLUDED.conversion_rate,
                   impression_share = EXCLUDED.impression_share,
                   platform         = EXCLUDED.platform""",
            (metric_date, entity_id, google_entity_id,
             impressions, clicks, conversions, cost_micros,
             ctr, cpc_avg_micros, cpa_micros, conversion_rate,
             impression_share, PLATFORM),
        )


def _safe_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return 0.0


def _safe_int(v):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except Exception:
        return 0


def sync_campaign_performance(access_token):
    """Read campaign_perf sheet tab and upsert into DB."""
    data = _sheets_get(access_token, SHEETS_ID, "campaign_perf!A:Z")
    if not data or "values" not in data:
        logger.warning("campaign_perf tab is empty or unreadable")
        return 0

    rows = data["values"]
    if len(rows) < 2:
        logger.warning("campaign_perf: no data rows (only header or empty)")
        return 0

    header = [h.strip().lower() for h in rows[0]]
    logger.info("campaign_perf columns: %s", header)

    def col(row, name, default=""):
        try:
            idx = header.index(name)
            return row[idx] if idx < len(row) else default
        except ValueError:
            return default

    upserted = 0
    for row in rows[1:]:
        if not row:
            continue
        try:
            metric_date      = col(row, "date")
            campaign_id_str  = col(row, "campaign_id")
            campaign_name    = col(row, "campaign_name")
            impressions      = _safe_int(col(row, "impressions"))
            clicks           = _safe_int(col(row, "clicks"))
            cost_micros      = _safe_int(col(row, "cost_micros"))
            conversions      = _safe_float(col(row, "conversions"))
            ctr              = _safe_float(col(row, "ctr"))
            avg_cpc_micros   = _safe_int(col(row, "avg_cpc_micros"))
            imp_share_raw    = col(row, "impression_share", "0")
            # impression_share comes as e.g. "0.45" or "< 10%" or "--"
            if "%" in str(imp_share_raw):
                imp_share = _safe_float(str(imp_share_raw).replace("%","").replace("<","").replace(">","").strip()) / 100.0
            else:
                imp_share = _safe_float(imp_share_raw)

            if not metric_date or not campaign_id_str:
                continue

            cpa_micros = int(cost_micros / conversions) if conversions > 0 else None
            conv_rate  = (conversions / clicks) if clicks > 0 else 0.0

            entity_id = _upsert_campaign(
                campaign_id_str, campaign_name, "ENABLED",
                daily_budget_micros=0,
                bidding_strategy="MANUAL_CPC",
            )
            _upsert_metric(
                metric_date=metric_date,
                entity_id=entity_id,
                google_entity_id=campaign_id_str,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                cost_micros=cost_micros,
                ctr=ctr,
                cpc_avg_micros=avg_cpc_micros,
                cpa_micros=cpa_micros,
                conversion_rate=conv_rate,
                impression_share=imp_share,
            )
            upserted += 1
        except Exception as e:
            logger.error("Row error: %s | row: %s", e, row)

    return upserted


def sync_search_terms(access_token):
    """Read search_terms sheet tab and store in a simple JSON file for reporting."""
    data = _sheets_get(access_token, SHEETS_ID, "search_terms!A:Z")
    if not data or "values" not in data:
        logger.warning("search_terms tab is empty or unreadable")
        return 0

    rows = data["values"]
    if len(rows) < 2:
        return 0

    # Store as JSON in the agent directory for ad-hoc queries
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "ridgecrest-agency", "performance", "search_terms_latest.json")
    header = rows[0]
    records = [dict(zip(header, row)) for row in rows[1:] if row]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"synced_at": datetime.now(timezone.utc).isoformat(),
                   "count": len(records), "rows": records}, f, indent=2)
    logger.info("search_terms: %d rows saved to %s", len(records), out_path)
    return len(records)


def sync_keywords(access_token):
    """Read keyword_perf sheet tab and save for reporting."""
    data = _sheets_get(access_token, SHEETS_ID, "keyword_perf!A:Z")
    if not data or "values" not in data:
        logger.warning("keyword_perf tab is empty or unreadable")
        return 0

    rows = data["values"]
    if len(rows) < 2:
        return 0

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "ridgecrest-agency", "performance", "keywords_latest.json")
    header = rows[0]
    records = [dict(zip(header, row)) for row in rows[1:] if row]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"synced_at": datetime.now(timezone.utc).isoformat(),
                   "count": len(records), "rows": records}, f, indent=2)
    logger.info("keyword_perf: %d rows saved to %s", len(records), out_path)
    return len(records)


def run():
    logger.info("=== Google Sync (Sheets) starting ===")

    if not SHEETS_ID:
        result = {"platform": PLATFORM, "status": "error",
                  "error": "GOOGLE_SHEETS_ID not set in .env - complete setup first"}
        print(json.dumps(result, indent=2))
        return result

    if not REFRESH_TOK:
        result = {"platform": PLATFORM, "status": "error",
                  "error": "GOOGLE_REFRESH_TOKEN not set - reconnect at /admin/google-connect"}
        print(json.dumps(result, indent=2))
        return result

    try:
        access_token = _get_access_token()
        if not access_token:
            raise ValueError("Could not obtain access token")
        logger.info("Access token obtained")
    except Exception as e:
        result = {"platform": PLATFORM, "status": "error", "error": f"Auth failed: {e}"}
        print(json.dumps(result, indent=2))
        return result

    campaigns_synced = 0
    search_terms_synced = 0
    keywords_synced = 0

    try:
        campaigns_synced = sync_campaign_performance(access_token)
        logger.info("Campaign rows upserted: %d", campaigns_synced)
    except Exception as e:
        logger.error("campaign_perf sync error: %s", e)

    try:
        search_terms_synced = sync_search_terms(access_token)
    except Exception as e:
        logger.error("search_terms sync error: %s", e)

    try:
        keywords_synced = sync_keywords(access_token)
    except Exception as e:
        logger.error("keyword_perf sync error: %s", e)

    result = {
        "platform": PLATFORM,
        "status": "ok",
        "campaigns_upserted": campaigns_synced,
        "search_terms_saved": search_terms_synced,
        "keywords_saved": keywords_synced,
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
