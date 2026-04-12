## Rule 11: Data Accuracy and Timestamps

Every data point presented to Henry must include:
- The exact source (API, screenshot, Google Ads Scripts, Meta API)
- The exact time it was retrieved
- A flag if the data is more than 1 hour old

Never present stale data as current. If the API returns cached/delayed data, state that clearly. When real-time accuracy is required, use Google Ads Scripts (for Google) or the Meta Marketing API directly (for Meta) instead of connector reporting APIs.

Never mix data from different sources without labeling each one.
