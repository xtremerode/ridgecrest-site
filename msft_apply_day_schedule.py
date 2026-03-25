#!/usr/bin/env python3
"""
Microsoft Ads — Apply Day Schedule to All RMA Campaigns
========================================================
SUPERSEDED: DayTimeCriterion bid modifiers are incompatible with
EnhancedCpc bidding (returns "Invalid client data" from Microsoft API).

Day scheduling is now handled in microsoft_manager.py via
_enforce_active_days(), which pauses/resumes campaigns by day of week
(same approach as meta_manager.py, per CLAUDE.md §8).

This file is kept for reference only. Do not run.
"""
raise SystemExit("Superseded — see microsoft_manager._enforce_active_days()")

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv("/root/agent/.env")

import db

ACCOUNT_ID    = int(os.getenv("MICROSOFT_ADS_ACCOUNT_ID", "187004108"))
CLIENT_ID     = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
TENANT_ID     = os.getenv("MICROSOFT_TENANT_ID", "")
DEV_TOKEN     = os.getenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "")
REFRESH_TOKEN = os.getenv("MICROSOFT_REFRESH_TOKEN", "")
REDIRECT_URI  = "https://login.microsoftonline.com/common/oauth2/nativeclient"

BLOCKED_DAYS = ["Tuesday", "Wednesday", "Thursday"]


def _refresh_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "client_id":     CLIENT_ID,
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "scope":         "https://ads.microsoft.com/msads.manage offline_access",
    }, timeout=30)
    resp.raise_for_status()
    td = resp.json()
    if "error" in td:
        raise RuntimeError(f"Token refresh failed: {td}")
    return td["access_token"], int(td.get("expires_in", 3600))


def _build_auth(access_token, expires_in):
    from bingads.authorization import (
        AuthorizationData, OAuthWebAuthCodeGrant, OAuthTokens, ADS_MANAGE,
    )
    tokens = OAuthTokens(
        access_token=access_token,
        access_token_expires_in_seconds=expires_in,
        refresh_token=REFRESH_TOKEN,
    )
    oauth = OAuthWebAuthCodeGrant(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        redirection_uri=REDIRECT_URI, oauth_tokens=tokens,
        oauth_scope=ADS_MANAGE, tenant=TENANT_ID,
    )
    auth = AuthorizationData(
        account_id=ACCOUNT_ID,
        developer_token=DEV_TOKEN,
        authentication=oauth,
    )
    from bingads import ServiceClient
    try:
        svc = ServiceClient("CustomerManagementService", 13, auth, "production")
        resp = svc.GetUser(UserId=None)
        roles = (resp.CustomerRoles.CustomerRole
                 if resp.CustomerRoles and resp.CustomerRoles.CustomerRole else [])
        for role in roles:
            if hasattr(role, "CustomerId"):
                auth.customer_id = int(role.CustomerId)
                break
    except Exception as e:
        print(f"  Warning: could not resolve customer ID: {e}")
    return auth


def _get_rma_campaigns():
    with db.get_db() as (conn, cur):
        cur.execute("""
            SELECT id, google_campaign_id, name, status
            FROM campaigns
            WHERE platform = 'microsoft_ads'
              AND managed_by = 'claude_code'
              AND name LIKE '[RMA]%%'
            ORDER BY name
        """)
        rows = []
        for r in cur.fetchall():
            msft_id_str = r["google_campaign_id"].replace("msft_", "")
            rows.append({
                "db_id":   r["id"],
                "name":    r["name"],
                "msft_id": int(msft_id_str),
            })
        return rows


def apply_day_schedule():
    print("Authenticating with Microsoft Ads...")
    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    print(f"  Auth OK (account {ACCOUNT_ID})")

    from bingads import ServiceClient
    svc = ServiceClient("CampaignManagementService", 13, auth, "production")

    campaigns = _get_rma_campaigns()
    print(f"\nFound {len(campaigns)} [RMA] campaigns in DB")
    print(f"Blocking days: {', '.join(BLOCKED_DAYS)} (-100% bid)\n")

    applied = 0
    failed  = 0

    for camp in campaigns:
        msft_id = camp["msft_id"]
        name    = camp["name"]
        print(f"  [{msft_id}] {name}")

        criteria = []
        for day in BLOCKED_DAYS:
            criterion = svc.factory.create("DayTimeCriterion")
            criterion.Day        = day
            criterion.FromHour   = 0
            criterion.ToHour     = 24
            criterion.FromMinute = "Zero"
            criterion.ToMinute   = "Zero"

            bcc = svc.factory.create("BiddableCampaignCriterion")
            bcc.CampaignId  = msft_id
            bcc.Type        = "BiddableCampaignCriterion"
            bcc.Status      = "Active"
            bcc.Criterion   = criterion

            bid_mul = svc.factory.create("BidMultiplier")
            bid_mul.Multiplier = -90   # Microsoft max reduction is -90%; closest to suppression
            bcc.CriterionBid = bid_mul

            criteria.append(bcc)

        try:
            svc.AddCampaignCriterions(
                CampaignCriterions={"CampaignCriterion": criteria},
                CriterionType="DayTime",
            )
            print(f"    ✓ Tue/Wed/Thu suppressed")
            applied += 1
        except Exception as e:
            print(f"    ✗ FAILED: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Day schedule complete: {applied} applied, {failed} failed")
    print(f"All successfully updated campaigns will only serve")
    print(f"on Friday, Saturday, Sunday, and Monday.")
    return applied, failed


if __name__ == "__main__":
    applied, failed = apply_day_schedule()
    sys.exit(0 if failed == 0 else 1)
