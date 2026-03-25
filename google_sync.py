"""
Google Sync Agent
=================
Pulls the last 30 days of campaign performance data from the Google Ads API
for customer 5576077690 (under manager 4478944999) and writes it into
performance_metrics with platform='google_ads'.

Run standalone:  python google_sync.py
"""
import logging
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [google_sync] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME   = "google_sync"
PLATFORM     = "google_ads"
CUSTOMER_ID  = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "5576077690").replace("-", "")
MANAGER_ID   = os.getenv("GOOGLE_ADS_MANAGER_ID",  "4478944999").replace("-", "")
DAYS_BACK    = 30


def _get_client():
    from google.ads.googleads.client import GoogleAdsClient
    creds = {
        "developer_token":  os.getenv("GOOGLE_DEVELOPER_TOKEN"),
        "client_id":        os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret":    os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token":    os.getenv("GOOGLE_REFRESH_TOKEN"),
        "login_customer_id": MANAGER_ID,
        "use_proto_plus":   True,
    }
    return GoogleAdsClient.load_from_dict(creds)


def _upsert_campaign(google_campaign_id: str, name: str, status: str,
                     daily_budget_micros: int, bidding_strategy: str) -> int:
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


def _upsert_metric(metric_date, entity_id: int, google_entity_id: str,
                   impressions: int, clicks: int, conversions: float,
                   cost_micros: int, ctr: float, cpc_avg_micros: int,
                   cpa_micros, conversion_rate: float, impression_share: float):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO performance_metrics
               (metric_date, entity_type, entity_id, google_entity_id,
                impressions, clicks, conversions, cost_micros,
                ctr, cpc_avg_micros, cpa_micros, conversion_rate,
                impression_share, platform)
               VALUES (%s,'campaign',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
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


def run() -> dict:
    logger.info("=== Google Sync starting (last %d days) ===", DAYS_BACK)
    db.heartbeat(AGENT_NAME, "alive")

    end   = date.today()
    start = end - timedelta(days=DAYS_BACK - 1)

    try:
        client = _get_client()
    except Exception as e:
        logger.error("Failed to build Google Ads client: %s", e)
        db.heartbeat(AGENT_NAME, "error", error=str(e))
        return {"platform": PLATFORM, "status": "error", "error": str(e)}

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.bidding_strategy_type,
            campaign_budget.amount_micros,
            segments.date,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.cost_micros,
            metrics.ctr,
            metrics.average_cpc,
            metrics.search_impression_share
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
          AND campaign.status != 'REMOVED'
        ORDER BY segments.date, campaign.id
    """

    rows_written = 0
    campaigns_synced = set()
    errors = []

    try:
        stream = ga_service.search_stream(customer_id=CUSTOMER_ID, query=query)
        for batch in stream:
            for row in batch.results:
                c   = row.campaign
                b   = row.campaign_budget
                m   = row.metrics
                seg = row.segments

                try:
                    campaign_db_id = _upsert_campaign(
                        google_campaign_id = str(c.id),
                        name               = c.name,
                        status             = c.status.name,
                        daily_budget_micros= b.amount_micros,
                        bidding_strategy   = c.bidding_strategy_type.name,
                    )
                    campaigns_synced.add(str(c.id))

                    ctr        = round(m.ctr, 4)
                    conv_rate  = round(m.conversions / m.clicks, 4) if m.clicks > 0 else 0
                    cpc_avg    = int(m.cost_micros / m.clicks)      if m.clicks > 0 else 0
                    cpa        = int(m.cost_micros / m.conversions) if m.conversions > 0 else None
                    imp_share  = round(float(m.search_impression_share or 0), 4)

                    _upsert_metric(
                        metric_date      = seg.date,
                        entity_id        = campaign_db_id,
                        google_entity_id = str(c.id),
                        impressions      = int(m.impressions),
                        clicks           = int(m.clicks),
                        conversions      = float(m.conversions),
                        cost_micros      = int(m.cost_micros),
                        ctr              = ctr,
                        cpc_avg_micros   = cpc_avg,
                        cpa_micros       = cpa,
                        conversion_rate  = conv_rate,
                        impression_share = imp_share,
                    )
                    rows_written += 1
                except Exception as e:
                    errors.append(str(e))
                    logger.warning("Row error: %s", e)

    except Exception as e:
        logger.error("Google Ads API error: %s", e)
        db.heartbeat(AGENT_NAME, "error", error=str(e))
        return {"platform": PLATFORM, "status": "error", "error": str(e)}

    status = "error" if errors and rows_written == 0 else "success"
    db.heartbeat(AGENT_NAME, status, metadata={
        "rows_written": rows_written,
        "campaigns_synced": len(campaigns_synced),
        "date_range": f"{start} to {end}",
    })
    logger.info(
        "=== Google Sync done — campaigns=%d rows=%d errors=%d ===",
        len(campaigns_synced), rows_written, len(errors),
    )
    return {
        "platform":         PLATFORM,
        "status":           status,
        "campaigns_synced": len(campaigns_synced),
        "rows_written":     rows_written,
        "date_range":       f"{start} to {end}",
        "errors":           errors,
    }


if __name__ == "__main__":
    import json
    result = run()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["status"] == "success" else 1)
