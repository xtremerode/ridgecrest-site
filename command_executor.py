"""
Command Executor
================
Polls the Supabase command_queue table for pending commands submitted via
the Lovable Command Center, executes them against the ad platforms, and
reports results back to Supabase.

Supported commands:
  - pause_campaign     {platform, external_id}   pause one campaign
  - enable_campaign    {platform, external_id}   enable one campaign
  - pause_all          {platform}                pause all on that platform
  - enable_all         {platform}                enable all on that platform

Platforms: google_ads | meta | microsoft_ads | all

Run standalone:  python command_executor.py
Run continuously: python command_executor.py --loop
"""

import argparse
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [command_executor] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SUPABASE_URL      = "https://itoinsaotwsmidbosqbq.supabase.co"
INGEST_API_KEY    = os.getenv("INGEST_API_KEY", "")
COMMANDS_ENDPOINT = f"{SUPABASE_URL}/functions/v1/get-pending-commands"

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_API_VERSION  = "v21.0"
META_BASE_URL     = f"https://graph.facebook.com/{META_API_VERSION}"

MSFT_CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID", "")
MSFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
MSFT_TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID", "")
MSFT_REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
MSFT_DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
MSFT_ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))

POLL_INTERVAL_SECONDS = 30
RECOMMENDATIONS_ENDPOINT = f"{SUPABASE_URL}/functions/v1/save-recommendation"


# ---------------------------------------------------------------------------
# Supabase edge function helpers
# ---------------------------------------------------------------------------

def _edge_headers() -> dict:
    return {
        "x-api-key": INGEST_API_KEY,
        "Content-Type": "application/json",
    }


def fetch_pending_commands() -> list[dict]:
    if not INGEST_API_KEY:
        logger.warning("INGEST_API_KEY not set — skipping command poll")
        return []
    resp = requests.post(
        COMMANDS_ENDPOINT,
        headers=_edge_headers(),
        json={"action": "list"},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("fetch_pending_commands: %d — %s", resp.status_code, resp.text[:200])
        return []
    data = resp.json()
    return data if isinstance(data, list) else data.get("commands", [])


def update_command(cmd_id: int, status: str, result: str = "") -> bool:
    resp = requests.post(
        COMMANDS_ENDPOINT,
        headers=_edge_headers(),
        json={"action": "update", "id": cmd_id, "status": status, "result_message": result},
        timeout=10,
    )
    ok = resp.status_code == 200 and resp.json().get("success", False)
    if not ok:
        logger.warning("update_command %d: %d — %s", cmd_id, resp.status_code, resp.text[:200])
    return ok


# ---------------------------------------------------------------------------
# Local DB helpers
# ---------------------------------------------------------------------------

def _get_campaigns(platform: str | None = None) -> list[dict]:
    with db.get_db() as (conn, cur):
        if platform and platform != "all":
            cur.execute(
                "SELECT * FROM campaigns WHERE platform = %s AND status != 'REMOVED'",
                (platform,),
            )
        else:
            cur.execute("SELECT * FROM campaigns WHERE status != 'REMOVED'")
        return [dict(r) for r in cur.fetchall()]


def _update_db_status(campaign_db_id: int, status: str):
    with db.get_db() as (conn, cur):
        cur.execute(
            "UPDATE campaigns SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, campaign_db_id),
        )
    logger.info("DB updated: campaign id=%d → %s", campaign_db_id, status)


# ---------------------------------------------------------------------------
# Meta platform actions
# ---------------------------------------------------------------------------

def _meta_set_status(external_id: str, status: str) -> tuple[bool, str]:
    """status: 'ACTIVE' or 'PAUSED'"""
    resp = requests.post(
        f"{META_BASE_URL}/{external_id}",
        params={"access_token": META_ACCESS_TOKEN},
        json={"status": status},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code == 200 and data.get("success"):
        return True, f"Meta {external_id} → {status}"
    return False, f"Meta API error {resp.status_code}: {data.get('error', {}).get('message', resp.text[:100])}"


# ---------------------------------------------------------------------------
# Microsoft platform actions
# ---------------------------------------------------------------------------

def _msft_refresh_access_token() -> str:
    url = f"https://login.microsoftonline.com/{MSFT_TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "client_id":     MSFT_CLIENT_ID,
        "grant_type":    "refresh_token",
        "refresh_token": MSFT_REFRESH_TOKEN,
        "scope":         "https://ads.microsoft.com/msads.manage offline_access",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _msft_set_status(external_id: str, status: str) -> tuple[bool, str]:
    """status: 'Active' or 'Paused'"""
    try:
        from bingads.authorization import (
            AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
        )
        from bingads import ServiceClient

        access_token = _msft_refresh_access_token()
        tokens = OAuthTokens(
            access_token=access_token,
            access_token_expires_in_seconds=3600,
            refresh_token=MSFT_REFRESH_TOKEN,
        )
        oauth = OAuthWebAuthCodeGrant(
            client_id=MSFT_CLIENT_ID,
            client_secret=MSFT_CLIENT_SECRET,
            redirection_uri="https://login.microsoftonline.com/common/oauth2/nativeclient",
            oauth_tokens=tokens,
            oauth_scope=ADS_MANAGE,
            tenant=MSFT_TENANT_ID,
        )
        auth = AuthorizationData(
            account_id=MSFT_ACCOUNT_ID,
            developer_token=MSFT_DEV_TOKEN,
            authentication=oauth,
        )
        svc = ServiceClient("CampaignManagementService", 13, auth, "production")

        msft_id = int(external_id.replace("msft_", ""))
        camp = svc.Factory.CreateTransportObject("Campaign")
        camp.Id = msft_id
        camp.Status = status

        arr = svc.Factory.CreateTransportObject("ArrayOfCampaign")
        arr.Campaign.append(camp)
        svc.UpdateCampaigns(AccountId=MSFT_ACCOUNT_ID, Campaigns=arr)
        return True, f"Microsoft {external_id} → {status}"
    except Exception as e:
        return False, f"Microsoft error: {e}"


# ---------------------------------------------------------------------------
# Google Ads platform actions
# ---------------------------------------------------------------------------

def _google_set_status(external_id: str, status: str) -> tuple[bool, str]:
    """
    Google Ads developer token pending production approval.
    Status is applied to local DB and will sync on next pipeline run.
    """
    # TODO: full Google Ads API mutate when developer token is production-approved
    return True, (
        f"Google {external_id} → {status} applied to local DB "
        "(live API update pending developer token production approval)"
    )


# ---------------------------------------------------------------------------
# Platform dispatch
# ---------------------------------------------------------------------------

def _apply_to_platform(platform: str, external_id: str, desired_status: str) -> tuple[bool, str]:
    if platform == "meta":
        api_status = "ACTIVE" if desired_status == "ENABLED" else "PAUSED"
        return _meta_set_status(external_id, api_status)
    elif platform == "microsoft_ads":
        api_status = "Active" if desired_status == "ENABLED" else "Paused"
        return _msft_set_status(external_id, api_status)
    elif platform == "google_ads":
        return _google_set_status(external_id, desired_status)
    return False, f"Unknown platform: {platform}"


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

def execute_command(cmd: dict) -> tuple[str, str]:
    """
    Execute one command. Returns (final_status, result_message).
    final_status: 'completed' | 'failed'
    """
    cmd_type    = cmd.get("command_type", "")
    platform    = cmd.get("platform", "all")
    external_id = cmd.get("external_id") or ""

    logger.info("Executing: type=%s platform=%s external_id=%s", cmd_type, platform, external_id)

    results: list[str] = []
    all_ok = True

    # --- Single campaign ---
    if cmd_type in ("pause_campaign", "enable_campaign"):
        desired = "ENABLED" if cmd_type == "enable_campaign" else "PAUSED"
        with db.get_db() as (conn, cur):
            cur.execute(
                "SELECT * FROM campaigns WHERE google_campaign_id = %s AND status != 'REMOVED'",
                (external_id,),
            )
            row = cur.fetchone()
        if not row:
            return "failed", f"Campaign not found in DB: external_id={external_id}"
        camp = dict(row)
        ok, msg = _apply_to_platform(camp["platform"], external_id, desired)
        if ok:
            _update_db_status(camp["id"], desired)
        else:
            all_ok = False
        results.append(msg)

    # --- Bulk ---
    elif cmd_type in ("pause_all", "enable_all"):
        desired = "ENABLED" if cmd_type == "enable_all" else "PAUSED"
        target_platform = None if platform == "all" else platform
        campaigns = _get_campaigns(target_platform)
        if not campaigns:
            return "completed", "No campaigns found to update"
        for camp in campaigns:
            ok, msg = _apply_to_platform(camp["platform"], camp["google_campaign_id"], desired)
            if ok:
                _update_db_status(camp["id"], desired)
            else:
                all_ok = False
            results.append(msg)

    else:
        return "failed", f"Unknown command_type: {cmd_type}"

    final_status = "completed" if all_ok else "failed"
    return final_status, " | ".join(results)


# ---------------------------------------------------------------------------
# Recommendation execution
# ---------------------------------------------------------------------------

def fetch_approved_recommendations() -> list[dict]:
    """Fetch recommendations with status=approved that haven't been executed yet."""
    if not INGEST_API_KEY:
        return []
    resp = requests.post(
        RECOMMENDATIONS_ENDPOINT,
        headers=_edge_headers(),
        json={"action": "fetch_approved"},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("fetch_approved_recommendations: %d — %s", resp.status_code, resp.text[:200])
        return []
    return resp.json().get("recommendations", [])


def mark_recommendation(rec_id: int, success: bool, result: str):
    """Mark a recommendation as executed or failed."""
    resp = requests.post(
        RECOMMENDATIONS_ENDPOINT,
        headers=_edge_headers(),
        json={"action": "mark_executed", "id": rec_id, "success": success, "result": result},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("mark_recommendation %d: %d — %s", rec_id, resp.status_code, resp.text[:200])


def _get_campaign_by_id(campaign_id: int) -> dict | None:
    """Look up a campaign in the local DB by its integer id."""
    if not campaign_id:
        return None
    with db.get_db() as (conn, cur):
        cur.execute(
            "SELECT * FROM campaigns WHERE id = %s AND status != 'REMOVED'",
            (campaign_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _meta_set_budget(external_id: str, daily_budget_usd: float) -> tuple[bool, str]:
    """Set a Meta campaign's daily budget (API expects cents as integer)."""
    daily_budget_cents = int(daily_budget_usd * 100)
    resp = requests.post(
        f"{META_BASE_URL}/{external_id}",
        params={"access_token": META_ACCESS_TOKEN},
        json={"daily_budget": daily_budget_cents},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code == 200 and data.get("success"):
        return True, f"Meta {external_id} daily budget → ${daily_budget_usd:.2f}"
    return False, f"Meta API error {resp.status_code}: {data.get('error', {}).get('message', resp.text[:100])}"


def _msft_set_budget(external_id: str, daily_budget_usd: float) -> tuple[bool, str]:
    """Set a Microsoft Ads campaign's daily budget."""
    try:
        from bingads.authorization import (
            AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
        )
        from bingads import ServiceClient

        access_token = _msft_refresh_access_token()
        tokens = OAuthTokens(
            access_token=access_token,
            access_token_expires_in_seconds=3600,
            refresh_token=MSFT_REFRESH_TOKEN,
        )
        oauth = OAuthWebAuthCodeGrant(
            client_id=MSFT_CLIENT_ID,
            client_secret=MSFT_CLIENT_SECRET,
            redirection_uri="https://login.microsoftonline.com/common/oauth2/nativeclient",
            oauth_tokens=tokens,
            oauth_scope=ADS_MANAGE,
            tenant=MSFT_TENANT_ID,
        )
        auth = AuthorizationData(
            account_id=MSFT_ACCOUNT_ID,
            developer_token=MSFT_DEV_TOKEN,
            authentication=oauth,
        )
        svc = ServiceClient("CampaignManagementService", 13, auth, "production")

        msft_id = int(external_id.replace("msft_", ""))
        camp = svc.Factory.CreateTransportObject("Campaign")
        camp.Id = msft_id
        camp.DailyBudget = daily_budget_usd
        camp.BudgetType = "DailyBudgetStandard"

        arr = svc.Factory.CreateTransportObject("ArrayOfCampaign")
        arr.Campaign.append(camp)
        svc.UpdateCampaigns(AccountId=MSFT_ACCOUNT_ID, Campaigns=arr)
        return True, f"Microsoft {external_id} daily budget → ${daily_budget_usd:.2f}"
    except Exception as e:
        return False, f"Microsoft budget error: {e}"


def execute_recommendation(rec: dict) -> tuple[bool, str]:
    """
    Execute an approved recommendation against the appropriate platform.
    Returns (success, result_message).
    """
    action_type   = rec.get("action_type", "")
    platform      = rec.get("platform", "")
    campaign_id   = rec.get("campaign_id")
    campaign_name = rec.get("campaign_name", "unknown")

    proposed = rec.get("proposed_value") or {}
    if isinstance(proposed, str):
        import json
        try:
            proposed = json.loads(proposed)
        except Exception:
            proposed = {}

    logger.info(
        "Executing recommendation id=%s type=%s platform=%s campaign=%s",
        rec.get("id"), action_type, platform, campaign_name,
    )

    # Look up campaign in local DB
    camp = _get_campaign_by_id(campaign_id)
    if not camp:
        return False, f"Campaign id={campaign_id} not found in local DB"

    external_id = camp.get("google_campaign_id", "")

    # --- pause_campaign ---
    if action_type == "pause_campaign":
        ok, msg = _apply_to_platform(platform, external_id, "PAUSED")
        if ok:
            _update_db_status(camp["id"], "PAUSED")
        return ok, msg

    # --- budget_increase or blitz ---
    if action_type in ("budget_increase", "blitz"):
        new_budget = proposed.get("daily_budget_usd")
        if not new_budget:
            return False, "proposed_value missing daily_budget_usd"

        if platform == "meta":
            ok, msg = _meta_set_budget(external_id, float(new_budget))
        elif platform == "microsoft_ads":
            ok, msg = _msft_set_budget(external_id, float(new_budget))
        elif platform == "google_ads":
            # Update local DB — will apply on next Google Ads sync
            new_budget_micros = int(float(new_budget) * 1_000_000)
            with db.get_db() as (conn, cur):
                cur.execute(
                    "UPDATE campaigns SET daily_budget_micros = %s, updated_at = NOW() WHERE id = %s",
                    (new_budget_micros, camp["id"]),
                )
            ok  = True
            msg = (
                f"Google {campaign_name} budget → ${new_budget:.2f} applied to local DB "
                "(live API update pending developer token approval)"
            )
        else:
            return False, f"Unknown platform: {platform}"

        return ok, msg

    return False, f"Unsupported action_type: {action_type}"


def process_approved_recommendations() -> int:
    """Fetch and execute all approved recommendations. Returns count processed."""
    recs = fetch_approved_recommendations()
    if not recs:
        return 0

    processed = 0
    for rec in recs:
        rec_id = rec.get("id")
        try:
            success, result = execute_recommendation(rec)
            mark_recommendation(rec_id, success, result)
            logger.info(
                "Recommendation #%d %s: %s",
                rec_id, "executed" if success else "failed", result[:120],
            )
        except Exception as e:
            logger.error("Recommendation #%d exception: %s", rec_id, e, exc_info=True)
            mark_recommendation(rec_id, False, str(e))
        processed += 1

    return processed


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------

def poll_once() -> int:
    commands = fetch_pending_commands()
    if not commands:
        return 0
    executed = 0
    for cmd in commands:
        cmd_id = cmd["id"]
        update_command(cmd_id, "processing")
        try:
            final_status, result_msg = execute_command(cmd)
            update_command(cmd_id, final_status, result_msg)
            logger.info("Command %d → %s: %s", cmd_id, final_status, result_msg[:120])
        except Exception as e:
            logger.error("Command %d exception: %s", cmd_id, e, exc_info=True)
            update_command(cmd_id, "failed", str(e))
        executed += 1
    return executed


def run() -> int:
    """Called by orchestrator on its schedule."""
    commands_processed = poll_once()
    recs_processed     = process_approved_recommendations()
    return commands_processed + recs_processed


def main():
    parser = argparse.ArgumentParser(description="Ridgecrest — Command Executor")
    parser.add_argument("--loop", action="store_true",
                        help=f"Run continuously every {POLL_INTERVAL_SECONDS}s")
    args = parser.parse_args()

    if args.loop:
        logger.info("Command executor loop started (interval=%ds)", POLL_INTERVAL_SECONDS)
        while True:
            try:
                n = poll_once()
                if n:
                    logger.info("Executed %d command(s)", n)
            except Exception as e:
                logger.error("Poll loop error: %s", e)
            time.sleep(POLL_INTERVAL_SECONDS)
    else:
        n = poll_once()
        logger.info("Done — executed %d command(s)", n)


if __name__ == "__main__":
    main()
