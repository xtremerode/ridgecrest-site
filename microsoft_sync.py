"""
Microsoft Sync Agent
====================
Pulls the last 30 days of campaign performance data from the Microsoft Ads API
for account 187004108 and writes it into performance_metrics
with platform='microsoft_ads'.

Run standalone:  python microsoft_sync.py
"""
import csv
import io
import logging
import os
import sys
import time
import urllib.request
import zipfile
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [microsoft_sync] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

AGENT_NAME    = "microsoft_sync"
PLATFORM      = "microsoft_ads"
ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))
CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID", "")
DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
REDIRECT_URI  = "https://login.microsoftonline.com/common/oauth2/nativeclient"
DAYS_BACK     = 30
REPORT_TIMEOUT = 120   # seconds to wait for report generation


def _refresh_access_token() -> str:
    url  = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id":     CLIENT_ID,
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "scope":         "https://ads.microsoft.com/msads.manage offline_access",
    }
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    token_data = resp.json()
    if "error" in token_data:
        raise RuntimeError(f"Token refresh failed: {token_data}")
    return token_data["access_token"], int(token_data.get("expires_in", 3600))


def _build_auth(access_token: str, expires_in: int):
    from bingads.authorization import (
        AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
    )
    tokens = OAuthTokens(
        access_token=access_token,
        access_token_expires_in_seconds=expires_in,
        refresh_token=REFRESH_TOKEN,
    )
    oauth = OAuthWebAuthCodeGrant(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirection_uri=REDIRECT_URI,
        oauth_tokens=tokens,
        oauth_scope=ADS_MANAGE,
        tenant=TENANT_ID,
    )
    return AuthorizationData(
        account_id=ACCOUNT_ID,
        developer_token=DEV_TOKEN,
        authentication=oauth,
    )


def _resolve_customer_id(auth_data) -> int | None:
    from bingads import ServiceClient
    try:
        svc = ServiceClient("CustomerManagementService", 13, auth_data, "production")
        resp = svc.GetUser(UserId=None)
        roles = (resp.CustomerRoles.CustomerRole
                 if resp.CustomerRoles and resp.CustomerRoles.CustomerRole else [])
        for role in roles:
            if hasattr(role, "CustomerId"):
                return int(role.CustomerId)
    except Exception as e:
        logger.warning("GetUser failed: %s", e)
    return None


def _fetch_campaigns(auth_data) -> dict[int, dict]:
    """Returns {campaign_id: {name, budget_usd, status}} for all Search campaigns."""
    from bingads import ServiceClient
    try:
        svc = ServiceClient("CampaignManagementService", 13, auth_data, "production")
        resp = svc.GetCampaignsByAccountId(AccountId=ACCOUNT_ID, CampaignType="Search")
        raw = (resp.Campaign.Campaign
               if resp.Campaign and hasattr(resp.Campaign, "Campaign")
               else list(resp.Campaign or []))
        result = {}
        for c in raw:
            budget_usd = None
            try:
                # DailyBudget is in the campaign object for shared or campaign-level budgets
                if hasattr(c, "DailyBudget") and c.DailyBudget is not None:
                    budget_usd = float(c.DailyBudget)
                elif hasattr(c, "Budget") and c.Budget is not None:
                    b = c.Budget
                    if hasattr(b, "Amount") and b.Amount is not None:
                        budget_usd = float(b.Amount)
            except Exception:
                pass
            result[int(c.Id)] = {
                "name":       c.Name,
                "budget_usd": budget_usd,
                "status":     str(c.Status) if hasattr(c, "Status") else "ENABLED",
            }
        return result
    except Exception as e:
        logger.warning("Could not fetch campaign list: %s — names will fall back to IDs", e)
        return {}


def _upsert_campaign(msft_campaign_id: int, name: str, budget_usd: float | None = None, status: str = "ENABLED") -> int:
    external_id   = f"msft_{msft_campaign_id}"
    budget_micros = int(budget_usd * 1_000_000) if budget_usd is not None else None
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO campaigns
               (google_campaign_id, name, status, platform, daily_budget_micros, last_synced_at)
               VALUES (%s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_campaign_id) DO UPDATE SET
                   name                 = EXCLUDED.name,
                   status               = EXCLUDED.status,
                   platform             = EXCLUDED.platform,
                   daily_budget_micros  = COALESCE(EXCLUDED.daily_budget_micros, campaigns.daily_budget_micros),
                   last_synced_at       = NOW(),
                   updated_at           = NOW()
               RETURNING id""",
            (external_id, name, status, PLATFORM, budget_micros),
        )
        return cur.fetchone()["id"]


def _upsert_metric(metric_date, entity_id: int, external_id: str,
                   impressions: int, clicks: int, conversions: float,
                   cost_micros: int, ctr: float, cpc_avg_micros: int):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO performance_metrics
               (metric_date, entity_type, entity_id, google_entity_id,
                impressions, clicks, conversions, cost_micros,
                ctr, cpc_avg_micros, platform)
               VALUES (%s,'campaign',%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                   impressions    = EXCLUDED.impressions,
                   clicks         = EXCLUDED.clicks,
                   conversions    = EXCLUDED.conversions,
                   cost_micros    = EXCLUDED.cost_micros,
                   ctr            = EXCLUDED.ctr,
                   cpc_avg_micros = EXCLUDED.cpc_avg_micros,
                   platform       = EXCLUDED.platform""",
            (metric_date, entity_id, external_id,
             impressions, clicks, conversions, cost_micros,
             ctr, cpc_avg_micros, PLATFORM),
        )


def _submit_and_download_report(auth_data, start_date: date, end_date: date) -> list[dict] | None:
    """Submit a CampaignPerformanceReport, poll until ready, download and parse CSV."""
    from bingads import ServiceClient

    svc = ServiceClient("ReportingService", 13, auth_data, "production")

    req = svc.factory.create("CampaignPerformanceReportRequest")
    req.Format    = "Csv"
    req.ReportName = f"30-Day Campaign Performance"
    req.ReturnOnlyCompleteData = False

    agg = svc.factory.create("ReportAggregation")
    req.Aggregation = agg.Daily

    scope = svc.factory.create("AccountThroughCampaignReportScope")
    scope.AccountIds = {"long": [ACCOUNT_ID]}
    req.Scope = scope

    time_obj = svc.factory.create("ReportTime")
    sd = svc.factory.create("Date")
    sd.Day, sd.Month, sd.Year = start_date.day, start_date.month, start_date.year
    ed = svc.factory.create("Date")
    ed.Day, ed.Month, ed.Year = end_date.day, end_date.month, end_date.year
    time_obj.CustomDateRangeStart = sd
    time_obj.CustomDateRangeEnd   = ed
    time_obj.PredefinedTime       = None
    time_obj.ReportTimeZone       = "PacificTimeUSCanadaTijuana"
    req.Time = time_obj

    cols = svc.factory.create("ArrayOfCampaignPerformanceReportColumn")
    cols.CampaignPerformanceReportColumn = [
        "TimePeriod", "CampaignId", "CampaignName", "CampaignStatus",
        "Impressions", "Clicks", "Ctr", "AverageCpc",
        "Spend", "Conversions",
    ]
    req.Columns = cols

    logger.info("Submitting Microsoft Ads report request (%s to %s)...", start_date, end_date)
    submit_resp = svc.SubmitGenerateReport(req)
    report_id   = (submit_resp.ReportRequestId
                   if hasattr(submit_resp, "ReportRequestId")
                   else str(submit_resp).strip())
    logger.info("Report ID: %s — polling...", report_id)

    waited = 0
    poll_interval = 10
    download_url = None
    while waited < REPORT_TIMEOUT:
        time.sleep(poll_interval)
        waited += poll_interval
        status_resp = svc.PollGenerateReport(ReportRequestId=report_id)
        rrs    = (status_resp.ReportRequestStatus
                  if hasattr(status_resp, "ReportRequestStatus")
                  else status_resp)
        status = rrs.Status
        logger.info("  Report status after %ds: %s", waited, status)
        if status == "Success":
            download_url = rrs.ReportDownloadUrl
            break
        elif status in ("Error", "Failed"):
            logger.error("Report generation failed: %s", status)
            return None

    if not download_url:
        logger.warning("Report not ready within %ds — no data returned.", REPORT_TIMEOUT)
        return []

    logger.info("Downloading report...")
    req_dl = urllib.request.Request(download_url)
    with urllib.request.urlopen(req_dl, timeout=60) as resp:
        raw = resp.read()

    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        csv_data = z.read(z.namelist()[0]).decode("utf-8-sig")

    lines   = csv_data.splitlines()
    # Microsoft CSV has a header section before the data; find the row with "TimePeriod"
    header_idx = next(
        (i for i, line in enumerate(lines) if "TimePeriod" in line or "Time period" in line),
        None,
    )
    if header_idx is None:
        logger.warning("Could not find CSV header row in report")
        return []

    reader = csv.DictReader(lines[header_idx:])
    rows = [row for row in reader if row.get("TimePeriod") and row.get("CampaignId")]
    logger.info("Parsed %d data rows from report CSV", len(rows))
    return rows


def _fetch_keywords(auth_data, ag_id: int) -> list[dict]:
    """Fetch all keywords for a single Microsoft Ads ad group."""
    from bingads import ServiceClient
    try:
        svc = ServiceClient("CampaignManagementService", 13, auth_data, "production")
        resp = svc.GetKeywordsByAdGroupId(AdGroupId=ag_id)
        raw = (resp.Keyword.Keyword
               if resp.Keyword and hasattr(resp.Keyword, "Keyword")
               else list(resp.Keyword or []))
        results = []
        for kw in raw:
            if not hasattr(kw, "Id") or kw.Id is None:
                continue
            bid_usd = None
            try:
                if hasattr(kw, "Bid") and kw.Bid is not None and hasattr(kw.Bid, "Amount"):
                    bid_usd = float(kw.Bid.Amount) if kw.Bid.Amount is not None else None
            except Exception:
                pass
            results.append({
                "id":         int(kw.Id),
                "text":       str(kw.Text) if hasattr(kw, "Text") and kw.Text else "",
                "match_type": str(kw.MatchType) if hasattr(kw, "MatchType") else "Broad",
                "bid_usd":    bid_usd,
                "status":     str(kw.Status) if hasattr(kw, "Status") else "Active",
            })
        return results
    except Exception as e:
        logger.warning("GetKeywordsByAdGroupId failed for ag %d: %s", ag_id, e)
        return []


def _upsert_keyword(ag_db_id: int, msft_kw_id: int, text: str,
                    match_type: str, bid_usd: float | None, status: str) -> None:
    external_id   = f"msft_kw_{msft_kw_id}"
    bid_micros    = int(bid_usd * 1_000_000) if bid_usd is not None else None
    norm_status   = "ENABLED" if status.lower() in ("active", "enabled") else "PAUSED"
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO keywords
               (google_keyword_id, ad_group_id, keyword_text, match_type,
                status, cpc_bid_micros, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (google_keyword_id) DO UPDATE SET
                   keyword_text   = EXCLUDED.keyword_text,
                   match_type     = EXCLUDED.match_type,
                   status         = EXCLUDED.status,
                   cpc_bid_micros = COALESCE(EXCLUDED.cpc_bid_micros, keywords.cpc_bid_micros),
                   updated_at     = NOW()""",
            (external_id, ag_db_id, text, match_type.upper(), norm_status, bid_micros),
        )


def _scan_all_ad_groups(auth_data, campaign_db_map: dict[int, int]) -> dict[int, int]:
    """
    Walk ALL campaigns via GetCampaignsByAccountId and upsert every ad group.
    Returns {msft_ag_id: db_ad_group_id} covering all 18 campaigns, including
    those with zero impressions that never appear in performance reports.

    Builds its own full campaign list instead of relying on the report-based
    campaign_db_map (which only covers campaigns with recent activity).
    """
    from bingads import ServiceClient
    svc = ServiceClient("CampaignManagementService", 13, auth_data, "production")
    ag_db_map: dict[int, int] = {}

    # Get ALL campaigns from the account — not just those in the performance report
    try:
        camp_resp = svc.GetCampaignsByAccountId(AccountId=ACCOUNT_ID, CampaignType="Search")
        all_camps = (list(camp_resp.Campaign.Campaign)
                     if camp_resp.Campaign and hasattr(camp_resp.Campaign, "Campaign")
                     else list(camp_resp.Campaign or []))
    except Exception as e:
        logger.warning("GetCampaignsByAccountId in _scan_all_ad_groups failed: %s", e)
        # Fall back to whatever was passed in
        all_camps = []

    # Build a full campaign map, merging API results with the report-based map
    full_campaign_db_map: dict[int, int] = dict(campaign_db_map)  # copy
    for c in all_camps:
        if not hasattr(c, "Id") or c.Id is None:
            continue
        msft_cid = int(c.Id)
        if msft_cid not in full_campaign_db_map:
            # Campaign not yet in DB — upsert it
            c_name  = str(c.Name) if hasattr(c, "Name") and c.Name else str(msft_cid)
            c_status = str(c.Status) if hasattr(c, "Status") else "ENABLED"
            budget_usd = None
            try:
                if hasattr(c, "DailyBudget") and c.DailyBudget is not None:
                    budget_usd = float(c.DailyBudget)
                elif hasattr(c, "Budget") and c.Budget is not None and hasattr(c.Budget, "Amount"):
                    budget_usd = float(c.Budget.Amount) if c.Budget.Amount is not None else None
            except Exception:
                pass
            full_campaign_db_map[msft_cid] = _upsert_campaign(msft_cid, c_name, budget_usd, c_status)

    logger.info("Full ad group scan: walking %d campaign(s)", len(full_campaign_db_map))

    for msft_cid, camp_db_id in full_campaign_db_map.items():
        try:
            resp = svc.GetAdGroupsByCampaignId(CampaignId=msft_cid)
            raw  = (list(resp.AdGroup.AdGroup)
                    if resp.AdGroup and hasattr(resp.AdGroup, "AdGroup")
                    else list(resp.AdGroup or []))
            for ag in raw:
                if not hasattr(ag, "Id") or ag.Id is None:
                    continue
                msft_ag_id = int(ag.Id)
                ag_name    = str(ag.Name) if hasattr(ag, "Name") and ag.Name else str(msft_ag_id)
                ag_db_id   = _upsert_ad_group(camp_db_id, msft_ag_id, ag_name)
                ag_db_map[msft_ag_id] = ag_db_id
        except Exception as e:
            logger.warning("GetAdGroupsByCampaignId failed for campaign %d: %s", msft_cid, e)

    logger.info("Full ad group scan: found %d ad group(s) across %d campaign(s)",
                len(ag_db_map), len(full_campaign_db_map))
    return ag_db_map


def _sync_keywords(auth_data, ag_db_map: dict[int, int]) -> int:
    """
    Fetch keywords for every known Microsoft ad group and upsert into DB.
    ag_db_map: {msft_ag_id -> db ad_group id}
    Returns total keywords upserted.
    """
    total = 0
    for msft_ag_id, ag_db_id in ag_db_map.items():
        keywords = _fetch_keywords(auth_data, msft_ag_id)
        for kw in keywords:
            try:
                _upsert_keyword(
                    ag_db_id   = ag_db_id,
                    msft_kw_id = kw["id"],
                    text       = kw["text"],
                    match_type = kw["match_type"],
                    bid_usd    = kw["bid_usd"],
                    status     = kw["status"],
                )
                total += 1
            except Exception as e:
                logger.warning("Keyword upsert failed (ag=%d kw=%d): %s", msft_ag_id, kw["id"], e)
        if keywords:
            logger.info("  Ad group %d: synced %d keyword(s)", msft_ag_id, len(keywords))
    logger.info("Keyword sync complete — %d keywords upserted across %d ad groups", total, len(ag_db_map))
    return total


def _upsert_ad_group(campaign_db_id: int, msft_ag_id: int, name: str) -> int:
    external_id = f"msft_ag_{msft_ag_id}"
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO ad_groups
               (google_ad_group_id, campaign_id, name, status, cpc_bid_micros, updated_at)
               VALUES (%s, %s, %s, 'ENABLED', 2500000, NOW())
               ON CONFLICT (google_ad_group_id) DO UPDATE SET
                   name       = EXCLUDED.name,
                   updated_at = NOW()
               RETURNING id""",
            (external_id, campaign_db_id, name),
        )
        return cur.fetchone()["id"]


def _upsert_ag_metric(metric_date, ag_db_id: int, msft_ag_id: int,
                      impressions: int, clicks: int, conversions: float,
                      cost_micros: int, ctr: float, cpc_avg_micros: int):
    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO performance_metrics
               (metric_date, entity_type, entity_id, google_entity_id,
                impressions, clicks, conversions, cost_micros,
                ctr, cpc_avg_micros, platform)
               VALUES (%s,'ad_group',%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                   impressions    = EXCLUDED.impressions,
                   clicks         = EXCLUDED.clicks,
                   conversions    = EXCLUDED.conversions,
                   cost_micros    = EXCLUDED.cost_micros,
                   ctr            = EXCLUDED.ctr,
                   cpc_avg_micros = EXCLUDED.cpc_avg_micros,
                   platform       = EXCLUDED.platform""",
            (metric_date, ag_db_id, f"msft_ag_{msft_ag_id}",
             impressions, clicks, conversions, cost_micros,
             ctr, cpc_avg_micros, PLATFORM),
        )


def _submit_adgroup_report(auth_data, start_date: date, end_date: date) -> list[dict] | None:
    """Submit an AdGroupPerformanceReport and return parsed rows."""
    from bingads import ServiceClient

    svc = ServiceClient("ReportingService", 13, auth_data, "production")

    req = svc.factory.create("AdGroupPerformanceReportRequest")
    req.Format     = "Csv"
    req.ReportName = "30-Day AdGroup Performance"
    req.ReturnOnlyCompleteData = False

    agg = svc.factory.create("ReportAggregation")
    req.Aggregation = agg.Daily

    scope = svc.factory.create("AccountThroughAdGroupReportScope")
    scope.AccountIds = {"long": [ACCOUNT_ID]}
    req.Scope = scope

    time_obj = svc.factory.create("ReportTime")
    sd = svc.factory.create("Date")
    sd.Day, sd.Month, sd.Year = start_date.day, start_date.month, start_date.year
    ed = svc.factory.create("Date")
    ed.Day, ed.Month, ed.Year = end_date.day, end_date.month, end_date.year
    time_obj.CustomDateRangeStart = sd
    time_obj.CustomDateRangeEnd   = ed
    time_obj.PredefinedTime       = None
    time_obj.ReportTimeZone       = "PacificTimeUSCanadaTijuana"
    req.Time = time_obj

    cols = svc.factory.create("ArrayOfAdGroupPerformanceReportColumn")
    cols.AdGroupPerformanceReportColumn = [
        "TimePeriod", "CampaignId", "CampaignName",
        "AdGroupId", "AdGroupName",
        "Impressions", "Clicks", "Ctr", "AverageCpc",
        "Spend", "Conversions",
    ]
    req.Columns = cols

    logger.info("Submitting Microsoft ad group report (%s to %s)...", start_date, end_date)
    try:
        submit_resp = svc.SubmitGenerateReport(req)
        report_id   = (submit_resp.ReportRequestId
                       if hasattr(submit_resp, "ReportRequestId")
                       else str(submit_resp).strip())
        logger.info("Ad group report ID: %s — polling...", report_id)
    except Exception as e:
        logger.warning("Ad group report submit failed: %s", e)
        return None

    waited = 0
    poll_interval = 10
    download_url  = None
    while waited < REPORT_TIMEOUT:
        time.sleep(poll_interval)
        waited += poll_interval
        try:
            status_resp = svc.PollGenerateReport(ReportRequestId=report_id)
            rrs    = (status_resp.ReportRequestStatus
                      if hasattr(status_resp, "ReportRequestStatus")
                      else status_resp)
            status = rrs.Status
            logger.info("  Ad group report status after %ds: %s", waited, status)
            if status == "Success":
                download_url = rrs.ReportDownloadUrl
                break
            elif status in ("Error", "Failed"):
                logger.warning("Ad group report generation failed")
                return None
        except Exception as e:
            logger.warning("Poll error: %s", e)
            return None

    if not download_url:
        logger.warning("Ad group report not ready within %ds", REPORT_TIMEOUT)
        return []

    try:
        req_dl = urllib.request.Request(download_url)
        with urllib.request.urlopen(req_dl, timeout=60) as resp:
            raw = resp.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            csv_data = z.read(z.namelist()[0]).decode("utf-8-sig")
    except Exception as e:
        logger.warning("Ad group report download failed: %s", e)
        return None

    lines = csv_data.splitlines()
    header_idx = next(
        (i for i, line in enumerate(lines) if "TimePeriod" in line or "Time period" in line),
        None,
    )
    if header_idx is None:
        return []
    reader = csv.DictReader(lines[header_idx:])
    rows = [r for r in reader if r.get("TimePeriod") and r.get("AdGroupId")]
    logger.info("Parsed %d ad group report rows", len(rows))
    return rows


def run() -> dict:
    logger.info("=== Microsoft Sync starting (last %d days) ===", DAYS_BACK)
    db.heartbeat(AGENT_NAME, "alive")

    end_date   = date.today()
    start_date = end_date - timedelta(days=DAYS_BACK - 1)

    try:
        access_token, expires_in = _refresh_access_token()
    except Exception as e:
        logger.error("Token refresh failed: %s", e)
        db.heartbeat(AGENT_NAME, "error", error=str(e))
        return {"platform": PLATFORM, "status": "error", "error": str(e)}

    auth_data = _build_auth(access_token, expires_in)

    # Resolve customer ID
    customer_id = _resolve_customer_id(auth_data)
    if customer_id:
        auth_data.customer_id = customer_id
        logger.info("Customer ID resolved: %d", customer_id)

    # Pre-fetch campaign names
    campaign_names = _fetch_campaigns(auth_data)
    logger.info("Pre-fetched %d campaign name(s)", len(campaign_names))

    try:
        report_rows = _submit_and_download_report(auth_data, start_date, end_date)
    except Exception as e:
        logger.error("Report failed: %s", e)
        db.heartbeat(AGENT_NAME, "error", error=str(e))
        return {"platform": PLATFORM, "status": "error", "error": str(e)}

    if not report_rows:
        logger.info("No report rows returned — upserting campaign metadata only.")
        for cid, info in campaign_names.items():
            name       = info.get("name", str(cid)) if isinstance(info, dict) else info
            budget_usd = info.get("budget_usd") if isinstance(info, dict) else None
            status_val = info.get("status", "ENABLED") if isinstance(info, dict) else "ENABLED"
            _upsert_campaign(cid, name, budget_usd, status_val)
        db.heartbeat(AGENT_NAME, "success", metadata={"rows_written": 0, "campaigns_synced": len(campaign_names)})
        return {
            "platform": PLATFORM, "status": "success",
            "campaigns_synced": len(campaign_names), "rows_written": 0,
            "date_range": f"{start_date} to {end_date}",
        }

    campaign_db_map: dict[int, int] = {}
    rows_written = 0
    errors = []

    for row in report_rows:
        try:
            cid_raw = row.get("CampaignId", "").strip()
            if not cid_raw or not cid_raw.isdigit():
                continue
            cid = int(cid_raw)

            # Upsert campaign
            if cid not in campaign_db_map:
                camp_info = campaign_names.get(cid, {})
                name       = camp_info.get("name", row.get("CampaignName", str(cid))) if isinstance(camp_info, dict) else camp_info
                budget_usd = camp_info.get("budget_usd") if isinstance(camp_info, dict) else None
                status_val = camp_info.get("status", "ENABLED") if isinstance(camp_info, dict) else "ENABLED"
                campaign_db_map[cid] = _upsert_campaign(cid, name, budget_usd, status_val)

            # Parse metrics — Microsoft CSV uses commas in numbers; strip them
            def _num(s):
                return s.replace(",", "").strip() if s else "0"

            impressions = int(_num(row.get("Impressions", "0")))
            clicks      = int(_num(row.get("Clicks", "0")))
            spend_usd   = float(_num(row.get("Spend", "0")))
            cost_micros = int(spend_usd * 1_000_000)
            ctr_str     = _num(row.get("Ctr", "0%")).replace("%", "")
            ctr         = round(float(ctr_str) / 100, 6)
            cpc_usd     = float(_num(row.get("AverageCpc", "0")))
            cpc_micros  = int(cpc_usd * 1_000_000)
            conversions = float(_num(row.get("Conversions", "0")))

            # TimePeriod format: MM/DD/YYYY or YYYY-MM-DD
            time_period = row["TimePeriod"].strip()
            if "/" in time_period:
                parts = time_period.split("/")
                metric_date = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            else:
                metric_date = time_period[:10]

            _upsert_metric(
                metric_date    = metric_date,
                entity_id      = campaign_db_map[cid],
                external_id    = f"msft_{cid}",
                impressions    = impressions,
                clicks         = clicks,
                conversions    = conversions,
                cost_micros    = cost_micros,
                ctr            = ctr,
                cpc_avg_micros = cpc_micros,
            )
            rows_written += 1
        except Exception as e:
            errors.append(str(e))
            logger.warning("Row error: %s", e)

    # ── Ad group level sync ───────────────────────────────────────────────
    ag_rows_written = 0
    ag_db_map: dict[int, int] = {}
    try:
        ag_report_rows = _submit_adgroup_report(auth_data, start_date, end_date)
        if ag_report_rows:
            def _num(s):
                return s.replace(",", "").strip() if s else "0"

            for row in ag_report_rows:
                try:
                    cid_raw  = row.get("CampaignId", "").strip()
                    agid_raw = row.get("AdGroupId", "").strip()
                    if not cid_raw.isdigit() or not agid_raw.isdigit():
                        continue
                    cid  = int(cid_raw)
                    agid = int(agid_raw)

                    # Resolve campaign DB id
                    camp_db_id = campaign_db_map.get(cid)
                    if camp_db_id is None:
                        camp_info  = campaign_names.get(cid, {})
                        ag_name_c  = camp_info.get("name", row.get("CampaignName", str(cid))) if isinstance(camp_info, dict) else row.get("CampaignName", str(cid))
                        budget_usd = camp_info.get("budget_usd") if isinstance(camp_info, dict) else None
                        status_val = camp_info.get("status", "ENABLED") if isinstance(camp_info, dict) else "ENABLED"
                        camp_db_id = _upsert_campaign(cid, ag_name_c, budget_usd, status_val)
                        campaign_db_map[cid] = camp_db_id

                    # Upsert ad group
                    if agid not in ag_db_map:
                        ag_name = row.get("AdGroupName", str(agid))
                        ag_db_map[agid] = _upsert_ad_group(camp_db_id, agid, ag_name)

                    impressions = int(_num(row.get("Impressions", "0")))
                    clicks      = int(_num(row.get("Clicks", "0")))
                    spend_usd   = float(_num(row.get("Spend", "0")))
                    cost_micros = int(spend_usd * 1_000_000)
                    ctr_str     = _num(row.get("Ctr", "0%")).replace("%", "")
                    ctr         = round(float(ctr_str) / 100, 6)
                    cpc_usd     = float(_num(row.get("AverageCpc", "0")))
                    cpc_micros  = int(cpc_usd * 1_000_000)
                    conversions = float(_num(row.get("Conversions", "0")))

                    time_period = row["TimePeriod"].strip()
                    if "/" in time_period:
                        parts = time_period.split("/")
                        metric_date = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                    else:
                        metric_date = time_period[:10]

                    _upsert_ag_metric(
                        metric_date    = metric_date,
                        ag_db_id       = ag_db_map[agid],
                        msft_ag_id     = agid,
                        impressions    = impressions,
                        clicks         = clicks,
                        conversions    = conversions,
                        cost_micros    = cost_micros,
                        ctr            = ctr,
                        cpc_avg_micros = cpc_micros,
                    )
                    ag_rows_written += 1
                except Exception as e:
                    logger.warning("Ad group row error: %s", e)
    except Exception as e:
        logger.warning("Ad group sync failed (non-fatal): %s", e)

    logger.info("Ad group sync: %d ad groups, %d rows written",
                len(ag_db_map), ag_rows_written)

    # ── Full ad group scan (catches campaigns with 0 impressions) ─────────
    # The performance report only returns ad groups that have activity.
    # This API walk ensures every ad group and keyword is in the DB
    # regardless of spend/impression history.
    try:
        full_ag_map = _scan_all_ad_groups(auth_data, campaign_db_map)
        # Merge: report-based entries take precedence (they have perf data);
        # API-scan entries fill in the gaps.
        for msft_ag_id, ag_db_id in full_ag_map.items():
            if msft_ag_id not in ag_db_map:
                ag_db_map[msft_ag_id] = ag_db_id
        logger.info("ag_db_map after full scan: %d ad groups total", len(ag_db_map))
    except Exception as e:
        logger.warning("Full ad group scan failed (non-fatal): %s", e)

    # ── Keyword sync ──────────────────────────────────────────────────────
    keywords_synced = 0
    if ag_db_map:
        try:
            keywords_synced = _sync_keywords(auth_data, ag_db_map)
        except Exception as e:
            logger.warning("Keyword sync failed (non-fatal): %s", e)

    status = "error" if errors and rows_written == 0 else "success"
    db.heartbeat(AGENT_NAME, status, metadata={
        "rows_written":     rows_written,
        "ag_rows_written":  ag_rows_written,
        "keywords_synced":  keywords_synced,
        "campaigns_synced": len(campaign_db_map),
        "ad_groups_synced": len(ag_db_map),
        "date_range":       f"{start_date} to {end_date}",
    })
    logger.info(
        "=== Microsoft Sync done — campaigns=%d ad_groups=%d keywords=%d camp_rows=%d ag_rows=%d errors=%d ===",
        len(campaign_db_map), len(ag_db_map), keywords_synced, rows_written, ag_rows_written, len(errors),
    )
    return {
        "platform":         PLATFORM,
        "status":           status,
        "campaigns_synced": len(campaign_db_map),
        "ad_groups_synced": len(ag_db_map),
        "keywords_synced":  keywords_synced,
        "rows_written":     rows_written,
        "ag_rows_written":  ag_rows_written,
        "date_range":       f"{start_date} to {end_date}",
        "errors":           errors,
    }


if __name__ == "__main__":
    import json
    result = run()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["status"] == "success" else 1)
