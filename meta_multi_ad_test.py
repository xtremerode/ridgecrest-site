#!/usr/bin/env python3
"""
Meta Ads — Multi-Ad Test Campaign Creator
==========================================
Creates one campaign, one ad set (saved audience, Advantage+ off),
and three ads with different copy angles for A/B testing.

All entities created as PAUSED. Nothing activated.

Run:  python meta_multi_ad_test.py

Saved audience: "refined location age and interest 2/26" (ID: 6934900931693)
  - Age 35–55, female, parents with children
  - 12 East Bay zip codes, home + recent location types
"""

import json
import os
import sys
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv("/root/agent/.env")

ACCESS_TOKEN    = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID   = os.environ["META_AD_ACCOUNT_ID"]  # act_58393749
API_VERSION     = "v21.0"
BASE_URL        = f"https://graph.facebook.com/{API_VERSION}"

LANDING_PAGE_URL   = "https://go.ridgecrestdesigns.com"
PAGE_ID            = "537283506373402"
SAVED_AUDIENCE_ID  = "6934900931693"   # refined location age and interest 2/26


def _fetch_saved_audience_targeting() -> dict:
    """
    Fetch the targeting spec from the saved audience and prepare it for ad set use.
    - Applies the saved audience's geo, gender, age, and interest targeting
    - Overrides age_min/age_max from the age_range field if present
    - Strips targeting_automation so we can disable Advantage+ at the ad set level
    """
    resp = _get(f"/{SAVED_AUDIENCE_ID}", {"fields": "name,targeting"})
    if "error" in resp:
        print(f"  ERROR fetching saved audience: {resp['error'].get('message', resp['error'])}")
        sys.exit(1)

    raw = resp["targeting"]
    print(f"  Saved audience: {resp['name']}")

    # Apply age_range override if present (age_min/age_max may reflect account defaults)
    age_range = raw.get("age_range", [])
    targeting = {k: v for k, v in raw.items() if k not in ("targeting_automation", "age_range")}
    if len(age_range) == 2:
        targeting["age_min"] = age_range[0]
        targeting["age_max"] = age_range[1]

    # Disable Advantage+ targeting expansion inside the targeting spec
    targeting["targeting_automation"] = {"advantage_audience": 0}

    return targeting


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

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


def _check(resp: dict, label: str) -> None:
    if "error" in resp:
        print(f"  ERROR ({label}): {resp['error'].get('message', resp['error'])}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1 — Campaign
# ---------------------------------------------------------------------------

def create_campaign() -> str:
    print("\n[1] Creating campaign …")
    resp = _post(f"/{AD_ACCOUNT_ID}/campaigns", {
        "name":                           "[RMA] Design Build — East Bay",
        "objective":                      "OUTCOME_LEADS",
        "status":                         "PAUSED",
        "special_ad_categories":          json.dumps([]),
        "is_adset_budget_sharing_enabled": "false",
    })
    _check(resp, "campaign")
    cid = resp["id"]
    print(f"  Campaign created  id={cid}  status=PAUSED")
    return cid


# ---------------------------------------------------------------------------
# Step 2 — Ad Set  (saved audience, Advantage+ disabled)
# ---------------------------------------------------------------------------

def create_adset(campaign_id: str) -> str:
    print("\n[2] Creating ad set …")

    print("  Fetching saved audience targeting spec …")
    targeting = _fetch_saved_audience_targeting()

    start = date.today().isoformat()
    end   = (date.today() + timedelta(days=60)).isoformat()

    resp = _post(f"/{AD_ACCOUNT_ID}/adsets", {
        "name":               "[RMA] Design Build — Saved Audience",
        "campaign_id":        campaign_id,
        "status":             "PAUSED",
        "optimization_goal":  "LEAD_GENERATION",
        "billing_event":      "IMPRESSIONS",
        "bid_strategy":       "LOWEST_COST_WITHOUT_CAP",
        "daily_budget":       12500,        # $125.00 in cents
        "start_time":         f"{start}T00:00:00-0700",
        "end_time":           f"{end}T23:59:59-0700",
        # Apply saved audience targeting spec directly
        # advantage_audience=0 is embedded inside targeting_automation within targeting
        "targeting":          json.dumps(targeting),
        # Required promoted object for OUTCOME_LEADS
        "promoted_object":    json.dumps({"page_id": PAGE_ID}),
    })
    _check(resp, "adset")
    asid = resp["id"]
    print(f"  Ad set created    id={asid}  status=PAUSED  budget=$125/day")
    return asid


# ---------------------------------------------------------------------------
# Step 3 — Ad Creatives + Ads  (three copy angles)
# ---------------------------------------------------------------------------

# Existing production creatives — generated by creative_agent.py
# Cannot create new creatives via API while Meta app is in development mode.
# These three span distinct copy angles for split-testing.
AD_VARIATIONS = [
    {
        "label":       "Mistake",
        "ad_name":     "[RMA] Design Build — Ad 1 Mistake Angle",
        "creative_id": "4355432118046631",   # "Don't Make This Costly Mistake"
    },
    {
        "label":       "Stress-Free",
        "ad_name":     "[RMA] Design Build — Ad 2 Stress-Free Angle",
        "creative_id": "2005383790405585",   # "Build a Custom Home Without the Stress!"
    },
    {
        "label":       "Errors",
        "ad_name":     "[RMA] Design Build — Ad 3 Errors Angle",
        "creative_id": "1852084575495268",   # "Avoid Thousands in Homebuilding Errors"
    },
]


def create_ad(adset_id: str, variation: dict) -> str:
    label = variation["label"]
    crid  = variation["creative_id"]
    print(f"\n  Attaching creative {crid} — {label} angle …")

    ad_resp = _post(f"/{AD_ACCOUNT_ID}/ads", {
        "name":     variation["ad_name"],
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": crid}),
        "status":   "PAUSED",
    })
    _check(ad_resp, f"ad-{label}")
    ad_id = ad_resp["id"]
    print(f"  Ad created        id={ad_id}  status=PAUSED  [{label}]")
    return ad_id


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify(campaign_id: str, adset_id: str, ad_ids: list[str]) -> None:
    print("\n[4] Verifying hierarchy …")

    c = _get(f"/{campaign_id}", {"fields": "id,name,status,objective"})
    a = _get(f"/{adset_id}",    {"fields": "id,name,status,daily_budget,targeting,advantage_audience"})

    print(f"\n  Campaign:  [{c['id']}] {c['name']}")
    print(f"             status={c['status']}  objective={c['objective']}")

    budget_usd = int(a.get("daily_budget", 0)) / 100
    adv = a.get("advantage_audience", "?")
    print(f"\n  Ad Set:    [{a['id']}] {a['name']}")
    print(f"             status={a['status']}  daily_budget=${budget_usd:.2f}  advantage_audience={adv}")

    print("\n  Ads:")
    all_paused = c.get("status") == "PAUSED" and a.get("status") == "PAUSED"
    for ad_id in ad_ids:
        d = _get(f"/{ad_id}", {"fields": "id,name,status"})
        paused = d.get("status") == "PAUSED"
        all_paused = all_paused and paused
        mark = "✓" if paused else "!"
        print(f"    [{d['id']}] {d['name']}  status={d['status']} {mark}")

    print(f"\n  All paused: {'YES ✓' if all_paused else 'NO — check statuses above'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("Meta Ads — Multi-Ad Test Campaign")
    print(f"Account:         {AD_ACCOUNT_ID}")
    print(f"Saved Audience:  {SAVED_AUDIENCE_ID}  (refined location age and interest 2/26)")
    print(f"Advantage+:      DISABLED")
    print(f"Ads to create:   {len(AD_VARIATIONS)}  ({', '.join(v['label'] for v in AD_VARIATIONS)})")
    print("All entities created as PAUSED")
    print("=" * 65)

    campaign_id = create_campaign()
    adset_id    = create_adset(campaign_id)

    print("\n[3] Creating ads …")
    ad_ids = []
    for variation in AD_VARIATIONS:
        ad_id = create_ad(adset_id, variation)
        ad_ids.append(ad_id)

    verify(campaign_id, adset_id, ad_ids)

    print("\n" + "=" * 65)
    print("DONE — IDs for reference:")
    print(f"  Campaign ID:  {campaign_id}")
    print(f"  Ad Set ID:    {adset_id}")
    for i, (ad_id, v) in enumerate(zip(ad_ids, AD_VARIATIONS), 1):
        print(f"  Ad {i} ({v['label']:8s}):  {ad_id}")
    print("=" * 65)
    print("\nNext steps:")
    print("  - Review ads in Meta Ads Manager")
    print("  - When ready to test, activate the campaign (status=ACTIVE)")
    print("  - meta_manager.py will enforce Fri/Sat/Sun/Mon active days automatically")


if __name__ == "__main__":
    main()
