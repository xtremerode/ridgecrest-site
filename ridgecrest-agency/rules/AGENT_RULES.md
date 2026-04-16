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

---

## Rule 11: End-to-End Verification Before Reporting Done

NEVER tell Henry something is done until you complete ALL THREE verification steps:

### Step 1: File on Disk
Confirm the file exists at the expected path and contains the correct content. Read it back, don't assume.

### Step 2: Browser URL Accessible
For ANY file that the browser needs to load (CSS, JS, images, fonts), curl the EXACT URL the browser would use and confirm HTTP 200 with the correct file size. Do not assume a file is accessible because it exists on disk — the server routing may not match the URL.

### Step 3: Rendered Page Shows the Effect
Load the actual page and verify the change is visible. For CSS: confirm the rule appears in the rendered page's stylesheet. For images: confirm the image loads. For JS: confirm the script executes without errors.

### Why This Rule Exists
On April 12, 2026, overrides.css was added with the path /css/overrides.css. The file existed on disk. The link tag was injected into the HTML. But the server serves files under /view/css/, so /css/overrides.css returned 404. The browser could not load any of the CSS fixes. This was reported as done to Henry when nothing was actually working.

### Violation
If you skip any step and Henry discovers the change doesn't work, you have wasted his time and broken trust. Do not test this boundary.

---

## Rule 12: Full Inventory Before Touching Any Files

Before making ANY change that is supposed to apply across multiple pages or files, you MUST enumerate the complete scope first. Never assume you know every file from memory or a partial audit.

### Required Steps Before Starting

1. **List every file in the directory** — run `ls /home/claudeuser/agent/preview/*.html` (or equivalent glob) and read the full output
2. **Grep for the exact class/pattern being changed** — e.g. `grep -l "page-hero" *.html` to find every file containing that pattern
3. **Read the hero/target section of EVERY matched file** — not just the ones you expect. Surprises live in the files you don't think to check.
4. **Confirm the full list with Henry before writing a single line of code** — say "I found X pages that need this change: [list them all]." Wait for confirmation.

### Why This Rule Exists

On April 16, 2026, Henry asked for hero text changes across every page on the site. Claude audited only 4 pages (about, process, portfolio, contact) without listing the directory first. Pages missed: services, team, kitchen-remodels, bathroom-remodels, whole-house-remodels, custom-homes. Henry had to discover the gaps himself after the work was reported as done.

### Scope Confirmation Template

Before starting any multi-file task, say exactly this:

> "I found [N] files that match this change. Full list: [file1, file2, ...]. Confirming before I touch anything — is this the complete scope?"

Do not begin implementation until Henry says yes.

### Violation

If Henry discovers you missed files he asked to be changed, you have wasted a full work session and broken trust. This rule has no exceptions, even when the scope seems obvious.
