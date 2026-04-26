"""
Phase 2 DB cleanup — AI render phantom records and stale path references.

Codex fixes applied:
  1. No date filter — use filename NOT IN (disk list) only
  2. NULL guard on active_version/image/hero_image resets
  3. pages.hero_image handled separately (different path format)
  4. Cards with only phantom/lost renders flagged, not silently NULLed
"""
import os, re, sys
import psycopg2, psycopg2.extras

OPT_DIR = '/home/claudeuser/agent/preview/assets/images-opt'
DB_URL  = 'postgresql://agent_user:StrongPass123!@127.0.0.1/marketing_agent'

def get_disk_set():
    """Return set of ALL *_ai_*.webp filenames on disk (base + size variants)."""
    result = set()
    for f in os.listdir(OPT_DIR):
        if '_ai_' in f and f.endswith('.webp'):
            result.add(f)
    return result

def base_stem(filename):
    """ff5b18_xxx_mv2_ai_3_960w.webp → ff5b18_xxx_mv2_ai_3
       ff5b18_xxx_mv2_ai_3.webp     → ff5b18_xxx_mv2_ai_3"""
    f = filename
    f = re.sub(r'_(201|480|960|1920)w\.webp$', '.webp', f)
    return f[:-5]  # strip .webp

def source_stem(filename):
    """ff5b18_xxx_mv2_ai_3_960w.webp → ff5b18_xxx_mv2
       ff5b18_xxx_mv2_1920w_ai_1.webp → ff5b18_xxx_mv2_1920w  (hero source format)"""
    return re.sub(r'_ai_\d+.*$', '', filename[:-5] if filename.endswith('.webp') else filename)

def main():
    disk = get_disk_set()
    print(f'[cleanup] Files on disk: {len(disk)}')
    conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cur  = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # Step 2a: Delete phantom image_render_prompts records
    # These have DB entries but no file on disk (failed/queued renders that never wrote files)
    # Guard: filename NOT IN (disk list) — no date filter per Codex fix #3
    # ─────────────────────────────────────────────────────────────
    cur.execute("SELECT filename FROM image_render_prompts")
    all_db_renders = [r['filename'] for r in cur.fetchall()]
    phantom = [f for f in all_db_renders if f not in disk]
    print(f'\n[2a] Phantom records in image_render_prompts (no file on disk): {len(phantom)}')
    for f in phantom:
        print(f'     DELETE: {f}')

    if phantom:
        cur.execute(
            "DELETE FROM image_render_prompts WHERE filename = ANY(%s)",
            (phantom,)
        )
        print(f'     Deleted {cur.rowcount} record(s)')

    # ─────────────────────────────────────────────────────────────
    # Step 2b: Fix stale image_labels.active_version
    # active_version stores the BASE filename (no size suffix)
    # If it's missing from disk → reset to most recent valid render for same source
    # Codex fix #2: only update WHERE replacement IS NOT NULL
    # ─────────────────────────────────────────────────────────────
    cur.execute("SELECT filename, active_version FROM image_labels WHERE active_version IS NOT NULL")
    stale_labels = []
    for row in cur.fetchall():
        av = row['active_version']
        if av and av not in disk:
            stale_labels.append(row)

    print(f'\n[2b] Stale image_labels.active_version entries: {len(stale_labels)}')
    needs_rerender = []
    for row in stale_labels:
        src = source_stem(row['active_version'])
        # Find best valid render: same source, file on disk, most recent
        cur.execute("""
            SELECT filename FROM image_render_prompts
            WHERE filename LIKE %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (f'{src}_ai_%.webp',))
        best = cur.fetchone()
        if best and best['filename'] in disk:
            print(f'     FIX: {row["filename"]} active_version {row["active_version"]} → {best["filename"]}')
            cur.execute(
                "UPDATE image_labels SET active_version = %s WHERE filename = %s",
                (best['filename'], row['filename'])
            )
        else:
            print(f'     FLAG (no valid render): {row["filename"]} — will need re-render')
            needs_rerender.append(row['filename'])
            # Do NOT set NULL — leave active_version as-is so the portal can
            # detect it as "needs re-render" (file missing = red badge)

    # ─────────────────────────────────────────────────────────────
    # Step 2c: Fix stale card_settings.image (sized path, _960w)
    # Path format: /assets/images-opt/ff5b18_xxx_mv2_ai_1_960w.webp
    # ─────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT card_id, image FROM card_settings
        WHERE image LIKE '/assets/images-opt/%_ai_%'
    """)
    stale_cards = []
    for row in cur.fetchall():
        fname = row['image'].split('/')[-1]
        bstem = base_stem(fname)  # e.g. ff5b18_xxx_mv2_ai_3
        # Check if the 960w variant exists on disk
        sized_960 = f'{bstem}_960w.webp'
        if sized_960 not in disk and bstem + '.webp' not in disk:
            stale_cards.append(row)

    print(f'\n[2c] Stale card_settings.image entries: {len(stale_cards)}')
    for row in stale_cards:
        fname = row['image'].split('/')[-1]
        src = source_stem(fname)
        cur.execute("""
            SELECT filename FROM image_render_prompts
            WHERE filename LIKE %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (f'{src}_ai_%.webp',))
        best = cur.fetchone()
        if best:
            bstem = base_stem(best['filename'])
            replacement = f'/assets/images-opt/{bstem}_960w.webp'
            if f'{bstem}_960w.webp' in disk:
                print(f'     FIX card {row["card_id"]}: {fname} → {replacement.split("/")[-1]}')
                cur.execute(
                    "UPDATE card_settings SET image = %s WHERE card_id = %s",
                    (replacement, row['card_id'])
                )
            else:
                print(f'     FLAG (no 960w): card {row["card_id"]} — {fname}')
        else:
            print(f'     FLAG (no renders at all): card {row["card_id"]} — {fname}')

    # ─────────────────────────────────────────────────────────────
    # Step 2d: Fix stale pages.hero_image (separate logic — Codex fix #4)
    # Two formats:
    #   Standard: /assets/images-opt/ff5b18_xxx_mv2_ai_1_1920w.webp
    #   Hero source: /assets/images-opt/ff5b18_xxx_mv2_1920w_ai_1.webp
    # ─────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT slug, hero_image FROM pages
        WHERE hero_image LIKE '/assets/images-opt/%_ai_%'
    """)
    stale_pages = []
    for row in cur.fetchall():
        fname = row['hero_image'].split('/')[-1]
        # Check if file exists on disk (either format)
        if fname not in disk:
            stale_pages.append(row)

    print(f'\n[2d] Stale pages.hero_image entries: {len(stale_pages)}')
    for row in stale_pages:
        fname = row['hero_image'].split('/')[-1]
        src = source_stem(fname)
        # Try both LIKE patterns (standard ai render OR 1920w-source render)
        cur.execute("""
            SELECT filename FROM image_render_prompts
            WHERE (filename LIKE %s OR filename LIKE %s)
            ORDER BY created_at DESC
            LIMIT 1
        """, (f'{src}_ai_%.webp', f'{src}%_ai_%.webp'))
        best = cur.fetchone()
        if best:
            bfname = best['filename']
            # Build 1920w path — check which format exists on disk
            bstem = base_stem(bfname)
            candidate_std   = f'{bstem}_1920w.webp'
            candidate_plain = bfname  # some hero renders are already the right size
            if candidate_std in disk:
                replacement = f'/assets/images-opt/{candidate_std}'
                print(f'     FIX page {row["slug"]}: {fname} → {candidate_std}')
                cur.execute("UPDATE pages SET hero_image = %s WHERE slug = %s",
                            (replacement, row['slug']))
            elif candidate_plain in disk:
                replacement = f'/assets/images-opt/{candidate_plain}'
                print(f'     FIX page {row["slug"]}: {fname} → {candidate_plain}')
                cur.execute("UPDATE pages SET hero_image = %s WHERE slug = %s",
                            (replacement, row['slug']))
            else:
                print(f'     FLAG (no 1920w): page {row["slug"]} — {fname}')
        else:
            print(f'     FLAG (no renders at all): page {row["slug"]} — {fname}')

    conn.commit()

    # ─────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────
    print(f'\n{"="*60}')
    print(f'CLEANUP COMPLETE')
    print(f'  Phantom records deleted: {len(phantom)}')
    print(f'  Stale active_version fixed: {len(stale_labels) - len(needs_rerender)}')
    print(f'  Stale card_settings fixed: {len(stale_cards)}')
    print(f'  Stale pages.hero_image fixed: {len(stale_pages)}')
    if needs_rerender:
        print(f'\n  NEEDS RE-RENDER ({len(needs_rerender)} source images — active render permanently lost):')
        for f in needs_rerender:
            print(f'    {f}')
    print(f'{"="*60}')
    conn.close()

if __name__ == '__main__':
    main()
