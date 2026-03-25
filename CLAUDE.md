# Ridgecrest Designs — Claude Code.md
A cohesive Google Ads-first marketing plan built from the full chat history for Ridgecrest Designs.

---

## 1. Company Overview
Ridgecrest Designs is a high-end design-build firm based in Pleasanton, California. The company is known for:
- Photo-realistic renders
- A strong and clearly defined build process
- High-quality teams
- Long-term relationships
- Deep knowledge of design, engineering, permitting, and backend processes
- Attention to detail
- Flawless execution

Ridgecrest Designs should be positioned as a premium, process-driven, technically sophisticated design-build partner for affluent homeowners seeking high-end homes and major remodels.

---

## 2. Primary Business Goal
Generate qualified, high-value project inquiries for:
- Large custom home design-build projects
- High-end custom homes in the $5M to $10M range
- Whole house remodels with budgets of $1M+
- Kitchen remodels with budgets of $150,000+
- Bathroom remodels with budgets of $60,000+
- Master bathroom remodels with budgets of $100,000+

The strategy should intentionally filter out smaller, low-budget jobs and prioritize premium, whole-home, and luxury custom home opportunities.

---

## 3. Ideal Customer Profile

### Age
- 35 to 50 years old

### Household Profile
- High-income homeowners
- Typically families with children ages 2 to 20
- Young professionals and established households
- Looking for long-term homes, luxury upgrades, or legacy residences

### Buyer Mindset
Best-fit prospects are likely to:
- Value quality over price
- Want a turnkey experience
- Prefer a firm that can handle complexity
- Care about communication, process, and trust
- Respond to premium creative and polished presentation
- Want confidence before construction begins

### Geographic Focus / Service Areas
Target only the following service areas:
- Pleasanton
- Walnut Creek
- San Ramon
- Dublin
- Orinda
- Moraga
- Danville
- Alamo
- Lafayette
- Rossmoor
- Sunol
- Diablo


---

## 4. Positioning Strategy
Ridgecrest Designs should not compete on price. The brand should be presented as:
- Premium
- Luxury-focused
- Precise
- Process-oriented
- Technically fluent
- Visually sophisticated
- Trustworthy
- High-touch

### Core Positioning Statement
Ridgecrest Designs delivers luxury design-build services for affluent homeowners who want a seamless, expertly managed experience from vision and visualization through permitting and construction.

---

## 5. Core Differentiators
Every campaign, landing page, and ad message should reinforce these differentiators:
- Photo-realistic renders that create visual certainty before construction starts
- Integrated design-build delivery
- Expertise across design, engineering, permitting, and construction
- Strong backend and permitting process knowledge
- Clear, dependable build process
- Specialized teams
- Strong relationships and communication
- Meticulous attention to detail
- Flawless execution

---

## 6. Services and Offer Prioritization

### Highest Priority
1. Custom design-build homes
2. Luxury custom homes ($5M to $10M)

### Secondary Priority
3. Whole house remodels ($1M+)

### Selective Priority
4. Kitchen remodels ($150,000+)
5. Bathroom remodels ($60,000+)
6. Master bathroom remodels ($100,000+)

### Qualification Principle
Campaigns, ads, and landing pages should be written to attract premium projects and naturally discourage lower-budget leads.

---

## 7. Platform Rollout Plan

### Phase 1: Google Ads First
Start with Google Ads only until the account structure, lead quality, and conversion tracking are working properly.

Primary channel:
- Google Search campaigns

Reason:
- Highest intent
- Best fit for premium services
- Stronger control over budget and lead quality

### Phase 2: Meta
Add Meta after Google Ads is producing strong, qualified results.
Best use cases:
- Retargeting
- Visual storytelling
- Render-driven creative
- Reinforcement of trust and premium brand positioning

### Phase 3: Microsoft Ads
Add Microsoft Ads after Google Ads is stable and profitable enough to expand.
Best use cases:
- Incremental search demand
- Lower-cost supplemental reach for high-intent queries

---

## 8. Budget and Spend Strategy

### Budget Rules
- Weekly ceiling: $1,000 maximum across all platforms combined (hard stop)
- Weekly floor: $500 target minimum — alert if pacing below $400
- Daily soft cap: $250 per day — no budget increases once reached
- Active days only: Friday, Saturday, Sunday, Monday
- Do not run ads Tuesday, Wednesday, or Thursday unless strategy is intentionally revised later

### Weekly and Monthly Spend
- Weekly range: $500–$1,000
- Monthly baseline with a 4-week month: $2,000–$4,000

### Spend Philosophy
- Performance-driven allocation — never cap a top-performing campaign with a flat limit
- Shift budget from under-performers to top performers continuously
- Optimize for qualified conversions, not clicks or impressions
- The $1,000 weekly ceiling is the only absolute limit — within it, budget follows performance
- Never reduce a top-performing campaign (score ≥ 60) regardless of daily totals
- Never reduce any campaign below $10/day minimum

### Spend Guardrails
- Never exceed $1,000/week combined across all platforms
- Daily soft cap of $250 blocks new budget increases but permits reallocations
- Escalation alert fires if daily spend exceeds $300 or weekly exceeds $1,100
- Concentrate budget on highest-converting campaigns first
- Shift spend toward top performers and away from zero-conversion campaigns
- Keep structure tight enough that limited budget produces measurable results

### Budget Use Principle
Budget follows performance. Top performers receive budget from under-performers. The weekly ceiling ($1,000) is the only hard constraint — within it, the optimizer allocates dynamically based on CPL and conversion rate.

### Ad Scheduling — All Platforms (MANDATORY)
Ads run Friday, Saturday, Sunday, Monday ONLY. Tuesday, Wednesday, Thursday must be fully suppressed on every platform using that platform's native scheduling tool.

#### Meta — Campaign pause/unpause by day of week (meta_manager.py Step 0)
Meta's native adset_schedule requires lifetime budgets and is incompatible with daily
budget campaigns. Instead, meta_manager enforces active days by pausing all campaigns
on Tue/Wed/Thu and resuming them on Fri/Sat/Sun/Mon each pipeline run.

#### Microsoft Ads — DayTimeCriterion bid adjustments (applied at campaign level)
Set -100% bid adjustment for Tuesday, Wednesday, Thursday.
Days suppressed: Tuesday, Wednesday, Thursday
Days active: Friday, Saturday, Sunday, Monday (0% adjustment = normal serving)

#### Google Ads — AdSchedule campaign criteria (staged, applies when developer token approved)
Add AdScheduleInfo criteria for Friday, Saturday, Sunday, Monday only.
Remove or set -100% bid modifier for Tuesday, Wednesday, Thursday.

---

## 9. Conversion Strategy

### Official Landing Page
Use this landing page URL:
https://go.ridgecrestdesigns.com

### Conversion Events (All Platforms)
Two confirmed conversion URLs — static, no unique IDs:

| Event | URL | Type |
|---|---|---|
| Project Inquiry Submitted | https://elevate-scheduling-6b2fdec8.base44.app/inquiry-submitted | Primary |
| Booking Confirmed | https://elevate-scheduling-6b2fdec8.base44.app/booking-confirmed | Secondary |

### Meta Pixel
- **Pixel ID:** `534314263109913` (Ridgecrest Designs)
- Must be installed on all pages of the Base44 app (`elevate-scheduling-6b2fdec8.base44.app`)

### Meta Custom Conversions
| Name | ID | Trigger | Event Type |
|---|---|---|---|
| Project Inquiry Submitted | `1274199281573639` | URL contains `inquiry-submitted` | LEAD |
| Booking Confirmed | `2010554443142598` | URL contains `booking-confirmed` | COMPLETE_REGISTRATION |

### Conversion Quality Standard
- Primary optimization target: Project Inquiry Submitted
- Secondary: Booking Confirmed
- Do NOT optimize for clicks or impressions alone — always tie campaign optimization to one of these two conversion events
- At low conversion volume, optimize for Landing Page Views and use these as reported conversions only until sufficient data accumulates (50+ events/week)

### Pixel Installation Required
The Meta Pixel script must be added to the root layout of the Base44 app. Without it, the custom conversions will not fire. Provide Base44 with pixel ID `534314263109913` and ask them to add the standard Meta Pixel init script to the app's root layout or `index.html`.

---

## 10. Performance Targets

### Cost Per Lead Goal
- Target CPL: $150 to $500

### Optimization Goal
- Maximize high-quality project inquiry submissions
- Prioritize lead quality over total lead volume
- Focus on premium project opportunities rather than cheaper form submissions

### Practical Interpretation
At this spend level, fewer but better leads are preferable to many low-quality inquiries.

---

## 11. Google Ads Strategy

### Primary Campaign Type
- Google Search only at launch

### Why Search First
Search captures prospects actively looking for services such as:
- Design build
- Custom home builder
- Whole house remodel
- Kitchen remodel
- Bathroom remodel
- Interior design firm
- Home builder
- General contractor
- Architect
- Design build contractor

### Recommended Initial Campaign Buckets
Separate campaigns or tightly controlled ad groups by service intent:
- Design Build
- Custom Home
- Custom Home Builder
- Whole House Remodel
- Kitchen Remodel
- Bathroom Remodel
- Interior Design
- Interior Design Firm
- Kitchen Design
- Bathroom Design
- Home Design
- Architect
- Home Builder
- General Contractor
- Remodeling Contractor
- Home Renovation
- Design Build Contractor

### Match Type Guidance
Use:
- Exact match
- Phrase match

Avoid broad match early unless the account later has enough data and strong negatives.

### Campaign Structure Guidance
- Segment by service type
- Segment by location as needed
- Keep ad groups tightly themed
- Align keywords, ad copy, and landing pages closely
- Emphasize premium service and project scale
- Use negative keywords aggressively to reduce irrelevant and low-budget traffic

---

## 12. Geographic Targeting Strategy

### Required Locations
Target only these service areas:
- Walnut Creek
- Pleasanton
- Sunol
- San Ramon
- Dublin
- Orinda
- Moraga
- Danville
- Alamo
- Lafayette
- Rossmoor
- Diablo



### Zip Code Targeting (MANDATORY)
- 94596
- 94595
- 94588
- 94586
- 94583
- 94582
- 94568
- 94566
- 94563
- 94556

Rules:
- These zip codes must be actively targeted from the start
- Do not delay or phase in zip targeting
- Campaigns should be restricted to these zip codes in addition to city targeting
- Use zip codes to refine audience quality and eliminate lower-income areas

---

## 13. Messaging Strategy

### Core Messaging Themes
- Luxury
- Precision
- Confidence
- Clarity
- Process
- Trust
- Expertise
- Premium quality

### Messaging Angles
- Luxury design-build expertise
- Seamless execution from concept to construction
- Photo-realistic renders that reduce uncertainty
- Deep permitting and engineering knowledge
- Whole-home and custom-home specialists
- Clear process and dependable communication
- Premium results for discerning homeowners

### Messaging Rules
- Do not lead with low price
- Do not present the brand as a commodity contractor
- Emphasize quality and process over discounts
- Use premium language that attracts affluent homeowners
- Make it clear Ridgecrest Designs is built for large, serious projects

---

## 14. Landing Page and Funnel Guidance
Because the budget is limited, the funnel should be highly intentional.

### Landing Page Priorities
- Match user intent by service
- Reinforce service area relevance
- Show premium project quality
- Include renders, process, team credibility, and project sophistication
- Set expectations around project scope and quality
- Pre-qualify leads where possible

### Conversion Path
1. Click ad
2. Land on the official landing page
3. Submit project inquiry information
4. Count a conversion when the project inquiry form is submitted

### Official URLs
- Landing page: https://go.ridgecrestdesigns.com
- Project inquiry form: https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm

### Pre-Qualification Suggestions
Use copy and form structure to help filter smaller projects:
- Mention premium service
- Mention project scale
- Use “starting at” or minimum-investment framing where appropriate
- Emphasize whole-home and luxury expertise

---

## 15. Optimization Principles
- Prioritize top performers
- Optimize for qualified conversions
- Shift spend toward campaigns driving project inquiry submissions
- Remove waste aggressively
- Focus on exact and phrase match first
- Build strong negative keyword lists
- Review search terms closely
- Keep geo targeting tight
- Scale only after proof of quality

---

## 16. Future Expansion Plan

### Meta
When added, focus on:
- Retargeting site visitors
- Showcasing render work
- Reinforcing authority, trust, and luxury positioning
- Supporting higher-consideration buyer journeys

### Microsoft Ads
When added, focus on:
- Replicating proven Google Search structures
- Expanding incremental reach
- Testing performance by keyword segment

### App Integration
Later, connect app-based confirmed booking data back into campaign optimization so advertising can be measured against true sales-qualified activity.

---

## 17. Keyword Structure (Search Campaign Ready)

## Match Types
- Exact Match → [keyword]
- Phrase Match → "keyword"

---

## DESIGN BUILD
[design build walnut creek]
"design build walnut creek"
[design build pleasanton]
"design build pleasanton"
[design build sunol]
"design build sunol"
[design build san ramon]
"design build san ramon"
[design build dublin]
"design build dublin"
[design build orinda]
"design build orinda"
[design build moraga]
"design build moraga"
[design build danville]
"design build danville"
[design build alamo]
"design build alamo"
[design build lafayette]
"design build lafayette"
[design build rossmoor]
"design build rossmoor"
[design build diablo]
"design build diablo"

---

## KITCHEN REMODEL
[kitchen remodel walnut creek]
"kitchen remodel walnut creek"
[kitchen remodel pleasanton]
"kitchen remodel pleasanton"
[kitchen remodel sunol]
"kitchen remodel sunol"
[kitchen remodel san ramon]
"kitchen remodel san ramon"
[kitchen remodel dublin]
"kitchen remodel dublin"
[kitchen remodel orinda]
"kitchen remodel orinda"
[kitchen remodel moraga]
"kitchen remodel moraga"
[kitchen remodel danville]
"kitchen remodel danville"
[kitchen remodel alamo]
"kitchen remodel alamo"
[kitchen remodel lafayette]
"kitchen remodel lafayette"
[kitchen remodel rossmoor]
"kitchen remodel rossmoor"
[kitchen remodel diablo]
"kitchen remodel diablo"

---

## BATHROOM REMODEL
[bathroom remodel walnut creek]
"bathroom remodel walnut creek"
[bathroom remodel pleasanton]
"bathroom remodel pleasanton"
[bathroom remodel sunol]
"bathroom remodel sunol"
[bathroom remodel san ramon]
"bathroom remodel san ramon"
[bathroom remodel dublin]
"bathroom remodel dublin"
[bathroom remodel orinda]
"bathroom remodel orinda"
[bathroom remodel moraga]
"bathroom remodel moraga"
[bathroom remodel danville]
"bathroom remodel danville"
[bathroom remodel alamo]
"bathroom remodel alamo"
[bathroom remodel lafayette]
"bathroom remodel lafayette"
[bathroom remodel rossmoor]
"bathroom remodel rossmoor"
[bathroom remodel diablo]
"bathroom remodel diablo"

---

## WHOLE HOUSE REMODEL
[whole house remodel walnut creek]
"whole house remodel walnut creek"
[whole house remodel pleasanton]
"whole house remodel pleasanton"
[whole house remodel sunol]
"whole house remodel sunol"
[whole house remodel san ramon]
"whole house remodel san ramon"
[whole house remodel dublin]
"whole house remodel dublin"
[whole house remodel orinda]
"whole house remodel orinda"
[whole house remodel moraga]
"whole house remodel moraga"
[whole house remodel danville]
"whole house remodel danville"
[whole house remodel alamo]
"whole house remodel alamo"
[whole house remodel lafayette]
"whole house remodel lafayette"
[whole house remodel rossmoor]
"whole house remodel rossmoor"
[whole house remodel diablo]
"whole house remodel diablo"

---

## CUSTOM HOME
[custom home walnut creek]
"custom home walnut creek"
[custom home pleasanton]
"custom home pleasanton"
[custom home sunol]
"custom home sunol"
[custom home san ramon]
"custom home san ramon"
[custom home dublin]
"custom home dublin"
[custom home orinda]
"custom home orinda"
[custom home moraga]
"custom home moraga"
[custom home danville]
"custom home danville"
[custom home alamo]
"custom home alamo"
[custom home lafayette]
"custom home lafayette"
[custom home rossmoor]
"custom home rossmoor"
[custom home diablo]
"custom home diablo"

---

## INTERIOR DESIGN
[interior design walnut creek]
"interior design walnut creek"
[interior design pleasanton]
"interior design pleasanton"
[interior design sunol]
"interior design sunol"
[interior design san ramon]
"interior design san ramon"
[interior design dublin]
"interior design dublin"
[interior design orinda]
"interior design orinda"
[interior design moraga]
"interior design moraga"
[interior design danville]
"interior design danville"
[interior design alamo]
"interior design alamo"
[interior design lafayette]
"interior design lafayette"
[interior design rossmoor]
"interior design rossmoor"
[interior design diablo]
"interior design diablo"

---

## INTERIOR DESIGN FIRM
[interior design firm walnut creek]
"interior design firm walnut creek"
[interior design firm pleasanton]
"interior design firm pleasanton"
[interior design firm sunol]
"interior design firm sunol"
[interior design firm san ramon]
"interior design firm san ramon"
[interior design firm dublin]
"interior design firm dublin"
[interior design firm orinda]
"interior design firm orinda"
[interior design firm moraga]
"interior design firm moraga"
[interior design firm danville]
"interior design firm danville"
[interior design firm alamo]
"interior design firm alamo"
[interior design firm lafayette]
"interior design firm lafayette"
[interior design firm rossmoor]
"interior design firm rossmoor"
[interior design firm diablo]
"interior design firm diablo"

---

## KITCHEN DESIGN
[kitchen design walnut creek]
"kitchen design walnut creek"
[kitchen design pleasanton]
"kitchen design pleasanton"
[kitchen design sunol]
"kitchen design sunol"
[kitchen design san ramon]
"kitchen design san ramon"
[kitchen design dublin]
"kitchen design dublin"
[kitchen design orinda]
"kitchen design orinda"
[kitchen design moraga]
"kitchen design moraga"
[kitchen design danville]
"kitchen design danville"
[kitchen design alamo]
"kitchen design alamo"
[kitchen design lafayette]
"kitchen design lafayette"
[kitchen design rossmoor]
"kitchen design rossmoor"
[kitchen design diablo]
"kitchen design diablo"

---

## BATHROOM DESIGN
[bathroom design walnut creek]
"bathroom design walnut creek"
[bathroom design pleasanton]
"bathroom design pleasanton"
[bathroom design sunol]
"bathroom design sunol"
[bathroom design san ramon]
"bathroom design san ramon"
[bathroom design dublin]
"bathroom design dublin"
[bathroom design orinda]
"bathroom design orinda"
[bathroom design moraga]
"bathroom design moraga"
[bathroom design danville]
"bathroom design danville"
[bathroom design alamo]
"bathroom design alamo"
[bathroom design lafayette]
"bathroom design lafayette"
[bathroom design rossmoor]
"bathroom design rossmoor"
[bathroom design diablo]
"bathroom design diablo"

---

## HOME DESIGN
[home design walnut creek]
"home design walnut creek"
[home design pleasanton]
"home design pleasanton"
[home design sunol]
"home design sunol"
[home design san ramon]
"home design san ramon"
[home design dublin]
"home design dublin"
[home design orinda]
"home design orinda"
[home design moraga]
"home design moraga"
[home design danville]
"home design danville"
[home design alamo]
"home design alamo"
[home design lafayette]
"home design lafayette"
[home design rossmoor]
"home design rossmoor"
[home design diablo]
"home design diablo"

---

## ARCHITECT
[architect walnut creek]
"architect walnut creek"
[architect pleasanton]
"architect pleasanton"
[architect sunol]
"architect sunol"
[architect san ramon]
"architect san ramon"
[architect dublin]
"architect dublin"
[architect orinda]
"architect orinda"
[architect moraga]
"architect moraga"
[architect danville]
"architect danville"
[architect alamo]
"architect alamo"
[architect lafayette]
"architect lafayette"
[architect rossmoor]
"architect rossmoor"
[architect diablo]
"architect diablo"

---

## HOME BUILDER
[home builder walnut creek]
"home builder walnut creek"
[home builder pleasanton]
"home builder pleasanton"
[home builder sunol]
"home builder sunol"
[home builder san ramon]
"home builder san ramon"
[home builder dublin]
"home builder dublin"
[home builder orinda]
"home builder orinda"
[home builder moraga]
"home builder moraga"
[home builder danville]
"home builder danville"
[home builder alamo]
"home builder alamo"
[home builder lafayette]
"home builder lafayette"
[home builder rossmoor]
"home builder rossmoor"
[home builder diablo]
"home builder diablo"

---

## GENERAL CONTRACTOR
[general contractor walnut creek]
"general contractor walnut creek"
[general contractor pleasanton]
"general contractor pleasanton"
[general contractor sunol]
"general contractor sunol"
[general contractor san ramon]
"general contractor san ramon"
[general contractor dublin]
"general contractor dublin"
[general contractor orinda]
"general contractor orinda"
[general contractor moraga]
"general contractor moraga"
[general contractor danville]
"general contractor danville"
[general contractor alamo]
"general contractor alamo"
[general contractor lafayette]
"general contractor lafayette"
[general contractor rossmoor]
"general contractor rossmoor"
[general contractor diablo]
"general contractor diablo"

---

## REMODELING CONTRACTOR
[remodeling contractor walnut creek]
"remodeling contractor walnut creek"
[remodeling contractor pleasanton]
"remodeling contractor pleasanton"
[remodeling contractor sunol]
"remodeling contractor sunol"
[remodeling contractor san ramon]
"remodeling contractor san ramon"
[remodeling contractor dublin]
"remodeling contractor dublin"
[remodeling contractor orinda]
"remodeling contractor orinda"
[remodeling contractor moraga]
"remodeling contractor moraga"
[remodeling contractor danville]
"remodeling contractor danville"
[remodeling contractor alamo]
"remodeling contractor alamo"
[remodeling contractor lafayette]
"remodeling contractor lafayette"
[remodeling contractor rossmoor]
"remodeling contractor rossmoor"
[remodeling contractor diablo]
"remodeling contractor diablo"

---

## CUSTOM HOME BUILDER
[custom home builder walnut creek]
"custom home builder walnut creek"
[custom home builder pleasanton]
"custom home builder pleasanton"
[custom home builder sunol]
"custom home builder sunol"
[custom home builder san ramon]
"custom home builder san ramon"
[custom home builder dublin]
"custom home builder dublin"
[custom home builder orinda]
"custom home builder orinda"
[custom home builder moraga]
"custom home builder moraga"
[custom home builder danville]
"custom home builder danville"
[custom home builder alamo]
"custom home builder alamo"
[custom home builder lafayette]
"custom home builder lafayette"
[custom home builder rossmoor]
"custom home builder rossmoor"
[custom home builder diablo]
"custom home builder diablo"

---

## HOME RENOVATION
[home renovation walnut creek]
"home renovation walnut creek"
[home renovation pleasanton]
"home renovation pleasanton"
[home renovation sunol]
"home renovation sunol"
[home renovation san ramon]
"home renovation san ramon"
[home renovation dublin]
"home renovation dublin"
[home renovation orinda]
"home renovation orinda"
[home renovation moraga]
"home renovation moraga"
[home renovation danville]
"home renovation danville"
[home renovation alamo]
"home renovation alamo"
[home renovation lafayette]
"home renovation lafayette"
[home renovation rossmoor]
"home renovation rossmoor"
[home renovation diablo]
"home renovation diablo"

---

## DESIGN BUILD CONTRACTOR
[design build contractor walnut creek]
"design build contractor walnut creek"
[design build contractor pleasanton]
"design build contractor pleasanton"
[design build contractor sunol]
"design build contractor sunol"
[design build contractor san ramon]
"design build contractor san ramon"
[design build contractor dublin]
"design build contractor dublin"
[design build contractor orinda]
"design build contractor orinda"
[design build contractor moraga]
"design build contractor moraga"
[design build contractor danville]
"design build contractor danville"
[design build contractor alamo]
"design build contractor alamo"
[design build contractor lafayette]
"design build contractor lafayette"
[design build contractor rossmoor]
"design build contractor rossmoor"
[design build contractor diablo]
"design build contractor diablo"

---

## MASTER BATHROOM REMODEL
[master bathroom remodel walnut creek]
"master bathroom remodel walnut creek"
[master bathroom remodel pleasanton]
"master bathroom remodel pleasanton"
[master bathroom remodel sunol]
"master bathroom remodel sunol"
[master bathroom remodel san ramon]
"master bathroom remodel san ramon"
[master bathroom remodel dublin]
"master bathroom remodel dublin"
[master bathroom remodel orinda]
"master bathroom remodel orinda"
[master bathroom remodel moraga]
"master bathroom remodel moraga"
[master bathroom remodel danville]
"master bathroom remodel danville"
[master bathroom remodel alamo]
"master bathroom remodel alamo"
[master bathroom remodel lafayette]
"master bathroom remodel lafayette"
[master bathroom remodel rossmoor]
"master bathroom remodel rossmoor"
[master bathroom remodel diablo]
"master bathroom remodel diablo"

---

## 18. Meta Audience Strategy

### Saved Audience — Primary (MANDATORY for all Meta campaigns)
**Name:** refined location age and interest 2/26
**Saved Audience ID:** `6934900931693`
**Account:** act_58393749

#### Audience Spec
- **Age:** 35–55
- **Gender:** Female (genders: [2])
- **Family Status (flexible_spec):** Parents with preschoolers (3–5), early school-age (6–8), preteens (9–12), teenagers (13–17), adult children (18–26)
- **Zip Codes:** 94506, 94507, 94526, 94549, 94551, 94556, 94563, 94566, 94568, 94582, 94583, 94588
- **Location Type:** home + recent

#### Advantage+ Audience Setting
- **ALWAYS set `targeting_automation.advantage_audience = 0`**
- This saved audience must be used as a hard constraint, not a signal
- Do NOT allow Meta to expand beyond this audience definition
- The budget is too limited ($125/day) to absorb broad/untargeted impressions

#### Why This Audience
- Directly matches the ICP: affluent homeowners, families with children, premium East Bay zip codes
- Built by the client from firsthand knowledge of who Ridgecrest's customers are
- Zip codes overlap with the approved service area targeting in §12
- Interest + family status layering pre-qualifies intent before the click

#### API Targeting Spec (use this verbatim when creating/updating Meta ad sets)
```json
{
  "age_min": 35,
  "age_max": 55,
  "genders": [2],
  "flexible_spec": [
    {
      "family_statuses": [
        {"id": "6023005529383"},
        {"id": "6023005570783"},
        {"id": "6023005681983"},
        {"id": "6023005718983"},
        {"id": "6023080302983"}
      ]
    }
  ],
  "geo_locations": {
    "zips": [
      {"key": "US:94506"}, {"key": "US:94507"}, {"key": "US:94526"},
      {"key": "US:94549"}, {"key": "US:94551"}, {"key": "US:94556"},
      {"key": "US:94563"}, {"key": "US:94566"}, {"key": "US:94568"},
      {"key": "US:94582"}, {"key": "US:94583"}, {"key": "US:94588"}
    ],
    "location_types": ["home", "recent"]
  },
  "targeting_automation": {
    "advantage_audience": 0
  }
}
```

---

## 19. Operating Summary
This file is intended to guide Claude Code or any campaign-building workflow for Ridgecrest Designs using the full chat history and all revisions.

### New Campaign Grace Period
New Meta campaigns go through ad review and a learning phase before they start spending. A campaign showing ACTIVE with $0 spend and 0 impressions is NOT underperforming — it is processing. This can take 24–48 hours or longer. Never recommend pausing, flagging, or modifying a campaign that is less than 3 days old regardless of spend or conversion data.

### Meta Conversion Tracking
Meta lead form completions will show zero for campaigns that drive traffic to the Base44 landing page (`elevate-scheduling-6b2fdec8.base44.app`). Conversions are tracked via the Meta Pixel (ID: `534314263109913`) on the landing page, not as native Meta lead forms. Zero leads in Meta reporting does not mean zero conversions. Always evaluate Meta campaign performance using landing page views and pixel-based conversion events, not Meta lead counts.

### Existing Meta Campaigns
The following active campaigns were running before the RMA strategy was implemented and use `advantage_audience=1` with age 18–65. Do NOT change their targeting — they are generating leads within target CPL and should be evaluated on performance data, not targeting configuration:
- Lead Gen | Custom Home Design & Build (Refresh) 2/8/2026 — CPL ~$260, 11 leads/30d
- Lead Gen | Home Remodel (Refresh) 2/8/26 — CPL ~$149, 18 leads/30d
- booking AI test 1 and 2 — $0.54/landing page view, conversion data via pixel only

### Non-Negotiables
- Google Ads first
- $125/day maximum
- Friday through Monday only
- Focus on premium projects
- Whole house remodels must be treated as $1M+ opportunities
- Optimize for submitted project inquiry forms as the current conversion action
- Use the official landing page and project inquiry URLs provided in this file
- Use exact and phrase match first
- Emphasize luxury positioning
- Prioritize top performers
- Maintain strong geographic focus
- Restrict campaigns to the approved service areas listed in this file
- Provide Claude Code all required location and spending guardrails up front
- Expand to Meta and Microsoft only after Google Ads is working properly
- All Meta ad sets MUST use saved audience ID 6934900931693 with advantage_audience=0

