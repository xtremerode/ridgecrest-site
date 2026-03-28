"""
Orchestrator Agent
==================
The central controller for the Ridgecrest Designs marketing automation system.
Coordinates all sub-agents, manages the run schedule, handles critical alerts,
and ensures the system operates within defined constraints.

Architecture:
  orchestrator → spawns / sequences:
      1. performance_analyst   — pull metrics, detect anomalies
      2. bid_budget_optimizer  — apply bid/budget changes
      3. creative_agent        — refresh ad copy as needed
      4. reporting_agent       — generate daily/weekly reports

Scheduling (respects CLAUDE.md rules):
  - Active ad days: Friday, Saturday, Sunday, Monday
  - Daily run at configurable time (default: 08:00 local)
  - Weekly report: Monday mornings

Run standalone:  python orchestrator.py
Run as daemon:   python orchestrator.py --daemon
"""
import os
import json
import logging
import sys
import time
import argparse
import importlib
from datetime import date, datetime, timedelta

import schedule
from dotenv import load_dotenv

load_dotenv()

import db
import guardrails
import google_sync
import meta_sync
import microsoft_sync
import meta_manager
import microsoft_manager
import google_ads_scheduler
import performance_analyst
import bid_budget_optimizer
import creative_agent
import reporting_agent
import supabase_sync
import command_executor
import recommendation_agent
import health_agent
import chat_agent
import compliance_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [orchestrator] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator.log"),
            mode="a",
        ),
    ]
)
logger = logging.getLogger(__name__)

from config import ACTIVE_DAYS

AGENT_NAME = "orchestrator"

# ---------------------------------------------------------------------------
# Manual-mode flag
# Set CAMPAIGN_AUTOMATION_ENABLED=false in .env to disable all campaign writes
# while keeping data sync, reporting, and chat fully operational.
# ---------------------------------------------------------------------------
CAMPAIGN_AUTOMATION_ENABLED = os.getenv(
    "CAMPAIGN_AUTOMATION_ENABLED", "true"
).strip().lower() not in ("false", "0", "off", "no")


# ---------------------------------------------------------------------------
# Critical alert handler
# ---------------------------------------------------------------------------

def handle_critical_alerts(alerts: list[dict]):
    """
    React to critical alerts from performance_analyst.
    Currently: log and record. Future: send email/Slack notification.
    """
    for alert in alerts:
        severity = alert.get("severity", "unknown").upper()
        alert_type = alert.get("type", "unknown")
        message = alert.get("message", "")
        logger.warning("[CRITICAL ALERT] %s | %s: %s", severity, alert_type, message)

    # Store as a DB report for visibility
    if alerts:
        with db.get_db() as (conn, cur):
            cur.execute(
                """INSERT INTO reports (report_type, period_start, period_end,
                                        title, summary, metrics_snapshot, created_by)
                   VALUES ('alert', CURRENT_DATE, CURRENT_DATE,
                           'CRITICAL ALERTS — Immediate Action Required',
                           %s, %s, %s)""",
                (
                    f"{len(alerts)} critical alert(s) detected",
                    json.dumps({"alerts": alerts}),
                    AGENT_NAME
                )
            )


# ---------------------------------------------------------------------------
# Process orchestrator's own message queue
# ---------------------------------------------------------------------------

def process_messages():
    messages = db.receive_messages(AGENT_NAME)
    for msg in messages:
        try:
            mtype = msg["message_type"]
            payload = msg["payload"] if isinstance(msg["payload"], dict) else json.loads(msg["payload"])

            if mtype == "critical_alert":
                handle_critical_alerts(payload.get("alerts", []))
            elif mtype == "optimization_complete":
                logger.info(
                    "Optimization complete — bid_actions=%d, budget_actions=%d",
                    payload.get("bid_actions", 0),
                    payload.get("budget_actions", 0)
                )
            elif mtype == "report_complete":
                logger.info("Report ready: id=%s type=%s",
                            payload.get("report_id"), payload.get("report_type"))
            elif mtype == "creative_work_complete":
                logger.info("Creative work done: %s", payload)

            db.ack_message(msg["id"])
        except Exception as e:
            db.ack_message(msg["id"], error=str(e))
            logger.error("Error handling message %d: %s", msg["id"], e)


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------

def print_system_status():
    """Print current status of all agents and key metrics."""
    with db.get_db() as (conn, cur):
        cur.execute("SELECT * FROM agent_heartbeats ORDER BY agent_name")
        heartbeats = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT COALESCE(SUM(cost_micros)/1000000.0,0) AS spend_today
               FROM performance_metrics
               WHERE metric_date = CURRENT_DATE AND entity_type = 'campaign'"""
        )
        today_spend = float(cur.fetchone()["spend_today"] or 0)

        cur.execute(
            """SELECT COUNT(*) AS pending FROM agent_messages WHERE status='pending'"""
        )
        pending_msgs = cur.fetchone()["pending"]

        cur.execute(
            """SELECT COUNT(*) AS cnt FROM optimization_actions
               WHERE DATE(created_at) = CURRENT_DATE"""
        )
        todays_actions = cur.fetchone()["cnt"]

        cur.execute(
            """SELECT COUNT(*) AS cnt FROM creative_briefs WHERE status='draft'"""
        )
        draft_briefs = cur.fetchone()["cnt"]

    today = date.today()
    day_name = today.strftime("%A").lower()
    is_active = day_name in ACTIVE_DAYS

    logger.info("=" * 60)
    logger.info("RIDGECREST DESIGNS — MARKETING AUTOMATION STATUS")
    logger.info("=" * 60)
    logger.info("Date: %s (%s) | Active Ad Day: %s",
                today, today.strftime("%A"), "YES" if is_active else "NO")
    logger.info("Today's Spend: $%.2f / $125.00 | Pending Messages: %d",
                today_spend, pending_msgs)
    logger.info("Today's Optimization Actions: %d | Draft Creative Briefs: %d",
                todays_actions, draft_briefs)
    logger.info("-" * 60)

    for hb in heartbeats:
        last_run = hb.get("last_run_at")
        last_run_str = last_run.strftime("%H:%M:%S") if last_run else "never"
        logger.info(
            "  %-30s status=%-8s runs=%-4d errors=%-3d last=%s",
            hb["agent_name"],
            hb["status"],
            hb.get("run_count", 0),
            hb.get("error_count", 0),
            last_run_str
        )
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Main pipeline run
# ---------------------------------------------------------------------------

def run_pipeline(force: bool = False) -> dict:
    """
    Execute the full agent pipeline in sequence.

    force=True bypasses the day-of-week check (useful for testing).
    """
    today = date.today()
    day_name = today.strftime("%A").lower()
    is_active = day_name in ACTIVE_DAYS

    # Generate a unique run ID for traceability across all guardrail logs
    pipeline_run_id = f"{today.isoformat()}-{int(time.time())}"

    logger.info("=== Orchestrator pipeline starting (day=%s, active=%s, force=%s, run_id=%s) ===",
                day_name, is_active, force, pipeline_run_id)

    db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "starting", "run_id": pipeline_run_id})

    # ---- Guardrails: verify rules file is present before anything else ----
    try:
        guardrails.assert_guardrails_present()
    except RuntimeError as e:
        logger.critical("GUARDRAILS.md missing — aborting pipeline immediately. %s", e)
        return {
            "date": str(today), "day": day_name, "is_active_day": is_active,
            "forced": force, "pipeline_run_id": pipeline_run_id,
            "phases": {"guardrails": {"status": "error", "error": str(e)}},
            "aborted": True, "abort_reason": "guardrails_file_missing",
        }

    # ---- Guardrails: check current pipeline state for escalation triggers ----
    logger.info("--- Guardrails: Pipeline State Check ---")
    try:
        grl_violations = guardrails.check_pipeline_state(pipeline_run_id)
    except Exception as e:
        logger.error("Guardrails state check failed: %s", e, exc_info=True)
        grl_violations = []

    escalation_violations = [v for v in grl_violations if v["category"] == "escalation"]
    optimization_halted = len(escalation_violations) > 0

    if optimization_halted:
        logger.critical(
            "[guardrails] %d escalation trigger(s) fired — Phases 2 and 3 (optimization & "
            "creative) are HALTED. Alerts sent to %s. Run ID: %s",
            len(escalation_violations), guardrails.ALERT_EMAIL, pipeline_run_id
        )
        for ev in escalation_violations:
            logger.critical("[guardrails] ESCALATION: [%s] %s", ev["rule"], ev["message"])

    # Process any queued messages
    process_messages()

    results = {
        "date": str(today),
        "day": day_name,
        "is_active_day": is_active,
        "forced": force,
        "pipeline_run_id": pipeline_run_id,
        "guardrails": {
            "violations": len(grl_violations),
            "escalations": len(escalation_violations),
            "optimization_halted": optimization_halted,
        },
        "phases": {}
    }

    # ---- Phase 0: Platform Data Sync (pull latest from all ad platforms) ----
    logger.info("--- Phase 0: Platform Data Sync ---")
    db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "platform_sync",
                                                 "run_id": pipeline_run_id})
    platform_sync_results = {}
    for sync_module, label in [
        (google_sync,    "google_ads"),
        (meta_sync,      "meta"),
        (microsoft_sync, "microsoft_ads"),
    ]:
        try:
            result = sync_module.run()
            platform_sync_results[label] = {
                "status":           result.get("status"),
                "campaigns_synced": result.get("campaigns_synced", 0),
                "rows_written":     result.get("rows_written", 0),
            }
        except Exception as e:
            logger.error("Platform sync failed for %s: %s", label, e, exc_info=True)
            platform_sync_results[label] = {"status": "error", "error": str(e)}
    results["phases"]["platform_sync"] = platform_sync_results

    # ---- Phase 1: Performance Analysis (always run, even on inactive days) ----
    logger.info("--- Phase 1: Performance Analysis ---")
    db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "performance_analysis",
                                                 "run_id": pipeline_run_id})
    try:
        pa_result = performance_analyst.run()
        results["phases"]["performance_analysis"] = {
            "status": "success",
            "alerts": pa_result.get("alert_count", 0),
            "spend": pa_result.get("today_spend", 0),
        }
        # Handle any critical alerts immediately
        if pa_result.get("critical_alerts"):
            handle_critical_alerts(pa_result["critical_alerts"])
    except Exception as e:
        logger.error("Performance analysis failed: %s", e, exc_info=True)
        results["phases"]["performance_analysis"] = {"status": "error", "error": str(e)}
        db.heartbeat(AGENT_NAME, "error", error=str(e))

    # ---- Phase 1b: Platform Managers (Meta + Microsoft write-back) ----
    if not CAMPAIGN_AUTOMATION_ENABLED:
        logger.info("--- Phase 1b: Platform Managers SKIPPED (manual mode) ---")
        results["phases"]["platform_managers"] = {
            "status": "skipped", "reason": "CAMPAIGN_AUTOMATION_ENABLED=false"
        }
    else:
        logger.info("--- Phase 1b: Platform Managers ---")
        db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "platform_managers",
                                                     "run_id": pipeline_run_id})
        platform_manager_results = {}
        for manager_module, label in [
            (meta_manager,      "meta"),
            (microsoft_manager, "microsoft_ads"),
        ]:
            try:
                result = manager_module.run()
                platform_manager_results[label] = {
                    "status":          result.get("status"),
                    "actions_total":   result.get("actions_total", 0),
                    "actions_applied": result.get("actions_applied", 0),
                    "actions_pending": result.get("actions_pending", 0),
                }
            except Exception as e:
                logger.error("Platform manager failed for %s: %s", label, e, exc_info=True)
                platform_manager_results[label] = {"status": "error", "error": str(e)}

        # Google Ads day scheduler — staged until developer token approved
        try:
            sched_result = google_ads_scheduler.apply_schedule(auto_apply=False)
            platform_manager_results["google_ads_scheduler"] = sched_result
        except Exception as e:
            logger.warning("Google Ads scheduler skipped (token pending): %s", e)
            platform_manager_results["google_ads_scheduler"] = {
                "status": "skipped", "reason": str(e)
            }

        results["phases"]["platform_managers"] = platform_manager_results

    # ---- Phase 1c: Compliance Check (verify all CLAUDE.md parameters are met) ----
    if not CAMPAIGN_AUTOMATION_ENABLED:
        logger.info("--- Phase 1c: Compliance Check SKIPPED (manual mode) ---")
        results["phases"]["compliance_check"] = {
            "status": "skipped", "reason": "CAMPAIGN_AUTOMATION_ENABLED=false"
        }
    else:
        logger.info("--- Phase 1c: Compliance Check ---")
        db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "compliance_check",
                                                     "run_id": pipeline_run_id})
        try:
            comp_result = compliance_agent.run()
            results["phases"]["compliance_check"] = {
                "status":       comp_result.get("status"),
                "checks_total": comp_result.get("checks_total", 0),
                "checks_fail":  comp_result.get("checks_fail", 0),
                "auto_fixed":   comp_result.get("auto_fixed", 0),
            }
        except Exception as e:
            logger.error("Compliance check failed: %s", e, exc_info=True)
            results["phases"]["compliance_check"] = {"status": "error", "error": str(e)}

    # ---- Phase 2: Bid & Budget Optimization ----
    if not CAMPAIGN_AUTOMATION_ENABLED:
        logger.info("--- Phase 2: Bid & Budget Optimization SKIPPED (manual mode) ---")
        results["phases"]["bid_budget_optimization"] = {
            "status": "skipped", "reason": "CAMPAIGN_AUTOMATION_ENABLED=false"
        }
    elif optimization_halted:
        logger.warning(
            "--- Phase 2: SKIPPED — escalation violations active. "
            "Human review required before optimization resumes. ---"
        )
        results["phases"]["bid_budget_optimization"] = {
            "status": "halted",
            "reason": "guardrails_escalation",
            "escalation_count": len(escalation_violations),
        }
    else:
        logger.info("--- Phase 2: Bid & Budget Optimization ---")
        db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "bid_budget_optimization",
                                                     "run_id": pipeline_run_id})
        try:
            # Fetch proposed actions from the optimizer and filter through guardrails
            proposed_actions = bid_budget_optimizer.get_proposed_actions()
            allowed_actions, blocked_actions = guardrails.filter_actions(
                proposed_actions, pipeline_run_id
            )
            if blocked_actions:
                logger.warning(
                    "[guardrails] %d optimization action(s) blocked: %s",
                    len(blocked_actions),
                    [a.get("action_type") + "/" + a.get("entity_name", "?")
                     for a in blocked_actions]
                )
            bbo_result = bid_budget_optimizer.run(allowed_actions=allowed_actions)
            results["phases"]["bid_budget_optimization"] = {
                "status": "success",
                "bid_actions": bbo_result.get("bid_actions", 0),
                "budget_actions": bbo_result.get("budget_actions", 0),
                "schedule_changes": bbo_result.get("schedule_changes", 0),
                "blocked_by_guardrails": len(blocked_actions),
            }
        except TypeError:
            # bid_budget_optimizer.get_proposed_actions() not yet implemented —
            # fall back to running the optimizer directly without pre-filtering
            logger.warning(
                "bid_budget_optimizer does not expose get_proposed_actions() — "
                "running without per-action guardrail filtering"
            )
            try:
                bbo_result = bid_budget_optimizer.run()
                results["phases"]["bid_budget_optimization"] = {
                    "status": "success",
                    "bid_actions": bbo_result.get("bid_actions", 0),
                    "budget_actions": bbo_result.get("budget_actions", 0),
                    "schedule_changes": bbo_result.get("schedule_changes", 0),
                }
            except Exception as e:
                logger.error("Bid/budget optimization failed: %s", e, exc_info=True)
                results["phases"]["bid_budget_optimization"] = {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error("Bid/budget optimization failed: %s", e, exc_info=True)
            results["phases"]["bid_budget_optimization"] = {"status": "error", "error": str(e)}

    # ---- Phase 3: Creative Agent (refresh on active days only) ----
    if not CAMPAIGN_AUTOMATION_ENABLED:
        logger.info("--- Phase 3: Creative Refresh SKIPPED (manual mode) ---")
        results["phases"]["creative_refresh"] = {
            "status": "skipped", "reason": "CAMPAIGN_AUTOMATION_ENABLED=false"
        }
    elif optimization_halted:
        logger.warning(
            "--- Phase 3: SKIPPED — escalation violations active. "
            "Creative changes blocked until human review. ---"
        )
        results["phases"]["creative_refresh"] = {
            "status": "halted",
            "reason": "guardrails_escalation",
        }
    elif is_active or force:
        logger.info("--- Phase 3: Creative Refresh ---")
        db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "creative_refresh",
                                                     "run_id": pipeline_run_id})
        try:
            ca_result = creative_agent.run(generate_all=False)
            results["phases"]["creative_refresh"] = {
                "status": "success",
                "refreshed_ads": ca_result.get("refreshed_ads", 0),
            }
        except Exception as e:
            logger.error("Creative agent failed: %s", e, exc_info=True)
            results["phases"]["creative_refresh"] = {"status": "error", "error": str(e)}
    else:
        logger.info("Phase 3 skipped — not an active ad day")
        results["phases"]["creative_refresh"] = {"status": "skipped"}

    # ---- Phase 4: Reporting ----
    logger.info("--- Phase 4: Reporting ---")
    db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "reporting",
                                                 "run_id": pipeline_run_id})

    # Daily report
    try:
        rpt_result = reporting_agent.run(report_type="daily", use_claude=True)
        results["phases"]["daily_report"] = {
            "status": "success",
            "report_id": rpt_result.get("report_id"),
        }
    except Exception as e:
        logger.error("Daily report failed: %s", e, exc_info=True)
        results["phases"]["daily_report"] = {"status": "error", "error": str(e)}

    # Weekly report on Mondays
    if day_name == "monday":
        logger.info("--- Phase 4b: Weekly Report (Monday) ---")
        try:
            wrpt = reporting_agent.run(report_type="weekly", use_claude=True)
            results["phases"]["weekly_report"] = {
                "status": "success",
                "report_id": wrpt.get("report_id"),
            }
        except Exception as e:
            logger.error("Weekly report failed: %s", e, exc_info=True)
            results["phases"]["weekly_report"] = {"status": "error", "error": str(e)}

    # ---- Phase 4c: Recommendation Agent ----
    logger.info("--- Phase 4c: Recommendation Agent ---")
    db.heartbeat(AGENT_NAME, "alive", metadata={"phase": "recommendation_agent",
                                                 "run_id": pipeline_run_id})
    try:
        ra_result = recommendation_agent.run()
        results["phases"]["recommendation_agent"] = {
            "status": "success",
            "recommendations_generated": ra_result.get("recommendations_generated", 0),
            "emails_sent": ra_result.get("emails_sent", 0),
        }
    except Exception as e:
        logger.error("Recommendation agent failed: %s", e, exc_info=True)
        results["phases"]["recommendation_agent"] = {"status": "error", "error": str(e)}

    # ---- Final status ----
    errors = [p for p, v in results["phases"].items() if v.get("status") == "error"]
    halted = [p for p, v in results["phases"].items() if v.get("status") == "halted"]
    final_status = "error" if errors else ("halted" if halted else "success")

    db.heartbeat(AGENT_NAME, final_status, metadata={
        "last_pipeline_date": str(today),
        "run_id": pipeline_run_id,
        "phases": list(results["phases"].keys()),
        "errors": errors,
        "halted": halted,
        "guardrails_escalations": len(escalation_violations),
    })

    logger.info(
        "=== Pipeline complete — status=%s | phases=%d | errors=%s | halted=%s | "
        "guardrail_escalations=%d | run_id=%s ===",
        final_status, len(results["phases"]), errors or "none", halted or "none",
        len(escalation_violations), pipeline_run_id
    )

    print_system_status()

    # ---- Phase 5: Supabase Sync ----
    logger.info("--- Phase 5: Supabase Sync ---")
    try:
        sync_result = supabase_sync.sync(pipeline_run_id=pipeline_run_id)
        results["phases"]["supabase_sync"] = {
            "status": "success" if sync_result.get("success") else "error",
            "row_counts": sync_result.get("row_counts", {}),
        }
        if not sync_result.get("success"):
            results["phases"]["supabase_sync"]["error"] = sync_result.get("error", "unknown")
    except Exception as e:
        logger.error("Supabase sync failed: %s", e, exc_info=True)
        results["phases"]["supabase_sync"] = {"status": "error", "error": str(e)}

    return results


# ---------------------------------------------------------------------------
# Standalone Supabase sync (runs every 5 minutes independent of pipeline)
# ---------------------------------------------------------------------------

def _run_health_agent():
    """Run end-to-end health checks across the full agency stack."""
    try:
        result = health_agent.run()
        if result.get("checks_failing", 0):
            logger.warning(
                "Health check: %d/%d checks failing — %s",
                result["checks_failing"], result["checks_total"],
                [f["component"] for f in result.get("failures", [])],
            )
        else:
            logger.info("Health check: all %d checks passing", result["checks_total"])
    except Exception as e:
        logger.error("Health agent error: %s", e, exc_info=True)


def _run_command_executor():
    """Poll Supabase command_queue and execute any pending commands from Lovable."""
    try:
        n = command_executor.run()
        if n:
            logger.info("Command executor: processed %d command(s)", n)
    except Exception as e:
        logger.error("Command executor error: %s", e, exc_info=True)


def _run_chat_agent():
    """Poll Supabase chat_messages for pending user messages and respond via Claude."""
    try:
        n = chat_agent.run()
        if n:
            logger.info("Chat agent: processed %d message(s)", n)
    except Exception as e:
        logger.error("Chat agent error: %s", e, exc_info=True)


def _sync_supabase():
    """Push the current DB snapshot to the Lovable Command Center.

    Runs on a 5-minute schedule so the dashboard stays near-real-time without
    waiting for the daily pipeline. Safe to call at any time — read-only on
    the local DB, no platform API calls made.
    """
    try:
        result = supabase_sync.sync()
        if result.get("success"):
            logger.info("Supabase sync OK — rows: %s", result.get("row_counts", {}))
        else:
            logger.warning("Supabase sync returned error: %s", result.get("error"))
    except Exception as e:
        logger.error("Supabase sync failed: %s", e, exc_info=True)


# ---------------------------------------------------------------------------
# Daemon scheduler
# ---------------------------------------------------------------------------

def _run_platform_sync():
    """
    Lightweight sync-only run: pulls fresh data from Meta and Microsoft into the DB
    without running optimization, creative, or reporting phases.
    Runs every 6 hours so the DB never goes more than 6 hours stale between
    the daily 08:00 full pipeline runs.
    """
    logger.info("=== Platform sync (lightweight) starting ===")
    try:
        meta_result = meta_sync.run()
        logger.info("Meta sync: %s", meta_result.get("status"))
    except Exception as e:
        logger.warning("Meta sync error in lightweight run: %s", e)
    try:
        msft_result = microsoft_sync.run()
        logger.info("Microsoft sync: %s — keywords=%s",
                    msft_result.get("status"), msft_result.get("keywords_synced", 0))
    except Exception as e:
        logger.warning("Microsoft sync error in lightweight run: %s", e)
    logger.info("=== Platform sync (lightweight) done ===")


def _run_compliance_check():
    """
    Lightweight compliance check (spend + Meta targeting).
    Runs every 6 hours. Full Microsoft criteria check runs in the daily pipeline.
    """
    try:
        result = compliance_agent.run(lightweight=True)
        if result.get("checks_fail", 0) or result.get("auto_fixed", 0):
            logger.warning(
                "Compliance: %d/%d checks failing, %d auto-fixed",
                result["checks_fail"], result["checks_total"], result["auto_fixed"],
            )
        else:
            logger.info("Compliance: all %d checks passing", result.get("checks_total", 0))
    except Exception as e:
        logger.error("Compliance check error: %s", e, exc_info=True)


def setup_schedule():
    """Configure the daily run schedule."""
    # Run pipeline at 08:00 every day
    schedule.every().day.at("08:00").do(run_pipeline)

    # Lightweight platform data sync every 6 hours (keeps DB fresh between pipeline runs)
    schedule.every(6).hours.do(_run_platform_sync)

    # Lightweight status check every hour
    schedule.every().hour.do(print_system_status)

    # Process messages every 5 minutes
    schedule.every(5).minutes.do(process_messages)

    # Push latest DB snapshot to Lovable Command Center every 5 minutes
    schedule.every(5).minutes.do(_sync_supabase)

    # Poll Supabase command_queue for commands from Lovable Command Center
    schedule.every(30).seconds.do(_run_command_executor)

    # Poll Supabase chat_messages for Command Center chat (responds via Claude)
    schedule.every(5).seconds.do(_run_chat_agent)

    # End-to-end health checks every 30 minutes
    schedule.every(30).minutes.do(_run_health_agent)

    # Compliance checks every 6 hours (runs after platform sync)
    schedule.every(6).hours.do(_run_compliance_check)

    logger.info("Scheduler configured: pipeline at 08:00 daily, status every hour, supabase sync every 5 min, command executor every 30s, chat agent every 5s, health checks every 30 min, compliance checks every 6 hours")


def run_daemon():
    """Run orchestrator as a background daemon."""
    logger.info("Starting orchestrator daemon...")
    db.heartbeat(AGENT_NAME, "alive", metadata={"mode": "daemon"})

    setup_schedule()
    print_system_status()

    # Run immediately on startup
    run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(30)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ridgecrest Designs — Marketing Orchestrator")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as a continuous daemon with scheduled execution")
    parser.add_argument("--force", action="store_true",
                        help="Force full pipeline run regardless of day-of-week")
    parser.add_argument("--status", action="store_true",
                        help="Print system status and exit")
    parser.add_argument("--phase", choices=["analysis", "optimize", "creative", "report"],
                        help="Run a single phase only")
    args = parser.parse_args()

    if args.status:
        print_system_status()
        return

    if args.phase:
        import time as _time
        _run_id = f"{date.today().isoformat()}-{int(_time.time())}"
        db.heartbeat(AGENT_NAME, "alive")
        guardrails.assert_guardrails_present()
        if args.phase == "analysis":
            performance_analyst.run()
        elif args.phase == "optimize":
            violations = guardrails.check_pipeline_state(_run_id)
            if any(v["category"] == "escalation" for v in violations):
                logger.critical(
                    "Optimization halted — escalation violations active. "
                    "Resolve before running --phase optimize."
                )
            else:
                bid_budget_optimizer.run()
        elif args.phase == "creative":
            creative_agent.run(generate_all=False)
        elif args.phase == "report":
            reporting_agent.run(report_type="daily", use_claude=True)
        return

    if args.daemon:
        run_daemon()
    else:
        run_pipeline(force=args.force)


if __name__ == "__main__":
    main()
