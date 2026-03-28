#!/usr/bin/env python3
"""
Meta Ads — Test Campaign / Ad Set / Ad Creator
===============================================
Creates a paused test campaign, ad set, and ad for Ridgecrest Designs.
Nothing is activated. Prints IDs for verification.

Run:  python meta_create_test.py
"""

import json
import os
import sys
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv("/root/agent/.env")

ACCESS_TOKEN  = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"]   # act_58393749 (Ridgecrest Designs 1)
API_VERSION   = "v21.0"
BASE_URL      = f"https://graph.facebook.com/{API_VERSION}"

# Landing page per CLAUDE.md §9
LANDING_PAGE_URL = "https://go.ridgecrestdesigns.com"


def _get(path: str, params: dict = None) -> dict:
    p = {"access_token": ACCESS_TOKEN}
    if params:
        p.update(params)
    r = requests.get(f"{BASE_URL}{path}", params=p, timeout=30)
    return r.json()


def _post(path: str, data: dict) -> dict:
    data["access_token"] = ACCESS_TOKEN
    r = requests.post(f"{BASE_URL}{path}", data=data, timeout=30)
    return r.json()


# ---------------------------------------------------------------------------
# Step 1 — Campaign
# ---------------------------------------------------------------------------

def create_campaign() -> str:
    print("\n[1] Creating test campaign …")
    resp = _post(f"/{AD_ACCOUNT_ID}/campaigns", {
        "name":      "[RMA TEST] Design Build — Ridgecrest Designs",
        "objective": "OUTCOME_LEADS",
        "status":    "PAUSED",
        "special_ad_categories":          json.dumps([]),
        "is_adset_budget_sharing_enabled": "false",   # budget set at ad-set level
    })
    if "error" in resp:
        print(f"  ERROR: {resp['error'].get('message', resp['error'])}")
        sys.exit(1)
    cid = resp["id"]
    print(f"  Campaign created  id={cid}  status=PAUSED")
    return cid


# ---------------------------------------------------------------------------
# Step 2 — Ad Set
# ---------------------------------------------------------------------------

def create_adset(campaign_id: str) -> str:
    print("\n[2] Creating test ad set …")

    # Targeting: 17 zip codes from CLAUDE.md §12
    zip_codes = [
        "94506", "94507", "94526", "94528", "94549",
        "94556", "94563", "94566", "94568", "94582",
        "94583", "94586", "94588", "94595", "94596",
        "94597", "94598",
    ]
    # Advantage+ audience (default for OUTCOME_LEADS) caps age_min at 25.
    # Target by zip code only; age skew comes from creative messaging.
    targeting = {
        "geo_locations": {
            "zips": [{"key": f"US:{z}"} for z in zip_codes],
        },
    }

    start = date.today().isoformat()
    end   = (date.today() + timedelta(days=30)).isoformat()

    resp = _post(f"/{AD_ACCOUNT_ID}/adsets", {
        "name":                "[RMA TEST] Design Build — Walnut Creek + East Bay",
        "campaign_id":         campaign_id,
        "status":              "PAUSED",
        "optimization_goal":   "LEAD_GENERATION",
        "billing_event":       "IMPRESSIONS",
        "bid_amount":          1000,          # $10.00 CPM floor (cents)
        "daily_budget":        12500,         # $125.00 (cents)
        "start_time":          f"{start}T00:00:00-0700",
        "end_time":            f"{end}T23:59:59-0700",
        "targeting":           json.dumps(targeting),
    })
    if "error" in resp:
        print(f"  ERROR: {resp['error'].get('message', resp['error'])}")
        sys.exit(1)
    asid = resp["id"]
    print(f"  Ad set created    id={asid}  status=PAUSED  budget=$125/day")
    return asid


# ---------------------------------------------------------------------------
# Step 3 — Ad Creative + Ad
# ---------------------------------------------------------------------------

def create_ad(adset_id: str) -> str:
    print("\n[3] Creating test ad creative …")

    # Link ad (no image required for a test — uses link preview)
    creative_data = {
        "name": "[RMA TEST] Design Build Creative",
        "object_story_spec": json.dumps({
            "page_id": _get_page_id(),
            "link_data": {
                "link":        LANDING_PAGE_URL,
                "message":     (
                    "Ridgecrest Designs — Luxury Design-Build for the East Bay. "
                    "Photo-realistic renders. Seamless permitting. "
                    "Premium homes from vision to completion."
                ),
                "name":        "Luxury Design-Build | Ridgecrest Designs",
                "description": (
                    "Serving Pleasanton, Walnut Creek, Danville & the East Bay. "
                    "Custom homes starting at $5M. Inquire today."
                ),
                "call_to_action": {
                    "type":  "LEARN_MORE",
                    "value": {"link": LANDING_PAGE_URL},
                },
            },
        }),
    }

    cr = _post(f"/{AD_ACCOUNT_ID}/adcreatives", creative_data)
    if "error" in cr:
        print(f"  Creative ERROR: {cr['error'].get('message', cr['error'])}")
        sys.exit(1)
    crid = cr["id"]
    print(f"  Creative created  id={crid}")

    print("\n[4] Creating test ad …")
    ad_resp = _post(f"/{AD_ACCOUNT_ID}/ads", {
        "name":        "[RMA TEST] Design Build — Ad 1",
        "adset_id":    adset_id,
        "creative":    json.dumps({"creative_id": crid}),
        "status":      "PAUSED",
    })
    if "error" in ad_resp:
        print(f"  Ad ERROR: {ad_resp['error'].get('message', ad_resp['error'])}")
        sys.exit(1)
    ad_id = ad_resp["id"]
    print(f"  Ad created        id={ad_id}  status=PAUSED")
    return ad_id


def _get_page_id() -> str:
    """Fetch the first Facebook Page connected to this ad account."""
    resp = _get(f"/{AD_ACCOUNT_ID}", {"fields": "promotable_objects"})
    pages = (resp.get("promotable_objects") or {}).get("data", [])
    if pages:
        return pages[0]["id"]
    # Fallback: fetch pages directly
    resp2 = _get("/me/accounts", {"fields": "id,name"})
    items = resp2.get("data", [])
    if items:
        return items[0]["id"]
    print("  ERROR: Could not find a Facebook Page connected to this account.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify(campaign_id: str, adset_id: str, ad_id: str):
    print("\n[5] Verifying hierarchy …")

    c = _get(f"/{campaign_id}", {"fields": "id,name,status,objective"})
    a = _get(f"/{adset_id}",    {"fields": "id,name,status,daily_budget"})
    d = _get(f"/{ad_id}",       {"fields": "id,name,status"})

    print(f"\n  Campaign:  [{c['id']}] {c['name']}")
    print(f"             status={c['status']}  objective={c['objective']}")

    budget_usd = int(a.get("daily_budget", 0)) / 100
    print(f"\n  Ad Set:    [{a['id']}] {a['name']}")
    print(f"             status={a['status']}  daily_budget=${budget_usd:.2f}")

    print(f"\n  Ad:        [{d['id']}] {d['name']}")
    print(f"             status={d['status']}")

    all_paused = all(
        x.get("status") == "PAUSED"
        for x in [c, a, d]
    )
    print(f"\n  All paused: {'YES ✓' if all_paused else 'NO — check statuses above'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Meta Ads — Test Hierarchy Creation")
    print(f"Account: {AD_ACCOUNT_ID}")
    print("All entities will be created with status=PAUSED")
    print("=" * 60)

    campaign_id = create_campaign()
    adset_id    = create_adset(campaign_id)
    ad_id       = create_ad(adset_id)

    verify(campaign_id, adset_id, ad_id)

    print("\n" + "=" * 60)
    print("DONE — IDs for reference:")
    print(f"  Campaign ID:  {campaign_id}")
    print(f"  Ad Set ID:    {adset_id}")
    print(f"  Ad ID:        {ad_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
