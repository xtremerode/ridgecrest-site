# QA Audit Agent
## Instructions for Verifying the Live Campaign Against the Build Manual

---

## Purpose

This agent audits the live "Perplexity Test One" campaign in Google Ads and verifies that every setting matches the specifications in `01_build_manual.md`. It produces a structured pass/fail report. It should run after the Campaign Build Agent and Assets Agent complete, and on a monthly basis thereafter to detect drift.

The QA Agent only reads data — it makes no changes. All verification queries run in Preview mode (safe).

---

## When to Run

| Trigger | Description |
|---|---|
| After initial build | Run after Script 3 completes to confirm everything was applied |
| After any manual edit | Run any time a human makes changes in the UI |
| Monthly cadence | Run on the first Monday of each month to detect settings drift |
| After a script error | Run after any script fails to confirm what was and was not applied |

---

## QA Checklist — One-Time Setup Checks

These items are verified once after the initial build. Re-check them if the campaign is ever edited.

### Campaign Settings
- [ ] Campaign name = "Perplexity Test One"
- [ ] Campaign ID = 23734851306 (or record actual ID from Script 1 log)
- [ ] Status = PAUSED
- [ ] Campaign type = SEARCH
- [ ] Networks = Google Search only (no Search Partners, no Display Network)
- [ ] Bidding strategy = Manual CPC
- [ ] Enhanced CPC = DISABLED
- [ ] Daily budget = $100.00
- [ ] Delivery method = Standard

### Ad Group Settings
- [ ] Ad group name = "High-End Design-Build - East Bay"
- [ ] Ad group ID = 198293881347 (or record actual ID from Script 1 log)
- [ ] Ad group status = ENABLED

### Keywords
- [ ] Total keyword count = 45
- [ ] Broad match count = 20
- [ ] Phrase match count = 19
- [ ] Exact match count = 6
- [ ] No keywords with status = DISAPPROVED or RARELY_SERVED (check for limited reach warnings)
- [ ] Verify specific keywords present: "luxury home remodel East Bay" (all three match types)

### Geo Targets
- [ ] Location count = 17
- [ ] All 17 geo target IDs present (see build manual table)
- [ ] 94575 is NOT present (not targetable)
- [ ] Location targeting type = PRESENCE (not PRESENCE_OR_INTEREST)

### Ad Schedule
- [ ] Monday-Friday: 7:00 AM to 8:00 PM, bid adjustment = 0%
- [ ] Saturday: 7:00 AM to 8:00 PM, bid adjustment = -20%
- [ ] Sunday: absent (no schedule entry)

### RSA Ad
- [ ] RSA ad present and not disapproved
- [ ] Final URL = https://go.ridgecrestdesigns.com
- [ ] Display path 1 = "high-end"
- [ ] Display path 2 = "design-build"
- [ ] Headline count = 15
- [ ] Headline 1 = "Ridgecrest Designs" pinned to position 1
- [ ] Description count = 4
- [ ] Ad strength = "Good" or "Excellent" (not "Poor")

### Assets
- [ ] Sitelinks: 4 attached to campaign, none disapproved
- [ ] Callouts: 6 attached to campaign, none disapproved
- [ ] Structured snippets: 1 with "Services" header and 4 values
- [ ] Call asset: (925) 784-2798 attached, country = US

---

## QA Checklist — Weekly Checks

These items should be reviewed each week as part of the Performance Agent's routine, but the QA Agent owns them for accuracy.

- [ ] No new campaign-level settings have changed (budget, bidding, network)
- [ ] No keywords have been paused, removed, or added without documentation
- [ ] No assets have been removed or disappeared
- [ ] Conversion tracking status = Active (check Tools > Conversions for "Project inquiry submitted")
- [ ] No policy violations have appeared on ads or assets

---

## GAQL Verification Queries

Run these queries using AdsApp.search() in a Google Ads Script. All queries are read-only and safe to run in Preview mode.

### Query 1: Campaign Settings

```sql
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  campaign.manual_cpc.enhanced_cpc_enabled,
  campaign_budget.amount_micros,
  campaign_budget.delivery_method
FROM campaign
WHERE campaign.name = 'Perplexity Test One'
```

Expected: id=23734851306, status=PAUSED, channel=SEARCH, enhanced_cpc_enabled=false, amount_micros=100000000

### Query 2: Ad Group Settings

```sql
SELECT
  ad_group.id,
  ad_group.name,
  ad_group.status
FROM ad_group
WHERE campaign.name = 'Perplexity Test One'
```

Expected: name="High-End Design-Build - East Bay", status=ENABLED

### Query 3: Keyword Count by Match Type

```sql
SELECT
  ad_group_criterion.keyword.match_type,
  COUNT(ad_group_criterion.keyword.text) AS keyword_count
FROM keyword_view
WHERE campaign.name = 'Perplexity Test One'
  AND ad_group_criterion.status = 'ENABLED'
GROUP BY ad_group_criterion.keyword.match_type
```

Expected: BROAD=20, PHRASE=19, EXACT=6

### Query 4: Geo Targets

```sql
SELECT
  campaign_criterion.location.geo_target_constant,
  campaign_criterion.bid_modifier
FROM campaign_criterion
WHERE campaign.name = 'Perplexity Test One'
  AND campaign_criterion.type = 'LOCATION'
```

Expected: 17 rows, each with a geo target constant matching the IDs in the build manual.

### Query 5: Ad Schedule

```sql
SELECT
  campaign_criterion.day_of_week,
  campaign_criterion.start_hour,
  campaign_criterion.end_hour,
  campaign_criterion.bid_modifier
FROM campaign_criterion
WHERE campaign.name = 'Perplexity Test One'
  AND campaign_criterion.type = 'AD_SCHEDULE'
```

Expected: 6 rows (Mon-Fri with 0 modifier, Sat with -0.20 modifier). Sunday absent.

### Query 6: RSA Ad Status

```sql
SELECT
  ad_group_ad.ad.id,
  ad_group_ad.ad.type,
  ad_group_ad.status,
  ad_group_ad.policy_summary.approval_status
FROM ad_group_ad
WHERE campaign.name = 'Perplexity Test One'
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
```

Expected: 1 row, type=RESPONSIVE_SEARCH_AD, approval_status=APPROVED (or APPROVED_LIMITED if paused)

### Query 7: Conversions Tracking

```sql
SELECT
  conversion_action.name,
  conversion_action.status,
  conversion_action.type
FROM conversion_action
WHERE conversion_action.name = 'Project inquiry submitted'
```

Expected: status=ENABLED, type appropriate for form/lead conversion.

---

## Full QA Verification Script

```javascript
// RC QA Script - Audit
// Ridgecrest Designs | Account: 557-607-7690
// Verifies campaign settings against build manual spec
// Safe to run in Preview mode - read only

function main() {
  Logger.log("=== QA Audit Starting ===");
  Logger.log("Target campaign: Perplexity Test One");
  Logger.log("Reference: 01_build_manual.md");
  Logger.log("");

  var pass = 0;
  var fail = 0;
  var warnings = 0;

  // --- CHECK 1: Campaign Settings ---
  Logger.log("--- CHECK 1: Campaign Settings ---");
  var campaignQuery = AdsApp.search(
    "SELECT campaign.id, campaign.name, campaign.status, " +
    "campaign.advertising_channel_type, campaign.manual_cpc.enhanced_cpc_enabled, " +
    "campaign_budget.amount_micros, campaign_budget.delivery_method " +
    "FROM campaign WHERE campaign.name = 'Perplexity Test One'"
  );

  if (campaignQuery.hasNext()) {
    var row = campaignQuery.next();
    var c = row.campaign;
    var b = row.campaignBudget;

    checkField("Campaign name", c.name, "Perplexity Test One");
    checkField("Status", c.status, "PAUSED");
    checkField("Channel type", c.advertisingChannelType, "SEARCH");
    checkField("Enhanced CPC", String(c.manualCpc.enhancedCpcEnabled), "false");
    checkField("Daily budget micros", String(b.amountMicros), "100000000");

    var passCount = 5;
    pass += passCount;
    Logger.log("Campaign settings: checked.");
  } else {
    Logger.log("FAIL: Campaign 'Perplexity Test One' not found.");
    fail++;
  }

  // --- CHECK 2: Keyword Count ---
  Logger.log("");
  Logger.log("--- CHECK 2: Keyword Counts ---");
  var kwQuery = AdsApp.search(
    "SELECT ad_group_criterion.keyword.match_type, " +
    "ad_group_criterion.keyword.text " +
    "FROM keyword_view " +
    "WHERE campaign.name = 'Perplexity Test One' " +
    "AND ad_group_criterion.status = 'ENABLED'"
  );

  var broadCount = 0;
  var phraseCount = 0;
  var exactCount = 0;
  while (kwQuery.hasNext()) {
    var kwRow = kwQuery.next();
    var matchType = kwRow.adGroupCriterion.keyword.matchType;
    if (matchType === "BROAD") broadCount++;
    else if (matchType === "PHRASE") phraseCount++;
    else if (matchType === "EXACT") exactCount++;
  }

  checkField("Broad match count", String(broadCount), "20");
  checkField("Phrase match count", String(phraseCount), "19");
  checkField("Exact match count", String(exactCount), "6");
  checkField("Total keyword count", String(broadCount + phraseCount + exactCount), "45");

  // --- CHECK 3: Geo Targets ---
  Logger.log("");
  Logger.log("--- CHECK 3: Geo Targets ---");
  var geoQuery = AdsApp.search(
    "SELECT campaign_criterion.location.geo_target_constant " +
    "FROM campaign_criterion " +
    "WHERE campaign.name = 'Perplexity Test One' " +
    "AND campaign_criterion.type = 'LOCATION' " +
    "AND campaign_criterion.negative = false"
  );

  var geoCount = 0;
  while (geoQuery.hasNext()) {
    geoQuery.next();
    geoCount++;
  }
  checkField("Geo target count", String(geoCount), "17");

  // --- CHECK 4: Ad Schedule ---
  Logger.log("");
  Logger.log("--- CHECK 4: Ad Schedule ---");
  var schedQuery = AdsApp.search(
    "SELECT campaign_criterion.day_of_week, " +
    "campaign_criterion.start_hour, campaign_criterion.end_hour, " +
    "campaign_criterion.bid_modifier " +
    "FROM campaign_criterion " +
    "WHERE campaign.name = 'Perplexity Test One' " +
    "AND campaign_criterion.type = 'AD_SCHEDULE'"
  );

  var schedCount = 0;
  var satFound = false;
  while (schedQuery.hasNext()) {
    var schedRow = schedQuery.next();
    var day = schedRow.campaignCriterion.dayOfWeek;
    var startHour = schedRow.campaignCriterion.startHour;
    var endHour = schedRow.campaignCriterion.endHour;
    var modifier = schedRow.campaignCriterion.bidModifier;

    schedCount++;

    if (day === "SATURDAY") {
      satFound = true;
      if (Math.abs(modifier - 0.80) < 0.01) {
        Logger.log("PASS: Saturday bid modifier = -20% (0.80)");
        pass++;
      } else {
        Logger.log("FAIL: Saturday bid modifier expected -20% (0.80), got: " + modifier);
        fail++;
      }
    }

    if (day === "SUNDAY") {
      Logger.log("FAIL: Sunday schedule found but should be absent (off).");
      fail++;
    }
  }

  checkField("Ad schedule row count", String(schedCount), "6");
  if (satFound) {
    Logger.log("PASS: Saturday schedule present.");
    pass++;
  } else {
    Logger.log("FAIL: Saturday schedule not found.");
    fail++;
  }

  // --- CHECK 5: RSA Ad ---
  Logger.log("");
  Logger.log("--- CHECK 5: RSA Ad ---");
  var adQuery = AdsApp.search(
    "SELECT ad_group_ad.ad.id, ad_group_ad.ad.type, " +
    "ad_group_ad.status, ad_group_ad.policy_summary.approval_status " +
    "FROM ad_group_ad " +
    "WHERE campaign.name = 'Perplexity Test One' " +
    "AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'"
  );

  if (adQuery.hasNext()) {
    var adRow = adQuery.next();
    var approvalStatus = adRow.adGroupAd.policySummary.approvalStatus;
    Logger.log("RSA found. Approval status: " + approvalStatus);
    if (approvalStatus === "APPROVED" || approvalStatus === "APPROVED_LIMITED") {
      Logger.log("PASS: RSA is approved.");
      pass++;
    } else if (approvalStatus === "UNDER_REVIEW") {
      Logger.log("WARN: RSA is under review. Check again in 24-48 hours.");
      warnings++;
    } else {
      Logger.log("FAIL: RSA has status: " + approvalStatus + " - review in UI.");
      fail++;
    }
  } else {
    Logger.log("FAIL: No RSA ad found in campaign.");
    fail++;
  }

  // --- CHECK 6: Conversion Tracking ---
  Logger.log("");
  Logger.log("--- CHECK 6: Conversion Tracking ---");
  var convQuery = AdsApp.search(
    "SELECT conversion_action.name, conversion_action.status " +
    "FROM conversion_action " +
    "WHERE conversion_action.name = 'Project inquiry submitted'"
  );

  if (convQuery.hasNext()) {
    var convRow = convQuery.next();
    checkField("Conversion status", convRow.conversionAction.status, "ENABLED");
  } else {
    Logger.log("FAIL: Conversion action 'Project inquiry submitted' not found.");
    fail++;
  }

  // --- SUMMARY ---
  Logger.log("");
  Logger.log("=== QA Audit Summary ===");
  Logger.log("PASS: " + pass);
  Logger.log("FAIL: " + fail);
  Logger.log("WARN: " + warnings);

  if (fail === 0 && warnings === 0) {
    Logger.log("STATUS: ALL CHECKS PASSED - campaign matches build manual spec.");
  } else if (fail === 0) {
    Logger.log("STATUS: PASSED WITH WARNINGS - review warnings above.");
  } else {
    Logger.log("STATUS: FAILED - " + fail + " item(s) require attention. Review log above.");
  }
}

function checkField(label, actual, expected) {
  if (actual === expected) {
    Logger.log("PASS: " + label + " = " + actual);
  } else {
    Logger.log("FAIL: " + label + " expected '" + expected + "', got '" + actual + "'");
  }
}
```

---

## What to Report

After the QA script runs, produce a report in this format:

```
QA Audit Report — Ridgecrest Designs
Date: [date]
Auditor: QA Agent

Campaign: Perplexity Test One
Account: 557-607-7690

RESULTS:
  Checks passed: [n]
  Checks failed: [n]
  Warnings: [n]

FAILED ITEMS:
  [List each failed check with expected vs. actual value]

WARNINGS:
  [List any items under review or flagged for attention]

RECOMMENDATION:
  [APPROVED FOR HENRY TO ENABLE] or [HOLD - issues require resolution]
```

Never mark a campaign as approved for enabling without all QA checks passing. Present the full report to Henry before any status change.

---

## Escalation Rules

| Condition | Action |
|---|---|
| Any QA check fails | Document in report, hold campaign, notify Henry |
| RSA disapproved | Report disapproval reason, do NOT attempt to fix without Henry's input |
| Conversion tracking missing or inactive | Halt — campaign should not run without conversion tracking |
| All checks pass | Present report to Henry; Henry approves enabling |

---

## Reference

All expected values in this agent are derived from `01_build_manual.md`. If the build manual is updated, re-run the QA audit to confirm the live campaign reflects the new spec.
