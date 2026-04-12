# Ridgecrest Designs — Agency Knowledge Base

This is the **single source of truth** for all AI agents working on Ridgecrest Designs advertising campaigns. Every agent — Claude, Perplexity, GPT, Codex, or any future agent — must read from and write to this directory to stay in sync.

---

## Folder Structure

| Folder | Purpose |
|---|---|
| `campaigns/` | Campaign configs, build scripts, diagnostic results, campaign-level notes |
| `keywords/` | Keyword lists (positives and negatives), organized by theme and match type |
| `locations/` | Zip code target lists, exclusion lists, geographic targeting notes |
| `competitors/` | Competitor research outputs, SERP analysis, ad copy samples |
| `rules/` | Agent rules, guardrails, and operating procedures (`AGENT_RULES.md`) |
| `ads/` | Ad copy: headlines, descriptions, RSA drafts, callout/sitelink copy |
| `performance/` | Performance logs, optimization notes, weekly spend summaries |
| `handoffs/` | Session summaries written by each AI agent before ending a session |
| `scripts/` | All Google Ads Scripts (Steps 1-7, status report, enable ad group, etc.) |
| `assets/` | Sitelink URLs, callout text values, structured snippet values |

---

## Root Files

| File | Purpose |
|---|---|
| `README.md` | This file — directory overview and conventions |
| `CURRENT_STATUS.md` | Always overwritten (never appended) — exact current campaign state |
| `CAMPAIGN_IDS.md` | Hardcoded account, campaign, and ad group IDs — read-only reference |
| `API_TOKEN.txt` | Bearer token for the file API on port 8765 — keep private |

---

## Protocol for AI Agents

1. **Read `CURRENT_STATUS.md` first** — this is the most up-to-date state of all campaigns.
2. **Read `CAMPAIGN_IDS.md`** — never guess account or campaign IDs.
3. **Read `rules/AGENT_RULES.md`** — non-negotiable operating rules.
4. **Write your session summary to `handoffs/`** before ending any session.
5. **Overwrite `CURRENT_STATUS.md`** with the new current state before ending any session.

---

## File API

A persistent HTTP API runs on port **8765** on this server, allowing any AI agent to read and write files programmatically.

- `POST /upload` — upload a file (requires `folder`, `filename`, `content` in JSON body)
- `GET /file?path=<relative-path>` — read any file by relative path
- Auth: `Authorization: Bearer <token>` (token in `API_TOKEN.txt`)

---

*Last updated: 2026-04-10*
