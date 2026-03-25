"""
Chat Agent
==========
Bridges the Lovable Command Center chat UI with the Ridgecrest Designs
marketing automation system.

Polls Supabase for pending user messages every 5 seconds, processes them
with Claude Opus 4.6 (adaptive thinking, tool use), and writes the
assistant response back to Supabase for the frontend to display.

Tools available to Claude:
  get_active_campaigns    — list all campaigns and their status / budget
  get_campaign_status     — 7-day performance metrics per platform
  get_today_metrics       — live today spend / conversions from Meta API
  get_budget_status       — weekly + daily spend vs guardrail caps
  get_reports             — most recent AI-generated performance reports
  run_meta_sync           — pull latest Meta data into the local DB
  run_optimizer           — run bid/budget optimizer
  run_creative_agent      — generate new ad copy briefs
  pause_campaign          — pause a specific campaign
  enable_campaign         — enable / resume a specific campaign

Run standalone:  python chat_agent.py
"""

import json
import logging
import os
import sys
import time
from datetime import date, datetime
from decimal import Decimal

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [chat_agent] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from config import (
    SUPABASE_URL, META_AD_ACCOUNT_ID, META_BASE_URL,
    META_PIXEL_ID, META_CONVERSION_INQUIRY_ID, META_CONVERSION_BOOKING_ID,
    META_AUDIENCE_ID, LANDING_PAGE_URL, INQUIRY_SUBMITTED_URL, BOOKING_CONFIRMED_URL,
    WEEKLY_BUDGET_CEILING_USD, DAILY_BUDGET_SOFT_CAP_USD,
    TARGET_CPL_LOW, TARGET_CPL_HIGH, ACTIVE_DAYS,
    COMMAND_CENTER_URL,
)

AGENT_NAME        = "chat_agent"
CHAT_ENDPOINT     = f"{SUPABASE_URL}/functions/v1/chat-messages"
INGEST_API_KEY    = os.getenv("INGEST_API_KEY", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT   = META_AD_ACCOUNT_ID
POLL_INTERVAL     = 2   # seconds between polls


# ---------------------------------------------------------------------------
# Claude client
# ---------------------------------------------------------------------------

_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


# ---------------------------------------------------------------------------
# System prompt — full agency context
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = f"""
You are the Ridgecrest Designs Marketing AI — an expert marketing operations
agent embedded directly inside the Command Center dashboard at
{COMMAND_CENTER_URL}.

You have full control of the marketing automation system for Ridgecrest Designs,
a premium design-build firm in Pleasanton, California. You can query live
performance data, run syncs, optimize campaigns, generate ad copy, and
pause or enable campaigns — all using the tools available to you.

COMPANY & STRATEGY
------------------
- Premium design-build firm for affluent East Bay homeowners
- Service areas: Pleasanton, Walnut Creek, Danville, Alamo, San Ramon, Dublin,
  Orinda, Moraga, Lafayette, Rossmoor, Sunol, Diablo
- Target customer: 35–55 yo, high-income homeowners, families with children
- Priority services: Custom homes ($5M–$10M), whole-house remodels ($1M+),
  kitchen remodels ($150K+), bathroom remodels ($60K+)
- Positioning: luxury, precision, process-driven, premium — never compete on price

BUDGET GUARDRAILS (non-negotiable)
-----------------------------------
- Weekly ceiling: ${WEEKLY_BUDGET_CEILING_USD:,.0f} across all platforms combined
- Daily soft cap: ${DAILY_BUDGET_SOFT_CAP_USD:,.0f} — no increases once reached
- Active ad days: {', '.join(d.title() for d in sorted(ACTIVE_DAYS, key=lambda x: ['monday','tuesday','wednesday','thursday','friday','saturday','sunday'].index(x)))} ONLY
- Target CPL: ${TARGET_CPL_LOW:,.0f}–${TARGET_CPL_HIGH:,.0f}

PLATFORMS (in priority order)
------------------------------
1. Meta (Facebook/Instagram) — ACTIVE. Account: {META_AD_ACCOUNT_ID}
2. Google Ads — the get_active_campaigns tool dynamically checks last sync date and spend data. Always use that tool to answer Google Ads questions — never assume or state a fixed answer.
3. Microsoft Ads — active but subordinate to Google

CONVERSION TRACKING
--------------------
- Landing page: {LANDING_PAGE_URL}
- Primary conversion: Project Inquiry Submitted
  URL: {INQUIRY_SUBMITTED_URL}
  Custom conversion ID: {META_CONVERSION_INQUIRY_ID}
- Secondary: Booking Confirmed
  URL: {BOOKING_CONFIRMED_URL}
  Custom conversion ID: {META_CONVERSION_BOOKING_ID}
- Meta Pixel ID: {META_PIXEL_ID}

META CAMPAIGN NOTES
--------------------
- All new Meta ad sets MUST use saved audience ID {META_AUDIENCE_ID}
  with advantage_audience=0 (hard constraint, NOT a signal)
- New campaigns need 24–48h review before spending — never flag as broken
  if less than 3 days old
- Zero Meta lead form completions ≠ zero conversions — conversions tracked
  via pixel on the Base44 app, not as native Meta lead forms

BEHAVIOR GUIDELINES
--------------------
- Be direct, concise, and action-oriented
- When asked to run something, use the appropriate tool immediately
- Always confirm actions before taking them when the action is irreversible
  (e.g., pausing a live campaign)
- Cite actual numbers from the data — never guess at performance
- Flag guardrail violations proactively if you see them in the data
- Today's date is always available — use it when interpreting time references
- DATE PRECISION IS CRITICAL: always map time words to exact dates before calling tools
  - "yesterday" → date_from and date_to both set to yesterday's YYYY-MM-DD date
  - "today" → date_from and date_to both set to today's YYYY-MM-DD date
  - "this week" → date_from = most recent Monday, date_to = today
  - "last 7 days" → use days=7 (rolling window)
  - Never use a multi-day window when the user asks about a single specific day
""".strip()


# ---------------------------------------------------------------------------
# Supabase edge function helpers
# ---------------------------------------------------------------------------

def _edge_headers() -> dict:
    return {
        "x-api-key": INGEST_API_KEY,
        "Content-Type": "application/json",
    }


def _edge(action: str, **kwargs) -> dict:
    body = {"action": action, **kwargs}
    resp = requests.post(CHAT_ENDPOINT, headers=_edge_headers(),
                         json=body, timeout=15)
    if resp.status_code != 200:
        logger.warning("chat edge fn (%s): %d — %s", action,
                       resp.status_code, resp.text[:200])
        return {}
    return resp.json()


def fetch_pending_messages() -> list[dict]:
    data = _edge("get_pending")
    return data.get("messages", [])


def fetch_history(session_id: str) -> list[dict]:
    data = _edge("get_history", session_id=session_id)
    return data.get("messages", [])


def mark_processing(msg_id: int):
    _edge("mark_processing", id=msg_id)


def post_response(session_id: str, content: str,
                  user_message_id: int, metadata: dict = None):
    _edge("post_response",
          session_id=session_id,
          content=content,
          user_message_id=user_message_id,
          metadata=metadata or {})


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def tool_get_active_campaigns() -> str:
    with db.get_db() as (conn, cur):
        cur.execute("""
            SELECT id, name, platform, status, daily_budget_usd,
                   service_category, google_campaign_id
            FROM campaigns
            WHERE status != 'REMOVED'
            ORDER BY platform, name
        """)
        rows = [dict(r) for r in cur.fetchall()]
    if not rows:
        return "No active campaigns found."

    # For each Google Ads campaign, check last confirmed spend date and sync status
    with db.get_db() as (conn2, cur2):
        # Last spend date per Google campaign
        cur2.execute("""
            SELECT c.id,
                   COALESCE(SUM(pm.cost_usd), 0) AS spend_7d,
                   MAX(pm.metric_date) AS last_spend_date
            FROM campaigns c
            LEFT JOIN performance_metrics pm
              ON pm.entity_id = c.id
             AND pm.entity_type = 'campaign'
             AND pm.cost_usd > 0
            WHERE c.platform = 'google_ads'
            GROUP BY c.id
        """)
        google_data = {r["id"]: dict(r) for r in cur2.fetchall()}

        # Check if google_sync is currently erroring
        cur2.execute("""
            SELECT last_error, last_run_at, status
            FROM agent_heartbeats
            WHERE agent_name = 'google_sync'
            ORDER BY last_run_at DESC LIMIT 1
        """)
        gsync = cur2.fetchone()
        sync_broken = gsync and gsync["status"] == "error"
        last_sync = gsync["last_run_at"].strftime("%Y-%m-%d") if gsync and gsync["last_run_at"] else "unknown"

    lines = []
    for r in rows:
        budget = f"${_safe_float(r.get('daily_budget_usd')):.2f}/day" \
                 if r.get("daily_budget_usd") else "—"
        platform = r["platform"]
        if platform == "google_ads":
            gdata = google_data.get(r.get("id"), {})
            last_spend = gdata.get("last_spend_date")
            if last_spend:
                if sync_broken:
                    note = f" — last confirmed spend {last_spend} (sync broken since {last_sync}, likely still running)"
                else:
                    note = f" — last spend {last_spend}"
            else:
                note = " ⚠️ no spend on record — not yet live"
        else:
            note = ""
        lines.append(
            f"[{platform}] {r['name']} | {r['status']} | budget: {budget}{note}"
        )

    return "\n".join(lines)


def tool_get_campaign_status(platform: str = "all", days: int = 7,
                             date_from: str = None, date_to: str = None) -> str:
    import zoneinfo
    from datetime import timedelta
    pt = zoneinfo.ZoneInfo("America/Los_Angeles")
    today = db.pacific_today()

    if date_from and date_to:
        start, end = date_from, date_to
        label = f"{date_from} to {date_to}"
    elif date_from:
        start, end = date_from, date_from
        label = date_from
    else:
        start = (today - timedelta(days=days - 1)).isoformat()
        end   = today.isoformat()
        label = f"last {days} day{'s' if days != 1 else ''}"

    with db.get_db() as (conn, cur):
        params = [start, end]
        platform_filter = "AND pm.platform = %s" if platform != "all" else ""
        if platform != "all":
            params.append(platform)
        cur.execute(f"""
            SELECT c.name, c.platform,
                   SUM(pm.cost_usd)    AS spend,
                   SUM(pm.clicks)      AS clicks,
                   SUM(pm.impressions) AS impressions,
                   SUM(pm.conversions) AS conversions
            FROM performance_metrics pm
            JOIN campaigns c ON c.id = pm.entity_id
            WHERE pm.metric_date BETWEEN %s AND %s
              AND pm.entity_type = 'campaign'
              {platform_filter}
            GROUP BY c.name, c.platform
            ORDER BY spend DESC
        """, params)
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return f"No performance data found for {label}."
    lines = [f"Performance — {label}:"]
    for r in rows:
        spend = _safe_float(r.get("spend"))
        convs = _safe_float(r.get("conversions"))
        cpl   = f"${spend/convs:.0f}" if convs > 0 else "—"
        lines.append(
            f"  [{r['platform']}] {r['name']}: "
            f"${spend:.2f} spend | {r['clicks']} clicks | "
            f"{convs:.1f} conversions | CPL {cpl}"
        )
    return "\n".join(lines)


def tool_get_today_metrics() -> str:
    today = db.pacific_today().isoformat()
    r = requests.get(f"{META_BASE_URL}/{META_AD_ACCOUNT}/campaigns", params={
        "access_token": META_ACCESS_TOKEN,
        "effective_status": '["ACTIVE"]',
        "fields": "id,name",
        "limit": 50,
    }).json()
    campaigns = r.get("data", [])
    if not campaigns:
        return "No active Meta campaigns found."

    results = []
    for c in campaigns:
        ins = requests.get(f"{META_BASE_URL}/{c['id']}/insights", params={
            "access_token": META_ACCESS_TOKEN,
            "time_range": f'{{"since":"{today}","until":"{today}"}}',
            "fields": "spend,impressions,clicks,actions",
            "level": "campaign",
        }).json()
        data = ins.get("data", [])
        if not data:
            results.append(f"  {c['name']}: no data yet today")
            continue
        d = data[0]
        actions     = {a["action_type"]: a["value"] for a in d.get("actions", [])}
        lp_views    = actions.get("landing_page_view", "0")
        pixel_leads = actions.get(f"offsite_conversion.custom.1274199281573639", "0")
        booking     = actions.get("offsite_conversion.fb_pixel_complete_registration", "0")
        results.append(
            f"  {c['name']}: "
            f"${d.get('spend','0')} spend | "
            f"{d.get('impressions','0')} impr | "
            f"{d.get('clicks','0')} clicks | "
            f"LPV: {lp_views} | "
            f"Inquiries: {pixel_leads} | "
            f"Bookings: {booking}"
        )
    return f"Today ({today}) — Meta campaigns:\n" + "\n".join(results)


def tool_get_budget_status() -> str:
    with db.get_db() as (conn, cur):
        # Today's spend
        cur.execute("""
            SELECT COALESCE(SUM(cost_usd), 0) AS today_spend
            FROM performance_metrics
            WHERE metric_date = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Los_Angeles')::date AND entity_type = 'campaign'
        """)
        today_spend = _safe_float(cur.fetchone()["today_spend"])

        # This week (Mon–Sun)
        cur.execute("""
            SELECT COALESCE(SUM(cost_usd), 0) AS week_spend
            FROM performance_metrics
            WHERE metric_date >= date_trunc('week', (CURRENT_TIMESTAMP AT TIME ZONE 'America/Los_Angeles')::date)
              AND entity_type = 'campaign'
        """)
        week_spend = _safe_float(cur.fetchone()["week_spend"])

    daily_remaining  = max(0, DAILY_BUDGET_SOFT_CAP_USD - today_spend)
    weekly_remaining = max(0, WEEKLY_BUDGET_CEILING_USD - week_spend)
    daily_status     = "OVER CAP"  if today_spend >= DAILY_BUDGET_SOFT_CAP_USD else \
                       "NEAR CAP"  if today_spend >= DAILY_BUDGET_SOFT_CAP_USD * 0.80 else "OK"
    weekly_status    = "OVER CEILING"      if week_spend >= WEEKLY_BUDGET_CEILING_USD else \
                       "NEAR CEILING"      if week_spend >= WEEKLY_BUDGET_CEILING_USD * 0.80 else \
                       "ALERT — underspend" if week_spend < 400 else "OK"

    return (
        f"Budget Status — {db.pacific_today()}\n"
        f"  Daily:  ${today_spend:.2f} / ${DAILY_BUDGET_SOFT_CAP_USD:.2f} cap  "
        f"(${daily_remaining:.2f} remaining) — {daily_status}\n"
        f"  Weekly: ${week_spend:.2f} / ${WEEKLY_BUDGET_CEILING_USD:.2f} ceiling  "
        f"(${weekly_remaining:.2f} remaining) — {weekly_status}"
    )


def tool_get_reports(n: int = 3) -> str:
    with db.get_db() as (conn, cur):
        cur.execute("""
            SELECT report_type, platform, period_start, period_end,
                   title, summary, created_at
            FROM reports
            ORDER BY created_at DESC
            LIMIT %s
        """, (n,))
        rows = [dict(r) for r in cur.fetchall()]
    if not rows:
        return "No reports found."
    lines = [f"Last {n} reports:"]
    for r in rows:
        ts = r["created_at"].strftime("%Y-%m-%d %H:%M") if r.get("created_at") else "—"
        lines.append(
            f"\n[{ts}] {r.get('title','Untitled')} "
            f"({r.get('report_type','?')} / {r.get('platform','?')})\n"
            f"  {r.get('summary','')}"
        )
    return "\n".join(lines)


def tool_run_meta_sync() -> str:
    try:
        import meta_sync
        result = meta_sync.run()
        return f"Meta sync complete — {result}"
    except Exception as e:
        return f"Meta sync failed: {e}"


def tool_run_optimizer() -> str:
    try:
        import bid_budget_optimizer
        result = bid_budget_optimizer.run()
        return (
            f"Optimizer complete — "
            f"bid_actions={result.get('bid_actions',0)}, "
            f"budget_actions={result.get('budget_actions',0)}, "
            f"schedule_changes={result.get('schedule_changes',0)}"
        )
    except Exception as e:
        return f"Optimizer failed: {e}"


def tool_run_creative_agent(service_category: str = None) -> str:
    try:
        import creative_agent
        result = creative_agent.run()
        return f"Creative agent complete — {result}"
    except Exception as e:
        return f"Creative agent failed: {e}"


def tool_pause_campaign(campaign_name: str, platform: str) -> str:
    try:
        import command_executor
        with db.get_db() as (conn, cur):
            cur.execute(
                """SELECT * FROM campaigns
                   WHERE LOWER(name) LIKE LOWER(%s) AND platform = %s
                     AND status != 'REMOVED'""",
                (f"%{campaign_name}%", platform),
            )
            row = cur.fetchone()
        if not row:
            return f"Campaign not found matching '{campaign_name}' on {platform}."
        camp = dict(row)
        ok, msg = command_executor._apply_to_platform(
            platform, camp["google_campaign_id"], "PAUSED"
        )
        if ok:
            command_executor._update_db_status(camp["id"], "PAUSED")
        return msg
    except Exception as e:
        return f"Pause failed: {e}"


def tool_enable_campaign(campaign_name: str, platform: str) -> str:
    try:
        import command_executor
        with db.get_db() as (conn, cur):
            cur.execute(
                """SELECT * FROM campaigns
                   WHERE LOWER(name) LIKE LOWER(%s) AND platform = %s
                     AND status != 'REMOVED'""",
                (f"%{campaign_name}%", platform),
            )
            row = cur.fetchone()
        if not row:
            return f"Campaign not found matching '{campaign_name}' on {platform}."
        camp = dict(row)
        ok, msg = command_executor._apply_to_platform(
            platform, camp["google_campaign_id"], "ENABLED"
        )
        if ok:
            command_executor._update_db_status(camp["id"], "ENABLED")
        return msg
    except Exception as e:
        return f"Enable failed: {e}"


# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_active_campaigns",
        "description": (
            "List all campaigns across all platforms with their current "
            "status and daily budget."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_campaign_status",
        "description": (
            "Get performance metrics (spend, clicks, impressions, conversions, CPL) "
            "for all campaigns. Use date_from/date_to for precise date ranges. "
            "For 'yesterday' pass date_from and date_to both set to yesterday's date. "
            "For 'today' pass both as today's date. For 'this week' use the Monday "
            "date as date_from and today as date_to. Only fall back to 'days' when "
            "the user asks for a rolling window like 'last 7 days'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google_ads", "microsoft_ads", "all"],
                    "description": "Platform to filter by, or 'all' for every platform.",
                },
                "days": {
                    "type": "integer",
                    "description": "Rolling lookback in days. Only use when no specific date is given.",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (Pacific time). Use for specific day or range queries.",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (Pacific time). Set equal to date_from for a single day.",
                },
            },
        },
    },
    {
        "name": "get_today_metrics",
        "description": (
            "Get live today-only spend, impressions, clicks, landing page views, "
            "and pixel conversions for all active Meta campaigns. Pulls directly "
            "from the Meta API."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_budget_status",
        "description": (
            "Check today's spend vs the $250 daily soft cap and this week's "
            "cumulative spend vs the $1,000 weekly ceiling."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_reports",
        "description": "Retrieve the most recent AI-generated performance reports.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {
                    "type": "integer",
                    "description": "Number of reports to retrieve. Default: 3.",
                },
            },
        },
    },
    {
        "name": "run_meta_sync",
        "description": (
            "Pull the latest campaign performance data from the Meta Marketing API "
            "into the local database. Run this before querying metrics if you need "
            "up-to-the-minute data."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_optimizer",
        "description": (
            "Run the bid and budget optimizer. It will shift budget from "
            "under-performers to top performers, adjust bids, and pause "
            "campaigns that are burning spend without conversions."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_creative_agent",
        "description": (
            "Generate new ad copy briefs using Claude. Produces headlines, "
            "descriptions, callout extensions, and sitelinks aligned with "
            "Ridgecrest's premium positioning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service_category": {
                    "type": "string",
                    "description": (
                        "Optional service category to focus on, e.g. "
                        "'design_build', 'kitchen_remodel', 'whole_house_remodel'."
                    ),
                },
            },
        },
    },
    {
        "name": "pause_campaign",
        "description": (
            "Pause a specific campaign. Searches by name (partial match) "
            "and platform. Always confirm with the user before pausing a "
            "live campaign."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_name": {
                    "type": "string",
                    "description": "Full or partial campaign name.",
                },
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google_ads", "microsoft_ads"],
                },
            },
            "required": ["campaign_name", "platform"],
        },
    },
    {
        "name": "enable_campaign",
        "description": "Enable / resume a paused campaign by name and platform.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_name": {
                    "type": "string",
                    "description": "Full or partial campaign name.",
                },
                "platform": {
                    "type": "string",
                    "enum": ["meta", "google_ads", "microsoft_ads"],
                },
            },
            "required": ["campaign_name", "platform"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def _execute_tool(name: str, inp: dict) -> str:
    logger.info("Tool call: %s(%s)", name, json.dumps(inp)[:120])
    try:
        if name == "get_active_campaigns":
            return tool_get_active_campaigns()
        if name == "get_campaign_status":
            return tool_get_campaign_status(
                platform=inp.get("platform", "all"),
                days=inp.get("days", 7),
                date_from=inp.get("date_from"),
                date_to=inp.get("date_to"),
            )
        if name == "get_today_metrics":
            return tool_get_today_metrics()
        if name == "get_budget_status":
            return tool_get_budget_status()
        if name == "get_reports":
            return tool_get_reports(n=inp.get("n", 3))
        if name == "run_meta_sync":
            return tool_run_meta_sync()
        if name == "run_optimizer":
            return tool_run_optimizer()
        if name == "run_creative_agent":
            return tool_run_creative_agent(
                service_category=inp.get("service_category")
            )
        if name == "pause_campaign":
            return tool_pause_campaign(
                campaign_name=inp["campaign_name"],
                platform=inp["platform"],
            )
        if name == "enable_campaign":
            return tool_enable_campaign(
                campaign_name=inp["campaign_name"],
                platform=inp["platform"],
            )
        return f"Unknown tool: {name}"
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e, exc_info=True)
        return f"Tool error ({name}): {e}"


# ---------------------------------------------------------------------------
# Claude conversation loop
# ---------------------------------------------------------------------------

def _build_messages(history: list[dict]) -> list[dict]:
    """
    Convert Supabase chat_messages rows into Claude API message format.
    Only include done messages (skip pending/processing ones).
    """
    messages = []
    for row in history:
        if row["role"] in ("user", "assistant") and row["status"] == "done":
            messages.append({"role": row["role"], "content": row["content"]})
    return messages


def process_message(user_msg: dict):
    """Process one pending user message end-to-end."""
    session_id    = user_msg["session_id"]
    user_msg_id   = user_msg["id"]
    user_content  = user_msg["content"]

    logger.info("Processing session=%s msg_id=%d: %s",
                session_id, user_msg_id, user_content[:80])

    # Mark as processing so other poll cycles don't pick it up
    mark_processing(user_msg_id)

    # Load conversation history (messages before this one)
    history = fetch_history(session_id)
    messages = _build_messages(history)

    # Append the current user message as 'done' so history is consistent
    # after we respond — but send it now as the active turn
    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": user_content})

    # Agentic loop: call Claude, execute tools, repeat until end_turn
    max_turns = 10
    for turn in range(max_turns):
        with _claude.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        # Extract tool use blocks
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_uses:
            # Done — extract the text reply
            text_reply = " ".join(
                b.text for b in response.content if b.type == "text"
            ).strip()
            if not text_reply:
                text_reply = "Done."
            break

        # Execute all tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tu in tool_uses:
            result_text = _execute_tool(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result_text,
            })
        messages.append({"role": "user", "content": tool_results})
    else:
        text_reply = (
            "I ran out of turns processing your request. "
            "Please try a more specific question."
        )

    logger.info("Response for session=%s: %s", session_id, text_reply[:120])

    # Mark the current user message as done and write the response
    post_response(
        session_id=str(session_id),
        content=text_reply,
        user_message_id=user_msg_id,
        metadata={"turns": turn + 1},
    )
    db.heartbeat(AGENT_NAME, "success")


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------

def run_once() -> int:
    """Poll for pending messages and process them. Returns count processed."""
    if not INGEST_API_KEY:
        logger.warning("INGEST_API_KEY not set — skipping chat poll")
        return 0

    pending = fetch_pending_messages()
    for msg in pending:
        try:
            process_message(msg)
        except Exception as e:
            logger.error("Failed to process msg id=%s: %s", msg.get("id"), e,
                         exc_info=True)
            db.heartbeat(AGENT_NAME, "error", error=str(e))
    return len(pending)


def run() -> int:
    """Called by orchestrator on its 5-second schedule."""
    return run_once()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ridgecrest — Chat Agent")
    parser.add_argument("--loop", action="store_true",
                        help=f"Poll continuously every {POLL_INTERVAL}s")
    args = parser.parse_args()

    if args.loop:
        logger.info("Chat agent loop started (interval=%ds)", POLL_INTERVAL)
        while True:
            try:
                n = run_once()
                if n:
                    logger.info("Processed %d message(s)", n)
            except Exception as e:
                logger.error("Poll error: %s", e)
            time.sleep(POLL_INTERVAL)
    else:
        n = run_once()
        logger.info("Done — processed %d message(s)", n)
