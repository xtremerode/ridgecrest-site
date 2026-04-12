# Ridgecrest Marketing Agency — Google Ads Campaign Build Playbook
## Reusable Agency Workflow: Building a Search Campaign from Scratch

**Authored:** April 9, 2026
**Based on:** Live build session for "Perplexity Test One" (Ridgecrest Designs, Account 557-607-7690)
**Purpose:** Step-by-step operational playbook for any agent or operator to build a complete Google Ads Search campaign in a single session, without trial and error.

---

## HOW TO USE THIS DOCUMENT

Read every section before running any script. There are no shortcuts. Every rule and limitation in this document was learned the hard way during the April 9, 2026 build. Skipping sections will reproduce those same errors.

---

## SECTION 1: Pre-Build Checklist

Complete every item before touching Google Ads. Do not begin until all boxes are checked.

### 1.1 Account Access

- [ ] Identify the **Manager Account ID** (Ridgecrest Marketing: 447-894-4999)
- [ ] Identify the **Client Account ID** (Ridgecrest Designs: 557-607-7690)
- [ ] Log into Google Ads and confirm you are inside the **client account** (557-607-7690), NOT the manager account
- [ ] Navigate to Tools > Scripts and confirm the account ID in the top-right header matches the client account
- [ ] If account ID does not match, stop — navigate to the correct account before proceeding

### 1.2 Conversion Tracking

- [ ] Go to Tools > Conversions in the client account
- [ ] Confirm the primary conversion action exists by name (for Ridgecrest Designs: "Project inquiry submitted")
- [ ] Confirm its status is **Active** (green dot, not "No recent conversions" or "Inactive")
- [ ] If conversion tracking is not active, halt and fix before building the campaign — a campaign without active conversion tracking cannot be optimized

### 1.3 GA4 Integration

- [ ] Go to Tools > Linked accounts > Google Analytics
- [ ] Confirm GA4 is linked to the correct property
- [ ] Confirm the link status is **Active**
- [ ] If not linked, link it before proceeding — data from day one is important

### 1.4 Auto-Tagging

- [ ] Go to Admin > Account settings
- [ ] Confirm **Auto-tagging** is enabled (toggle is ON)
- [ ] Auto-tagging is required for GA4 data to flow correctly — if disabled, UTM parameters in Script 6 will still work, but auto-tagging should also be on

### 1.5 Shared Library — Negative Keyword Lists

- [ ] Go to Tools > Shared Library > Negative keyword lists
- [ ] Confirm that the negative keyword lists you intend to use exist by their exact names
- [ ] Write down the exact names — you will need them for Script 4
- [ ] If a list does not exist, create it in the Shared Library before running any scripts (lists cannot be created via script)

### 1.6 Campaign Name Uniqueness

- [ ] Go to Campaigns in the UI
- [ ] Search or scroll to confirm no campaign with the target name already exists
- [ ] If the campaign already exists: **do not run Script 1** — jump to the script step where the build was interrupted
- [ ] Duplicate campaigns will each spend against their own budgets and compete against each other

### 1.7 Settings Documentation

Before writing any script, document the following. Every setting must be confirmed, not assumed.

| Field | Value to Confirm |
|---|---|
| Campaign name | Exact string (no trailing spaces) |
| Daily budget | Dollar amount |
| Bidding strategy | Manual CPC, Smart Bidding type, etc. |
| Target locations | List of geo target IDs (not zip codes — IDs) |
| Location targeting option | Presence only vs. Presence or interest |
| Ad schedule | Days, hours, and bid adjustments |
| Keywords | Full list by match type |
| RSA headlines | All 15, under 30 characters each |
| RSA descriptions | All 4, under 90 characters each |
| Sitelink text | Minimum 6, under 25 characters each — 6 gives Google more combinations to test |
| Callout text | All 4+, under 25 characters each |
| Structured snippet header | Must be a Google-approved header type |
| Structured snippet values | All values, under 25 characters each |
| Call asset phone number | Digits only, no formatting |
| Final URL | Full URL including https:// |
| Negative keyword lists | Exact names of Shared Library lists |
| Location exclusions | Country/state/zip IDs to exclude |
| UTM tracking template | Full template string |

**Do not begin scripting until this table is complete.**

---

## SECTION 2: The 7-Script Build Process

Each script must be run as a **separate execution**. Never combine scripts. Never skip Preview. Always select all (Ctrl+A) and delete the editor contents before pasting a new script.

### Execution Protocol (applies to every script)

1. Go to Tools > Scripts in the client account
2. Click **+** to create a new script
3. Give the script a clear name (e.g., "RC Script 1 - Campaign Build")
4. In the editor: press **Ctrl+A** to select all, then **Delete** to clear it
5. Paste the script
6. Click **Preview** — read every line of the log output
7. Confirm the log shows expected results with no errors
8. Click **Run** — wait for completion
9. Read the run log — confirm results match the preview log
10. Verify in the UI before proceeding to the next script

---

### Script 1 — Campaign Build (Campaign + Ad Group + Keywords)

**Purpose:** Creates the campaign skeleton. Nothing else exists until this completes.

**What it creates:**
- Campaign with name, status (PAUSED), type (Search), bidding (Manual CPC), budget, and network settings
- Ad group with name, status (ENABLED), and default CPC
- All keywords: broad match, phrase match, and exact match

**What it does NOT do:**
- Does not add locations, schedule, or RSA ad (Script 2)
- Does not add assets (Script 3)
- Does not link negative lists (Script 4)
- Does not add exclusions (Script 5)

**After running — verify in UI:**
- [ ] Campaign appears in Campaigns list with status PAUSED
- [ ] Ad group appears under the campaign
- [ ] Keyword count matches expected total (Ridgecrest: 45)
- [ ] Log shows: "Campaign created", "Ad group created", total keyword count
- [ ] Record the campaign ID from the log (you will need it for troubleshooting)

**Critical notes:**
- Campaign is created PAUSED — it cannot go live without explicit approval
- The campaign will NOT appear in script queries run in the same execution — always run a new script to work with it
- If Script 1 fails partway through, check the UI before re-running — a duplicate campaign may have been partially created

---

### Script 2 — Configure (Locations + Ad Schedule + Negative Keywords + RSA Ad)

**Purpose:** Configures all campaign-level settings and creates the primary ad.

**Prerequisite:** Script 1 must be complete and the campaign must be visible in the UI.

**What it creates:**
- Location targets (geo target IDs, Presence only)
- Ad schedule (days, hours, bid adjustments)
- Campaign-level negative keywords
- Responsive Search Ad (RSA) with all headlines and descriptions

**What it does NOT do:**
- Does not add assets (Script 3)
- Does not link shared negative lists (Script 4)
- Does not add location exclusions (Script 5)

**After running — verify in UI:**
- [ ] Locations tab: correct number of zip codes listed, targeting = Presence only
- [ ] Ad schedule tab: correct days and hours, correct bid adjustments, Sunday absent
- [ ] Ads tab: RSA present, not disapproved
- [ ] RSA headline 1 pinned to position 1
- [ ] Log shows: location count, schedule entries added, "RSA ad created successfully"

**Critical notes:**
- Location Presence-only targeting must be set via `setTargetingSettingForDimension()` — there is no UI-equivalent shortcut via script
- The RSA ad will appear as "Under review" for up to 48 hours — this is normal
- Verify geo target IDs against the official Google geo targets CSV before running — wrong IDs will silently fail or target unintended locations
- Geo target 94575 is NOT a targetable US postal code in Google Ads — do not include it

---

### Script 3 — Assets (Sitelinks + Callouts + Structured Snippet + Call Asset)

**Purpose:** Attaches all ad assets (formerly "extensions") to the campaign.

**Prerequisite:** Scripts 1 and 2 must be complete.

**What it creates:**
- Minimum 6 sitelinks (link text, final URL, description 1, description 2) — 4 is Google's minimum to display any, 6 is the required minimum for this agency
- 4+ callouts (short text phrases)
- 1 structured snippet (header + values)
- 1 call asset (phone number)

**What it does NOT do:**
- Does not add image assets — these cannot be added via script; use the UI after 30-60 days of data
- Does not link shared negative lists (Script 4)

**After running — verify in UI:**
- [ ] Navigate to Assets in the left nav for the campaign
- [ ] Sitelinks: expected count present, none disapproved
- [ ] Callouts: expected count present, none disapproved
- [ ] Structured snippet: present with correct header and values
- [ ] Call asset: phone number correct, country correct
- [ ] Log shows: each asset type added with count

**Critical notes:**
- Assets may show "Under review" for 24-48 hours — do not re-add them if they are under review
- Sitelink link text: 25 character maximum — verify every sitelink before scripting
- Callout text: 25 character maximum — verify every callout before scripting
- Structured snippet values: 25 character maximum each
- The header for structured snippets must be a Google-approved type (e.g., "Services", "Brands", "Types") — do not invent a header
- `withCallOnly(false)` is the correct syntax — `withCallOnly()` with no argument is deprecated and will throw an error

---

### Script 4 — Negatives (Link Shared Negative Keyword Lists)

**Purpose:** Links all shared negative keyword lists from the Shared Library to the campaign.

**Prerequisite:** Scripts 1-3 must be complete. Shared Library lists must already exist (created manually in the UI).

**What it does:**
- Queries the Shared Library for negative keyword lists by exact name
- Links each list to the campaign

**After running — verify in UI:**
- [ ] Go to Keywords > Negative keywords
- [ ] Confirm the Shared Library section shows the linked list names
- [ ] Log shows: each list name found and linked

**Critical notes:**
- Shared negative keyword lists cannot be created via script — they must exist in the Shared Library before this script runs
- List names are case-sensitive — match them exactly as they appear in the Shared Library
- Run a discovery script first if you are unsure of exact list names: query `AdsApp.negativeKeywordLists()` to see all available lists

---

### Script 5 — Exclusions (Country + State + Zip Code Location Exclusions)

**Purpose:** Adds location exclusions to prevent ads from serving to unintended areas.

**Prerequisite:** Scripts 1-4 must be complete.

**What it does:**
- Adds negative geo targets at campaign level (countries, states, zip codes to exclude)
- For Ridgecrest Designs: excludes all US states and zip codes outside the East Bay target area, plus international locations

**After running — verify in UI:**
- [ ] Locations tab: confirm the excluded locations appear (marked with a minus/red icon)
- [ ] For Ridgecrest Designs: 436 excluded locations
- [ ] Log shows: exclusion count added

**Critical notes:**
- Location exclusions use the same geo target IDs as location targets — get IDs from the official Google geo targets CSV, not from zip codes
- Script 5 must run after Script 2 (which adds the target locations) to avoid conflicts
- Geo target 94575 is not a valid Google Ads postal code — do not attempt to exclude it either

---

### Script 6 — UTM (Tracking Template)

**Purpose:** Sets the campaign-level tracking template for UTM parameter tracking.

**Prerequisite:** Scripts 1-5 must be complete.

**What it does:**
- Sets the campaign-level URL tracking template using `campaign.urls().setTrackingTemplate()`

**After running — verify in UI:**
- [ ] Go to Campaign settings > URLs
- [ ] Confirm tracking template is set to the correct template string
- [ ] Log shows: "Tracking template set" with the template value

**Critical notes:**
- The correct method is `campaign.urls().setTrackingTemplate()` — NOT `campaign.setTrackingTemplate()` (that method does not exist)
- Always verify the method name against the official AdsApp documentation before writing this script
- The tracking template must include `{lpurl}` as the base URL placeholder
- Standard template format for Ridgecrest Designs: `{lpurl}?utm_source=google&utm_medium=cpc&utm_campaign={campaignid}&utm_content={adgroupid}&utm_term={keyword}`

---

### Script 7 — Enable Ad Group (Must Run Separately After All Above)

**Purpose:** Sets the ad group status to ENABLED. This is a separate script because ad group status cannot be reliably set and then queried in the same execution that created the campaign structure.

**Prerequisite:** Scripts 1-6 must all be complete and verified.

**What it does:**
- Queries the campaign by name
- Queries the ad group by name within that campaign
- Sets ad group status to ENABLED

**After running — verify in UI:**
- [ ] Ad group status shows ENABLED (not Paused)
- [ ] Primary status shows ELIGIBLE (campaign is still PAUSED, so ads will not serve yet)
- [ ] Log shows: "Ad group enabled: [ad group name]"

**Critical notes:**
- Do not run this script until all prior scripts are verified complete
- Ad group status ENABLED does not enable the campaign — the campaign remains PAUSED until Henry explicitly approves it
- If Script 1 set the ad group to ENABLED at creation and you can confirm it in the UI, Script 7 may not be needed — but run it anyway to be certain

---

## SECTION 3: Critical Rules

These rules are non-negotiable. Every agent and operator must follow them. Every rule below was derived from a real error or policy violation encountered during the April 9, 2026 build.

### Rule 1: Verify Method Names from Official Docs Before Writing Scripts

Before writing any script, fetch the official AdsApp reference page for every method you plan to use. Confirm the exact method name, arguments, and return type. Do not assume a method exists because it sounds logical.

**Example:**
- Wrong: Assuming `campaign.setTrackingTemplate()` exists
- Right: Fetching `https://developers.google.com/google-ads/scripts/docs/reference/adsapp/adsapp_campaignurls`, confirming the method is `campaign.urls().setTrackingTemplate()`, then writing the code

### Rule 2: Never Use Non-ASCII Characters in Scripts

Google Ads Scripts rejects any character with a byte value greater than 127. This includes:
- Em dashes (—)
- Curly/smart quotes (" " ' ')
- Box-drawing characters (─ │ ┌)
- Any accented or special character

Use only standard ASCII. If you paste text from a document or website, strip all non-ASCII characters before using it in a script.

### Rule 3: Always Use Double Quotes Only

Use double quotes (`"`) throughout all scripts. Mixed quote types cause SyntaxErrors in the Google Ads Scripts JavaScript engine.

### Rule 4: containsEuPoliticalAdvertising Must Be a String

The field `containsEuPoliticalAdvertising` accepts a string enum value, not a boolean.

- Wrong: `containsEuPoliticalAdvertising: false`
- Right: `containsEuPoliticalAdvertising: "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"`

Using `false` will throw an enum error at runtime.

### Rule 5: The Ampersand Symbol Triggers PROHIBITED Policy

The `&` character in any ad copy triggers a PROHIBITED policy violation. Google Ads rejects it.

- Wrong: `"Kitchen & Bath Remodeling"` (in headlines or descriptions)
- Right: `"Kitchen and Bath Remodeling"`

Review every piece of ad copy for ampersands before including it in a script.

### Rule 6: Phone Numbers in Ad Descriptions Trigger PROHIBITED Policy

Do not include any phone number in RSA descriptions or sitelink descriptions.

- Wrong: `"Call us at (925) 784-2798 for a free consultation."`
- Right: `"Contact us for a free consultation."`

Phone numbers belong only in call assets, not in text ad fields.

### Rule 7: Temporary Resource Names Only Exist During mutateAll Execution

When using `mutateAll()` with temporary resource names (-1, -2, -3), those names are session-scoped. They do not persist after the execution completes. Never reference a temporary resource name in a subsequent script — always query for the real ID by name.

### Rule 8: withCallOnly() Is Deprecated

Do not use `withCallOnly()` with no argument. The correct syntax is:
- `withCallOnly(false)` — call asset shows alongside other ad formats
- `withCallOnly(true)` — call-only (shows phone number only, no link to website)

Using the deprecated no-argument form will throw a runtime error.

### Rule 9: campaign.setTrackingTemplate() Does Not Exist

The method to set a tracking template on a campaign object is chained through `.urls()`:
- Wrong: `campaign.setTrackingTemplate("...")`
- Right: `campaign.urls().setTrackingTemplate("...")`

### Rule 10: Newly Created Entities Cannot Be Queried in the Same Execution

Google Ads has an indexing lag. If Script 1 creates a campaign, Script 1 cannot query that campaign using `AdsApp.campaigns()` or `AdsApp.search()`. Always split creation and configuration into separate scripts, run in separate executions.

### Rule 11: Always Preview Before Running

Click **Preview** first, review every line of the log output, then click **Run**. Preview mode makes no real changes. Skipping Preview means encountering errors on live data rather than catching them safely first.

### Rule 12: Select All and Delete Before Pasting

Before pasting any script into the Google Ads Scripts editor, press **Ctrl+A** and **Delete** to clear the editor. Leftover code from a previous script will cause conflicts or duplicate executions.

### Rule 13: Campaigns Are Always Created PAUSED

Never create a campaign with status ENABLED. All campaigns are created PAUSED. Henry must explicitly approve enabling any campaign before it goes live. Do not enable without that approval.

### Rule 14: One main() Function Per Script

Every script must have exactly one `main()` function. Multiple `main()` functions in a single script will cause one to shadow the other.

### Rule 15: Check Exact Names Before Using Them

Before referencing any entity by name (campaign name, negative keyword list name, conversion action name), run a discovery script first to get the exact name as it appears in the account. Names are case-sensitive and may have trailing spaces or unexpected characters.

---

## SECTION 4: Required Campaign Settings Template

These are the canonical settings for a standard Ridgecrest Designs Search campaign. Every value in every script must match this template exactly.

### 4.1 Campaign Settings

| Setting | Value |
|---|---|
| Campaign name | Perplexity Test One |
| Campaign type | Search |
| Status | PAUSED |
| Bidding strategy | Manual CPC |
| Enhanced CPC | OFF (disabled) |
| Daily budget | $100.00 |
| Delivery method | Standard |
| Search Network | Google Search only |
| Search Partners | OFF |
| Display Network | OFF |
| Start date | 20260401 (format: YYYYMMDD) |

### 4.2 Ad Group Settings

| Setting | Value |
|---|---|
| Ad group name | High-End Design-Build - East Bay |
| Status | ENABLED |
| Default CPC | $5.00 (broad), $6.00 (phrase), $8.00 (exact) |

### 4.3 Location Targeting

| Setting | Value |
|---|---|
| Targeting method | Presence only (NOT "Presence or interest") |
| API method | `campaign.setTargetingSettingForDimension("GEO_MODIFIER", "TARGET_ALL_SUBLOCATIONS")` |
| Number of targeted zip codes | 17 |
| Excluded zip code | 94575 (not a valid Google Ads geo target — do not include) |

**Geo Target IDs (source: Google geo targets CSV, 2026-03-31):**

| Zip Code | Geo Target ID |
|---|---|
| 94506 | 9031981 |
| 94507 | 9031982 |
| 94526 | 9031999 |
| 94549 | 9032015 |
| 94553 | 9032019 |
| 94556 | 9032021 |
| 94563 | 9032027 |
| 94566 | 9032030 |
| 94568 | 9032032 |
| 94582 | 9032043 |
| 94583 | 9032044 |
| 94586 | 9032046 |
| 94588 | 9032048 |
| 94595 | 9032053 |
| 94596 | 9032054 |
| 94597 | 9032055 |
| 94598 | 9032056 |

### 4.4 Ad Schedule

| Day | Start | End | Bid Adjustment |
|---|---|---|---|
| Monday | 7:00 AM | 8:00 PM | None (0%) |
| Tuesday | 7:00 AM | 8:00 PM | None (0%) |
| Wednesday | 7:00 AM | 8:00 PM | None (0%) |
| Thursday | 7:00 AM | 8:00 PM | None (0%) |
| Friday | 7:00 AM | 8:00 PM | None (0%) |
| Saturday | 7:00 AM | 8:00 PM | -20% |
| Sunday | Off | Off | N/A |

**API format:** `campaign.addAdSchedule("MONDAY", 7, 0, 20, 0, 0.0)` — parameters are: day, startHour, startMinute, endHour, endMinute, bidModifier (1.0 = no change; 0.80 = -20%)

### 4.5 Keywords

| Match Type | Count | CPC |
|---|---|---|
| Broad match | 20 keywords | $5.00 |
| Phrase match | 19 keywords | $6.00 |
| Exact match | 6 keywords | $8.00 |
| **Total** | **45 keywords** | |

See `01_build_manual.md` for the complete keyword list.

### 4.6 RSA Ad Requirements

| Field | Requirement |
|---|---|
| Final URL | https://go.ridgecrestdesigns.com |
| Display path 1 | high-end |
| Display path 2 | design-build |
| Headlines | 15 required; maximum 30 characters each |
| Descriptions | 4 required; maximum 90 characters each |
| Headline 1 | "Ridgecrest Designs" — pinned to HEADLINE_1 position |
| Pinning method | `.withPinnedField("HEADLINE_1")` on the asset builder |

**Character limit enforcement:** Count every headline and description character before scripting. Google will reject headlines over 30 characters and descriptions over 90 characters at the API level, but the script will fail silently or log a generic error unless character lengths are pre-verified.

**Policy prohibitions in ad copy:**
- No `&` character — use "and"
- No phone numbers in any text field
- No non-ASCII characters

### 4.7 Asset Requirements

| Asset Type | Minimum Required | Character Limits |
|---|---|---|
| Sitelinks | 6 minimum | Link text: 25 chars; Description 1: 35 chars; Description 2: 35 chars |
| Callouts | 4 (6 recommended) | Text: 25 chars |
| Structured snippet | 1 | Header: approved types only; Values: 25 chars each; Minimum 3 values |
| Call asset | 1 | Phone: digits only, no formatting |

**Sitelink URLs:** For single-page landing pages, use query parameters to differentiate traffic:
- Sitelink 1: `https://go.ridgecrestdesigns.com?sl=1`
- Sitelink 2: `https://go.ridgecrestdesigns.com?sl=2`
- Sitelink 3: `https://go.ridgecrestdesigns.com?sl=3`
- Sitelink 4: `https://go.ridgecrestdesigns.com?sl=4`
- Sitelink 5: `https://go.ridgecrestdesigns.com?sl=5`
- Sitelink 6: `https://go.ridgecrestdesigns.com?sl=6`

### 4.8 UTM Tracking Template

**Standard template:**
```
{lpurl}?utm_source=google&utm_medium=cpc&utm_campaign={campaignid}&utm_content={adgroupid}&utm_term={keyword}
```

**Method:** `campaign.urls().setTrackingTemplate("...")`

**Verification:** After setting, confirm the template appears in Campaign settings > URLs in the UI.

---

## SECTION 5: Post-Build Verification Checklist

Run the Full Status Report script after all 7 scripts complete. This is the final QA gate before presenting the campaign to Henry for approval to enable.

### Full Status Report — Expected Results

| Item | Expected Value |
|---|---|
| Campaign status | ENABLED (in the campaign object; campaign serving is controlled by PAUSED setting) |
| Campaign serving status | PAUSED |
| Ad group status | ENABLED |
| Ad group primary status | ELIGIBLE |
| RSA ad | APPROVED (or APPROVED_LIMITED; UNDER_REVIEW is acceptable for 24-48 hours) |
| Keywords | All ENABLED — check for any DISAPPROVED or RARELY_SERVED flags |
| Location targets | 17 targeted zip codes |
| Location exclusions | 436 excluded |
| Sitelinks | 6 attached minimum, none disapproved |
| Callouts | 6 attached, none disapproved |
| Structured snippet | 1 attached with Services header and 4 values |
| Call asset | 1 attached, (925) 784-2798, US |
| UTM tracking template | Set at campaign level, visible in Campaign settings > URLs |
| Shared negative lists | Linked — visible in Keywords > Negative keywords > Shared library section |
| Conversion tracking | Active — "Project inquiry submitted" shows status ENABLED |

### How to Run the Full Status Report

Use the QA Verification Script in `04_qa_agent.md`. Run it in Preview mode — it is read-only and safe. The script checks campaign settings, keyword counts, geo target count, ad schedule, RSA approval status, and conversion tracking.

### What to Do If Checks Fail

| Failure | Action |
|---|---|
| Campaign not found | Script 1 did not complete — check UI and re-run if needed |
| Keyword count wrong | Review log from Script 1 for per-keyword errors |
| Geo target count wrong | Re-run Script 2 after verifying geo IDs in build manual |
| RSA disapproved | Read disapproval reason in UI; check for & symbols, phone numbers, non-ASCII characters |
| Assets missing or disapproved | Re-check character counts; re-add if needed |
| Conversion tracking inactive | Do not enable campaign until conversion tracking is confirmed active |
| UTM template not set | Re-run Script 6; verify method name is `campaign.urls().setTrackingTemplate()` |

---

## SECTION 6: First 30 Days Monitoring

### Before the Campaign Goes Live

- [ ] All 5 Post-Build verification checks pass
- [ ] Henry has reviewed and approved the campaign
- [ ] Conversion tracking confirmed active in the UI
- [ ] Henry explicitly approves: "Enable the campaign"
- [ ] Run enable script (sets campaign status to ENABLED)
- [ ] Confirm campaign status changes to ENABLED in UI
- [ ] Confirm ads show as "Eligible" within 15 minutes

### Week 1 (Days 1-7): Stability Check

**Check daily for the first 3 days, then every other day:**
- Confirm campaign is serving (impression count > 0)
- Check for any new ad disapprovals or asset disapprovals
- Confirm conversion tracking is firing (check Diagnostics in Tools > Conversions)
- Check search term report for obviously irrelevant queries — add as negatives if found

**Do not:** Change bids, budget, or structure during Week 1. The campaign needs time to stabilize.

### Week 2 (Days 8-14): Search Term Review

**Run the Performance Agent weekly report (see `05_performance_agent.md`).**

**Search terms report — review criteria:**
- Flag any search term with 1+ click that is not relevant to high-end home design/remodel
- Add flagged terms as campaign-level broad match negatives
- Document every negative added in the weekly report

**Impression share check:**
- Target: Search Impression Share > 70%
- If Search Lost IS (Budget) > 5%: flag for Henry — budget may need to increase
- If Search Lost IS (Rank) > 20%: flag for Henry — bids may be too low

### Week 3 (Days 15-21): Keyword Performance Check

**First keyword-level analysis:**
- Which keywords are getting impressions vs. clicks?
- Which match types are performing best?
- Are phrase match keywords triggering appropriate search terms?

**Do not:** Pause any keyword before 30 days unless it has generated clear policy issues or is spending heavily with zero relevant traffic.

### Week 4 (Days 22-30): First Optimization Review

**At 30 days, produce a full performance summary:**

| Metric | 30-Day Actual | Target |
|---|---|---|
| Total spend | $[actual] | Up to $3,000 |
| Search IS | [actual]% | >70% |
| Search Lost IS (Budget) | [actual]% | <5% |
| Avg CPC | $[actual] | $30-70 |
| Clicks | [actual] | Track trend |
| Conversions | [actual] | Any conversion is success at 30 days |
| CPL | $[actual] or N/A | Track; $200-1,000 acceptable |

**30-day decisions (all require Henry's approval before action):**
- If Search IS < 50%: propose bid increases
- If Budget Lost IS > 15%: propose budget increase
- If avg CPC > $70 with low CTR: investigate quality scores
- If any keyword has > $200 spend and 0 clicks: propose pausing
- If a search term has driven a conversion: note the keyword and match type

### Ongoing Weekly Schedule

Every Monday morning:
1. Run Performance Agent weekly report
2. Review search terms — add negatives for clearly irrelevant terms
3. Check impression share status (Green/Yellow/Red threshold)
4. Check conversion tracking active status
5. Present report to Henry with any escalation items

---

## SECTION 7: Known API Limitations

These are hard limitations discovered during the April 9, 2026 build. They cannot be worked around with clever scripting — they require specific approaches or manual UI action.

### Limitation 1: Image Assets Cannot Be Added via Script

Image assets (formerly image extensions) cannot be attached to campaigns using Google Ads Scripts. They must be added manually through the Google Ads UI.

**Timing recommendation:** Wait until the campaign has 30-60 days of data before adding image assets. Google recommends having sufficient performance data before enabling image assets for optimal machine learning.

**How to add:** Google Ads UI > Campaign > Assets > + > Image

### Limitation 2: Location Presence-Only Setting Requires Specific API Approach

Setting location targeting to "Presence only" (as opposed to "Presence or interest") must be done via `campaign.setTargetingSettingForDimension()` in scripts. There is no simple boolean setter.

**Correct syntax:**
```javascript
campaign.setTargetingSettingForDimension("GEO_MODIFIER", "TARGET_ALL_SUBLOCATIONS");
```

After running, verify the setting in the UI — Location options > Target > "Presence: People in or regularly in your targeted locations."

### Limitation 3: Ad Group Status Must Be Set in a Separate Script After Campaign Creation

When a campaign is created in Script 1, the ad group's ENABLED status set at creation time may not persist as expected when queried in later scripts. Script 7 (Enable Ad Group) exists specifically to confirm and set ad group status after all other configuration is complete. Do not assume the status set in Script 1 is the final state without Script 7 verification.

### Limitation 4: Preview Mode Makes No Real Changes

Google Ads Scripts Preview mode is a simulation. Every log output in Preview is what *would* happen — not what has happened. Always click Run to apply real changes. Verify in the UI after Run completes.

**This means:** If you only ever run Preview, the campaign will not exist. The log output in Preview looks identical to a real Run. Do not confuse them.

### Limitation 5: Geo Target 94575 Is Not a Targetable US Postal Code

The zip code 94575 (Moraga, CA area) does not have a valid geo target ID in the Google Ads system as of the 2026-03-31 geo targets CSV. Attempting to target or exclude it will fail silently or throw an error.

**Action:** Remove 94575 from any location target or exclusion list. The 17-zip coverage for Ridgecrest Designs is complete without it.

### Limitation 6: Newly Created Entities Cannot Be Queried in the Same Execution

This is repeated from Section 3 because it is the most common source of script failures. If Script 1 creates a campaign, you cannot call `AdsApp.campaigns().withCondition("Name = 'X'").get()` in that same script and expect to find it. Split creation and configuration into separate scripts, run sequentially.

### Limitation 7: Shared Negative Keyword Lists Cannot Be Created via Script

`AdsApp.negativeKeywordLists()` provides read and link access only. You cannot create a new shared negative keyword list using scripts. Lists must be created manually in Tools > Shared Library > Negative keyword lists before Script 4 can link them.

### Limitation 8: The withCallOnly() Method Is Deprecated

Do not use `withCallOnly()` without an argument. Always pass `true` or `false` explicitly. The deprecated no-argument form throws a runtime error in current Google Ads Scripts.

---

## QUICK REFERENCE: Script Run Order

```
PRE-BUILD: Complete Section 1 checklist entirely

Script 1  -->  Campaign + Ad Group + Keywords
              [Verify in UI: campaign exists, ad group exists, keyword count correct]

Script 2  -->  Locations + Schedule + Negative KWs + RSA Ad
              [Verify in UI: 17 locations, schedule set, RSA present]

Script 3  -->  Sitelinks + Callouts + Structured Snippet + Call Asset
              [Verify in UI: all 4 asset types present]

Script 4  -->  Link Shared Negative Keyword Lists
              [Verify in UI: shared lists appear in Negative keywords section]

Script 5  -->  Location Exclusions (countries, states, zip codes)
              [Verify in UI: 436 exclusions listed in Locations tab]

Script 6  -->  UTM Tracking Template
              [Verify in UI: tracking template visible in Campaign settings > URLs]

Script 7  -->  Enable Ad Group Status
              [Verify in UI: ad group status = ENABLED, primary status = ELIGIBLE]

POST-BUILD: Run Full Status Report script (Section 5)
            Present results to Henry for approval to enable
```

---

## DOCUMENT MAINTENANCE

This document must be updated after every build session or significant discovery.

| Update Trigger | Action |
|---|---|
| New API error discovered | Add to Section 7 Known Limitations |
| New policy violation encountered | Add to Section 3 Critical Rules |
| Settings changed for Ridgecrest Designs | Update Section 4 template |
| New script added to the workflow | Add entry to Section 2 |
| Geo target IDs updated (new CSV) | Update Section 4.3 geo target table |

The source of truth for all Ridgecrest Designs-specific settings is `01_build_manual.md`. This playbook documents the process. When they conflict, `01_build_manual.md` takes precedence for client-specific values.
