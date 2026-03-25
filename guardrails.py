"""
Guardrails Engine — Ridgecrest Designs
=======================================
Reads GUARDRAILS.md as the authoritative rules document and enforces those
rules programmatically before any pipeline action is taken.

Usage:
    import guardrails

    # At start of every pipeline run:
    violations = guardrails.check_pipeline_state(metrics)
    # Before any optimizer action:
    allowed, reason = guardrails.check_action(action_dict)
    # To send an escalation alert directly:
    guardrails.escalate(trigger_name, detail)
"""

import os
import json
import logging
from datetime import date, datetime, timezone
from typing import Any

from dotenv import load_dotenv

import db
from db import pacific_today

load_dotenv()

logger = logging.getLogger(__name__)

AGENT_NAME = "guardrails"

# ---------------------------------------------------------------------------
# Hard limits — derived from GUARDRAILS.md
# ---------------------------------------------------------------------------

GUARDRAILS_PATH = os.path.join(os.path.dirname(__file__), "GUARDRAILS.md")

from config import (
    WEEKLY_BUDGET_CEILING_USD, WEEKLY_BUDGET_FLOOR_USD, DAILY_BUDGET_SOFT_CAP_USD,
    DAILY_BUDGET_CAP_USD, MIN_CAMPAIGN_DAILY_BUDGET_USD,
    MAX_SINGLE_CAMPAIGN_INCREASE_PCT, MAX_BUDGET_REALLOCATION_PCT,
    MAX_KEYWORD_PAUSES_PER_DAY, MAX_KEYWORD_BID_INCREASE_PCT as MAX_BID_INCREASE_PCT, MAX_KEYWORD_BID_DECREASE_PCT as MAX_BID_DECREASE_PCT,
    MIN_ACTIVE_KEYWORDS,
    ESCALATION_CPL_USD, ESCALATION_DAILY_SPEND_USD, ESCALATION_WEEKLY_SPEND_USD,
    ESCALATION_KEYWORD_SPEND_USD, ESCALATION_API_FAILURE_HOURS,
    WEEKLY_UNDERSPEND_ALERT_USD, UNDERSPEND_ALERT_USD, HIGH_SPEND_DECISION_USD,
    ALERT_EMAIL, ALERT_FROM,
)


# ---------------------------------------------------------------------------
# Guardrails.md loader
# ---------------------------------------------------------------------------

def load_guardrails_doc() -> str:
    """Read GUARDRAILS.md and return its contents. Logged once per pipeline run."""
    try:
        with open(GUARDRAILS_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("GUARDRAILS.md not found at %s — halting pipeline.", GUARDRAILS_PATH)
        raise RuntimeError(f"GUARDRAILS.md missing: {GUARDRAILS_PATH}")


def assert_guardrails_present() -> bool:
    """
    Called at the start of every pipeline run.
    Verifies GUARDRAILS.md exists and logs a record of the check.
    Returns True if the file is present and readable.
    """
    content = load_guardrails_doc()
    word_count = len(content.split())
    logger.info(
        "[guardrails] GUARDRAILS.md loaded — %d words, %d bytes. Rules are active.",
        word_count, len(content)
    )
    return True


# ---------------------------------------------------------------------------
# Violation logger
# ---------------------------------------------------------------------------

def _log_violation(
    rule_category: str,
    rule_name: str,
    reason: str,
    action_type: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    entity_name: str | None = None,
    proposed_value: Any = None,
    limit_value: Any = None,
    escalated: bool = False,
    pipeline_run_id: str | None = None,
) -> int:
    """Write a guardrail violation to the database. Returns the row id."""
    try:
        with db.get_db() as (conn, cur):
            cur.execute(
                """INSERT INTO guardrail_violations
                   (rule_category, rule_name, action_type, entity_type, entity_id,
                    entity_name, proposed_value, limit_value, reason,
                    escalated, pipeline_run_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    rule_category, rule_name, action_type, entity_type, entity_id,
                    entity_name,
                    json.dumps(proposed_value) if proposed_value is not None else None,
                    json.dumps(limit_value)    if limit_value    is not None else None,
                    reason, escalated, pipeline_run_id,
                )
            )
            vid = cur.fetchone()["id"]
        logger.warning("[guardrails] VIOLATION #%d — [%s] %s: %s", vid, rule_category, rule_name, reason)
        return vid
    except Exception as e:
        logger.error("[guardrails] Failed to log violation to DB: %s", e)
        return -1


# ---------------------------------------------------------------------------
# Resend email alert
# ---------------------------------------------------------------------------

def _send_alert_email(trigger_name: str, detail: str, metrics: dict | None = None) -> bool:
    """
    Send an escalation alert to ALERT_EMAIL via Resend.
    Returns True on success, False on failure (non-blocking — violation is
    already logged to DB before this is called).
    """
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.error(
            "[guardrails] RESEND_API_KEY not set — cannot send alert email for: %s",
            trigger_name
        )
        return False

    try:
        import resend
        resend.api_key = api_key

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        metrics_block = ""
        if metrics:
            metrics_block = "\nMetrics:\n" + "\n".join(
                f"  {k}: {v}" for k, v in metrics.items()
            )

        body_text = f"""RIDGECREST DESIGNS — AUTOMATED MARKETING ALERT
{'=' * 55}

Trigger:    {trigger_name}
Time (UTC): {now_utc}
Account:    Ridgecrest Designs (act_658645131272143)

Detail:
{detail}
{metrics_block}

Action Taken:
All automated optimization has been paused pending your review.
No further bid changes, budget reallocations, or campaign actions
will occur until you re-enable automation.

To re-enable, update the agent_heartbeats table or restart
the orchestrator with the --force flag after reviewing the issue.

— Ridgecrest Designs Marketing Automation
"""

        response = resend.Emails.send({
            "from":    ALERT_FROM,
            "to":      [ALERT_EMAIL],
            "subject": f"[ALERT] Ridgecrest Designs — {trigger_name} — {pacific_today()}",
            "text":    body_text,
        })
        logger.info("[guardrails] Alert email sent to %s (id=%s)", ALERT_EMAIL, response.get("id"))
        return True

    except Exception as e:
        logger.error("[guardrails] Alert email failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Public escalation function
# ---------------------------------------------------------------------------

def escalate(
    trigger_name: str,
    detail: str,
    metrics: dict | None = None,
    pipeline_run_id: str | None = None,
) -> None:
    """
    Log an escalation violation and send an alert email.
    Called when any human escalation trigger fires.
    """
    vid = _log_violation(
        rule_category="escalation",
        rule_name=trigger_name,
        reason=detail,
        escalated=True,
        pipeline_run_id=pipeline_run_id,
    )
    sent = _send_alert_email(trigger_name, detail, metrics)

    # Mark escalation_sent in DB
    if vid > 0:
        try:
            with db.get_db() as (conn, cur):
                cur.execute(
                    "UPDATE guardrail_violations SET escalation_sent=%s WHERE id=%s",
                    (sent, vid)
                )
        except Exception as e:
            logger.error("[guardrails] Failed to update escalation_sent: %s", e)


# ---------------------------------------------------------------------------
# Pipeline-state checks (run at the top of every pipeline cycle)
# ---------------------------------------------------------------------------

def check_pipeline_state(pipeline_run_id: str | None = None) -> list[dict]:
    """
    Query current DB metrics and check all escalation triggers and spend rules.
    Returns a list of violation dicts. An empty list means all clear.

    Escalation triggers cause all automation to be flagged — the caller
    (orchestrator) is responsible for halting the pipeline if any escalation
    is returned.
    """
    violations: list[dict] = []
    today = pacific_today()

    try:
        with db.get_db() as (conn, cur):

            # ── Today's total spend (claude_code campaigns only) ────────────
            cur.execute(
                """SELECT COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS total_spend
                   FROM performance_metrics pm
                   JOIN campaigns c ON c.id = pm.entity_id
                   WHERE pm.metric_date = %s
                     AND pm.entity_type = 'campaign'
                     AND c.managed_by = 'claude_code'""",
                (today,)
            )
            today_spend = float(cur.fetchone()["total_spend"] or 0)

            # ── Current calendar week spend (Mon–Sun) ───────────────────────
            week_start = today - __import__('datetime').timedelta(days=today.weekday())
            cur.execute(
                """SELECT COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS weekly_spend
                   FROM performance_metrics pm
                   JOIN campaigns c ON c.id = pm.entity_id
                   WHERE pm.metric_date >= %s
                     AND pm.entity_type = 'campaign'
                     AND c.managed_by = 'claude_code'""",
                (week_start,)
            )
            weekly_spend = float(cur.fetchone()["weekly_spend"] or 0)

            # ── 7-day CPL (claude_code campaigns only) ──────────────────────
            cur.execute(
                """SELECT
                       COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS spend_7d,
                       COALESCE(SUM(pm.conversions), 0)           AS conv_7d
                   FROM performance_metrics pm
                   JOIN campaigns c ON c.id = pm.entity_id
                   WHERE pm.metric_date >= %s
                     AND pm.entity_type = 'campaign'
                     AND c.managed_by = 'claude_code'""",
                (today - __import__('datetime').timedelta(days=6),)
            )
            row = cur.fetchone()
            spend_7d = float(row["spend_7d"] or 0)
            conv_7d  = float(row["conv_7d"]  or 0)
            cpl_7d   = (spend_7d / conv_7d) if conv_7d > 0 else 0

            # ── Keyword-level spend with 0 conversions (claude_code only) ───
            cur.execute(
                """SELECT k.id, k.keyword_text,
                       COALESCE(SUM(pm.cost_micros)/1000000.0, 0) AS spend_7d,
                       COALESCE(SUM(pm.conversions), 0)           AS conv_7d
                   FROM performance_metrics pm
                   JOIN keywords k ON k.id = pm.entity_id
                   JOIN ad_groups ag ON ag.id = k.ad_group_id
                   JOIN campaigns c ON c.id = ag.campaign_id
                   WHERE pm.entity_type = 'keyword'
                     AND pm.metric_date >= %s
                     AND c.managed_by = 'claude_code'
                   GROUP BY k.id, k.keyword_text
                   HAVING COALESCE(SUM(pm.conversions), 0) = 0
                      AND COALESCE(SUM(pm.cost_micros)/1000000.0, 0) >= %s""",
                (today - __import__('datetime').timedelta(days=6),
                 ESCALATION_KEYWORD_SPEND_USD)
            )
            zero_conv_keywords = cur.fetchall()

            # ── API failure check — sync agents only ────────────────────────
            # Only monitor platform sync agents for API connectivity.
            # Optimization agents (bid_budget_optimizer, performance_analyst)
            # run on the daily pipeline schedule and will naturally have long
            # gaps — they should not trigger API failure escalations.
            cur.execute(
                """SELECT agent_name, last_success_at
                   FROM agent_heartbeats
                   WHERE agent_name IN ('google_sync', 'meta_sync', 'microsoft_sync')""",
            )
            heartbeats = {r["agent_name"]: r for r in cur.fetchall()}

    except Exception as e:
        logger.error("[guardrails] DB query failed during pipeline state check: %s", e)
        return violations

    # ── Escalation: weekly spend > $1,100 (ceiling + 10% buffer) ──────────
    if weekly_spend > ESCALATION_WEEKLY_SPEND_USD:
        msg = (f"Weekly spend ${weekly_spend:.2f} exceeds escalation threshold "
               f"${ESCALATION_WEEKLY_SPEND_USD:.2f} (ceiling ${WEEKLY_BUDGET_CEILING_USD:.2f})")
        escalate("Weekly Spend Exceeded $1,100",
                 msg, {"weekly_spend": f"${weekly_spend:.2f}",
                       "ceiling": f"${WEEKLY_BUDGET_CEILING_USD:.2f}"}, pipeline_run_id)
        violations.append({"category": "escalation", "rule": "weekly_spend_exceeded", "message": msg})

    # ── Hard block: weekly spend >= $1,000 ceiling ─────────────────────────
    elif weekly_spend >= WEEKLY_BUDGET_CEILING_USD:
        msg = (f"Weekly budget ceiling of ${WEEKLY_BUDGET_CEILING_USD:.2f} reached "
               f"(spent ${weekly_spend:.2f} this week) — blocking all spend increases")
        _log_violation("spend_limits", "weekly_budget_ceiling_reached", msg,
                       proposed_value={"weekly_spend": weekly_spend},
                       limit_value={"ceiling": WEEKLY_BUDGET_CEILING_USD},
                       pipeline_run_id=pipeline_run_id)
        violations.append({"category": "spend_limits", "rule": "weekly_ceiling_reached", "message": msg})

    # ── Escalation: daily spend > $300 (soft cap + 20% buffer) ─────────────
    if today_spend > ESCALATION_DAILY_SPEND_USD:
        msg = (f"Daily spend ${today_spend:.2f} exceeds escalation threshold "
               f"${ESCALATION_DAILY_SPEND_USD:.2f}")
        escalate("Daily Spend Exceeded $300",
                 msg, {"today_spend": f"${today_spend:.2f}"}, pipeline_run_id)
        violations.append({"category": "escalation", "rule": "daily_spend_exceeded", "message": msg})

    # ── Alert: weekly underspend pace < $400 ───────────────────────────────
    elif weekly_spend < WEEKLY_UNDERSPEND_ALERT_USD and weekly_spend > 0:
        msg = (f"Weekly underspend alert: ${weekly_spend:.2f} spent this week "
               f"(pacing below ${WEEKLY_UNDERSPEND_ALERT_USD:.2f} floor — "
               f"target ${WEEKLY_BUDGET_FLOOR_USD:.2f}–${WEEKLY_BUDGET_CEILING_USD:.2f})")
        _log_violation("reporting", "weekly_underspend_alert", msg,
                       proposed_value={"weekly_spend": weekly_spend},
                       limit_value={"floor": WEEKLY_UNDERSPEND_ALERT_USD},
                       pipeline_run_id=pipeline_run_id)
        violations.append({"category": "reporting", "rule": "weekly_underspend_alert", "message": msg})

    # ── Escalation: CPL > $1,000 ────────────────────────────────────────────
    if cpl_7d > ESCALATION_CPL_USD:
        msg = (f"7-day CPL ${cpl_7d:.2f} exceeds escalation threshold "
               f"${ESCALATION_CPL_USD:.2f} "
               f"(${spend_7d:.2f} spend, {conv_7d:.0f} conversions)")
        escalate("CPL Exceeded $1,000",
                 msg,
                 {"cpl_7d": f"${cpl_7d:.2f}", "spend_7d": f"${spend_7d:.2f}",
                  "conv_7d": int(conv_7d)},
                 pipeline_run_id)
        violations.append({"category": "escalation", "rule": "cpl_exceeded", "message": msg})

    # ── Escalation: keyword ≥ $75 with 0 conversions ───────────────────────
    for kw in zero_conv_keywords:
        kw_spend = float(kw["spend_7d"])
        msg = (f"Keyword '{kw['keyword_text']}' (id={kw['id']}) has spent "
               f"${kw_spend:.2f} over 7 days with 0 conversions — "
               f"exceeds ${ESCALATION_KEYWORD_SPEND_USD:.2f} escalation threshold")
        escalate("Keyword Spend ≥$75 with Zero Conversions",
                 msg,
                 {"keyword": kw["keyword_text"], "spend_7d": f"${kw_spend:.2f}",
                  "conversions": 0},
                 pipeline_run_id)
        violations.append({"category": "escalation", "rule": "keyword_zero_conv_spend",
                            "message": msg, "keyword_id": kw["id"]})

    # ── Escalation: API agent not responding for > 2 hours ─────────────────
    now_utc = datetime.now(timezone.utc)
    for agent_name, hb in heartbeats.items():
        last_ok = hb.get("last_success_at")
        if last_ok is None:
            continue
        if last_ok.tzinfo is None:
            last_ok = last_ok.replace(tzinfo=timezone.utc)
        hours_silent = (now_utc - last_ok).total_seconds() / 3600
        if hours_silent > ESCALATION_API_FAILURE_HOURS:
            msg = (f"Agent '{agent_name}' last succeeded "
                   f"{hours_silent:.1f} hours ago — exceeds "
                   f"{ESCALATION_API_FAILURE_HOURS}h API failure threshold")
            escalate("API Connection Failure > 2 Hours",
                     msg,
                     {"agent": agent_name,
                      "last_success": str(last_ok),
                      "hours_silent": round(hours_silent, 1)},
                     pipeline_run_id)
            violations.append({"category": "escalation", "rule": "api_failure",
                                "message": msg, "agent": agent_name})

    if not violations:
        logger.info("[guardrails] Pipeline state check passed — no violations.")
    else:
        esc = [v for v in violations if v["category"] == "escalation"]
        non_esc = [v for v in violations if v["category"] != "escalation"]
        logger.warning("[guardrails] %d violation(s): %d escalation(s), %d warning(s)",
                       len(violations), len(esc), len(non_esc))

    return violations


# ---------------------------------------------------------------------------
# Per-action checks
# ---------------------------------------------------------------------------

def check_action(
    action: dict,
    pipeline_run_id: str | None = None,
) -> tuple[bool, str]:
    """
    Validate a proposed optimizer action against the guardrails.

    action dict keys:
        action_type   — "bid_increase" | "bid_decrease" | "pause_keyword" |
                        "budget_increase" | "budget_decrease" | "budget_reallocation" |
                        "pause_campaign" | "new_campaign" | "change_objective" |
                        "change_match_type" | "publish_creative"
        entity_type   — "keyword" | "campaign" | "ad"
        entity_id     — DB int id (optional)
        entity_name   — human-readable name (optional)
        before_value  — dict with current state
        after_value   — dict with proposed state
        reason        — why this action is being proposed
        campaign_id   — owning campaign (for keyword actions)
        extra         — dict with additional context:
            active_keywords_in_campaign  — int, current active keyword count
            keyword_pauses_today         — int, pauses already applied today
            todays_spend_usd             — float
            reallocation_usd             — float (for budget moves)
            creative_in_db               — bool

    Returns (allowed: bool, reason: str).
    If not allowed, the violation is logged to the database.
    """
    atype  = action.get("action_type", "")
    etype  = action.get("entity_type", "")
    eid    = action.get("entity_id")
    ename  = action.get("entity_name", "")
    before = action.get("before_value", {})
    after  = action.get("after_value", {})
    extra  = action.get("extra", {})

    # ── Skip guardrails entirely for manually managed campaigns ────────────
    # Only campaigns created by the Claude Code Ridgecrest Marketing agency
    # are subject to guardrails. Human-managed campaigns are never touched.
    campaign_id = extra.get("campaign_id") or (eid if etype == "campaign" else None)
    if campaign_id:
        try:
            with db.get_db() as (conn, cur):
                cur.execute(
                    "SELECT managed_by FROM campaigns WHERE id = %s",
                    (campaign_id,)
                )
                row = cur.fetchone()
                if row and row["managed_by"] != "claude_code":
                    logger.info(
                        "[guardrails] Skipping guardrails for manually managed campaign id=%s '%s'",
                        campaign_id, ename
                    )
                    return True, "ok — manually managed campaign, guardrails not applied"
        except Exception as e:
            logger.warning("[guardrails] Could not check managed_by for campaign %s: %s", campaign_id, e)

    def _block(rule_category: str, rule_name: str, reason: str,
               proposed=None, limit=None) -> tuple[bool, str]:
        _log_violation(rule_category, rule_name, reason,
                       action_type=atype, entity_type=etype,
                       entity_id=eid, entity_name=ename,
                       proposed_value=proposed, limit_value=limit,
                       pipeline_run_id=pipeline_run_id)
        return False, reason

    # ── Spend cap: block spend increases if weekly ceiling already met ──────
    weekly_spend = extra.get("weekly_spend_usd", 0)
    if weekly_spend >= WEEKLY_BUDGET_CEILING_USD and atype in (
        "budget_increase", "budget_reallocation", "bid_increase"
    ):
        return _block("spend_limits", "weekly_ceiling_reached",
                      f"Weekly ceiling ${WEEKLY_BUDGET_CEILING_USD:.2f} already reached "
                      f"(${weekly_spend:.2f} spent this week) — blocking {atype}",
                      proposed={"weekly_spend": weekly_spend},
                      limit={"ceiling": WEEKLY_BUDGET_CEILING_USD})

    # ── Soft block: daily spend > $250 soft cap ─────────────────────────────
    todays_spend = extra.get("todays_spend_usd", 0)
    if todays_spend >= DAILY_BUDGET_SOFT_CAP_USD and atype == "budget_increase":
        return _block("spend_limits", "daily_soft_cap_reached",
                      f"Daily soft cap ${DAILY_BUDGET_SOFT_CAP_USD:.2f} reached "
                      f"(${todays_spend:.2f} spent today) — blocking budget_increase",
                      proposed={"todays_spend": todays_spend},
                      limit={"soft_cap": DAILY_BUDGET_SOFT_CAP_USD})

    # ── Bid increase: max +25% ──────────────────────────────────────────────
    if atype == "bid_increase":
        old_bid = before.get("cpc_bid_micros", before.get("cpc_bid_usd", 0))
        new_bid = after.get("cpc_bid_micros",  after.get("cpc_bid_usd",  0))
        if old_bid and new_bid and old_bid > 0:
            pct_change = (new_bid - old_bid) / old_bid
            if pct_change > MAX_BID_INCREASE_PCT:
                allowed_bid = old_bid * (1 + MAX_BID_INCREASE_PCT)
                return _block("keyword_rules", "bid_increase_exceeds_25pct",
                              f"Proposed bid increase {pct_change*100:.1f}% > {MAX_BID_INCREASE_PCT*100:.0f}% "
                              f"max for '{ename}' (before={old_bid}, after={new_bid}, "
                              f"allowed_max={allowed_bid:.0f})",
                              proposed={"pct_change": pct_change, "new_bid": new_bid},
                              limit={"max_pct": MAX_BID_INCREASE_PCT, "allowed_bid": allowed_bid})

        # Flag if the resulting spend decision > $50
        decision_spend = extra.get("decision_spend_usd", 0)
        if decision_spend > HIGH_SPEND_DECISION_USD:
            _log_violation("reporting", "high_spend_decision_flagged",
                           f"Bid increase for '{ename}' involves >${HIGH_SPEND_DECISION_USD:.0f} "
                           f"decision (${decision_spend:.2f})",
                           action_type=atype, entity_type=etype, entity_id=eid,
                           entity_name=ename,
                           proposed_value={"decision_spend": decision_spend},
                           limit_value={"flag_threshold": HIGH_SPEND_DECISION_USD},
                           pipeline_run_id=pipeline_run_id)

    # ── Bid decrease: max -30% ──────────────────────────────────────────────
    elif atype == "bid_decrease":
        old_bid = before.get("cpc_bid_micros", before.get("cpc_bid_usd", 0))
        new_bid = after.get("cpc_bid_micros",  after.get("cpc_bid_usd",  0))
        if old_bid and new_bid and old_bid > 0:
            pct_change = (old_bid - new_bid) / old_bid   # positive = decrease
            if pct_change > MAX_BID_DECREASE_PCT:
                allowed_bid = old_bid * (1 - MAX_BID_DECREASE_PCT)
                return _block("keyword_rules", "bid_decrease_exceeds_30pct",
                              f"Proposed bid decrease {pct_change*100:.1f}% > {MAX_BID_DECREASE_PCT*100:.0f}% "
                              f"max for '{ename}' (before={old_bid}, after={new_bid}, "
                              f"allowed_min={allowed_bid:.0f})",
                              proposed={"pct_decrease": pct_change, "new_bid": new_bid},
                              limit={"max_pct": MAX_BID_DECREASE_PCT, "allowed_bid": allowed_bid})

    # ── Pause keyword: max 3/day, min 5 active keywords ────────────────────
    elif atype == "pause_keyword":
        pauses_today = extra.get("keyword_pauses_today", 0)
        if pauses_today >= MAX_KEYWORD_PAUSES_PER_DAY:
            return _block("keyword_rules", "max_keyword_pauses_reached",
                          f"Campaign already has {pauses_today} keyword pause(s) today "
                          f"(max {MAX_KEYWORD_PAUSES_PER_DAY}) — '{ename}' pause blocked",
                          proposed={"pauses_today": pauses_today},
                          limit={"max_pauses": MAX_KEYWORD_PAUSES_PER_DAY})

        active_kw = extra.get("active_keywords_in_campaign", MIN_ACTIVE_KEYWORDS + 1)
        if active_kw <= MIN_ACTIVE_KEYWORDS:
            return _block("keyword_rules", "min_active_keywords_violated",
                          f"Pausing '{ename}' would leave campaign with {active_kw - 1} "
                          f"active keywords — minimum is {MIN_ACTIVE_KEYWORDS}",
                          proposed={"active_after": active_kw - 1},
                          limit={"min_active": MIN_ACTIVE_KEYWORDS})

    # ── Budget increase: max +20% per day ──────────────────────────────────
    elif atype == "budget_increase":
        old_budget = before.get("daily_budget_usd", 0)
        new_budget = after.get("daily_budget_usd", 0)
        if old_budget and new_budget and old_budget > 0:
            pct_change = (new_budget - old_budget) / old_budget
            if pct_change > MAX_SINGLE_CAMPAIGN_INCREASE_PCT:
                allowed_budget = old_budget * (1 + MAX_SINGLE_CAMPAIGN_INCREASE_PCT)
                return _block("spend_limits", "budget_increase_exceeds_20pct",
                              f"Proposed budget increase {pct_change*100:.1f}% > "
                              f"{MAX_SINGLE_CAMPAIGN_INCREASE_PCT*100:.0f}% max "
                              f"for campaign '{ename}' (${old_budget:.2f} → ${new_budget:.2f}, "
                              f"allowed max ${allowed_budget:.2f})",
                              proposed={"pct_change": pct_change, "new_budget": new_budget},
                              limit={"max_pct": MAX_SINGLE_CAMPAIGN_INCREASE_PCT,
                                     "allowed_budget": allowed_budget})

    # ── Budget reallocation: max 30% of under-performer's budget per cycle ──
    elif atype == "budget_reallocation":
        realloc_usd = extra.get("reallocation_usd", 0)
        from_budget  = extra.get("from_budget_usd", 0)
        max_realloc  = from_budget * MAX_BUDGET_REALLOCATION_PCT if from_budget else 0
        if max_realloc > 0 and realloc_usd > max_realloc:
            return _block("spend_limits", "reallocation_exceeds_30pct",
                          f"Proposed reallocation ${realloc_usd:.2f} exceeds "
                          f"30% of source budget (${max_realloc:.2f}) for this cycle",
                          proposed={"reallocation_usd": realloc_usd},
                          limit={"max_reallocation_usd": max_realloc})

    # ── Pause campaign: requires 3-day trend — escalate for human review ────
    elif atype == "pause_campaign":
        underperformance_days = extra.get("underperformance_days", 0)
        if underperformance_days < 3:
            return _block("campaign_rules", "insufficient_underperformance_trend",
                          f"Cannot pause campaign '{ename}' — only {underperformance_days} "
                          f"day(s) of underperformance (need 3). Human review required.",
                          proposed={"underperformance_days": underperformance_days},
                          limit={"required_days": 3})

    # ── Hard blocks: actions that always require human approval ────────────
    elif atype in ("new_campaign", "change_objective", "change_match_type"):
        label = {
            "new_campaign":       "New campaign creation",
            "change_objective":   "Campaign objective change",
            "change_match_type":  "Keyword match type change",
        }[atype]
        return _block("campaign_rules", f"{atype}_requires_human",
                      f"{label} for '{ename}' is blocked — requires explicit human approval",
                      proposed=after, limit={"requires": "human_approval"})

    # ── Creative: must be in DB before publish ─────────────────────────────
    elif atype == "publish_creative":
        if not extra.get("creative_in_db", False):
            return _block("creative_rules", "creative_not_stored_before_publish",
                          f"Cannot publish creative for '{ename}' — "
                          f"not yet stored in the database. Store first.",
                          proposed=after, limit={"requires": "db_storage_first"})

    return True, "ok"


# ---------------------------------------------------------------------------
# Convenience: check a batch of proposed actions, return only allowed ones
# ---------------------------------------------------------------------------

def filter_actions(
    actions: list[dict],
    pipeline_run_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Given a list of proposed actions, return (allowed, blocked).
    Violations for blocked actions are logged automatically.
    """
    allowed = []
    blocked = []
    for action in actions:
        ok, reason = check_action(action, pipeline_run_id)
        if ok:
            allowed.append(action)
        else:
            action["_blocked_reason"] = reason
            blocked.append(action)
    if blocked:
        logger.warning("[guardrails] %d/%d action(s) blocked by guardrails",
                       len(blocked), len(actions))
    return allowed, blocked


# ---------------------------------------------------------------------------
# Helper: are there any active escalations right now?
# ---------------------------------------------------------------------------

def has_active_escalations(pipeline_run_id: str | None = None) -> bool:
    """
    Returns True if the pipeline state check found escalation-level violations.
    The orchestrator should halt optimization phases when this is True.
    """
    violations = check_pipeline_state(pipeline_run_id)
    return any(v["category"] == "escalation" for v in violations)
