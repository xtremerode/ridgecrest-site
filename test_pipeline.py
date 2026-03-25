#!/usr/bin/env python3
"""
test_pipeline.py
================
Ridgecrest Designs — End-to-end pipeline test harness.

Seeds PostgreSQL with 7 days of mock Google Search campaign data across
3 campaigns, then runs each agent in sequence and prints findings + a
pass/fail summary for each component.

No live Google Ads API calls are made — agents degrade gracefully when
the Google Ads client is unavailable (client=None).

The Anthropic API IS called for:
  • creative_agent  — generates 3 kitchen-remodel ad copy variations
  • reporting_agent — Claude-narrated daily Markdown report

Usage:
    python3 test_pipeline.py
"""

import os
import sys
import json
import random
import traceback
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import db
import performance_analyst
import bid_budget_optimizer
import reporting_agent
from creative_agent import (
    generate_creative_brief,
    validate_brief,
    store_brief,
    SERVICE_CATEGORIES,
)
import anthropic

# ─────────────────────────────────────────────────────────────────────────────
# Globals
# ─────────────────────────────────────────────────────────────────────────────
BANNER = "=" * 70
THIN   = "-" * 70
random.seed(42)

TODAY        = date.today()
DATE_WINDOW  = [TODAY - timedelta(days=i) for i in range(6, -1, -1)]  # oldest → newest
ACTIVE_DAYS  = {"friday", "saturday", "sunday", "monday"}
ACTIVE_IN_WINDOW = [d for d in DATE_WINDOW if d.strftime("%A").lower() in ACTIVE_DAYS]
N_ACTIVE     = len(ACTIVE_IN_WINDOW)

RESULTS: dict[str, str] = {
    "1_database_seed":        "NOT RUN",
    "2_performance_analyst":  "NOT RUN",
    "3_bid_budget_optimizer": "NOT RUN",
    "4_creative_agent":       "NOT RUN",
    "5_reporting_agent":      "NOT RUN",
}

# ─────────────────────────────────────────────────────────────────────────────
# Mock data definitions
# ─────────────────────────────────────────────────────────────────────────────

# 3 campaigns — strong, average, underperformer
# Metric ranges per spec: impressions 200–800/day, CTR 3–6%, CPC $8–$18,
# conversions 0–3/day, spend capped at per-campaign budget (total ≤ $125/day).
MOCK_CAMPAIGNS = [
    {
        "google_id":  "TEST_CAMP_001",
        "name":       "Kitchen Remodel — Pleasanton",
        "category":   "kitchen_remodel",
        "budget_usd": 45.0,
        # Strong performer: higher impressions, best CTR, lowest CPC
        "impr_range": (400, 800),
        "ctr_range":  (0.045, 0.060),
        "cpc_range":  (8.0, 12.0),
        # Conversions indexed by active-day slot (cycles if window > len)
        "conv_seq":   [1, 2, 1, 0],
    },
    {
        "google_id":  "TEST_CAMP_002",
        "name":       "Design Build — Danville",
        "category":   "design_build",
        "budget_usd": 45.0,
        # Average performer: mid-range impressions, moderate CTR/CPC
        "impr_range": (280, 600),
        "ctr_range":  (0.035, 0.055),
        "cpc_range":  (10.0, 15.0),
        "conv_seq":   [0, 1, 0, 1],
    },
    {
        "google_id":  "TEST_CAMP_003",
        "name":       "Whole House Remodel — Walnut Creek",
        "category":   "whole_house_remodel",
        "budget_usd": 35.0,
        # Underperformer: lower impressions, weak CTR, highest CPC
        "impr_range": (200, 450),
        "ctr_range":  (0.030, 0.050),
        "cpc_range":  (13.0, 18.0),
        "conv_seq":   [0, 0, 0, 0],   # zero conversions → triggers optimizer alert
    },
]

# Keyword performance profiles (totals across active days in the 7-day window).
# Designed to exercise each optimizer decision path.
# CPC bids and spend reflect the $8–$18 CPC range specified for this test.
#
# Columns: google_id_prefix, text, match, bid_usd, total_clicks, total_conv, total_spend_usd
# Expected optimizer actions annotated below:
MOCK_KEYWORDS = [
    # ── Campaign 1: Kitchen Remodel ──────────────────────────────────────────
    # CPL = $240/4.0 = $60  → bid_increase  (< $300 ideal)
    ("TEST_CAMP_001", "kitchen remodel pleasanton",        "EXACT",  10.00, 24, 4.0,  240.0),
    # CPL = $240/1.0 = $240 → bid_increase  (< $300 ideal)
    ("TEST_CAMP_001", "kitchen remodel pleasanton",        "PHRASE", 12.00, 20, 1.0,  240.0),
    # CPL = $330/0.2 = $1650 → bid_decrease (> $500 target max)
    ("TEST_CAMP_001", "luxury kitchen remodel pleasanton", "EXACT",  15.00, 22, 0.2,  330.0),

    # ── Campaign 2: Design Build ─────────────────────────────────────────────
    # CPL = $336/2.0 = $168 → bid_increase  (< $300 ideal)
    ("TEST_CAMP_002", "design build danville",             "EXACT",  12.00, 28, 2.0,  336.0),
    # 0 conv, $180 > $30    → pause keyword
    ("TEST_CAMP_002", "design build danville",             "PHRASE",  9.00, 20, 0.0,  180.0),
    # 12 clicks < 20 threshold → NO ACTION
    ("TEST_CAMP_002", "design build contractor danville",  "EXACT",  11.00, 12, 0.0,  132.0),

    # ── Campaign 3: Whole House Remodel ──────────────────────────────────────
    # CPL = $260/1.0 = $260 → bid_increase  (< $300 ideal)
    ("TEST_CAMP_003", "whole house remodel walnut creek",  "EXACT",  13.00, 20, 1.0,  260.0),
    # 0 conv, $176 > $30    → pause keyword
    ("TEST_CAMP_003", "whole house remodel walnut creek",  "PHRASE",  9.00, 22, 0.0,  176.0),
    # 10 clicks < 20 threshold → NO ACTION
    ("TEST_CAMP_003", "home renovation walnut creek",      "EXACT",  10.00, 10, 0.0,  100.0),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def section(title: str) -> None:
    print(f"\n{BANNER}")
    print(f"  {title}")
    print(BANNER)


def sub(msg: str) -> None:
    print(f"  {msg}")


def _distribute_int(total: int, n: int) -> list[int]:
    """Split an integer total into n roughly equal random parts."""
    if n == 0 or total == 0:
        return [0] * max(n, 0)
    weights = [random.uniform(0.7, 1.3) for _ in range(n)]
    w_sum = sum(weights)
    parts = [int(total * w / w_sum) for w in weights]
    # Correct rounding drift
    diff = total - sum(parts)
    for i in range(abs(diff)):
        parts[i % n] += 1 if diff > 0 else -1
    return parts


def _distribute_float(total: float, n: int) -> list[float]:
    """Split a float total into n roughly equal random parts."""
    if n == 0 or total == 0.0:
        return [0.0] * max(n, 0)
    weights = [random.uniform(0.7, 1.3) for _ in range(n)]
    w_sum = sum(weights)
    parts = [round(total * w / w_sum, 4) for w in weights]
    # Fix rounding drift on last element
    parts[-1] = round(total - sum(parts[:-1]), 4)
    return parts


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Seed Database
# ─────────────────────────────────────────────────────────────────────────────

def cleanup_test_data() -> None:
    """Remove all rows inserted by previous test runs (TEST_CAMP_* prefix)."""
    with db.get_db() as (conn, cur):
        cur.execute(
            "SELECT id FROM campaigns WHERE google_campaign_id LIKE 'TEST_CAMP_%'"
        )
        camp_ids = [r["id"] for r in cur.fetchall()]

        if camp_ids:
            # Keyword IDs (for keyword metrics)
            cur.execute(
                """SELECT k.id FROM keywords k
                   JOIN ad_groups ag ON ag.id = k.ad_group_id
                   WHERE ag.campaign_id = ANY(%s)""",
                (camp_ids,)
            )
            kw_ids = [r["id"] for r in cur.fetchall()]

            if kw_ids:
                cur.execute(
                    "DELETE FROM performance_metrics "
                    "WHERE entity_type='keyword' AND entity_id = ANY(%s)",
                    (kw_ids,)
                )

            cur.execute(
                "DELETE FROM performance_metrics "
                "WHERE entity_type='campaign' AND entity_id = ANY(%s)",
                (camp_ids,)
            )

            # CASCADE handles ad_groups / keywords / ads
            cur.execute(
                "DELETE FROM campaigns WHERE id = ANY(%s)",
                (camp_ids,)
            )


def seed_campaigns() -> dict[str, int]:
    """Insert mock campaigns; return {google_id: db_id}."""
    camp_db_ids: dict[str, int] = {}
    for c in MOCK_CAMPAIGNS:
        with db.get_db() as (conn, cur):
            cur.execute(
                """INSERT INTO campaigns
                       (google_campaign_id, name, status, service_category,
                        daily_budget_micros, bidding_strategy)
                   VALUES (%s, %s, 'ENABLED', %s, %s, 'MANUAL_CPC')
                   ON CONFLICT (google_campaign_id) DO UPDATE SET
                       name=EXCLUDED.name,
                       status='ENABLED',
                       daily_budget_micros=EXCLUDED.daily_budget_micros,
                       updated_at=NOW()
                   RETURNING id""",
                (c["google_id"], c["name"], c["category"],
                 int(c["budget_usd"] * 1_000_000))
            )
            camp_db_ids[c["google_id"]] = cur.fetchone()["id"]
    return camp_db_ids


def seed_ad_groups(camp_db_ids: dict[str, int]) -> dict[tuple, int]:
    """2 ad groups per campaign (Exact / Phrase). Returns {(google_id, suffix): db_id}."""
    ag_db_ids: dict[tuple, int] = {}
    for c in MOCK_CAMPAIGNS:
        cid = camp_db_ids[c["google_id"]]
        for suffix, label in [("A", "Exact Match"), ("B", "Phrase Match")]:
            ag_gid = f"{c['google_id']}_AG_{suffix}"
            with db.get_db() as (conn, cur):
                cur.execute(
                    """INSERT INTO ad_groups
                           (google_ad_group_id, campaign_id, name, status, cpc_bid_micros)
                       VALUES (%s, %s, %s, 'ENABLED', %s)
                       ON CONFLICT (google_ad_group_id) DO UPDATE SET
                           name=EXCLUDED.name, updated_at=NOW()
                       RETURNING id""",
                    (ag_gid, cid, f"{c['name']} — {label}", 10_000_000)
                )
                ag_db_ids[(c["google_id"], suffix)] = cur.fetchone()["id"]
    return ag_db_ids


def seed_keywords(ag_db_ids: dict[tuple, int]) -> dict[str, int]:
    """Insert keywords; return {google_keyword_id: db_id}."""
    kw_db_ids: dict[str, int] = {}
    kw_counter: dict[str, int] = {}  # per campaign count

    for (camp_gid, kw_text, match_type, bid_usd, *_) in MOCK_KEYWORDS:
        idx = kw_counter.get(camp_gid, 0) + 1
        kw_counter[camp_gid] = idx
        ag_suffix = "A" if match_type == "EXACT" else "B"
        ag_db_id = ag_db_ids[(camp_gid, ag_suffix)]
        kw_gid = f"{camp_gid}_KW_{idx:02d}"

        with db.get_db() as (conn, cur):
            cur.execute(
                """INSERT INTO keywords
                       (google_keyword_id, ad_group_id, keyword_text, match_type,
                        status, cpc_bid_micros, quality_score)
                   VALUES (%s, %s, %s, %s, 'ENABLED', %s, %s)
                   ON CONFLICT (google_keyword_id) DO UPDATE SET
                       cpc_bid_micros=EXCLUDED.cpc_bid_micros,
                       updated_at=NOW()
                   RETURNING id""",
                (kw_gid, ag_db_id, kw_text, match_type,
                 int(bid_usd * 1_000_000), random.randint(4, 8))
            )
            kw_db_ids[kw_gid] = cur.fetchone()["id"]

    return kw_db_ids


def seed_campaign_metrics(camp_db_ids: dict[str, int]) -> None:
    """7 days × 3 campaigns of campaign-level performance metrics."""
    for day_idx, day in enumerate(DATE_WINDOW):
        day_name = day.strftime("%A").lower()
        is_active = day_name in ACTIVE_DAYS

        for c in MOCK_CAMPAIGNS:
            cid = camp_db_ids[c["google_id"]]

            if not is_active:
                impressions = clicks = cost_micros = 0
                conversions = 0.0
                ctr = cpc_avg = 0.0
                cpa_micros = None
                conv_rate = 0.0
            else:
                active_slot = sum(
                    1 for d in DATE_WINDOW[:day_idx]
                    if d.strftime("%A").lower() in ACTIVE_DAYS
                )
                impressions = random.randint(*c["impr_range"])
                ctr = random.uniform(*c["ctr_range"])
                clicks = max(1, int(impressions * ctr))
                cpc_usd = random.uniform(*c["cpc_range"])
                spend_usd = min(clicks * cpc_usd, c["budget_usd"])
                cost_micros = int(spend_usd * 1_000_000)
                conversions = float(c["conv_seq"][active_slot % len(c["conv_seq"])])
                ctr = clicks / impressions
                cpc_avg = int(cost_micros / clicks) if clicks > 0 else 0
                cpa_micros = int(cost_micros / conversions) if conversions > 0 else None
                conv_rate = conversions / clicks if clicks > 0 else 0.0

            with db.get_db() as (conn, cur):
                cur.execute(
                    """INSERT INTO performance_metrics
                           (metric_date, entity_type, entity_id, google_entity_id,
                            impressions, clicks, conversions, cost_micros,
                            ctr, cpc_avg_micros, cpa_micros, conversion_rate)
                       VALUES (%s,'campaign',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                           impressions=EXCLUDED.impressions,
                           clicks=EXCLUDED.clicks,
                           conversions=EXCLUDED.conversions,
                           cost_micros=EXCLUDED.cost_micros,
                           ctr=EXCLUDED.ctr,
                           cpc_avg_micros=EXCLUDED.cpc_avg_micros,
                           cpa_micros=EXCLUDED.cpa_micros,
                           conversion_rate=EXCLUDED.conversion_rate""",
                    (day, cid, c["google_id"],
                     impressions, clicks, conversions, cost_micros,
                     round(ctr, 4), cpc_avg, cpa_micros, round(conv_rate, 4))
                )


def seed_keyword_metrics(kw_db_ids: dict[str, int]) -> None:
    """Distribute keyword totals across active days in the window."""
    if N_ACTIVE == 0:
        sub("WARNING: No active days in 7-day window — keyword metrics not seeded.")
        return

    kw_counter: dict[str, int] = {}
    for (camp_gid, kw_text, match_type, bid_usd,
         total_clicks, total_conv, total_spend_usd) in MOCK_KEYWORDS:
        idx = kw_counter.get(camp_gid, 0) + 1
        kw_counter[camp_gid] = idx
        kw_gid = f"{camp_gid}_KW_{idx:02d}"
        kw_db_id = kw_db_ids.get(kw_gid)
        if kw_db_id is None:
            continue

        # Distribute totals across active days
        click_parts   = _distribute_int(total_clicks, N_ACTIVE)
        spend_parts   = _distribute_float(total_spend_usd, N_ACTIVE)
        conv_parts    = _distribute_float(total_conv, N_ACTIVE)

        for i, day in enumerate(ACTIVE_IN_WINDOW):
            clicks     = max(1, click_parts[i])
            spend_usd  = max(0.0, spend_parts[i])
            conversions = max(0.0, conv_parts[i])
            cost_micros = int(spend_usd * 1_000_000)
            impressions = max(clicks, int(clicks / max(0.01, random.uniform(0.03, 0.06))))
            ctr         = clicks / impressions if impressions > 0 else 0.04
            cpc_avg     = int(cost_micros / clicks) if clicks > 0 else 0
            cpa_micros  = int(cost_micros / conversions) if conversions > 0 else None
            conv_rate   = conversions / clicks if clicks > 0 else 0.0

            with db.get_db() as (conn, cur):
                cur.execute(
                    """INSERT INTO performance_metrics
                           (metric_date, entity_type, entity_id, google_entity_id,
                            impressions, clicks, conversions, cost_micros,
                            ctr, cpc_avg_micros, cpa_micros, conversion_rate)
                       VALUES (%s,'keyword',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (metric_date, entity_type, entity_id) DO UPDATE SET
                           impressions=EXCLUDED.impressions,
                           clicks=EXCLUDED.clicks,
                           conversions=EXCLUDED.conversions,
                           cost_micros=EXCLUDED.cost_micros,
                           ctr=EXCLUDED.ctr,
                           cpc_avg_micros=EXCLUDED.cpc_avg_micros,
                           cpa_micros=EXCLUDED.cpa_micros,
                           conversion_rate=EXCLUDED.conversion_rate""",
                    (day, kw_db_id, kw_gid,
                     impressions, clicks, round(conversions, 4), cost_micros,
                     round(ctr, 4), cpc_avg, cpa_micros, round(conv_rate, 4))
                )


def step_seed_database() -> None:
    section("STEP 1 — SEEDING DATABASE")
    try:
        cleanup_test_data()
        sub("Cleaned up prior test data.")

        camp_db_ids = seed_campaigns()
        sub(f"{len(MOCK_CAMPAIGNS)} campaigns inserted.")

        ag_db_ids = seed_ad_groups(camp_db_ids)
        sub(f"{len(MOCK_CAMPAIGNS) * 2} ad groups inserted.")

        kw_db_ids = seed_keywords(ag_db_ids)
        sub(f"{len(MOCK_KEYWORDS)} keywords inserted.")

        seed_campaign_metrics(camp_db_ids)
        sub(f"Campaign metrics: {len(DATE_WINDOW)} days × {len(MOCK_CAMPAIGNS)} campaigns "
            f"= {len(DATE_WINDOW) * len(MOCK_CAMPAIGNS)} rows "
            f"({N_ACTIVE} active days, {len(DATE_WINDOW) - N_ACTIVE} inactive/zero).")

        seed_keyword_metrics(kw_db_ids)
        sub(f"Keyword metrics: {len(MOCK_KEYWORDS)} keywords × {N_ACTIVE} active days "
            f"= {len(MOCK_KEYWORDS) * N_ACTIVE} rows.")

        print()
        print("  Campaign summary:")
        for c in MOCK_CAMPAIGNS:
            print(f"    • {c['name']}  (${c['budget_usd']:.0f}/day budget)")

        print()
        print("  7-day window:")
        for d in DATE_WINDOW:
            flag = "ACTIVE  " if d.strftime("%A").lower() in ACTIVE_DAYS else "inactive"
            print(f"    {d}  {d.strftime('%A'):<9}  [{flag}]")

        RESULTS["1_database_seed"] = "PASS"

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        traceback.print_exc()
        RESULTS["1_database_seed"] = f"FAIL — {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Performance Analyst
# ─────────────────────────────────────────────────────────────────────────────

def step_performance_analyst() -> None:
    section("STEP 2 — PERFORMANCE ANALYST")
    sub("Running performance_analyst.run() against seeded data …")
    sub("(Google Ads client will be unavailable; agent falls back to DB.)\n")
    try:
        analysis = performance_analyst.run()

        print()
        print(f"  Report date : {analysis['report_date']}")
        print(f"  Today spend : ${analysis['today_spend']:.2f}")
        print(f"  Budget left : ${analysis['budget_remaining']:.2f}")

        s7 = analysis["summary_7d"]
        print(f"\n  7-Day Summary:")
        print(f"    Impressions  : {int(s7.get('total_impressions') or 0):,}")
        print(f"    Clicks       : {int(s7.get('total_clicks') or 0):,}")
        print(f"    Conversions  : {float(s7.get('total_conversions') or 0):.1f}")
        print(f"    Spend        : ${float(s7.get('total_spend') or 0):.2f}")
        print(f"    Avg CPC      : ${float(s7.get('avg_cpc') or 0):.2f}")
        cpl = s7.get("cpl")
        print(f"    CPL          : {'$' + f'{float(cpl):.2f}' if cpl else 'N/A (no conversions)'}")

        print(f"\n  Campaign Breakdown (today):")
        if analysis["campaign_breakdown"]:
            for c in analysis["campaign_breakdown"]:
                cost = float(c.get("cost_usd") or 0)
                conv = float(c.get("conversions") or 0)
                cpa  = float(c.get("cpa_usd") or 0) if c.get("cpa_usd") else 0
                print(f"    • {c['name'][:40]:<40}  "
                      f"spend=${cost:.2f}  conv={conv:.1f}  "
                      f"CPA={'$'+f'{cpa:.0f}' if cpa else '—'}")
        else:
            print("    (no campaign data for today — inactive day)")

        print(f"\n  Alerts detected: {analysis['alert_count']}")
        for alert in analysis["alerts"]:
            severity = alert.get("severity", "info").upper()
            print(f"    [{severity}] {alert['message']}")

        if analysis["critical_alerts"]:
            print(f"\n  CRITICAL alerts: {len(analysis['critical_alerts'])}")
            for ca in analysis["critical_alerts"]:
                print(f"    ⚠  {ca['message']}")

        RESULTS["2_performance_analyst"] = "PASS"

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        traceback.print_exc()
        RESULTS["2_performance_analyst"] = f"FAIL — {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Bid / Budget Optimizer (dry-run)
# ─────────────────────────────────────────────────────────────────────────────

def step_optimizer() -> None:
    section("STEP 3 — BID / BUDGET OPTIMIZER  (dry-run — no Google Ads writes)")
    sub("Running bid_budget_optimizer.run(force=True) …")
    sub("force=True bypasses cooldown for test; client=None skips Google Ads mutations.\n")
    try:
        result = bid_budget_optimizer.run(force=True)

        print(f"  Schedule changes : {result['schedule_changes']}")
        print(f"  Bid actions      : {result['bid_actions']}")
        print(f"  Budget actions   : {result['budget_actions']}")

        bid_changes = result["details"]["bid_changes"]
        if bid_changes:
            print(f"\n  Keyword bid recommendations ({len(bid_changes)}):")
            for bc in bid_changes:
                applied = "applied" if bc["applied"] else "dry-run (no client)"
                before  = f"${bc['before_bid_usd']:.2f}" if bc["before_bid_usd"] else "—"
                after   = f"${bc['after_bid_usd']:.2f}" if bc["after_bid_usd"] else "PAUSE"
                print(f"    [{bc['action_type'].upper():<14}]  "
                      f"'{bc['keyword']}'  ({bc['match_type']})  "
                      f"{before} → {after}")
                print(f"      Reason: {bc['reason']}")
        else:
            print("  No keyword bid changes recommended.")

        budget_changes = result["details"]["budget_changes"]
        if budget_changes:
            print(f"\n  Budget reallocation recommendations ({len(budget_changes)}):")
            for bc in budget_changes:
                applied = "applied" if bc["applied"] else "dry-run (no client)"
                print(f"    • {bc['campaign']:<42} "
                      f"${bc['old_budget_usd']:.2f} → ${bc['new_budget_usd']:.2f}  [{applied}]")
        else:
            print("  No budget reallocations recommended.")

        RESULTS["3_bid_budget_optimizer"] = "PASS"

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        traceback.print_exc()
        RESULTS["3_bid_budget_optimizer"] = f"FAIL — {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Creative Agent (3 ad copy variations)
# ─────────────────────────────────────────────────────────────────────────────

CREATIVE_BRIEF = {
    "service_category": "kitchen_remodel",
    "city":             "Pleasanton",
    "service_info":     SERVICE_CATEGORIES["kitchen_remodel"],
}

def step_creative_agent() -> None:
    section("STEP 4 — CREATIVE AGENT  (3 kitchen-remodel ad copy variations)")
    sub(f"Service   : {CREATIVE_BRIEF['service_info']['label']}")
    sub(f"City      : {CREATIVE_BRIEF['city']}")
    sub(f"Budget floor : {CREATIVE_BRIEF['service_info']['budget_floor']}")
    sub("Calling Claude claude-sonnet-4-6 three times …\n")

    try:
        claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        svc    = CREATIVE_BRIEF["service_info"]
        city   = CREATIVE_BRIEF["city"]
        cat    = CREATIVE_BRIEF["service_category"]

        variations = []
        for i in range(1, 4):
            sub(f"Generating variation {i}/3 …")
            brief  = generate_creative_brief(cat, city, svc, claude)
            errors = validate_brief(brief)
            bid    = store_brief(brief, cat)
            variations.append({
                "variation":   i,
                "brief_id":    bid,
                "brief":       brief,
                "errors":      errors,
            })

        print()
        for v in variations:
            brief = v["brief"]
            print(f"  {THIN}")
            print(f"  Variation {v['variation']}  (brief_id={v['brief_id']})")
            print(f"  Messaging angle: {brief.get('messaging_angle', 'N/A')}")

            print(f"\n  Headlines ({len(brief.get('headlines', []))} options):")
            for h in brief.get("headlines", []):
                flag = f"  ⚠ {len(h)} chars" if len(h) > 30 else ""
                print(f"    [{len(h):2d}] {h}{flag}")

            print(f"\n  Descriptions ({len(brief.get('descriptions', []))} options):")
            for d in brief.get("descriptions", []):
                flag = f"  ⚠ {len(d)} chars" if len(d) > 90 else ""
                print(f"    [{len(d):2d}] {d}{flag}")

            print(f"\n  Callout Extensions ({len(brief.get('callout_extensions', []))}):")
            for co in brief.get("callout_extensions", []):
                flag = f"  ⚠" if len(co) > 25 else ""
                print(f"    • {co}{flag}")

            if v["errors"]:
                print(f"\n  Validation warnings ({len(v['errors'])}):")
                for err in v["errors"]:
                    print(f"    ⚠ {err}")
            else:
                print(f"\n  Validation: all character limits OK ✓")

        print(f"\n  {THIN}")
        all_valid = all(len(v["errors"]) == 0 for v in variations)
        print(f"  Generated {len(variations)} variations — "
              f"{'all passed' if all_valid else 'some have warnings'} validation.")

        RESULTS["4_creative_agent"] = "PASS"

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        traceback.print_exc()
        RESULTS["4_creative_agent"] = f"FAIL — {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Reporting Agent
# ─────────────────────────────────────────────────────────────────────────────

def step_reporting_agent() -> None:
    section("STEP 5 — REPORTING AGENT  (Claude-narrated daily Markdown report)")
    sub("Running reporting_agent.run(report_type='daily', use_claude=True) …\n")
    try:
        result = reporting_agent.run(report_type="daily", use_claude=True)

        print()
        print(f"  Report stored   : id={result.get('report_id')}  "
              f"type={result.get('report_type')}  date={result.get('date')}")

        RESULTS["5_reporting_agent"] = "PASS"

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        traceback.print_exc()
        RESULTS["5_reporting_agent"] = f"FAIL — {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Pass / Fail Summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary() -> None:
    section("FINAL PASS / FAIL SUMMARY")
    labels = {
        "1_database_seed":        "Database Seed",
        "2_performance_analyst":  "Performance Analyst",
        "3_bid_budget_optimizer": "Bid / Budget Optimizer",
        "4_creative_agent":       "Creative Agent",
        "5_reporting_agent":      "Reporting Agent",
    }
    passed = 0
    failed = 0
    for key in sorted(RESULTS):
        status = RESULTS[key]
        icon   = "✅" if status == "PASS" else "❌"
        label  = labels.get(key, key)
        detail = "" if status == "PASS" else f"  → {status}"
        print(f"  {icon}  {label:<28} {detail}")
        if status == "PASS":
            passed += 1
        else:
            failed += 1

    print()
    print(f"  {THIN}")
    print(f"  Result: {passed}/{passed+failed} components passed")
    if failed == 0:
        print("  All pipeline components are operational.")
    else:
        print(f"  {failed} component(s) need attention — see errors above.")
    print(f"  {BANNER}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{BANNER}")
    print("  RIDGECREST DESIGNS — MARKETING PIPELINE TEST")
    print(f"  Run date   : {TODAY}  ({TODAY.strftime('%A')})")
    print(f"  DB URL     : {os.getenv('DATABASE_URL', '(not set)')}")
    print(f"  Active window days: {N_ACTIVE}/7  "
          f"({', '.join(d.strftime('%a %m/%d') for d in ACTIVE_IN_WINDOW) or 'none'})")
    print(BANNER)

    step_seed_database()
    step_performance_analyst()
    step_optimizer()
    step_creative_agent()
    step_reporting_agent()
    print_summary()


if __name__ == "__main__":
    main()
