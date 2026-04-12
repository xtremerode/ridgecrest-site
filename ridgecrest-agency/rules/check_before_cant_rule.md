# Rule 16: Check Before Saying "Can't"
## Added: April 11, 2026

### Non-Negotiable

NEVER tell Henry you cannot do something without FIRST:

1. Calling list_external_tools to check all available connectors
2. Checking if the DigitalOcean server has the capability
3. Checking if SSH access can accomplish it
4. Searching the web for alternative approaches

The Google Ads Pipedream connector CAN pull live campaign reports, ad group reports, keyword ideas, and custom GAQL queries. Do NOT tell Henry to run Google Ads Scripts for data the connector can retrieve.

This rule exists because Perplexity has repeatedly told Henry "I can't do that" only to discover minutes later that the capability was available the entire time. This wastes Henry's time and erodes trust.

### Before saying "I can't":
1. Check connectors (list_external_tools)
2. Check SSH access to DigitalOcean
3. Check Slack integration
4. Search the web for solutions
5. Only THEN, if truly impossible, explain why with evidence
