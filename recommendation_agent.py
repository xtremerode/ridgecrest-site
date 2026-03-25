"""
Recommendation Agent
====================
Analyzes performance trends across all platforms and generates human-readable
action recommendations that exceed normal guardrail limits. Each recommendation
requires explicit human approval (via email or Lovable UI) before execution.

Recommendation types:
  - budget_increase  : CPL trending well, room to scale
  - blitz            : Short-term budget surge for high-momentum campaigns
  - shift_budget     : Move budget from under to top performer
  - bid_increase     : Keyword gaining traction, increase bid aggressively
  - pause_campaign   : Campaign burning spend with zero returns
  - review           : Data pattern needs human judgment

Approval flow:
  1. Recommendation written to Supabase recommendations table
  2. Email sent via Resend with Approve / Dismiss links
  3. Links hit approve-recommendation Supabase edge function
  4. command_executor polls for approved recommendations and executes

Run standalone:  python recommendation_agent.py
"""

import hashlib
import hmac
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

import db
from db import pacific_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [recommendation_agent] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME = "recommendation_agent"

from config import (
    TARGET_CPL_LOW, TARGET_CPL_HIGH, TARGET_CPL_IDEAL,
    LOOKBACK_DAYS, RECOMMENDATION_TTL_HOURS, NEW_CAMPAIGN_GRACE_DAYS,
    ALERT_EMAIL, ALERT_FROM, SUPABASE_URL,
)

INGEST_API_KEY    = os.getenv("INGEST_API_KEY", "")
RESEND_API_KEY    = os.getenv("RESEND_API_KEY", "")
APPROVAL_SECRET   = os.getenv("RECOMMENDATION_SECRET", INGEST_API_KEY[:32] if INGEST_API_KEY else "ridgecrest-secret")

MIN_SPEND_FOR_REC    = 20.0
MIN_CONV_FOR_REC     = 1
BLITZ_CPL_MAX        = 250.0

EDGE_BASE = f"{SUPABASE_URL}/functions/v1"


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "x-api-key": INGEST_API_KEY,
        "Content-Type": "application/json",
    }


def _write_recommendation(rec: dict) -> int | None:
    """Write a recommendation to Supabase. Returns the new row id."""
    resp = requests.post(
        f"{EDGE_BASE}/save-recommendation",
        headers=_sb_headers(),
        json=rec,
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("id")
    logger.warning("save-recommendation: %d — %s", resp.status_code, resp.text[:200])
    return None


def _get_pending_count() -> int:
    """Check how many pending recommendations already exist to avoid flooding."""
    resp = requests.post(
        f"{EDGE_BASE}/save-recommendation",
        headers=_sb_headers(),
        json={"action": "count_pending"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("count", 0)
    return 0


# ---------------------------------------------------------------------------
# Approval token (HMAC — prevents URL tampering)
# ---------------------------------------------------------------------------

def _make_token(rec_id: int, action: str) -> str:
    msg = f"{rec_id}:{action}".encode()
    return hmac.new(APPROVAL_SECRET.encode(), msg, hashlib.sha256).hexdigest()[:16]


def _approval_url(rec_id: int, action: str) -> str:
    token = _make_token(rec_id, action)
    return (
        f"{EDGE_BASE}/approve-recommendation"
        f"?id={rec_id}&action={action}&token={token}"
    )


# ---------------------------------------------------------------------------
# Email notification
# ---------------------------------------------------------------------------

def _send_recommendation_email(rec: dict, rec_id: int) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email")
        return False

    approve_url = _approval_url(rec_id, "approve")
    dismiss_url = _approval_url(rec_id, "dismiss")

    risk_color = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"}.get(
        rec.get("risk_level", "medium"), "#f59e0b"
    )

    expires = rec.get("expires_at", "")
    data_snap = rec.get("data_snapshot", {})
    metrics_rows = "".join(
        f"<tr><td style='padding:4px 8px;color:#6b7280'>{k}</td>"
        f"<td style='padding:4px 8px;font-weight:600'>{v}</td></tr>"
        for k, v in data_snap.items()
        if k not in ("campaign_id",)
    )

    html = f"""
<html><body style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:24px">

  <div style="background:#0f172a;padding:16px 24px;border-radius:8px 8px 0 0">
    <p style="color:#94a3b8;margin:0;font-size:12px;text-transform:uppercase;letter-spacing:1px">
      Ridgecrest Designs — Marketing Agent
    </p>
    <h2 style="color:#ffffff;margin:4px 0 0">Recommended Action</h2>
  </div>

  <div style="border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 8px 8px">

    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <span style="background:{risk_color}20;color:{risk_color};padding:4px 10px;
                   border-radius:99px;font-size:12px;font-weight:600;text-transform:uppercase">
        {rec.get("risk_level","medium")} risk
      </span>
      <span style="color:#64748b;font-size:13px">{rec.get("platform","").replace("_"," ").title()}</span>
    </div>

    <h3 style="margin:0 0 8px;color:#0f172a">{rec.get("campaign_name","")}</h3>
    <p style="margin:0 0 16px;font-size:18px;font-weight:600;color:#1e293b">
      {rec.get("recommendation","")}
    </p>

    <div style="background:#f8fafc;padding:16px;border-radius:6px;margin-bottom:16px">
      <p style="margin:0 0 8px;font-size:12px;font-weight:600;text-transform:uppercase;
                color:#64748b">Why</p>
      <p style="margin:0;color:#334155">{rec.get("reasoning","")}</p>
    </div>

    {"<div style='background:#f8fafc;padding:16px;border-radius:6px;margin-bottom:16px'><p style='margin:0 0 8px;font-size:12px;font-weight:600;text-transform:uppercase;color:#64748b'>Expected Impact</p><p style='margin:0;color:#334155'>" + rec.get("expected_impact","") + "</p></div>" if rec.get("expected_impact") else ""}

    {"<table style='width:100%;border-collapse:collapse;margin-bottom:16px'><tr><th colspan='2' style='text-align:left;padding:4px 8px;font-size:12px;text-transform:uppercase;color:#64748b'>Performance Data</th></tr>" + metrics_rows + "</table>" if metrics_rows else ""}

    {"<div style='background:#fef3c7;border:1px solid #f59e0b;padding:12px;border-radius:6px;margin-bottom:16px;font-size:13px;color:#92400e'>⚡ This action exceeds normal automated limits and requires your explicit approval.</div>" if rec.get("guardrail_override") else ""}

    <div style="display:flex;gap:12px;margin-top:24px">
      <a href="{approve_url}"
         style="flex:1;text-align:center;background:#22c55e;color:#ffffff;padding:14px;
                border-radius:6px;text-decoration:none;font-weight:600;font-size:16px">
        ✓ Approve
      </a>
      <a href="{dismiss_url}"
         style="flex:1;text-align:center;background:#f1f5f9;color:#64748b;padding:14px;
                border-radius:6px;text-decoration:none;font-weight:600;font-size:16px">
        Dismiss
      </a>
    </div>

    <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:16px">
      Expires {expires[:10] if expires else "in 48 hours"} ·
      <a href="https://go.ridgecrestdesigns.com" style="color:#94a3b8">View in Command Center</a>
    </p>
  </div>
</body></html>
"""

    try:
        import resend
        resend.api_key = RESEND_API_KEY
        response = resend.Emails.send({
            "from":    ALERT_FROM,
            "to":      [ALERT_EMAIL],
            "subject": f"[Action Recommended] {rec.get('recommendation','')} — {pacific_today()}",
            "html":    html,
        })
        logger.info("Recommendation email sent — id=%s", response.get("id"))
        return True
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Performance data fetchers
# ---------------------------------------------------------------------------

def _get_campaign_performance(lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    since = pacific_today() - timedelta(days=lookback_days - 1)
    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT
                c.id, c.name, c.platform, c.daily_budget_micros,
                c.service_category,
                COALESCE(SUM(pm.impressions), 0)            AS impressions,
                COALESCE(SUM(pm.clicks), 0)                 AS clicks,
                COALESCE(SUM(pm.conversions), 0)            AS conversions,
                COALESCE(SUM(pm.cost_micros)/1000000.0, 0)  AS spend_usd,
                CASE WHEN SUM(pm.conversions) > 0
                     THEN SUM(pm.cost_micros)/1000000.0 / SUM(pm.conversions)
                     ELSE NULL END                          AS cpl,
                CASE WHEN SUM(pm.clicks) > 0
                     THEN SUM(pm.conversions)::float / SUM(pm.clicks) * 100
                     ELSE NULL END                          AS conv_rate_pct
            FROM campaigns c
            LEFT JOIN performance_metrics pm
                   ON pm.entity_id = c.id
                  AND pm.entity_type = 'campaign'
                  AND pm.metric_date >= %s
            WHERE c.status = 'ENABLED'
              AND c.managed_by = 'claude_code'
              AND c.created_at <= NOW() - INTERVAL '%s days'
            GROUP BY c.id, c.name, c.platform, c.daily_budget_micros, c.service_category
            ORDER BY spend_usd DESC
            """,
            (since, NEW_CAMPAIGN_GRACE_DAYS),
        )
        return [dict(r) for r in cur.fetchall()]


def _get_recent_trend(campaign_id: int, days: int = 3) -> dict:
    """Compare last 3 days vs prior 4 days to detect momentum."""
    today = pacific_today()
    recent_start = today - timedelta(days=days - 1)
    prior_start  = today - timedelta(days=LOOKBACK_DAYS - 1)

    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT
                SUM(CASE WHEN metric_date >= %s THEN cost_micros ELSE 0 END)/1000000.0
                    AS recent_spend,
                SUM(CASE WHEN metric_date >= %s THEN conversions ELSE 0 END)
                    AS recent_conv,
                SUM(CASE WHEN metric_date < %s THEN cost_micros ELSE 0 END)/1000000.0
                    AS prior_spend,
                SUM(CASE WHEN metric_date < %s THEN conversions ELSE 0 END)
                    AS prior_conv
            FROM performance_metrics
            WHERE entity_id = %s
              AND entity_type = 'campaign'
              AND metric_date >= %s
            """,
            (recent_start, recent_start, recent_start, recent_start,
             campaign_id, prior_start),
        )
        row = dict(cur.fetchone())

    recent_spend = float(row.get("recent_spend") or 0)
    recent_conv  = float(row.get("recent_conv")  or 0)
    prior_spend  = float(row.get("prior_spend")  or 0)
    prior_conv   = float(row.get("prior_conv")   or 0)

    recent_cpl = recent_spend / recent_conv if recent_conv > 0 else None
    prior_cpl  = prior_spend  / prior_conv  if prior_conv  > 0 else None

    improving = (
        recent_cpl is not None and prior_cpl is not None and recent_cpl < prior_cpl
    )

    return {
        "recent_spend": recent_spend,
        "recent_conv":  recent_conv,
        "recent_cpl":   recent_cpl,
        "prior_cpl":    prior_cpl,
        "improving":    improving,
        "momentum":     "up" if improving else ("flat" if recent_cpl == prior_cpl else "down"),
    }


def _already_recommended(campaign_id: int, action_type: str) -> bool:
    """Avoid duplicate pending recommendations for the same campaign+action."""
    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT id FROM optimization_actions
               WHERE action_type = %s
                 AND entity_id = %s
                 AND applied = FALSE
                 AND created_at > NOW() - INTERVAL '48 hours'
               LIMIT 1""",
            (f"recommend_{action_type}", campaign_id),
        )
        return cur.fetchone() is not None


def _log_recommendation_action(campaign_id: int, action_type: str, rec: dict):
    """Log recommendation to optimization_actions for audit trail."""
    db.log_action(
        agent_name=AGENT_NAME,
        action_type=f"recommend_{action_type}",
        entity_type="campaign",
        entity_id=campaign_id,
        before=rec.get("current_value", {}),
        after=rec.get("proposed_value", {}),
        reason=rec.get("reasoning", ""),
    )


# ---------------------------------------------------------------------------
# Recommendation generators
# ---------------------------------------------------------------------------

def _recommend_budget_increase(camp: dict, trend: dict) -> dict | None:
    cpl   = float(camp["cpl"]) if camp["cpl"] else None
    spend = float(camp["spend_usd"] or 0)
    convs = float(camp["conversions"] or 0)
    daily_budget = float(camp["daily_budget_micros"] or 0) / 1_000_000

    if spend < MIN_SPEND_FOR_REC or convs < MIN_CONV_FOR_REC:
        return None
    if cpl is None or cpl > TARGET_CPL_HIGH:
        return None
    if not trend["improving"]:
        return None

    # Standard increase: +25% (just above the 20% automated guardrail)
    new_budget = round(daily_budget * 1.25, 2)
    increase   = new_budget - daily_budget

    return {
        "action_type":   "budget_increase",
        "recommendation": f"Increase {camp['name']} daily budget ${daily_budget:.0f} → ${new_budget:.0f}",
        "reasoning": (
            f"CPL ${cpl:.0f} is within target and improving over the last 3 days "
            f"(was ${trend['prior_cpl']:.0f}, now ${trend['recent_cpl']:.0f}). "
            f"Campaign is gaining momentum — increasing budget captures more qualified leads "
            f"before the window closes."
        ),
        "expected_impact": (
            f"Est. {round(increase / cpl, 1)} additional conversions/week "
            f"at current CPL of ${cpl:.0f}"
        ),
        "risk_level": "low",
        "current_value":  {"daily_budget_usd": daily_budget},
        "proposed_value": {"daily_budget_usd": new_budget},
        "guardrail_override": True,  # exceeds automated 20% cap
        "data_snapshot": {
            "7d_spend":   f"${spend:.2f}",
            "7d_convs":   int(convs),
            "CPL":        f"${cpl:.0f}",
            "prior_CPL":  f"${trend['prior_cpl']:.0f}" if trend["prior_cpl"] else "n/a",
            "trend":      "improving ↓",
        },
    }


def _recommend_blitz(camp: dict, trend: dict) -> dict | None:
    """Weekend blitz: aggressive short-term budget surge for top performers."""
    cpl   = float(camp["cpl"]) if camp["cpl"] else None
    spend = float(camp["spend_usd"] or 0)
    convs = float(camp["conversions"] or 0)
    daily_budget = float(camp["daily_budget_micros"] or 0) / 1_000_000

    if spend < MIN_SPEND_FOR_REC or convs < 2:
        return None
    if cpl is None or cpl > BLITZ_CPL_MAX:
        return None

    # Blitz: +60% for this weekend only
    new_budget = round(daily_budget * 1.60, 2)

    today = pacific_today().strftime("%A")
    if today in ("Friday", "Saturday"):
        window = "this weekend"
    elif today == "Sunday":
        window = "today and Monday"
    else:
        window = "this weekend (Fri–Mon)"

    return {
        "action_type":    "blitz",
        "recommendation": f"Weekend blitz: {camp['name']} ${daily_budget:.0f} → ${new_budget:.0f}/day {window}",
        "reasoning": (
            f"CPL ${cpl:.0f} is well below the $250 blitz threshold with {int(convs)} conversions "
            f"this week. This campaign is earning its spend — a short-term budget surge "
            f"{window} maximizes leads while performance is hot."
        ),
        "expected_impact": (
            f"Est. {round((new_budget - daily_budget) * 4 / cpl, 1)} additional leads "
            f"over the active weekend window"
        ),
        "risk_level": "medium",
        "current_value":  {"daily_budget_usd": daily_budget},
        "proposed_value": {"daily_budget_usd": new_budget, "window": window},
        "guardrail_override": True,
        "data_snapshot": {
            "7d_spend":  f"${spend:.2f}",
            "7d_convs":  int(convs),
            "CPL":       f"${cpl:.0f}",
            "window":    window,
        },
    }


def _recommend_pause(camp: dict) -> dict | None:
    """Flag campaigns burning spend with zero conversions."""
    spend = float(camp["spend_usd"] or 0)
    convs = float(camp["conversions"] or 0)
    daily_budget = float(camp["daily_budget_micros"] or 0) / 1_000_000

    if spend < 50.0 or convs > 0:
        return None

    return {
        "action_type":    "pause_campaign",
        "recommendation": f"Review or pause {camp['name']} — ${spend:.0f} spent, 0 conversions",
        "reasoning": (
            f"${spend:.2f} spent over the last {LOOKBACK_DAYS} days with zero conversions. "
            f"This spend is not generating leads. Campaign should be paused or restructured "
            f"before continuing to consume budget."
        ),
        "expected_impact": f"Save ${daily_budget:.0f}/day until campaign is fixed",
        "risk_level": "high",
        "current_value":  {"daily_budget_usd": daily_budget, "status": "ENABLED"},
        "proposed_value": {"status": "PAUSED"},
        "guardrail_override": False,
        "data_snapshot": {
            "7d_spend":  f"${spend:.2f}",
            "7d_convs":  0,
            "CPL":       "n/a",
        },
    }


# ---------------------------------------------------------------------------
# Main analysis loop
# ---------------------------------------------------------------------------

def analyze_and_recommend() -> list[dict]:
    campaigns = _get_campaign_performance()
    recommendations = []

    if not campaigns:
        logger.info("No campaign performance data available — skipping recommendations")
        return []

    logger.info("Analyzing %d campaigns for recommendations", len(campaigns))

    for camp in campaigns:
        camp_id = camp["id"]
        trend   = _get_recent_trend(camp_id)
        recs_for_camp = []

        # 1. Pause recommendation
        pause_rec = _recommend_pause(camp)
        if pause_rec and not _already_recommended(camp_id, "pause_campaign"):
            recs_for_camp.append(pause_rec)

        # 2. Blitz recommendation (takes priority over standard increase)
        blitz_rec = _recommend_blitz(camp, trend)
        if blitz_rec and not _already_recommended(camp_id, "blitz"):
            recs_for_camp.append(blitz_rec)
        elif not blitz_rec:
            # 3. Standard budget increase
            increase_rec = _recommend_budget_increase(camp, trend)
            if increase_rec and not _already_recommended(camp_id, "budget_increase"):
                recs_for_camp.append(increase_rec)

        for rec in recs_for_camp:
            rec["campaign_id"]   = camp_id
            rec["campaign_name"] = camp["name"]
            rec["platform"]      = camp["platform"]
            recommendations.append(rec)
            logger.info(
                "Recommendation: [%s] %s — %s",
                rec["action_type"], camp["name"], rec["recommendation"][:60],
            )

    return recommendations


# ---------------------------------------------------------------------------
# Write to Supabase and send emails
# ---------------------------------------------------------------------------

def publish_recommendations(recommendations: list[dict]) -> int:
    """Write recommendations to Supabase and send email notifications."""
    if not recommendations:
        return 0

    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=RECOMMENDATION_TTL_HOURS)
    ).isoformat()

    sent = 0
    for rec in recommendations:
        payload = {**rec, "expires_at": expires_at, "status": "pending"}
        rec_id = _write_recommendation(payload)

        if rec_id:
            _log_recommendation_action(rec["campaign_id"], rec["action_type"], rec)
            email_ok = _send_recommendation_email(rec, rec_id)
            if email_ok:
                sent += 1
                logger.info("Recommendation #%d emailed", rec_id)
        else:
            logger.warning("Failed to write recommendation to Supabase")

    return sent


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> dict:
    logger.info("=== Recommendation Agent starting ===")
    db.heartbeat(AGENT_NAME, "alive")

    recs  = analyze_and_recommend()
    sent  = publish_recommendations(recs)

    result = {
        "recommendations_generated": len(recs),
        "emails_sent": sent,
        "campaigns_analyzed": len(_get_campaign_performance()),
    }

    db.heartbeat(AGENT_NAME, "alive", metadata=result)
    logger.info("=== Recommendation Agent done — %d recommendation(s), %d email(s) ===",
                len(recs), sent)
    return result


if __name__ == "__main__":
    run()
