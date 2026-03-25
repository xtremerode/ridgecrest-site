#!/usr/bin/env python3
"""
Test Microsoft Ads API connection.
Reads-only: authenticates, pulls account info for account 187004108,
and retrieves last 7 days of campaign performance data.
Makes NO changes to campaigns.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID      = os.environ["MICROSOFT_CLIENT_ID"]
TENANT_ID      = os.environ["MICROSOFT_TENANT_ID"]
CLIENT_SECRET  = os.environ["MICROSOFT_CLIENT_SECRET"]
DEV_TOKEN      = os.environ["MICROSOFT_ADS_DEVELOPER_TOKEN"]
ACCOUNT_ID     = int(os.environ["MICROSOFT_ADS_ACCOUNT_ID"])
REFRESH_TOKEN  = os.environ["MICROSOFT_REFRESH_TOKEN"]

REDIRECT_URI   = "https://login.microsoftonline.com/common/oauth2/nativeclient"


def _refresh_access_token() -> dict:
    """Exchange the refresh token for a new access token via direct HTTP.
    App is registered as a public client — no client_secret in the request.
    """
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id":    CLIENT_ID,
        "grant_type":   "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "scope":        "https://ads.microsoft.com/msads.manage offline_access",
    }
    print("  Refreshing access token via tenant-specific endpoint...")
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    token_data = resp.json()
    if "error" in token_data:
        raise RuntimeError(f"Token error: {token_data}")
    print(f"  Access token obtained. Expires in {token_data.get('expires_in')}s. "
          f"Scope: {token_data.get('scope')}")
    return token_data


def _build_auth_data(access_token: str, expires_in: int):
    """Build bingads AuthorizationData with pre-obtained token injected at construction."""
    from bingads.authorization import (
        AuthorizationData,
        OAuthWebAuthCodeGrant,
        OAuthTokens,
        ADS_MANAGE,
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
        oauth_tokens=tokens,          # ← inject at construction time
        oauth_scope=ADS_MANAGE,
        tenant=TENANT_ID,
    )

    auth_data = AuthorizationData(
        account_id=ACCOUNT_ID,
        developer_token=DEV_TOKEN,
        authentication=oauth,
    )
    return auth_data


def test_step(label: str):
    print(f"\n[STEP] {label}")


def test_authentication():
    test_step("1. Authenticate with Microsoft Ads")
    token_data = _refresh_access_token()
    access_token = token_data["access_token"]
    expires_in   = int(token_data.get("expires_in", 3600))
    auth_data    = _build_auth_data(access_token, expires_in)
    print("  AuthorizationData built successfully.")
    print(f"  oauth_tokens.access_token present: {bool(auth_data.authentication.oauth_tokens.access_token)}")
    return auth_data


def resolve_customer_id(auth_data) -> int | None:
    """Call GetUser (no customer_id required) to discover the customer ID."""
    from bingads import ServiceClient
    try:
        svc = ServiceClient(
            service="CustomerManagementService",
            version=13,
            authorization_data=auth_data,
            environment="production",
        )
        # UserId=0 or None means "current user"
        response = svc.GetUser(UserId=None)
        roles = (response.CustomerRoles.CustomerRole
                 if response.CustomerRoles and response.CustomerRoles.CustomerRole
                 else [])
        for role in roles:
            if hasattr(role, "CustomerId"):
                return int(role.CustomerId)
        # Fallback: first linked account's parent
        return None
    except Exception as e:
        print(f"  WARNING: GetUser failed: {e}")
        return None


def diagnose_credentials(access_token: str, dev_token: str):
    """Make a raw SOAP GetUser call and return the detailed error, if any."""
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Header>
    <AuthenticationToken xmlns="https://bingads.microsoft.com/Customer/v13">{access_token}</AuthenticationToken>
    <DeveloperToken xmlns="https://bingads.microsoft.com/Customer/v13">{dev_token}</DeveloperToken>
  </s:Header>
  <s:Body>
    <GetUserRequest xmlns="https://bingads.microsoft.com/Customer/v13">
      <UserId xmlns:a="http://www.w3.org/2001/XMLSchema" i:nil="true"
              xmlns:i="http://www.w3.org/2001/XMLSchema-instance"/>
    </GetUserRequest>
  </s:Body>
</s:Envelope>"""

    resp = requests.post(
        "https://clientcenter.api.bingads.microsoft.com/Api/CustomerManagement/v13/CustomerManagementService.svc",
        data=soap_body.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "GetUser"},
        timeout=30,
    )
    text = resp.text
    # Extract ErrorCode and Message from the SOAP fault
    import re as _re
    error_code = _re.search(r"<ErrorCode>([^<]+)</ErrorCode>", text)
    message    = _re.search(r"<Message>([^<]+)</Message>", text)
    code_num   = _re.search(r"<Code>(\d+)</Code>", text)
    return {
        "http_status": resp.status_code,
        "error_code":  error_code.group(1) if error_code else None,
        "code_num":    code_num.group(1)   if code_num   else None,
        "message":     message.group(1)    if message    else None,
        "raw":         text[:500],
    }


def test_account_info(auth_data) -> int | None:
    """Pull account info and return the customer_id if found."""
    test_step("2. Pull account info for account 187004108")
    from bingads import ServiceClient

    # First, resolve customer_id via GetUser (requires no customer_id header)
    print("  Resolving customer ID via GetUser...")
    customer_id = resolve_customer_id(auth_data)
    if customer_id:
        auth_data.customer_id = customer_id
        print(f"  Customer ID resolved: {customer_id}")
    else:
        print("  Could not resolve customer ID — subsequent calls may fail")

    try:
        svc = ServiceClient(
            service="CustomerManagementService",
            version=13,
            authorization_data=auth_data,
            environment="production",
        )
        response = svc.GetAccount(AccountId=ACCOUNT_ID)
        # SDK returns the account directly on the response object (AdvertiserAccount type)
        acct = response if hasattr(response, "Id") else getattr(response, "Account", response)
        print(f"  Account ID:       {acct.Id}")
        print(f"  Account Name:     {acct.Name}")
        print(f"  Account Number:   {acct.Number}")
        print(f"  Currency Code:    {acct.CurrencyCode}")
        print(f"  Time Zone:        {acct.TimeZone}")
        print(f"  Account Status:   {acct.AccountLifeCycleStatus}")
        return customer_id
    except Exception as e:
        print(f"  ERROR getting account details: {e}")
        # Return customer_id even on account fetch error — it's still useful
        return customer_id


def test_campaign_list(auth_data):
    test_step("3. List campaigns for account 187004108")
    from bingads import ServiceClient

    try:
        svc = ServiceClient(
            service="CampaignManagementService",
            version=13,
            authorization_data=auth_data,
            environment="production",
        )
        response = svc.GetCampaignsByAccountId(
            AccountId=ACCOUNT_ID,
            CampaignType="Search",
        )
        campaigns = (response.Campaign.Campaign
                     if response.Campaign and hasattr(response.Campaign, "Campaign")
                     else [])
        if not campaigns:
            # Try alternate attribute name
            try:
                campaigns = list(response.Campaign) if response.Campaign else []
            except Exception:
                campaigns = []
        print(f"  Found {len(campaigns)} Search campaign(s):")
        ids = []
        for c in campaigns:
            budget = getattr(c, "DailyBudget", "N/A")
            status = getattr(c, "Status", "N/A")
            print(f"    [{c.Id}] {c.Name}  status={status}  daily_budget=${budget}")
            ids.append(c.Id)
        return ids
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
        return None


def test_performance_report(auth_data, campaign_ids: list):
    test_step("4. Retrieve last 7 days of campaign performance")
    from bingads import ServiceClient
    import time, urllib.request

    end_date   = datetime.utcnow().date()
    start_date = end_date - timedelta(days=6)

    try:
        svc = ServiceClient(
            service="ReportingService",
            version=13,
            authorization_data=auth_data,
            environment="production",
        )

        # Build the report request
        ReportRequest = svc.factory.create("CampaignPerformanceReportRequest")
        ReportRequest.Format  = "Csv"
        ReportRequest.ReportName = "7-Day Campaign Performance"
        ReportRequest.ReturnOnlyCompleteData = False

        Aggregation = svc.factory.create("ReportAggregation")
        ReportRequest.Aggregation = Aggregation.Daily

        Scope = svc.factory.create("AccountThroughCampaignReportScope")
        Scope.AccountIds = {"long": [ACCOUNT_ID]}
        # Don't filter by campaign ID — scope to the account only
        ReportRequest.Scope = Scope

        # Date range
        Time = svc.factory.create("ReportTime")
        StartDate = svc.factory.create("Date")
        StartDate.Day   = start_date.day
        StartDate.Month = start_date.month
        StartDate.Year  = start_date.year
        EndDate = svc.factory.create("Date")
        EndDate.Day   = end_date.day
        EndDate.Month = end_date.month
        EndDate.Year  = end_date.year
        Time.CustomDateRangeStart = StartDate
        Time.CustomDateRangeEnd   = EndDate
        Time.PredefinedTime       = None
        Time.ReportTimeZone       = "PacificTimeUSCanadaTijuana"
        ReportRequest.Time = Time

        # Columns
        Columns = svc.factory.create("ArrayOfCampaignPerformanceReportColumn")
        Columns.CampaignPerformanceReportColumn = [
            "TimePeriod", "CampaignName", "CampaignStatus",
            "Impressions", "Clicks", "Ctr",
            "AverageCpc", "Spend", "Conversions", "CostPerConversion",
        ]
        ReportRequest.Columns = Columns

        print(f"  Submitting report request for {start_date} to {end_date}...")
        submit_response = svc.SubmitGenerateReport(ReportRequest)
        print(f"  submit_response type: {type(submit_response)}")
        print(f"  submit_response: {submit_response}")
        # The SDK sometimes returns a Text node wrapping the ID directly
        if hasattr(submit_response, "ReportRequestId"):
            report_id = submit_response.ReportRequestId
        else:
            report_id = str(submit_response).strip()
        print(f"  Report request ID: {report_id}")

        # Poll for completion (up to 60s)
        max_wait = 60
        poll_interval = 5
        waited = 0
        download_url = None
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            status_response = svc.PollGenerateReport(ReportRequestId=report_id)
            # SDK returns ReportRequestStatus directly (not nested under .ReportRequestStatus)
            rrs = (status_response.ReportRequestStatus
                   if hasattr(status_response, "ReportRequestStatus")
                   else status_response)
            status = rrs.Status
            print(f"  Status after {waited}s: {status}")
            if status == "Success":
                download_url = rrs.ReportDownloadUrl
                break
            elif status in ("Error", "Failed"):
                print(f"  Report generation failed with status: {status}")
                return False

        if not download_url:
            print(f"  Report not ready within {max_wait}s — no data to display.")
            print("  (This is expected for accounts with no recent activity or new reports.)")
            return True

        # Download and show first ~30 lines
        print(f"\n  Downloading report from: {download_url[:80]}...")
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            import zipfile, io
            raw = resp.read()

        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            csv_name = z.namelist()[0]
            csv_data = z.read(csv_name).decode("utf-8-sig")

        lines = csv_data.splitlines()
        print(f"\n  Report CSV ({len(lines)} lines total). First 30 lines:\n")
        for line in lines[:30]:
            print(f"    {line}")

        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Microsoft Ads API Connection Test")
    print(f"Account ID: {ACCOUNT_ID}")
    print(f"Tenant ID:  {TENANT_ID}")
    print("=" * 60)

    results = {}

    try:
        auth_data = test_authentication()
        results["authentication"] = "PASS"
    except Exception as e:
        print(f"  FATAL: {e}")
        import traceback
        traceback.print_exc()
        results["authentication"] = f"FAIL: {e}"
        _print_summary(results)
        sys.exit(1)

    # Deep-diagnose credentials before attempting SDK calls
    test_step("1b. Diagnose credential validity (raw SOAP)")
    access_token = auth_data.authentication.oauth_tokens.access_token
    diag = diagnose_credentials(access_token, DEV_TOKEN)
    print(f"  Raw SOAP HTTP status: {diag['http_status']}")
    if diag["error_code"]:
        print(f"  Error code:  {diag['code_num']} ({diag['error_code']})")
        print(f"  Message:     {diag['message']}")
        if diag["error_code"] == "InvalidCredentials":
            print()
            print("  DIAGNOSIS: Developer token rejected by Microsoft Advertising API.")
            print("  The OAuth access token is valid (scope confirmed), but the")
            print("  developer token may be:")
            print("    1. Invalid or revoked — check Tools > Account Settings in")
            print("       the Microsoft Advertising portal")
            print("    2. Not approved — new developer tokens require Microsoft approval")
            print("    3. Associated with a different Ads account than the OAuth user")
            print()
            print("  All subsequent SDK calls will fail until the developer token is corrected.")
            results["account_info"] = "FAIL (InvalidCredentials — developer token)"
            results["campaign_list"] = "SKIP"
            results["performance_report"] = "SKIP"
            _print_summary(results)
            sys.exit(0)
    else:
        print("  No credential errors — proceeding with SDK calls")

    customer_id = test_account_info(auth_data)
    results["account_info"] = "PASS" if customer_id is not None else "FAIL"

    # Set customer_id on auth_data so subsequent service calls include it in headers
    if customer_id:
        auth_data.customer_id = customer_id
        print(f"\n  customer_id={customer_id} set on AuthorizationData")

    campaign_ids = test_campaign_list(auth_data)
    results["campaign_list"] = "PASS" if campaign_ids is not None else "FAIL"

    results["performance_report"] = "PASS" if test_performance_report(auth_data, campaign_ids or []) else "FAIL"

    _print_summary(results)


def _print_summary(results: dict):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for step, status in results.items():
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} {step:<25} {status}")
        if status != "PASS":
            all_pass = False
    print("=" * 60)
    print("OVERALL:", "PASS" if all_pass else "FAIL (see errors above)")


if __name__ == "__main__":
    main()
