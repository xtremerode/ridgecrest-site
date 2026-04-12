# CURRENT_STATUS.md
## Ridgecrest Designs - Campaign Status
### Last Updated: April 11, 2026 11:09 AM PDT

---

## Google Ads - Perplexity Test One

- **Status**: ENABLED (Live)
- **Campaign ID**: 23734851306
- **Daily Budget**: $200/day
- **Max CPC Bid**: $25 (all ad groups)
- **Schedule**: 7 days/week with bid adjustments
  - Fri/Sat/Sun/Mon: Full bid, +20% evening (6-10pm)
  - Tue/Wed/Thu: -25% bid, full bid evening (6-10pm)
- **Location Targeting**: 16 zip codes, PRESENCE only
- **Martinez (94553)**: REMOVED April 11, 2026

### Ad Groups (7) - Created April 11, 2026
| Ad Group | Keywords | Status |
|----------|----------|--------|
| [PX] AG1 - Kitchen Remodeling | 27 | ENABLED |
| [PX] AG2 - Bathroom Remodeling | 23 | ENABLED |
| [PX] AG3 - Whole House and Home Remodel | 44 | ENABLED |
| [PX] AG4 - Design-Build and Custom | 25 | ENABLED |
| [PX] AG5 - Home Additions and ADU | 38 | ENABLED |
| [PX] AG6 - Interior Design and Architecture | 42 | ENABLED |
| [PX] AG7 - General Contractor and Neighborhood | 47 | ENABLED |
| **TOTAL** | **246** | |

### Keywords: 246 total (all broad match)
- 88 generic/near-me keywords
- 143 city-specific (11 patterns x 13 cities)
- 15 neighborhood-specific (golf course/country club verified)
- Full strategy doc: campaigns/keyword_strategy_final_2026_04_11.md

### Negative Keywords: 198 (campaign-level, phrase match)
- 10 categories covering job seekers, DIY, free/cheap/budget, education, wholesale/supplies, commercial/industrial, non-offered services, irrelevant remodeling, lead aggregators, brand safety
- "affordable" included per Henry instruction

### Cities Targeted (13):
Walnut Creek, Danville, Pleasanton, San Ramon, Lafayette, Alamo, Moraga, Orinda, Dublin, Sunol, Blackhawk, Rossmoor, Diablo

### Cities REMOVED:
- Martinez (94553) - removed April 11, 2026, not target market

### Neighborhoods Targeted (15):
Blackhawk, Crow Canyon, Diablo, Round Hill, Ruby Hill, Castlewood, Happy Valley, Sleepy Hollow, Orinda Downs, Rossmoor, Rudgear Estates, Walnut Heights, Dougherty Valley, Gale Ranch, Canyon Lakes

### Removed Campaigns:
- Custom Home Builder | Google Search (ID: 23691180840) - removed April 11, 2026
- Campaign #1 (Performance Max) - already removed
- Demand Gen - 2026-03-09 - already removed

---

## Meta Ads

### [PX] Home Remodel - Hook 10
- **Status**: ENABLED
- **Campaign ID**: 6969359384893
- **Budget**: $30/day
- **PENDING**: Remove Martinez from targeting

### [PX] Custom Home Design-Build - Hook 3
- **Status**: ENABLED
- **Campaign ID**: 6969359386493
- **Budget**: $30/day
- **PENDING**: Remove Martinez from targeting

---

## Pending Actions
1. Remove Martinez from Meta Ads targeting
2. Disable automatically created assets in Google Ads campaign settings (UI task)
3. Link approved images to ad groups (UI task)
4. Pull search terms report after 3-5 days of new keyword data
5. Review ad group performance to identify which themes drive leads
6. Build Master Playbook for Ridgecrest Marketing Agency

---

## Ridgecrest Marketing Agency (Business)
- Business plan saved: competitors/turnkey_app_business_plan_2026_04_11.md
- Task system initiated: TASK-001.md posted for Claude Code
- Platform: Lovable (frontend) + DigitalOcean (backend/brain) + Supabase (auth/db)
- Revenue model: Hybrid direct-to-user

---

## Rules (on server)
- rules/AGENT_RULES.md - 10 core rules
- rules/data_accuracy_rule.md - Rule 11
- rules/script_delivery_rule.md - Rule 12 (scripts in chat only)
- rules/fact_based_rule.md - Rule 13 (fact-based operations only)
- rules/px_naming_rule.md - Rule 14 ([PX] prefix required)
- rules/claude_code_guardrails.md - Rule 15 (safety guardrails for Claude Code)
