# Rule 13: Fact-Based Operations Only
## Added: April 11, 2026

### Non-Negotiable

1. **Never guess.** If you do not have verified data, say so. Do not fill gaps with assumptions.
2. **Every keyword must have a documented source** with a URL before it enters the campaign.
3. **Every negative keyword must have a documented rationale** — either from a published best-practice list (with URL) or from a search term report showing irrelevant clicks.
4. **Every city and neighborhood must be verified** against the actual zip code targeting in the campaign. Pull the geo target IDs from the build manual or from a live campaign audit script. Never list cities from memory.
5. **Before making any campaign change**, read the current campaign state via a Google Ads Script. Do not assume the current state based on prior session notes.
6. **Before presenting research findings**, cite the source name and URL for every data point. If a data point has no source, it does not get presented.
7. **Before adding keywords**, verify they reflect how real people search — not how the brand describes itself. Cross-reference with published search volume data.
8. **All keyword and negative keyword lists must be saved to the server** as MD files with full source documentation before any script is run.
9. **Search term reports must be reviewed weekly.** Any keyword with zero impressions after 14 days gets flagged for removal.
10. **Do not present stale data as current.** If data is from a previous session, flag it with the date and verify before acting on it.

### Reference Files (Always Check Before Acting)
- `competitors/keyword_research_2026_04_11.md` — keyword strategy and sources
- `competitors/ad_schedule_research_2026_04_11.md` — ad schedule research
- `competitors/competitive_intelligence_2026_04_10.md` — competitor data
- `rules/AGENT_RULES.md` — core 10 rules
- `rules/data_accuracy_rule.md` — Rule 11
- `rules/script_delivery_rule.md` — Rule 12 (scripts in chat, not files)
- `rules/fact_based_rule.md` — this file (Rule 13)
- `CAMPAIGN_IDS.md` — all account/campaign IDs
- `agency_mode.txt` — check before campaign changes
