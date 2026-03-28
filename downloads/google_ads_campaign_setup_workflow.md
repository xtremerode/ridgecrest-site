# Google Ads Campaign Setup Workflow — Ridgecrest Designs
**Use this file with Claude to set up each new Google Ads Search campaign step by step.**
Last updated: 2026-03-27

---

## Before You Start

Have these ready:
- Google Ads account open and logged in
- This workflow file loaded in Claude
- The keyword file for this campaign (e.g., `Custom_Home_Builder_Keywords.txt`)
- The negative keyword file: `Ridgecrest_Negative_Keywords.txt`

The campaign structure below follows the exact settings used for the live **Custom Home Builder | Google Search** campaign. Replicate these settings for each new campaign, swapping out the campaign name, keywords, and ad copy.

---

## STEP 1 — Create New Campaign

1. In Google Ads, click **+ New Campaign**
2. Select goal: **Leads**
3. Select campaign type: **Search**
4. Check **Website visits**
5. Enter website URL: `https://go.ridgecrestdesigns.com`
6. Click **Continue**

---

## STEP 2 — Campaign Settings

### Campaign Name
Use this naming convention:
```
[RMA] {Service Theme} | Google Search
```
Examples:
- `[RMA] Custom Home Builder | Google Search`
- `[RMA] Custom Home | Google Search`
- `[RMA] Design Build | Google Search`
- `[RMA] Kitchen Remodel | Google Search`
- `[RMA] Whole House Remodel | Google Search`

### Bidding
- Bidding strategy: **Maximize Conversions**
- Do NOT set a Target CPA (insufficient data at launch)
- If prompted for a Target CPA, leave it blank

### Budget
- Daily budget: **$125.00**
- Do not exceed $125/day per campaign
- Weekly ceiling across all campaigns combined: $1,000

### Networks
- **Uncheck** "Include Google Search Partners"
- **Uncheck** "Include Google Display Network"
- Search Network ONLY

### Campaign Start/End Dates
- Start: today's date
- End date: none

---

## STEP 3 — Locations

### Add Target Locations
Add each of the following zip codes individually using the **Enter another location** search:

```
94506 — Blackhawk / Danville
94507 — Alamo
94526 — Danville
94528 — Diablo
94549 — Lafayette
94556 — Moraga
94563 — Orinda
94566 — Pleasanton
94568 — Dublin
94582 — San Ramon
94583 — San Ramon
94586 — Sunol
94588 — Pleasanton
94595 — Walnut Creek
94596 — Walnut Creek
94597 — Walnut Creek
94598 — Walnut Creek
```

> Tip: Search each zip code, confirm the correct city appears, then click Add.

### Location Options
- Set to: **Presence: People in or regularly in your targeted locations**
- Do NOT use "People searching for your targeted locations" — this will pull in out-of-area traffic

### Location Exclusions
Click **Exclude locations** and add:
- **Alaska** (state)
- **Hawaii** (state)
- **Canada** (country)

> The full exclusion list from CLAUDE.md Section 12 covers all non-US countries. Adding Alaska, Hawaii, and Canada at minimum is required. Add additional countries if the exclusion UI allows bulk entry.

---

## STEP 4 — Ad Schedule

Set ads to run **Friday, Saturday, Sunday, Monday ONLY**.

1. Go to **Ad Schedule** settings
2. Click **+ Add ad schedule**
3. Add each active day with hours: **12:00 AM – 12:00 AM (all day)**:
   - Friday
   - Saturday
   - Sunday
   - Monday
4. Do NOT add Tuesday, Wednesday, or Thursday
5. Save

> This suppresses all spend on off-days without needing bid adjustments.

---

## STEP 5 — Languages

- Set to: **English**

---

## STEP 6 — Audience Segments (Observation Mode)

Add the following audience segments in **Observation** mode (not Targeting):

| Segment | Category |
|---|---|
| Home Improvement & Remodeling | In-market |
| Residential Properties | In-market |
| Luxury Goods & Services | In-market |
| Home Renovation | In-market |

> Observation mode collects data without restricting reach. Do not switch to Targeting mode until you have enough conversion data to evaluate segment performance.

---

## STEP 7 — Demographics

### Age
- **Enable:** 35–44, 45–54
- **Exclude:** 18–24, 25–34
- **Reduce bids (observation):** 55–64, 65+

### Gender
- Enable: All (men and women)

### Household Income
- **Enable:** Top 10%, 11–20%, 21–30%
- **Exclude:** Lower 50%
- Leave 31–40% and 41–50% in observation

---

## STEP 8 — Create Ad Group

### Ad Group Name
Match the service theme:
```
{Service Theme}
```
Examples:
- `Custom Home Builder`
- `Custom Home`
- `Design Build`
- `Kitchen Remodel`
- `Whole House Remodel`

### Final URL
```
https://go.ridgecrestdesigns.com
```

### Display Path
Use a clean, relevant path:
```
/custom-builder
/custom-home
/design-build
/kitchen-remodel
/whole-house-remodel
```

---

## STEP 9 — Add Keywords

1. Open the keyword file for this campaign (e.g., `Custom_Home_Builder_Keywords.txt`)
2. Copy the full keyword list
3. Paste into the keyword entry box in Google Ads
4. Confirm match types are applied correctly:
   - `[brackets]` = Exact Match
   - `"quotes"` = Phrase Match
5. Do NOT use Broad Match at launch

> Each campaign uses 168 keywords: 7 themes × 12 cities × 2 match types.

---

## STEP 10 — Create Responsive Search Ad (RSA)

### Headlines (add all 15)
```
1.  Custom Home Builder
2.  Design Build Experts
3.  High-End Custom Home Designs
4.  Premium Build Process
5.  Pleasanton's Design Build Firm
6.  Luxury Homes, Flawless Results
7.  We Handle Design & Permits
8.  East Bay's Premier Builder
9.  Ridgecrest Designs
10. Onsite Services Available
11. Luxury Design Build Firm
12. From Vision to Completion
13. Design Build Contractor
14. Design Build Firm
15. Request a Free Consultation
```

> Note: Customize headlines 1–3 and 5 to match the campaign theme (e.g., for Kitchen Remodel, lead with kitchen-specific headlines). Headlines 6–15 can be reused across campaigns.

### Descriptions (add all 4)
```
1. See photo-realistic renders of your custom home before we break ground.
2. Design-build experts serving Pleasanton, Walnut Creek, Danville & the East Bay.
3. We manage design, engineering, permits & construction under one roof. No surprises.
4. Premium custom homes for discerning homeowners. Request a consultation today.
```

> Customize descriptions 1 and 4 to match the campaign theme where relevant.

### Pinning
- Do NOT pin any headlines or descriptions at launch
- Let Google optimize combinations first
- Revisit pinning after 30 days of impression data

---

## STEP 11 — Ad Extensions

### Sitelinks (add all 7)
| Sitelink Text | Final URL |
|---|---|
| Start Your Project | https://ridgecrestdesigns.com/contact |
| Our Design-Build Process | https://ridgecrestdesigns.com/california-process |
| View Our Portfolio | https://ridgecrestdesigns.com/portfolio |
| About Ridgecrest Designs | https://ridgecrestdesigns.com/about |
| Meet Our Team | https://ridgecrestdesigns.com/bios |
| The RD Edit | https://ridgecrestdesigns.com/therdedit |
| Client Testimonials | https://ridgecrestdesigns.com/testimonials |

### Callouts (add all 6)
```
Photo-Realistic Renders
Licensed & Insured
Integrated Design-Build
Serving the East Bay
Luxury Custom Homes
Free Consultation
```

---

## STEP 12 — Conversion Tracking

### Conversion Actions to Link
Confirm both conversion actions are active on the account:

| Action | URL | Type |
|---|---|---|
| Project Inquiry Submitted | https://elevate-scheduling-6b2fdec8.base44.app/inquiry-submitted | Primary |
| Booking Confirmed | https://elevate-scheduling-6b2fdec8.base44.app/booking-confirmed | Secondary |

- **Primary optimization target:** Project Inquiry Submitted
- Do NOT optimize for clicks or impressions alone

> If conversion tracking is not yet set up, go to **Tools → Conversions** and add both URLs as website conversion actions before launching any campaign.

---

## STEP 13 — Negative Keywords

### Account-Level Negatives (add first, one time only)
Open `Ridgecrest_Negative_Keywords.txt` and add these sections at the **account level** (Tools → Shared Library → Negative keyword lists):

1. Section 1 — Price & Budget (highest priority)
2. Section 3 — Jobs & Employment
3. Section 4 — Repair & Maintenance
4. Section 2 — DIY / Research Intent
5. Sections 5–9 — remaining sections

### Campaign-Level Negatives (add per campaign)
From Section 10 of the negative keyword file, add the campaign-specific negatives:

**For Custom Home / Design Build campaigns:**
```
remodel
renovation
bathroom
kitchen
```

**For Kitchen Remodel campaigns:**
```
custom home
new construction
home builder
whole house
```

**For Bathroom Remodel campaigns:**
```
custom home
new construction
home builder
whole house
kitchen
```

---

## STEP 14 — Final Review Checklist

Before saving and publishing, confirm each item:

- [ ] Campaign name follows `[RMA] {Theme} | Google Search` format
- [ ] Bidding: Maximize Conversions, no Target CPA
- [ ] Budget: $125/day
- [ ] Networks: Search only — Search Partners and Display Network OFF
- [ ] All 17 zip codes added
- [ ] Location option: Presence only (not "searching for")
- [ ] Alaska and Hawaii excluded
- [ ] Ad schedule: Friday, Saturday, Sunday, Monday only
- [ ] Language: English
- [ ] Age: 35–44 and 45–54 active; 18–24 and 25–34 excluded
- [ ] Household income: Top 10–30% active; bottom 50% excluded
- [ ] Audience segments: added in Observation mode
- [ ] Keywords: exact and phrase match only, no broad
- [ ] RSA: 15 headlines and 4 descriptions entered
- [ ] Final URL: https://go.ridgecrestdesigns.com
- [ ] Display path matches campaign theme
- [ ] Sitelinks: all 7 added
- [ ] Callouts: all 6 added
- [ ] Conversion actions: both linked and active
- [ ] Account-level negative keywords: imported (first campaign only)
- [ ] Campaign-level negatives: added for this campaign's theme

---

## STEP 15 — After Launch

1. Allow 24–48 hours for ad review and learning phase
2. Do NOT pause or modify the campaign for the first 3 days
3. After 7–14 days, pull the **Search Terms report** and add new negatives
4. After 30 days, review audience segment performance and demographic bid adjustments
5. Never reduce a campaign below $10/day minimum
6. Never reduce a top-performing campaign (score ≥ 60) regardless of daily totals

---

## Campaigns To Build (Ridgecrest RMA Rollout)

| # | Campaign Name | Status | Theme | Keyword File |
|---|---|---|---|---|
| 1 | [RMA] Custom Home Builder \| Google Search | **LIVE** | Custom Home Builder | Custom_Home_Builder_Keywords.txt |
| 2 | [RMA] Custom Home \| Google Search | Pending | Custom Home | — |
| 3 | [RMA] Design Build \| Google Search | Pending | Design Build | — |
| 4 | [RMA] Kitchen Remodel \| Google Search | Pending | Kitchen Remodel | — |
| 5 | [RMA] Whole House Remodel \| Google Search | Pending | Whole House Remodel | — |

---

## Key URLs Reference

| Item | URL |
|---|---|
| Landing page | https://go.ridgecrestdesigns.com |
| Project inquiry form | https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm |
| Inquiry submitted (conversion) | https://elevate-scheduling-6b2fdec8.base44.app/inquiry-submitted |
| Booking confirmed (conversion) | https://elevate-scheduling-6b2fdec8.base44.app/booking-confirmed |
