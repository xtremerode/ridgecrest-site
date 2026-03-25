"""
Reporting Agent
===============
Aggregates data from all other agents via PostgreSQL and generates
structured Markdown reports using Claude. Produces:
  - Daily performance summaries
  - Weekly trend analysis
  - Budget compliance checks
  - Optimization action logs
  - Creative performance breakdowns

Run standalone:  python reporting_agent.py
"""
import os
import json
import logging
import sys
from datetime import date, timedelta
from decimal import Decimal

import anthropic
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

import db
from db import pacific_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [reporting_agent] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

AGENT_NAME = "reporting_agent"

from config import (
    DAILY_BUDGET_SOFT_CAP_USD as DAILY_BUDGET_CAP,
    ACTIVE_DAYS, TARGET_CPL_LOW, TARGET_CPL_HIGH,
)


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------

def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def get_daily_snapshot(report_date: date) -> dict:
    with db.get_db() as (conn, cur):
        # Overall totals
        cur.execute(
            """SELECT
                   COALESCE(SUM(impressions), 0) AS impressions,
                   COALESCE(SUM(clicks), 0) AS clicks,
                   COALESCE(SUM(conversions), 0) AS conversions,
                   COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend,
                   CASE WHEN COALESCE(SUM(clicks),0) > 0
                        THEN COALESCE(SUM(cost_micros),0)/1000000.0 / SUM(clicks)
                        ELSE 0 END AS avg_cpc,
                   CASE WHEN COALESCE(SUM(conversions),0) > 0
                        THEN COALESCE(SUM(cost_micros),0)/1000000.0 / SUM(conversions)
                        ELSE NULL END AS cpl,
                   CASE WHEN COALESCE(SUM(clicks),0) > 0
                        THEN COALESCE(SUM(impressions),0)::float / SUM(clicks)
                        ELSE 0 END AS avg_ctr
               FROM performance_metrics
               WHERE metric_date = %s AND entity_type = 'campaign'""",
            (report_date,)
        )
        totals = dict(cur.fetchone() or {})

        # Per-platform breakdown
        cur.execute(
            """SELECT platform,
                   COALESCE(SUM(impressions), 0) AS impressions,
                   COALESCE(SUM(clicks), 0) AS clicks,
                   COALESCE(SUM(conversions), 0) AS conversions,
                   COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend,
                   CASE WHEN COALESCE(SUM(clicks),0) > 0
                        THEN COALESCE(SUM(cost_micros),0)/1000000.0 / SUM(clicks)
                        ELSE 0 END AS avg_cpc,
                   CASE WHEN COALESCE(SUM(conversions),0) > 0
                        THEN COALESCE(SUM(cost_micros),0)/1000000.0 / SUM(conversions)
                        ELSE NULL END AS cpl
               FROM performance_metrics
               WHERE metric_date = %s AND entity_type = 'campaign'
               GROUP BY platform""",
            (report_date,)
        )
        platform_breakdown = {r["platform"]: dict(r) for r in cur.fetchall()}

        # Per-campaign
        cur.execute(
            """SELECT c.name, pm.impressions, pm.clicks, pm.conversions,
                      pm.cost_micros/1000000.0 AS spend,
                      pm.ctr, pm.cpa_micros/1000000.0 AS cpa,
                      pm.impression_share
               FROM performance_metrics pm
               JOIN campaigns c ON c.id = pm.entity_id
               WHERE pm.metric_date = %s AND pm.entity_type = 'campaign'
               ORDER BY pm.cost_micros DESC""",
            (report_date,)
        )
        campaigns = [dict(r) for r in cur.fetchall()]

        # Budget snapshot
        cur.execute(
            "SELECT * FROM budget_snapshots WHERE snapshot_date = %s",
            (report_date,)
        )
        budget = dict(cur.fetchone() or {})

        # Optimization actions for the day
        cur.execute(
            """SELECT agent_name, action_type, entity_type,
                      reason, applied, created_at
               FROM optimization_actions
               WHERE DATE(created_at) = %s
               ORDER BY created_at""",
            (report_date,)
        )
        actions = [dict(r) for r in cur.fetchall()]

        # Alerts from agent messages
        cur.execute(
            """SELECT message_type, payload, from_agent, created_at
               FROM agent_messages
               WHERE DATE(created_at) = %s
                 AND message_type IN ('critical_alert', 'performance_analysis_complete')
               ORDER BY created_at DESC LIMIT 5""",
            (report_date,)
        )
        messages = [dict(r) for r in cur.fetchall()]

    return {
        "date": str(report_date),
        "day_of_week": report_date.strftime("%A"),
        "is_active_day": report_date.strftime("%A").lower() in ACTIVE_DAYS,
        "totals": totals,
        "platform_breakdown": platform_breakdown,
        "campaigns": campaigns,
        "budget": budget,
        "optimization_actions": actions,
        "agent_messages": messages,
    }


def get_platform_snapshot(report_date: date, platform: str) -> dict:
    """Pull daily metrics for a single platform."""
    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT
                   COALESCE(SUM(impressions), 0) AS impressions,
                   COALESCE(SUM(clicks), 0) AS clicks,
                   COALESCE(SUM(conversions), 0) AS conversions,
                   COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend,
                   CASE WHEN COALESCE(SUM(clicks),0) > 0
                        THEN COALESCE(SUM(cost_micros),0)/1000000.0 / SUM(clicks)
                        ELSE 0 END AS avg_cpc,
                   CASE WHEN COALESCE(SUM(conversions),0) > 0
                        THEN COALESCE(SUM(cost_micros),0)/1000000.0 / SUM(conversions)
                        ELSE NULL END AS cpl
               FROM performance_metrics
               WHERE metric_date = %s AND entity_type = 'campaign' AND platform = %s""",
            (report_date, platform)
        )
        totals = dict(cur.fetchone() or {})

        cur.execute(
            """SELECT c.name, pm.impressions, pm.clicks, pm.conversions,
                      pm.cost_micros/1000000.0 AS spend, pm.ctr,
                      pm.cpa_micros/1000000.0 AS cpa
               FROM performance_metrics pm
               JOIN campaigns c ON c.id = pm.entity_id
               WHERE pm.metric_date = %s AND pm.entity_type = 'campaign'
                 AND pm.platform = %s
               ORDER BY pm.cost_micros DESC""",
            (report_date, platform)
        )
        campaigns = [dict(r) for r in cur.fetchall()]

    return {
        "date": str(report_date),
        "day_of_week": report_date.strftime("%A"),
        "platform": platform,
        "totals": totals,
        "campaigns": campaigns,
    }


def generate_platform_report_with_claude(snapshot: dict, client: anthropic.Anthropic) -> str:
    """Generate a platform-specific daily report."""
    platform_labels = {
        "meta": "Meta Ads (Facebook/Instagram)",
        "microsoft_ads": "Microsoft Ads (Bing)",
        "google_ads": "Google Ads",
    }
    platform_label = platform_labels.get(snapshot["platform"], snapshot["platform"])
    data_str = json.dumps(snapshot, default=_serialize, indent=2)

    prompt = f"""You are the reporting system for Ridgecrest Designs, a luxury design-build firm.
Generate a concise daily performance report for {platform_label} in Markdown.

Data:
{data_str}

Structure:
## {platform_label} Daily Report — {{date}}

### Summary
2-3 sentences on performance and key takeaway.

### Key Metrics
Table: Impressions | Clicks | Conversions | Spend | Avg CPC | CPL

### Campaign Breakdown
Table of each campaign's performance. Highlight best and worst.

### Observations
2-3 bullet points specific to this platform's performance.

Be concise and data-driven. Audience is the account owner."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def get_weekly_snapshot(end_date: date) -> dict:
    start_date = end_date - timedelta(days=6)
    with db.get_db() as (conn, cur):
        # Daily spend trend
        cur.execute(
            """SELECT metric_date,
                      SUM(impressions) AS impressions,
                      SUM(clicks) AS clicks,
                      SUM(conversions) AS conversions,
                      SUM(cost_micros)/1000000.0 AS spend
               FROM performance_metrics
               WHERE metric_date BETWEEN %s AND %s AND entity_type = 'campaign'
               GROUP BY metric_date ORDER BY metric_date""",
            (start_date, end_date)
        )
        daily_trend = [dict(r) for r in cur.fetchall()]

        # Top performing keywords (by conversions)
        cur.execute(
            """SELECT k.keyword_text, k.match_type,
                      SUM(pm.conversions) AS conversions,
                      SUM(pm.cost_micros)/1000000.0 AS spend,
                      CASE WHEN SUM(pm.conversions) > 0
                           THEN SUM(pm.cost_micros)/1000000.0 / SUM(pm.conversions)
                           ELSE NULL END AS cpl
               FROM performance_metrics pm
               JOIN keywords k ON k.id = pm.entity_id
               WHERE pm.metric_date BETWEEN %s AND %s AND pm.entity_type = 'keyword'
               GROUP BY k.keyword_text, k.match_type
               ORDER BY conversions DESC NULLS LAST LIMIT 10""",
            (start_date, end_date)
        )
        top_keywords = [dict(r) for r in cur.fetchall()]

        # Creative brief status
        cur.execute(
            "SELECT status, COUNT(*) AS count FROM creative_briefs GROUP BY status"
        )
        brief_status = {r["status"]: r["count"] for r in cur.fetchall()}

        # Negative keyword count
        cur.execute("SELECT COUNT(*) AS cnt FROM negative_keywords")
        neg_kw_count = cur.fetchone()["cnt"]

        # Weekly totals
        cur.execute(
            """SELECT
                   COALESCE(SUM(impressions), 0) AS impressions,
                   COALESCE(SUM(clicks), 0) AS clicks,
                   COALESCE(SUM(conversions), 0) AS conversions,
                   COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend,
                   CASE WHEN COALESCE(SUM(conversions),0) > 0
                        THEN SUM(cost_micros)/1000000.0 / SUM(conversions)
                        ELSE NULL END AS cpl
               FROM performance_metrics
               WHERE metric_date BETWEEN %s AND %s AND entity_type = 'campaign'""",
            (start_date, end_date)
        )
        weekly_totals = dict(cur.fetchone() or {})

        # Weekly per-platform breakdown
        cur.execute(
            """SELECT platform,
                   COALESCE(SUM(impressions), 0) AS impressions,
                   COALESCE(SUM(clicks), 0) AS clicks,
                   COALESCE(SUM(conversions), 0) AS conversions,
                   COALESCE(SUM(cost_micros)/1000000.0, 0) AS spend,
                   CASE WHEN COALESCE(SUM(conversions),0) > 0
                        THEN SUM(cost_micros)/1000000.0 / SUM(conversions)
                        ELSE NULL END AS cpl
               FROM performance_metrics
               WHERE metric_date BETWEEN %s AND %s AND entity_type = 'campaign'
               GROUP BY platform""",
            (start_date, end_date)
        )
        weekly_platform_breakdown = {r["platform"]: dict(r) for r in cur.fetchall()}

    return {
        "period": f"{start_date} to {end_date}",
        "weekly_totals": weekly_totals,
        "platform_breakdown": weekly_platform_breakdown,
        "daily_trend": daily_trend,
        "top_keywords": top_keywords,
        "creative_brief_status": brief_status,
        "negative_keyword_count": neg_kw_count,
    }


# ---------------------------------------------------------------------------
# Claude report generation
# ---------------------------------------------------------------------------

def _serialize(obj):
    """JSON-serializable coercion for DB types."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date,)):
        return str(obj)
    return str(obj)


def generate_daily_report_with_claude(snapshot: dict, client: anthropic.Anthropic) -> str:
    """Use Claude to narrate a daily performance report in Markdown."""
    data_str = json.dumps(snapshot, default=_serialize, indent=2)

    prompt = f"""You are the reporting system for Ridgecrest Designs, a luxury design-build firm
running paid search and social campaigns targeting affluent homeowners in the East Bay / Contra Costa area of California.

Here is today's performance data (across all platforms):

{data_str}

Write a concise daily performance report in Markdown. Structure it as:

## Daily Performance Report — {{date}}

### Executive Summary
2-3 sentences on overall performance across all platforms and the most important takeaway.

### Key Metrics — All Platforms Combined
A clean table with: Impressions | Clicks | Conversions | Spend | Avg CPC | CPL

### Platform Breakdown
Separate table for each platform present in platform_breakdown (google_ads, meta, microsoft_ads).
Show: Platform | Impressions | Clicks | Conversions | Spend | CPL
Only include platforms that have data. Note: the $125/day budget cap applies to Google Ads only.

### Campaign Breakdown
Table showing each campaign's performance across all platforms. Highlight best and worst performers.

### Budget Status (Google Ads)
- Daily cap: $125.00
- Google Ads spend today: $X
- Remaining: $X
- Pacing: [under/on_track/over]
- Is today an active ad day? [Yes/No]

### Optimizations Applied
List any bid changes, pauses, or budget moves made today.

### Alerts & Flags
List any anomalies, CPL violations, or budget concerns.

### Recommendations
3-5 specific, actionable recommendations for tomorrow based on today's data.
Frame recommendations in terms of Ridgecrest's premium positioning and $125/day Google Ads budget discipline.

Use professional, data-driven language. Keep it tight — this report is read by the account owner."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def generate_weekly_report_with_claude(snapshot: dict, client: anthropic.Anthropic) -> str:
    data_str = json.dumps(snapshot, default=_serialize, indent=2)

    prompt = f"""You are the reporting system for Ridgecrest Designs, a luxury design-build firm.
Generate a weekly multi-platform performance report in Markdown.

Data for the week (all platforms):
{data_str}

Structure:
## Weekly Performance Report — {{period}}

### Week at a Glance
Summary paragraph with key metrics across all platforms and overall trend direction.

### 7-Day Metrics — All Platforms Combined
Impressions | Clicks | Conversions | Spend | CPL | CTR

### Platform Breakdown
Separate table row per platform in platform_breakdown (google_ads, meta, microsoft_ads).
Show: Platform | Impressions | Clicks | Conversions | Spend | CPL
Only include platforms that have data.

### Daily Spend Trend
Small table showing day-by-day spend and whether it was an active ad day.
Active days are: Friday, Saturday, Sunday, Monday. Google Ads budget cap: $125/day.

### Top Keywords (Google Ads)
Table of the top 10 keywords by conversions. Note CPL vs target ($150–$500 range).

### Creative Performance
Brief note on creative brief status and any ad refresh activity.

### Budget Compliance (Google Ads)
- Weekly Google Ads spend vs. $500 target
- Any budget overages or underspend?
- Budget pacing assessment

### Key Wins This Week
2-4 bullet points on what worked across all platforms.

### Issues to Address
2-4 bullet points on what underperformed or needs attention.

### Next Week Priorities
3-5 specific, ranked actions for next week. Align with Ridgecrest's premium positioning and
lead quality optimization goals.

Be direct. The audience is the account owner and wants data-driven insight, not fluff."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Store reports
# ---------------------------------------------------------------------------

def store_report(report_type: str, title: str, body: str,
                 period_start: date, period_end: date, metrics: dict,
                 platform: str = "all") -> int:
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO reports (report_type, platform, period_start, period_end, title,
                                    body_markdown, metrics_snapshot, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (report_type, platform, period_start, period_end, title, body,
             json.dumps(metrics, default=_serialize), AGENT_NAME)
        )
        return cur.fetchone()["id"]


def print_report(title: str, body: str):
    """Print formatted report to stdout."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  {title}")
    print(f"{separator}")
    print(body)
    print(f"{separator}\n")


# ---------------------------------------------------------------------------
# Fallback: plain-text report (no Claude needed)
# ---------------------------------------------------------------------------

def generate_plain_daily_report(snapshot: dict) -> str:
    totals = snapshot["totals"]
    campaigns = snapshot["campaigns"]
    budget = snapshot["budget"]
    day = snapshot["day_of_week"]
    is_active = snapshot["is_active_day"]

    lines = [
        f"# Daily Performance Report — {snapshot['date']}",
        f"**Day:** {day} | **Active Ad Day:** {'YES' if is_active else 'NO'}",
        "",
        "## Key Metrics",
    ]

    headers = ["Metric", "Value"]
    rows = [
        ["Impressions", f"{int(_safe_float(totals.get('impressions'))):,}"],
        ["Clicks", f"{int(_safe_float(totals.get('clicks'))):,}"],
        ["Conversions", f"{_safe_float(totals.get('conversions')):.1f}"],
        ["Spend", f"${_safe_float(totals.get('spend')):.2f}"],
        ["Avg CPC", f"${_safe_float(totals.get('avg_cpc')):.2f}"],
        ["CPL", f"${_safe_float(totals.get('cpl')):.2f}" if totals.get("cpl") else "N/A"],
    ]
    lines.append(tabulate(rows, headers=headers, tablefmt="github"))

    lines += ["", "## Budget Status"]
    spend = _safe_float(budget.get("total_spend_usd"))
    remaining = _safe_float(budget.get("remaining_usd"))
    pacing = budget.get("pacing_status", "unknown")
    lines.append(f"- Spend: **${spend:.2f}** / ${DAILY_BUDGET_CAP:.2f} cap")
    lines.append(f"- Remaining: **${remaining:.2f}**")
    lines.append(f"- Pacing: **{pacing.upper()}**")

    if campaigns:
        lines += ["", "## Campaign Breakdown"]
        camp_headers = ["Campaign", "Impr", "Clicks", "Conv", "Spend ($)", "CPL ($)"]
        camp_rows = [
            [
                c["name"][:35],
                f"{int(_safe_float(c.get('impressions'))):,}",
                f"{int(_safe_float(c.get('clicks'))):,}",
                f"{_safe_float(c.get('conversions')):.1f}",
                f"{_safe_float(c.get('spend')):.2f}",
                f"{_safe_float(c.get('cpa')):.2f}" if c.get("cpa") else "—",
            ]
            for c in campaigns
        ]
        lines.append(tabulate(camp_rows, headers=camp_headers, tablefmt="github"))

    if snapshot["optimization_actions"]:
        lines += ["", "## Optimizations Applied"]
        for act in snapshot["optimization_actions"]:
            applied = "✓" if act["applied"] else "○"
            lines.append(f"- [{applied}] **{act['action_type']}** ({act['entity_type']}) — {act['reason']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Process incoming messages
# ---------------------------------------------------------------------------

def process_messages(client: anthropic.Anthropic):
    messages = db.receive_messages(AGENT_NAME)
    for msg in messages:
        try:
            mtype = msg["message_type"]
            payload = msg["payload"] if isinstance(msg["payload"], dict) else json.loads(msg["payload"])

            if mtype == "performance_analysis_complete":
                # Store alert summary
                alerts = payload.get("alerts", [])
                if alerts:
                    with db.get_db() as (conn, cur):
                        cur.execute(
                            """INSERT INTO reports (report_type, period_start, period_end,
                                                    title, summary, metrics_snapshot, created_by)
                               VALUES ('alert', CURRENT_DATE, CURRENT_DATE,
                                       'Performance Alerts', %s, %s, %s)""",
                            (
                                f"{len(alerts)} alert(s) — {', '.join(a.get('type','') for a in alerts[:3])}",
                                json.dumps({"alerts": alerts}),
                                AGENT_NAME
                            )
                        )

            elif mtype == "generate_report_request":
                report_type = payload.get("report_type", "daily")
                today = pacific_today()
                if report_type == "weekly":
                    snap = get_weekly_snapshot(today)
                    body = generate_weekly_report_with_claude(snap, client)
                    report_id = store_report("weekly", f"Weekly Report — {snap['period']}",
                                             body, today - timedelta(days=6), today,
                                             snap["weekly_totals"])
                else:
                    snap = get_daily_snapshot(today)
                    body = generate_daily_report_with_claude(snap, client)
                    report_id = store_report("daily", f"Daily Report — {today}",
                                             body, today, today, snap["totals"])
                db.send_message(
                    from_agent=AGENT_NAME,
                    to_agent=msg["from_agent"],
                    message_type="report_ready",
                    payload={"report_id": report_id, "report_type": report_type}
                )

            db.ack_message(msg["id"])
        except Exception as e:
            db.ack_message(msg["id"], error=str(e))
            logger.error("Error processing message %d: %s", msg["id"], e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(report_type: str = "daily", use_claude: bool = True):
    """
    report_type: 'daily' or 'weekly'
    use_claude:  False = use plain-text fallback (no API cost)
    """
    logger.info("=== Reporting Agent starting (type=%s, claude=%s) ===", report_type, use_claude)
    db.heartbeat(AGENT_NAME, "alive")

    claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    today = pacific_today()

    # Process any queued requests
    process_messages(claude_client)

    if report_type == "daily":
        snapshot = get_daily_snapshot(today)
        if use_claude:
            try:
                body = generate_daily_report_with_claude(snapshot, claude_client)
            except Exception as e:
                logger.warning("Claude unavailable (%s) — using plain report", e)
                body = generate_plain_daily_report(snapshot)
        else:
            body = generate_plain_daily_report(snapshot)

        title = f"Daily Performance Report — {today}"
        report_id = store_report("daily", title, body, today, today, {
            **snapshot["totals"],
            "platform_breakdown": snapshot.get("platform_breakdown", {}),
        }, platform="all")
        print_report(title, body)
        logger.info("Daily report stored (id=%d)", report_id)

        # Generate per-platform reports for every platform that has data today
        platform_report_ids = {}
        active_platforms = list(snapshot.get("platform_breakdown", {}).keys())
        # Also check yesterday if today has no data yet (API lag)
        if not active_platforms:
            yesterday_snap = get_daily_snapshot(today - timedelta(days=1))
            active_platforms = list(yesterday_snap.get("platform_breakdown", {}).keys())
            platform_snap_date = today - timedelta(days=1)
        else:
            platform_snap_date = today

        for platform in active_platforms:
            try:
                plat_snapshot = get_platform_snapshot(platform_snap_date, platform)
                if not plat_snapshot["campaigns"]:
                    continue
                if use_claude:
                    plat_body = generate_platform_report_with_claude(plat_snapshot, claude_client)
                else:
                    plat_body = json.dumps(plat_snapshot, default=_serialize, indent=2)
                plat_title = f"{platform.replace('_', ' ').title()} Daily Report — {platform_snap_date}"
                plat_id = store_report("daily", plat_title, plat_body,
                                       platform_snap_date, platform_snap_date,
                                       plat_snapshot["totals"], platform=platform)
                platform_report_ids[platform] = plat_id
                logger.info("Platform report stored — platform=%s id=%d", platform, plat_id)
            except Exception as e:
                logger.error("Platform report failed for %s: %s", platform, e)

        result = {
            "report_id": report_id,
            "report_type": "daily",
            "date": str(today),
            "platform_report_ids": platform_report_ids,
        }

    elif report_type == "weekly":
        snapshot = get_weekly_snapshot(today)
        if use_claude:
            try:
                body = generate_weekly_report_with_claude(snapshot, claude_client)
            except Exception as e:
                logger.warning("Claude unavailable (%s) — using plain report", e)
                body = json.dumps(snapshot, default=_serialize, indent=2)
        else:
            body = json.dumps(snapshot, default=_serialize, indent=2)

        title = f"Weekly Performance Report — {snapshot['period']}"
        report_id = store_report("weekly", title, body,
                                 today - timedelta(days=6), today, {
                                     **snapshot["weekly_totals"],
                                     "platform_breakdown": snapshot.get("platform_breakdown", {}),
                                 }, platform="all")
        print_report(title, body)
        logger.info("Weekly report stored (id=%d)", report_id)
        result = {"report_id": report_id, "report_type": "weekly", "period": snapshot["period"]}
    else:
        raise ValueError(f"Unknown report_type: {report_type}")

    db.send_message(
        from_agent=AGENT_NAME,
        to_agent="orchestrator",
        message_type="report_complete",
        payload=result,
        priority=7
    )

    db.heartbeat(AGENT_NAME, "alive", metadata=result)
    logger.info("=== Reporting Agent done ===")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ridgecrest Reporting Agent")
    parser.add_argument("--type", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--no-claude", action="store_true",
                        help="Skip Claude narration — use plain-text report")
    args = parser.parse_args()
    run(report_type=args.type, use_claude=not args.no_claude)
