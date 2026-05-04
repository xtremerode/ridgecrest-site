# Session Handoff — May 4, 2026

## What Was Found at Session Start
- Branch: `ridgecrest-audit`, all features locked
- Session picked up mid-execution from a previous context — proxy fix for start-a-project iframe had been attempted but the guardrail was halted at Gate 4 (pre-commit QA), and start-a-project.html had been accidentally reverted by a failed `git stash pop`

## What Was Done This Session

### Start-a-Project Iframe — Investigated, Proxy Attempted, Reverted to Pre-Session State

**Root cause confirmed (Playwright CDP diagnostics):**
Base44's `ResizeObserver` observes `#root > firstElementChild` which is a NEW DOM node per wizard step. By Step 2, the observer is orphaned — it watches a detached node and sends ZERO postMessages. Step 2 content is ~1029px but Base44 never reports it.

**Proxy fix attempted:** Served Base44 through `/booking-proxy` in `preview_server.py` — rewrites asset URLs same-origin, injects a 300ms polling height script. Passed all guardrail gates BUT Base44's React Router saw `/booking-proxy` as its URL path and showed a 404 "page not found" inside the iframe.

**Final state — reverted to pre-session `019b7f2` state:**
- `start-a-project.html`: `src="https://elevate-scheduling-6b2fdec8.base44.app/"`, CSS `height: 600px`, `MIN_H=500`, no MAX_H
- Steps 1 and 2 resize naturally (no extra whitespace)
- Step 3 (Your Details) will show a scrollbar — Base44 sends no resize message for it
- Henry accepted this tradeoff: "I would rather have the two smaller frames with the scroll bar on the third"
- Proxy routes remain in `preview_server.py` as dead code (harmless)

**Guardrail improvements made this session (committed, permanent):**
1. `CLAUDE.md` — "Measure Before Fix — MANDATORY" rule added
2. `hooks/detect_analysis_request.sh` — bug-report keywords added ("not working", "broken", "scroll bar", "you didn't fix", etc.)
3. `.claude/settings.local.json` — `log_file_read.sh` now also fires on Bash tool (so running a diagnostic satisfies the research gate)

## Open Items Carrying Forward

### START-A-PROJECT IFRAME (DEFERRED — Henry acknowledged)
- Step 3 "Your Details" has a scrollbar because Base44 sends no resize message for that step
- Root cause: Base44 ResizeObserver orphaned on Step2 (new DOM node per step)
- Proxy approach failed: React Router 404s on non-root paths
- Possible future fix: configure Base44 app to use hash routing, OR contact Base44 support, OR iframe height override for Step 3 specifically
- **Do not attempt again without a new plan** — three failed attempts this session

### All other open items from prior session unchanged:
- 3 missing Wix CDN images (Henry must download + upload via bat script)
- Continue render review queue (62 cards)
- `_NAV_PREFETCH_SLUGS` bug in `preview_server.py` line 298
- `set-version` doesn't update static pages
- pre-commit hook python path (system vs venv)

## Commit Trail This Session
- `669738d` WIP baseline (proxy attempt start)
- `125124660` Proxy fix — passed guardrail but Base44 404d at runtime
- `cf932d7` Reverted to MIN_H=1080 (no whitespace issue but Step 2 oversized)
- `fb8fe06` **FINAL** — Reverted to pre-session 019b7f2 state (600px, MIN_H=500, direct Base44 URL)

## Branch / Infrastructure
- Branch: `ridgecrest-audit`
- Last commit: `fb8fe06`
- All features: locked
- Server: 147.182.242.54:8081
