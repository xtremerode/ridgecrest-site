# Restore Point — Kitchen Card _1920w Fix
Created: 2026-04-12 06:12:46

## What this restores
- Full PostgreSQL database (all tables, all data)
- All 32 rendered HTML pages (preview/*.html)
- img_dims.json (image dimension cache)
- Manifest of all 2615 WebP files with sizes and timestamps

## Changes included since last restore point (post_card960w_fix_20260412_055930)
- card_settings DB: service-kitchen-remodels (home + portfolio) switched from _960w → _1920w
  Reason: _960w for Napa kitchen (ff5b18_38c7317e1d4b4773ab0a16ed48332f31) was only 54KB
  causing visible compression artifacts. _1920w is 209KB (4× more data).
- CLAUDE.md: Added Rule 21 — Execution Mode Control (discussion vs execution)

## What this does NOT restore
- WebP image files themselves (use manifest to verify state)
- Python, JS, CSS code files (use git)

## To restore the database
```bash
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent < /home/claudeuser/agent/restore_points/post_kitchen_card_fix_20260412_061246/db_full.sql
```

## To restore HTML pages
```bash
cp /home/claudeuser/agent/restore_points/post_kitchen_card_fix_20260412_061246/*.html /home/claudeuser/agent/preview/
```

## Git reference
Branch: ridgecrest-audit
Commit: e47b668 (Rule 21 CLAUDE.md)
