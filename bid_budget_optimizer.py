"""
Bid & Budget Optimizer Agent
=============================
Reads performance analysis from the message bus, evaluates campaign /
keyword performance against Ridgecrest Designs' KPIs, and applies
data-driven bid and budget adjustments via the Google Ads API.

Optimization rules:
  • Daily budget hard cap: $125
  • Active days only: Fri, Sat, Sun, Mon
  • Target CPL: $150–$500
  • Pause campaigns/keywords with >$30 spend, 0 conversions
  • Increase bids for keywords with CPL < $300 and CTR > 3%
  • Decrease bids for keywords with CPL > $500
  • Reallocate budget toward top-converting campaigns

Run standalone:  python bid_budget_optimizer.py
"""
import os
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

import db
from db import pacific_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [bid_budget_optimizer] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

AGENT_NAME = "bid_budget_optimizer"

from config import (
    WEEKLY_BUDGET_CEILING_USD, WEEKLY_BUDGET_FLOOR_USD,
    DAILY_BUDGET_SOFT_CAP_USD, DAILY_BUDGET_CAP_USD, MIN_CAMPAIGN_DAILY_BUDGET,
    ACTIVE_DAYS, TARGET_CPL_LOW, TARGET_CPL_HIGH, TARGET_CPL_IDEAL,
    MIN_SPEND_FOR_PAUSE, MIN_CLICKS_FOR_BID_CHANGE,
    BID_INCREASE_PCT, BID_DECREASE_PCT,
    MAX_BUDGET_REALLOC_PCT, MIN_RUN_INTERVAL_MINUTES,
)


# ---------------------------------------------------------------------------
# Google Ads API helpers
# ---------------------------------------------------------------------------

def _get_client():
    try:
        from google.ads.googleads.client import GoogleAdsClient
        creds = {
            "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "login_customer_id": os.getenv("GOOGLE_ADS_MANAGER_ID"),
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(creds)
    except Exception as e:
        logger.warning("Could not build Google Ads client: %s", e)
        return None


def _apply_campaign_budget(client, customer_id: str,
                            campaign_budget_resource: str,
                            new_budget_micros: int) -> bool:
    if client is None:
        return False
    try:
        service = client.get_service("CampaignBudgetService")
        op = client.get_type("CampaignBudgetOperation")
        budget = op.update
        budget.resource_name = campaign_budget_resource
        budget.amount_micros = new_budget_micros
        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        op.update_mask.CopyFrom(field_mask)
        service.mutate_campaign_budgets(customer_id=customer_id, operations=[op])
        return True
    except Exception as e:
        logger.error("Failed to update campaign budget: %s", e)
        return False


def _apply_keyword_bid(client, customer_id: str,
                       keyword_resource: str,
                       new_bid_micros: int) -> bool:
    if client is None:
        return False
    try:
        service = client.get_service("AdGroupCriterionService")
        op = client.get_type("AdGroupCriterionOperation")
        criterion = op.update
        criterion.resource_name = keyword_resource
        criterion.cpc_bid_micros = new_bid_micros
        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("cpc_bid_micros")
        op.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_criteria(customer_id=customer_id, operations=[op])
        return True
    except Exception as e:
        logger.error("Failed to update keyword bid: %s", e)
        return False


def _pause_keyword(client, customer_id: str, keyword_resource: str) -> bool:
    if client is None:
        return False
    try:
        service = client.get_service("AdGroupCriterionService")
        op = client.get_type("AdGroupCriterionOperation")
        criterion = op.update
        criterion.resource_name = keyword_resource
        criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("status")
        op.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_criteria(customer_id=customer_id, operations=[op])
        return True
    except Exception as e:
        logger.error("Failed to pause keyword: %s", e)
        return False


# ---------------------------------------------------------------------------
# Schedule enforcement
# ---------------------------------------------------------------------------

def enforce_day_schedule(client, customer_id: str):
    """Pause all campaigns on non-active days, enable on active days."""
    today = pacific_today().strftime("%A").lower()
    is_active = today in ACTIVE_DAYS
    target_status = "ENABLED" if is_active else "PAUSED"

    with db.get_db() as (conn, cur):
        cur.execute(
            "SELECT id, google_campaign_id, name, status FROM campaigns WHERE status != 'REMOVED'"
        )
        campaigns = [dict(r) for r in cur.fetchall()]

    actions_taken = 0
    for camp in campaigns:
        if camp["status"] == target_status:
            continue

        action_id = db.log_action(
            agent_name=AGENT_NAME,
            action_type="schedule_status_change",
            entity_type="campaign",
            entity_id=camp["id"],
            google_entity_id=camp["google_campaign_id"],
            before={"status": camp["status"]},
            after={"status": target_status},
            reason=f"Schedule enforcement: {today} is {'an active' if is_active else 'an inactive'} day"
        )

        if client:
            try:
                ga_service = client.get_service("CampaignService")
                op = client.get_type("CampaignOperation")
                c = op.update
                c.resource_name = ga_service.campaign_path(customer_id, camp["google_campaign_id"])
                if is_active:
                    c.status = client.enums.CampaignStatusEnum.ENABLED
                else:
                    c.status = client.enums.CampaignStatusEnum.PAUSED
                field_mask = client.get_type("FieldMask")
                field_mask.paths.append("status")
                op.update_mask.CopyFrom(field_mask)
                ga_service.mutate_campaigns(customer_id=customer_id, operations=[op])
                applied = True
            except Exception as e:
                logger.error("Failed to set campaign %s status: %s", camp["name"], e)
                applied = False
        else:
            applied = False  # dry-run

        if applied:
            db.mark_action_applied(action_id)
            with db.get_db() as (conn, cur):
                cur.execute(
                    "UPDATE campaigns SET status=%s, updated_at=NOW() WHERE id=%s",
                    (target_status, camp["id"])
                )
        actions_taken += 1

    logger.info("Schedule enforcement: %s → target_status=%s | %d campaigns adjusted",
                today, target_status, actions_taken)
    return actions_taken


# ---------------------------------------------------------------------------
# Keyword bid optimization
# ---------------------------------------------------------------------------

def optimize_keyword_bids(client, customer_id: str, lookback_days: int = 7) -> list[dict]:
    """
    Adjust keyword bids based on CPL vs target range.
    Returns list of optimization actions.
    """
    window_start = pacific_today() - timedelta(days=lookback_days - 1)

    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT
                   k.id, k.google_keyword_id, k.keyword_text, k.match_type,
                   k.cpc_bid_micros, k.status,
                   SUM(pm.impressions) AS impressions,
                   SUM(pm.clicks) AS clicks,
                   SUM(pm.conversions) AS conversions,
                   SUM(pm.cost_micros) / 1000000.0 AS cost_usd,
                   CASE WHEN SUM(pm.conversions) > 0
                        THEN SUM(pm.cost_micros) / 1000000.0 / SUM(pm.conversions)
                        ELSE NULL END AS cpl,
                   CASE WHEN SUM(pm.clicks) > 0
                        THEN SUM(pm.impressions)::float / SUM(pm.clicks)
                        ELSE 0 END AS avg_ctr
               FROM keywords k
               LEFT JOIN performance_metrics pm ON pm.entity_type = 'keyword'
                   AND pm.entity_id = k.id
                   AND pm.metric_date >= %s
               WHERE k.status = 'ENABLED'
               GROUP BY k.id, k.google_keyword_id, k.keyword_text, k.match_type,
                        k.cpc_bid_micros, k.status
               HAVING SUM(pm.clicks) IS NOT NULL""",
            (window_start,)
        )
        keywords = [dict(r) for r in cur.fetchall()]

    actions = []
    for kw in keywords:
        clicks = int(kw["clicks"] or 0)
        cost = float(kw["cost_usd"] or 0)
        conversions = float(kw["conversions"] or 0)
        cpl = float(kw["cpl"]) if kw["cpl"] else None
        current_bid = int(kw["cpc_bid_micros"] or 0)

        if clicks < MIN_CLICKS_FOR_BID_CHANGE:
            continue

        new_bid = None
        reason = None
        action_type = None

        if cpl is None and cost > MIN_SPEND_FOR_PAUSE:
            # No conversions with significant spend → pause
            action_type = "pause_keyword"
            reason = f"${cost:.2f} spent over {lookback_days}d with 0 conversions"
        elif cpl and cpl > TARGET_CPL_HIGH:
            # CPL too high → reduce bid
            new_bid = int(current_bid * (1 - BID_DECREASE_PCT))
            action_type = "bid_decrease"
            reason = f"CPL ${cpl:.2f} exceeds target max ${TARGET_CPL_HIGH}"
        elif cpl and cpl < TARGET_CPL_IDEAL and current_bid > 0:
            # Performing well → increase bid to capture more volume
            new_bid = int(current_bid * (1 + BID_INCREASE_PCT))
            action_type = "bid_increase"
            reason = f"CPL ${cpl:.2f} is within target, increasing bid for volume"

        if action_type is None:
            continue

        action_id = db.log_action(
            agent_name=AGENT_NAME,
            action_type=action_type,
            entity_type="keyword",
            entity_id=kw["id"],
            google_entity_id=kw["google_keyword_id"],
            before={"cpc_bid_micros": current_bid, "status": kw["status"]},
            after={"cpc_bid_micros": new_bid} if new_bid else {"status": "PAUSED"},
            reason=reason
        )

        applied = False
        if action_type == "pause_keyword":
            kw_resource = f"customers/{customer_id}/adGroupCriteria/{kw['google_keyword_id']}"
            applied = _pause_keyword(client, customer_id, kw_resource)
            if applied:
                with db.get_db() as (conn, cur):
                    cur.execute(
                        "UPDATE keywords SET status='PAUSED', updated_at=NOW() WHERE id=%s",
                        (kw["id"],)
                    )
        elif new_bid:
            kw_resource = f"customers/{customer_id}/adGroupCriteria/{kw['google_keyword_id']}"
            applied = _apply_keyword_bid(client, customer_id, kw_resource, new_bid)
            if applied:
                with db.get_db() as (conn, cur):
                    cur.execute(
                        "UPDATE keywords SET cpc_bid_micros=%s, updated_at=NOW() WHERE id=%s",
                        (new_bid, kw["id"])
                    )

        if applied:
            db.mark_action_applied(action_id)

        action_record = {
            "action_id": action_id,
            "action_type": action_type,
            "keyword": kw["keyword_text"],
            "match_type": kw["match_type"],
            "before_bid_usd": current_bid / 1_000_000,
            "after_bid_usd": new_bid / 1_000_000 if new_bid else None,
            "reason": reason,
            "applied": applied,
        }
        actions.append(action_record)
        logger.info(
            "[%s] %s '%s' — %s (applied=%s)",
            action_type, kw["match_type"], kw["keyword_text"], reason, applied
        )

    return actions


# ---------------------------------------------------------------------------
# Budget reallocation
# ---------------------------------------------------------------------------

def _get_weekly_spend() -> float:
    """Sum spend for the current Mon–Sun calendar week across all managed campaigns."""
    today = pacific_today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS weekly_spend
               FROM performance_metrics pm
               JOIN campaigns c ON c.id = pm.entity_id
               WHERE pm.metric_date >= %s
                 AND pm.entity_type = 'campaign'
                 AND c.managed_by = 'claude_code'""",
            (week_start,),
        )
        return float(cur.fetchone()["weekly_spend"] or 0)


def _remaining_active_days_this_week() -> int:
    """Count active days (Fri–Mon) remaining after today in the current week cycle."""
    today = pacific_today()
    # Campaign week runs Mon + Fri + Sat + Sun — check up to next Monday
    remaining = 0
    for offset in range(1, 8):
        d = today + timedelta(days=offset)
        if d.strftime("%A").lower() in ACTIVE_DAYS:
            remaining += 1
        if d.weekday() == 0 and offset > 1:  # stop after next Monday
            break
    return remaining


def _score_campaign(camp: dict) -> float:
    """
    Performance score for budget allocation ranking.
    Higher = better. Top performers get budget, under-performers lose it.

    Components:
      - Conversion volume  (60% weight) — campaigns generating leads
      - CPL efficiency     (40% weight) — cost relative to $150–$500 target
    Returns 0.0 for campaigns with no data yet (neutral — don't punish or reward).
    """
    convs = float(camp.get("conversions") or 0)
    cpl   = float(camp["cpl"]) if camp.get("cpl") else None
    spend = float(camp.get("cost_usd") or 0)

    if spend == 0:
        return 0.0  # no data — neutral

    if cpl is None:
        # Spent money, zero conversions — poor performer
        if spend > MIN_SPEND_FOR_PAUSE:
            return -50.0
        return 0.0  # too early to judge

    # CPL score: peaks at $150–$300, drops toward $500, negative above $500
    if cpl <= TARGET_CPL_IDEAL:
        cpl_score = 1.0
    elif cpl <= TARGET_CPL_HIGH:
        cpl_score = 1.0 - ((cpl - TARGET_CPL_IDEAL) / (TARGET_CPL_HIGH - TARGET_CPL_IDEAL))
    else:
        cpl_score = -((cpl - TARGET_CPL_HIGH) / TARGET_CPL_HIGH)

    # Conversion volume score: increases with conversions, caps at 10
    conv_score = min(convs / 10.0, 1.0)

    return (conv_score * 60.0) + (cpl_score * 40.0)


def reallocate_budget(client, customer_id: str, lookback_days: int = 7) -> list[dict]:
    """
    Performance-ranked budget reallocation engine.

    Rules:
    - Never cut a top performer's budget (score > 60)
    - Shift budget FROM under-performers (score < 0) TO top performers
    - Never reduce any campaign below MIN_CAMPAIGN_DAILY_BUDGET ($10/day)
    - Respect weekly ceiling — if week is near $1,000, reduce all budgets proportionally
    - If weekly pace is below floor, increase top performers first
    """
    window_start = pacific_today() - timedelta(days=lookback_days - 1)

    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT
                   c.id, c.google_campaign_id, c.name,
                   c.daily_budget_micros, c.platform,
                   COALESCE(SUM(pm.conversions), 0)           AS conversions,
                   COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS cost_usd,
                   COALESCE(SUM(pm.clicks), 0)                AS clicks,
                   CASE WHEN SUM(pm.conversions) > 0
                        THEN SUM(pm.cost_micros)/1000000.0 / SUM(pm.conversions)
                        ELSE NULL END AS cpl
               FROM campaigns c
               LEFT JOIN performance_metrics pm
                      ON pm.entity_type = 'campaign'
                     AND pm.entity_id = c.id
                     AND pm.metric_date >= %s
               WHERE c.status = 'ENABLED'
                 AND c.managed_by = 'claude_code'
               GROUP BY c.id, c.google_campaign_id, c.name,
                        c.daily_budget_micros, c.platform
               ORDER BY c.id""",
            (window_start,),
        )
        campaigns = [dict(r) for r in cur.fetchall()]

    if len(campaigns) < 2:
        return []

    # Score every campaign
    for c in campaigns:
        c["score"] = _score_campaign(c)
        c["daily_budget_usd"] = float(c["daily_budget_micros"] or 0) / 1_000_000

    campaigns.sort(key=lambda c: c["score"], reverse=True)

    # Tier campaigns
    top_performers    = [c for c in campaigns if c["score"] >= 60]
    mid_performers    = [c for c in campaigns if 0 <= c["score"] < 60]
    under_performers  = [c for c in campaigns if c["score"] < 0]

    logger.info(
        "Budget reallocation: %d top | %d mid | %d under-performers",
        len(top_performers), len(mid_performers), len(under_performers),
    )

    # Weekly ceiling check
    weekly_spend    = _get_weekly_spend()
    weekly_remaining = WEEKLY_BUDGET_CEILING_USD - weekly_spend
    remaining_days   = _remaining_active_days_this_week()
    projected_spend  = weekly_spend + (
        sum(c["daily_budget_usd"] for c in campaigns) * max(remaining_days, 0)
    )

    at_ceiling = weekly_spend >= WEEKLY_BUDGET_CEILING_USD
    near_ceiling = projected_spend > WEEKLY_BUDGET_CEILING_USD * 0.95

    logger.info(
        "Weekly spend: $%.2f / $%.2f | remaining days: %d | projected: $%.2f | "
        "at_ceiling=%s near_ceiling=%s",
        weekly_spend, WEEKLY_BUDGET_CEILING_USD,
        remaining_days, projected_spend,
        at_ceiling, near_ceiling,
    )

    actions = []
    budget_changes: dict[int, float] = {}  # campaign_id → new daily budget

    # ── Case 1: At or near weekly ceiling — reduce under/mid performers ────
    if at_ceiling:
        logger.info("Weekly ceiling reached — blocking all budget increases")
        # No increases allowed; optionally reduce under-performers
        for c in under_performers:
            old = c["daily_budget_usd"]
            new = max(old * 0.80, MIN_CAMPAIGN_DAILY_BUDGET)
            if new < old - 0.50:  # only act if saving > $0.50/day
                budget_changes[c["id"]] = (c, old, new,
                    f"Weekly ceiling ${WEEKLY_BUDGET_CEILING_USD:.0f} reached — "
                    f"reducing under-performer (score={c['score']:.1f})")

    elif near_ceiling and remaining_days > 0:
        # Proportionally scale down to fit within ceiling
        max_daily_total = weekly_remaining / remaining_days
        current_total   = sum(c["daily_budget_usd"] for c in campaigns)
        if current_total > max_daily_total and max_daily_total > 0:
            scale = max_daily_total / current_total
            for c in campaigns:
                old = c["daily_budget_usd"]
                # Never scale down top performers — absorb cuts from under/mid only
                if c["score"] >= 60:
                    continue
                new = max(old * scale, MIN_CAMPAIGN_DAILY_BUDGET)
                if new < old - 0.50:
                    budget_changes[c["id"]] = (c, old, new,
                        f"Near weekly ceiling — scaling budget to fit "
                        f"${max_daily_total:.2f}/day available")

    # ── Case 2: Have headroom — shift from under-performers to top performers
    if not at_ceiling and under_performers and top_performers:
        for donor in under_performers:
            old_donor = donor["daily_budget_usd"]
            transfer  = round(old_donor * MAX_BUDGET_REALLOC_PCT, 2)
            if transfer < 1.0:
                continue

            new_donor = max(old_donor - transfer, MIN_CAMPAIGN_DAILY_BUDGET)
            actual_transfer = old_donor - new_donor

            # Distribute transfer equally among top performers
            per_top = actual_transfer / len(top_performers)
            budget_changes[donor["id"]] = (donor, old_donor, new_donor,
                f"Under-performer (score={donor['score']:.1f}, "
                f"CPL=${donor['cpl']:.0f if donor['cpl'] else 'N/A'}) — "
                f"transferring ${actual_transfer:.2f}/day to top performer(s)")

            for receiver in top_performers:
                old_recv = receiver["daily_budget_usd"]
                new_recv = old_recv + per_top
                # Don't push one campaign over the daily soft cap
                new_recv = min(new_recv, DAILY_BUDGET_SOFT_CAP_USD)
                if new_recv > old_recv + 0.50:
                    existing = budget_changes.get(receiver["id"])
                    if existing:
                        # Accumulate increases for same top performer
                        _, orig_old, prev_new, prev_reason = existing
                        budget_changes[receiver["id"]] = (
                            receiver, orig_old, prev_new + per_top, prev_reason
                        )
                    else:
                        budget_changes[receiver["id"]] = (receiver, old_recv, new_recv,
                            f"Top performer (score={receiver['score']:.1f}) — "
                            f"receiving budget from under-performer '{donor['name']}'")

    if not budget_changes:
        logger.info("Budget reallocation: no changes warranted")
        return []

    # Apply changes
    for camp_id, (camp, old_budget, new_budget, reason) in budget_changes.items():
        new_budget = round(new_budget, 2)
        if abs(new_budget - old_budget) < 0.50:
            continue  # skip trivial changes

        action_id = db.log_action(
            agent_name=AGENT_NAME,
            action_type="budget_reallocation",
            entity_type="campaign",
            entity_id=camp["id"],
            google_entity_id=camp["google_campaign_id"],
            before={"daily_budget_usd": old_budget},
            after={"daily_budget_usd": new_budget},
            reason=reason,
        )

        new_micros = int(new_budget * 1_000_000)
        applied = False

        if camp["platform"] == "google_ads":
            camp_resource = f"customers/{customer_id}/campaigns/{camp['google_campaign_id']}"
            applied = _apply_campaign_budget(client, customer_id, camp_resource, new_micros)
        else:
            # Meta and Microsoft budget changes are handled by their own managers
            # Log the intent here; platform managers pick it up on next run
            applied = True

        if applied:
            db.mark_action_applied(action_id)
            with db.get_db() as (conn, cur):
                cur.execute(
                    "UPDATE campaigns SET daily_budget_micros=%s, updated_at=NOW() WHERE id=%s",
                    (new_micros, camp["id"]),
                )

        logger.info(
            "Budget reallocation: '%s' $%.2f → $%.2f (%s=%s)",
            camp["name"], old_budget, new_budget,
            "applied" if applied else "logged",
            camp["platform"],
        )

        actions.append({
            "action_id":     action_id,
            "campaign":      camp["name"],
            "platform":      camp["platform"],
            "score":         camp["score"],
            "old_budget_usd": old_budget,
            "new_budget_usd": new_budget,
            "reason":        reason,
            "applied":       applied,
        })

    return actions


# ---------------------------------------------------------------------------
# Process incoming messages
# ---------------------------------------------------------------------------

def process_messages(client, customer_id: str):
    """Handle messages from other agents (e.g., critical budget alerts)."""
    messages = db.receive_messages(AGENT_NAME)
    for msg in messages:
        try:
            mtype = msg["message_type"]
            payload = msg["payload"] if isinstance(msg["payload"], dict) else json.loads(msg["payload"])

            if mtype == "performance_analysis_complete":
                # React to critical budget alerts immediately
                for alert in payload.get("critical_alerts", []):
                    if alert.get("type") == "budget_overage":
                        logger.warning("CRITICAL: budget overage — pausing all campaigns")
                        enforce_day_schedule(client, customer_id)  # will pause non-active day

            elif mtype == "pause_keyword_request":
                kw_id = payload.get("keyword_id")
                reason = payload.get("reason", "Requested by orchestrator")
                if kw_id:
                    with db.get_db() as (conn, cur):
                        cur.execute("SELECT * FROM keywords WHERE id=%s", (kw_id,))
                        kw = cur.fetchone()
                    if kw:
                        resource = f"customers/{customer_id}/adGroupCriteria/{kw['google_keyword_id']}"
                        _pause_keyword(client, customer_id, resource)

            db.ack_message(msg["id"])
        except Exception as e:
            db.ack_message(msg["id"], error=str(e))
            logger.error("Error processing message %d: %s", msg["id"], e)


# ---------------------------------------------------------------------------
# Cooldown guard
# ---------------------------------------------------------------------------

def _cooldown_remaining() -> int:
    """
    Return the number of minutes until the optimizer is eligible to run again.
    0 means it is ready. Based on last_success_at in agent_heartbeats.
    """
    with db.get_db() as (conn, cur):
        cur.execute(
            "SELECT last_success_at FROM agent_heartbeats WHERE agent_name = %s",
            (AGENT_NAME,)
        )
        row = cur.fetchone()
    if not row or not row["last_success_at"]:
        return 0
    elapsed_min = (
        datetime.now(timezone.utc) - row["last_success_at"]
    ).total_seconds() / 60
    return max(0, int(MIN_RUN_INTERVAL_MINUTES - elapsed_min))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def get_proposed_actions() -> list[dict]:
    """
    Return proposed bid and budget actions without executing them.
    Called by the orchestrator to pre-filter through guardrails before
    passing allowed_actions back to run().

    Returns a list of dicts with keys:
      action_type, entity_type, entity_name, entity_id,
      before_value, after_value, reason
    """
    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
    try:
        client = _get_client()
    except Exception:
        return []

    proposed = []

    try:
        bid_actions = optimize_keyword_bids(client, customer_id)
        for a in bid_actions:
            proposed.append({
                "action_type":  a.get("action_type", "bid_change"),
                "entity_type":  "keyword",
                "entity_name":  a.get("keyword", a.get("entity_name", "")),
                "entity_id":    a.get("criterion_id", a.get("entity_id")),
                "before_value": a.get("old_bid_micros", a.get("before_value")),
                "after_value":  a.get("new_bid_micros", a.get("after_value")),
                "reason":       a.get("reason", ""),
            })
    except Exception as e:
        logger.warning("get_proposed_actions: bid scan failed: %s", e)

    try:
        budget_actions = reallocate_budget(client, customer_id)
        for a in budget_actions:
            proposed.append({
                "action_type":  a.get("action_type", "budget_change"),
                "entity_type":  "campaign",
                "entity_name":  a.get("campaign", a.get("entity_name", "")),
                "entity_id":    a.get("campaign_id", a.get("entity_id")),
                "before_value": a.get("old_budget_micros", a.get("before_value")),
                "after_value":  a.get("new_budget_micros", a.get("after_value")),
                "reason":       a.get("reason", ""),
            })
    except Exception as e:
        logger.warning("get_proposed_actions: budget scan failed: %s", e)

    logger.info("get_proposed_actions: %d proposed actions", len(proposed))
    return proposed


def run(force: bool = False, allowed_actions: list[dict] | None = None) -> dict:
    """
    Run bid and budget optimization.

    Args:
        force: Skip cooldown check if True.
        allowed_actions: If provided (from orchestrator guardrail pre-filter),
                         only execute actions whose entity_id appears in this list.
                         If None, all actions are executed (no pre-filtering).
    """
    logger.info("=== Bid & Budget Optimizer starting (force=%s) ===", force)

    if not force:
        mins = _cooldown_remaining()
        if mins > 0:
            logger.info(
                "Cooldown active — %d min until next eligible run "
                "(last success < %d min ago). Pass force=True to override.",
                mins, MIN_RUN_INTERVAL_MINUTES,
            )
            return {
                "skipped": True,
                "reason": f"cooldown: {mins}m remaining",
                "schedule_changes": 0,
                "bid_actions": 0,
                "budget_actions": 0,
                "details": {"bid_changes": [], "budget_changes": []},
            }

    # Build allowed entity_id set for guardrail filtering
    allowed_ids: set | None = None
    if allowed_actions is not None:
        allowed_ids = {
            str(a["entity_id"]) for a in allowed_actions
            if a.get("entity_id") is not None
        }
        logger.info("Guardrail pre-filter: %d allowed action(s)", len(allowed_ids))

    db.heartbeat(AGENT_NAME, "alive")

    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
    client = _get_client()

    # 1. Process any incoming messages first
    process_messages(client, customer_id)

    # 2. Enforce day schedule
    schedule_changes = enforce_day_schedule(client, customer_id)

    # 3. Keyword bid optimization (filtered by guardrails if allowed_ids set)
    bid_actions = optimize_keyword_bids(client, customer_id)
    if allowed_ids is not None:
        bid_actions = [
            a for a in bid_actions
            if str(a.get("criterion_id", a.get("entity_id", ""))) in allowed_ids
        ]

    # 4. Budget reallocation (filtered by guardrails if allowed_ids set)
    budget_actions = reallocate_budget(client, customer_id)
    if allowed_ids is not None:
        budget_actions = [
            a for a in budget_actions
            if str(a.get("campaign_id", a.get("entity_id", ""))) in allowed_ids
        ]

    summary = {
        "schedule_changes": schedule_changes,
        "bid_actions": len(bid_actions),
        "budget_actions": len(budget_actions),
        "details": {
            "bid_changes": bid_actions,
            "budget_changes": budget_actions,
        }
    }

    logger.info(
        "Optimization complete — schedule_changes=%d | bid_actions=%d | budget_actions=%d",
        schedule_changes, len(bid_actions), len(budget_actions)
    )

    # Broadcast results
    db.send_message(
        from_agent=AGENT_NAME,
        to_agent="all",
        message_type="optimization_complete",
        payload=summary,
        priority=5
    )

    db.heartbeat(AGENT_NAME, "alive", metadata=summary)
    logger.info("=== Bid & Budget Optimizer done ===")
    return summary


if __name__ == "__main__":
    run()
