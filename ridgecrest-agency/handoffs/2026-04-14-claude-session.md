# Session Handoff — April 14, 2026

## What Was Done This Session

### 1. Session Continuity System Built (Rule 23)
- **Problem discovered:** Claude started the session with no recollection of the past several days of work. Memory index was last updated March 28. Claude had to be told to search the entire filesystem before it found `/home/claudeuser/agent/ridgecrest-agency/` and the conversation logs.
- **Fix implemented:** Added Rule 23 to `/home/claudeuser/agent/CLAUDE.md` — mandatory session startup protocol requiring reading 6 specific files before any work.
- **Hook added:** `UserPromptSubmit` hook in `/home/claudeuser/.claude/settings.json` — fires automatically on the **first message only** of every new session. Injects: `agency_mode.txt`, `CURRENT_STATUS.md`, `ACTIVE_SESSION.md`, and the latest handoff file into Claude's context. Silent on all subsequent messages.
- **Stop hook enhanced:** Every 10 prompts, now also writes a dated `handoffs/YYYY-MM-DD-claude-session.md` AND overwrites `ACTIVE_SESSION.md`.
- **git committed** per Rule 19.

### 2. Perplexity → Claude Code Transition
- Henry decided Perplexity isn't working out and wants to go back to using Claude Code as the primary agent.
- `agency_mode.txt` still says `PERPLEXITY_CAMPAIGN_MANAGEMENT=true` at session end — **needs to be updated to false**.
- No RMA automation was turned on — still in manual mode.

### 3. Earlier This Session (Before Memory Was Found)
- Google Ads OAuth token was reconnected via new `/admin/google-connect` pages in `preview_server.py`
- Developer token for Google Ads API is still only approved for test accounts — external blocker, no code fix possible
- Explored pulling Google Ads reports via scripts — library was v23, mismatch was fixed

### 4. Security Discussion — Co-Work MCP Server (Discussion Mode Only — Not Implemented)
Henry was evaluating giving Claude Co-Work (an AI tool) access to the DigitalOcean server via MCP (Model Context Protocol) server. Session ended in discussion mode — **nothing was implemented**.

**What was discussed:**
- Root password (`hb2425hb`) was exposed in plain text in at least two AI chat sessions (Perplexity and Claude). **Recommendation: change root password via DigitalOcean dashboard.**
- DigitalOcean cloud firewall to restrict SSH to Henry's IP — recommended, safe, reversible.
- MCP server on port 3000 for Co-Work:
  - Original plan (Co-Work v1): Open port 3000 public, add Cloudflare "later" → **WRONG ORDER, rejected.**
  - Revised plan (Co-Work v2): Two-layer security:
    - Layer 1: DigitalOcean firewall rule allowing only Anthropic's IP range `160.79.104.0/21` to reach port 3000
    - Layer 2: Bearer token (randomly generated) — blocks every Anthropic user except Henry's
    - Firewall rule goes in **before** MCP server starts
  - Assessment: Plan is sound. Near-zero risk to existing services (SSH untouched, no changes to ports 8081/8080).
  - **Three things to verify before executing:**
    1. Confirm Anthropic IP range `160.79.104.0/21` is current and covers remote MCP connections (not just general Anthropic traffic)
    2. Confirm Bearer token is randomly generated (not manually chosen)
    3. Confirm exactly which tools MCP server will expose through the connection

---

## What Is Pending

1. **Update `agency_mode.txt`** — change `PERPLEXITY_CAMPAIGN_MANAGEMENT=true` to `false` to reflect transition back to Claude Code
2. **Change root password** — via DigitalOcean dashboard (not a code task, Henry does this)
3. **Co-Work MCP decision** — Henry still in discussion mode. If he decides to proceed, verify Anthropic IP range first, then implement the two-layer security plan
4. **Deploy Rule 23 to production** — dev `CLAUDE.md` has Rule 23, production `/root/agent/CLAUDE.md` needs the standard deploy command (requires sudo)
5. **Martinez removed from Meta Ads targeting** — pending from previous session (UI task)
6. **Disable automatically created assets in Google Ads** — UI task
7. **Link approved images to ad groups** — UI task
8. **Pull search terms report** — after 3-5 days of Perplexity Test One keyword data

---

## What Next Session Should Read First

1. This file (`2026-04-14-claude-session.md`)
2. `CURRENT_STATUS.md` — campaign state
3. `agency_mode.txt` — check if Perplexity flag was updated
4. `rules/AGENT_RULES.md` — 15 rules, all mandatory
5. `CLAUDE.md` Rule 23 — session continuity protocol

---

## Decisions Henry Made

1. **Perplexity is out** — switching back to Claude Code as primary agent
2. **Co-Work MCP plan is sound but not yet approved for execution** — still in discussion mode at session end
3. **Root password change** — agreed this should be done but not yet done (DigitalOcean dashboard task)
4. **The two-layer security model (IP filter + Bearer token) is the right approach** — if MCP is implemented, this is the design

---

## Campaign State at Session End

### Google Ads
- **Perplexity Test One** (ID: 23734851306) — LIVE, $200/day, 246 broad match keywords, 7 ad groups, 7-day schedule
- **Custom Home Builder | Google Search** (Claude's original) — REMOVED April 11

### Meta
- **[PX] Home Remodel - Hook 10** (ID: 6969359384893) — LIVE, $30/day
- **[PX] Custom Home Design-Build - Hook 3** (ID: 6969359386493) — LIVE, $30/day
- Martinez still in targeting (pending removal)

### RMA System
- `CAMPAIGN_AUTOMATION_ENABLED=false` — manual mode
- `PERPLEXITY_CAMPAIGN_MANAGEMENT=true` — **needs to be changed to false**
- Orchestrator daemon running but automation is paused
