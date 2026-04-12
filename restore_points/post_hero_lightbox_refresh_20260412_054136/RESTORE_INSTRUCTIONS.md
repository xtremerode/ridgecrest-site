# Restore Point — Post Hero/Lightbox/Refresh Fix
Created: 2026-04-12 05:41:36

## What this restores
- Full PostgreSQL database (all tables, all data)
- All 32 rendered HTML pages (preview/*.html)
- img_dims.json (image dimension cache)
- Manifest of all 2615 WebP files with sizes and timestamps

## Changes included since last restore point (pre_og_relative_20260411_221147)
- All 18 project page heroes → _1920w WebP variant (fixes GPU downscale artifacts)
- DB: pages.hero_image and portfolio_projects.hero_img both updated to _1920w
- Lightbox fix: iframe stays at PREVIEW_H, outer scroll synced via contentWindow.scrollTo()
- Mobile hero void fix: _updateViewportFix uses device-appropriate heights (phone=844, ipad=1024)
- Undo/Redo: global stack, clean labels, redo endpoint with after_data
- WebP quality: all settings standardized to 92
- Admin refresh: sessionStorage restores last-viewed page

## What this does NOT restore
- WebP image files themselves (use manifest to verify state)
- Python, JS, CSS code files (use git: commit f3a5458)

## To restore the database
```bash
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent < /home/claudeuser/agent/restore_points/post_hero_lightbox_refresh_20260412_054136/db_full.sql
```

## To restore HTML pages
```bash
cp /home/claudeuser/agent/restore_points/post_hero_lightbox_refresh_20260412_054136/*.html /home/claudeuser/agent/preview/
```

## To restore img_dims.json
```bash
cp /home/claudeuser/agent/restore_points/post_hero_lightbox_refresh_20260412_054136/img_dims.json /home/claudeuser/agent/preview/assets/img_dims.json
```

## To verify image files against manifest
```bash
find /home/claudeuser/agent/preview/assets/images-opt -maxdepth 1 -name "*.webp" \
  -exec stat --format="%n %s %Y" {} \; | sort > /tmp/current_manifest.txt
diff /home/claudeuser/agent/restore_points/post_hero_lightbox_refresh_20260412_054136/image_manifest.txt /tmp/current_manifest.txt
```

## Git reference
Branch: ridgecrest-audit
Commit: f3a5458
