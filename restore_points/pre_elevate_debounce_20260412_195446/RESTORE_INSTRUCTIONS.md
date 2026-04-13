# Restore Point — Pre Elevate Debounce Fix
Created: 2026-04-12 19:54:46

## What this restores
- Full PostgreSQL database (all tables, all data)
- All 104 HTML pages (preview/*.html + preview/services/*.html)
- img_dims.json (image dimension cache)
- Manifest of 2639 WebP files with sizes and timestamps

## State at this point
- iframe auto-resize Back button fix: working (window.blur collapses immediately)
- All Start a Project CTAs unified to start-a-project.html across all pages
- /book server redirect in place

## Why this restore point exists
About to attempt debounce improvement to window.blur handler in
start-a-project.html — reduces page jump on card clicks inside Elevate form.
Reverting restores immediate-collapse behavior (Back button still works, but
card clicks cause visible jump).

## What this does NOT restore
- Python, JS, CSS code files — use git (branch: ridgecrest-audit, commit: cd83464)

## To restore the database
```bash
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent < /home/claudeuser/agent/restore_points/pre_elevate_debounce_20260412_195446/db_full.sql
```

## To restore HTML pages
```bash
cp /home/claudeuser/agent/restore_points/pre_elevate_debounce_20260412_195446/*.html /home/claudeuser/agent/preview/
```

## To revert start-a-project.html via git
```bash
cd /home/claudeuser/agent && git checkout cd83464 -- preview/start-a-project.html
```

## Git reference
Branch: ridgecrest-audit
Commit: cd83464
