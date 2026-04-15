# Recovery Procedure — Ridgecrest Designs Website

## Last Verified Working State
- **Tag:** VERIFIED-WORKING-2026-04-14
- **Branch:** production-verified
- **Verified by:** Henry (visual) + Perplexity (automated checks)
- **Date:** April 14, 2026 6:20 PM PDT

## Emergency Recovery (one command)
```bash
cd /home/claudeuser/agent
git checkout ridgecrest-audit && git reset --hard production-verified
# Then restart preview server
```

## Rules for Claude Code

### NEVER DO:
1. Never switch the live server to master or any other branch
2. Never merge ridgecrest-audit into master or vice versa
3. Never cherry-pick commits between branches
4. Never force-push or delete branches/tags
5. Never delete the production-verified branch or VERIFIED-WORKING tags

### ALWAYS DO:
1. Work on ridgecrest-audit only
2. Create a PRE commit before any risky change
3. For experimental work: create a feature branch off ridgecrest-audit, switch back when done
4. If something breaks and you can't fix it: git reset --hard production-verified
5. After completing a feature: notify Henry/Perplexity for verification before moving on

### How Verified States Get Created
1. Claude completes work and reports done
2. Perplexity runs automated checks (all pages 200, key features working)
3. Henry visually confirms the site looks correct
4. Perplexity creates a new VERIFIED-WORKING-[date] tag and updates production-verified branch
5. Only Perplexity creates verified tags — Claude does not

### Available Safety Points
- VERIFIED-WORKING-2026-04-14 — Full site with all Apr 12-14 work including gallery fixes
- SAFE-APR14-PRE-GALLERY (8a1458e) — Clean state before gallery experiments
- SAFE-APR14-FULL-TIP — Same as VERIFIED-WORKING-2026-04-14
- safe-backup-apr14-6pm-pdt branch — Frozen copy of ridgecrest-audit tip
