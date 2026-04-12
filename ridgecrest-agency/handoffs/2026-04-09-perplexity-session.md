# Session Handoff: April 9, 2026
## Agent: Perplexity Computer
## Duration: ~12 hours (10:47 AM - 11:00 PM PDT)

## What Was Accomplished
1. Connected Google Ads via OAuth (Pipedream connector)
2. Discovered Google Ads Scripts as the workaround for campaign creation
3. Built complete campaign "Perplexity Test One" via 7 scripts:
   - Script 1: Campaign + ad group + 45 keywords
   - Script 2: 17 locations + ad schedule + RSA ad
   - Script 3: 4 sitelinks + 6 callouts + 1 structured snippet
   - Script 3b: Call asset (withCallOnly deprecated, removed)
   - Script 4: 8 negative keyword lists linked
   - Script 5: 436 location exclusions
   - Script 6: UTM tracking template
   - Script 7: Enable ad group
4. Added 2 more sitelinks (total 6)
5. Fixed PRESENCE_OR_INTEREST to PRESENCE only
6. Paused old "Custom Home Builder | Google Search" campaign
7. Created 8 agent MD files (build manual, workflow, QA, performance, etc.)
8. Uploaded all files to DigitalOcean server API

## Key Decisions Made by Henry
- Single campaign approach (not multiple) due to low budget
- $100/day budget, Manual CPC $8.00
- Use "and" not "&" in ad copy (triggers PROHIBITED policy)
- No phone numbers in descriptions (triggers PROHIBITED policy)
- Minimum 6 sitelinks for all future campaigns
- UTM params (?sl=1-6) for sitelinks on single-page landing page
- Friday/Saturday/Sunday/Monday historically best days (to revisit after data)

## Known Issues Discovered
- containsEuPoliticalAdvertising requires string enum, not boolean
- withCallOnly() is deprecated
- campaign.setTrackingTemplate() doesn't exist — use campaign.urls().setTrackingTemplate()
- Newly created entities can't be queried in same script execution
- Non-ASCII characters cause SyntaxError in Google Ads Scripts
- 94575 is not a targetable US postal code in Google Ads
- Google Drive connector persistently shows DISCONNECTED in Perplexity

## Server API
- Base URL: http://147.182.242.54:8081/agency
- Token: stored in ~/agent/ridgecrest-agency/API_TOKEN.txt
- All files uploaded to campaigns/ and rules/ folders
