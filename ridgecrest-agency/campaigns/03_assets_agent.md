# Assets Agent
## Instructions for Adding Campaign Assets to Ridgecrest Designs

---

## Purpose

This agent adds all required assets to the "Perplexity Test One" campaign after the Campaign Build Agent has completed. It runs a single script (Script 3) that attaches sitelinks, callouts, structured snippets, and a call asset.

Assets are not part of the campaign structure — they are extensions that appear alongside the ad. Google requires a minimum number of each type. This agent must run after Script 2 completes.

---

## Prerequisites

Before running Script 3, confirm:
- [ ] Script 1 has run successfully (campaign and ad group exist)
- [ ] Script 2 has run successfully (locations, schedule, and RSA ad configured)
- [ ] Campaign "Perplexity Test One" is visible in the Google Ads UI (even if PAUSED)
- [ ] You are in account **557-607-7690** (Ridgecrest Designs)
- [ ] You have reviewed all asset specs in `01_build_manual.md`

---

## API Syntax Reference (Verified)

The following syntax is verified against AdsApp documentation. Do not alter the method names or chaining patterns.

### Sitelink Builder (AdsApp.extensions().newSitelinkBuilder())

```javascript
var sitelink = AdsApp.extensions().newSitelinkBuilder()
  .withLinkText("Book a Discovery Call")
  .withFinalUrl("https://go.ridgecrestdesigns.com?sl=1")
  .withDescription1("Schedule your free consultation")
  .withDescription2("High-end design-build projects")
  .build()
  .getResult();
campaign.addSitelink(sitelink);
```

### Callout Builder (AdsApp.extensions().newCalloutBuilder())

```javascript
var callout = AdsApp.extensions().newCalloutBuilder()
  .withText("Free Discovery Call")
  .build()
  .getResult();
campaign.addCallout(callout);
```

### Structured Snippet Builder (AdsApp.extensions().newSnippetBuilder())

```javascript
var snippet = AdsApp.extensions().newSnippetBuilder()
  .withHeader("Services")
  .withValues(["Custom Home Design", "Whole House Remodels", "Home Additions", "Kitchen Remodeling"])
  .build()
  .getResult();
campaign.addSnippet(snippet);
```

### Call Asset Builder (AdsApp.extensions().newPhoneNumberBuilder())

```javascript
var phone = AdsApp.extensions().newPhoneNumberBuilder()
  .withPhoneNumber("9257842798")
  .withCountry("US")
  .withCallOnly(false)
  .build()
  .getResult();
campaign.addPhoneNumber(phone);
```

---

## Asset Specifications for Ridgecrest Designs

### Character Limits

| Asset Type | Field | Character Limit |
|---|---|---|
| Sitelink | Link text | 25 characters |
| Sitelink | Description 1 | 35 characters |
| Sitelink | Description 2 | 35 characters |
| Callout | Text | 25 characters |
| Structured Snippet | Header | Must use approved Google header |
| Structured Snippet | Each value | 25 characters |

### Sitelinks (4 total)

All sitelinks use UTM-style parameters (?sl=1 through ?sl=4) to differentiate traffic from a single-page site.

| # | Link Text | Final URL | Description 1 | Description 2 |
|---|---|---|---|---|
| 1 | Book a Discovery Call | https://go.ridgecrestdesigns.com?sl=1 | Schedule your free consultation | High-end design-build projects |
| 2 | Our Design-Build Process | https://go.ridgecrestdesigns.com?sl=2 | From concept to completion | Exceptional craftsmanship |
| 3 | Custom Home Projects | https://go.ridgecrestdesigns.com?sl=3 | Whole house remodels and additions | Serving the East Bay |
| 4 | Contact Ridgecrest Designs | https://go.ridgecrestdesigns.com?sl=4 | Get your project started today | Call or submit an inquiry |

**Character counts verified:**
- "Book a Discovery Call" = 21 chars (OK)
- "Our Design-Build Process" = 24 chars (OK)
- "Custom Home Projects" = 20 chars (OK)
- "Contact Ridgecrest Designs" = 26 chars — **TRIMMED to "Contact Us Today" = 16 chars** in script below

### Callouts (6 total)

| # | Text | Char Count |
|---|---|---|
| 1 | Free Discovery Call | 19 |
| 2 | Award-Winning Design Team | 25 |
| 3 | Custom Home Specialists | 23 |
| 4 | Serving the East Bay | 20 |
| 5 | Licensed and Insured | 20 |
| 6 | Projects From $200K+ | 20 |

All verified under 25 characters.

### Structured Snippet (1 total)

- Header: **Services** (Google-approved header type)
- Values:
  1. Custom Home Design (18 chars)
  2. Whole House Remodels (20 chars)
  3. Home Additions (14 chars)
  4. Kitchen Remodeling (18 chars)

All values verified under 25 characters.

### Call Asset (1 total)

- Phone number: 9257842798 (no formatting — digits only)
- Country: US
- Call-only: false

---

## Script 3 — Complete Ready-to-Run Script

```javascript
// RC Script 3 - Assets
// Ridgecrest Designs | Account: 557-607-7690
// Adds sitelinks, callouts, structured snippets, and call asset
// Run AFTER Script 2 completes

function main() {
  Logger.log("=== Script 3: Assets Starting ===");

  // Find the campaign by name
  var campaignIterator = AdsApp.campaigns()
    .withCondition("Name = 'Perplexity Test One'")
    .get();

  if (!campaignIterator.hasNext()) {
    Logger.log("ERROR: Campaign 'Perplexity Test One' not found. Run Scripts 1 and 2 first.");
    return;
  }

  var campaign = campaignIterator.next();
  Logger.log("Campaign found: " + campaign.getName() + " | ID: " + campaign.getId());

  // === SITELINKS (4) ===
  Logger.log("Adding sitelinks...");

  var sitelink1 = AdsApp.extensions().newSitelinkBuilder()
    .withLinkText("Book a Discovery Call")
    .withFinalUrl("https://go.ridgecrestdesigns.com?sl=1")
    .withDescription1("Schedule your free consultation")
    .withDescription2("High-end design-build projects")
    .build()
    .getResult();
  campaign.addSitelink(sitelink1);
  Logger.log("Sitelink 1 added: Book a Discovery Call");

  var sitelink2 = AdsApp.extensions().newSitelinkBuilder()
    .withLinkText("Our Design-Build Process")
    .withFinalUrl("https://go.ridgecrestdesigns.com?sl=2")
    .withDescription1("From concept to completion")
    .withDescription2("Exceptional craftsmanship")
    .build()
    .getResult();
  campaign.addSitelink(sitelink2);
  Logger.log("Sitelink 2 added: Our Design-Build Process");

  var sitelink3 = AdsApp.extensions().newSitelinkBuilder()
    .withLinkText("Custom Home Projects")
    .withFinalUrl("https://go.ridgecrestdesigns.com?sl=3")
    .withDescription1("Whole house remodels and additions")
    .withDescription2("Serving the East Bay")
    .build()
    .getResult();
  campaign.addSitelink(sitelink3);
  Logger.log("Sitelink 3 added: Custom Home Projects");

  var sitelink4 = AdsApp.extensions().newSitelinkBuilder()
    .withLinkText("Contact Us Today")
    .withFinalUrl("https://go.ridgecrestdesigns.com?sl=4")
    .withDescription1("Get your project started today")
    .withDescription2("Call or submit an inquiry")
    .build()
    .getResult();
  campaign.addSitelink(sitelink4);
  Logger.log("Sitelink 4 added: Contact Us Today");

  Logger.log("Sitelinks complete: 4 added.");

  // === CALLOUTS (6) ===
  Logger.log("Adding callouts...");

  var callout1 = AdsApp.extensions().newCalloutBuilder()
    .withText("Free Discovery Call")
    .build()
    .getResult();
  campaign.addCallout(callout1);
  Logger.log("Callout 1 added: Free Discovery Call");

  var callout2 = AdsApp.extensions().newCalloutBuilder()
    .withText("Award-Winning Design Team")
    .build()
    .getResult();
  campaign.addCallout(callout2);
  Logger.log("Callout 2 added: Award-Winning Design Team");

  var callout3 = AdsApp.extensions().newCalloutBuilder()
    .withText("Custom Home Specialists")
    .build()
    .getResult();
  campaign.addCallout(callout3);
  Logger.log("Callout 3 added: Custom Home Specialists");

  var callout4 = AdsApp.extensions().newCalloutBuilder()
    .withText("Serving the East Bay")
    .build()
    .getResult();
  campaign.addCallout(callout4);
  Logger.log("Callout 4 added: Serving the East Bay");

  var callout5 = AdsApp.extensions().newCalloutBuilder()
    .withText("Licensed and Insured")
    .build()
    .getResult();
  campaign.addCallout(callout5);
  Logger.log("Callout 5 added: Licensed and Insured");

  var callout6 = AdsApp.extensions().newCalloutBuilder()
    .withText("Projects From $200K+")
    .build()
    .getResult();
  campaign.addCallout(callout6);
  Logger.log("Callout 6 added: Projects From $200K+");

  Logger.log("Callouts complete: 6 added.");

  // === STRUCTURED SNIPPET (1) ===
  Logger.log("Adding structured snippet...");

  var snippet = AdsApp.extensions().newSnippetBuilder()
    .withHeader("Services")
    .withValues(["Custom Home Design", "Whole House Remodels", "Home Additions", "Kitchen Remodeling"])
    .build()
    .getResult();
  campaign.addSnippet(snippet);
  Logger.log("Structured snippet added: Services header with 4 values.");

  // === CALL ASSET (1) ===
  Logger.log("Adding call asset...");

  var phone = AdsApp.extensions().newPhoneNumberBuilder()
    .withPhoneNumber("9257842798")
    .withCountry("US")
    .withCallOnly(false)
    .build()
    .getResult();
  campaign.addPhoneNumber(phone);
  Logger.log("Call asset added: (925) 784-2798 | US | Call-only: false");

  Logger.log("=== Script 3: Assets Complete ===");
  Logger.log("Summary: 4 sitelinks, 6 callouts, 1 structured snippet, 1 call asset.");
}
```

---

## Verification After Script 3

After the script completes, verify in the Google Ads UI:

1. Go to the campaign "Perplexity Test One"
2. Navigate to **Assets** (formerly Extensions) in the left nav
3. Confirm the following:

| Asset Type | Expected Count | Status |
|---|---|---|
| Sitelinks | 4 | Eligible / Under review |
| Callouts | 6 | Eligible / Under review |
| Structured snippets | 1 | Eligible / Under review |
| Call | 1 | Eligible / Under review |

**Common delay:** Newly added assets may show "Under review" for up to 24-48 hours. This is normal.

**Disapproval:** If any asset is disapproved, check the reason in the UI. Common causes:
- Character count exceeded (verify against limits above)
- Capitalization policy (Title Case for sitelink text is required)
- URL policy (URL must be reachable)

---

## Error Handling

### "Campaign not found"
- Script 1 or Script 2 did not complete — do not proceed
- Verify the campaign name is exactly "Perplexity Test One" (case-sensitive)

### Build operation fails (getResult() throws)
- Check the log for the specific asset that failed
- Verify the character count of that asset's text fields
- Verify the URL is properly formatted

### Asset shows disapproved after review
- Read the disapproval reason in the UI
- Do not attempt to re-add without fixing the policy issue
- Consult the Known Issues Log in `01_build_manual.md`
- Document the new issue if it is not already logged

---

## Reference

All asset values in this agent are derived from `01_build_manual.md`. If any discrepancy exists between this file and the build manual, the build manual takes precedence.
