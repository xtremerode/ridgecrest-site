#!/usr/bin/env python3
"""
Apply image metadata (alt text) to all HTML files in /home/claudeuser/agent/preview/
Steps:
1. Build hash->alt_text map from local HTML aria-labels
2. Fetch Wix pages to extract more hash->alt_text from img tags
3. Auto-generate alt text for images with no metadata
4. Apply alt text to HTML files (img tags + aria-label on bg divs)
5. Update PostgreSQL image_library table
"""

import re
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import html
import psycopg2
from pathlib import Path
from collections import defaultdict

PREVIEW_DIR = Path("/home/claudeuser/agent/preview")
IMAGE_DIR = PREVIEW_DIR / "assets" / "images"
DB_DSN = "postgresql://agent_user:StrongPass123!@localhost:5432/marketing_agent"

WIX_PAGES = [
    "https://www.ridgecrestdesigns.com",
    "https://www.ridgecrestdesigns.com/about",
    "https://www.ridgecrestdesigns.com/portfolio",
    "https://www.ridgecrestdesigns.com/contact",
    "https://www.ridgecrestdesigns.com/therdedit",
    "https://www.ridgecrestdesigns.com/california-process",
    "https://www.ridgecrestdesigns.com/bios",
]

# Page context for auto-generation
PAGE_CONTEXT = {
    "danville-dream.html": "Danville Dream Home luxury remodel by Ridgecrest Designs, Danville CA",
    "danville-hilltop.html": "Danville Hilltop Hideaway modern home remodel by Ridgecrest Designs, Danville CA",
    "pleasanton-custom.html": "Pleasanton custom home design-build by Ridgecrest Designs, Pleasanton CA",
    "alamo-luxury.html": "Alamo luxury home remodel by Ridgecrest Designs, Alamo CA",
    "lafayette-bistro.html": "Lafayette kitchen remodel by Ridgecrest Designs, Lafayette CA",
    "lafayette-luxury.html": "Lafayette luxury home remodel by Ridgecrest Designs, Lafayette CA",
    "san-ramon.html": "San Ramon custom home remodel by Ridgecrest Designs, San Ramon CA",
    "orinda-kitchen.html": "Orinda kitchen remodel by Ridgecrest Designs, Orinda CA",
    "sunol-homestead.html": "Sunol Homestead custom home by Ridgecrest Designs, Sunol CA",
    "portfolio.html": "Luxury design-build project by Ridgecrest Designs, Pleasanton CA",
    "about.html": "Ridgecrest Designs luxury design-build team, Pleasanton CA",
    "team.html": "Ridgecrest Designs team member, Pleasanton CA",
    "process.html": "Ridgecrest Designs design-build process, Pleasanton CA",
    "contact.html": "Ridgecrest Designs design-build firm, Pleasanton CA",
}
DEFAULT_ALT = "Luxury home remodel by Ridgecrest Designs, Pleasanton CA"
BLOG_ALT = "Luxury design-build project by Ridgecrest Designs"

def extract_hash_from_local_filename(fname):
    """Extract hash from local filename like ff5b18_abc123_mv2.jpg -> ff5b18_abc123"""
    # Handle _7Emv2 variant too
    m = re.match(r'^(.+?)_(?:7E)?mv2\.\w+$', fname)
    if m:
        return m.group(1)
    # Try without mv2
    m = re.match(r'^(.+?)\.\w+$', fname)
    if m:
        return m.group(1)
    return fname

def extract_hash_from_wix_url(url):
    """
    Extract hash from Wix CDN URL.
    URL like: https://static.wixstatic.com/media/ff5b18_abc123~mv2.jpg/...
    or: https://static.wixstatic.com/media/ff5b18_abc123%7Emv2.jpg
    Hash = part after /media/ up to first /, then URL-decode %7E to ~, then take part before ~mv2 or ~
    """
    m = re.search(r'/media/([^/?#]+)', url)
    if not m:
        return None
    raw = m.group(1)
    # URL decode
    decoded = urllib.parse.unquote(raw)
    # Take part before ~mv2 or just ~
    decoded = re.sub(r'~mv2.*$', '', decoded)
    decoded = re.sub(r'~.*$', '', decoded)
    # Remove file extension if present
    decoded = re.sub(r'\.\w{2,5}$', '', decoded)
    return decoded if decoded else None

def is_descriptive_alt(text):
    """Returns True if alt text is descriptive (>15 chars, not a raw filename)"""
    if not text or len(text.strip()) <= 15:
        return False
    if re.search(r'\.(jpg|png|webp|jpeg|gif|svg)', text, re.I):
        return False
    return True

def get_html_files(exclude_admin=True):
    """Get all HTML files in preview dir, excluding admin/"""
    files = []
    for f in PREVIEW_DIR.rglob("*.html"):
        if exclude_admin and "admin" in f.parts:
            continue
        files.append(f)
    return sorted(files)

def get_blog_html_files():
    """Get HTML files that appear to be blog posts"""
    blog_files = []
    for f in get_html_files():
        # Blog posts are not the main named pages
        name = f.name
        known = set(PAGE_CONTEXT.keys()) | {"index.html", "services.html", "sitemap.xml"}
        if name not in known and f.parent == PREVIEW_DIR:
            # Could be a project page
            pass
        # Check inside blog subdirectory or similar
        if "blog" in str(f).lower() or f.parent.name not in ("preview",):
            blog_files.append(f)
    return blog_files

# ============================================================
# STEP 1: Build hash->alt_text from local HTML aria-labels
# ============================================================
print("\n=== STEP 1: Extract aria-labels from local HTML files ===")
hash_to_alt = {}

for html_file in get_html_files():
    content = html_file.read_text(encoding='utf-8', errors='replace')
    # Find elements with background-image pointing to /assets/images/FILENAME AND aria-label
    # Pattern: aria-label="..." ... background-image:url('/assets/images/FILENAME')
    # or vice versa on same element

    # Find tags that have both aria-label and background-image in /assets/images/
    # We need to match on the same HTML tag
    # Look for opening tags with style containing background-image url
    tag_pattern = re.compile(
        r'<(?:div|section|figure|header|article)[^>]*'
        r'aria-label="([^"]+)"[^>]*'
        r'style="[^"]*background-image\s*:\s*url\([\'"]?/assets/images/([^\'")\s]+)[\'"]?\)[^"]*"[^>]*>',
        re.IGNORECASE | re.DOTALL
    )
    for m in tag_pattern.finditer(content):
        aria = html.unescape(m.group(1).strip())
        fname = Path(m.group(2)).name
        h = extract_hash_from_local_filename(fname)
        if is_descriptive_alt(aria) and h:
            if h not in hash_to_alt:
                hash_to_alt[h] = aria

    # Also check reverse order: style first, aria-label second
    tag_pattern2 = re.compile(
        r'<(?:div|section|figure|header|article)[^>]*'
        r'style="[^"]*background-image\s*:\s*url\([\'"]?/assets/images/([^\'")\s]+)[\'"]?\)[^"]*"[^>]*'
        r'aria-label="([^"]+)"[^>]*>',
        re.IGNORECASE | re.DOTALL
    )
    for m in tag_pattern2.finditer(content):
        fname = Path(m.group(1)).name
        h = extract_hash_from_local_filename(fname)
        aria = html.unescape(m.group(2).strip())
        if is_descriptive_alt(aria) and h:
            if h not in hash_to_alt:
                hash_to_alt[h] = aria

print(f"  Found {len(hash_to_alt)} hash->alt mappings from local aria-labels")

# ============================================================
# STEP 2: Fetch Wix pages and extract img alt text
# ============================================================
print("\n=== STEP 2: Fetch Wix pages for img alt text ===")

def fetch_page(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; MetadataScraper/1.0)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  WARNING: Could not fetch {url}: {e}")
        return ""

wix_found = 0
for page_url in WIX_PAGES:
    print(f"  Fetching {page_url}...")
    content = fetch_page(page_url)
    if not content:
        continue

    # Find <img ... src="...wixstatic.com/media/HASH..." alt="...">
    img_pattern = re.compile(
        r'<img[^>]+src="([^"]*wixstatic\.com/media/[^"]+)"[^>]*alt="([^"]*)"[^>]*>|'
        r'<img[^>]+alt="([^"]*)"[^>]*src="([^"]*wixstatic\.com/media/[^"]+)"[^>]*>',
        re.IGNORECASE | re.DOTALL
    )
    for m in img_pattern.finditer(content):
        if m.group(1):
            src, alt = m.group(1), m.group(2)
        else:
            alt, src = m.group(3), m.group(4)

        alt = html.unescape(alt.strip()) if alt else ""
        h = extract_hash_from_wix_url(src)
        if h and is_descriptive_alt(alt):
            if h not in hash_to_alt:
                hash_to_alt[h] = alt
                wix_found += 1

print(f"  Found {wix_found} additional mappings from Wix pages")
print(f"  Total hash->alt mappings so far: {len(hash_to_alt)}")

# ============================================================
# STEP 3: Get all local images and build reverse map (hash -> pages)
# ============================================================
print("\n=== STEP 3: Build image->pages reference map ===")

all_local_images = {}
for img_file in IMAGE_DIR.iterdir():
    h = extract_hash_from_local_filename(img_file.name)
    if h:
        all_local_images[img_file.name] = h

print(f"  Total local images: {len(all_local_images)}")

# Build map: hash -> list of page filenames that reference it
hash_to_pages = defaultdict(list)
all_html_files = get_html_files()

for html_file in all_html_files:
    content = html_file.read_text(encoding='utf-8', errors='replace')
    for img_name, h in all_local_images.items():
        if img_name in content:
            hash_to_pages[h].append(html_file.name)

# ============================================================
# STEP 3b: Auto-generate alt text for images with no metadata
# ============================================================
print("\n=== STEP 3b: Auto-generate alt text for unmapped images ===")

auto_generated = 0
for img_name, h in all_local_images.items():
    if h in hash_to_alt:
        continue  # Already have alt text

    pages = hash_to_pages.get(h, [])

    # Find first matching page with a known context
    alt = None
    for page in pages:
        if page in PAGE_CONTEXT:
            alt = PAGE_CONTEXT[page]
            break

    if alt is None:
        # Check if it's in a blog-like file
        for page in pages:
            if page not in PAGE_CONTEXT and page not in ("index.html", "services.html", "sitemap.xml"):
                alt = BLOG_ALT
                break

    if alt is None:
        if not pages:
            alt = DEFAULT_ALT
        else:
            alt = DEFAULT_ALT

    hash_to_alt[h] = alt
    auto_generated += 1

discovered_count = len(hash_to_alt) - auto_generated
print(f"  Auto-generated: {auto_generated}")
print(f"  From discovered metadata: {discovered_count}")
print(f"  Total hash->alt: {len(hash_to_alt)}")

# ============================================================
# STEP 4: Apply alt text to HTML files
# ============================================================
print("\n=== STEP 4: Apply alt text to HTML files ===")

files_updated = 0
files_unchanged = 0
img_tags_updated = 0
aria_labels_added = 0

for html_file in all_html_files:
    original_content = html_file.read_text(encoding='utf-8', errors='replace')
    content = original_content

    # Part A: Add/fill alt on <img> tags
    def replace_img_alt(m):
        global img_tags_updated
        full_tag = m.group(0)
        src_match = re.search(r'src=["\']([^"\']+)["\']', full_tag, re.IGNORECASE)
        if not src_match:
            return full_tag
        src = src_match.group(1)

        # Extract filename from src
        fname = Path(src).name
        h = extract_hash_from_local_filename(fname)
        if not h or h not in hash_to_alt:
            return full_tag

        alt_text = hash_to_alt[h]

        # Check existing alt attribute
        alt_match = re.search(r'\balt\s*=\s*"([^"]*)"', full_tag, re.IGNORECASE)
        if alt_match:
            existing = alt_match.group(1).strip()
            if existing:  # Already has meaningful alt text
                return full_tag
            # Empty alt - fill it in
            new_tag = full_tag[:alt_match.start(1)] + alt_text + full_tag[alt_match.end(1):]
            img_tags_updated += 1
            return new_tag
        else:
            # No alt attribute - add it before the closing >
            # Find position to insert (before /> or >)
            close_match = re.search(r'\s*/?>$', full_tag)
            if close_match:
                insert_pos = close_match.start()
                new_tag = full_tag[:insert_pos] + f' alt="{alt_text}"' + full_tag[insert_pos:]
                img_tags_updated += 1
                return new_tag
            return full_tag

    # Match img tags that reference /assets/images/
    img_pattern = re.compile(
        r'<img\b[^>]*src=["\'][^"\']*assets/images/[^"\']+["\'][^>]*(?:/>|>)',
        re.IGNORECASE | re.DOTALL
    )
    content = img_pattern.sub(replace_img_alt, content)

    # Part B: Add aria-label to background-image elements missing it
    def replace_bg_aria(m):
        global aria_labels_added
        full_tag = m.group(0)

        # Check if aria-label already exists on this tag
        if re.search(r'\baria-label\s*=', full_tag, re.IGNORECASE):
            return full_tag

        # Extract the image filename
        bg_match = re.search(
            r'background-image\s*:\s*url\([\'"]?/assets/images/([^\'")\s]+)[\'"]?\)',
            full_tag, re.IGNORECASE
        )
        if not bg_match:
            return full_tag

        fname = Path(bg_match.group(1)).name
        h = extract_hash_from_local_filename(fname)
        if not h or h not in hash_to_alt:
            return full_tag

        alt_text = hash_to_alt[h]

        # Add role="img" and aria-label after the tag name
        # Find end of tag name
        tag_name_match = re.match(r'<(\w+)', full_tag)
        if tag_name_match:
            insert_pos = tag_name_match.end()
            new_tag = full_tag[:insert_pos] + f' role="img" aria-label="{alt_text}"' + full_tag[insert_pos:]
            aria_labels_added += 1
            return new_tag
        return full_tag

    bg_pattern = re.compile(
        r'<(?:div|section|figure|header|article)\b[^>]*background-image\s*:\s*url\([\'"]?/assets/images/[^\'")\s]+[\'"]?\)[^>]*>',
        re.IGNORECASE | re.DOTALL
    )
    content = bg_pattern.sub(replace_bg_aria, content)

    if content != original_content:
        html_file.write_text(content, encoding='utf-8')
        files_updated += 1
    else:
        files_unchanged += 1

print(f"  HTML files updated: {files_updated}")
print(f"  HTML files unchanged: {files_unchanged}")
print(f"  <img> tags updated: {img_tags_updated}")
print(f"  aria-labels added: {aria_labels_added}")

# ============================================================
# STEP 5: Update PostgreSQL image_library table
# ============================================================
print("\n=== STEP 5: Update PostgreSQL database ===")

try:
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Check if alt_text column exists, add if not
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='image_library' AND column_name='alt_text'
    """)
    if not cur.fetchone():
        print("  Adding alt_text column to image_library...")
        cur.execute("ALTER TABLE image_library ADD COLUMN IF NOT EXISTS alt_text TEXT;")
        conn.commit()
        print("  Column added.")
    else:
        print("  alt_text column already exists.")

    # Update rows
    db_updated = 0
    for h, alt in hash_to_alt.items():
        cur.execute(
            "UPDATE image_library SET alt_text = %s WHERE original_url LIKE %s AND (alt_text IS NULL OR alt_text = '')",
            (alt, f'%{h}%')
        )
        db_updated += cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Database rows updated: {db_updated}")

except Exception as e:
    print(f"  WARNING: Database update failed: {e}")

# ============================================================
# STEP 6: Final report
# ============================================================
print("\n=== FINAL REPORT ===")
total_images = len(all_local_images)
images_with_alt = len([h for h in (all_local_images.values()) if h in hash_to_alt])
images_still_missing = total_images - images_with_alt

print(f"  Total local images: {total_images}")
print(f"  Images with alt text (discovered from metadata): {discovered_count}")
print(f"  Images with alt text (auto-generated): {auto_generated}")
print(f"  Images with alt text total: {images_with_alt}")
print(f"  Images still missing alt text: {images_still_missing}")
print(f"  HTML files updated: {files_updated}")
print(f"  HTML files no changes needed: {files_unchanged}")
print(f"  <img> tags updated: {img_tags_updated}")
print(f"  aria-labels added to background-image elements: {aria_labels_added}")
