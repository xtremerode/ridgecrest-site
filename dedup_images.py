#!/usr/bin/env python3
"""
Image deduplication script for Ridgecrest Designs media library.
Finds byte-identical files, picks a canonical filename, remaps all DB
references, then deletes the non-canonical files.

Usage:
  python3 dedup_images.py          # dry-run (no changes)
  python3 dedup_images.py --execute # apply all changes
"""
import sys, os, re, json, hashlib
import psycopg2, psycopg2.extras

EXECUTE = '--execute' in sys.argv
OPT_DIR = '/home/claudeuser/agent/preview/assets/images-opt'

DB_PARAMS = dict(
    host='127.0.0.1', port=5432,
    user='agent_user', password='StrongPass123!',
    dbname='marketing_agent',
)

def db_conn():
    c = psycopg2.connect(**DB_PARAMS,
                         cursor_factory=psycopg2.extras.RealDictCursor)
    c.autocommit = False
    return c

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def is_base_file(fname):
    """True if fname is a base image (not a responsive size, not an AI render)."""
    if re.search(r'_\d+w\.webp$', fname):
        return False
    if re.search(r'_ai_\d+\.webp$', fname):
        return False
    ext = fname.rsplit('.', 1)[-1].lower()
    if ext not in ('webp', 'jpg', 'jpeg', 'png'):
        return False
    return True

def canonical_rank(fname):
    """
    Lower rank = more canonical.
    Priority:
      0 = ff5b18_*_mv2.webp   (clean Wix canonical)
      1 = ff5b18_* other      (Wix but non-standard suffix like _7Emv2)
      2 = plain name, no space, no upload prefix
      3 = upload_* (with timestamp prefix)
      4 = anything with spaces in name
    """
    if fname.startswith('ff5b18_'):
        if fname.endswith('_mv2.webp'):
            return (0, fname)
        return (1, fname)
    if fname.startswith('upload_'):
        m = re.match(r'^upload_(\d+)_', fname)
        ts = int(m.group(1)) if m else 9999999999
        return (3, ts)
    if ' ' in fname:
        return (4, fname)
    return (2, fname)

def responsive_sizes_on_disk(base_fname):
    """Return list of responsive-size filenames that exist on disk for a base file."""
    stem = base_fname.rsplit('.', 1)[0]
    suffixes = ['_201w.webp', '_480w.webp', '_960w.webp', '_1920w.webp']
    result = []
    for s in suffixes:
        cand = stem + s
        if os.path.isfile(os.path.join(OPT_DIR, cand)):
            result.append(cand)
    return result

def ai_renders_on_disk(base_fname):
    """Return list of AI render filenames on disk for this base."""
    # Get the stem up to _mv2 or full stem
    stem = base_fname.rsplit('.', 1)[0]
    # Strip any existing _ai_N suffix
    stem = re.sub(r'_ai_\d+$', '', stem)
    renders = []
    for f in sorted(os.listdir(OPT_DIR)):
        if f.startswith(stem + '_ai_') and re.search(r'_ai_\d+\.webp$', f):
            renders.append(f)
    return renders

def ai_render_responsive_sizes_on_disk(render_fname):
    stem = render_fname[:-5]  # strip .webp
    suffixes = ['_201w.webp', '_480w.webp', '_960w.webp', '_1920w.webp']
    result = []
    for s in suffixes:
        cand = stem + s
        if os.path.isfile(os.path.join(OPT_DIR, cand)):
            result.append(cand)
    return result

print(f"{'DRY RUN' if not EXECUTE else 'EXECUTING'} — Image Deduplication")
print("=" * 60)

# ── Step 1: Hash all base files ──────────────────────────────
print("\n[1/5] Hashing all base images…")
hash_map = {}  # hash -> [fname, ...]
all_files = sorted(os.listdir(OPT_DIR))
base_files = [f for f in all_files if is_base_file(f)]
print(f"      {len(base_files)} base files to hash")

for i, fname in enumerate(base_files):
    path = os.path.join(OPT_DIR, fname)
    try:
        if os.path.getsize(path) < 100:
            continue  # skip stubs
        h = sha256_file(path)
        hash_map.setdefault(h, []).append(fname)
    except Exception as e:
        print(f"      WARN: could not hash {fname}: {e}")
    if (i+1) % 100 == 0:
        print(f"      … {i+1}/{len(base_files)}")

# ── Step 2: Find duplicate groups ────────────────────────────
print("\n[2/5] Finding duplicates…")
dup_groups = {h: fnames for h, fnames in hash_map.items() if len(fnames) > 1}
print(f"      {len(dup_groups)} duplicate groups found")

if not dup_groups:
    print("\nNo duplicates found. Nothing to do.")
    sys.exit(0)

# ── Step 3: Determine canonical and duplicates ────────────────
remap = {}    # old_fname -> canonical_fname
to_delete = []  # non-canonical filenames

for h, fnames in sorted(dup_groups.items()):
    ranked = sorted(fnames, key=canonical_rank)
    canonical = ranked[0]
    dupes = ranked[1:]
    print(f"\n  Hash group ({h[:12]}…):")
    print(f"    KEEP:   {canonical}")
    for d in dupes:
        print(f"    DELETE: {d}")
        remap[d] = canonical
        to_delete.append(d)

# ── Step 4: Check DB references ──────────────────────────────
print("\n\n[3/5] Checking DB references…")
conn = db_conn()
cur = conn.cursor()

ref_updates = []  # structured list of what to do

for old_fname, can_fname in remap.items():
    old_path = f'/assets/images-opt/{old_fname}'
    new_path = f'/assets/images-opt/{can_fname}'

    # pages.hero_image  (exact and cache-busted)
    cur.execute("SELECT slug, hero_image FROM pages WHERE hero_image = %s OR hero_image LIKE %s",
                (old_path, old_path + '?%'))
    for row in cur.fetchall():
        ref_updates.append({'type': 'pages', 'slug': row['slug'],
                            'old': row['hero_image'], 'new': new_path})
        print(f"    pages.hero_image [{row['slug']}]: {old_fname} → {can_fname}")

    # card_settings.image
    cur.execute("SELECT id, page_slug, card_id FROM card_settings WHERE image = %s OR image LIKE %s",
                (old_path, old_path + '?%'))
    for row in cur.fetchall():
        ref_updates.append({'type': 'card_settings', 'id': row['id'],
                            'old': old_path, 'new': new_path})
        print(f"    card_settings [{row['page_slug']}/{row['card_id']}]: {old_fname} → {can_fname}")

    # blog_posts.featured_image
    cur.execute("SELECT id FROM blog_posts WHERE featured_image = %s OR featured_image LIKE %s",
                (old_path, old_path + '?%'))
    for row in cur.fetchall():
        ref_updates.append({'type': 'blog_posts', 'id': row['id'],
                            'old': old_path, 'new': new_path})
        print(f"    blog_posts [{row['id']}]: {old_fname} → {can_fname}")

    # image_labels.filename (label/metadata row for this base image)
    cur.execute("SELECT filename, active_version FROM image_labels WHERE filename = %s", (old_fname,))
    old_row = cur.fetchone()
    if old_row:
        cur.execute("SELECT filename, active_version FROM image_labels WHERE filename = %s", (can_fname,))
        can_row = cur.fetchone()
        ref_updates.append({'type': 'image_labels_merge',
                            'old_fname': old_fname, 'can_fname': can_fname,
                            'old_active': old_row['active_version'],
                            'can_active': can_row['active_version'] if can_row else None})
        print(f"    image_labels merge: {old_fname} → {can_fname}"
              f" (old active_ver={old_row['active_version']})")

    # image_labels.active_version pointing at an AI render of the old base
    old_stem = old_fname.rsplit('.', 1)[0]
    cur.execute("SELECT filename, active_version FROM image_labels WHERE active_version LIKE %s",
                (f'{old_stem}_ai_%.webp',))
    for row in cur.fetchall():
        ref_updates.append({'type': 'image_labels_av_reset',
                            'base_fname': row['filename'], 'old_av': row['active_version']})
        print(f"    image_labels.active_version NULL for {row['filename']} "
              f"(was render of deleted {old_fname})")

    # portfolio_projects.gallery_json
    # The JSON stores stems like "ff5b18_xxx_mv2" or "ff5b18_xxx_7Emv2"
    old_stem_j = old_fname.rsplit('.', 1)[0]   # e.g. ff5b18_xxx_mv2
    can_stem_j = can_fname.rsplit('.', 1)[0]   # e.g. ff5b18_xxx_mv2
    if old_stem_j != can_stem_j:
        cur.execute("SELECT id, slug, gallery_json FROM portfolio_projects WHERE gallery_json LIKE %s",
                    (f'%{old_stem_j}%',))
        for row in cur.fetchall():
            ref_updates.append({'type': 'portfolio_gallery', 'id': row['id'],
                                'slug': row['slug'],
                                'old_stem': old_stem_j, 'new_stem': can_stem_j})
            print(f"    portfolio_projects [{row['slug']}]: {old_stem_j} → {can_stem_j}")

if not ref_updates:
    print("    (no DB references to update)")

# ── Step 5: Deletion plan ─────────────────────────────────────
print("\n\n[4/5] Files to delete:")
all_to_delete_files = []   # absolute paths
ai_move_plan = []          # [(old_render_path, new_render_path), ...]

for old_fname in to_delete:
    can_fname = remap[old_fname]
    print(f"\n  BASE: {old_fname}")

    # Responsive sizes of the base duplicate
    for rs in responsive_sizes_on_disk(old_fname):
        all_to_delete_files.append(os.path.join(OPT_DIR, rs))
        print(f"    RESP: {rs}")

    # AI renders of the duplicate
    old_renders = ai_renders_on_disk(old_fname)
    can_renders = ai_renders_on_disk(can_fname)

    if old_renders:
        if can_renders:
            # Canonical already has AI renders — orphan/delete duplicate's renders
            print(f"    NOTE: {len(old_renders)} AI render(s) for deleted base; "
                  f"canonical already has {len(can_renders)} — deleting orphaned renders")
            for r in old_renders:
                all_to_delete_files.append(os.path.join(OPT_DIR, r))
                print(f"    AI:   {r}")
                for rs in ai_render_responsive_sizes_on_disk(r):
                    all_to_delete_files.append(os.path.join(OPT_DIR, rs))
                    print(f"    AIRS: {rs}")
        else:
            # Move AI renders to canonical's series so they're not lost
            can_stem = can_fname.rsplit('.', 1)[0]
            print(f"    NOTE: {len(old_renders)} AI render(s) → moving to canonical series")
            for n, old_r in enumerate(sorted(old_renders), 1):
                new_r = f'{can_stem}_ai_{n}.webp'
                ai_move_plan.append((old_r, new_r))
                print(f"    MOVE: {old_r} → {new_r}")
                for rs in ai_render_responsive_sizes_on_disk(old_r):
                    old_stem_r = old_r[:-5]
                    new_rs = rs.replace(old_stem_r, f'{can_stem}_ai_{n}')
                    ai_move_plan.append((rs, new_rs))
                    print(f"    MVRS: {rs} → {new_rs}")

    all_to_delete_files.append(os.path.join(OPT_DIR, old_fname))

# Deduplicate deletion list (some paths might appear twice)
all_to_delete_files = list(dict.fromkeys(all_to_delete_files))
existing_to_delete = [p for p in all_to_delete_files if os.path.isfile(p)]

print(f"\nFiles to delete: {len(existing_to_delete)}")
print(f"AI renders to move: {len(ai_move_plan)}")
print(f"DB updates: {len(ref_updates)}")

if not EXECUTE:
    print("\n" + "="*60)
    print("DRY RUN complete. Run with --execute to apply changes.")
    sys.exit(0)

# ── EXECUTE ────────────────────────────────────────────────────
print("\n\n[5/5] Applying changes…")

try:
    # ── DB updates ────────────────────────────────────────────
    for u in ref_updates:
        t = u['type']
        if t == 'pages':
            cur.execute("UPDATE pages SET hero_image = %s WHERE slug = %s AND hero_image = %s",
                        (u['new'], u['slug'], u['old']))
            print(f"  ✓ pages.hero_image [{u['slug']}]")

        elif t == 'card_settings':
            cur.execute("UPDATE card_settings SET image = %s WHERE id = %s",
                        (u['new'], u['id']))
            print(f"  ✓ card_settings id={u['id']}")

        elif t == 'blog_posts':
            cur.execute("UPDATE blog_posts SET featured_image = %s WHERE id = %s",
                        (u['new'], u['id']))
            print(f"  ✓ blog_posts id={u['id']}")

        elif t == 'image_labels_merge':
            # If old had an active_version and canonical doesn't, carry it over
            if u['can_active'] is None and u['old_active'] is not None:
                cur.execute("""
                    INSERT INTO image_labels (filename, active_version)
                    VALUES (%s, %s)
                    ON CONFLICT (filename) DO UPDATE
                    SET active_version = EXCLUDED.active_version
                """, (u['can_fname'], u['old_active']))
                print(f"  ✓ Carried active_version to {u['can_fname']}")
            cur.execute("DELETE FROM image_labels WHERE filename = %s", (u['old_fname'],))
            print(f"  ✓ image_labels row deleted for {u['old_fname']}")

        elif t == 'image_labels_av_reset':
            cur.execute("UPDATE image_labels SET active_version = NULL WHERE filename = %s",
                        (u['base_fname'],))
            print(f"  ✓ image_labels.active_version → NULL for {u['base_fname']}")

        elif t == 'portfolio_gallery':
            cur.execute("SELECT gallery_json FROM portfolio_projects WHERE id = %s", (u['id'],))
            row = cur.fetchone()
            if row and row['gallery_json']:
                new_gj = row['gallery_json'].replace(u['old_stem'], u['new_stem'])
                cur.execute("UPDATE portfolio_projects SET gallery_json = %s WHERE id = %s",
                            (new_gj, u['id']))
                print(f"  ✓ portfolio_projects [{u['slug']}] gallery_json updated")

    conn.commit()
    print("  ✓ All DB changes committed")

    # ── Move AI renders ───────────────────────────────────────
    for old_r, new_r in ai_move_plan:
        old_path = os.path.join(OPT_DIR, old_r)
        new_path = os.path.join(OPT_DIR, new_r)
        if os.path.isfile(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"  ✓ Moved {old_r} → {new_r}")
        elif os.path.exists(new_path):
            # Target already exists — just delete the source
            os.remove(old_path)
            print(f"  ✓ Removed {old_r} (target {new_r} already exists)")

    # ── Delete duplicate files ────────────────────────────────
    deleted = 0
    for fpath in existing_to_delete:
        if os.path.isfile(fpath):
            os.remove(fpath)
            deleted += 1
            print(f"  ✓ Deleted {os.path.basename(fpath)}")

    print(f"\n  ✓ Deleted {deleted} files")
    print("\nDeduplication complete.")

except Exception as e:
    conn.rollback()
    print(f"\n  ✗ ERROR: {e}")
    import traceback; traceback.print_exc()
    print("  DB changes rolled back. No files deleted.")
    sys.exit(1)
finally:
    conn.close()
