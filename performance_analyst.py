"""
Performance Analyst Agent
=========================
Pulls performance data from Google Ads, stores it in PostgreSQL,
computes derived metrics, flags anomalies, and broadcasts findings
to other agents via the message bus.

Run standalone:  python performance_analyst.py
"""
import os
import json
import logging
import sys
from datetime import date, timedelta, datetime

from dotenv import load_dotenv

load_dotenv()

import db
from db import pacific_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [performance_analyst] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

AGENT_NAME = "performance_analyst"

from config import (
    DAILY_BUDGET_SOFT_CAP_USD as DAILY_BUDGET_CAP,
    ACTIVE_DAYS, TARGET_CPL_LOW, TARGET_CPL_HIGH,
)

# Minimum thresholds before flagging performance
MIN_CLICKS_FOR_CPL_ALERT = 10


# ---------------------------------------------------------------------------
# Google Ads helpers
# ---------------------------------------------------------------------------

def _get_google_ads_client():
    """Build and return a Google Ads API client."""
    try:
        from google.ads.googleads.client import GoogleAdsClient
        credentials = {
            "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "login_customer_id": os.getenv("GOOGLE_ADS_MANAGER_ID"),
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(credentials)
    except Exception as e:
        logger.warning("Could not build Google Ads client: %s", e)
        return None


def _gaql_campaign_performance(customer_id: str, start_date: str, end_date: str) -> str:
    return f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.bidding_strategy_type,
            campaign_budget.amount_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.cost_micros,
            metrics.ctr,
            metrics.average_cpc,
            metrics.search_impression_share
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND campaign.status != 'REMOVED'
    """


def _gaql_keyword_performance(customer_id: str, start_date: str, end_date: str) -> str:
    return f"""
        SELECT
            campaign.id,
            ad_group.id,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            ad_group_criterion.quality_info.quality_score,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.cost_micros,
            metrics.ctr,
            metrics.average_cpc
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND ad_group_criterion.status != 'REMOVED'
    """


def _gaql_search_terms(customer_id: str, start_date: str, end_date: str) -> str:
    return f"""
        SELECT
            search_term_view.search_term,
            campaign.id,
            ad_group.id,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.cost_micros
        FROM search_term_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """


# ---------------------------------------------------------------------------
# Sync campaigns from Google Ads → DB
# ---------------------------------------------------------------------------

def sync_campaigns(client, customer_id: str) -> list[dict]:
    """Fetch campaigns from Google Ads and upsert into DB."""
    if client is None:
        logger.warning("No Google Ads client — using existing DB campaigns.")
        with db.get_db() as (conn, cur):
            cur.execute("SELECT * FROM campaigns WHERE status != 'REMOVED'")
            return [dict(r) for r in cur.fetchall()]

    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            campaign.id, campaign.name, campaign.status,
            campaign_budget.amount_micros,
            campaign.bidding_strategy_type
        FROM campaign
        WHERE campaign.status != 'REMOVED'
    """
    campaigns = []
    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        for batch in stream:
            for row in batch.results:
                c = row.campaign
                b = row.campaign_budget
                record = {
                    "google_campaign_id": str(c.id),
                    "name": c.name,
                    "status": c.status.name,
                    "daily_budget_micros": b.amount_micros,
                    "bidding_strategy": c.bidding_strategy_type.name,
                }
                campaigns.append(record)
                with db.get_db() as (conn, cur):
                    cur.execute(
                        """INSERT INTO campaigns (google_campaign_id, name, status, daily_budget_micros,
                                                 bidding_strategy, last_synced_at)
                           VALUES (%(google_campaign_id)s, %(name)s, %(status)s, %(daily_budget_micros)s,
                                   %(bidding_strategy)s, NOW())
                           ON CONFLICT (google_campaign_id) DO UPDATE SET
                               name = EXCLUDED.name,
                               status = EXCLUDED.status,
                               daily_budget_micros = EXCLUDED.daily_budget_micros,
                               bidding_strategy = EXCLUDED.bidding_strategy,
                               last_synced_at = NOW(),
                               updated_at = NOW()""",
                        record
                    )
        logger.info("Synced %d campaigns from Google Ads", len(campaigns))
    except Exception as e:
        logger.warning("Google Ads campaign sync failed (%s) — falling back to DB campaigns.", e)
        with db.get_db() as (conn, cur):
            cur.execute("SELECT * FROM campaigns WHERE status != 'REMOVED'")
            campaigns = [dict(r) for r in cur.fetchall()]
        logger.info("Using %d campaigns from DB", len(campaigns))
    return campaigns


# ---------------------------------------------------------------------------
# Pull performance metrics
# ---------------------------------------------------------------------------

def pull_campaign_metrics(client, customer_id: str, report_date: date) -> list[dict]:
    """Pull campaign-level metrics for a given date and store in DB."""
    start = end = report_date.strftime("%Y-%m-%d")
    metrics_list = []

    if client is None:
        logger.warning("No Google Ads client — skipping live metric pull.")
        return metrics_list

    ga_service = client.get_service("GoogleAdsService")
    query = _gaql_campaign_performance(customer_id, start, end)

    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        for batch in stream:
            for row in batch.results:
                m = row.metrics
                c = row.campaign

                # Resolve internal campaign id
                with db.get_db() as (conn, cur):
                    cur.execute(
                        "SELECT id FROM campaigns WHERE google_campaign_id = %s",
                        (str(c.id),)
                    )
                    result = cur.fetchone()
                    if not result:
                        continue
                    campaign_db_id = result["id"]

                ctr = m.ctr if m.impressions > 0 else 0
                cpa = int(m.cost_micros / m.conversions) if m.conversions > 0 else None
                conv_rate = m.conversions / m.clicks if m.clicks > 0 else 0
                cpc_avg = int(m.cost_micros / m.clicks) if m.clicks > 0 else 0

                record = {
                    "metric_date": report_date,
                    "entity_type": "campaign",
                    "entity_id": campaign_db_id,
                    "google_entity_id": str(c.id),
                    "impressions": int(m.impressions),
                    "clicks": int(m.clicks),
                    "conversions": float(m.conversions),
                    "cost_micros": int(m.cost_micros),
                    "ctr": round(ctr, 4),
                    "cpc_avg_micros": cpc_avg,
                    "cpa_micros": cpa,
                    "conversion_rate": round(conv_rate, 4),
                    "impression_share": round(float(m.search_impression_share or 0), 4),
                }
                metrics_list.append(record)

                with db.get_db() as (conn, cur):
                    cur.execute(
                        """INSERT INTO performance_metrics
                           (metric_date, entity_type, entity_id, google_entity_id,
                            impressions, clicks, conversions, cost_micros,
                            ctr, cpc_avg_micros, cpa_micros, conversion_rate, impression_share)
                           VALUES (%(metric_date)s, %(entity_type)s, %(entity_id)s, %(google_entity_id)s,
                                   %(impressions)s, %(clicks)s, %(conversions)s, %(cost_micros)s,
                                   %(ctr)s, %(cpc_avg_micros)s, %(cpa_micros)s, %(conversion_rate)s,
                                   %(impression_share)s)
                           ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                               impressions = EXCLUDED.impressions,
                               clicks = EXCLUDED.clicks,
                               conversions = EXCLUDED.conversions,
                               cost_micros = EXCLUDED.cost_micros,
                               ctr = EXCLUDED.ctr,
                               cpc_avg_micros = EXCLUDED.cpc_avg_micros,
                               cpa_micros = EXCLUDED.cpa_micros,
                               conversion_rate = EXCLUDED.conversion_rate,
                               impression_share = EXCLUDED.impression_share""",
                        record
                    )
    except Exception as e:
        logger.error("Error pulling campaign metrics: %s", e)

    return metrics_list


def pull_search_terms(client, customer_id: str, report_date: date):
    """Store search terms for review / negative-keyword mining."""
    if client is None:
        return

    ga_service = client.get_service("GoogleAdsService")
    start = end = report_date.strftime("%Y-%m-%d")
    query = _gaql_search_terms(customer_id, start, end)

    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        count = 0
        for batch in stream:
            for row in batch.results:
                m = row.metrics
                # Resolve campaign / ad group db ids
                with db.get_db() as (conn, cur):
                    cur.execute(
                        "SELECT id FROM campaigns WHERE google_campaign_id=%s",
                        (str(row.campaign.id),)
                    )
                    camp = cur.fetchone()
                    if not camp:
                        continue

                    cur.execute(
                        "SELECT id FROM ad_groups WHERE google_ad_group_id=%s",
                        (str(row.ad_group.id),)
                    )
                    ag = cur.fetchone()

                    cur.execute(
                        """INSERT INTO search_terms
                           (report_date, search_term, campaign_id, ad_group_id,
                            impressions, clicks, conversions, cost_micros)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (report_date, search_term, campaign_id) DO UPDATE SET
                               impressions = EXCLUDED.impressions,
                               clicks = EXCLUDED.clicks,
                               conversions = EXCLUDED.conversions,
                               cost_micros = EXCLUDED.cost_micros""",
                        (report_date, row.search_term_view.search_term,
                         camp["id"], ag["id"] if ag else None,
                         int(m.impressions), int(m.clicks),
                         float(m.conversions), int(m.cost_micros))
                    )
                    count += 1
        logger.info("Stored %d search terms", count)
    except Exception as e:
        logger.error("Error pulling search terms: %s", e)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse_performance(report_date: date) -> dict:
    """
    Compute summary stats and flag anomalies from stored metrics.
    Returns an analysis dict broadcast to other agents.
    """
    with db.get_db() as (conn, cur):
        # 7-day rolling window
        window_start = report_date - timedelta(days=6)

        cur.execute(
            """SELECT
                   SUM(impressions) AS total_impressions,
                   SUM(clicks) AS total_clicks,
                   SUM(conversions) AS total_conversions,
                   SUM(cost_micros) / 1000000.0 AS total_spend,
                   CASE WHEN SUM(clicks) > 0
                        THEN SUM(cost_micros) / 1000000.0 / SUM(clicks)
                        ELSE 0 END AS avg_cpc,
                   CASE WHEN SUM(conversions) > 0
                        THEN SUM(cost_micros) / 1000000.0 / SUM(conversions)
                        ELSE NULL END AS cpl
               FROM performance_metrics
               WHERE metric_date BETWEEN %s AND %s
                 AND entity_type = 'campaign'""",
            (window_start, report_date)
        )
        summary = dict(cur.fetchone() or {})

        # Per-campaign breakdown for the report date
        cur.execute(
            """SELECT c.name, c.google_campaign_id,
                      pm.impressions, pm.clicks, pm.conversions,
                      pm.cost_micros / 1000000.0 AS cost_usd,
                      pm.ctr, pm.cpa_micros / 1000000.0 AS cpa_usd,
                      pm.impression_share
               FROM performance_metrics pm
               JOIN campaigns c ON c.id = pm.entity_id
               WHERE pm.metric_date = %s AND pm.entity_type = 'campaign'
               ORDER BY pm.cost_micros DESC""",
            (report_date,)
        )
        campaign_rows = [dict(r) for r in cur.fetchall()]

        # Today's spend vs budget — claude_code campaigns only
        # The $125/day cap applies only to campaigns managed by the Claude Code agency
        cur.execute(
            """SELECT COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS today_spend
               FROM performance_metrics pm
               JOIN campaigns c ON c.id = pm.entity_id
               WHERE pm.metric_date = %s
                 AND pm.entity_type = 'campaign'
                 AND c.managed_by = 'claude_code'""",
            (report_date,)
        )
        today_spend = float(cur.fetchone()["today_spend"] or 0)

        # Per-platform spend breakdown
        cur.execute(
            """SELECT platform, COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend
               FROM performance_metrics
               WHERE metric_date = %s AND entity_type = 'campaign'
               GROUP BY platform""",
            (report_date,)
        )
        platform_spend = {r["platform"]: float(r["spend"]) for r in cur.fetchall()}

    # ---------- anomaly detection ----------
    alerts = []

    day_name = report_date.strftime("%A").lower()
    if day_name not in ACTIVE_DAYS:
        alerts.append({"type": "schedule", "severity": "warning",
                       "message": f"Today ({day_name}) is not an active ad day. Campaigns should be paused."})

    if today_spend > DAILY_BUDGET_CAP:
        alerts.append({"type": "budget_overage", "severity": "critical",
                       "message": f"Daily spend ${today_spend:.2f} exceeds ${DAILY_BUDGET_CAP} cap!"})
    elif today_spend > DAILY_BUDGET_CAP * 0.90:
        alerts.append({"type": "budget_pacing", "severity": "warning",
                       "message": f"Spend ${today_spend:.2f} is >90% of daily cap. Monitor closely."})

    cpl = summary.get("cpl")
    if cpl and cpl > TARGET_CPL_HIGH:
        alerts.append({"type": "high_cpl", "severity": "warning",
                       "message": f"CPL ${cpl:.2f} exceeds target max of ${TARGET_CPL_HIGH}"})
    elif cpl and cpl < TARGET_CPL_LOW and summary.get("total_conversions", 0) >= 3:
        alerts.append({"type": "low_cpl", "severity": "info",
                       "message": f"CPL ${cpl:.2f} is below target min — possible lead quality concern"})

    # Flag zero-conversion campaigns with significant spend
    for camp in campaign_rows:
        if camp["conversions"] == 0 and float(camp["cost_usd"] or 0) > 30:
            alerts.append({
                "type": "zero_conversions",
                "severity": "warning",
                "campaign": camp["name"],
                "message": f"Campaign '{camp['name']}' spent ${camp['cost_usd']:.2f} with 0 conversions today."
            })

    analysis = {
        "report_date": str(report_date),
        "summary_7d": summary,
        "campaign_breakdown": campaign_rows,
        "today_spend": today_spend,
        "platform_spend": platform_spend,
        "budget_remaining": max(0, DAILY_BUDGET_CAP - today_spend),
        "alerts": alerts,
        "alert_count": len(alerts),
        "critical_alerts": [a for a in alerts if a["severity"] == "critical"],
    }

    # Convert non-serializable types (Decimal from DB computed columns)
    for k, v in analysis["summary_7d"].items():
        if hasattr(v, '__float__'):
            analysis["summary_7d"][k] = float(v)

    analysis["campaign_breakdown"] = [
        {k: float(v) if hasattr(v, '__float__') else v for k, v in row.items()}
        for row in analysis["campaign_breakdown"]
    ]

    return analysis


# ---------------------------------------------------------------------------
# Budget snapshot
# ---------------------------------------------------------------------------

def update_budget_snapshot(report_date: date, today_spend: float,
                            campaign_breakdown: list[dict]):
    day_name = report_date.strftime("%A").lower()
    is_active = day_name in ACTIVE_DAYS
    remaining = max(0, DAILY_BUDGET_CAP - today_spend)
    if today_spend > DAILY_BUDGET_CAP:
        pacing = "over"
    elif today_spend > DAILY_BUDGET_CAP * 0.8:
        pacing = "on_track"
    else:
        pacing = "under"

    breakdown = {c["name"]: float(c.get("cost_usd") or 0) for c in campaign_breakdown}

    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO budget_snapshots
               (snapshot_date, day_of_week, is_active_day, total_spend_usd,
                daily_cap_usd, remaining_usd, campaign_breakdown, pacing_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (snapshot_date) DO UPDATE SET
                   total_spend_usd = EXCLUDED.total_spend_usd,
                   remaining_usd = EXCLUDED.remaining_usd,
                   campaign_breakdown = EXCLUDED.campaign_breakdown,
                   pacing_status = EXCLUDED.pacing_status""",
            (report_date, day_name, is_active, today_spend,
             DAILY_BUDGET_CAP, remaining, json.dumps(breakdown), pacing)
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    logger.info("=== Performance Analyst starting ===")
    db.heartbeat(AGENT_NAME, "alive")

    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
    client = _get_google_ads_client()
    today = pacific_today()

    # Sync campaigns
    sync_campaigns(client, customer_id)

    # Pull yesterday + today metrics
    for report_date in [today - timedelta(days=1), today]:
        pull_campaign_metrics(client, customer_id, report_date)
        pull_search_terms(client, customer_id, report_date)

    # Analyse
    analysis = analyse_performance(today)
    update_budget_snapshot(today, analysis["today_spend"], analysis["campaign_breakdown"])

    logger.info(
        "Analysis complete — spend: $%.2f | conversions: %s | alerts: %d",
        analysis["today_spend"],
        analysis["summary_7d"].get("total_conversions", 0),
        analysis["alert_count"]
    )

    # Broadcast to all agents
    db.send_message(
        from_agent=AGENT_NAME,
        to_agent="all",
        message_type="performance_analysis_complete",
        payload=analysis,
        priority=3
    )

    # If critical alerts, ping orchestrator directly at priority 1
    if analysis["critical_alerts"]:
        db.send_message(
            from_agent=AGENT_NAME,
            to_agent="orchestrator",
            message_type="critical_alert",
            payload={"alerts": analysis["critical_alerts"]},
            priority=1
        )
        logger.warning("CRITICAL ALERTS: %s", analysis["critical_alerts"])

    db.heartbeat(AGENT_NAME, "alive", metadata={
        "last_report_date": str(today),
        "alerts": analysis["alert_count"]
    })
    logger.info("=== Performance Analyst done ===")
    return analysis


if __name__ == "__main__":
    run()
