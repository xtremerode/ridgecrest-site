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

### 4. Co-Work MCP Server Security Research (Discussion Mode Only — Nothing Implemented)

Full deep research conducted on Co-Work server access options. Plan evolved through 4 iterations.

**Research verified:**
- Anthropic outbound IP range `160.79.104.0/21` — confirmed correct on official docs
- Co-Work remote MCP connector **requires HTTPS** — plain HTTP rejected at API schema level
- `claude mcp serve` is stdio-only — `--transport sse` flag does not exist on it (closed as not planned)
- `--transport sse` on mcp-proxy IS valid — mcp-proxy bridges stdio to SSE for network
- mcp-proxy v0.11.0, Bearer token env var: `API_ACCESS_TOKEN` — confirmed correct

**Final resolution — local SSH MCP server (approved, not yet executed):**
- `claude-ssh-server` npm package runs on Henry's Windows laptop — NOT on the server
- Local stdio transport — no HTTPS, no domain, no cert, no port 3000, zero server changes
- Co-Work talks to it locally via stdio; it SSH's to server exactly like Perplexity did
- **Prerequisite:** Verify `%APPDATA%\Claude\claude_desktop_config.json` exists (confirms Co-Work = Claude Desktop)
- **Three steps when ready:** `npm install -g claude-ssh-server` → add config JSON → restart Co-Work

**Rejected approaches:**
- Port 3000 + Cloudflare Tunnel — too many moving parts
- Port 3000 + nginx/Let's Encrypt — requires domain, mixing concerns
- Using ridgecrestdesigns.com domain — wrong, keep business and infrastructure separate
- No Cloudflare Tunnel — Henry's decision, data concerns

**SSH firewall (DigitalOcean dashboard) still recommended independently:**
- Restrict port 22 to Henry's IP only — safe, reversible, no SSH config touched
- Completely separate from Co-Work setup

---

## Pending Actions (Priority Order)

1. **Co-Work SSH setup** — verify `%APPDATA%\Claude\claude_desktop_config.json` exists, then 3 steps on laptop (no server changes)
2. **DigitalOcean SSH firewall** — restrict port 22 to Henry's IP via dashboard (Henry's task)
3. **Deploy Rule 23 to production** — run standard deploy command from CLAUDE.md §23 (requires sudo)
4. **Remove Martinez from Meta Ads targeting** — UI task (both ToF and retargeting campaigns)
5. **Disable auto-created assets in Google Ads** — UI task
6. **Link approved images to ad groups** — UI task
7. **Pull search terms report** — after 3-5 days of Perplexity Test One keyword data
8. **Change root password** — DigitalOcean dashboard (Henry's task, low urgency)

---

## What Next Session Should Read First

1. This file (`2026-04-14-claude-session.md`)
2. `CURRENT_STATUS.md` — campaign state
3. `agency_mode.txt` — Perplexity flag now false ✅
4. Pick up with Co-Work SSH setup — check `%APPDATA%\Claude\claude_desktop_config.json` first

---

## Decisions Henry Made

1. **Perplexity is permanently out** — Claude Code is primary agent
2. **No Cloudflare Tunnel** — data concerns, too many moving parts
3. **Local SSH MCP server (`claude-ssh-server`) is the right approach** — approved pending verification
4. **ridgecrestdesigns.com not to be used for infrastructure** — keep business and backend separate
5. **DigitalOcean SSH firewall is worth doing independently** — agreed

---

## Campaign State at Session End

### Google Ads
- **Perplexity Test One** (ID: 23734851306) — LIVE, $200/day, 246 broad match keywords, 7 ad groups
- **Custom Home Builder | Google Search** (Claude's original) — REMOVED April 11

### Meta
- **[PX] Top of Funnel - Video Views** (ID: 6970213843893) — created April 11, $0/day
- **[PX] Retargeting - Conversions** (ID: 6970214205893) — created April 11, $0/day
- **[PX] Home Remodel - Hook 10** (ID: 6969359384893) — PAUSED April 11
- **[PX] Custom Home Design-Build - Hook 3** (ID: 6969359386493) — PAUSED April 11
- Martinez still in targeting — pending removal

### RMA System
- `CAMPAIGN_AUTOMATION_ENABLED=false` — manual mode
- `PERPLEXITY_CAMPAIGN_MANAGEMENT=false` — updated this session ✅
- Orchestrator running, automation paused
