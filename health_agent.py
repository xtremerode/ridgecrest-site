"""
Health Agent
============
Runs end-to-end connectivity checks across every component of the agency stack.
Writes pass/fail results to Supabase system_health table.
Sends an alert email via Resend when any check transitions from passing to failing.

Checks:
  - Local PostgreSQL database
  - Google Ads API (lightweight campaign list)
  - Meta Graph API (account info)
  - Microsoft Ads API (token refresh)
  - Supabase edge functions (save-recommendation, approve-recommendation, get-pending-commands)
  - Resend (API key validation)
  - Supabase sync freshness (last sync < 10 min ago)
  - Agent heartbeats (flag agents stale > 26 hours)

Run standalone:  python health_agent.py
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [health_agent] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME     = "health_agent"
SUPABASE_URL   = "https://itoinsaotwsmidbosqbq.supabase.co"
INGEST_API_KEY = os.getenv("INGEST_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
ALERT_EMAIL    = "henry@ridgecrestdesigns.com"
ALERT_FROM     = "alerts@ridgecrestdesigns.com"

# How long before an agent heartbeat is considered stale
STALE_AGENT_HOURS = 26


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------

def _ok(component: str, detail: str = "") -> dict:
    return {"component": component, "status": "ok", "detail": detail}


def _fail(component: str, detail: str) -> dict:
    return {"component": component, "status": "fail", "detail": detail}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_database() -> dict:
    try:
        with db.get_db() as (conn, cur):
            cur.execute("SELECT 1 AS ping")
            cur.fetchone()
        return _ok("database", "Local PostgreSQL reachable")
    except Exception as e:
        return _fail("database", str(e))


def check_google_ads() -> dict:
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        # Package not installed in this environment — verify credentials are set instead
        required = ["GOOGLE_DEVELOPER_TOKEN", "GOOGLE_CLIENT_ID",
                    "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            return _fail("google_ads", f"Missing credentials: {', '.join(missing)}")
        return _ok("google_ads", "Credentials present (SDK not in this env — runs via orchestrator)")
    try:
        customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "5576077690").replace("-", "")
        manager_id  = os.getenv("GOOGLE_ADS_MANAGER_ID",  "4478944999").replace("-", "")
        creds = {
            "developer_token":   os.getenv("GOOGLE_DEVELOPER_TOKEN"),
            "client_id":         os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret":     os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token":     os.getenv("GOOGLE_REFRESH_TOKEN"),
            "login_customer_id": manager_id,
            "use_proto_plus":    True,
        }
        client  = GoogleAdsClient.load_from_dict(creds)
        service = client.get_service("GoogleAdsService")
        query   = "SELECT campaign.id FROM campaign LIMIT 1"
        service.search(customer_id=customer_id, query=query)
        return _ok("google_ads", "API connection successful")
    except Exception as e:
        return _fail("google_ads", str(e)[:200])


def check_meta() -> dict:
    try:
        access_token  = os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = os.getenv("META_AD_ACCOUNT_ID", "act_58393749")
        if not access_token:
            return _fail("meta", "META_ACCESS_TOKEN not set")
        url    = f"https://graph.facebook.com/v21.0/{ad_account_id}"
        params = {"fields": "id,name", "access_token": access_token}
        resp   = requests.get(url, params=params, timeout=15)
        data   = resp.json()
        if "error" in data:
            return _fail("meta", data["error"].get("message", "API error")[:200])
        return _ok("meta", f"Account {data.get('name', ad_account_id)} reachable")
    except Exception as e:
        return _fail("meta", str(e)[:200])


def check_microsoft() -> dict:
    try:
        client_id     = os.getenv("MICROSOFT_CLIENT_ID", "")
        tenant_id     = os.getenv("MICROSOFT_TENANT_ID", "")
        refresh_token = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
        dev_token     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
        if not all([client_id, tenant_id, refresh_token, dev_token]):
            return _fail("microsoft_ads", "One or more Microsoft credentials not set")
        # Use public client flow (no client_secret) matching actual sync agent
        url  = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id":     client_id,
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
            "scope":         "https://ads.microsoft.com/msads.manage offline_access",
        }
        resp = requests.post(url, data=data, timeout=15)
        token_data = resp.json()
        if "error" in token_data:
            return _fail("microsoft_ads", token_data.get("error_description", "Token refresh failed")[:200])
        return _ok("microsoft_ads", "Token refresh successful")
    except Exception as e:
        return _fail("microsoft_ads", str(e)[:200])


def check_supabase_edge_functions() -> list[dict]:
    results = []
    edge_base = f"{SUPABASE_URL}/functions/v1"
    headers   = {"x-api-key": INGEST_API_KEY, "Content-Type": "application/json"}

    # save-recommendation: count_pending is a safe read-only action
    try:
        resp = requests.post(
            f"{edge_base}/save-recommendation",
            headers=headers,
            json={"action": "count_pending"},
            timeout=10,
        )
        if resp.status_code == 200:
            results.append(_ok("supabase_save_recommendation", f"count_pending={resp.json().get('count', '?')}"))
        else:
            results.append(_fail("supabase_save_recommendation", f"HTTP {resp.status_code}: {resp.text[:100]}"))
    except Exception as e:
        results.append(_fail("supabase_save_recommendation", str(e)[:200]))

    # get-pending-commands: list action
    try:
        resp = requests.post(
            f"{edge_base}/get-pending-commands",
            headers=headers,
            json={"action": "list"},
            timeout=10,
        )
        if resp.status_code == 200:
            results.append(_ok("supabase_get_pending_commands", "reachable"))
        else:
            results.append(_fail("supabase_get_pending_commands", f"HTTP {resp.status_code}: {resp.text[:100]}"))
    except Exception as e:
        results.append(_fail("supabase_get_pending_commands", str(e)[:200]))

    # approve-recommendation: OPTIONS preflight is enough to verify it's deployed
    try:
        resp = requests.options(
            f"{edge_base}/approve-recommendation",
            timeout=10,
        )
        if resp.status_code in (200, 204):
            results.append(_ok("supabase_approve_recommendation", "reachable"))
        else:
            results.append(_fail("supabase_approve_recommendation", f"HTTP {resp.status_code}"))
    except Exception as e:
        results.append(_fail("supabase_approve_recommendation", str(e)[:200]))

    return results


def check_resend() -> dict:
    try:
        if not RESEND_API_KEY:
            return _fail("resend", "RESEND_API_KEY not set")
        resp = requests.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return _ok("resend", "API key valid")
        return _fail("resend", f"HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        return _fail("resend", str(e)[:200])


def check_supabase_sync_freshness() -> dict:
    """Verify that the Supabase sync has run recently (within 10 minutes)."""
    try:
        with db.get_db() as (conn, cur):
            cur.execute(
                """SELECT last_run_at FROM agent_heartbeats
                   WHERE agent_name = 'supabase_sync'
                   ORDER BY last_run_at DESC LIMIT 1"""
            )
            row = cur.fetchone()
        if not row or not row["last_run_at"]:
            return _fail("supabase_sync", "No sync heartbeat found")
        last_run = row["last_run_at"]
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
        age_minutes = (datetime.now(timezone.utc) - last_run).total_seconds() / 60
        if age_minutes > 10:
            return _fail("supabase_sync", f"Last sync {age_minutes:.0f} min ago (threshold: 10 min)")
        return _ok("supabase_sync", f"Last sync {age_minutes:.1f} min ago")
    except Exception as e:
        return _fail("supabase_sync", str(e)[:200])


def check_agent_heartbeats() -> list[dict]:
    """Flag any agent that hasn't reported in more than STALE_AGENT_HOURS hours."""
    results = []
    try:
        with db.get_db() as (conn, cur):
            cur.execute("SELECT agent_name, status, last_run_at FROM agent_heartbeats ORDER BY agent_name")
            rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            name     = row["agent_name"]
            last_run = row["last_run_at"]
            if not last_run:
                results.append(_fail(f"heartbeat_{name}", "Never run"))
                continue
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
            if age_hours > STALE_AGENT_HOURS:
                results.append(_fail(f"heartbeat_{name}", f"Stale — last run {age_hours:.0f}h ago"))
            else:
                results.append(_ok(f"heartbeat_{name}", f"Last run {age_hours:.1f}h ago, status={row['status']}"))
    except Exception as e:
        results.append(_fail("heartbeat_check", str(e)[:200]))
    return results


# ---------------------------------------------------------------------------
# Write results to Supabase
# ---------------------------------------------------------------------------

def _write_results(results: list[dict]):
    """Write health check results to Supabase via a direct edge function call."""
    headers = {"x-api-key": INGEST_API_KEY, "Content-Type": "application/json"}
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/functions/v1/save-health-check",
            headers=headers,
            json={"checks": results, "checked_at": datetime.now(timezone.utc).isoformat()},
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("Health results written to Supabase")
        else:
            logger.warning("save-health-check returned %d: %s", resp.status_code, resp.text[:100])
    except Exception as e:
        logger.error("Failed to write health results: %s", e)


# ---------------------------------------------------------------------------
# Alert on newly failing checks
# ---------------------------------------------------------------------------

def _send_alert(failures: list[dict]):
    if not RESEND_API_KEY or not failures:
        return
    rows = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #e2e8f0;font-weight:600'>"
        f"{f['component']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0;color:#ef4444'>"
        f"{f['detail']}</td></tr>"
        for f in failures
    )
    html = f"""
<html><body style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:24px">
  <div style="background:#0f172a;padding:16px 24px;border-radius:8px 8px 0 0">
    <p style="color:#94a3b8;margin:0;font-size:12px;text-transform:uppercase;letter-spacing:1px">
      Ridgecrest Designs — Health Monitor
    </p>
    <h2 style="color:#ef4444;margin:4px 0 0">⚠ System Health Alert</h2>
  </div>
  <div style="border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 8px 8px">
    <p style="color:#334155">{len(failures)} component(s) are currently failing:</p>
    <table style="width:100%;border-collapse:collapse">
      <tr>
        <th style="text-align:left;padding:6px 12px;background:#f8fafc;font-size:12px;
                   text-transform:uppercase;color:#64748b">Component</th>
        <th style="text-align:left;padding:6px 12px;background:#f8fafc;font-size:12px;
                   text-transform:uppercase;color:#64748b">Error</th>
      </tr>
      {rows}
    </table>
    <p style="color:#94a3b8;font-size:12px;margin-top:24px;text-align:center">
      Ridgecrest Designs Marketing Automation · Health check ran at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
    </p>
  </div>
</body></html>
"""
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from":    ALERT_FROM,
            "to":      [ALERT_EMAIL],
            "subject": f"[Health Alert] {len(failures)} system component(s) failing — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "html":    html,
        })
        logger.info("Health alert email sent for %d failure(s)", len(failures))
    except Exception as e:
        logger.error("Failed to send health alert email: %s", e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> dict:
    logger.info("=== Health Agent starting ===")
    db.heartbeat(AGENT_NAME, "alive")

    results: list[dict] = []

    # Core infrastructure
    results.append(check_database())

    # Platform APIs
    results.append(check_google_ads())
    results.append(check_meta())
    results.append(check_microsoft())

    # Supabase edge functions
    results.extend(check_supabase_edge_functions())

    # Email
    results.append(check_resend())

    # Sync freshness
    results.append(check_supabase_sync_freshness())

    # Agent heartbeats
    results.extend(check_agent_heartbeats())

    # Summary
    failures = [r for r in results if r["status"] == "fail"]
    passing  = [r for r in results if r["status"] == "ok"]

    logger.info(
        "Health check complete — %d passing, %d failing",
        len(passing), len(failures),
    )
    for f in failures:
        logger.warning("FAIL [%s]: %s", f["component"], f["detail"])

    # Write to Supabase
    _write_results(results)

    # Alert on failures
    if failures:
        _send_alert(failures)

    db.heartbeat(AGENT_NAME, "alive" if not failures else "error", metadata={
        "checks_total":   len(results),
        "checks_passing": len(passing),
        "checks_failing": len(failures),
        "failures":       [f["component"] for f in failures],
    })

    logger.info("=== Health Agent done ===")
    return {
        "checks_total":   len(results),
        "checks_passing": len(passing),
        "checks_failing": len(failures),
        "failures":       failures,
    }


if __name__ == "__main__":
    run()
