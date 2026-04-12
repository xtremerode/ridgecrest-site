# Agent Rules — Non-Negotiable

These rules apply to every agent, every script, every action. No exceptions.

---

## Rule 1: Verify Before You Write

Before writing ANY script or code:

1. Fetch the official API reference page for every method you plan to use
2. Confirm the exact method name, arguments, and return type
3. Only then write the code

**Wrong:** Assuming `campaign.setTrackingTemplate()` exists because it sounds right
**Right:** Fetching `https://developers.google.com/google-ads/scripts/docs/reference/adsapp/adsapp_campaignurls` first, confirming the method is `campaign.urls().setTrackingTemplate()`, then writing the code

---

## Rule 2: Never Guess

If you do not know something with certainty, research it first. Do not give Henry information "off the cuff." Every recommendation must be backed by a verified source.

---

## Rule 3: Never Enable Campaigns Without Henry's Approval

Campaigns are always created PAUSED. Nothing goes live until Henry explicitly says so.

---

## Rule 4: No Non-ASCII Characters in Scripts

Google Ads Scripts rejects em dashes, curly quotes, box-drawing characters, and any character with byte value > 127. Use only standard ASCII. Use double quotes throughout.

---

## Rule 5: One main() Function Per Script

Every script must have exactly one `main()` function. When giving Henry a script, always tell him to select all (Ctrl+A) and delete before pasting.

---

## Rule 6: Separate Scripts for Separate Steps

Newly created entities cannot be queried in the same script execution that created them. Always split creation and configuration into separate scripts.

---

## Rule 7: Use Preview First, Then Run

Always instruct Henry to Preview first, review the log, then Run. Never skip preview.

---

## Rule 8: Check the Exact Name Before Using It

Before referencing any account entity by name (campaign name, negative keyword list name, conversion action name), run a discovery script first to get the exact name as it appears in the account.

---

## Rule 9: Update the MD Files

After every session, update `01_build_manual.md` with any new settings, fixes, or lessons learned. The MD files are the source of truth for all agents.

---

## Rule 10: No Partial Work

Do not hand Henry a partial solution and say "we'll fix it later." Every script must be complete, verified, and tested before delivery.
