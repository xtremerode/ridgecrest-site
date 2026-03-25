# Ridgecrest Designs — Lovable Frontend Reference

**Database:** `marketing_agent` on PostgreSQL (localhost:5432)
**Last updated:** 2026-03-20
**Purpose:** Complete reference for frontend developers and AI app builders. Every table, every column, every data type, with real sample data from the live database.

---

## Table of Contents

1. [Database Overview](#database-overview)
2. [Schema: campaigns](#table-campaigns)
3. [Schema: ad_groups](#table-ad_groups)
4. [Schema: keywords](#table-keywords)
5. [Schema: negative_keywords](#table-negative_keywords)
6. [Schema: ads](#table-ads)
7. [Schema: creative_briefs](#table-creative_briefs)
8. [Schema: performance_metrics](#table-performance_metrics)
9. [Schema: optimization_actions](#table-optimization_actions)
10. [Schema: reports](#table-reports)
11. [Schema: budget_snapshots](#table-budget_snapshots)
12. [Schema: agent_messages](#table-agent_messages) *(used as alerts)*
13. [Schema: agent_heartbeats](#table-agent_heartbeats)
14. [Schema: guardrail_violations](#table-guardrail_violations)
15. [Schema: geo_performance](#table-geo_performance)
16. [Schema: search_terms](#table-search_terms)
17. [Live Data Samples](#live-data-samples)
18. [Key Relationships](#key-relationships)
19. [Money / Units Reference](#money--units-reference)

---

## Database Overview

| Table | Rows | Purpose |
|---|---|---|
| `campaigns` | 3 | Google Ads campaigns |
| `ad_groups` | 6 | Ad groups inside campaigns |
| `keywords` | 9 | Active and paused keywords |
| `negative_keywords` | 21 | Account-level negative keyword list |
| `ads` | 0 | Responsive Search Ads (populated when live ads are synced) |
| `creative_briefs` | 6 | AI-generated ad copy briefs (headlines, descriptions, extensions) |
| `performance_metrics` | 57 | Daily metrics per campaign and keyword |
| `optimization_actions` | 36 | Proposed and applied bid/budget optimizer actions |
| `reports` | 4 | Daily and weekly performance reports (full markdown) |
| `budget_snapshots` | 2 | Daily budget pacing snapshots |
| `agent_messages` | 15 | Inter-agent messages (also carries alert payloads) |
| `agent_heartbeats` | 5 | Agent health and run status |
| `guardrail_violations` | 0 | Guardrail rule violation log |
| `geo_performance` | 0 | Geographic performance breakdown (populated when synced) |
| `search_terms` | 0 | Raw search term report (populated when synced) |

---

## Table: `campaigns`

The top-level entity. Each row is one Google Ads campaign.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `google_campaign_id` | varchar(50) | YES | — | Google Ads campaign ID (string) |
| `name` | varchar(255) | NOT NULL | — | Human-readable campaign name |
| `status` | varchar(20) | NOT NULL | `'ENABLED'` | `ENABLED` / `PAUSED` / `REMOVED` |
| `campaign_type` | varchar(50) | YES | `'SEARCH'` | Always `SEARCH` for now |
| `daily_budget_micros` | bigint | YES | `0` | Budget in micros (÷1,000,000 = USD) |
| `daily_budget_usd` | numeric | YES | — | Budget in USD (convenience field) |
| `bidding_strategy` | varchar(50) | YES | `'MANUAL_CPC'` | e.g. `MANUAL_CPC`, `TARGET_CPA` |
| `target_cpa_micros` | bigint | YES | — | Target CPA in micros (nullable) |
| `service_category` | varchar(80) | YES | — | `kitchen_remodel`, `design_build`, `whole_house_remodel`, etc. |
| `geo_targets` | ARRAY | YES | — | Array of targeted geo IDs |
| `created_at` | timestamptz | YES | `now()` | |
| `updated_at` | timestamptz | YES | `now()` | |
| `last_synced_at` | timestamptz | YES | — | Last Google Ads API sync |

### Sample Rows

```
id=4  name="Kitchen Remodel — Pleasanton"
      google_campaign_id="TEST_CAMP_001"
      status=ENABLED  campaign_type=SEARCH
      daily_budget_micros=45000000  daily_budget_usd=45.00
      bidding_strategy=MANUAL_CPC  service_category=kitchen_remodel

id=5  name="Design Build — Danville"
      google_campaign_id="TEST_CAMP_002"
      status=ENABLED  campaign_type=SEARCH
      daily_budget_micros=45000000  daily_budget_usd=45.00
      bidding_strategy=MANUAL_CPC  service_category=design_build

id=6  name="Whole House Remodel — Walnut Creek"
      google_campaign_id="TEST_CAMP_003"
      status=ENABLED  campaign_type=SEARCH
      daily_budget_micros=35000000  daily_budget_usd=35.00
      bidding_strategy=MANUAL_CPC  service_category=whole_house_remodel
```

---

## Table: `ad_groups`

One campaign → many ad groups. Groups are organized by match type (Exact, Phrase).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `google_ad_group_id` | varchar(50) | YES | — | Google Ads ad group ID |
| `campaign_id` | integer | YES | — | FK → `campaigns.id` |
| `name` | varchar(255) | NOT NULL | — | Human-readable name |
| `status` | varchar(20) | NOT NULL | `'ENABLED'` | `ENABLED` / `PAUSED` / `REMOVED` |
| `cpc_bid_micros` | bigint | YES | `0` | Default CPC bid for the group in micros |
| `created_at` | timestamptz | YES | `now()` | |
| `updated_at` | timestamptz | YES | `now()` | |

### Sample Rows

```
id=7   campaign_id=4  name="Kitchen Remodel — Pleasanton — Exact Match"
       google_ad_group_id="TEST_CAMP_001_AG_A"  status=ENABLED  cpc_bid_micros=10000000

id=8   campaign_id=4  name="Kitchen Remodel — Pleasanton — Phrase Match"
       google_ad_group_id="TEST_CAMP_001_AG_B"  status=ENABLED  cpc_bid_micros=10000000

id=9   campaign_id=5  name="Design Build — Danville — Exact Match"
       google_ad_group_id="TEST_CAMP_002_AG_A"  status=ENABLED  cpc_bid_micros=10000000

id=10  campaign_id=5  name="Design Build — Danville — Phrase Match"
       google_ad_group_id="TEST_CAMP_002_AG_B"  status=ENABLED  cpc_bid_micros=10000000

id=11  campaign_id=6  name="Whole House Remodel — Walnut Creek — Exact Match"
       google_ad_group_id="TEST_CAMP_003_AG_A"  status=ENABLED  cpc_bid_micros=10000000

id=12  campaign_id=6  name="Whole House Remodel — Walnut Creek — Phrase Match"
       google_ad_group_id="TEST_CAMP_003_AG_B"  status=ENABLED  cpc_bid_micros=10000000
```

---

## Table: `keywords`

Individual keywords within ad groups. CPC bids are per-keyword overrides.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `google_keyword_id` | varchar(50) | YES | — | Google Ads keyword ID |
| `ad_group_id` | integer | YES | — | FK → `ad_groups.id` |
| `keyword_text` | varchar(255) | NOT NULL | — | The keyword string |
| `match_type` | varchar(20) | NOT NULL | `'EXACT'` | `EXACT` / `PHRASE` / `BROAD` |
| `status` | varchar(20) | NOT NULL | `'ENABLED'` | `ENABLED` / `PAUSED` / `REMOVED` |
| `cpc_bid_micros` | bigint | YES | `0` | Per-keyword CPC bid in micros |
| `quality_score` | integer | YES | — | Google Quality Score 1–10 |
| `created_at` | timestamptz | YES | `now()` | |
| `updated_at` | timestamptz | YES | `now()` | |

### Sample Rows

```
id=10  ad_group_id=7   keyword_text="kitchen remodel pleasanton"
       match_type=EXACT   status=ENABLED  cpc_bid_micros=10000000 ($10.00)  quality_score=4

id=11  ad_group_id=8   keyword_text="kitchen remodel pleasanton"
       match_type=PHRASE  status=ENABLED  cpc_bid_micros=12000000 ($12.00)  quality_score=4

id=12  ad_group_id=7   keyword_text="luxury kitchen remodel pleasanton"
       match_type=EXACT   status=ENABLED  cpc_bid_micros=15000000 ($15.00)  quality_score=6

id=13  ad_group_id=9   keyword_text="design build danville"
       match_type=EXACT   status=ENABLED  cpc_bid_micros=12000000 ($12.00)  quality_score=5

id=14  ad_group_id=10  keyword_text="design build danville"
       match_type=PHRASE  status=ENABLED  cpc_bid_micros=9000000  ($9.00)   quality_score=5

id=15  ad_group_id=9   keyword_text="design build contractor danville"
       match_type=EXACT   status=ENABLED  cpc_bid_micros=11000000 ($11.00)  quality_score=5

id=16  ad_group_id=11  keyword_text="whole house remodel walnut creek"
       match_type=EXACT   status=ENABLED  cpc_bid_micros=13000000 ($13.00)  quality_score=4

id=17  ad_group_id=12  keyword_text="whole house remodel walnut creek"
       match_type=PHRASE  status=ENABLED  cpc_bid_micros=9000000  ($9.00)   quality_score=8

id=18  ad_group_id=11  keyword_text="home renovation walnut creek"
       match_type=EXACT   status=ENABLED  cpc_bid_micros=10000000 ($10.00)  quality_score=4
```

---

## Table: `negative_keywords`

Account-level and campaign-level terms to exclude from matching. Filters out budget-focused and irrelevant searchers.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `keyword_text` | varchar(255) | NOT NULL | — | The negative keyword string |
| `match_type` | varchar(20) | YES | `'BROAD'` | `BROAD` / `PHRASE` / `EXACT` |
| `scope` | varchar(20) | YES | `'account'` | `account` or `campaign` |
| `campaign_id` | integer | YES | — | FK → `campaigns.id` (if scope=campaign) |
| `ad_group_id` | integer | YES | — | FK → `ad_groups.id` (if scope=ad_group) |
| `reason` | text | YES | — | Why this negative was added |
| `added_at` | timestamptz | YES | `now()` | |

### All 21 Current Negative Keywords

```
cheap           BROAD   account  "Price-sensitive — filters low-budget prospects"
affordable      BROAD   account  "Budget-focused — not aligned with premium positioning"
low cost        PHRASE  account  "Budget-focused"
discount        BROAD   account  "Discount seekers not target audience"
free            BROAD   account  "Free services not offered"
diy             BROAD   account  "Do-it-yourself intent — not a buyer"
how to          PHRASE  account  "Informational, not transactional"
rent            BROAD   account  "Renters do not make renovation decisions"
apartment       BROAD   account  "Apartment context — low relevance"
condo           BROAD   account  "Typically lower budget projects"
handyman        BROAD   account  "Small jobs — not premium design-build"
repair          BROAD   account  "Repair intent — too small scope"
fix             BROAD   account  "Repair / fix intent"
template        BROAD   account  "Non-custom intent"
jobs            BROAD   account  "Employment seekers"
hiring          BROAD   account  "Employment seekers"
salary          BROAD   account  "Employment seekers"
school          BROAD   account  "Educational intent"
course          BROAD   account  "Educational intent"
software        BROAD   account  "Wrong context — software products"
app             BROAD   account  "Wrong context — software app intent"
```

---

## Table: `ads`

Responsive Search Ads. Currently empty (populated when Google Ads sync runs against live campaigns).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `google_ad_id` | varchar(50) | YES | — | Google Ads ad ID |
| `ad_group_id` | integer | YES | — | FK → `ad_groups.id` |
| `ad_type` | varchar(50) | YES | `'RESPONSIVE_SEARCH_AD'` | Ad format |
| `status` | varchar(20) | NOT NULL | `'ENABLED'` | `ENABLED` / `PAUSED` / `REMOVED` |
| `headlines` | jsonb | YES | — | Array of headline strings (up to 15) |
| `descriptions` | jsonb | YES | — | Array of description strings (up to 4) |
| `final_urls` | jsonb | YES | — | Array of landing page URLs |
| `ai_generated` | boolean | YES | `false` | Whether copy was AI-generated |
| `creative_notes` | text | YES | — | Internal notes on the creative |
| `created_at` | timestamptz | YES | `now()` | |
| `updated_at` | timestamptz | YES | `now()` | |

---

## Table: `creative_briefs`

AI-generated ad copy briefs. Before any ad is published to Google, the creative must be stored here first (guardrail rule). All 6 current briefs are for the `kitchen_remodel` service category.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `ad_group_id` | integer | YES | — | FK → `ad_groups.id` (null = account-level draft) |
| `service_category` | varchar(80) | YES | — | Matches `campaigns.service_category` |
| `headlines` | jsonb | YES | — | Array of headline strings (max 30 chars each) |
| `descriptions` | jsonb | YES | — | Array of description strings (max 90 chars each) |
| `callout_extensions` | jsonb | YES | — | Array of callout strings (max 25 chars each) |
| `sitelink_extensions` | jsonb | YES | — | Array of objects: `{title, url, description_line_1, description_line_2}` |
| `messaging_angle` | text | YES | — | AI-written brief explaining the creative strategy |
| `status` | varchar(20) | YES | `'draft'` | `draft` / `approved` / `deployed` / `archived` |
| `performance_notes` | text | YES | — | Post-deploy performance observations |
| `created_at` | timestamptz | YES | `now()` | |
| `deployed_at` | timestamptz | YES | — | When this brief was pushed live |

### Sample Row (Brief id=1)

**service_category:** `kitchen_remodel`
**status:** `draft`
**messaging_angle:**
> Position Ridgecrest Designs as the definitive luxury design-build authority for high-investment kitchen remodels in Pleasanton. Every headline and description reinforces premium positioning — emphasizing the $150K+ project threshold, photo-realistic renders, integrated permitting, and white-glove execution — to naturally attract affluent, serious homeowners while filtering out low-budget inquiries.

**headlines (15):**
```json
[
  "{KeyWord:Kitchen Remodel Pleasanton}",
  "Pleasanton Kitchen Remodels",
  "Luxury Kitchens in Pleasanton",
  "Design-Build Kitchen Experts",
  "Kitchens Starting at $150K",
  "Photo-Realistic 3D Renders",
  "Integrated Design & Build",
  "White-Glove Project Management",
  "Permits Handled End-to-End",
  "Flawless Kitchen Execution",
  "Built for Discerning Homes",
  "Your Vision, Precisely Built",
  "Trusted Luxury Remodelers",
  "Premium Kitchens, Zero Stress",
  "Crafted for Lasting Value"
]
```

**descriptions (6):**
```json
[
  "Ridgecrest Designs delivers luxury kitchen remodels from $150K with seamless design-build management.",
  "From photo-realistic renders to final install, we handle every detail of your Pleasanton kitchen.",
  "Expert permitting, precision craftsmanship, and a dedicated team guide your project start to finish.",
  "We work with homeowners who expect flawless results — our process ensures nothing is left to chance.",
  "High-end kitchen transformations designed, permitted, and built by one trusted Pleasanton firm.",
  "See your kitchen before we build it. Our 3D renders bring your vision to life with total clarity."
]
```

**callout_extensions (8):**
```json
[
  "Projects From $150K+",
  "Photo-Realistic Renders",
  "Full Permit Management",
  "Integrated Design-Build",
  "White-Glove Experience",
  "Pleasanton-Based Team",
  "Single Point of Contact",
  "Precision Craftsmanship"
]
```

**sitelink_extensions (4):**
```json
[
  {
    "title": "Our Kitchen Portfolio",
    "url": "https://go.ridgecrestdesigns.com",
    "description_line_1": "See completed luxury kitchen projects",
    "description_line_2": "Crafted for high-end Pleasanton homes"
  },
  {
    "title": "Our Design-Build Process",
    "url": "https://go.ridgecrestdesigns.com",
    "description_line_1": "One firm from concept to completion",
    "description_line_2": "Permits, design, and build included"
  },
  {
    "title": "Request a Consultation",
    "url": "https://go.ridgecrestdesigns.com",
    "description_line_1": "Start with a premium design session",
    "description_line_2": "Reserved for serious remodel projects"
  },
  {
    "title": "3D Render Previews",
    "url": "https://go.ridgecrestdesigns.com",
    "description_line_1": "See your kitchen before we build",
    "description_line_2": "Photo-realistic detail at every stage"
  }
]
```

---

## Table: `performance_metrics`

Daily metrics for each campaign and each keyword. One row per entity per date. This is the core analytics table.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `metric_date` | date | NOT NULL | — | The date these metrics cover |
| `entity_type` | varchar(20) | NOT NULL | — | `campaign` or `keyword` |
| `entity_id` | integer | NOT NULL | — | FK → `campaigns.id` or `keywords.id` |
| `google_entity_id` | varchar(50) | YES | — | Google's string ID for the entity |
| `impressions` | integer | YES | `0` | Total ad impressions |
| `clicks` | integer | YES | `0` | Total clicks |
| `conversions` | numeric | YES | `0` | Conversion count (can be fractional from attribution) |
| `cost_micros` | bigint | YES | `0` | Total spend in micros (÷1,000,000 = USD) |
| `cost_usd` | numeric | YES | — | Total spend in USD (convenience field) |
| `ctr` | numeric | YES | — | Click-through rate (clicks / impressions) |
| `cpc_avg_micros` | bigint | YES | — | Average CPC in micros |
| `cpa_micros` | bigint | YES | — | Cost per conversion in micros (null if 0 conversions) |
| `conversion_rate` | numeric | YES | — | Conversions / clicks |
| `impression_share` | numeric | YES | — | Impression share (0.0–1.0) — populated from API |
| `avg_position` | numeric | YES | — | Average ad position — populated from API |
| `quality_score` | integer | YES | — | Quality score snapshot — populated from API |
| `created_at` | timestamptz | YES | `now()` | |

### Sample Rows — March 20, 2026 (Campaign Level)

```
date=2026-03-20  entity_type=campaign  entity_id=4  google_entity_id=TEST_CAMP_001
  impressions=422   clicks=23  conversions=1.00   cost_usd=45.00   ctr=0.0545
  cpc_avg=$1.96     cpa=null (split across keywords)

date=2026-03-20  entity_type=campaign  entity_id=5  google_entity_id=TEST_CAMP_002
  impressions=473   clicks=17  conversions=1.00   cost_usd=45.00   ctr=0.0359
  cpc_avg=$2.65     cpa=$45.00

date=2026-03-20  entity_type=campaign  entity_id=6  google_entity_id=TEST_CAMP_003
  impressions=360   clicks=15  conversions=0.00   cost_usd=35.00   ctr=0.0417
  cpc_avg=$2.33     cpa=null
```

### Sample Rows — March 20, 2026 (Keyword Level, Selected)

```
entity_type=keyword  entity_id=10  keyword="kitchen remodel pleasanton" EXACT
  impressions=101  clicks=5  conversions=0.97  cost_usd=56.66
  ctr=4.95%  cpc_avg=$11.33  cpa_micros=58207725 ($58.21)  conv_rate=19.47%

entity_type=keyword  entity_id=12  keyword="luxury kitchen remodel pleasanton" EXACT
  impressions=83   clicks=5  conversions=0.06  cost_usd=70.50
  ctr=6.02%  cpc_avg=$14.10  cpa_micros=1272617328 ($1,272.62)  conv_rate=1.11%
  ⚠️ CPL >$1,250 — optimizer generated bid_decrease action

entity_type=keyword  entity_id=13  keyword="design build danville" EXACT
  impressions=118  clicks=6  conversions=0.57  cost_usd=62.90
  ctr=5.08%  cpc_avg=$10.48  cpa_micros=110966831 ($110.97)  conv_rate=9.45%
  ✅ Top performer — optimizer generated bid_increase action

entity_type=keyword  entity_id=17  keyword="whole house remodel walnut creek" PHRASE
  impressions=148  clicks=5  conversions=0.00  cost_usd=55.11
  ctr=3.38%  cpc_avg=$11.02  cpa_micros=null  conv_rate=0.00%
  ⚠️ $176 spent 7d, 0 conversions — optimizer generated pause_keyword action
```

---

## Table: `optimization_actions`

Every proposed and applied bid/budget optimization action. This is the action log and approval queue.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `agent_name` | varchar(50) | NOT NULL | — | Which agent created this: `bid_budget_optimizer` |
| `action_type` | varchar(80) | NOT NULL | — | See action types below |
| `entity_type` | varchar(20) | YES | — | `campaign` or `keyword` |
| `entity_id` | integer | YES | — | FK → entity's internal id |
| `google_entity_id` | varchar(50) | YES | — | Google's string ID |
| `before_value` | jsonb | YES | — | State before the action |
| `after_value` | jsonb | YES | — | Proposed state after the action |
| `reason` | text | YES | — | Why the optimizer proposed this |
| `applied` | boolean | YES | `false` | Whether the action was sent to Google Ads |
| `applied_at` | timestamptz | YES | — | When it was applied |
| `result` | text | YES | — | API result / error after applying |
| `created_at` | timestamptz | YES | `now()` | |

**action_type values:**
- `bid_increase` — increase keyword CPC bid
- `bid_decrease` — decrease keyword CPC bid
- `pause_keyword` — pause a keyword
- `budget_increase` — increase campaign daily budget
- `budget_decrease` — decrease campaign daily budget
- `budget_reallocation` — move budget between campaigns
- `pause_campaign` — pause a campaign (requires 3-day trend + human approval)
- `new_campaign` — blocked, requires human approval
- `change_objective` — blocked, requires human approval
- `change_match_type` — blocked, requires human approval
- `publish_creative` — publish creative brief to Google Ads

### Sample Rows (Latest 9 Actions — 2026-03-20)

```
id=28  bid_increase  keyword_id=10  google="TEST_CAMP_001_KW_01"
  before={cpc_bid_micros: 10000000}  after={cpc_bid_micros: 11500000}
  reason="CPL $60.00 is within target, increasing bid for volume"
  applied=false

id=29  bid_increase  keyword_id=11  google="TEST_CAMP_001_KW_02"
  before={cpc_bid_micros: 12000000}  after={cpc_bid_micros: 13799999}
  reason="CPL $240.00 is within target, increasing bid for volume"
  applied=false

id=30  bid_decrease  keyword_id=12  google="TEST_CAMP_001_KW_03"
  before={cpc_bid_micros: 15000000}  after={cpc_bid_micros: 12000000}
  reason="CPL $1650.00 exceeds target max $500.0"
  applied=false

id=31  bid_increase  keyword_id=13  google="TEST_CAMP_002_KW_01"
  before={cpc_bid_micros: 12000000}  after={cpc_bid_micros: 13799999}
  reason="CPL $168.00 is within target, increasing bid for volume"
  applied=false

id=32  pause_keyword  keyword_id=14  google="TEST_CAMP_002_KW_02"
  before={status: "ENABLED", cpc_bid_micros: 9000000}  after={status: "PAUSED"}
  reason="$180.00 spent over 7d with 0 conversions"
  applied=false

id=33  bid_increase  keyword_id=16  google="TEST_CAMP_003_KW_01"
  before={cpc_bid_micros: 13000000}  after={cpc_bid_micros: 14949999}
  reason="CPL $260.00 is within target, increasing bid for volume"
  applied=false

id=34  pause_keyword  keyword_id=17  google="TEST_CAMP_003_KW_02"
  before={status: "ENABLED", cpc_bid_micros: 9000000}  after={status: "PAUSED"}
  reason="$176.00 spent over 7d with 0 conversions"
  applied=false

id=35  budget_reallocation  campaign_id=4  google="TEST_CAMP_001"
  before={daily_budget_usd: 45.0}  after={daily_budget_usd: 55.5}
  reason="Reallocating toward top performer. Score: 355.0 vs -999.0"
  applied=false

id=36  budget_reallocation  campaign_id=6  google="TEST_CAMP_003"
  before={daily_budget_usd: 35.0}  after={daily_budget_usd: 24.5}
  reason="Reallocating toward top performer. Score: 355.0 vs -999.0"
  applied=false
```

> **Note:** All 36 current actions have `applied=false`. They are proposals waiting to be executed against the Google Ads API.

---

## Table: `reports`

Full daily and weekly performance reports generated by the `reporting_agent`. Each report includes a complete markdown body, a metrics snapshot, and optional recommendations.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `report_type` | varchar(50) | NOT NULL | — | `daily`, `weekly`, `alert` |
| `period_start` | date | YES | — | First day of report period |
| `period_end` | date | YES | — | Last day of report period |
| `title` | text | YES | — | Report title |
| `summary` | text | YES | — | One-line executive summary (sometimes null) |
| `body_markdown` | text | YES | — | Full report in Markdown format |
| `metrics_snapshot` | jsonb | YES | — | Key metrics as structured data |
| `recommendations` | jsonb | YES | — | Structured recommendations array (sometimes null) |
| `created_by` | varchar(50) | YES | `'reporting_agent'` | Agent that created the report |
| `created_at` | timestamptz | YES | `now()` | |

### `metrics_snapshot` JSON Structure

```json
{
  "impressions": 1255,
  "clicks": 55,
  "conversions": 1.0,
  "spend": 125.00,
  "avg_cpc": 2.2727,
  "avg_ctr": 22.82,
  "cpl": 125.00
}
```

### Latest Report (id=4) — Daily Performance Report 2026-03-20

**report_type:** `daily`
**period:** 2026-03-20 → 2026-03-20
**created_by:** `reporting_agent`
**created_at:** 2026-03-20 00:23:51 UTC

**metrics_snapshot:**
```json
{
  "impressions": 1255,
  "clicks": 55,
  "conversions": 1.0,
  "spend": 125.00,
  "avg_cpc": 2.2727272727272725,
  "avg_ctr": 22.818181818181817,
  "cpl": 125.0
}
```

**body_markdown (full):**

---

## Daily Performance Report — March 20, 2026

### Executive Summary

Ridgecrest Designs hit its $125.00 daily budget cap across all three campaigns, generating 1,255 impressions, 55 clicks, and 1 confirmed conversion at a $125.00 day-of CPL. The sole conversion came from **Design Build — Danville**, which continues to be the account's top performer; the other two campaigns spent a combined $80.00 with zero conversions today. The 7-day CPL of **$83.33** remains healthy relative to target, but single-day conversion volume is thin and budget efficiency needs tightening before tomorrow's spend cycle opens.

### Key Metrics

| Metric | Today | 7-Day Avg / Total |
|---|---|---|
| Impressions | 1,255 | 5,483 (7d total) |
| Clicks | 55 | 239 (7d total) |
| Conversions | 1 | 6 (7d total) |
| Spend | $125.00 | $500.00 (7d total) |
| Avg CPC | $2.27 | $2.09 |
| CPL | $125.00 (today) | $83.33 (7d) |

### Campaign Breakdown

| Campaign | Impressions | Clicks | CTR | Conversions | Spend | CPA |
|---|---|---|---|---|---|---|
| 🏆 Design Build — Danville | 473 | 17 | 3.59% | **1** | $45.00 | **$45.00** |
| Kitchen Remodel — Pleasanton | 422 | 23 | 5.45% | 0 | $45.00 | — |
| ⚠️ Whole House Remodel — Walnut Creek | 360 | 15 | 4.17% | 0 | $35.00 | — |

### Budget Status

- **Daily cap:** $125.00 | **Today's spend:** $125.00 | **Remaining:** $0.00
- **Pacing:** ✅ On Track (cap fully utilized) | **Active day:** Yes (Friday)

### Alerts & Flags

| Severity | Type | Detail |
|---|---|---|
| ⚠️ Warning | Budget Pacing | Spend reached 100% of daily cap ($125.00). |
| ℹ️ Info | Low CPL (7d) | 7-day CPL of $83.33 is below target minimum — verify lead quality. |
| ⚠️ Warning | Zero Conversions | Kitchen Remodel — Pleasanton: $45.00 today, 0 conversions. |
| ⚠️ Warning | Zero Conversions | Whole House Remodel — Walnut Creek: $35.00 today, 0 conversions. |
| 🔴 Urgent | Runaway Keyword CPL | One keyword tracking at **$1,650 CPL** — 3.3× the $500 max. |
| 🔴 Urgent | Dead Keyword Spend | Two keywords consumed **$180** and **$176** over 7d with 0 conversions. |

---

## Table: `budget_snapshots`

Daily snapshot of budget pacing. One row per active day.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `snapshot_date` | date | NOT NULL | — | The date of the snapshot |
| `day_of_week` | varchar(10) | YES | — | e.g. `friday`, `thursday` |
| `is_active_day` | boolean | YES | — | Whether ads ran this day |
| `total_spend_usd` | numeric | YES | `0` | Total spend across all campaigns |
| `daily_cap_usd` | numeric | YES | `125.00` | The daily budget cap |
| `remaining_usd` | numeric | YES | — | `daily_cap_usd - total_spend_usd` |
| `campaign_breakdown` | jsonb | YES | — | Object: `{campaign_name: spend_usd}` |
| `pacing_status` | varchar(20) | YES | — | `on_track`, `under`, `over`, `at_risk` |
| `created_at` | timestamptz | YES | `now()` | |

### Sample Rows

```
id=3  snapshot_date=2026-03-20  day_of_week=friday  is_active_day=true
  total_spend_usd=125.00  daily_cap_usd=125.00  remaining_usd=0.00
  pacing_status=on_track
  campaign_breakdown={
    "Design Build — Danville": 45.0,
    "Kitchen Remodel — Pleasanton": 45.0,
    "Whole House Remodel — Walnut Creek": 35.0
  }

id=1  snapshot_date=2026-03-19  day_of_week=thursday  is_active_day=false
  total_spend_usd=0.00  daily_cap_usd=125.00  remaining_usd=125.00
  pacing_status=under
  campaign_breakdown={}
```

---

## Table: `agent_messages`

Inter-agent messaging queue. Also serves as the **alerts feed** — performance alerts, optimization completions, and report completions are all published here.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `from_agent` | varchar(50) | NOT NULL | — | Sending agent name |
| `to_agent` | varchar(50) | NOT NULL | — | Receiving agent or `all` for broadcast |
| `message_type` | varchar(80) | NOT NULL | — | See types below |
| `payload` | jsonb | NOT NULL | `{}` | Message body (structure varies by type) |
| `status` | varchar(20) | NOT NULL | `'pending'` | `pending` / `done` / `error` |
| `priority` | integer | NOT NULL | `5` | Lower = higher priority |
| `created_at` | timestamptz | YES | `now()` | |
| `processed_at` | timestamptz | YES | — | When the message was acknowledged |
| `error_detail` | text | YES | — | Error message if status=error |

**message_type values:**
- `performance_analysis_complete` — from `performance_analyst`, contains alerts array
- `optimization_complete` — from `bid_budget_optimizer`, contains action summaries
- `report_complete` — from `reporting_agent`, contains report_id
- `critical_alert` — escalation alerts
- `creative_work_complete` — from `creative_agent`

### Latest Alert Payload (message id=11, type=performance_analysis_complete)

```json
{
  "report_date": "2026-03-20",
  "today_spend": 125.0,
  "budget_remaining": 0,
  "alert_count": 4,
  "critical_alerts": [],
  "alerts": [
    {
      "type": "budget_pacing",
      "severity": "warning",
      "message": "Spend $125.00 is >90% of daily cap. Monitor closely."
    },
    {
      "type": "low_cpl",
      "severity": "info",
      "message": "CPL $83.33 is below target min — possible lead quality concern"
    },
    {
      "type": "zero_conversions",
      "severity": "warning",
      "message": "Campaign 'Kitchen Remodel — Pleasanton' spent $45.00 with 0 conversions today.",
      "campaign": "Kitchen Remodel — Pleasanton"
    },
    {
      "type": "zero_conversions",
      "severity": "warning",
      "message": "Campaign 'Whole House Remodel — Walnut Creek' spent $35.00 with 0 conversions today.",
      "campaign": "Whole House Remodel — Walnut Creek"
    }
  ],
  "summary_7d": {
    "cpl": 83.33,
    "avg_cpc": 2.09,
    "total_spend": 500.0,
    "total_clicks": 239.0,
    "total_conversions": 6.0,
    "total_impressions": 5483.0
  },
  "campaign_breakdown": [
    {
      "name": "Kitchen Remodel — Pleasanton",
      "google_campaign_id": "TEST_CAMP_001",
      "impressions": 422.0,
      "clicks": 23.0,
      "conversions": 0.0,
      "cost_usd": 45.0,
      "ctr": 0.0545,
      "cpa_usd": null
    },
    {
      "name": "Design Build — Danville",
      "google_campaign_id": "TEST_CAMP_002",
      "impressions": 473.0,
      "clicks": 17.0,
      "conversions": 1.0,
      "cost_usd": 45.0,
      "ctr": 0.0359,
      "cpa_usd": 45.0
    },
    {
      "name": "Whole House Remodel — Walnut Creek",
      "google_campaign_id": "TEST_CAMP_003",
      "impressions": 360.0,
      "clicks": 15.0,
      "conversions": 0.0,
      "cost_usd": 35.0,
      "ctr": 0.0417,
      "cpa_usd": null
    }
  ]
}
```

---

## Table: `agent_heartbeats`

Health and run status for each agent. One row per agent (upserted on each run).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `agent_name` | varchar(50) | NOT NULL | — | Unique agent identifier |
| `status` | varchar(20) | YES | `'alive'` | `alive`, `error`, `idle` |
| `last_run_at` | timestamptz | YES | `now()` | Last heartbeat timestamp |
| `last_success_at` | timestamptz | YES | — | Last successful run |
| `run_count` | integer | YES | `0` | Total runs since first seen |
| `error_count` | integer | YES | `0` | Total errors |
| `last_error` | text | YES | — | Last error message |
| `metadata` | jsonb | YES | `{}` | Agent-specific context (last run details, etc.) |

### Current Agent Status (2026-03-20)

```
agent_name=bid_budget_optimizer  status=alive  run_count=13  error_count=0
  last_run_at=2026-03-20 00:51:18 UTC
  last_success_at=2026-03-20 00:51:18 UTC

agent_name=creative_agent        status=alive  run_count=1   error_count=0
  last_run_at=2026-03-20 00:22:34 UTC

agent_name=orchestrator          status=alive  run_count=1   error_count=0
  last_run_at=2026-03-20 00:23:51 UTC

agent_name=performance_analyst   status=alive  run_count=3   error_count=0
  last_run_at=2026-03-20 00:22:35 UTC

agent_name=reporting_agent       status=alive  run_count=4   error_count=0
  last_run_at=2026-03-20 00:23:51 UTC
```

---

## Table: `guardrail_violations`

Log of every guardrail rule violation or escalation trigger. Currently empty (no violations have fired yet).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `created_at` | timestamptz | NOT NULL | `now()` | When the violation was detected |
| `rule_category` | text | NOT NULL | — | `spend_limits`, `keyword_rules`, `campaign_rules`, `creative_rules`, `reporting`, `escalation` |
| `rule_name` | text | NOT NULL | — | Specific rule identifier (e.g. `bid_increase_exceeds_25pct`) |
| `action_type` | text | YES | — | The action type that was blocked |
| `entity_type` | text | YES | — | `campaign`, `keyword`, `ad`, etc. |
| `entity_id` | integer | YES | — | FK to the relevant entity |
| `entity_name` | text | YES | — | Human-readable entity name |
| `proposed_value` | jsonb | YES | — | What the optimizer was trying to do |
| `limit_value` | jsonb | YES | — | The guardrail threshold that was violated |
| `reason` | text | NOT NULL | — | Human-readable explanation |
| `escalated` | boolean | NOT NULL | `false` | Whether this triggered human escalation |
| `escalation_sent` | boolean | NOT NULL | `false` | Whether the alert email was sent |
| `pipeline_run_id` | text | YES | — | Run ID for traceability (format: `YYYY-MM-DD-<epoch>`) |

**Escalation triggers** (auto-email to henry@ridgecrestdesigns.com):
- CPL > $1,000
- Daily spend > $150.00
- Any keyword ≥ $75 spend with 0 conversions
- Any API agent silent for > 2 hours

---

## Table: `geo_performance`

Geographic breakdown of performance metrics. Currently empty — populated when Google Ads geographic reports are synced.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `metric_date` | date | NOT NULL | — | Report date |
| `location_type` | varchar(20) | YES | — | `city`, `zip`, `region` |
| `location_value` | varchar(50) | YES | — | e.g. `Pleasanton`, `94566` |
| `campaign_id` | integer | YES | — | FK → `campaigns.id` |
| `impressions` | integer | YES | `0` | |
| `clicks` | integer | YES | `0` | |
| `conversions` | numeric | YES | `0` | |
| `cost_micros` | bigint | YES | `0` | Spend in micros |
| `created_at` | timestamptz | YES | `now()` | |

---

## Table: `search_terms`

Raw search term report showing exactly what users typed before clicking an ad. Currently empty — populated from Google Ads search term reports.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | integer | NOT NULL | auto-increment | Internal PK |
| `report_date` | date | NOT NULL | — | Report date |
| `search_term` | varchar(500) | NOT NULL | — | The exact query the user searched |
| `campaign_id` | integer | YES | — | FK → `campaigns.id` |
| `ad_group_id` | integer | YES | — | FK → `ad_groups.id` |
| `impressions` | integer | YES | `0` | |
| `clicks` | integer | YES | `0` | |
| `conversions` | numeric | YES | `0` | |
| `cost_micros` | bigint | YES | `0` | |
| `classification` | varchar(20) | YES | `'unreviewed'` | `unreviewed`, `relevant`, `irrelevant`, `added_as_negative` |
| `created_at` | timestamptz | YES | `now()` | |

---

## Live Data Samples

### Account-Level 7-Day Summary (as of 2026-03-20)

```
Period:         2026-03-14 → 2026-03-20
Total Spend:    $500.00  (4 active days × $125/day)
Impressions:    5,483
Clicks:         239
Conversions:    6
Avg CPC:        $2.09
7-Day CPL:      $83.33
Target CPL:     $150 – $500
```

### Current Campaign Performance (2026-03-20)

| Campaign | Budget | Spend Today | Impressions | Clicks | CTR | Conversions | CPA |
|---|---|---|---|---|---|---|---|
| Kitchen Remodel — Pleasanton | $45/day | $45.00 | 422 | 23 | 5.45% | 0 | — |
| Design Build — Danville | $45/day | $45.00 | 473 | 17 | 3.59% | 1 | $45.00 |
| Whole House Remodel — Walnut Creek | $35/day | $35.00 | 360 | 15 | 4.17% | 0 | — |
| **TOTAL** | **$125/day** | **$125.00** | **1,255** | **55** | **4.38%** | **1** | **$125.00** |

### Keyword Performance Ranking (2026-03-20, by CPA)

| Keyword | Match | Spend | Clicks | Conv | CPA | Status |
|---|---|---|---|---|---|---|
| kitchen remodel pleasanton | EXACT | $56.66 | 5 | 0.97 | $58.21 | ✅ Top performer |
| design build danville | EXACT | $62.90 | 6 | 0.57 | $110.97 | ✅ Top performer |
| kitchen remodel pleasanton | PHRASE | $57.20 | 4 | 0.19 | $295.00 | 🟡 Monitor |
| whole house remodel walnut creek | EXACT | $49.07 | 3 | 0.29 | $170.00 | 🟡 Monitor |
| luxury kitchen remodel pleasanton | EXACT | $70.50 | 5 | 0.06 | $1,272.00 | 🔴 Bid decrease pending |
| design build contractor danville | EXACT | $37.21 | 3 | 0 | — | ⚠️ 7d zero conv |
| design build danville | PHRASE | $49.79 | 4 | 0 | — | ⚠️ Pause pending ($180 wasted) |
| whole house remodel walnut creek | PHRASE | $55.11 | 5 | 0 | — | ⚠️ Pause pending ($176 wasted) |
| home renovation walnut creek | EXACT | $23.99 | 2 | 0 | — | ⚠️ 7d zero conv |

---

## Key Relationships

```
campaigns (1)
  └── ad_groups (many)        campaign_id → campaigns.id
        └── keywords (many)   ad_group_id → ad_groups.id
        └── ads (many)        ad_group_id → ad_groups.id
        └── creative_briefs   ad_group_id → ad_groups.id (nullable)

performance_metrics
  entity_type='campaign' + entity_id → campaigns.id
  entity_type='keyword'  + entity_id → keywords.id

optimization_actions
  entity_type='campaign' + entity_id → campaigns.id
  entity_type='keyword'  + entity_id → keywords.id

geo_performance
  campaign_id → campaigns.id

search_terms
  campaign_id → campaigns.id
  ad_group_id → ad_groups.id

negative_keywords
  campaign_id → campaigns.id (nullable, null=account-level)
  ad_group_id → ad_groups.id (nullable)

guardrail_violations
  entity_id → varies by entity_type
```

---

## Money / Units Reference

All monetary values in the database are stored in one of two ways. Never mix them.

| Field suffix | Unit | Conversion | Example |
|---|---|---|---|
| `_micros` | Micros (millionths of USD) | `÷ 1,000,000` = USD | `10000000` micros = `$10.00` |
| `_usd` | US Dollars (decimal) | Already USD | `45.00` = `$45.00` |

**Common conversions:**
```
cpc_bid_micros = 10000000  →  $10.00 CPC bid
cost_micros    = 56659400  →  $56.66 spend
cpa_micros     = 58207725  →  $58.21 CPA
cpa_micros     = 1272617328 → $1,272.62 CPA  ← runaway keyword
```

**CTR and conversion_rate** are stored as decimals (e.g. `0.0495` = 4.95%). Multiply by 100 to display as percentage.

---

## Active Days & Schedule

Campaigns only run on:
- **Friday, Saturday, Sunday, Monday**

Campaigns are **paused on Tuesday, Wednesday, and Thursday.**

Daily budget cap: **$125.00 / day** (hard limit — never exceeded).
Weekly maximum: **$500.00**.
Target CPL range: **$150 – $500**.

---

*Generated 2026-03-20 from live marketing_agent database. Schema version current as of this date.*
