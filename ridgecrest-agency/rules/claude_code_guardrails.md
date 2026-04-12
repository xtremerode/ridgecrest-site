# Rule 15: Claude Code Safety Guardrails
## Added: April 11, 2026

### Non-Negotiable

Every prompt sent to Claude Code MUST include the following safety guardrails:

1. **Do NOT delete existing files** unless explicitly instructed by Henry or by a Perplexity task that specifies deletion
2. **Do NOT modify existing code** unless the task specifically says to modify it
3. **Do NOT redeploy or overwrite live applications** — the Command Center, website, or any other live service
4. **Test changes in isolation** before applying to production
5. **Back up any file before modifying it** — create a copy with _backup suffix before making changes
6. **Do NOT touch campaigns without [RMA] prefix** — Claude's prefix is [RMA], Perplexity's is [PX]
7. **Do NOT modify server API endpoints** — the file API at 147.182.242.54:8081 is shared infrastructure
8. **Read all rules/ files before every task** — no exceptions

### Standard Footer for All Claude Code Prompts
The following must be appended to every prompt Perplexity sends to Claude Code:

"SAFETY: Do not delete existing files. Do not modify existing code unless this task explicitly instructs it. Do not redeploy or overwrite live applications. Back up any file before modifying. Read all rules/ files before starting. Report what you plan to do before doing it."
