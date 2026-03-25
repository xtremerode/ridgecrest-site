# Ridgecrest Designs — Marketing Automation System Report
**Generated:** 2026-03-24
**Account:** Ridgecrest Designs | Meta act_58393749 | Pleasanton, CA

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Infrastructure](#2-infrastructure)
3. [Database — PostgreSQL](#3-database--postgresql)
4. [Agent Architecture](#4-agent-architecture)
5. [Agent Health — Live Status](#5-agent-health--live-status)
6. [Platform Integrations](#6-platform-integrations)
7. [Guardrails & Safety System](#7-guardrails--safety-system)
8. [Command Center & Chat Interface](#8-command-center--chat-interface)
9. [Scheduling & Automation](#9-scheduling--automation)
10. [Meta Campaigns — Current State](#10-meta-campaigns--current-state)
11. [Google Ads — Current State](#11-google-ads--current-state)
12. [Microsoft Ads — Current State](#12-microsoft-ads--current-state)
13. [Conversion Tracking](#13-conversion-tracking)
14. [Budget Rules & Spend Strategy](#14-budget-rules--spend-strategy)
15. [Key Configuration Values](#15-key-configuration-values)
16. [File Inventory](#16-file-inventory)
17. [Pending Items](#17-pending-items)

---

## 1. System Overview

Ridgecrest Designs operates a fully autonomous multi-platform ad management system running on a DigitalOcean server. The system manages Google Ads, Meta (Facebook/Instagram), and Microsoft Ads campaigns for a premium design-build firm targeting affluent East Bay homeowners.

The system runs 24/7 as a background daemon managed by systemd. It executes a full marketing pipeline every day at 8:00 AM, syncs data to a Supabase-powered Lovable frontend (the Command Center) every 5 minutes, polls for campaign commands every 30 seconds, responds to Command Center chat messages every 5 seconds, and runs health checks every 30 minutes.

**Platform:** Ubuntu Linux on DigitalOcean
**Language:** Python 3.12
**Database:** PostgreSQL 14 (localhost:5432, database: `marketing_agent`)
**Frontend:** Lovable (ridgecrest-command-center.lovable.app)
**Frontend database:** Supabase (itoinsaotwsmidbosqbq)
**Process manager:** systemd (`ridgecrest-orchestrator.service`)
**AI model:** Claude Opus 4.6 (claude-opus-4-6) — used by creative agent, reporting agent, and chat agent

---

## 2. Infrastructure

### Server
- **Provider:** DigitalOcean Ubuntu droplet
- **Working directory:** `/root/agent/`
- **Python virtual environment:** `/root/agent/venv/`
- **Log file:** `/root/agent/orchestrator.log`

### Systemd Service
**File:** `/etc/systemd/system/ridgecrest-orchestrator.service`

```ini
[Unit]
Description=Ridgecrest Designs Marketing Orchestrator
After=network.target postgresql.service
Wants=postgresql.service

[Service]
WorkingDirectory=/root/agent
ExecStart=/root/agent/venv/bin/python orchestrator.py --daemon
Restart=always
RestartSec=30
StandardOutput=append:/root/agent/orchestrator.log
StandardError=append:/root/agent/orchestrator.log

[Install]
WantedBy=multi-user.target
```

**Enabled on boot:** Yes
**Auto-restart on crash:** Yes (30-second delay)

**Service management commands:**
```bash
systemctl status ridgecrest-orchestrator    # check status
systemctl restart ridgecrest-orchestrator   # restart
systemctl stop ridgecrest-orchestrator      # stop
tail -f /root/agent/orchestrator.log        # live logs
```

### Environment Variables (`.env`)
| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API — used by creative, reporting, and chat agents |
| `META_ACCESS_TOKEN` | Meta Marketing API long-lived access token |
| `META_APP_ID` | Meta app ID (26025194863773698) |
| `META_APP_SECRET` | Meta app secret |
| `META_AD_ACCOUNT_ID` | `act_58393749` |
| `INGEST_API_KEY` | `RCM-2026-xK9mP3vL8nQ5wJ2hY7tF4dA6sE1uB0cD` — authenticates all Supabase edge function calls |
| `SUPABASE_INGEST_ENDPOINT` | Edge function URL for DB→Supabase sync |
| `DATABASE_URL` | PostgreSQL connection string |
| `RESEND_API_KEY` | Email alerts (escalation triggers) |
| `META_MANAGER_AUTO_APPLY` | `true`/`false` — whether optimizer applies changes immediately |
| `MICROSOFT_CLIENT_ID` | Microsoft Ads OAuth client |
| `MICROSOFT_CLIENT_SECRET` | Microsoft Ads OAuth secret |
| `MICROSOFT_TENANT_ID` | Microsoft Ads tenant |
| `MICROSOFT_REFRESH_TOKEN` | Microsoft Ads refresh token |
| `MICROSOFT_ADS_DEVELOPER_TOKEN` | Microsoft Ads developer token |
| `MICROSOFT_ADS_ACCOUNT_ID` | 187004108 |

---

## 3. Database — PostgreSQL

**Database name:** `marketing_agent`
**Host:** localhost:5432
**User:** agent_user

### Live Row Counts (as of 2026-03-24)
| Table | Rows | Purpose |
|---|---|---|
| `campaigns` | 92 active | All campaigns across all platforms |
| `performance_metrics` | 257 | Daily metrics — Google, Meta, Microsoft |
| `optimization_actions` | 224 | Full audit log of every automated action |
| `reports` | 32 | AI-generated daily/weekly performance reports |
| `creative_briefs` | 6 | Claude-generated ad copy |
| `ad_groups` | varies | Ad groups nested under campaigns |
| `keywords` | varies | Active and paused keywords |
| `negative_keywords` | 21 seeded | Account-level negative keyword list |
| `agent_heartbeats` | 14 agents | Health and run status per agent |
| `agent_messages` | varies | Inter-agent message bus and alerts |
| `budget_snapshots` | varies | Daily budget pacing |
| `geo_performance` | 0 | Geographic breakdown (populated when synced) |
| `search_terms` | 0 | Raw search term report |
| `guardrail_violations` | 0 | Guardrail violation log |

### Schema Notes
- `campaigns.google_campaign_id` is the universal external ID across all platforms — Meta campaigns use prefix `meta_<id>`, Microsoft uses `msft_<id>`
- `performance_metrics.platform` distinguishes google_ads / meta / microsoft_ads rows
- `cost_usd` is a generated column (`cost_micros / 1,000,000`) — never written directly
- Every optimization action is logged to `optimization_actions` before being applied
- `agent_heartbeats` uses `UNIQUE(agent_name)` — one row per agent, upserted on each run

### Seeded Negative Keywords (account-level)
cheap, affordable, low cost, discount, free, diy, how to, rent, apartment, condo, handyman, repair, fix, template, jobs, hiring, salary, school, course, software, app

---

## 4. Agent Architecture

All agents are Python modules imported and orchestrated by `orchestrator.py`. There are no separate processes — the orchestrator is the single daemon that runs everything on schedule.

---

### `orchestrator.py` — Central Controller
The single entry point. Runs the full pipeline daily at 8:00 AM and manages all background polling schedules.

**Pipeline sequence (8:00 AM daily):**
1. Guardrails check — abort if escalation triggers are active
2. Sync: pull from Google Ads, Meta, Microsoft APIs
3. Bid & budget optimization — filter through guardrails, apply allowed actions
4. Creative refresh — generate new ad copy (active days only)
5. Performance reporting — daily report written to `reports` table
6. Supabase sync — push DB snapshot to the Command Center

**Background schedules:**
- Every 5 seconds: chat agent (Command Center AI chat)
- Every 30 seconds: command executor (campaign pause/enable from Command Center)
- Every 5 minutes: Supabase sync (Command Center data refresh)
- Every 5 minutes: inter-agent message processing
- Every 30 minutes: health checks
- Every hour: system status log

**Flags:**
- `--daemon` — run as continuous daemon (used by systemd)
- `--force` — run pipeline regardless of day of week
- `--status` — print system status and exit
- `--phase` — run a single pipeline phase only

---

### `chat_agent.py` — Command Center AI Chat *(new 2026-03-23)*
Bridges the Lovable Command Center chat UI with the marketing automation system. Polls Supabase for pending user messages, processes them with Claude Opus 4.6 (adaptive thinking + tool use), and writes assistant responses back.

**Model:** claude-opus-4-6 with `thinking: {type: "adaptive"}`
**Poll interval:** Every 5 seconds (via orchestrator schedule)
**Max tool turns per message:** 10

**Tools available to Claude in chat:**
| Tool | What it does |
|---|---|
| `get_active_campaigns` | List all campaigns, status, and daily budgets |
| `get_campaign_status` | 7-day performance metrics per platform (spend, CPL, conversions) |
| `get_today_metrics` | Live today spend/conversions pulled directly from Meta API |
| `get_budget_status` | Daily and weekly spend vs guardrail caps |
| `get_reports` | Most recent AI-generated performance reports |
| `run_meta_sync` | Pull latest Meta data into local DB |
| `run_optimizer` | Run bid/budget optimizer |
| `run_creative_agent` | Generate new ad copy briefs |
| `pause_campaign` | Pause a specific campaign by name and platform |
| `enable_campaign` | Enable/resume a specific campaign |

**Conversation flow:**
1. Lovable frontend writes user message to Supabase `chat_messages` table (`role=user`, `status=pending`)
2. `chat_agent.py` picks it up, marks it `processing`
3. Loads full conversation history for the `session_id`
4. Calls Claude with tools and full agency context in system prompt
5. Executes tool calls, feeds results back to Claude
6. Writes final text response to Supabase (`role=assistant`, `status=done`)
7. Frontend receives it via Supabase Realtime subscription

---

### `meta_sync.py` — Meta Data Sync
Pulls 30 days of campaign and ad set performance from Meta Marketing API v21.0 and writes to `performance_metrics` and `campaigns` tables.

Tracks: spend, impressions, clicks, conversions (`offsite_conversion.custom.*`), landing page views, CPL. Runs as part of the daily pipeline and can be triggered manually via the chat agent.

---

### `meta_manager.py` — Meta Optimizer
Reads Meta performance from DB and applies CPL-based rules:
- Pause ad sets: 7-day spend > $50 with 0 conversions
- Budget +25%: CPL $150–$300 and spend > $20
- Budget −20%: CPL > $500
- Pause campaign: 7-day spend > $200 with 0 conversions
- Flag for review: CPL < $100 (lead quality risk)

Enforces active days (Fri/Sat/Sun/Mon) by pausing/resuming campaigns on each run. Controlled by `META_MANAGER_AUTO_APPLY` env var.

---

### `google_sync.py` — Google Ads Data Sync
Pulls campaign, ad group, keyword, and performance data from Google Ads API. Currently in limited access mode pending developer token production approval — logs errors on each run, does not affect other agents.

---

### `google_ads_builder.py` — Google Ads Campaign Builder
Creates campaigns, ad groups, keywords, and ads via Google Ads API. Full keyword structure from CLAUDE.md §17 is staged. Uses exact match and phrase match only. Will activate on developer token approval.

---

### `google_ads_scheduler.py` — Google Ads Day Scheduling
Applies AdSchedule criteria to campaigns — suppresses Tue/Wed/Thu. Currently errors due to developer token status.

---

### `microsoft_sync.py` — Microsoft Ads Data Sync
Pulls performance data from Microsoft Ads API and writes to `performance_metrics` with `platform='microsoft_ads'`.

---

### `microsoft_manager.py` — Microsoft Ads Optimizer
Applies the same CPL-based optimization rules as meta_manager. Manages Tue/Wed/Thu suppression via DayTimeCriterion −100% bid adjustments.

---

### `msft_apply_day_schedule.py` — Microsoft Day Schedule (one-time)
Applied −100% bid adjustments for Tue/Wed/Thu at campaign level.

---

### `msft_apply_geo_targeting.py` — Microsoft Geo Targeting (one-time)
Applied approved zip code targeting to Microsoft campaigns.

---

### `performance_analyst.py` — Performance Analysis
Detects anomalies and underperformance across all platforms. Produces critical alerts for escalation triggers. Feeds data to the bid/budget optimizer and reporting agent.

---

### `bid_budget_optimizer.py` — Bid & Budget Optimizer
- Reads proposed actions from performance_analyst
- Filters all actions through guardrails before applying
- Executes allowed bid changes, budget reallocations, and pauses
- Every action logged to `optimization_actions` before and after execution
- 224 actions logged to date

---

### `creative_agent.py` — Creative Agent
Uses Claude API to generate ad copy. All briefs written to `creative_briefs` before any publish attempt. Enforces 30-char headline limit, 90-char description limit, no competitor names, no price-competitive language.

---

### `reporting_agent.py` — Reporting Agent
Uses Claude API to generate structured Markdown performance reports. Produces daily summaries, weekly trend analysis, budget compliance checks, and optimization action logs. Stores to `reports` table. 32 reports generated to date.

---

### `recommendation_agent.py` — Recommendation Agent
Generates strategic recommendations from performance data and writes them to Supabase for display and approval in the Command Center.

---

### `health_agent.py` — Health Agent
Runs end-to-end health checks across the full agency stack every 30 minutes. Writes results to Supabase via the `save-health-check` edge function.

---

### `guardrails.py` — Guardrails Engine
Loaded and checked at the start of every pipeline run.
- `assert_guardrails_present()` — aborts pipeline if `GUARDRAILS.md` is missing
- `check_pipeline_state()` — checks DB for active escalation triggers
- `filter_actions()` — filters proposed optimization actions against all rules
- If any escalation trigger is active, Phases 2 and 3 are halted and alert email sent

---

### `supabase_sync.py` — Supabase / Command Center Sync
Pushes local PostgreSQL snapshot to Supabase every 5 minutes so the Command Center dashboard stays current. Tables synced: campaigns, ad_groups, ads, performance_metrics, reports, agent_messages, optimization_actions, agent_heartbeats, budget_snapshots.

---

### `command_executor.py` — Command Executor
Polls Supabase `command_queue` every 30 seconds. Executes campaign control commands sent from the Command Center: `pause_campaign`, `enable_campaign`, `pause_all`, `enable_all`. Also processes approved recommendations. Marks commands `completed` or `failed`.

---

### `db.py` — Database Utilities (shared)
Shared by all agents:
- `get_db()` — context manager for all DB operations (auto-commit/rollback)
- `send_message()` / `receive_messages()` / `ack_message()` — inter-agent message bus
- `heartbeat()` — upsert agent health status
- `log_action()` / `mark_action_applied()` — optimization action audit log

---

## 5. Agent Health — Live Status

As of 2026-03-23 23:59 UTC:

| Agent | Status | Runs | Errors | Notes |
|---|---|---|---|---|
| orchestrator | success | 53 | 0 | Healthy |
| meta_sync | success | 28 | 0 | Healthy |
| meta_manager | success | 18 | 0 | Healthy |
| microsoft_sync | success | 25 | 0 | Healthy |
| microsoft_manager | success | 46 | 1 | Healthy (1 historical error) |
| bid_budget_optimizer | alive | 17 | 0 | Healthy |
| creative_agent | alive | 9 | 0 | Healthy |
| performance_analyst | alive | 23 | 0 | Healthy |
| reporting_agent | alive | 33 | 0 | Healthy |
| recommendation_agent | alive | 6 | 0 | Healthy |
| health_agent | error | 14 | 0 | Status label anomaly — runs completing |
| google_sync | error | 24 | 12 | Expected — developer token pending |
| google_ads_scheduler | error | 8 | 4 | Expected — developer token pending |
| chat_agent | new | — | — | Added 2026-03-23, polling active |

**Note on google_sync / google_ads_scheduler errors:** These are expected and normal. Both agents require a production-approved Google Ads developer token which is pending. All other agents are unaffected.

---

## 6. Platform Integrations

### Meta (Facebook/Instagram)
| Item | Value |
|---|---|
| Ad Account | act_58393749 |
| API Version | v21.0 |
| Pixel ID | 534314263109913 (installed on Base44 app) |
| Saved Audience ID | 6934900931693 |
| Advantage+ Audience | ALWAYS 0 (hard constraint on all new ad sets) |
| Day enforcement | Campaigns paused Tue/Wed/Thu, resumed Fri/Sat/Sun/Mon |

### Google Ads
| Item | Value |
|---|---|
| Developer token | Applied — awaiting production approval |
| Campaign type | Search only (Phase 1) |
| Structure | All campaigns staged and ready in DB |
| Day enforcement | AdSchedule criteria — staged, applies on token approval |
| Geo | Zip code + city targeting for approved service areas |
| Match types | Exact and phrase only (no broad match at launch) |

### Microsoft Ads
| Item | Value |
|---|---|
| Account ID | 187004108 |
| Day enforcement | DayTimeCriterion −100% bid adjustment Tue/Wed/Thu (applied) |
| Geo | Zip code targeting matching approved service area (applied) |
| Structure | Mirrors Google Ads campaign structure |
| Status | Active but subordinate — expands after Google proven |

---

## 7. Guardrails & Safety System

All rules defined in `GUARDRAILS.md` and enforced by `guardrails.py`. Pipeline aborts if the rules file is missing.

### Spend Limits
| Rule | Limit |
|---|---|
| Weekly ceiling (all platforms) | $1,000 hard maximum |
| Weekly floor (target) | $500 — alert if pacing below $400 |
| Daily soft cap | $250 — blocks new budget increases |
| Max budget increase per cycle | +20% |
| Max reallocation from source campaign | 30% of source budget |
| Minimum budget per campaign | $10/day floor |

### Keyword Rules
| Rule | Limit |
|---|---|
| Keyword pauses per campaign per day | 3 maximum |
| Bid increase per cycle | +25% maximum |
| Bid decrease per cycle | −30% maximum |
| Minimum active keywords per campaign | 5 at all times |

### Campaign Rules
- Never pause a campaign based on fewer than 3 consecutive days of underperformance
- Never create a new campaign automatically — requires human approval
- Never change campaign objectives automatically
- Never change keyword match types automatically
- Never delete a campaign (pause only)

### Creative Rules
- Every brief must be written to DB before any publish attempt
- No competitor brand names in any ad copy
- Headlines: 30 characters maximum
- Descriptions: 90 characters maximum
- No price-competitive language ("cheap", "affordable", "discount")

### Human Escalation Triggers
When any of these fire: all automated optimization pauses + email alert to henry@ridgecrestdesigns.com

| Trigger | Threshold |
|---|---|
| CPL | Exceeds $1,000 |
| Weekly spend | Exceeds $1,100 |
| Daily spend | Exceeds $300 |
| Single keyword spend with 0 conversions | ≥ $75 |
| API connection failure | > 2 hours |

---

## 8. Command Center & Chat Interface

### Command Center Dashboard
**URL:** https://ridgecrest-command-center.lovable.app
**Built with:** Lovable (React/TypeScript frontend)
**Database:** Supabase (project: itoinsaotwsmidbosqbq)

### Data Flow — Dashboard
```
Meta / Google / Microsoft APIs
          ↓
    *_sync.py agents
          ↓
  PostgreSQL (local DB)
          ↓
  supabase_sync.py (every 5 min)
          ↓
       Supabase
          ↓
  Lovable Command Center
```

### Command Flow — Campaign Controls
```
Lovable Command Center (button click)
          ↓
  execute-command edge function
          ↓
  command_queue (Supabase table)
          ↓
  command_executor.py (polls every 30s)
          ↓
  Platform API (Meta / Google / Microsoft)
```

### Chat Interface — Architecture *(new 2026-03-23)*
```
Lovable Command Center (chat input)
          ↓
  chat-messages edge function (post_message)
          ↓
  chat_messages table (Supabase, role=user, status=pending)
          ↓
  chat_agent.py (polls every 5s)
          ↓
  Claude Opus 4.6 with tools
          ↓
  Tool execution (DB queries, Meta API, agent runs)
          ↓
  chat-messages edge function (post_response)
          ↓
  chat_messages table (role=assistant, status=done)
          ↓
  Supabase Realtime subscription
          ↓
  Lovable Command Center (response displayed)
```

### Supabase Tables (in Supabase, not local PostgreSQL)
| Table | Purpose |
|---|---|
| `command_queue` | Campaign commands from Command Center |
| `recommendations` | Optimization recommendations for human approval |
| `system_health` | Agent health check results |
| `chat_messages` | Command Center AI chat conversations *(new)* |

### Supabase Edge Functions
| Function | Purpose |
|---|---|
| `ingest-metrics` | Receives DB snapshot from supabase_sync.py |
| `execute-command` | Receives campaign commands from Command Center |
| `get-pending-commands` | Returns pending commands for command_executor.py |
| `save-recommendation` | Writes recommendation_agent output |
| `approve-recommendation` | Approves/marks recommendations executed |
| `save-health-check` | Writes health_agent results |
| `chat-messages` | Handles all chat_messages read/write *(new)* |

### chat_messages Table Schema
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial | Primary key |
| `session_id` | uuid | Groups a conversation — new UUID per browser session |
| `role` | varchar(20) | `user` or `assistant` |
| `content` | text | Message text (markdown supported for assistant) |
| `status` | varchar(20) | `pending` → `processing` → `done` |
| `metadata` | jsonb | Tool turn count and other metadata |
| `created_at` | timestamptz | Auto-set |

### Pending Lovable Build Steps
The chat UI frontend still needs to be built in Lovable (the backend is complete):
1. Run `supabase_migrations/004_chat_messages.sql` in Supabase SQL Editor
2. Enable Supabase Realtime on `chat_messages` table
3. Deploy `supabase_edge_functions/chat-messages/` via `supabase functions deploy chat-messages`
4. Build the chat page in Lovable using the prompt in the step-by-step guide

---

## 9. Scheduling & Automation

### Active Ad Days
**Friday, Saturday, Sunday, Monday ONLY.**
Tuesday, Wednesday, Thursday are fully suppressed on all platforms.

### Full Schedule
| Task | Frequency | Agent |
|---|---|---|
| Full pipeline (sync → optimize → creative → report → sync) | Daily at 8:00 AM | orchestrator |
| Chat agent (Command Center AI responses) | Every 5 seconds | chat_agent |
| Command executor (campaign pause/enable) | Every 30 seconds | command_executor |
| Supabase sync (Command Center data refresh) | Every 5 minutes | supabase_sync |
| Inter-agent message processing | Every 5 minutes | orchestrator |
| Health checks | Every 30 minutes | health_agent |
| System status log | Every hour | orchestrator |

---

## 10. Meta Campaigns — Current State

### Active Campaigns (as of 2026-03-24)
| Campaign | Notes |
|---|---|
| [RMA] Design Build — East Bay | Launched 2026-03-22. RMA targeting (advantage_audience=0, age 35–55, female). **1 Project Inquiry Submitted conversion on day 2 (2026-03-23, $23.70 spend).** |
| Lead Gen \| Custom Home Design & Build (Refresh) 2/8/2026 | CPL ~$260, 11 leads/30d. Pre-RMA targeting (advantage_audience=1). Do NOT change. |
| Lead Gen \| Home Remodel (Refresh) 2/8/26 | CPL ~$149, 18 leads/30d. Pre-RMA targeting (advantage_audience=1). Do NOT change. |
| booking AI test 1 | 2,215 landing page views at ~$0.54/view. Conversions via pixel only. |
| booking AI test 2 | Same as test 1. |
| New landing page. | Engagement-focused. No conversions to date. |
| Lead Gen \| Home Remodel (Refresh) -2/7/26 | Older version, active. |
| Lead Gen \| Home Remodel (Refresh) | Original version, active. |
| Lead Gen \| Custom Home Design & Build (Refresh) | Original version, active. |
| Retargeting Leads Campaign (25% of winning ads \| 180 days) | Retargeting, active. |
| Lead Gen \| Home Remodel | Original, active. |
| Lead Gen \| Custom Home Design & Build | Original, active. |

### RMA Targeting Spec (mandatory for all new Meta ad sets)
```json
{
  "age_min": 35, "age_max": 55, "genders": [2],
  "flexible_spec": [{"family_statuses": [
    {"id": "6023005529383"}, {"id": "6023005570783"},
    {"id": "6023005681983"}, {"id": "6023005718983"}, {"id": "6023080302983"}
  ]}],
  "geo_locations": {
    "zips": [
      {"key": "US:94506"}, {"key": "US:94507"}, {"key": "US:94526"},
      {"key": "US:94549"}, {"key": "US:94551"}, {"key": "US:94556"},
      {"key": "US:94563"}, {"key": "US:94566"}, {"key": "US:94568"},
      {"key": "US:94582"}, {"key": "US:94583"}, {"key": "US:94588"}
    ],
    "location_types": ["home", "recent"]
  },
  "targeting_automation": {"advantage_audience": 0}
}
```

### Important Meta Rules
- New campaigns take 24–48+ hours to start spending — never flag as broken if under 3 days old
- Do NOT change targeting on pre-RMA campaigns (Lead Gen Refresh) — they are producing leads within target CPL
- Zero Meta lead form completions ≠ zero conversions — conversions tracked via pixel, not native Meta lead forms

---

## 11. Google Ads — Current State

**Status:** Staged and ready — awaiting production developer token approval.

**Check approval status:** Go to ads.google.com/aw/apicenter in the Ridgecrest Marketing manager account.

### Campaign Buckets (staged in DB, ready to launch)
Design Build, Custom Home, Custom Home Builder, Whole House Remodel, Kitchen Remodel, Bathroom Remodel, Master Bathroom Remodel, Interior Design, Interior Design Firm, Kitchen Design, Bathroom Design, Home Design, Architect, Home Builder, General Contractor, Remodeling Contractor, Home Renovation, Design Build Contractor

### Targeting
- **Service areas:** Pleasanton, Walnut Creek, San Ramon, Dublin, Orinda, Moraga, Danville, Alamo, Lafayette, Rossmoor, Sunol, Diablo
- **Zip codes:** 94596, 94595, 94588, 94586, 94583, 94582, 94568, 94566, 94563, 94556
- **Match types:** Exact `[keyword]` and phrase `"keyword"` only — no broad match at launch
- **Ad schedule:** Fri/Sat/Sun/Mon only

---

## 12. Microsoft Ads — Current State

- Structure mirrors Google Ads campaign layout
- Day scheduling applied: −100% bid adjustment Tue/Wed/Thu
- Geo targeting applied: approved zip codes
- Active and syncing — subordinate to Google in platform rollout priority

---

## 13. Conversion Tracking

### Official URLs
| Event | URL | Type |
|---|---|---|
| Ad landing page | https://go.ridgecrestdesigns.com | Landing |
| Project Inquiry Submitted | https://elevate-scheduling-6b2fdec8.base44.app/inquiry-submitted | Primary conversion |
| Booking Confirmed | https://elevate-scheduling-6b2fdec8.base44.app/booking-confirmed | Secondary conversion |
| Project Inquiry Form | https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm | Form page |

### Meta Custom Conversions
| Event | Custom Conversion ID | Meta Action Type |
|---|---|---|
| Project Inquiry Submitted | `1274199281573639` | `offsite_conversion.custom.1274199281573639` |
| Booking Confirmed | `2010554443142598` | `offsite_conversion.fb_pixel_complete_registration` |

### Meta Pixel
- **Pixel ID:** 534314263109913
- **Installed on:** elevate-scheduling-6b2fdec8.base44.app (all pages)

### Primary Optimization Target
Project Inquiry Submitted. At low conversion volume (< 50/week), optimize for Landing Page Views as a proxy.

---

## 14. Budget Rules & Spend Strategy

### Hard Limits
| Rule | Amount |
|---|---|
| Weekly ceiling (all platforms combined) | $1,000 maximum |
| Weekly floor (target minimum) | $500 |
| Underspend alert threshold | Below $400/week |
| Daily soft cap | $250 — blocks new budget increases |
| Daily escalation alert | Above $300 |
| Weekly escalation alert | Above $1,100 |
| Minimum per campaign | $10/day floor |

### Allocation Philosophy
- Budget follows performance — top performers receive budget from under-performers
- Never reduce a campaign scoring ≥ 60 regardless of daily totals
- Never reduce any campaign below $10/day
- Concentrate spend on highest-converting campaigns first
- Active days: Friday, Saturday, Sunday, Monday only

### Target CPL
$150–$500 per qualified project inquiry

---

## 15. Key Configuration Values

| Item | Value |
|---|---|
| Meta Ad Account | act_58393749 |
| Meta Pixel ID | 534314263109913 |
| Meta Saved Audience ID | 6934900931693 |
| Meta API Version | v21.0 |
| Custom Conversion — Project Inquiry | 1274199281573639 |
| Custom Conversion — Booking Confirmed | 2010554443142598 |
| Command Center | https://ridgecrest-command-center.lovable.app |
| Ad Landing Page | https://go.ridgecrestdesigns.com |
| Inquiry Submitted URL | https://elevate-scheduling-6b2fdec8.base44.app/inquiry-submitted |
| Booking Confirmed URL | https://elevate-scheduling-6b2fdec8.base44.app/booking-confirmed |
| Project Inquiry Form | https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm |
| Alert Email | henry@ridgecrestdesigns.com |
| Supabase Project ID | itoinsaotwsmidbosqbq |
| Supabase URL | https://itoinsaotwsmidbosqbq.supabase.co |
| Ingest API Key | RCM-2026-xK9mP3vL8nQ5wJ2hY7tF4dA6sE1uB0cD |
| Microsoft Ads Account ID | 187004108 |
| Daily Budget Cap | $125.00 (per Meta manager) / $250.00 daily soft cap (guardrails) |
| Weekly Budget Ceiling | $1,000 |
| Target CPL Range | $150–$500 |
| Pipeline Run Time | 8:00 AM daily |
| Chat Agent Poll Interval | Every 5 seconds |
| Command Executor Poll Interval | Every 30 seconds |
| Supabase Sync Interval | Every 5 minutes |
| Health Check Interval | Every 30 minutes |
| PostgreSQL Database | marketing_agent @ localhost:5432 |
| Working Directory | /root/agent |
| Systemd Service | ridgecrest-orchestrator.service |
| AI Model | claude-opus-4-6 |

---

## 16. File Inventory

### Core Agent Files
| File | Purpose |
|---|---|
| `orchestrator.py` | Central controller and daemon — single entry point for everything |
| `chat_agent.py` | Command Center AI chat — Claude with tools, polls every 5s *(new)* |
| `meta_sync.py` | Pull Meta campaign performance data (30 days) |
| `meta_manager.py` | Meta optimization — budget, bids, pauses, day scheduling |
| `google_sync.py` | Pull Google Ads performance data |
| `google_ads_builder.py` | Build Google Ads campaigns, ad groups, keywords, ads |
| `google_ads_scheduler.py` | Apply Google Ads day scheduling (Fri–Mon only) |
| `microsoft_sync.py` | Pull Microsoft Ads performance data |
| `microsoft_manager.py` | Microsoft Ads optimization |
| `msft_apply_day_schedule.py` | One-time: apply Tue/Wed/Thu bid suppression on Microsoft |
| `msft_apply_geo_targeting.py` | One-time: apply zip code targeting on Microsoft |
| `performance_analyst.py` | Anomaly detection and performance analysis |
| `bid_budget_optimizer.py` | Bid and budget optimization engine |
| `creative_agent.py` | Claude-powered ad copy generation |
| `reporting_agent.py` | Claude-powered performance report generation |
| `recommendation_agent.py` | Strategic recommendations for Command Center |
| `health_agent.py` | End-to-end system health checks |
| `guardrails.py` | Guardrails enforcement engine |
| `supabase_sync.py` | Push DB snapshot to Supabase every 5 minutes |
| `command_executor.py` | Execute campaign commands from Command Center |
| `db.py` | Shared database utilities (connection, message bus, heartbeat, action log) |
| `campaign_setup.py` | Campaign structure setup utility |
| `get_google_token.py` | Google OAuth token helper |

### Configuration & Reference Files
| File | Purpose |
|---|---|
| `CLAUDE.md` | Master strategy document — all campaign rules, targeting, messaging |
| `GUARDRAILS.md` | Hard constraints for all automated agents |
| `BRAND.md` | Brand voice and creative guidelines |
| `LOVABLE_REFERENCE.md` | Complete DB schema reference for Lovable frontend developer |
| `SYSTEM_REPORT.md` | This file — full system documentation |
| `schema.sql` | PostgreSQL schema — all tables, indexes, seed data |
| `.env` | Environment variables (API keys, credentials) |

### Supabase Migrations
| File | Purpose |
|---|---|
| `supabase_migrations/001_command_queue.sql` | command_queue table + RLS policies |
| `supabase_migrations/002_recommendations.sql` | recommendations table |
| `supabase_migrations/003_system_health.sql` | system_health table |
| `supabase_migrations/004_chat_messages.sql` | chat_messages table *(new)* |

### Supabase Edge Functions
| Directory | Purpose |
|---|---|
| `supabase_edge_functions/execute-command/` | Execute campaign commands from Command Center |
| `supabase_edge_functions/get-pending-commands/` | Return pending commands to command_executor |
| `supabase_edge_functions/approve-recommendation/` | Approve recommendations |
| `supabase_edge_functions/save-recommendation/` | Save recommendation_agent output |
| `supabase_edge_functions/save-health-check/` | Save health_agent output |
| `supabase_edge_functions/chat-messages/` | All chat_messages read/write operations *(new)* |

### Test Files
| File | Purpose |
|---|---|
| `test_meta_ads.py` | Meta API integration tests |
| `test_microsoft_ads.py` | Microsoft Ads API integration tests |
| `test_pipeline.py` | Full pipeline integration test |
| `meta_create_test.py` | Meta campaign creation test |
| `meta_multi_ad_test.py` | Meta multi-ad creation test |

---

## 17. Pending Items

### High Priority
| Item | Status | Notes |
|---|---|---|
| Google Ads developer token production approval | Pending | Check ads.google.com/aw/apicenter in Ridgecrest Marketing manager account |
| Chat UI build in Lovable | Pending | Backend complete — Supabase migration, edge function, and chat_agent all ready |

### Chat UI — Remaining Steps
1. Run `supabase_migrations/004_chat_messages.sql` in Supabase SQL Editor
2. Enable Supabase Realtime on `chat_messages` table (Database → Replication)
3. Deploy edge function: `supabase functions deploy chat-messages`
4. Build chat page in Lovable using the provided step-by-step prompt

### Once Google Ads Token Is Approved
1. Run `google_ads_builder.py` to push all staged campaigns live
2. Verify `google_ads_scheduler.py` applies the Fri–Mon ad schedule
3. Confirm `google_sync.py` starts pulling performance data cleanly
4. Monitor CPL vs Meta for budget allocation decisions

### Platform Expansion Sequence
1. **Now:** Meta (live and producing conversions)
2. **Next:** Google Ads (staged, awaiting token)
3. **After Google proven:** Microsoft Ads (active but subordinate)

---

*Last updated: 2026-03-24 | Contact: henry@ridgecrestdesigns.com*
