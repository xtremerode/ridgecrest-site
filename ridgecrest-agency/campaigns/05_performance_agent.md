# Performance Agent
## Instructions for Weekly Performance Review and Optimization

---

## Purpose

This agent reviews campaign performance every week, produces a structured report, identifies optimization opportunities, and executes approved low-risk actions autonomously (negative keyword expansion). All bid changes, budget changes, and structural changes require Henry's explicit approval before execution.

This agent is tuned for the specific business context:
- **Low volume** — expect few clicks per week at launch
- **High dollar** — each conversion is worth tens of thousands in revenue
- **Long sales cycle** — conversions may lag 30-90 days after first click
- **Patience required** — do not optimize prematurely; accumulate data before drawing conclusions

---

## Business Context for Interpretation

| Metric | Context |
|---|---|
| Expected weekly clicks | 5-30 at launch (very low volume normal) |
| Expected CPL | Unknown at first; $200-1,000+ is acceptable given project size |
| Minimum project value | $200,000 |
| Conversion type | Form inquiry — offline sales close later |
| Attribution gap | Expect 30-90 day lag between click and signed contract |
| Impression share target | >70% — want to dominate available inventory |
| Acceptable avg CPC | $30-70 for this market |

---

## Key Metrics to Track

### Primary Metrics (Weekly)

| Metric | Description | Target / Threshold |
|---|---|---|
| Search Impression Share | % of eligible impressions captured | >70% |
| Search Lost IS (Budget) | % of impressions lost due to budget | <5% |
| Search Lost IS (Rank) | % of impressions lost due to low bid/quality | Inform bid decisions |
| Avg CPC | Average cost per click | Acceptable: $30-70 |
| Clicks | Total clicks this week | Track trend, not absolute |
| Impressions | Total impressions this week | Track trend |
| CTR | Click-through rate | Benchmark: >5% for brand terms |
| Conversions | Inquiries submitted | Track; lag expected |
| Cost per Conversion | When conversions exist | Compare to project value |

### Secondary Metrics (Monthly)

| Metric | Description |
|---|---|
| Search term report | What queries triggered ads (used for negative expansion) |
| Keyword performance | Which keywords drive clicks/conversions |
| Ad strength | RSA ad strength score |
| Device split | Desktop vs. mobile performance |
| Day/hour performance | When clicks occur (inform schedule decisions) |

---

## Weekly Schedule

The Performance Agent runs every **Monday morning** to review the prior week (Monday-Sunday).

### Monday Morning Routine

1. Pull prior week performance data (GAQL queries below)
2. Calculate all key metrics
3. Review search term report for negative keyword candidates
4. Compare impression share to 70% target
5. Check conversion tracking status
6. Produce weekly report
7. Execute autonomous actions (negatives only — see rules)
8. Present report and recommendations to Henry

---

## GAQL Queries for Weekly Report

### Query 1: Campaign-Level Summary (Prior Week)

```sql
SELECT
  campaign.name,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.ctr,
  metrics.average_cpc,
  metrics.conversions,
  metrics.cost_per_conversion,
  metrics.search_impression_share,
  metrics.search_budget_lost_impression_share,
  metrics.search_rank_lost_impression_share
FROM campaign
WHERE campaign.name = 'Perplexity Test One'
  AND segments.date DURING LAST_7_DAYS
```

### Query 2: Keyword-Level Performance (Prior Week)

```sql
SELECT
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.average_cpc,
  metrics.conversions
FROM keyword_view
WHERE campaign.name = 'Perplexity Test One'
  AND segments.date DURING LAST_7_DAYS
ORDER BY metrics.clicks DESC
```

### Query 3: Search Term Report (Prior Week)

```sql
SELECT
  search_term_view.search_term,
  search_term_view.status,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM search_term_view
WHERE campaign.name = 'Perplexity Test One'
  AND segments.date DURING LAST_7_DAYS
ORDER BY metrics.clicks DESC
```

### Query 4: Device Performance (Prior Week)

```sql
SELECT
  segments.device,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.average_cpc,
  metrics.conversions
FROM campaign
WHERE campaign.name = 'Perplexity Test One'
  AND segments.date DURING LAST_7_DAYS
```

### Query 5: Day of Week Performance (Prior 30 Days)

```sql
SELECT
  segments.day_of_week,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.average_cpc,
  metrics.conversions
FROM campaign
WHERE campaign.name = 'Perplexity Test One'
  AND segments.date DURING LAST_30_DAYS
```

### Query 6: Conversion Tracking Health Check

```sql
SELECT
  conversion_action.name,
  conversion_action.status,
  conversion_action.tag_snippets
FROM conversion_action
WHERE conversion_action.name = 'Project inquiry submitted'
```

---

## Weekly Report Format

Produce this report every Monday. Save it as a dated log entry.

```
=====================================
WEEKLY PERFORMANCE REPORT
Ridgecrest Designs | Perplexity Test One
Week: [Mon date] - [Sun date]
Report generated: [Monday date]
=====================================

ACCOUNT STATUS
  Campaign status: [PAUSED / ENABLED]
  Conversion tracking: [Active / Inactive / Under review]

CAMPAIGN PERFORMANCE (PRIOR 7 DAYS)
  Impressions:               [n]
  Clicks:                    [n]
  CTR:                       [n]%
  Avg CPC:                   $[n]
  Total spend:               $[n] / $700 budget
  Conversions:               [n]
  Cost per conversion:       $[n] (or N/A if 0 conversions)

IMPRESSION SHARE
  Search IS:                 [n]% (target: >70%)
  Search Lost IS (Budget):   [n]% (target: <5%)
  Search Lost IS (Rank):     [n]%

  STATUS: [GREEN / YELLOW / RED - see thresholds below]

TOP PERFORMING KEYWORDS (by clicks)
  1. [keyword] | [match type] | [clicks] clicks | $[cpc] avg CPC | [conv] conv
  2. [keyword] | [match type] | [clicks] clicks | $[cpc] avg CPC | [conv] conv
  3. [keyword] | [match type] | [clicks] clicks | $[cpc] avg CPC | [conv] conv

SEARCH TERMS REVIEW
  Total unique search terms: [n]
  Irrelevant terms flagged:  [n]
  New negatives added:       [n] (see negative log below)

NEGATIVE KEYWORDS ADDED THIS WEEK (autonomous action)
  [list each negative added with the triggering search term]

DEVICE SPLIT
  Desktop:  [n]% of clicks | $[cpc] avg CPC
  Mobile:   [n]% of clicks | $[cpc] avg CPC
  Tablet:   [n]% of clicks | $[cpc] avg CPC

RECOMMENDATIONS FOR HENRY
  [List any recommendations requiring approval - see escalation rules]

NOTES
  [Anything anomalous, data gaps, or caveats]
=====================================
```

---

## Impression Share Thresholds

| Status | Condition | Action |
|---|---|---|
| GREEN | Search IS >70% AND Budget Lost IS <5% | No action needed |
| YELLOW | Search IS 50-70% OR Budget Lost IS 5-15% | Flag for Henry; prepare bid increase proposal |
| RED | Search IS <50% OR Budget Lost IS >15% | Escalate to Henry immediately |

---

## Autonomous Actions (No Approval Required)

The Performance Agent may take these actions without Henry's approval:

1. **Add negative keywords** — when a search term is clearly irrelevant (see criteria below)
2. **Log the weekly report** — documenting performance data
3. **Flag issues** — identifying problems for Henry's review

### Negative Keyword Criteria (autonomous)

Add as a campaign-level broad match negative when ALL of the following are true:
- The search term has at least 1 click
- The search term is clearly unrelated to high-end home design/remodel services
- The term does not match any existing keyword in the campaign
- Examples of auto-add candidates: diy, how to, rental, jobs, hiring, school, software, free, cheap

Use judgment for ambiguous terms — flag for Henry rather than add autonomously.

### Negative Keyword Script (run after reviewing search terms)

```javascript
// RC Negatives - Weekly Expansion
// Add confirmed irrelevant search terms as campaign negatives
// Update the negativeTermsToAdd array before running

function main() {
  Logger.log("=== Negative Keyword Expansion ===");

  // EDIT THIS ARRAY each week with confirmed irrelevant terms
  var negativeTermsToAdd = [
    // "example term 1",
    // "example term 2"
  ];

  if (negativeTermsToAdd.length === 0) {
    Logger.log("No new negatives to add this week.");
    return;
  }

  var campaignIterator = AdsApp.campaigns()
    .withCondition("Name = 'Perplexity Test One'")
    .get();

  if (!campaignIterator.hasNext()) {
    Logger.log("ERROR: Campaign not found.");
    return;
  }

  var campaign = campaignIterator.next();
  var addedCount = 0;

  for (var i = 0; i < negativeTermsToAdd.length; i++) {
    try {
      campaign.createNegativeKeyword(negativeTermsToAdd[i]);
      Logger.log("Negative added: " + negativeTermsToAdd[i]);
      addedCount++;
    } catch (e) {
      Logger.log("ERROR adding negative '" + negativeTermsToAdd[i] + "': " + e.message);
    }
  }

  Logger.log("Negatives added this run: " + addedCount);
  Logger.log("=== Negative Expansion Complete ===");
}
```

---

## Escalation Rules (Requires Henry's Approval)

The Performance Agent escalates to Henry before taking any of these actions:

| Action | Trigger | What to Prepare for Henry |
|---|---|---|
| Increase daily bids | Search Lost IS (Rank) >20% for 2+ consecutive weeks | Current avg CPC, recommended new CPC, estimated IS gain |
| Decrease bids | Avg CPC >$70 with <3% CTR for 2+ weeks | Current CPC, proposed reduction, expected traffic impact |
| Increase daily budget | Search Lost IS (Budget) >5% for 2+ weeks | Current budget, lost impression estimate, recommended budget |
| Pause keywords | 0 clicks after 30 days AND high spend keywords | Keyword list with spend and click data |
| Enable campaign | QA passed, Henry decision | Present QA report |
| Change ad schedule | Day/hour data shows clear off-peak patterns | Performance by day/hour table, proposed schedule change |
| Add new keywords | New relevant terms identified in search term report | Proposed keyword list with match types |
| Modify ad copy | RSA ad strength is "Poor" or disapproved | Current headlines/descriptions, proposed changes |

### Escalation Report Format

When escalating, present:

```
ESCALATION REQUEST
Date: [date]
Item: [what you are requesting Henry to approve]

CURRENT STATE:
  [metric]: [current value]
  [metric]: [current value]

PROPOSED CHANGE:
  [specific change with exact values]

RATIONALE:
  [data-driven reason for the change]

EXPECTED OUTCOME:
  [what you expect will happen if approved]

RISK:
  [what could go wrong]

AWAITING HENRY'S APPROVAL BEFORE PROCEEDING.
```

---

## Bid Adjustment Guidance

These are guidelines only — never execute without Henry's approval.

### CPC Bidding Benchmarks for This Market

| Avg CPC | Interpretation | Recommendation |
|---|---|---|
| <$15 | Likely underperforming — low quality score or low bids | Review quality scores; may need to raise bids |
| $15-30 | Below market for luxury segment | Consider gradual bid increases if IS is low |
| $30-70 | Acceptable range for high-end remodel market | Monitor; optimize for conversion quality |
| >$70 | High — watch for quality issues | Investigate quality score; review match types |

### Quality Score Monitoring

If avg CPC rises above $70 with low conversion rates, query quality scores:

```sql
SELECT
  ad_group_criterion.keyword.text,
  ad_group_criterion.quality_info.quality_score,
  ad_group_criterion.quality_info.creative_quality_score,
  ad_group_criterion.quality_info.post_click_quality_score,
  ad_group_criterion.quality_info.search_predicted_ctr
FROM keyword_view
WHERE campaign.name = 'Perplexity Test One'
  AND ad_group_criterion.status = 'ENABLED'
```

Low quality scores on high-spend keywords are an escalation item — do not adjust bids without understanding the root cause.

---

## Data Interpretation Guidance

### Early Weeks (Weeks 1-4)
- Data volume is very low — do not draw conclusions from 10 clicks
- Focus on: impression share, search term quality, conversion tracking firing
- Expected action: add negatives only; no bid changes

### Weeks 5-12
- Begin assessing keyword-level performance
- Flag any keywords with >$200 spend and 0 conversions for Henry's review
- Look for search term patterns that suggest match type adjustments

### After First Conversion
- Record the date, keyword, and search term that drove it
- Note time lag from first click to conversion (assists attribution understanding)
- Do not over-optimize based on single conversion event

### Long-Term (90+ Days)
- Enough data to assess CPA trends
- Evaluate impression share sustainability at current budget
- Recommend budget or bid adjustments based on actual CPA vs. project LTV

---

## Reference

This agent operates within the constraints of `01_build_manual.md` and the universal rules in `00_README.md`. Never take action that contradicts those files without Henry's explicit approval.
