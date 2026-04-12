# Rule 14: [PX] Naming Convention
## Added: April 11, 2026

### Non-Negotiable

Every campaign, ad group, ad set, and ad created by Perplexity MUST include the [PX] prefix in its name.

- Campaigns: [PX] Campaign Name
- Ad Groups: [PX] AG# - Description
- Meta Ad Sets: [PX] Ad Set Name
- Meta Ads: [PX] Ad Name

### Why
Henry manages multiple AI agents. [PX] identifies Perplexity-created assets. Claude uses [RMA]. Never touch anything without your own prefix. This is how we avoid agents interfering with each other's work.

### Enforcement
Before any script that creates a campaign, ad group, ad set, or ad is presented to Henry:
1. Search the script for every name/setName/withName call
2. Verify each one starts with [PX]
3. If any are missing [PX], fix before presenting

This applies to Google Ads, Meta Ads, and any future platform (Microsoft Ads, etc.).
