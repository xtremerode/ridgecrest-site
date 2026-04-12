# Restore Point — Card _960w Moiré Fix
Created: 2026-04-12 05:59:30

## What this restores
- Full PostgreSQL database (all tables, all data)
- All 32 rendered HTML pages (preview/*.html)
- img_dims.json (image dimension cache)
- Manifest of all 2615 WebP files with sizes and timestamps

## Changes included since last restore point (post_hero_lightbox_refresh_20260412_054136)
- card_settings DB: 9 CSS background cards updated from _mv2.webp → _mv2_960w.webp
  - allprojects: allprojects-danville-dream, allprojects-sierra-mountain-ranch
  - home: service-bathroom-remodels, service-kitchen-remodels, service-whole-house-remodels, diff-visual-bottom
  - portfolio: service-bathroom-remodels, service-kitchen-remodels, service-whole-house-remodels
- pages DB: portfolio.hero_image updated from _mv2.webp → _mv2_960w.webp (Sierra Mountain Ranch featured card)
- preview_server.py: Added _portfolio_thumb_src() helper + docstring warning on _portfolio_img_src()
- CLAUDE.md: Added Section 20 — Three-tier image serving rules (base/1920w/960w)
- All static HTML card backgrounds updated to _960w across: portfolio.html, allprojects.html,
  bathroom-remodels.html, kitchen-remodels.html, whole-house-remodels.html, custom-homes.html, main.css

## What this does NOT restore
- WebP image files themselves (use manifest to verify state)
- Python, JS, CSS code files (use git: commit 7105f06 or later)

## To restore the database
```bash
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent < /home/claudeuser/agent/restore_points/post_card960w_fix_20260412_055930/db_full.sql
```

## To restore HTML pages
```bash
cp /home/claudeuser/agent/restore_points/post_card960w_fix_20260412_055930/*.html /home/claudeuser/agent/preview/
```

## To restore img_dims.json
```bash
cp /home/claudeuser/agent/restore_points/post_card960w_fix_20260412_055930/img_dims.json /home/claudeuser/agent/preview/assets/img_dims.json
```

## Git reference
Branch: ridgecrest-audit
Commit: 7105f06 (PRE commit — code changes before this DB fix)
