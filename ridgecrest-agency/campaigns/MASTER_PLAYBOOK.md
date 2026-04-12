# Ridgecrest Marketing Agency — Master Playbook
### Operating Manual for AI Agents: Google Ads Campaign Setup for Contractors

**Version:** 1.0  
**Maintained by:** Ridgecrest Marketing Agency  
**Last Updated:** 2026  
**Agent Prefixes:** [PX] = Perplexity | [RMA] = Claude/Anthropic agents  

---

> **BEFORE ANYTHING ELSE:** Read `rules/` directory, check `agency_mode.txt`, and read `CURRENT_STATUS.md`. Every session starts here — no exceptions.

---

## Table of Contents

1. [Pre-Campaign Audit](#section-1-pre-campaign-audit)
2. [Client Intake](#section-2-client-intake)
3. [Keyword Research Methodology](#section-3-keyword-research-methodology)
4. [Negative Keyword Strategy](#section-4-negative-keyword-strategy)
5. [Ad Group Structure](#section-5-ad-group-structure)
6. [Campaign Assets](#section-6-campaign-assets)
7. [Geo Targeting](#section-7-geo-targeting)
8. [Ad Schedule and Bidding](#section-8-ad-schedule-and-bidding)
9. [Conversion Tracking](#section-9-conversion-tracking)
10. [Monitoring and Optimization](#section-10-monitoring-and-optimization)
11. [Competitive Intelligence](#section-11-competitive-intelligence)
12. [Rules (Non-Negotiable)](#section-12-rules-non-negotiable)
13. [File Structure (Server)](#section-13-file-structure-server)
14. [Platform-Specific Notes](#section-14-platform-specific-notes)

---

## Section 1: Pre-Campaign Audit

### Purpose
Before creating, modifying, or pausing anything, establish ground truth about the account's current state. This prevents duplicate campaigns, conflicting settings, and blown budgets. **Read before you write.**

### Step 1.1 — Verify Account Access and Prefix Ownership

Before touching any entity, confirm:
- Which agent prefix owns which campaigns (only touch campaigns with YOUR prefix)
- Check `agency_mode.txt` — if it reads `PAUSED` or `READ_ONLY`, do not make changes
- Read `CAMPAIGN_IDS.md` to understand the account structure

### Step 1.2 — Run the Read-Only Account Audit Script

Paste this script into **Google Ads > Tools > Scripts** and run in PREVIEW mode first. Never run live without preview.

```javascript
// RIDGECREST AUDIT SCRIPT v1.0
// READ-ONLY — No changes made
// Run in Preview mode to confirm safe output

function main() {
  var report = [];
  
  // --- Account Info ---
  var account = AdsApp.currentAccount();
  report.push("=== ACCOUNT INFO ===");
  report.push("Name: " + account.getName());
  report.push("CID: " + account.getCustomerId());
  report.push("Currency: " + account.getCurrencyCode());
  report.push("Timezone: " + account.getTimeZone());
  report.push("");

  // --- Campaign Inventory ---
  report.push("=== CAMPAIGNS ===");
  var campaigns = AdsApp.campaigns().get();
  while (campaigns.hasNext()) {
    var c = campaigns.next();
    report.push(
      "ID: " + c.getId() +
      " | Name: " + c.getName() +
      " | Status: " + c.isEnabled() +
      " | Budget: $" + c.getBudget().getAmount() +
      " | BidStrategy: " + c.getBiddingStrategyType()
    );
  }
  report.push("");

  // --- Conversion Actions ---
  report.push("=== CONVERSION ACTIONS ===");
  var convActions = AdsApp.conversionActions().get();
  while (convActions.hasNext()) {
    var ca = convActions.next();
    report.push(
      "Name: " + ca.getName() +
      " | Category: " + ca.getCategory() +
      " | Status: " + ca.isEnabled() +
      " | IncludeInConversions: " + ca.includeInConversionsMetric()
    );
  }
  report.push("");

  // --- Geo Targets (per campaign) ---
  report.push("=== GEO TARGETS ===");
  var camps2 = AdsApp.campaigns().get();
  while (camps2.hasNext()) {
    var c2 = camps2.next();
    report.push("Campaign: " + c2.getName());
    var targeting = c2.targeting().targetedLocations().get();
    while (targeting.hasNext()) {
      var loc = targeting.next();
      report.push("  Location: " + loc.getName() + " (ID: " + loc.getId() + ")");
    }
  }
  report.push("");

  // --- Budget Summary ---
  report.push("=== BUDGET SUMMARY ===");
  var budgets = AdsApp.budgets().get();
  while (budgets.hasNext()) {
    var b = budgets.next();
    report.push(
      "Budget Name: " + b.getName() +
      " | Amount: $" + b.getAmount() +
      " | Delivery: " + b.getDeliveryMethod()
    );
  }

  // Output to log
  Logger.log(report.join("\n"));
}
```

### Step 1.3 — What to Check in Audit Results

Review every item in this checklist before proceeding:

| Check | What to Look For | Red Flag |
|-------|-----------------|----------|
| **Conversion tracking** | At least one action with `includeInConversionsMetric = true` | No conversions set up, or all set to "Observation" only |
| **Existing campaigns** | Any campaigns with your client's service keywords already running | Duplicate or conflicting campaigns eating budget |
| **Existing keywords** | Broad match terms that could cannibalise new ad groups | Unfocused catch-all campaigns |
| **Geo targeting** | Location targets match agreed service area | Targeting entire state or country |
| **Budget** | Daily budget aligns with monthly target ÷ 30.4 | Over- or under-allocated |
| **Bid strategy** | Appropriate for account maturity (see Section 8) | Target CPA/ROAS with fewer than 30 conversions/month |
| **Ad schedule** | Hours match client operating hours | Running 24/7 for a business that closes at 5pm |
| **Negative keywords** | Campaign-level and ad group-level negatives exist | No negatives at all |
| **Ad status** | No disapproved ads | Policy violations blocking delivery |
| **Search terms** | Irrelevant terms eating budget | Budget going to DIY, job seekers, or wrong geography |

### Step 1.4 — Document Findings

After the audit script runs, save output to:
```
CURRENT_STATUS.md
```

Format:
```
## Audit — [DATE] [TIME]
Agent: [YOUR PREFIX]
Account CID: [CID]

### Findings
- Conversion tracking: [STATUS]
- Active campaigns: [COUNT]
- Geo targeting: [SUMMARY]
- Budget: [AMOUNT/DAY]
- Bid strategy: [TYPE]
- Issues found: [LIST]

### Recommended Next Steps
[YOUR RECOMMENDATIONS]
```

### Step 1.5 — Keyword Audit Script

Run this separately to get a full keyword dump:

```javascript
// KEYWORD AUDIT SCRIPT — READ ONLY
function main() {
  var report = [];
  var adGroups = AdsApp.adGroups().get();
  
  while (adGroups.hasNext()) {
    var ag = adGroups.next();
    var campaign = ag.getCampaign();
    report.push("\nCampaign: " + campaign.getName() + " | AdGroup: " + ag.getName());
    
    var keywords = ag.keywords().get();
    while (keywords.hasNext()) {
      var kw = keywords.next();
      report.push(
        "  [" + kw.getMatchType() + "] " + kw.getText() +
        " | QS: " + kw.getQualityScore() +
        " | Impressions: " + kw.getStatsFor("LAST_30_DAYS").getImpressions() +
        " | Clicks: " + kw.getStatsFor("LAST_30_DAYS").getClicks()
      );
    }
  }
  
  Logger.log(report.join("\n"));
}
```

---

## Section 2: Client Intake

### Purpose
Every campaign starts with a structured intake. Do not begin keyword research, ad copy, or geo targeting until all eight questions below are answered and documented. Incomplete intake = wasted budget.

### Intake Form Template

Save completed form to: `campaigns/[CLIENT_SLUG]_intake.md`

---

**RIDGECREST MARKETING AGENCY — CLIENT INTAKE FORM**

**Date:** ___________  
**Client Name:** ___________  
**Client Business Name:** ___________  
**Intake Completed By:** ___________  

---

**Question 1: What industry?**

Primary industry (circle one): Remodeling | HVAC | Plumbing | Roofing | Electrical | Landscaping | Painting | Flooring | Windows/Doors | General Contractor | Other: ___________

*Why this matters:* Determines which keyword libraries to pull from, which negative services to add, and which Google vertical (Home Services vs. standard Search) applies.

*Example — Ridgecrest Designs:* Luxury home remodeling (kitchen, bathroom, whole-home remodel, additions/ADU, design-build)

---

**Question 2: What specific services do you offer?**

List every service the client actively wants leads for. Be granular — "remodeling" is not sufficient.

Format:
```
Primary services (want most leads):
- [SERVICE 1]
- [SERVICE 2]

Secondary services (want some leads):
- [SERVICE 3]

Services they do NOT want leads for (become negatives):
- [SERVICE 4]
```

*Example — Ridgecrest Designs:*
- Primary: Kitchen remodeling, bathroom remodeling, whole-home remodel
- Secondary: Room additions, ADU/granny flat, design-build
- NOT offered: Roofing, plumbing, HVAC, electrical, painting, landscaping → all become negatives

---

**Question 3: What zip codes do you serve?**

Collect every zip code. Do not accept city names alone — zip codes are the source of truth for geo targeting.

```
Served zip codes:
94507, 94523, 94526, 94528, 94531, 94549, 94553, 94556, 94563, 94564,
94565, 94566, 94568, 94582, 94583, 94595, 94596, 94597, 94598

EXCLUSIONS (zip codes within physical area but NOT served):
94553 (Martinez) — excluded per client instruction
```

*Action after collecting:* Cross-reference against Google's geo targets CSV (see Section 7). Map every zip to its city name. Remove any cities that fall outside client territory.

---

**Question 4: What is your price positioning?**

Circle one: **Luxury** | Mid-Range | Budget

*Implications by tier:*

| Tier | Negatives to add | Headlines to use | Ad groups to prioritize |
|------|-----------------|-----------------|------------------------|
| Luxury | "affordable", "cheap", "budget", "discount", "low cost", "inexpensive", "economical" | "Award-Winning Design", "Premium Craftsmanship", "Concierge Service" | Design-Build, Whole Home, High-end Kitchen/Bath |
| Mid-Range | "cheap", "budget" (keep "affordable") | "Quality Work, Fair Price", "Trusted Local Contractor" | All service types equally |
| Budget | None of the above negatives | "Affordable [Service]", "Best Price Guarantee" | Volume-oriented generic terms |

*Example — Ridgecrest Designs:* **Luxury** → "affordable" is a permanent negative keyword. Do not remove. Do not argue. Do not override.

---

**Question 5: What is your monthly ad budget?**

```
Monthly budget confirmed: $___________
Daily budget calculation: Monthly ÷ 30.4 = $___________/day
```

*Notes:*
- Google now attempts to spend 30.4x the daily budget per month regardless of ad schedule (March 2026 change). If the client runs a restricted schedule, adjust daily budget down accordingly.
- Do not set daily budget to monthly ÷ 31. Use 30.4.
- If budget is under $1,500/month for a local market, flag to account manager — below this threshold, very limited data accumulates for optimization.

*Example — Ridgecrest Designs:* $3,000/month → $98.68/day

---

**Question 6: What is your website URL?**

```
Main URL: ___________
Service pages (if separate landing pages exist):
- Kitchen: ___________
- Bathroom: ___________
- [Other]: ___________
```

*Action:* Verify the site loads without errors. Verify each service page actually exists before using it as a sitelink destination. Check for contact form and phone number visibility above the fold.

---

**Question 7: What phone number for call assets?**

```
Primary phone: ___________
Tracking number (if using CallRail or similar): ___________
Forward-to number: ___________
Hours phone is staffed: ___________
```

*If client uses a call tracking number:* Use the tracking number in Google Ads call asset so calls are attributed. Verify forwarding is active before launch.

---

**Question 8: Do you offer free estimates/consultations?**

Circle one: **Yes — Free Estimates** | Yes — Paid Consultation | No free offer

*Impact:*
- If yes: include "Free Estimate" in at least 2 headlines and 1 description per RSA
- Include in callout assets: "Free In-Home Estimates"
- Use in sitelink text: "Get Your Free Estimate"
- If no: use "Schedule a Consultation" instead — do not fabricate an offer that doesn't exist

---

### Intake Completion Checklist

Before proceeding to keyword research, confirm:
- [ ] Industry identified
- [ ] Specific services listed (with "NOT offered" services for negatives)
- [ ] All zip codes collected and documented
- [ ] Price positioning confirmed
- [ ] Monthly budget confirmed and daily budget calculated
- [ ] Website URL verified (loads, has contact form)
- [ ] Phone number confirmed and tested
- [ ] Free estimate offer confirmed or denied

If any item is unchecked, **stop and get the information**. Do not proceed with assumptions.

---

## Section 3: Keyword Research Methodology

### Overview

Keyword research for local service contractors follows a strict 7-step process. Every keyword must have a documented source and verified search volume before inclusion. Do not add keywords from intuition alone.

**Guiding principle:** For small local service businesses, broad match + geo targeting + comprehensive negatives outperforms exact/phrase match. Reason: in small local markets, exact match for niche contractor terms results in zero or near-zero impressions because the search volume is too low to trigger consistently. Broad match captures natural language variants and related queries that exact match misses, while geo targeting and negatives filter out irrelevant traffic. This approach is validated across Ridgecrest Designs implementation and supported by ClicksGeek home improvement research.

---

### Step 3.1 — Map Zip Codes to Cities

**Source:** Google's official geo targets CSV  
**URL:** https://developers.google.com/google-ads/api/data/geotargets  
**File to download:** geotargets-[date].csv

Process:
1. Download the CSV
2. Filter by `Country Code = US` and `Target Type = Postal Code`
3. For each client zip code, look up the `Name` field — this is the city Google associates with that zip
4. Record the mapping

Example mapping for Ridgecrest Designs:
```
94507 → Alamo, CA
94523 → Pleasant Hill, CA
94526 → Danville, CA
94528 → Diablo, CA
94531 → Antioch, CA
94549 → Lafayette, CA
94553 → Martinez, CA ← EXCLUDED per client
94556 → Moraga, CA
94563 → Orinda, CA
94564 → Pinole, CA
94565 → Pittsburg, CA
94566 → Pleasanton, CA
94568 → Dublin, CA
94582 → San Ramon, CA
94583 → San Ramon, CA
94595 → Walnut Creek, CA
94596 → Walnut Creek, CA
94597 → Walnut Creek, CA
94598 → Walnut Creek, CA
```

**Critical:** If a zip maps to a city that falls outside the client's actual service area, remove that zip from geo targeting AND from keyword city lists. Never add city keywords for cities you are not geo-targeting.

---

### Step 3.2 — Identify Affluent Neighborhoods Using the Golf Course / Country Club Method

**Purpose:** High-value remodeling leads concentrate in affluent neighborhoods. Generic city keywords get volume but attract mid-range clients. Neighborhood-specific keywords attract luxury clients with larger project budgets.

**The Method:**

1. Open Google Maps
2. Search for: `private golf course [city name]` and `country club [city name]` for each city in the target market
3. For each result, identify the surrounding neighborhood name (not the club itself)
4. Cross-reference with Zillow or Redfin to confirm median home values ($800K+ qualifies for luxury targeting)
5. Document the neighborhood name and the city it belongs to

Example — Ridgecrest Designs neighborhoods identified via this method:
```
Alamo (94507) → Alamo neighborhood, Roundhill Country Club area
Danville (94526) → Blackhawk, Diablo area (near Diablo Country Club)
Lafayette (94549) → Upper Lafayette hills, Happy Valley area
Moraga (94556) → Rheem Valley, Country Club of Moraga area
Orinda (94563) → Orinda Country Club area, Sleepy Hollow
Walnut Creek (94595-98) → Boundary Oak area, Rossmoor (55+ but high HHI)
Diablo (94528) → Diablo Country Club — highest HHI in service area
Pleasanton (94566) → Ruby Hill, Castlewood Country Club area
```

6. These neighborhood names become a dedicated keyword tier (see Step 3.5)

---

### Step 3.3 — Build Generic / Near-Me Keywords by Service Type

Build 20–30 generic keywords per service. These capture intent without geographic specificity — the geo targeting handles location restriction.

**Template format:**
```
[service] contractor
[service] company
[service] services
[service] near me
local [service] contractor
best [service] contractor
[service] remodeler (if applicable)
[service] specialist
[service] expert
custom [service]
[service] quote
[service] estimate
[service] cost
[service] pricing
[service] design
[service] build
[service] renovation
[service] upgrade
[service] remodel
licensed [service] contractor
```

**Example — Kitchen Remodeling generic keywords:**
```
kitchen remodeling contractor
kitchen remodeling company
kitchen remodeling services
kitchen remodel near me
local kitchen remodeler
best kitchen remodeler
kitchen renovation contractor
kitchen renovation company
kitchen renovation near me
custom kitchen remodel
kitchen remodel quote
kitchen remodel estimate
kitchen remodeling cost
kitchen remodel pricing
kitchen design build
kitchen cabinet replacement
kitchen makeover contractor
luxury kitchen remodel
high end kitchen remodel
kitchen addition contractor
full kitchen renovation
kitchen gut renovation
kitchen remodeling specialist
kitchen remodeling expert
kitchen remodeler near me
```

All match type: **Broad Match** (no brackets, no quotes in Google Ads keyword field)

---

### Step 3.4 — Build City-Specific Keywords

Pattern: `[service keyword] [city name]`

Apply service keyword patterns to every city in the geo target list (excluding excluded cities like Martinez for Ridgecrest).

**Formula:** Take your top 8–12 service keyword patterns × number of target cities = city keyword list

**Example — Kitchen Remodeling × Cities (abbreviated):**
```
kitchen remodel Danville
kitchen remodeling Danville
kitchen renovation Danville
kitchen remodeler Danville
kitchen remodel Lafayette
kitchen remodeling Lafayette
kitchen renovation Lafayette
kitchen remodeler Lafayette
kitchen remodel Walnut Creek
kitchen remodeling Walnut Creek
kitchen renovation Walnut Creek
kitchen remodeler Walnut Creek
kitchen remodel Alamo
kitchen remodeling Alamo
kitchen remodel Orinda
kitchen remodeling Orinda
kitchen remodel Moraga
kitchen remodeling Moraga
kitchen remodel Pleasanton
kitchen remodeling Pleasanton
kitchen remodel San Ramon
kitchen remodeling San Ramon
kitchen remodel Dublin
kitchen remodeling Dublin
```

Repeat this pattern for every service (bathroom, whole home, additions, etc.).

---

### Step 3.5 — Build Neighborhood-Specific Keywords

Higher specificity = higher intent = better lead quality. These keywords typically have very low volume individually but exceptional conversion rates.

**Pattern:** `[service] [neighborhood name]`

**Example — Ridgecrest Designs neighborhood keywords:**
```
kitchen remodel Blackhawk
kitchen remodeling Blackhawk
kitchen renovation Blackhawk
bathroom remodel Blackhawk
home remodel Blackhawk
kitchen remodel Diablo CA
kitchen remodel Alamo CA
home renovation Alamo
luxury remodel Orinda
kitchen renovation Orinda
bathroom renovation Orinda
home remodel Sleepy Hollow Orinda
kitchen remodel Rossmoor
bathroom remodel Rossmoor
home renovation Ruby Hill
kitchen remodel Ruby Hill Pleasanton
```

Include "CA" qualifier for neighborhoods that share names with other places nationally (Diablo, Dublin, etc.) to prevent keyword confusion.

---

### Step 3.6 — Document Every Keyword's Source and Volume

**Non-negotiable rule:** Every keyword added to the strategy file must have:
1. A verified search volume estimate
2. The source URL where that volume was checked
3. The date checked (data older than 90 days is stale for fast-moving markets)

**Volume verification sources (check at least 2 per keyword tier):**

| Tool | URL | Best For |
|------|-----|---------|
| KeySearch | https://www.keysearch.co | Local keyword volumes, competition scores |
| SEOpital | https://www.seopital.co | Keyword clustering, local intent signals |
| Marketkeep | https://www.marketkeep.com | Home services keyword benchmarks |
| AdTargeting | https://www.adtargeting.io | Google Ads keyword intelligence |
| SERPWARS | https://www.serpwars.com | SERP competitiveness for local terms |

**Documentation format in strategy file:**
```
| Keyword | Match Type | Est. Volume | Source URL | Date Checked |
|---------|------------|-------------|------------|--------------|
| kitchen remodel Danville | Broad | 50-100/mo | https://www.keysearch.co/... | 2026-04-10 |
| kitchen remodeling Danville | Broad | 30-70/mo | https://www.keysearch.co/... | 2026-04-10 |
```

**Volume interpretation for local markets:**
- 0–10/mo: Include only if high commercial intent, note low volume risk
- 10–100/mo: Good target range for local contractor terms
- 100–1,000/mo: High volume — verify match type and negatives are tight
- 1,000+/mo: Potentially too broad — investigate if modifier is needed

---

### Step 3.7 — All Keywords Are Broad Match

In Google Ads, add all keywords WITHOUT brackets or quotes. Broad match format is simply the keyword text.

**In Google Ads Scripts:**
```javascript
adGroup.newKeywordBuilder()
  .withText("kitchen remodel Danville")  // No quotes, no brackets = broad match
  .withCpc(3.50)
  .build();
```

**Why broad match for local contractors (full rationale):**
- Local service keywords like "kitchen remodel Danville" often have exact match search volumes of <10/month — too low to trigger reliably with exact match
- Broad match captures variants: "kitchen remodeling company Danville CA", "Danville kitchen remodel estimate", "best kitchen remodeler near Danville"
- Geo targeting at the zip code level limits the geographic spread that makes broad match risky in national campaigns
- Comprehensive negative keyword lists (Section 4) filter out the irrelevant broad match traffic
- Result: significantly more impressions, more data, more optimization opportunities — without sacrificing lead quality when negatives are maintained

**Do not second-guess this decision in the field.** If a keyword is generating irrelevant traffic, the answer is to add negatives — not to switch to exact match.

---

## Section 4: Negative Keyword Strategy

### Overview

Negative keywords protect budget from wasted clicks. For local contractor campaigns, the negative list is often as important as the positive keyword list. Maintain these at the campaign level (not ad group level) unless a specific ad group needs its own exclusion.

**Sources:**
- [groas.ai 2026 master negative keyword list](https://groas.ai)
- BG Collective remodeler negative keyword guide
- ClicksGeek home improvement negative keyword guide
- Ongoing additions from weekly search term reports

---

### Category 1: Job Seekers (30 terms)

These searchers are looking for employment, not services.

```
job
jobs
career
careers
hiring
hire
employment
work
salary
salaries
wages
wage
hourly
pay rate
benefits
apply
application
apply now
job listing
job posting
open position
positions available
apprentice
apprenticeship
journeyman
foreman
crew
subcontractor
sub contractor
1099
```

---

### Category 2: DIY / How-To (35 terms)

These searchers want to do the work themselves.

```
DIY
do it yourself
how to
how do I
tutorial
step by step
guide
instructions
tips
ideas
inspiration
plans
blueprint
design ideas
before and after
video
youtube
reddit
forum
community
advice
learn
training
workshop
course
class
lessons
self build
owner builder
permit yourself
build your own
install yourself
replace yourself
fix yourself
repair yourself
```

---

### Category 3: Free / Cheap / Budget (29 terms)

For **luxury-positioned** clients, add all 29. For mid-range clients, remove "affordable". For budget clients, remove all.

```
free
cheap
cheapest
budget
bargain
discount
discounted
sale
clearance
low cost
low price
lowest price
best price
price match
coupon
coupons
promo
promotion
deal
deals
special offer
going out of business
closeout
liquidation
economical
inexpensive
no cost
at cost
cost effective
```

**RIDGECREST DESIGNS RULE:** "affordable" is a permanent negative. "affordable" does not appear in this list above because it must be added separately and never removed. See Section 12, Rule 12.

---

### Category 4: Education (22 terms)

These searchers are students or professionals seeking training — not homeowners seeking contractors.

```
university
college
school
trade school
vo-tech
vocational
community college
certification
certificate
certified
license exam
exam
test
degree
associate degree
bachelor
program
curriculum
textbook
online course
accredited
OSHA training
```

---

### Category 5: Wholesale / Supplies (18 terms)

These searchers want materials, not labor.

```
wholesale
supplies
supply
materials
material
lumber
hardware
home depot
lowes
menards
build.com
cabinet depot
tile shop
flooring depot
granite yard
stone supplier
countertop supplier
plumbing supply
```

---

### Category 6: Commercial / Industrial (12 terms)

Unless the client explicitly serves commercial clients, exclude:

```
commercial
industrial
office building
restaurant
retail
warehouse
hotel
hospital
school building
multi-unit
apartment complex
condo complex
```

---

### Category 7: Non-Offered Services (Customize Per Client)

This list is built from the intake form Question 2 "NOT offered" services. Every service the client does not offer becomes a negative keyword.

**Example — Ridgecrest Designs non-offered services:**
```
roofing
roof
roofer
roof repair
roof replacement
plumbing
plumber
plumber near me
drain
sewer
HVAC
heating
cooling
air conditioning
AC repair
furnace
electrical
electrician
wiring
painting
painter
paint
landscaping
landscape
lawn
sprinkler
fence
fencing
driveway
asphalt
garage door
window replacement (if not offered)
carpet
flooring (if not offered)
```

**Process for building this list:**
1. Take client's "NOT offered" list from intake
2. For each service, generate 3–5 variants (service, servicer, "service near me", etc.)
3. Add all variants as negatives

---

### Category 8: Irrelevant Modifiers (from Search Term Reports)

These are discovered over time by reading weekly search term reports. Common ones to start with:

```
mobile home
manufactured home
RV
tiny house
tiny home
trailer
modular home
cabin
barn
shed
container home
prefab
kit home
vacation home (unless client serves vacation markets)
rental property (unless client serves landlords)
```

**Process:** Pull search terms report weekly. For any term that generated a click but zero conversions, evaluate: is this irrelevant? If yes, add the problematic component as a negative. Document the date added and the triggering search term.

---

### Category 9: Competitor Aggregators (7 terms)

These searchers are going to aggregator platforms, not looking for a single contractor.

```
angi
angi's list
angies list
thumbtack
homeadvisor
home advisor
houzz
yelp
porch
taskrabbit
bark
networx
buildzoom
```

---

### Category 10: Brand Safety (14 terms)

Prevent ads from appearing in unsafe contexts.

```
porn
pornography
gambling
casino
bet
betting
scam
fraud
fraudulent
lawsuit
illegal
piracy
hack
hacking
```

---

### Negative Keyword Management Rules

1. **Campaign-level negatives** (Categories 1–6, 9–10): Apply to the campaign. Do not add at ad group level unless ad group-specific.
2. **Service-specific negatives** (Category 7): Apply at campaign level.
3. **Modifier negatives** (Category 8): Add as discovered from search term reports. Document each addition in `CURRENT_STATUS.md`.
4. **Match type for negatives:** Use phrase match `[in quotes]` for most negatives so you catch variants. Use exact match `[in brackets]` for words that appear legitimately in some queries (e.g., if "free estimate" is an offer, don't make "free" an exact negative — make it phrase match with exceptions).
5. **Review schedule:** Check search terms report every 7 days for the first 60 days. After 60 days, monthly review is acceptable.

---

## Section 5: Ad Group Structure

### Overview

One campaign per client (for most small contractors). Multiple themed ad groups within the campaign. Each ad group represents a service theme — distinct headlines, distinct keywords, distinct landing page destination.

**Why this structure works:**
- Ad relevance: Google scores quality based on how well the keyword matches the ad matches the landing page. A "kitchen remodel" keyword in a kitchen-specific ad group pointing to a kitchen landing page scores better than all services lumped together.
- Optimization visibility: You can see which themes produce leads vs. which produce zero conversions
- Bid control: Future bid adjustments can be applied at ad group level if one theme is more profitable than another
- Easier maintenance: Adding new kitchen keywords doesn't affect bathroom ad group performance

---

### Standard Ad Group Structure for Remodeling Contractor

```
[PREFIX] [CLIENT] — Search Campaign
├── [PREFIX] Kitchen
├── [PREFIX] Bathroom
├── [PREFIX] Whole Home / Full Renovation
├── [PREFIX] Design-Build
├── [PREFIX] Additions / ADU
├── [PREFIX] Interior Design / Architecture
└── [PREFIX] General Contractor / Neighborhood
```

**Example — Ridgecrest Designs with [PX] prefix:**
```
[PX] Ridgecrest Designs — Search
├── [PX] Kitchen
├── [PX] Bathroom
├── [PX] Whole Home
├── [PX] Design-Build
├── [PX] Additions ADU
├── [PX] Interior Design
└── [PX] Neighborhood GC
```

---

### RSA Ad Requirements

Every ad group gets one Responsive Search Ad (RSA). Requirements:

| Element | Requirement | Hard Limit |
|---------|-------------|------------|
| Headlines | Minimum 15 | Maximum 15 |
| Descriptions | Minimum 4 | Maximum 4 |
| Headline length | Must verify before deploying | 30 characters max |
| Description length | Must verify before deploying | 90 characters max |
| Headline 1 pin | Brand name (pinned, not rotated) | Required |

**CHARACTER COUNT IS NON-NEGOTIABLE.** Google will reject any headline over 30 characters or description over 90 characters. Count every character including spaces. Always verify with a character counter before deploying. When in doubt, count again.

**Example character counting:**
- "Award-Winning Kitchen Remodels" = 30 characters ✓ (exactly at limit)
- "Award-Winning Kitchen Remodeling" = 32 characters ✗ (2 over limit)
- "Luxury Kitchen Remodel Experts" = 30 characters ✓

---

### RSA Template — Kitchen Ad Group

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓  
**Headlines 2–15 (rotated):**

```
Award-Winning Kitchen Remodels      (30 chars) ✓
Custom Kitchen Renovations          (28 chars) ✓
Luxury Kitchen Remodel Experts      (30 chars) ✓
Walnut Creek Kitchen Remodeler      (30 chars) ✓
Free In-Home Kitchen Estimate       (30 chars) ✓
Danville Kitchen Renovation Pros    (32 chars) ✗ — SHORTEN
East Bay Kitchen Remodeling         (27 chars) ✓
Trusted Local Kitchen Contractor    (31 chars) ✗ — SHORTEN
High-End Kitchen Transformations    (31 chars) ✗ — SHORTEN
Kitchen Design-Build Specialists    (31 chars) ✗ — SHORTEN
Custom Cabinets and Countertops     (30 chars) ✓
Full Kitchen Gut Renovations        (29 chars) ✓
Licensed Kitchen Remodel Pros       (29 chars) ✓
Bay Area Kitchen Remodeling         (27 chars) ✓
```

*(Any headlines marked ✗ must be shortened before deploying. This example intentionally shows the verification process — always run this check.)*

**Corrected versions:**
```
Danville Kitchen Renovation         (27 chars) ✓
Trusted Kitchen Contractor          (26 chars) ✓
Premium Kitchen Transformations     (30 chars) ✓
Kitchen Design-Build Service        (28 chars) ✓
```

**Descriptions (4 required, 90 chars max each):**

```
Description 1 (88 chars):
Transform your kitchen with Contra Costa's premier remodeling team. Free estimates.

Description 2 (86 chars):
Custom kitchens designed for how you live. Licensed, insured, 5-star rated. Call today.

Description 3 (84 chars):
From concept to completion — we handle design, permits, and build. No surprises.

Description 4 (89 chars):
Serving Danville, Walnut Creek, Lafayette, Orinda, and surrounding areas. Call now.
```

**Verify every description is under 90 characters before entry.**

---

### RSA Template — Bathroom Ad Group

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓

**Headlines 2–15 (rotated, verified):**
```
Custom Bathroom Remodeling          (26 chars) ✓
Luxury Bathroom Renovation          (26 chars) ✓
Award-Winning Bath Remodels         (27 chars) ✓
Master Bath Renovation Experts      (28 chars) ✓
Spa-Style Bathroom Transformations  (33 chars) ✗ — SHORTEN
Free Bathroom Remodel Estimate      (28 chars) ✓
Walnut Creek Bathroom Remodeler     (29 chars) ✓
East Bay Bathroom Renovation        (27 chars) ✓
Luxury Master Suite Remodels        (28 chars) ✓
Full Bath Gut Renovations           (25 chars) ✓
Custom Tile and Shower Design       (28 chars) ✓
Licensed Bathroom Remodelers        (28 chars) ✓
Bay Area Bathroom Renovation        (27 chars) ✓
High-End Bathroom Remodeling        (27 chars) ✓
```

*(Corrected: "Spa-Style Bathroom Remodels" = 26 chars ✓)*

---

### RSA Template — Whole Home / Full Renovation Ad Group

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓

**Headlines 2–15:**
```
Whole Home Remodeling Experts       (29 chars) ✓
Full Home Renovation Specialists    (30 chars) ✓
Complete Home Transformation        (27 chars) ✓
Luxury Whole Home Renovations       (28 chars) ✓
East Bay Home Remodeling            (24 chars) ✓
Free Whole Home Remodel Estimate    (30 chars) ✓
Licensed Home Renovation Team       (27 chars) ✓
Custom Home Remodels in Danville    (30 chars) ✓
Award-Winning Home Renovations      (28 chars) ✓
Full Home Gut Renovation Pros       (28 chars) ✓
Multi-Room Home Remodeling          (26 chars) ✓
Home Renovation from Start to End   (30 chars) ✓
High-End Whole Home Remodeling      (28 chars) ✓
Walnut Creek Home Remodel Pros      (28 chars) ✓
```

---

### RSA Template — Design-Build Ad Group

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓

**Headlines 2–15:**
```
Design-Build Remodeling Firm        (27 chars) ✓
All-in-One Design and Build         (26 chars) ✓
Concept to Completion Remodels      (28 chars) ✓
Custom Design-Build Contractor      (28 chars) ✓
Architect and Builder in One        (26 chars) ✓
Luxury Design-Build Services        (27 chars) ✓
No-Surprise Design Build Projects   (30 chars) ✓
Award-Winning Design-Build Firm     (28 chars) ✓
Bay Area Design Build Specialist    (28 chars) ✓
Free Design Consultation            (24 chars) ✓
Residential Design-Build Experts    (29 chars) ✓
High-End Home Design and Build      (28 chars) ✓
Licensed Design-Build Contractor    (29 chars) ✓
East Bay Design-Build Remodeling    (28 chars) ✓
```

---

### RSA Template — Additions / ADU Ad Group

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓

**Headlines 2–15:**
```
Home Addition Contractor            (23 chars) ✓
ADU Builder and Contractor          (24 chars) ✓
Granny Flat Construction            (23 chars) ✓
Room Addition Specialists           (24 chars) ✓
Licensed ADU Contractor             (22 chars) ✓
Add Square Footage to Your Home     (28 chars) ✓
Garage Conversion Specialist        (28 chars) ✓
ADU Design and Build Services       (27 chars) ✓
Second Unit Contractor East Bay     (28 chars) ✓
Free ADU Design Estimate            (25 chars) ✓
Bump-Out and Addition Experts       (27 chars) ✓
Master Suite Addition Contractor    (28 chars) ✓
In-Law Suite Construction           (25 chars) ✓
Danville ADU and Addition Pros      (28 chars) ✓
```

---

### RSA Template — Interior Design / Architecture Ad Group

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓

**Headlines 2–15:**
```
Residential Interior Design         (27 chars) ✓
Full-Service Interior Designers     (28 chars) ✓
Luxury Home Interior Design         (25 chars) ✓
Home Renovation with Design         (25 chars) ✓
Architecture and Interior Design    (29 chars) ✓
Custom Home Design Services         (25 chars) ✓
Award-Winning Interior Designers    (28 chars) ✓
East Bay Interior Design Firm       (27 chars) ✓
Free Interior Design Consultation   (30 chars) ✓
Kitchen and Bath Design Experts     (28 chars) ✓
Whole Home Interior Designers       (27 chars) ✓
Licensed Architecture Services      (28 chars) ✓
Contemporary Home Design Experts    (29 chars) ✓
Danville Interior Design Pros       (27 chars) ✓
```

---

### RSA Template — General Contractor / Neighborhood Ad Group

This ad group captures broad "general contractor" queries and neighborhood-specific terms.

**Headline 1 (PINNED):** `Ridgecrest Designs` (18 chars) ✓

**Headlines 2–15:**
```
Danville General Contractor         (25 chars) ✓
Walnut Creek Remodeling Pros        (28 chars) ✓
Blackhawk Home Remodeling           (25 chars) ✓
Alamo Remodeling Contractor         (26 chars) ✓
Orinda Home Renovation Experts      (28 chars) ✓
Lafayette Remodeling Contractor     (29 chars) ✓
Diablo Home Remodeling              (22 chars) ✓
Moraga Remodeling Specialist        (27 chars) ✓
Free Estimate — Call Today          (25 chars) ✓
East Bay Licensed Contractor        (27 chars) ✓
5-Star Rated General Contractor     (28 chars) ✓
Luxury Home Remodeling Service      (28 chars) ✓
Award-Winning East Bay Remodeler    (28 chars) ✓
Serving Contra Costa County         (27 chars) ✓
```

---

## Section 6: Campaign Assets

### Overview

Assets (formerly "extensions") expand your ads with additional information and links. They increase click-through rate, improve Ad Rank, and provide more paths for users to contact the client. Apply assets at the campaign level so they appear across all ad groups, then supplement with ad-group-level image assets.

---

### Campaign-Level Assets (Apply to All Ad Groups)

#### Sitelinks (Minimum 4 Required)

Each sitelink needs: link text (25 chars max), description line 1 (35 chars max), description line 2 (35 chars max), and URL.

| Link Text | Desc Line 1 | Desc Line 2 | URL |
|-----------|-------------|-------------|-----|
| Kitchen Remodeling | Custom kitchens designed to order | Licensed, insured, 5-star rated | /kitchen-remodeling |
| Bathroom Remodeling | Spa-style baths and master suites | Free in-home estimate available | /bathroom-remodeling |
| Home Additions & ADU | Add space and value to your home | Granny flats, room additions | /additions |
| About Ridgecrest | Award-winning contractor since [YEAR] | See our portfolio and reviews | /about |
| Free Estimate | No cost, no obligation estimate | We come to you — call or book | /contact |
| Our Portfolio | See completed kitchen and bath work | Before and after project photos | /portfolio |

**Verify every URL actually exists on the client's website before adding.**

#### Callout Assets (Minimum 4, Maximum 25 Characters Each)

```
Licensed and Insured          (20 chars) ✓
5-Star Google Reviews         (21 chars) ✓
Free In-Home Estimates        (22 chars) ✓
East Bay Since [YEAR]         (varies)   ✓
No Subcontractors             (17 chars) ✓
On-Time and On Budget         (21 chars) ✓
Family-Owned Business         (21 chars) ✓
Award-Winning Design          (20 chars) ✓
```

Add up to 20 callouts. Google rotates them. More callouts = more variety in what users see.

#### Structured Snippets (Minimum 3 Values)

Header type: **Services**

```
Services: Kitchen Remodeling, Bathroom Remodeling, Home Additions, ADU Construction, Design-Build, Whole Home Renovation
```

Add additional headers if applicable:
- **Neighborhoods served:** Danville, Walnut Creek, Lafayette, Orinda, Alamo, Blackhawk, Diablo, Moraga

#### Call Asset

```
Phone number: [CLIENT PHONE FROM INTAKE]
Conversion action: link to "Phone Call" conversion action
Schedule: match client staffed hours from intake
```

---

### Ad Group-Level Image Assets

**Purpose:** Image assets display in responsive display format within search results on some placements. Ad-group-level image assets improve relevance (kitchen images in kitchen ad group, bathroom images in bathroom ad group).

**Requirements:**
- Minimum 4 images per ad group
- Mix of 1:1 square format (min 300×300px, recommended 1200×1200px) and 1.91:1 landscape format (min 600×314px, recommended 1200×628px)
- Must be high quality, professional photos — not stock photos if possible
- No text overlays exceeding 20% of image area
- Must show the actual service (kitchen for kitchen ad group, etc.)

**Image sourcing process:**
1. First ask client for professional project photos
2. If client has a Houzz or portfolio page, request original files (not web-compressed versions)
3. Upload to Google Ads > Assets library before linking to ad groups
4. Link at ad group level, not campaign level, for relevance

**Eligibility requirement:**
Google requires the account be open for 60+ days AND have had active Search spend in the last 28 days before image assets are approved. Plan accordingly — do not expect image assets to show immediately on new accounts.

---

## Section 7: Geo Targeting

### The Most Important Rule

**Use PRESENCE targeting only.** Never use PRESENCE_OR_INTEREST.

In Google Ads campaign settings:
- Location targeting option: "People in or regularly in your targeted locations" (**PRESENCE**)
- NOT: "People in, regularly in, or who've shown interest in your targeted locations" (PRESENCE_OR_INTEREST)

PRESENCE_OR_INTEREST will serve your ads to people in Seattle who searched for "kitchen remodel Danville" — they are not going to hire your Danville contractor. This wastes budget and distorts performance data.

---

### Geo Targeting Setup Process

#### Step 1: Download Official Geo Targets CSV

URL: https://developers.google.com/google-ads/api/data/geotargets  
File: `geotargets-[date].csv`  
Save to server: `campaigns/[CLIENT_SLUG]/geo_targets_verified.csv`

#### Step 2: Verify Each Zip Code

For every zip code from client intake:
1. Open the CSV
2. Filter by Target Type = "Postal Code"
3. Find the zip — confirm it exists in Google's system
4. Record the Google-assigned Criterion ID (needed for API/Script targeting)
5. Record the city name Google assigns to that zip

**If a zip code does not appear in the CSV:** Do not add it to geo targeting. Contact Google support or use the next closest zip that covers the same area.

#### Step 3: Add Zip Codes to Campaign

**Via Google Ads UI:**
1. Campaign → Settings → Locations
2. Search for each zip code individually
3. Add as target (not exclusion)
4. Verify PRESENCE-only setting in "Location options"

**Via Google Ads Script:**
```javascript
// GEO TARGETING SCRIPT — RIDGECREST DESIGNS
// Verified zip codes for Contra Costa County service area
// Source: Google Geo Targets CSV, verified 2026-04-10

var TARGET_ZIP_CODES = [
  "94507",  // Alamo
  "94523",  // Pleasant Hill
  "94526",  // Danville
  "94528",  // Diablo
  "94531",  // Antioch
  "94549",  // Lafayette
  // 94553 EXCLUDED — Martinez per client instruction
  "94556",  // Moraga
  "94563",  // Orinda
  "94564",  // Pinole
  "94565",  // Pittsburg
  "94566",  // Pleasanton
  "94568",  // Dublin
  "94582",  // San Ramon
  "94583",  // San Ramon
  "94595",  // Walnut Creek
  "94596",  // Walnut Creek
  "94597",  // Walnut Creek
  "94598"   // Walnut Creek
];

// NOTE: Script to add location targeting requires Google Ads API, 
// not available via Apps Script. Use UI for zip code targeting.
// This array documents the verified target list for reference.

Logger.log("Target zips: " + TARGET_ZIP_CODES.join(", "));
Logger.log("Total zips: " + TARGET_ZIP_CODES.length);
Logger.log("EXCLUDED: 94553 (Martinez) — client instruction");
```

#### Step 4: Document the Zip-to-City Mapping

Save this mapping to `campaigns/[CLIENT_SLUG]/zip_city_mapping.md`. This is the canonical reference. When writing city keywords, refer to this document — never guess city names from memory.

```markdown
## [CLIENT] Zip Code to City Mapping
Source: Google Geo Targets CSV (downloaded [DATE])

| Zip Code | City Name (Google) | Status | Notes |
|----------|-------------------|--------|-------|
| 94507 | Alamo | ACTIVE | |
| 94523 | Pleasant Hill | ACTIVE | |
| 94526 | Danville | ACTIVE | |
| 94528 | Diablo | ACTIVE | Very affluent, low volume |
| 94531 | Antioch | ACTIVE | |
| 94549 | Lafayette | ACTIVE | |
| 94553 | Martinez | EXCLUDED | Client instruction |
| 94556 | Moraga | ACTIVE | |
| 94563 | Orinda | ACTIVE | |
| 94564 | Pinole | ACTIVE | |
| 94565 | Pittsburg | ACTIVE | |
| 94566 | Pleasanton | ACTIVE | |
| 94568 | Dublin | ACTIVE | |
| 94582 | San Ramon | ACTIVE | |
| 94583 | San Ramon | ACTIVE | Same city as 94582 |
| 94595 | Walnut Creek | ACTIVE | |
| 94596 | Walnut Creek | ACTIVE | |
| 94597 | Walnut Creek | ACTIVE | |
| 94598 | Walnut Creek | ACTIVE | |
```

#### Step 5: Exclude Problem Locations

After verifying, add location exclusions if needed:
- Any zip codes that map to cities the client explicitly excludes (e.g., 94553/Martinez)
- Any neighboring counties that show up in impression data but are outside service area
- Once set, do not remove exclusions without explicit client approval

---

## Section 8: Ad Schedule and Bidding

### Default Ad Schedule Setup

Run campaigns 7 days a week with time-of-day bid adjustments. Do not restrict to fewer days unless client has a strong business reason — and if you do restrict days, lower the daily budget to compensate (see March 2026 pacing change below).

#### Time Block Structure

| Day | Time Block | Bid Adjustment |
|-----|-----------|---------------|
| Mon–Fri (Primary) | 6am–6pm | Base bid (0%) |
| Mon–Fri (Primary) | 6pm–10pm | +20% (peak window) |
| Mon–Fri | 10pm–6am | -50% (overnight) |
| Sat–Sun (Secondary) | 8am–6pm | -25% |
| Sat–Sun (Secondary) | 6pm–10pm | Base bid (0%) |
| Sat–Sun | 10pm–8am | -50% (overnight) |

**Why the 6–10pm evening boost:**
Studies from [Zahavian Legal Marketing](https://zahavian.com), [ClicksGeek](https://clicksgeek.com), and [RapportAgent](https://rapportagent.com) consistently show that 6–10pm is the peak conversion window for home service businesses. Homeowners research and contact contractors after dinner, when they have time to think about home improvement. The +20% bid increase during this window captures more of these high-intent searchers.

**Adjust these defaults based on client input.** If the client says "we get most calls on Saturday morning," increase Saturday bids. If they say "we never get leads on Sunday," reduce Sunday bids further. Use data, not defaults, once 30+ days of data are available.

---

### March 2026 Pacing Change — Critical

**What changed:** As of approximately March 2026, Google Ads attempts to spend 30.4× the daily budget over the course of a calendar month, regardless of the ad schedule settings. Previously, restricted schedules meant proportionally lower monthly spend. This is no longer the case.

**Impact:** If you set a $100/day budget but only run ads Mon–Fri (5/7 days), Google will still attempt to spend $100 × 30.4 = $3,040 that month — not $100 × 22 weekdays = $2,200 as you might expect.

**What to do:**
- If running 7 days/week: Set daily budget = monthly budget ÷ 30.4 (no adjustment needed)
- If running 5 days/week: Set daily budget = (monthly budget × 5/7) ÷ 30.4 — or alternatively, run 7 days with lower off-day bids
- If running 3 days/week: Set daily budget = (monthly budget × 3/7) ÷ 30.4

**Recommended approach:** Run 7 days/week with bid adjustments rather than schedule restrictions. This avoids the pacing math and provides more data points for optimization.

**Reference:** `competitors/ad_schedule_research_2026_04_11.md`

---

### Bid Strategy by Account Maturity

| Account Age | Conversion Data | Recommended Bid Strategy |
|-------------|----------------|--------------------------|
| New account (0–30 days) | No conversions yet | Manual CPC with enhanced CPC (eCPC) |
| Growing (30–90 days) | 1–29 conversions/month | Manual CPC with eCPC, begin collecting data |
| Established (90+ days) | 30+ conversions/month | Target CPA or Maximize Conversions |
| Mature (6+ months) | 50+ conversions/month | Target CPA with refined targets |

**Do not use Target CPA until the account has at least 30 conversions in the last 30 days.** Google's algorithm needs this minimum data to optimize. Running Target CPA before this threshold results in erratic spending and delivery gaps.

**Starting CPCs for new campaigns:**
- Kitchen remodeling: $3.00–$6.00 max CPC starting point
- Bathroom remodeling: $2.50–$5.00
- Home additions/ADU: $3.00–$5.50
- General contractor: $2.00–$4.00

Adjust within 14 days based on actual CPC data from impressions. If keywords get zero impressions after 14 days, either CPC is too low or keyword quality score is poor — investigate before increasing budget.

---

## Section 9: Conversion Tracking

### Overview

Without conversion tracking, you are flying blind. Every campaign must have at least one verified, working conversion action before launch. Delay the launch, not the conversion setup.

### Step 9.1 — Identify the Primary Conversion Action

From client intake, determine:
- **Form submission:** Typical for "request a quote" or "contact us" forms
- **Phone call from ad:** Call asset clicks tracked as conversions
- **Phone call from website:** Calls made after clicking to the website, tracked via Google tag

For most remodeling contractors: primary conversion = form submission OR phone call (set up both, count both in conversions).

### Step 9.2 — Set Up Conversion Tracking in Google Ads

**Via Google Ads UI:**
1. Tools → Measurement → Conversions
2. Click "New conversion action"
3. Select: Website (for form submissions) or Phone calls (for call tracking)
4. Configure settings:
   - Category: Contact (for leads)
   - Count: One (count one conversion per click, not every repeat form submission)
   - Click-through conversion window: 30 days
   - Engaged-view conversion window: 1 day
   - `Include in conversions`: **YES** — verify this is ON
   - Attribution model: Data-driven (if available), otherwise Last click
5. Save and get the tag/snippet

**Verify `includeInConversionsMetric = true`:**
This setting controls whether the conversion is used in the "Conversions" column and whether it feeds smart bidding. If this is OFF (set to "Observation only"), the conversions don't count for bidding — your automated bids will behave as if no conversions exist.

Check via:
1. Tools → Measurement → Conversions
2. Click on the conversion action
3. Look for "Include in conversions" setting — must say "Yes"

**Via Script (audit only):**
```javascript
// Verify conversion action settings
function main() {
  var convActions = AdsApp.conversionActions().get();
  while (convActions.hasNext()) {
    var ca = convActions.next();
    Logger.log(
      "Name: " + ca.getName() + "\n" +
      "  Status: " + (ca.isEnabled() ? "ENABLED" : "DISABLED") + "\n" +
      "  Include in conversions: " + ca.includeInConversionsMetric() + "\n" +
      "  Category: " + ca.getCategory() + "\n"
    );
  }
}
```

### Step 9.3 — Install the Tag

**For Google Tag (gtag.js):**
1. Install the base Google tag on all pages of the client's website (via Google Tag Manager or direct code insertion)
2. Install the event snippet on the "thank you" page that appears after form submission

**For Google Tag Manager (recommended):**
1. Create GTM account for client
2. Install GTM container snippet on all pages
3. Create a Tag → Google Ads Conversion Tracking
4. Create a Trigger → Page View → URL contains "/thank-you" (or whatever the confirmation URL is)
5. Publish

**For CallRail or similar call tracking:**
1. Get the Google Ads import configured in CallRail
2. Verify calls are flowing to Google Ads conversions column
3. Set call length threshold (recommended: 60 seconds for quality lead calls)

### Step 9.4 — Test Before Launch

**Test form submission conversion:**
1. Go to the client's website from a non-logged-in browser
2. Submit the contact form with test data
3. Wait 30 minutes
4. Check Google Ads → Reports → Conversions to see if a conversion registered
5. If yes: conversion tracking is working. If no: debug the tag installation.

**Google Tag Assistant:**
Install the Chrome extension "Google Tag Assistant" to verify tags are firing correctly on each page.

**Required before launch:**
- [ ] At least one conversion action with `includeInConversionsMetric = true`
- [ ] Tag verified firing on confirmation/thank-you page
- [ ] Test conversion registered in Google Ads
- [ ] Call asset linked to phone call conversion action

---

## Section 10: Monitoring and Optimization

### Overview

Campaign monitoring follows a structured schedule. Each phase has specific tasks. Do not skip phases — the 14-day check is not optional.

---

### Week 1: Launch Verification

**Goal:** Confirm the campaign is delivering. Catch obvious problems early.

| Task | How to Check | What's Normal | Red Flag |
|------|-------------|---------------|----------|
| Campaign serving | Check status column | "Eligible" or "Active" | "Limited" or "Disapproved" |
| Disapproved ads | Ads tab → filter by Disapproval | Zero disapprovals | Any disapprovals |
| Impressions | Campaign overview tab | Some impressions by day 2 | Zero impressions after 48 hours |
| Budget spending | Budget column | Spending close to daily budget | Spending 0% or >120% |
| Keyword quality scores | Keywords tab → QS column | 5–10 range | Consistent 1–3 |
| Conversion tag firing | Google Tag Assistant | Green checkmarks | Red X's |

**Day 1 check script — quick health check:**
```javascript
function main() {
  var yesterday = getDateRange(1);
  var campaigns = AdsApp.campaigns()
    .withCondition("Name CONTAINS '[PX]'")  // Change prefix to yours
    .get();
    
  while (campaigns.hasNext()) {
    var c = campaigns.next();
    var stats = c.getStatsFor("YESTERDAY");
    Logger.log(
      "Campaign: " + c.getName() + "\n" +
      "  Impressions: " + stats.getImpressions() + "\n" +
      "  Clicks: " + stats.getClicks() + "\n" +
      "  Cost: $" + stats.getCost().toFixed(2) + "\n" +
      "  CTR: " + (stats.getCtr() * 100).toFixed(2) + "%\n"
    );
  }
}

function getDateRange(daysBack) {
  var today = new Date();
  today.setDate(today.getDate() - daysBack);
  return Utilities.formatDate(today, AdsApp.currentAccount().getTimeZone(), "yyyyMMdd");
}
```

---

### Week 2: First Search Terms Report Review

**Pull the search terms report:**
1. Keywords → Search terms tab
2. Filter: Date range = Last 7 days
3. Export to CSV
4. Review every term

**For each search term, evaluate:**
- Is this relevant? (yes/no)
- If yes: does it belong in its current ad group, or should a new ad group be created?
- If no: what negative keyword would block it?

**Add new negatives immediately.** For each irrelevant term, identify the specific word or phrase that makes it irrelevant, add that as a negative (not the entire search term — find the problematic component).

**Check quality scores:**
- QS 8–10: Excellent — no action needed
- QS 5–7: Average — consider improving ad copy or landing page relevance
- QS 1–4: Poor — investigate immediately. Poor QS means high CPCs and limited delivery.

QS improvement actions:
- Improve ad copy to better match keywords in the ad group
- Create a more specific landing page for the ad group's theme
- Move mismatched keywords to a more appropriate ad group

---

### Week 3+: Ad Group Performance Review

**The 14-Day Rule:**
Any keyword that has received zero impressions after 14 days gets flagged for review.

Possible causes:
1. Quality Score too low to enter auctions
2. Max CPC too low to compete
3. Search volume too low (term barely searched in this market)
4. Keyword triggering a policy hold

**Investigation process:**
1. Check keyword status — hover over status bubble for explanation
2. Check quality score — if QS is N/A, the keyword hasn't triggered enough auctions to be rated
3. Check Keyword Planner for this term in the target geo — is there any volume?
4. If volume exists but no impressions, raise CPC by 20% and wait another 7 days
5. If still no impressions after raising CPC, consider removing the keyword or replacing with a broader variant

**Ad group-level performance evaluation:**
After 30 days, sort ad groups by conversions. Identify:
- High-converting ad groups: Consider increasing budget allocation (via portfolio bids or separate campaigns)
- Zero-conversion ad groups: Do not kill immediately — check if impressions are occurring. If impressions exist but no conversions, the issue may be landing page quality, not keyword quality.
- Zero-impression ad groups: Keyword QS issue or CPC too low — investigate

---

### Weekly: Auction Insights Report

Pull weekly to track competitive landscape:
1. Select your campaign or ad groups
2. Click "Auction insights" in the toolbar
3. Review:
   - **Impression share:** How often you appear vs. how often you could appear
   - **Overlap rate:** How often a competitor appears when you do
   - **Position above rate:** How often competitor appears above you
   - **Top-of-page rate:** How often you appear in top positions

**Document in:** `competitors/auction_insights_[CLIENT]_[DATE].md`

**Target benchmarks for local contractor campaigns:**
- Impression share: 30–60% (100% is rarely achievable or cost-effective in local)
- Top-of-page rate: 60%+
- Lost impression share (budget): Below 20%
- Lost impression share (rank): Below 30%

---

### Monthly: Budget and CPC Review

1. **Budget utilization:** If spending less than 90% of daily budget consistently, the campaign is restricted somewhere (QS issue, low bids, limited search volume). Investigate.
2. **CPC trends:** Are CPCs rising? Competitor activity may be increasing. Check Auction Insights for new entrants.
3. **Conversion rate trends:** If conversion rate drops, check the landing page for changes, check form functionality, check call tracking.
4. **Cost per lead:** Compare to client's acceptable CPL. Flag to account manager if trending above target.

**Monthly report format:**
```markdown
## Monthly Performance Report — [CLIENT] — [MONTH YEAR]

### Summary
- Total spend: $[X]
- Total conversions: [N]
- Cost per lead: $[X]
- Impression share: [X]%

### Top Converting Ad Groups
1. [Ad Group Name]: [N] conversions, $[X] CPL
2. [Ad Group Name]: [N] conversions, $[X] CPL

### Keywords to Pause (zero conversions, 30+ days, 100+ impressions)
- [keyword]
- [keyword]

### New Negatives Added This Month
- [term] — added [DATE] — triggered by search term: [ORIGINAL SEARCH]

### Recommended Changes for Next Month
- [RECOMMENDATION]
```

---

## Section 11: Competitive Intelligence

### Overview

Understanding the competitive landscape helps position the client's ads more effectively, identify gaps in competitor offerings, and ensure bids reflect actual competition levels.

---

### Step 11.1 — Auction Insights via Google Ads

**Pull process:**
1. Google Ads → Campaigns → select client campaign
2. Click "Auction insights" in the top bar
3. Date range: Last 30 days
4. Export the table

**What you learn:**
- Who is bidding on the same keywords
- How aggressive they are (overlap rate, top-of-page rate)
- Your impression share vs. theirs

**Document in:** `competitors/auction_insights_[CLIENT]_[YYYYMMDD].md`

---

### Step 11.2 — Competitor Website Research

For each competitor identified in Auction Insights:

1. **Visit their website.** Document:
   - Services offered (what do they serve that your client doesn't, and vice versa?)
   - Geographic focus (any cities they emphasize?)
   - Price signals (do they show prices? Do they use words like "luxury", "affordable", "premium"?)
   - Trust signals (years in business, number of projects, certifications, awards)
   - Lead capture method (form, phone, chat, phone only?)
   - Free estimate offer? (yes/no)

2. **Check their Google Business Profile:**
   - Review count and average rating
   - Review recency (are they getting new reviews or is the profile stale?)
   - Photos (professional? Recent?)
   - Q&A section (what are customers asking?)

3. **Check Houzz, Yelp, and Angi profiles** if present — collect same data points

**Document in:** `competitors/[COMPETITOR_DOMAIN]_research_[DATE].md`

---

### Step 11.3 — The Golf Course Method for Competitor Service Area Mapping

The same method used for keyword research (Section 3.2) can be used to understand where competitors focus their efforts:

1. Visit the competitor's website and note any city or neighborhood names mentioned
2. Search Google for `[competitor name] reviews [city]` for cities in the market
3. Search Google Maps for the competitor's address — where are they located relative to the service market?
4. If competitor mentions "Blackhawk" or "Alamo" specifically, they are targeting the same affluent neighborhoods — this is direct competition for luxury clients

**Competitive gap identification:**
If a competitor does not mention neighborhoods like Blackhawk, Diablo, or Orinda — but your client serves those areas — this is a keyword and positioning opportunity. Create neighborhood-specific ads that the competitor isn't running.

---

### Step 11.4 — Competitor Ad Research

**Using Google's Ad Transparency Center:**
1. Go to https://adstransparency.google.com
2. Search for the competitor's brand name
3. Review active ads — what messaging do they use? What offers?

**Manual method:**
1. Open Google Ads Preview Tool (Tools → Planning → Ad Preview and Diagnosis)
2. Enter target keywords
3. Set location to a target zip code
4. See which competitors appear and in what position

**Document findings in:** `competitors/[CLIENT]_ad_intelligence_[DATE].md`

Include:
- Competitor name
- Sample ad headline observed
- Offers mentioned (free estimate, discounts, etc.)
- Positioning angle (luxury, volume, price-competitive)
- Weaknesses to exploit (poor reviews, no free estimate, limited service area)

---

## Section 12: Rules (Non-Negotiable)

These rules apply to all agents working on any Ridgecrest Marketing Agency account. They are not suggestions. They are not guidelines. They do not have exceptions unless explicitly approved in writing by the account manager.

---

**Rule 1: Never guess. Every decision must be based on verified data with a source URL.**

If you don't have data, get data. If you can't get data, say so and wait. Do not invent search volumes, city names, zip codes, competitor names, or any other factual claim. Every fact in a strategy document must have a verifiable source URL attached to it.

---

**Rule 2: Every keyword must have documented search volume data.**

Before a keyword is added to any campaign, its monthly search volume must be checked using at least one tool from the approved source list (KeySearch, SEOpital, Marketkeep, AdTargeting, SERPWARS). The result must be logged in the keyword strategy file in this format:

```
| keyword text | match type | estimated volume | source URL | date checked |
```

---

**Rule 3: Every city must be verified against actual zip code targeting.**

Do not add city keywords for a city that is not represented in the geo targeting zip code list. Do not assume a zip code maps to a particular city — look it up in the Google geo targets CSV. If you can't verify the mapping, do not use the city name.

---

**Rule 4: Check campaign state via script before making changes. Never assume.**

Before modifying anything — budget, bids, keywords, ads — run the audit script from Section 1 and read the output. Confirm the current state. Document it in CURRENT_STATUS.md. Then make changes. Never proceed based on memory of a previous session's findings.

---

**Rule 5: Scripts go in chat as code blocks, never as file attachments.**

When sharing Google Ads Scripts with the user or account manager, paste them as code blocks in the conversation. Do not attach as .js files, .txt files, or any other format. Code blocks can be copy-pasted directly into Google Ads → Scripts without reformatting.

---

**Rule 6: All campaigns/ad groups/ads must use the agent's prefix.**

- Perplexity agent: `[PX]` prefix on all campaign names, ad group names
- Claude/Anthropic agent: `[RMA]` prefix on all campaign names, ad group names
- No exceptions — the prefix is how agents identify their own work and avoid touching each other's campaigns

Example: `[PX] Ridgecrest Designs — Search` not `Ridgecrest Designs — Search`

---

**Rule 7: Never touch campaigns without your own prefix.**

If you see a campaign named `[RMA] Ridgecrest Designs — Search` and your prefix is `[PX]`, you do not read, modify, pause, or analyze that campaign. It belongs to the other agent. If you believe the other agent's campaign has a problem, document it in `CURRENT_STATUS.md` and flag it for the account manager.

---

**Rule 8: Check agency_mode.txt before campaign changes.**

Before making ANY change to a live campaign:
1. Read `agency_mode.txt`
2. If it says `ACTIVE` or `ENABLED`: proceed normally
3. If it says `PAUSED`, `READ_ONLY`, or `HOLD`: stop. Do not make changes. Document what you intended to do in CURRENT_STATUS.md and wait for instructions.

---

**Rule 9: Read all rules files at the start of every session.**

At the beginning of every work session, before any other action:
1. Read `agency_mode.txt`
2. Read all files in the `rules/` directory
3. Read `CURRENT_STATUS.md`
4. Read `CAMPAIGN_IDS.md`

Do not skip this step even if you believe nothing has changed. Things change between sessions.

---

**Rule 10: Every prompt to Claude Code must include safety guardrails.**

When generating prompts for Claude Code or similar code-generating AI systems, always include:
- "Do not delete or modify any files not explicitly referenced in this task"
- "Do not make live API calls unless explicitly instructed"
- "Output all changes as code blocks for review before execution"
- "Confirm the scope of changes before executing"

---

**Rule 11: Flag data older than 1 hour as stale.**

Any data pulled from Google Ads (impressions, spend, conversions, search terms) that is more than 1 hour old at the time you are making decisions should be marked `[STALE - pulled at HH:MM]` in your notes. For decisions involving budget changes or bid strategy changes, pull fresh data. Do not base live campaign decisions on data from a previous session.

---

**Rule 12: "Affordable" is always a negative keyword for luxury positioning.**

For any client with luxury price positioning (confirmed in intake): the word "affordable" is a permanent, non-negotiable negative keyword. It is added at the campaign level. It is never removed. It is never reconsidered. If a search term report shows "affordable kitchen remodel" triggering impressions, this means the negative was not properly added — fix it immediately.

This rule exists because "affordable" signals a fundamentally different buyer intent than luxury remodeling clients want. A person searching "affordable kitchen remodel" will not convert for a $50,000 kitchen renovation and will waste budget while skewing performance data.

---

**Rule 13: Martinez (94553) is excluded from Ridgecrest Designs targeting.**

Zip code 94553, city of Martinez, is excluded from all Ridgecrest Designs campaigns. It is:
- Not added to geo targeting
- Not used in city keywords
- Added as a location exclusion at the campaign level

This is a client instruction. Do not question it, do not accidentally re-add it, and do not add "Martinez" as a keyword under any circumstance for this client.

---

## Section 13: File Structure (Server)

### Overview

All agents write to and read from a shared server directory. The file structure is standardized — do not create files outside of designated folders without account manager approval.

---

### Root-Level Files

```
/
├── CURRENT_STATUS.md          ← Overwrite at end of every session
├── CAMPAIGN_IDS.md            ← All account, campaign, ad group IDs
└── agency_mode.txt            ← Read before every campaign change
```

**CURRENT_STATUS.md** — Overwrite (not append) at the end of every session. Include:
- Date and time
- Agent prefix
- What was done this session
- Current state of all active campaigns
- Blockers or unresolved issues
- Recommended next steps for the next session

**CAMPAIGN_IDS.md** — Append-only. Never delete a line. Format:
```
## [CLIENT NAME]
- Account CID: [XXXXXXXXXX]
- Campaign: [NAME] | ID: [XXXXXXXXXX]
- Ad Group: [NAME] | ID: [XXXXXXXXXX]
- Budget: [BUDGET ID]
```

**agency_mode.txt** — Single line file. Valid values:
- `ACTIVE` — Normal operations, changes permitted
- `PAUSED` — Read-only, no changes
- `READ_ONLY` — Same as paused
- `HOLD` — Specific hold, see CURRENT_STATUS.md for reason

---

### Directory Structure

```
rules/
├── agent_rules.md             ← Core rules (supersedes all other instructions)
├── negative_keyword_rules.md  ← Negative keyword management rules
└── [additional rule files]

campaigns/
├── [CLIENT_SLUG]/
│   ├── [CLIENT]_intake.md          ← Client intake form (completed)
│   ├── [CLIENT]_keyword_strategy.md ← All keywords with sources and volumes
│   ├── [CLIENT]_ad_copy.md         ← All RSA headlines and descriptions
│   ├── [CLIENT]_negative_keywords.md ← Full negative keyword list
│   ├── geo_targets_verified.csv    ← Verified from Google's CSV
│   └── zip_city_mapping.md         ← Zip code to city name mapping

competitors/
├── auction_insights_[CLIENT]_[DATE].md
├── [COMPETITOR_DOMAIN]_research_[DATE].md
├── [CLIENT]_ad_intelligence_[DATE].md
└── ad_schedule_research_2026_04_11.md    ← March 2026 pacing change documentation

handoffs/
├── [DATE]_[AGENT]_to_[AGENT]_handoff.md ← Session-to-session summaries
└── [DATE]_session_summary.md

tasks/
├── [DATE]_task_[DESCRIPTION].md    ← Task assignments between agents
└── [DATE]_task_[DESCRIPTION].md

task_status/
├── [DATE]_task_[DESCRIPTION]_COMPLETE.md
└── [DATE]_task_[DESCRIPTION]_BLOCKED.md
```

---

### File Naming Conventions

- Dates always use `YYYY_MM_DD` format (underscores, not hyphens)
- Client slugs: lowercase, underscores, no spaces (e.g., `ridgecrest_designs`)
- No spaces in any filename
- Agent prefix in filename where applicable: `[PX]_keyword_strategy.md`

---

### Handoff Protocol

At the end of every session, create a handoff file:

```markdown
## Session Handoff — [DATE] — [YOUR PREFIX]

### Work Completed This Session
- [Specific task 1]
- [Specific task 2]

### Current Campaign State
- Campaign [NAME]: [STATUS] — [IMPRESSIONS] impressions, [SPEND] spent today
- Conversion tracking: [WORKING / NEEDS ATTENTION]

### Files Created/Modified This Session
- [FILE PATH]: [what was done]

### Blockers / Unresolved Issues
- [ISSUE]: [context]

### Recommended Next Steps (for next agent/session)
1. [TASK 1]
2. [TASK 2]

### Do Not Touch
- [ANYTHING THAT SHOULD NOT BE MODIFIED]
```

---

## Section 14: Platform-Specific Notes

---

### Google Ads

#### Scripts (Google Ads Scripts)

Google Ads Scripts run JavaScript inside Google's servers. They can read and write campaign data.

**Execution environment:**
- Language: JavaScript (ES5/ES6 subset)
- Runtime: Google's V8 engine, not Node.js
- Libraries: AdsApp, SpreadsheetApp, UrlFetchApp available
- Time limit: 30 minutes per script execution
- Rate limit: Be aware of quotas when iterating over large accounts

**Known Issues — Read Before Writing Scripts:**

**Issue 1: `containsEuPoliticalAdvertising` requires enum string, not boolean**
```javascript
// WRONG — will throw error:
campaign.setContainsEuPoliticalAdvertising(false);

// CORRECT — use enum string:
campaign.setContainsEuPoliticalAdvertising("UNSPECIFIED");
```

**Issue 2: Ampersand (&) symbol triggers PROHIBITED policy**
If your ad copy, sitelink text, or callout text contains `&`, Google may flag it for policy review. Use "and" instead of `&` in all ad copy.
```
// WRONG: "Kitchen & Bathroom Remodeling"
// CORRECT: "Kitchen and Bathroom Remodeling"
```

**Issue 3: Newly created objects cannot be queried in the same script execution**
If you create a campaign in a script, you cannot then query that campaign in the same script run. It will not appear in results until the next script execution.
```javascript
// This will NOT work in one script:
var campaign = AdsApp.newCampaignBuilder()...build();
var found = AdsApp.campaigns().withCondition("Name = '" + campaign.getName() + "'").get();
// found will be empty — query in a separate script run
```

**Issue 4: Non-ASCII characters cause SyntaxError**
If you copy-paste ad copy from a word processor, it may include "smart quotes" (`"`, `"`, `'`, `'`) or em-dashes (`—`). These are non-ASCII and will cause scripts to fail with a SyntaxError.
```javascript
// WRONG — contains smart quotes (looks right, fails silently):
var headline = "Award-Winning Kitchen Remodels";  // Uses " not "

// CORRECT — use straight ASCII quotes:
var headline = "Award-Winning Kitchen Remodels";
```
Always write scripts in a plain-text editor, not Word or Google Docs.

**Issue 5: Asset removal via Scripts does NOT work**
You cannot remove sitelinks, callouts, structured snippets, or other assets using Google Ads Scripts. Asset removal must be done via the Google Ads UI. Scripts can ADD assets but not REMOVE them.

**Script best practices:**
- Always run in PREVIEW mode before live execution
- Log aggressively — use `Logger.log()` to document every significant action
- Never run a script that writes data without first running it in preview and reviewing the log
- Add a dry-run flag to all scripts:

```javascript
var DRY_RUN = true;  // Set to false when ready to execute live

// Then in code:
if (!DRY_RUN) {
  keyword.remove();
  Logger.log("REMOVED keyword: " + keyword.getText());
} else {
  Logger.log("DRY RUN — would remove keyword: " + keyword.getText());
}
```

---

### Meta Ads

#### General Guidelines for Contractor Clients

**Budget threshold:**
For budgets under $100/day, use **manual campaigns** rather than Advantage+ campaigns. Advantage+ requires sufficient volume to optimize effectively — below $100/day in most local markets, there is insufficient data for Advantage+ to outperform well-structured manual campaigns.

**Housing special ad category:**
Remodeling contractors — kitchen, bathroom, home improvement, additions — do **NOT** require the Housing Special Ad Category. This category applies to real estate listings, rental housing, and mortgage products. General home improvement services are not subject to these restrictions.

Do not apply Housing Special Ad Category to remodeling contractor campaigns — it limits targeting options unnecessarily.

**Campaign structure:**
- 1 campaign per objective (Lead Generation)
- Ad set level: age, gender, interest, and location targeting
- Ad level: creative (image + headline + description + CTA)

**Targeting approach for remodeling contractors:**
- Age: 30–65+ (homeowners)
- Interests: Home improvement, interior design, home remodeling, kitchen remodeling
- Custom audiences: Website visitors (if pixel is installed), customer list uploads
- Lookalike audiences: After 100+ pixel events, create lookalike from converters

**Meta Marketing API:**
Use the Marketing API for programmatic campaign creation, not the manual UI, when building multiple campaigns. Ensure all API calls include:
- `special_ad_categories: []` (empty, since housing category doesn't apply)
- Correct account ID format: `act_[account_id]`

---

### Microsoft Ads (Future Implementation)

#### Setup Process

1. Create Microsoft Ads account at ads.microsoft.com
2. Import existing Google Ads campaign via the Import tool:
   - Sign in → Import → From Google Ads
   - Select the Google Ads account and campaign to import
   - Map settings (budget, bids, etc.)
   - Schedule regular imports OR import once and manage separately

#### Key Differences from Google Ads

| Factor | Google Ads | Microsoft Ads |
|--------|-----------|---------------|
| Average CPC | Baseline | 20–30% lower for identical keywords |
| Search volume | Higher | Lower (Bing has ~3–8% US search share) |
| Demographics | All ages | Skews slightly older (30–65+) — relevant for homeowners |
| Scripts | Google Ads Scripts | Microsoft Ads Scripts (similar but different API) |
| Smart campaigns | Yes | Yes — avoid for same reasons as Google's |

#### Microsoft Ads Scripts

Microsoft uses its own scripting environment. Scripts from Google Ads will need adaptation — the API objects are similar but not identical. Test all scripts in sandbox before deploying live.

---

## Appendix A: Quick Reference — Character Counts

| Element | Hard Limit | Recommended |
|---------|------------|-------------|
| RSA Headline | 30 characters | 25–30 |
| RSA Description | 90 characters | 80–90 |
| Sitelink link text | 25 characters | 20–25 |
| Sitelink description line | 35 characters | 30–35 |
| Callout text | 25 characters | 18–25 |
| Structured snippet value | 25 characters | 15–25 |

**Always count characters before deploying.** Use the Google Ads UI character counter, or an online character counter. Do not trust visual estimation.

---

## Appendix B: Quick Reference — Approved Data Sources

| Source | URL | Use Case |
|--------|-----|----------|
| Google Geo Targets CSV | https://developers.google.com/google-ads/api/data/geotargets | Zip code to city verification |
| KeySearch | https://www.keysearch.co | Keyword volume and competition |
| SEOpital | https://www.seopital.co | Keyword clustering, local intent |
| Marketkeep | https://www.marketkeep.com | Home services benchmarks |
| AdTargeting | https://www.adtargeting.io | Google Ads keyword intelligence |
| SERPWARS | https://www.serpwars.com | SERP competitiveness |
| Google Ad Transparency | https://adstransparency.google.com | Competitor ad research |
| groas.ai | https://groas.ai | Master negative keyword lists |

---

## Appendix C: Ridgecrest Designs — Master Reference

This section documents the specific implementation details for the founding client account.

```
Client: Ridgecrest Designs
Slug: ridgecrest_designs
Industry: Luxury Home Remodeling
Price Positioning: Luxury
Service Area: Contra Costa County, CA (select cities)
Excluded: Martinez (94553) — permanent exclusion
Monthly Budget: [CONFIRM WITH ACCOUNT MANAGER]

Active Services:
- Kitchen Remodeling
- Bathroom Remodeling
- Whole Home Renovation
- Design-Build
- Room Additions / ADU
- Interior Design / Architecture

Non-Offered Services (negatives):
- Roofing, plumbing, HVAC, electrical, painting, landscaping

Free Estimate: Yes — "Free In-Home Estimates" in callouts and headlines

Permanent Negative Keywords:
- affordable (luxury positioning rule — never remove)
- martinez (excluded city)
- 94553 (excluded zip)

Target Neighborhoods (golf course method):
- Blackhawk (Danville/Diablo CC area)
- Diablo (Diablo Country Club)
- Alamo (Round Hill CC)
- Orinda Country Club area
- Rossmoor (Walnut Creek — 55+, high HHI)
- Ruby Hill (Pleasanton — Castlewood CC)
- Happy Valley (Lafayette)
- Sleepy Hollow (Orinda)

Agent Prefixes:
- [PX] = Perplexity agent campaigns
- [RMA] = Claude/Anthropic agent campaigns
```

---

*End of Master Playbook v1.0*  
*Ridgecrest Marketing Agency — Confidential*  
*All sections are actionable. If a step is unclear, re-read the section context before asking for clarification. This document is the source of truth.*
