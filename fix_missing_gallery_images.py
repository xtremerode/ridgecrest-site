#!/usr/bin/env python3
"""
fix_missing_gallery_images.py

Reads /tmp/wix_scan_results.json (from scan_wix_hashes.js),
compares against gallery_json in DB, and for each project:
  1. Images on disk but NOT in gallery_json → added directly to gallery_json
  2. Images NOT on disk → downloaded via wsrv.nl proxy and saved, then added
  3. All affected projects re-rendered
  4. Gallery counts updated

Usage:
  python3 fix_missing_gallery_images.py
"""

import json, os, sys, time, subprocess, urllib.request, urllib.error
import psycopg2
from psycopg2.extras import RealDictCursor
from PIL import Image
import io

# ── Config ────────────────────────────────────────────────────────────────────
DB_DSN     = "host=127.0.0.1 dbname=marketing_agent user=agent_user password=StrongPass123!"
OPT_DIR    = "/home/claudeuser/agent/preview/assets/images-opt"
SCAN_FILE  = "/tmp/wix_scan_results.json"
TOKEN      = "ea501a45abb967a5fde5feaa14361a230d0eed48bd76a6284d868ab7737e4365"
SERVER     = "http://127.0.0.1:8081"

# Wix image URLs to try (in order of quality preference)
WIX_URL_TEMPLATES = [
    "https://static.wixstatic.com/media/{hash}_mv2.jpg/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/{hash}_mv2.jpg",
    "https://static.wixstatic.com/media/{hash}_mv2.png/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/{hash}_mv2.png",
    "https://static.wixstatic.com/media/{hash}_mv2.webp/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/{hash}_mv2.webp",
]

# Shared site-wide hashes that appear on every project page — NOT project gallery images
# These are portfolio thumbnails and site-wide graphics
LOGO_HASH = "ff5b18_39307a9fb5f448aa8699880d142bb1fe"

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_on_disk():
    """Return set of base hashes (with _mv2) that exist on disk."""
    files = os.listdir(OPT_DIR)
    result = set()
    for f in files:
        if f.startswith('ff5b18_') and f.endswith('.webp') and '_ai_' not in f:
            # Skip variant files
            if any(f.endswith(f'_{w}w.webp') for w in ['201','480','960','1920']):
                continue
            result.add(f.replace('.webp', ''))
    return result

def get_gallery_hashes(cur, slug):
    """Return set of hashes (with _mv2) currently in gallery_json for this project."""
    cur.execute("SELECT gallery_json FROM portfolio_projects WHERE slug=%s", (slug,))
    row = cur.fetchone()
    if not row:
        return set()
    gallery = json.loads(row['gallery_json'] or '[]')
    hashes = set()
    for item in gallery:
        if isinstance(item, list) and len(item) >= 1:
            hashes.add(item[0])  # e.g. 'ff5b18_xxx_mv2'
        elif isinstance(item, dict):
            h = item.get('hash', '')
            if h: hashes.add(h)
    return hashes

def get_gallery_json(cur, slug):
    """Return parsed gallery_json list for this project."""
    cur.execute("SELECT gallery_json FROM portfolio_projects WHERE slug=%s", (slug,))
    row = cur.fetchone()
    if not row:
        return []
    return json.loads(row['gallery_json'] or '[]')

def download_via_wsrv(hash_no_mv2):
    """Try to download image via wsrv.nl proxy. Returns bytes or None."""
    for ext in ['jpg', 'png', 'webp']:
        wix_url = f"https://static.wixstatic.com/media/{hash_no_mv2}_mv2.{ext}"
        proxy_url = f"https://wsrv.nl/?url={urllib.parse.quote(wix_url, safe=':/')}&q=90&output=jpg"
        try:
            req = urllib.request.Request(proxy_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if len(data) > 5000:  # valid image check
                    # Verify it's a real image
                    try:
                        Image.open(io.BytesIO(data)).verify()
                        return data, ext
                    except Exception:
                        continue
        except Exception:
            continue
    return None, None

def to_webp(img_bytes, src_ext, dest_path):
    """Convert image bytes to WebP and save to dest_path."""
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    # High quality
    img.save(dest_path, 'WEBP', quality=90, method=6)
    return dest_path

def generate_variants(base_webp_path):
    """Generate _480w and _960w variants for the gallery grid."""
    base = os.path.splitext(base_webp_path)[0]
    img = Image.open(base_webp_path)
    orig_w, orig_h = img.size
    for width in [480, 960, 1920]:
        variant_path = f"{base}_{width}w.webp"
        if os.path.isfile(variant_path):
            continue
        if orig_w <= width:
            img.save(variant_path, 'WEBP', quality=90)
        else:
            ratio = width / orig_w
            new_h = int(orig_h * ratio)
            resized = img.resize((width, new_h), Image.LANCZOS)
            resized.save(variant_path, 'WEBP', quality=90)
    img.close()

def add_to_gallery_json(cur, conn, slug, hash_mv2, guessed_ext='jpg'):
    """Append a hash to gallery_json for a project. Does nothing if already present."""
    gallery = get_gallery_json(cur, slug)
    existing = {item[0] if isinstance(item, list) else item.get('hash','') for item in gallery}
    if hash_mv2 in existing:
        return False  # already there
    gallery.append([hash_mv2, guessed_ext])
    cur.execute(
        "UPDATE portfolio_projects SET gallery_json=%s, updated_at=NOW() WHERE slug=%s",
        (json.dumps(gallery), slug)
    )
    conn.commit()
    return True

def update_image_labels(cur, conn, hash_mv2, slug):
    """Ensure image_labels has this image assigned to the project."""
    base_fname = hash_mv2 + '.webp'
    project_name = slug.replace('-', ' ').title()
    cur.execute("SELECT id FROM image_labels WHERE filename=%s", (base_fname,))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE image_labels
            SET gallery_project_slug=%s,
                label=COALESCE(NULLIF(label,''), %s)
            WHERE filename=%s
        """, (slug, project_name, base_fname))
    else:
        cur.execute("""
            INSERT INTO image_labels (filename, gallery_project_slug, label)
            VALUES (%s, %s, %s)
            ON CONFLICT (filename) DO UPDATE
              SET gallery_project_slug=EXCLUDED.gallery_project_slug,
                  label=COALESCE(NULLIF(image_labels.label,''), EXCLUDED.label)
        """, (base_fname, slug, project_name))
    conn.commit()

# ── Main ──────────────────────────────────────────────────────────────────────

import urllib.parse

def main():
    if not os.path.isfile(SCAN_FILE):
        print(f"ERROR: {SCAN_FILE} not found. Run scan_wix_hashes.js first.")
        sys.exit(1)

    with open(SCAN_FILE) as f:
        scan = json.load(f)

    on_disk = get_on_disk()
    print(f"Images on disk: {len(on_disk)}")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    total_added_from_disk = 0
    total_downloaded = 0
    total_failed = 0
    projects_updated = []

    for slug, data in scan.items():
        wix_hashes_bare = data.get('wixHashes', [])  # bare hashes without _mv2
        # Normalize: ensure all have _mv2 suffix
        wix_hashes = set()
        for h in wix_hashes_bare:
            wix_hashes.add(h + '_mv2' if not h.endswith('_mv2') else h)

        # Skip logo
        wix_hashes.discard(LOGO_HASH + '_mv2')
        wix_hashes.discard(LOGO_HASH)

        gallery_hashes = get_gallery_hashes(cur, slug)
        to_add = wix_hashes - gallery_hashes

        if not to_add:
            print(f"[{slug}] ✓ all {len(wix_hashes)} Wix images already in gallery")
            continue

        print(f"\n[{slug}] {len(to_add)} images to add ({len(gallery_hashes)} in gallery, {len(wix_hashes)} on Wix)")

        added = 0
        failed = 0
        for hash_mv2 in sorted(to_add):
            bare = hash_mv2.replace('_mv2', '')

            if hash_mv2 in on_disk:
                # Already on disk — just add to gallery_json
                disk_path = os.path.join(OPT_DIR, hash_mv2 + '.webp')
                # Guess ext from disk file (it's webp now, but original ext for gallery_json)
                ok = add_to_gallery_json(cur, conn, slug, hash_mv2, 'jpg')
                if ok:
                    update_image_labels(cur, conn, hash_mv2, slug)
                    # Generate variants if missing
                    try: generate_variants(disk_path)
                    except: pass
                    print(f"  ✓ {bare[:20]}... (from disk)")
                    added += 1
                    total_added_from_disk += 1
                else:
                    print(f"  - {bare[:20]}... (already in gallery, skipping)")
            else:
                # Not on disk — try wsrv.nl download
                print(f"  ↓ {bare[:20]}... downloading via wsrv.nl")
                img_bytes, src_ext = download_via_wsrv(bare)
                if img_bytes:
                    dest_path = os.path.join(OPT_DIR, hash_mv2 + '.webp')
                    try:
                        to_webp(img_bytes, src_ext, dest_path)
                        generate_variants(dest_path)
                        ok = add_to_gallery_json(cur, conn, slug, hash_mv2, src_ext or 'jpg')
                        if ok:
                            update_image_labels(cur, conn, hash_mv2, slug)
                        on_disk.add(hash_mv2)  # mark as now on disk
                        print(f"    ✓ downloaded ({len(img_bytes)//1024}KB)")
                        added += 1
                        total_downloaded += 1
                    except Exception as e:
                        print(f"    ✗ save failed: {e}")
                        failed += 1
                        total_failed += 1
                else:
                    print(f"    ✗ wsrv.nl failed — will need laptop bat file")
                    failed += 1
                    total_failed += 1
                time.sleep(0.5)  # rate limit wsrv.nl

        if added > 0:
            projects_updated.append(slug)
            print(f"  → Added {added} images to {slug}")

    cur.close()
    conn.close()

    print(f"\n{'='*55}")
    print(f"Summary:")
    print(f"  Added from disk (no download needed): {total_added_from_disk}")
    print(f"  Downloaded via wsrv.nl:               {total_downloaded}")
    print(f"  Failed (need laptop bat files):        {total_failed}")
    print(f"  Projects updated:                      {len(projects_updated)}")

    if projects_updated:
        print(f"\nRe-rendering {len(projects_updated)} updated projects...")
        import urllib.request
        req = urllib.request.Request(
            f"{SERVER}/admin/api/gallery/rerender-all",
            method='POST',
            headers={'X-Admin-Token': TOKEN, 'Content-Length': '0'}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                print(f"Re-render complete: {len(result.get('rendered',[]))} pages")
        except Exception as e:
            print(f"Re-render error: {e}")

    if total_failed > 0:
        print(f"\n⚠️  {total_failed} images could not be downloaded server-side.")
        print("   These need to be fetched from Henry's laptop via bat files.")
        print("   Bat files will be generated in preview/assets/ after manual scan.")

    print("\nDone.")

if __name__ == '__main__':
    main()
