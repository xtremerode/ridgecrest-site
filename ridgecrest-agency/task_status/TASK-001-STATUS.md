# [RMA] TASK-001-STATUS: Command Center Inventory and Integration Assessment
## Assigned by: Perplexity (Manager)
## Completed by: Claude Code / Ridgecrest Marketing Agency
## Date: April 11, 2026
## Status: COMPLETE

---

## 1. What Exists in the Command Center

The Command Center is a web application built in Lovable, hosted as a Lovable project. It is a single-page dashboard for Henry to monitor and control the Ridgecrest marketing automation system.

### Pages
- **Overview (home page)** — primary view; contains all current functionality

### Components and Features (confirmed from session discussion)
- **Reporting Active** toggle — on/off pill button; controls whether the agent reporting pipeline is running
- **Campaign Management** toggle — previously a single on/off pill; NOW REPLACED (per session April 11, 2026) with two separate pills:
  - **RMA** pill — controls Claude / Ridgecrest Marketing Agency campaign management
  - **PX** pill — controls Perplexity campaign management
- Mutual exclusion enforced: turning either RMA or PX on automatically turns the other off (server-side)

### Data Displayed
- Current automation state (which agent is active)
- Reporting status

### User Actions Available
- Toggle RMA campaign management on/off
- Toggle PX campaign management on/off
- Toggle reporting on/off

---

## 2. What It Connects To

### DigitalOcean Server (147.182.242.54:8081)
Yes — confirmed. The Command Center calls:

**GET** (via Supabase Edge Function `automation-toggle`):
- `http://147.182.242.54:8081/agency/file?path=agency_mode.txt`
- Auth: `Authorization: Bearer giPauDx1ZjKAFgXB-IIGlaPBseL2uLuP319sGLTJGY0`
- Returns: `CAMPAIGN_AUTOMATION_ENABLED=true/false` and `PERPLEXITY_CAMPAIGN_MANAGEMENT=true/false`

**POST** (via Supabase Edge Function `automation-toggle`):
- `http://147.182.242.54:8081/admin/api/system/automation`
- Auth: `X-Ingest-Key: RCM-2026-xK9mP3vL8nQ5wJ2hY7tF4dA6sE1uB0cD`
- Body: `{ "agent": "rma"|"px", "enabled": true|false }`

**Legacy endpoints also available on server (from prior build, callable with X-Ingest-Key):**
- `GET /admin/api/agents/status` — returns `agents_enabled`, `campaign_management_enabled`
- `POST /admin/api/agents/management-toggle`
- `POST /admin/api/agents/toggle`

### Supabase
- Supabase Edge Functions are used as a proxy layer between Lovable frontend and the DigitalOcean server
- Secrets stored: `AUTOMATION_BEARER_TOKEN`, `AGENTS_API_KEY` (ingest key)
- This keeps API keys server-side and out of the browser

### Google Ads
- Not connected directly. No Google Ads API calls from the Command Center.

### Meta Ads
- Not connected directly. No Meta API calls from the Command Center.

### Authentication
- No user login on the Command Center — it is an internal tool, no auth UI
- API security handled via bearer token and ingest key (server-side in Supabase Edge Functions)

---

## 3. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend framework | React (Lovable generates React) |
| Hosting | Lovable (built-in hosting) |
| Backend proxy | Supabase Edge Functions (Deno/TypeScript) |
| Database | Supabase (available but not confirmed in active use for Command Center) |
| State management | React Query (useQuery + useMutation pattern confirmed from PR description) |
| Styling | Tailwind CSS (standard in Lovable) |
| API target | DigitalOcean server at 147.182.242.54:8081 |

---

## 4. What Can Be Reused

### Directly Reusable
- **Pill toggle component** — the RMA/PX toggle pattern is clean, generic, and reusable for any on/off control. Works for any agent or platform toggle.
- **Supabase Edge Function proxy pattern** — the `automation-toggle` edge function is a clean template for any server call that needs to keep keys secret. Can be cloned for Google Ads API calls, Meta API calls, reporting fetches.
- **React Query pattern** — `useQuery` for state + `useMutation` + `invalidateQueries` for optimistic updates is the right pattern for a live dashboard. Reuse for all data panels.

### Reusable With Modification
- **Overview page layout** — currently just toggles; the layout shell can hold performance panels, lead counts, spend summaries
- **Agency file read pattern** — reading `agency_mode.txt` via the file API is a template for reading any agency knowledge base file (CURRENT_STATUS.md, campaign metrics, reports)

### Would Need to Be Built Fresh
- Campaign performance panels (impressions, clicks, conversions, spend by platform)
- Lead tracking display
- Plain-English report rendering
- Keyword performance table
- Alert/notification system
- Multi-client support (for the turnkey product vision)

---

## 5. What Is Missing (vs. Business Plan)

Based on `competitors/turnkey_app_business_plan_2026_04_11.md`:

| Feature Required by Business Plan | Status |
|-----------------------------------|--------|
| Plain-English performance reports ("Your kitchen ads got 12 clicks at $18") | MISSING |
| Campaign builder UI (industry + zip codes + services → auto-build) | MISSING |
| Keyword research display and approval flow | MISSING |
| Negative keyword management | MISSING |
| Search term report review | MISSING |
| Ad schedule controls | MISSING |
| Budget management controls | MISSING |
| Geo-targeting display and editor | MISSING |
| Multi-platform view (Google + Meta + Microsoft) | MISSING |
| Alert system (zero impressions, overspend, etc.) | MISSING |
| Golf course neighborhood identification tool | MISSING |
| Multi-client / white-label support | MISSING |
| Onboarding flow (answer 5 questions → campaign built) | MISSING |

### Summary Gap Assessment
The Command Center today is a **control panel stub** — it has the toggle infrastructure and the right architectural patterns (React Query, Supabase proxy, agency file API). It does not yet display any campaign data or provide any campaign management UI. The foundation is correct and reusable. Everything in the business plan beyond on/off toggles needs to be built.

---

## Next Steps (for Perplexity to assign)
1. Decide which business plan feature to build first
2. Confirm whether to keep Lovable hosting or migrate to a standalone React app as complexity grows
3. Define the data contract between the DigitalOcean server and the Command Center for performance metrics

