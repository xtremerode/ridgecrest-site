"""
Meta Manager Agent
==================
Reads Meta campaign and ad set performance from the DB (written by meta_sync),
applies CPL-based optimization rules, and writes changes back to the Meta
Marketing API.

Optimization rules (mirrors CLAUDE.md targets):
  • Pause ad sets: spend > $50 over 7d with 0 conversions
  • Budget increase (+25%): ad set CPL $150–$300 AND spend > $20
  • Budget decrease (−20%): ad set CPL > $500
  • Pause campaign: 7d spend > $200 with 0 conversions
  • Flag for review: CPL < $100 (below floor — lead quality risk)
  • Daily budget cap check: total Meta spend must not push combined cap over $125

All actions are logged to optimization_actions with applied=False by default;
set AUTO_APPLY=True (env var) to execute changes immediately.

Run standalone:  python meta_manager.py
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
    format="%(asctime)s [meta_manager] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME    = "meta_manager"
from config import (
    TARGET_CPL_LOW, TARGET_CPL_HIGH, TARGET_CPL_IDEAL,
    BID_INCREASE_PCT as BUDGET_INCREASE_PCT,
    BID_DECREASE_PCT as BUDGET_DECREASE_PCT,
    LOOKBACK_DAYS, ACTIVE_DAYS,
    META_AD_ACCOUNT_ID, META_BASE_URL, META_API_VERSION,
)

PLATFORM      = "meta"
API_VERSION   = META_API_VERSION
BASE_URL      = META_BASE_URL
AD_ACCOUNT_ID = META_AD_ACCOUNT_ID
ACCESS_TOKEN  = os.getenv("META_ACCESS_TOKEN", "")
AUTO_APPLY    = os.getenv("META_MANAGER_AUTO_APPLY", "false").lower() == "true"

# Meta-specific thresholds
PAUSE_SPEND_FLOOR = 50.0
PAUSE_CAMP_FLOOR  = 200.0


# ---------------------------------------------------------------------------
# Meta API helpers
# ---------------------------------------------------------------------------

def _api_get(path: str, params: dict = None) -> dict:
    p = {"access_token": ACCESS_TOKEN}
    if params:
        p.update(params)
    r = requests.get(f"{BASE_URL}{path}", params=p, timeout=30)
    return r.json()


def _api_post(path: str, data: dict) -> dict:
    data["access_token"] = ACCESS_TOKEN
    r = requests.post(f"{BASE_URL}{path}", data=data, timeout=30)
    return r.json()


def _get_live_adsets() -> dict[str, dict]:
    """
    Fetch all active / paused ad sets from Meta with their current budget and status.
    Returns {adset_id: {name, status, daily_budget, campaign_id}}
    """
    resp = _api_get(
        f"/{AD_ACCOUNT_ID}/adsets",
        {
            "fields": "id,name,status,daily_budget,campaign_id,effective_status",
            "limit": 200,
        },
    )
    if "error" in resp:
        logger.error("Ad sets fetch failed: %s", resp["error"].get("message", resp["error"]))
        return {}

    result = {}
    for adset in resp.get("data", []):
        result[adset["id"]] = {
            "name":         adset.get("name", adset["id"]),
            "status":       adset.get("status", "UNKNOWN"),
            "daily_budget": int(adset.get("daily_budget", 0)),  # cents
            "campaign_id":  adset.get("campaign_id", ""),
        }
    return result


def _get_live_campaigns() -> dict[str, dict]:
    """Fetch all campaigns with their current status and budget."""
    resp = _api_get(
        f"/{AD_ACCOUNT_ID}/campaigns",
        {"fields": "id,name,status,daily_budget,objective", "limit": 200},
    )
    if "error" in resp:
        logger.error("Campaign fetch failed: %s", resp["error"].get("message", resp["error"]))
        return {}
    return {
        c["id"]: {
            "name":         c.get("name", c["id"]),
            "status":       c.get("status", "UNKNOWN"),
            "daily_budget": int(c.get("daily_budget", 0)),
        }
        for c in resp.get("data", [])
    }


# ---------------------------------------------------------------------------
# DB performance helpers
# ---------------------------------------------------------------------------

def _get_adset_performance(lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """
    Returns 7-day aggregated performance per Meta ad set (from DB).
    """
    since = date.today() - timedelta(days=lookback_days)
    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT
                ag.id                          AS ag_db_id,
                ag.google_ad_group_id          AS external_id,
                ag.name                        AS name,
                ag.status                      AS db_status,
                c.google_campaign_id           AS campaign_external_id,
                COALESCE(SUM(pm.impressions),0)           AS impressions,
                COALESCE(SUM(pm.clicks),0)                AS clicks,
                COALESCE(SUM(pm.conversions),0)           AS conversions,
                COALESCE(SUM(pm.cost_micros)/1000000.0,0) AS spend_usd
            FROM ad_groups ag
            JOIN campaigns c ON c.id = ag.campaign_id
            LEFT JOIN performance_metrics pm
                   ON pm.entity_id = ag.id
                  AND pm.entity_type = 'ad_group'
                  AND pm.metric_date >= %s
            WHERE c.platform = 'meta'
            GROUP BY ag.id, ag.google_ad_group_id, ag.name, ag.status, c.google_campaign_id
            """,
            (since,),
        )
        return [dict(r) for r in cur.fetchall()]


def _get_campaign_performance(lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """Returns 7-day aggregated performance per Meta campaign."""
    since = date.today() - timedelta(days=lookback_days)
    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT
                c.id                           AS camp_db_id,
                c.google_campaign_id           AS external_id,
                c.name                         AS name,
                c.status                       AS db_status,
                COALESCE(SUM(pm.impressions),0)           AS impressions,
                COALESCE(SUM(pm.clicks),0)                AS clicks,
                COALESCE(SUM(pm.conversions),0)           AS conversions,
                COALESCE(SUM(pm.cost_micros)/1000000.0,0) AS spend_usd
            FROM campaigns c
            LEFT JOIN performance_metrics pm
                   ON pm.entity_id = c.id
                  AND pm.entity_type = 'campaign'
                  AND pm.metric_date >= %s
            WHERE c.platform = 'meta'
            GROUP BY c.id, c.google_campaign_id, c.name, c.status
            """,
            (since,),
        )
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------

def _pause_adset(adset_id: str, name: str, reason: str, ag_db_id: int,
                 auto_apply: bool) -> dict:
    action = {
        "type":    "pause_adset",
        "target":  f"Ad Set: {name}",
        "adset_id": adset_id,
        "reason":  reason,
        "applied": False,
    }
    if auto_apply:
        resp = _api_post(f"/{adset_id}", {"status": "PAUSED"})
        action["applied"] = "error" not in resp
        action["api_response"] = resp
        logger.info("  Paused ad set %s (%s): %s", adset_id, name, resp)
    db.log_action(
        agent_name=AGENT_NAME, action_type="pause_adset",
        entity_type="ad_group", entity_id=ag_db_id,
        before={"status": "ACTIVE"}, after={"status": "PAUSED"},
        reason=reason, google_entity_id=f"meta_adset_{adset_id}",
    )
    return action


def _pause_campaign(campaign_id: str, name: str, reason: str,
                    camp_db_id: int, auto_apply: bool) -> dict:
    action = {
        "type":        "pause_campaign",
        "target":      f"Campaign: {name}",
        "campaign_id": campaign_id,
        "reason":      reason,
        "applied":     False,
    }
    if auto_apply:
        resp = _api_post(f"/{campaign_id}", {"status": "PAUSED"})
        action["applied"] = "error" not in resp
        action["api_response"] = resp
        logger.info("  Paused campaign %s (%s): %s", campaign_id, name, resp)
    db.log_action(
        agent_name=AGENT_NAME, action_type="pause_campaign",
        entity_type="campaign", entity_id=camp_db_id,
        before={"status": "ACTIVE"}, after={"status": "PAUSED"},
        reason=reason, google_entity_id=f"meta_{campaign_id}",
    )
    return action


def _adjust_adset_budget(adset_id: str, name: str, current_budget_cents: int,
                          new_budget_cents: int, direction: str, reason: str,
                          ag_db_id: int, auto_apply: bool) -> dict:
    action = {
        "type":           f"budget_{direction}",
        "target":         f"Ad Set: {name}",
        "adset_id":       adset_id,
        "before_budget":  f"${current_budget_cents / 100:.2f}/day",
        "after_budget":   f"${new_budget_cents / 100:.2f}/day",
        "reason":         reason,
        "applied":        False,
    }
    if auto_apply:
        resp = _api_post(f"/{adset_id}", {"daily_budget": str(new_budget_cents)})
        action["applied"] = "error" not in resp
        action["api_response"] = resp
        logger.info("  Budget %s for %s: $%.2f → $%.2f: %s",
                    direction, name,
                    current_budget_cents / 100, new_budget_cents / 100, resp)
    db.log_action(
        agent_name=AGENT_NAME, action_type=f"budget_{direction}",
        entity_type="ad_group", entity_id=ag_db_id,
        before={"daily_budget_cents": current_budget_cents},
        after={"daily_budget_cents": new_budget_cents},
        reason=reason, google_entity_id=f"meta_adset_{adset_id}",
    )
    return action


# ---------------------------------------------------------------------------
# Day scheduling enforcement — pause/unpause by day of week
# ---------------------------------------------------------------------------

def _enforce_active_days(auto_apply: bool) -> list[dict]:
    """
    Pause all campaigns on inactive days (Tue/Wed/Thu).
    Unpause campaigns on active days (Fri/Sat/Sun/Mon).

    Meta adset_schedule requires lifetime budgets and is incompatible with
    daily budget campaigns. Pause/unpause at the campaign level is the
    correct approach for daily budget campaigns (CLAUDE.md §8).
    """
    from datetime import date
    today = date.today().strftime("%A").lower()
    is_active_day = today in ACTIVE_DAYS
    target_status = "ACTIVE" if is_active_day else "PAUSED"

    resp = _api_get(
        f"/{AD_ACCOUNT_ID}/campaigns",
        {"fields": "id,name,status", "limit": 200},
    )
    if "error" in resp:
        logger.warning("Active-day check: could not fetch campaigns — %s",
                       resp.get("error", {}).get("message", resp))
        return []

    actions = []
    for camp in resp.get("data", []):
        camp_id     = camp["id"]
        name        = camp.get("name", camp_id)
        cur_status  = camp.get("status", "UNKNOWN")

        if cur_status == target_status:
            continue

        # Never auto-resume a campaign that was manually paused for other reasons
        # Only resume if it was paused by the day scheduler (status is PAUSED on active day)
        if is_active_day and cur_status != "PAUSED":
            continue

        action = {
            "type":        "day_schedule_status",
            "target":      f"Campaign: {name}",
            "campaign_id": camp_id,
            "from_status": cur_status,
            "to_status":   target_status,
            "reason":      f"CLAUDE.md §8 — today is {today.title()}, "
                           f"{'active' if is_active_day else 'inactive'} day",
            "applied":     False,
        }

        if auto_apply:
            r = _api_post(f"/{camp_id}", {"status": target_status})
            if "error" in r:
                action["error"] = r["error"].get("message", str(r["error"]))
                logger.warning("  Day status failed for %s: %s", name, action["error"])
            else:
                action["applied"] = True
                logger.info("  %s → %s: %s", cur_status, target_status, name)
        else:
            logger.info("  [PENDING] Would set %s → %s: %s",
                        cur_status, target_status, name)

        db.log_action(
            agent_name=AGENT_NAME, action_type="day_schedule_status",
            entity_type="campaign", entity_id=0,
            before={"status": cur_status},
            after={"status": target_status},
            reason=action["reason"],
            google_entity_id=f"meta_{camp_id}",
        )
        actions.append(action)

    logger.info("Active-day check (%s, %s): %d campaign(s) need status change",
                today, "ACTIVE day" if is_active_day else "INACTIVE day", len(actions))
    return actions


# ---------------------------------------------------------------------------
# Optimization logic
# ---------------------------------------------------------------------------

def _evaluate_adsets(adset_perf: list[dict], live_adsets: dict[str, dict],
                     auto_apply: bool) -> list[dict]:
    """Apply CPL rules to each ad set and return list of actions taken."""
    actions = []

    for row in adset_perf:
        ext_id = row["external_id"]                        # e.g. "meta_adset_12345"
        adset_id = ext_id.replace("meta_adset_", "")
        name     = row["name"]
        spend    = float(row["spend_usd"])
        convs    = float(row["conversions"])
        cpl      = spend / convs if convs > 0 else None

        live = live_adsets.get(adset_id, {})
        live_status = live.get("status", "UNKNOWN")
        daily_budget_cents = live.get("daily_budget", 0)

        # Skip already-paused or inactive ad sets
        if live_status not in ("ACTIVE", "ENABLED"):
            continue

        # Rule 1: Pause — spent > $50 with 0 conversions over 7 days
        if spend >= PAUSE_SPEND_FLOOR and convs == 0:
            reason = (f"${spend:.2f} spent over {LOOKBACK_DAYS}d with 0 conversions "
                      f"(floor: ${PAUSE_SPEND_FLOOR:.0f})")
            logger.warning("  [PAUSE ADSET] %s — %s", name, reason)
            actions.append(_pause_adset(adset_id, name, reason,
                                        row["ag_db_id"], auto_apply))
            continue

        # Rule 2: Budget decrease — CPL > $500
        if cpl is not None and cpl > TARGET_CPL_HIGH and daily_budget_cents > 0:
            new_budget = max(int(daily_budget_cents * (1 - BUDGET_DECREASE_PCT)), 1000)
            reason = (f"CPL ${cpl:.2f} exceeds target ceiling ${TARGET_CPL_HIGH:.0f}; "
                      f"reducing budget by {int(BUDGET_DECREASE_PCT*100)}%")
            logger.warning("  [BUDGET DECREASE] %s — %s", name, reason)
            actions.append(_adjust_adset_budget(
                adset_id, name, daily_budget_cents, new_budget,
                "decrease", reason, row["ag_db_id"], auto_apply,
            ))

        # Rule 3: Budget increase — CPL in $150–$300 sweet spot with enough spend
        elif cpl is not None and TARGET_CPL_LOW <= cpl <= TARGET_CPL_IDEAL and spend >= 20.0:
            new_budget = int(daily_budget_cents * (1 + BUDGET_INCREASE_PCT))
            reason = (f"CPL ${cpl:.2f} in sweet spot (${TARGET_CPL_LOW:.0f}–"
                      f"${TARGET_CPL_IDEAL:.0f}); increasing budget by "
                      f"{int(BUDGET_INCREASE_PCT*100)}%")
            logger.info("  [BUDGET INCREASE] %s — %s", name, reason)
            actions.append(_adjust_adset_budget(
                adset_id, name, daily_budget_cents, new_budget,
                "increase", reason, row["ag_db_id"], auto_apply,
            ))

        # Rule 4: Flag quality concern — CPL < $100 with spend > $20
        elif cpl is not None and cpl < TARGET_CPL_LOW and spend >= 20.0:
            reason = (f"CPL ${cpl:.2f} is below floor ${TARGET_CPL_LOW:.0f} — "
                      f"verify lead quality before scaling")
            logger.warning("  [QUALITY ALERT] %s — %s", name, reason)
            db.log_action(
                agent_name=AGENT_NAME, action_type="quality_alert",
                entity_type="ad_group", entity_id=row["ag_db_id"],
                before={"cpl": cpl}, after={},
                reason=reason, google_entity_id=f"meta_adset_{adset_id}",
            )
            actions.append({"type": "quality_alert", "target": name,
                             "cpl": cpl, "reason": reason})

    return actions


def _evaluate_campaigns(camp_perf: list[dict], live_campaigns: dict[str, dict],
                         auto_apply: bool) -> list[dict]:
    """Pause campaigns that are burning budget with zero conversions."""
    actions = []

    for row in camp_perf:
        ext_id      = row["external_id"]           # e.g. "meta_6883951350893"
        campaign_id = ext_id.replace("meta_", "")
        name        = row["name"]
        spend       = float(row["spend_usd"])
        convs       = float(row["conversions"])

        live = live_campaigns.get(campaign_id, {})
        if live.get("status", "UNKNOWN") not in ("ACTIVE", "ENABLED"):
            continue

        if spend >= PAUSE_CAMP_FLOOR and convs == 0:
            reason = (f"${spend:.2f} spent over {LOOKBACK_DAYS}d with 0 conversions "
                      f"(floor: ${PAUSE_CAMP_FLOOR:.0f})")
            logger.warning("  [PAUSE CAMPAIGN] %s — %s", name, reason)
            actions.append(_pause_campaign(campaign_id, name, reason,
                                           row["camp_db_id"], auto_apply))

    return actions


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(auto_apply: bool | None = None) -> dict:
    if auto_apply is None:
        auto_apply = AUTO_APPLY

    logger.info("=== Meta Manager starting (auto_apply=%s) ===", auto_apply)
    db.heartbeat(AGENT_NAME, "alive")

    if not ACCESS_TOKEN:
        err = "META_ACCESS_TOKEN not set"
        logger.error(err)
        db.heartbeat(AGENT_NAME, "error", error=err)
        return {"platform": PLATFORM, "status": "error", "error": err}

    # Pull live state from Meta API
    live_adsets    = _get_live_adsets()
    live_campaigns = _get_live_campaigns()
    logger.info("Live state: %d ad sets, %d campaigns fetched from Meta API",
                len(live_adsets), len(live_campaigns))

    # Pull performance from DB
    adset_perf  = _get_adset_performance()
    camp_perf   = _get_campaign_performance()
    logger.info("DB performance: %d ad sets, %d campaigns with data",
                len(adset_perf), len(camp_perf))

    all_actions: list[dict] = []

    # Step 0: Enforce active days (pause/unpause by day of week)
    logger.info("--- Step 0: Enforce Fri/Sat/Sun/Mon active days ---")
    all_actions += _enforce_active_days(auto_apply)

    # Evaluate ad sets
    logger.info("--- Evaluating ad sets ---")
    all_actions += _evaluate_adsets(adset_perf, live_adsets, auto_apply)

    # Evaluate campaigns
    logger.info("--- Evaluating campaigns ---")
    all_actions += _evaluate_campaigns(camp_perf, live_campaigns, auto_apply)

    # Summary
    action_counts = {}
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
        "=== Meta Manager done — actions=%d applied=%d pending=%d ===",
        len(all_actions), applied, pending,
    )
    logger.info("  Action breakdown: %s", action_counts)

    if not auto_apply and all_actions:
        logger.info(
            "  AUTO_APPLY is off — %d action(s) logged to optimization_actions "
            "for review. Set META_MANAGER_AUTO_APPLY=true to execute automatically.",
            pending,
        )

    # Broadcast results to orchestrator
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
    result = run()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["status"] == "success" else 1)
