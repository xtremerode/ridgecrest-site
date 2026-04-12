# Restore Point — Pre Image Re-fetch
Created: 2026-04-10 04:27:50

## What this restores
- Full PostgreSQL database (all tables, all data)
- All 32 rendered HTML pages (preview/*.html)
- img_dims.json (image dimension cache)
- Manifest of all 2609 WebP files with sizes and timestamps

## What this does NOT restore
- The WebP image files themselves (515MB — use manifest to verify state)
- If images are overwritten during re-fetch and need restoring, they must be re-downloaded from Wix

## To restore the database
```bash
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
PGPASSWORD=StrongPass123! psql -h 127.0.0.1 -U agent_user -d marketing_agent < /home/claudeuser/agent/restore_points/pre_image_refetch_20260410_042750/db_full.sql
```

## To restore HTML pages
```bash
cp /home/claudeuser/agent/restore_points/pre_image_refetch_20260410_042750/*.html /home/claudeuser/agent/preview/
```

## To restore img_dims.json
```bash
cp /home/claudeuser/agent/restore_points/pre_image_refetch_20260410_042750/img_dims.json /home/claudeuser/agent/preview/assets/img_dims.json
```

## To verify image files against manifest
```bash
find /home/claudeuser/agent/preview/assets/images-opt -maxdepth 1 -name "*.webp" \
  -exec stat --format="%n %s %Y" {} \; | sort > /tmp/current_manifest.txt
diff /home/claudeuser/agent/restore_points/pre_image_refetch_20260410_042750/image_manifest.txt /tmp/current_manifest.txt
```
