#!/usr/bin/env python3
"""
Microsoft Ads — Apply Geo Targeting to All RMA Campaigns
=========================================================
Adds LocationCriterion for East Bay California cities AND zip codes
to all 18 [RMA] campaigns so ads only serve in the target service area.

Target locations per CLAUDE.md §12:
  Cities: Walnut Creek, Pleasanton, San Ramon, Dublin, Danville,
          Orinda, Lafayette, Moraga, Alamo, Diablo, Sunol
  Zip codes: 94596, 94595, 94588, 94586, 94583, 94582, 94568, 94566, 94563, 94556

Location IDs sourced from GetGeoLocationsFileUrl (CampaignManagementService).

Run:  python msft_apply_geo_targeting.py
"""

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

# Microsoft Ads Location IDs — downloaded via GetGeoLocationsFileUrl (GeoLocations.csv v2.0)
CITY_LOCATION_IDS = {
    "Walnut Creek": 43579,
    "Pleasanton":   43949,
    "San Ramon":    43577,
    "Dublin":       43559,
    "Danville":     43602,
    "Orinda":       43599,
    "Lafayette":    43565,
    "Moraga":       43592,
    "Alamo":        43553,
    "Diablo":       134599,
    "Sunol":        136213,
}

ZIP_LOCATION_IDS = {
    "94596": 87855,
    "94595": 87823,
    "94588": 87376,
    "94586": 86988,
    "94583": 87500,
    "94582": 87493,
    "94568": 87357,
    "94566": 87192,
    "94563": 87825,
    "94556": 87713,
}

# All location IDs to apply (cities + zip codes)
ALL_LOCATION_IDS = list(CITY_LOCATION_IDS.values()) + list(ZIP_LOCATION_IDS.values())


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


def _build_location_criterion(svc, camp_id: int, location_id: int):
    """Build a BiddableCampaignCriterion with LocationCriterion."""
    loc = svc.factory.create("LocationCriterion")
    loc.LocationId = location_id

    bcc = svc.factory.create("BiddableCampaignCriterion")
    bcc.CampaignId           = camp_id
    bcc.Type                 = "BiddableCampaignCriterion"
    bcc.Status               = "Active"
    bcc.Criterion            = loc
    bcc.CriterionCashback    = None
    bcc.ForwardCompatibilityMap = None

    bid = svc.factory.create("FixedBid")
    bid.Amount       = 0
    bcc.CriterionBid = bid
    return bcc


def apply_geo_targeting():
    print("Authenticating with Microsoft Ads...")
    access_token, expires_in = _refresh_token()
    auth = _build_auth(access_token, expires_in)
    print(f"  Auth OK (account {ACCOUNT_ID})")

    from bingads import ServiceClient
    svc = ServiceClient("CampaignManagementService", 13, auth, "production")

    campaigns = _get_rma_campaigns()
    print(f"\nFound {len(campaigns)} [RMA] campaigns in DB")
    print(f"Applying {len(ALL_LOCATION_IDS)} location targets:")
    print(f"  Cities ({len(CITY_LOCATION_IDS)}): {', '.join(CITY_LOCATION_IDS.keys())}")
    print(f"  Zip codes ({len(ZIP_LOCATION_IDS)}): {', '.join(ZIP_LOCATION_IDS.keys())}")
    print()

    applied = 0
    failed  = 0

    for camp in campaigns:
        msft_id = camp["msft_id"]
        name    = camp["name"]
        print(f"  [{msft_id}] {name}")

        criteria = [_build_location_criterion(svc, msft_id, loc_id)
                    for loc_id in ALL_LOCATION_IDS]

        try:
            result = svc.AddCampaignCriterions(
                CampaignCriterions={"CampaignCriterion": criteria},
                CriterionType="Targets",
            )
            # Check for partial errors
            partial_errors = getattr(result, "NestedPartialErrors", None) or \
                             getattr(result, "PartialErrors", None)
            if partial_errors:
                print(f"    ⚠ Applied with partial errors: {partial_errors}")
            else:
                print(f"    ✓ {len(ALL_LOCATION_IDS)} locations applied")
            applied += 1
        except Exception as e:
            print(f"    ✗ FAILED: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Geo targeting complete: {applied} campaigns updated, {failed} failed")
    return applied, failed


if __name__ == "__main__":
    applied, failed = apply_geo_targeting()
    sys.exit(0 if failed == 0 else 1)
