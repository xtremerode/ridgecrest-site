# Ridgecrest Designs — Marketing Strategy & Campaign Rules

> This file is auto-loaded when working in the `ridgecrest-agency/` directory.
> Code governance, git rules, and execution guardrail live in the root `agent/CLAUDE.md`.

---

## 1. Company Overview
Ridgecrest Designs is a high-end design-build firm based in Pleasanton, California. Known for:
- Photo-realistic renders
- A strong and clearly defined build process
- High-quality teams and long-term relationships
- Deep knowledge of design, engineering, permitting, and backend processes
- Attention to detail and flawless execution

**Contact:** Tyler Ridgecrest (Founder) — 5502 Sunol Blvd Suite 100, Pleasanton CA 94566 — 925-784-2798 — info@ridgecrestdesigns.com — Founded 2013

---

## 2. Primary Business Goal
Generate qualified, high-value project inquiries for:
- Large custom home design-build projects ($5M–$10M)
- Whole house remodels ($1M+)
- Kitchen remodels ($150,000+)
- Bathroom remodels ($60,000+)
- Master bathroom remodels ($100,000+)

Intentionally filter out smaller, low-budget jobs.

---

## 3. Ideal Customer Profile
- **Age:** 35–50
- **Household:** High-income homeowners, families with children ages 2–20
- **Mindset:** Values quality over price, wants turnkey experience, cares about process and trust
- **Geography:** Pleasanton, Walnut Creek, San Ramon, Dublin, Orinda, Moraga, Danville, Alamo, Lafayette, Rossmoor, Sunol, Diablo

---

## 4. Positioning
Do not compete on price. Position as:
- Premium, luxury-focused, precise, process-oriented, technically fluent, visually sophisticated, trustworthy, high-touch

**Core Statement:** Ridgecrest Designs delivers luxury design-build services for affluent homeowners who want a seamless, expertly managed experience from vision and visualization through permitting and construction.

---

## 5. Core Differentiators
Reinforce in every campaign, ad, and landing page:
- Photo-realistic renders — visual certainty before construction starts
- Integrated design-build delivery
- Expertise across design, engineering, permitting, and construction
- Clear, dependable build process
- Specialized teams, strong relationships, meticulous attention to detail
- Flawless execution

---

## 6. Services and Offer Prioritization
1. Custom design-build homes (highest priority)
2. Luxury custom homes ($5M–$10M)
3. Whole house remodels ($1M+)
4. Kitchen remodels ($150,000+)
5. Bathroom / master bathroom remodels ($60,000–$100,000+)

Campaigns, ads, and landing pages should attract premium projects and naturally discourage lower-budget leads.

---

## 7. Platform Rollout Plan
- **Phase 1 (current):** Google Ads Search only
- **Phase 2:** Meta — add after Google Ads produces qualified results (retargeting, visual storytelling, render-driven creative)
- **Phase 3:** Microsoft Ads — add after Google is stable (incremental reach, replicate proven structures)

---

## 8. Budget and Spend Strategy

### Hard Rules
- **Weekly ceiling:** $1,000 maximum across all platforms (hard stop)
- **Weekly floor:** $500 target — alert if pacing below $400
- **Daily soft cap:** $250/day — no new budget increases once reached
- **Active days:** Friday, Saturday, Sunday, Monday ONLY
- **Off days:** Tuesday, Wednesday, Thursday — fully suppressed on every platform

### Spend Philosophy
- Budget follows performance — shift from under-performers to top performers continuously
- Never reduce a top-performing campaign (score ≥ 60) regardless of daily totals
- Never reduce any campaign below $10/day minimum
- Escalation alert fires if daily spend exceeds $300 or weekly exceeds $1,100
- Optimize for qualified conversions, not clicks or impressions

### Ad Scheduling Implementation
- **Meta:** Pause all campaigns Tue/Wed/Thu, resume Fri/Sat/Sun/Mon each pipeline run (daily budget campaigns cannot use adset_schedule)
- **Microsoft Ads:** Set -100% bid adjustment for Tue/Wed/Thu at campaign level (DayTimeCriterion)
- **Google Ads:** AdSchedule criteria for Fri/Sat/Sun/Mon only; -100% modifier for Tue/Wed/Thu

---

## 9. Conversion Strategy

### URLs
- **Landing page:** https://go.ridgecrestdesigns.com
- **Project inquiry form:** https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm
- **Inquiry submitted (primary conversion):** https://elevate-scheduling-6b2fdec8.base44.app/inquiry-submitted
- **Booking confirmed (secondary conversion):** https://elevate-scheduling-6b2fdec8.base44.app/booking-confirmed

### Meta Pixel & Custom Conversions
- **Pixel ID:** `534314263109913`
- Project Inquiry Submitted — ID `1274199281573639` — URL contains `inquiry-submitted` — LEAD
- Booking Confirmed — ID `2010554443142598` — URL contains `booking-confirmed` — COMPLETE_REGISTRATION

### Optimization Rules
- Primary target: Project Inquiry Submitted
- Secondary: Booking Confirmed
- Never optimize for clicks or impressions alone
- At low conversion volume: optimize for Landing Page Views until 50+ events/week

### Meta Conversion Tracking Note
Meta lead counts will show zero for Base44-destination campaigns. Conversions fire via pixel only. Zero Meta leads ≠ zero conversions. Always evaluate via landing page views and pixel events.

---

## 10. Performance Targets
- **Target CPL:** $150–$500
- Fewer, better leads preferred over many low-quality inquiries
- Maximize high-quality project inquiry submissions

---

## 11. Google Ads Strategy
- Search campaigns only at launch
- Exact match and phrase match — no broad match until sufficient data and strong negatives
- Segment by service type; keep ad groups tightly themed
- Use negative keywords aggressively
- Keyword file: `/home/claudeuser/agent/downloads/Ridgecrest_Keywords_Master.txt` (442 keywords, 18 themes × 12 cities)
- Negative keywords: `/home/claudeuser/agent/downloads/Ridgecrest_Negative_Keywords.txt`

---

## 12. Geographic Targeting

### Service Areas (all platforms)
Walnut Creek, Pleasanton, Sunol, San Ramon, Dublin, Orinda, Moraga, Danville, Alamo, Lafayette, Rossmoor, Diablo

### Zip Codes (MANDATORY — all platforms)
94506, 94507, 94526, 94528, 94549, 94556, 94563, 94566, 94568, 94582, 94583, 94586, 94588, 94595, 94596, 94597, 94598

### Location Exclusions (MANDATORY — all platforms)
Exclude all countries outside the United States, plus Alaska and Hawaii.

---

## 13. Messaging Strategy

### Rules
- Do not lead with low price
- Do not position as a commodity contractor
- Emphasize quality, process, and expertise over discounts
- Use premium language that attracts affluent homeowners
- Make clear Ridgecrest is built for large, serious projects

### Core Themes
Luxury, Precision, Confidence, Clarity, Process, Trust, Expertise, Premium quality

### Angles
- Luxury design-build expertise
- Seamless execution from concept to construction
- Photo-realistic renders that reduce uncertainty
- Deep permitting and engineering knowledge
- Whole-home and custom-home specialists
- Clear process and dependable communication

---

## 14. Landing Page and Funnel Guidance
- Match user intent by service
- Reinforce service area relevance
- Show premium project quality (renders, process, team credibility)
- Pre-qualify: use "starting at" framing, emphasize project scale and luxury expertise

---

## 15. Optimization Principles
- Prioritize top performers
- Optimize for qualified conversions (project inquiry submissions)
- Shift spend toward top performers, remove waste aggressively
- Exact and phrase match first
- Keep geo targeting tight — scale only after proof of quality

---

## 16. Meta Audience Strategy

### Saved Audience (MANDATORY for all [RMA] Meta campaigns)
- **Name:** refined location age and interest 2/26
- **Saved Audience ID:** `6934900931693`
- **Account:** act_58393749
- **ALWAYS set `targeting_automation.advantage_audience = 0`** — hard constraint, not a signal

### API Targeting Spec (use verbatim when creating/updating [RMA] ad sets)
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
      {"key": "US:94528"}, {"key": "US:94549"}, {"key": "US:94556"},
      {"key": "US:94563"}, {"key": "US:94566"}, {"key": "US:94568"},
      {"key": "US:94582"}, {"key": "US:94583"}, {"key": "US:94586"},
      {"key": "US:94588"}, {"key": "US:94595"}, {"key": "US:94596"},
      {"key": "US:94597"}, {"key": "US:94598"}
    ],
    "location_types": ["home", "recent"]
  },
  "targeting_automation": {
    "advantage_audience": 0
  }
}
```

### Do NOT touch these existing Meta campaigns (advantage_audience=1 intentionally, producing leads at target CPL)
- Lead Gen | Custom Home Design & Build (Refresh) 2/8/2026
- Lead Gen | Home Remodel (Refresh) 2/8/26
- booking AI test 1 and 2

### New Campaign Grace Period
New Meta campaigns take 24–48h+ for ad review and learning phase. ACTIVE status with $0 spend is NOT underperforming. Never pause, flag, or modify a campaign less than 3 days old.

---

## 17. Non-Negotiables
- Google Ads first
- $1,000/week maximum ($125/day per campaign)
- Friday through Monday only — no exceptions
- Focus on premium projects only
- Whole house remodels = $1M+ opportunities
- Optimize for submitted project inquiry forms (primary conversion action)
- Use exact and phrase match first
- Emphasize luxury positioning throughout
- Prioritize top performers; maintain strong geographic focus
- Restrict all campaigns to the approved service areas in §12
- All [RMA] Meta ad sets MUST use saved audience ID `6934900931693` with `advantage_audience=0`
- Compliance agent auto-fix applies ONLY to `[RMA]` campaigns — never touch non-RMA campaigns


---

## Agent-Added Rules

- NEVER run git filter-repo without first backing up all tracked image and asset files. git filter-repo rewrites git history AND simultaneously deletes those files from the working tree. To stop committing images going forward use .gitignore + git rm --cached, NOT filter-repo. Incident 2026-04-26: filter-repo deleted 1761 WebP variants and 61 original Wix source photos from disk. AI renders (not regeneratable from source) were also permanently lost.
