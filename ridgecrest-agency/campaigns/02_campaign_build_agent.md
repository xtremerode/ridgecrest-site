# Campaign Build Agent
## Instructions for Building the Ridgecrest Designs Campaign Structure

---

## Purpose

This agent builds the full Google Ads campaign structure for Ridgecrest Designs using two scripts run in sequence. It creates the campaign, ad group, keywords, geo targets, ad schedule, negative keywords, and RSA ad. It does NOT add assets — that is the Assets Agent's job.

All settings must match `01_build_manual.md` exactly. Never deviate from the build manual without Henry's approval.

---

## Pre-Build Checklist

Complete every item before running Script 1. Do not skip.

- [ ] Read `01_build_manual.md` in full — confirm all settings are current
- [ ] Confirm you are logged into account **557-607-7690** (Ridgecrest Designs), NOT the manager account
- [ ] Navigate to Tools > Scripts and confirm you are in the correct account
- [ ] Search existing campaigns: confirm no campaign named **"Perplexity Test One"** already exists
  - If it exists: do NOT run Script 1 — jump to Script 2 verification or contact Henry
- [ ] Confirm daily budget is set to $100.00 in the build manual — do not use a different amount
- [ ] Review the Known Issues Log in `01_build_manual.md` — be aware of all past issues before starting
- [ ] Confirm Preview mode is ON before the first run of each script

---

## Step-by-Step Build Process

### Phase 1: Script 1 — Campaign, Ad Group, Keywords

**What Script 1 does:**
- Creates the campaign named "Perplexity Test One" (PAUSED, Manual CPC, $100/day, Search only)
- Creates the ad group named "High-End Design-Build - East Bay"
- Adds all 45 keywords (20 broad, 19 phrase, 6 exact)

**Steps:**
1. Go to Google Ads account 557-607-7690 > Tools > Scripts
2. Click the **+** button to create a new script
3. Name it: `RC Script 1 - Campaign Build`
4. Paste the full Script 1 code (below)
5. Click **Preview** — review the log output carefully
6. Confirm the log shows: campaign created, ad group created, keyword count = 45
7. If preview looks correct, click **Run**
8. Wait for the run to complete
9. Note the campaign ID from the log output — verify it matches 23734851306 or record the new ID if this is a fresh build
10. Navigate to Campaigns in the UI and confirm "Perplexity Test One" appears as PAUSED

**Do not proceed to Script 2 until Script 1 completes successfully.**

---

### Phase 2: Script 2 — Locations, Schedule, Negatives, RSA Ad

**What Script 2 does:**
- Adds all 17 geo targets with Presence Only targeting
- Sets the ad schedule (Mon-Fri 7am-8pm, Sat 7am-8pm with -20%, Sun off)
- Adds negative keywords
- Creates the RSA ad with 15 headlines and 4 descriptions

**Steps:**
1. Go to Tools > Scripts
2. Click **+** to create a new script
3. Name it: `RC Script 2 - Configure`
4. Paste the full Script 2 code (below)
5. Click **Preview** — review the log output
6. Confirm the log shows: 17 locations added, schedule set, RSA ad created
7. If preview looks correct, click **Run**
8. Wait for the run to complete
9. Verify in the UI:
   - Locations tab: 17 zip codes listed, targeting = Presence only
   - Ad schedule tab: Mon-Sat with correct hours, Sun absent
   - Ads tab: RSA ad present with status "Eligible" or "Paused" (not disapproved)

---

## Script 1 — Campaign, Ad Group, Keywords

```javascript
// RC Script 1 - Campaign Build
// Ridgecrest Designs | Account: 557-607-7690
// Creates campaign, ad group, and 45 keywords
// Run BEFORE Script 2

function main() {
  Logger.log("=== Script 1: Campaign Build Starting ===");

  // --- CREATE CAMPAIGN ---
  var campaignOperation = AdsApp.newCampaignBuilder()
    .withName("Perplexity Test One")
    .withStatus("PAUSED")
    .withAdServingOptimizationStatus("OPTIMIZE")
    .withBiddingStrategy("MANUAL_CPC")
    .withBudget(100.00)
    .withStartDate("20260401")
    .forSearchNetwork(true)
    .forDisplayNetwork(false)
    .build();

  if (campaignOperation.isSuccessful()) {
    var campaign = campaignOperation.getResult();
    Logger.log("Campaign created: " + campaign.getName() + " | ID: " + campaign.getId());

    // Disable Enhanced CPC
    campaign.bidding().setEnhancedCpcEnabled(false);
    Logger.log("Enhanced CPC disabled.");

    // --- CREATE AD GROUP ---
    var adGroupOperation = campaign.newAdGroupBuilder()
      .withName("High-End Design-Build - East Bay")
      .withStatus("ENABLED")
      .withCpc(5.00)
      .build();

    if (adGroupOperation.isSuccessful()) {
      var adGroup = adGroupOperation.getResult();
      Logger.log("Ad group created: " + adGroup.getName() + " | ID: " + adGroup.getId());

      // --- BROAD MATCH KEYWORDS (20) ---
      var broadKeywords = [
        "home remodel near me",
        "home renovation near me",
        "home remodeling contractor near me",
        "kitchen remodel near me",
        "bathroom remodel near me",
        "kitchen renovation near me",
        "bathroom renovation near me",
        "home addition near me",
        "whole house remodel near me",
        "design build contractor near me",
        "custom home builder near me",
        "general contractor near me",
        "home remodel contractor",
        "kitchen remodel contractor",
        "design build firm",
        "custom home design build",
        "whole house renovation",
        "home addition contractor",
        "high end home remodel",
        "high end remodeling contractor"
      ];

      var broadCount = 0;
      for (var i = 0; i < broadKeywords.length; i++) {
        var kwOp = adGroup.newKeywordBuilder()
          .withText(broadKeywords[i])
          .withMatchType("BROAD")
          .withCpc(5.00)
          .build();
        if (kwOp.isSuccessful()) {
          broadCount++;
        } else {
          Logger.log("ERROR adding broad keyword: " + broadKeywords[i] + " | " + kwOp.getErrors());
        }
      }
      Logger.log("Broad keywords added: " + broadCount + " / 20");

      // --- PHRASE MATCH KEYWORDS (19) ---
      var phraseKeywords = [
        "luxury home remodel East Bay",
        "luxury home remodel near me",
        "luxury home renovation near me",
        "luxury kitchen remodel East Bay",
        "luxury kitchen remodel near me",
        "high end remodel Danville",
        "high end home remodel near me",
        "premium home remodel Pleasanton",
        "luxury renovation East Bay",
        "luxury home renovation Walnut Creek",
        "upscale home remodel near me",
        "luxury bathroom remodel near me",
        "high end kitchen remodel near me",
        "luxury home builder East Bay",
        "high end general contractor near me",
        "luxury remodeling company near me",
        "high end renovation contractor",
        "kitchen remodel Walnut Creek",
        "kitchen remodel Danville"
      ];

      var phraseCount = 0;
      for (var j = 0; j < phraseKeywords.length; j++) {
        var pkwOp = adGroup.newKeywordBuilder()
          .withText(phraseKeywords[j])
          .withMatchType("PHRASE")
          .withCpc(6.00)
          .build();
        if (pkwOp.isSuccessful()) {
          phraseCount++;
        } else {
          Logger.log("ERROR adding phrase keyword: " + phraseKeywords[j] + " | " + pkwOp.getErrors());
        }
      }
      Logger.log("Phrase keywords added: " + phraseCount + " / 19");

      // --- EXACT MATCH KEYWORDS (6) ---
      var exactKeywords = [
        "luxury home remodel East Bay",
        "design build firm near me",
        "whole house remodel near me",
        "custom home builder East Bay",
        "high end remodel Danville",
        "luxury kitchen remodel East Bay"
      ];

      var exactCount = 0;
      for (var k = 0; k < exactKeywords.length; k++) {
        var ekwOp = adGroup.newKeywordBuilder()
          .withText(exactKeywords[k])
          .withMatchType("EXACT")
          .withCpc(8.00)
          .build();
        if (ekwOp.isSuccessful()) {
          exactCount++;
        } else {
          Logger.log("ERROR adding exact keyword: " + exactKeywords[k] + " | " + ekwOp.getErrors());
        }
      }
      Logger.log("Exact keywords added: " + exactCount + " / 6");

      var totalKeywords = broadCount + phraseCount + exactCount;
      Logger.log("Total keywords added: " + totalKeywords + " / 45");

    } else {
      Logger.log("ERROR creating ad group: " + adGroupOperation.getErrors());
    }

  } else {
    Logger.log("ERROR creating campaign: " + campaignOperation.getErrors());
  }

  Logger.log("=== Script 1: Complete ===");
}
```

---

## Script 2 — Locations, Schedule, Negatives, RSA Ad

```javascript
// RC Script 2 - Configure
// Ridgecrest Designs | Account: 557-607-7690
// Adds locations, ad schedule, negatives, and RSA ad
// Run AFTER Script 1 completes

function main() {
  Logger.log("=== Script 2: Configure Starting ===");

  // Find the campaign by name
  var campaignIterator = AdsApp.campaigns()
    .withCondition("Name = 'Perplexity Test One'")
    .get();

  if (!campaignIterator.hasNext()) {
    Logger.log("ERROR: Campaign 'Perplexity Test One' not found. Run Script 1 first.");
    return;
  }

  var campaign = campaignIterator.next();
  Logger.log("Campaign found: " + campaign.getName() + " | ID: " + campaign.getId());

  // --- GEO TARGETS (17 zip codes, Presence Only) ---
  // Source: Google geo targets CSV 2026-03-31
  var geoTargetIds = [
    9031981,  // 94506
    9031982,  // 94507
    9031999,  // 94526
    9032015,  // 94549
    9032019,  // 94553
    9032021,  // 94556
    9032027,  // 94563
    9032030,  // 94566
    9032032,  // 94568
    9032043,  // 94582
    9032044,  // 94583
    9032046,  // 94586
    9032048,  // 94588
    9032053,  // 94595
    9032054,  // 94596
    9032055,  // 94597
    9032056   // 94598
  ];

  // Note: 94575 is NOT targetable - excluded intentionally
  var locationCount = 0;
  for (var i = 0; i < geoTargetIds.length; i++) {
    try {
      campaign.addLocation(geoTargetIds[i]);
      locationCount++;
    } catch (e) {
      Logger.log("ERROR adding location ID " + geoTargetIds[i] + ": " + e.message);
    }
  }
  Logger.log("Locations added: " + locationCount + " / 17");

  // Set location targeting to Presence Only
  campaign.setTargetingSettingForDimension("GEO_MODIFIER", "TARGET_ALL_SUBLOCATIONS");
  Logger.log("Location targeting: Presence only set.");

  // --- AD SCHEDULE ---
  // Mon-Fri: 7am-8pm (no adjustment)
  // Sat: 7am-8pm (-20%)
  // Sun: off

  var weekdays = [
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"
  ];

  for (var d = 0; d < weekdays.length; d++) {
    campaign.addAdSchedule(weekdays[d], 7, 0, 20, 0, 0);  // 0.0 = no adjustment
  }
  Logger.log("Weekday schedule added: Mon-Fri 7am-8pm");

  campaign.addAdSchedule("SATURDAY", 7, 0, 20, 0, -0.20);  // -20% bid adjustment
  Logger.log("Saturday schedule added: 7am-8pm -20%");
  // Sunday: no entry = off

  // --- NEGATIVE KEYWORDS (Campaign Level) ---
  var negatives = [
    "diy",
    "do it yourself",
    "how to",
    "rent",
    "rental",
    "apartment",
    "condo",
    "cheap",
    "affordable",
    "low cost",
    "free",
    "estimate tool",
    "software",
    "school",
    "course",
    "training",
    "jobs",
    "hiring",
    "careers",
    "salary"
  ];

  var negCount = 0;
  for (var n = 0; n < negatives.length; n++) {
    try {
      campaign.createNegativeKeyword(negatives[n]);
      negCount++;
    } catch (e) {
      Logger.log("ERROR adding negative: " + negatives[n] + " | " + e.message);
    }
  }
  Logger.log("Negative keywords added: " + negCount);

  // --- RSA AD ---
  var adGroupIterator = campaign.adGroups()
    .withCondition("Name = 'High-End Design-Build - East Bay'")
    .get();

  if (!adGroupIterator.hasNext()) {
    Logger.log("ERROR: Ad group not found.");
    return;
  }

  var adGroup = adGroupIterator.next();
  Logger.log("Ad group found: " + adGroup.getName());

  // Build RSA
  // Headline 1 is pinned to position 1
  // All other headlines are unpinned
  var adOperation = adGroup.newAd().responsiveSearchAdBuilder()
    .withFinalUrl("https://go.ridgecrestdesigns.com")
    .withPath1("high-end")
    .withPath2("design-build")
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Ridgecrest Designs")
      .withPinnedField("HEADLINE_1")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("High-End Home Remodeling")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("East Bay Design-Build Firm")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Book a Free Discovery Call")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("High-End Custom Renovations")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Pleasanton Design-Build Firm")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Whole House Remodels")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Custom Homes and Additions")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Award-Winning Design Team")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("From Concept to Completion")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Serving Danville and Walnut Ck")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Transform Your Home")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Large-Scale Custom Projects")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Kitchen and Bath Remodeling")
      .build())
    .addHeadline(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Get Your Project Started")
      .build())
    .addDescription(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("High-end design-build firm in Pleasanton. Custom homes and whole-house remodels.")
      .build())
    .addDescription(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("High-end custom homes for East Bay homeowners. Book a free discovery call today.")
      .build())
    .addDescription(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("From concept to completion, exceptional craftsmanship. Serving Danville to Lafayette.")
      .build())
    .addDescription(AdsApp.responsiveSearchAdAssetBuilder()
      .withText("Transform your home with Ridgecrest Designs. Contact us for a free consultation.")
      .build())
    .build();

  if (adOperation.isSuccessful()) {
    var ad = adOperation.getResult();
    Logger.log("RSA ad created successfully. Ad ID: " + ad.getId());
  } else {
    Logger.log("ERROR creating RSA ad: " + adOperation.getErrors());
  }

  Logger.log("=== Script 2: Complete ===");
}
```

---

## Verification Steps After Build

After both scripts complete, verify the following in the Google Ads UI:

### Campaign Level
- [ ] Campaign name: "Perplexity Test One"
- [ ] Status: PAUSED
- [ ] Budget: $100/day
- [ ] Bidding: Manual CPC
- [ ] Enhanced CPC: Disabled
- [ ] Network: Google Search only (no Display, no Partners)

### Ad Group Level
- [ ] Ad group name: "High-End Design-Build - East Bay"
- [ ] Status: Enabled

### Keywords
- [ ] Total keyword count: 45
- [ ] Broad match count: 20
- [ ] Phrase match count: 19
- [ ] Exact match count: 6
- [ ] No keyword errors or disapprovals

### Locations
- [ ] 17 zip codes listed in Locations tab
- [ ] All set to Presence only (not Presence or interest)
- [ ] 94575 is absent (not targetable)

### Ad Schedule
- [ ] Monday-Friday: 7am-8pm, no adjustment
- [ ] Saturday: 7am-8pm, -20% bid adjustment
- [ ] Sunday: absent (off)

### RSA Ad
- [ ] Status: Eligible (or Paused if campaign is paused)
- [ ] Not disapproved
- [ ] Headline 1 "Ridgecrest Designs" pinned to position 1
- [ ] 15 headlines total
- [ ] 4 descriptions total
- [ ] Display path: high-end / design-build
- [ ] Final URL: https://go.ridgecrestdesigns.com

---

## Error Handling

### "Campaign not found" in Script 2
- Script 1 did not complete successfully, OR
- There is a lag — wait 2-3 minutes and re-run Script 2

### Keyword errors
- Review the log for the specific keyword that failed
- Check for prohibited characters or policy violations
- Cross-reference with Known Issues Log in `01_build_manual.md`

### RSA ad disapproved
- Check Google Ads UI for the disapproval reason
- Common causes: policy violation in ad copy, URL mismatch
- Review ad copy against Known Issues Log (no &, no phone numbers in descriptions)
- Do NOT attempt to fix without reading the disapproval reason first

### Location error
- If a geo target ID fails, cross-reference with the official geo targets CSV
- Do not guess or substitute IDs

### Unexpected errors not in Known Issues Log
- Document the error before retrying
- Add to Known Issues Log in `01_build_manual.md`
- Contact Henry if the issue cannot be resolved

---

## Reference

All settings in this agent are derived from `01_build_manual.md`. If any discrepancy exists between this file and the build manual, the build manual takes precedence.
