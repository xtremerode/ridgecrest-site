"""
Google Ads Day Scheduler
========================
Applies Fri/Sat/Sun/Mon ad scheduling to all Ridgecrest Designs campaigns
via AdSchedule campaign criteria. Blocks Tuesday, Wednesday, Thursday.

STATUS: Staged — runs automatically once the Google Ads developer token
        is approved and google_ads_builder.py campaigns are live.

Run standalone:  python google_ads_scheduler.py
"""

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [google_ads_scheduler] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME  = "google_ads_scheduler"
PLATFORM    = "google_ads"
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")

# Active days only — CLAUDE.md §8
# DayOfWeek enum: MONDAY=2, TUESDAY=3, WEDNESDAY=4, THURSDAY=5,
#                 FRIDAY=6, SATURDAY=7, SUNDAY=1
ACTIVE_DAYS = [
    {"day": "FRIDAY",   "start_hour": 0, "end_hour": 24},
    {"day": "SATURDAY", "start_hour": 0, "end_hour": 24},
    {"day": "SUNDAY",   "start_hour": 0, "end_hour": 24},
    {"day": "MONDAY",   "start_hour": 0, "end_hour": 24},
]
BLOCKED_DAYS = ["TUESDAY", "WEDNESDAY", "THURSDAY"]


def _get_google_client():
    """Initialize and return a Google Ads API client."""
    from google.ads.googleads.client import GoogleAdsClient
    creds = {
        "developer_token":   os.getenv("GOOGLE_DEVELOPER_TOKEN"),
        "client_id":         os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret":     os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token":     os.getenv("GOOGLE_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_MANAGER_ID", "").replace("-", ""),
        "use_proto_plus":    True,
    }
    return GoogleAdsClient.load_from_dict(creds)


def _get_rma_campaign_ids() -> list[tuple[int, str]]:
    """Return (campaign_resource_name, db_id) for all [RMA] Google campaigns."""
    with db.get_db() as (conn, cur):
        cur.execute(
            """
            SELECT google_campaign_id, id, name
            FROM campaigns
            WHERE platform = 'google_ads'
              AND managed_by = 'claude_code'
              AND name LIKE '[RMA]%%'
            """,
        )
        return [(r["google_campaign_id"], r["id"], r["name"])
                for r in cur.fetchall()]


def apply_schedule(auto_apply: bool = False) -> dict:
    """
    Apply AdSchedule criteria to all [RMA] Google Ads campaigns.
    Creates criteria for Fri/Sat/Sun/Mon; removes or sets -100% for Tue/Wed/Thu.

    Returns summary dict.
    """
    logger.info("=== Google Ads Scheduler starting (auto_apply=%s) ===", auto_apply)
    db.heartbeat(AGENT_NAME, "alive")

    try:
        client = _get_google_client()
    except Exception as e:
        err = f"Google Ads client init failed: {e}"
        logger.error(err)
        db.heartbeat(AGENT_NAME, "error", error=err)
        return {"platform": PLATFORM, "status": "error", "error": err}

    campaigns = _get_rma_campaign_ids()
    if not campaigns:
        logger.info("No [RMA] Google campaigns found in DB — nothing to schedule")
        db.heartbeat(AGENT_NAME, "success",
                     metadata={"campaigns_processed": 0})
        return {"platform": PLATFORM, "status": "success", "campaigns_processed": 0}

    campaign_criterion_service = client.get_service("CampaignCriterionService")
    applied = 0
    errors  = []

    for external_id, db_id, name in campaigns:
        try:
            operations = []

            for day_cfg in ACTIVE_DAYS:
                criterion = client.get_type("CampaignCriterion")
                criterion.campaign = external_id
                criterion.negative = False
                criterion.ad_schedule.day_of_week = (
                    client.enums.DayOfWeekEnum[day_cfg["day"]]
                )
                criterion.ad_schedule.start_hour    = day_cfg["start_hour"]
                criterion.ad_schedule.end_hour      = day_cfg["end_hour"]
                criterion.ad_schedule.start_minute  = (
                    client.enums.MinuteOfHourEnum.ZERO
                )
                criterion.ad_schedule.end_minute    = (
                    client.enums.MinuteOfHourEnum.ZERO
                )
                op = client.get_type("CampaignCriterionOperation")
                op.create.CopyFrom(criterion)
                operations.append(op)

            for day in BLOCKED_DAYS:
                criterion = client.get_type("CampaignCriterion")
                criterion.campaign = external_id
                criterion.negative = True   # exclude these days entirely
                criterion.ad_schedule.day_of_week = (
                    client.enums.DayOfWeekEnum[day]
                )
                criterion.ad_schedule.start_hour   = 0
                criterion.ad_schedule.end_hour      = 24
                criterion.ad_schedule.start_minute  = (
                    client.enums.MinuteOfHourEnum.ZERO
                )
                criterion.ad_schedule.end_minute    = (
                    client.enums.MinuteOfHourEnum.ZERO
                )
                op = client.get_type("CampaignCriterionOperation")
                op.create.CopyFrom(criterion)
                operations.append(op)

            if auto_apply:
                campaign_criterion_service.mutate_campaign_criteria(
                    customer_id=CUSTOMER_ID,
                    operations=operations,
                )
                logger.info("  Schedule applied: %s", name)
                db.log_action(
                    agent_name=AGENT_NAME, action_type="apply_day_schedule",
                    entity_type="campaign", entity_id=db_id,
                    before={},
                    after={
                        "active_days":  [d["day"] for d in ACTIVE_DAYS],
                        "blocked_days": BLOCKED_DAYS,
                    },
                    reason="CLAUDE.md §8 — ads run Fri/Sat/Sun/Mon only",
                    google_entity_id=external_id,
                )
                applied += 1
            else:
                logger.info("  [PENDING] Would schedule Fri/Sat/Sun/Mon for: %s", name)
                db.log_action(
                    agent_name=AGENT_NAME, action_type="apply_day_schedule",
                    entity_type="campaign", entity_id=db_id,
                    before={},
                    after={
                        "active_days":  [d["day"] for d in ACTIVE_DAYS],
                        "blocked_days": BLOCKED_DAYS,
                    },
                    reason="CLAUDE.md §8 — pending auto_apply",
                    google_entity_id=external_id,
                )

        except Exception as e:
            errors.append({"campaign": name, "error": str(e)})
            logger.error("  Failed to schedule %s: %s", name, e)

    status = "error" if errors and applied == 0 else "success"
    db.heartbeat(AGENT_NAME, status, metadata={
        "campaigns_processed": len(campaigns),
        "applied":             applied,
        "errors":              len(errors),
        "auto_apply":          auto_apply,
    })
    logger.info(
        "=== Google Ads Scheduler done — campaigns=%d applied=%d errors=%d ===",
        len(campaigns), applied, len(errors),
    )
    return {
        "platform":            PLATFORM,
        "status":              status,
        "campaigns_processed": len(campaigns),
        "applied":             applied,
        "errors":              errors,
    }


if __name__ == "__main__":
    import json
    auto = os.getenv("GOOGLE_SCHEDULER_AUTO_APPLY", "false").lower() == "true"
    result = apply_schedule(auto_apply=auto)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["status"] == "success" else 1)
