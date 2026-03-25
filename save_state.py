"""
State Snapshot — Ridgecrest Designs
=====================================
Runs every minute via cron. Writes current system state to Claude memory
so any new session starts with full context. No API calls, no credits used.
"""
import os
import sys
import zoneinfo
from datetime import datetime

# Add agent directory to path
sys.path.insert(0, "/root/agent")
os.chdir("/root/agent")

from dotenv import load_dotenv
load_dotenv()

import db

MEMORY_PATH = "/root/.claude/projects/-root-agent/memory/project_current_state.md"
PT = zoneinfo.ZoneInfo("America/Los_Angeles")


def run():
    now_pt = datetime.now(PT)
    today = now_pt.date()
    timestamp = now_pt.strftime("%Y-%m-%d %H:%M PT")

    # Orchestrator health
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "is-active", "ridgecrest-agent.service"],
            capture_output=True, text=True
        )
        orchestrator_status = result.stdout.strip()
    except Exception:
        orchestrator_status = "unknown"

    # Recent spend and conversions
    try:
        with db.get_db() as (conn, cur):
            # Today
            cur.execute("""
                SELECT COALESCE(SUM(cost_usd), 0) AS spend,
                       COALESCE(SUM(conversions), 0) AS convs
                FROM performance_metrics
                WHERE metric_date = %s AND entity_type = 'campaign'
            """, (today,))
            today_row = cur.fetchone()

            # This week
            cur.execute("""
                SELECT COALESCE(SUM(cost_usd), 0) AS spend,
                       COALESCE(SUM(conversions), 0) AS convs
                FROM performance_metrics
                WHERE metric_date >= date_trunc('week', %s::date)
                  AND entity_type = 'campaign'
            """, (today,))
            week_row = cur.fetchone()

            # Active campaigns
            cur.execute("""
                SELECT name, platform, status, daily_budget_usd
                FROM campaigns
                WHERE status = 'ENABLED'
                ORDER BY platform, name
            """)
            active = cur.fetchall()

            # Recent errors from agent heartbeats
            cur.execute("""
                SELECT agent_name, status, last_error, last_run_at
                FROM agent_heartbeats
                WHERE status = 'error'
                ORDER BY last_run_at DESC
                LIMIT 5
            """)
            errors = cur.fetchall()

            # Last sync times
            cur.execute("""
                SELECT agent_name, last_run_at, status
                FROM agent_heartbeats
                ORDER BY last_run_at DESC
                LIMIT 8
            """)
            heartbeats = cur.fetchall()

    except Exception as e:
        write_error(str(e), timestamp)
        return

    today_spend = float(today_row["spend"])
    today_convs = float(today_row["convs"])
    week_spend  = float(week_row["spend"])
    week_convs  = float(week_row["convs"])

    daily_pct  = (today_spend / 250) * 100
    weekly_pct = (week_spend / 1000) * 100

    # Build active campaigns table
    camp_lines = []
    for c in active:
        budget = f"${float(c['daily_budget_usd']):.2f}/day" if c['daily_budget_usd'] else "—"
        camp_lines.append(f"- [{c['platform']}] {c['name']} | {budget}")

    # Build heartbeat table
    hb_lines = []
    for h in heartbeats:
        ts = h["last_run_at"].strftime("%m-%d %H:%M") if h["last_run_at"] else "—"
        hb_lines.append(f"- {h['agent_name']}: {h['status']} @ {ts}")

    # Build error lines
    error_lines = []
    for e in errors:
        error_lines.append(f"- {e['agent_name']}: {e['last_error']}")

    content = f"""---
name: Ridgecrest Designs — Current System State
description: What is built, what is working, what is pending. Auto-updated every minute.
type: project
---

## Last Updated
{timestamp}

## Orchestrator
- Service status: {orchestrator_status}
- Auto-restarts via systemd on crash or reboot

## Today's Performance ({today})
- Spend: ${today_spend:.2f} / $250.00 ({daily_pct:.1f}% of daily cap)
- Conversions: {today_convs:.0f}

## This Week's Performance
- Spend: ${week_spend:.2f} / $1,000.00 ({weekly_pct:.1f}% of weekly ceiling)
- Conversions: {week_convs:.0f}

## Active Campaigns ({len(active)} enabled)
{chr(10).join(camp_lines) if camp_lines else '- None'}

## Agent Heartbeats (most recent)
{chr(10).join(hb_lines) if hb_lines else '- No heartbeat data'}

## Recent Agent Errors
{chr(10).join(error_lines) if error_lines else '- None'}

## What Is Built and Working
- Orchestrator running as systemd service (auto-restarts on crash/reboot)
- Meta campaigns syncing and running (act_58393749)
- Microsoft Ads campaigns created and syncing
- Google Ads campaigns in DB — awaiting developer token approval for live API writes
- Supabase sync pushing local DB to Supabase every cycle
- Chat agent live — Command Center Chat page connected via chat-messages edge function
- Bid/budget optimizer running on active days
- Creative agent generating ad copy briefs
- Reporting agent producing daily/weekly reports
- Recommendation agent generating optimization suggestions
- Health agent monitoring system status
- Timezone fix applied — all agents use Pacific time (not UTC server time)

## Recent Architecture Decisions
- Chat agent uses claude-sonnet-4-6 (not Opus) for speed — no adaptive thinking
- Chat poll interval: 2 seconds
- All date logic uses db.pacific_today() or AT TIME ZONE 'America/Los_Angeles'
- Lovable sidebar: persistent on desktop (lg+), Sheet overlay on mobile
- Memory auto-updated every minute via cron (save_state.py)

## Pending / Known Issues
- Google Ads developer token still awaiting approval
- Microsoft campaigns spending $0 — needs investigation
- chat_agent tools do not yet include: create_campaign, adjust_budget, add_negative_keywords

## Key Files
- /root/agent/orchestrator.py — main daemon
- /root/agent/chat_agent.py — Command Center chat
- /root/agent/bid_budget_optimizer.py — budget/bid logic
- /root/agent/meta_manager.py — Meta campaign management
- /root/agent/campaign_setup.py — new campaign creation
- /root/agent/db.py — shared DB utilities + pacific_today()
- /root/agent/.env — all API keys and credentials

## Key Config
- Supabase project: itoinsaotwsmidbosqbq
- Meta ad account: act_58393749
- Weekly ceiling: $1,000 | Daily cap: $250
- Active ad days: Friday, Saturday, Sunday, Monday
- Target CPL: $150–$500
- INGEST_API_KEY: RCM-2026-xK9mP3vL8nQ5wJ2hY7tF4dA6sE1uB0cD

**Why:** Auto-snapshot so any new Claude session has full current context.
**How to apply:** Read this at the start of every session before making changes.
"""

    with open(MEMORY_PATH, "w") as f:
        f.write(content)


def write_error(error: str, timestamp: str):
    try:
        with open(MEMORY_PATH, "r") as f:
            existing = f.read()
        with open(MEMORY_PATH, "w") as f:
            f.write(existing.replace(
                "## Last Updated",
                f"## Snapshot Error\n{timestamp} — {error}\n\n## Last Updated"
            ))
    except Exception:
        pass


if __name__ == "__main__":
    run()
