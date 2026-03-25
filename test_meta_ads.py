#!/usr/bin/env python3
"""
Test Meta Ads API connection.
Read-only: authenticates, pulls account info for act_658645131272143,
and retrieves last 7 days of campaign performance data.
Makes NO changes to campaigns.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv("/root/agent/.env")

ACCESS_TOKEN   = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID  = os.environ["META_AD_ACCOUNT_ID"]   # act_658645131272143
APP_ID         = os.environ["META_APP_ID"]
APP_SECRET     = os.environ["META_APP_SECRET"]

API_VERSION    = "v21.0"
BASE_URL       = f"https://graph.facebook.com/{API_VERSION}"

end_date   = datetime.now(timezone.utc).date()
start_date = end_date - timedelta(days=6)


def get(path: str, params: dict = None) -> dict:
    """GET request with token auth, raises on error."""
    p = {"access_token": ACCESS_TOKEN}
    if params:
        p.update(params)
    r = requests.get(f"{BASE_URL}{path}", params=p, timeout=30)
    return r.json()


def test_step(label: str):
    print(f"\n[STEP] {label}")


def ok(v) -> bool:
    return "error" not in v


# ── Step 1: Token inspection ─────────────────────────────────────────────────
def test_authentication():
    test_step("1. Authenticate — inspect access token")
    data = get("/debug_token", {
        "input_token":  ACCESS_TOKEN,
        "access_token": f"{APP_ID}|{APP_SECRET}",
    })

    if "error" in data:
        print(f"  ERROR: {data['error']}")
        return False

    info = data.get("data", {})
    app_name  = info.get("application", "unknown")
    token_type = info.get("type", "unknown")
    valid      = info.get("is_valid", False)
    scopes     = info.get("scopes", [])
    exp_ts     = info.get("expires_at", 0)
    exp_str    = (datetime.fromtimestamp(exp_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                  if exp_ts else "never / long-lived")

    print(f"  App:        {app_name} ({APP_ID})")
    print(f"  Token type: {token_type}")
    print(f"  Valid:      {valid}")
    print(f"  Expires:    {exp_str}")
    print(f"  Scopes:     {', '.join(scopes) if scopes else '(none listed)'}")

    # Check required scopes
    required = {"ads_read", "ads_management"}
    missing  = required - set(scopes)
    if missing:
        print(f"  WARNING: Missing scopes: {missing}")
    if not valid:
        print("  ERROR: Token is not valid.")
        return False
    print("  Token is valid.")
    return True


# ── Step 2: Account info ─────────────────────────────────────────────────────
def test_account_info():
    test_step("2. Pull account info for act_658645131272143")
    fields = "id,name,account_status,currency,timezone_name,spend_cap,balance,amount_spent,business"
    data = get(f"/{AD_ACCOUNT_ID}", {"fields": fields})

    if "error" in data:
        print(f"  ERROR {data['error'].get('code')}: {data['error'].get('message')}")
        return False

    status_map = {1: "Active", 2: "Disabled", 3: "Unsettled", 7: "Pending Review",
                  8: "Pending Closure", 9: "In Grace Period", 100: "Pending Closure",
                  101: "Closed", 201: "Any Active", 202: "Any Closed"}
    raw_status = data.get("account_status", "?")
    status_str = status_map.get(raw_status, str(raw_status))

    spent_cents = int(data.get("amount_spent", 0))
    print(f"  Account ID:    {data.get('id')}")
    print(f"  Account Name:  {data.get('name')}")
    print(f"  Status:        {status_str} ({raw_status})")
    print(f"  Currency:      {data.get('currency')}")
    print(f"  Timezone:      {data.get('timezone_name')}")
    print(f"  Amount Spent:  ${spent_cents / 100:,.2f} (lifetime)")
    biz = data.get("business", {})
    if biz:
        print(f"  Business:      {biz.get('name')} ({biz.get('id')})")
    return True


# ── Step 3: Campaign list ────────────────────────────────────────────────────
def test_campaign_list():
    test_step("3. List campaigns for act_658645131272143")
    fields = "id,name,status,objective,daily_budget,lifetime_budget,buying_type"
    data = get(f"/{AD_ACCOUNT_ID}/campaigns", {"fields": fields, "limit": 50})

    if "error" in data:
        print(f"  ERROR {data['error'].get('code')}: {data['error'].get('message')}")
        return []

    campaigns = data.get("data", [])
    print(f"  Found {len(campaigns)} campaign(s):")
    for c in campaigns:
        daily   = int(c.get("daily_budget", 0)) / 100 if c.get("daily_budget") else None
        lifetime = int(c.get("lifetime_budget", 0)) / 100 if c.get("lifetime_budget") else None
        budget_str = (f"daily=${daily:.2f}" if daily else
                      f"lifetime=${lifetime:.2f}" if lifetime else "no budget")
        print(f"    [{c['id']}] {c['name']}")
        print(f"             status={c.get('status')}  objective={c.get('objective')}  {budget_str}")
    return [c["id"] for c in campaigns]


# ── Step 4: 7-day performance ────────────────────────────────────────────────
def test_performance(campaign_ids: list):
    test_step(f"4. Retrieve {start_date} to {end_date} campaign performance (last 7 days)")

    fields = ",".join([
        "campaign_name", "campaign_id",
        "impressions", "clicks", "ctr",
        "cpc", "spend", "actions", "cost_per_action_type",
        "reach", "frequency",
    ])
    params = {
        "fields":     fields,
        "level":      "campaign",
        "time_range": json.dumps({"since": str(start_date), "until": str(end_date)}),
        "time_increment": 1,
        "limit":      200,
    }
    data = get(f"/{AD_ACCOUNT_ID}/insights", params)

    if "error" in data:
        print(f"  ERROR {data['error'].get('code')}: {data['error'].get('message')}")
        return False

    rows = data.get("data", [])
    if not rows:
        print("  No performance data returned for this period.")
        print("  (Campaigns may be paused or have had no spend in the last 7 days.)")
        return True

    # Aggregate by campaign
    from collections import defaultdict
    totals: dict = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "spend": 0.0,
        "conversions": 0, "name": "", "status": ""
    })
    for row in rows:
        cid  = row.get("campaign_id", "?")
        t    = totals[cid]
        t["name"]        = row.get("campaign_name", "?")
        t["status"]      = row.get("status", "?")
        t["impressions"] += int(row.get("impressions", 0))
        t["clicks"]      += int(row.get("clicks", 0))
        t["spend"]       += float(row.get("spend", 0))
        # Count lead/purchase/submit actions as conversions
        for action in row.get("actions", []):
            if action.get("action_type") in {
                "lead", "offsite_conversion.fb_pixel_lead",
                "offsite_conversion.fb_pixel_purchase",
                "submit_application",
            }:
                t["conversions"] += int(float(action.get("value", 0)))

    print(f"  Period: {start_date} → {end_date} ({len(rows)} daily rows)")
    print()
    print(f"  {'Campaign':<40} {'Impr':>7} {'Clicks':>6} {'CTR':>6} {'Spend':>8} {'Conv':>5}")
    print(f"  {'-'*40} {'-'*7} {'-'*6} {'-'*6} {'-'*8} {'-'*5}")

    total_spend = 0.0
    for cid, t in totals.items():
        ctr = (t["clicks"] / t["impressions"] * 100) if t["impressions"] else 0
        print(f"  {t['name'][:40]:<40} {t['impressions']:>7,} {t['clicks']:>6,} "
              f"{ctr:>5.2f}% ${t['spend']:>7.2f} {t['conversions']:>5}")
        total_spend += t["spend"]

    print(f"\n  Total spend (7d): ${total_spend:.2f}")
    return True


# ── Summary ──────────────────────────────────────────────────────────────────
def _print_summary(results: dict):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for step, status in results.items():
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} {step:<30} {status}")
        if status != "PASS":
            all_pass = False
    print("=" * 60)
    print("OVERALL:", "PASS" if all_pass else "FAIL (see errors above)")


def main():
    print("=" * 60)
    print("Meta Ads API Connection Test")
    print(f"Ad Account: {AD_ACCOUNT_ID}")
    print(f"API Version: {API_VERSION}")
    print("=" * 60)

    results = {}

    results["authentication"] = "PASS" if test_authentication() else "FAIL"
    results["account_info"]   = "PASS" if test_account_info()   else "FAIL"
    campaign_ids = test_campaign_list()
    results["campaign_list"]  = "PASS" if campaign_ids is not None else "FAIL"
    results["performance"]    = "PASS" if test_performance(campaign_ids or []) else "FAIL"

    _print_summary(results)


if __name__ == "__main__":
    main()
