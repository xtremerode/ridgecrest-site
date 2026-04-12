# Ridgecrest Designs — Google Ads Agent System
## Master Overview

---

## Business Context

| Field | Value |
|---|---|
| Business | Ridgecrest Designs |
| Type | High-end custom home design-build |
| Location | Pleasanton, CA |
| Website | https://go.ridgecrestdesigns.com |
| Phone | (925) 784-2798 |
| Google Ads Account | 557-607-7690 |
| Manager Account | Ridgecrest Marketing (447-894-4999) |
| Primary Conversion | "Project inquiry submitted" |
| Weekly Budget | $700 ($100/day) |
| Minimum Project Size | $200,000 |
| Sales Cycle | Long (weeks to months) |
| Volume Profile | Low volume, very high dollar value |

---

## System Architecture

```
+----------------------------------------------------------+
|          RIDGECREST DESIGNS GOOGLE ADS AGENT SYSTEM      |
+----------------------------------------------------------+
|                                                          |
|   [00_README.md]  <-- You are here (master overview)    |
|                                                          |
|   +------------------+   +------------------+           |
|   | 02_campaign_     |   | 03_assets_       |           |
|   | build_agent.md   |   | agent.md         |           |
|   |                  |   |                  |           |
|   | Runs: Script 1   |   | Runs: Script 3   |           |
|   | (Campaign/KWs)   |   | (Sitelinks,      |           |
|   | Then: Script 2   |   |  Callouts,       |           |
|   | (Locations/Ad)   |   |  Snippets, Call) |           |
|   +--------+---------+   +--------+---------+           |
|            |                      |                     |
|            v                      v                     |
|   +------------------+   +------------------+           |
|   | 04_qa_agent.md   |   | 05_performance_  |           |
|   |                  |   | agent.md         |           |
|   | Runs: GAQL       |   |                  |           |
|   | verification     |   | Runs: Weekly     |           |
|   | queries          |   | performance      |           |
|   |                  |   | review           |           |
|   +------------------+   +------------------+           |
|                                                          |
|   [01_build_manual.md] = Ground truth for all settings  |
|   All agents reference this file for campaign specs.    |
|                                                          |
+----------------------------------------------------------+
```

### Data Flow

```
01_build_manual.md (canonical settings)
        |
        +---> Campaign Build Agent (Script 1 -> Script 2)
        |             |
        |             v
        |       Campaign exists in Google Ads
        |             |
        +---> Assets Agent (Script 3)
        |             |
        |             v
        |       All assets attached to campaign
        |             |
        +---> QA Agent (GAQL verification)
        |             |
        |             v
        |       QA report: pass / fail / delta
        |
        +---> Performance Agent (weekly cadence)
                      |
                      v
                Weekly report + recommendations -> Henry
```

---

## Agent Roles and Responsibilities

### 01_build_manual.md — Canonical Settings Document
Not an agent — this is the **ground truth reference** for all campaign settings, keywords, ad copy, geo targets, and known issues. All agents read from this before taking any action. When settings change, update this file first.

### Campaign Build Agent (02_campaign_build_agent.md)
**Responsibility:** Build the full campaign structure from scratch.
- Runs Script 1: creates campaign, ad group, and all 45 keywords
- Runs Script 2: adds geo targets, ad schedule, negative keywords, and RSA ad
- Uses only settings from `01_build_manual.md`
- Does NOT add assets (that is the Assets Agent's job)

### Assets Agent (03_assets_agent.md)
**Responsibility:** Add all required campaign assets after the campaign structure exists.
- Runs Script 3: adds sitelinks, callouts, structured snippets, and call asset
- Requires the campaign to already exist (Campaign Build Agent must have run first)
- Verifies assets are attached before signing off

### QA Agent (04_qa_agent.md)
**Responsibility:** Audit the live campaign against the build manual spec.
- Runs GAQL verification queries via Google Ads Scripts
- Checks every setting: budget, bidding, locations, schedule, keywords, ad, assets
- Produces a structured pass/fail report
- Should run after Campaign Build Agent AND after Assets Agent
- Can also run on a scheduled basis to detect drift

### Performance Agent (05_performance_agent.md)
**Responsibility:** Weekly performance review and optimization recommendations.
- Pulls impression share, CPC, click, and conversion data
- Flags issues for Henry's review vs. handles autonomously
- Manages negative keyword expansion from search term reports
- Does NOT make bid or budget changes without Henry's approval

---

## Order of Operations

### Initial Campaign Setup (one-time)

```
Step 1: Read 01_build_manual.md — confirm all settings are correct
Step 2: Campaign Build Agent — run Script 1, verify, then run Script 2
Step 3: Assets Agent — run Script 3
Step 4: QA Agent — run full audit, confirm everything matches spec
Step 5: Present QA report to Henry for review
Step 6: Henry approves -> campaign set to ENABLED (never done by an agent)
```

### Weekly Recurring (ongoing)

```
Every Monday:
  - Performance Agent reviews prior week data
  - Produces weekly report
  - Flags escalations for Henry
  - Executes approved optimizations (negatives, minor bid adjustments)

Monthly:
  - QA Agent runs full audit to detect settings drift
  - Performance Agent reviews month-over-month trends
```

---

## How to Invoke Each Agent

### Campaign Build Agent
1. Open Google Ads account **557-607-7690**
2. Navigate to **Tools > Scripts**
3. Create a new script, paste **Script 1** from `02_campaign_build_agent.md`
4. Click **Preview** first to review, then click **Run** to execute
5. Wait for Script 1 to complete and confirm campaign ID appears in logs
6. Create a second script, paste **Script 2** from `02_campaign_build_agent.md`
7. Click **Preview**, then **Run**

### Assets Agent
1. After Campaign Build Agent completes, open **Tools > Scripts**
2. Create a new script, paste **Script 3** from `03_assets_agent.md`
3. Click **Preview**, then **Run**
4. Confirm all 4 asset types appear in campaign's asset report

### QA Agent
1. Open **Tools > Scripts**
2. Create a new script, paste the QA verification script from `04_qa_agent.md`
3. Click **Preview** to run in read-only mode (safe to run anytime)
4. Review the log output for pass/fail items

### Performance Agent
1. Open **Tools > Scripts**
2. Create a new script or schedule the performance script from `05_performance_agent.md`
3. Schedule for weekly execution (Monday morning)
4. Review log output or email report

---

## Universal Rules (Apply to ALL Agents)

These rules are non-negotiable and apply to every agent in this system:

1. **Never enable campaigns without Henry's explicit approval.** All scripts leave campaigns in PAUSED status. Enabling is a manual action performed by Henry only.

2. **Never guess — always research first.** If a setting, API method, or ID is uncertain, verify it against the build manual or official Google Ads API documentation before using it. Do not assume syntax is correct.

3. **Always verify before acting.** Before running any mutating script (Scripts 1, 2, 3), run in Preview mode first. Review the log output. Only proceed to Run after confirming the preview looks correct.

4. **Never use temporary resource names across scripts.** Temporary resource names (-1, -2, -3) assigned during a mutateAll call do not persist. Never reference them in a subsequent script run — always query for real IDs.

5. **ASCII only in scripts.** Non-ASCII characters (em dashes, curly quotes, box-drawing characters) cause SyntaxError in Google Ads Scripts. Use only standard ASCII in all script files.

6. **Double quotes only in scripts.** Mixed quote types cause SyntaxError. Use double quotes throughout all JavaScript strings.

7. **Reference 01_build_manual.md for all settings.** Never hard-code settings from memory. Always read from the build manual to ensure accuracy.

8. **Log everything.** Every script must use Logger.log() to record what it does, what IDs are created, and what errors occur. This is the only audit trail.

9. **Never run in production without Preview first.** Google Ads Scripts run in Preview by default — this is intentional and must not be bypassed on first run.

10. **Document errors.** If a script encounters an error not in the Known Issues Log in `01_build_manual.md`, add it before retrying.
