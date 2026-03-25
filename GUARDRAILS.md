# Agent Guardrails — Ridgecrest Designs
**Status: ACTIVE — These rules are hard constraints. No exceptions without explicit human approval.**

These rules govern all automated actions taken by the bid/budget optimizer, creative agent, performance analyst, and any other agent operating on this account. When a rule conflicts with an optimization opportunity, the rule wins. When a situation is ambiguous, escalate rather than act.

---

## 1. Spend Limits

| Rule | Limit | Action if violated |
|---|---|---|
| Weekly budget ceiling — all platforms combined | **$1,000 / week maximum** | Hard block all spend increases. Log and alert. |
| Weekly budget floor — target minimum | **$500 / week** | Alert if pacing below $400. Investigate underspend. |
| Daily soft cap — all campaigns combined | **$250 / day** | Block budget increases for the day. Reallocations still allowed. |
| Single campaign budget increase per cycle | **+20% maximum** | Cap the increase at 20%. Log the cap. |
| Budget reallocation per cycle | **30% of source campaign's budget** | Cap at 30%. Never reduce below $10/day floor. |
| Minimum daily budget per campaign | **$10.00** | Never reduce any campaign below this floor. |

**Hard rules:**
- Never allow total weekly spend to exceed $1,000 under any circumstance.
- The $1,000 weekly ceiling is tracked Mon–Sun calendar week across all platforms combined.
- Never cut a top-performing campaign's budget (score ≥ 60) — only shift from under-performers.
- Never reduce any campaign below $10/day regardless of performance.
- Budget increases are blocked once daily soft cap of $250 is reached — reallocations still permitted.
- Do not run campaigns on Tuesday, Wednesday, or Thursday. Active days are Friday, Saturday, Sunday, and Monday only.

---

## 2. Keyword Rules

| Rule | Limit | Action if violated |
|---|---|---|
| Keyword pauses per campaign per day | **3 maximum** | Queue remaining pauses for the next day. |
| Keyword bid increase per optimization cycle | **+25% maximum** | Cap the increase. Log the cap. |
| Keyword bid decrease per optimization cycle | **−30% maximum** | Cap the decrease. Log the cap. |
| Minimum active keywords per campaign | **5 at all times** | Block any pause that would drop below 5. |

**Hard rules:**
- Never pause a keyword if doing so would leave the campaign with fewer than 5 active keywords. Block the pause and log the reason.
- Never apply more than 3 keyword pauses to the same campaign in a single calendar day, regardless of performance data.
- Bid changes must be applied one keyword at a time. Never batch-update all keywords simultaneously.
- Never remove a keyword permanently. Pausing is the only automated action. Deletion requires human approval.

---

## 3. Campaign Rules

| Rule | Condition | Action |
|---|---|---|
| Pause a campaign | Requires 3 consecutive days of underperformance | Block if trend is fewer than 3 days. Escalate. |
| Create a new campaign | **Always** | Block. Require explicit human approval. |
| Change campaign objective | **Always** | Block. Require explicit human approval. |
| Change keyword match types | **Always** | Block. Require explicit human approval. |

**Hard rules:**
- Never pause an entire campaign based on a single day of data. A campaign must show underperformance on 3 consecutive days before a pause is eligible for automated action — and even then, escalate to a human before executing.
- Never create a new campaign automatically. All new campaign creation must be explicitly approved by a human and initiated manually.
- Never change a campaign's objective (e.g., from Conversions to Clicks) automatically. This is a permanent human decision.
- Never switch keyword match types (Exact → Phrase, Phrase → Broad, etc.) automatically. Match type strategy is set by a human.
- Never delete a campaign. Pausing is the maximum automated action.

---

## 4. Creative Rules

| Rule | Limit | Action if violated |
|---|---|---|
| Publish ad copy without database storage | Never | Block publish. Store first, then publish. |
| Competitor brand names in ad copy | Never | Flag and reject the creative brief. |
| Headline character limit | **30 characters maximum** | Reject and regenerate. Do not trim silently. |
| Description character limit | **90 characters maximum** | Reject and regenerate. Do not trim silently. |

**Hard rules:**
- Every creative brief — including all headlines, descriptions, callouts, and sitelinks — must be written to the `creative_briefs` table in the database before any publish or upload action is attempted.
- Never use competitor brand names (e.g., other design-build firms, contractors, or remodeling companies operating in the service area) in any ad copy, headline, description, or extension.
- Keyword insertion placeholders (`{KeyWord:Default Text}`) count by the length of the default text only, not the full placeholder string. Validate accordingly.
- Ad copy must reflect Ridgecrest Designs' premium positioning. Do not use price-competitive language ("cheapest," "affordable," "low cost," "discount") in any ad copy.
- Callout extensions: 25 characters maximum. Sitelink titles: 25 characters maximum. Sitelink description lines: 35 characters maximum.

---

## 5. Reporting Rules

| Rule | Trigger | Required Action |
|---|---|---|
| Log every automated action | Every action | Write to `optimization_actions` table with timestamp, action type, entity, before/after values, and reason. |
| Flag high-spend decisions | Any action spending **> $50 in a single decision** | Log with `flagged = true`. Include in next report. |
| Alert on underspend | Daily spend < **70% of $125.00** ($87.50) | Log alert. Include in daily report. Investigate cause. |

**Hard rules:**
- No automated action is considered complete until it has been logged to the database. If the database write fails, roll back the action.
- Every log entry must include: timestamp (UTC), agent name, action type, affected entity (campaign/keyword/ad), previous value, new value, reason for action, and whether it was flagged.
- Any single decision that allocates or moves more than $50 must be flagged in the database and surfaced in the daily performance report.
- If daily spend falls below $87.50 (70% of the $125 cap), log an underspend alert and investigate whether campaigns are limited by budget, quality score, bid floors, or scheduling errors.
- The daily performance report must be generated every active campaign day and stored in the `reports` table. Do not skip report generation even if no optimization actions were taken.

---

## 6. Human Escalation Triggers

**When any of the following conditions are detected, the agent must:**
1. Immediately pause all automated optimization actions for the account.
2. Log the trigger condition to the database with full context.
3. Send an alert to **henry@ridgecrestdesigns.com**.
4. Do not resume automated actions until a human explicitly re-enables them.

| Trigger | Threshold | Severity |
|---|---|---|
| Cost per lead (CPL) | **Exceeds $1,000** | 🔴 Critical |
| Weekly spend | **Exceeds $1,100** (ceiling + 10% buffer) | 🔴 Critical |
| Daily spend | **Exceeds $300.00** (soft cap + 20% buffer) | 🔴 Critical |
| Single keyword spend with zero conversions | **≥ $75.00 with 0 conversions** | 🔴 Critical |
| API connection failure | **Failure lasting > 2 hours** (Google Ads, Meta, or Microsoft Ads) | 🔴 Critical |

**Alert format — minimum required fields:**
```
TO: henry@ridgecrestdesigns.com
SUBJECT: [ALERT] Ridgecrest Designs — {trigger_name} — {date}

Trigger:    {condition that fired}
Value:      {actual value} vs. {threshold}
Account:    Ridgecrest Designs
Time (UTC): {timestamp}
Action:     All automated optimization paused pending review.

Details:
{full context — campaign name, keyword, spend amount, CPL, etc.}
```

**Additional escalation notes:**
- A CPL above $1,000 on any single keyword or campaign is a data quality or targeting emergency, not a routine optimization event. Do not attempt to fix it automatically.
- A daily spend above $150 means the $125 cap has failed. This is a system error requiring immediate investigation.
- A keyword spending $75 or more with zero conversions has likely escaped the standard optimizer thresholds and must be reviewed by a human before any further spend is allowed.
- API failures longer than 2 hours mean the agent is operating blind. Do not make optimization decisions based on stale data. Pause and wait.

---

## Enforcement Summary

| Category | Automated Block | Requires Human | Escalate Immediately |
|---|---|---|---|
| Weekly spend over $1,000 | ✅ (block increases) | | |
| Weekly spend over $1,100 | ✅ (pause all) | | ✅ |
| Daily spend over $250 | ✅ (block increases) | | |
| Daily spend over $300 | ✅ (pause all) | | ✅ |
| Budget increase > 20% | ✅ (cap at 20%) | | |
| Reallocation > 30% of source | ✅ (cap at 30%) | | |
| Campaign reduced below $10/day | ✅ (block) | | |
| Keyword pauses > 3/day/campaign | ✅ (queue remainder) | | |
| Bid increase > 25% | ✅ (cap at 25%) | | |
| Bid decrease > 30% | ✅ (cap at 30%) | | |
| Active keywords < 5 | ✅ (block pause) | | |
| Campaign pause < 3-day trend | ✅ (block) | ✅ | |
| New campaign creation | ✅ (block) | ✅ | |
| Campaign objective change | ✅ (block) | ✅ | |
| Match type change | ✅ (block) | ✅ | |
| Ad copy not in database | ✅ (block publish) | | |
| Competitor brand in copy | ✅ (reject brief) | | |
| CPL > $1,000 | ✅ (pause all) | | ✅ |
| Daily spend > $150 | ✅ (pause all) | | ✅ |
| Keyword ≥ $75, 0 conversions | ✅ (pause all) | | ✅ |
| API failure > 2 hours | ✅ (pause all) | | ✅ |

---

*Last updated: 2026-03-20 | Account: Ridgecrest Designs | Contact: henry@ridgecrestdesigns.com*
